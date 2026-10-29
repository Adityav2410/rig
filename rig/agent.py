"""The stateful wrapper around runtime.run() (pi's agent.ts).

The runtime decides the order of things; the Agent owns everything that has state or side
effects: the transcript, the workspace the tools act on, the trace and the budget. Its entry
point, `Agent(...).run(task)`, is the one the eval harness calls. An Agent is a session: the
constructor takes what lasts (workspace, provider, budget, any earlier messages), and each
`run(task)` appends one prompt to the same transcript.
"""

import queue
import threading
import time
from collections.abc import Callable, Generator
from functools import cache, partial
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict

from . import runtime
from .budget import Budget
from .exceptions import BudgetExceededError, LLMError
from .logging import get_logger
from .providers import get_provider
from .providers.types import (
    AssistantMessage,
    Event,
    Message,
    Provider,
    StopReason,
    Text,
    Thinking,
    ToolCall,
    ToolEnd,
    ToolSpec,
    ToolStart,
    TurnEnd,
    TurnStart,
    UserMessage,
)
from .runtime import Hooks, RuntimeTool, ToolOutput
from .session import SessionLog
from .tools import get_tools, run_tool
from .trace import NullTrace, Trace
from .workspace import Workspace

logger = get_logger()
SYSTEM_PROMPT = Path(__file__).parent / "prompts" / "system_prompt.md"


@cache
def get_sys_prompt() -> str | None:
    if SYSTEM_PROMPT.exists():
        return SYSTEM_PROMPT.read_text()
    return None


class AgentRunResult(BaseModel):
    status: str
    messages: list[Any]  # rig messages as JSON-ready dicts, for the harness's messages.json
    final_response: str = ""
    exception: Exception | None = None

    model_config = ConfigDict(arbitrary_types_allowed=True)


def build_tools(ws: Workspace) -> list[RuntimeTool]:
    """Turn the tool registry into RuntimeTools bound to this workspace."""
    tools = []
    for t in get_tools():
        # partial binds t.name now; a lambda would capture the loop variable and call the last tool
        call = partial(_call_tool, ws, t.name)
        lock_key = partial(_edited_path, ws) if t.name == "edit_file" else None
        spec = ToolSpec(
            name=t.name, description=t.description, parameters=t.input_schema.model_dump()
        )
        tools.append(RuntimeTool(spec=spec, run=call, read_only=t.read_only, lock_key=lock_key))
    return tools


def _call_tool(ws: Workspace, name: str, arguments: dict[str, Any]) -> ToolOutput:
    return run_tool(ws, name, **arguments)


def _edited_path(ws: Workspace, arguments: dict[str, Any]) -> Path:
    return (ws.root / str(arguments.get("path", ""))).resolve()


def _resolve_provider(provider: str | Provider, model: str | None, max_tokens: int) -> Provider:
    if isinstance(provider, str):
        if model is None:
            raise ValueError(f"model is required when provider is a name ({provider!r})")
        return get_provider(provider, model, max_tokens=max_tokens)
    if model is not None and model != provider.model:
        raise ValueError(f"model={model!r} disagrees with the provider's {provider.model!r}")
    return provider


