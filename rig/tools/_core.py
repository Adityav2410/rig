from typing import Any

from ..exceptions import PathEscapesWorkspace, ToolError
from ..logging import get_logger
from ..workspace import Workspace
from . import _registry

logger = get_logger()

MAX_OUT = 30_000  # characters returned by model per call


def run_tool(ws: Workspace, name: str, **kwargs: Any) -> tuple[str, bool]:
    tool = _registry.get_tool(name)
    if tool is None:
        return f"Tool {name} is not registered. Available tools: {_registry.get_tool_names()}", True
    error_msg: str | None = None
    exc: Exception | None = None
    try:
        out = tool.func(ws, **kwargs)
    except PathEscapesWorkspace as e:
        error_msg, exc = f"Error executing tool: {name}. [{e.status}] {e}", e
    except ToolError as e:
        error_msg, exc = f"Error executing tool: {name}. Error: {e}", e
    except TypeError as e:
        error_msg, exc = f"Bad arguments for {name}: {e}", e
    except Exception as e:
        error_msg, exc = f"Error executing tool: {name}. {e}", e

    if error_msg:
        logger.exception(error_msg, exc)
        return truncate(error_msg), True
    return truncate(out), False


def truncate(s: str) -> str:
    if len(s) <= MAX_OUT:
        return s
    head, tail = (
        s[: MAX_OUT * 2 // 3],
        s[-(MAX_OUT // 3) :],
    )  # keep the tail: errors and summaries live there
    return f"{head}\n\n[... {len(s) - len(head) - len(tail)} characters omitted ...]\n\n{tail}"
