"""What every command group shares: the caller's context, config loading and error exits."""

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import typer

from ..core import config
from ..core.agent import Agent
from ..core.config import LoadedConfig
from ..providers.types import Provider


@dataclass
class Ctx:
    """What the commands take from their caller, passed as Typer's `obj`."""

    cwd: Path = field(default_factory=Path.cwd)
    # Tests put a FakeProvider here; otherwise --provider/--model build a real one.
    provider: Provider | None = None
    # Called with the Agent before it runs, so the CLI can wire Ctrl-C and typed input to it.
    on_agent: Callable[[Agent], None] | None = None


def get_ctx(ctx: typer.Context) -> Ctx:
    """The Ctx the caller passed as `obj`, or a default one if it passed none."""
    return ctx.ensure_object(Ctx)


def load_config(c: Ctx, flags: dict[str, Any] | None = None) -> LoadedConfig:
    try:
        loaded = config.load(c.cwd, flags)
    except config.ConfigError as e:
        raise fail(str(e)) from None
    for warning in loaded.warnings:
        typer.echo(f"rig: warning: {warning}", err=True)
    return loaded


def fail(message: str, code: int = 1) -> typer.Exit:
    typer.echo(f"rig: {message}", err=True)
    return typer.Exit(code)
