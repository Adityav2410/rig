"""edit_file v2: line endings survive, matches are exact and unique, and misses say why."""

from pathlib import Path

import pytest

from rig import Workspace
from rig.core.exceptions import ToolError
from rig.tools import run_tool
from rig.tools.fs import edit_file


@pytest.fixture
def ws(tmp_path: Path) -> Workspace:
    return Workspace(root=tmp_path, name="test", run_id="test", use_sandbox=False)


def test_a_crlf_file_keeps_its_crlf(ws: Workspace) -> None:
    f = ws.root / "win.py"
    f.write_bytes(b"def run():\r\n    pass\r\n\r\nrun()\r\n")

    # old_text is written with plain newlines, as a model writes it
    edit_file(ws, "win.py", "def run():\n    pass", "def run():\n    serve()")

    assert f.read_bytes() == b"def run():\r\n    serve()\r\n\r\nrun()\r\n"


def test_a_near_miss_names_the_closest_line_and_leaves_the_file_alone(ws: Workspace) -> None:
    f = ws.root / "app.py"
    f.write_text("import os\n\ndef serve(port):\n    return port\n")
    before = f.read_bytes()

    with pytest.raises(ToolError) as err:
        edit_file(ws, "app.py", "def serve(port=8000):", "def serve(port=9000):")

    assert "line 3: def serve(port):" in str(err.value)
    assert f.read_bytes() == before


@pytest.mark.parametrize(
    ("old", "new", "message"),
    [("x", "y", "matches 2 times.*set replace_all"), ("x = 1", "x = 1", "changes nothing")],
)
def test_ambiguous_and_no_op_edits_are_refused(
    ws: Workspace, old: str, new: str, message: str
) -> None:
    (ws.root / "app.py").write_text("x = 1\nx = 2\n")
    with pytest.raises(ToolError, match=message):
        edit_file(ws, "app.py", old, new)


def test_replace_all_changes_every_occurrence(ws: Workspace) -> None:
    f = ws.root / "app.py"
    f.write_text("count = 0\ncount += 1\nprint(count)\n")
    assert "3 replacements" in edit_file(ws, "app.py", "count", "total", replace_all=True)
    assert f.read_text() == "total = 0\ntotal += 1\nprint(total)\n"


def test_an_edit_that_already_landed_says_so(ws: Workspace) -> None:
    (ws.root / "app.py").write_text("def run():\n    serve()\n")
    with pytest.raises(ToolError, match="may already be applied"):
        edit_file(ws, "app.py", "def run():\n    pass", "def run():\n    serve()")


def test_a_utf8_bom_survives(ws: Workspace) -> None:
    f = ws.root / "bom.txt"
    f.write_bytes("﻿hello\n".encode())
    edit_file(ws, "bom.txt", "hello", "bye")
    assert f.read_bytes() == "﻿bye\n".encode()


def test_creating_a_file_and_refusing_to_overwrite_one(ws: Workspace) -> None:
    assert edit_file(ws, "new/notes.md", "", "first\n") == "Created new/notes.md"
    assert (ws.root / "new/notes.md").read_text() == "first\n"
    with pytest.raises(ToolError, match="already exists"):
        edit_file(ws, "new/notes.md", "", "again\n")


def test_through_the_dispatcher_a_miss_is_an_error_result_for_the_model(ws: Workspace) -> None:
    (ws.root / "app.py").write_text("x = 1\n")
    out, is_error = run_tool(ws, "edit_file", path="app.py", old_text="x = 2", new_text="x = 3")
    assert is_error and "old_text not found" in out
