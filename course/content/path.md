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
