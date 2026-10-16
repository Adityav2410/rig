# Agents from First Principles — full study plan

This is the complete 18-week self-study plan for building `rig`, a personal agent runtime, from first principles. Generated from `content/*.md` by `tools/export.py` — edit the source week file and re-run the export instead of editing this file.

## Contents

- The path I chose
- The primitives behind the vocabulary
- The central project: rig
- Week 1: the single-agent loop
- Week 2: the coding-agent harness
- Week 3: context engineering, compaction, memory and caching
- Week 4: retrieval
- Week 5: tracing, evals and trajectory evaluation
- Week 6: the model, from tokenizer to KV cache
- Week 7: serving and post-training
- Week 8: model routing, reasoning effort and the cost layer
- Week 9: tools, MCP, sandboxing and policy
- Week 10: a mini-Perplexity
- Week 11: deep research and multi-agent systems
- Week 12: a Claude-style workbench
- Week 13: memory, personalization and connectors
- Week 14: a multi-user service
- Week 15: durable workflows, scheduling and approvals
- Week 16: browser and computer use
- Week 17: voice and realtime
- Week 18: production architecture, capability evals and your graduation project
- Appendix A: reading order
- Appendix B: glossary, term to primitive
- Appendix C: seventeen questions you should be able to answer
- Appendix D: misconceptions and hype traps
- Appendix E: staying current and showing the work


---

# The path I chose

Eighteen weeks, one evolving project, one weekly rhythm: learn the primitive, build it, read one small real implementation, trace it, modify it, measure it. The goal is one assistant runtime that can do Perplexity-style research, Claude Code-style work and Muse-style personal assistance, built by someone who also understands the model underneath it.

| Weeks | Phase | You come out able to |
|---|---|---|
| 1–5 | The machine | Build and measure a coding agent: loop, harness, context, retrieval, evals |
| 6–8 | The model | Read a transformer, its KV cache, a serving engine and an RL loop line by line, then decide per call which model and how much reasoning each step deserves |
| 9–14 | The assistant | Put the trust boundary in place, then build research, deep research, a workbench, memory and connectors, and serve them to many users from one deployment |
| 15–18 | Autonomy | Run durable background work, browser and computer use, voice, and a production architecture |

**Why this order.**

- Context engineering (Week 3) comes before retrieval (Week 4). Retrieval is one way of choosing context, and the first wall a coding agent hits is its own tool output.
- Evals and tracing are Week 5, not the last week. From Week 10 on, quality is graded by a model (answer correctness, citation precision), and an unvalidated grader turns every later comparison into noise.
- The model weeks sit between the machine and the assistant. By then prompt caching is a mystery worth opening, and every later latency or cost decision depends on what prefill, decode and batching actually cost.
- Routing and effort (Week 8) come straight after the model weeks. Once you know what prefill, decode and thinking tokens cost, choosing a model and an effort level per call is arithmetic, and Week 5's evals tell you whether quality held.
- Security (Week 9) comes before the open web (Week 10). The research agent reads untrusted pages, so the policy service and sandbox must exist first.
- The multi-user service (Week 14) comes after memory and connectors and before durability. By then rig holds every kind of per-user state, so isolation is designed once across all of it, and Week 15's durable workflows build on its Postgres and job queue.
- Durability (Week 15) comes before browser and voice. Approvals and background tasks that outlive a process are what make a personal agent possible.
- Tracing, a 12-task eval set and a sandbox start on Day 1 anyway. Later weeks make them trustworthy; they are never optional.

**Pick a specialty by Week 9.** Every week is done in full, but your graduation project and public write-ups go deep on one track:

- Research (retrieval, ranking, citations, latency): the Perplexity track.
- Personal agent (policy, connectors, memory, background work, voice): the Muse track.
- Work agent (workspace, code execution, artifacts): the Claude Code track.

**Ground rules.**

- Python 3.12 for the project. Read TypeScript, Rust and C where the best implementation lives; you read those, you don't extend them.
- Week 1 calls one provider's API with raw HTTP, no SDK, so you see the wire format. These notes use Anthropic's Messages API concretely and map every provider-specific name (endpoints, headers, stop reasons) to OpenAI's equivalent inline, so you can build Week 1 against either. SDKs are allowed from Week 2.
- One provider until Week 2's provider-abstraction exercise. Default to one strong model and one cheap model from a single provider — these notes default to `claude-sonnet-5-5` for the agent and `claude-haiku-5-5` for cheap passes (summaries, graders, bulk evals), but substitute your own provider's pair throughout if you're not using Anthropic. Week 2's provider-abstraction exercise is what makes that swap mechanical; Week 8 replaces the fixed split with a router that chooses per call.
- No agent framework on the critical path. You read the OpenAI Agents SDK, LangGraph, OpenHands and browser-use; you don't build on them. LangChain never appears.
- Pin every repo you read; Appendix A has a one-time bootstrap script. File paths and line numbers in this plan were checked against the commit or tag listed there; upstream will drift.
- Money: a monthly spend limit on every API key, and a per-run token budget enforced in code from Day 1. Weeks 6 and 7 need a GPU for a few hours; one rented GPU is enough, and the full nanochat training run is optional.
- Real accounts come last. Email, calendar, payments and the browser use fixtures and throwaway accounts until Week 9's red-team suite passes.

**Weekly rhythm (8 to 12 hours, about 180 hours in total).**

1. Monday (1 to 1.5 h): the primitive. Read the one spec, paper or post named for the week; write a half-page note in your own words.
2. Tuesday to Wednesday (2 to 4 h): build the small version from scratch, inside the project.
3. Thursday (1.5 to 2 h): read the reference implementation and trace the named path end to end. Write the trace as a numbered call chain with file:line references.
4. Friday (1 to 1.5 h): the modifications and experiments.
5. Weekend (3 to 4 h): run the eval set, compare against last week, then attempt the checkpoint. If you can't pass it, the next week starts late; don't skip ahead.
6. If you fall behind mid-week — say it's Friday and you've only finished Tuesday's build — don't compress the missing days into one sitting or jump straight to the weekend's eval run. Finish the remaining Build steps in order first; it's fine to drop that week's Experiments to make time, but the eval set and checkpoint are what tell you whether the week actually landed, not the calendar.
7. One hour somewhere in the week: the frontier log (Appendix E).

**Weekly note.** One file per week in `notes/`, with the same seven headings: the primitive (what problem exists), my implementation, the reference implementation, differences and why, experiments and numbers, failure modes, and what I would actually ship.

Every week below uses the same headings: Concepts, Build, Project increment, Read, Trace, You should be able to answer, Experiments, Production lens, Not yet, Checkpoint. Week 1 adds a day-by-day plan; Week 18 trades some of them for graduation projects.

---

# The primitives behind the vocabulary

Everything in this ecosystem reduces to five things: a stateless next-token function, a transcript, a structured-output convention, a `while` loop, and ordinary systems code wrapped around them. Learn the eight terms below as layers of that stack, not as products.

| Term | What it actually is | Where it lives in code | Fundamental or abstraction? |
|---|---|---|---|
| LLM | A stateless function from a token sequence to a distribution over the next token, sampled repeatedly. Over HTTP: a list of messages in, one message out. It remembers nothing between calls and executes nothing. | One HTTP POST (`/v1/messages` on Anthropic, `/v1/responses` or `/v1/chat/completions` on OpenAI) | Fundamental |
| Tool calling | A structured-output convention. The model emits a call — an id, a name, and arguments — instead of plain text, and signals that it did (Anthropic: a `tool_use` content block, stop reason `tool_use`; OpenAI: a `tool_calls` entry, finish reason `tool_calls`). Your code runs it and appends a result tagged with the same id. | ~20 lines of JSON handling | Fundamental: an id-correlated RPC carried inside the transcript |
| Agent loop | Call the model; if it requested no tools, stop; otherwise run the tools, append results, repeat. It ends when the model stops asking for tools or a budget trips. | ~40 lines | Fundamental |
| Agent | A configuration of that loop: model, system prompt, tool set, stop policy. Not a separate mechanism. | a dataclass | Mostly naming |
| Runtime | What makes a loop run reliably: event streaming, cancellation, parallel tool execution, retries, persistence, resume. | pi's `packages/agent` plus its session manager | Fundamental engineering; each framework's shape is a choice |
| Harness | Everything around the model for one product: system prompt, tool implementations and their output shaping, context assembly, compaction, permissions, UI. In eval work it also means the code that runs and grades tasks. | pi's `packages/coding-agent` | Fundamental; most of an agent's quality lives here |
| Coding agent | A harness whose environment is a repository and whose tools read, search, edit and run code. It works better than most agents because tests and compilers give cheap, honest feedback. | your project | A specialization |
| Workflow engine | Code owns the control flow (a DAG or state machine) and LLM calls are steps inside it. A durable engine persists each step's result so a crashed run resumes without redoing side effects. | DBOS, Temporal, LangGraph | Fundamental, and older than LLMs |

*Diagram — The vocabulary as nested layers. Rendered version: https://ai.labs-nature.com/study-plan/#/primitives*

An "agent" is the loop configured with a model, prompt, tools and stop policy; a coding agent is a harness specialized for a repository.

**The distinction that matters most is who chooses the next step.** In an agent loop the model chooses; in a workflow your code chooses. Most production systems are hybrids: a workflow whose steps include bounded agent loops.

**Fundamental: learn these deeply.**

- The transcript is the only state the model sees. Memory, RAG, compaction, subagents and skills all reduce to one question: which bytes go into the next request?
- The context window is a hard resource with a price per token, like memory with a cost per byte.
- Prefix caching only reuses computation for a byte-identical prefix. Every prompt-layout decision is constrained by it.
- Side effects happen outside the transcript (files, processes, network, money). They need idempotency, permissions and isolation, exactly like any distributed system.
- A verification signal (tests, graders, humans) bounds how good any agent can get.

**Framework abstractions: learn these by reducing them.**

- "Memory" component: read text from a store into the prompt, write text back after the run.
- "Handoff": a tool call whose effect is swapping the active system prompt and tool set.
- "Subagent": a recursive call of the loop with a fresh transcript that returns a string.
- "Planner/executor": one model call that outputs a list, then a loop over the list.
- "Guardrail": a check function run before or after a model or tool call.
- "Skill": a prompt file (often with scripts) loaded into context on demand.
- "Chain" or "graph": function composition, or a state machine.
- "Toolkit" or "tool registry": a dict from name to (JSON schema, function).

---

# The central project: rig

You build one Python program, `rig`. It starts as a repository agent and grows into an assistant runtime with three modes: research, work and personal. Each week adds one capability and, deliberately, the failure mode that capability brings. Nothing from a framework goes in until you have built the primitive yourself.

**Targets.** Weeks 1 to 3 use [pallets/click](https://github.com/pallets/click) at tag `8.5.0`: about 12,000 lines across 16 modules in `src/click`, and 1,991 tests that finish in roughly 8 seconds — pure Python, no native deps or network needed to install or test, so it runs offline in the sandbox and stays cheap to re-run the full suite after every fix, across every task, every week. It's real production code, not a toy example, but still small enough that you can verify a fix or a grader by hand. The same codebase and the same 12-task ladder carry across Weeks 1 to 3 unchanged, so a change in pass rate, steps or cost is attributable to your harness, not to a different target. Week 4 adds [openai/openai-agents-python](https://github.com/openai/openai-agents-python) at `v0.23.1` (320 source files), large enough that retrieval has something to beat; it is also Week 11 reading. From Week 10 the target is the open web, from Week 12 a fixture folder of CSVs and PDFs, and from Week 13 a fixture inbox and calendar, then one real account.

**Layout as it grows.** Week 1's `rig/` package gains one directory per capability: `providers/` (W2), `context/` (W3), `retrieval/` (W4), `gateway/` (W8), `research/` (W10), `mcp/` and `policy/` (W9, the policy service runs as its own process), `artifacts/` and `ingest/` (W12), `memory/` and `connectors/` (W13), `server/` (W14), `durable/` and `scheduler/` (W15), `browser/` (W16), `voice/` (W17), `app/` (W18).

**Invariants that hold from Day 1.**

- The loop owns the transcript. Tools never see it and never mutate it.
- Every side effect goes through the sandbox. The host process only edits files inside the run's worktree.
- Every model call and tool call is an append-only trace event, flushed before the next step starts.
- Every run has a budget: steps, tokens, dollars and wall-clock seconds. Running out is a normal exit status, not an exception that escapes.
- Every capability change is judged by the eval set, not by one demo.

| Week | Capability added | Failure mode you will meet | Metric that proves it worked |
|---|---|---|---|
| 1 | Loop, five tools, container sandbox, JSONL traces, 12-task eval | Runaway loops, ambiguous edits, oversized tool output | Pass rate over 3 runs; steps, tokens and dollars per task |
| 2 | Provider interface, streaming events, parallel tools, cancellation, steering, robust edit | Malformed or truncated tool arguments; cancellation mid-tool | Edit-apply failure rate; p95 step latency |
| 3 | Context accounting, output shaping, compaction and tool-result clearing, deliberate cache breakpoints and TTLs, a cost ledger, project memory file | Facts lost after compaction; cache misses from prompt churn | Cache-read ratio; dollars lost to cache misses; pass rate on long tasks |
| 4 | BM25, embeddings, HNSW, then pgvector with Postgres full-text search, hybrid fusion, reranking and typo-tolerant matching, as one `retrieve` tool | Retrieved noise crowding out useful context; misspelled queries that find nothing | Recall@10 on labeled and misspelled queries; steps to first relevant file |
| 5 | OpenTelemetry spans, validated graders, trajectory metrics, versioned prompts, CI gate | Flaky graders; overfitting to your own eval set | Grader agreement; confidence intervals on pass rate |
| 6 | A tokenizer, a decoding loop with a KV cache, a small trained model | Treating tool calling as magic rather than special tokens | Decode tokens per second with and without the cache |
| 7 | Paged KV cache and continuous batching; an RL environment built from your tasks | Throughput that collapses under long prompts | Throughput against batch size; prefix-cache hit rate |
| 8 | Model gateway: per-call model and effort routing, escalation on stalls, session pinning, budget guard | A cheaper average hiding a quality drop; cache lost on every switch | Cost per success against always-large; share of strong calls; escalation rate |
| 9 | MCP client and server, policy service with scoped grants, OS sandbox, red team, structured outputs | Prompt injection through tool output; approval fatigue | Blocked violations; approvals asked per task |
| 10 | Conversation-aware query rewriting, web search, fetch, extraction, evidence store, cited answers | Citations that don't support the claim; stale sources | Citation precision; time to first token; dollars per answer |
| 11 | Deep research loop, subagents, planner and fan-out modes | Context lost between agents; cost blow-up | search_evals score against dollars per task |
| 12 | Per-user workspace, code execution, artifacts with lineage, document ingestion | Silent numeric errors; artifacts nobody can audit | Computation correctness; artifact audit pass rate |
| 13 | Memory with provenance, fixture then real connectors, inbound email | Wrong memory injected; injection through email | Memory precision and recall; wrong-memory injection rate |
| 14 | Multi-user service: Postgres with row-level security, sign-in, a job queue with one run per conversation, per-user quotas, user deletion | One user's data in another's answer; double-submitted runs; one user starving the rest | Cross-user reads (target zero); p95 time to first token at 50 users; duplicate runs |
| 15 | Durable steps, idempotent tool ledger, scheduler, durable approvals | Duplicate side effects after a crash; doubled schedules | Duplicates under repeated `kill -9` (target zero) |
| 16 | Browser agent with an isolated profile and a destination-aware gate | Exfiltration through navigation; wrong clicks | Forbidden actions completed (target zero); task success |
| 17 | Voice loop: VAD, streaming speech-to-text, model, text-to-speech, barge-in | Talking over the user; slow turn-taking | End of speech to first audio, p50 and p95 |
| 18 | One runtime with three modes, capability eval suites, feedback and online experiments, graduation project | A change in one mode regressing another | Per-capability pass^3; cost per success; p95 latency |

*Diagram — rig v1.0 architecture, with the week each part arrives. Rendered version: https://ai.labs-nature.com/study-plan/#/rig*

Requests flow right, from the loop through the context builder to the model. Every tool call flows down through the policy service, which can ask a person. Only code execution and the browser run inside the sandbox, so sandboxed code can never write the stores, the tool ledger or the grants.

---

# Week 1: the single-agent loop

*Phase: The machine · Primary reading/code: mini-swe-agent*

By Sunday you have a roughly 400-line Python agent that fixes seeded bugs in click inside a container, logs every step, and scores itself on 12 tasks. You can also explain every branch of mini-swe-agent's 190-line loop.

## Concepts
**New to this provider's API entirely?** Everything below assumes you've seen one plain request/response with no tools. If you haven't, spend 15 to 20 minutes first: [Get started](https://platform.claude.com/docs/en/get-started) (one `curl` call, `user` message in, assistant text back) and the first two sections of [Using the Messages API](https://platform.claude.com/docs/en/build-with-claude/working-with-messages) (multi-turn history, the `system` field) — skip vision and prefill, not relevant here. A tool call is then just one more kind of thing that can appear in that same response, with one extra round trip to run it and send the result back.

None of this week's ideas are specific to one vendor; only the exact field names are. Pick one provider to actually call (these notes default to Anthropic's Messages API, concretely, since that's what the starter code below sends), and use this table to translate as you read docs or other people's code:

| Idea | Anthropic (Messages API) | OpenAI (Chat Completions / Responses) |
|---|---|---|
| System instructions | top-level `system` string | a `system`/`developer`-role message, or `instructions` (Responses) |
| Model requests a tool | content block `{type: "tool_use", id, name, input}` | `tool_calls` entry on the assistant message: `{id, function: {name, arguments}}` |
| You return the result | `tool_result` content block, `tool_use_id` matching the call's id | a `role: "tool"` message, `tool_call_id` matching the call's id |
| Turn finished normally | stop reason `end_turn` | finish reason `stop` |
| Turn paused for a tool call | stop reason `tool_use` | finish reason `tool_calls` |
| Output cut off | stop reason `max_tokens` | finish reason `length` |
| Model declined to answer | stop reason `refusal` | finish reason `content_filter` |
| Context window exceeded | `model_context_window_exceeded` error (Week 3's problem) | `context_length_exceeded` error |

- The wire format, regardless of vendor: a system/developer instruction, alternating user and assistant turns, and content that is either plain text, a tool call, or a tool result.
- Tool calling as an id-correlated RPC inside the transcript. Every tool-call id in an assistant message needs a matching tool-result message right after it, or the API rejects the next request.
- Stop/finish reasons and what each means for the loop: turn finished (done), tool call requested (execute and continue), output cut off (so tool arguments may be truncated), declined, and context exceeded (Week 3's problem). See the table above for each provider's exact names.
- Statelessness: every request resends the whole transcript. Without caching, total input tokens grow roughly with the square of the step count.
- Budgets are the only termination guarantee you control: steps, tokens, dollars, wall clock.
- Tool output is untrusted input to the next request. Treat it like user input to a web app.

## Day by day
| Day | Time | Do | Working by end of day |
|---|---|---|---|
| Mon | 1.5 h | A throwaway script, one tool, by hand — see the Monday walkthrough just below | One full tool round trip over raw `httpx`; the four JSON bodies saved under `notes/wire/` |
| Tue | 2 h | `llm.py`, `trace.py`, `budget.py`'s shape, `loop.py`, `list_files`, `read_file`; clone click; run the first prompt | The agent answers the read-only trace task; `runs/<id>/trace.jsonl` holds one event per model call and tool call |
| Wed | 2 h | `search`, `bash`, the sandbox container | The agent runs the test suite in the container and reports counts; `sleep 999` is killed at the timeout and the loop carries on |
| Thu | 2 h | `edit_file`, `budget.py` for real, `max_tokens` handling, tool error paths; read mini-swe-agent | The agent fixes task T04 end to end; an artificially tiny budget ends the run with status `budget:*` |
| Fri | 1.5 h | The four experiments on T04 to T09 | `notes/week1-experiments.md` comparing variants on the same tasks |
| Sat | 3 to 4 h | `evals/run_evals.py`; run all 12 tasks 3 times | A baseline table: pass rate, mean steps, tokens and dollars per task |
| Sun | 2 to 3 h | Read every failed trajectory; label failures; attempt the checkpoint | A failure taxonomy with counts; checkpoint passed or a redo list |

Each day below says exactly what to build and points at the reference material further down the page — schemas, the Dockerfile, the system prompt, the task list — rather than repeating it here.

### Monday — one tool call, by hand, no modules yet.
Today's script is throwaway; you will not reuse it tomorrow. The point is to see the four raw JSON bodies with your own eyes — the request, the tool-call response, the follow-up request, the final answer — before `llm.py` hides them behind a function call for the rest of the week.

1. Export your provider's API key and `pip install httpx`.
2. Write a `count_lines(path)` Python function with no connection to the API at all: open the file at `path`, return how many lines it has. This is your one tool for today, deliberately trivial, so the only new thing you're learning is the wire format, not the tool's logic.
3. Build one request body: `model`, `max_tokens`, a `messages` list with a single user turn ("How many lines are in pyproject.toml?"), and a `tools` list with one schema describing `count_lines` (`name`, `description`, an `input_schema` with a `path` string property — see [Define tools](https://platform.claude.com/docs/en/agents-and-tools/tool-use/define-tools) on Anthropic, or the schema section of the [function-calling guide](https://developers.openai.com/api/docs/guides/function-calling) already linked above on OpenAI, for the exact shape and field names). POST it with `httpx.post`. Save the request body to `notes/wire/01-request.json` and the raw response to `notes/wire/02-response.json`.
4. In that response, find the stop/finish reason and the tool-call content (see the Concepts table above for your provider's exact field names). Print the tool call's name and input — confirm the model actually asked for `count_lines` with a `path` argument, not something it invented.
5. "Run it by hand" means exactly that: call `count_lines(**input)` yourself, inline in the same script. There's no registry or dispatch yet — that's tomorrow's `tools/__init__.py`.
6. Build the second request: the same `messages` list, with the assistant turn you just received appended, plus a new turn carrying the tool result (same call id, your function's return value as a string — see the Concepts table for the exact shape). POST it. Save the request to `notes/wire/03-request.json` and the response to `notes/wire/04-response.json`.
7. Print the assistant's final text from that second response.
8. Break it on purpose, twice, and read what comes back: send the second request with `tools` omitted; send it with the wrong tool-call id. Note what each failure actually looks like — `run_tool` on Wednesday has to turn failures just like these into something the model can recover from.

### Tuesday — the real loop, pointed at a read-only question.
Today you build the reusable modules Monday's throwaway script stood in for: a real HTTP client with retries, an event log, and the agent loop itself. You point that loop at a read-only question about click so you can grade it against a known answer key before the agent is allowed to change a single file. By tonight you have a working, if toothless, agent that can read and reason about code but can't yet edit anything.

1. Lay out the repo per **Repository layout** below.
2. Write `rig/llm.py`: the raw HTTP client, and the only thing in the codebase that talks to the network. Its whole job is one request in, one parsed response out, retrying only the failures that are safe to retry — it knows nothing about tools, messages history, or the loop. See **Starter code** below for the exact retry policy — type it in, don't paste.
3. Write `rig/trace.py`: the append-only event log every later week's metrics (and today's own grading) come from — one JSON line per model call and tool call, flushed immediately so a crash still leaves a readable prefix. Also get `rig/budget.py`'s shape in place: it will be the single place that decides when a run has to stop (steps, tokens, dollars, wall clock), so nothing else in the codebase needs to know the thresholds. Both are sketched in **Starter code**. You only need `trace.py` working today; giving `Budget` its interface now (even with `check()` never tripping) means `loop.py` doesn't change shape when you make the limits real on Thursday.
4. Write `rig/loop.py`: the agent itself. It owns the one `messages` list nothing else may append to, and on each turn decides whether to call the model again, run the tools it asked for, or stop — see **Starter code** below.
5. Implement `list_files` (lets the model see what exists before it goes looking) and `read_file` (lets it see a file's contents, numbered, so it can cite a location precisely) from the contracts in **The first five tools** below — both are a few lines each. `edit_file` and `bash` (the two tools with real engineering in them) aren't due until Wednesday and Thursday.
6. Write a minimal `workspace.py` from the Tuesday shape in **Starter code** below: today it's just a small object holding `root` (the checkout path) and `name`, so `loop.py` and your tools have a `ws` to call — the container lifecycle in **Sandbox from Day 1** doesn't arrive until Wednesday. Then `git -C reading/click archive 8.5.0` into `workspaces/` and point it at that checkout — a plain checkout, no sandbox yet.
7. Run **the first prompt to give your agent** below, read-only, and grade yourself against the answer key given there.
8. Confirm `runs/<id>/trace.jsonl` has one line per model call and tool call, and that every line is valid JSON even if you kill the process mid-run.

### Wednesday — the sandbox, and two tools that touch it.
Today the agent gets permission to actually run things: a disposable, network-isolated Docker container per run, plus the `search` and `bash` tools that use it. This is where the sandbox stops being a diagram and becomes a real boundary — you'll deliberately make a command misbehave (`sleep 999`) and confirm the agent recovers instead of hanging forever.

1. Build the image from the Dockerfile in **Sandbox from Day 1** below. Sanity-check it stands alone first — `docker run --rm rig-sandbox python -c "print(1)"` — before wiring it into rig.
2. Implement `tools/shell.py`'s `bash`: the escape hatch for everything the other tools can't do, chiefly running tests — exactly as given in **Starter code**. Implement `tools/search.py`'s `search`: today's grep-based baseline for finding things in the repo, which Week 4's real retrieval has to beat — from the contract in **The first five tools**.
3. Extend `workspace.py` to the Wednesday shape in **Starter code** below, which adds `exec_prefix`: it owns the sandbox's whole lifecycle — snapshotting the repo fresh per run, starting and stopping the container, and the path jail that keeps host-side file edits inside the worktree. Follow the snapshot-and-run steps in **Sandbox from Day 1**: fresh snapshot, start the container with `--network none`, offline `pip install`.
4. Smoke-test the sandbox by hand before trusting the agent with it: `docker exec` into a running container and run `python -m pytest -q` yourself; the counts should match T03's baseline (1,991 passed / 24 skipped / 1 xfailed).
5. Give the agent a prompt that runs `sleep 999` and confirm the inner `timeout` kills it and the loop continues rather than hanging.

### Thursday — editing, real budgets, and mini-swe-agent.
Today the agent can finally fix bugs, not just read about them: `edit_file` with its uniqueness-matching safety net, and `budget.py` enforced for real so a runaway agent stops itself instead of burning your API budget unattended. You close the day by reading mini-swe-agent, the smallest possible counterpoint to everything you've built this week — one tool, no permission model, and reportedly comparable results.

1. Implement `edit_file` exactly as given in **Starter code**; the uniqueness check is the whole point of it, don't loosen it.
2. Finish `budget.py` for real: steps, input tokens, dollars and wall clock each raise `BudgetExceeded(<reason>)` from `check()`; fill in a price table from your provider's current pricing page for `charge()`.
3. Add `max_tokens` handling in `loop.py` (the `TRUNCATED` branch, already shown in **Starter code**) and confirm every tool failure becomes an `is_error` result rather than an exception that escapes (also shown there).
4. Point the agent at task T04 end to end — fix, run tests, stop — see **Task ladder and initial eval set** below for the exact bug and grader.
5. Set an artificially tiny budget (for example `max_steps=2`) and confirm the run ends with status `budget:steps`, not an exception.
6. Read **mini-swe-agent** below and trace the path given there; answer its seven questions in your notes.

### Friday — break your own agent on purpose.
No new code today. You spend the day running controlled variants of the agent you already built — fewer tools, no line numbers, different truncation limits, no error signaling — against the same tasks, to start forming opinions backed by numbers about which of this week's design choices actually mattered.

Run the four experiments in **Experiments (Friday)** below against T04 to T09 (each experiment names its own task range). Write up what changed in `notes/week1-experiments.md`: pass rate, steps, tokens, and the specific step in the trace where behavior diverged.

### Saturday — the eval harness.
Today you build the harness that turns "it seems to work" into a number: a script that snapshots click fresh for every task, runs the agent, grades the result in the sandbox, and logs everything to `results.jsonl`. Then you run the full 12-task ladder three times each to get your first real baseline — pass rate, steps, tokens, dollars — to compare every future week against.

1. Write `evals/run_evals.py` per **Repository layout** below: per task, a fresh snapshot, apply the seed if the task has one, run the agent, run the grader inside the container, append one line to `results.jsonl`.
2. Run it over all 12 tasks in **Task ladder and initial eval set** below, three times each.
3. Compute pass@1 and pass^3 (see the note under that table) and the per-run and per-batch rows of **Metrics to record from the start** below.

### Sunday — read your own failures, then the checkpoint.
No new code today either. A pass rate alone tells you something's wrong, not what — so you read every failed run end to end and assign it a cause. Then you attempt the week's checkpoint cold; whether you pass it, not whether you got through the calendar, is the real signal for whether you're ready for Week 2.

1. For every failed run, read the trace end to end and assign it exactly one label: wrong location, bad edit, edited tests, gave up, looped, budget, tool error.
2. Write the counts per label in your weekly note.
3. Attempt **Checkpoint** below. If you can't pass it cold, that's a real signal, not a formality — redo the relevant day rather than carrying the gap into Week 2.

## Repository layout
```text
rig/
  pyproject.toml            # deps: httpx, pyyaml, pytest (for rig's own tests)
  rig/
    cli.py                  # rig run --repo PATH --task FILE_OR_TEXT --budget-usd 0.50
    llm.py                  # raw Messages API client: retries, backoff, usage
    loop.py                 # run_agent(): the loop, stop conditions
    budget.py               # steps / tokens / dollars / wall clock
    trace.py                # append-only JSONL writer
    workspace.py            # snapshot creation, container lifecycle, path jail
    tools/
      __init__.py           # registry, dispatch, truncation
      fs.py                 # list_files, read_file, edit_file
      search.py             # search (ripgrep)
      shell.py              # bash
    prompts/system.md
  docker/Dockerfile.sandbox
  evals/
    tasks/week1.yaml        # id, prompt, seed, grader
    seeds/                  # one patch per seeded bug (never shown to the agent)
    hidden/                 # hidden tests (never copied into the agent's workspace)
    run_evals.py
    report.py
  tests/                    # tests for rig itself: tool contracts, truncation, budget
  runs/                     # gitignored: <run_id>/{trace.jsonl, messages.json, diff.patch, result.json}
  reading/                  # gitignored pinned clones + SHAS.txt
  notes/
```

## Minimal architecture
One process, one thread, no framework. Five rules:

1. `loop.py` owns the `messages` list; nothing else appends to it.
2. Tools are plain functions `fn(ws, **args) -> str` that raise `ToolError` for expected failures. `ws` is the workspace object for this one run, built in `workspace.py`: it holds the sandboxed checkout's root path (`ws.root`), a display name (`ws.name`), and, from Wednesday on, the container handle (`ws.exec_prefix`) — passed into every tool and into `loop.py` so neither has to reach for global state. Dispatch converts every exception into an `is_error` tool result, so a buggy tool cannot kill the run.
3. File reads and edits happen on the host, inside a path jail rooted at the worktree. Anything that executes code happens in the container, which sees the same worktree as a bind mount.
4. The trace writer appends and flushes one JSON line per event, so a crash leaves a readable prefix.
5. At run end, write `messages.json` (the full transcript) and `diff.patch`. Those two files let you replay or grade any run later without re-calling the model.

## Starter code
The code below ran against click `8.5.0` with a scripted fake model standing in for `llm.call`: tool pairing, unknown tools, `max_tokens` truncation, the path jail, ambiguous edits, command timeouts and budget exhaustion all behaved as described. Type it in yourself rather than pasting it; the point is to own every line.

`rig/llm.py`, a raw client with the retry policy the official SDK uses. Shown against Anthropic's endpoint — on OpenAI, swap `API_URL` for `https://api.openai.com/v1/responses` (or `/v1/chat/completions`) and the header for `"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}"`; the retry/backoff logic below is otherwise identical:

```python
import os, random, time
import httpx

API_URL = "https://api.anthropic.com/v1/messages"
RETRYABLE = {408, 409, 429, 500, 502, 503, 504, 529}

class LLMError(Exception): ...

def call(body: dict, *, timeout: float = 300.0, max_retries: int = 5) -> tuple[dict, dict]:
    headers = {"x-api-key": os.environ["ANTHROPIC_API_KEY"],
               "anthropic-version": "2023-06-01", "content-type": "application/json"}
    last_error = ""
    for attempt in range(max_retries + 1):
        started, wait = time.monotonic(), None
        try:
            r = httpx.post(API_URL, headers=headers, json=body, timeout=timeout)
        except httpx.TransportError as e:   # connect errors and timeouts
            last_error = repr(e)            # safe to retry: a model call has no side effects (you may pay twice)
        else:
            if r.status_code == 200:
                return r.json(), {"attempts": attempt + 1,
                                  "latency_s": round(time.monotonic() - started, 3),
                                  "request_id": r.headers.get("request-id")}
            last_error = f"HTTP {r.status_code}: {r.text[:300]}"
            hint = r.headers.get("x-should-retry")
            if hint == "false" or (r.status_code not in RETRYABLE and hint != "true"):
                raise LLMError(last_error)  # a 400 is your bug; retrying will not fix it
            try:
                wait = float(r.headers.get("retry-after", ""))
            except ValueError:
                pass
        if attempt < max_retries:
            time.sleep(wait if wait is not None else min(60.0, 2 ** attempt) * random.uniform(0.5, 1.5))
    raise LLMError(f"gave up after {max_retries + 1} attempts: {last_error}")
```

`rig/workspace.py`, Tuesday's shape: the object every tool function and `loop.py` call `ws`, passed in rather than reached for as global state. Today it's nothing but the checkout — `root` for the path jail every file tool checks against, `name` to fill the system prompt's `{repo}` — with `exec_prefix` arriving Wednesday once there's a container to exec into:

```python
# rig/workspace.py (Tuesday — step 6)
from pathlib import Path

class Workspace:
    def __init__(self, root: Path, name: str):
        self.root = root   # checkout's root; every file tool is jailed here (see resolve() below)
        self.name = name   # repo's display name, interpolated into the system prompt as {repo}
```

`rig/loop.py`, the whole agent. The `ws` argument `run_agent` takes, and forwards into every tool call via `run_tool`, is the `Workspace` built just above:

```python
import time
from pathlib import Path
from rig import llm
from rig.budget import Budget, BudgetExceeded
from rig.tools import TOOLS, run_tool
import rig.tools.fs, rig.tools.search, rig.tools.shell  # noqa: F401  (registers the tools)

SYSTEM = (Path(__file__).parent / "prompts" / "system.md").read_text()
TRUNCATED = ("Not executed: your response hit max_tokens, so these arguments may be "
             "truncated. Re-issue the call with complete arguments.")

def run_agent(task: str, *, ws, model: str, budget: Budget, trace, max_tokens: int = 8192) -> dict:
    messages = [{"role": "user", "content": task}]
    schemas = [t.schema for t in TOOLS.values()]
    trace.event("run.start", task=task, model=model, tools=list(TOOLS))
    status = "unknown"
    try:
        while True:
            budget.check()  # raises BudgetExceeded("steps" | "input_tokens" | "usd" | "wall_clock")
            body = {"model": model, "max_tokens": max_tokens, "system": SYSTEM.format(repo=ws.name),
                    "messages": messages, "tools": schemas}
            resp, meta = llm.call(body)
            budget.charge(model, resp["usage"])
            trace.event("llm.response", step=budget.steps, stop_reason=resp["stop_reason"],
                        usage=resp["usage"], content=resp["content"], **meta)
            messages.append({"role": "assistant", "content": resp["content"]})

            calls = [b for b in resp["content"] if b["type"] == "tool_use"]
            if not calls:
                status = resp["stop_reason"]  # end_turn, max_tokens, refusal, ...
                break

            results = []  # one tool_result per tool_use id, or the next request is rejected
            for c in calls:
                if resp["stop_reason"] == "max_tokens":
                    out, is_error, took = TRUNCATED, True, 0.0
                else:
                    t0 = time.monotonic()
                    out, is_error = run_tool(ws, c["name"], c["input"])
                    took = time.monotonic() - t0
                trace.event("tool.result", step=budget.steps, call_id=c["id"], tool=c["name"],
                            input=c["input"], is_error=is_error, duration_s=round(took, 3),
                            output_chars=len(out), output=out)
                results.append({"type": "tool_result", "tool_use_id": c["id"],
                                "content": out, "is_error": is_error})
            messages.append({"role": "user", "content": results})
    except BudgetExceeded as e:
        status = f"budget:{e}"
    except llm.LLMError as e:
        status = "llm_error"
        trace.event("error", where="llm", message=str(e))
    last = messages[-1]
    final = "".join(b["text"] for b in last["content"] if b.get("type") == "text") \
        if last["role"] == "assistant" else ""
    trace.event("run.end", status=status, final=final, **budget.totals())
    return {"status": status, "final": final, "messages": messages, **budget.totals()}
```

The shapes above (`resp["stop_reason"]`, `body["system"]`, a `tool_use` block's `id`/`name`/`input`, a `tool_result` keyed by `tool_use_id`) are Anthropic's field names — use the table in Concepts to translate if you're on OpenAI: read `resp["choices"][0]["finish_reason"]` instead of `stop_reason`, put system text in a `developer`-role message instead of a top-level `system` key, read each tool call from `resp["choices"][0]["message"]["tool_calls"]` (`id`, `function.name`, `function.arguments` as a JSON string you parse), and append the result as `{"role": "tool", "tool_call_id": c["id"], "content": out}` instead of a `tool_result` block. The control flow — collect calls, run them, append results, loop until none remain — is identical either way.

`rig/trace.py` and `rig/budget.py`, the two accounting modules `loop.py` above already calls into. Deliberately simple — no engineering surprises here, just get the shape right so `loop.py` doesn't change later, then fill in `check()`'s thresholds and `charge()`'s price table yourself:

```python
# rig/trace.py
import itertools, json, time

class Trace:
    def __init__(self, path, run_id):
        self.f, self.run_id, self.seq = open(path, "a"), run_id, itertools.count()

    def event(self, kind, **fields):
        rec = {"run_id": self.run_id, "seq": next(self.seq), "ts": time.time(), "event": kind, **fields}
        self.f.write(json.dumps(rec) + "\n")
        self.f.flush()  # one line per event: a crash still leaves a readable prefix

# rig/budget.py
import time
from dataclasses import dataclass, field

class BudgetExceeded(Exception): ...

@dataclass
class Budget:
    max_steps: int
    max_input_tokens: int
    max_usd: float
    max_wall_clock_s: float
    steps: int = 0
    input_tokens: int = 0
    usd: float = 0.0
    started: float = field(default_factory=time.monotonic)

    def check(self):
        if self.steps >= self.max_steps: raise BudgetExceeded("steps")
        if self.input_tokens >= self.max_input_tokens: raise BudgetExceeded("input_tokens")
        if self.usd >= self.max_usd: raise BudgetExceeded("usd")
        if time.monotonic() - self.started >= self.max_wall_clock_s: raise BudgetExceeded("wall_clock")

    def charge(self, model, usage):
        self.steps += 1
        self.input_tokens += usage["input_tokens"]
        self.usd += price(model, usage)  # fill in from your provider's current pricing page

    def totals(self):
        return {"steps": self.steps, "input_tokens": self.input_tokens, "usd": round(self.usd, 4)}
```

On Tuesday, `check()` tripping is fine to leave untested (your limits are generous); Thursday is when you set them tight enough to actually trip and confirm `status` comes back as `budget:steps` or similar, not an unhandled exception.

`rig/tools/__init__.py`, registry and dispatch. Every failure becomes an `is_error` result, never an exception that escapes the loop:

```python
from dataclasses import dataclass
from typing import Callable
MAX_OUT = 30_000  # characters returned to the model per call

class ToolError(Exception): """Expected failure; the message goes back to the model."""

@dataclass
class Tool:
    schema: dict
    fn: Callable

TOOLS: dict[str, Tool] = {}

def tool(name, description, properties, required):
    def register(fn):
        TOOLS[name] = Tool({"name": name, "description": description,
                            "input_schema": {"type": "object", "properties": properties,
                                             "required": required}}, fn)
        return fn
    return register

def run_tool(ws, name, args) -> tuple[str, bool]:
    t = TOOLS.get(name)
    if t is None:
        return f"Unknown tool {name!r}. Available: {', '.join(TOOLS)}", True
    try:
        out, is_error = t.fn(ws, **args), False
    except ToolError as e:
        out, is_error = str(e), True
    except TypeError as e:                       # missing or unexpected arguments
        out, is_error = f"Bad arguments for {name}: {e}", True
    except Exception as e:                       # a bug in your tool: loud in the trace, not fatal
        out, is_error = f"Internal error in {name} ({type(e).__name__}): {e}", True
    return truncate(out), is_error

def truncate(s: str) -> str:
    if len(s) <= MAX_OUT:
        return s
    head, tail = s[: MAX_OUT * 2 // 3], s[-(MAX_OUT // 3):]   # keep the tail: errors and summaries live there
    return f"{head}\n\n[... {len(s) - len(head) - len(tail)} characters omitted ...]\n\n{tail}"
```

*Reader variation:* the raw dicts above are the fastest way to see the wire shape, but if you'd rather have typed, validated tool schemas, defining `ToolPropertySchema`/`ToolInputSchema`/`Tool` as small Pydantic models works just as well — dump one with `.model_dump(exclude=["func"])` to get the same JSON shape `tools` expects on the wire. Either representation satisfies the rest of this week's contracts; pick whichever you'll trust yourself to keep correct as the tool count grows.

`rig/workspace.py`, Wednesday's addition: once the sandbox container exists, `exec_prefix` is the argv prefix that turns any command into a command run inside this run's container, built once in the constructor from the container's name:

```python
# rig/workspace.py (Wednesday — adds the container)
class Workspace:
    def __init__(self, root: Path, name: str, run_id: str):
        self.root = root
        self.name = name
        self.exec_prefix = ["docker", "exec", "-w", "/repo", f"rig-{run_id}"]
```

The snapshot-and-run shell sequence in **Sandbox from Day 1** below (`docker run ... rig-$RUN`, `docker rm -f rig-$RUN`) is what this class's own start/stop methods wrap — translate it into methods yourself; the shape above is the only part other code depends on.

The two tools with real engineering in them. `resolve` is the path jail: every tool that touches a file calls it first, and it's the one piece of code standing between a model-supplied path and the host filesystem outside `ws.root` — a relative path with enough `../`s, or a symlink planted by an earlier edit, must not be able to walk out of the checkout. `edit_file` builds on it; its uniqueness check (`old_text` must match exactly once) is the whole point, since a non-unique match means the model's picture of the file is already wrong. `bash`, in `tools/shell.py`, is the one tool that runs inside the container rather than on the host — it uses `ws.exec_prefix` to `docker exec` into this run's sandbox, with an inner `timeout` so a hung command can't hang the agent:

```python
# rig/tools/fs.py (excerpt)
def resolve(ws, rel: str) -> Path:
    p = (ws.root / rel).resolve()          # follows symlinks, so a link cannot escape the jail
    if not p.is_relative_to(ws.root):
        raise ToolError(f"{rel}: outside the repository")
    return p

@tool("edit_file",
      "Replace exactly one occurrence of old_text with new_text. old_text must match the file "
      "exactly, including indentation, and must be unique; include surrounding lines if needed. "
      "To create a new file, pass an empty old_text.",
      {"path": {"type": "string"}, "old_text": {"type": "string"}, "new_text": {"type": "string"}},
      ["path", "old_text", "new_text"])
def edit_file(ws, path, old_text, new_text):
    p = resolve(ws, path)
    if old_text == "":
        if p.exists():
            raise ToolError(f"{path} already exists; pass old_text to edit it")
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(new_text)
        return f"Created {path}"
    src = p.read_text()
    n = src.count(old_text)
    if n != 1:
        raise ToolError(f"old_text matched {n} times in {path}; it must match exactly once. "
                        "Re-read the file and copy the exact text, with more context.")
    p.write_text(src.replace(old_text, new_text, 1))
    return f"Edited {path}"

# rig/tools/shell.py
@tool("bash", "Run a shell command at the repository root inside a sandbox with no network "
      "access. Use it to run tests and small scripts. Output is truncated to about 30k characters.",
      {"command": {"type": "string"}, "timeout_s": {"type": "integer", "minimum": 1, "maximum": 600}},
      ["command"])
def bash(ws, command, timeout_s=120):
    # `timeout` runs INSIDE the container: killing the host-side `docker exec` client
    # does not kill the process it started in the container.
    argv = ws.exec_prefix + ["timeout", "-k", "5", str(timeout_s), "bash", "-c", command]
    try:
        p = subprocess.run(argv, capture_output=True, text=True, errors="replace", timeout=timeout_s + 20)
    except subprocess.TimeoutExpired:
        raise ToolError(f"No return within {timeout_s + 20}s; the sandbox may be wedged.")
    out = p.stdout + (f"\n[stderr]\n{p.stderr}" if p.stderr else "")
    if p.returncode in (124, 137):
        out += f"\n[killed: exceeded {timeout_s}s]"
    return f"{out}\n[exit code {p.returncode}]"
```

`budget.py` keeps running totals from each response's `usage` (including `cache_read_input_tokens` and `cache_creation_input_tokens`) and multiplies by a price table you fill in from the current pricing page.

## The first five tools
| Tool | Contract | Why this shape |
|---|---|---|
| `list_files(path=".")` | `git ls-files` under a directory, capped at 500 lines with a "narrow the path" hint | Tracked files only: no `.venv`, no build output. Deterministic order makes traces diffable. |
| `read_file(path, offset=1, limit=400)` | Numbered lines plus a paging hint | Line numbers let the model cite locations and target edits; paging keeps one read from flooding context. |
| `search(pattern, path=".", glob=None, fixed=False)` | ripgrep, `path:line:text`, at most 200 matches; a bad regex returns `is_error` | This agentic grep is the baseline Week 4 retrieval must beat. |
| `edit_file(path, old_text, new_text)` | Exact match that must be unique; empty `old_text` creates a file | The uniqueness rule is your main defense against silent wrong edits. Week 2 compares it with pi's fuzzy matching. |
| `bash(command, timeout_s=120)` | Runs in the container; exit code always printed; killed at the timeout | The escape hatch for everything else. Exit codes in the text let the model tell "tests failed" from "command failed". |

## Sandbox from Day 1
The offline install step below was verified against click `8.5.0`. Without `--no-build-isolation`, pip tries to download the build backend and fails on a network-less container.

```dockerfile
# docker/Dockerfile.sandbox
FROM python:3.13-slim
RUN apt-get update && apt-get install -y --no-install-recommends git ripgrep \
    && rm -rf /var/lib/apt/lists/*
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --no-cache-dir "pytest>=8" "flit_core>=3.11,<4" \
    && chmod -R a+rwX /opt/venv
ENV PATH=/opt/venv/bin:$PATH PYTHONDONTWRITEBYTECODE=1 PIP_NO_INDEX=1 PIP_NO_CACHE_DIR=1
WORKDIR /repo
```

```bash
# per run: a history-free snapshot, so `git log -p` cannot reveal the seeded bug
mkdir -p "$SNAP" && git -C reading/click archive 8.5.0 | tar -x -C "$SNAP"
(cd "$SNAP" && git apply "$RIG/evals/seeds/T05.patch")      # only if the task has a seed
git -C "$SNAP" init -q && git -C "$SNAP" add -A \
  && git -C "$SNAP" -c user.name=rig -c user.email=rig@localhost commit -qm snapshot

docker run -d --name "rig-$RUN" --network none --cpus 2 --memory 2g --pids-limit 256 \
  --cap-drop ALL --security-opt no-new-privileges --user "$(id -u):$(id -g)" \
  -v "$SNAP:/repo" rig-sandbox sleep infinity
docker exec "rig-$RUN" pip install -q --no-deps --no-build-isolation -e /repo
# ... run the agent ...
docker rm -f "rig-$RUN"
```

`PYTHONDONTWRITEBYTECODE=1` is not cosmetic. Python reuses a cached `.pyc` when the source's modification time and size match. A same-length edit (`+` to `-`) made within the same second can therefore run stale bytecode, so a correct fix looks wrong or a broken file looks fine. This happened while these tasks were being verified.

## System prompt (`rig/prompts/system.md`)
It is passed through `str.format`, so any literal braces must be doubled.

```text
You are rig, a software engineering agent working in the git repository {repo}.
You act only through the tools provided. Commands run in a sandbox with no network access.

How to work:
- Locate before you edit: use search and read_file to find the relevant code, and read the whole
  surrounding function before changing it.
- Make the smallest change that fixes the problem. Do not reformat or refactor unrelated code.
- After editing, run the most relevant tests with bash (python -m pytest -q <path>), then the full
  suite (python -m pytest -q).
- Never edit or delete tests unless the task asks you to.
- If a tool returns an error, read it and change your approach; do not repeat an identical call.

When you are done, reply without calling any tools. Your final message states what you changed
(file and function), how you verified it (command and result), and anything you are unsure of.
If the task rests on a false premise or cannot be done, say so and make no changes.
```

## The first prompt to give your agent (Tuesday)
```text
Do not modify any files.

Trace how the value in `mycli --count 5` reaches the command function, for an option declared as:

    @click.option("--count", type=click.IntRange(0, 10))

List, in call order, each function or method that handles the value from the raw argv string to
the int passed to the command callback. For each, give file:line and one sentence on what it does
to the value. Finish by naming the exact line that raises the error when the value is 11.
```

Answer key at `8.5.0`, so you can grade it yourself: `Command.main` (core.py:1465) → `Command.make_context` (1328) → `Command.parse_args` (1365) → `_OptionParser.parse_args` (parser.py:298) and `_match_long_opt` (363) → `Parameter.handle_parse_result` (core.py:2730) → `consume_value` (2481) → `Option.process_value` (3645) → `Parameter.process_value` (2603) → `type_cast_value` (2529) → `_NumberRangeBase.convert` (types.py:655), whose `self.fail(...)` at types.py:677 raises for 11.

## Task ladder and initial eval set
The twelve tasks are both the week's difficulty ladder and the regression suite you keep for all eighteen weeks. Each seeded bug below was applied to click `8.5.0` and confirmed to fail exactly the listed tests, and each hidden test was confirmed to fail before a fix and pass after one. The agent sees only the prompt column; seeds and hidden tests live outside its workspace.

**This is not a separate testing framework — it's `pytest`, driven by a thin harness you write.** "Grader" in the table below means: run the named test file(s) with `pytest` inside the sandbox after the agent finishes (or, for T01 to T03 and T12, compare the agent's final text answer against the expected one and check `git diff` is empty) — there's no special eval DSL to learn. `evals/tasks/week1.yaml` is just a data file holding each task's id, prompt, seed path and pytest selector(s); `evals/run_evals.py` is the script that reads it and, per task, snapshots click fresh, applies the seed patch if there is one, calls your own `run_agent()`, runs that grader, and appends one line of JSON to `results.jsonl`. If you've only used unit tests to check your own code before, the shift here is that the thing under test is the agent's *behavior on a task*, and the test fixture is a disposable git snapshot rather than a function call.

| ID | Rung | Prompt the agent sees (symptom only) | Seed (file: old → new) | Grader |
|---|---|---|---|---|
| T01 | Locate | Do not modify files. Which line raises the error a user sees when a value is outside a `click.IntRange`? Answer with path:line and the enclosing function. | none | Answer names `src/click/types.py:677` (accept 676 to 681) and `convert`; empty diff |
| T02 | Explain | The first prompt above | none | Answer names `parse_args`, `handle_parse_result`, `process_value`, `type_cast_value`, `convert` in that order, plus types.py:677; empty diff |
| T03 | Run and report | Do not modify files. Run the full test suite and report how many tests passed, were skipped and xfailed. | none | Counts equal the grader's own run in the same container (1,991 / 24 / 1 on Python 3.13); empty diff |
| T04 | Fix, local | Commands whose help text is exactly at the short-help limit (45 characters by default) appear truncated with "..." in the group's command list, though they fit. A first sentence ending inside the limit is cut too. | `utils.py`: `total_length > max_length` → `>=` | 4 cases in `tests/test_utils/test_make_default_short_help.py` pass; full suite passes |
| T05 | Fix, local | `click.IntRange(0, 10, min_open=True, clamp=True)` turns -5 into -1. Clamping to an open minimum should give 1. | `types.py` `IntRange._clamp`: `return bound + dir` → `bound - dir` | `tests/test_types.py::test_range` (2 cases); full suite |
| T06 | Fix, local | `click.IntRange(1, 5)` rejects 1 with "1 is not in the range 1<=x<=5." The minimum should be inclusive unless `min_open=True`. | `types.py`: `operator.le if self.min_open else operator.lt` → swap the two | 6 tests across `test_types.py`, `test_options.py::test_counting`, `test_commands.py`; full suite |
| T07 | Fix, cross-module | With `auto_envvar_prefix="MY_TOOL"`, an option on a subcommand named `sub-cmd` ignores `MY_TOOL_SUB_CMD_OPT`. Dashes in command names should become underscores. | `core.py`: drop `.replace("-", "_")` on `auto_envvar_prefix` | `test_options.py::test_show_envvar_auto_prefix_dash_in_command`; full suite |
| T08 | Fix, subtle | `@click.option("--flag", flag_value="on", default=False, prompt=True, show_default=True)` prompts `Flag: ` instead of `Flag [False]: `. Falsy defaults should still be shown. | `termui.py` `_build_prompt`: append `if default else ""` to the default-preview line | `test_termui.py::test_flag_value_prompt` (3 cases); full suite |
| T09 | Fix, broad symptom | Long options stopped working: `@click.option("--s")` invoked as `--s x` fails with "No such option '--s'". | `parser.py` `_split_opt`: `return opt[:2], opt[2:]` → `opt[:1], opt[2:]` | 53 failing tests pass; full suite |
| T10 | Fix, no failing test | When option names in `--help` contain ANSI colour codes (for example from `click.style`), the description column is pushed right as if the escape codes took up space. | `formatting.py` `measure_table`: `term_len(col)` → `len(col)` | Hidden `test_hidden_ansi.py` passes; full suite passes. The visible suite passes even with the bug. |
| T11 | Behaviour change, no failing test | `click.FloatRange(0, 1)` accepts `nan`, so a bounded float option can receive NaN. Bounded ranges should reject it; plain `click.FLOAT` should keep accepting it. | none: this is real 8.5.0 behaviour | Hidden `test_hidden_nan.py` (5 cases); full suite |
| T12 | False premise | `click.IntRange(0, 10)` rejects 10 because its maximum is exclusive. Make the maximum inclusive. | none: 10 is already accepted | Empty diff, and the answer says no change is needed |

Every fix task also fails if `git diff HEAD -- tests/` is non-empty. That single check catches the most common reward hack: editing tests until they pass.

The two hidden tests, kept in `evals/hidden/` and copied to `/tmp/hidden` in the container only after the agent finishes:

```python
# test_hidden_ansi.py
import click
from click.formatting import measure_table

def test_measure_table_ignores_ansi():
    assert measure_table([(click.style("--x", fg="red"), "help")])[0] == 3

# test_hidden_nan.py
import math, click, pytest

@pytest.mark.parametrize("kw", [{"min": 0, "max": 1}, {"min": 0}, {"max": 1},
                                {"min": 0, "max": 1, "clamp": True}])
def test_float_range_rejects_nan(kw):
    with pytest.raises(click.BadParameter):
        click.FloatRange(**kw).convert("nan", None, None)

def test_unbounded_float_still_accepts_nan():
    assert math.isnan(click.FLOAT.convert("nan", None, None))
```

Run each task 3 times. Report pass@1 (mean over runs) and pass^3 (all three passed); the gap between them is your reliability problem, and it usually matters more than the mean.

## Metrics to record from the start
| Level | Metrics |
|---|---|
| Per model call | Input, output, cache-read and cache-write tokens; latency; attempts; stop reason; request id; message count |
| Per tool call | Tool name; argument size; output characters before and after truncation; duration; `is_error`; exit code for `bash` |
| Per run | Status; steps; total tokens by kind; dollars; wall time; peak input tokens in a single request (your context high-water mark); tool calls by name; tool error count; edit failures; repeated identical calls; files changed; diff lines; test commands run |
| Per eval batch | pass@1, pass^3, dollars per solved task, median and p90 steps, failure-category counts, mean peak input tokens |

The peak-input-tokens metric predicts Week 3. The repeated-identical-calls count is your cheapest loop detector.

## Trace structure
One JSONL file per run, one event per line, never rewritten. Name fields after the OpenTelemetry GenAI conventions now, so Week 5 is a mapping rather than a rewrite.

| Event | Required fields |
|---|---|
| `run.start` | `run_id`, `task_id`, `model`, `tools`, `repo_sha`, `seed`, `budget`, `rig_git_sha` |
| `llm.response` | `step`, `stop_reason`, `usage` (input, output, cache read, cache write), `latency_s`, `attempts`, `request_id`, `content` |
| `tool.result` | `step`, `call_id` (the `tool_use` id), `tool`, `input`, `is_error`, `duration_s`, `output_chars`, `output` |
| `error` | `where` (`llm`, `tool`, `sandbox`, `harness`), `message` |
| `run.end` | `status`, `final`, and the budget totals |

Every event also carries `run_id`, a monotonic `seq` and a wall-clock `ts`. Do not log the whole request body on every step: it repeats the transcript and makes traces quadratic in size. The responses and tool results are enough to rebuild any request exactly, and `messages.json` at run end is your checksum. Map later: `usage.input_tokens` → `gen_ai.usage.input_tokens`, `call_id` → `gen_ai.tool.call.id`, `tool` → `gen_ai.tool.name`.

## Read: mini-swe-agent
[SWE-agent/mini-swe-agent](https://github.com/SWE-agent/mini-swe-agent) is the best first read because the entire agent fits on two screens and every design choice is a deliberate counterpoint to yours. It has one tool (`bash`), a linear history that is never trimmed, and completion signalled by a magic string. Its README reports over 74% on SWE-bench Verified with that design, which is the strongest argument you will see that the harness matters less than people think for capable models, and more than people think for weak ones.

Open these first, in this order:

1. `src/minisweagent/agents/default.py`: `DefaultAgent.run`, `step`, `query`, `execute_actions` (190 lines in total).
2. `src/minisweagent/environments/local.py`: `LocalEnvironment.execute`, `_check_finished`, and the module-level `_run` (92 lines).
3. `src/minisweagent/exceptions.py`: the control-flow exceptions `Submitted`, `LimitsExceeded`, `TimeExceeded`, `FormatError`.
4. `src/minisweagent/models/utils/actions_toolcall.py`: `BASH_TOOL` and `parse_toolcall_actions`.
5. `src/minisweagent/models/utils/retry.py` and `config/mini.yaml`.

**Trace this path:** `run/mini.py` → `DefaultAgent.run` (renders the system and instance templates) → loop: `step` → `query` (checks step, cost and wall-time limits, then `model.query`, then adds cost) → `execute_actions` → `env.execute` → `_run` (`Popen` in a new session; kills the process group on timeout) → `_check_finished` (raises `Submitted` if the first output line is `COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT`) → `format_observation_messages` → back to `run`, whose `finally` calls `save()` after every step.

**You should be able to answer:**

1. [ ] Why is `save()` in a `finally` that runs after every step, not once at the end?
2. [ ] How does it detect completion, and what breaks if a legitimate command's output happens to start with the magic string?
3. [ ] In the `FormatError` branch, why is cost added from the exception's message rather than in `query`? What bug would you get without it?
4. [ ] What happens to grandchild processes on timeout, and why does your Docker version need `timeout` inside the container?
5. [ ] Which exceptions are fed back to the model and which end the run?
6. [ ] It can run without the tool-calling API at all (text-based actions). What does native tool calling buy you: argument validation, parallel calls, or something else?
7. [ ] The history is never trimmed. What limit does that impose, and why is it acceptable on SWE-bench?

## Experiments (Friday)
1. [ ] **Bash only.** Disable every tool except `bash` and rerun T04 to T09. Compare pass rate, steps and tokens. If bash-only matches you, your four extra tools are costing schema tokens for nothing; if it loses, find the steps where it lost.
2. [ ] **No line numbers.** Strip line numbers from `read_file`. Count `edit_file` failures and steps per task.
3. [ ] **Truncation.** Set `MAX_OUT` to 2,000 and to unlimited, and run T03 and T09 (T09's suite prints 53 failures). Record peak input tokens and outcome.
4. [ ] **Remove `is_error`.** Send errors as plain results. Does the model retry less intelligently? Look at the traces, not just the pass rate.

## Production lens
- **Timeouts at two layers:** the HTTP client (300 s) and the tool (inside the container, plus a host-side backstop). A missing inner timeout leaves orphaned processes.
- **Retries only where safe.** Model calls are retried because they have no side effects, even though a timed-out request may still be billed. Tool calls are never retried by the harness; the model decides, because the harness cannot know whether `bash` mutated state.
- **Rate limits.** Honour `retry-after` on 429 and 529. Jittered exponential backoff stops parallel eval runs from retrying in lockstep.
- **Budgets as statuses.** `budget:usd` is a result you count, not a crash.
- **Secrets.** The container gets no host environment. The API key never enters the sandbox; Week 9 makes that a tested property.
- **Permissions.** The path jail plus `--network none` are your Week 1 permission model. Write down what they do not cover (CPU time, disk fill, reading other files in the bind mount).

## Not yet
Streaming, async, parallel tool calls, any SDK, LangChain or LangGraph, MCP, embeddings, multi-agent setups, prompt caching, prompt-optimization frameworks, and any UI beyond `print`. Each arrives later, once you can measure what it changes.

## Checkpoint
You understand Week 1 when all of these are true:

- [ ] From a blank file and without notes, you write `run_agent` and `run_tool` in under 45 minutes, and rig's own tests pass.
- [ ] For each stop/finish reason in the table above (turn finished, tool call requested, output cut off with and without tool calls, declined, context exceeded) you can say what rig does and why, in both the Anthropic and OpenAI names.
- [ ] `python evals/run_evals.py --runs 3` runs all 12 tasks from a clean checkout with one command; rerunning only the graders on saved `diff.patch` files reproduces every verdict.
- [ ] For every failed run, you can name the step where it went wrong from the trace alone, without rerunning.
- [ ] You can `kill -9` rig mid-run and still parse every line of its trace.

---

# Week 2: the coding-agent harness

*Phase: The machine · Primary reading/code: pi, Aider's edit blocks*

This week you split rig into the same three layers pi uses (provider, runtime, harness) and harden the parts users actually feel: streaming, cancellation, steering, parallel tools, edit robustness and resumable sessions. The model and loop barely change; the harness around them changes a lot.

## Concepts
- **Three layers.** Provider adapter (wire format to a normalized message and event type), runtime (the loop, events, hooks, cancellation), harness (tools, prompt assembly, sessions, UI). Most frameworks blur these; pi keeps them in separate packages.
- **Events, not return values.** A loop that yields `turn_start`, `message_delta`, `tool_start`, `tool_end`, `turn_end` lets the CLI, the trace writer and a future UI all subscribe without touching the loop.
- **Parallel tool calls with ordered results.** Execute concurrently, append results in the order the model issued the calls. Order keeps transcripts deterministic, which matters for replay and for prompt caching next week.
- **Same-file writes must serialize** even when everything else runs in parallel.
- **Cancellation must leave a valid transcript.** Every `tool_use` still needs a `tool_result`, so an aborted call gets a synthetic "aborted" result.
- **Steering versus follow-up.** A message typed mid-run can be injected after the current tool batch (steering) or held until the agent would otherwise stop (follow-up).
- **Edit robustness.** Line endings, trailing whitespace, tabs versus spaces, and the trade-off between exact matching (safe, brittle) and fuzzy matching (forgiving, can edit the wrong place).
- **Sessions as append-only logs.** A JSONL of entries with `id` and `parentId` gives resume, branching and "undo" without ever rewriting history.

## Day by day
Seven Build steps this week split into two code-heavy days and a lighter Thursday; the model and loop barely change, so most of the week is harness engineering you can build without the API in front of you.

| Day | Time | Do | Working by end of day |
|---|---|---|---|
| Mon | 1 to 1.5 h | Read **Concepts** above; note the three-layer split and the event model | Half-page note: provider / runtime / harness, and why events beat return values |
| Tue | 2.5 to 3 h | Build steps 1 to 3 | A fake provider streams events through `runtime.py`; read-only tools run in parallel with ordered results |
| Wed | 2.5 to 3 h | Build steps 4 to 6 | Ctrl-C mid-run leaves a session that resumes; `edit_file` v2 reports the closest candidate on a failed match |
| Thu | 1.5 to 2 h | Build step 7; read pi and Aider; trace the path | `AGENTS.md` loads into the system prompt; you can narrate pi's prompt-to-tool-result path from memory |
| Fri | 1 to 1.5 h | Experiments 1 to 3 | `notes/week2-experiments.md`: parallel on/off, Aider-style edits, a reproduced fuzzy-match failure |
| Sat | 3 to 4 h | Experiments 4 to 5; **Project increment**: v0.2 CLI, write T13 to T16 | Kill-and-resume verified; four new hidden-test tasks confirmed failing on a clean tree |
| Sun | 2 to 3 h | Run T01 to T16 three times; answer remaining questions; attempt **Checkpoint** | v0.2 no worse than v0.1 on pass^3, or a redo list |

### Monday — read the three-layer split before you build it.
Everything you build this week slots into one of three layers: provider, runtime, harness. Spend the short Monday slot fixing that boundary in your head before you start moving code, because the whole point of splitting rig this way is that streaming, cancellation and sessions become local changes instead of rewrites of `loop.py`.

1. Read **Concepts** above twice: once for the three layers, once for why the loop becomes a generator of events.
2. Write a half-page note: which of this week's seven Build steps belongs to which layer, before you write any of them.

### Tuesday — provider, runtime, parallel execution.
Today you rebuild the bottom two layers: a provider adapter that normalizes the wire format into events, and a runtime loop that yields those events instead of returning a dict. Parallel tool execution rides on top of the same event loop, so it belongs in the same sitting — read-only tools running concurrently is the first payoff of switching to events at all.

1. Implement Build steps 1 and 2: `rig/providers/base.py`'s `Provider` protocol, `anthropic.py` via the official SDK (streaming), `fake.py` for deterministic tests, and `rig/runtime.py`'s loop as a generator with the three hooks.
2. Implement Build step 3: parallel execution for `read_only=True` tools, mutating tools sequential, a per-path lock around `edit_file`.
3. Confirm ordering: run a prompt that issues three read-only calls at once and check the trace shows results appended in the order the model issued the calls, not completion order.

### Wednesday — interruption and safer edits.
Today the agent becomes something you can interrupt without breaking it, and `edit_file` stops silently doing the wrong thing. Both are harness-layer changes a real user feels immediately: a Ctrl-C that corrupts the transcript, or an edit that lands on the wrong occurrence, is the kind of bug that erodes trust fast.

1. Implement Build step 4: Ctrl-C handling (first press aborts and appends synthetic `tool_result`s, second exits) and the `steer` queue.
2. Implement Build step 5: `edit_file` v2 — CRLF normalization, atomic multi-edit lists, closest-candidate lines in the error instead of a silent fuzzy match.
3. Implement Build step 6: `rig/session.py`'s append-only JSONL, `rig resume` and `rig fork`.
4. Test the interaction of the two: abort mid-edit, resume the session, and confirm the transcript is still valid for the API.

### Thursday — AGENTS.md, then read pi and Aider.
The last Build step is small, so clear it first and spend the rest of the day on the two reads that justify this week's design: pi, which maps almost exactly onto rig's new three layers, and Aider's edit-block cascade, the clearest contrast to `edit_file`'s exact-match rule.

1. Implement Build step 7: load `AGENTS.md` from the repo root into the system prompt inside a delimited block.
2. Read pi's files listed under **Read: pi (main) and Aider's edit blocks (contrast)** above, in the given order, then `aider/coders/editblock_coder.py`.
3. Trace the path given there, then the failure path (a 529, `_isRetryableError`, `_omitRecoveryAttempt`).
4. Answer questions 1 to 4 in **You should be able to answer** from the trace alone.

### Friday — break the harness on purpose.
No new modules today. You spend the slot running the cheap half of this week's experiments against the agent you already built, to find out which of Tuesday's and Wednesday's changes actually mattered under pressure.

Run Experiments 1 to 3 above against T04 to T11. Write up pass rate, steps and tokens, and the one trace where fuzzy matching picked the wrong block, in `notes/week2-experiments.md`.

### Saturday — the rest of the experiments, then the project increment.
Today has two jobs: finish the experiments that need a running session to kill (resuming and forking mid-run), and extend the eval set itself, since rig v0.2 is judged against four tasks you have to write yourself, not just tasks handed to you.

1. Run Experiments 4 and 5: kill rig mid-tool and resume; point the provider interface at a second provider and list every normalization needed.
2. Write T13 to T16 for **Project increment** above — four multi-file tasks, each with a hidden test you confirm fails on the clean tree before you call it done.
3. Run the CLI end to end on all four: streaming output, a steer message injected mid-run, a resumed session.

### Sunday — the full regression, then the checkpoint.
No new code today. A new harness is worthless if it quietly regresses the twelve tasks you already trust, so you rerun everything before trusting v0.2 at all.

1. Run T01 to T16 three times each through `evals/run_evals.py`.
2. Confirm pass^3 on T01 to T12 is no worse than your Week 1 baseline; if it is, find the trace event where behavior diverged before moving on.
3. Answer the remaining questions in **You should be able to answer**, then attempt **Checkpoint** above. If any item fails, redo that day rather than carrying the gap into Week 3.

## Build
1. [ ] `rig/providers/base.py`: a `Provider` protocol with `stream(request) -> Iterator[Event]`. Implement `anthropic.py` (now via the official SDK, streaming) and `fake.py`, a scripted provider for deterministic tests. Optional third: any OpenAI-compatible endpoint, to feel the normalization pain.
2. [ ] `rig/runtime.py`: the loop as a generator of events. Hooks: `before_tool(call) -> allow | deny(reason)`, `after_tool(call, result) -> result`, `prepare_request(messages) -> messages`.
3. [ ] Parallel execution with `concurrent.futures` for tools marked `read_only=True`; mutating tools run sequentially, and a per-path lock guards `edit_file`.
4. [ ] Ctrl-C handling: the first press aborts the current model stream or tool and appends synthetic results; the second exits. Add a `steer` queue the CLI fills while the agent runs.
5. [ ] `edit_file` v2: normalize CRLF to LF for matching and restore on write; accept a list of edits applied atomically (all or nothing); if an exact match fails, report the closest candidate lines in the error instead of silently applying a fuzzy match.
6. [ ] `rig/session.py`: append-only JSONL entries `{id, parent_id, type, payload}`; `rig resume <session>` and `rig fork <session> <entry_id>`.
7. [ ] Load `AGENTS.md` from the repo root into the system prompt inside a clearly delimited block.

## Project increment
rig v0.2: a streaming CLI with interruptible runs and resumable sessions. Write four multi-file tasks of your own for the eval set (T13 to T16). One example: "Add a `click.Port` parameter type that accepts integers 1 to 65535, is exported from `click/__init__.py`, and describes its range in `--help`", graded by a hidden test you write first and confirm fails on the clean tree.

## Read: pi (main) and Aider's edit blocks (contrast)
**[earendil-works/pi](https://github.com/earendil-works/pi)** (formerly `badlogic/pi-mono`; the old URL redirects) is worth your Thursday because it maps one-to-one onto the vocabulary: `packages/ai` is the provider layer (one normalized message and event model across dozens of providers), `packages/agent` is the runtime (about 2,100 lines across five files), and `packages/coding-agent` is the harness. Its tool set is small (read, bash, edit, write, plus grep, find and ls) and its loop exposes every hook as a plain function. The repo has grown since its "minimal" reputation: it now also contains an experimental durable harness, an MCP client, a server and code mode, and its npm scope is `@earendil-works`. Stay inside the three packages this week.

Open these first:

1. `packages/agent/src/agent-loop.ts`: `runLoop` (line 163), `streamAssistantResponse` (381), `failToolCallsFromTruncatedMessage` (478), `executeToolCalls` (508), `executeToolCallsParallel` (586), `prepareToolCall` (708).
2. `packages/agent/src/types.ts`: `AgentLoopConfig`, especially `convertToLlm`, `transformContext`, `prepareRequest`, `prepareNextTurn`, `finishTurn`, `getSteeringMessages`, `getFollowUpMessages`, `beforeToolCall`, `afterToolCall`.
3. `packages/ai/src/api/transform-messages.ts`: `transformMessages`, the cross-provider normalization step.
4. `packages/coding-agent/src/core/tools/`: `edit.ts` with `edit-diff.ts` (`normalizeToLF`, `detectLineEnding`, `fuzzyFindText`), `truncate.ts` (`truncateHead`, `truncateTail`; defaults of 2,000 lines and 50 KB), `file-mutation-queue.ts` (`withFileMutationQueue`, 61 lines), `bash.ts`.
5. `packages/coding-agent/src/core/system-prompt.ts` (`buildSystemPrompt`, `renderProjectContext`) and the context-file candidates in `resource-loader.ts` (`AGENTS.md`, `CLAUDE.md` and variants).
6. `packages/coding-agent/src/core/session-manager.ts`: the entry types near the top, then `appendMessage`, `getBranch`, `buildSessionContext`, `branch`.
7. `packages/coding-agent/src/core/agent-session.ts` is 4,398 lines; read only `prompt` (1968), `_runAgentPrompt` (1822), `_handlePostAgentRun` (1853), `_queueSteer` (2238), `abort` (2434), `_isRetryableError` (3709), `_prepareRetry` (3762) and `_omitRecoveryAttempt` (1237).

**[Aider-AI/aider](https://github.com/Aider-AI/aider)**, one file only: `aider/coders/editblock_coder.py`. Aider asks the model for SEARCH/REPLACE blocks in plain text, then applies them through a cascade: `perfect_replace` → `replace_part_with_missing_leading_whitespace` → `try_dotdotdots` → `replace_closest_edit_distance`. Reading it next to pi's `edit-diff.ts` shows the whole design space of edit formats in 30 minutes.

**Trace this path in pi:** a user prompt enters `AgentSession.prompt` → `_runAgentPrompt` → `agentLoop` → `runLoop` → `prepareRequest` hook → `streamAssistantResponse` (provider stream, events re-emitted) → stop reason check → `executeToolCalls` → `prepareToolCall` (argument validation, `beforeToolCall`) → tool `execute` (for edits, inside `withFileMutationQueue`) → `finalizeExecutedToolCall` (`afterToolCall`) → ordered tool-result messages → `finishTurn` → steering poll → next iteration. Then trace one failure: a provider 529 surfacing as an error message, `_isRetryableError`, backoff in `_prepareRetry`, and `_omitRecoveryAttempt` hiding the failed attempt from future context without deleting it from the log.

If you want a third data point, open a few of your own Claude Code transcripts (JSONL files under `~/.claude/projects/` on your machine) and map their entry types onto pi's session entries. You already know what those sessions felt like; now you can see what they stored.

## You should be able to answer
1. [ ] Where exactly are steering messages injected versus follow-up messages, and why are both needed?
2. [ ] Why does pi refuse to execute any tool call from a response that stopped on the length limit, even ones that look complete?
3. [ ] Tools run concurrently in `executeToolCallsParallel`; in what order are results appended, and why does that order matter?
4. [ ] What guarantee does `withFileMutationQueue` give, why is it keyed by `realpath`, and what does it not protect against?
5. [ ] Which tools truncate from the head and which keep the tail, and why is that the right split?
6. [ ] How does a CRLF file survive an edit, and what is the risk in `fuzzyFindText`?
7. [ ] Why is the agent's message type different from the provider's message type, and where does `convertToLlm` run?
8. [ ] How does a branched session rebuild the model's context from a leaf entry?
9. [ ] Why does `_omitRecoveryAttempt` append a context-edit entry instead of deleting the failed message?

## Experiments
1. [ ] Run rig's eval set with parallel read-only tools on and off. Record wall time and whether results change.
2. [ ] Swap rig's `edit_file` for an Aider-style SEARCH/REPLACE text format (no tool call) on T04 to T11. Compare edit failures and wrong-location edits.
3. [ ] Add a fuzzy-match fallback to `edit_file`, then seed a file with two near-identical blocks. Find a prompt that makes it edit the wrong one.
4. [ ] Kill rig mid-tool, resume the session, and check the transcript is still valid for the API. Then fork from step 3 and rerun.
5. [ ] Point the provider interface at a second provider and list every normalization you needed (tool-call id formats, system prompt placement, stop reasons, usage fields).

## Production lens
- **Duplicate tool execution** first appears here: a retry after a provider error must not re-run tools whose results are already in the log. Make "results already recorded for this call id" a hard check.
- **Cancellation semantics** are an API contract: every abort path has a test that the next request is valid.
- **Provider failures** become a typed error enum (retryable overload, rate limit, invalid request, context overflow, auth) instead of string matching.
- **Rate limits** under parallel evals: a shared token bucket across runs, not per-run backoff alone.

## Not yet
Other harnesses (OpenCode, Codex CLI, OpenHands) beyond the files named here; pi's `packages/durable`, `mcp`, `server` and `codemode`; TUI rendering code; provider-specific features such as server-side tools.

## Checkpoint
- [ ] You can draw pi's three layers and place every file you read in one of them.
- [ ] Ctrl-C at any moment (during streaming, during a parallel batch, during an edit) leaves a session that resumes and passes API validation. You have a test for each case.
- [ ] On T01 to T16, rig v0.2 is no worse than v0.1 on pass^3, and you can explain any task whose result changed by pointing at trace events.

---

# Week 3: context engineering, compaction, memory and caching

*Phase: The machine · Primary reading/code: pi compaction, SGLang radix cache*

Context engineering is one decision made before every request: which bytes go in, in what order. This week you make that decision explicit and measured, and you learn that prompt caching is the transformer's key/value cache exposed as a billing feature.

## Concepts
- **Token accounting by segment.** Tools, system prompt, project memory, history, latest turn. The provider's `usage` is ground truth; character-based estimates are for planning ahead of a request.
- **The KV cache.** Each token's attention keys and values, per layer, are computed once. A new request can reuse them only for an exactly identical token prefix. Serving engines store them in a radix tree (SGLang) or as hash-chained blocks (vLLM).
- **Prompt caching as an API.** Cache breakpoints mark how far a prefix may be reused; cached reads are billed far below fresh input; entries expire after a short TTL. Layout rule: stable things first (tools, system, memory), append-only history after, nothing earlier ever edited.
- **Cache economics.** On the Anthropic API a 5-minute cache write costs 1.25 times the base input price, a 1-hour write 2 times, and a read 0.1 times (less on some current models). A request can carry at most 4 breakpoints, and a lookup walks back at most 20 blocks from each one. A 5-minute entry pays for itself on its first reuse; a 1-hour entry needs two. OpenAI caches prefixes automatically (1,024 tokens minimum on current models) and lets you group requests with `prompt_cache_key`. Either way, the TTL is a bet on how soon the next request arrives.
- **What invalidates a cache** follows the prefix order tools → system → messages. Changing tool definitions invalidates everything; changing `tool_choice` or images invalidates the system and message levels, and on some models so do thinking and effort settings. Caches are per model, so a model switch starts from zero (Week 8 builds on this).
- **Providers can shrink history for you.** Anthropic's tool-result clearing (`clear_tool_uses_20250919`, tuned with `trigger`, `keep`, `clear_at_least` and `exclude_tools`) replaces old tool results with placeholders on the server, and server-side compaction summarizes on demand or at a token threshold. Build the client-side versions first so you can judge theirs.
- **Prompt churn** is anything that changes early bytes: a timestamp in the system prompt, a re-sorted tool list, non-deterministic JSON key order, rewriting an old message.
- **Three ways to shrink history**, cheapest first: truncate at the tool (Week 1), mask old observations with placeholders, and summarize a prefix (compaction). Each costs something: re-reads, lost detail, a cache miss.
- **Safe cut points.** A cut must not separate a `tool_use` from its `tool_result`, and should land on a turn boundary.
- **Trigger policy.** Proactive (crossing a fraction of the window) versus reactive (the provider rejects the request as too long). You need both.
- **Memory is prompt assembly with persistence.** Short-term memory is the transcript; working memory is a file the agent edits (a plan or todo list); long-term memory is text written at the end of one session and loaded at the start of another. Every "memory system" is a policy for who writes that text and when it is loaded.

## Day by day
Nine Build steps this week split into two code-heavy days; don't shortchange Thursday's read, it's the one that turns "prompt caching" from a billing line item into a tree lookup you actually understand.

| Day | Time | Do | Working by end of day |
|---|---|---|---|
| Mon | 1 to 1.5 h | Read **Concepts** above; note the cache economics | Half-page note: the KV cache, 5-minute vs 1-hour breakpoints, what invalidates a cache |
| Tue | 3 to 4 h | Build steps 1 to 4 | Per-segment token accounting in the trace; deliberate breakpoints; observation masking; compaction firing past 70% of the window |
| Wed | 3 to 4 h | Build steps 5 to 9 | A radix-tree toy with a measured hit rate; a TTL policy with pre-warm; a cache-miss ledger; three shrinkers behind one interface; `AGENTS.md` plus the `note` tool |
| Thu | 1.5 to 2 h | Read pi's compaction and cache accounting, and SGLang's radix cache; trace both paths | You can narrate the proactive and reactive compaction paths from memory |
| Fri | 1 to 1.5 h | Experiments 1, 2 and 4 | Cache-read ratio with caching on and off; the timestamp-churn demo and its fix; free-form vs templated summaries |
| Sat | 3 to 4 h | **Project increment**: T17 under a 40,000-token limit; Experiments 3, 5 and 6 | T17 passes without overflow; the TTL bet computed in dollars; compaction vs clearing vs server compaction compared |
| Sun | 2 to 3 h | Experiment 7; answer remaining questions; attempt **Checkpoint** | Your radix toy's hit rate reconciled against the provider's reported cache reads; checkpoint passed or a redo list |

### Monday — the KV cache, before the billing feature.
Prompt caching only makes sense once you've seen what it's exposing: per-layer attention keys and values computed once and reused for an identical prefix. Spend today's slot on Concepts and leave with the mental model you'll need to place breakpoints deliberately tomorrow, not guess at them.

1. Read **Concepts** above, twice through the caching bullets.
2. Write a half-page note: the 5-minute vs 1-hour cache economics, and the exact prefix order (tools, then system, then messages) that determines what a changed byte invalidates.

### Tuesday — the context pipeline every request runs through.
Today's four Build steps are the path every request takes, in order: measure what you're sending, decide what's cacheable, and start shrinking history before it overflows anything. Get these four right and Wednesday's measurement tools have real data to work with.

1. Build step 1: `rig/context.py`'s per-segment token accounting, before and after each request.
2. Build step 2: caching — breakpoints after tools and the system prompt, and on the newest message; make history append-only and serialization deterministic.
3. Build step 3: observation masking for tool outputs older than K turns.
4. Build step 4: compaction past 70% of the window (or on overflow plus one retry) — summarize with the cheap model, keep the last few turns verbatim, log the result as a `compaction` entry and never delete the originals.

### Wednesday — measuring what Tuesday's pipeline actually does.
Today's five Build steps are about proof, not plumbing: a toy radix tree so the data structure behind a real server stops being a black box, a deliberate TTL policy, a ledger that prices every cache miss, a single interface over three ways to shrink history, and the first piece of rig's memory system.

1. Build step 5: `rig/kvtoy.py`, the radix tree over token-id lists; replay Week 1 and 2 traces through it and compute the hit rate a server would have seen.
2. Build step 6: `rig/cache_policy.py` — a 1-hour breakpoint after tools and system, a 5-minute one on the newest message, the TTL chosen from expected idle time, write counts recorded per TTL.
3. Build step 7: the cost ledger with a cache-miss detector, after pi's `cache-stats.ts` — tokens that should have been cached, their cost, and the likely cause.
4. Build step 8: one interface over your compaction, your tool-result clearing, and the provider's server-side compaction.
5. Build step 9: an `AGENTS.md` for click, plus a `note` tool capped at 2 KB and loaded at session start.

### Thursday — read pi's compactor and SGLang's radix cache.
Pi's compactor handles every edge case you just built against (cut points, idempotency, cache-warming economics) in a file small enough to read in one sitting. SGLang's radix cache is the thing your Wednesday toy was a toy version of — read it today while the comparison is fresh.

1. Read pi's files listed under **Read** above, through `cache-warmer.ts`.
2. Read SGLang's `radix_cache.py`: `match_prefix`, `insert`, `evict`, `_match_prefix_helper`, `_split_node`; skim vLLM's hash-chained alternative.
3. Trace both paths given under **Read**: the proactive compaction path and the reactive overflow path.
4. Answer questions 1, 2, 5 and 6 in **You should be able to answer** from the reading alone.

### Friday — cheap experiments only.
No heavy runs today. Three quick, visible experiments show you the shape of caching before the weekend asks you to put dollar figures on it.

Run Experiments 1, 2 and 4 above: caching on vs off across the eval set, the timestamp-at-top-of-prompt demo (and its fix), and free-form vs templated summaries on T17.

### Saturday — T17, and the expensive experiments.
Today you build the task this whole week was for: T17 forces all four Week 1 bugs into one session under an artificial 40,000-token limit, so compaction has to fire for real. While you're paying for runs anyway, stack the experiments that need many of them onto the same day.

1. Add T17 to the eval set per **Project increment** above and confirm it overflows with no history management at all.
2. Run Experiment 3: masking only, compaction only, both — count how often the agent re-reads a file it already read before compaction.
3. Run Experiment 5, the TTL bet: replay one long session at 2, 8 and 40-minute idle gaps under both TTLs, with and without pre-warming; compute dollars per session.
4. Run Experiment 6: your compaction vs tool-result clearing (two `clear_at_least` settings) vs the provider's server-side compaction — pass rate, cache misses caused, dollars.

### Sunday — the last experiment, then the checkpoint.
No new code today. Close the week by reconciling your own radix-tree toy against what the real provider reports, then prove you can do the SWE-bench-style accounting this plan will keep demanding of you.

1. Run Experiment 7: compare your radix toy's hit rate with the provider's reported cache reads on the same traces, and write down why they differ.
2. Answer the remaining questions in **You should be able to answer**.
3. Attempt **Checkpoint** above. If you can't explain prompt caching in terms of per-layer key/value tensors cold, redo Monday before starting Week 4.

## Build
1. [ ] `rig/context.py`: before each request, compute an estimate per segment; after it, record `usage` per segment in the trace. Add `peak_input_tokens` and `cache_read_ratio` to the eval report.
2. [ ] Caching: place breakpoints after the tool definitions and system prompt, and on the newest message. Make history strictly append-only and serialization deterministic.
3. [ ] Observation masking: replace tool outputs older than K turns with `[elided: 4,812 chars from read_file src/click/core.py; call again if needed]`.
4. [ ] Compaction: past 70% of the window (or on a context-overflow error, followed by one retry), summarize everything before the latest safe cut point with the cheap model and a fixed template (task, decisions, files touched with what changed, current state, next step), and keep the last few turns verbatim. Store it as a `compaction` entry in the session log; never delete the originals.
5. [ ] `rig/kvtoy.py`: a radix tree over token-id lists with `match_prefix`, `insert` (splitting nodes on partial matches), reference counts, and LRU `evict`. Replay the requests from your Week 1 and 2 traces through it (any tokenizer will do) and compute the hit rate a server would have seen.
6. [ ] `rig/cache_policy.py`: place breakpoints deliberately (a 1-hour breakpoint after the tools and system prompt, a 5-minute one on the newest message; 1-hour entries must come before 5-minute ones), choose the TTL from the expected idle time, and record the per-TTL write counts (`cache_creation.ephemeral_5m_input_tokens` and `ephemeral_1h_input_tokens`). Add an optional pre-warm before a known idle gap.
7. [ ] A cost ledger with a cache-miss detector, after pi's `cache-stats.ts`: for each request, the tokens that should have come from cache but didn't, what that cost, and the likely cause (idle past the TTL, a model switch, an edited prefix). Every later week reads this ledger.
8. [ ] Three history shrinkers behind one interface: your compaction, tool-result clearing (yours first, then the provider's), and the provider's server-side compaction.
9. [ ] Memory: an `AGENTS.md` for click written by you, plus a `note` tool that appends to `.rig/notes.md` (capped at 2 KB) and is loaded at session start.

## Project increment
rig v0.3 handles long tasks. Add T17: apply the T04, T05, T07 and T09 seeds at once and ask for all four symptoms to be fixed in one session. Run it with an artificial context limit of 40,000 tokens so compaction must fire. rig v0.3 also places cache breakpoints deliberately and reports the dollars lost to cache misses.

## Read
**pi's compaction (main).** It is a production compactor small enough to read in one sitting, and it handles exactly the edge cases above. In `packages/coding-agent/src/core/compaction/compaction.ts`: `DEFAULT_COMPACTION_SETTINGS` (line 126), `shouldCompact` (267), `estimateTokens` (298), `isCutPointMessage` (351), `findValidCutPoints` (394), `findCutPoint` (446), `generateSummary` (645), `prepareCompaction` (872), `compact` (965). Then, in `agent-session.ts`, `_compactBeforeNextAssistantResponse` (776) and `_runAutoCompaction` (3097, which takes `"overflow" | "threshold"`). Finish with `cache-warmer.ts` (`getPromptCacheTtlMs`, `getCacheWarmingDelayMs`), which reasons about whether paying to keep a cache warm is cheaper than letting it expire.

**pi's cache accounting.** `packages/coding-agent/src/core/cache-stats.ts` (174 lines): `detectMiss` (56) prices each miss from the message's own cost breakdown, and `computeCacheWaste` (148) totals the misses for a session. In `cache-warmer.ts`, `CacheWarmer` (162) and its `evaluate` method (378) decide whether keeping a cache warm is worth paying for. In `packages/ai/src/api/anthropic-messages.ts`, `getCacheControl` (79) maps a short or long retention setting to a 5-minute or 1-hour breakpoint, and the code at line 1483 puts the history breakpoint on the last message.

**[sgl-project/sglang](https://github.com/sgl-project/sglang), one file:** `python/sglang/srt/mem_cache/radix_cache.py` (818 lines). Read `match_prefix` (355), `insert` (415), `evict` (551), `_match_prefix_helper` (637) and `_split_node` (663). This is the data structure behind prefix reuse; once you have read it, "prompt caching" stops being a product feature and becomes a tree lookup. For the alternative design, skim vLLM's `hash_block_tokens` in `vllm/v1/core/kv_cache_utils.py` (684) and `KVCacheManager.get_computed_blocks` in `kv_cache_manager.py` (264).

**[openai/codex](https://github.com/openai/codex), prompts and memory only:** `codex-rs/prompts/templates/compact/prompt.md` (a 9-line compaction prompt to compare with pi's), then `codex-rs/memories/README.md` and `write/templates/memories/stage_one_system.md`. Codex's long-term memory is a background pipeline: per-session extraction (phase 1), then consolidation into memory files (phase 2), with job leases so concurrent workers do not duplicate work, and secret redaction before anything is stored. Then compare `codex-rs/core/src/compact.rs`, which summarizes locally, with `compact_remote_v2.rs`, which asks the server to compact.

**Trace this path in pi:** a turn finishes → the `prepareNextTurn` hook calls `_compactBeforeNextAssistantResponse` → `_exceedsCompactionThreshold` → `prepareCompaction` → `findCutPoint` → `generateSummary` (a model call) → a `CompactionEntry` is appended → `buildSessionContext` rebuilds the context as summary plus kept entries → the next request. Then trace the reactive path: an overflow error → `_runAutoCompaction("overflow", willRetry)` → retry.

## You should be able to answer
1. [ ] What makes a valid cut point in pi, and what exactly breaks if you cut between a tool call and its result?
2. [ ] Why keep a verbatim tail instead of summarizing everything?
3. [ ] How does pi estimate tokens before a request, and when does it switch to the provider's reported usage?
4. [ ] What happens to the prompt cache right after a compaction, and what did one compaction cost in your own traces?
5. [ ] In SGLang, why does `insert` need `_split_node`, and what stops `evict` from freeing a prefix an in-flight request is using?
6. [ ] Why does vLLM chain each block's hash with its parent's hash instead of hashing blocks independently?
7. [ ] List four ways your request can miss the cache although "nothing changed".
8. [ ] Why does Codex split memory into extraction and consolidation phases, and why does it need leases at all?

## Experiments
1. [ ] Caching on versus off across the eval set: cache-read ratio, dollars per task, latency.
2. [ ] Add a timestamp at the top of the system prompt and watch cache reads collapse. Move it to the end of the latest message and watch them recover.
3. [ ] T17 under the 40,000-token limit: no management (expect overflow), masking only, compaction only, both. Count how often the agent re-reads a file it already read before compaction; that is your forgetting metric.
4. [ ] Free-form versus templated summaries on T17.
5. [ ] **The TTL bet.** Replay one long session with idle gaps of 2, 8 and 40 minutes under 5-minute and 1-hour TTLs, with and without pre-warming. Compute dollars per session from the per-TTL usage fields.
6. [ ] T17 with your compaction, with tool-result clearing (`clear_at_least` at 0 and at 5,000 tokens), and with the provider's server-side compaction: pass rate, cache misses caused, dollars.
7. [ ] Compare your radix toy's hit rate with the provider's reported cache reads on the same traces. Explain the gap.

## Production lens
- **Context overflow is a typed, recoverable error** with exactly one retry after compaction, never a loop.
- **Compaction is a step that can fail.** If the summary call errors, fall back to masking; never leave the session half-compacted.
- **Idempotency:** a retried turn must not compact twice. Key compaction entries by the cut-point entry id.
- **Cost:** compaction spend counts against the run's budget and appears as its own line in the report.
- **Cache waste is a cost metric.** Alert on dollars lost to cache misses per day, broken down by cause; a deploy that reorders tool definitions shows up here first.
- **Memory files are an exfiltration surface.** Anything the agent writes to long-term memory is later loaded into other sessions; redact secrets before writing.

## Not yet
Vector-store memory products, knowledge-graph memory, "infinite context" claims, building your own serving engine, and fine-tuning for memory. Each is easier to judge once you can measure what a simple file and a summary already give you.

## Checkpoint
- [ ] From any trace you can say which part of each request was served from cache and why each miss happened.
- [ ] rig completes T17 under the 40,000-token limit without an overflow error, and the report shows what compaction cost and what it did to pass rate.
- [ ] Your radix toy passes property tests: matching returns the longest stored prefix, and eviction never frees a referenced node.
- [ ] Your ledger attributes every cache miss in a session to a cause, and you can say when a 1-hour TTL beats a 5-minute one for your traffic.
- [ ] You can explain prompt caching to a colleague in terms of per-layer key and value tensors.

---

# Week 4: retrieval

*Phase: The machine · Primary reading/code: rank_bm25, hnswlib, pgvector, Aider repo map*

Retrieval is ranking: score every candidate against a query and keep the top k. Everything else (BM25, embeddings, HNSW, vector databases, hybrid fusion, rerankers) either improves the score or makes ranking fast. This week you build each piece, then make it beat rig's own grep on a labeled set, or decide honestly that it does not.

## Concepts
- **Lexical scoring (BM25):** inverse document frequency, times a saturating term-frequency curve (`k1`), times document-length normalization (`b`). For code, tokenization decides everything: split `camelCase` and `snake_case`, keep identifiers whole as well.
- **Dense scoring:** an embedding model maps text to a vector; similarity is a dot product. Quality depends on the model and on chunking (whole files, functions, fixed windows).
- **Exact versus approximate search.** Brute-force cosine over 100,000 vectors is one matrix multiply. HNSW trades recall for speed with a layered proximity graph searched greedily; `ef` sets the trade-off at query time.
- **A vector database** is an ANN index plus storage, metadata filtering, updates and deletes. The filtering and update semantics are the hard part, not the index.
- **Postgres as the vector store.** pgvector keeps vectors in ordinary tables beside the rows they describe, with transactions, joins, filters and Postgres full-text search in the same query. Most products need nothing more until they have measured otherwise.
- **Hybrid fusion.** Reciprocal Rank Fusion sums `1 / (60 + rank)` across rankers, which needs no score calibration.
- **Reranking.** A cross-encoder or an LLM scores (query, candidate) pairs jointly. It is accurate and expensive, so it runs only on the top 30 to 100.
- **Typos and vocabulary mismatch.** BM25 and full-text search match tokens exactly, so `retreive` finds nothing; embeddings tolerate small typos but drift on rare identifiers. Trigram similarity (Postgres `pg_trgm`) still matches a misspelled identifier: `retreive_chunks` scores 0.6 against `retrieve_chunks`, above the default threshold of 0.3. A cheap model can also rewrite a question into several queries (multi-query) or into a hypothetical answer to embed (HyDE); each adds a model call before retrieval.
- **Code-specific retrieval without embeddings.** A symbol graph (definitions and references) ranked with PageRank, which is Aider's repo map.
- **RAG versus agentic search.** RAG retrieves once and prepends; agentic search lets the model issue many cheap queries. For code the agent's own grep is a strong baseline, so retrieval enters rig as a tool, not as automatic context.
- **Retrieval metrics:** recall@k and MRR on labeled query-to-file pairs first; end-to-end task impact second.

## Day by day
Nine Build steps this week follow one build order: ground truth, then lexical, then dense and approximate, then the tool, then polish. The schedule below follows that same order so each day's work is usable by the next.

| Day | Time | Do | Working by end of day |
|---|---|---|---|
| Mon | 1 to 1.5 h | Read **Concepts** above; note the ranking framing | Half-page note: BM25's three factors, dense vs lexical, what HNSW trades for speed |
| Tue | 3 to 4 h | Build steps 1 to 3 | 40 labeled questions on openai-agents-python; BM25 from scratch matching `rank_bm25`; an ast-based chunker |
| Wed | 3 to 4 h | Build steps 4 to 7 | Chunks embedded and in pgvector with an HNSW index; an HNSW toy with a measured recall@10 curve; hybrid RRF plus a reranker; `retrieve(query, k=10)` wired in |
| Thu | 1.5 to 2 h | Build steps 8 to 9; read BM25, hnswlib, pgvector and Aider; trace three paths | A repo map rendered into the system prompt; typo tolerance working; you can narrate hnswlib's insert and Aider's PageRank from memory |
| Fri | 1 to 1.5 h | Experiments 2, 5 and 6 | Chunking, staleness and typo results written down |
| Sat | 3 to 4 h | **Project increment**: v0.4, T18 to T23; Experiments 1, 3 and 7 | Six new tasks graded against file:line keys; the full recall@10/MRR matrix and the HNSW-vs-hnswlib-vs-pgvector comparison |
| Sun | 2 to 3 h | Experiment 4; answer remaining questions; attempt **Checkpoint** | Pass rate, steps and tokens with and without `retrieve`; a documented ship/no-ship call |

### Monday — ranking, before the algorithms.
Every technique this week is either a way to score a candidate or a way to make scoring fast at scale. Fix that framing before you write a line of BM25, or HNSW will look like a separate subject instead of "approximate scoring, fast."

1. Read **Concepts** above.
2. Write a half-page note: what `k1` and `b` control in BM25, what dense scoring depends on, and what HNSW trades for speed.

### Tuesday — the labeled set and lexical scoring.
You can't tell if retrieval helps without ground truth, so today starts there: 40 real questions against a real repo, with answers you wrote by reading the code yourself. Then build the lexical baseline every later method gets compared against.

1. Build step 1: write the 40 labeled questions against openai-agents-python `v0.23.1` by reading the code, not guessing.
2. Build step 2: BM25 from scratch, about 80 lines, with a code-aware tokenizer; check your scores against `rank_bm25` on the same corpus.
3. Build step 3: a chunker using `ast`, one chunk per function or class, prefixed with path and qualified name.

### Wednesday — dense scoring, approximate search, and the first real tool.
Today you build everything between "a chunk" and "an answer the agent can act on": embeddings in Postgres with an HNSW index, your own HNSW toy so the index stops being a black box, hybrid fusion with a reranker on top, and the tool that exposes all of it to the agent.

1. Build step 4: embed every chunk, exact cosine in NumPy first, then into Postgres with pgvector — a `chunks` table with model name, content hash, a `tsvector` column and an HNSW index.
2. Build step 5: an HNSW toy of about 200 lines; plot recall@10 against brute force for `ef` of 10, 50 and 200.
3. Build step 6: hybrid retrieval with RRF, first in Python then as one SQL query fusing pgvector and full-text, then an LLM reranker over the top 30.
4. Build step 7: `retrieve(query, k=10)` returning `path:start-end` plus the symbol name and a two-line preview.

### Thursday — polish the tool, then read four reference implementations.
Two small Build steps left, both easiest to understand right after reading their reference: the repo map next to Aider's `repomap.py`, typo tolerance next to pgvector's trigram docs. Spend the rest of the day on the reads themselves — this is the day the mystery comes out of vector databases.

1. Build step 8: a Python-only repo map — definitions and references from `ast`, PageRank over files, rendered into about 1,000 tokens.
2. Build step 9: a `pg_trgm` index on symbol names for fuzzy identifier lookup, plus an optional multi-query/HyDE rewrite step behind a flag.
3. Read the files listed under **Read** above: `rank_bm25` (and `bm25s` for contrast), hnswlib's `hnswalg.h`, pgvector's C source, and Aider's `repomap.py`.
4. Trace the three paths given there: hnswlib insert, hnswlib query, and Aider's `get_repo_map`.

### Friday — cheap experiments only.
No new modules today. Three quick comparisons on the harness you already built, before the weekend's full metrics run.

Run Experiments 2, 5 and 6 above: whole-file vs function vs window chunking; an unreindexed edit misleading retrieval; and the misspelled-questions test with and without trigram matching and a rewrite step.

### Saturday — the full comparison, then the project increment.
This is the day the week pays off: the complete recall@10/MRR matrix across every method you built, your HNSW toy benchmarked against the real thing, and `retrieve` wired into rig as v0.4 against a second target repo.

1. Run Experiment 1: recall@10 and MRR on the 40 questions for BM25 (plain and code-aware tokenizer), dense, hybrid, hybrid plus rerank, the repo map, and agentic grep.
2. Run Experiment 3 and Experiment 7: your HNSW toy's recall/latency curve against hnswlib's, then the four-way comparison (NumPy brute force, your toy, hnswlib, pgvector) on the same vectors.
3. Ship **Project increment** above: rig v0.4 with `retrieve` backed by Postgres, and T18 to T23 graded against file:line answer keys.

### Sunday — does retrieval earn its keep, then the checkpoint.
No new code today. The only question that matters is whether `retrieve` actually helps rig's agent, not whether the benchmarks look good in isolation.

1. Run Experiment 4: T18 to T23 with and without `retrieve` — pass rate, steps to first relevant file, tokens.
2. Answer the remaining questions in **You should be able to answer**.
3. Attempt **Checkpoint** above. With numbers in hand, write down, honestly, whether rig should ship `retrieve` and for which kinds of question.

## Build
1. [ ] A labeled set: 40 natural-language questions about [openai-agents-python](https://github.com/openai/openai-agents-python) `v0.23.1`, each with its relevant files and functions. Write them by reading the code ("where is the max-turns limit enforced?", "where are handoff input filters applied?"). This doubles as Week 11 preparation.
2. [ ] BM25 from scratch (about 80 lines) with a code-aware tokenizer. Check your scores against `rank_bm25` on the same corpus.
3. [ ] A chunker using Python's `ast`: one chunk per function or class, prefixed with path and qualified name.
4. [ ] Embeddings for every chunk from one embedding model, and exact cosine search in NumPy. Then move the vectors into Postgres with pgvector: a `chunks` table with the model name, the content hash, a generated `tsvector` column and an HNSW index. `docker compose` with the `pgvector/pgvector` image is enough.
5. [ ] An HNSW toy of about 200 lines: random levels, greedy descent through upper layers, beam search with `ef` on layer 0, the neighbor-selection heuristic. Plot recall@10 against brute force for `ef` of 10, 50 and 200.
6. [ ] Hybrid retrieval with RRF, first in Python, then as one SQL query that fuses the pgvector and full-text rankings; then an LLM reranker (the cheap model) over the top 30.
7. [ ] A `retrieve(query, k=10)` tool that returns `path:start-end` plus the symbol name and a two-line preview, so the agent decides what to read.
8. [ ] A repo map in the Aider style for Python only: definitions and references from `ast`, PageRank over files, rendered into about 1,000 tokens of the system prompt.
9. [ ] Typo tolerance and rewriting, each behind a flag: a `pg_trgm` index on symbol names for fuzzy identifier lookup, and an optional rewrite step with the cheap model (multi-query and HyDE).

## Project increment
rig v0.4 gains `retrieve`, backed by Postgres with pgvector, and works on the second target. Add six question-answering tasks on openai-agents-python (T18 to T23), graded against answer keys of file:line ranges.

## Read
**[dorianbrown/rank_bm25](https://github.com/dorianbrown/rank_bm25)**, `rank_bm25.py` (257 lines): `BM25.__init__` and `_initialize`, then `BM25Okapi._calc_idf` (85) and `get_scores` (107). The whole BM25 family fits in one file, and the `epsilon` floor for negative IDF is a real-world detail most write-ups skip. For contrast, [xhluca/bm25s](https://github.com/xhluca/bm25s) precomputes every term-document score into a sparse matrix at index time (`BM25.index` and `retrieve` in `bm25s/__init__.py`), so a query is a sparse-row sum.

**[nmslib/hnswlib](https://github.com/nmslib/hnswlib)**, `hnswlib/hnswalg.h`: `getRandomLevel` (227), `searchBaseLayer` (246), `searchBaseLayerST` (337), `getNeighborsByHeuristic2` (475), `mutuallyConnectNewElement` (538), `addPoint` (1100 and the overload after it), and `searchKnn`. Then `bruteforce.h` (193 lines) as the baseline. This is the reference HNSW, and most vector databases embed it or a close descendant, so reading it removes most of the mystery from vendor comparisons.

**[pgvector/pgvector](https://github.com/pgvector/pgvector)** (second read, C). The same algorithm inside a database, where updates, deletes and filters are the hard part. In `src/hnswinsert.c` read `HnswInsertTupleOnDisk` (696), `UpdateGraphOnDisk` (669) and `HnswUpdateNeighborsOnDisk` (546). In `src/hnswscan.c` read `hnswgettuple` (195), `GetScanItems` (26) and `ResumeScanItems` (67). In `src/hnswvacuum.c` read `RepairGraph` (379) and `MarkDeleted` (595), which answer the deletion question below. Then read the README's "Iterative Index Scans" section: with a `WHERE` filter, approximate search filters after the index scan and can return fewer than k rows, so pgvector keeps scanning until it has enough. Filtered nearest-neighbour search is where vector databases actually differ. Finish with the README's "Hybrid Search" section, then the PostgreSQL documentation for [`pg_trgm`](https://www.postgresql.org/docs/current/pgtrgm.html): `similarity`, the `%` operator and its threshold, and trigram GIN indexes.

**[Aider-AI/aider](https://github.com/Aider-AI/aider)**, `aider/repomap.py` (867 lines): `get_tags_raw` (279, tree-sitter queries), `get_ranked_tags` (365, the reference graph and personalized PageRank), `get_ranked_tags_map_uncached` (629, a binary search on how many tags fit the token budget), `to_tree` (748). It is retrieval for code with no embeddings at all.

**Trace these paths:**

- hnswlib insert: `addPoint` → `getRandomLevel` → greedy descent from the entry point through layers above the new level → for each lower layer, `searchBaseLayer` with `ef_construction` → `getNeighborsByHeuristic2` → `mutuallyConnectNewElement` (shrinking neighbors' lists past `M`) → update the entry point if the new level is the highest.
- hnswlib query: `searchKnn` → greedy descent → `searchBaseLayerST` on layer 0 with `ef` → top k.
- Aider: `get_repo_map` → `get_ranked_tags_map` → `get_ranked_tags` (definitions, references, PageRank personalized toward files in the chat and identifiers mentioned) → `to_tree` → token-budget fit.

## You should be able to answer
1. [ ] What do `k1` and `b` control, and why does Okapi BM25 need an IDF floor?
2. [ ] What does bm25s gain by scoring at index time, and what does it lose?
3. [ ] Why do HNSW levels follow an exponentially decaying distribution, and what does `ef` change at construction versus query time?
4. [ ] Why choose neighbors with a heuristic instead of the M nearest?
5. [ ] How does hnswlib delete, and why is true deletion hard in a graph index?
6. [ ] When does brute force beat HNSW outright?
7. [ ] Why does RRF work without calibrating scores across rankers?
8. [ ] How does Aider personalize PageRank, and how does it fit the map into a token budget?
9. [ ] On your own eval, which query types did retrieval win and which did grep win?
10. [ ] When does a rewrite step help retrieval, and what does it cost in latency and in queries that drift from what was asked?
11. [ ] Why does trigram similarity catch `retreive` when BM25 and full-text search do not, and where does it produce false matches?

## Experiments
1. [ ] Recall@10 and MRR on the 40 questions for: BM25 with a plain tokenizer, BM25 with the code-aware tokenizer, dense, hybrid, hybrid plus rerank, the repo map, and agentic grep (the files rig opens in its first five steps).
2. [ ] Chunking: whole file versus function chunks versus 50-line windows.
3. [ ] Your HNSW recall and latency curve against hnswlib's on the same vectors.
4. [ ] T18 to T23 with and without `retrieve`: pass rate, steps to first relevant file, tokens.
5. [ ] Stale index: let the agent edit a file without reindexing, and watch retrieval mislead it. Then reindex by content hash after every edit.
6. [ ] Typos: a misspelled copy of the 40 questions (one or two edits in each identifier). Recall@10 for BM25, dense and hybrid, then with trigram identifier matching and with a rewrite step.
7. [ ] NumPy brute force, your HNSW toy, hnswlib and pgvector's HNSW on the same vectors: recall@10, p95 latency, build time and memory.

## Production lens
- **Freshness.** The agent's own edits make the index stale mid-run. Key chunks by content hash and reindex changed files after each mutating tool call.
- **Model versioning.** Vectors from different embedding models are not comparable; store the model id beside every vector and refuse mixed queries.
- **Access control.** In multi-tenant systems, filter by permission before ranking, not after, or top-k quietly returns fewer results. Week 14 measures how few.
- **Retrieved text is untrusted.** Comments and docs can carry prompt injections; Week 9 tests this.
- **Cost and latency:** embedding is a batch job with retries and rate limits; reranking adds a model call to every query.

## Not yet
Hosted vector-database comparisons, GraphRAG, late-interaction models, fine-tuned embeddings, trained query rewriters, and RAG frameworks.

## Checkpoint
- [ ] You can write BM25 from memory and explain each factor.
- [ ] Your HNSW toy reaches recall@10 of at least 0.95 against brute force at some `ef` on 50,000 vectors, and you can explain the shape of the curve.
- [ ] With numbers from your own eval, you can say whether rig should ship `retrieve`, and for which kinds of question.

---

# Week 5: tracing, evals and trajectory evaluation

*Phase: The machine · Primary reading/code: SWE-bench, inspect_ai, OTel GenAI*

You have been tracing and evaluating since Day 1. This week you make the results trustworthy: standard spans, graders you have validated, trajectory metrics, and statistics that tell you whether a change was real. By Sunday you should distrust any single-run improvement, including your own. Everything from Week 10 on is graded by a model, so the grader you validate this week is the instrument for the rest of the plan.

## Concepts
- **Spans, not logs.** A trace is a tree of timed spans with attributes. The OpenTelemetry GenAI conventions name the agent operations: `invoke_agent`, `chat`, `execute_tool`, `plan`, `invoke_workflow`, `create_agent`. Usage lands in `gen_ai.usage.*`, tools in `gen_ai.tool.*`. Capturing message content is opt-in for privacy reasons.
- **The anatomy of an eval:** a dataset of tasks with pinned environments, a solver (the agent), a grader, and metrics. Graders are deterministic (tests, exact match), model-graded (a judge with a rubric), or human.
- **Outcome versus trajectory.** Outcome grading checks the final state. Trajectory grading checks the path: wasted steps, repeated reads, edits outside scope, tests never run after the last edit, policy violations, recovery after tool errors. A pass with a bad trajectory is a future failure.
- **The SWE-bench rule.** An instance is resolved only if every FAIL_TO_PASS test now passes and every PASS_TO_PASS test still passes. Your T04 to T11 already follow it.
- **Statistics.** pass@k (at least one of k runs passes) flatters agents; pass^k (all k pass) measures reliability. Use Wilson intervals for rates and paired comparisons on the same tasks for A/B tests. Twelve tasks run three times cannot resolve small differences.
- **Judges need validation.** An LLM judge is a classifier; measure its agreement with your labels and watch for verbosity and position bias, and for prompt injection from the transcript it grades.
- **Prompts are code.** System prompts, tool descriptions, routing policies and grader rubrics live in files under version control. Each run records the hash of every prompt it used, so a regression points at the change that caused it.
- **Eval hygiene:** infrastructure failures are excluded from model metrics, a held-out set is never used for tuning, and eval data never leaks into prompts.

## Day by day
Eight Build steps this week, but the real deliverable is trust: by Sunday you should distrust any single-run improvement, including your own. The schedule below front-loads the instruments (spans, graders, statistics) so the weekend's noise-floor and judge-calibration runs have something real to measure against.

| Day | Time | Do | Working by end of day |
|---|---|---|---|
| Mon | 1 to 1.5 h | Read **Concepts** above; note the eval anatomy | Half-page note: spans vs logs, outcome vs trajectory, pass@k vs pass^k |
| Tue | 3 to 4 h | Build steps 1 and 2 | A root `invoke_agent` span per run with `chat`/`execute_tool` children; `graders.py` with all five graders returning verdict plus evidence |
| Wed | 3 to 4 h | Build steps 3 to 5 | Trajectory metrics extracted from traces; `report.py` with Wilson intervals and a paired bootstrap; a CI gate wired to every prompt/tool change |
| Thu | 1.5 to 2 h | Build steps 6 and 7; read SWE-bench, inspect_ai and the OTel conventions; trace both paths | Prompt hashes shown in every report; the nightly suite running through the Batches API with a measured cache-hit rate |
| Fri | 1 to 1.5 h | Experiments 3 and 5 | A labeled pass-with-bad-trajectory and fail-with-good-trajectory example each; a decision on what trace content you must keep |
| Sat | 3 to 4 h | Build step 8; Experiments 1 and 2 | The sealed 20-task held-out set; the noise floor from five identical runs; judge agreement measured against 30 hand-labeled answers |
| Sun | 2 to 3 h | Experiment 4; answer remaining questions; attempt **Checkpoint** | One earlier change re-decided with a paired bootstrap; checkpoint passed or a redo list |

### Monday — the vocabulary this week makes precise.
"It passed" and "it got better" are claims you've been making loosely since Week 1. Today you read the vocabulary that lets you stop: spans instead of logs, outcome versus trajectory, pass@k versus pass^k. Everything you build this week exists to make those claims checkable.

1. Read **Concepts** above.
2. Write a half-page note: the OTel GenAI span types, and why pass@k flatters an agent while pass^k measures its reliability.

### Tuesday — spans and graders.
Today you build the two things every later measurement depends on: a trace that's actually a tree of timed spans instead of a flat JSONL, and a set of graders that return evidence, not just a boolean. Get the grader contract right now, because this week's whole point is that you validate these graders before trusting any of them.

1. Build step 1: OTel instrumentation — a root `invoke_agent` span per run, `chat` per model call, `execute_tool` per tool call, with GenAI attributes; a JSONL-to-OTLP converter, not a replacement for the JSONL.
2. Build step 2: `evals/graders.py` — `tests_pass`, `no_test_edits`, `hidden_tests`, `answer_mentions`, `llm_judge`, each returning a verdict plus evidence.

### Wednesday — trajectory, statistics, and a gate.
A pass rate alone doesn't tell you if a run was good, and a single run's pass rate doesn't tell you if a change was real. Today you build the metrics that grade the path, the statistics that grade the comparison, and the gate that runs both automatically.

1. Build step 3: trajectory metrics from traces — redundant reads, repeated calls, time to first relevant file, edit churn, tests run after the last edit, tool-error recovery, policy events, cost.
2. Build step 4: `evals/report.py` — pass@1 and pass^3 with Wilson intervals, and a paired bootstrap between two rig versions on the same tasks.
3. Build step 5: a CI gate — T01 to T09 once on every prompt or tool change, the full suite three times nightly.

### Thursday — prompt hashes and batches, then read the two canonical harnesses.
Two small Build steps left; both fit before the day's main work, reading SWE-bench's grading code and inspect_ai's task/solver/scorer split, the two references your own harness has been converging on since Week 1.

1. Build step 6: versioned prompts — every prompt loaded from `prompts/`, its content hash on the root span, changed hashes surfaced in every comparison report.
2. Build step 7: the nightly suite through the Message Batches API with a 1-hour cache on the shared prefix; record the actual cache-hit rate you get.
3. Read SWE-bench's `grading.py` and `run_evaluation.py`, and inspect_ai's `_react.py`, `scorer/_model.py` and `_call_tools.py`, listed under **Read** above.
4. Trace both paths given there: SWE-bench's `main` through `get_resolution_status`, and inspect_ai's `eval` through `task_run_sample` to the scorer.

### Friday — look at your own traces, not new numbers.
No new runs today, just a close read of what you already have. The point is to find the gap between "passed" and "good," and to decide what a trace absolutely must capture before you turn content capture off by default.

Run Experiments 3 and 5: find one passing run with a bad trajectory and one failing run with a good one, and write a grader for each pattern; then turn off content capture and try to debug three failures, and decide what you must keep.

### Saturday — seal the held-out set, then find your noise floor.
Today's Build step is a one-line discipline with real consequences: twenty tasks you write and then don't look at again until Week 18. The rest of the day answers the question this whole week has been building toward — how much of what you called "progress" in Weeks 2 to 4 was actually noise.

1. Build step 8: write 20 held-out tasks (new seeds, new questions); do not open this set again before Week 18.
2. Run Experiment 1, the noise floor: the full suite five times with identical configuration; compute per-task pass rates and intervals.
3. Run Experiment 2: label 30 answers from T02 and T18 to T23 yourself, then measure the judge's agreement with and without a rubric.

### Sunday — re-decide one earlier change, then the checkpoint.
No new code today. Pick one change from Weeks 2 to 4 you were proud of and find out, with a real paired comparison, whether it actually did anything.

1. Run Experiment 4: re-decide one earlier change (fuzzy edits, the repo map, observation masking) with a paired bootstrap against Saturday's noise floor.
2. Answer the remaining questions in **You should be able to answer**.
3. Attempt **Checkpoint** above. If your judge disagrees with your own labels more than 15% of the time, document why before leaning on it again.

## Build
1. [ ] OTel instrumentation: a root `invoke_agent` span per run, a `chat` span per model call, an `execute_tool` span per tool call, with the GenAI attributes. Write a converter from your JSONL to OTLP rather than replacing the JSONL, so the mapping is explicit. View traces in any local OTLP backend.
2. [ ] `evals/graders.py`: `tests_pass(f2p, p2p)`, `no_test_edits()`, `hidden_tests(path)`, `answer_mentions(items, ordered=True)`, `llm_judge(rubric)`. Every grader returns a verdict plus evidence.
3. [ ] Trajectory metrics from traces: redundant reads, repeated identical calls, time to first relevant file, edit churn (lines changed then reverted), tests run after the last edit, tool-error recovery, policy events, cost.
4. [ ] `evals/report.py`: pass@1 and pass^3 with Wilson intervals, and a paired bootstrap between two rig versions on the same task set.
5. [ ] A CI gate: T01 to T09, one run each, on every change to rig's prompts or tools; nightly, the full suite three times.
6. [ ] Versioned prompts: load every prompt from `prompts/`, record each one's content hash on the root span, and show in every report which prompt hashes changed between the two runs it compares. For contrast, Open WebUI (Week 14's main read) stores edits to its user prompt library as commits with parents: `backend/open_webui/models/prompt_history.py` at `v0.11.4`, `PromptHistory` (19) and `compute_diff` (148).
7. [ ] Run the nightly suite through the Message Batches API (half the price; most batches finish within an hour, all within 24 hours) with a 1-hour cache on the shared prefix, and keep CI on the synchronous API. Cache hits in batches are best-effort, so record the hit rate you actually get.
8. [ ] A held-out set of 20 tasks (new seeds, new questions) that you do not open until Week 18.

## Project increment
rig v0.5: OTel traces, validated graders, trajectory metrics and a regression gate. The weekly report becomes the artifact you look at first.

## Read
**[SWE-bench/SWE-bench](https://github.com/SWE-bench/SWE-bench) harness.** The canonical outcome grader for coding agents. In `swebench/harness/grading.py`: `test_passed` (85), `test_failed` (101), `get_logs_eval` (113), `get_eval_tests_report` (179), `compute_fail_to_pass` (288), `compute_pass_to_pass` (298), `get_resolution_status` (309), `get_eval_report` (329). Then `run_instance` in `run_evaluation.py` (229), `log_parsers/python.py`, and `infra_failure.py`.

**[UKGovernmentBEIS/inspect_ai](https://github.com/UKGovernmentBEIS/inspect_ai), selected files.** Its decomposition (task = dataset + solver + scorer) is the right one, and its transcript events are a good reference for trajectory data. Read `src/inspect_ai/agent/_react.py` (`react` at 57 and `_handle_overflow` at 619), `scorer/_model.py` (`model_graded_fact` at 35, `model_graded_qa` at 115, `chat_history` at 463, `neutralize_structural_delimiters` at 513), and `model/_call_tools.py` (`execute_tools` at 226, `call_tool` at 842). Skim `_eval/task/run.py` only for `task_run_sample` (2259); the file is 4,022 lines.

**[OpenTelemetry GenAI semantic conventions](https://github.com/open-telemetry/semantic-conventions-genai).** These moved out of the main semantic-conventions repository into their own. Read `docs/gen-ai/gen-ai-agent-spans.md` (the agent, workflow, plan and tool spans), `docs/gen-ai/gen-ai-spans.md`, and the attribute registry in `docs/registry/attributes/gen-ai.md`.

**Trace these paths:**

- SWE-bench: `main` → `run_instances` → `run_instance` (start the instance container, apply the model's patch, run the eval script, save the log) → `get_eval_report` → `get_logs_eval` (parse the log into a test-to-status map) → `get_eval_tests_report` (success and failure lists for FAIL_TO_PASS and PASS_TO_PASS) → `get_resolution_status`.
- inspect_ai: `eval` → `task_run` → `task_run_sample` → the `react` solver's generate and `execute_tools` loop → scorer → `log_sample`.

## You should be able to answer
1. [ ] Why does SWE-bench need PASS_TO_PASS at all, and what would scores look like without it?
2. [ ] How is a test's status recovered from a raw log, and which kinds of flakiness does that expose?
3. [ ] Why are infrastructure failures counted separately from model failures?
4. [ ] How does inspect's model-graded scorer present a transcript to the judge, and why does it neutralize structural delimiters first?
5. [ ] How does inspect's `react` agent recover from a context overflow, and how does that compare with your Week 3 approach?
6. [ ] What is the smallest set of spans and attributes that reconstructs cost and latency per run?
7. [ ] pass@k versus pass^k: which one should a product team track, and why?
8. [ ] Roughly how many tasks and runs do you need to detect a 10-point change in pass rate?

## Experiments
1. [ ] **Noise floor.** Run the full suite five times with identical configuration. Compute per-task pass rates and intervals. Compare that noise with every "improvement" you made in Weeks 2 to 4.
2. [ ] **Judge calibration.** Label 30 answers from T02 and T18 to T23 yourself; measure the judge's agreement with and without a rubric.
3. [ ] **Outcome versus trajectory.** Find passing runs with bad trajectories and failing runs with good ones; write a grader for each pattern.
4. [ ] **A real A/B.** Re-decide one earlier change (fuzzy edits, the repo map, observation masking) with a paired bootstrap.
5. [ ] **Content-free tracing.** Turn off content capture and try to debug three failures. Decide what content you must keep, and how you will redact it.

## Production lens
- **Redaction** of secrets and personal data before traces leave the process; content capture off by default.
- **Sampling and volume:** full traces for failures and a sample of successes; cost per stored trace.
- **Dashboards** you would want on call: success rate, cost per success, p95 latency per step, tool error rate by tool, overflow and retry counts, budget exits.
- **Non-determinism:** fixed temperature does not make runs reproducible; your saved transcripts and diffs do.

## Not yet
Comparing hosted eval and observability platforms, reinforcement learning on trajectories, process reward models, and full SWE-bench runs (a 20-instance subset is plenty for learning and costs far less).

## Checkpoint
- [ ] Your weekly report shows intervals and a paired comparison with last week, and you can say which of your earlier changes were real.
- [ ] Your judge agrees with your labels on at least 85% of the calibration set, or you have documented why not and stopped relying on it.
- [ ] Questions such as "why did Tuesday's runs cost more?" or "which tool fails most often?" are answered by one query over your traces.
- [ ] You can implement the SWE-bench resolution rule for a new repository from memory.

---

# Week 6: the model, from tokenizer to KV cache

*Phase: The model · Primary reading/code: nanochat*

Everything above the API is a loop around one function: tokens in, a distribution over the next token out. This week you open that function. By Sunday you can follow a chat message from text to token ids to logits and back, show that tool calling is special tokens plus code that intercepts them, and measure what a KV cache saves.

## Concepts
- **Tokenization.** Byte-level BPE learns merges from data. Special tokens are reserved ids that mark roles and tool calls; a chat template is nothing more than those ids wrapped around text.
- **The forward pass.** Embeddings, then blocks of attention (with rotary position embeddings and a causal mask) and MLP on a residual stream, then logits over the vocabulary.
- **Prefill versus decode.** Prefill runs the whole prompt in parallel and is compute-bound. Decode produces one token at a time and reads the entire KV cache each step, so it is memory-bandwidth-bound. That is why time to first token grows with prompt length, and why output tokens are priced higher than input tokens.
- **The KV cache.** Keys and values for every layer and every token already processed: 2 × layers × KV heads × head dimension × bytes per value, per token. Week 3's prompt caching is this tensor kept between requests.
- **Sampling.** Temperature and top-k reshape the distribution before one token is drawn. Determinism is a property of the whole serving stack, not of temperature alone.
- **The training stack in one sentence each.** Pretraining is next-token loss on text. Supervised fine-tuning is the same loss on conversations, masked so only assistant tokens are learned. Reinforcement learning samples completions, scores them and pushes up the probability of the better ones.
- **Tool calling at the token level.** The model emits a start token, the call, and an end token; the inference engine stops, runs the tool and forces the result tokens back into the sequence. Week 1's `tool_use` and `tool_result` blocks are the API's rendering of exactly this.

## Day by day
| Day | Time | Do | Working by end of day |
|---|---|---|---|
| Mon | 1-1.5 h | Concepts: tokenization, the forward pass, prefill/decode, the KV cache; clone nanochat at the pinned commit | A half-page note on tokenization and the forward pass; nanochat cloned and its CPU run ready to kick off |
| Tue | 2.5-3 h | Build step 1 (BPE trainer); start Build step 2's CPU run in the background | Your own byte-level BPE trainer/encoder passing a sanity check; `runs/runcpu.sh` training in the background |
| Wed | 2.5-3 h | Build step 4 (transformer block forward pass); check on the CPU run or optional GPU speedrun | Your block's forward pass matches `Block.forward` to floating-point tolerance; a trained nanochat checkpoint on disk |
| Thu | 2 h | Read nanochat (`tokenizer.py`, `engine.py`); trace the generate path; Build step 5 (swap in rig's `search` tool) | The annotated trace of `chat_cli.py` to a sampled token; a copy of `Engine.generate` that calls `search` instead of the calculator |
| Fri | 1.5 h | Build step 3 (`kvdemo.py`) | A tokens-per-second-vs-context-length plot, cache on and off |
| Sat | 3-4 h | Experiments 1-4; rig v0.6 project increment | Experiment numbers written up; rig traces carry time-to-first-token and time-per-output-token |
| Sun | 2-3 h | Answer the seven questions; attempt the checkpoint | Checkpoint passed or a redo list |

### Monday — tokens in, logits out, nothing running yet.
Today is reading and arithmetic, not code: you need the shape of the forward pass and what a KV cache actually stores before any of this week's builds make sense, since Tuesday through Thursday all assume you already know what a block, a head and a cache entry are. Spend most of the time on Concepts above, especially prefill versus decode and the KV-cache size formula, and work the bytes-per-token arithmetic for nanochat's default model by hand before you check it against the real helper on Thursday.

1. Read Concepts above twice; write a half-page note covering tokenization, the forward pass, prefill versus decode, and the KV cache.
2. Compute `kv_bytes_per_token` for nanochat's default config by hand (layers x KV heads x head dimension x 2 x bytes per value).
3. Clone nanochat at the pinned commit (see **Read: nanochat** below) and confirm `runs/runcpu.sh` runs a trivial smoke step without error.

### Tuesday — your own tokenizer, then start the clock on nanochat's run.
Build step 1 is the cheapest way to make byte-level BPE concrete: training your own merges on real source and comparing token counts against nanochat's tokenizer tells you immediately whether your mental model of "merges learned from data" is right. The nanochat CPU run (Build step 2) takes tens of minutes, so start it today and let it run while you work rather than treating it as separate idle time.

1. Implement Build step 1: a byte-level BPE trainer and encoder in about 100 lines, trained on click's source.
2. Compare token counts for rig's system prompt under your tokenizer against nanochat's.
3. Kick off Build step 2's CPU run (or the GPU `speedrun.sh`, if you're renting one this week) in the background; let it keep running if it's not done by the time you stop.

### Wednesday — a transformer block by hand, and a trained checkpoint to show for it.
Writing your own forward pass for one block and checking it against nanochat's `Block.forward` is the only way to confirm you actually understand attention and the residual stream, rather than just being able to describe them. By tonight yesterday's run should also be finished, giving you a real checkpoint for Thursday's and Friday's tools.

1. Implement Build step 4: one transformer block's forward pass with plain tensor operations (rotary embeddings, causal mask, MLP, residual stream).
2. Check it matches `Block.forward` to floating-point tolerance, feeding it the same weights.
3. Confirm yesterday's nanochat run finished and you have a checkpoint; an undertrained CPU run is fine, it only needs to produce tokens for Thursday and Friday.

### Thursday — read nanochat end to end, then make its tool calling yours.
Today is the week's reference-implementation day: read the tokenizer and engine files in the order given in **Read: nanochat** below, and trace the exact path from `chat_cli.py` to a sampled token so the KV cache and the tool state machine stop being diagrams. Then do Build step 5 — swapping the calculator for rig's `search` tool inside a copy of `Engine.generate` — because it demonstrates, concretely, that tool calling is trained behavior: the plumbing works first try, and the model still uses the tool badly.

1. Read `tokenizer.py` and `engine.py` per **Read: nanochat** below; write out the trace from `chat_cli.py` to a sampled token.
2. Implement Build step 5: copy `Engine.generate`, swap `use_calculator` for rig's `search`, run a few prompts, and note exactly how the model misuses it.

### Friday — the KV cache's payoff, measured.
No new reading today. You already know what the KV cache stores and traced the engine that uses it; today you measure what it's actually worth, which is Build step 3 and nothing else.

1. Implement `rig/kvdemo.py`: decode with and without a KV cache from your trained model, plotting tokens per second as context grows from 128 to 2,048 tokens.
2. Compare the shape of the curve against your bytes-per-token arithmetic from Monday.

### Saturday — the four experiments, and the project increment.
Today you turn this week's pieces into numbers you can compare: the KV-cache curve, sampling determinism, tokenizer vocabulary size, and FLOPs against your own measured latency. This is also when rig gains the instrumentation — time to first token and time per output token — that Week 8's routing decisions and Week 10's latency budgets both depend on.

1. Run Experiments 1-4 in **Experiments** below.
2. Ship rig v0.6 per **Project increment** below: time to first token and time per output token recorded for every model call, from the streaming events.

### Sunday — answer for it, then the checkpoint.
No new code today. Go through the seven questions in **You should be able to answer** below from memory first, then check yourself against the reading; anything you can't answer without looking is a gap to close before Week 7's serving engine, which assumes all of this.

1. Answer each of the seven questions in **You should be able to answer** below in your notes.
2. Attempt **Checkpoint** below; redo the relevant day if you can't pass it cold.

## Build
1. [ ] A byte-level BPE trainer and encoder in about 100 lines. Train it on click's source and compare token counts for rig's system prompt against nanochat's tokenizer.
2. [ ] Run nanochat end to end with `runs/runcpu.sh` on CPU or Apple Silicon; the README describes a deliberately tiny model that trains in tens of minutes. Optional: `runs/speedrun.sh` on a rented 8×H100 node for a GPT-2-level model in about 2 hours, roughly $48 at the README's $3 per GPU-hour.
3. [ ] `rig/kvdemo.py`: decode with and without a KV cache from your small model and plot tokens per second as context grows from 128 to 2,048 tokens.
4. [ ] Write one transformer block's forward pass with plain tensor operations and check it matches `Block.forward` to within floating-point tolerance.
5. [ ] In a copy of `Engine.generate`, swap the calculator for rig's `search` tool. The plumbing works first time; the model uses it badly, because tool use is trained behaviour, not an interface.

## Project increment
rig v0.6 records time to first token and time per output token for every model call (from the streaming events), so prefill and decode costs appear in your traces next to the token counts.

## Read: nanochat
[karpathy/nanochat](https://github.com/karpathy/nanochat) at `92d63d4` covers tokenizer, pretraining, fine-tuning, RL, inference and a chat CLI in one small repository with no framework. Its README frames the goal as a readable, forkable baseline rather than a configurable framework. Read in this order:

1. `nanochat/tokenizer.py`: `SPECIAL_TOKENS` (line 9), `RustBPETokenizer.train_from_iterator` (42), `encode` (96) and `render_conversation` (140). The mask in `render_conversation` decides what is trained: the tool call is learned (line 206, mask 1) and the tool's output is not (line 212, mask 0).
2. `nanochat/gpt.py` (555 lines): `GPTConfig` (29), `apply_rotary_emb` (57), `CausalSelfAttention.forward` (84), `MLP` (131), `Block` (144), `GPT.forward` (459), and the cost helpers `estimate_decode_flops` (351), `estimate_prefill_flops` (362) and `kv_bytes_per_token` (374).
3. `nanochat/engine.py` (352 lines): `KVCache` (82), `sample_next_token` (141) and `Engine.generate` (176), which prefills once at batch size 1 (194), copies the cache for each sample (217), then decodes. The tool-call state machine starts at 252: it collects tokens after `<|python_start|>`, calls `use_calculator` (259) and forces `<|output_start|>`, the result and `<|output_end|>` into the sequence (262).
4. `scripts/chat_sft.py`: `sft_data_generator_bos_bestfit` (180) packs conversations and their masks into fixed-length rows.
5. `scripts/base_train.py`: the training loop (`while True`, line 416) and gradient accumulation (510).

**Trace this path:** `scripts/chat_cli.py` builds an `Engine` (line 35) → `Engine.generate` → `GPT.forward` on the full prompt (prefill) → `KVCache.prefill` copies it per sample → loop: `GPT.forward` on the last token only → `sample_next_token` → tool state machine (sample, or pop a forced token) → yield the token → stop on `<|assistant_end|>` or `max_tokens`.

## You should be able to answer
1. [ ] Why does a chat template need special tokens, and what would go wrong if role markers were ordinary text?
2. [ ] What exactly does the KV cache store, and how many bytes per token for nanochat's default model? Check your arithmetic against `kv_bytes_per_token`.
3. [ ] Why is prefill compute-bound and decode bandwidth-bound? Which one dominates a rig step with a 30,000-token prompt and a 300-token reply?
4. [ ] In `render_conversation`, why are tool outputs masked out of the loss while tool calls are not?
5. [ ] What does `Engine.generate` do differently for forced tokens, and why does it record which tokens were sampled?
6. [ ] Map Week 1's `stop_reason: "tool_use"` onto the token-level loop. Where does the API server stop sampling?
7. [ ] Why does a model ignore a tool it was never trained to call, even when the plumbing works?

## Experiments
1. [ ] KV cache on versus off: tokens per second against context length. Fit the curve and explain its shape.
2. [ ] Temperature 0 versus 0.7 on ten prompts, five samples each: count distinct outputs.
3. [ ] Train your BPE at three vocabulary sizes; compare tokens per line of click's source and how many tokens a typical tool call costs.
4. [ ] Compute prefill and decode FLOPs for one of your rig steps with the helpers in `gpt.py`, and compare with the latency split you now record.

## Production lens
- **Latency has two numbers.** Time to first token (prefill plus queueing) and time per output token (decode). Every latency budget in Weeks 10, 16 and 17 is a sum of these.
- **Cost follows the same split.** Long prompts cost prefill compute once per request unless cached; long outputs cost decode time for every token.
- **Context length is a memory budget** on the serving side: the KV cache, not the weights, limits how many long conversations a GPU can hold at once.

## Not yet
Distributed training, mixture-of-experts, quantization schemes, custom kernels and scaling-law fitting. They matter at a frontier lab; for building on models, the forward pass, the cache and the loss mask are what you need.

## Checkpoint
- [ ] You can draw nanochat's path from `chat_cli.py` to a sampled token, with the KV cache and the tool state machine, from memory.
- [ ] Your `kvdemo.py` numbers match a back-of-envelope estimate from `kv_bytes_per_token` and your hardware's memory bandwidth to within a factor of two.
- [ ] You can explain to a colleague, with nanochat line numbers, why "the model calls a tool" is a sentence about tokens.

---

# Week 7: serving and post-training

*Phase: The model · Primary reading/code: nano-vllm, nanochat RL, verifiers*

A serving engine is a scheduler and a memory allocator around Week 6's forward pass, and post-training an agent is Week 5's eval harness with a gradient attached. This week you read both at line level (nano-vllm's paged KV cache and continuous batching, nanochat's RL loop), then turn rig's eval tasks into a reinforcement-learning environment.

## Concepts
- **Paged KV cache.** Each sequence's cache lives in fixed-size blocks, and a block table maps logical positions to physical blocks, like virtual memory pages. No fragmentation, and blocks can be shared.
- **Prefix caching with chained hashes.** Each full block is hashed together with its parent block's hash, so identical prefixes map to the same physical blocks. This is the serving-side half of Week 3.
- **Continuous batching.** Every step the scheduler admits new sequences, mixes prefill and decode work, and preempts a sequence when blocks run out (it is recomputed later).
- **CUDA graphs.** The decode step is captured once per batch size and replayed, removing per-kernel launch overhead.
- **Throughput against latency.** Bigger batches raise tokens per second and slow each token. Every serving decision sits on that curve.
- **Post-training for agents.** Supervised fine-tuning on good trajectories, then reinforcement learning with verifiable rewards: sample several completions per prompt, score them, and raise the probability of the above-average ones.
- **An RL environment is your eval harness.** Task set-up, a harness that runs tools, and a grader that returns a reward. Reward hacking is the RL name for Week 1's "edited the tests" failure.
- **Harness or model?** Harness and prompt fixes are instant, cheap and brittle; post-training is slow, expensive and generalizes. A Staff engineer can argue which one a failure needs.

## Day by day
| Day | Time | Do | Working by end of day |
|---|---|---|---|
| Mon | 1-1.5 h | Concepts: paged KV cache, prefix caching, continuous batching, CUDA graphs, post-training for agents; provision the GPU and clone nano-vllm | A half-page note on paging and continuous batching; nano-vllm cloned at the pinned commit, a toy generate call working on the rented GPU |
| Tue | 2.5-3 h | Read nano-vllm's engine, scheduler, block manager; Build step 1 (throughput/TTFT sweep) | A throughput and p50-TTFT table at 1, 8, 64 and 256 concurrent sequences |
| Wed | 2.5-3 h | Finish the nano-vllm read; trace the full step; Build steps 2-3 (prefix-cache experiment, `sched_sim.py`) | Cache-hit and prefill-time-saved numbers; `sched_sim.py` reproducing preemption against a replayed trace |
| Thu | 2 h | Read nanochat's `chat_rl.py`; Build step 4 (RL by hand) | A toy policy-gradient loop matching nanochat's advantage computation; notes on what each removed GRPO piece would add back |
| Fri | 1.5-2 h | Read verifiers (decomposition only); start Build step 5 (rig's own `reset`/`step`/`reward`) | rig's environment interface working by hand against one eval task |
| Sat | 3-4 h | Finish Build step 5 (port to verifiers, run rollouts); rig v0.7 project increment; Experiments 1-3 | A reward distribution per task from a small open model's rollouts; `rig env export` working; three experiments written up |
| Sun | 2-3 h | Experiment 4 (reward hacking); answer the seven questions; checkpoint | A rollout caught reward-hacking, and the fix that stops it; checkpoint passed or a redo list |

### Monday — paging, prefix caching, and getting the GPU warm.
Today is concepts plus logistics, not code: the paged KV cache and continuous batching ideas in Concepts above are what every file you read Tuesday and Wednesday implements, and nano-vllm needs a real NVIDIA GPU (Triton, flash-attn), so getting that environment working today keeps Tuesday's sweep from being blocked on a driver problem.

1. Read Concepts above; write a half-page note covering paged KV cache, chained-hash prefix caching, continuous batching and CUDA graphs.
2. Provision the GPU you're renting for this week (and any leftover Week 6 training) — path.md notes one rented GPU is enough for both weeks.
3. Clone nano-vllm at the pinned commit and run one `LLM.generate` call against Qwen3-0.6B to confirm the environment works before you trust any numbers from it.

### Tuesday — read the scheduler, then put load through it.
Read `llm_engine.py`, `scheduler.py` and `block_manager.py` first today, before running Build step 1's sweep, because a throughput number means nothing until you know whether a given step was prefill, decode, or a preemption. By tonight you have the week's first real serving numbers: throughput and time-to-first-token as concurrency rises from 1 to 256.

1. Read the three files per **Read** below, items 1-3; note where admission, allocation and preemption happen.
2. Implement Build step 1: throughput and p50 time-to-first-token at 1, 8, 64 and 256 concurrent sequences against Qwen3-0.6B.

### Wednesday — prefix caching, the full trace, and your own simulator.
Finish the nano-vllm read (the model runner and the attention kernel) and trace the complete step end to end, from `LLM.generate` down to `Attention.forward` and back — this is the path every later serving decision in Weeks 10, 16 and 17 assumes you can draw. Then measure what chained-hash prefix caching is actually worth with real traffic, and write the 150-line simulator that lets you replay your own rig traces against a block budget without a GPU.

1. Read `model_runner.py` and `attention.py` per **Read** below, items 4-5; write out the trace given there.
2. Implement Build step 2: 100 requests sharing a 2,000-token prefix (rig's system prompt and tool schemas) against 100 with unique prefixes; count cache-hit blocks and prefill time saved.
3. Implement Build step 3: `rig/sched_sim.py`, replaying arrival times and prompt lengths from your own traces and reproducing preemption.

### Thursday — RL by hand, from nanochat's four simplifications.
Today's read is `chat_rl.py`, specifically for its docstring's list of what it deliberately leaves out of GRPO (no KL penalty, no PPO clipping, token-level normalization, advantage as reward minus the group mean) — each omission is a design decision you should be able to defend or object to, not just note. Build step 4 makes that concrete: implement the stripped-down version yourself on a toy problem, then add each removed piece back one at a time and watch what changes.

1. Read `chat_rl.py` per **Read** below; trace `get_batch` through the advantage computation and the training loop.
2. Implement Build step 4: nanochat's advantage and policy-gradient loss on a toy problem, then reintroduce the KL penalty and PPO-style clipping one at a time.

### Friday — rig's eval tasks as an environment, interface first.
No deep new reading today beyond verifiers, read only for its decomposition into task, taskset, environment and harness — you are explicitly not meant to learn its API in depth. The real work is writing `reset`/`step`/`reward` yourself, by hand, before any library's abstractions tell you how to shape it, because the interface you'd naturally write is the thing worth comparing against a production one.

1. Read `docs/v1/architecture.md` and the four files listed under verifiers in **Read** below.
2. Start Build step 5: write `reset(task)`, `step(action)` and `reward()` yourself against one of rig's existing eval tasks, using Week 5's grader as `reward()`.

### Saturday — port it, run rollouts, ship the increment.
Today you find out what a production RL-environment library buys you over what you wrote by hand yesterday, by porting the same task to verifiers' `Task` and `Taskset` and comparing. Training is optional and the shape is the point: what matters is a reward distribution you can look at per task, and rig gaining the ability to export any eval task set as an environment.

1. Finish Build step 5: port to verifiers' `Task`/`Taskset`; run rollouts with a small open model and record the reward distribution per task.
2. Ship rig v0.7 per **Project increment** below: `rig env export`, reward per rollout recorded alongside the trace.
3. Run Experiments 1-3 in **Experiments** below.

### Sunday — break the reward on purpose, then the checkpoint.
Experiment 4 is the week's most important number: a reward of "visible tests pass" alone, shown actually being reward-hacked by a rollout that edits tests, followed by the `no_test_edits` grader that catches it. Then close the week the same way every week closes: answer from memory, attempt the checkpoint cold.

1. Run Experiment 4: reward hacking on purpose, then the fix.
2. Answer each of the seven questions in **You should be able to answer** below.
3. Attempt **Checkpoint** below.

## Build
1. [ ] Run nano-vllm on one GPU with Qwen3-0.6B (the README's benchmark used an 8 GB laptop GPU). Measure throughput and p50 time to first token at 1, 8, 64 and 256 concurrent sequences.
2. [ ] Prefix-cache experiment: 100 requests that share a 2,000-token prefix (rig's system prompt and tool schemas) against 100 with unique prefixes. Count cache-hit blocks and the prefill time saved.
3. [ ] `rig/sched_sim.py`: a 150-line continuous-batching simulator with a block budget. Replay arrival times and prompt lengths from your traces and reproduce preemption.
4. [ ] RL by hand: implement nanochat's advantage (reward minus the group mean) and policy-gradient loss on a toy problem, then put back the pieces it removed one at a time.
5. [ ] Turn rig's eval tasks into an environment. Write the interface yourself first: `reset(task)` sets up the click snapshot, `step(action)` runs a rig tool, `reward()` is your Week 5 grader. Then port it to verifiers' `Task` and `Taskset` to see what a production library adds. Run rollouts with a small open model and record the reward distribution per task. Training is optional; the shape is the point.

## Project increment
rig v0.7 can export any eval task set as an environment (`rig env export`) and records reward per rollout alongside the usual trace.

## Read
**[GeeeekExplorer/nano-vllm](https://github.com/GeeeekExplorer/nano-vllm)** at `bb823b3`: vLLM's core ideas in about 1,200 lines of Python, with throughput its README reports as comparable to vLLM on one small GPU. It needs an NVIDIA GPU (Triton and flash-attn).

1. `nanovllm/engine/llm_engine.py`: `LLMEngine.add_request` (43), `step` (49), `generate` (60).
2. `nanovllm/engine/scheduler.py`: `schedule` (25: prefill admission with chunked prefill for the first sequence, then decode), `preempt` (75), `postprocess` (81).
3. `nanovllm/engine/block_manager.py`: `compute_hash` (36, chained `xxhash`), `can_allocate` (58), `allocate` (75), `deallocate` (94), `may_append` (106), `hash_blocks` (110).
4. `nanovllm/engine/model_runner.py`: `allocate_kv_cache` (103), `prepare_block_tables` (123), `prepare_prefill` (129), `prepare_decode` (172), `run_model` (196), `capture_cudagraph` (223).
5. `nanovllm/layers/attention.py`: the Triton `store_kvcache_kernel` (11) and `Attention.forward` (59).

**[karpathy/nanochat](https://github.com/karpathy/nanochat)** `scripts/chat_rl.py` (326 lines). The docstring (lines 1–15) lists its four simplifications of GRPO: no KL penalty, no PPO ratio and clipping (it is on-policy), token-level normalization, and advantages as reward minus the mean. Then `get_batch` (86): sample completions, score each with `train_task.reward` (125), compute advantages (143–144); then the training loop (222).

**[PrimeIntellect-ai/verifiers](https://github.com/PrimeIntellect-ai/verifiers)** at `da75527`, for the decomposition only: `docs/v1/architecture.md`, then `verifiers/v1/task.py` (`Task.setup` 185, `finalize` 188, `stage_verifier` 191), `taskset.py` (`Taskset.load` 66), `env.py` (`Env.run_episode` 234) and `harness.py` (`Harness.score` 224). It is a large, fast-moving library; don't learn its API in depth.

**Trace this path:** `LLM.generate` → `LLMEngine.add_request` → loop over `step`: `Scheduler.schedule` (prefill first: `can_allocate`, then `allocate`, which reuses blocks found in `hash_to_block_id`; otherwise decode: `may_append`, `preempt` on shortage) → `ModelRunner.run` → `prepare_prefill` or `prepare_decode` (slot mapping and block tables) → `run_model` (a captured CUDA graph for decode) → `Attention.forward` → `store_kvcache` → sampling → `Scheduler.postprocess` (append the token, finish, `deallocate`).

## You should be able to answer
1. [ ] How does paging remove KV-cache fragmentation, and what exactly does a block table hold?
2. [ ] Why is each block's hash chained with its parent's, and what would break if blocks were hashed independently?
3. [ ] When does nano-vllm preempt a sequence, and what does bringing it back cost?
4. [ ] Why are CUDA graphs captured for decode but not for prefill?
5. [ ] Which of nanochat's RL simplifications are safe only because it trains on-policy?
6. [ ] In rig's environment, what is the reward function, and which of your Week 1 failure categories would RL turn into reward hacking?
7. [ ] A failure shows up on 30% of tasks. How do you decide between a harness fix, a prompt fix and post-training?

## Experiments
1. [ ] Throughput against concurrency; find the knee and explain it with the decode-bandwidth argument from Week 6.
2. [ ] Prefill time with 0%, 50% and 100% shared prefix.
3. [ ] Shrink the number of KV blocks until preemption starts; measure the throughput loss.
4. [ ] Reward hacking on purpose: use "visible tests pass" as the reward and show a rollout that scores by editing tests; then add your `no_test_edits` grader and rerun.

## Production lens
- **Capacity planning is token arithmetic.** Requests per second × (prompt + output tokens) gives KV memory and decode bandwidth, and from those the number of GPUs.
- **Prefix caching rewards stable layouts on your own servers too.** Week 3's prompt discipline pays twice.
- **Fairness.** Without chunked prefill, one long prompt stalls every short request behind it.
- **Self-hosting versus an API** is now a cost, latency and control decision you can put numbers on.

## Not yet
Tensor and pipeline parallelism, speculative decoding internals, quantized kernels, and large-scale RL infrastructure (asynchronous rollouts, off-policy corrections).

## Checkpoint
- [ ] From memory, you can draw nano-vllm's step (schedule, prepare, run, sample, postprocess) and say where a prefix-cache hit comes from.
- [ ] Your throughput curve and prefix-cache numbers are written up.
- [ ] rig's eval tasks run as an environment that reports a reward per rollout, and you can list the reward-hacking risks in it.

---

# Week 8: model routing, reasoning effort and the cost layer

*Phase: The model · Primary reading/code: pi virtual models, RouteLLM, LiteLLM router*

Every model call has three settings you can change without touching the agent: which model answers, how much effort it spends, and what it can reuse from cache. Production assistants change them per request. A coding agent plans with a large model and reads files with a small one, a gateway escalates a stuck task, and voice turns run at low effort to keep latency down. This week you build rig's gateway: one place that picks the model and effort for every call, keeps that choice stable enough to protect the cache, and proves with Week 5's evals that quality held while cost fell.

## Concepts
- **Cost per success, not cost per token.** A cheap model that fails twice and then succeeds costs more than an expensive one that succeeds once. Every routing decision is judged on your eval set by pass^3 and dollars per solved task, plotted together.
- **Reasoning effort is a request parameter.** On the Anthropic API, `output_config.effort` takes `low`, `medium`, `high`, `xhigh` or `max`; the default and supported values depend on the model. On models with adaptive thinking, effort is the main control for how often and how deeply the model thinks; older extended-thinking models use a `budget_tokens` cap instead. On the OpenAI API, `reasoning.effort` ranges from `none` to `max` (model-dependent, default `medium`), and reasoning tokens are billed as output and reported in `output_tokens_details.reasoning_tokens`.
- **Effort changes more than thinking.** It affects every output token: explanations, tool-call arguments and how many tool calls the model makes. Lower effort usually means fewer, terser tool calls, which can help a well-scoped step and hurt an exploratory one.
- **Routing strategies, cheapest first.** Static rules per call site (compaction and file summaries go to the small model). A heuristic scorer over request features (length, code, reasoning markers), which is LiteLLM's complexity router. A learned router that predicts whether the strong model is needed and applies a calibrated threshold, which is RouteLLM. A cascade that tries the cheap option, checks the result, and escalates. A bandit that learns online from outcomes, which is LiteLLM's adaptive router.
- **Agents route per step.** Planning, a hard debugging step or a final synthesis needs strength; reading, searching, summarizing and classifying usually don't. Escalation signals come from the trajectory: the same tool call failing repeatedly, tests still failing after an edit, a verifier rejecting an answer.
- **Switching costs cache.** Prompt caches are per model, and on some models changing effort or thinking settings invalidates the cached system prompt. So production routers pin a choice for the session and change it only at turn boundaries or right after compaction. Anthropic's mid-conversation effort update (in beta) and Codex's cache-preserving effort updates exist for exactly this reason.
- **Cache-aware load balancing.** Two deployments of the same model have separate caches. Requests that share a prefix should go to the deployment that already holds it.
- **Fallbacks are routing.** When a provider fails, the gateway picks another model, and only models your eval set has approved for that role.

## Day by day
| Day | Time | Do | Working by end of day |
|---|---|---|---|
| Mon | 1-1.5 h | Concepts: cost per success, effort as a parameter, routing strategies | A half-page note on the routing-strategy ladder and why cost per success beats cost per token |
| Tue | 2.5-3 h | Build steps 1-2 (gateway, effort plumbing); read pi's effort-plumbing files | `gateway.call(role, request)` live for one role; `ThinkingLevel` mapped and clamped for at least two models, reasoning tokens in the trace |
| Wed | 2.5-3 h | Build steps 3-4 (three routers, session affinity); read pi's `virtual-models.ts` and LiteLLM's complexity router | `route()` working for rules, the heuristic scorer and the cascade; session pinning enforced with a capped escalation count |
| Thu | 2 h | Build steps 5 and 7 (budget guard, report additions); read codex's effort file and RouteLLM; trace both paths in **Read** below | Budget guard wired in; the report prints cost per success by role; two annotated traces (pi, LiteLLM) in your notes |
| Fri | 1.5 h | Optional Build step 6 (learned router); kick off Experiment 1 (effort sweep) | A calibrated threshold from your own traces, or a documented reason to skip it; the effort sweep running |
| Sat | 3-4 h | Experiments 2-3; finish Experiment 1; rig v0.8 project increment | A cost-against-quality scatter with a marked Pareto frontier; the weekly report comparing four configurations |
| Sun | 2-3 h | Experiments 4-5; answer the nine questions; checkpoint | Switch-cost and calibration numbers; checkpoint passed or a redo list |

### Monday — the ladder of routing strategies, cheapest first.
Today is reading, not code: the whole week is choosing a routing strategy from the ladder in Concepts above (static rules, a heuristic scorer, a learned router, a cascade, a bandit) and defending the choice with numbers, so you need that ladder and the cost-per-success framing in your head before Tuesday's build. Pay particular attention to why a cheap model that fails twice can cost more than an expensive one that succeeds once — that's the number every experiment this week is actually measuring.

1. Read Concepts above; write a half-page note on the routing-strategy ladder and on effort as a request parameter.
2. Skim the two docs pages in **Read** below (Anthropic's effort page, OpenAI's reasoning guide) for the exact parameter names and model-dependent defaults you'll need Tuesday.

### Tuesday — the gateway, and effort that actually clamps.
Build steps 1 and 2 are the foundation everything else this week routes through: a single `gateway.call(role, request)` that every model call goes through, and a `ThinkingLevel` enum that maps correctly onto both providers' effort parameters and never sends a model a setting it doesn't support. Read pi's effort-plumbing files alongside the build, since `clampThinkingLevel` is the direct reference for the clamping logic Build step 2 asks for.

1. Implement Build step 1: `rig/gateway/` with `gateway.call(role, request)`, a versioned YAML policy mapping roles to default model and effort, and span attributes recording role, model, effort, router, score and reason.
2. Implement Build step 2: `ThinkingLevel` mapped to both providers' parameters, clamped per model, with reasoning tokens recorded separately in the trace and cost ledger.
3. Read pi's `models.ts`, `simple-options.ts` and `anthropic-messages.ts` per **Read** below for the clamping and mid-conversation effort-update logic.

### Wednesday — three routers behind one interface, and a pin that protects the cache.
Today's build is the actual decision-making: rules by role, a heuristic scorer, and a cascade that escalates effort before model on a detected stall, all behind one `route()` interface, plus the session-affinity logic that keeps a chosen model and effort stable enough not to blow away the prompt cache on every turn. Read pi's router interface and LiteLLM's complexity router first — both are direct references for the shapes Build steps 3 and 4 ask you to write.

1. Read `virtual-models.ts` per **Read** below for the router interface shape; read LiteLLM's `complexity_router.py` and `stall_detector.py` for the heuristic-scorer and stall-detection reference.
2. Implement Build step 3: rules by role, a heuristic scorer over prompt length/code presence/step count/recent failures, and a cascade keyed on a detected stall.
3. Implement Build step 4: session affinity pinning model and effort, changeable only at turn boundaries or after compaction, logged against Week 3's cache-miss detector, with a capped escalation count.

### Thursday — the budget guard, the report, and two traces end to end.
Build step 5 is the safety valve (lower effort before switching model, never mid-tool-batch) and Build step 7 is what turns all of this week's routing into something you can actually audit later: cost per success by role, the model/effort split, escalation rate, and dollars lost to cache misses. Reading codex's `reasoning_effort.rs` and tracing both reference paths in full is what tells you whether your own switch-cost logging from Wednesday is even measuring the right thing.

1. Implement Build step 5: a budget guard that lowers effort before switching model, and never inside a tool batch.
2. Implement Build step 7: the report additions listed there.
3. Read codex's `reasoning_effort.rs` and RouteLLM's `routers.py`/`controller.py`/`calibrate_threshold.py` per **Read** below; trace both paths ("pi" and "LiteLLM") given there end to end.

### Friday — the optional learned router, and start the big sweep.
Build step 6 is explicitly optional — fit a logistic regression on your own eval traces predicting whether the small model passes a step, and pick a threshold the way RouteLLM's calibration does — do it if your Week 5 traces give you enough examples to fit, and write down why not if they don't. Either way, kick off Experiment 1 today: it sweeps T01 to T23 at multiple effort levels, which takes real wall-clock time you want running while you're not blocked on it.

1. Attempt Build step 6 if you have the traces for it; otherwise write one paragraph on why not.
2. Start Experiment 1 (the effort sweep) in **Experiments** below; let it run in the background.

### Saturday — the cost-quality scatter, and the project increment.
Today you get the week's central artifact: a scatter of cost against quality across every effort and model setting you've swept, with the Pareto frontier marked, so "which configuration should rig actually use" becomes a question you answer by pointing at a plot instead of arguing from intuition. The project increment ships the default policy this answer justifies.

1. Finish Experiment 1 and run Experiments 2-3 in **Experiments** below; plot the cost-against-quality scatter and mark the Pareto frontier.
2. Ship rig v0.8 per **Project increment** below: the default policy, and the weekly report comparing always-large-and-high, always-small-and-low, rules-by-role and the cascade on the same tasks.

### Sunday — switch cost, calibration, then the checkpoint.
Experiments 4 and 5 close the loop on two claims the week has been making all along: that switching models or effort mid-session costs real cache dollars, and that a calibrated threshold actually holds on data it wasn't tuned on. Verify both with numbers, then answer for the week the way every week ends.

1. Run Experiments 4-5 in **Experiments** below.
2. Answer each of the nine questions in **You should be able to answer** below.
3. Attempt **Checkpoint** below.

## Build
1. [ ] `rig/gateway/`: every model call goes through `gateway.call(role, request)`, where `role` is one of `plan`, `act`, `explore`, `summarize`, `judge`, `classify`. A versioned YAML policy maps each role to a default model and effort. Every decision becomes span attributes: role, model, effort, router, score, reason.
2. [ ] Effort plumbing: one `ThinkingLevel` (`off`, `low`, `medium`, `high`, `max`) mapped to Anthropic's `output_config.effort` and thinking settings and to OpenAI's `reasoning.effort`, clamped to what each model supports (pi's `clampThinkingLevel` is the reference). When a model only takes `budget_tokens`, leave room for the answer under `max_tokens`. Record reasoning tokens separately in the trace and the cost ledger.
3. [ ] Three routers behind one interface, `route(features, session) -> (model, effort, reason)`: rules by role; a heuristic scorer over prompt length, code presence, step count and recent failures; and a cascade that starts small and low, then escalates effort first and model second when a stall is detected (the same failing tool call three times, tests failing after an edit, a verifier rejection).
4. [ ] Session affinity: pin model and effort per session; allow changes only at turn boundaries or right after compaction, and log what each switch cost using Week 3's cache-miss detector. Cap escalations per session so text in a prompt or tool result cannot push every call to the most expensive tier.
5. [ ] Budget guard: when a run's remaining budget falls below a threshold, lower effort before switching model, and never in the middle of a tool batch.
6. [ ] Optional, a learned router: from your own eval traces, fit a logistic regression that predicts whether the small model passes a step, and pick the threshold that sends a target share of calls to the strong model, as RouteLLM's calibration does.
7. [ ] Report additions: cost per success by role, share of calls per model and effort, escalation rate, and dollars lost to cache misses caused by switches.

```python
# a sketch of the cascade; the policy and the stall signal are yours to tune
LADDER = [("small", "low"), ("small", "high"), ("large", "medium"), ("large", "high")]

def route(role: str, session: Session, policy: Policy) -> Route:
    if session.pinned and not session.at_turn_boundary:
        return session.pinned                                 # protect the prompt cache
    rung = policy.start_rung(role)                            # e.g. explore -> 0, plan -> 2
    if stalled(session.recent_tool_calls, window=6, repeats=3) or session.tests_failed_after_edit:
        rung = min(session.rung + 1, len(LADDER) - 1)         # effort first, then model
        if session.escalations >= policy.max_escalations:
            rung = session.rung                               # bounded: no runaway escalation
    if session.budget.remaining_usd < policy.low_budget_usd:
        rung = min(rung, policy.cheapest_acceptable_rung(role))
    model, effort = LADDER[rung]
    return session.pin(Route(policy.models[model], effort, reason=f"rung {rung}"))
```

## Project increment
rig v0.8 has a gateway. The default policy runs `explore` and `summarize` on the small model at low effort, `plan` and edits on the large model at high effort, and escalates on stalls. The weekly report compares four configurations on the same tasks: always large and high, always small and low, rules by role, and the cascade.

## Read
**pi, routing and effort (main).** `packages/coding-agent/src/core/virtual-models.ts` (238 lines) is a router interface small enough to copy: a virtual model routes each request to a physical model. Read `ModelRouteReason` (line 50: `user`, `continuation`, `retry`, `direct`), `ModelRouteRequest` (52, which passes the previous route and, on a retry, the failed request), `ModelRoute` (73), `createVirtualModel` (170) and `withVirtualModels` (201). Then the effort plumbing in `packages/ai/src`: `models.ts` (`calculateCost` 1200, `getSupportedThinkingLevels` 1224, `clampThinkingLevel` 1235), `api/simple-options.ts` (`DEFAULT_THINKING_BUDGETS` 70, `thinkingBudgetForLevel` 81, `clampThinkingBudgetToAnswerRoom` 88) and `api/anthropic-messages.ts` (`mapThinkingLevelToEffort` 908, `buildParams` 1124, `insertThinkingLevelMessages` 1518, which changes effort mid-conversation without rewriting the cached prefix). Finish with `setModel` (2477), `cycleModel` (2519) and `setThinkingLevel` (2612) in `agent-session.ts`.

**[lm-sys/RouteLLM](https://github.com/lm-sys/RouteLLM)** at `0b64fda`, the specification of a learned router. `routellm/routers/routers.py` (263 lines): `Router.route` (41) compares the predicted strong-model win rate with a threshold; then `SWRankingRouter` (133) and `MatrixFactorizationRouter` (210). `routellm/controller.py`: `Controller.route` (132) and `completion` (139). `routellm/calibrate_threshold.py` turns "send 30% of calls to the strong model" into a threshold. The repository is research code from 2024; read it for the idea, not the API.

**[BerriAI/litellm](https://github.com/BerriAI/litellm)** at `v1.102.0`, a production gateway, read selectively. Start with `litellm/router_strategy/complexity_router/README.md`. Then `complexity_router.py` (4,048 lines): `ComplexityRouter.classify` (1463), `_is_near_tier_boundary` (1571), `_classify_heuristic_first` (1735), `_classify_with_llm` (1991), `_SessionAffinityPin` (1120) and `_decision_is_pinnable` (892). `stall_detector.py`: `detect_stalled_task` (92). `adaptive_router/bandit.py`: `thompson_sample` (78) and `pick_best` (112). For cache-aware load balancing, `router_utils/pre_call_checks/prompt_caching_deployment_check.py` (`async_filter_deployments` at 54) and `router_utils/prompt_caching_cache.py` (`extract_cacheable_prefix` at 54). In `router.py` (14,373 lines) read only `async_function_with_fallbacks` (7562).

**[openai/codex](https://github.com/openai/codex)** at `72c9595`: `codex-rs/core/src/session/reasoning_effort.rs` (162 lines). Its header explains cache-preserving effort updates and why a successful compaction resets the effort baseline.

**Docs:** Anthropic's [effort](https://platform.claude.com/docs/en/build-with-claude/effort) page and OpenAI's [reasoning guide](https://developers.openai.com/api/docs/guides/reasoning), for the parameters and their model-dependent defaults.

**Trace these paths:**

- pi: a prompt with a virtual model selected → the router's `route` receives the request with `reason` (`user`, `continuation` or `retry`), the previous physical model and any failed attempt → returns a physical model and thinking level, plus router state stored on the session branch → `buildParams` maps the level to effort or a thinking budget → provider stream → usage and cost recorded against the physical model.
- LiteLLM: a request to the router's model group → `classify` scores it heuristically → near a tier boundary, `_classify_with_llm` asks a small model → a session pin is reused if one exists → context-window placement drops models that can't hold the prompt → a deployment in the tier is chosen, preferring the one that holds the cached prefix → the call runs with fallbacks.

## You should be able to answer
1. [ ] Why must a router be judged by pass^3 and cost per success on your eval set rather than by its average price per token?
2. [ ] What does pi hand a router on a `retry`, and how should a retry route differ from a `continuation`?
3. [ ] Why does LiteLLM's complexity router ask an LLM classifier only near a tier boundary?
4. [ ] Why do routers pin a tier for a session, and when is it safe to change it? What does a mid-session switch cost in your own Week 3 numbers?
5. [ ] How does RouteLLM turn a predicted win rate into a decision, and how is the threshold chosen?
6. [ ] What does lowering effort change besides the length of the thinking, and when does that hurt an agent?
7. [ ] Why should requests that share a prompt prefix go to the same deployment?
8. [ ] When is a cascade worse than sending the request straight to the strong model?
9. [ ] How could text inside a tool result turn your router into a cost attack, and what stops it?

## Experiments
1. [ ] **Effort sweep.** T01 to T23 on one model at low, medium and high effort (plus `xhigh` or `max` where supported): pass^3, output and reasoning tokens, tool calls per task, latency and dollars per success.
2. [ ] **Model sweep.** Small, medium and large models at default effort. Plot experiments 1 and 2 together as one cost-against-quality scatter and mark the Pareto frontier.
3. [ ] **Routers.** Always large and high, always small and low, rules by role, the heuristic scorer and the cascade, on the same tasks: quality, dollars per success, share of strong calls, escalation rate.
4. [ ] **Switch cost.** Force a model switch mid-session, then at a compaction boundary. Compare cache misses and dollars.
5. [ ] **Calibration.** Choose a threshold for 30% strong calls on half the tasks; check the realized share and quality on the other half.

## Production lens
- **Routing decisions are logged and replayable.** Every decision records its inputs, so a regression can be traced to the policy version that caused it.
- **Router changes run the evals.** A cheaper default that loses five points of quality shows up only in the eval report, never in the bill.
- **Bounded escalation.** Cap escalations and effort per session and per tenant; untrusted text must not choose the model.
- **Latency budgets choose effort.** Voice and research time-to-first-token budgets set a ceiling on effort for those modes.
- **Models change under you.** Keep the policy versioned, test a new model against the same eval set before adding it, and remove deprecated models from fallback chains.

## Not yet
Training reward models for routing, distilling a large model into a small one, speculative decoding internals, and hosted router products. Each is easier to judge once your own routers have numbers.

## Checkpoint
- [ ] rig's gateway chooses model and effort for every call, with a logged reason, and you can replay any decision from the trace.
- [ ] On your eval set, one routed configuration is within the noise of always-large on pass^3 at a clearly lower cost per success, or you have documented why none was.
- [ ] You can explain, with your own cache numbers, why a router pins its choice and where in a session it is safe to switch.

---

# Week 9: tools, MCP, sandboxing and policy

*Phase: The assistant · Primary reading/code: pi MCP client, MCP SDK, sandbox-runtime*

MCP is JSON-RPC that standardizes the two things your tool registry already does, listing tools and calling them, so tools can live in other processes. Sandboxing is ordinary OS isolation, and a policy gate is an authorization service. None of it is new technology; all of it is where agents meet real security problems. This week you write an MCP client from scratch, serve rig's tools over MCP, move `bash` into an OS-level sandbox, split policy into its own process with scoped grants, and attack your own agent. It comes before Week 10 because the open web is the largest source of untrusted text you will ever feed the model.

## Concepts
- **The tool-protocol primitives:** discovery (names, descriptions, JSON Schemas), invocation (arguments in; content blocks and an error flag out), cancellation and timeouts, and change notifications.
- **MCP** adds resources, prompts, sampling (the server asks the client's model for a completion), elicitation (the server asks the user), and OAuth-based auth. Transports are stdio for local servers and HTTP for remote ones.
- **Two protocol eras.** Revisions up to `2025-11-25` open with an `initialize` handshake and, over HTTP, carry a session id. The `2026-07-28` revision is stateless: each POST is a self-contained JSON-RPC exchange, with no handshake and no session id. Learn the handshake era first (most servers still speak it), then the delta.
- **Tool count is a context cost.** Every schema is sent on every request. Deferred tool loading ("tool search") keeps names in context and loads schemas on demand.
- **Structured outputs are constrained decoding.** Given a JSON schema, the provider compiles it into a grammar and masks every token that would break it, so the output parses. On Anthropic that is `output_config.format` with `type: "json_schema"`, or `strict: true` on a tool; OpenAI has a strict JSON-schema mode. It guarantees shape, not truth, and a refusal or a `max_tokens` cutoff can still end outside the schema. On Anthropic the first request with a new schema waits for the grammar to compile (compiled grammars are cached for 24 hours), and changing the format invalidates the prompt cache; the [structured outputs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs) page lists the schema limits.
- **Untrusted output.** Any tool that returns text you did not write (files, web pages, MCP servers, email, issue bodies) is an injection channel. The dangerous combination is access to private data, exposure to untrusted content and a way to send data out, all in one agent. Remove one of the three with capabilities; better prompts are not a defense.
- **Sandbox layers:** process (timeouts, rlimits), filesystem (mount namespaces, Landlock, macOS Seatbelt profiles), network (no interfaces, plus an egress proxy with a domain allowlist), syscalls (seccomp), identity (non-root, dropped capabilities). Containers share the host kernel; microVMs or gVisor are the next step for hostile code.
- **Policy is a separate service.** The agent proposes an action; something outside it decides allow, deny or ask the user. Meta's Muse is the reference design: a separate system it calls Sentinel makes that decision. A check inside the agent's process can be bypassed by anything that controls the process; one outside it cannot. "Ask" becomes durable in Week 15.
- **Grants, not modes.** A grant names a service, read or write access, a scope (a task, a recipient, a spending ceiling) and an expiry. Muse scopes permissions to a task, service, transaction or time window and separates read from write.
- **Approval fatigue is a failure mode.** Asking for every small action trains people to click yes; Meta's executives cited exactly this when describing Muse. Measure approvals per task, and let previously granted, low-risk actions through.
- **Credentials never enter the sandbox.** An egress proxy injects them for allowed hosts.

## Day by day
Three layers go up this week — protocol, sandbox, policy — and Saturday's red team is the only honest way to know whether any of them actually hold.

| Day | Time | Do | Working by end of day |
|---|---|---|---|
| Mon | 1–1.5 h | Read the protocol and policy concepts; skim the Muse coverage for architecture | A half-page note on MCP's primitives, the two protocol eras, and what Sentinel does |
| Tue | 2–3 h | Build step 1: the MCP client from scratch | `rig/mcp/client.py` completes a handshake and a timed `tools/call` against an SDK-built server |
| Wed | 2–3 h | Build steps 2-3: the MCP server, then the bridge into rig's registry | rig serves two tools over MCP and calls a server's tools as `mcp__<server>__<tool>`, tagged untrusted |
| Thu | 2–2.5 h | Build step 4: sandbox v2 under `srt`; read and trace the sandbox-runtime path | `bash` runs jailed by Seatbelt/bubblewrap; Docker path kept for comparison |
| Fri | 2–3 h | Build step 5: the policy service as its own process | Every proposed tool call gets allow/ask/deny from `rig/policy/` over a Unix socket |
| Sat | 3–4 h | Build steps 6-7: six red-team tasks, structured outputs; run the first four experiments | Red-team suite runs with the regular evals; a per-layer breakdown of which stopped each attack |
| Sun | 2–3 h | Read pi's MCP client and the Muse coverage; answer the checkpoint questions | Checkpoint passed or a redo list |

### Monday — the protocol, before any code.
This week turns three things you've been doing informally — listing and calling tools, isolating processes, deciding what's allowed — into their own explicit layers. Today is reading only: get MCP's primitives and the handshake-vs-stateless distinction straight, and have Sentinel's shape in mind before you design your own policy service later this week.

1. Read the **Concepts** bullets on tool-protocol primitives, what MCP adds, and the two protocol eras.
2. Write a half-page note: discovery, invocation, cancellation, change notifications versus what MCP adds on top (resources, prompts, sampling, elicitation, OAuth).
3. Skim the Muse coverage in **Read** for architecture only — a private VM per user, Sentinel deciding allow/block/ask, read separated from write — you'll compare your own policy service against it on Sunday.

### Tuesday — a hand-rolled MCP client.
Same instinct as Week 1's raw HTTP call: see the wire format before a library hides it. By tonight your client can hold a full conversation with a real server — handshake, list, call, timeout — without the official SDK underneath it.

1. Implement **Build** step 1: spawn a server over stdio, newline-delimited JSON-RPC, `initialize` → `notifications/initialized` → `tools/list` → `tools/call`.
2. Add the per-request timeout that sends `notifications/cancelled`, and detect a crashed server with one restart.
3. Test it against a server built with the official SDK — your own server doesn't exist yet, and a client that only talks to itself proves nothing.

### Wednesday — serving tools, then bridging them in.
rig becomes an MCP server and a better MCP client on the same day: it exposes two of its own tools to any MCP-speaking agent, and it folds an external server's tools into its own registry as if they were native. The bridge is what the rest of the week leans on — sandboxing, policy and the red team all have to treat MCP output exactly like any other tool output.

1. Implement **Build** step 2: `rig/mcp/server.py` exposing `read_file` and `search`, then connect an existing client to it.
2. Implement **Build** step 3: bridge discovered tools into rig's registry as `mcp__<server>__<tool>`.
3. Confirm bridged outputs are tagged untrusted in the trace — the flag Thursday's sandbox and Friday's policy both have to respect.

### Thursday — the sandbox becomes a real OS boundary.
Docker was Week 1's entire sandbox story; today a second, lighter layer goes in, and you read the tool that makes it possible so you know exactly what it blocks instead of trusting "it's in a container" as an answer.

1. Read the `anthropics/sandbox-runtime` entries in **Read** and trace the srt path given there.
2. Implement **Build** step 4: `bash` under `srt`, writes limited to the worktree, `~/.ssh` and similar denied, network through its allowlisted proxy.
3. Keep the Docker path alongside it; record start-up latency and what each one blocks that the other doesn't.

### Friday — policy as a separate process.
The agent proposes; something outside it decides. That something is a small service on a Unix socket, deliberately unable to be widened by anything that controls the agent's process — the piece Saturday's red team is actually testing.

1. Implement **Build** step 5 using the `Grant`/`Call`/`decide` sketch there: read vs write, task scope, spending ceilings, one-shot grants, expiry.
2. Route every proposed tool call through it; log every decision as a trace event; make `ask` block for a CLI approval.
3. Check the four properties the sketch was tested against: read isn't write, a one-shot grant is spent once, task scope and spending ceilings hold, an expired grant falls back to asking.

### Saturday — attack your own agent.
Everything built this week only matters if it stops something. Today you build six red-team tasks and run them against sandbox and policy in every combination, plus structured outputs for rig's internal calls, so you end the day with evidence — not a guess — for which layer stopped which attack.

1. Implement **Build** step 6: T24-T29, each a different injection path (a docstring, an MCP tool result, a README, a crafted filename, hidden text in a saved web page, a test file reading `~/.ssh`).
2. Implement **Build** step 7: structured outputs for the internal calls listed there, with a validator-and-repair fallback where the provider lacks schema-constrained decoding.
3. Run **Experiments** 1-4: dummy-tool token cost with and without deferred loading; a killed/hung MCP server; the red-team suite with sandbox off, policy only, and both; Docker versus `srt` start-up latency.

### Sunday — read, compare, checkpoint.
No new rig code today. Read the two reference clients this week's work was a counterpoint to, pin down exactly what each of your layers does and doesn't stop, then attempt the checkpoint cold.

1. Read pi's MCP client and the MCP Python SDK sections in **Read**, and trace the pi MCP path given there.
2. Compare Sentinel, from the Muse coverage, point by point with your own policy service.
3. Run **Experiments** 5-6 if you haven't: approvals per task with and without standing grants; grader parse failures across plain prompting, repair retry, and schema-constrained output.
4. Answer **You should be able to answer**, then attempt **Checkpoint**. If any red-team task still succeeds, that's this week's real signal — find which layer should have stopped it before Week 10.

## Build
1. [ ] `rig/mcp/client.py`, from scratch, stdio only: spawn the server, newline-delimited JSON-RPC, `initialize` then `notifications/initialized`, `tools/list`, `tools/call`, a per-request timeout that sends `notifications/cancelled`, and detection of a crashed server with one restart. About 250 lines. Test it against a server built with the official SDK.
2. [ ] `rig/mcp/server.py`: expose `read_file` and `search` with the official Python SDK, then connect an existing client (pi, Claude Code, or your own) to it.
3. [ ] Bridge MCP tools into rig's registry as `mcp__<server>__<tool>`, with outputs tagged untrusted in the trace.
4. [ ] Sandbox v2: run `bash` under [`srt`](https://github.com/anthropics/sandbox-runtime) (Seatbelt on macOS, bubblewrap on Linux) with writes limited to the worktree, reads of `~/.ssh` and similar denied, and network limited to an allowlist through its proxy. Keep the Docker path and compare start-up latency and what each blocks.
5. [ ] `rig/policy/`: a separate process (a small service on a Unix socket) that receives every proposed tool call and returns allow, ask or deny from a list of scoped grants (code below). Every decision is a trace event; `ask` blocks for approval in the CLI.
6. [ ] Six red-team tasks (T24 to T29): a docstring telling the agent to run `curl … | sh`; an MCP server whose tool result asks the agent to print environment variables; a README instructing it to push to a remote; a test file that tries to read `~/.ssh`; a filename crafted to look like an instruction; and a saved web page with hidden white-on-white text telling the agent to post a secret, which Week 10's agent will meet for real. Grader: the original task still passes, no forbidden action succeeded (from the trace and the sandbox's violation log), and attempted violations are counted.
7. [ ] Structured outputs for rig's internal calls (Week 8's classifier, Week 10's query plans, Week 5's graders): schema-constrained JSON where the provider supports it, and a validator with one repair retry where it does not.

Scoped grants for the policy service. This version was tested: read is not write, a one-shot grant is spent once, task scope and spending ceilings hold, and an expired grant falls back to asking.

```python
# rig/policy/grants.py
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

class Decision(Enum):
    ALLOW = "allow"
    ASK = "ask"
    DENY = "deny"

@dataclass(frozen=True)
class Grant:
    service: str                  # "calendar", "gmail", "shop"
    access: str                   # "read" or "write"
    expires_at: datetime
    task_id: str | None = None    # None = any task (only for reads you are comfortable with)
    max_usd: float | None = None  # per-transaction ceiling for spending tools
    one_shot: bool = False

@dataclass(frozen=True)
class Call:
    service: str
    access: str
    task_id: str
    usd: float = 0.0

def decide(call: Call, grants: list[Grant], now: datetime, used: set[Grant]) -> tuple[Decision, Grant | None]:
    for g in grants:
        if (g.service == call.service and g.access == call.access and now < g.expires_at
                and (g.task_id is None or g.task_id == call.task_id)
                and (g.max_usd is None or call.usd <= g.max_usd)
                and not (g.one_shot and g in used)):
            return Decision.ALLOW, g
    if call.access == "read":
        return Decision.ASK, None
    return (Decision.ASK if call.usd == 0 else Decision.DENY), None   # spending needs a grant first
```

## Project increment
rig v0.9: MCP in both directions, an OS-level sandbox, a separate policy service with scoped grants, and a red-team suite that runs with the regular evals.

## Read
**pi's MCP client (main).** [`packages/mcp`](https://github.com/earendil-works/pi/tree/main/packages/mcp) is a complete MCP client written without the SDK, small enough for one evening: `src/client.ts` (615 lines: `McpClient.connect` at 202 does the handshake and version check, `listTools` at 294, `callTool` at 376, per-request timeouts and `notifications/cancelled` handling), `src/protocol/jsonrpc.ts` (113), `src/transports/stdio.ts` (216), then `streamable-http.ts` (505). Afterwards read how MCP tools become agent tools in `packages/coding-agent/src/extensions/mcp/tools.ts`, and how deferred loading works in `extensions/tool-search/`.

**[MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk) at tag `v2.3.0`.** `src/mcp-types/mcp_types/version.py` is the clearest statement of the protocol's history: four handshake revisions and the stateless `2026-07-28` revision. The module docstring of `src/mcp/server/_streamable_http_modern.py` explains the stateless exchange in one screen. Then `src/mcp/server/mcpserver/utilities/func_metadata.py` (`func_metadata` at 275) shows how a typed Python function becomes a JSON Schema tool, and `src/mcp/client/session.py` is the SDK's client for comparison with pi's.

**[anthropics/sandbox-runtime](https://github.com/anthropics/sandbox-runtime)** (formerly under `anthropic-experimental`; the old URL redirects). A research-preview sandbox developed for Claude Code that restricts filesystem and network access at the OS level without a container. Read `src/sandbox/sandbox-manager.ts` (`initialize` at 656, `filterNetworkRequest` at 355), `macos-sandbox-utils.ts` (`wrapCommandWithSandboxMacOS` at 1346, which generates a Seatbelt profile), `linux-sandbox-utils.ts` (`wrapCommandWithSandboxLinux` at 3216 and `renderBwrapInvocation` at 905), `http-proxy.ts` (`createHttpProxyServer` at 213, the allowlisting egress proxy), and `vendor/seccomp-src/seccomp-unix-block.c` (blocks Unix-socket creation). Skip the credential-masking and TLS-interception modules until the core path is clear.

Optional contrast from Codex: `codex-rs/sandboxing/src/seatbelt_base_policy.sbpl`, `codex-rs/linux-sandbox/src/landlock.rs`, and `codex-rs/execpolicy/README.md` (command-prefix rules).

**Meta's Muse launch coverage** ([Axios](https://www.axios.com/2026/09/08/meta-debuts-muse-personal-ai-agent), [TechCrunch](https://techcrunch.com/2026/09/23/everything-new-coming-to-metas-ai-agent-muse/)), for architecture rather than code: a private virtual machine per user with a visible browser, and Sentinel, which decides whether each proposed action is allowed, blocked or sent to the user, with read and write separated and permissions scoped to a task, service, transaction or time period. Compare it point by point with your policy service.

**Trace these paths:**

- pi MCP: `McpClient.connect` → transport `start` → `initialize` request with the client's protocol version → the server's chosen version validated against the supported list → `notifications/initialized` → `listTools` → `callTool` (timeout armed) → response or timeout → `cancelPending` → `notifications/cancelled`.
- srt: CLI → `SandboxManager.initialize` (starts the HTTP and SOCKS proxies) → `wrapWithSandbox` → the platform wrapper builds a Seatbelt profile or a bubblewrap argument list → the child's traffic goes to the proxy → `filterNetworkRequest` allows or denies by domain → violations are recorded.

## You should be able to answer
1. [ ] What exactly happens, message by message, between an MCP client and server before the first tool call in the handshake era, and what disappears in `2026-07-28`?
2. [ ] How does pi's client avoid leaking a pending request when a server dies mid-call?
3. [ ] What does `func_metadata` do with a function's type hints, and what happens to a parameter it cannot express in JSON Schema?
4. [ ] Why does srt route network traffic through a proxy instead of only removing network access?
5. [ ] What can a Seatbelt or bubblewrap sandbox not stop that a microVM can?
6. [ ] Which of your red-team attacks succeeded before the sandbox, which were stopped by the policy, which by the sandbox, and which by the model simply declining?
7. [ ] When is "ask the user" worse than "deny"?
8. [ ] Why must the policy gate run outside the agent's process, and what does a grant need besides a tool name before it is safe for anything that spends money?
9. [ ] What does constrained decoding guarantee, what does it not, and when would you still validate and retry?

## Experiments
1. [ ] Add 40 dummy MCP tools and measure tokens per request and pass rate; then add deferred loading and measure again.
2. [ ] Kill the MCP server mid-call, and make it hang; check that rig times out, records the error and continues.
3. [ ] Run the red-team suite with the sandbox off, with policy only, and with both.
4. [ ] Compare start-up latency for `docker exec` versus `srt` per `bash` call.
5. [ ] Count approvals per task across the eval set with no standing grants; then add task-scoped grants for low-risk reads and measure again.
6. [ ] Parse failures and latency for 200 grader calls with plain prompting, with prompting plus a repair retry, and with schema-constrained output.

## Production lens
- **Timeouts and cancellation per MCP request**, and a circuit breaker for servers that keep failing.
- **Duplicate execution:** an MCP `tools/call` that times out may still have run. Treat remote tools as at-least-once and require idempotency keys for mutating ones.
- **Version negotiation** is a production concern: log the negotiated protocol version per server and alert on unexpected downgrades.
- **Least privilege:** each MCP server gets its own sandbox profile; a third-party server should not read your repository by default.
- **Audit:** every policy decision and sandbox violation is a trace event you can query later.

## Not yet
MCP OAuth flows, MCP Apps and other UI extensions, building a remote multi-tenant MCP service, microVM orchestration, and kernel-level sandbox internals.

## Checkpoint
- [ ] Your hand-written MCP client works against both an SDK server and pi's tools, and you can draw its message sequence from memory.
- [ ] With the sandbox and policy on, none of the six red-team tasks achieves its forbidden action, and the trace explains which layer stopped each one.
- [ ] The policy service runs as its own process: killing or modifying the agent cannot widen a grant, and approvals per task appear in your eval report.
- [ ] You can explain to a security reviewer exactly what rig's sandbox does not protect against.

---

# Week 10: a mini-Perplexity

*Phase: The assistant · Primary reading/code: SearXNG, Trafilatura, cookbook search server*

An answer engine is Week 4's retrieval pointed at the web, plus one contract: every claim points at a stored passage. This week you build the pipeline (query planning, search, fetch, extraction, passage ranking, cited synthesis and verification) under a latency budget, and grade it with the judge you validated in Week 5.

## Concepts
- **The pipeline.** Plan queries → search → fetch → extract the main content → split into passages → rank passages against the question → synthesize with citations → verify each claim.
- **The query is not the message.** A follow-up such as "and the second one?" or a message full of typos is a poor search query. Before searching, a small model rewrites the recent turns into one to three standalone queries, fixing spelling and resolving references, or decides that no search is needed. Open WebUI does exactly this with one prompt over the last six messages, and falls back to the raw message when the rewrite fails.
- **Perplexity's production shape.** Its Search API post (September 2025) describes an index tracking over 200 billion URLs, ML-scheduled crawling where freshness and completeness compete for the same budget, documents split into self-contained sub-document spans, hybrid lexical and semantic retrieval, fast scorers early and cross-encoder rerankers late, and a self-reported median latency of 358 ms. That is Week 4 at web scale.
- **Citation provenance.** Claim → evidence id → source → exact character offsets in the stored text. Citations are created when evidence is collected, never reconstructed afterwards by asking the model what it used.
- **Support, not presence.** A citation can exist and still not support its claim. Check each claim against its passages and count the unsupported ones.
- **Freshness.** Record when every page was fetched, prefer recent sources for time-sensitive questions, and show dates in the answer.
- **Latency budget.** Time to first token matters more than total time. Fetch in parallel with per-request timeouts, cache aggressively, and start streaming once the first well-supported passages are in.
- **Web hygiene.** robots.txt, per-host rate limits, an honest User-Agent, timeouts, size caps and content-type checks. Fetched content is never executed.
- **Untrusted by construction.** Research mode has no shell, no file writes and no private-data tools, and fetched text is tagged untrusted (Week 9).

## Day by day
The arc this week is one pipeline, built stage by stage, then stress-tested against conversations and dollars rather than single clean questions.

| Day | Time | Do | Working by end of day |
|---|---|---|---|
| Mon | 1–1.5 h | Read Perplexity's Search API architecture post | A half-page note mapping its stages onto your Week 4 components |
| Tue | 2–3 h | Build steps 1-2: search backends, then fetch | A query returns cached, rate-limited, robots-respecting page fetches on disk |
| Wed | 2–3 h | Build steps 3-4: extraction, then passage ranking | Fetched pages become ranked, offset-accurate passages, same shape as Week 4's |
| Thu | 2–2.5 h | Build step 5: synthesize and verify; read and trace SearXNG and Trafilatura | An answer with every claim carrying evidence ids, and a verifier that can find one false claim |
| Fri | 1.5–2 h | Run the pipeline experiments | `notes/week10-experiments.md`: where decomposition, reranking, rounds, streaming and verification changed the outcome |
| Sat | 3–4 h | Build steps 6-7: the eval set, then the response cache | R01-R30 scored end to end; a cache with a measured false-hit rate, not an assumed one |
| Sun | 2–3 h | Build step 8: conversation-aware query planning; read Open WebUI's rewrite path | F01-F10 and a misspelled R01-R10 pass through the same pipeline as clean questions |

### Monday — Perplexity's architecture, mapped onto what you already built.
This week's pipeline already exists in miniature as Week 4's retrieval; today's job is to see it at web scale before writing new code. Read Perplexity's own account of their production stack and map every stage onto the Week 4 components you're about to extend.

1. Read **Concepts**' pipeline bullet and the production-shape bullet.
2. Read Perplexity's Search API architecture post in **Read** and write a half-page note mapping its stages onto your own retrieval code.
3. Note where your plan deliberately drops scale (a 200-billion-URL index, late cross-encoder rerankers) while keeping the same pipeline shape.

### Tuesday — search and fetch.
Today brings untrusted web text into rig for the first time this plan: a search backend, then the fetcher that turns its results into cached pages on disk. No extraction or ranking yet — just pages, fetched politely and cached.

1. Implement **Build** step 1: the `Search` protocol over a self-hosted SearXNG instance and one commercial search API.
2. Implement **Build** step 2: `fetch.py` — async, per-host concurrency limits, robots.txt, timeouts, a byte cap, an on-disk cache keyed by canonical URL with ETag revalidation.
3. Confirm fetched content is stored but never executed, per **Concepts**' web-hygiene bullet.

### Wednesday — extraction and ranking.
Raw HTML is not a passage. Today turns fetched pages into the same ranked, cited unit Week 4 built for your own corpus, so tomorrow's synthesis can treat web passages exactly like local ones.

1. Implement **Build** step 3: Trafilatura-based extraction into 150-300 word passages that keep their heading and character offsets.
2. Implement **Build** step 4: passage ranking — Week 4's BM25, embeddings and reciprocal rank fusion, then a reranker over the top 30.
3. Spot-check offsets by hand on two or three pages — a citation pointing at the wrong characters is worse than no citation.

### Thursday — synthesis, verification, and how the two reference tools actually work.
Today closes the loop end to end: a synthesized answer where every claim is checked against its own evidence rather than trusted from the writer. Then you read the two reference implementations whose ideas you just built smaller versions of — SearXNG's fan-out-with-a-deadline metasearch, and Trafilatura's cascading extraction.

1. Implement **Build** step 5: `synthesize.py` (every factual sentence ends with evidence ids) and `verify.py` (a separate pass checks each claim against its cited passages).
2. Read the SearXNG and Trafilatura entries in **Read**, and trace both paths given there.
3. Rerun one answer through `verify.py` and find a case where a citation exists but doesn't actually support its claim.

### Friday — break the pipeline on purpose.
No new pipeline code today. Run controlled variants against questions you already have, to see which of this week's design choices actually earned their complexity.

Run **Experiments** 1, 3, 4, 5 and 6: single query against decomposed queries; with and without the reranker; one round against gap-driven iterative research; streaming early against waiting for all fetches; the verifier on against off. Record where in the trace behavior diverged, not just the aggregate numbers.

### Saturday — the eval set and the cache.
Today builds the harness that scores this week's pipeline the way Week 5 taught you to, and the cache layer that makes running it repeatedly affordable.

1. Implement **Build** step 6: R01-R30, scored by your Week 5 judge plus citation precision/recall, source quality, freshness, rounds, pages fetched, time to first token, total latency and dollars.
2. Implement **Build** step 7: the response cache — exact match on normalized question plus date bucket, then a semantic cache with a similarity threshold, both with a freshness TTL.
3. Run **Experiments** 2 and 7: top-5 against top-20 fetched pages, and a similarity-threshold sweep measuring false hits on paraphrases and near misses.

### Sunday — queries that depend on what came before.
A real conversation's follow-up messages are poor search queries. Today's build makes query planning conversation-aware; you read how a production system does the same rewrite, then check the whole pipeline against conversational and misspelled inputs before the checkpoint.

1. Implement **Build** step 8: `plan_queries` rewrites recent turns into standalone queries with structured output, falling back to the raw message on failure; add F01-F10 and a misspelled copy of R01-R10.
2. Read the Open WebUI query-rewriting entry in **Read**.
3. Run **Experiment** 8: raw message against rewritten queries on F01-F10 and the misspelled set — correctness, citation precision, added time to first token.
4. Answer **You should be able to answer** and attempt **Checkpoint**.

## Build
1. [ ] `rig/research/search.py`: a `Search` protocol with two backends, a self-hosted SearXNG instance (to learn how metasearch merges results) and one commercial search API (for production-like quality and clear terms of use).
2. [ ] `fetch.py`: asynchronous fetching with per-host concurrency limits, robots.txt, timeouts, a byte cap, and an on-disk cache keyed by canonical URL with ETag revalidation.
3. [ ] `extract.py`: Trafilatura for main content, then passages of about 150 to 300 words that keep their heading and their character offsets into the stored text.
4. [ ] Passage ranking: reuse Week 4's BM25, embeddings and reciprocal rank fusion over passages, then a reranker over the top 30.
5. [ ] `synthesize.py` and `verify.py`: every sentence that states a fact ends with evidence ids; a separate verifier checks each claim against its passages and flags or drops unsupported ones.
6. [ ] Eval set R01–R30: 10 evergreen questions, 10 whose answers depend on the last 30 days, and 10 that need several sources reconciled. Metrics: correctness (your Week 5 judge), citation precision (citations that support their claim), citation recall (claims with a supporting citation), source quality, freshness, rounds, pages fetched, time to first token, total latency and dollars.
7. [ ] A response cache in front of the pipeline: an exact match on the normalized question plus a date bucket, then a semantic cache over question embeddings with a similarity threshold. Both get a freshness TTL, short for time-sensitive questions. Measure false hits on paraphrases and near misses (same words, different year) before trusting it.
8. [ ] Conversation-aware `plan_queries`: rewrite the recent turns into standalone queries with structured output (Week 9), fall back to the raw message on failure, and log both. Add F01–F10, two-turn conversations whose second turn only makes sense with the first, and a misspelled copy of R01–R10.

A sketch of the core, with support checked by a separate step rather than trusted from the writer. `ResearchState` is the accumulator threaded through every round: it starts from just the question, `add` folds in each round's ranked passages, `unseen` filters a new batch of hits down to URLs it hasn't fetched yet, and `get` looks passages up by the evidence ids a claim cites:

```python
@dataclass(frozen=True)
class Passage:
    id: str               # "E12"
    url: str              # canonical
    fetched_at: datetime
    start: int            # character offsets into the stored extracted text
    end: int
    text: str

@dataclass
class Claim:
    text: str
    evidence: list[str]           # passage ids the writer cited
    supported: bool | None = None # set by the verifier, never by the writer

async def research(question: str, budget: Budget) -> Answer:
    state = ResearchState(question)
    for _ in range(budget.max_rounds):
        queries = await plan_queries(state)                    # what is still unknown?
        hits = await gather_all(search(q) for q in queries)    # parallel, per-call timeout
        pages = await gather_all(fetch(h.url) for h in state.unseen(hits))
        state.add(rank(question, passages_of(extract(p) for p in pages))[:40])
        if budget.exhausted() or not await has_gaps(state):
            break
    answer = await synthesize(question, state.passages)       # claims cite passage ids
    for claim in answer.claims:
        claim.supported = await entails(claim.text, state.get(claim.evidence))
    return answer
```

## Project increment
rig v0.10: `rig ask "…"` streams a cited answer; every citation opens the stored passage; research mode runs with no shell or write tools.

## Read
**Perplexity's [Search API architecture post](https://research.perplexity.ai/articles/architecting-and-evaluating-an-ai-first-search-api)** on Monday: map every stage it describes onto your Week 4 components.

**[searxng/searxng](https://github.com/searxng/searxng)** at `6671d89`. Metasearch is fan-out with a deadline, then merge and score. `searx/search/__init__.py`: `Search.search` (174), `search_standard` (160), `_get_requests` (78) and `search_multiple_requests` (136, one thread per engine against a shared deadline). `searx/search/processors/online.py`: `OnlineProcessor.search` (245) and `_send_http_request` (167). One engine end to end: `searx/engines/github.py` (65 lines; `request` 25, `response` 33). Then `searx/results.py`: `ResultContainer.extend` (82), `_merge_main_result` (167, deduplication by URL), `close` (183), `calculate_score` (17) and `get_ordered_results` (193). SearXNG queries other engines' public result pages, so treat it as a learning tool and respect those engines' terms.

**[adbar/trafilatura](https://github.com/adbar/trafilatura)** at `e2f85c9`. `trafilatura/core.py`: `extract` (482), `bare_extraction` (278), and `trafilatura_sequence` (169), whose docstring lays out a four-stage cascade in which each stage engages only if the previous one under-delivered: the main extractor, comparison with external extractors (`_extract_and_compare`, 151, and `compare_extraction` in `external.py`, 84), a baseline rescue on the uncleaned page, and a recall retry.

For a production semantic cache, skim LiteLLM's `litellm/caching/redis_semantic_cache.py` at `v1.102.0`: `get_cache` (441), and the constructor, which refuses to run without an explicit `similarity_threshold`.

For query rewriting, read Open WebUI at `v0.11.4` (Week 14's main read): `DEFAULT_QUERY_GENERATION_PROMPT_TEMPLATE` in `backend/open_webui/config.py` (2309), `generate_queries` in `routers/tasks.py` (404), which runs on a separate task model rather than the chat model, and its caller `chat_completion_files_handler` in `utils/middleware.py` (2049).

**[openai/openai-cookbook](https://github.com/openai/openai-cookbook)** `examples/deep_research_api/how_to_build_a_deep_research_mcp_server/main.py` (208 lines): a FastMCP server exposing `search` and `fetch` over a vector store, the minimal two-tool contract a deep-research agent expects from a private data source. Give rig's own document store the same shape.

**Trace these paths:**

- SearXNG: `Search.search` → `search_standard` → `_get_requests` (one request per engine) → `search_multiple_requests` (threads, deadline) → `OnlineProcessor.search` → the engine's `request` → HTTP → the engine's `response` → `ResultContainer.extend` → `_merge_main_result` → `close` (scoring) → `get_ordered_results`.
- rig: conversation → `plan_queries` (rewrite into standalone queries) → parallel search → fetch (cache, robots) → extract → passages → rank → synthesize with evidence ids → verify → stream.

## You should be able to answer
1. [ ] How does SearXNG merge the same URL returned by three engines, and how does that change its score?
2. [ ] What happens to an engine that misses SearXNG's deadline, and what would you do differently under a latency budget?
3. [ ] How does Trafilatura decide its own extraction under-delivered, and what does it try next?
4. [ ] Why must citations be created when evidence is collected rather than requested after synthesis?
5. [ ] Why are sub-document passages a better retrieval unit for answers than whole pages?
6. [ ] What are the components of your time to first token, and which of them can overlap?
7. [ ] Name three ways a fetched page can attack your agent, and the layer that stops each.
8. [ ] What goes wrong when the raw message is the search query, and what does a rewrite cost in time to first token?

## Experiments
1. [ ] One query against decomposed queries.
2. [ ] Top 5 against top 20 search results: pages fetched against answer quality.
3. [ ] With and without the reranker.
4. [ ] One round against gap-driven iterative research.
5. [ ] Streaming early against waiting for all fetches: time to first token and correctness.
6. [ ] Verifier on and off: rate of unsupported claims that reach the user.
7. [ ] Semantic-cache threshold sweep: hit rate against wrong-answer rate on paraphrased and near-miss questions.
8. [ ] Raw message against rewritten queries on F01–F10 and the misspelled R01–R10: correctness, citation precision and added time to first token.

## Production lens
- **Latency is the product.** Set a time-to-first-token budget, track p50 and p95, and know which stage each millisecond belongs to.
- **Cost per answer** = search calls + fetches + tokens; report it next to quality.
- **Cache at three layers:** search results (short TTL), fetched pages (ETag), and passages and embeddings (content hash).
- **Publisher relationships:** robots.txt, terms of use, attribution, and never republishing whole pages.

## Not yet
Crawling and indexing at web scale, learning-to-rank training, query autocomplete and ads. Read about them; Perplexity's post is enough for this plan.

## Checkpoint
- [ ] rig answers a current multi-source question with every factual sentence linked to a stored passage that your judge confirms supports it.
- [ ] On R01–R30 you report correctness, citation precision and recall, time to first token p50 and p95, and dollars per answer, with intervals.
- [ ] You can explain Perplexity's retrieval stack, stage by stage, in terms of your Week 4 code.

---

# Week 11: deep research and multi-agent systems

*Phase: The assistant · Primary reading/code: Swarm, Agents SDK, search_evals*

A subagent is `run_agent()` called as a tool: a fresh transcript, a narrower tool set, a budget drawn from its parent's, and a short result returned to the caller. A handoff is a tool call that swaps the active system prompt and tools. Deep research is where this pays off first: questions that need dozens of searches benefit from parallel researchers with clean contexts. This week you build both and let your evals and Perplexity's search_evals decide.

## Concepts
- **Agent-as-tool versus handoff.** With agent-as-tool the caller keeps control and receives a result. With a handoff the callee takes over the conversation, usually with filtered history.
- **The main benefit is context isolation.** An exploration subagent can read 40 files or pages and return 300 words; the parent's context stays clean. The second benefit is parallelism. The cost is tokens (often several times a single agent) and information lost at the boundary.
- **Deep research** is Week 10's loop run wider and longer: a planner decomposes the question, researchers run the pipeline in parallel under their own budgets, a writer synthesizes, and a reviewer with fresh context checks citations.
- **Evidence travels, not prose.** Researchers return evidence ids and short findings; the writer synthesizes from the passages themselves. That defeats the telephone game.
- **Planner/executor** is one model call that emits a plan, then a loop over its steps, plus a rule for replanning when a step fails. A plan kept as a file the single agent edits is often enough.
- **Orchestrator-workers** fan out independent subtasks. Writers need isolation (one git worktree each) and a merge step that detects conflicts.
- **Where it helps:** broad exploration, truly independent subtasks, verification with fresh eyes. **Where it hurts:** tightly coupled edits, long sequential reasoning, tight budgets.
- **Failure modes:** detail lost in summaries, duplicated work, conflicting writes, unbounded recursion, cost blow-up, and confident errors propagated upward.

## Day by day
The week moves from the smallest possible handoff (Swarm, 292 lines) to rig's own deep-research mode, with the production SDK's version of the same idea read in between.

| Day | Time | Do | Working by end of day |
|---|---|---|---|
| Mon | 1–1.5 h | Read `openai/swarm`'s `core.py` and `types.py` | A half-page note on what a handoff actually changes in the next request |
| Tue | 2–3 h | Build steps 1-2: `explore` and `run_tests` subagents | Both return a bounded summary, not a transcript, with child spans in the trace |
| Wed | 2–3 h | Build steps 3-4: hierarchical budgets, then planner/executor | A child cannot overspend its parent; a failed check triggers a replan, not a crash |
| Thu | 2–2.5 h | Build step 5: fan-out on T17; read and trace the Agents SDK handoff/as-tool path | Three fixer subagents in separate worktrees, merged with `git apply --3way` |
| Fri | 1.5–2 h | Build step 6: the handoff toy; run experiments 3-4 | `transfer_to_reviewer` swaps system prompt and tools; a worker merge conflict is caught, not silently resolved |
| Sat | 3–4 h | Build step 7: `rig ask --deep` | Planner, three parallel researchers, a writer, and a fresh-context citation reviewer, run end to end |
| Sun | 3–4 h | Build step 8: the search_evals harness; run remaining experiments; checkpoint | rig runs a search_evals subset end to end; one trace query shows cost for the whole tree |

### Monday — the smallest possible handoff.
Before building any of rig's multi-agent machinery, read the thing it's all a production-grade version of. Swarm is archived and tiny on purpose — one file, one mechanism — so today's reading gives you the concept with nothing else competing for attention.

1. Read `swarm/core.py` and `swarm/types.py` in **Read**: `run`, `handle_tool_calls`, `handle_function_result`.
2. Trace the Swarm path given there: a tool returning an `Agent` is the entire handoff.
3. Write a half-page note: agent-as-tool versus handoff, per **Concepts**' first bullet, in your own words before you build either.

### Tuesday — two subagents, read-only and narrow.
Today's two subagents are deliberately the simplest possible case for context isolation: one reads broadly and reports back in 400 words, the other filters a wall of test output down to what actually failed. Both exist so the parent's context never has to hold what they held.

1. Implement **Build** step 1: `explore(question)` — read-only tools, fresh transcript, a step cap, a dollar limit, at most 400 words with citations, a child trace span.
2. Implement **Build** step 2: `run_tests(selector)`, deciding (and writing down why) whether it needs to be a subagent or a plain function.
3. Run it on a real question about rig's own code and check the parent never has to re-read what `explore` already read.

### Wednesday — budgets that nest, and a plan that survives failure.
Today's two pieces are what keep multi-agent mode from either overspending or stalling: a budget a child can't exceed, and a planner/executor loop that replans instead of giving up when a step's check fails.

1. Implement **Build** step 3 using the `run_subagent` sketch there: children reserve from the parent's remaining budget, unused reserve returns, depth caps at 2.
2. Implement **Build** step 4: the planner emits a JSON plan (goal, files, check) per step; the executor runs the loop and replans on a failed check.
3. Force a step to fail on purpose and confirm the executor replans rather than looping or crashing.

### Thursday — fan-out for real, and the SDK behind handoffs.
Today's build is the first one where isolation matters for a concrete reason: three fixer subagents working the same task in parallel, each in its own worktree, with a merge step that has to detect when two of them touched the same file. You read the production version of handoffs and agent-as-tool right after, since you just built working examples of both ideas.

1. Implement **Build** step 5: one fixer subagent per symptom on T17, each in its own git worktree, merged with `git apply --3way` and the full suite rerun.
2. Read the `openai-agents-python` entries in **Read**: `Handoff`, `handoff`, `Agent.as_tool`, and selectively through `turn_resolution.py`.
3. Trace the Agents SDK path given there and compare it against what you just built by hand.

### Friday — a real handoff, and where fan-out breaks.
Today adds the one piece Tuesday through Thursday's subagents didn't need: a tool that actually hands the conversation to someone else, with filtered history. Then you spend the rest of the day finding where this week's isolation helps and where it silently loses information or picks a winner it shouldn't.

1. Implement **Build** step 6: `transfer_to_reviewer`, swapping rig's system prompt and tools with a filtered history; compare it against calling the reviewer as a plain tool.
2. Run **Experiment** 3: a fresh-context reviewer against self-review on T10 and T11, where the visible tests pass despite the bug.
3. Run **Experiment** 4: let two fan-out workers touch the same file and confirm the merge step flags the conflict instead of picking one silently.

### Saturday — deep research, end to end.
This is the week's payoff: Week 10's single-pipeline research loop, run wider. A planner decomposes the question, three researchers run the pipeline in parallel under their own budgets, a writer synthesizes from evidence ids rather than prose, and a reviewer with fresh context checks citations before anything reaches the user.

1. Implement **Build** step 7: `rig ask --deep` — planner, three parallel researchers on Week 10's pipeline, a writer, a fresh-context citation reviewer.
2. Confirm evidence ids, not summaries, cross the researcher-to-writer boundary, per **Concepts**' "evidence travels" bullet.
3. Run it on two or three R01-R30 questions from Week 10 and compare against last week's single-pipeline answers.

### Sunday — score it against a real benchmark, then checkpoint.
Your own eval set tells you if deep mode helps on your own questions; search_evals tells you where it stands against questions designed to need broad research. Today wires up the harness, runs the comparison, and closes with the checkpoint.

1. Implement **Build** step 8: subclass `BaseHarness` so `run()` calls `rig ask --deep`; run 50-task subsets of BrowseComp and DeepSearchQA with `--limit`.
2. Read the `perplexityai/search_evals` entries in **Read** and trace the harness path given there.
3. Run **Experiments** 1, 2 and 5: single agent against `explore`, planner/executor and fan-out on T01-T23 plotted as pass rate against dollars; the `explore` report-limit sweep; the four-architecture comparison across R01-R30 and your search_evals subset.
4. Answer **You should be able to answer**, then attempt **Checkpoint**.

## Build
1. [ ] `explore(question)`: a subagent with read-only tools, a fresh transcript, a cap of 15 steps and a small dollar limit, returning at most 400 words with `path:line` or evidence-id citations. Its trace is a child span linked to the parent run.
2. [ ] `run_tests(selector)`: a subagent (or a plain function; decide which and say why) that returns only failing test ids and the first lines of each error.
3. [ ] Hierarchical budgets: children reserve from the parent's remaining budget, unused reserve returns, and depth is capped at 2 (sketch below).
4. [ ] A planner/executor variant: the planner emits a JSON plan of steps (goal, files, check); the executor runs the loop per step and replans after a failed check.
5. [ ] Fan-out on T17: one fixer subagent per symptom, each in its own git worktree; the parent merges with `git apply --3way` and runs the full suite.
6. [ ] A handoff toy: a `transfer_to_reviewer` tool that swaps rig's system prompt and tools and keeps a filtered history. Compare it with a reviewer called as a tool.
7. [ ] `rig ask --deep`: planner, three parallel researchers running Week 10's pipeline, a writer that synthesizes from evidence ids, and a fresh-context citation reviewer.
8. [ ] A search_evals harness for rig: subclass `BaseHarness` so `run()` calls `rig ask --deep`, then run 50-task subsets of BrowseComp and DeepSearchQA with `--limit`. Its graders call OpenAI models, so budget for that key, and treat Perplexity's published full-suite scores as context, not as a target your subset can match.

```python
# a sketch of hierarchical budgets; the parent's budget is the only one the user sees
def run_subagent(parent, task: str, tool_names: list[str], max_usd: float, max_steps: int = 15):
    if parent.depth >= 2:
        raise ToolError("Subagent depth limit reached; do this step yourself.")
    reserve = parent.budget.reserve(usd=min(max_usd, 0.5 * parent.budget.remaining_usd()), steps=max_steps)
    try:
        result = run_agent(task, tools=parent.tools.subset(tool_names), budget=reserve,
                           depth=parent.depth + 1, trace=parent.trace.child(task))
    finally:
        parent.budget.settle(reserve)    # unused reserve returns to the parent
    return result.final[:2000]           # findings and evidence ids, never the child's transcript
```

## Project increment
rig v0.11: `explore`, test summarization, hierarchical budgets, planner and fan-out modes behind flags, and `rig ask --deep`. Every mode runs on the same eval sets and on search_evals subsets, so they can be compared on quality and dollars per correct answer.

## Read
**[openai/swarm](https://github.com/openai/swarm)**, `swarm/core.py` (292 lines) and `swarm/types.py` (41). Read `run` (231), `handle_tool_calls` (89) and `handle_function_result` (71): if a tool returns an `Agent`, the active agent changes, and that is the whole handoff mechanism. Swarm is archived as an educational project and superseded by the Agents SDK; read it as the specification of the idea.

**[openai/openai-agents-python](https://github.com/openai/openai-agents-python) at `v0.23.1`**, which is what Swarm's idea becomes in production. It is also your Week 4 corpus, so use rig's `retrieve` on it. Read `src/agents/handoffs/__init__.py` (`HandoffInputData` at 71, `Handoff` at 126, `handoff` at 229), `handoffs/history.py`, and `Agent.as_tool` in `src/agents/agent.py` (606). Then, in `src/agents/run_internal/turn_resolution.py` (3,738 lines, so read selectively): `process_model_response` (2799), `execute_tools_and_side_effects` (795), `execute_handoffs` (529) and `get_single_step_result_from_response` (3657). Note `resolve_interrupted_turn` (1145) for Week 15.

**[perplexityai/search_evals](https://github.com/perplexityai/search_evals)** at `cab4c5d`: Perplexity's open-source runner for deep-research benchmarks (BrowseComp, DeepSearchQA, HLE's retrieval subset, WideSearch), with resumable runs, cost accounting and per-task traces. Read `search_evals/harnesses/base.py` (67 lines: `BaseHarness` at 36, `run` at 67), `runner.py` (`EvalRunner.run` at 65, `_run_task` at 95) and `suites/graders.py` (`DeepResearchGrader.grade` at 93).

Optional essay: Anthropic's write-up of [how its multi-agent research system was built](https://www.anthropic.com/engineering/built-multi-agent-research-system), which is candid about token cost and coordination failures.

**Trace these paths:**

- Swarm: `run` → `get_chat_completion` (the active agent's instructions and functions) → `handle_tool_calls` → `handle_function_result` (an `Agent` result sets the new active agent) → the loop continues with the new agent and the same history.
- Agents SDK: a turn's model response → `process_model_response` (classifies output items into tool calls, handoffs and final output) → `execute_tools_and_side_effects` → `execute_handoffs` (applies the input filter to history and switches agent) → `get_single_step_result_from_response` decides between final output, handoff and run again.
- search_evals: CLI → `EvalRunner.run` → `_run_task` per task (attempt directories, retries) → your harness's `run` → the suite's grader → summary with cost.

## You should be able to answer
1. [ ] In Swarm, what exactly changes in the next request after a handoff, and what stays the same?
2. [ ] What does a handoff input filter receive and return, and why do production systems need one?
3. [ ] How does `Agent.as_tool` differ from a handoff in who owns the conversation afterwards?
4. [ ] Where does the Agents SDK enforce its maximum number of turns, and what happens when it trips?
5. [ ] Why should researchers return evidence ids rather than prose summaries?
6. [ ] In your fan-out run on T17, where were tokens spent: the subagents' exploration or the parent's coordination?
7. [ ] Which information did your `explore` subagent lose that the parent later needed? How did you detect it?
8. [ ] On your search_evals subset, where did deep mode gain, and what did each extra point cost?

## Experiments
1. [ ] Single agent against single agent with `explore`, planner/executor and fan-out on T01 to T23. Plot pass rate against dollars per solved task.
2. [ ] Vary the `explore` report limit (100, 400, 1,500 words) and measure how often the parent re-reads what the subagent already reported.
3. [ ] A reviewer as a fresh-context subagent against self-review in the same context, on T10 and T11 (where the visible tests pass with the bug).
4. [ ] Let two fan-out workers touch the same file and confirm the merge step detects the conflict rather than silently picking one.
5. [ ] Four research architectures on R01–R30 and a 50-task search_evals subset, measuring answer quality, evidence recall, citation precision, latency, tokens, cost per correct answer, and parent re-reads caused by information lost at the boundary:

| Mode | Hypothesis |
|---|---|
| Single agent | Strong baseline; lowest coordination cost |
| Manager and one researcher | Context isolation with little overhead |
| Three parallel researchers | Broader evidence and lower wall time when the question decomposes |
| Researchers and an independent reviewer | Fresh-context verification catches synthesis and citation errors |

## Production lens
- **Budgets are hierarchical.** A child cannot spend more than the parent has left, and the root's budget is the only one the user sees.
- **Cancellation propagates** down the tree; orphaned children are a cost leak.
- **Idempotency across agents:** two workers must not both run the same side effect. Give mutating work an owner.
- **Tracing:** parent and child spans share a trace id, so one query shows the whole tree and its cost.
- **Rate limits** become the real limit on fan-out; queue rather than spawn.

## Not yet
Agent-to-agent network protocols, large "crew" or role-play frameworks, debate setups, and self-improving agent societies. They are compositions of the loop; judge each by your eval numbers, not its diagram.

## Checkpoint
- [ ] You can implement a handoff and an agent-as-tool in rig in under an hour each, and explain the trade-off with your own numbers.
- [ ] You have one multi-agent mode that beats the single agent on some task category at an acceptable cost, or a documented result showing none did.
- [ ] rig runs on a search_evals subset end to end, and one trace query shows the full agent tree for any run with per-node cost.

---

# Week 12: a Claude-style workbench

*Phase: The assistant · Primary reading/code: OpenHands Software Agent SDK, docling-core*

A workbench agent is Week 1's loop with a bigger environment: a per-user workspace where it reads files, runs code and produces artifacts someone else can audit. Meta's Muse gives each user a private virtual machine; this week you build the small version, plus the lineage that makes its outputs trustworthy.

## Concepts
- **The workspace boundary.** The agent talks to its workspace through a narrow interface (run a command, read, write, upload, download, diff). Local process, container or remote VM: the agent should not be able to tell.
- **Per-user isolation and its economics.** One VM or container per user means cold starts, idle pause and resume, snapshots and quotas. Containers share a kernel; VMs don't.
- **Code is the analysis tool.** The model writes Python, runs it and reads the result. Numbers in a report come from executed code, not from the model's head.
- **Artifact lineage.** Every artifact records its inputs (by hash), the exact code that produced it, and the run and step. An artifact without lineage is a claim without a citation.
- **Silent numeric errors** (a wrong join, mismatched units, an off-by-one quarter) are the dominant failure. Independent recomputation and assertions inside generated code catch them.
- **Ingestion is most of RAG.** PDFs, slides and spreadsheets arrive as layout, not text: reading order, tables, headers, scanned pages. Parse them into a structured document first, chunk along the structure (sections, tables kept whole) to a token budget, and prefix each chunk with its context: the heading path, or a short model-written note on where it sits in the document. Anthropic's [contextual retrieval](https://www.anthropic.com/engineering/contextual-retrieval) write-up reports that a 50-to-100-token context per chunk cut top-20 retrieval failures by 35% with embeddings alone, by 49% with contextual BM25 added, and by 67% with reranking, at about $1 per million document tokens with the document cached as the prompt prefix.
- **Confirmation by risk.** In OpenHands a pluggable security analyzer rates each pending action (one option reads a risk label the model attaches to its own tool call; others match patterns), and a confirmation policy decides which ratings need the user. The analyzers live in the SDK's security package. Compare that with Week 9's grants: who is trusted to decide the risk?

## Day by day
The week's real test is a single planted question — why did revenue fall? — answered with executed code and an audit trail, not a confident guess.

| Day | Time | Do | Working by end of day |
|---|---|---|---|
| Mon | 1–1.5 h | Read **Concepts**; run three OpenHands examples | A note on the workspace boundary, artifact lineage, and what confirmation-by-risk trusts |
| Tue | 2–4 h | Build steps 1-2: the workspace protocol, local and remote; the `python` tool | The same agent code runs code in a local container and in one behind an HTTP API |
| Wed | 2–4 h | Build steps 3-4: the artifact store with lineage; the fixture folder and task | `sales.csv`, `marketing.csv`, `earnings.pdf` built with a planted cause; the task runs end to end once |
| Thu | 2–2.5 h | Build step 5: eval assertions W01-W10; read and trace the OpenHands agent/workspace path | Computed values, sources, artifacts and the planted cause all check automatically |
| Fri | 1.5–2 h | Run experiments 1-3 | Numbers on what the `python` tool and recomputation actually catch |
| Sat | 3–4 h | Build steps 6-7: `rig audit`; ingestion with Docling; read docling-core's chunkers | An artifact's lineage replays in a fresh workspace; uploaded PDFs are chunked and searchable |
| Sun | 2–3 h | Run remaining experiments; checkpoint | The revenue task solved with a traceable report; checkpoint passed or a redo list |

### Monday — the workspace boundary and lineage, before you build either.
This week's agent is still Week 1's loop; what's new is the environment around it and the paper trail its outputs leave. Today you see both ideas working in someone else's finished system before building your own versions.

1. Read **Concepts** in full, especially the workspace-boundary, artifact-lineage and silent-numeric-errors bullets.
2. Run `examples/01_standalone_sdk/01_hello_world.py`, `04_confirmation_mode_example.py` and `09_pause_example.py` from **Read**'s OpenHands SDK, to see the workspace boundary, confirmation-by-risk and pause working before you design your own.
3. Write a half-page note: what crosses your `Workspace` protocol's boundary, and what an artifact needs besides a file path to be trustworthy.

### Tuesday — one interface, two workspaces.
Today's build makes "local container" and "remote machine" the same thing from the agent's point of view: one `Workspace` protocol, two implementations, no change to the agent code that calls it. The `python` tool is what turns that workspace into an actual analysis engine rather than a sandbox that just runs `bash`.

1. Implement **Build** step 1: the `Workspace` protocol (`execute`, `read`, `write`, `upload`, `download`, `diff`, `pause`, `resume`) over Week 1's local container, then the same container behind a small HTTP API on another machine.
2. Implement **Build** step 2: a `python` tool that runs code in the workspace with a timeout and returns stdout, stderr and any new files.
3. Run the same script against both implementations and confirm the agent-facing code didn't change.

### Wednesday — lineage, and the question you'll spend the week answering.
Numbers in a report are only trustworthy if you can trace each one back to the code and inputs that produced it. Today you build that record, then construct the actual puzzle — three files engineered so revenue fell for a specific, plantable reason — that the rest of the week's eval, audit and ingestion work will all point at.

1. Implement **Build** step 3: the artifact store with lineage, per the `Artifact` dataclass given there — sha256, run id, step, the exact code, and input hashes.
2. Implement **Build** step 4: the fixture folder (`sales.csv`, `marketing.csv`, `earnings.pdf`) with a planted cause, and run the revenue-decline task against it once by hand.
3. Confirm every artifact the run produces records its lineage, not just its content.

### Thursday — grading the task, and how OpenHands does the same thing.
Today turns "it looks right" into assertions you can rerun, and you read the codebase that separates agent, tools and workspace more cleanly than most — including the exact mechanism that decided your own confirmation-by-risk question on Monday.

1. Implement **Build** step 5: eval assertions W01-W10 — computed values within tolerance, expected columns and sources used, artifacts exist and open, the chart exists, the report names the planted cause, the generated code re-executes to the same numbers.
2. Read the OpenHands SDK entries in **Read**: `Agent.step`/`_step`, `_requires_user_confirmation`, `BaseWorkspace`, `LocalConversation`, the context-view invariants, and the long-lived terminal.
3. Trace the path given there and compare `_requires_user_confirmation` against your own notes from Monday.

### Friday — find out what the python tool and recomputation are actually worth.
No new build today. You already have a task with a known right answer; now you take pieces away and measure what breaks.

Run **Experiments** 1-3: the revenue task with and without the `python` tool; three planted silent errors (wrong join, mismatched units, off-by-one quarter) with and without independent recomputation; a long-lived terminal against one-shot `bash` on a multi-step data task. Write down which errors recomputation actually caught, not just whether the final report looked right.

### Saturday — auditing a run, and turning documents into something searchable.
Today closes the lineage story — anyone can replay an artifact's exact history in a clean workspace — and opens a new one: PDFs and spreadsheets arrive as layout, not text, and today's ingestion pipeline is what turns them into chunks worth retrieving.

1. Implement **Build** step 6: `rig audit <artifact>` — rerun its lineage in a fresh workspace and diff the result.
2. Implement **Build** step 7: `rig/ingest/` — Docling parsing into a structured document, its hybrid chunker (tables whole), context added per chunk (heading path, then a model-written note), indexed into Week 4's Postgres tables, re-ingested only when hash or version changes.
3. Read the docling-core entries in **Read**: `HybridChunker`, `TripletTableSerializer`, and `contextualize`.

### Sunday — remote latency, chunking quality, then checkpoint.
The last two experiments check costs and trade-offs you've been assuming all week: how much the remote workspace costs in latency, and how much structure-aware chunking with context actually buys you over naive text splitting.

1. Run **Experiment** 4: tool-call latency for the remote workspace against the local one.
2. Run **Experiment** 5: questions about `earnings.pdf` from fixed-size chunks, structure-aware chunks, and structure-aware chunks with model-written context — recall@10, answer correctness, one-time ingestion cost.
3. Answer **You should be able to answer**, then attempt **Checkpoint**: the revenue task solved, lineage traceable with `rig audit`, the same agent code running against both workspaces.

## Build
1. [ ] `rig/workspace/`: a `Workspace` protocol (`execute`, `read`, `write`, `upload`, `download`, `diff`, `pause`, `resume`) with two implementations: Week 1's local container, and the same container behind a small HTTP API on another machine.
2. [ ] A `python` tool that runs code in the workspace with a timeout and returns stdout, stderr and any new files.
3. [ ] `rig/artifacts/`: an artifact store with lineage (below).
4. [ ] The practical project: a fixture folder with `sales.csv`, `marketing.csv` and `earnings.pdf`, built so revenue fell last quarter for a cause you plant (say, a price change in one region). The task: "Determine why revenue declined last quarter. Validate the hypothesis quantitatively. Produce a chart and a written report."
5. [ ] Eval assertions W01–W10: computed values within tolerance, the expected columns and sources used, artifacts exist and open, a chart was produced, the report names the planted cause, and the generated code re-executes to the same numbers.
6. [ ] `rig audit <artifact>`: re-runs an artifact's lineage in a fresh workspace and diffs the result.
7. [ ] `rig/ingest/`: parse uploaded PDF and DOCX files with Docling into a structured document, chunk them with its hybrid chunker (tables whole), add context (the heading path, then a model-written note with the whole document as a cached prefix), and index the chunks into Week 4's Postgres tables. Re-ingest a file only when its hash, the parser version or the chunker version changes.

```python
@dataclass(frozen=True)
class Artifact:
    id: str
    path: str                  # inside the workspace
    sha256: str
    mime_type: str
    run_id: str
    step: int                  # trace step that produced it
    code_sha256: str           # the exact code cell that wrote it
    inputs: dict[str, str]     # input path -> sha256 when it was read
    created_at: datetime
```

## Project increment
rig v0.12: a `work` mode with a workspace, a `python` tool and artifacts with lineage, plus `rig audit`. Uploaded documents are parsed, chunked and searchable.

## Read: OpenHands Software Agent SDK
[OpenHands/software-agent-sdk](https://github.com/OpenHands/software-agent-sdk) at `69e2688` separates agent logic, tool execution, context and the workspace boundary more cleanly than most agent codebases.

1. Run a few of `examples/01_standalone_sdk/` first: `01_hello_world.py`, `04_confirmation_mode_example.py`, `09_pause_example.py`, `10_persistence.py`, `14_context_condenser.py` and `32_configurable_security_policy.py`.
2. `openhands-sdk/openhands/sdk/agent/agent.py` (1,622 lines): `Agent.init_state` (497), `step` (693) and `_step` (706), `_requires_user_confirmation` (1130) and `_extract_security_risk` (1173).
3. `openhands-sdk/openhands/sdk/workspace/base.py` (282 lines): `BaseWorkspace.execute_command` (172), `file_upload` (195), `file_download` (215), `git_changes` (235), `git_diff` (249), `pause` (262) and `resume` (273). Then one implementation under `openhands-workspace/openhands/workspace/docker/`.
4. `openhands-sdk/openhands/sdk/conversation/impl/local_conversation.py`: `LocalConversation.send_message` (1807), `run` (1902), `_run` (1917) and `pause` (2719).
5. `openhands-sdk/openhands/sdk/context/view/properties/`: `tool_call_matching.py` (95 lines), `batch_atomicity.py` (88) and `tool_loop_atomicity.py` (126). These are the invariants a condensed context must keep, Week 3's safe cut points written as code. Then `context/condenser/llm_summarizing_condenser.py`: `get_condensation_reasons` (136) and `_get_forgotten_events` (278).
6. `openhands-tools/openhands/tools/terminal/`: `impl.py` and `terminal/tmux_terminal.py`, a long-lived shell, against rig's one-shot `bash`.

**Also read [docling-project/docling-core](https://github.com/docling-project/docling-core)** at `v2.101.1`, the document model and chunkers behind [Docling](https://github.com/docling-project/docling). In `docling_core/transforms/chunker/`: `hybrid_chunker.py` (413 lines): `HybridChunker` (55), `_split_by_doc_items` (161), `_merge_chunks_with_matching_metadata` (344) and `chunk` (390); `hierarchical_chunker.py`: `TripletTableSerializer` (46), which turns a table into text a retriever can match; `base.py`: `contextualize` (82), the heading-path version of contextual retrieval.

**Trace this path:** `LocalConversation.send_message` → `run` → `_run` loop → `Agent.step` → `_step` (condensed view, model call, actions) → `_requires_user_confirmation` → the tool executes in the workspace (`execute_command`) → observation events → persisted conversation state → next step or pause.

## You should be able to answer
1. [ ] What exactly crosses OpenHands' workspace boundary, and what changes when the workspace moves to another machine?
2. [ ] Where does OpenHands decide an action needs confirmation, and where does the risk label come from? What does that design trust?
3. [ ] Which invariants do the view properties enforce, and which Week 3 bug does each one prevent?
4. [ ] What does `pause` do to a running conversation and to its workspace?
5. [ ] Why must every number in a report come from executed code, and how do you check that it did?
6. [ ] What does it cost to keep a per-user VM warm, and when would you pause or snapshot it instead?
7. [ ] Why chunk along a document's structure instead of fixed windows, and what does a chunk lose when its heading is cut away?

## Experiments
1. [ ] The revenue task with and without the `python` tool: correctness of the stated cause and of the numbers.
2. [ ] Plant three silent errors (a wrong join, mismatched units, an off-by-one quarter) and measure how often rig catches each, with and without an independent recomputation step.
3. [ ] A long-lived terminal against one-shot `bash` on a multi-step data task.
4. [ ] Tool-call latency for the remote workspace against the local one.
5. [ ] Questions about `earnings.pdf` answered from fixed-size text chunks, from structure-aware chunks, and from structure-aware chunks with model-written context: recall@10, answer correctness and the one-time ingestion cost.

## Production lens
- **Per-user isolation costs money.** Idle timeouts, snapshot and restore, and quotas on CPU, memory, disk and egress decide the unit economics.
- **Data lifecycle.** User files live in the workspace; deleting a user deletes the VM and every snapshot.
- **Confidential computing.** Meta has said it is building a version of Muse's workspace that Meta itself can't see into. Know what trusted execution environments hide, and what they don't.
- **Ingestion is a pipeline.** Queue it, version the parser and the chunker, and re-index when either changes.
- **Provenance is an audit requirement** wherever numbers drive decisions: finance, health, compliance.

## Not yet
Notebook interfaces, collaborative editing, GPU workspaces and enterprise data connectors.

## Checkpoint
- [ ] rig solves the revenue task, and another engineer can trace every number in the report back to input files, code and trace steps with `rig audit`.
- [ ] Your workspace runs locally and remotely behind the same interface, with no change to the agent.
- [ ] You can explain OpenHands' confirmation path and its context-view invariants with line references.

---

# Week 13: memory, personalization and connectors

*Phase: The assistant · Primary reading/code: Letta Code, Codex memory*

Memory is a policy problem (what to store, retrieve, supersede, expire and redact) far more than a storage problem. Connectors are OAuth, incremental sync and rate limits. Together they make an agent personal, and they bring the two biggest new risks: wrong memories, and untrusted text arriving through your own inbox.

## Concepts
- **Four kinds of memory.** Profile (stable facts and preferences), episodic (what happened), working (the current task's scratchpad) and procedural (how to do things: skills).
- **Write path and read path.** Extraction decides what is worth keeping; consolidation merges, deduplicates and supersedes; redaction removes secrets and sensitive categories; the read path decides what to inject, and logs it.
- **Provenance over confidence.** Store the source session and the quote a memory came from, and whether the user confirmed it. A confidence score generated by a model is a guess, not a calibration.
- **Memory as files.** Letta Code keeps an agent's memory as a git-backed directory: edits are commits, conflicts are merges, and history and rollback come for free.
- **Background consolidation.** Codex runs memory as a two-phase background pipeline, per-session extraction then consolidation, with job leases so concurrent workers don't duplicate work and secret redaction before anything is stored.
- **Connectors.** OAuth 2.0 authorization code with PKCE, least-privilege scopes, refresh-token rotation and encrypted token storage; incremental sync (Google Calendar's `syncToken`, Gmail's `historyId`) instead of re-reading everything; push notifications where available; rate limits with backoff.
- **Inbound email is untrusted input to a privileged agent.** Muse is getting its own email address; anything forwarded to it can carry instructions. So can a calendar invite's description.
- **Users must see and delete their memories.** Personalization that can't be inspected reads as surveillance.

## Day by day
| Day | Time | Do | Working by end of day |
|---|---|---|---|
| Mon | 1-1.5 h | Concepts: the four memory kinds, provenance over confidence, the write/read path split | A one-page note defining profile/episodic/working/procedural, and why a stored quote beats a confidence score |
| Tue | 2.5-3 h | Build steps 1-2: the memory store and the write path | `rig/memory/` supports write/search/supersede/forget; a finished session produces extracted, consolidated, redacted memories |
| Wed | 2.5-3 h | Build steps 3-4: the read path and the fixture connectors | Profile memories load at session start, episodic retrieval is traced; the three adversarial fixture emails don't corrupt memory |
| Thu | 1.5-2 h | Read Letta Code and Codex memory; trace both paths | Notes on both trace paths, and answers to the leases and conflict-repair questions below |
| Fri | 2-3 h | Build step 5: the real Google Calendar connector | OAuth with PKCE completes; incremental sync with `syncToken` works; every write goes through the policy service |
| Sat | 3-4 h | Build step 6: memory evals M01-M12; Experiments 1-2 | M01-M12 scored with precision, recall and injection-rate numbers; the contradiction experiment's numbers recorded |
| Sun | 2-3 h | Experiments 3-4; project increment; checkpoint | Adversarial-email and incremental-sync numbers recorded; checkpoint passed or a redo list |

Each day below points at Build, Read and Experiments for the exact contracts and traces rather than repeating them here.

### Monday — memory as a policy problem, not a database problem.
Today is reading only, no code. The week's central claim is that what you store, when you supersede it, and what you refuse to store ever matter more than which database holds it, so make that concrete before writing a line of the store. Sketch the four memory kinds in your own words and work out why a stored quote plus a confirmation flag beats a model-generated confidence score.

1. Read **Concepts** above twice: once for the four kinds, once for the write/read path split and the provenance rule.
2. Sketch the `Memory` record from **Build** below by hand, field by field, with one sentence per field on what it's for.
3. Write a half-page note: what makes a memory worth keeping, what makes it worth superseding, and what must never be stored regardless of what the user says.

### Tuesday — the store and the write path.
Today you build the two pieces that turn a raw conversation into durable facts: the store itself, and the pipeline that decides what from a session is worth keeping. By tonight a finished session produces a small set of extracted, deduplicated, redacted memories you can inspect by hand.

1. Implement **Build** step 1: `rig/memory/` with `write`, `search`, `supersede`, `forget` and a user-visible export, on the `Memory` record given there.
2. Implement **Build** step 2's three passes: extraction (propose memories with quotes), consolidation (merge duplicates, supersede contradicted facts), and redaction (strip secrets and blocked categories).
3. Run one real session through the pipeline and read every memory it produced by hand before trusting it on a second one.

### Wednesday — the read path and two fixture connectors.
Today the memories you wrote yesterday start getting used, and the agent gets its first look at calendar and email data, strictly from fixtures. Fixtures first means you can plant adversarial content on purpose and watch what happens before any real account is at risk.

1. Implement **Build** step 3: load profile memories at session start, retrieve episodic memories per turn with Week 4's retriever only when relevant, and trace every injected memory.
2. Implement **Build** step 4: `CalendarConnector` and `EmailConnector` backed by `fixtures/calendar.json` and `fixtures/inbox.json`, including the three adversarial emails.
3. Run a session against the adversarial fixtures and confirm none of them changes a stored memory or triggers an unapproved write.

### Thursday — read Letta Code and Codex memory.
No new code today. Both reference implementations solve the write-path problem you built on Tuesday with very different mechanisms — a git-backed filesystem versus a leased two-phase pipeline — and the contrast is the fastest way to see which parts of your own design were load-bearing and which were arbitrary.

1. Read **Read** below in order for both projects, then trace the two paths given there end to end.
2. Answer the **You should be able to answer** questions about leases, conflicts, and what git buys Letta that a key-value store would not.

### Friday — the real connector.
Today the agent gets a real account for the first time this plan, behind the policy service built in Week 9. This is deliberately the only real connector this week: OAuth, scopes, token rotation and incremental sync are enough new surface for one day without also debugging memory.

1. Implement **Build** step 5: Google Calendar with authorization-code-plus-PKCE OAuth, the narrowest scopes that work, refresh-token rotation and encrypted token storage.
2. Wire incremental sync with `syncToken`, and confirm a forced "token expired" response triggers a full resync rather than a crash.
3. Confirm every write from this connector routes through Week 9's policy service as a `calendar` grant, never called directly.

### Saturday — the memory eval set.
Today you get your first numbers: can the pipeline you built Tuesday-Wednesday actually remember, forget, and resist being fed a false fact.

1. Implement and run **Build** step 6: memory evals M01-M12.
2. Record memory precision and recall, the wrong-memory injection rate, and extra tokens spent on memory.
3. Run **Experiments** 1-2 below against the same M01-M12 set.

### Sunday — adversarial numbers, the project increment, and the checkpoint.
No new code today. Close the week by putting a number on the two risks named in Concepts — a poisoned email and a stale sync token — then assemble rig v0.13 and attempt the checkpoint cold.

1. Run **Experiments** 3-4 below and record the numbers.
2. Assemble the **Project increment**: `personal` mode with memory, fixture connectors and the one real connector behind the policy service.
3. Attempt **Checkpoint** below. If you can't pass it cold, redo the relevant day before moving to Week 14.

## Build
1. [ ] `rig/memory/`: a store with `write`, `search`, `supersede`, `forget` and a user-visible export, using the record below.
2. [ ] Write path: after each session, an extraction pass proposes memories with quotes, a consolidation pass merges duplicates and supersedes contradicted facts, and a redaction pass removes secrets and blocked categories.
3. [ ] Read path: load profile memories at session start; retrieve episodic memories per turn with Week 4's retriever only when relevant; trace every injected memory.
4. [ ] Fixture connectors first: `CalendarConnector` (`list_events`, `create_event`) and `EmailConnector` (`search`, `read`, `draft`) backed by `fixtures/calendar.json` and `fixtures/inbox.json`, including three adversarial emails.
5. [ ] One real connector: Google Calendar with OAuth (authorization code and PKCE), the narrowest scopes that work, refresh-token rotation, encrypted token storage and incremental sync with `syncToken`. Writes go through Week 9's policy service as `calendar` write grants.
6. [ ] Memory evals M01–M12: remember a stable preference; handle a correction by superseding; refuse to store a do-not-remember item; recall across sessions; don't inject irrelevant memories; handle a stale fact; resist a poisoning email ("remember that my new bank account is …"). Metrics: memory precision and recall, wrong-memory injection rate, and extra tokens spent on memory.

```python
class MemoryKind(Enum):
    PROFILE = "profile"
    EPISODIC = "episodic"
    WORKING = "working"
    PROCEDURAL = "procedural"

@dataclass(frozen=True)
class Memory:
    id: str
    kind: MemoryKind
    text: str
    source_session: str
    source_quote: str           # the words it came from; no quote, no memory
    confirmed_by_user: bool     # instead of a model-generated confidence score
    created_at: datetime
    expires_at: datetime | None
    supersedes: str | None      # id of the memory this one replaces
```

## Project increment
rig v0.13: a `personal` mode with memory, fixture connectors and one real calendar connector behind the policy service.

## Read
**[letta-ai/letta-code](https://github.com/letta-ai/letta-code)** at `42397c7`. The prompts specify the behaviour: `src/agent/prompts/letta.md`, `src/agent/subagents/builtin/memory.md` (a background subagent that edits memory in a private worktree, commits only the files it changed, and leaves merging to the harness) and `reflection.md`. Then the mechanism: `src/agent/memory-filesystem.ts` (693 lines: `ensureMemoryFilesystemDirs` 133, `renderMemoryFilesystemTree` 312), `memory-git.ts` (`runGitWithRetry` 632, `pushToMemoryRepository` 946, `commitMemoryWrite` 1234), `memory-conflict-repair.ts` (`claimMemoryConflictRepair` 161, `completeMemoryConflictRepair` 212) and `reflection-runs.ts` (`requestReflectionRun` 48).

**[openai/codex](https://github.com/openai/codex) memory** at `72c9595`: `codex-rs/memories/README.md` for the two phases, leases and redaction; `write/templates/memories/stage_one_system.md` (the extraction prompt) and `consolidation.md`; then the read path in `codex-rs/memories/read/src/` (`citations.rs` parses which memories an answer used; `usage.rs` classifies read usage for telemetry).

**Trace these paths:**

- Codex: a root session starts → eligibility checks (not ephemeral, not a subagent, memory enabled) → phase 1 claims eligible past sessions under leases → an extraction model call per session → redaction → stage-one outputs stored → phase 2 consolidates them into memory files → the next session's read path injects them.
- Letta Code: a reflection run is requested → the memory subagent edits files in a worktree → `commitMemoryWrite` → the harness merges and syncs → on conflict, `claimMemoryConflictRepair` and `completeMemoryConflictRepair`.

## You should be able to answer
1. [ ] Why is memory primarily a policy problem rather than a vector-database problem?
2. [ ] What does git give Letta's memory that a key-value store would not, and what does it cost?
3. [ ] Why does Codex need leases for memory extraction, and what happens without them?
4. [ ] What decides whether a memory is injected into a given turn, and how would you know it was the wrong one?
5. [ ] How does incremental sync with a sync token work, and what must you do when the server says the token has expired?
6. [ ] Walk through how an email in the inbox could get a false fact into long-term memory, and where your design stops it.

## Experiments
1. [ ] Memory off, profile only, and profile plus episodic retrieval on M01–M12: precision, recall and tokens.
2. [ ] Inject a contradicting fact; measure how often the old one is still used after consolidation.
3. [ ] Run the three adversarial emails with and without the redaction and untrusted-text tagging.
4. [ ] Full re-read against incremental sync on a calendar with 1,000 events: API calls, latency and rate-limit headroom.

## Production lens
- **Deletion is a feature.** "Forget this" must remove the memory, anything derived from it, and its copies in caches and indexes.
- **Token storage** is a secrets-management problem: encrypted at rest, scoped per user, revocable, rotated.
- **Rate limits are per user and per app.** One noisy user must not exhaust the app's quota.
- **Privacy classes.** Some categories are never stored at all, whatever the user says in passing.

## Not yet
Knowledge-graph memory, learned retrieval policies and enterprise directory connectors. The policy and lifecycle questions come first.

## Checkpoint
- [ ] You can explain why memory is a policy problem with your own M01–M12 numbers.
- [ ] The real calendar connector syncs incrementally, survives an expired sync token and token refresh, and every write passes through the policy service.
- [ ] None of the adversarial emails changes a stored memory or triggers a write without approval.

---

# Week 14: a multi-user service

*Phase: The assistant · Primary reading/code: Open WebUI, pgvector filtering, procrastinate*

Until now rig has served one person on one machine. Perplexity and Muse serve millions of people from shared servers: many users, many conversations each, several open tabs per user, and workers that come and go. This week rig becomes a service. Users sign in. Every conversation and message lives in Postgres, every row and every vector belongs to exactly one user, and the database enforces it. A job queue spreads runs across workers, and a test suite proves no user can read another's data. By now rig holds every kind of per-user state (conversations, memory, files, grants, retrieved chunks and caches), so isolation can be designed once, across all of it.

## Concepts
- **The data model.** Users own conversations; conversations hold messages; a message starts a run; a run has steps. Messages form a tree through `parent_id`, so an edit or a regenerate branches instead of overwriting. The messages are the source of truth: on every turn, the context sent to the model is rebuilt from them (plus Week 3's compaction summaries) on whichever worker picks the run up. Workers keep no conversation state in memory.
- **Identity comes from the session, never from the request body or the model.** The user id is read from an authenticated session; the conversation id is checked against it; the context builder then loads only that conversation's messages and that user's memory, files and grants. Tool calls, retrieval and the policy service all receive the same identity.
- **Tenancy models.** Shared tables with a `user_id` (or `tenant_id`) column, a partition or schema per tenant, or a database per tenant. Shared tables are the cheapest and the easiest to leak from. Most products start there and add enforcement in the database.
- **Row-level security.** A Postgres policy on a table (`USING (user_id = current_setting('app.user_id', true)::uuid)`) filters every query, and `WITH CHECK` refuses writes for anyone else. The app sets the user id inside each transaction with `set_config('app.user_id', …, true)`, the bind-parameter form of `SET LOCAL`. Table owners skip policies unless the table has `FORCE ROW LEVEL SECURITY`, and superusers and roles with `BYPASSRLS` always skip them, so the app connects as a plain role. A query that forgets `WHERE user_id = …` then returns that user's rows only, and a query outside any user scope fails instead of returning everything.
- **Vectors are tenant data too.** In a shared HNSW index, a filter is applied after the index scan. With 100 users and pgvector's default `hnsw.ef_search` of 40, a per-user query that goes through the HNSW index returns about half a row instead of 10 (measured below). pgvector 0.8's iterative scans keep scanning until there are enough rows. Partitioning by tenant also stops one tenant's vectors from changing another's recall. Open WebUI ships both designs: one collection per user, or one shared collection with a tenant filter.
- **Caches are the classic leak.** Week 10's response and semantic caches, retrieval caches and any memoized tool result are keyed by user unless they are provably public (a fetched public web page). A semantic cache shared across users answers one person's question with another person's private answer.
- **One active run per conversation.** Two tabs, a double click or a client retry can start two runs on one conversation that interleave messages and repeat tool calls. Serialize runs per conversation with a queue lock keyed on the conversation id, and make message submission idempotent with a client-generated id.
- **Stateless servers, a shared queue.** API servers authenticate, enqueue and stream; workers claim runs from a queue. Postgres can be the queue: `FOR UPDATE SKIP LOCKED` hands each job to exactly one worker, `LISTEN` and `NOTIFY` wake idle workers, and heartbeats expose dead ones. The worker running a job is rarely the server holding the user's connection, so events travel through pub/sub (Postgres `NOTIFY` or Redis) to the right tab.
- **Fairness.** Per-user request rates, per-user concurrent runs and per-user daily spend are checked before work is queued. A global token bucket protects the provider; it does not stop one heavy user from starving the rest.
- **Authentication is a library, not a project.** Use an existing library or identity provider for sign-in, sessions, expiry and revocation. Your job is to carry the identity through every layer, including traces and the cost ledger.
- **Deleting a user is a workflow.** Rows, vectors, uploaded files, workspace snapshots, caches, traces, and backups that expire on a stated schedule. A foreign-key cascade covers only the first of these.

## Day by day
| Day | Time | Do | Working by end of day |
|---|---|---|---|
| Mon | 1-1.5 h | Concepts: the data model, identity source, tenancy models, row-level security | A one-page note on why identity must come from the session, and what RLS adds over `WHERE user_id = …` |
| Tue | 2.5-3 h | Build steps 1-2: the Postgres schema and row-level security | Every per-user table has `FORCE ROW LEVEL SECURITY`; a forgotten `WHERE` still returns only the scoped user's rows |
| Wed | 3-4 h | Build steps 3-4: the HTTP API and the Postgres job queue | `rig serve` accepts a message over HTTP, enqueues it with the conversation as lock, and a worker claims and runs it |
| Thu | 1.5-2 h | Read Open WebUI (identity, conversations, vectors/tenants) and procrastinate; trace both paths | Notes on where Open WebUI enforces isolation in code versus where Build 2 puts it in the database |
| Fri | 2-3 h | Build steps 5-6: per-user limits and tenant-scoped retrieval/caches | A flooding user gets 429s; a filtered HNSW query keeps full recall with `hnsw.iterative_scan` on |
| Sat | 3-4 h | Build steps 7-8: the isolation suite and `rig admin delete-user` | U01-U12 report zero cross-user reads; the delete-user checker finds no trace of a deleted user |
| Sun | 3-4 h | Build step 9 load test; remaining experiments; project increment; checkpoint | p50/p95 time to first token recorded at 50 users; checkpoint passed or a redo list |

Each day below points at Build, Read and Experiments for the exact schemas, queries and traces rather than repeating them here.

### Monday — identity and the shape of a multi-tenant table.
Reading only. The whole week rests on one rule: identity comes from the authenticated session, never from the request body or the model, and the database — not application code — is what actually enforces it. Work through why shared tables with `user_id` are the cheapest tenancy model and the easiest to leak from, and what row-level security adds on top of a `WHERE` clause you could still forget to write.

1. Read **Concepts** above in full, twice through the row-level-security bullet.
2. Sketch the data model (`users` → `conversations` → `messages` → `runs`) and mark, for each table, which columns scope it to one user.
3. Write a half-page note: what a `FORCE ROW LEVEL SECURITY` policy does that a careful `WHERE` clause doesn't, and which Postgres roles skip it silently.

### Tuesday — schema and row-level security.
Today the database itself becomes the enforcement boundary. By tonight every per-user table rejects a cross-user read or write even if the application code forgets to filter — the property the rest of the week is tested against.

1. Implement **Build** step 1: the Postgres schema, plus `user_id` added to Week 4's `chunks`, Week 13's memories, Week 12's artifacts and Week 9's grants.
2. Implement **Build** step 2: `ENABLE`/`FORCE ROW LEVEL SECURITY` and a policy on every per-user table, the `user_scope` helper, and an app role without `BYPASSRLS`.
3. Deliberately drop a `WHERE user_id = …` from one repository query and confirm the database, not the code, is what stops the leak.

### Wednesday — the service and the queue.
Today rig stops being a CLI that happens to talk to Postgres and becomes an actual service: an HTTP API in front of the runtime, and a job queue that lets more than one worker process runs at once without two workers ever touching the same conversation concurrently.

1. Implement **Build** step 3: `rig/server/`, sign-in through an existing library, the idempotent message endpoint, the server-sent-events run stream, and cancel.
2. Implement **Build** step 4: the `jobs` table and claim query given there, worker heartbeats, and requeue on a dead worker.
3. Run two workers against one conversation and confirm the claim query's `o.id < j.id` clause does its job: never two running jobs for the same lock.

### Thursday — read Open WebUI and procrastinate.
No new code today. Open WebUI is the production version of everything built Tuesday-Wednesday, done in application code rather than the database; procrastinate is the Postgres-only queue whose claim query you copied. Reading both tells you exactly where your database-level enforcement is stronger, and where it still depends on code you wrote correctly.

1. Read **Read** below in the order given — identity, conversations, vectors and tenants, many workers, limits and deletion — then procrastinate's schema.
2. Trace both paths given there end to end.
3. Answer the **You should be able to answer** questions on where Open WebUI gets its user id and what `delete_user_by_id` does and doesn't touch.

### Friday — limits and tenant-scoped retrieval.
Today you close the two remaining ways one user can hurt another: a noisy user exhausting shared capacity, and a shared vector index quietly returning another tenant's near-neighbors into "yours." Neither failure is loud — the first looks like ordinary slowness, the second looks like below-average recall — which is why both need numbers, not a glance.

1. Implement **Build** step 5: the sliding-window request limiter, the two-active-runs cap, and the daily dollar budget read from Week 3's cost ledger.
2. Implement **Build** step 6: `user_id` filtering on every vector and full-text query with `hnsw.iterative_scan` on, and user-keyed response and semantic caches with an allowlisted public-web exception.
3. Confirm a flooding user gets 429 with `Retry-After` and that other users' latency doesn't move.

### Saturday — prove isolation, then prove deletion.
Today you stop asserting isolation and start attacking it: two users with planted secrets, then every route, query, cache and stream in the system asked for the other user's data. Then the mirror problem — proving a deleted user is actually gone everywhere, not just from the obvious table.

1. Implement and run **Build** step 7: the isolation suite U01-U12, including the forged-id and shared-document-injection cases.
2. Implement **Build** step 8: `rig admin delete-user` and its cross-store checker.
3. Run **Experiments** 1 and 3 below against the suite you just built.

### Sunday — load, the rest of the experiments, and the checkpoint.
Today you find out what happens under real concurrency: 50 simulated users, three tabs each, and one user deliberately flooding the rest. Then you assemble rig v0.14 and attempt the checkpoint cold.

1. Implement and run **Build** step 9: the load test, recording p50/p95 time to first token, queue wait and runs per worker per minute.
2. Run **Experiments** 2, 4, 5 and 6 below.
3. Assemble the **Project increment**: `rig serve` running the API and N workers against Postgres, with the isolation suite in CI.
4. Attempt **Checkpoint** below. If you can't pass it cold, redo the relevant day before Week 15.

## Build
1. [ ] Postgres for rig's own state: `users`, `conversations`, `messages` (with `parent_id` and a unique `(user_id, client_id)` for idempotent submits), `runs`, plus `user_id` on Week 4's `chunks`, Week 13's memories, Week 12's artifacts and Week 9's grants. Keep SQLite for a local single-user mode behind the same repository interface.
2. [ ] Row-level security on every per-user table, with `FORCE ROW LEVEL SECURITY`, an app role without `BYPASSRLS`, and a `user_scope` helper that opens a transaction and sets the user id (below). Every repository function takes a scoped connection; nothing else can reach the tables.
3. [ ] `rig/server/`: an HTTP API in front of the runtime. Sign-in through an existing library; `POST /conversations/{id}/messages` (idempotent on the client message id, returns a run id); `GET /runs/{id}/events` as server-sent events; `POST /runs/{id}/cancel`. The CLI becomes one client of this API.
4. [ ] A Postgres job queue: a `jobs` table whose `lock` is the conversation id, a claim query that never runs two jobs with the same lock (below), worker heartbeats, and requeue when a worker stops heartbeating. Run events reach the API process holding the stream through `NOTIFY` or Redis pub/sub.
5. [ ] Per-user limits, checked before enqueueing: a sliding-window request limiter, at most two active runs per user, and a daily dollar budget read from Week 3's cost ledger. Refusals return 429 with `Retry-After`.
6. [ ] Tenant-scoped retrieval and caches: every vector and full-text query filters by `user_id` with `hnsw.iterative_scan` on; Week 10's response and semantic caches are keyed by user, except an allowlisted public-web layer.
7. [ ] Isolation suite U01–U12. Two users with planted secrets. Every API route, retrieval query, memory lookup, cache, artifact download and event stream is asked for the other user's data: forged ids in URLs, user A's conversation id in user B's request, a reused event-stream URL, and a shared document carrying a prompt injection that asks the agent for another user's memory. Target: zero cross-user reads.
8. [ ] `rig admin delete-user`: a workflow over every store, then a checker that searches all of them for the user's id and planted strings.
9. [ ] A load test: 50 simulated users with 3 tabs each, mixed research and work turns. Measure time to first token (p50 and p95), queue wait, runs per worker per minute, and what happens to everyone else when one user floods.

These were tested on Postgres 16 with pgvector 0.8.7. A forgotten `WHERE` returns only the scoped user's rows, a forged insert is refused, and a query outside any scope errors. The claim query ran 200 jobs across 20 conversations on 8 concurrent workers with no double claims and never two running jobs for one conversation.

```python
@contextmanager
def user_scope(conn, user_id: UUID):
    with conn.transaction():
        # set_config(..., true) is SET LOCAL that accepts a bind parameter; it ends with the transaction
        conn.execute("SELECT set_config('app.user_id', %s, true)", (str(user_id),))
        yield conn
```

```sql
-- every per-user table: enable, force, one policy
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE messages FORCE ROW LEVEL SECURITY;          -- the table owner is checked too
CREATE POLICY own_rows ON messages
  USING      (user_id = current_setting('app.user_id', true)::uuid)
  WITH CHECK (user_id = current_setting('app.user_id', true)::uuid);

-- claim the next job: at most one running job per conversation, earliest first
UPDATE jobs SET status = 'running', worker_id = %(worker)s, heartbeat_at = now()
WHERE id = (
  SELECT j.id FROM jobs j
  WHERE j.status = 'queued'
    AND NOT EXISTS (SELECT 1 FROM jobs o
                    WHERE o.lock = j.lock
                      AND (o.status = 'running' OR (o.status = 'queued' AND o.id < j.id)))
  ORDER BY j.id
  LIMIT 1
  FOR UPDATE SKIP LOCKED)
RETURNING id, lock;
```

The `o.id < j.id` clause matters. Without it, two workers can each claim a different queued job for the same conversation in the same instant, because neither sees the other's uncommitted claim. With it, only the earliest queued job of a conversation is ever eligible, and `SKIP LOCKED` lets just one worker take it.

## Project increment
rig v0.14 is a multi-user service: `rig serve` runs the API and N workers against Postgres, and the isolation suite runs in CI on every change.

## Read
**[open-webui/open-webui](https://github.com/open-webui/open-webui)** at `v0.11.4`, a self-hosted, multi-user chat assistant with retrieval, memory and pluggable vector stores. The backend is Python. Read it as the production version of this week, and note where it enforces isolation in application code, where Build 2 puts it in the database. All paths are under `backend/open_webui/`.

1. Identity: `utils/auth.py` (665 lines): `create_token` (232), `decode_token` (246), `is_valid_token` (276, revocation), `revoke_user_tokens` (349) and `get_current_user` (393).
2. Conversations: `models/chats.py`: the `Chat` table (129) and its composite indexes on `user_id`; `get_chat_by_id_and_user_id` (1732), the ownership check used throughout `routers/chats.py`. `models/chat_messages.py`: `ChatMessage` (127, a tree through `parent_id`) and `has_unfinished_assistant_by_chat_id` (327), which tells the UI a run is still going.
3. Vectors and tenants: `retrieval/vector/dbs/pgvector.py` (792 lines): `DocumentChunk` (73), `_iterative_scan_setting` (263), `_ensure_text_search_index` (277) and `hybrid_search` (579). Then compare `qdrant.py`, which creates one collection per name, with `qdrant_multitenancy.py` (362 lines), which maps every name onto a few shared collections with a tenant filter: `_tenant_filter` (39), `_get_collection_and_tenant_id` (100) and `search` (246). `routers/memories.py` shows the naming that ties it together: each user's memories live in `user-memory-{user_id}` (134).
4. Many workers: `socket/main.py`: the Redis client manager (89) that lets any worker emit to any connection, `SESSION_POOL` (150), `get_session_ids_by_user_id` (344) and `emit_to_users` (356, one room per user).
5. Limits and deletion: `utils/rate_limit.py` (114 lines): `RateLimiter` (8) and `_is_limited_redis` (79), a rolling window built from per-minute buckets. `models/users.py`: `delete_user_by_id` (847), and the route that calls it in `routers/users.py` (1043).

**[procrastinate-org/procrastinate](https://github.com/procrastinate-org/procrastinate)** at `3.10.0`, a Postgres-only job queue. `procrastinate/sql/schema.sql` (599 lines): `procrastinate_fetch_job_v2` (210), whose `lock` rule is the one-run-per-conversation guarantee above; `procrastinate_defer_jobs_v1` (118) and the partial unique index on `queueing_lock` (100), which drops duplicate enqueues; the `pg_notify` triggers (around 412); `procrastinate_update_heartbeat_v1` (542) and `procrastinate_prune_stalled_workers_v1` (553).

**pgvector's README** at `v0.8.7` (pinned in Appendix A): the "Filtering", "Multitenancy" and "Iterative Index Scans" sections.

**Docs:** PostgreSQL's [Row Security Policies](https://www.postgresql.org/docs/current/ddl-rowsecurity.html) chapter, start to finish.

**Trace these paths:**

- Open WebUI: a chat request → `get_verified_user`, through `get_current_user`, decodes the token and loads the user → `chat_completion` in `main.py` (1110) → retrieval queries generated from the last messages (Week 10) → vector search in the user's collection → model stream → events to the user's room through the Redis manager → `ChatMessage` rows upserted.
- rig: `POST /conversations/{id}/messages` → session → `user_scope` → insert the message (idempotent) → enqueue with `lock` = conversation id → a worker claims it → rebuilds context under the same user scope → model and tools → events via `NOTIFY` → server-sent events to every open tab.

## You should be able to answer
1. [ ] Where does Open WebUI get the user id for a request, and what stops a client from sending another user's chat id?
2. [ ] What does row-level security add over a `WHERE user_id = …` in every query, and which roles skip it without warning?
3. [ ] Why does a filtered HNSW query return fewer than k rows, and what do iterative scans and partitioning each change?
4. [ ] Open WebUI's pgvector `hybrid_search` returns `None` when a metadata filter is set. Write the filtered hybrid query in one SQL statement instead.
5. [ ] How does procrastinate guarantee one running job per lock, and why must an earlier queued job with the same lock block later ones?
6. [ ] Which of rig's caches may be shared across users, and what exactly would a shared semantic cache leak?
7. [ ] List every store Open WebUI's `delete_user_by_id` touches, and every per-user store it doesn't. How would you find out whether something else cleans those up?
8. [ ] Why do streamed events need a pub/sub hop between the worker and the API server?

## Experiments
1. [ ] The isolation suite with row-level security off, on, and on with one repository query deliberately missing its `user_id` filter.
2. [ ] Filtered recall: 100 users sharing one HNSW index. Rows returned and recall@10 per user with `hnsw.iterative_scan` off, `relaxed_order` and `strict_order`, then with a partition per user; latency for each. On 20,000 random 32-dimensional vectors, with the planner kept on the HNSW index (`enable_seqscan` and `enable_bitmapscan` off), the off setting returned 0.5 rows out of 10 per query; `relaxed_order` returned all 10 at recall 1.00 and `strict_order` all 10 at 0.98.
3. [ ] Double submit: the same message from two tabs, 100 times. Count duplicate runs and repeated tool calls with and without the conversation lock and the idempotency key.
4. [ ] Load: time to first token (p50 and p95) and queue wait at 10, 50 and 100 simulated users. Then one user floods, with and without per-user concurrency limits.
5. [ ] Kill a worker mid-run: time until another worker claims the job (Week 15 makes the resume exact).
6. [ ] A semantic cache shared across users against one keyed by user: plant private answers and count cross-user hits.

## Production lens
- **Identity is threaded through everything:** logs, traces, the policy service, sandbox labels and the cost ledger. Traces hold user content, so access to traces is itself controlled, audited and time-limited.
- **Noisy neighbours:** per-user and per-organization quotas, and separate queues so interactive turns never wait behind background jobs.
- **Connection pools:** `SET LOCAL` and `set_config(…, true)` are safe behind a transaction-mode pooler such as PgBouncer; a session-level `SET` leaks one user's id into the next user's transaction.
- **Schema changes without downtime:** expand, migrate, contract. Workers on the old and new versions run side by side during a deploy.
- **Data residency:** some customers require their data to stay in one region, which decides where Postgres, the vector index and the caches live.
- **Admin access is a privilege:** any path that bypasses row-level security (migrations, support tools) uses a separate role, and every use is logged.

## Not yet
Organizations and sharing between users, SSO and SCIM provisioning, sharding Postgres, multi-region active-active, and end-to-end encryption.

## Checkpoint
- [ ] With two users and planted secrets, U01–U12 report zero cross-user reads, and removing one `WHERE` clause still leaks nothing.
- [ ] Two tabs on one conversation never produce two concurrent runs, and a killed worker's job is picked up by another worker.
- [ ] You can state rig's p95 time to first token at 50 users and what fails first as load grows.
- [ ] `rig admin delete-user` leaves no trace of the user's id or planted strings in any store you control, and you can say when backups forget them.

---

# Week 15: durable workflows, scheduling and approvals

*Phase: Autonomy · Primary reading/code: DBOS, LangGraph, OpenHands automation*

Durable execution is one idea: record every non-deterministic step's result in a durable log, and on recovery replay the code, returning recorded results instead of re-executing. An agent's transcript is already most of that log. The hard part is the gap between starting a side effect and recording its result. Add a clock and you have a scheduler, which is what proactive behaviour like Muse's background work needs.

## Concepts
- **The failure model:** `kill -9`, out-of-memory kills and deploys mid-run; host loss; provider overload; hung tools; side effects that half-happened; users who approve hours later.
- **Replay.** DBOS stores each step's output keyed by workflow id and step number; Temporal replays an event history; LangGraph snapshots state after each superstep and keeps pending writes for partly finished ones. All of them require the orchestrating code to be deterministic, so model calls, tool calls, clocks and randomness happen inside recorded steps.
- **Model ids are not stable keys.** Tool-call ids are generated by the model, and a re-query after a crash returns new ones. Record each model response before running its tools, and key side effects on run, step and call index.
- **Exactly-once execution is not available.** You get at-least-once execution plus idempotent effects, or at-most-once plus reconciliation. A tool ledger makes the choice explicit per tool: an intent row before executing, a result row after.
- **Recovering the gap.** Read-only tools re-run. Tools whose external API honours an idempotency key re-run with the same key. Tools with an observable effect are checked (a file's content hash, a marker's presence). Arbitrary `bash` cannot be classified, so it goes to a person.
- **Approvals are durable waits.** Persist state, release the process and the sandbox, and resume on an external signal, with an expiry that defaults to deny.
- **Scheduling is durable execution with a clock.** Decide what happens to runs missed during downtime, handle time zones and daylight-saving changes, and make sure two workers waking at 08:00 send one briefing, not two.
- **Code changes between crash and resume** break naive replay. Version prompts and tools, and record which version each run started with.
- **Load control:** queues with global concurrency and token-rate limits, circuit breakers per provider, and fallback models your eval set has approved.

## Day by day
| Day | Time | Do | Working by end of day |
|---|---|---|---|
| Mon | 1-1.5 h | Concepts: the failure model, replay, why a tool-call id can't be the idempotency key | A one-page note on the four tool classes (re-runnable, idempotent-by-key, observable, opaque) applied to every rig tool |
| Tue | 2.5-3 h | Build steps 1-2: the ledger tables and `rig resume` | A killed run resumes without re-calling the model for any recorded step |
| Wed | 3-4 h | Build steps 3-4: `edit_file` v3 and the crash fuzzer | The fuzzer kills and resumes at random points with zero duplicate and zero missing canary lines |
| Thu | 1.5-2 h | Read DBOS and LangGraph checkpointing; trace both paths | Notes on what makes a repeated workflow start idempotent, and what LangGraph's pending writes are for |
| Fri | 2-3 h | Build steps 5-6: durable approvals and the scheduler | An approval survives overnight with no live process; two workers waking at 08:00 send one briefing |
| Sat | 3-4 h | Build steps 7-8: the daily briefing and provider resilience; read OpenHands automation and pi's durable harness | The briefing runs end to end once; a forced provider failure falls over to the approved fallback model |
| Sun | 3-4 h | Experiments; project increment; checkpoint | Fifty-kill numbers recorded; checkpoint passed or a redo list |

Each day below points at Build, Read and Experiments for the exact schemas, code and traces rather than repeating them here.

### Monday — the failure model and why replay needs determinism.
Reading only. Before writing a ledger, get the central distinction straight in your own words: at-least-once execution plus idempotent effects, versus at-most-once plus reconciliation, and why the model's own tool-call id can't be your idempotency key (a crash and retry gets a new one). This is the one idea the rest of the week is built on.

1. Read **Concepts** above twice, and work through the `durable_tool_call` sketch in **Build** below line by line before typing any of it in.
2. Classify every tool rig currently has as re-runnable, idempotent-by-key, observable, or opaque, per the four recovery strategies in Concepts.
3. Write a half-page note: what identifies a step, and why must the orchestrating code around it be deterministic for replay to be correct.

### Tuesday — the ledger and resume.
Today you build the two tables that make a crash survivable: `steps`, which lets replay skip model calls that already happened, and `tool_ledger`, which lets replay tell whether a side effect happened before the crash. By tonight a run you `kill -9` partway through can be resumed without repeating anything already committed.

1. Implement **Build** step 1: `steps` and `tool_ledger`, committed before any output is shown or any side effect starts.
2. Implement **Build** step 2: `rig resume <run_id>`, rebuilding the transcript from `steps` and resolving every `intent` row by tool class.
3. Kill a run by hand after a model call but before its tool results, resume it, and confirm the model call isn't re-sent.

### Wednesday — reconcile, then fuzz it.
Today you give `edit_file` a way to tell whether an edit it attempted actually landed, and then build the tool that proves the whole ledger under real kills rather than hand-picked ones. This is deliberately the heaviest build day of the week — the fuzzer is what turns "should be crash-safe" into a measured property.

1. Implement **Build** step 3: `edit_file` v3 with a content-hash precondition, so `reconcile` can distinguish "landed," "didn't happen," and "unknown."
2. Implement **Build** step 4: the crash fuzzer — a supervisor that kills a child process at random points and resumes it — and the canary tool it grades against.
3. Run the fuzzer for at least 50 trials and confirm the grader reports exactly one canary line per idempotency key before moving on.

### Thursday — read DBOS and LangGraph checkpointing.
No new code today. DBOS reduces durable execution to two tables you can read in ten minutes; LangGraph solves the same problem with a checkpoint-per-superstep model built for branching and human-in-the-loop. Both are the same idea as Tuesday's ledger, dressed differently — reading them is the fastest way to see what your own design is missing.

1. Read **Read** below for DBOS and LangGraph, in the order given, then trace both paths.
2. Answer the **You should be able to answer** questions on what a checkpoint holds versus pending writes, and why a node re-executes from its start after `interrupt` resumes.

### Friday — approvals and the scheduler.
Today two different kinds of "wait" get built: a human approval that can sit for hours with no process or sandbox held open, and a clock-driven scheduler that must never double-fire when two workers wake at the same moment. Both are durable waits — the difference is who releases them.

1. Implement **Build** step 5: durable approvals — a pending-approval row on `ask`, `rig approve <run_id> <key>` to resume, and expiry that defaults to deny.
2. Implement **Build** step 6: `rig/scheduler/`, the cron poller claiming due slots under a lease, run ids derived from schedule and slot time, and an explicit missed-run policy.
3. Leave an approval pending overnight, or simulate it, and confirm resume works with no process kept alive in between.

### Saturday — the briefing, provider resilience, and the remaining reads.
Today rig does its first proactive, unprompted work: a daily briefing assembled from calendar, inbox, tasks and memory, delivered exactly once a day even across a restart. Alongside it, provider resilience means a primary-provider outage degrades to an approved fallback model instead of failing the run outright. Read OpenHands' scheduler and dispatcher today too — it's the production version of the scheduler you built yesterday.

1. Implement **Build** step 7: the daily briefing, confirmed to produce an update rather than a second briefing when a calendar changes after delivery.
2. Implement **Build** step 8: the typed error taxonomy, circuit breaker, and fallback model, enabled only where Week 8's evals show an acceptable pass rate.
3. Read **Read** below for OpenHands automation and pi's durable harness, and trace the OpenHands path given there.

### Sunday — fifty kills, the rest of the experiments, and the checkpoint.
Today you put a number on everything built this week, assemble rig v0.15, and attempt the checkpoint cold.

1. Run **Experiments** 1-6 below, including the fifty-kill suite and the scheduler's daylight-saving and outage runs.
2. Assemble the **Project increment**: resumable after any crash, a tool ledger, durable approvals, a scheduler and a daily briefing.
3. Attempt **Checkpoint** below. If you can't pass it cold, redo the relevant day before Week 16.

## Build
1. [ ] `rig/durable/`: `steps` and `tool_ledger` tables (below), in Week 14's Postgres or in SQLite in WAL mode for the local single-user mode; the rules are the same. Commit before any output is shown or any side effect starts.
2. [ ] `rig resume <run_id>`: rebuild the transcript from `steps` without re-calling the model for recorded responses, and resolve every `intent` row by tool class.
3. [ ] `edit_file` v3 with a content-hash precondition, so its `reconcile` can tell whether an edit landed.
4. [ ] The crash fuzzer: a supervisor runs tasks in a child process and kills it at random points (before or after the model call, after the intent row, after the side effect, after the result), then resumes. A canary tool appends one line per call; the grader asserts exactly one line per idempotency key.
5. [ ] Durable approvals: a policy `ask` writes a pending-approval row and exits; `rig approve <run_id> <key>` resumes, possibly the next day; unanswered approvals expire to deny.
6. [ ] `rig/scheduler/`: `rig schedule add "0 8 * * *" briefing --tz America/Los_Angeles`. A poller claims due slots under a lease, derives the run id from the schedule and the slot time so a retry or a second worker cannot send twice, and applies an explicit missed-run policy (run only the latest missed slot).
7. [ ] The daily briefing, rig's first Muse-style proactive job: calendar, inbox, tasks, memory and a little web research become one prioritized briefing, delivered once a day. A calendar change after delivery produces an update, not a second briefing.
8. [ ] Provider resilience: a typed error taxonomy, a circuit breaker, and a fallback model in Week 8's gateway, enabled only for task types where the eval shows an acceptable pass rate.

The ledger core below was tested with real process kills. In 50 trials with 82 kills at random points, it produced zero duplicate and zero missing side effects, and an orphaned `bash` intent stopped for a person instead of re-running. The 12-week draft's `durable_tool_call`, re-implemented as written (keyed on the model's call id, no recorded model responses), produced 521 duplicate side effects under the same 50 trials.

```python
# rig/durable/ledger.py (core)
# CREATE TABLE steps (run_id TEXT, seq INTEGER, kind TEXT, payload TEXT,
#                     PRIMARY KEY (run_id, seq, kind));
# CREATE TABLE tool_ledger (idem_key TEXT PRIMARY KEY, run_id TEXT, tool TEXT, args TEXT,
#   state TEXT NOT NULL CHECK (state IN ('intent', 'done', 'unknown')), result TEXT);
# SQLite in autocommit mode, journal_mode=WAL, synchronous=FULL: every write is durable on its own.

NOT_DONE, UNKNOWN = object(), object()     # what a tool's reconcile() can report

class NeedsHuman(Exception):
    """A side effect may or may not have happened; a person (or a reconciliation job) decides."""

def durable_tool_call(ledger, run_id, seq, index, call, tools):
    key = f"{run_id}:{seq}:{index}"        # stable across replays; the model's call id is not
    tool = tools[call["name"]]
    row = ledger.row(key)                   # (state, result) or None
    if row and row[0] == "done":
        return row[1]                       # replay: never execute twice
    if row and row[0] == "unknown":
        raise NeedsHuman(key)
    if row and row[0] == "intent":          # died between intent and result: did it happen?
        seen = tool.reconcile(key, call["input"])
        if seen is UNKNOWN:
            ledger.mark_unknown(key)
            raise NeedsHuman(key)
        if seen is not NOT_DONE:            # it happened; record what we observed
            ledger.finish(key, seen)
            return seen
    else:
        ledger.intent(key, run_id, call["name"], call["input"])   # durable BEFORE the side effect
    result = tool.run(call["input"], idempotency_key=key)        # external APIs dedupe on the key
    ledger.finish(key, result)
    return result

def run_durable(run_id, task, model, tools, ledger, max_steps=20):
    transcript = [{"role": "user", "content": task}]
    for seq in range(max_steps):
        response = ledger.get_step(run_id, seq, "model")
        if response is None:                # not recorded, so nothing from this step has run yet
            response = ledger.put_step(run_id, seq, "model", model(transcript))  # INSERT OR IGNORE
        transcript.append({"role": "assistant", "content": response["content"]})
        calls = [b for b in response["content"] if b["type"] == "tool_use"]
        if not calls:
            return response
        results = []
        for i, call in enumerate(calls):
            out = durable_tool_call(ledger, run_id, seq, i, call, tools)
            results.append({"type": "tool_result", "tool_use_id": call["id"], "content": out})
        transcript.append({"role": "user", "content": results})
    return {"stop": "max_steps"}
```

## Project increment
rig v0.15: resumable after any crash, a tool ledger, durable approvals, a scheduler and a daily briefing.

## Read
**[dbos-inc/dbos-transact-py](https://github.com/dbos-inc/dbos-transact-py) (main).** Durable execution reduced to database tables you can read. In `dbos/_schemas/system_database.py`, the `workflow_status` table (line 28) and `operation_outputs` (103): the second table is the whole trick. Then in `dbos/_core.py`: `_init_workflow` (591), `_execute_workflow_wthread` (1097), `workflow_wrapper` (1910), `invoke_step` (2218), `run_step` (2394). In `dbos/_sys_db.py`: `record_operation_result` (2804), `check_operation_execution` (2967), `get_pending_workflows` (2616), `init_workflow` (4775). Finally `dbos/_recovery.py` (72 lines), whose `recover_pending_workflows` (50) is the entire recovery story.

**[langchain-ai/langgraph](https://github.com/langchain-ai/langgraph), checkpointing and interrupts only.** `libs/checkpoint/langgraph/checkpoint/base/__init__.py` (`Checkpoint` at 93, `BaseCheckpointSaver` at 199 with `get_tuple`, `list`, `put`, `put_writes`), `libs/checkpoint/langgraph/checkpoint/memory/__init__.py` (the shortest complete saver), `libs/langgraph/langgraph/pregel/_loop.py` (`tick` at 623, `after_tick` at 707, `put_writes` at 439, `_put_checkpoint` at 1181), `pregel/_algo.py` (`should_interrupt` at 156, `apply_writes` at 233, `prepare_next_tasks` at 348), and `langgraph/types.py` (`Interrupt` at 584, `Command` at 833, `interrupt` at 893).

**[OpenHands/automation](https://github.com/OpenHands/automation)** at `b43294c`: a production scheduler and dispatcher for agent runs. `openhands/automation/scheduler.py` (320 lines): `_is_automation_due_safely` (79, cron evaluation), `poll_and_schedule` (157, which claims due automations with `FOR UPDATE SKIP LOCKED` at line 151) and `scheduler_loop` (265). `dispatcher.py`: `_poll_pending_runs` (127, `SKIP LOCKED` again at 163), `_execute_run` (209) and `dispatch_pending_runs` (565). `models.py`: `Automation` (61) and `AutomationRun` (175).

**[pi's durable harness](https://github.com/earendil-works/pi/tree/main/packages/durable) (experimental).** The Week 2 harness rebuilt so that conversations, model turns and tool calls are committed to storage before anything is shown. Read the README sections on persisting and resuming, busy conversations, aborts and subagents, child tasks and the task graph, then `src/harness/harness.ts` (437 lines), `submissions.ts` and `inbox.ts`. Its API is marked experimental.

**Trace these paths:**

- DBOS: calling a `@DBOS.workflow` → `workflow_wrapper` → `_init_workflow` (inserts the status row, or finds the existing one for that id, which makes starts idempotent) → the function body → each `@DBOS.step` → `invoke_step` → `check_operation_execution` (a recorded output short-circuits the step) → otherwise run it and `record_operation_result` → `update_workflow_outcome`. Recovery: process start → `recover_pending_workflows` → `get_pending_workflows` → `_recover_workflow` → re-execution under the same id, where completed steps return their recorded outputs.
- LangGraph: `invoke(input, {"thread_id": ...})` → `_first` loads the latest checkpoint → `tick` → `prepare_next_tasks` → tasks run → `put_writes` saves each task's writes as it finishes → `after_tick` → `apply_writes` → `_put_checkpoint`. HITL: `interrupt(value)` raises inside a node → the checkpoint records the pending interrupt → `invoke(Command(resume=answer))` re-runs that node from its start with the answer returned from `interrupt`.
- OpenHands automation: `scheduler_loop` → `poll_and_schedule` (lock due rows, skip ones another worker holds) → `_is_automation_due_safely` → a new `AutomationRun` → `dispatcher_loop` → `dispatch_pending_runs` → `_poll_pending_runs` → `_execute_run`.

## You should be able to answer
1. [ ] What identifies a step in DBOS, and why must workflow code be deterministic for replay to be correct?
2. [ ] If the process dies after a step's side effect but before `record_operation_result`, what happens on recovery? What guarantee does that give, and how do you turn it into effectively-once?
3. [ ] Why does starting a workflow with an id that already exists not run it twice?
4. [ ] In LangGraph, what is in a checkpoint and what is in pending writes, and why are pending writes needed?
5. [ ] Why does a node re-execute from its beginning after `interrupt` resumes, and what does that require of the code before the `interrupt` call?
6. [ ] Classify every rig tool as re-runnable, idempotent by key, observable, or opaque.
7. [ ] Why can't the model's tool-call id be the idempotency key?
8. [ ] Where does a pending approval live so that no process or container is held open overnight?
9. [ ] Two scheduler workers wake at 08:00. Walk through why exactly one briefing is sent.

## Experiments
1. [ ] Fifty random kills across the suite: resume success rate, duplicated canary markers (target zero), and the extra cost of recovery.
2. [ ] Key the ledger on the model's call id instead and reproduce the duplicates.
3. [ ] Change the system prompt between crash and resume, and confirm recorded steps are not re-queried.
4. [ ] Leave an approval pending overnight; resume and measure the cold-cache cost of the first request.
5. [ ] Force primary-provider failure and run the suite on the fallback model; compare pass rate and cost.
6. [ ] Run the scheduler across a simulated daylight-saving change and a six-hour outage; count briefings per day (target exactly one).

## Production lens
- **Every side effect has an owner and an idempotency key** that reaches the external system, not just your own database.
- **Recovery costs tokens** only for steps that were never recorded; measure it.
- **Durable approvals free compute.** Nothing runs while a person decides, and the default on expiry is deny.
- **Scheduled jobs have an SLO:** on time, exactly once, in the user's time zone.

## Not yet
Temporal's internals and building a workflow engine at scale. With the primitives in hand, each is a reading project.

## Checkpoint
- [ ] rig survives 50 random `kill -9`s with zero duplicated canary markers, and resumed runs pass at a rate within the noise of uninterrupted ones.
- [ ] An approval waits overnight with no live process, then resumes and completes correctly.
- [ ] The daily briefing arrives exactly once a day across a restart, a second worker and a daylight-saving change.

---

# Week 16: browser and computer use

*Phase: Autonomy · Primary reading/code: browser-use*

A browser agent is Week 1's loop where the observation is a page and the actions are navigate, click and type. The new problem is security: the page is untrusted input, the browser holds sessions, and every request leaves your machine. This week you wrap a real browser runtime, separate observation from action, and gate actions on where data goes, not only on the verb.

## Concepts
- **Observation and action.** The observation is a serialized DOM or accessibility tree with numbered interactive elements, often plus a screenshot; the action names an element index. Computer use replaces the DOM with pixels and mouse and keyboard, which works on any app (Muse is gaining Mac computer use) and costs far more per step.
- **Risk follows the data.** A GET to an attacker's URL with a secret in the query string is exfiltration. Links can unsubscribe, confirm or log in. Typing can autosave, search as you type, or submit on Enter. So `navigate` is not read-only and "fill but don't submit" is not reversible.
- **The Comet case (Brave, August 2025).** Hidden text in a Reddit comment led Perplexity's Comet to read the user's account email, open a lookalike domain with a trailing dot, read a one-time password from the user's logged-in Gmail, and post both back as a reply. Brave's mitigations: separate the user's instructions from page content, check every action against what the user asked, confirm sensitive actions, and isolate agentic browsing from everyday browsing.
- **Isolation.** The agent's browser never uses your everyday logged-in profile. Credentials are injected per domain from a secrets store and never appear in the model's context.
- **Taint.** Once a task has read private data, navigation to any host outside the task's allowlist needs approval.
- **Loops and drift.** Agents repeat failing actions; page fingerprints and loop detectors catch it.

## Day by day
The loop is Week 1's; the new work is almost entirely the gate and the isolation around it, so most of the week's code is smaller than it looks.

| Day | Time | Do | Working by end of day |
|---|---|---|---|
| Mon | 1 to 1.5 h | Read Concepts; note why `navigate` is not read-only | A half-page note with three examples of actions that look read-only but aren't |
| Tue | 2 to 3 h | `rig/browser/`'s `BrowserTool`: navigate, observe, click, type, download | A real page returns a stable observation (URL, title, text, numbered elements) |
| Wed | 2 to 4 h | The destination-aware gate; isolated profile, per-domain credentials, per-task allowlist | The gate's own test cases (OTP in a query string, trailing-dot host, `javascript:` URL, a private value typed into another site) all stop or ask; pre-taint browsing is still allowed |
| Thu | 1.5 to 2 h | Read browser-use; trace the path to `SecurityWatchdog`; replay the Comet disclosure against your gate | Notes naming the exact rule where your gate stops the Comet attack |
| Fri | 1 to 1.5 h | The four experiments | `notes/week16-experiments.md` |
| Sat | 3 to 4 h | Browser evals B01 to B12 on fixture and adversarial pages; rig v0.16 | Zero forbidden actions completed across B01 to B12 |
| Sun | 1 to 2 h | Optional desktop-app pass via screenshots; checkpoint | Checkpoint passed or a redo list |

### Monday — observation, action, and why risk follows the data.
No code today. This week's loop is Week 1's; what's new is that the page is untrusted and the browser holds sessions. Read **Concepts** and understand why `navigate` is not read-only, a GET can be an exfiltration channel, and typing can autosave or submit — every later decision this week (the gate, the allowlist, the isolated profile) is a direct consequence of that one fact.

1. Read **Concepts** in full, including the Comet case.
2. Write a half-page note: three actions that look read-only but aren't, and why.

### Tuesday — the browser tool, no gate yet.
Today you wrap a real browser runtime and get a clean, numbered observation out of it, before worrying about what the agent is allowed to do with that observation. Everything downstream — the gate, the evals — depends on this shape being right first.

1. Implement **Build** step 1's `rig/browser/`: `navigate`, `observe`, `click`, `type`, `download` on Playwright or browser-use's `BrowserSession`.
2. Point it at a few ordinary pages by hand and confirm the observation (URL, title, text, interactive elements, optional screenshot) is stable and the numbered elements match what you'd click.

### Wednesday — the gate and isolation.
Today the agent stops being able to hurt you. Wire the destination-aware gate from **Build** in front of every action, give each task its own browser profile, inject credentials by domain, and scope navigation to a per-task host allowlist — this is the week's actual security boundary; everything else is scaffolding around it.

1. Implement the destination-aware gate — the check that runs before every browser action and decides allow, deny or ask — exactly as given in **Build** step 2; don't loosen the taint rule.
2. Wire a fresh profile per task and per-domain credential injection, per **Build** step 3.
3. Run the gate's own test cases (OTP in a query string, a trailing-dot host, a `javascript:` URL, a private value typed into another site) and confirm each stops or asks, and that ordinary pre-taint browsing is still allowed.

### Thursday — read browser-use, then replay Comet.
browser-use is a production agent built around exactly this week's problem, so read it for how a real `SecurityWatchdog` makes the allow/ask/deny decision your gate makes. Then replay Brave's Comet disclosure step by step against your own gate — the actual test of whether Wednesday's work holds against a real attack, not just your own test cases.

1. Read **Read** in full, following the given trace path.
2. Replay the Comet disclosure; at each step, note which rule in your gate would stop it, or wouldn't.
3. Answer **You should be able to answer** question 5 from this replay, not from memory.

### Friday — break the gate on purpose.
No new code today. Run the four experiments in **Experiments** below against the agent you already built. Write up what changed in `notes/week16-experiments.md`: pass rate, approvals, and where the adversarial pages actually got stopped.

### Saturday — the eval ladder.
Today you run B01 to B12, the fixture-and-adversarial task ladder that is this week's real regression suite, and ship rig v0.16. Passing the benign tasks says the agent is useful; passing the adversarial ones is the point of the week.

1. Run **Build** step 4's evals B01 to B12, local fixture sites where possible.
2. Confirm **Project increment**: an isolated profile per task and the gate behind the policy service.
3. Record approvals per benign task alongside pass/fail — you need it for the checkpoint and for Experiment 4.

### Sunday — optional desktop pass, then checkpoint.
Optional computer-use detour if you want to feel the cost difference; otherwise go straight to the checkpoint. Whether you pass it cold, not whether you clicked through B01 to B12, is the real signal for whether you're ready for Week 17.

1. Optional: drive one desktop app through screenshots with the same gate (**Build** step 5); compare cost per step against the DOM path.
2. Attempt **Checkpoint** below cold.

## Build
1. [ ] `rig/browser/`: a `BrowserTool` on Playwright (or browser-use's `BrowserSession`) with `navigate`, `observe`, `click`, `type` and `download`, and an observation of URL, title, text, interactive elements and an optional screenshot path.
2. [ ] The destination-aware gate below, called by Week 9's policy service before every browser action.
3. [ ] A fresh browser profile per task, credentials injected by domain, and a per-task host allowlist.
4. [ ] Browser evals B01–B12 on local fixture sites where possible: find information; compare products; navigate documentation; download a public file; fill a form but stop before submitting; find an appointment slot without booking; and adversarial pages with hidden-text instructions, a trailing-dot lookalike login, a request to visit a URL carrying another tab's content, and HTML that pretends to be a system message.
5. [ ] Optional: drive one desktop app through screenshots with the same gate, to feel the cost of pixels against the DOM.

The gate below was tested: an OTP in a query string, a trailing-dot lookalike host, a `javascript:` URL, typing a private value into another site and submitting all stop or ask, while ordinary browsing before any private data is read is allowed.

```python
# rig/browser/gate.py
from dataclasses import dataclass, field
from enum import Enum
from urllib.parse import urlsplit

class Decision(Enum):
    ALLOW = "allow"
    ASK = "ask"
    DENY = "deny"

@dataclass
class BrowserTask:
    allowed_hosts: set[str]                                 # granted for this task only
    private_values: set[str] = field(default_factory=set)   # strings read from private sources

    @property
    def tainted(self) -> bool:
        return bool(self.private_values)

def host_of(url: str) -> str | None:
    u = urlsplit(url)
    return u.hostname if u.scheme == "https" else None      # keeps a trailing dot: "x.ai." != "x.ai"

def carries_private(task: BrowserTask, text: str) -> bool:
    return any(v and v in text for v in task.private_values)

def gate(task: BrowserTask, action: str, *, url: str = "", text: str = "", submits: bool = False,
         irreversible: bool = False) -> Decision:
    if irreversible:                                        # purchase, delete, send money
        return Decision.ASK
    if action == "navigate":
        host = host_of(url)
        if host is None:
            return Decision.DENY                            # no http:, file:, javascript:, data:
        if carries_private(task, url):
            return Decision.ASK                             # a GET is an exfiltration channel
        if host not in task.allowed_hosts:
            return Decision.ASK if task.tainted else Decision.ALLOW
        return Decision.ALLOW
    if action == "type":
        if carries_private(task, text) and host_of(url) not in task.allowed_hosts:
            return Decision.ASK
        return Decision.ASK if submits else Decision.ALLOW  # Enter or a submit button sends it
    if action == "click":
        return Decision.ASK if submits else Decision.ALLOW
    return Decision.DENY                                    # unknown action: closed by default
```

## Project increment
rig v0.16: a browser mode with an isolated profile per task and a destination-aware gate behind the policy service.

## Read
**[browser-use/browser-use](https://github.com/browser-use/browser-use)** at `c75e847`. Start with `skills/open-source/references/agent.md` and `browser.md` for orientation, then:

1. `browser_use/agent/service.py` (4,163 lines; read selectively): `Agent.run` (2503), `step` (1035), `_prepare_context` (1087), `_get_next_action` (1176), `get_model_output` (1945), `_execute_actions` (1211), `multi_act` (2730), `_post_process` (1219) and `_handle_step_error` (1258); and how domain-scoped `sensitive_data` credentials are handled (from line 533).
2. `browser_use/agent/views.py`: `PageFingerprint` (95), `ActionLoopDetector` (157), `ActionResult` (307), `AgentOutput` (388) and `AgentHistory` (488).
3. `browser_use/tools/service.py`: `Tools` (441) and the actions `navigate` (507), `input` (778), `upload_file` (864), `evaluate` (1837) and `click` (2132).
4. `browser_use/browser/watchdogs/security_watchdog.py` (296 lines): `on_NavigateToUrlEvent` (35), `_is_url_allowed` (176) and `_is_url_match` (252); and in `browser/profile.py`, `user_data_dir` (557), `allowed_domains` (628) and `prohibited_domains` (632).

**Brave's [Comet disclosure](https://brave.com/blog/comet-prompt-injection/)**: replay it, step by step, against your gate.

**Trace this path:** `Agent.run` → `step` → `_prepare_context` (DOM serialization and screenshot into a browser-state summary) → `_get_next_action` → `get_model_output` (an `AgentOutput` with actions) → `_execute_actions` → `multi_act` → a `Tools` action such as `navigate` → a navigate event → `SecurityWatchdog.on_NavigateToUrlEvent` → `_is_url_allowed` → browser navigation → `_post_process` (loop detection) → next step.

## You should be able to answer
1. [ ] What does browser-use send the model as "the page", and why not raw HTML?
2. [ ] How does the security watchdog decide whether a URL is allowed, and how does it treat IP addresses and subdomains?
3. [ ] Why is `navigate` not read-only? Give two exfiltration routes that use navigation alone.
4. [ ] How do domain-scoped credentials keep secrets out of the model's context?
5. [ ] Walk the Comet attack through your gate: at which step does rig stop, and on which rule?
6. [ ] When would you choose computer use over DOM actions, and what does it cost?

## Experiments
1. [ ] The adversarial pages with the gate off, the gate on, and the gate plus an isolated profile.
2. [ ] DOM only, screenshot only, and both: success rate, tokens and latency.
3. [ ] Loop detection on and off on an infinite-scroll page.
4. [ ] Approvals per benign task: is the gate creating approval fatigue?

## Production lens
- **Agentic browsing gets its own profile, cookies and credentials.** Never the user's everyday browser.
- **Every navigation and submission is a trace event** with its destination host.
- **CAPTCHAs and bot detection** are a site's decision; respect them rather than evade them.
- **Recordings** (screenshots, network logs) are sensitive data with a retention policy.

## Not yet
Anti-detection, browser-based crawling at scale, and training visual grounding models.

## Checkpoint
- [ ] rig stops at the approval boundary before every external or irreversible action, even with adversarial instructions on the page: zero forbidden actions completed across B01–B12.
- [ ] You can replay the Comet attack against rig and point to the trace event where it stops.
- [ ] Benign tasks need few enough approvals that you would accept them as a user.

---

# Week 17: voice and realtime

*Phase: Autonomy · Primary reading/code: pipecat*

A voice agent is the same loop inside a hard real-time budget: audio in, speech detection, transcription, the model, synthesis, audio out, with the user free to interrupt at any moment. Muse is coming to Meta's glasses with a wake word and has a realtime avatar. This week you build the small version and measure where every millisecond goes.

## Concepts
- **The pipeline.** Microphone → voice activity detection → streaming speech-to-text → end-of-turn decision → the model (streaming) → streaming text-to-speech → speaker. A speech-to-speech model collapses the middle three stages.
- **The latency budget.** What the user feels is the gap between when they stop speaking and when audio starts. It sums the VAD's stop delay (pipecat's default `stop_secs` is 0.2 s), the final transcription, the model's time to first token, text-to-speech time to first audio, and buffering. Measure each; overlap what you can.
- **Turn-taking.** Silence alone cuts people off mid-thought, so end-of-turn detection is a classification problem. Barge-in means stopping playback and cancelling generation the moment the user speaks: Week 2's cancellation on a 200 ms clock.
- **Frames.** pipecat models audio, text and control as frames flowing through processors; interruptions are system frames that jump the queue.
- **Transcript truth.** After a barge-in the transcript must record what was actually played, not what was generated, or the model believes it said things the user never heard.
- **Always-on devices.** Wake-word detection runs on the device; only audio after the wake word should leave it.

## Day by day
The hard part this week isn't any single stage, it's that all of them run under a budget the user actually feels — so the day shape front-loads getting a pipeline working at all, then spends the back half of the week measuring and breaking it.

| Day | Time | Do | Working by end of day |
|---|---|---|---|
| Mon | 1 to 1.5 h | Read Concepts; map every stage of the latency budget | A half-page note naming every stage between end of speech and first audio |
| Tue | 2 to 3 h | `rig/voice/`: a pipecat pipeline — Silero VAD, streaming STT, rig's runtime, streaming TTS | A spoken question gets a spoken answer end to end, uninstrumented |
| Wed | 2 to 4 h | Barge-in and sentence-level streaming | Speaking over the bot stops playback and cancels generation; the first sentence reaches TTS before the model finishes |
| Thu | 1.5 to 2 h | Read pipecat; trace the frame path; add latency instrumentation | Timestamps for all six latency-budget stages, with p50 and p95 over a few runs |
| Fri | 1 to 1.5 h | The four experiments | `notes/week17-experiments.md` |
| Sat | 3 to 4 h | Voice evals V01 to V10; rig v0.17 | V01 to V10 pass with the same policy and memory behaviour as text mode |
| Sun | 1 to 2 h | Optional wake word or image input; checkpoint | Checkpoint passed or a redo list |

### Monday — the pipeline and the latency budget.
No code today. Before writing a pipecat pipeline you need to know what you're budgeting: six stages between the user falling silent and your bot's first sound, each a real number you'll measure Thursday. Read **Concepts** and map every stage onto the pipeline so Tuesday's build already has a shape in your head.

1. Read **Concepts** in full.
2. For VAD stop delay, final transcription, model time to first token, TTS time to first audio, and buffering, write one sentence on what determines each.
3. Note which stages a speech-to-speech model would collapse, and why that doesn't make them free.

### Tuesday — assemble the pipeline.
Today you wire pipecat's frame graph end to end for the first time — VAD, STT, rig's runtime, TTS — with no interruption handling and no instrumentation yet. A spoken question producing a spoken answer, however slowly, is the only goal; barge-in and latency come once the happy path exists.

1. Implement **Build** step 1: Silero VAD, a streaming STT service, rig's runtime in research or personal mode, a streaming TTS service.
2. Run one full turn by voice and confirm the answer comes back as audio.

### Wednesday — real-time behavior: barge-in and sentence streaming.
Today the pipeline stops assuming the user waits politely. Add barge-in (stop playback, cancel the model stream and any not-yet-started tool calls, truncate the transcript to what was actually played) and sentence-level streaming (send the first sentence to TTS before the model finishes) — the two mechanisms that make a voice agent feel real-time instead of like a slow phone tree.

1. Implement **Build** step 2 (barge-in); confirm interrupting mid-sentence stops audio immediately.
2. Implement **Build** step 4 (sentence-level streaming); confirm the first sentence reaches TTS before the model's full response is generated.
3. Interrupt yourself mid-bot-sentence a few times by hand and read the resulting transcript: it must say what was actually played, not what was generated.

### Thursday — read pipecat, then instrument.
pipecat's own frame types and VAD defaults are the reference for exactly the mechanism you built Wednesday by feel. Read it to see the real implementation, then add **Build** step 3's instrumentation with those frame boundaries in mind — you now know exactly which frame transition each timestamp belongs to.

1. Read **Read: pipecat** in full, following the given trace path.
2. Implement **Build** step 3: timestamps at end of user speech, VAD stop, final transcript, model first token, first synthesized audio, playback start.
3. Report p50 and p95 per segment on a handful of turns.

### Friday — find the knobs that actually move latency.
No new code today. Run the four experiments in **Experiments** below against the pipeline you built Tuesday to Thursday. Write up what moved in `notes/week17-experiments.md`: which knob changed perceived latency, and which just moved cost around.

### Saturday — the voice eval ladder.
Today you run V01 to V10, covering the failure modes a pure latency number hides — a correction mid-answer, a long pause that must not get cut off, a tool request. Passing them is what lets you claim rig works by voice, not just that it's fast.

1. Run **Build** step 5's evals V01 to V10.
2. Confirm **Project increment**: a voice front end for research and personal modes, with barge-in and a latency report.

### Sunday — optional extras, then checkpoint.
Optional if time allows; otherwise go straight to the checkpoint, the real signal for whether Week 17 is done.

1. Optional: an on-device wake word, or an image-input path (**Build** step 6).
2. Attempt **Checkpoint** below cold.

## Build
1. [ ] `rig/voice/`: a pipecat pipeline with Silero VAD, a streaming speech-to-text service, rig's runtime (research or personal mode) and a streaming text-to-speech service.
2. [ ] Barge-in: when the user starts speaking, stop playback, cancel the model stream and any tool calls not yet started, and truncate the assistant's message to what was played.
3. [ ] Latency instrumentation: timestamps for end of user speech, VAD stop, final transcript, model first token, first synthesized audio and playback start; report p50 and p95 per segment.
4. [ ] Sentence-level streaming: send the first sentence to text-to-speech before the model finishes.
5. [ ] Voice evals V01–V10: short factual questions, a multi-turn task with a correction mid-answer, an interruption mid-sentence, a noisy-room recording, a long pause mid-thought (the agent must not cut in), and a tool request ("what's on my calendar tomorrow?").
6. [ ] Optional: an on-device wake word, and an image input path (a photo of a document, then a question about it).

## Project increment
rig v0.17: a voice front end for research and personal modes, with barge-in and a latency report.

## Read: pipecat
[pipecat-ai/pipecat](https://github.com/pipecat-ai/pipecat) at `a3b149f`, an open-source framework for realtime voice and multimodal agents.

1. `src/pipecat/frames/frames.py` (2,662 lines; skim): `InterruptionFrame` (1241), `UserStartedSpeakingFrame` (1253), `BotStartedSpeakingFrame` (1411).
2. `src/pipecat/processors/frame_processor.py`: `FrameProcessor` (194), `queue_frame` (699), `process_frame` (819), `push_frame` (1007) and `_start_interruption` (1133).
3. `src/pipecat/pipeline/pipeline.py` (202 lines): `PipelineSource` (21), `PipelineSink` (55) and `Pipeline` (91). Then `pipeline/worker.py`: `PipelineWorker` (202), `run` (866) and `queue_frame` (911). `PipelineTask` is deprecated in favour of `PipelineWorker`.
4. `src/pipecat/audio/vad/vad_analyzer.py`: `VADParams` (47; defaults of confidence 0.7, start 0.2 s, stop 0.2 s) and `VADAnalyzer` (63). Then `silero.py`: `SileroVADAnalyzer` (130) and `voice_confidence` (199).
5. `src/pipecat/turns/`: the end-of-turn strategies, including `speculation_gate.py` and `eager_end_of_turn_mixin.py`.

**Trace this path:** an input audio frame → the VAD analyzer → `UserStartedSpeakingFrame` → if the bot is speaking, an `InterruptionFrame`, and `_start_interruption` clears queued frames → speech-to-text frames → the user stops (after `stop_secs`) → the aggregated user turn → the model service streams text frames → text-to-speech streams audio frames → `BotStartedSpeakingFrame` → output.

## You should be able to answer
1. [ ] Where does each millisecond between the end of the user's speech and the first audio go in your pipeline?
2. [ ] What does `stop_secs` trade off, and why isn't silence alone a good end-of-turn signal?
3. [ ] What happens to queued frames when an interruption arrives, and why are interruptions system frames?
4. [ ] After a barge-in, what should the transcript say the assistant said?
5. [ ] Which tool calls can be cancelled mid-flight during a barge-in, and which must be allowed to finish (Week 15)?
6. [ ] What leaves an always-listening device before and after the wake word?

## Experiments
1. [ ] `stop_secs` at 0.2, 0.5 and 0.8 s: false cut-ins against latency.
2. [ ] Sentence streaming to text-to-speech on and off: time to first audio.
3. [ ] A cascaded pipeline against a speech-to-speech model, if you have access to one: latency, quality and tool-calling reliability.
4. [ ] Interrupt at 20 random points; check the transcript is truthful and no tool runs twice.

## Production lens
- **Per-segment latency SLOs,** with p95 mattering more than p50 for how a conversation feels.
- **Audio is sensitive data:** consent, retention, and on-device processing where possible.
- **Transport:** WebRTC against WebSockets, jitter buffers, packet loss.
- **Cost per minute** adds speech-to-text, model and text-to-speech.

## Not yet
Training speech models, echo-cancellation internals, and building a WebRTC stack.

## Checkpoint
- [ ] Median time from end of speech to first audio is reported with a breakdown, and you can name the biggest segment and what would shrink it.
- [ ] Barge-in stops audio, cancels generation and leaves a truthful transcript in all 20 interruptions.
- [ ] V01–V10 pass with the same policy and memory behaviour as text mode.

---

# Week 18: production architecture, capability evals and your graduation project

*Phase: Autonomy · Primary reading/code: Your own traces*

This week you put research, work and personal modes behind one runtime, evaluate by capability rather than one score, run the held-out set once, and finish the graduation project for your track. The architecture is the diagram in "The central project"; the point of the week is that every box has an eval and every risk has a mechanism you can point to in code.

## Concepts
- **One runtime, three modes.** A mode is a configuration: system prompt, tool set, grants and budgets. A hard upfront router is a classifier with its own error rate; prefer one agent with mode-scoped tools, and if you keep a router, evaluate it like any other component.
- **Trust layering.** The sandbox wraps only code execution and the browser. Sessions, memory, the tool ledger, workflows, artifacts and the policy service live on the trusted side, where sandboxed code cannot write them.
- **Evaluate by capability.** One headline score hides regressions; a suite per capability shows them. Report pass@1 and pass^3, cost per success, p50 and p95 latency, peak input tokens and compaction events, and tool-error and policy-violation rates for each.
- **Online evaluation.** Offline suites catch the regressions you thought of; production traffic finds the rest. Collect explicit feedback (thumbs, a reason) and implicit signals (regenerations, edits, abandoned turns), sample traces into a review queue graded by your judge, and ship changes behind A/B splits or as shadow runs on copies of live requests. Open WebUI turns side-by-side votes into Elo ratings per model.
- **Cross-mode regressions.** A prompt or tool change for one mode runs every suite before it merges.

| Suite | Core metrics |
|---|---|
| Research | Accuracy, citation precision and recall, freshness, source quality, time to first token |
| Work | Task, computation and artifact correctness; tool and sandbox errors |
| Personal | Memory precision and recall, connector correctness, approval and schedule correctness |
| Runtime | Resume success, duplicate side effects, timeouts, retries, overflows, budget exits |
| Browser | Task completion, wrong clicks, forbidden actions, approval compliance, injection resistance |
| Voice | End of speech to first audio, false cut-ins, barge-in transcript truthfulness |
| Multi-user | Cross-user reads (target zero), p95 time to first token under load, fairness when one user floods |

## Day by day
Last week of the plan, and the heaviest skew toward the graduation project of any week: Tuesday to Thursday wire the plumbing (one front door, CI, feedback, retention, the held-out run), and Friday through Sunday are almost entirely your track's project and the write-ups it feeds.

| Day | Time | Do | Working by end of day |
|---|---|---|---|
| Mon | 1 to 1.5 h | Read Concepts; commit to your track if you haven't | A half-page note on why one agent with mode-scoped tools beats a hard router |
| Tue | 2 to 3 h | `rig/app/`: one front door for all three modes; capability suites wired into CI | Every request carries user, mode, budget and grants; CI runs a subset on a trivial change |
| Wed | 2 to 4 h | Feedback and experiment plumbing; a retention policy per store | Thumbs and regenerate events land on every answer; `rig admin delete-user` actually clears every store |
| Thu | 2 h | Run the Week 5 held-out set once; scope your track's graduation project | The held-out write-up exists, with intervals, and is not rerun; your task is picked and its fixtures lined up |
| Fri | 3 to 4 h | Graduation project, day one | Your track's project runs end to end at a basic level; the other two tracks' basic versions also pass |
| Sat | 3 to 4 h | Graduation project, day two; the production concerns document | Your track's project is at public-write-up quality, with numbers; every row of Production concerns, mapped points at code |
| Sun | 2 to 3 h | Publish the write-up; final checkpoint | Write-up published; Final checkpoint passed or a redo list |

### Monday — one runtime, three modes.
No code today. Everything else this week assumes modes are configuration, not separate agents, and that one headline score would hide exactly the regressions you're about to spend the week catching. Read **Concepts**, and if you haven't committed to a track yet, decide now — Thursday's scoping depends on it.

1. Read **Concepts** in full.
2. Write a half-page note on why a hard upfront router is a classifier with its own error rate, and what that costs you against mode-scoped tools on one agent.
3. If undecided, pick your track from **Graduation projects** below.

### Tuesday — the front door and CI.
Today all three modes stop being separate code paths and become configuration behind one API — Week 14's surface, extended so every request carries a mode alongside its budget and grants. Wire the capability suites into CI now, before the rest of the week's changes need a regression gate to run against.

1. Implement **Build** step 1: `rig/app/` as the one front door for conversations, runs, approvals and schedules across modes.
2. Implement **Build** step 2: CI running capability-suite subsets on every change, full suites nightly, blocking on regressions judged with Week 5's paired comparisons.
3. Make a trivial change in one mode and confirm CI catches a deliberate regression in another.

### Wednesday — feedback loop and retention.
Today you close two loops that don't show up in any offline eval: online signal (thumbs, regenerations, a sampled review queue, an experiment flag) and the deletion path a real multi-user service owes its users. Neither is exciting; both are load-bearing for the production document you write Saturday.

1. Implement **Build** step 3: feedback and regenerate events, a nightly sampling job into your Week 5 judge, an experiment flag reported with a paired comparison.
2. Implement **Build** step 4: a retention policy per store (messages, traces, caches, artifacts, backups), enforced by a Week 15 scheduled job.
3. Run `rig admin delete-user` against a fixture account and confirm every store is actually clean.

### Thursday — the held-out set, once, then scope the graduation project.
The held-out set only means something if you run it exactly once and don't tune on it, so do that before the graduation project tempts you to go patch something it exposes. Then scope your track's project: what you'll build, what fixture data or repo you need, and what your graders check for it.

1. Run **Build** step 5: the Week 5 held-out set, once, written up with intervals. Do not rerun it.
2. Read your track's prompt under **Graduation projects** below and write down, before coding, what each grader needs to see.
3. Line up whatever fixtures the project needs: nothing extra for the research prompt; the two CSVs, the PDF and a repo for the work prompt; fixture email and calendar for the personal prompt.

### Friday — graduation project, day one.
Today you build your track's project to a basic, end-to-end level, and confirm the other two tracks' basic versions also run — the task asks for all three at a basic level before your own track goes deep. This is the week's biggest block of new code; Tuesday through Thursday exist to support it.

1. Build your track's project from **Graduation projects** end to end at a basic level.
2. Get the other two tracks' projects running at a basic level too, even if shallow.
3. Run your track's graders against your first end-to-end pass and read every failure.

### Saturday — graduation project, day two, and the production document.
Today you take your own track's project from "runs" to "published with numbers," and write the two-page "rig in production" document that **Production concerns, mapped** structures for you. The document is not new prose per concern — it's a pointer, row by row, to the actual mechanism in your code.

1. Finish your track's project to public-write-up quality: fix what Friday's grader run exposed, and compute the numbers your track's graders ask for.
2. Write **Build** step 7's document, one line per row of **Production concerns, mapped** pointing at a file and mechanism, using the failed-run traces from **Read** where a row needs evidence you don't already have.

### Sunday — publish, then the final checkpoint.
The last day of the plan is paperwork that matters: get the write-up out where someone else can read it, then attempt the checkpoint cold. Passing it, not finishing eighteen weeks on the calendar, is the actual finish line.

1. Publish the final write-up (**Build** step 8, Appendix E).
2. Attempt **Final checkpoint** below cold; if a row has no code to point to, that's your redo list, not a footnote.

## Build
1. [ ] `rig/app/`: Week 14's API becomes the one front door for all three modes (conversations, runs, approvals, schedules). Modes are configurations; every request carries user, mode, budget and grants.
2. [ ] CI that runs capability-suite subsets on every change and the full suites nightly, blocking merges on regressions judged with Week 5's paired comparisons.
3. [ ] Feedback and experiments: thumbs and regenerate events on every answer, a nightly job that samples traces into a review queue graded by your Week 5 judge, and an experiment flag that splits users between two configurations, reported with Week 5's paired comparison.
4. [ ] Retention: a policy per store (messages, traces, caches, artifacts, backups), enforced by a Week 15 scheduled job and checked by `rig admin delete-user`.
5. [ ] Run the Week 5 held-out set exactly once and write it up with intervals.
6. [ ] Your graduation project (below).
7. [ ] "rig in production": a two-page design document organized by the table below.
8. [ ] Publish the final write-up (Appendix E).

## Project increment
rig v1.0: one runtime with research, work and personal modes, every capability suite in CI, and your graduation project.

## Graduation projects
Do all three at a basic level, then take your track's project to a public write-up with numbers. These three come from the 12-week draft and are kept as written.

1. **Research track.** "Research how NVIDIA's datacenter strategy has changed over the past six months. Reconcile conflicting reports and support every major factual claim with sources." Exercises fresh search, query decomposition, ranking and deduplication, iterative research, citation provenance and synthesis. Score with your R-suite graders plus a manual citation audit.
2. **Work track.** Input: two CSVs, one PDF and a git repository. "Determine why this metric regressed. Validate your hypothesis using code and repository evidence. Produce a report and charts." Exercises file understanding, code search, shell and Python execution, long-context management, and artifact creation and verification.
3. **Personal track.** Using fixture email and calendar first: "Over the next month, help me prepare for a conference. Track important deadlines, research attendees before meetings, generate a Monday briefing, and adjust when my calendar changes. Ask before changing anything important." Exercises memory, connectors, research, scheduled execution, durable state, change detection, approvals and proactive work.

## Production concerns, mapped
| Concern | Mechanism in rig | Where you saw it in real code |
|---|---|---|
| Timeouts | HTTP 300 s; tool timeout inside the sandbox; run wall clock; approval expiry; voice turn budget | mini-swe-agent `_run`; pi `bash.ts`; pipecat `VADParams` |
| Retries | Model calls only, jittered backoff honouring `retry-after`; tools never retried by the harness | SDK `_should_retry`; pi `_prepareRetry` |
| Context limits | Accounting, masking, tool-result clearing, compaction, one retry after overflow; deliberate cache breakpoints and TTLs | pi `compaction.ts`; inspect `_handle_overflow`; OpenHands view properties |
| Duplicate tool execution | Ledger keyed on run, step and call index; intent and result rows; reconcile by tool class | DBOS `operation_outputs`; your crash fuzzer |
| Process crashes | Model responses recorded before tools run; resume replays recorded outputs | DBOS recovery; LangGraph checkpoints; pi durable |
| Provider failures and rate limits | Typed errors, circuit breaker, global token bucket, eval-approved fallback | pi `_isRetryableError` |
| Idempotency | Keys passed to external APIs; content-hash preconditions; run ids derived from schedule slots | your `edit_file` v3; OpenHands automation `SKIP LOCKED` |
| Checkpointing | Postgres (SQLite WAL locally), a row per step, committed before output | LangGraph `BaseCheckpointSaver` |
| Permissions | A separate policy service; scoped, expiring grants; durable approvals; audit events | Muse's Sentinel (as described); Codex `execpolicy`; srt |
| Sandboxing | Per-user workspace; OS sandbox or container; no secrets inside; egress allowlist; isolated browser profile | sandbox-runtime; OpenHands workspaces; browser-use profiles |
| Multi-tenancy | Row-level security; caches and vectors keyed by user; one run per conversation; per-user quotas | Open WebUI tenant collections; procrastinate locks; your isolation suite |
| Data retention and deletion | A policy per store; deletion as a workflow with a checker | Open WebUI `delete_user_by_id` |
| Untrusted input | Tagging; research mode without shell or writes; destination-aware gate; inbound email treated as data | Brave's Comet disclosure; your red-team suites |
| Cost and token budgets | Hierarchical budgets; caps per run; per-call model and effort routing; cost per success in reports | mini-swe-agent `cost_limit`; search_evals cost accounting |
| Latency | Time-to-first-token budgets for research and voice; effort ceilings per mode; prefix caching; streaming | Perplexity's Search API post; nano-vllm; pipecat |
| Observability | OTel spans, trajectory metrics, capability suites, regression gate | OTel GenAI conventions; SWE-bench grading |
| Online quality | Feedback events, sampled judge review, A/B splits | Open WebUI evaluations and Elo |

## Read
Your own system. Pick three failed runs from each capability suite and trace each one end to end, from the request to the failing step, using only your traces. Then re-read Perplexity's Search API post and the Muse coverage and list every mechanism they describe that rig does not have. Then Open WebUI's feedback loop at `v0.11.4`: `backend/open_webui/models/feedbacks.py` (`Feedback`, 20) and `routers/evaluations.py`: `_calculate_elo` (86) and `get_leaderboard` (223), which reweights votes by how similar their tags are to a query.

## Not yet (after the eighteen weeks)
Temporal's internals, building a workflow engine at scale, agent hosting on Kubernetes, and training models on your own trajectories. With the primitives in hand, each is a reading project rather than a new field.

## Final checkpoint
- [ ] One runtime serves all three modes; every capability suite runs in CI; a change in one mode cannot merge if another regresses.
- [ ] The held-out result is reported once, with intervals, and you did not tune on it.
- [ ] Your graduation project is published with numbers, and your "rig in production" document covers every row of the table; a reviewer finds no concern you cannot point to in code.

---

# Appendix A: reading order

Read in this order; each repository arrives only after the week that gives you the primitive it implements. Pins are the commits or tags that the file paths and line numbers in this plan were checked against. Two repositories moved organizations: `badlogic/pi-mono` is now `earendil-works/pi`, and `anthropic-experimental/sandbox-runtime` is now `anthropics/sandbox-runtime`; the old URLs redirect and the pinned commits are the same.

| # | Repository | Pin | Weeks | Why it earns the time | Start with |
|---|---|---|---|---|---|
| 1 | [anthropics/anthropic-sdk-python](https://github.com/anthropics/anthropic-sdk-python) | `22feda0` | 1 | A production retry policy in about 40 lines | `_base_client.py` `_should_retry` |
| 2 | [SWE-agent/mini-swe-agent](https://github.com/SWE-agent/mini-swe-agent) | `04d809c` | 1 | The whole loop on two screens; the bash-only baseline | `agents/default.py` |
| 3 | [earendil-works/pi](https://github.com/earendil-works/pi) | `75a9972` | 2, 3, 8, 9, 15 | Provider, runtime and harness as separate packages; compaction and cache accounting; virtual-model routing; an MCP client; a durable harness | `packages/agent/src/agent-loop.ts` |
| 4 | [Aider-AI/aider](https://github.com/Aider-AI/aider) | `5dc9490` | 2, 4 | Text-format edits with fallbacks; code retrieval with PageRank | `coders/editblock_coder.py`, `repomap.py` |
| 5 | [sgl-project/sglang](https://github.com/sgl-project/sglang) | `0b63526` | 3 | The radix tree behind prefix caching | `srt/mem_cache/radix_cache.py` |
| 6 | [openai/codex](https://github.com/openai/codex) | `72c9595` | 3, 8, 9, 13 | A compaction prompt, cache-preserving effort updates, sandbox profiles, a two-phase memory pipeline | `codex-rs/memories/README.md` |
| 7 | [dorianbrown/rank_bm25](https://github.com/dorianbrown/rank_bm25) | `47aa3dd` | 4 | The BM25 family in one 257-line file | `rank_bm25.py` |
| 8 | [nmslib/hnswlib](https://github.com/nmslib/hnswlib) | `ca42672` | 4 | The reference HNSW | `hnswlib/hnswalg.h` |
| 9 | [pgvector/pgvector](https://github.com/pgvector/pgvector) | `f37c13f` | 4, 14 | HNSW inside a database: inserts, deletes, filtered search, iterative scans for tenants | `src/hnswinsert.c`, `src/hnswscan.c` |
| 10 | [SWE-bench/SWE-bench](https://github.com/SWE-bench/SWE-bench) | `02e7a74` | 5 | The canonical definition of "resolved" | `harness/grading.py` |
| 11 | [UKGovernmentBEIS/inspect_ai](https://github.com/UKGovernmentBEIS/inspect_ai) | `6d252fe` | 5 | Dataset, solver and scorer; a validated-judge pattern | `agent/_react.py`, `scorer/_model.py` |
| 12 | [open-telemetry/semantic-conventions-genai](https://github.com/open-telemetry/semantic-conventions-genai) | `06ec68e` | 5 | Standard span and attribute names for agents | `docs/gen-ai/gen-ai-agent-spans.md` |
| 13 | [karpathy/nanochat](https://github.com/karpathy/nanochat) | `92d63d4` | 6, 7 | Tokenizer to RL to inference, small enough to read whole | `nanochat/engine.py` |
| 14 | [GeeeekExplorer/nano-vllm](https://github.com/GeeeekExplorer/nano-vllm) | `bb823b3` | 7 | Paged KV cache and continuous batching in about 1,200 lines | `engine/scheduler.py`, `engine/block_manager.py` |
| 15 | [PrimeIntellect-ai/verifiers](https://github.com/PrimeIntellect-ai/verifiers) | `da75527` | 7 | An eval harness seen as an RL environment | `docs/v1/architecture.md` |
| 16 | [lm-sys/RouteLLM](https://github.com/lm-sys/RouteLLM) | `0b64fda` | 8 | A learned router and its threshold calibration in a few hundred lines | `routellm/routers/routers.py` |
| 17 | [BerriAI/litellm](https://github.com/BerriAI/litellm) | `v1.102.0` | 8, 10 | A production gateway: complexity routing, session pinning, cache-aware load balancing, semantic cache | `router_strategy/complexity_router/README.md` |
| 18 | [modelcontextprotocol/python-sdk](https://github.com/modelcontextprotocol/python-sdk) | `v2.3.0` | 9 | The protocol's version history in code | `mcp_types/version.py` |
| 19 | [anthropics/sandbox-runtime](https://github.com/anthropics/sandbox-runtime) | `d9aac20` | 9 | OS-level sandboxing plus an allowlisting egress proxy | `src/sandbox/sandbox-manager.ts` |
| 20 | [searxng/searxng](https://github.com/searxng/searxng) | `6671d89` | 10 | Metasearch: fan-out with a deadline, merge, score | `searx/search/__init__.py` |
| 21 | [adbar/trafilatura](https://github.com/adbar/trafilatura) | `e2f85c9` | 10 | A main-content extraction cascade | `trafilatura/core.py` |
| 22 | [openai/openai-cookbook](https://github.com/openai/openai-cookbook) | `0eac144` | 10 | The two-tool search and fetch contract | `examples/deep_research_api/how_to_build_a_deep_research_mcp_server/main.py` |
| 23 | [openai/swarm](https://github.com/openai/swarm) | `6af0b4c` | 11 | Handoffs specified in 292 lines (archived) | `swarm/core.py` |
| 24 | [openai/openai-agents-python](https://github.com/openai/openai-agents-python) | `v0.23.1` | 4, 11 | Swarm's ideas hardened: input filters, agent-as-tool | `src/agents/handoffs/__init__.py` |
| 25 | [perplexityai/search_evals](https://github.com/perplexityai/search_evals) | `cab4c5d` | 11 | Perplexity's deep-research benchmark runner | `harnesses/base.py` |
| 26 | [OpenHands/software-agent-sdk](https://github.com/OpenHands/software-agent-sdk) | `69e2688` | 12 | Agent, workspace and context cleanly separated | `sdk/workspace/base.py` |
| 27 | [docling-project/docling-core](https://github.com/docling-project/docling-core) | `v2.101.1` | 12 | Document structure and chunking that keeps tables and headings | `transforms/chunker/hybrid_chunker.py` |
| 28 | [letta-ai/letta-code](https://github.com/letta-ai/letta-code) | `42397c7` | 13 | Memory as a git-backed filesystem | `src/agent/memory-filesystem.ts` |
| 29 | [open-webui/open-webui](https://github.com/open-webui/open-webui) | `v0.11.4` | 5, 10, 14, 18 | A real multi-user assistant: auth, conversations, tenant-scoped vectors, query rewriting, feedback | `backend/open_webui/retrieval/vector/dbs/pgvector.py` |
| 30 | [procrastinate-org/procrastinate](https://github.com/procrastinate-org/procrastinate) | `3.10.0` | 14 | A job queue in Postgres: `SKIP LOCKED`, per-lock ordering, heartbeats | `procrastinate/sql/schema.sql` |
| 31 | [dbos-inc/dbos-transact-py](https://github.com/dbos-inc/dbos-transact-py) | `f8f9ee7` | 15 | Durable execution as readable tables | `dbos/_recovery.py` |
| 32 | [langchain-ai/langgraph](https://github.com/langchain-ai/langgraph) | `87f1c8e` | 15 | Superstep checkpoints, pending writes, `interrupt` | `checkpoint/base/__init__.py` |
| 33 | [OpenHands/automation](https://github.com/OpenHands/automation) | `b43294c` | 15 | A scheduler and dispatcher with row locks | `openhands/automation/scheduler.py` |
| 34 | [browser-use/browser-use](https://github.com/browser-use/browser-use) | `c75e847` | 16 | A browser agent runtime with domain controls | `browser/watchdogs/security_watchdog.py` |
| 35 | [pipecat-ai/pipecat](https://github.com/pipecat-ai/pipecat) | `a3b149f` | 17 | Frames, interruptions and VAD for realtime voice | `processors/frame_processor.py` |

Target codebase: [pallets/click](https://github.com/pallets/click) at `8.5.0`.

**Bootstrap the reading set once.** This clones everything with history but without file contents until checkout, then pins each repository. It was tested on a sample of the list, including the two moved repositories at their pinned commits.

```bash
mkdir -p reading && cd reading
while read -r repo ref; do
  dir=$(basename "$repo")
  git clone --quiet --filter=blob:none --no-checkout "https://github.com/$repo.git" "$dir"
  git -C "$dir" checkout --quiet "$ref"
done <<'EOF'
pallets/click 8.5.0
anthropics/anthropic-sdk-python 22feda0
SWE-agent/mini-swe-agent 04d809c
earendil-works/pi 75a9972
Aider-AI/aider 5dc9490
sgl-project/sglang 0b63526
openai/codex 72c9595
dorianbrown/rank_bm25 47aa3dd
nmslib/hnswlib ca42672
pgvector/pgvector f37c13f
SWE-bench/SWE-bench 02e7a74
UKGovernmentBEIS/inspect_ai 6d252fe
open-telemetry/semantic-conventions-genai 06ec68e
karpathy/nanochat 92d63d4
GeeeekExplorer/nano-vllm bb823b3
PrimeIntellect-ai/verifiers da75527
lm-sys/RouteLLM 0b64fda
BerriAI/litellm v1.102.0
modelcontextprotocol/python-sdk v2.3.0
anthropics/sandbox-runtime d9aac20
searxng/searxng 6671d89
adbar/trafilatura e2f85c9
openai/openai-cookbook 0eac144
openai/swarm 6af0b4c
openai/openai-agents-python v0.23.1
perplexityai/search_evals cab4c5d
OpenHands/software-agent-sdk 69e2688
docling-project/docling-core v2.101.1
letta-ai/letta-code 42397c7
open-webui/open-webui v0.11.4
procrastinate-org/procrastinate 3.10.0
dbos-inc/dbos-transact-py f8f9ee7
langchain-ai/langgraph 87f1c8e
OpenHands/automation b43294c
browser-use/browser-use c75e847
pipecat-ai/pipecat a3b149f
EOF
for d in */; do printf "%-40s %s\n" "${d%/}" "$(git -C "$d" rev-parse HEAD)"; done > SHAS.txt
```

**After the eighteen weeks**, in this order: vLLM's `vllm/v1/core` (the production version of Week 7), the rest of Codex CLI's `codex-rs/core`, Temporal's documentation on deterministic replay, and Perplexity's research blog. Each will read as a variation on something you have already built.

---

# Appendix B: glossary, term to primitive

Every entry reduces a term to something you have built in rig. "Framework-ism" means the term names a packaging choice rather than a new mechanism.

| Term | Underlying primitive | Kind |
|---|---|---|
| Prompt | The bytes of one request | Fundamental |
| System prompt | The first, privileged segment of a request | Fundamental |
| Context window | The maximum tokens one request may hold (input plus output) | Fundamental |
| Context engineering | Choosing and ordering the bytes of each request | Fundamental |
| Tokenizer, BPE | Learned merges from bytes to token ids | Fundamental |
| Special token | A reserved id that marks roles and tool calls; a chat template is these ids around text | Fundamental |
| Tool or function calling | Special tokens the model emits plus an engine that intercepts them; over an API, id-correlated results in the transcript | Fundamental |
| Tool schema | JSON Schema for arguments, sent (and billed) on every request | Fundamental |
| Structured output | Output constrained by a grammar compiled from a schema, or validated against it | Fundamental |
| Stop reason | Why generation ended; the loop's branch condition | Fundamental |
| Reasoning or thinking tokens | Output tokens spent before the answer; billed, sometimes hidden | Fundamental |
| Prefill, decode | Processing the prompt in parallel; generating one token at a time | Fundamental |
| KV cache | Per-layer attention keys and values for processed tokens | Fundamental |
| Prompt caching | Provider-side reuse of the KV cache for an identical prefix | Fundamental |
| Paged KV cache | The KV cache stored in fixed blocks with a block table, like virtual memory | Fundamental |
| Cache TTL, breakpoint | How long a cached prefix lives and where a request marks it; a bet on when the next request comes | Fundamental |
| Tool-result clearing, context editing | Replacing old tool outputs with placeholders, client- or server-side | Fundamental |
| Continuous batching | Admitting and retiring sequences at every decode step | Fundamental |
| Post-training, RLVR, GRPO | Raising the probability of completions that score well on a checkable reward | Fundamental |
| RL environment | Task set-up, tools and a reward: an eval harness | Fundamental |
| Reward hacking | Optimizing the grader instead of the task | Fundamental |
| Reasoning effort | A request parameter that scales how many output tokens, thinking and tool calls a model spends | Fundamental |
| Model routing | Choosing the model and effort for each call from features, rules or a learned predictor | Fundamental |
| Cascade, escalation | Trying a cheaper setting first and moving up when a check fails or the task stalls | Fundamental |
| Session affinity, pinning | Keeping a session on one model and effort so its prompt cache stays valid | Fundamental |
| Semantic cache | Reusing a stored answer when a new question's embedding is close enough to an old one | Fundamental |
| Agent | Model plus system prompt plus tools plus a loop plus a stop policy | Framework-ism |
| Agent loop, ReAct | A `while` loop alternating model calls and tool execution | Fundamental |
| Runtime | The machinery that runs loops reliably: events, cancellation, retries, persistence | Fundamental |
| Harness, scaffold | Everything around the model for one product | Fundamental |
| Coding agent | A harness over a repository with read, search, edit and shell tools, verified by tests | Specialization |
| Steering | A user message injected at the next turn boundary | Framework-ism |
| Workflow | Code-defined control flow with model calls as steps | Fundamental |
| Durable execution | Recorded step outputs plus deterministic replay | Fundamental |
| Checkpoint | Serialized state at a step boundary | Fundamental |
| Scheduler | Durable execution with a clock: due slots, leases, missed-run policy | Fundamental |
| Short-term memory | The transcript | Fundamental |
| Working memory, scratchpad, todo list | A file or message the agent rewrites | Framework-ism |
| Long-term memory | Text written after one session and loaded into later prompts | Framework-ism |
| Compaction, condensation | Replacing a transcript prefix with a summary | Fundamental |
| Observation masking | Replacing old tool outputs with placeholders | Fundamental |
| RAG | Ranking, then prepending the top results to the prompt | Fundamental |
| Agentic search | The model issuing its own searches through tools | Fundamental |
| Answer engine | Search, fetch, extract, rank passages, synthesize with citations | Composition |
| Deep research | An answer engine run for many rounds, often with parallel researchers | Composition |
| Citation provenance | Claim → evidence id → character offsets in stored source text | Fundamental |
| Embedding | A vector from an encoder model; similarity is a dot product | Fundamental |
| Vector database | An ANN index plus storage, metadata filtering and updates | Packaging |
| HNSW | A layered proximity graph searched greedily | Fundamental |
| Hybrid search | Several rankers fused, usually with reciprocal rank fusion | Fundamental |
| Query rewriting, multi-query, HyDE | A model call that turns a message into better search queries before retrieval | Fundamental |
| Contextual retrieval | Prefixing each chunk with a short note on where it sits in its document before indexing | Fundamental |
| Trigram matching | Similarity over three-character substrings, which survives typos | Fundamental |
| Reranker | A pairwise scorer applied to a short list | Fundamental |
| Subagent | A recursive loop call with a fresh transcript that returns a string | Framework-ism |
| Handoff | A tool call that swaps the active system prompt and tools | Framework-ism |
| Agent as tool | A subagent whose caller keeps control | Framework-ism |
| Planner/executor | One call that emits a list, then a loop over the list | Framework-ism |
| Orchestrator-workers | Fan-out of subagents plus a merge step | Framework-ism |
| Multi-agent system | Several loops connected by function calls or messages | Framework-ism |
| Guardrail | A check function before or after a model or tool call | Framework-ism |
| Skill | A prompt file, often with scripts, loaded on demand | Framework-ism |
| Tool search, deferred tools | Names in context; schemas loaded on demand | Framework-ism |
| Code mode | The model writes a script that calls tools as functions, run in a sandbox | Framework-ism |
| MCP | JSON-RPC for listing and calling tools, resources and prompts across processes | Protocol |
| MCP server | A process that answers those JSON-RPC methods | Protocol |
| Connector | An OAuth-scoped API client with incremental sync | Fundamental |
| Sandbox | OS isolation: namespaces, seccomp, Seatbelt, containers or VMs | Fundamental |
| Per-user workspace, VM | An isolated execution environment per user behind a narrow interface | Fundamental |
| Multi-tenancy | Many users on shared infrastructure, separated by keys the database enforces | Fundamental |
| Row-level security | A database policy that filters every query by the current user | Fundamental |
| Job queue | A table of work claimed with row locks (`SKIP LOCKED`), with heartbeats and retries | Fundamental |
| Artifact lineage | The inputs, code and step that produced an output | Fundamental |
| Policy gate (Muse's "Sentinel") | A separate service that decides allow, deny or ask for each proposed action | Fundamental |
| Grant | A scoped, expiring permission: service, access, scope, expiry | Fundamental |
| Permission, approval | A policy check; "ask" is a wait for a human | Fundamental |
| Approval fatigue | People approving reflexively because they are asked too often | Human factors |
| Human in the loop | A durable wait for external input | Fundamental |
| Agentic browser | A loop whose observation is a page and whose actions are navigate, click and type | Fundamental |
| Computer use | A loop whose observation is a screenshot and whose actions are mouse and keyboard | Fundamental |
| VAD, end-of-turn detection | Detecting speech, then deciding the user has finished | Fundamental |
| Barge-in | Cancelling speech and generation when the user interrupts | Fundamental |
| Wake word | An on-device detector that gates which audio leaves the device | Fundamental |
| Trace, span | A timed tree of operations with attributes | Fundamental |
| Trajectory | The full sequence of model outputs and tool calls in a run | Fundamental |
| Eval | Dataset plus solver plus grader plus metric | Fundamental |
| Trajectory evaluation | Grading properties of the path, not only the end state | Fundamental |
| LLM as judge | A model used as a classifier, valid only once measured against labels | Fundamental |
| Online evaluation, A/B test | Grading live traffic: feedback, sampled review and randomized splits between configurations | Fundamental |
| pass@k, pass^k | Probability that at least one, or all, of k runs pass | Fundamental |

---

# Appendix C: seventeen questions you should be able to answer

Answer each aloud, with numbers from your own rig runs where they apply. If an answer needs a framework's name to make sense, it is not finished.

1. Walk through one turn at the wire level: the bytes sent, every stop reason that can come back, and what the loop does for each, including a tool call cut off by the output limit.
2. Explain tool calling from the token level up: what the model emits, what the inference engine does, and what the API shows you.
3. "The agent got slower and more expensive as the session went on." Explain why with token arithmetic, then give three mitigations and what each costs in cache hits, summary calls and quality.
4. Why does a timestamp at the top of a system prompt cost money? Start from per-layer key and value tensors and end at a serving engine's block table.
5. A serving engine is at 40% of its target throughput. What do you measure first, and what are the likely causes?
6. When should retrieval be a tool rather than automatic context, and how would you prove the choice for a specific codebase?
7. Design the edit tool for a coding agent. Defend exact versus fuzzy matching with failure modes you have measured.
8. How does your research mode make every claim traceable, and how do you measure that the citations actually support the claims?
9. Your bill doubled and quality held. Walk through how you would find out whether routing, effort, cache misses or traffic caused it, using only your traces.
10. A tool call timed out. Did it run? Explain how you design the system so the answer does not matter, and why the model's tool-call id can't be the key.
11. Design the permission system for a personal agent that can spend money and send email for its user. Where does policy run, what is a grant, and how do you avoid approval fatigue?
12. What does your sandbox not protect against, and what changes once the agent reads untrusted web pages, documents and email?
13. A user reports seeing another user's document in an answer. Which layers could have leaked it (a retrieval filter, a cache key, memory, a role that skips row-level security, an event stream), and how do your traces tell you which?
14. How do you know a prompt change improved the agent? Describe the eval, the statistics and the confounds.
15. When does a multi-agent design beat a single agent, and what would you measure before shipping one?
16. The agent is waiting six hours for a human approval and you deploy a new version meanwhile. What happens, step by step, from the approval click to the next model call?
17. Where do the milliseconds go in a voice turn, and what happens to the transcript, the model call and any tool calls when the user interrupts?

---

# Appendix D: misconceptions and hype traps

Each trap below is something you will have disproved, or at least measured, in rig by Week 18.

| Trap | What is actually true | Where rig shows it |
|---|---|---|
| "You need a framework to build an agent." | The loop is about 40 lines. Frameworks earn their keep in runtime, durability and observability, not in the loop. | Week 1 `loop.py` |
| "Tool calling is an API feature." | It is special tokens the model was trained to emit and an engine that intercepts them. A model uses badly a tool it was never trained on. | Week 6 `Engine.generate` |
| "More tools make a more capable agent." | Every schema costs tokens on every request and adds selection errors. One shell plus a few well-shaped tools is a strong baseline. | Week 1 bash-only experiment; Week 9 tool-count experiment |
| "Bigger context windows end context engineering." | Cost scales with tokens per request times steps, distractors hurt quality, and caching constrains layout. | Week 3 peak-token and cache metrics |
| "RAG means a vector database." | Retrieval is ranking. BM25 and the agent's own grep are strong baselines, especially for code. | Week 4 recall table |
| "A citation means the claim is supported." | Presence is not support. Each claim has to be checked against its passage. | Week 10 citation precision |
| "Memory is a product you buy." | It is prompt assembly with persistence. The hard parts are what to write, when to load it, and what to redact. | Week 13 memory evals |
| "Multi-agent is the next level of capability." | It mainly buys context isolation and parallelism at a multiple of the token cost, and many tasks get worse. | Week 11 pass-rate-versus-cost plot |
| "MCP makes tools safe." | It standardizes discovery and invocation. Trust, scoping and injection are still yours. A server is untrusted code with untrusted output. | Week 9 red-team suite |
| "Prompt injection is fixed with better prompts." | The defense is capability restriction: sandboxing, a policy service outside the agent, egress control, and keeping untrusted content away from privileged actions. | Weeks 9 and 16 |
| "Navigation is read-only." | A GET can carry a secret to an attacker, and links can confirm, unsubscribe or log in. | Week 16 gate and the Comet replay |
| "The biggest model at maximum effort is the safe default." | It is the expensive default. Most agent steps pass on a smaller model or lower effort; the safe default is the cheapest setting your evals approve per role, with escalation. | Week 8 effort and model sweeps |
| "Caching is free money." | Writes cost more than plain input, entries expire, and a model or effort switch can throw them away. The TTL and breakpoints are choices to measure. | Week 3 TTL bet; Week 8 switch cost |
| "You need a dedicated vector database." | Postgres with pgvector keeps vectors beside the rows they belong to, with transactions, filters and row-level security. A dedicated engine earns its place at a scale, or for a feature, you have measured you need. | Week 4 pgvector comparison; Week 14 filtered recall |
| "Filtering by user id in the app is enough." | One forgotten clause, cache key or background job leaks data. Enforce isolation in the database and prove it with planted secrets. | Week 14 isolation suite |
| "It worked in the demo." | Run-to-run variance is large. Report pass^k and intervals, never a single run. | Week 5 noise-floor experiment |
| "An LLM judge is objective." | It is an unvalidated classifier until measured against labels, and the transcript it grades can inject it. | Week 5 judge calibration |
| "Temperature zero makes runs reproducible." | It does not guarantee identical outputs. Reproducibility comes from recording outputs. | `messages.json` and saved diffs |
| "Retries are free." | Retrying a tool repeats its side effects; retrying a model call costs money and changes the output. | Week 1 retry policy; Week 15 ledger |
| "Durable execution means exactly-once." | It means recorded replay. Side effects still need idempotency or reconciliation, keyed on something the model cannot change. | Week 15 crash fuzzer |
| "Voice is chat with speech bolted on." | It is a real-time system; end-of-turn detection, barge-in and a millisecond budget decide the experience. | Week 17 latency breakdown |
| "Benchmark scores transfer to my product." | A score measures one model in one harness on specific tasks. Your eval set on your data is the number that matters. | Weeks 1 to 18 eval suites |
| "Agents are autonomous." | Production agents are bounded loops inside workflows, with budgets, permissions and humans at the irreversible steps. | rig v1.0 |

---

# Appendix E: staying current and showing the work

Reading code makes you deep, but it doesn't keep you current and it doesn't show anyone what you know. Spend about an hour a week on each.

**The frontier log.** Read primary sources only: model and system cards, protocol changelogs, engineering posts from labs and product teams, and papers that ship code. For each item, write three lines in `notes/frontier.md`: what changed, which primitive in Appendix B it reduces to, and whether it changes anything in rig. An item you can't reduce to a primitive is the one to read in depth. Some examples, already reduced:

| What changed | Reduces to | Where it lands |
|---|---|---|
| MCP's `2026-07-28` revision dropped the `initialize` handshake and session ids; each request is self-contained | Stateless RPC over HTTP | Week 9 |
| OpenTelemetry's GenAI conventions moved to their own repository, with agent, workflow, plan and tool spans | A trace schema | Week 5 |
| Meta launched Muse in September 2026: a private VM per user with a visible browser, and Sentinel deciding allow, block or ask for each action | Workspace, policy service, grants | Weeks 9, 12 and 16 |
| Perplexity open-sourced search_evals, scoring deep-research systems on BrowseComp, DeepSearchQA, HLE and WideSearch | An eval harness | Week 11 |
| Effort became a first-class request parameter (Anthropic `output_config.effort`, OpenAI `reasoning.effort`), with mid-conversation changes that keep the cache | A request parameter that scales output tokens | Week 8 |
| nanochat trains a GPT-2-level model in about two hours on one 8×H100 node | The whole model pipeline | Week 6 |

**What 2026's launches point to.** This is my reading of what shipped, not a forecast. Agents are becoming long-running background workers with their own machines (Muse's per-user VM). Policy is moving out of the agent into separate services with scoped grants, because approval fatigue is real. Agents are starting to act in email and commerce, which makes idempotency and spending limits product requirements. Voice and wearables add a hard latency budget. Model choice and reasoning effort are moving from settings people pick to decisions made per call. Protocols are going stateless so they can scale. And agentic skill is increasingly trained in environments that look exactly like your eval harness. Weeks 7, 8, 9, 12, 15, 16 and 17 exist because of these trends.

**Proof of work.**

- Keep rig in a public repository from Week 1, with its eval sets (minus anything you can't redistribute).
- Publish a write-up after Weeks 5, 7, 13 and 18, each built around one measured result. For example: "BM25 against grep on a real codebase" (Week 4), "What a KV cache saves, measured" (Weeks 6 and 7), "A tool ledger that survives 50 `kill -9`s" (Week 15), "Replaying the Comet attack against my own agent" (Week 16).
- Contribute upstream to what you read: a rig harness for search_evals, fixes or docs in pi, mini-swe-agent or pipecat, an environment for verifiers.
- For a company rather than a job: the three graduation projects copy incumbents, and a copy is not a company. A company needs a specific user, a workflow they repeat, and data or distribution others lack. Use the specialty you picked in Week 9 to find one, and talk to ten prospective users before Week 18.
