# rig/runtime.py
"""The agent loop as a generator of events (pi's agent-loop.ts).

Stateless and vendor-free: it speaks only providers/types.py, imports no SDK and touches no
files. The caller owns `messages` (appended to in place), the tools' side effects and the
queues; the runtime only decides what happens in which order.
"""

import threading
from collections.abc import Callable, Generator, Hashable
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing, nullcontext
from dataclasses import dataclass, field
from typing import Any

from .budget import Budget
from .exceptions import LLMError
from .providers.types import (
    AssistantMessage,
    Context,
    Event,
    Message,
    MessageDelta,
    Provider,
    Text,
    ToolCall,
    ToolEnd,
    ToolResult,
    ToolSpec,
    ToolStart,
    TurnEnd,
    TurnStart,
    Usage,
    UserMessage,
)

TRUNCATED_MSG = (
    "Not executed: your response hit max_tokens, so these arguments may be truncated. "
    "Re-issue the call with complete arguments."
)
ABORTED_MSG = "Aborted by user"
ORPHAN_MSG = "No result was recorded for this call (the run was interrupted)."

ToolOutput = tuple[str, bool]  # (output, is_error)
ToolCallResult = tuple[ToolCall, str, bool]


@dataclass(frozen=True)
class RuntimeTool:
    """A tool the runtime can call. The caller binds the workspace into `run`."""

    spec: ToolSpec
    run: Callable[[dict[str, Any]], ToolOutput]
    read_only: bool = False
    # For tools that write a file: maps the arguments to a lock key (the resolved path).
    lock_key: Callable[[dict[str, Any]], Hashable] | None = None


@dataclass(frozen=True)
class Deny:
    reason: str


def _allow(call: ToolCall) -> Deny | None:
    return None


def _identity_result(call: ToolCall, result: ToolOutput) -> ToolOutput:
    return result


def _identity_messages(messages: list[Message]) -> list[Message]:
    return messages


@dataclass(frozen=True)
class Hooks:
    """The caller's say in the loop; the defaults allow every call and change nothing."""

    before_tool: Callable[[ToolCall], Deny | None] = _allow  # None means allow
    after_tool: Callable[[ToolCall, ToolOutput], ToolOutput] = _identity_result
    prepare_request: Callable[[list[Message]], list[Message]] = _identity_messages


def _no_messages() -> list[UserMessage]:
    return []


@dataclass
class _PathLocks:
    """One lock per file, created on first use, so edits to the same file never overlap.

    `_guard` makes lookup-or-create atomic; without it two threads could both miss and each
    store a different lock for the same file.
    """

    _locks: dict[Hashable, threading.Lock] = field(default_factory=dict)
    _guard: threading.Lock = field(default_factory=threading.Lock)

    def get(self, key: Hashable) -> threading.Lock:
        with self._guard:
            return self._locks.setdefault(key, threading.Lock())


_PATH_LOCKS = _PathLocks()  # process-wide: two runs editing one file still take turns


def run(
    provider: Provider,
    system: str | None,
    messages: list[Message],
    tools: list[RuntimeTool],
    budget: Budget,
    hooks: Hooks | None = None,
    *,
    abort: threading.Event | None = None,
    get_steering: Callable[[], list[UserMessage]] = _no_messages,
    get_follow_up: Callable[[], list[UserMessage]] = _no_messages,
) -> Generator[Event]:
    """Run turns until the model stops asking for tools and nothing new is queued.

    `messages` is the caller's transcript; the runtime appends to it in place.

    `abort` is set by the caller (the first Ctrl-C); the runtime stops at the next safe point
    and answers every pending call, so the transcript stays valid for the next request.

    `get_steering` and `get_follow_up` let the user type while the agent runs. Each returns
    the messages queued since it was last called (usually [] — it is polled, not awaited):
      - steering ("don't touch utils.py") changes course mid-task: it is delivered after each
        tool batch, the first point where the transcript is complete and a user message fits;
      - follow-up ("also add a test") is the next task: it is held until the agent would
        otherwise stop, then the loop continues with all the context built so far.
    They are callables rather than queues so the runtime stays ignorant of where input comes
    from: the CLI's stdin thread, a later interactive shell, or a test's script.
    """
    hooks = hooks or Hooks()
    abort = abort or threading.Event()
    by_name = {t.spec.name: t for t in tools}
    specs = [t.spec for t in tools]

    while True:
        budget.check()
        yield TurnStart()
        request_messages = _close_orphans(hooks.prepare_request(messages))
        context = Context(system=system, messages=request_messages, tools=specs)

        calls: list[ToolCall] = []
        deltas: list[str] = []
        end: TurnEnd | None = None
        # closing() makes an abort close the provider's stream (and its HTTP connection) now.
        with closing(provider.stream(context)) as stream:
            for event in stream:
                if abort.is_set():
                    break
                yield event  # the CLI prints deltas; agent.py traces everything
                match event:
                    case MessageDelta():
                        deltas.append(event.text)
                    case ToolCall():
                        calls.append(event)
                    case TurnEnd():
                        end = event

        if end is not None:
            budget.charge(provider.model, end.usage.model_dump())

        if abort.is_set():
            # Every unanswered call still gets a result, so the transcript stays valid.
            text = [Text(text="".join(deltas))] if deltas else []
            message = (
                end.message
                if end
                else AssistantMessage(
                    content=[*text, *calls], provider=provider.name, model=provider.model
                )
            )
            messages.append(message)
            for c in calls:
                yield ToolEnd(call=c, output=ABORTED_MSG, is_error=True)
                messages.append(ToolResult(call_id=c.id, output=ABORTED_MSG, is_error=True))
            yield TurnEnd(stop_reason="aborted", usage=Usage(), message=message)
            return

        if end is None:
            raise LLMError(
                message=f"{provider.name} stream ended without a TurnEnd", status="incomplete"
            )
        messages.append(end.message)  # rig's own type: the runtime never sees vendor JSON

        if calls:
            results = yield from run_tools(calls, end.stop_reason, by_name, hooks, abort)
            messages.extend(
                ToolResult(call_id=c.id, output=out, is_error=err) for c, out, err in results
            )
            if abort.is_set():
                return

        # Steering lands here, after the tool results and before the next request: never
        # mid-stream (the model is mid-answer) or mid-batch (a tool_use would lose its result).
        steer = get_steering()
        if not calls and not steer:
            # The agent is about to stop. A queued follow-up becomes the next task instead of
            # interrupting this one; with none, the run is over.
            steer = get_follow_up()
            if not steer:
                return  # end_turn, refusal, or truncated text with no calls
        messages.extend(steer)  # appended to the transcript, so the next turn sees it


