"""OpenAI Chat Completions adapter: rig's Context in, rig's Events out.

One class serves OpenAI, OpenRouter and any OpenAI-compatible server (vLLM, Ollama): they all
accept the same request and stream the same chunks, and differ only in base_url, the API key's
environment variable and a few field names. pi's same adapter is openai-completions.ts.
"""

import json
import os
from collections.abc import Generator
from typing import Any

import openai

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

OPENROUTER_URL = "https://openrouter.ai/api/v1"

_STOP_REASONS: dict[str, StopReason] = {
    "stop": "end_turn",
    "tool_calls": "tool_use",
    "function_call": "tool_use",  # the deprecated single-function form
    "length": "max_tokens",
    "content_filter": "refusal",
}


class OpenAIChatProvider:
    def __init__(
        self,
        model: str,
        *,
        max_tokens: int = 10_000,
        base_url: str | None = None,
        api_key_env: str = "OPENAI_API_KEY",
        name: str = "openai",
        # OpenAI wants max_completion_tokens (its reasoning models reject max_tokens); most
        # compatible servers know only max_tokens. pi has the same switch: compat.maxTokensField.
        max_tokens_field: str = "max_completion_tokens",
        client: openai.OpenAI | None = None,
        max_retries: int = 3,
        timeout: float = 300,
    ) -> None:
        self.name = name
        self.model = model
        self.max_tokens = max_tokens
        self._max_tokens_field = max_tokens_field
        if client is None:
            key = os.environ.get(api_key_env)
            if not key:
                raise ValueError(f"{api_key_env} is not set (any value works for a local server)")
            # Like Anthropic's SDK, this one retries 408/409/429/5xx with backoff itself.
            extra: dict[str, Any] = {"base_url": base_url} if base_url else {}  # else SDK default
            client = openai.OpenAI(api_key=key, max_retries=max_retries, timeout=timeout, **extra)
        self._client = client

    # --- request: rig Context -> Chat Completions body ---

    def to_request(self, context: Context) -> dict[str, Any]:
        """The Chat Completions request body for `context`; public so tests can inspect it."""
        messages: list[dict[str, Any]] = []
        if context.system:
            messages.append({"role": "system", "content": context.system})
        for msg in context.messages:
            match msg:
                case UserMessage():
                    messages.append({"role": "user", "content": msg.text})
                case AssistantMessage():
                    messages.append(_assistant(msg))
                case ToolResult():
                    # One message per result, unlike Anthropic. There is no error flag, so
                    # is_error is lost; rig's error outputs already say what went wrong.
                    messages.append(
                        {"role": "tool", "tool_call_id": msg.call_id, "content": msg.output}
                    )
        body: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            self._max_tokens_field: self.max_tokens,
        }
        if context.tools:
            body["tools"] = [
                {
                    "type": "function",
                    "function": {
                        "name": t.name,
                        "description": t.description,
                        "parameters": t.parameters,
                    },
                }
                for t in context.tools
            ]
        return body

    # --- response: Chat Completions stream -> rig Events ---

    def stream(self, context: Context) -> Generator[Event]:
        """Send one request and translate the streamed chunks into rig Events.

        How: text arrives as `delta.content` and is yielded at once as MessageDeltas. Tool
        calls arrive in fragments keyed by `index`: the first fragment of an index carries the
        call's id and name, later ones only more characters of its JSON arguments. So each
        index gets a slot that collects the pieces, and the arguments are parsed only when the
        stream ends, when the string is complete. The last chunk has no choices and carries the
        usage, because `include_usage` asks for it.
        """
        body = self.to_request(context)
        text: list[str] = []
        slots: dict[int, dict[str, Any]] = {}  # index -> {"id", "name", "args": [fragments]}
        finish: str | None = None
        usage: Any = None
        try:
            with self._client.chat.completions.create(
                **body, stream=True, stream_options={"include_usage": True}
            ) as chunks:
                for chunk in chunks:
                    if chunk.usage:
                        usage = chunk.usage
                    for choice in chunk.choices:  # one choice: rig never asks for n > 1
                        delta = choice.delta
                        if delta.content:
                            text.append(delta.content)
                            yield MessageDelta(text=delta.content)
                        for frag in delta.tool_calls or []:
                            slot = slots.setdefault(frag.index, {"id": "", "name": "", "args": []})
                            if frag.id:
                                slot["id"] = frag.id
                            if frag.function and frag.function.name:
                                slot["name"] = frag.function.name
                            if frag.function and frag.function.arguments:
                                slot["args"].append(frag.function.arguments)
                        if choice.finish_reason:
                            finish = choice.finish_reason
        except openai.APIStatusError as e:
            raise LLMError(
                message=f"{self.name} API error {e.status_code}: {e.message}",
                status=str(e.status_code),
                payload={"request_id": e.request_id},
            ) from e
        except openai.APIConnectionError as e:
            raise LLMError(message=f"Could not reach {self.name}: {e}", status="connection") from e
        except openai.APIError as e:
            raise LLMError(message=f"{self.name} API error: {e}", status="invalid_response") from e

        if finish is None:
            raise LLMError(
                message=f"{self.name} stream ended without a finish_reason", status="incomplete"
            )

        content: list[Text | Thinking | ToolCall] = [Text(text="".join(text))] if text else []
        for index in sorted(slots):
            call = _tool_call(index, slots[index])
            content.append(call)
            yield call

        stop = _STOP_REASONS.get(finish, "end_turn")
        if stop == "end_turn" and slots:
            stop = "tool_use"  # some compatible servers say "stop" even when they called tools
        yield TurnEnd(
            stop_reason=stop,
            usage=_usage(usage),
            message=AssistantMessage(content=content, provider=self.name, model=self.model),
        )


def _assistant(msg: AssistantMessage) -> dict[str, Any]:
    # Thinking is dropped: Chat Completions has no field to send it back in, and another
    # vendor's reasoning would mean nothing to this model anyway.
    text = "".join(p.text for p in msg.content if isinstance(p, Text))
    calls = [p for p in msg.content if isinstance(p, ToolCall)]
    out: dict[str, Any] = {"role": "assistant", "content": text or None}
    if calls:
        out["tool_calls"] = [
            {
                "id": c.id,
                "type": "function",
                "function": {"name": c.name, "arguments": json.dumps(c.arguments)},
            }
            for c in calls
        ]
    elif not text:
        out["content"] = ""  # neither text nor calls: content can't be null then
    return out


def _tool_call(index: int, slot: dict[str, Any]) -> ToolCall:
    raw = "".join(slot["args"])
    call_id = slot["id"] or f"call_{index}"  # some local servers send no id
    try:
        arguments = json.loads(raw) if raw.strip() else {}  # no arguments at all is {}
    except json.JSONDecodeError:
        arguments = None
    if not isinstance(arguments, dict):
        return ToolCall(id=call_id, name=slot["name"], arguments={}, invalid_arguments=raw)
    return ToolCall(id=call_id, name=slot["name"], arguments=arguments)


def _usage(u: Any) -> Usage:
    if u is None:  # a server that ignores include_usage
        return Usage()
    details = u.prompt_tokens_details
    cached = (details.cached_tokens if details else 0) or 0
    # prompt_tokens includes cache hits; rig's input_tokens excludes them, as Anthropic's does.
    return Usage(
        input_tokens=u.prompt_tokens - cached,
        output_tokens=u.completion_tokens,
        cache_read_tokens=cached,
    )
