from pathlib import Path

import pytest

from rig.core.exceptions import PathEscapesWorkspace
from rig.sandbox.workspace import Workspace
from rig.tools.fs import resolve


def _ws(tmp_path: Path) -> Workspace:
    return Workspace(root=tmp_path, name="test", run_id="test", use_sandbox=False)


def test_resolve_allows_path_inside_workspace(tmp_path: Path) -> None:
    ws = _ws(tmp_path)
    (tmp_path / "a.txt").write_text("hi")
    assert resolve(ws, "a.txt") == tmp_path / "a.txt"


def test_resolve_rejects_path_escaping_workspace(tmp_path: Path) -> None:
    ws = _ws(tmp_path)
    with pytest.raises(PathEscapesWorkspace):
        resolve(ws, "../outside.txt")
