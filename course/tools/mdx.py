"""Deterministic, dependency-free markdown <-> HTML for the study plan.

Covers exactly the subset of markdown this project uses: paragraphs, h2 and
h3 headings with explicit {#id} anchors, bold/code/link inline spans, fenced
code blocks, GFM pipe tables, plain lists, and a custom task-list block
(`<!-- tasks:CAT -->` followed by a checkbox list) that reproduces the
`data-id`-driven checkboxes the app's progress tracker depends on. A
`raw-html` fence passes content through untouched (used for the two
hand-drawn SVG figures).

The page outline (compute_toc) is built from h2s, with any h3s nested under
the h2 that precedes them — used for the day-by-day sub-links in each week's
"On this page" sidebar. h3 is not a general section level: only use it where
an h2 section has linkable sub-parts, never as a standalone heading tier.

md_to_html() is what tools/build.py uses on every build. html_to_md() was
used once by tools/extract.py to bootstrap content/*.md from the old
monolithic index.html, and is kept here so the pair stays in sync.
"""

import html as _html
import re
from html.parser import HTMLParser as _HTMLParserBase

EXTERNAL_LINK_ATTRS = ' rel="noopener" target="_blank"'


# ---------------------------------------------------------------------------
# inline: markdown <-> HTML for text within a block (no block-level markup)
# ---------------------------------------------------------------------------


def inline_md_to_html(text):
    out = []
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if c == '\\' and i + 1 < n and text[i + 1] in '\\`*[]':
            out.append(_esc(text[i + 1]))
            i += 2
            continue
        if c == '`':
            j = text.find('`', i + 1)
            if j == -1:
                out.append(_esc(text[i:]))
                i = n
                continue
            code = text[i + 1 : j]
            out.append('<code>' + _esc(code) + '</code>')
            i = j + 1
            continue
        if text.startswith('**', i):
            j = text.find('**', i + 2)
            if j == -1:
                out.append(_esc(text[i:]))
                i = n
                continue
            out.append('<strong>' + inline_md_to_html(text[i + 2 : j]) + '</strong>')
            i = j + 2
            continue
        if c == '[':
            m = re.match(r'\[([^\]]*)\]\(([^)]+)\)', text[i:])
            if m:
                label, url = m.group(1), m.group(2)
                attrs = EXTERNAL_LINK_ATTRS if url.startswith('http') else ''
                out.append('<a href="' + _esc_attr(url) + '"' + attrs + '>' + inline_md_to_html(label) + '</a>')
                i += m.end()
                continue
        out.append(_esc(c))
        i += 1
    return ''.join(out)


def _esc(s):
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def _esc_attr(s):
    return _esc(s)


# ---------------------------------------------------------------------------
# block: markdown -> HTML
# ---------------------------------------------------------------------------

_HEADING_RE = re.compile(r'^##\s+(.*?)\s*\{#([a-z0-9-]+)\}\s*$')
_HEADING3_RE = re.compile(r'^###\s+(.*?)\s*\{#([a-z0-9-]+)\}\s*$')
_FENCE_RE = re.compile(r'^```([a-zA-Z0-9-]*)\s*$')
_TASKS_DIRECTIVE_RE = re.compile(r'^<!--\s*tasks:(\w+)\s*-->$')
_UL_ITEM_RE = re.compile(r'^- (?:\[( |x)\] )?(.*)$')
_OL_ITEM_RE = re.compile(r'^\d+\. (?:\[( |x)\] )?(.*)$')
_TABLE_SEP_RE = re.compile(r'^\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)*\|?$')

_TASK_KIND = {
    'q': ('task q', 'I can answer this', True),
}


def _task_style(cat):
    return _TASK_KIND.get(cat, ('task do', 'Done', False))


