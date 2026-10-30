"""Keep every test away from the developer's own settings."""

import os
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def isolated_config(
    tmp_path_factory: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch
) -> Path:
    """A fresh, empty user config directory, and no RIG_* variables from the real shell."""
    home = tmp_path_factory.mktemp("config-home")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(home))
    for name in [n for n in os.environ if n.startswith("RIG_")]:
        monkeypatch.delenv(name)
    return home
