"""Agent end to end with FakeProvider and real tools in a temporary workspace (no Docker)."""

import json
from collections.abc import Generator
from pathlib import Path
from typing import Any

from rig import Agent, Budget, Trace, Workspace
from rig.core.exceptions import LLMError
from rig.providers.fake import FakeProvider, text_turn, tool_turn
from rig.providers.types import Context, Event


def test_three_reads_run_and_the_trace_shows_them_in_call_order(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    for name in ("a.py", "b.py", "c.py"):
        (repo / name).write_text(f"# {name}\n")
    reads = [("read_file", {"path": name}) for name in ("a.py", "b.py", "c.py")]
    provider = FakeProvider([tool_turn(*reads), text_turn("read all three")])
    trace_path = tmp_path / "trace.jsonl"

    ws = Workspace(root=repo, name="test", run_id="test", use_sandbox=False)
    agent = Agent(
        ws,
        budget=Budget.get_dummy_budget(),
        trace=Trace(run_id="test", filepath=str(trace_path)),
        provider=provider,
    )
    result = agent.run("read the files")

    assert result.status == "success"
    assert result.final_response == "read all three"
    lines = [json.loads(line) for line in trace_path.read_text().splitlines()]
    tool_results = [e["fields"] for e in lines if e["kind"] == "tool.result"]
    assert [r["input"]["path"] for r in tool_results] == ["a.py", "b.py", "c.py"]
    assert all(not r["is_error"] and r["duration_s"] is not None for r in tool_results)
    assert "# a.py" in tool_results[0]["output"]
    # messages.json for the harness: plain dicts, one per rig message.
    assert [m["role"] for m in result.messages] == [
        "user",
        "assistant",
        "tool_result",
        "tool_result",
        "tool_result",
        "assistant",
    ]


def test_a_second_run_continues_the_same_transcript(tmp_path: Path) -> None:
    provider = FakeProvider([text_turn("first answer"), text_turn("second answer")])
    ws = Workspace(root=tmp_path, name="test", run_id="test", use_sandbox=False)
    agent = Agent(
        ws,
        budget=Budget.get_dummy_budget(),
        trace=Trace(run_id="test", filepath=str(tmp_path / "trace.jsonl")),
        provider=provider,
    )
    agent.run("one")
    result = agent.run("two")

    assert result.final_response == "second answer"
    # The second request carried the whole first exchange.
    assert [m.role for m in provider.contexts[1].messages] == ["user", "assistant", "user"]


def _agent(tmp_path: Path, provider: Any) -> Agent:
    ws = Workspace(root=tmp_path, name="test", run_id="test", use_sandbox=False)
    trace = Trace(run_id="test", filepath=str(tmp_path / "trace.jsonl"))
    return Agent(ws, budget=Budget.get_dummy_budget(), trace=trace, provider=provider)


def _trace(tmp_path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in (tmp_path / "trace.jsonl").read_text().splitlines()]


def test_a_truncated_answer_is_not_a_success(tmp_path: Path) -> None:
    provider = FakeProvider([text_turn("the answer is", stop_reason="max_tokens")])
    result = _agent(tmp_path, provider).run("go")
    assert result.status == "stopped.max_tokens"
    assert [e["kind"] for e in _trace(tmp_path)] == ["run.start", "llm.response", "run.end"]


class _FailingProvider:
    name = "failing"
    model = "failing"

    def stream(self, context: Context) -> Generator[Event]:
        raise LLMError(message="rate limited", status="429", payload={"request_id": "req_1"})
        yield  # unreachable; makes this a generator, like a real adapter


def test_an_llm_error_keeps_its_cause_in_the_status_and_the_trace(tmp_path: Path) -> None:
    result = _agent(tmp_path, _FailingProvider()).run("go")
    assert result.status == "error.llm.429"
    lines = _trace(tmp_path)
    error = next(e["fields"] for e in lines if e["kind"] == "error")
    assert error["status"] == "error.llm.429" and error["payload"] == {"request_id": "req_1"}
    assert lines[-1]["kind"] == "run.end" and lines[-1]["fields"]["status"] == "error.llm.429"


def test_without_a_trace_the_agent_runs_and_writes_nothing(tmp_path: Path) -> None:
    ws = Workspace(root=tmp_path, name="test", run_id="test", use_sandbox=False)
    agent = Agent(ws, budget=Budget.get_dummy_budget(), provider=FakeProvider([text_turn("ok")]))

    assert agent.run("go").status == "success"
    assert list(tmp_path.iterdir()) == []
