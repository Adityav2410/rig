#!/usr/bin/env python3
"""Regenerate index.html from content/*.md. Pure Python stdlib, no LLM calls.

    python3 tools/build.py

Run this after editing any file under content/. It is deterministic: same
markdown in, same index.html out, every time.

Besides each page's html, the build derives what the week hero and the home page
show, from the page's own text and never invented:

- Time: the sum of the day-by-day Time column ("1 to 1.5 h" + ...), from the table or the
  timeline's `- Time:` fields.
- Ships: the first sentence of the Project increment section.
- Lead: the first sentence of the week intro.
- Outcomes ("You will be able to"): only from a `::: hero` block in the source; a week
  without one gets a TODO, which the app shows as a visible chip.

A `::: hero` block overrides any derived field. Every TODO is printed at the end of
the build so it can go into the redesign report.
"""

import html as _html
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'tools'))
import mdx  # noqa: E402

PLACEHOLDER = 'const DATA = /*__RIG_DATA__*/;'
DATA_PREFIX = 'const DATA = '
SPRITE_PLACEHOLDER = '<!--__ICON_SPRITE__-->'
HIDDEN_PAGES = ['_components']  # rendered for review, absent from the index, search and totals

_DAY_ROW_RE = re.compile(r'^\|\s*(Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s*\|\s*([^|]+?)\s*\|', re.M)
_DAY_FIELD_RE = re.compile(r'^::: \{\.day label="(\w+)"\}\n(?:.*\n)*?- Time: (.+)$', re.M)
_HOURS_RE = re.compile(r'^(\d+(?:\.\d+)?)(?:\s*(?:to|–|-)\s*(\d+(?:\.\d+)?))?\s*h$')


def week_time(md_text):
    """Sum the day table's Time column into 'low to high h'; None if any cell won't parse."""
    lo = hi = 0.0
    rows = _DAY_ROW_RE.findall(md_text) or _DAY_FIELD_RE.findall(md_text)
    if not rows:
        return None
    for _day, cell in rows:
        m = _HOURS_RE.match(cell.strip())
        if not m:
            return None
        a = float(m.group(1))
        b = float(m.group(2) or a)
        lo, hi = lo + a, hi + b
    fmt = lambda x: '%g' % x  # noqa: E731
    return '%s to %s h' % (fmt(lo), fmt(hi)) if lo != hi else '%s h' % fmt(lo)


def first_sentence(text):
    text = ' '.join(text.split())
    m = re.match(r'^(.+?[.!?])(?:\s|$)', text)
    return m.group(1) if m else text


def section_text(html, suffix):
    m = re.search(r'<section [^>]*data-sec="%s".*?</h2>(.*?)</section>' % re.escape(suffix), html, re.S)
    return mdx.compute_text(m.group(1)) if m else ''


def intro_text(html):
    m = re.search(r'<div class="week-intro">(.*?)</div>', html, re.S)
    return mdx.compute_text(m.group(1)) if m else ''


def glossary(md_text):
    terms = []
    for line in md_text.splitlines():
        cells = [c.strip() for c in line.strip().strip('|').split('|')]
        if len(cells) == 3 and line.startswith('|') and cells[0] not in ('Term', '---') and not cells[0].startswith('-'):
            plain = [mdx.compute_text(mdx.inline_md_to_html(c)) for c in cells[:2]]
            terms.append(plain)
    return terms


def build():
    content_dir = ROOT / 'content'
    manifest = json.loads((content_dir / 'manifest.json').read_text())
    hidden = {'group': 'Hidden', 'title': 'Component library', 'short': 'Components', 'hidden': True}
    entries = manifest + [dict(hidden, id=pid) for pid in HIDDEN_PAGES]

    pages, meta, todos = [], {}, []
    for entry in entries:
        pid = entry['id']
        md_text = (content_dir / (pid + '.md')).read_text()
        html, extras = mdx.md_to_page(md_text, pid)
        page = {
            'id': pid,
            'group': entry['group'],
            'title': entry['title'],
            'short': entry['short'],
            'html': html,
            'toc': mdx.compute_toc(html),
            'text': mdx.compute_text(html),
            'tasks': mdx.compute_tasks(html),
        }
        if entry.get('hidden'):
            page['hidden'] = True
        if 'meta' in entry:
            m = dict(entry['meta'])
            hero = extras.get('hero', {})
            m['lead'] = hero.get('lead') or _html.escape(first_sentence(intro_text(html)))
            m['time'] = hero.get('time') or week_time(md_text)
            m['ships'] = hero.get('ships') or _html.escape(first_sentence(section_text(html, 'project-increment')))
            m['outcomes'] = hero.get('outcomes', [])
            for field in ('time', 'ships', 'outcomes'):
                if not m[field]:
                    todos.append('%s: %s' % (pid, field))
            meta[pid] = m
        else:
            page['lead'] = _html.escape(first_sentence(page['text']))
        pages.append(page)

    weeks = sorted(meta.values(), key=lambda m: m['n'])
    phases = []
    for w in weeks:
        if phases and phases[-1][0] == w['phase']:
            phases[-1][2] = w['n']
        else:
            phases.append([w['phase'], w['n'], w['n']])

    gloss = glossary((content_dir / 'app-b.md').read_text())
    data = {'pages': pages, 'meta': meta, 'phases': phases, 'glossary': gloss}
    data_json = json.dumps(data, ensure_ascii=False)

    template = (ROOT / 'tools' / 'template.html').read_text()
    if PLACEHOLDER not in template:
        raise SystemExit('template.html is missing the DATA placeholder')
    sprite = (ROOT / 'tools' / 'icons.svg').read_text().strip()
    out = template.replace(PLACEHOLDER, DATA_PREFIX + data_json + ';').replace(SPRITE_PLACEHOLDER, sprite)

    (ROOT / 'index.html').write_text(out)
    print('wrote index.html (%d pages, %d bytes)' % (len(pages), len(out)))
    if todos:
        print('TODO chips (%d): %s' % (len(todos), ', '.join(todos)))


if __name__ == '__main__':
    build()
