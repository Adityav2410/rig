from typing import Any


class RigError(Exception):
    """Base class for exceptions in this module."""

    def __init__(
        self, message: str, status: str | None = None, payload: dict[str, Any] | None = None
    ) -> None:
        super().__init__(message)
        self.status = status
        self.payload = payload


class BudgetExceededError(RigError):
    """Exception raised when the budget is exceeded."""


class LLMError(RigError): ...


class ToolError(RigError):
    def __init__(
        self,
        tool: str,
        message: str,
        status: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message=message, status=status, payload=payload)
        self.tool = tool


class PathEscapesWorkspace(RigError):
    """Raised when a resolved path would fall outside the workspace root."""


class SandboxUnavailable(RigError): ...


class SandboxError(RigError): ...
