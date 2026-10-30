"""Ctrl-C at three points of a run, then a resume; and when steering and follow-ups land.

Everything is driven by FakeProvider and fake tools: no network, no Docker, no cost. Each
abort test checks the one property that matters: the transcript the next request sends still
has a result for every tool call, so the API would accept it.
"""

import time
from pathlib import Path
from typing import Any

from rig import Agent, Budget, Workspace
from rig.core.runtime import ABORTED_MSG, RuntimeTool
from rig.providers.fake import FakeProvider, text_turn, tool_turn
from rig.providers.types import AssistantMessage, Event, Message, ToolCall, ToolResult, ToolSpec


def _tool(name: str, log: list[str], *, read_only: bool = True, action: Any = None) -> RuntimeTool:
    """A fake tool that records that it ran, and can do something mid-run (like abort)."""

    def run(arguments: dict[str, Any]) -> tuple[str, bool]:
        log.append(name)
        if action:
            action()
        return f"{name} ok", False

    spec = ToolSpec(name=name, description=f"fake {name}", parameters={"type": "object"})
    return RuntimeTool(spec=spec, run=run, read_only=read_only)


def _agent(
    tmp_path: Path,
    provider: FakeProvider,
    tools: list[RuntimeTool],
    messages: list[Message] | None = None,
) -> Agent:
    ws = Workspace(root=tmp_path, name="test", run_id="test", use_sandbox=False)
    return Agent(
        ws,
        budget=Budget.get_dummy_budget(),
        provider=provider,
        tools=tools,
        messages=messages,
    )


def _unanswered(messages: list[Message]) -> list[str]:
    """Ids of tool calls with no ToolResult: what the API would reject."""
    calls = [
        p.id
        for m in messages
        if isinstance(m, AssistantMessage)
        for p in m.content
        if isinstance(p, ToolCall)
    ]
    answered = {m.call_id for m in messages if isinstance(m, ToolResult)}
    return [c for c in calls if c not in answered]


def _resume_is_valid(tmp_path: Path, agent: Agent) -> None:
    """Resume from the aborted transcript; its first request needs no patching to be valid."""
    provider = FakeProvider([text_turn("picked up where we left off")])
    resumed = _agent(tmp_path, provider, tools=[], messages=agent.messages)
    result = resumed.run()
    assert result.status == "success"
    sent = provider.contexts[0].messages
    assert _unanswered(sent) == []
    assert len(sent) == len(agent.messages)  # exactly the stored transcript: nothing patched in


def test_abort_mid_stream_answers_the_calls_already_streamed(tmp_path: Path) -> None:
    log: list[str] = []
    provider = FakeProvider(
        [tool_turn(("read", {}), ("read", {}), text="reading both"), text_turn("never sent")]
    )
    agent = _agent(tmp_path, provider, [_tool("read", log)])

    def on_event(event: Event) -> None:
        if isinstance(event, ToolCall):  # the first call has streamed; the second hasn't
            agent.abort()

    result = agent.run("go", on_event=on_event)

    assert result.status == "stopped.aborted"
    assert log == []  # no tool ran
    partial = agent.messages[1]
    assert isinstance(partial, AssistantMessage)
    assert [type(p).__name__ for p in partial.content] == [
        "Text",
        "ToolCall",
    ]  # text kept, one call
    assert _unanswered(agent.messages) == []
    assert isinstance(agent.messages[2], ToolResult) and agent.messages[2].output == ABORTED_MSG
    assert len(provider.contexts) == 1
    _resume_is_valid(tmp_path, agent)


def test_abort_mid_parallel_batch_answers_every_call_and_stops(tmp_path: Path) -> None:
    log: list[str] = []
    provider = FakeProvider([tool_turn(("a", {}), ("b", {}), ("c", {})), text_turn("never sent")])
    holder: dict[str, Agent] = {}
    tools = [
        _tool("a", log, action=lambda: time.sleep(0.1)),
        _tool("b", log, action=lambda: holder["agent"].abort()),  # Ctrl-C while the batch runs
        _tool("c", log, action=lambda: time.sleep(0.1)),
    ]
    agent = holder["agent"] = _agent(tmp_path, provider, tools)

    result = agent.run("go")

    assert result.status == "stopped.aborted"
    # Each call checks the abort when its thread starts, so which calls ran depends on timing;
    # the rule is that a call that ran keeps its real result and one that didn't says so.
    assert "b" in log
    results = {m.call_id: m.output for m in agent.messages if isinstance(m, ToolResult)}
    batch = agent.messages[1]
    assert isinstance(batch, AssistantMessage)
    calls = [p for p in batch.content if isinstance(p, ToolCall)]
    for c in calls:
        assert results[c.id] == (f"{c.name} ok" if c.name in log else ABORTED_MSG)
    assert _unanswered(agent.messages) == []
    assert len(provider.contexts) == 1  # no request after the abort
    _resume_is_valid(tmp_path, agent)


def test_abort_mid_edit_lets_the_edit_finish_and_skips_the_rest(tmp_path: Path) -> None:
    log: list[str] = []
    provider = FakeProvider([tool_turn(("edit", {}), ("read", {})), text_turn("never sent")])
    holder: dict[str, Agent] = {}
    edit = _tool("edit", log, read_only=False, action=lambda: holder["agent"].abort())
    agent = holder["agent"] = _agent(tmp_path, provider, [edit, _tool("read", log)])

    result = agent.run("go")

    assert result.status == "stopped.aborted"
    assert log == ["edit"]  # a mixed batch runs in order; the read never started
    edit_result, read_result = agent.messages[2], agent.messages[3]
    assert isinstance(edit_result, ToolResult) and edit_result.output == "edit ok"
    assert isinstance(read_result, ToolResult) and read_result.output == ABORTED_MSG
    _resume_is_valid(tmp_path, agent)


def test_steering_lands_after_the_running_batch(tmp_path: Path) -> None:
    log: list[str] = []
    provider = FakeProvider([tool_turn(("read", {})), text_turn("done, utils.py untouched")])
    agent = _agent(tmp_path, provider, [_tool("read", log)])

    def on_event(event: Event) -> None:
        if type(event).__name__ == "ToolStart":
            agent.steer("don't touch utils.py")

    result = agent.run("fix the bug", on_event=on_event)

    assert result.status == "success"
    second_request = provider.contexts[1].messages
    assert [type(m).__name__ for m in second_request[-2:]] == ["ToolResult", "UserMessage"]
    assert getattr(second_request[-1], "text", None) == "don't touch utils.py"


def test_follow_up_waits_until_the_agent_would_stop(tmp_path: Path) -> None:
    provider = FakeProvider([text_turn("fixed"), text_turn("test added")])
    agent = _agent(tmp_path, provider, [])
    agent.follow_up("also add a test")

    result = agent.run("fix the bug")

    assert result.status == "success"
    assert result.final_response == "test added"
    assert getattr(provider.contexts[1].messages[-1], "text", None) == "also add a test"
    assert len(provider.contexts) == 2


def test_an_abort_does_not_leak_into_the_next_run(tmp_path: Path) -> None:
    provider = FakeProvider([text_turn("ok")])
    agent = _agent(tmp_path, provider, [])
    agent.abort()  # e.g. a Ctrl-C that arrived after the previous run had already finished

    assert agent.run("go").status == "success"
