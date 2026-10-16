#!/usr/bin/env python3
"""One-time migration: split the monolithic index.html into content/*.md
plus content/manifest.json and tools/template.html.

    python3 tools/extract.py

Run from the repo root. Safe to re-run (overwrites content/*.md), but there
should be no need to once the markdown files are the source of truth.
"""

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'tools'))
import mdx  # noqa: E402

DATA_PREFIX = 'const DATA = '
PLACEHOLDER = 'const DATA = /*__RIG_DATA__*/;'


def load_data_line(html_text):
    lines = html_text.split('\n')
    for idx, line in enumerate(lines):
        if line.startswith(DATA_PREFIX):
            rest = line[len(DATA_PREFIX) :]
            assert rest.endswith(';')
            return idx, json.loads(rest[:-1])
    raise SystemExit('could not find the DATA line')


def main():
    index_path = ROOT / 'index.html'
    html_text = index_path.read_text()
    line_idx, data = load_data_line(html_text)

    content_dir = ROOT / 'content'
    content_dir.mkdir(exist_ok=True)

    manifest = []
    for page in data['pages']:
        pid = page['id']
        md = mdx.html_to_md(page['html'])
        (content_dir / (pid + '.md')).write_text(md + '\n')
        entry = {'id': pid, 'group': page['group'], 'title': page['title'], 'short': page['short']}
        if pid in data['meta']:
            entry['meta'] = data['meta'][pid]
        manifest.append(entry)

    (content_dir / 'manifest.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + '\n')

    lines = html_text.split('\n')
    lines[line_idx] = PLACEHOLDER
    (ROOT / 'tools' / 'template.html').write_text('\n'.join(lines))

    print('wrote %d markdown files to %s' % (len(manifest), content_dir))
    print('wrote %s' % (content_dir / 'manifest.json'))
    print('wrote %s' % (ROOT / 'tools' / 'template.html'))


if __name__ == '__main__':
    main()
