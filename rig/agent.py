from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from functools import cache
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict

from . import llm
from .budget import Budget
from .exceptions import BudgetExceededError, LLMError, ToolError
from .logging import get_logger
from .timer import Timer
from .tools import get_tool_names, get_tools_schemas, run_tool
from .trace import Trace
from .workspace import Workspace

logger = get_logger()
SYSTEM_PROMPT = Path(__file__).parent / "prompts" / "system_prompt.md"


@cache
def get_sys_prompt() -> str | None:
    if SYSTEM_PROMPT.exists():
        return SYSTEM_PROMPT.read_text()
    return None


def _prepare_message(role: str, text: str) -> dict[str, Any]:
    return {"role": role, "content": [{"type": "text", "text": text}]}


def _get_tool_requests(llm_response: dict[str, Any]) -> list[Any]:
    return [
        block
        for block in llm_response["content"]
        if block["type"] == "tool_use" and block["name"] in get_tool_names()
    ]


def _execute_tools(
    ws: Workspace, tool_requests: list[dict[str, Any]]
) -> Iterator[tuple[tuple[str, bool], dict[str, float]]]:
    def _task_executor(
        tool_request: dict[str, Any],
    ) -> tuple[tuple[str, bool], dict[str, float]]:
        with Timer() as t:
            return run_tool(ws, tool_request["name"], **tool_request["input"]), {
                "runtime_s": t.elapsed_s()
            }

    return _TOOL_EXECUTOR.map(_task_executor, tool_requests)


# def _call_llm(model: str, )

_TOOL_EXECUTOR = ThreadPoolExecutor(max_workers=10)


class AgentRunResult(BaseModel):
    status: str
    messages: list[Any]
    final_response: str = ""
    exception: Exception | None = None

    model_config = ConfigDict(arbitrary_types_allowed=True)


