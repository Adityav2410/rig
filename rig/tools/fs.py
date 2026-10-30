import difflib
import subprocess
from pathlib import Path

from ..core.exceptions import PathEscapesWorkspace, ToolError
from ..sandbox.workspace import Workspace
from . import tool
from .schema import ToolInputSchema, ToolPropertySchema, ToolPropertyType

MAX_FILES = 500
MAX_LINES = 400


def resolve(ws: Workspace, rel: str) -> Path:
    """Resolve the path relative to a workspace."""
    p = (ws.root / rel).resolve()
    if not p.is_relative_to(ws.root):  # in case of symlinks this can break
        raise PathEscapesWorkspace(
            f"{rel}: outside the repository", status="path.escapes_workspace"
        )
    return p


_EDIT = ToolPropertySchema(
    type=ToolPropertyType.OBJECT,
    properties={
        "old_text": ToolPropertySchema(
            type=ToolPropertyType.STRING,
            description="Text to replace. Must appear exactly once in the file. "
            "Leave empty to create a new file.",
        ),
        "new_text": ToolPropertySchema(
            type=ToolPropertyType.STRING, description="Replacement text."
        ),
    },
    required=["old_text", "new_text"],
)


@tool(
    name="edit_file",
    description="Replace text in a file. Use this, not `bash`, to change source code. Each "
    "edit's `old_text` must appear exactly once in the file, indentation included: read the "
    "file first and include enough lines to make it unique. All edits are checked against the "
    "file before anything changes; if one fails, nothing is written and the error shows the "
    "closest lines. Use plain newlines; the file keeps its own line endings. To create a file, "
    "pass one edit with an empty `old_text`.",
    input_schema=ToolInputSchema(
        properties={
            "path": ToolPropertySchema(
                type=ToolPropertyType.STRING, description="Path of file relative to workspace."
            ),
            "edits": ToolPropertySchema(
                type=ToolPropertyType.ARRAY,
                description="Replacements, applied together or not at all.",
                items=_EDIT,
            ),
        },
        required=["path", "edits"],
    ),
    input_examples=[
        {"path": "notes/todo.md", "edits": [{"old_text": "", "new_text": "Creating new file\n"}]},
        {
            "path": "src/app.py",
            "edits": [
                {"old_text": "DEBUG = True", "new_text": "DEBUG = False"},
                {"old_text": "def run():\n    pass", "new_text": "def run():\n    serve()"},
            ],
        },
    ],
)
def edit_file(ws: Workspace, path: str, edits: list[dict[str, str]]) -> str:
    """Apply all `edits` to one file, or none of them.

    How:
      1. Read bytes, so Windows (CRLF) line endings survive; text mode would turn them into LF.
         Match on an LF copy, since the model writes `old_text` with plain newlines.
      2. Check every edit before changing anything: each must match exactly once and not
         overlap another. A miss names the edit and the closest lines; it never guesses.
      3. Apply from the end of the file backwards, so earlier positions stay valid, then put
         the original line endings back and write.
    """
    p = resolve(ws, path)
    if not edits or not all(
        isinstance(e, dict) and {"old_text", "new_text"} <= e.keys() for e in edits
    ):
        raise ToolError(
            "edit_file", "edits must be a non-empty list of {old_text, new_text} objects"
        )
    if any(e["old_text"] == "" for e in edits):
        if len(edits) != 1:
            raise ToolError(
                "edit_file", "an empty old_text creates a file and must be the only edit"
            )
        if p.exists():
            raise ToolError("edit_file", f"{path} already exists; give old_text to edit it")
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(edits[0]["new_text"].encode())
        return f"Created {path}"
    if not p.is_file():
        raise ToolError(
            "edit_file",
            f"{path} does not exist; to create it, pass one edit with an empty old_text",
        )

    raw = p.read_bytes().decode("utf-8")
    bom = "\ufeff" if raw.startswith("\ufeff") else ""  # a marker some editors add; keep it
    ending = _line_ending(raw)
    content = _to_lf(raw[len(bom) :])

    spans = []  # (start, end, new_text) of each edit in the LF copy
    for i, e in enumerate(edits, 1):
        old, new = _to_lf(e["old_text"]), _to_lf(e["new_text"])
        n = content.count(old)
        which = f"edit {i} of {len(edits)}"
        if n == 0:
            raise ToolError(
                "edit_file", f"{which}: old_text not found in {path}.{_closest(content, old)}"
            )
        if n > 1:
            raise ToolError(
                "edit_file", f"{which}: old_text matches {n} times in {path}; add surrounding lines"
            )
        start = content.index(old)
        spans.append((start, start + len(old), new))
    spans.sort()
    for (_, prev_end, _), (start, _, _) in zip(spans, spans[1:], strict=False):
        if start < prev_end:
            raise ToolError("edit_file", "two edits overlap; merge them into one")

    result = content
    for start, end, new in reversed(spans):
        result = result[:start] + new + result[end:]
    if result == content:
        raise ToolError("edit_file", "the edits change nothing")
    p.write_bytes((bom + result.replace("\n", ending)).encode("utf-8"))
    return f"Edited {path} ({len(edits)} edit{'s' if len(edits) > 1 else ''})"


