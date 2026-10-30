"""The `rig` command line: one Typer app, one function per subcommand.

These are one-shot commands (`rig run`, `rig resume`, ...). Commands typed inside a running
session (`/steer`, later `/config`) get their own small handler in the interactive session
(Week 12); both call the same core functions, so only the thin parsing layer differs.
"""

import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Annotated, Any

import typer

from . import config
from .agent import Agent
from .config import Config, LoadedConfig
from .providers.types import AssistantMessage, Event, MessageDelta, Provider, ToolStart, TurnEnd
from .session import SessionLog
from .trace import Trace
from .workspace import Workspace

app = typer.Typer(
    help="rig: a coding agent built from first principles.",
    no_args_is_help=True,
    add_completion=False,  # shell completion comes with the interactive shell (Week 12)
)


@dataclass
class Ctx:
    """What the commands take from their caller, passed as Typer's `obj`."""

    cwd: Path = field(default_factory=Path.cwd)
    # Tests put a FakeProvider here; otherwise --provider/--model build a real one.
    provider: Provider | None = None
    # Called with the Agent before it runs, so the CLI can wire Ctrl-C and typed input to it.
    on_agent: Callable[[Agent], None] | None = None


def _ctx(ctx: typer.Context) -> Ctx:
    return ctx.obj if isinstance(ctx.obj, Ctx) else Ctx()


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


def _settings(c: Ctx, repo: Path | None, **flags: Any) -> _Settings:
    """The flags actually given, over the layered config; the workspace defaults to the cwd."""
    loaded = _load_config(c, flags)
    return _Settings(repo or c.cwd, loaded.config)


def _load_config(c: Ctx, flags: dict[str, Any] | None = None) -> LoadedConfig:
    try:
        loaded = config.load(c.cwd, flags)
    except config.ConfigError as e:
        raise _fail(str(e)) from None
    for warning in loaded.warnings:
        typer.echo(f"rig: warning: {warning}", err=True)
    return loaded


def _fail(message: str, code: int = 1) -> typer.Exit:
    typer.echo(f"rig: {message}", err=True)
    return typer.Exit(code)


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
        raise _fail(f"no session {ref!r} (looked for {path})")
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
            raise _fail("this session ended with an answer; pass --task to continue it")
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
    c = _ctx(ctx)
    session = SessionLog(_sessions_dir(c) / f"{_new_session_id()}.jsonl")
    o = _settings(
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
    c = _ctx(ctx)
    o = _settings(
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
    c = _ctx(ctx)
    log = _open_session(c, session)
    try:
        log.checkout(entry_id)
    except KeyError as e:
        raise _fail(e.args[0]) from None
    o = _settings(
        c, repo, use_sandbox=use_sandbox, provider=provider, model=model, max_tokens=max_tokens
    )
    _run(c, o, log, task)


@app.command()
def show(
    ctx: typer.Context,
    session: Annotated[str, typer.Argument(help="Session id, or a path to its .jsonl file")],
) -> None:
    """List a session's entries, to pick one to fork from."""
    for e in _open_session(_ctx(ctx), session).load():
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


# --- rig config: read and change the layered settings ---

config_app = typer.Typer(
    help="Read and change settings. Layers, lowest first: built-in defaults, your user file "
    "(~/.config/rig/config.json), the project's .rig/config.json, RIG_* environment variables, "
    "then command-line flags.",
    no_args_is_help=True,
)
app.add_typer(config_app, name="config")

UserScope = Annotated[
    bool, typer.Option("--user", help="Your user file instead of the project's .rig/config.json")
]


@config_app.command("get")
def config_get(
    ctx: typer.Context, key: Annotated[str, typer.Argument(help="e.g. budget.max_usd")]
) -> None:
    """Print the value a run would use."""
    try:
        typer.echo(_load_config(_ctx(ctx)).get(key))
    except config.ConfigError as e:
        raise _fail(str(e)) from None


@config_app.command("set")
def config_set(
    ctx: typer.Context,
    key: Annotated[str, typer.Argument(help="e.g. model, budget.max_usd")],
    value: str,
    user: UserScope = False,
) -> None:
    """Set KEY in the project file (or your user file with --user)."""
    try:
        path = config.set_value(_ctx(ctx).cwd, key, value, "user" if user else "project")
    except config.ConfigError as e:
        raise _fail(str(e)) from None
    typer.echo(f"{key} = {value}  ({path})")


@config_app.command("unset")
def config_unset(ctx: typer.Context, key: str, user: UserScope = False) -> None:
    """Remove KEY from the project file (or your user file with --user)."""
    if not config.unset_value(_ctx(ctx).cwd, key, "user" if user else "project"):
        raise _fail(f"{key} is not set in the {'user' if user else 'project'} file")
    typer.echo(f"unset {key}")


@config_app.command("list")
def config_list(
    ctx: typer.Context,
    show_origin: Annotated[
        bool, typer.Option("--show-origin", help="Name the layer each value came from")
    ] = False,
) -> None:
    """Print every setting a run would use."""
    loaded = _load_config(_ctx(ctx))
    for key in config.leaves(loaded.config.model_dump()):
        line = f"{key} = {loaded.get(key)}"
        typer.echo(f"{line:<40}  # {loaded.origins[key]}" if show_origin else line)
