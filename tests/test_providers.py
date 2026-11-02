"""The provider adapters, tested directly: no network, no API key."""

from collections.abc import Iterator
from types import SimpleNamespace
from typing import Any

import anthropic
from openai.types.chat import ChatCompletionChunk

from rig.providers.anthropic import AnthropicProvider
from rig.providers.openai_chat import OpenAIChatProvider
from rig.providers.types import (
    AssistantMessage,
    Context,
    Message,
    Text,
    Thinking,
    ToolCall,
    ToolResult,
    ToolSpec,
    TurnEnd,
    UserMessage,
)


def _provider() -> AnthropicProvider:
    # A dummy key: to_request never sends anything.
    return AnthropicProvider("claude-test", client=anthropic.Anthropic(api_key="unused"))


def _context(*messages: Message) -> Context:
    spec = ToolSpec(name="read_file", description="d", parameters={"type": "object"})
    return Context(system="be brief", messages=list(messages), tools=[spec])


def test_consecutive_tool_results_become_one_user_message() -> None:
    calls = [ToolCall(id=f"c{i}", name="read_file", arguments={}) for i in range(3)]
    body = _provider().to_request(
        _context(
            UserMessage(text="go"),
            AssistantMessage(content=list(calls), provider="anthropic", model="claude-test"),
            *(ToolResult(call_id=c.id, output="ok") for c in calls),
        )
    )
    assert [m["role"] for m in body["messages"]] == ["user", "assistant", "user"]
    results = body["messages"][2]["content"]
    assert [b["tool_use_id"] for b in results] == ["c0", "c1", "c2"]


def test_thinking_from_another_provider_is_dropped() -> None:
    message = AssistantMessage(
        content=[Thinking(text="hmm", signature="sig"), Text(text="answer")],
        provider="openai",
        model="gpt-x",
    )
    body = _provider().to_request(_context(UserMessage(text="go"), message))
    assert body["messages"][1]["content"] == [{"type": "text", "text": "answer"}]


def test_own_thinking_is_replayed_with_its_signature() -> None:
    message = AssistantMessage(
        content=[Thinking(text="hmm", signature="sig")], provider="anthropic", model="claude-test"
    )
    body = _provider().to_request(_context(UserMessage(text="go"), message))
    assert body["messages"][1]["content"] == [
        {"type": "thinking", "thinking": "hmm", "signature": "sig"}
    ]


def test_system_and_tools_use_anthropics_shape() -> None:
    body = _provider().to_request(_context(UserMessage(text="go")))
    assert body["system"] == "be brief"
    assert body["tools"] == [
        {"name": "read_file", "description": "d", "input_schema": {"type": "object"}}
    ]
    assert body["messages"] == [{"role": "user", "content": "go"}]


# --- OpenAIChatProvider: a stub client plays hand-built chunks; no network, no API key ---


class _StubStream:
    def __init__(self, chunks: list[ChatCompletionChunk]) -> None:
        self.chunks = chunks

    def __enter__(self) -> _StubStream:
        return self

    def __exit__(self, *exc: object) -> None:
        pass

    def __iter__(self) -> Iterator[ChatCompletionChunk]:
        return iter(self.chunks)


class _StubClient:
    """Just enough of openai.OpenAI: chat.completions.create returns the scripted stream."""

    def __init__(self, chunks: list[dict[str, Any]]) -> None:
        self.requests: list[dict[str, Any]] = []
        stream = _StubStream([ChatCompletionChunk.model_validate(_chunk(c)) for c in chunks])
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))
        self._stream = stream

    def _create(self, **body: Any) -> _StubStream:
        self.requests.append(body)
        return self._stream


def _chunk(fields: dict[str, Any]) -> dict[str, Any]:
    base = {"id": "c", "object": "chat.completion.chunk", "created": 0, "model": "m"}
    return {**base, "choices": [], **fields}


