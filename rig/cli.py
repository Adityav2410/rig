"""The `rig` command: the Typer app in commands.py, plus what only a terminal needs.

The terminal-only parts live here: Ctrl-C and reading what you type while a run streams.
"""

import signal
import sys
import threading
from types import FrameType

from .agent import Agent
from .commands import Ctx, app


def main() -> None:
    app(obj=Ctx(on_agent=_attach))  # exits with the command's status


def _attach(agent: Agent) -> None:
    """First Ctrl-C stops the run at its next safe point; a second one quits.

    A signal handler, not `except KeyboardInterrupt`: the interrupt can land in the middle of
    any line, while `agent.abort()` only sets a flag the runtime checks where stopping is safe.
    """

    def on_sigint(signum: int, frame: FrameType | None) -> None:
        if agent.aborting:
            sys.exit(130)
        agent.abort()
        print("\n[stopping after the current step; Ctrl-C again to quit]", file=sys.stderr)

    signal.signal(signal.SIGINT, on_sigint)
    if sys.stdin.isatty():
        threading.Thread(target=_read_input, args=(agent,), daemon=True).start()


def _read_input(agent: Agent) -> None:
    """Lines typed during a run: `/steer ...` redirects the current task, anything else queues
    the next one."""
    for line in sys.stdin:
        text = line.strip()
        if text.startswith("/steer "):
            agent.steer(text.removeprefix("/steer ").strip())
        elif text:
            agent.follow_up(text)
