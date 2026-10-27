# Next steps

Snapshot as of 2026-10-16. Finish Week 1 before starting Week 2 — a week
finished out of its calendar slot still counts; skipping ahead doesn't.

## Where I actually am (Week 1 day-by-day)

| Day | Target | Status |
|---|---|---|
| Mon | wire-format walkthrough, `notes/wire/*.json` | Not done — no `notes/` dir |
| Tue | `llm.py`, `trace.py`, `budget.py`, `loop.py`, `list_files`/`read_file`, first prompt graded | **Done** — verified working via `scripts/run_agent.py` (correct file:line trace through click's `IntRange`) |
| Wed | Docker sandbox, `bash`, `search` | **Not done** — no `docker/` dir; `bash`/`search` exist but run on host, not in a container |
| Thu | `edit_file`, real `budget.py`, `max_tokens` handling | Partially done — `edit_file` exists, budget enforcement exists but has a bug (below); no `max_tokens`/truncation handling yet |
| Fri | 4 experiments | Not done |
| Sat | `evals/run_evals.py`, 12-task ladder x3 | Not done — no `evals/` dir |
| Sun | failure taxonomy, checkpoint | Not attempted |

Ahead of schedule: parallel tool execution with ordered results in
`agent.py` (`ThreadPoolExecutor`) — that's actually a Week 2 Tuesday
concept.

## Bugs to fix before building further (found by code review, not yet fixed)

### 1. `rig/llm.py` retry logic — three separate issues

- `httpx.TransportError` (timeout, connection reset) falls into a branch
  that does `raise LLMError(status_code=response.status_code, ...)` —
  but `response` was never assigned on that path, so it's an
  `UnboundLocalError` instead of a retry.
- The retryable-status branch `continue`s immediately, skipping backoff
  entirely. The `retry-after` header is parsed but never used.
- `_should_retry()` requires **both** `x-should-retry == "true"` **and**
  the status code being in the retryable set. Intent (per the plan's
  retry policy) is "retry unless explicitly told not to" — if Anthropic
  doesn't send that header on a given 503, it won't retry at all.

Revisit Day 8's exercise ("break it on purpose, twice") — it's designed
to surface exactly this.

### 2. `rig/budget.py` + `rig/agent.py` — no structured budget-exceeded status

`BudgetExceededError` carries only a free-text message. `agent.py`'s
`run()` catches it in the generic `except Exception` branch, so the
result is `status="error"` instead of `status="budget:steps"` /
`status="budget:usd"` etc. The Thursday checkpoint item ("an
artificially tiny budget ends the run with status `budget:*`") won't
pass as-is.

### 3. `rig/costs/cost_provider.py` — pricing stubs return 0

Expected at this stage (Thursday's task), but note it means the dollar
budget never actually trips in testing until this is filled in.

## Remaining Week 1 work, in order

1. Fix bug #1 (`llm.py` retries) and bug #2 (budget status).
2. **Wednesday**: build `docker/Dockerfile.sandbox`, route `bash`/`search`
   through `ws.exec_prefix` into the container, verify `sleep 999` gets
   killed without hanging the loop.
3. **Thursday**: fill in real pricing in `cost_provider.py`; add
   `stop_reason == "max_tokens"` handling in the loop.
4. **Friday**: run the 4 experiments (bash-only, no line numbers,
   truncation limits, no `is_error`) against early task-ladder tasks.
5. **Saturday**: write `evals/tasks/week1.yaml` for the 12-task ladder
   (T01-T12), build `evals/run_evals.py`, run all 12 three times each
   (pass@1 vs pass^3).
6. **Sunday**: read every failed trajectory, label it, attempt the
   checkpoint cold.

### Eval sets, in one line

Not a separate framework. `evals/tasks/week1.yaml` is a plain data file
(id, prompt, seed patch, grader). `evals/run_evals.py` is a script that:
snapshots the target repo, applies the seed patch, runs the agent via
your own `run_agent()`-equivalent, runs the grader (a `pytest` selector,
or a string/diff check), appends one line to `results.jsonl`. It's your
existing test suite plus a thin orchestration wrapper.

## Week 2/3/4 roadmap (pointers only — read each week's Concepts section when you get there)

- **Week 2 — coding-agent harness.** Provider/runtime/harness split,
  streaming, Ctrl-C-safe cancellation, a steer-vs-follow-up message
  queue, `edit_file` v2 (CRLF, closest-candidate errors), session resume
  via append-only JSONL. New tasks T13-T16. (Parallel tool execution is
  already done, ahead of schedule.)
- **Week 3 — context engineering.** Per-segment token accounting,
  deliberate cache breakpoints (5-min vs 1-hour), observation masking for
  stale tool output, compaction past ~70% of context window. New task
  T17 under a tight token budget forces compaction to fire.
- **Week 4 — retrieval.** BM25 from scratch, AST-based chunker,
  embeddings + pgvector + HNSW, hybrid fusion with RRF, reranker, repo
  map (Aider-style PageRank). Write 40 labeled ground-truth questions
  first, then measure whether any of it beats the Week 1 `search` tool.
  New tasks T18-T23.

## Study-plan updates made (for reference)

Three edits landed in `rig-study/content/*.md`, rebuilt into
`index.html` and `templates/study-plan.md`:

1. `content/path.md` — "Weekly rhythm" item on falling behind mid-week.
2. `content/w1.md` — paragraph clarifying evals are pytest + a thin
   script, not a new framework.
3. `content/w1.md` — "reader variation" note that pydantic-typed tool
   schemas are a valid alternative to raw dicts.

Canonical starter code (`llm.py`/`loop.py`/`budget.py`) was **not**
replaced with my version, since it has the two bugs above — not safe to
bake into material future students rely on. Worth revisiting once fixed.
