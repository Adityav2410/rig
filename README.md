# rig

[![CI](https://github.com/Adityav2410/rig/actions/workflows/ci.yml/badge.svg)](https://github.com/Adityav2410/rig/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.14](https://img.shields.io/badge/python-3.14-blue.svg)](https://www.python.org/)

> **About this project.** In Q4 2026 I (Aditya) set out to learn how agents really work by building them: first a coding agent, then general-purpose tools in the spirit of Perplexity and Muse. To guide that, I wrote a study plan with Claude's help, [*Agents from First Principles*](https://ai.labs-nature.com/study-plan/). This repository is my implementation of that plan, built week by week as part of the learning process, so it follows the plan roughly rather than exactly.

**rig** is a provider-agnostic coding agent built from scratch, one primitive at a time, directly on model APIs: no agent framework, no hidden loop. Every piece (the request loop, the tools, the sandbox, the budget, the trace, the eval harness) is small enough to read in one sitting.

Each week of the 18-week plan is preserved as a branch (`week1`, `week2`, ...), so you can see exactly what the code looked like at each stage.

> **Status:** early and evolving. `main` tracks the latest week; APIs change from week to week by design.

## Model providers

rig is meant to work with any capable model, not one vendor. From Week 2 it talks to models through one small `Provider` interface, so the agent loop never depends on a vendor's wire format.

| Provider | API | Status |
|---|---|---|
| Anthropic | Messages API | Supported |
| OpenAI | Chat Completions | Planned (Week 2) |
| OpenRouter and other OpenAI-compatible endpoints (vLLM, Ollama, ...) | Chat Completions | Planned (Week 2) |

## What's in it

| Piece | Where | What it does |
|---|---|---|
| Providers | `rig/providers/` | rig's own message and event types, and one adapter per model API; the only code that talks to the network |
| Agent | `rig/core/` | The event loop (`runtime.py`), the stateful `Agent`, sessions, layered config, budget and trace |
| Tools | `rig/tools/` | `list_files`, `read_file`, `edit_file`, `search`, and `bash`, each registered with a JSON schema |
| Sandbox | `rig/sandbox/` | The workspace, an optional throwaway Docker container for tool commands (the API key never enters it), and repo snapshots |
| CLI | `rig/cli/` | The `rig` command: `run`, `resume`, `fork`, `show` and `config` |
| Evals | `evals/` | A task ladder run against a pinned [click](https://github.com/pallets/click) checkout, with automatic grading |

## Quickstart

Requirements: Python 3.14, [uv](https://docs.astral.sh/uv/), Docker, and an API key for a supported provider (today: an [Anthropic API key](https://platform.claude.com/)).

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

Run the agent:

```bash
uv run rig run --repo workspaces/click --task "Where is IntRange validated?"   # prints a session id
uv run rig resume <session> --task "Now add a test"     # continue that conversation
uv run rig show <session>                               # list its entries
uv run rig fork <session> <entry_id> --task "..."       # branch from an earlier entry
```

While a run streams, Ctrl-C stops it at the next safe point (twice quits), a line starting
with `/steer` redirects the current task, and any other line queues the next one. `rig resume`
with no `--task` finishes a run that was interrupted. Sessions live in `.rig/sessions/`, traces
in `.rig/traces/`. The workspace is the current directory unless you pass `--repo`, and tools
run on the host unless you pass `--use-sandbox` (Docker). `./rig.sh …` does the same without
typing `uv run`, from any directory.

Settings come in layers, lowest first: built-in defaults, your user file
(`~/.config/rig/config.json`), the project's `.rig/config.json`, `RIG_*` environment variables
(`RIG_MODEL`, `RIG_BUDGET__MAX_USD`), then command-line flags:

```bash
uv run rig config set model claude-sonnet-5-5          # this project (.rig/config.json)
uv run rig config set budget.max_usd 2 --user          # your user file, every project
uv run rig config list --show-origin                   # every value and where it came from
```

API keys never go in a config file, and `base_url` is read only from your user file.

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
    agent = Agent(
        ws,
        model="claude-haiku-5-5",
        budget=budget,
        trace=Trace.get_dummy_trace(run_id=run_id),  # optional: omit it to record nothing
    )
    result = agent.run("Where is IntRange validated?")

print(result.status, result.final_response)
```

## Evals

```bash
uv run python evals/run_evals.py --runs 3            # the whole ladder, three runs per task
uv run python evals/run_evals.py --task-id T04       # a single task
uv run python scripts/parse_trace.py runs/<run_id>/trace.jsonl   # an eval run; no argument: the newest .rig/traces/ file
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
make course      # rebuild the course site and study-plan.md from course/content/
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
course/         the study plan: week pages in content/, the site generator in tools/
study-plan.md   the whole plan as one file (a link to course/templates/, generated)
AGENTS.md       instructions for AI coding assistants working in this repo (also generated)
```

## License

[MIT](LICENSE)