def _line_ending(text: str) -> str:
    """'\r\n' if the file's first line ends that way, else '\n' (pi's detectLineEnding)."""
    i = text.find("\n")
    return "\r\n" if i > 0 and text[i - 1] == "\r" else "\n"


def _to_lf(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _closest(content: str, old: str) -> str:
    """The file lines most like old_text's first line, as a hint after a miss."""
    target = next((ln.strip() for ln in old.splitlines() if ln.strip()), "")
    lines = content.splitlines()
    stripped = [ln.strip() for ln in lines]
    matches = difflib.get_close_matches(target, stripped, n=3, cutoff=0.6)
    if not matches:
        return " No similar lines; read the file again before retrying."
    found = [f"  line {stripped.index(m) + 1}: {lines[stripped.index(m)]}" for m in matches]
    return " Closest lines:\n" + "\n".join(found)


@tool(
    name="list_files",
    read_only=True,
    description="List files tracked by git under a directory, relative to the workspace root. "
    "Use this to see what exists in the repository before reading or searching it. Equivalent "
    "to `git ls-files <path>`: build output, caches, and anything git-ignored are excluded "
    "automatically, but a file that hasn't been committed yet will not appear. Returns one "
    "path per line, capped at 500 entries — if you hit the cap, call again with a narrower "
    "`path` to see the rest.",
    input_schema=ToolInputSchema(
        properties={
            "path": ToolPropertySchema(
                type=ToolPropertyType.STRING,
                description="Directory to list, relative to the workspace root. "
                'Defaults to "." (the repository root).',
            ),
        },
        required=[],
    ),
    input_examples=[{"path": "."}, {"path": "src/click"}],
)
def list_files(ws: Workspace, path: str = ".") -> str:
    p = resolve(ws, path)
    if not p.is_dir():
        raise ToolError("list_files", f"{path}: not a directory")

    out = subprocess.run(["git", "ls-files", path], cwd=ws.root, capture_output=True, text=True)
    if out.returncode != 0:
        raise ToolError("list_files", f"git ls-files failed: {out.stderr.strip()}")

    files = out.stdout.splitlines()
    if not files:
        return f"No tracked files under {path!r}."
    if len(files) > MAX_FILES:
        shown = files[:MAX_FILES]
        return "\n".join(shown) + (
            f"\n\n[... {len(files) - MAX_FILES} more files omitted; narrow `path` to see them ...]"
        )
    return "\n".join(files)


@tool(
    name="read_file",
    read_only=True,
    description="Read a text file's contents with 1-indexed line numbers prefixed to each "
    "line, so you can cite exact locations and target `edit_file` calls precisely. Reads up "
    "to `limit` lines starting at `offset` (both 1-indexed); if the file is longer than that, "
    "the output ends with a hint giving the `offset` to pass to continue reading. Fails if "
    "`path` is not a file, is not valid UTF-8 text (e.g. a binary file), or if `offset` is "
    "past the end of the file.",
    input_schema=ToolInputSchema(
        properties={
            "path": ToolPropertySchema(
                type=ToolPropertyType.STRING, description="Path of file relative to workspace."
            ),
            "offset": ToolPropertySchema(
                type=ToolPropertyType.NUMBER,
                description="1-indexed line number to start reading from. Defaults to 1.",
            ),
            "limit": ToolPropertySchema(
                type=ToolPropertyType.NUMBER,
                description=f"Maximum number of lines to read. Defaults to {MAX_LINES}.",
            ),
        },
        required=["path"],
    ),
    input_examples=[
        {"path": "src/click/core.py"},
        {"path": "src/click/core.py", "offset": 200, "limit": 100},
    ],
)
def read_file(ws: Workspace, path: str, offset: int = 1, limit: int = MAX_LINES) -> str:
    p = resolve(ws, path)
    if not p.is_file():
        raise ToolError("read_file", f"{path}: not a file")
    if offset < 1:
        raise ToolError("read_file", "offset must be >= 1")

    try:
        lines = p.read_text().splitlines()
    except UnicodeDecodeError as err:
        raise ToolError("read_file", f"{path}: not a text file") from err

    total = len(lines)
    start = offset - 1
    if start >= total:
        return f"{path} has {total} lines; offset {offset} is past the end of the file."

    end = min(start + limit, total)
    numbered = "\n".join(f"{i + 1:6d}\t{lines[i]}" for i in range(start, end))
    if end < total:
        numbered += f"\n\n[... {total - end} more lines; call again with offset={end + 1} ...]"
    return numbered