def _split_blocks(lines):
    """Group raw markdown lines into top-level blocks (list of line-lists)."""
    blocks = []
    i, n = 0, len(lines)
    while i < n:
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        if _FENCE_RE.match(line):
            j = i + 1
            while j < n and lines[j].strip() != '```':
                j += 1
            blocks.append(lines[i : j + 1])
            i = j + 1
            continue
        if _TASKS_DIRECTIVE_RE.match(line.strip()):
            j = i + 1
            while j < n and lines[j].strip():
                j += 1
            blocks.append(lines[i:j])
            i = j
            continue
        if _UL_ITEM_RE.match(line) or _OL_ITEM_RE.match(line):
            j = i
            while j < n and (lines[j].strip() == '' and False):
                j += 1
            j = i
            while j < n and lines[j].strip() and (_UL_ITEM_RE.match(lines[j]) or _OL_ITEM_RE.match(lines[j])):
                j += 1
            blocks.append(lines[i:j])
            i = j
            continue
        if line.lstrip().startswith('|'):
            j = i
            while j < n and lines[j].strip() and lines[j].lstrip().startswith('|'):
                j += 1
            blocks.append(lines[i:j])
            i = j
            continue
        # paragraph / heading: single logical line, but allow soft-wrapped
        # continuation lines (joined with a space) until a blank line.
        j = i
        while j < n and lines[j].strip():
            j += 1
        blocks.append(lines[i:j])
        i = j
    return blocks


def render_list_items_html(item_lines, ordered, data_id_prefix=None, cat=None):
    out = []
    for raw in item_lines:
        m = (_OL_ITEM_RE if ordered else _UL_ITEM_RE).match(raw)
        _, body = m.group(1), m.group(2)
        if data_id_prefix is not None:
            idx = len([o for o in out]) + 1
            data_id = '%s.%s.%d' % (data_id_prefix, cat, idx)
            li_class, aria, has_qtag = _task_style(cat)
            cb_id = 'c-' + data_id.replace('.', '-')
            tag = (
                '<li class="%s" data-id="%s"><input aria-label="%s" data-id="%s" id="%s" type="checkbox"/>'
                '<div class="task-body">%s</div>' % (li_class, data_id, aria, data_id, cb_id, inline_md_to_html(body))
            )
            if has_qtag:
                tag += '<span class="qtag">Can answer</span>'
            tag += '</li>'
            out.append(tag)
        else:
            out.append('<li>%s</li>' % inline_md_to_html(body))
    return out


def block_to_html(block, page_id):
    first = block[0]

    m = _HEADING_RE.match(first)
    if m:
        text, hid = m.group(1), m.group(2)
        return '<h2 id="%s">%s</h2>' % (hid, inline_md_to_html(text))

    m3 = _HEADING3_RE.match(first)
    if m3:
        text, hid = m3.group(1), m3.group(2)
        return '<h3 id="%s">%s</h3>' % (hid, inline_md_to_html(text))

    fm = _FENCE_RE.match(first)
    if fm:
        lang = fm.group(1)
        code_lines = block[1:-1]
        code = '\n'.join(code_lines)
        if lang == 'raw-html':
            return code
        cls = ' class="language-%s"' % lang if lang else ''
        return '<div class="code-wrap"><pre><code%s>%s</code></pre></div>' % (cls, _esc(code))

    directive = _TASKS_DIRECTIVE_RE.match(first.strip())
    if directive:
        cat = directive.group(1)
        item_lines = block[1:]
        ordered = bool(item_lines) and bool(_OL_ITEM_RE.match(item_lines[0]))
        items = render_list_items_html(item_lines, ordered, data_id_prefix=page_id, cat=cat)
        if ordered:
            return '<ol class="tasks" type="1">\n' + '\n'.join(items) + '\n</ol>'
        return '<ul class="tasks">\n' + '\n'.join(items) + '\n</ul>'

    if _UL_ITEM_RE.match(first) or _OL_ITEM_RE.match(first):
        ordered = bool(_OL_ITEM_RE.match(first))
        items = render_list_items_html(block, ordered)
        if ordered:
            return '<ol type="1">\n' + '\n'.join(items) + '\n</ol>'
        return '<ul>\n' + '\n'.join(items) + '\n</ul>'

    if first.lstrip().startswith('|'):
        rows = [ln.strip() for ln in block if ln.strip()]
        header_cells = [c.strip() for c in rows[0].strip('|').split('|')]
        body_rows = [r for r in rows[2:]] if len(rows) > 1 and _TABLE_SEP_RE.match(rows[1]) else rows[1:]
        out = ['<div class="table-wrap"><table>', '<thead>', '<tr class="header">']
        out += ['<th>%s</th>' % inline_md_to_html(c) for c in header_cells]
        out += ['</tr>', '</thead>', '<tbody>']
        for idx, r in enumerate(body_rows):
            cells = [c.strip() for c in r.strip('|').split('|')]
            cls = 'odd' if idx % 2 == 0 else 'even'
            out.append('<tr class="%s">' % cls)
            out += ['<td>%s</td>' % inline_md_to_html(c) for c in cells]
            out.append('</tr>')
        out += ['</tbody>', '</table></div>']
        return '\n'.join(out)

    # paragraph: join soft-wrapped lines with a space
    text = ' '.join(ln.strip() for ln in block)
    return '<p>%s</p>' % inline_md_to_html(text)


