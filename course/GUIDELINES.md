# Guidelines for building and iterating on interactive course sites

These are lessons learned while building and repeatedly editing this project
(a single-page, deterministically-built study plan site driven by a small
custom markdown engine). They're written to be useful in **this repo** and
**portable to a new one** — copy this file to a fresh project and strip the
repo-specific bits (file names, the `{#wN-...}` id scheme) if you're starting
something similar from scratch.

## 1. Know your markdown engine's actual dialect before writing against it

If a project uses a small custom markdown→HTML engine instead of a full
CommonMark library (as this one does, in `tools/mdx.py`), it almost never
supports everything standard markdown does. Read the engine's docstring and
source *before* writing content that assumes a feature it doesn't have.

- Here, only `##` and `###` headings with explicit `{#id}` anchors are
  supported — arbitrary nesting, auto-generated ids, and setext headings
  are not. Before H3 existed, every sub-structure had to be a bold lead-in
  paragraph instead.
- If you extend the dialect (we added H3 support), update **every**
  direction the engine supports, not just the one you need today. This
  engine is bidirectional (`md_to_html` / `html_to_md`); leaving the reverse
  direction broken "because it's only used once" is a trap for whoever
  touches it next, and it rotted silently until checked.
- Document a new dialect feature in the engine's own docstring immediately,
  not just in your head.

## 2. Stateful, position-keyed data embedded in content is a landmine

This site tracks a reader's checked/unchecked progress by the **position**
of each checklist item within its list, not by its text. That means:

- Never reorder, reword-into-a-different-item, insert-in-the-middle, or
  delete an existing checklist line once it might have been checked by a
  real reader. Append new items at the end only. State this rule loudly in
  the repo's `AGENTS.md`/`CLAUDE.md` so it survives context resets.
- Before any bulk or automated edit near such lists — especially when
  dispatching several agents in parallel — snapshot the exact list content
  first (not just a diff of the whole file, since line numbers shift when
  you insert content above them) and diff the *content*, ignoring line
  numbers, after every agent returns. Don't trust a summary that says
  "I didn't touch the checklist" — verify it.

## 3. Single-page apps with hash-based routing break plain anchor links

If the app uses `location.hash` to choose which top-level page to show (as
this one does), a plain markdown link to a heading on the *same* page
(`[text](#some-id)`) gets misread as "navigate to a different top-level
route," fails to match, and silently falls back to a default page. Two
consequences:

- In content, reference another section by its **bold name** in prose
  ("see **Build** below"), never as a clickable `#id` link — unless the
  app's own TOC-generation code specifically intercepts that link (it does
  here, via a `data-to` attribute and a click handler that calls
  `scrollIntoView`, but that only applies to links the renderer itself
  generates, not to ones written by hand in markdown).
- When writing automated browser checks against such an app, nail the exact
  hash format the app actually uses (test it once, deliberately, by
  checking a structural marker like `aria-current="page"`) before trusting
  any check built on it. A wrong format can silently render the wrong page
  while a naive `grep`/`dump-dom` check still reports success for unrelated
  reasons (see next point) — this happened mid-session here and quietly
  invalidated several earlier "verified live" claims until caught.

## 4. A text diff or a successful build is not proof the page renders

- A build script completing without error, or a generated file's bytes
  matching expectations, does not prove the client-side JS actually
  executes correctly — it can fail silently and leave a blank page. Always
  load the real, rendered output (headless browser or otherwise) and check
  actual DOM structure after any change that touches the app's JS, CSS, or
  the shape of its data.
