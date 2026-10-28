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