class Agent:
    def __init__(
        self,
        ws: Workspace,
        task: str,
        *,
        model: str,
        budget: Budget,
        trace: Trace,
        max_tokens: int = 10000,
    ) -> None:
        self._model = model
        self.task = task
        self._all_messages = []
        self._ws = ws
        self._trace = trace
        self._budget = budget
        self._step = 0

        self._all_messages.append(_prepare_message("user", task))

        self._base_request = {
            "max_tokens": max_tokens,
            "model": model,
            "messages": self._all_messages,
            "tools": get_tools_schemas(),
        }
        if get_sys_prompt():
            self._base_request["system"] = get_sys_prompt()

        self._stop_reason_handler = {
            "end_turn": self._handle_end_turn,
            "tool_use": self._handle_tool_use,
            "max_tokens": self._handle_stop_reason_max_tokens,
        }

    def _call_llm(self) -> dict[str, Any]:
        try:
            self._budget.check()
        except BudgetExceededError as err:
            self._trace.log_event(
                "agent.budget.exceeded", budget=self._budget.totals(), step=self._step
            )
            raise err
        logger.debug(f"Requesting llm: {self._all_messages[-1]}")
        self._trace.log_event(
            "agent.llm_request.latest_message", user_message=self._all_messages[-1], step=self._step
        )
        llm_response, api_call_info = llm.call(self._base_request)
        self._all_messages.append({"role": "assistant", "content": llm_response["content"]})
        self._trace.log_event(
            "agent.llm_response",
            response_content=[
                block for block in llm_response["content"] if block["type"] != "thinking"
            ],
            step=self._step,
            stop_reason=llm_response["stop_reason"],
        )
        logger.debug(f"LLM response: {llm_response['content']}")
        self._budget.charge(self._model, llm_response["usage"])
        return llm_response

    def _handle_stop_reason_fallback_fn(self, llm_response: dict[str, Any]) -> bool:
        return False

    def _handle_stop_reason_max_tokens(self, llm_response: dict[str, Any]) -> bool:
        tool_requests = _get_tool_requests(llm_response)
        if len(tool_requests) == 0:
            # no tool requests, most likely response was text which was truncated.
            # nothing pending to respond to.
            return False

        _TRUNCATED_MSG = (
            "Not executed: your response hit max_tokens, so these arguments may be "
            "truncated. Re-issue the call with complete arguments."
        )
        _llm_response_content = []

        for _request in tool_requests:
            self._trace.log_event(
                "agent.tool.result",
                step=self._step,
                call_id=_request["id"],
                tool=_request["name"],
                input=_request["input"],
                response=_TRUNCATED_MSG,
                is_error=True,
            )
            _llm_response_content.append(
                {
                    "tool_use_id": _request["id"],
                    "type": "tool_result",
                    "content": [{"type": "text", "text": _TRUNCATED_MSG}],
                    "is_error": True,
                }
            )
        self._all_messages.append({"role": "user", "content": _llm_response_content})
        return True

    def _handle_end_turn(self, llm_response: dict[str, Any]) -> bool:
        # end loop.
        return False

    def _handle_tool_use(self, llm_response: dict[str, Any]) -> bool:
        logger.debug(f"Handling tool_use with llm_response: {llm_response}")
        tool_requests = _get_tool_requests(llm_response)
        if len(tool_requests) == 0:
            logger.debug("LLM response is to run tool but no valid tool found in request.")
            return False

        _all_tool_results = _execute_tools(self._ws, tool_requests)
        logger.debug("Tool Run complete.")
        _llm_response_content = []
        for _request, ((_tool_result, is_error), _t_metadata) in zip(
            tool_requests, _all_tool_results, strict=True
        ):
            self._trace.log_event(
                "agent.tool.result",
                step=self._step,
                call_id=_request["id"],
                tool=_request["name"],
                input=_request["input"],
                response=_tool_result,
                is_error=is_error,
                duration_s=_t_metadata["runtime_s"],
            )
            _llm_response_content.append(
                {
                    "tool_use_id": _request["id"],
                    "type": "tool_result",
                    "content": [{"type": "text", "text": _tool_result}],
                    "is_error": is_error,
                }
            )
        self._all_messages.append({"role": "user", "content": _llm_response_content})
        return True

    def run(self) -> AgentRunResult:
        self._trace.log_event("agent.run.start", step=self._step)
        _run_result = AgentRunResult(status="error", messages=self._all_messages)
        try:
            while True:
                self._step += 1
                logger.debug(f"Agent-RUN: Running loop iteration: {self._step}")
                llm_response = self._call_llm()
                logger.debug(f"AgentRun response stop_reason: {llm_response['stop_reason']}")

                # Determine next steps after response from llm
                _continue_loop = self._stop_reason_handler.get(
                    llm_response["stop_reason"], self._handle_stop_reason_fallback_fn
                )(llm_response)
                if not _continue_loop:
                    break

            last_msg = self._all_messages[-1]
            if last_msg["role"] != "assistant":
                final_msg = ""
            else:
                final_msg = "".join(
                    block["text"] for block in last_msg["content"] if block["type"] == "text"
                )
            _run_result.status = "success"
            _run_result.final_response = final_msg
        except Exception as err:
            logger.exception(err)
            _run_result.status = "error"
            if isinstance(err, BudgetExceededError):
                _run_result.final_response = str(err)
                _run_result.status = f"error.budget.{err.status}"
            elif isinstance(err, ToolError):
                _run_result.final_response = str(err)
                _run_result.status = f"error.tool.{err.tool}"
            elif isinstance(err, LLMError):
                _run_result.final_response = str(err)
                _run_result.status = "error.llm"
            else:
                _run_result.final_response = "Internal error."
            _run_result.exception = err
        finally:
            self._trace.log_event(
                "agent.run.end",
                result=_run_result.model_dump_json(exclude={"exception"}),
                step=self._step,
            )
            _run_result.messages = self._all_messages
        return _run_result
