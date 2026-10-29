# rig/providers/fake.py
"""A scripted Provider: replays canned turns, records every request, never touches the network."""

from collections.abc import Generator
from itertools import count
from typing import Any

from .types import (
    AssistantMessage,
    Context,
    Event,
    MessageDelta,
    StopReason,
    Text,
    ToolCall,
    TurnEnd,
    Usage,
)

_ids = count(1)


def text_turn(text: str, chunk: int = 8, stop_reason: StopReason = "end_turn") -> list[Event]:
    """A turn where the model just answers. Text arrives in small deltas, like a real stream."""
    deltas = [MessageDelta(text=text[i : i + chunk]) for i in range(0, len(text), chunk)]
    return [*deltas, _end(stop_reason, [Text(text=text)])]


def tool_turn(
    *calls: tuple[str, dict[str, Any]], text: str = "", stop_reason: StopReason = "tool_use"
) -> list[Event]:
    """A turn where the model asks for one or more tools, optionally after some text."""
    events: list[Event] = [MessageDelta(text=text)] if text else []
    content: list[Text | ToolCall] = [Text(text=text)] if text else []
    for name, arguments in calls:
        call = ToolCall(id=f"toolu_fake_{next(_ids)}", name=name, arguments=arguments)
        events.append(call)
        content.append(call)
    return [*events, _end(stop_reason, content)]


def _end(stop_reason: StopReason, content: list[Text | ToolCall]) -> TurnEnd:
    # The TurnEnd's message holds the same parts the turn streamed, as a real adapter's does.
    return TurnEnd(
        stop_reason=stop_reason,
        usage=Usage(input_tokens=100, output_tokens=20),
        message=AssistantMessage(content=list(content), provider="fake", model="fake"),
    )


class FakeProvider:
    """Each stream() call plays the next scripted turn.

    Running out of script is a test bug, so it raises.
    """

    name = "fake"
    model = "fake"

    def __init__(self, script: list[list[Event]]):
        self.script = list(script)
        self.contexts: list[Context] = []  # what the runtime actually sent, for assertions

    def stream(self, context: Context) -> Generator[Event]:
        self.contexts.append(context)
        if not self.script:
            raise AssertionError(
                f"FakeProvider ran out of turns after {len(self.contexts) - 1} requests."
            )
        yield from self.script.pop(0)


# # tests/test_runtime.py
# from rig.providers.types import ToolEnd
# from rig.providers.fake import FakeProvider, text_turn, tool_turn

# def test_parallel_reads_come_back_in_call_order():
#     provider = FakeProvider([
#         tool_turn(
#             ("read_file", {"path": "a.py"}),
#             ("read_file", {"path": "b.py"}),
#             ("search", {"pattern": "x"}),
#         ),
#         text_turn("done"),
#     ])
#     events = list(run(provider, messages=[UserMessage(text="go")], tools=TOOLS,
#                       budget=Budget(...)))
#     ends = [e for e in events if isinstance(e, ToolEnd)]
#     assert [e.call.name for e in ends] == ["read_file", "read_file", "search"]
#     assert len(provider.contexts) == 2               # one request per turn, nothing extra
