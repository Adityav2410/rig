# rig

[![CI](https://github.com/Adityav2410/rig/actions/workflows/ci.yml/badge.svg)](https://github.com/Adityav2410/rig/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.14](https://img.shields.io/badge/python-3.14-blue.svg)](https://www.python.org/)

> **About this project.** In Q4 2026 I (Aditya) set out to learn how agents really work by building them: first a coding agent, then general-purpose tools in the spirit of Perplexity and Muse. To guide that, I wrote a study plan with Claude's help, [*Agents from First Principles*](https://ai.labs-nature.com/study-plan/). This repository is my implementation of that plan, built week by week as part of the learning process, so it follows the plan roughly rather than exactly.

**rig** is a coding agent built from scratch, one primitive at a time, on the raw Anthropic Messages API: no agent framework, no hidden loop. Every piece (the request loop, the tools, the sandbox, the budget, the trace, the eval harness) is small enough to read in one sitting.

Each week of the 18-week plan is preserved as a branch (`week1`, `week2`, ...), so you can see exactly what the code looked like at each stage.

> **Status:** early and evolving. `main` tracks the latest week; APIs change from week to week by design.

## What's in it

| Piece | Where | What it does |
|---|---|---|
| Agent loop | `rig/agent.py` | Sends the conversation, runs the tools the model asks for, appends the results, and repeats until the model stops |
| API client | `rig/llm.py` | One function, `call(request)`, with retries and backoff; the only network code |
| Tools | `rig/tools/` | `list_files`, `read_file`, `edit_file`, `search`, and `bash`, each registered with a JSON schema |
| Sandbox | `rig/workspace.py`, `rig/docker/` | Runs tool commands inside a throwaway Docker container; the API key never enters it |
| Budget | `rig/budget.py` | Hard caps on steps, tokens, dollars, and wall-clock time |
| Trace | `rig/trace.py` | Append-only JSONL log of every request, response, and tool call |
| Evals | `evals/` | A task ladder run against a pinned [click](https://github.com/pallets/click) checkout, with automatic grading |

## Quickstart

Requirements: Python 3.14, [uv](https://docs.astral.sh/uv/), Docker, and an [Anthropic API key](https://platform.claude.com/).

```bash
git clone https://github.com/Adityav2410/rig.git
cd rig
uv sync
export ANTHROPIC_API_KEY=...            # read from the environment only, never logged

# One-time: build the sandbox image (rig-sandbox:v0.1)
uv run python scripts/prepare_sandbox_image.py

# The target repository the agent works on
git clone https://github.com/pallets/click workspaces/click
git -C workspaces/click checkout 8.5.0
```

Run the agent once:

```bash
uv run python scripts/run_agent.py
```

Or drive it from Python:

```python
import uuid
from pathlib import Path

from rig import Agent, Budget, Trace, Workspace

run_id = str(uuid.uuid4())
budget = Budget(
    max_steps=30,
    max_input_tokens=500_000,
    max_output_tokens=50_000,
    max_usd=1.0,
    max_wall_clock_s=600,
)

with Workspace(root=Path("workspaces/click"), name="click", run_id=run_id, use_sandbox=True) as ws:
    result = Agent(
        ws=ws,
        task="Where is IntRange validated?",
        model="claude-haiku-5-5",
        budget=budget,
        trace=Trace.get_dummy_trace(run_id=run_id),
    ).run()

print(result.status, result.final_response)
```

## Evals

```bash
uv run python evals/run_evals.py --runs 3            # the whole ladder, three runs per task
uv run python evals/run_evals.py --task-id T04       # a single task
uv run python scripts/parse_trace.py traces/<run>.jsonl
```

Tasks live in `evals/tasks/`, seeded bugs in `evals/seeds/`, and hidden grader tests in `evals/hidden/`. Results are appended to `evals/results.jsonl`. Eval runs call the API and cost money.

## Development

```bash
make help        # list commands
make test        # pytest (needs workspaces/click; no API key, no Docker)
make lint        # ruff check
make fmt-check   # ruff format --check
make typecheck   # mypy --strict
make fix         # auto-fix lint and format
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for how changes are organised around the weekly branches.

## Repository layout

```
rig/            the agent package
  tools/        tool implementations and the registry
  docker/       sandbox Dockerfile
  costs/        per-model pricing
  prompts/      system prompt
evals/          task ladder, seeds, hidden tests, runner
scripts/        entry points: run the agent, build the sandbox, read a trace
tests/          unit tests
study-plan.md   the course plan this repo follows
AGENTS.md       instructions for AI coding assistants working in this repo
```

## License

[MIT](LICENSE)
