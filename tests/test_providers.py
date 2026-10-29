"""AnthropicProvider.to_request, tested directly: no network, no API key."""

import anthropic

from rig.providers.anthropic import AnthropicProvider
from rig.providers.types import (
    AssistantMessage,
    Context,
    Message,
    Text,
    Thinking,
    ToolCall,
    ToolResult,
    ToolSpec,
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
