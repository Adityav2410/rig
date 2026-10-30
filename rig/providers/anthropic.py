# rig/providers/anthropic.py
"""Anthropic Messages API adapter: rig's Context in, rig's Events out."""

from collections.abc import Generator
from typing import Any

import anthropic

from ..core.exceptions import LLMError
from .types import (
    AssistantMessage,
    Context,
    Event,
    MessageDelta,
    StopReason,
    Text,
    Thinking,
    ToolCall,
    ToolResult,
    TurnEnd,
    Usage,
    UserMessage,
)

# Anthropic's names mostly match rig's; the extras fold into the nearest rig reason.
_STOP_REASONS: dict[str, StopReason] = {
    "end_turn": "end_turn",
    "stop_sequence": "end_turn",
    "pause_turn": "end_turn",  # only server tools pause; rig defines none
    "tool_use": "tool_use",
    "max_tokens": "max_tokens",
    "model_context_window_exceeded": "max_tokens",
    "refusal": "refusal",
}


class AnthropicProvider:
    name = "anthropic"

    def __init__(
        self,
        model: str,
        *,
        max_tokens: int = 10_000,
        client: anthropic.Anthropic | None = None,
        max_retries: int = 3,
        timeout: float = 300,
    ) -> None:
        self.model = model
        self.max_tokens = max_tokens
        # The SDK reads ANTHROPIC_API_KEY and retries 408/409/429/5xx with backoff itself.
        self._client = client or anthropic.Anthropic(max_retries=max_retries, timeout=timeout)

    # --- request: rig Context -> Messages API body ---

    def to_request(self, context: Context) -> dict[str, Any]:
        """The Messages API request body for `context`; public so tests can inspect it offline."""
        body: dict[str, Any] = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "messages": self._messages(context),
        }
        if context.system:
            body["system"] = context.system
        if context.tools:
            body["tools"] = [
                {"name": t.name, "description": t.description, "input_schema": t.parameters}
                for t in context.tools
            ]
        return body

    def _messages(self, context: Context) -> list[dict[str, Any]]:
        """Translate rig's messages into Anthropic's alternating user/assistant messages.

        How, one rig message at a time:
          - UserMessage -> a user message whose content is a plain string.
          - AssistantMessage -> an assistant message of content blocks (`_assistant_blocks`).
          - ToolResult -> a `tool_result` block. Anthropic wants all results of one turn in a
            single user message, while rig stores one ToolResult per call. So if the message
            just built (`out[-1]`) is a user message whose content is a list, that is a
            tool-result message from this same run of results: append the block to it.
            Otherwise start a new user message. A typed prompt's content is a string, never
            a list, so results are never merged into the user's own text.
        """
        out: list[dict[str, Any]] = []
        for msg in context.messages:
            match msg:
                case UserMessage():
                    out.append({"role": "user", "content": msg.text})
                case AssistantMessage():
                    out.append({"role": "assistant", "content": self._assistant_blocks(msg)})
                case ToolResult():
                    block = {
                        "type": "tool_result",
                        "tool_use_id": msg.call_id,
                        "content": msg.output,
                        "is_error": msg.is_error,
                    }
                    # Consecutive results share one user message, as the API expects.
                    prev = out[-1] if out else None
                    if prev and prev["role"] == "user" and isinstance(prev["content"], list):
                        prev["content"].append(block)
                    else:
                        out.append({"role": "user", "content": [block]})
        return out

    def _assistant_blocks(self, msg: AssistantMessage) -> list[dict[str, Any]]:
        # A thinking signature only verifies against the model that wrote it, so another
        # provider's or model's thinking is dropped; that lets a session switch providers.
        own = msg.provider == self.name and msg.model == self.model
        blocks: list[dict[str, Any]] = []
        for part in msg.content:
            match part:
                case Text() if part.text:  # the API rejects empty text blocks
                    blocks.append({"type": "text", "text": part.text})
                case ToolCall():
                    blocks.append(
                        {
                            "type": "tool_use",
                            "id": part.id,
                            "name": part.name,
                            "input": part.arguments,
                        }
                    )
                case Thinking() if own and part.signature:
                    blocks.append(
                        {"type": "thinking", "thinking": part.text, "signature": part.signature}
                    )
        return blocks

    # --- response: Anthropic stream -> rig Events ---

    def stream(self, context: Context) -> Generator[Event]:
        """Send one request and translate the response into rig Events.

        How: while the response streams, each text chunk is yielded as a MessageDelta so the
        CLI can print it live. Tool calls are not built from the stream: their arguments
        arrive as fragments of JSON. Instead, once the stream ends, `get_final_message()`
        returns the whole message with everything already parsed. From it, each tool_use
        block becomes a ToolCall (yielded, and kept), and one TurnEnd carries the normalized
        stop reason, usage and the complete AssistantMessage. SDK errors are re-raised as
        LLMError, so callers never see a vendor exception.
        """
        body = self.to_request(context)
        try:
            with self._client.messages.stream(**body) as stream:
                for text in stream.text_stream:
                    yield MessageDelta(text=text)
                final = stream.get_final_message()
        except anthropic.APIStatusError as e:
            raise LLMError(
                message=f"Anthropic API error {e.status_code}: {e.message}",
                status=str(e.status_code),
                payload={"request_id": e.request_id},
            ) from e
        except anthropic.APIConnectionError as e:
            raise LLMError(message=f"Could not reach Anthropic: {e}", status="connection") from e
        except anthropic.APIError as e:  # e.g. a response the SDK could not parse
            raise LLMError(message=f"Anthropic API error: {e}", status="invalid_response") from e

        content: list[Text | Thinking | ToolCall] = []
        for block in final.content:
            match block.type:
                case "text":
                    content.append(Text(text=block.text))
                case "thinking":
                    content.append(Thinking(text=block.thinking, signature=block.signature))
                case "tool_use":
                    call = ToolCall(id=block.id, name=block.name, arguments=dict(block.input))
                    content.append(call)
                    yield call
                # redacted_thinking and server-tool blocks have no rig type yet; dropped

        u = final.usage
        yield TurnEnd(
            stop_reason=_STOP_REASONS.get(final.stop_reason or "end_turn", "end_turn"),
            usage=Usage(
                input_tokens=u.input_tokens,  # already excludes cache reads and writes
                output_tokens=u.output_tokens,
                cache_read_tokens=u.cache_read_input_tokens or 0,
                cache_write_tokens=u.cache_creation_input_tokens or 0,
            ),
            message=AssistantMessage(content=content, provider=self.name, model=self.model),
        )