- If the app embeds **all** content inline as one JSON blob for client-side
  routing (common for small SPAs like this one), a `grep`/text-search over
  the full page source will find a string regardless of which page is
  currently "active," because the inert JSON blob contains every page's
  content all the time. That is not evidence of correct rendering. Scope
  checks to the actually-rendered container (e.g. `#main`'s innerHTML), and
  confirm routing succeeded via a structural marker, not substring presence.
- When a verification method is new or you're not fully sure what it's
  actually testing, run one deliberate control case first (a known-wrong
  input that should fail the check) before trusting it across many checks.

## 5. Never guess a URL that "looks plausible"

Verify every non-trivial external link (API docs, especially) with a real
fetch before shipping it. A wrong-but-plausible link wastes more of a
reader's time than no link at all — this was the very first problem that
motivated restructuring this project in the first place. If you catch
yourself typing a URL from memory, verify it immediately, even mid-task.

## 6. Scaling content work across many files with parallel agents

When the same transformation needs to land across many independent files
(here: adding a day-by-day section to 17 week files):

1. Do one file by hand first as the canonical pattern. Don't delegate the
   pattern design itself — delegate replication of an already-correct
   example.
2. Snapshot any positionally-sensitive content (see §2) across every target
   file *before* dispatching anything.
3. Give every agent the same full, self-contained context: the pattern file
   to study, the exact dialect constraints (§1, §3), and an explicit list of
   things to never touch. Agents start with zero memory of this
   conversation — nothing can be assumed.
4. Verify each agent's output against the snapshot as results come back,
   not only after the last one finishes, so a problem in one batch doesn't
   block noticing it in an earlier one.
5. Group files into agents along natural content boundaries (here: thematic
   phases, e.g. weeks 2–5) so each agent's output stays internally
   consistent in voice and pacing, rather than splitting arbitrarily.

## 7. Writing day-by-day / step-by-step pedagogical content

- Every actionable unit (a day, a step) should open with two or three
  sentences of *why* before the *how* — what's being built today and how it
  fits the larger arc — not just a bare numbered task list. This was the
  single most common piece of feedback across this project's iteration.
- Point to existing reference material by name rather than duplicating it
  inline; two copies of the same spec will drift.
- Keep a default rhythm/template for pacing (here: a weekly cadence from
  `path.md`) but adapt it per unit rather than mechanically forcing every
  unit into an identical shape — some days legitimately have no new
  building to do ("no new code today, you're reading/tracing/reviewing").
- **Every step that names a file or module to build must say, in the step
  itself, what that thing is *for* — not just where its reference code or
  contract lives.** "Write `rig/llm.py` from **Starter code** below" tells a
  reader where to copy from; "Write `rig/llm.py`: the only thing in the
  codebase that talks to the network — one request in, one parsed response
  out" tells them what they're actually building, so they can attempt it
  from the description alone and only check the reference code afterward,
  instead of reverse-engineering the provided code to infer its own intent.
  This is cheap (one clause) and was the single clearest piece of feedback
  on this project's day-by-day sections once they existed: a list of files
  to create, without each one's job stated, reads like a shopping list, not
  a lesson.
- **Every code/starter-code block needs a 1-2 line intro stating what it
  does, not just a filename label.** "The two tools with real engineering
  in them:" followed by code makes a reader reverse-engineer the point from
  the implementation. Say what each thing is *for* first — "`resolve` is
  the path jail: the one piece of code standing between a model-supplied
  path and the host filesystem outside the sandbox" — then show the code as
  confirmation, not as the only source of explanation.
- **Any parameter or object threaded through many functions must be defined
  in prose the first time it appears, not left to be inferred from its call
  sites.** A signature like `fn(ws, **args)` or `resolve(ws, rel)` is opaque
  on first read if `ws` was never introduced — the reader has to guess from
  usage (`ws.root`, `ws.exec_prefix`) what it actually is. State it once,
  plainly, at its first appearance ("`ws` is the workspace object for this
  run — it holds X, Y, Z") and later mentions can rely on that.
- **Prose alone is not enough for an object other code depends on — if other
  starter code uses its attributes, it needs its own starter-code block too,
  and that block must come *before* the first code that uses it, not after.**
  This project shipped exactly this bug once: `workspace.py` was described in
  prose ("today it's just a small object holding `root` and `name`") but
  never given a code skeleton anywhere, while `loop.py`, `fs.py`, and
  `shell.py`'s starter code all used `ws.root`, `ws.name`, and
  `ws.exec_prefix` as if the class already existed. Worse, the one sentence
  that *did* define `ws.exec_prefix`'s value sat *after* the `shell.py` code
  block that used it — so a reader hit the usage before the definition even
  in the one place it existed. The fix is to give every pervasively-used
  object the same treatment as the project's other starter-code modules
  (e.g. this project's `trace.py`/`budget.py`, which get full skeletons
  "so `loop.py` doesn't change shape later"): a minimal code block, placed
  immediately before the first code block that calls any of its attributes
  or methods, and a second block later (same pattern) when a day's work adds
  new attributes to it (here: `exec_prefix` arriving Wednesday). Before
  shipping any such content, grep for the object's name across the whole
  page and confirm every attribute/method access is preceded — not
  followed — by code or prose that defines it.

## 8. Teaching concretely vs. generically

When a tutorial's subject matter spans multiple real-world
systems/providers/vendors: teach the first, foundational mechanics against
**one** concrete system (so the learner sees real bytes/output, not an
abstraction), but make the vocabulary and concepts explicitly
system-neutral with an inline mapping table to the alternative(s) — don't
force full abstraction before the learner has built anything real, but
don't silently assume one vendor everywhere else in the material either.

## 9. Fix small, concrete gaps the moment you notice them

Several real improvements in this project came from noticing something
small and wrong while working on something else (a missing prerequisite
link, an undefined module referenced by name but never specified, a
diagram that only renders in one output format) rather than from a planned
audit. Keep that habit: when asked to do a scoped task, it's worth a brief,
bounded look for adjacent rot — but keep it bounded, and say plainly what
you checked and what you didn't, rather than implying an exhaustive audit
happened when it didn't.
