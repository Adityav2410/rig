"""SessionLog on its own, then with an Agent: logging as it goes, resume, fork, abort and kill."""

import json
from pathlib import Path
from typing import Any

import pytest

from rig import Agent, Budget, Workspace
from rig.core.runtime import RuntimeTool
from rig.core.session import SessionLog
from rig.providers.fake import FakeProvider, text_turn, tool_turn
from rig.providers.types import (
    AssistantMessage,
    Event,
    Message,
    ToolCall,
    ToolResult,
    ToolSpec,
    UserMessage,
)


def _user(text: str) -> UserMessage:
    return UserMessage(text=text)


def _texts(messages: list[Message]) -> list[str]:
    return [m.text for m in messages if isinstance(m, UserMessage)]


def test_fork_keeps_both_branches_and_rewrites_nothing(tmp_path: Path) -> None:
    log = SessionLog(tmp_path / "s.jsonl")
    ids = [log.append_message(_user(f"m{i}")) for i in range(1, 6)]

    log.checkout(ids[2])  # fork from the third entry
    log.append_message(_user("fork-a"))
    leaf = log.append_message(_user("fork-b"))

    assert _texts(log.branch(leaf)) == ["m1", "m2", "m3", "fork-a", "fork-b"]
    assert _texts(log.branch(ids[4])) == ["m1", "m2", "m3", "m4", "m5"]
    assert len((tmp_path / "s.jsonl").read_text().splitlines()) == 7


def test_reopening_resumes_from_the_last_entry(tmp_path: Path) -> None:
    path = tmp_path / "s.jsonl"
    first = SessionLog(path)
    first.append_message(_user("a"))
    last = first.append_message(_user("b"))

    again = SessionLog(path)
    assert again.head == last
    again.append_message(_user("c"))
    assert _texts(again.branch()) == ["a", "b", "c"]


def test_a_torn_last_line_is_skipped_but_damage_elsewhere_is_not(tmp_path: Path) -> None:
    path = tmp_path / "s.jsonl"
    log = SessionLog(path)
    log.append_message(_user("a"))
    with path.open("a") as f:
        f.write('{"id": "half-writ')  # what a kill in the middle of a write leaves behind
    assert _texts(SessionLog(path).branch()) == ["a"]

    path.write_text('{"broken\n' + path.read_text())
    with pytest.raises(json.JSONDecodeError):
        SessionLog(path)


def test_checkout_of_an_unknown_entry_fails(tmp_path: Path) -> None:
    log = SessionLog(tmp_path / "s.jsonl")
    log.append_message(_user("a"))
    with pytest.raises(KeyError):
        log.checkout("nope")


# --- with an Agent ---


def _read_tool() -> RuntimeTool:
    spec = ToolSpec(name="read", description="fake read", parameters={"type": "object"})
    return RuntimeTool(spec=spec, run=lambda arguments: ("contents", False), read_only=True)


def _agent(tmp_path: Path, provider: FakeProvider, **kwargs: Any) -> Agent:
    ws = Workspace(root=tmp_path, name="test", run_id="test", use_sandbox=False)
    budget = Budget.get_dummy_budget()
    return Agent(ws, budget=budget, provider=provider, tools=[_read_tool()], **kwargs)


def _unanswered(messages: list[Message]) -> list[str]:
    parts = [p for m in messages if isinstance(m, AssistantMessage) for p in m.content]
    calls = [p.id for p in parts if isinstance(p, ToolCall)]
    answered = {m.call_id for m in messages if isinstance(m, ToolResult)}
    return [c for c in calls if c not in answered]


def test_the_agent_logs_every_message_as_it_lands(tmp_path: Path) -> None:
    log = SessionLog(tmp_path / "s.jsonl")
    provider = FakeProvider([tool_turn(("read", {})), text_turn("done")])
    agent = _agent(tmp_path, provider, session=log)
    agent.run("go")

    assert log.branch() == agent.messages
    assert [m.role for m in log.branch()] == ["user", "assistant", "tool_result", "assistant"]


def test_a_new_agent_on_the_same_file_continues_the_conversation(tmp_path: Path) -> None:
    path = tmp_path / "s.jsonl"
    _agent(tmp_path, FakeProvider([text_turn("first answer")]), session=SessionLog(path)).run("one")

    provider = FakeProvider([text_turn("second answer")])
    result = _agent(tmp_path, provider, session=SessionLog(path)).run("two")

    assert result.final_response == "second answer"
    assert [m.role for m in provider.contexts[0].messages] == ["user", "assistant", "user"]
    assert len(SessionLog(path).branch()) == 4


def test_an_aborted_run_resumes_and_the_api_would_accept_it(tmp_path: Path) -> None:
    path = tmp_path / "s.jsonl"
    provider = FakeProvider([tool_turn(("read", {}), ("read", {}))])
    agent = _agent(tmp_path, provider, session=SessionLog(path))

    def on_event(event: Event) -> None:
        if isinstance(event, ToolCall):
            agent.abort()

    assert agent.run("go", on_event=on_event).status == "stopped.aborted"

    provider = FakeProvider([text_turn("carried on")])
    resumed = _agent(tmp_path, provider, session=SessionLog(path))
    assert resumed.run().status == "success"  # no new task: finish the interrupted one
    assert _unanswered(provider.contexts[0].messages) == []
    assert provider.contexts[0].messages == SessionLog(path).branch()[:-1]  # nothing patched in


def test_a_kill_mid_turn_resumes_with_the_orphan_answered_only_in_the_request(
    tmp_path: Path,
) -> None:
    path = tmp_path / "s.jsonl"
    log = SessionLog(path)
    log.append_message(_user("go"))
    call = ToolCall(id="toolu_1", name="read", arguments={})
    log.append_message(AssistantMessage(content=[call], provider="fake", model="fake"))
    # ...and then the process died before the tool's result was written.

    provider = FakeProvider([text_turn("carried on")])
    assert _agent(tmp_path, provider, session=SessionLog(path)).run().status == "success"
    assert _unanswered(provider.contexts[0].messages) == []  # the request got a synthetic result
    stored = SessionLog(path).branch()
    assert _unanswered(stored) == ["toolu_1"]  # the log itself was never rewritten


def test_messages_and_a_session_together_are_refused(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        _agent(tmp_path, FakeProvider([]), session=SessionLog(tmp_path / "s.jsonl"), messages=[])
