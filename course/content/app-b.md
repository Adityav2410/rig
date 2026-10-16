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
