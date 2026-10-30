"""`rig config`: read and change the layered settings (see core/config.py)."""

from typing import Annotated

import typer

from ..core import config
from .common import fail, get_ctx, load_config

app = typer.Typer(
    help="Read and change settings. Layers, lowest first: built-in defaults, your user file "
    "(~/.config/rig/config.json), the project's .rig/config.json, RIG_* environment variables, "
    "then command-line flags.",
    no_args_is_help=True,
)

UserScope = Annotated[
    bool, typer.Option("--user", help="Your user file instead of the project's .rig/config.json")
]


@app.command("get")
def config_get(
    ctx: typer.Context, key: Annotated[str, typer.Argument(help="e.g. budget.max_usd")]
) -> None:
    """Print the value a run would use."""
    try:
        typer.echo(load_config(get_ctx(ctx)).get(key))
    except config.ConfigError as e:
        raise fail(str(e)) from None


@app.command("set")
def config_set(
    ctx: typer.Context,
    key: Annotated[str, typer.Argument(help="e.g. model, budget.max_usd")],
    value: str,
    user: UserScope = False,
) -> None:
    """Set KEY in the project file (or your user file with --user)."""
    try:
        path = config.set_value(get_ctx(ctx).cwd, key, value, "user" if user else "project")
    except config.ConfigError as e:
        raise fail(str(e)) from None
    typer.echo(f"{key} = {value}  ({path})")


@app.command("unset")
def config_unset(ctx: typer.Context, key: str, user: UserScope = False) -> None:
    """Remove KEY from the project file (or your user file with --user)."""
    if not config.unset_value(get_ctx(ctx).cwd, key, "user" if user else "project"):
        raise fail(f"{key} is not set in the {'user' if user else 'project'} file")
    typer.echo(f"unset {key}")


@app.command("list")
def config_list(
    ctx: typer.Context,
    show_origin: Annotated[
        bool, typer.Option("--show-origin", help="Name the layer each value came from")
    ] = False,
) -> None:
    """Print every setting a run would use."""
    loaded = load_config(get_ctx(ctx))
    for key in config.leaves(loaded.config.model_dump()):
        line = f"{key} = {loaded.get(key)}"
        typer.echo(f"{line:<40}  # {loaded.origins[key]}" if show_origin else line)
