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

## 10. Every week page follows one format: orient in one screen, then typed blocks

The first fix (one top-down shape per week, references pulled into the step that needs them)
solved the scrolling problem but left about 33,000 words in one visual register: nothing told
the eye what to read first, what to do, or what mattered. The redesign keeps every word and
changes the shape: each week opens with a hero that answers what, why and how long, and every
section below it is one typed block in the same order on all 18 weeks. The source of these
rules is the **Study Site Redesign Spec**; `content/w3.md` is the canonical converted week
(the pilot) and `#_components` shows every component. Weeks not yet converted keep the older
shape (intro, pinning note, Concepts, objective and layout, day by day, then the reference
sections) until the roll-out reaches them; the template renders both.

Order of sections in a converted `wN.md`:

0. **Hero** — a `::: hero` block: `- Lead:` (the intro's first sentence) and 3 to 5
   `- Outcome:` lines condensed from the Checkpoint items. Time (summed from the day timeline)
   and Ships (the Project increment's first sentence) are derived by `tools/build.py`; a field
   that can't be derived shows a TODO chip, never a guess.
1. **Key idea** (`{#wN-key-idea}`) — the rest of the intro paragraph in a `key-idea` block,
   plus the week's diagram.
2. **Concepts** — one `{.concept title=".."}` card per idea: the bold term is the title, the first
   sentence the definition, everything else in a `details` disclosure whose summary names it.
3. **Build** — the checkable steps (`{.tasks cat="build"}`), then the old long-form sections as
   collapsible sub-sections (`{.sub}`), in this order: **Day by day** as a timeline (one
   `{.day}` per day: Time, Do, Working by end of day visible; Goal, Why, steps, tests and Done
   when in its disclosure), then **This week's objective and target layout** (objective, what
   changes, folder tree, how it fits together, why). Both keep their old heading ids.
4. **Project increment** — lead = its first sentence; the rest as `increment` fields.
5. **Read** — a pinned-commits block, then one `{.read title=.. commit=..}` card per source:
   files in reading order visible, function-and-line listings in a disclosure.
6. **Experiments** — `{.tasks cat="exp"}`, each step with Change / Measure / Expect, using only
   what the item states.
7. **You should be able to answer** — `{.tasks cat="q"}`, questions verbatim.
8. **Production lens** — a `production` block: titles visible, bodies collapsed.
9. **Not yet** — a `scope` block, one comma-separated line.
10. **Checkpoint** — `{.tasks cat="check"}`; renders as the filled exit-gate panel.

Rules that apply throughout:

- **Pin every code link to a commit** (`/blob/<sha>/path#L10-L42`), and check the lines against a
  checkout of that commit before shipping. Branch links drift; pinned links never do.
- **Be prescriptive and say why.** Name the file, the function, the data structure; when there's a
  real choice, make it and give the reason in one clause ("take tool arguments from the final
  message — parsing partial JSON buys nothing here").
- **Steps state what each file is *for*,** not only where its reference lives (§7).
- **No same-page `#id` links** (§3) — refer to other sections by **bold name**.
- **Restructure, never change meaning.** Move words into the right component and split long
  sentences; copy numbers, versions, hashes, prices, names and URLs character for character. If a
  split would change meaning, keep the original sentence intact in Details.
- **Task ids never move** (§2): a step's position inside its `.tasks` block is its id. You may
  rewrite an item into a short title plus fields; you may not reorder, insert or delete items.
  Write the expected id on each step (`id="w3.build.4"`) so the build fails if one shifts.
- **Don't teach later weeks early.** A day may point forward ("Week 9 revisits this"), never build it.

## 11. The design system: tokens, components, and how to check a page

The site is assembled from a small component library; no page styles content ad hoc.

- **Tokens only.** Every colour, size and space in `tools/template.html` comes from the `:root`
  token blocks (light, dark under `prefers-color-scheme`, and dark again under
  `[data-theme="dark"]`). No hex value outside them.
- **Colour carries meaning, and only one meaning.** Six hues mark kinds of content: blue concept
  (and production notes), green build (and the project increment), violet experiment, amber
  check (self-check, checkpoint), slate read (and not yet), red pitfall. Teal is the accent:
  links, buttons, focus, progress and the current location, never a content kind. The four
  phases are steps of the teal ramp and fill bars and bands only, never text.
- **Never colour alone.** Every block has an icon and a text label; progress states are shapes
  (hollow, half, filled with a check, ring for the current page), so everything reads in greyscale.
- **Only three blocks are filled:** the key idea, pitfalls, and the checkpoint panel. Everything
  else is a white card with a coloured left rule, so a page never turns into a rainbow.
- **Short visible layer, detail on demand.** Paragraphs at most 3 sentences and 60 words; visible
  bullets at most 20 words; checkable titles at most 12 words; every section opens with a lead
  sentence of at most 25 words. Detail goes into a native `<details>` whose summary says what is
  inside ("How serving engines store it", never "More"). Search opens the disclosure that holds
  a match.
- **Draw structure.** An order, a flow or a layering with 3 or more parts is an inline SVG with
  `role="img"`, an `aria-label` stating the takeaway, and a caption repeating it. Draw with the
  `dg-*` classes so figures follow the theme; keep them within 720 px (560 px minimum, scrolling
  inside the figure).
- **Links to a block** use `#page/anchor` (for example `#w3/c-w3-build-6-b`); a bare `#page` still
  works, and the router never treats the part after the slash as a page.

Check a page with the browser, not a diff (§4). For a converted week, run the spec's lint
snippet in the console and compare with the page's own baseline: visible words at most half,
no visible chunk over 60 words, at most 3 inline code spans per 100 visible words, at least one
diagram, no section without a lead. Then a fidelity diff (every task id, URL, commit hash, repo
name and number from before still present), axe-core with zero serious issues in both themes, no
horizontal scroll from 320 px up, and a saved progress state that shows identically before and
after.
