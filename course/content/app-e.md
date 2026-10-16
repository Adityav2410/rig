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
