from typing import Any

from ..core.exceptions import PathEscapesWorkspace, ToolError
from ..sandbox.workspace import Workspace
from ..util.logging import get_logger
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
        # Expected failures are results for the model, not crashes: log them quietly. Anything
        # else is a bug in a tool, so it gets its traceback.
        if isinstance(exc, (PathEscapesWorkspace, ToolError, TypeError)):
            logger.debug(error_msg)
        else:
            logger.error(error_msg, exc_info=exc)
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
