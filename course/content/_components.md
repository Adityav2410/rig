This page is the component library from the redesign spec, rendered by the same build as every other page. It is not in the index, search or progress totals; open it at `#_components`. The examples reuse Week 3 content.

## Key idea {#cx-key-idea}

::: lead
Every section opens with a one-sentence takeaway in this style.
:::

::: key-idea
Context engineering is one decision made before every request: which bytes go in, in what order.
:::

## Concepts {#cx-concepts}

::: lead
Concept cards: the term, a one-line definition, then detail behind a disclosure.
:::

::: {.concept title="The KV cache"}
Attention keys and values are computed once per token and reused only for an identical prefix.

::: {.details summary="How serving engines store it"}
SGLang keeps them in a radix tree; vLLM uses hash-chained blocks.
:::
:::

::: {.concept title="Cache economics"}
The TTL is a bet on how soon the next request arrives.

::: {.stats label="Anthropic prompt cache prices, relative to base input"}
- 1.25x | 5-minute cache write
- 2x | 1-hour cache write
- 0.1x | Cache read
- 4 | Breakpoints per request
:::

::: {.details summary="When each TTL pays for itself"}
A 5-minute entry pays for itself on its first reuse; a 1-hour entry needs two.
:::
:::

::: pitfall
A timestamp at the top of the system prompt changes the first bytes of every request, so nothing after it is ever read from cache.
:::

## Build {#cx-build}

::: lead
Build steps: a verb-first title, then Files and Done when; the method sits in Details.
:::

::: {.tasks cat="build"}
::: {.step title="Record token usage per segment in the trace"}
- Files: `rig/context.py`
- Done when: The eval report shows `peak_input_tokens` and `cache_read_ratio`.

::: details
Estimate each segment before the request; after it, record the provider's `usage` per segment.
:::
:::
::: {.step title="Compact history past 70% of the window"}
- Trigger: 70% of the window, or a context-overflow error (then one retry)
- Method: the cheap model summarizes everything before the latest safe cut point
- Template: task · decisions · files touched with what changed · current state · next step
- Keep: the last few turns verbatim
- Store: a `compaction` entry in the session log; never delete the originals
:::
- [ ] A plain one-line task renders as a step too.
:::

::: {.sub id="cx-day-by-day" title="Day by day" hint="Seven days, one line each; open a day for its steps"}
::: timeline
::: {.day label="Mon"}
#### Monday — the KV cache, before the billing feature. {#cx-day-mon}

- Time: 1 to 1.5 h
- Do: Concepts and the caching docs; the economics in your own numbers

::: {.details summary="Monday's steps"}
1. Read **Concepts** above, twice through the caching bullets.
2. Write the half-page note.
:::
:::
::: {.day label="Tue"}
#### Tuesday — the context pipeline every request runs through. {#cx-day-tue}

- Time: 3 to 4 h
- Do: Build steps 1 to 4
:::
:::
:::

```python file=rig/shrink.py
def latest_safe_cut(messages, keep_tail_tokens):
    budget, i = keep_tail_tokens, len(messages)
    while i > 0 and budget > 0:                         # walk back until the tail is big enough
        i -= 1; budget -= est(messages[i])
    return None
```

| Segment | Tokens | Cached |
|---|---|---|
| Tools | 1,820 | yes |
| System | 2,410 | yes |
| History | 31,004 | partly |

## Project increment {#cx-project-increment}

::: increment
rig v0.3 handles long tasks.
:::

## Read {#cx-read}

::: lead
Read cards: the repo, its pinned commit, the files in reading order.
:::

::: {.read title="sgl-project/sglang" commit="b068417" href="https://github.com/sgl-project/sglang"}
The data structure behind prefix reuse.

1. `match_prefix` (L364)
2. `insert` (L428)
3. `evict` (L552)
:::

## Experiments {#cx-experiments}

::: lead
Experiment cards: Change, Measure, Expect.
:::

::: {.tasks cat="exp"}
::: {.step title="Caching on versus off across the eval set"}
- Change: caching on, then off
- Measure: cache-read ratio, dollars per task, latency
:::
:::

## You should be able to answer {#cx-you-should-be-able-to-answer}

::: lead
Self-check cards: the question is the title; ticking means you can answer it.
:::

::: {.tasks cat="q"}
- [ ] Why keep a verbatim tail instead of summarizing everything?
:::

## Production lens {#cx-production-lens}

::: lead
Production notes: titles shown, bodies collapsed.
:::

::: production
- **Context overflow is a typed, recoverable error** with exactly one retry after compaction, never a loop.
- **Idempotency:** a retried turn must not compact twice.
:::

## Not yet {#cx-not-yet}

::: lead
Out of scope: one dashed line.
:::

::: scope
Vector-store memory products, knowledge-graph memory, "infinite context" claims.
:::

## Checkpoint {#cx-checkpoint}

::: lead
The week's exit gate: a filled panel.
:::

::: {.tasks cat="check"}
- [ ] From any trace you can say which part of each request was served from cache and why each miss happened.
:::
