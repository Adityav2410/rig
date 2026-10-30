"""rig run / resume / fork / show through Typer's CliRunner, driven by FakeProvider (no network)."""

import re
from pathlib import Path

from typer.testing import CliRunner, Result

from rig.cli.app import app
from rig.cli.common import Ctx
from rig.cli.sessions import settings
from rig.core.config import Config
from rig.core.session import SessionLog
from rig.providers.fake import FakeProvider, text_turn

runner = CliRunner()


def _rig(tmp_path: Path, *args: str, provider: FakeProvider | None = None) -> Result:
    (tmp_path / "repo").mkdir(exist_ok=True)
    flags = ["--repo", str(tmp_path / "repo")] if args[0] in ("run", "resume", "fork") else []
    return runner.invoke(app, [*args, *flags], obj=Ctx(cwd=tmp_path, provider=provider))


def _only_session(tmp_path: Path) -> SessionLog:
    (path,) = (tmp_path / ".rig" / "sessions").glob("*.jsonl")
    return SessionLog(path)


def test_typos_and_missing_options_fail_with_a_message(tmp_path: Path) -> None:
    typo = runner.invoke(app, ["rnu"])
    assert typo.exit_code == 2 and "No such command 'rnu'" in typo.output
    missing = runner.invoke(app, ["run"])
    assert missing.exit_code == 2 and "Missing option '--task'" in missing.output


def test_run_streams_the_answer_and_writes_a_session(tmp_path: Path) -> None:
    result = _rig(tmp_path, "run", "--task", "go", provider=FakeProvider([text_turn("the answer")]))

    assert result.exit_code == 0, result.output
    session = _only_session(tmp_path)
    assert "the answer" in result.output
    assert f"[success] session {session.path.stem}" in result.output
    assert re.fullmatch(r"\d{6}-\d{4}-[0-9a-f]{8}", session.path.stem)  # yymmdd-hhmm-<8 hex>
    assert [m.role for m in session.branch()] == ["user", "assistant"]
    assert (tmp_path / ".rig" / "traces" / f"{session.path.stem}.jsonl").exists()


def test_resume_continues_and_refuses_to_extend_a_finished_answer(tmp_path: Path) -> None:
    _rig(tmp_path, "run", "--task", "one", provider=FakeProvider([text_turn("a")]))
    sid = _only_session(tmp_path).path.stem

    refused = _rig(tmp_path, "resume", sid, provider=FakeProvider([]))
    assert refused.exit_code == 1 and "pass --task" in refused.output

    provider = FakeProvider([text_turn("b")])
    assert _rig(tmp_path, "resume", sid, "--task", "two", provider=provider).exit_code == 0
    assert [m.role for m in provider.contexts[0].messages] == ["user", "assistant", "user"]

    missing = _rig(tmp_path, "resume", "nope")
    assert missing.exit_code == 1 and "no session 'nope'" in missing.output


def test_fork_branches_from_an_earlier_entry_and_keeps_the_original(tmp_path: Path) -> None:
    _rig(tmp_path, "run", "--task", "one", provider=FakeProvider([text_turn("a")]))
    session = _only_session(tmp_path)
    first_user, original_leaf = session.load()[0]["id"], session.head

    provider = FakeProvider([text_turn("other answer")])
    assert _rig(tmp_path, "fork", session.path.stem, first_user, provider=provider).exit_code == 0

    # The fork re-answers the first prompt; the original answer is still on its own branch.
    assert [m.role for m in provider.contexts[0].messages] == ["user"]
    reopened = SessionLog(session.path)
    assert [m.role for m in reopened.branch(original_leaf)] == ["user", "assistant"]
    assert len(reopened.load()) == 3
    assert _rig(tmp_path, "fork", session.path.stem, "nope").exit_code == 1


def test_show_lists_entries_to_fork_from(tmp_path: Path) -> None:
    _rig(tmp_path, "run", "--task", "hello there", provider=FakeProvider([text_turn("hi")]))
    session = _only_session(tmp_path)

    result = _rig(tmp_path, "show", session.path.stem)

    assert result.exit_code == 0
    lines = result.output.splitlines()
    assert lines[0].startswith(session.load()[0]["id"]) and "hello there" in lines[0]
    assert "assistant" in lines[1] and "hi" in lines[1]


def test_without_flags_the_workspace_is_the_cwd_and_there_is_no_sandbox(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        ["run", "--task", "go"],
        obj=Ctx(cwd=tmp_path, provider=FakeProvider([text_turn("ok")])),
    )
    assert result.exit_code == 0, result.output  # no Docker needed: the sandbox is opt-in


def test_only_flags_that_were_given_override_the_defaults(tmp_path: Path) -> None:
    c = Ctx(cwd=tmp_path)
    s = settings(c, None, use_sandbox=None, provider=None, model="other", max_tokens=None)
    assert (s.repo, s.config.model, s.config.provider) == (tmp_path, "other", Config().provider)
    assert s.config.use_sandbox is False
