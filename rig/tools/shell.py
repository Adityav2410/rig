import platform
import subprocess

from ..exceptions import ToolError
from ..logging import get_logger
from ..workspace import Workspace
from . import tool
from .schema import ToolInputSchema, ToolPropertySchema, ToolPropertyType

logger = get_logger()


@tool(
    name="bash",
    description="Run a shell command at the repository root — the escape hatch for anything "
    "the other tools don't cover, chiefly running tests (e.g. `python -m pytest -q`). Prefer "
    "`list_files`/`read_file`/`search` for exploring code and `edit_file` for changing it; use "
    "`bash` to execute, not to browse. The result is the command's stdout, followed by stderr "
    "under a `[stderr]` marker if any was produced, followed by `[exit code N]` — a nonzero "
    "exit code means the command failed, not that the tool call failed. A command that runs "
    "longer than `timeout_s` is killed and the output is marked `[killed: exceeded <n>s]` "
    "instead of hanging.",
    input_schema=ToolInputSchema(
        properties={
            "command": ToolPropertySchema(
                type=ToolPropertyType.STRING,
                description="Shell command to run via `bash -c`, from the repository root.",
            ),
            "timeout_s": ToolPropertySchema(
                type=ToolPropertyType.NUMBER,
                description="Seconds to let the command run before it is killed. Defaults to 120.",
            ),
        },
        required=["command"],
    ),
    input_examples=[{"command": "ls <folder>"}],
)
def bash(ws: Workspace, command: str, timeout_s: int = 120) -> str:
    argv = ws.exec_prefix[:]
    if platform.system() == "Linux":
        # timeout is only supported on linux/not on mac.
        argv += ["timeout", "-k", str(timeout_s)]
    argv += ["bash", "-c", command]
    p = None
    try:
        logger.debug(f"Executing bash command: {argv}")
        p = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            errors="replace",
            timeout=timeout_s + 20,
            cwd=ws.root,
        )
    except subprocess.TimeoutExpired as err:
        raise ToolError("bash", f"No return within {timeout_s + 20}s") from err
    out = p.stdout + (f"\n[stderr]\n{p.stderr}" if p.stderr else "")
    if p.returncode in (124, 137):
        out += f"\n[killed: exceeded {timeout_s}s]"
    return f"{out}\n[exit code {p.returncode}]"
