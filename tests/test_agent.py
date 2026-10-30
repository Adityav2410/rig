"""The Week 1 loop with the model replaced by scripted responses: no network, no cost."""

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from rig import Agent, Budget, Trace, Workspace
from rig.core import llm
from rig.core.agent import TRUNCATED_MSG
from rig.core.exceptions import LLMError

USAGE = {"input_tokens": 100, "output_tokens": 20}


def _text(text: str, stop: str = "end_turn") -> dict[str, Any]:
    return {"content": [{"type": "text", "text": text}], "stop_reason": stop, "usage": USAGE}


def _tools(*calls: tuple[str, dict[str, Any]], stop: str = "tool_use") -> dict[str, Any]:
    blocks = [
        {"type": "tool_use", "id": f"toolu_{i}", "name": name, "input": args}
        for i, (name, args) in enumerate(calls)
    ]
    return {"content": blocks, "stop_reason": stop, "usage": USAGE}


@pytest.fixture
def script(monkeypatch: pytest.MonkeyPatch) -> Iterator[list[Any]]:
    """Responses llm.call returns in order; an exception in the list is raised instead."""
    responses: list[Any] = []
    sent: list[dict[str, Any]] = []

    def fake_call(request: dict[str, Any], **_: Any) -> tuple[dict[str, Any], Any]:
        sent.append(json.loads(json.dumps(request)))  # a copy: the agent keeps appending
        item = responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item, None

    monkeypatch.setattr(llm, "call", fake_call)
    responses.append(sent)  # the test reads requests from the last element
    yield responses


def _sent(script: list[Any]) -> list[dict[str, Any]]:
    return script[-1]  # type: ignore[no-any-return]


def _agent(tmp_path: Path, trace: bool = True, budget: Budget | None = None) -> Agent:
    (tmp_path / "a.py").write_text("x = 1\n")
    ws = Workspace(root=tmp_path, name="t", run_id="t", use_sandbox=False)
    tr = Trace(run_id="t", filepath=str(tmp_path / "trace.jsonl")) if trace else None
    return Agent(ws, model="claude-haiku-5-5", budget=budget or Budget.get_dummy_budget(), trace=tr)


def _kinds(tmp_path: Path) -> list[str]:
    return [json.loads(ln)["kind"] for ln in (tmp_path / "trace.jsonl").read_text().splitlines()]


def _queue(script: list[Any], *items: Any) -> None:
    script[-1:-1] = list(items)  # before the requests list


def test_a_text_answer_is_a_success_with_the_plan_trace_names(
    tmp_path: Path, script: list[Any]
) -> None:
    _queue(script, _text("the answer"))
    result = _agent(tmp_path).run("go")
    assert (result.status, result.final_response) == ("success", "the answer")
    assert _kinds(tmp_path) == ["run.start", "llm.response", "run.end"]


def test_tools_run_in_order_and_an_unknown_tool_still_gets_a_result(
    tmp_path: Path, script: list[Any]
) -> None:
    _queue(
        script,
        _tools(
            ("read_file", {"path": "a.py"}), ("no_such_tool", {}), ("list_files", {"path": "."})
        ),
        _text("done"),
    )
    assert _agent(tmp_path).run("go").status == "success"
    results = _sent(script)[1]["messages"][-1]["content"]
    assert [r["tool_use_id"] for r in results] == ["toolu_0", "toolu_1", "toolu_2"]
    assert "x = 1" in results[0]["content"] and not results[0]["is_error"]
    assert results[1]["is_error"] and "not registered" in results[1]["content"]


def test_a_max_tokens_turn_answers_its_calls_without_running_them(
    tmp_path: Path, script: list[Any]
) -> None:
    _queue(script, _tools(("read_file", {"path": "a.py"}), stop="max_tokens"), _text("ok"))
    _agent(tmp_path).run("go")
    (result,) = _sent(script)[1]["messages"][-1]["content"]
    assert result["is_error"] and result["content"] == TRUNCATED_MSG


@pytest.mark.parametrize(
    ("response", "status"),
    [
        (_text("cut off mid", stop="max_tokens"), "stopped.max_tokens"),
        (_text("I can't help with that.", stop="refusal"), "stopped.refusal"),
    ],
)
def test_ending_without_an_answer_is_not_a_success(
    tmp_path: Path, script: list[Any], response: dict[str, Any], status: str
) -> None:
    _queue(script, response)
    assert _agent(tmp_path).run("go").status == status


def test_an_llm_error_keeps_its_cause(tmp_path: Path, script: list[Any]) -> None:
    _queue(script, LLMError(message="rate limited", status="429"))
    result = _agent(tmp_path).run("go")
    assert result.status == "error.llm.429"
    assert _kinds(tmp_path) == ["run.start", "error", "run.end"]


def test_a_budget_stop_is_reported(tmp_path: Path, script: list[Any]) -> None:
    budget = Budget(
        max_steps=1, max_input_tokens=10**6, max_output_tokens=10**5, max_usd=1, max_wall_clock_s=60
    )
    _queue(script, _tools(("read_file", {"path": "a.py"})))
    result = _agent(tmp_path, budget=budget).run("go")
    assert result.status == "error.budget.steps.exceeded"
    assert "budget.exceeded" in _kinds(tmp_path)


def test_a_second_run_continues_the_transcript(tmp_path: Path, script: list[Any]) -> None:
    _queue(script, _text("one"), _text("two"))
    agent = _agent(tmp_path)
    agent.run("first")
    assert agent.run("second").final_response == "two"
    assert [m["role"] for m in _sent(script)[1]["messages"]] == ["user", "assistant", "user"]


def test_without_a_trace_nothing_is_written(tmp_path: Path, script: list[Any]) -> None:
    _queue(script, _text("ok"))
    assert _agent(tmp_path, trace=False).run("go").status == "success"
    assert not (tmp_path / "trace.jsonl").exists()


def test_cache_tokens_are_priced(tmp_path: Path, script: list[Any]) -> None:
    response = _text("ok")
    response["usage"] = {
        "input_tokens": 0,
        "output_tokens": 0,
        "cache_read_input_tokens": 50_000,
    }
    _queue(script, response)
    agent = _agent(tmp_path)
    agent.run("go")
    assert agent._budget.usd == pytest.approx(
        50_000 * 0.01 / 1e6
    )  # Haiku 5.5 cache hit, under 100k
