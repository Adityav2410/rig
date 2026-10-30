"""The session commands: run, resume, fork and show."""

import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Annotated, Any

import typer

from ..core.agent import Agent
from ..core.config import Config
from ..core.session import SessionLog
from ..core.trace import Trace
from ..providers.types import AssistantMessage, Event, MessageDelta, ToolStart, TurnEnd
from ..sandbox.workspace import Workspace
from .common import Ctx, fail, get_ctx, load_config

app = typer.Typer()

_D = Config()  # built-in defaults, for --help; config files and RIG_* env can change them

# Options shared by every command that runs the agent. Each defaults to None, meaning "not given
# on the command line", so a flag overrides the config only when it was actually passed.
Repo = Annotated[
    Path | None, typer.Option(help="Workspace to work in [default: current directory]")
]
UseSandbox = Annotated[
    bool | None,
    typer.Option("--use-sandbox", help="Run tools in a Docker sandbox, not on the host"),
]
ProviderName = Annotated[
    str | None, typer.Option(help=f"Which model API to call [default: {_D.provider}]")
]
Model = Annotated[str | None, typer.Option(help=f"Model id [default: {_D.model}]")]
MaxTokens = Annotated[
    int | None, typer.Option(help=f"Output limit per model call [default: {_D.max_tokens}]")
]


@dataclass(frozen=True)
class _Settings:
    repo: Path
    config: Config


def settings(c: Ctx, repo: Path | None, **flags: Any) -> _Settings:
    """The flags actually given, over the layered config; the workspace defaults to the cwd."""
    loaded = load_config(c, flags)
    return _Settings(repo or c.cwd, loaded.config)


# --- sessions on disk ---


def _sessions_dir(c: Ctx) -> Path:
    return c.cwd / ".rig" / "sessions"


def _new_session_id() -> str:
    """Like 261029-1432-3fa9c2e1: local start time first, so a listing sorts by when it began."""
    return f"{datetime.now():%y%m%d-%H%M}-{uuid.uuid4().hex[:8]}"


def _open_session(c: Ctx, ref: str) -> SessionLog:
    """A session by id (`.rig/sessions/<id>.jsonl`) or by path."""
    path = Path(ref) if ref.endswith(".jsonl") else _sessions_dir(c) / f"{ref}.jsonl"
    if not path.exists():
        raise fail(f"no session {ref!r} (looked for {path})")
    return SessionLog(path)


# --- running the agent ---


def _render(event: Event) -> None:
    match event:
        case MessageDelta():
            typer.echo(event.text, nl=False)
        case ToolStart():
            typer.echo(f"\n> {event.call.name} {event.call.arguments}")
        case TurnEnd() if event.stop_reason == "aborted":
            typer.echo("\n[aborted]")


def _run(c: Ctx, o: _Settings, session: SessionLog, task: str | None) -> None:
    """Run the agent on `session`, streaming its output; exit 0 only when it ends in an answer."""
    if task is None:
        last = session.branch()[-1:]
        if not last or isinstance(last[0], AssistantMessage):
            # Sending a transcript that ends in an answer would ask the model to extend it.
            raise fail("this session ended with an answer; pass --task to continue it")
    session_id = session.path.stem
    run_id = uuid.uuid4().hex[:8]  # one per run: names the sandbox container
    trace = Trace(run_id=run_id, filepath=str(c.cwd / ".rig" / "traces" / f"{session_id}.jsonl"))
    cfg = o.config
    with Workspace(root=o.repo, name=o.repo.name, run_id=run_id, use_sandbox=cfg.use_sandbox) as ws:
        agent = Agent(
            ws,
            budget=cfg.budget.build(),
            trace=trace,
            provider=c.provider or cfg.provider,
            model=None if c.provider else cfg.model,
            max_tokens=cfg.max_tokens,
            session=session,
        )
        if c.on_agent:
            c.on_agent(agent)
        result = agent.run(task, on_event=_render)
    typer.echo(
        f"\n\n[{result.status}] session {session_id}. "
        f'Resume session with `rig resume {session_id} --task: "..."`'
    )
    if result.status != "success":
        if result.final_response:
            typer.echo(result.final_response)
        raise typer.Exit(1)


@app.command()
def run(
    ctx: typer.Context,
    task: Annotated[str, typer.Option(help="The prompt for this run")],
    repo: Repo = None,
    use_sandbox: UseSandbox = None,
    provider: ProviderName = None,
    model: Model = None,
    max_tokens: MaxTokens = None,
) -> None:
    """Start a new session with --task as its first prompt."""
    c = get_ctx(ctx)
    session = SessionLog(_sessions_dir(c) / f"{_new_session_id()}.jsonl")
    o = settings(
        c, repo, use_sandbox=use_sandbox, provider=provider, model=model, max_tokens=max_tokens
    )
    _run(c, o, session, task)


@app.command()
def resume(
    ctx: typer.Context,
    session: Annotated[str, typer.Argument(help="Session id, or a path to its .jsonl file")],
    task: Annotated[
        str | None, typer.Option(help="A new prompt; omit to finish a cut-off run")
    ] = None,
    repo: Repo = None,
    use_sandbox: UseSandbox = None,
    provider: ProviderName = None,
    model: Model = None,
    max_tokens: MaxTokens = None,
) -> None:
    """Continue a session."""
    c = get_ctx(ctx)
    o = settings(
        c, repo, use_sandbox=use_sandbox, provider=provider, model=model, max_tokens=max_tokens
    )
    _run(c, o, _open_session(c, session), task)


@app.command()
def fork(
    ctx: typer.Context,
    session: Annotated[str, typer.Argument(help="Session id, or a path to its .jsonl file")],
    entry_id: Annotated[str, typer.Argument(help="The entry to branch from (see `rig show`)")],
    task: Annotated[str | None, typer.Option(help="A new prompt for the branch")] = None,
    repo: Repo = None,
    use_sandbox: UseSandbox = None,
    provider: ProviderName = None,
    model: Model = None,
    max_tokens: MaxTokens = None,
) -> None:
    """Branch a session from an earlier entry; the original branch stays in the file."""
    c = get_ctx(ctx)
    log = _open_session(c, session)
    try:
        log.checkout(entry_id)
    except KeyError as e:
        raise fail(e.args[0]) from None
    o = settings(
        c, repo, use_sandbox=use_sandbox, provider=provider, model=model, max_tokens=max_tokens
    )
    _run(c, o, log, task)


@app.command()
def show(
    ctx: typer.Context,
    session: Annotated[str, typer.Argument(help="Session id, or a path to its .jsonl file")],
) -> None:
    """List a session's entries, to pick one to fork from."""
    for e in _open_session(get_ctx(ctx), session).load():
        payload = e["payload"]
        role = payload.get("role", e["type"])
        text = (
            payload.get("text")
            or payload.get("output")
            or " ".join(
                c.get("text") or f"[{c.get('name', c.get('type'))}]"
                for c in payload.get("content", [])
            )
        )
        typer.echo(f"{e['id']}  {role:<11} {' '.join(str(text).split())[:70]}")
