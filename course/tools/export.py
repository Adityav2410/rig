#!/usr/bin/env python3
"""Build a single portable markdown file from content/*.md, for pasting into
or pointing any AI assistant (Claude Code, Codex, ChatGPT, ...) at the whole
plan at once. Deterministic, no LLM calls.

    python3 tools/export.py

Writes templates/study-plan.md — the sibling file templates/AGENTS.md refers to
by relative path, so the two travel together wherever they're copied. Re-run
after editing content/*.md.
"""

import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent

_TASKS_DIRECTIVE_RE = re.compile(r'^<!--\s*tasks:\w+\s*-->\n', re.MULTILINE)
_HEADING_ID_RE = re.compile(r'^(#+ .*?)\s*\{#[a-z0-9-]+\}\s*$', re.MULTILINE)
_RAW_HTML_FENCE_RE = re.compile(r'```raw-html\n(.*?)\n```\n?', re.DOTALL)
_FIGCAPTION_RE = re.compile(r'<figcaption>(.*?)</figcaption>')
PLAN_URL = 'https://ai.labs-nature.com/study-plan/'


def _describe_diagram(m, page_id):
    """A raw-html block is a hand-drawn SVG the site renders live. In a flat
    markdown file there's no generic way to render it: a fenced code block
    (even relabeled ```html) shows as literal SVG markup in any previewer,
    and it's pure coordinate noise to an LLM. Swap it for the figure's own
    caption plus a link to the real, rendered diagram."""
    cap = _FIGCAPTION_RE.search(m.group(1))
    caption = cap.group(1) if cap else 'diagram'
    return '*Diagram — %s. Rendered version: %s#/%s*\n' % (caption, PLAN_URL, page_id)


def clean(md_text, page_id):
    """Strip the build-only markdown dialect bits that generic markdown
    viewers and plain-text readers (including an LLM) don't need: the
    `<!-- tasks:CAT -->` directive, `{#id}` heading anchors, and the raw-SVG
    diagram fences (replaced with their caption and a link to the live page)."""
    text = _TASKS_DIRECTIVE_RE.sub('', md_text)
    text = _HEADING_ID_RE.sub(r'\1', text)
    text = _RAW_HTML_FENCE_RE.sub(lambda m: _describe_diagram(m, page_id), text)
    return text.strip()


def build():
    content_dir = ROOT / 'content'
    manifest = json.loads((content_dir / 'manifest.json').read_text())

    out = [
        '# Agents from First Principles — full study plan\n',
        "This is the complete 18-week self-study plan for building `rig`, a personal "
        "agent runtime, from first principles. Generated from `content/*.md` by "
        "`tools/export.py` — edit the source week file and re-run the export instead "
        "of editing this file.\n",
        '## Contents\n',
    ]
    out += ['- %s' % entry['title'] for entry in manifest]
    out.append('')

    for entry in manifest:
        pid = entry['id']
        md_text = (content_dir / (pid + '.md')).read_text()
        out.append('\n---\n')
        out.append('# %s\n' % entry['title'])
        if 'meta' in entry:
            m = entry['meta']
            out.append('*Phase: %s · Primary reading/code: %s*\n' % (m['phase'], m['code']))
        out.append(clean(md_text, pid))

    text = '\n'.join(out).rstrip() + '\n'
    out_path = ROOT / 'templates' / 'study-plan.md'
    out_path.write_text(text)
    print('wrote %s (%d pages, %d bytes)' % (out_path.relative_to(ROOT), len(manifest), len(text)))


if __name__ == '__main__':
    build()
