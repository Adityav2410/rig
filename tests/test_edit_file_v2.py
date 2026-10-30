"""edit_file v2: line endings survive, a list of edits is all or nothing, and misses say why."""

from pathlib import Path

import pytest

from rig import Workspace
from rig.core.exceptions import ToolError
from rig.tools import run_tool
from rig.tools.fs import edit_file


@pytest.fixture
def ws(tmp_path: Path) -> Workspace:
    return Workspace(root=tmp_path, name="test", run_id="test", use_sandbox=False)


def _edit(old: str, new: str) -> dict[str, str]:
    return {"old_text": old, "new_text": new}


def test_a_crlf_file_keeps_its_crlf(ws: Workspace) -> None:
    f = ws.root / "win.py"
    f.write_bytes(b"def run():\r\n    pass\r\n\r\nrun()\r\n")

    # old_text is written with plain newlines, as a model writes it
    edit_file(ws, "win.py", [_edit("def run():\n    pass", "def run():\n    serve()")])

    assert f.read_bytes() == b"def run():\r\n    serve()\r\n\r\nrun()\r\n"


def test_when_the_second_edit_misses_the_file_is_untouched(ws: Workspace) -> None:
    f = ws.root / "app.py"
    f.write_bytes(b"DEBUG = True\nPORT = 8000\n")
    before = f.read_bytes()

    with pytest.raises(ToolError, match="edit 2 of 2"):
        edit_file(
            ws, "app.py", [_edit("DEBUG = True", "DEBUG = False"), _edit("HOST = x", "HOST = y")]
        )

    assert f.read_bytes() == before


def test_a_near_miss_names_the_closest_line(ws: Workspace) -> None:
    (ws.root / "app.py").write_text("import os\n\ndef serve(port):\n    return port\n")

    with pytest.raises(ToolError) as err:
        edit_file(ws, "app.py", [_edit("def serve(port=8000):", "def serve(port=9000):")])

    assert "line 3: def serve(port):" in str(err.value)


def test_several_edits_apply_together(ws: Workspace) -> None:
    f = ws.root / "app.py"
    f.write_text("A = 1\nB = 2\nC = 3\n")
    edit_file(ws, "app.py", [_edit("C = 3", "C = 30"), _edit("A = 1", "A = 10")])  # any order
    assert f.read_text() == "A = 10\nB = 2\nC = 30\n"


def test_edits_match_the_original_not_each_others_output(ws: Workspace) -> None:
    f = ws.root / "app.py"
    f.write_text("x = 1\n")
    with pytest.raises(ToolError, match="edit 2 of 2: old_text not found"):
        edit_file(ws, "app.py", [_edit("x = 1", "y = 1"), _edit("y = 1", "z = 1")])
    assert f.read_text() == "x = 1\n"


@pytest.mark.parametrize(
    ("edits", "message"),
    [
        ([_edit("x", "y")], "matches 2 times"),
        ([_edit("x = 1\nx", "a"), _edit("1\nx = 2", "b")], "overlap"),
        ([_edit("x = 1", "x = 1")], "change nothing"),
        ([], "non-empty list"),
    ],
)
def test_ambiguous_overlapping_and_empty_edits_are_refused(
    ws: Workspace, edits: list[dict[str, str]], message: str
) -> None:
    (ws.root / "app.py").write_text("x = 1\nx = 2\n")
    with pytest.raises(ToolError, match=message):
        edit_file(ws, "app.py", edits)


def test_a_utf8_bom_survives(ws: Workspace) -> None:
    f = ws.root / "bom.txt"
    f.write_bytes("﻿hello\n".encode())
    edit_file(ws, "bom.txt", [_edit("hello", "bye")])
    assert f.read_bytes() == "﻿bye\n".encode()


def test_creating_a_file_and_refusing_to_overwrite_one(ws: Workspace) -> None:
    assert edit_file(ws, "new/notes.md", [_edit("", "first\n")]) == "Created new/notes.md"
    assert (ws.root / "new/notes.md").read_text() == "first\n"
    with pytest.raises(ToolError, match="already exists"):
        edit_file(ws, "new/notes.md", [_edit("", "again\n")])


def test_through_the_dispatcher_a_miss_is_an_error_result_for_the_model(ws: Workspace) -> None:
    (ws.root / "app.py").write_text("x = 1\n")
    out, is_error = run_tool(ws, "edit_file", path="app.py", edits=[_edit("x = 2", "x = 3")])
    assert is_error and "old_text not found" in out
