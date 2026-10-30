import inspect
import logging


def get_caller_module_name() -> str | None:
    # inspect.stack()[1] corresponds to the immediate caller of this function
    frame = inspect.stack()[2]

    # Get the module object associated with that frame
    module = inspect.getmodule(frame[0])

    # Return the module's __name__ (or None if it can't be resolved)
    return module.__name__ if module else None


class Logger(logging.Logger): ...


def get_logger(name: str | None = None) -> logging.Logger:
    """Return logger."""
    name = name or get_caller_module_name()
    return logging.getLogger(name)
