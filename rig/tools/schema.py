import enum
from collections.abc import Callable
from typing import Any

from pydantic import BaseModel


class ToolPropertyType(enum.StrEnum):
    NULL = "null"
    BOOLEAN = "boolean"
    OBJECT = "object"
    ARRAY = "array"
    NUMBER = "number"
    STRING = "string"


class ToolPropertySchema(BaseModel):
    type: ToolPropertyType
    description: str = ""


class ToolInputSchema(BaseModel):
    type: str = "object"
    properties: dict[str, ToolPropertySchema]
    required: list[str]


class Tool(BaseModel):
    name: str
    description: str
    input_schema: ToolInputSchema
    input_examples: list[dict[str, Any]]
    func: ToolFuncType
    # True only for tools that never change anything; the runtime runs a batch of them in
    # parallel. When in doubt, leave it False: a wrong True lets a write race other calls.
    read_only: bool = False

    def schema_for_llm(self) -> dict[str, Any]:
        return self.model_dump(exclude={"func", "read_only"})


ToolFuncType = Callable[..., str]
