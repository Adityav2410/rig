#!/usr/bin/env python3
"""Pretty-print a rig trace.jsonl file for human reading.

Events are sorted by timestamp and grouped into "==== Step: N ====" blocks (events
with no step field, e.g. agent.run.start, get their own "-" block), seq-ascending
within each block.

Usage:
    python scripts/parse_trace.py                      # newest file in traces/
    python scripts/parse_trace.py traces/<run>.jsonl
    python scripts/parse_trace.py traces/<run>.jsonl --out notes/trace.txt
    python scripts/parse_trace.py traces/<run>.jsonl --kind tool.result  # substring match
    python scripts/parse_trace.py traces/<run>.jsonl --raw | less
"""

import argparse
import json
import sys
from contextlib import ExitStack
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

DEFAULT_MAX_CHARS = 240

# Tolerates both shapes this project has used for a trace line:
#   - the week-1 sketch: {"event": kind, "run_id", "seq", "ts", **fields}
#   - what rig/trace.py actually writes: {"kind", "run_id", "seq", "ts", "fields": {...}}
_ENVELOPE_KEYS = {"kind", "event", "run_id", "seq", "ts", "fields"}


def truncate(value, max_chars: int) -> str:
    text = str(value)
    if len(text) <= max_chars:
        return text
    return f"{text[:max_chars]}… (+{len(text) - max_chars} chars)"


def as_json(value, max_chars: int) -> str:
    text = value if isinstance(value, str) else json.dumps(value)
    text = text.replace("\n", "\\n")  # keep every value a scannable one-liner
    return truncate(text, max_chars)


def fmt_ts(rec: dict) -> str:
    if "ts" not in rec:
        return "?"
    return datetime.fromtimestamp(rec["ts"], tz=UTC).strftime("%H:%M:%S.%f")[:-3]


def event_fields(rec: dict) -> tuple[str, dict]:
    kind = rec.get("kind") or rec.get("event") or "?"
    if "fields" in rec:
        return kind, rec["fields"]
    return kind, {k: v for k, v in rec.items() if k not in _ENVELOPE_KEYS}


def summarize_block(block: dict, max_chars: int) -> str:
    btype = block.get("type")
    if btype == "text":
        return f"text: {truncate(block.get('text', ''), max_chars)!r}"
    if btype == "thinking":
        thinking = block.get("thinking", "")
        return f"thinking: {truncate(thinking, max_chars)!r}" if thinking else "thinking: (empty)"
    if btype == "tool_use":
        name, input_ = block.get("name"), block.get("input", {})
        return f"tool_use[{block.get('id')}]: {name}({as_json(input_, max_chars)})"
    if btype == "tool_result":
        return (
            f"tool_result[{block.get('tool_use_id')}]: {as_json(block.get('content'), max_chars)}"
        )
    return f"{btype}: {as_json(block, max_chars)}"


def summarize_content(content, max_chars: int) -> list[str]:
    if isinstance(content, str):
        return [as_json(content, max_chars)]
    if isinstance(content, list):
        return [summarize_block(b, max_chars) for b in content if isinstance(b, dict)]
    return [as_json(content, max_chars)]


def is_message(value) -> bool:
    return isinstance(value, dict) and "role" in value and "content" in value


def is_block_list(value) -> bool:
    return (
        isinstance(value, list)
        and bool(value)
        and all(isinstance(b, dict) and "type" in b for b in value)
    )


def format_field(key: str, value, max_chars: int) -> list[str]:
    # Known "rich" shapes get pretty-printed; anything else is printed as-is rather
    # than skipped, so a field this script has never seen still shows up.
    if is_message(value):
        lines = [f"       {key}.role: {value.get('role')}"]
        lines += [f"       - {s}" for s in summarize_content(value.get("content"), max_chars)]
        return lines
    if is_block_list(value):
        lines = [f"       {key}:"]
        lines += [f"       - {s}" for s in summarize_content(value, max_chars)]
        return lines
    return [f"       {key}: {as_json(value, max_chars)}"]


def format_event(idx: int, rec: dict, max_chars: int) -> str:
    kind, fields = event_fields(rec)
    run_id = str(rec.get("run_id", "?"))[:8]
    lines = [f"[{idx:04d}] seq={rec.get('seq', '?'):<4} t={fmt_ts(rec):<15} run={run_id}  {kind}"]
    for key, value in fields.items():
        lines.extend(format_field(key, value, max_chars))
    return "\n".join(lines)


def step_of(rec: dict) -> int | None:
    _, fields = event_fields(rec)
    return fields.get("step")


def step_header(step) -> str:
    return f"==== Step: {step if step is not None else '-'} ===="


def indent(text: str, prefix: str = "    ") -> str:
    return "\n".join(prefix + line for line in text.splitlines())


def iter_records(path: Path):
    fh = sys.stdin if str(path) == "-" else path.open()
    with fh:
        for lineno, line in enumerate(fh, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                yield lineno, json.loads(line)
            except json.JSONDecodeError as e:
                print(f"warning: {path}:{lineno}: skipping malformed line ({e})", file=sys.stderr)


def latest_trace(directory: Path) -> Path:
    files = sorted(directory.glob("*.jsonl"), key=lambda p: p.stat().st_mtime)
    if not files:
        raise SystemExit(f"no .jsonl trace files found in {directory}")
    return files[-1]


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("trace", nargs="?", help="path to a trace .jsonl file, or '-' for stdin")
    parser.add_argument(
        "--dir", default="traces", help="dir to pick the newest .jsonl from (default: traces/)"
    )
    parser.add_argument("--out", help="write output to this file instead of stdout")
    parser.add_argument(
        "--raw", action="store_true", help="print each record as raw formatted JSON"
    )
    parser.add_argument("--kind", help="only show events whose kind contains this substring")
    parser.add_argument(
        "--max-chars", type=int, default=DEFAULT_MAX_CHARS, help="truncate long strings"
    )
    args = parser.parse_args()

    path = Path(args.trace) if args.trace else latest_trace(Path(args.dir))
    if str(path) != "-" and not path.exists():
        raise SystemExit(f"no such file: {path}")

    records = [rec for _, rec in iter_records(path)]
    records.sort(key=lambda r: (r.get("ts", 0.0), r.get("seq", 0)))

    unset = object()
    with ExitStack() as stack:
        out = stack.enter_context(Path(args.out).open("w")) if args.out else sys.stdout
        current_step = unset
        for idx, rec in enumerate(records, start=1):
            kind, _ = event_fields(rec)
            if args.kind and args.kind not in kind:
                continue
            step = step_of(rec)
            if step != current_step:
                if current_step is not unset:
                    print(file=out)
                print(step_header(step), file=out)
                print(file=out)
                current_step = step
            body = json.dumps(rec, indent=2) if args.raw else format_event(idx, rec, args.max_chars)
            print(indent(body), file=out)
            print(file=out)


if __name__ == "__main__":
    main()
