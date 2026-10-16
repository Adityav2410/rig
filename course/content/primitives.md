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

```raw-html
<figure class="diagram"><svg aria-label="Each term is a layer wrapped around a stateless model" font-size="13" role="img" viewbox="0 0 760 340"><text data-claude-text-id="title" fill="var(--cds-text-primary)" font-size="15" font-weight="600" x="24" y="30">Each term is a layer wrapped around a stateless model</text><g data-claude-anchor="workflow-engine"><rect fill="none" height="264" rx="8" stroke="var(--cds-chart-axis)" stroke-dasharray="5 4" stroke-width="1.25" width="712" x="24" y="48"></rect><text data-claude-text-id="wf-name" fill="var(--cds-text-primary)" font-weight="600" x="40" y="69">Workflow engine (optional)</text><text data-claude-text-id="wf-desc" fill="var(--cds-text-secondary)" font-size="11.5" text-anchor="end" x="720" y="69">code chooses the next step; steps are durable</text></g><g data-claude-anchor="harness"><rect fill="none" height="212" rx="8" stroke="var(--cds-chart-axis)" stroke-dasharray="none" stroke-width="1.25" width="680" x="40" y="84"></rect><text data-claude-text-id="h-name" fill="var(--cds-text-primary)" font-weight="600" x="56" y="105">Harness</text><text data-claude-text-id="h-desc" fill="var(--cds-text-secondary)" font-size="11.5" text-anchor="end" x="704" y="105">prompt, tools, context, permissions, UI</text></g><g data-claude-anchor="runtime"><rect fill="none" height="160" rx="8" stroke="var(--cds-chart-axis)" stroke-dasharray="none" stroke-width="1.25" width="648" x="56" y="120"></rect><text data-claude-text-id="rt-name" fill="var(--cds-text-primary)" font-weight="600" x="72" y="141">Runtime</text><text data-claude-text-id="rt-desc" fill="var(--cds-text-secondary)" font-size="11.5" text-anchor="end" x="688" y="141">events, cancellation, retries, persistence</text></g><g data-claude-anchor="agent-loop"><rect fill="none" height="108" rx="8" stroke="var(--cds-chart-axis)" stroke-dasharray="none" stroke-width="1.25" width="616" x="72" y="156"></rect><text data-claude-text-id="loop-name" fill="var(--cds-text-primary)" font-weight="600" x="88" y="177">Agent loop</text><text data-claude-text-id="loop-desc" fill="var(--cds-text-secondary)" font-size="11.5" text-anchor="end" x="672" y="177">call the model, run its tools, repeat until it asks for none</text></g><g data-claude-anchor="llm"><rect fill="var(--cds-chart-categorical-1)" fill-opacity="0.12" height="56" rx="8" stroke="var(--cds-chart-categorical-1)" stroke-width="2" width="284" x="88" y="192"></rect><text data-claude-text-id="llm-name" fill="var(--cds-text-primary)" font-weight="600" text-anchor="middle" x="230" y="214">LLM</text><text data-claude-text-id="llm-desc" fill="var(--cds-text-primary)" font-size="11.5" text-anchor="middle" x="230" y="234">stateless: messages in, one message out</text></g><g data-claude-anchor="tool-calling"><rect fill="none" height="56" rx="8" stroke="var(--cds-chart-axis)" stroke-width="1.25" width="284" x="388" y="192"></rect><text data-claude-text-id="tc-name" fill="var(--cds-text-primary)" font-weight="600" text-anchor="middle" x="530" y="214">Tool calling</text><text data-claude-text-id="tc-desc" fill="var(--cds-text-secondary)" font-size="11.5" text-anchor="middle" x="530" y="234">an id-correlated RPC inside the transcript</text></g></svg><figcaption>The vocabulary as nested layers</figcaption></figure>
```

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
