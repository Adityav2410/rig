import subprocess
from pathlib import Path

from ..exceptions import PathEscapesWorkspace, ToolError
from ..workspace import Workspace
from . import tool
from .schema import ToolInputSchema, ToolPropertySchema, ToolPropertyType

MAX_FILES = 500
MAX_LINES = 400


def resolve(ws: Workspace, rel: str) -> Path:
    """Resolve the path relative to a workspace."""
    p = (ws.root / rel).resolve()
    if not p.is_relative_to(ws.root):  # in case of symlinks this can break
        raise PathEscapesWorkspace(
            f"{rel}: outside the repository", status="path.escapes_workspace"
        )
    return p


@tool(
    name="edit_file",
    description="Make a targeted edit to a file by replacing exactly one occurrence of "
    "`old_text` with `new_text`. Use this instead of `bash` for any edit to tracked source "
    "code. `old_text` must match the file byte-for-byte, including indentation and "
    "surrounding whitespace, and must occur exactly once in the file; if it matches zero or "
    "more than one time, the edit is rejected and nothing is changed — read the file first "
    "and include enough surrounding lines to make the match unique. To create a brand-new "
    "file, pass an empty `old_text`; this fails if the file already exists.",
    input_schema=ToolInputSchema(
        properties={
            "path": ToolPropertySchema(
                type=ToolPropertyType.STRING, description="Path of file relative to workspace."
            ),
            "old_text": ToolPropertySchema(
                type=ToolPropertyType.STRING,
                description="Old text which should be overwritten by new text. "
                "If a new file has to be created, then this can be empty string.",
            ),
            "new_text": ToolPropertySchema(
                type=ToolPropertyType.STRING, description="New text which would replace old text."
            ),
        },
        required=["path", "old_text", "new_text"],
    ),
    input_examples=[
        {"path": "test.txt", "old_text": "", "new_text": "Creating new file"},
        {
            "path": "test.txt",
            "old_text": "old text which will be replaced.",
            "new_text": "new text which will replace this",
        },
    ],
)
def edit_file(ws: Workspace, path: str, old_text: str, new_text: str) -> str:
    p = resolve(ws, path)
    if old_text == "":
        if p.exists():
            raise ToolError(
                "edit_file", f"File: {p} already exists. Provide old_text if you want to edit file."
            )
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(new_text)
        return f"Created {path}"

    src = p.read_text()
    n = src.count(old_text)
    if n != 1:
        raise ToolError(
            "edit_file", f"old_text matched {n} times in {path}, it must match exactly once"
        )
    p.write_text(src.replace(old_text, new_text))
    return f"Edited {path}"


@tool(
    name="list_files",
    description="List files tracked by git under a directory, relative to the workspace root. "
    "Use this to see what exists in the repository before reading or searching it. Equivalent "
    "to `git ls-files <path>`: build output, caches, and anything git-ignored are excluded "
    "automatically, but a file that hasn't been committed yet will not appear. Returns one "
    "path per line, capped at 500 entries — if you hit the cap, call again with a narrower "
    "`path` to see the rest.",
    input_schema=ToolInputSchema(
        properties={
            "path": ToolPropertySchema(
                type=ToolPropertyType.STRING,
                description="Directory to list, relative to the workspace root. "
                'Defaults to "." (the repository root).',
            ),
        },
        required=[],
    ),
    input_examples=[{"path": "."}, {"path": "src/click"}],
)
def list_files(ws: Workspace, path: str = ".") -> str:
    p = resolve(ws, path)
    if not p.is_dir():
        raise ToolError("list_files", f"{path}: not a directory")

    out = subprocess.run(["git", "ls-files", path], cwd=ws.root, capture_output=True, text=True)
    if out.returncode != 0:
        raise ToolError("list_files", f"git ls-files failed: {out.stderr.strip()}")

    files = out.stdout.splitlines()
    if not files:
        return f"No tracked files under {path!r}."
    if len(files) > MAX_FILES:
        shown = files[:MAX_FILES]
        return "\n".join(shown) + (
            f"\n\n[... {len(files) - MAX_FILES} more files omitted; narrow `path` to see them ...]"
        )
    return "\n".join(files)


@tool(
    name="read_file",
    description="Read a text file's contents with 1-indexed line numbers prefixed to each "
    "line, so you can cite exact locations and target `edit_file` calls precisely. Reads up "
    "to `limit` lines starting at `offset` (both 1-indexed); if the file is longer than that, "
    "the output ends with a hint giving the `offset` to pass to continue reading. Fails if "
    "`path` is not a file, is not valid UTF-8 text (e.g. a binary file), or if `offset` is "
    "past the end of the file.",
    input_schema=ToolInputSchema(
        properties={
            "path": ToolPropertySchema(
                type=ToolPropertyType.STRING, description="Path of file relative to workspace."
            ),
            "offset": ToolPropertySchema(
                type=ToolPropertyType.NUMBER,
                description="1-indexed line number to start reading from. Defaults to 1.",
            ),
            "limit": ToolPropertySchema(
                type=ToolPropertyType.NUMBER,
                description=f"Maximum number of lines to read. Defaults to {MAX_LINES}.",
            ),
        },
        required=["path"],
    ),
    input_examples=[
        {"path": "src/click/core.py"},
        {"path": "src/click/core.py", "offset": 200, "limit": 100},
    ],
)
def read_file(ws: Workspace, path: str, offset: int = 1, limit: int = MAX_LINES) -> str:
    p = resolve(ws, path)
    if not p.is_file():
        raise ToolError("read_file", f"{path}: not a file")
    if offset < 1:
        raise ToolError("read_file", "offset must be >= 1")

    try:
        lines = p.read_text().splitlines()
    except UnicodeDecodeError as err:
        raise ToolError("read_file", f"{path}: not a text file") from err

    total = len(lines)
    start = offset - 1
    if start >= total:
        return f"{path} has {total} lines; offset {offset} is past the end of the file."

    end = min(start + limit, total)
    numbered = "\n".join(f"{i + 1:6d}\t{lines[i]}" for i in range(start, end))
    if end < total:
        numbered += f"\n\n[... {total - end} more lines; call again with offset={end + 1} ...]"
    return numbered
