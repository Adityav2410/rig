#!/usr/bin/env python3
"""Regenerate index.html from content/*.md. Pure Python stdlib, no LLM calls.

    python3 tools/build.py

Run this after editing any file under content/. It is deterministic: same
markdown in, same index.html out, every time.
"""

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'tools'))
import mdx  # noqa: E402

PLACEHOLDER = 'const DATA = /*__RIG_DATA__*/;'
DATA_PREFIX = 'const DATA = '


def build():
    content_dir = ROOT / 'content'
    manifest = json.loads((content_dir / 'manifest.json').read_text())

    pages = []
    meta = {}
    for entry in manifest:
        pid = entry['id']
        md_text = (content_dir / (pid + '.md')).read_text()
        html = mdx.md_to_html(md_text, pid)
        pages.append(
            {
                'id': pid,
                'group': entry['group'],
                'title': entry['title'],
                'short': entry['short'],
                'html': html,
                'toc': mdx.compute_toc(html),
                'text': mdx.compute_text(html),
                'tasks': mdx.compute_tasks(html),
            }
        )
        if 'meta' in entry:
            meta[pid] = entry['meta']

    weeks = sorted(meta.values(), key=lambda m: m['n'])
    phases = []
    for w in weeks:
        if phases and phases[-1][0] == w['phase']:
            phases[-1][2] = w['n']
        else:
            phases.append([w['phase'], w['n'], w['n']])

    data = {'pages': pages, 'meta': meta, 'phases': phases}
    data_json = json.dumps(data, ensure_ascii=False)

    template = (ROOT / 'tools' / 'template.html').read_text()
    if PLACEHOLDER not in template:
        raise SystemExit('template.html is missing the DATA placeholder')
    out = template.replace(PLACEHOLDER, DATA_PREFIX + data_json + ';')

    (ROOT / 'index.html').write_text(out)
    print('wrote index.html (%d pages, %d bytes)' % (len(pages), len(out)))


if __name__ == '__main__':
    build()