def run_tools(
    calls: list[ToolCall],
    stop_reason: str,
    tools: dict[str, RuntimeTool],
    hooks: Hooks,
    abort: threading.Event,
) -> Generator[Event, None, list[ToolCallResult]]:
    """Run one batch of calls; yields ToolStart/ToolEnd and returns results in call order.

    How:
      1. A `max_tokens` stop means the model was cut off mid-response, so a call's arguments
         may be incomplete JSON. Nothing runs; every call gets an error asking for a re-issue.
      2. `one(c)` handles a single call from start to finish and never raises: abort,
         unknown tool and a denied call all become error results the model can read.
      3. If every call is read-only, they run in parallel threads. `pool.map` returns results
         in submission order however they finish, so ToolEnds still come out in call order.
         All ToolStarts are yielded first, because the batch starts together.
      4. If any call can change something, the whole batch runs one at a time in order: a
         read after an edit must see the edit. Each call gets its ToolStart/ToolEnd pair
         around it, so the CLI shows progress live.
    The caller turns the returned results into ToolResult messages.
    """
    if stop_reason == "max_tokens":  # arguments may be cut off: run nothing
        truncated: list[ToolCallResult] = [(c, TRUNCATED_MSG, True) for c in calls]
        for c, out, err in truncated:
            yield ToolEnd(call=c, output=out, is_error=err)
        return truncated

    def one(c: ToolCall) -> ToolCallResult:
        # Checks run cheapest first; any of them short-circuits to an error result.
        if abort.is_set():  # checked per call, so Ctrl-C skips the calls not yet started
            return c, ABORTED_MSG, True
        tool = tools.get(c.name)
        if tool is None:
            return c, f"Tool {c.name} is not registered. Available tools: {sorted(tools)}", True
        verdict = hooks.before_tool(c)
        if verdict is not None:
            return c, f"Blocked: {verdict.reason}", True
        lock = _PATH_LOCKS.get(tool.lock_key(c.arguments)) if tool.lock_key else nullcontext()
        with lock:  # a no-op unless the tool writes a file
            out, is_error = tool.run(c.arguments)
        out, is_error = hooks.after_tool(c, (out, is_error))  # e.g. redact or trim output
        return c, out, is_error

    results: list[ToolCallResult] = []
    if all(c.name in tools and tools[c.name].read_only for c in calls):
        for c in calls:
            yield ToolStart(call=c)
        with ThreadPoolExecutor(max_workers=min(8, len(calls))) as pool:
            results = list(pool.map(one, calls))  # map() keeps submission order
        for c, out, err in results:
            yield ToolEnd(call=c, output=out, is_error=err)
    else:
        for c in calls:  # any mutating call: the whole batch runs in order, one at a time
            yield ToolStart(call=c)
            result = one(c)
            results.append(result)
            yield ToolEnd(call=c, output=result[1], is_error=result[2])
    return results


def _close_orphans(messages: list[Message]) -> list[Message]:
    """Give every ToolCall without a ToolResult a synthetic one, for the request only.

    Why: every API rejects a request where a tool call has no result. That happens when a
    run crashes or is killed between appending an AssistantMessage and appending its
    results, and the session is then resumed. The abort path already answers its calls;
    this is the last line of defense, and it runs on rig's types, so it covers every provider.

    How, in one pass:
      1. Collect the ids of every call that already has a ToolResult (`answered`).
      2. Copy messages to `out`. On each AssistantMessage, remember its unanswered calls
         in `pending`.
      3. Real results follow their assistant message, so while the next messages are
         ToolResults, keep copying. At the first message that isn't one (or at the end),
         `flush()` writes a synthetic error result for each pending call, then clears it.
    So synthetic results land right after the real ones of the same turn, which is where
    the API expects them. Example, where call 2 never got a result:
        [User, Assistant(call 1, call 2), Result(1), User]
     -> [User, Assistant(call 1, call 2), Result(1), Result(2, synthetic), User]
    It returns a new list and leaves `messages` alone: the stored transcript stays a true
    record, and only the request is patched.
    """
    answered = {m.call_id for m in messages if isinstance(m, ToolResult)}
    out: list[Message] = []
    pending: list[ToolCall] = []  # unanswered calls of the latest assistant message

    def flush() -> None:
        out.extend(ToolResult(call_id=c.id, output=ORPHAN_MSG, is_error=True) for c in pending)
        pending.clear()

    for m in messages:
        if not isinstance(m, ToolResult):
            flush()  # results belong right after their assistant message's real ones
        out.append(m)
        if isinstance(m, AssistantMessage):
            pending.extend(p for p in m.content if isinstance(p, ToolCall) and p.id not in answered)
    flush()
    return out
