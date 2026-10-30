import json
import logging

from ..sandbox.workspace import Workspace
from . import get_tool_names, get_tools, run_tool

logging.basicConfig(level=logging.DEBUG)


if __name__ == "__main__":
    print(f"Tools: {get_tool_names()}")
    for idx, tool in enumerate(get_tools()):
        print(f"\n\n{idx + 1}. {tool.name}: \n\t\t {json.dumps(tool.schema_for_llm(), indent=2)}")

    print(run_tool(Workspace.get_dummy_instance(), "bash", command="ls"))