def _delta(delta: dict[str, Any], finish: str | None = None) -> dict[str, Any]:
    return {"choices": [{"index": 0, "delta": delta, "finish_reason": finish}]}


def _frag(index: int, args: str, id: str | None = None, name: str | None = None) -> dict[str, Any]:
    function: dict[str, Any] = {"arguments": args}
    if name:
        function["name"] = name
    return {"index": index, "id": id, "type": "function" if id else None, "function": function}


def _openai(chunks: list[dict[str, Any]]) -> tuple[OpenAIChatProvider, _StubClient]:
    client = _StubClient(chunks)
    return OpenAIChatProvider("gpt-test", client=client), client  # type: ignore[arg-type]


def test_tool_call_fragments_are_joined_per_index_and_come_out_in_order() -> None:
    provider, client = _openai(
        [
            _delta({"role": "assistant", "content": "Reading."}),
            _delta({"tool_calls": [_frag(0, '{"pa', id="call_a", name="read_file")]}),
            _delta({"tool_calls": [_frag(1, '{"path": ', id="call_b", name="list_files")]}),
            _delta({"tool_calls": [_frag(0, 'th": "a.py"}')]}),
            _delta({"tool_calls": [_frag(1, '"."}')]}, finish="tool_calls"),
            _chunk(
                {
                    "usage": {
                        "prompt_tokens": 1000,
                        "completion_tokens": 50,
                        "total_tokens": 1050,
                        "prompt_tokens_details": {"cached_tokens": 800},
                    }
                }
            ),
        ]
    )
    events = list(provider.stream(_context(UserMessage(text="go"))))

    calls = [e for e in events if isinstance(e, ToolCall)]
    assert [(c.id, c.name, c.arguments) for c in calls] == [
        ("call_a", "read_file", {"path": "a.py"}),
        ("call_b", "list_files", {"path": "."}),
    ]
    end = events[-1]
    assert isinstance(end, TurnEnd) and end.stop_reason == "tool_use"
    assert (end.usage.input_tokens, end.usage.cache_read_tokens) == (200, 800)  # minus cached
    assert end.message.content[0] == Text(text="Reading.")
    assert client.requests[0]["stream_options"] == {"include_usage": True}


def test_arguments_that_are_not_json_become_an_invalid_call() -> None:
    provider, _ = _openai(
        [
            _delta({"tool_calls": [_frag(0, '{"path": "a.py"', id="c1", name="read_file")]}),
            _delta({}, finish="tool_calls"),
        ]
    )
    (call,) = [e for e in provider.stream(_context()) if isinstance(e, ToolCall)]
    assert call.arguments == {} and call.invalid_arguments == '{"path": "a.py"'


def test_three_tool_results_become_three_tool_messages() -> None:
    provider, _ = _openai([])
    calls = [ToolCall(id=f"c{i}", name="read_file", arguments={"path": "a"}) for i in range(3)]
    body = provider.to_request(
        _context(
            UserMessage(text="go"),
            AssistantMessage(
                content=[Thinking(text="hmm", signature="s"), *calls],
                provider="anthropic",
                model="claude-test",
            ),
            *(ToolResult(call_id=c.id, output=f"out{c.id}") for c in calls),
        )
    )
    roles = [m["role"] for m in body["messages"]]
    assert roles == ["system", "user", "assistant", "tool", "tool", "tool"]
    assistant = body["messages"][2]
    assert assistant["content"] is None  # Thinking dropped, and there was no text
    assert assistant["tool_calls"][0]["function"] == {
        "name": "read_file",
        "arguments": '{"path": "a"}',
    }
    assert [m["tool_call_id"] for m in body["messages"][3:]] == ["c0", "c1", "c2"]
    assert body["tools"][0] == {
        "type": "function",
        "function": {"name": "read_file", "description": "d", "parameters": {"type": "object"}},
    }
    assert body["max_completion_tokens"] == provider.max_tokens
