"""The single-agent loop (Week 1): call the model, run the tools it asks for, repeat.

Messages are the Anthropic Messages API's own dicts, sent with the raw client in llm.py. Week 2
replaces both (rig's own message types, a provider layer, an event runtime) and keeps this
file's interface: `Agent(ws, model=..., budget=...).run(task)`, its statuses and trace events.
"""

import time
from functools import cache
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict

from ..sandbox.workspace import Workspace
from ..tools import get_tools_schemas, run_tool
from ..util.logging import get_logger
from . import llm
from .budget import Budget
from .exceptions import BudgetExceededError, LLMError
from .trace import NullTrace, Trace

logger = get_logger()
SYSTEM_PROMPT = Path(__file__).parent.parent / "prompts" / "system_prompt.md"
TRUNCATED_MSG = (
    "Not executed: your response hit max_tokens, so these arguments may be truncated. "
    "Re-issue the call with complete arguments."
)


@cache
def get_sys_prompt() -> str | None:
    if SYSTEM_PROMPT.exists():
        return SYSTEM_PROMPT.read_text()
    return None


class AgentRunResult(BaseModel):
    status: str
    messages: list[Any]  # the transcript, for the harness's messages.json
    final_response: str = ""
    exception: Exception | None = None

    model_config = ConfigDict(arbitrary_types_allowed=True)


class Agent:
    def __init__(
        self,
        ws: Workspace,
        *,
        model: str,
        budget: Budget,
        trace: Trace | None = None,
        max_tokens: int = 10000,
    ) -> None:
        self._ws = ws
        self._model = model
        self._budget = budget
        self._trace: Trace | NullTrace = trace or NullTrace()  # None: record nothing
        self._max_tokens = max_tokens
        self._step = 0
        self.messages: list[dict[str, Any]] = []  # the whole transcript, across runs

    def run(self, task: str | None = None) -> AgentRunResult:
        """Add `task` as a user message and run until the model stops; map how it ended.

        Statuses:
          - "success": the last turn ended normally, so there is a final answer.
          - "stopped.<stop_reason>": it ended without one: "stopped.max_tokens" (the answer
            was cut off), "stopped.refusal".
          - "error.budget.<limit>", "error.llm.<cause>" (an HTTP status such as "429", or
            "connection"), "error.internal": an exception ended the run.
        Tool failures never appear here: `run_tool` turns them into `is_error` results.
        """
        if task is not None:
            self.messages.append({"role": "user", "content": [{"type": "text", "text": task}]})
        self._trace.log_event(
            "run.start",
            step=self._step,
            task=task,
            model=self._model,
            tools=[t["name"] for t in get_tools_schemas()],
        )
        result = AgentRunResult(status="error.internal", messages=[])
        try:
            stop = self._loop()
            result.status = (
                "success" if stop in ("end_turn", "stop_sequence") else f"stopped.{stop}"
            )
            result.final_response = self._final_text()
        except Exception as err:
            logger.exception(err)
            result.exception = err
            result.final_response = str(err)
            match err:
                case BudgetExceededError():
                    self._trace.log_event(
                        "budget.exceeded", step=self._step, **self._budget.totals()
                    )
                    result.status = f"error.budget.{err.status}"
                case LLMError():
                    result.status = f"error.llm.{err.status}" if err.status else "error.llm"
                case _:
                    result.final_response = "Internal error."
            if not isinstance(err, BudgetExceededError):
                self._trace.log_event(
                    "error",
                    step=self._step,
                    status=result.status,
                    message=str(err),
                    payload=getattr(err, "payload", None),
                )
        finally:
            result.messages = list(self.messages)
            self._trace.log_event(
                "run.end",
                step=self._step,
                status=result.status,
                final=result.final_response,
                **self._budget.totals(),
            )
        return result

    def _loop(self) -> str:
        """One model call per turn until a turn asks for no tools; returns that turn's stop reason.

        Every tool_use must get a tool_result in the next request, or the API rejects it, so a
        turn's calls are all answered: run one at a time in order (Week 2 runs read-only ones in
        parallel), or, if the turn hit max_tokens and the arguments may be cut off, not run at all.
        """
        while True:
            self._budget.check()
            self._step += 1
            response = self._call_model()
            calls = [b for b in response["content"] if b["type"] == "tool_use"]
            if not calls:
                return str(response["stop_reason"])  # end_turn, a cut-off answer, refusal, ...
            if response["stop_reason"] == "max_tokens":
                results = [self._not_run(c, TRUNCATED_MSG) for c in calls]
            else:
                results = [self._run_tool(c) for c in calls]
            self.messages.append({"role": "user", "content": results})

    def _call_model(self) -> dict[str, Any]:
        request: dict[str, Any] = {
            "model": self._model,
            "max_tokens": self._max_tokens,
            "messages": self.messages,
            "tools": get_tools_schemas(),
        }
        if system := get_sys_prompt():
            request["system"] = system
        started = time.monotonic()
        response, _info = llm.call(request)
        self.messages.append({"role": "assistant", "content": response["content"]})
        usage = _usage(response["usage"])
        self._budget.charge(self._model, usage)
        self._trace.log_event(
            "llm.response",
            step=self._step,
            model=self._model,
            stop_reason=response["stop_reason"],
            usage=usage,
            duration_s=round(time.monotonic() - started, 4),
            content=[b for b in response["content"] if b["type"] != "thinking"],
        )
        return response

    def _run_tool(self, call: dict[str, Any]) -> dict[str, Any]:
        self._trace.log_event("tool.start", step=self._step, call_id=call["id"], tool=call["name"])
        started = time.monotonic()
        output, is_error = run_tool(self._ws, call["name"], **call["input"])  # never raises
        duration = round(time.monotonic() - started, 4)
        return self._result(call, output, is_error, duration)

    def _not_run(self, call: dict[str, Any], output: str) -> dict[str, Any]:
        return self._result(call, output, True, None)

    def _result(
        self, call: dict[str, Any], output: str, is_error: bool, duration: float | None
    ) -> dict[str, Any]:
        self._trace.log_event(
            "tool.result",
            step=self._step,
            call_id=call["id"],
            tool=call["name"],
            input=call["input"],
            output=output,
            is_error=is_error,
            duration_s=duration,  # None when the call never ran
        )
        return {
            "type": "tool_result",
            "tool_use_id": call["id"],
            "content": output,
            "is_error": is_error,
        }

    def _final_text(self) -> str:
        last = self.messages[-1] if self.messages else None
        if not last or last["role"] != "assistant":
            return ""
        return "".join(b["text"] for b in last["content"] if b["type"] == "text")


def _usage(raw: dict[str, Any]) -> dict[str, int]:
    """Anthropic's usage, under the names budget and pricing read (Week 2's `Usage` model)."""
    return {
        "input_tokens": raw.get("input_tokens", 0),
        "output_tokens": raw.get("output_tokens", 0),
        "cache_read_tokens": raw.get("cache_read_input_tokens") or 0,
        "cache_write_tokens": raw.get("cache_creation_input_tokens") or 0,
    }
