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


def test_a_workspace_given_a_relative_root_still_accepts_paths_inside_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "repo" / "src").mkdir(parents=True)
    monkeypatch.chdir(tmp_path)
    ws = Workspace(root=Path("repo"), name="repo", run_id="t", use_sandbox=False)
    assert resolve(ws, "src") == tmp_path.resolve() / "repo" / "src"
