"""Layered config: which layer wins, one-key writes, validation, origins and the base_url rule.

conftest.py points the user file at an empty temp dir and clears RIG_* for every test.
"""

import json
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from rig import agent as agent_module
from rig import config
from rig.commands import Ctx, app
from rig.providers.fake import FakeProvider, text_turn

runner = CliRunner()


def _write(path: Path, data: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data))
    return path


def _user_file() -> Path:
    return config.user_path()


def _project_file(cwd: Path) -> Path:
    return cwd / ".rig" / "config.json"


def test_each_layer_beats_the_one_below(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    assert config.load(tmp_path).config.model == config.Config().model  # defaults alone

    _write(_user_file(), {"model": "from-user", "max_tokens": 1000})
    assert config.load(tmp_path).config.model == "from-user"

    _write(_project_file(tmp_path), {"model": "from-project"})
    loaded = config.load(tmp_path)
    assert (loaded.config.model, loaded.config.max_tokens) == ("from-project", 1000)

    monkeypatch.setenv("RIG_MODEL", "from-env")
    assert config.load(tmp_path).config.model == "from-env"

    assert config.load(tmp_path, {"model": "from-flag"}).config.model == "from-flag"
    assert config.load(tmp_path, {"model": None}).config.model == "from-env"  # None: not given


def test_nested_sections_merge_key_by_key(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _write(_project_file(tmp_path), {"budget": {"max_usd": 2.5}})
    monkeypatch.setenv("RIG_BUDGET__MAX_STEPS", "7")

    budget = config.load(tmp_path).config.budget

    assert (budget.max_usd, budget.max_steps) == (2.5, 7)
    assert budget.max_wall_clock_s == config.BudgetConfig().max_wall_clock_s  # untouched default


def test_the_nearest_project_file_above_the_cwd_is_used(tmp_path: Path) -> None:
    _write(_project_file(tmp_path), {"model": "repo-root"})
    deep = tmp_path / "src" / "pkg"
    deep.mkdir(parents=True)
    assert config.load(deep).config.model == "repo-root"


def test_origin_names_the_layer_each_value_came_from(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write(_user_file(), {"max_tokens": 1000})
    _write(_project_file(tmp_path), {"model": "m"})
    monkeypatch.setenv("RIG_PROVIDER", "openai")

    origins = config.load(tmp_path, {"use_sandbox": True}).origins

    assert origins["max_tokens"].startswith("user")
    assert origins["model"].startswith("project")
    assert origins["provider"] == "env"
    assert origins["use_sandbox"] == "flag"
    assert origins["budget.max_usd"] == "default"


def test_set_writes_one_key_to_one_file(tmp_path: Path) -> None:
    user = _write(_user_file(), {"model": "mine", "max_tokens": 1000})
    before = user.read_bytes()

    config.set_value(tmp_path, "max_tokens", "4096", "project")

    assert user.read_bytes() == before  # the user file is untouched
    assert json.loads(_project_file(tmp_path).read_text()) == {"max_tokens": 4096}  # coerced


def test_an_invalid_value_is_rejected_and_nothing_is_written(tmp_path: Path) -> None:
    project = _write(_project_file(tmp_path), {"model": "m"})
    before = project.read_bytes()

    with pytest.raises(config.ConfigError, match="max_tokens"):
        config.set_value(tmp_path, "max_tokens", "lots", "project")
    with pytest.raises(config.ConfigError, match="modle"):
        config.set_value(tmp_path, "modle", "x", "project")  # a typo is not a new setting

    assert project.read_bytes() == before


def test_unset_removes_only_that_key(tmp_path: Path) -> None:
    _write(_project_file(tmp_path), {"model": "m", "max_tokens": 1000})
    assert config.unset_value(tmp_path, "model", "project")
    assert json.loads(_project_file(tmp_path).read_text()) == {"max_tokens": 1000}
    assert not config.unset_value(tmp_path, "model", "project")


def test_base_url_comes_only_from_the_user_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write(_project_file(tmp_path), {"base_url": "https://attacker.example"})
    monkeypatch.setenv("RIG_BASE_URL", "https://also-not-trusted.example")

    loaded = config.load(tmp_path)

    assert loaded.config.base_url is None
    assert len(loaded.warnings) == 2
    with pytest.raises(config.ConfigError, match="--user"):
        config.set_value(tmp_path, "base_url", "http://localhost:8080", "project")

    config.set_value(tmp_path, "base_url", "http://localhost:8080", "user")
    assert config.load(tmp_path).config.base_url == "http://localhost:8080"


def test_secrets_and_unknown_keys_in_a_file_are_errors(tmp_path: Path) -> None:
    _write(_project_file(tmp_path), {"anthropic_api_key": "sk-..."})
    with pytest.raises(config.ConfigError, match="secret"):
        config.load(tmp_path)

    _write(_project_file(tmp_path), {"modle": "typo"})
    with pytest.raises(config.ConfigError, match="modle"):
        config.load(tmp_path)


# --- through the CLI: Wednesday's "Done when" ---


def test_config_set_then_run_uses_the_new_model(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    built: list[tuple[str, str]] = []

    def fake_get_provider(name: str, model: str, *, max_tokens: int = 0) -> FakeProvider:
        built.append((name, model))
        return FakeProvider([text_turn("ok")])

    monkeypatch.setattr(agent_module, "get_provider", fake_get_provider)
    ctx = Ctx(cwd=tmp_path)

    assert runner.invoke(app, ["config", "set", "model", "claude-test-x"], obj=ctx).exit_code == 0
    result = runner.invoke(app, ["run", "--task", "go"], obj=ctx)

    assert result.exit_code == 0, result.output
    assert built == [("anthropic", "claude-test-x")]


def test_config_list_show_origin_and_get(tmp_path: Path) -> None:
    ctx = Ctx(cwd=tmp_path)
    runner.invoke(app, ["config", "set", "budget.max_usd", "3"], obj=ctx)

    listed = runner.invoke(app, ["config", "list", "--show-origin"], obj=ctx)
    got = runner.invoke(app, ["config", "get", "budget.max_usd"], obj=ctx)

    line = next(ln for ln in listed.output.splitlines() if ln.startswith("budget.max_usd"))
    assert "3.0" in line and "# project" in line
    assert got.output.strip() == "3.0"
    assert runner.invoke(app, ["config", "get", "nope"], obj=ctx).exit_code == 1


def test_a_malformed_file_names_the_file(tmp_path: Path) -> None:
    path = _project_file(tmp_path)
    path.parent.mkdir(parents=True)
    path.write_text('{"model": "m",}')  # a trailing comma: valid in Python, not in JSON
    with pytest.raises(config.ConfigError, match="not valid JSON"):
        config.load(tmp_path)
