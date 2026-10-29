"""The Week 1 eval harness: per task, per repeat, a fresh snapshot, the seed if any,
a full agent run, grading inside the still-running sandbox, one line to results.jsonl.
"""

import argparse
import json
import logging
import re
import subprocess
import uuid
from pathlib import Path
from typing import Any

import yaml

from rig import Agent, Budget, Trace, Workspace
from rig.snapshot import create_snapshot

REPO_ROOT = Path(__file__).resolve().parent.parent
SOURCE_REPO = REPO_ROOT / "workspaces" / "click"
SEEDS_DIR = REPO_ROOT / "evals" / "seeds"
HIDDEN_DIR = REPO_ROOT / "evals" / "hidden"
RUNS_DIR = REPO_ROOT / "runs"


def load_tasks(path: Path) -> list[dict[str, Any]]:
    tasks = yaml.safe_load(path.read_text())
    assert isinstance(tasks, list)
    return tasks


def run_pytest(ws: Workspace, selectors: list[str]) -> tuple[bool, str]:
    result = subprocess.run(
        [*ws.exec_prefix, "python", "-m", "pytest", "-q", *selectors],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0, result.stdout + result.stderr


def git_diff(snap_dir: Path, scope: str | None = None) -> str:
    cmd = ["git", "diff", "HEAD"]
    if scope is not None:
        cmd += ["--", scope]
    return subprocess.run(cmd, cwd=snap_dir, capture_output=True, text=True).stdout


_COUNT_KEYS = ("passed", "skipped", "xfailed")


def parse_pytest_counts(output: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for key in _COUNT_KEYS:
        match = re.search(rf"(\d+) {key}", output)
        counts[key] = int(match.group(1)) if match else 0
    return counts


def grade_answer(
    task: dict[str, Any], final_response: str, snap_dir: Path, ws: Workspace
) -> dict[str, Any]:
    if git_diff(snap_dir).strip() != "":
        return {"passed": False, "reason": "diff is not empty"}

    answer = (final_response or "").lower()

    if task["grader"].get("pytest_count_match"):
        _, full_out = run_pytest(ws, [])
        expected = parse_pytest_counts(full_out)
        missing = [f"{v} {k}" for k, v in expected.items() if str(v) not in answer]
        if missing:
            return {"passed": False, "reason": f"answer missing counts: {missing}"}
        return {"passed": True, "reason": None}

    missing = [s for s in task["grader"].get("expect_in_answer", []) if s.lower() not in answer]

    any_of = task["grader"].get("expect_any_in_answer")
    if any_of is not None and not any(s.lower() in answer for s in any_of):
        missing.append(f"one of {any_of}")

    line_range = task["grader"].get("expect_line_in_answer")
    if line_range is not None:
        lo, hi = line_range["range"]
        prefix = line_range["prefix"].lower()
        if not any(f"{prefix}{n}" in answer for n in range(lo, hi + 1)):
            missing.append(f"a line number in {prefix}{lo}..{hi}")

    return {"passed": not missing, "reason": f"answer missing: {missing}" if missing else None}


def grade_pytest(task: dict[str, Any], snap_dir: Path, ws: Workspace) -> dict[str, Any]:
    if git_diff(snap_dir, scope="tests/").strip() != "":
        return {"passed": False, "reason": "tests/ was modified"}

    full_ok, full_out = run_pytest(ws, [])
    if not full_ok:
        return {"passed": False, "reason": f"full suite failed:\n{full_out[-2000:]}"}

    for hidden_name in task["grader"].get("hidden_tests", []):
        ws.copy_into(HIDDEN_DIR / hidden_name, f"/tmp/hidden/{hidden_name}")

    selectors = task["grader"]["selectors"]
    selector_ok, selector_out = run_pytest(ws, selectors)
    return {
        "passed": selector_ok,
        "reason": None if selector_ok else f"selectors failed:\n{selector_out[-2000:]}",
    }


def run_one(
    task: dict[str, Any], repeat: int, model: str, ref: str, results_path: Path, provider: str
) -> None:
    run_id = str(uuid.uuid4())
    run_dir = RUNS_DIR / run_id
    run_dir.mkdir(parents=True)
    snap_dir = run_dir / "snap"

    seed_name = task.get("seed")
    seed_patch = SEEDS_DIR / seed_name if seed_name else None
    create_snapshot(source_repo=SOURCE_REPO, ref=ref, dest=snap_dir, seed_patch=seed_patch)

    budget = Budget.get_dummy_budget()
    trace = Trace(run_id=run_id, filepath=str(run_dir / "trace.jsonl"))
    ws = Workspace(root=snap_dir, name=task["id"], run_id=run_id, use_sandbox=True)

    grade: dict[str, Any] = {"passed": False, "reason": "not graded"}
    status = "error"
    final_response = ""
    with ws:
        agent = Agent(ws, model=model, budget=budget, trace=trace, provider=provider)
        result = agent.run(task["prompt"])
        status = result.status
        final_response = result.final_response

        if result.status == "success":
            if task["grader"]["kind"] == "answer":
                grade = grade_answer(task, final_response, snap_dir, ws)
            else:
                grade = grade_pytest(task, snap_dir, ws)
        else:
            grade = {"passed": False, "reason": f"agent did not finish: {status}"}

        (run_dir / "messages.json").write_text(json.dumps(result.messages, default=str, indent=2))

    (run_dir / "diff.patch").write_text(git_diff(snap_dir))

    record = {
        "run_id": run_id,
        "task_id": task["id"],
        "repeat": repeat,
        "status": status,
        "passed": grade["passed"],
        "reason": grade.get("reason"),
        **budget.totals(),
    }
    (run_dir / "result.json").write_text(json.dumps(record, indent=2))
    with results_path.open("a") as f:
        f.write(json.dumps(record) + "\n")

    verdict = "PASS" if grade["passed"] else "FAIL"
    print(f"[{task['id']}] run {repeat + 1}: {verdict} ({status})")


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    logging.getLogger("rig").setLevel(logging.DEBUG)
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=1, help="Repeats per task")
    parser.add_argument("--tasks", type=Path, default=REPO_ROOT / "evals" / "tasks" / "week1.yaml")
    parser.add_argument("--results", type=Path, default=REPO_ROOT / "evals" / "results.jsonl")
    parser.add_argument("--model", default="claude-haiku-5-5")
    parser.add_argument("--provider", default="anthropic", help="Which model API to call")
    parser.add_argument("--ref", default="HEAD", help="git ref in workspaces/click to snapshot")
    parser.add_argument("--task-id", default=None, help="Run only this one task id")
    args = parser.parse_args()

    tasks = load_tasks(args.tasks)
    if args.task_id:
        tasks = [t for t in tasks if t["id"] == args.task_id]

    RUNS_DIR.mkdir(exist_ok=True)
    for task in tasks:
        for repeat in range(args.runs):
            run_one(task, repeat, args.model, args.ref, args.results, args.provider)


if __name__ == "__main__":
    main()
