# Agents from First Principles: local study site

    python3 serve.py

Open http://localhost:8765. Ticks, notes and the last page you visited are written to
`progress.json` in this folder on every change (the previous save is kept as
`progress.json.bak`). Close the browser or restart the machine and it all comes back.

- Other devices on your network: `python3 serve.py --host 0.0.0.0`, then open
  `http://<this-machine>:8765`. Put it behind your reverse proxy with auth if it leaves your LAN.
- Back up or sync: commit `progress.json` to git, or keep this folder in a synced directory.
- Docker: `docker run -d --name rig-study -p 8765:8765 -v "$PWD":/app -w /app --restart unless-stopped python:3.12-slim python serve.py --host 0.0.0.0`
- Opening `index.html` directly (file://) also works, but progress then lives only in that
  browser's storage.

## Editing the plan

`index.html` is generated — don't hand-edit it. Content lives in `content/*.md`, one file
per page (`w1.md`..`w18.md` for weeks, plus `path.md`, `primitives.md`, `rig.md` and the
appendices), with page titles/groups/metadata in `content/manifest.json`.

See `GUIDELINES.md` for the hard-won lessons behind the rules below — markdown-dialect
pitfalls, why a build succeeding doesn't mean a page renders, and how content changes here
have been safely scaled across many files at once. It's written to be useful outside this
repo too.

1. Edit the relevant markdown file.
2. Run `python3 tools/build.py` to regenerate `index.html`.

The build is a plain, deterministic Python script (`tools/mdx.py` + `tools/build.py`,
stdlib only) — no LLM calls, so iterating on wording doesn't cost tokens or risk touching
unrelated content. Markdown dialect notes:

- Heading ids are explicit: `## Concepts {#w1-concepts}`. `###` is also supported and
  nests under the preceding `##` in the page's "On this page" outline (used for each
  week's day-by-day sub-links, e.g. `### Monday — ... {#w1-day-by-day-mon}`). Keep
  existing ids stable — they're also used for in-page navigation links.
- Checklists that back the progress tracker use a directive comment plus a task list:
  ```
  <!-- tasks:check -->
  - [ ] Checkpoint item text
  ```
  Categories are `check`, `exp`, `q` (renders as "I can answer this") and `build`.
  `data-id`s (`w1.check.1`, ...) are assigned by position within the list — **don't
  reorder or delete existing task lines** once someone may have ticked them, or their
  progress silently detaches from a different task. Appending new items at the end is safe.
- Fenced ```` ```lang ```` blocks render as code; ```` ```raw-html ```` passes its contents
  through untouched (used for the two hand-drawn diagrams in `primitives.md`/`rig.md`).
- `tools/extract.py` is the one-time script that originally split the old monolithic
  `index.html` into these markdown files; there's no need to run it again.

## Using this plan from an AI coding assistant

Run `python3 tools/export.py` to regenerate `templates/study-plan.md` — a single clean
markdown file with the whole plan, meant to be read by (not just about) an assistant.

If you're building `rig` in a separate repo and want Claude Code, Codex, or similar to
answer questions and clarify doubts grounded in the plan while you work: copy both
`templates/AGENTS.md` and `templates/study-plan.md` into that repo's root (as a pair —
`AGENTS.md` refers to `study-plan.md` only by "the file next to this one," so the two
stay portable together regardless of where either repo lives). Codex and Claude Code
pick up `AGENTS.md` from a repo root automatically. See that file for what it does
(reads the current week's section before answering, gives hints rather than full
solutions on build/checkpoint items, verifies doc links instead of guessing them).
