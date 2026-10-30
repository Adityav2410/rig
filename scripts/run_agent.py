# from rig import A
import uuid

from rig import Agent, Budget, Trace, Workspace

# TASK = """
# Do not modify any files.

# Trace how the value in `mycli --count 5` reaches the command function, for an option declared as:

#     @click.option("--count", type=click.IntRange(0, 10))

# List, in call order, each function or method that handles the value from the raw argv string to
# the int passed to the command callback. For each, give file:line and one sentence on what it does
# to the value. Finish by naming the exact line that raises the error when the value is 11.
# """

TASK = (
    "List files in current working directory with one file in each "
    "line with line number sorted by file size with biggest size of file at top."
)

if __name__ == "__main__":
    import logging
    from pathlib import Path

    logging.basicConfig(level="INFO")
    logging.getLogger("rig").setLevel("DEBUG")
    # logging.getLogger("__main__").setLevel("DEBUG")
    # logging.getLogger("rig.tools.shell").setLevel("DEBUG")
    budget = Budget.get_dummy_budget()
    budget.max_steps = 100
    run_id = str(uuid.uuid4())
    with Workspace(
        root=Path.cwd() / "workspaces" / "click", name="click", run_id=run_id, use_sandbox=True
    ) as ws:
        agent = Agent(
            ws,
            model="claude-haiku-5-5",
            budget=budget,
            trace=Trace.get_dummy_trace(run_id=run_id),
            max_tokens=250,
        )
        result = agent.run(TASK)
        # result = agent.run("What is the highest and lowest temperature today in Santa Clara")

    if result.status == "success":
        print(f"Agent ran successfully. Output: {result.final_response}")
    else:
        print(f"Error running agent. status={result.status}. response: {result.final_response}")
