"""The runtime, driven by FakeProvider: no network, no API key, no cost."""

import time
from typing import Any

from rig.core import runtime
from rig.core.budget import Budget
from rig.core.runtime import Deny, Hooks, RuntimeTool
from rig.providers.fake import FakeProvider, text_turn, tool_turn
from rig.providers.types import (
    AssistantMessage,
    Message,
    ToolCall,
    ToolEnd,
    ToolResult,
    ToolSpec,
    TurnEnd,
    UserMessage,
)


def _tool(
    name: str, *, read_only: bool = True, sleep: float = 0.0, log: list[str] | None = None
) -> RuntimeTool:
    """A fake tool that sleeps, records when it starts and ends, and echoes its arguments."""

    def run(arguments: dict[str, Any]) -> tuple[str, bool]:
        if log is not None:
            log.append(f"start {name}")
        time.sleep(sleep)
        if log is not None:
            log.append(f"end {name}")
        return f"{name} ran with {arguments}", False

    spec = ToolSpec(name=name, description=f"fake {name}", parameters={"type": "object"})
    return RuntimeTool(spec=spec, run=run, read_only=read_only)


def _run(
    provider: FakeProvider, tools: list[RuntimeTool], hooks: Hooks | None = None
) -> tuple[list[Any], list[Message]]:
    messages: list[Message] = [UserMessage(text="go")]
    events = list(runtime.run(provider, None, messages, tools, Budget.get_dummy_budget(), hooks))
    return events, messages


def test_text_only_turn_ends_the_loop() -> None:
    provider = FakeProvider([text_turn("all done")])
    events, messages = _run(provider, [])
    assert isinstance(events[-1], TurnEnd)
    assert len(provider.contexts) == 1
    assert isinstance(messages[-1], AssistantMessage)


def test_one_tool_call_round_trips() -> None:
    provider = FakeProvider([tool_turn(("read_file", {"path": "a.py"})), text_turn("done")])
    _, messages = _run(provider, [_tool("read_file")])
    assert [type(m).__name__ for m in messages] == [
        "UserMessage",
        "AssistantMessage",
        "ToolResult",
        "AssistantMessage",
    ]
    result = messages[2]
    assert isinstance(result, ToolResult)
    assert result.output == "read_file ran with {'path': 'a.py'}"
    # The second request carried the call and its result back to the model.
    assert provider.contexts[1].messages[-1] == result


def test_read_only_calls_run_in_parallel_and_finish_in_call_order() -> None:
    tools = [_tool("a", sleep=0.3), _tool("b", sleep=0.1), _tool("c", sleep=0.2)]
    provider = FakeProvider([tool_turn(("a", {}), ("b", {}), ("c", {})), text_turn("done")])
    started = time.monotonic()
    events, _ = _run(provider, tools)
    elapsed = time.monotonic() - started
    assert [e.call.name for e in events if isinstance(e, ToolEnd)] == ["a", "b", "c"]
    assert elapsed < 0.5  # sequential would take 0.6 s


def test_a_batch_with_a_mutating_call_runs_sequentially() -> None:
    log: list[str] = []
    tools = [_tool("read_file", log=log), _tool("edit_file", read_only=False, log=log)]
    calls: tuple[tuple[str, dict[str, Any]], ...] = (
        ("read_file", {}),
        ("edit_file", {}),
        ("read_file", {}),
    )
    provider = FakeProvider([tool_turn(*calls), text_turn("done")])
    _run(provider, tools)
    assert log == [
        "start read_file",
        "end read_file",
        "start edit_file",
        "end edit_file",
        "start read_file",
        "end read_file",
    ]


def test_max_tokens_turn_runs_no_tool() -> None:
    log: list[str] = []
    provider = FakeProvider(
        [tool_turn(("edit_file", {}), stop_reason="max_tokens"), text_turn("done")]
    )
    _, messages = _run(provider, [_tool("edit_file", read_only=False, log=log)])
    assert log == []
    result = messages[2]
    assert isinstance(result, ToolResult) and result.is_error
    assert "max_tokens" in result.output


def test_denied_and_unknown_calls_become_error_results() -> None:
    provider = FakeProvider([tool_turn(("read_file", {}), ("nope", {})), text_turn("done")])
    hooks = Hooks(before_tool=lambda call: Deny("reads are off"))
    _, messages = _run(provider, [_tool("read_file")], hooks)
    denied, unknown = messages[2], messages[3]
    assert isinstance(denied, ToolResult) and denied.output == "Blocked: reads are off"
    assert isinstance(unknown, ToolResult) and "not registered" in unknown.output


def test_orphaned_calls_get_a_result_in_the_request_only() -> None:
    calls = [ToolCall(id="1", name="a", arguments={}), ToolCall(id="2", name="a", arguments={})]
    messages: list[Message] = [
        UserMessage(text="go"),
        AssistantMessage(content=list(calls), provider="fake", model="fake"),
        ToolResult(call_id="1", output="ok"),
        UserMessage(text="next"),
    ]
    fixed = runtime._close_orphans(messages)
    assert [getattr(m, "call_id", None) for m in fixed] == [None, None, "1", "2", None]
    assert len(messages) == 4  # the stored transcript is untouched
