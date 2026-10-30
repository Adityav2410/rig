"""The `rig` command line: the root Typer app, assembled from one module per command group.

These are one-shot commands (`rig run`, `rig config set ...`). Commands typed inside a running
session (`/steer`, later `/config`) get their own small handler in the interactive session
(Week 12); both call the same core functions, so only the thin parsing layer differs.
"""

import typer

from . import config_cmd, sessions

app = typer.Typer(
    help="rig: a coding agent built from first principles.",
    no_args_is_help=True,
    add_completion=False,  # shell completion comes with the interactive shell (Week 12)
)
app.add_typer(sessions.app)  # no name: run, resume, fork and show are top-level commands
app.add_typer(config_cmd.app, name="config")