def md_to_html(md_text, page_id):
    lines = md_text.split('\n')
    blocks = _split_blocks(lines)
    return '\n'.join(block_to_html(b, page_id) for b in blocks) + '\n'


# ---------------------------------------------------------------------------
# derived fields: toc / plain text / task count (computed from rendered html)
# ---------------------------------------------------------------------------

_TAG_RE = re.compile(r'<[^>]+>')
_H2_RE = re.compile(r'<h2 id="([a-z0-9-]+)">(.*?)</h2>')
_HEADING_TAG_RE = re.compile(r'<(h2|h3) id="([a-z0-9-]+)">(.*?)</\1>')
_DATA_ID_RE = re.compile(r'data-id="([^"]+)"')


def compute_toc(html):
    """[[h2id, h2text, [[h3id, h3text], ...]], ...] — any h3 nests under
    the nearest preceding h2 (there is always one: content starts with h2)."""
    toc = []
    for tag, hid, text in _HEADING_TAG_RE.findall(html):
        if tag == 'h2':
            toc.append([hid, compute_text(text), []])
        else:
            toc[-1][2].append([hid, compute_text(text)])
    return toc


_INLINE_TAGS = {'code', 'strong', 'a', 'span', 'input'}


class _TextExtractor(_HTMLParserBase):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out = []

    def _sep(self):
        if self.out and self.out[-1] and self.out[-1][-1] not in ' \n\t':
            self.out.append(' ')

    def handle_starttag(self, tag, attrs):
        if tag not in _INLINE_TAGS:
            self._sep()

    def handle_startendtag(self, tag, attrs):
        if tag not in _INLINE_TAGS:
            self._sep()

    def handle_endtag(self, tag):
        if tag not in _INLINE_TAGS:
            self._sep()

    def handle_data(self, data):
        if data.strip() == '':
            return
        self.out.append(data)

    def text(self):
        return ''.join(self.out).strip()


def compute_text(html):
    p = _TextExtractor()
    p.feed(html)
    p.close()
    return p.text()


def compute_tasks(html):
    return len(set(_DATA_ID_RE.findall(html)))


# ---------------------------------------------------------------------------
# inline: HTML -> markdown (used once, by tools/extract.py)
# ---------------------------------------------------------------------------


def inline_html_to_md(s):
    out = []
    i, n = 0, len(s)
    while i < n:
        if s[i] == '<':
            if s.startswith('<code>', i):
                j = s.find('</code>', i)
                out.append('`' + _html.unescape(s[i + 6 : j]) + '`')
                i = j + 7
                continue
            if s.startswith('<strong>', i):
                j = s.find('</strong>', i)
                out.append('**' + inline_html_to_md(s[i + 8 : j]) + '**')
                i = j + 9
                continue
            m = re.match(r'<a href="([^"]*)"[^>]*>', s[i:])
            if m:
                url = _html.unescape(m.group(1))
                start = i + m.end()
                j = s.find('</a>', start)
                out.append('[' + inline_html_to_md(s[start:j]) + '](' + url + ')')
                i = j + 4
                continue
            raise ValueError('unexpected tag at: ' + s[i : i + 40])
        j = s.find('<', i)
        if j == -1:
            j = n
        chunk = _html.unescape(s[i:j])
        chunk = re.sub(r'(?<!\\)([\\`*\[\]])', r'\\\1', chunk)
        out.append(chunk)
        i = j
    return ''.join(out)


# ---------------------------------------------------------------------------
# block: HTML -> markdown
# ---------------------------------------------------------------------------

_TASK_LI_RE = re.compile(
    r'<li class="task (?:do|q)" data-id="([^"]+)"><input [^>]*/><div class="task-body">(.*?)</div>'
    r'(?:<span class="qtag">Can answer</span>)?</li>',
    re.DOTALL,
)
_PLAIN_LI_RE = re.compile(r'<li>(.*?)</li>', re.DOTALL)


