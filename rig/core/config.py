"""Layered settings: built-in defaults < your user file < the project file < RIG_* env < flags.

A project can pin a model while you keep your own defaults, the way Claude Code and pi layer
their settings. Two safety rules hold everywhere: API keys never go in a config file (they stay
in the environment), and `base_url` is read only from your own user file, because a project file
comes from whoever wrote the repository and could send your API key to their server.
"""

import copy
import json
import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, ValidationError

from .budget import Budget

Scope = Literal["user", "project"]
LAYERS = ("default", "user", "project", "env", "flag")  # lowest first


class BudgetConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    max_steps: int = 100
    max_input_tokens: int = 1_000_000
    max_output_tokens: int = 100_000
    max_usd: float = 0.5
    max_wall_clock_s: float = 300

    def build(self) -> Budget:
        return Budget(**self.model_dump())


class Config(BaseModel):
    model_config = ConfigDict(extra="forbid")  # a typo in a file is an error, not a silent no-op

    provider: str = "anthropic"
    model: str = "claude-haiku-5-5"
    max_tokens: int = 8192
    use_sandbox: bool = False
    base_url: str | None = None  # a local or proxy endpoint; user file only
    budget: BudgetConfig = BudgetConfig()


class ConfigError(Exception):
    pass


# --- where the files are ---


def user_path(env: Mapping[str, str] | None = None) -> Path:
    env = os.environ if env is None else env
    base = env.get("XDG_CONFIG_HOME") or str(Path(env.get("HOME", "~")).expanduser() / ".config")
    return Path(base) / "rig" / "config.json"


def project_path(cwd: Path) -> Path | None:
    """The nearest .rig/config.json at or above `cwd`."""
    for d in [cwd, *cwd.parents]:
        p = d / ".rig" / "config.json"
        if p.is_file():
            return p
    return None


# --- loading ---


@dataclass
class LoadedConfig:
    """The merged config, plus where each value came from and anything that was ignored."""

    config: Config
    origins: dict[str, str]  # dotted key -> layer name ("project (.../.rig/config.json)")
    warnings: list[str] = field(default_factory=list)

    def get(self, key: str) -> Any:
        value: Any = self.config.model_dump()
        for part in key.split("."):
            if not isinstance(value, dict) or part not in value:
                raise ConfigError(f"unknown key {key!r}; see `rig config list`")
            value = value[part]
        return value


def load(
    cwd: Path, flags: Mapping[str, Any] | None = None, env: Mapping[str, str] | None = None
) -> LoadedConfig:
    """Merge every layer, lowest first, then validate the result once.

    How: each layer is read into a plain nested dict and merged key by key over the ones
    below it, so a project file that sets only `budget.max_usd` keeps every other budget
    value. Each leaf key remembers the last layer that set it, for `rig config list
    --show-origin`. Validating only the merged result lets a layer be partial.
    """
    env = os.environ if env is None else env
    warnings: list[str] = []
    user = user_path(env)
    project = project_path(cwd)
    layers: list[tuple[str, dict[str, Any]]] = [
        ("default", Config().model_dump()),
        (f"user ({user})", _read(user)),
    ]
    project_data = _read(project) if project else {}
    if "base_url" in project_data:
        project_data.pop("base_url")
        warnings.append(f"ignored base_url in {project}: it is accepted only from {user}")
    layers.append((f"project ({project})", project_data))
    layers.append(("env", _from_env(env, warnings)))
    layers.append(("flag", {k: v for k, v in (flags or {}).items() if v is not None}))

    merged: dict[str, Any] = {}
    origins: dict[str, str] = {}
    for name, data in layers:
        _merge(merged, data)
        for key in leaves(data):
            origins[key] = name
    try:
        config = Config.model_validate(merged)
    except ValidationError as e:
        raise ConfigError(_explain(e)) from None
    return LoadedConfig(config, origins, warnings)


