# AGENTS.md — working on this repo

This repo is the content and build tooling for "Agents from First Principles," an
18-week self-study plan (hosted at https://ai.labs-nature.com/study-plan/). It is
not the `rig` project the plan has the reader build — that lives in a separate repo.

Read `GUIDELINES.md` too. It's the distilled, portable lessons from building and
repeatedly iterating on this site — markdown-dialect pitfalls, why a text diff never
proves a page renders, the hash-routing gotcha below, and how content work here has
been safely parallelized across agents. It's written to also be useful if you copy it
into an unrelated project.

- `content/*.md` is the source of truth: one markdown file per page (`w1.md`..`w18.md`,
  `path.md`, `primitives.md`, `rig.md`, `app-a.md`..`app-e.md`), plus `content/manifest.json`
  for titles/groups/week metadata.
- `index.html` is **generated** — never hand-edit it. After editing a file under
  `content/`, run `python3 tools/build.py` to regenerate it.
- `tools/mdx.py` is a small, dependency-free markdown↔HTML engine matching exactly the
  markup `index.html`'s JS app expects (see its docstring for the dialect: `##`/`###`
  headings with `{#id}` anchors — `###` nests under the preceding `##` in the page's
  "On this page" outline — `<!-- tasks:CAT -->` checklist blocks, ```raw-html```
  passthrough). It supports exactly this subset, not full CommonMark; check it before
  assuming a markdown feature works.
- `tools/export.py` regenerates `templates/study-plan.md`, a single clean markdown file
  with the same content, meant for pointing an AI assistant at the whole plan at once.
  It's the sibling file `templates/AGENTS.md` refers to — see that file for the actual
  student-facing integration, and re-run this export whenever `content/*.md` changes.
- `tools/extract.py` was the one-time script that split the original monolithic
  `index.html` into `content/*.md`; there's no need to run it again.
- `tools/lint.sh` lints and formats the Python tooling (`tools/*.py`, `serve.py`)
  with `ruff`, configured in `pyproject.toml`. Run `tools/lint.sh` to check,
  `tools/lint.sh --fix` to apply fixes and reformat. It deliberately does not
  touch `content/*.md` — see the dialect note above; a generic formatter would
  corrupt the custom markdown syntax.

**Week pages have a fixed format** — objective and target layout with "how it fits together"
pseudocode first, then prescriptive day-by-day steps with pinned code references inline. Follow
`GUIDELINES.md` §10 for every edit to `content/w*.md`, and use `content/w2.md` as the model.

Checklist `data-id`s (e.g. `w1.check.3`) are assigned by position within a task list and
are what a reader's ticked-checkbox progress is keyed on. Don't reorder or delete existing
task lines in a week file — append new ones at the end instead — or a reader's saved
progress silently detaches from a different task.

After any content change: run `python3 tools/build.py && python3 tools/export.py`, then
sanity-check `index.html` actually renders (a JSON/text diff is not enough — the app's JS
can fail silently and leave the page blank; load it in a real or headless browser).

When checking a specific page in a real or headless browser, the hash route is the bare
page id — `#w9`, not `#/w9`. The leading-slash form silently falls back to the home page,
and since every page's content is embedded inline as JSON for client-side routing, a
`grep` over the full dumped DOM will still find matching text regardless — so that mistake
doesn't even look like a failure. Confirm routing with a structural check (e.g. the active
nav button has `aria-current="page"`), not substring presence. See `GUIDELINES.md` §3–4.
