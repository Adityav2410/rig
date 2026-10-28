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
