# Contributing

Thanks for your interest in rig. It's a teaching project, so readability counts for more than features: a change should make the code easier to follow, not just more capable.

## Branches

- `main` is the latest week of the course and where new work lands.
- `weekN` branches are frozen snapshots of the code at the end of week N. They only change to fix a real bug, so the history a learner reads stays accurate.

## Before you open a pull request

```bash
uv sync
make lint fmt-check typecheck test
```

All four must pass; CI runs the same checks. The snapshot tests need the click checkout from the README's quickstart (`workspaces/click` at `8.5.0`). Beyond that, unit tests must not need the network, an API key, or Docker; anything that calls the model belongs in `evals/`.

## Reporting a bug

Open an issue with the command you ran, what you expected, and what happened. If the agent misbehaved, attach the trace (`traces/<run>.jsonl`) and remove anything private from it first.

## Changing the course

The study plan lives in `course/`. Edit the week pages in `course/content/w*.md`, then run `make course` to regenerate `course/index.html` and `course/templates/study-plan.md`; never edit those two by hand. `course/GUIDELINES.md` describes the page format and the rules that keep readers' checklist progress intact.