class Agent:
    def __init__(
        self,
        ws: Workspace,
        *,
        budget: Budget,
        trace: Trace | None = None,
        model: str | None = None,
        max_tokens: int = 10000,
        provider: str | Provider = "anthropic",
        messages: list[Message] | None = None,
        tools: list[RuntimeTool] | None = None,
        session: SessionLog | None = None,
    ) -> None:
        if session is not None and messages is not None:
            raise ValueError(
                "pass messages or a session, not both: a session brings its own history"
            )
        self._ws = ws
        self._trace: Trace | NullTrace = trace or NullTrace()  # None: record nothing
        self._budget = budget
        self._step = 0
        self._turn_started = 0.0  # monotonic time of the latest TurnStart, for llm.response
        self._last_stop: StopReason | None = None  # the latest TurnEnd's, decides the status
        self._provider = _resolve_provider(provider, model, max_tokens)
        self._tools = tools if tools is not None else build_tools(ws)
        # Earlier history: a resumed or forked session's branch, or messages passed in directly.
        self.messages: list[Message] = session.branch() if session else list(messages or [])
        self._session = session
        self._logged = len(self.messages)  # how many of self.messages the session already holds
        # call id -> start time / measured duration, written by the tool hooks for the trace
        self._tool_started: dict[str, float] = {}
        self._tool_duration: dict[str, float] = {}
        self._timer_lock = threading.Lock()
        # Set from another thread (the CLI's Ctrl-C handler); the runtime checks it at safe points.
        self._abort = threading.Event()
        # Typed while a run streams (the CLI's stdin thread); the runtime drains them between turns.
        self._steering: queue.Queue[UserMessage] = queue.Queue()
        self._follow_up: queue.Queue[UserMessage] = queue.Queue()

    # --- control from outside the run: safe to call from any thread ---

    def abort(self) -> None:
        """Ask the running loop to stop at its next safe point; it never interrupts a tool."""
        self._abort.set()

    @property
    def aborting(self) -> bool:
        return self._abort.is_set()

    def steer(self, text: str) -> None:
        """Queue a message for the current task; it lands after the running tool batch."""
        self._steering.put(UserMessage(text=text))

    def follow_up(self, text: str) -> None:
        """Queue the next task; it lands only when the agent would otherwise stop."""
        self._follow_up.put(UserMessage(text=text))

    def events(self, task: str | None = None) -> Generator[Event]:
        """Add `task` as a user message, run the loop, and yield every event after recording it.

        With no task the loop continues the transcript as it stands: a resumed session that
        was interrupted, or history that already ends in the new prompt.

        How: iterate `runtime.run(...)`, and for each event first update the Agent's own state
        (the trace), then yield it to whoever is listening — pi's `processEvents` order, so a
        listener never sees an event the trace doesn't have. `self.messages` is passed in and
        the runtime appends to it, so it is always the full transcript, even after an error.
        With a session, whatever the runtime appended is written to the log after each event,
        so a crash or a kill loses at most the message being built.
        """
        if task is not None:
            self.messages.append(UserMessage(text=task))
        self._persist()
        self._abort.clear()  # an abort belongs to the run it interrupted, not the next one
        hooks = Hooks(before_tool=self._start_timer, after_tool=self._stop_timer)
        try:
            for event in runtime.run(
                self._provider,
                get_sys_prompt(),
                self.messages,
                self._tools,
                self._budget,
                hooks,
                abort=self._abort,
                get_steering=partial(self._drain, self._steering, "steer"),
                get_follow_up=partial(self._drain, self._follow_up, "follow_up"),
            ):
                self._record(event)
                self._persist()
                yield event
        finally:
            self._persist()  # the runtime appends the last message after its final event

    def run(
        self, task: str | None = None, on_event: Callable[[Event], None] | None = None
    ) -> AgentRunResult:
        """Run to completion and map the outcome to a status.

        `on_event`, if given, sees every event as it happens — a script uses it to print
        MessageDeltas live. The eval harness passes nothing.

        Statuses, by how the run ended:
          - "success": the last turn ended normally (`end_turn`), so there is a final answer.
          - "stopped.<stop_reason>": the loop finished without one: "stopped.max_tokens"
            (the answer was cut off), "stopped.refusal", "stopped.aborted" (Ctrl-C).
          - "error.budget.<limit>", "error.llm.<cause>" (an HTTP status such as "429", or
            "connection"), "error.internal": an exception ended the run.
        Tool failures never appear here: `run_tool` turns them into `is_error` results.
        """
        self._last_stop = None
        self._trace.log_event(
            "run.start",
            step=self._step,
            task=task,
            provider=self._provider.name,
            model=self._provider.model,
            tools=[t.spec.name for t in self._tools],
        )
        result = AgentRunResult(status="error.internal", messages=[])
        try:
            for event in self.events(task):
                if on_event:
                    on_event(event)
            # An abort between tool batches ends the loop without an "aborted" TurnEnd.
            stop = "aborted" if self._abort.is_set() else self._last_stop or "end_turn"
            result.status = "success" if stop == "end_turn" else f"stopped.{stop}"
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
                    payload=getattr(err, "payload", None),  # e.g. the provider's request id
                )
        finally:
            result.messages = [m.model_dump(mode="json") for m in self.messages]
            self._trace.log_event(
                "run.end",
                step=self._step,
                status=result.status,
                final=result.final_response,
                **self._budget.totals(),
            )
        return result

    def _persist(self) -> None:
        if self._session is None:
            return
        for m in self.messages[self._logged :]:
            self._session.append_message(m)
        self._logged = len(self.messages)

    def _drain(self, q: queue.Queue[UserMessage], kind: str) -> list[UserMessage]:
        """Everything queued so far, without waiting; each message is traced as it lands."""
        out: list[UserMessage] = []
        while True:
            try:
                out.append(q.get_nowait())
            except queue.Empty:
                break
        for m in out:
            self._trace.log_event("user.message", step=self._step, source=kind, text=m.text)
        return out

    # --- trace ---

    def _record(self, event: Event) -> None:
        """Write one trace event per runtime Event, under Week 1's kind names (Week 5 reads them).

        MessageDeltas are skipped on purpose: TurnEnd carries the same text whole, and a line
        per chunk would bury everything else.
        """
        match event:
            case TurnStart():
                self._step += 1
                self._turn_started = time.monotonic()
            case TurnEnd():
                self._last_stop = event.stop_reason
                content = [
                    p.model_dump(mode="json")
                    for p in event.message.content
                    if not isinstance(p, Thinking)
                ]
                self._trace.log_event(
                    "llm.response",
                    step=self._step,
                    provider=event.message.provider,
                    model=event.message.model,
                    stop_reason=event.stop_reason,
                    usage=event.usage.model_dump(),
                    duration_s=round(time.monotonic() - self._turn_started, 4),
                    content=content,
                )
            case ToolStart():
                self._trace.log_event(
                    "tool.start", step=self._step, call_id=event.call.id, tool=event.call.name
                )
            case ToolEnd():
                duration = self._tool_duration.pop(event.call.id, None)
                self._trace.log_event(
                    "tool.result",
                    step=self._step,
                    call_id=event.call.id,
                    tool=event.call.name,
                    input=event.call.arguments,
                    output=event.output,
                    is_error=event.is_error,
                    duration_s=duration,  # None when the call never ran (denied, aborted)
                )

    # Tool timing rides on the hooks because they run on the tool's own thread, immediately
    # before and after the call. Timing at ToolEnd instead would be wrong for a parallel batch:
    # its ToolEnds are only yielded once every call has finished, so each would get the
    # batch's time. The lock guards the dicts, since parallel calls write them concurrently.

    def _start_timer(self, call: ToolCall) -> None:  # returning None means "allow"
        with self._timer_lock:
            self._tool_started[call.id] = time.monotonic()

    def _stop_timer(self, call: ToolCall, result: ToolOutput) -> ToolOutput:
        with self._timer_lock:
            started = self._tool_started.pop(call.id)
            self._tool_duration[call.id] = round(time.monotonic() - started, 4)
        return result  # unchanged: this hook only observes

    def _final_text(self) -> str:
        last = self.messages[-1]
        if not isinstance(last, AssistantMessage):
            return ""
        return "".join(p.text for p in last.content if isinstance(p, Text))