def _read(path: Path | None) -> dict[str, Any]:
    if path is None or not path.exists():
        return {}
    try:
        data = json.loads(path.read_text() or "{}")
    except json.JSONDecodeError as e:
        raise ConfigError(f"{path}: not valid JSON ({e})") from None
    if not isinstance(data, dict):
        raise ConfigError(f"{path}: expected a mapping of keys to values")
    for key in leaves(data):
        if _looks_secret(key):
            raise ConfigError(
                f"{path}: {key!r} looks like a secret; keep API keys in the environment"
            )
    return data


def _looks_secret(key: str) -> bool:
    k = key.lower()
    return any(s in k for s in ("api_key", "apikey", "secret", "password")) or k.endswith("_token")


def _from_env(env: Mapping[str, str], warnings: list[str]) -> dict[str, Any]:
    """RIG_MODEL -> model, RIG_BUDGET__MAX_USD -> budget.max_usd. Other RIG_* names are ignored."""
    known = set(leaves(Config().model_dump()))
    out: dict[str, Any] = {}
    for name, value in env.items():
        if not name.startswith("RIG_"):
            continue
        key = name.removeprefix("RIG_").lower().replace("__", ".")
        if key == "base_url":
            warnings.append("ignored RIG_BASE_URL: base_url is accepted only from your user file")
        elif key in known:
            _merge(out, _nest(key, value))
    return out


# --- writing one key in one file ---


def set_value(cwd: Path, key: str, value: str, scope: Scope) -> Path:
    """Set one key in the user or project file, after checking the value is valid.

    How: read only the target file, put the value in, and validate that file merged over the
    defaults (so the value is checked against its type and coerced: "8192" becomes 8192),
    then write the file back with just its own keys. Writing the merged config instead
    would copy every default and every user setting into the project file.
    """
    if key == "base_url" and scope == "project":
        raise ConfigError("base_url can be set only in your user file (--user)")
    path = _target(cwd, scope)
    data = _read(path)
    _merge(data, _nest(key, value))
    try:
        checked = Config.model_validate(_merge(Config().model_dump(), copy.deepcopy(data)))
    except ValidationError as e:
        raise ConfigError(_explain(e)) from None
    coerced: Any = checked.model_dump()
    for part in key.split("."):
        coerced = coerced[part]
    _merge(data, _nest(key, coerced))
    _write(path, data)
    return path


def unset_value(cwd: Path, key: str, scope: Scope) -> bool:
    """Remove one key from one file; False if it wasn't set there."""
    path = _target(cwd, scope)
    data = _read(path)
    *parents, leaf = key.split(".")
    node = data
    for part in parents:
        node = node.get(part, {})
    if leaf not in node:
        return False
    del node[leaf]
    _write(path, data)
    return True


def _target(cwd: Path, scope: Scope) -> Path:
    if scope == "user":
        return user_path()
    return project_path(cwd) or cwd / ".rig" / "config.json"


def _write(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n")


# --- small dict helpers ---


def _nest(key: str, value: Any) -> dict[str, Any]:
    """'budget.max_usd', 2 -> {'budget': {'max_usd': 2}}."""
    for part in reversed(key.split(".")):
        value = {part: value}
    assert isinstance(value, dict)
    return value


def _merge(base: dict[str, Any], over: Mapping[str, Any]) -> dict[str, Any]:
    """Deep-merge `over` into `base` in place: nested sections merge key by key."""
    for k, v in over.items():
        if isinstance(v, Mapping) and isinstance(base.get(k), dict):
            _merge(base[k], v)
        else:
            base[k] = copy.deepcopy(v)
    return base


def leaves(data: Mapping[str, Any], prefix: str = "") -> list[str]:
    out = []
    for k, v in data.items():
        key = f"{prefix}{k}"
        out += leaves(v, key + ".") if isinstance(v, Mapping) else [key]
    return out


def _explain(e: ValidationError) -> str:
    return "; ".join(
        f"{'.'.join(str(p) for p in err['loc'])}: {err['msg'].lower()}" for err in e.errors()
    )