def _html_blocks(html):
    """Split a page's top-level HTML into block strings."""
    blocks = []
    i, n = 0, len(html)
    while i < n:
        while i < n and html[i] in '\n':
            i += 1
        if i >= n:
            break
        if html.startswith('<div class="table-wrap">', i):
            j = html.index('</table></div>', i) + len('</table></div>')
        elif html.startswith('<div class="code-wrap">', i):
            j = html.index('</code></pre></div>', i) + len('</code></pre></div>')
        elif html.startswith('<figure', i):
            j = html.index('</figure>', i) + len('</figure>')
        elif html.startswith('<h2 ', i):
            j = html.index('</h2>', i) + len('</h2>')
        elif html.startswith('<h3 ', i):
            j = html.index('</h3>', i) + len('</h3>')
        elif html.startswith('<ul class="tasks">', i) or html.startswith('<ul>', i):
            j = html.index('</ul>', i) + len('</ul>')
        elif html.startswith('<ol class="tasks" type="1">', i) or html.startswith('<ol type="1">', i):
            j = html.index('</ol>', i) + len('</ol>')
        elif html.startswith('<p>', i):
            j = html.index('</p>', i) + len('</p>')
        else:
            raise ValueError('unrecognized block at: ' + html[i : i + 60])
        blocks.append(html[i:j])
        i = j
    return blocks


def block_to_md(block):
    if block.startswith('<div class="table-wrap">'):
        ths = re.findall(r'<th>(.*?)</th>', block, re.DOTALL)
        rows = re.findall(r'<tr class="(?:odd|even)">(.*?)</tr>', block, re.DOTALL)
        header = [inline_html_to_md(c) for c in ths]
        lines = ['| ' + ' | '.join(header) + ' |', '|' + '|'.join(['---'] * len(header)) + '|']
        for r in rows:
            cells = [inline_html_to_md(c) for c in re.findall(r'<td>(.*?)</td>', r, re.DOTALL)]
            lines.append('| ' + ' | '.join(cells) + ' |')
        return '\n'.join(lines)

    if block.startswith('<div class="code-wrap">'):
        m = re.match(
            r'<div class="code-wrap"><pre><code(?: class="language-([a-zA-Z0-9-]*)")?>(.*)</code></pre></div>$',
            block,
            re.DOTALL,
        )
        lang, code = m.group(1) or '', m.group(2)
        code = _html.unescape(code)
        return '```%s\n%s\n```' % (lang, code)

    if block.startswith('<figure'):
        return '```raw-html\n%s\n```' % block

    m = re.match(r'<h2 id="([a-z0-9-]+)">(.*)</h2>$', block, re.DOTALL)
    if m:
        return '## %s {#%s}' % (inline_html_to_md(m.group(2)), m.group(1))

    m3 = re.match(r'<h3 id="([a-z0-9-]+)">(.*)</h3>$', block, re.DOTALL)
    if m3:
        return '### %s {#%s}' % (inline_html_to_md(m3.group(2)), m3.group(1))

    if block.startswith('<ul class="tasks">') or block.startswith('<ol class="tasks" type="1">'):
        ordered = block.startswith('<ol')
        items = _TASK_LI_RE.findall(block)
        cat = items[0][0].split('.')[1] if items else 'check'
        lines = ['<!-- tasks:%s -->' % cat]
        for idx, (_data_id, body) in enumerate(items, 1):
            prefix = '%d. [ ] ' % idx if ordered else '- [ ] '
            lines.append(prefix + inline_html_to_md(body))
        return '\n'.join(lines)

    if block.startswith('<ul>') or block.startswith('<ol type="1">'):
        ordered = block.startswith('<ol')
        items = _PLAIN_LI_RE.findall(block)
        lines = []
        for idx, body in enumerate(items, 1):
            prefix = '%d. ' % idx if ordered else '- '
            lines.append(prefix + inline_html_to_md(body))
        return '\n'.join(lines)

    if block.startswith('<p>'):
        return inline_html_to_md(block[3:-4])

    raise ValueError('unrecognized block: ' + block[:60])


def html_to_md(html):
    return '\n\n'.join(block_to_md(b) for b in _html_blocks(html))
