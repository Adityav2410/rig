import subprocess

from ..core.exceptions import ToolError
from ..sandbox.workspace import Workspace
from . import tool
from .fs import resolve
from .schema import ToolInputSchema, ToolPropertySchema, ToolPropertyType

MAX_MATCHES = 200


@tool(
    name="search",
    description="Search tracked files under `path` for `pattern` using ripgrep — the fastest "
    "way to find where something is defined or used, before reading or editing it. Returns "
    f"one `path:line:text` line per match, capped at {MAX_MATCHES} matches; narrow `pattern` "
    "or `glob` if you hit the cap. `pattern` is a regex by default — pass `fixed=true` to match it "
    "as a literal string instead, which is safer for text containing regex metacharacters like "
    "`.`, `(`, or `*`. An invalid regex is reported as an error; zero matches is not.",
    input_schema=ToolInputSchema(
        properties={
            "pattern": ToolPropertySchema(
                type=ToolPropertyType.STRING,
                description="Regex pattern to search for (literal string if `fixed` is true).",
            ),
            "path": ToolPropertySchema(
                type=ToolPropertyType.STRING,
                description="Directory to search under, relative to the workspace root. "
                'Defaults to "." (the repository root).',
            ),
            "glob": ToolPropertySchema(
                type=ToolPropertyType.STRING,
                description="Optional glob to restrict matched filenames, e.g. '*.py'.",
            ),
            "fixed": ToolPropertySchema(
                type=ToolPropertyType.BOOLEAN,
                description="Treat `pattern` as a literal string instead of a regex. "
                "Defaults to false.",
            ),
        },
        required=["pattern"],
    ),
    input_examples=[
        {"pattern": "def parse_args"},
        {"pattern": "TODO", "glob": "*.py", "fixed": True},
    ],
)
def search(
    ws: Workspace, pattern: str, path: str = ".", glob: str | None = None, fixed: bool = False
) -> str:
    resolve(ws, path)  # raises PathEscapesWorkspace if path escapes the workspace

    argv = ws.exec_prefix + [
        "rg",
        "--line-number",
        "--with-filename",
        "--no-heading",
        "--color=never",
    ]
    if fixed:
        argv.append("--fixed-strings")
    if glob:
        argv += ["--glob", glob]
    argv += [pattern, path]

    out = subprocess.run(argv, cwd=ws.root, capture_output=True, text=True)
    # rg exit codes: 0 = matches found, 1 = no matches (not an error), 2+ = real error
    # (bad regex, bad path, ...) — only the latter should surface as a tool error.
    if out.returncode == 1:
        return "No matches found."
    if out.returncode != 0:
        raise ToolError("search", f"search failed: {out.stderr.strip()}")

    lines = out.stdout.splitlines()
    if len(lines) > MAX_MATCHES:
        shown = lines[:MAX_MATCHES]
        return "\n".join(shown) + (
            f"\n\n[... {len(lines) - MAX_MATCHES} more matches omitted; "
            "narrow `pattern` or `glob` ...]"
        )
    return "\n".join(lines)
