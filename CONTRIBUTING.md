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

## Comments and docstrings

rig is read to be learned from, so where the logic is tricky, a function's docstring explains **how it achieves its result**, not just what it returns. Where the code is already easy to follow, more prose only adds noise.

**First decide whether a function needs a docstring at all:**
- **None:** functions whose code reads as fast as a sentence would. Getters, defaults, one-line wrappers, and short validation or lookups such as `_resolve_provider` and `get_provider`. If one line in them hides a reason, give that line an inline comment.
- **One line:** a public function whose name and signature don't quite say what it does.
- **The full treatment below:** logic a reader couldn't reconstruct quickly from the code. That means multi-step algorithms, shared state or concurrency, ordering rules, and wire-format quirks.

**The full treatment:**
- **First line: what it does**, in one sentence.
- **Why, when it isn't obvious:** the constraint that forces the design (an API rule, a race, a failure it prevents). "Every API rejects a tool call without a result" is why `_close_orphans` exists.
- **How: the steps of the algorithm**, numbered when there is more than one, naming the variables the code uses (`answered`, `pending`, `flush()`), so the prose and the code line up.
- **A small before → after example** when the transformation is easier to see than to describe.
- **Non-obvious choices and their alternatives:** why a lock is needed on top of `setdefault`, why a result list is returned instead of mutating the input.
- **Inline comments say why a line exists**, never what it does: `# map() keeps submission order`, not `# map over calls`.

Being private doesn't exempt a helper; helpers are often where the tricky logic lives. Being private doesn't earn a helper a docstring either: judge each one by its logic. `rig/runtime.py` (`run_tools`, `_close_orphans`) and `rig/providers/anthropic.py` are the reference examples.

## Reporting a bug

Open an issue with the command you ran, what you expected, and what happened. If the agent misbehaved, attach the trace (`traces/<run>.jsonl`) and remove anything private from it first.

## Changing the course

The study plan lives in `course/`. Edit the week pages in `course/content/w*.md`, then run `make course` to regenerate `course/index.html` and `course/templates/study-plan.md`; never edit those two by hand. `course/GUIDELINES.md` describes the page format and the rules that keep readers' checklist progress intact.
