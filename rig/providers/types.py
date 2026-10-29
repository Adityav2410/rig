from collections.abc import Generator
from typing import Annotated, Any, Literal, Protocol

from pydantic import BaseModel, Field


class Text(BaseModel):
    type: Literal["text"] = "text"
    text: str


class Thinking(BaseModel):
    type: Literal["thinking"] = "thinking"
    text: str
    signature: str | None = None  # opaque replay data: only the model that wrote it can read it


class ToolCall(BaseModel):  # provider: the model asked for a tool
    type: Literal["tool_call"] = "tool_call"
    id: str
    name: str
    arguments: dict[str, Any]


class UserMessage(BaseModel):
    role: Literal["user"] = "user"
    text: str


class AssistantMessage(BaseModel):
    role: Literal["assistant"] = "assistant"
    content: list[Text | Thinking | ToolCall]
    provider: str  # who wrote it; decides whether its Thinking can be replayed
    model: str


class ToolResult(BaseModel):
    role: Literal["tool_result"] = "tool_result"
    call_id: str
    output: str
    is_error: bool = False


Message = Annotated[UserMessage | AssistantMessage | ToolResult, Field(discriminator="role")]


class ToolSpec(BaseModel):  # each adapter wraps this in its own tool format
    name: str
    description: str
    parameters: dict[str, Any]  # JSON Schema


class Context(BaseModel):  # everything one request needs, in rig's terms
    system: str | None
    messages: list[Message]
    tools: list[ToolSpec]


class Usage(BaseModel):  # input_tokens excludes cache reads, on every provider
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0


StopReason = Literal["end_turn", "tool_use", "max_tokens", "refusal", "aborted"]


class TurnStart(BaseModel):
    type: Literal["turn_start"] = "turn_start"


class MessageDelta(BaseModel):  # provider: a chunk of streamed text
    type: Literal["message_delta"] = "message_delta"
    text: str


class TurnEnd(BaseModel):  # provider: response finished; carries the full assistant content
    type: Literal["turn_end"] = "turn_end"
    stop_reason: StopReason
    usage: Usage
    message: AssistantMessage


class ToolStart(BaseModel):  # runtime: about to execute
    type: Literal["tool_start"] = "tool_start"
    call: ToolCall


class ToolEnd(BaseModel):  # runtime: finished, yielded in call order
    type: Literal["tool_end"] = "tool_end"
    call: ToolCall
    output: str
    is_error: bool


Event = Annotated[
    TurnStart | MessageDelta | ToolCall | TurnEnd | ToolStart | ToolEnd,
    Field(discriminator="type"),
]


class Provider(Protocol):
    name: str  # "anthropic", "openai", "openrouter", "fake"
    model: str

    def stream(self, context: Context) -> Generator[Event]: ...
