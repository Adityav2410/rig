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
