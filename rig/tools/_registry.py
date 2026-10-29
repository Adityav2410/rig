import functools
from collections.abc import Callable
from typing import Any, ParamSpec, TypeVar

from .schema import Tool, ToolInputSchema

_TOOLS: dict[str, Tool] = {}
_TOOL_NAMES: list[str] = []

P = ParamSpec("P")
R = TypeVar("R")


def tool(
    *,
    name: str | None = None,
    description: str = "",
    input_schema: ToolInputSchema,
    input_examples: list[dict[str, Any]],
    read_only: bool = False,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    if name is not None and len(name) == 0:
        raise ValueError("Invalid tool name. Provided empty string which isn't allowed.")

    def register_func(func: Callable[P, R]) -> Callable[P, R]:
        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            return func(*args, **kwargs)

        _register_tool(
            name or func.__name__, description, input_schema, input_examples, func, read_only
        )
        return wrapper

    return register_func


def _register_tool(
    name: str,
    description: str,
    input_schema: ToolInputSchema,
    input_examples: list[dict[str, Any]],
    func: Callable[..., Any],
    read_only: bool = False,
) -> None:
    global _TOOLS
    if len(name) == 0:
        name = func.__name__
    if len(description) == 0:
        raise ValueError(
            f"Invalid description for tool: `{name}`. Description doesn't have any characters."
        )

    if name in _TOOLS:
        raise ValueError(
            f"Tool: {name} is already registered. Cannot register another tool with same name."
        )
    _TOOLS[name] = Tool(
        name=name,
        description=description,
        input_schema=input_schema,
        input_examples=input_examples,
        func=func,
        read_only=read_only,
    )
    _TOOL_NAMES.append(name)
    _TOOL_NAMES.sort()


def get_tool(name: str) -> None | Tool:
    if name not in _TOOLS:
        return None
    return _TOOLS.get(name)


def get_tool_names() -> list[str]:
    return _TOOL_NAMES


def get_tools() -> list[Tool]:
    return list(_TOOLS.values())


def get_tools_schemas() -> list[dict[str, Any]]:
    return [tool.schema_for_llm() for tool in get_tools()]


## run at the end to register all tools
# _register_tools()
