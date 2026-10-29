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

Typed blocks (the site's component library) are Pandoc-style fenced divs:
`::: {.type key="value"}` opens one, a line of just `:::` closes it, and they
nest. Their content is ordinary markdown in this dialect (code fences at
column 0 are fine inside). Types:

    lead                     the section's one-sentence takeaway (p.lead)
    hero                     week hero fields, not rendered inline:
                             `- Lead: ...`, `- Outcome: ...` (repeat), `- Ships: ...`, `- Time: ...`
    key-idea                 the filled concept block that opens a week
    {.concept title=".."}    concept card: first paragraph is the definition
    stats                    key numbers strip: `- 1.25x | 5-minute cache write`
    {.details summary=".."}  a disclosure; the summary names what is inside
    {.tasks cat="build"}     checkable cards (cat: build, exp, q, check); children are
                             `- [ ] title` lines or {.step title=".." id=".."} divs whose
                             `- Key: value` list becomes Files / Done when / ... fields.
                             ids are positional (page.cat.n) exactly like `<!-- tasks -->`;
                             a step's `id` is an assertion the build checks.
    {.read title=".." commit=".." href=".."}   read card
    pitfall, scope, increment, production, {.block kind=".." label=".."}
    timeline / {.day label="Mon"}            the day-by-day timeline
    {.sub id=".." title=".." hint=".."}      collapsible sub-section; its h3 keeps `id`
    `####` headings with {#id} are allowed inside blocks (they stay out of the outline).

A fence may carry attributes after the language: ```python file=rig/agent.py
puts a filename tab on the code block.

md_to_page() is what tools/build.py uses on every build; it returns the html
and the extras (hero fields) blocks hand back. Each h2 and what follows it is
wrapped in a <section> whose kind comes from the h2 id suffix (SECTION_KINDS).

html_to_md() was used once by tools/extract.py to bootstrap content/*.md from
the old monolithic index.html. It reads only that original markup (no typed
blocks, no section wrappers) and is kept as a record, not as a round trip.
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
_HEADING4_RE = re.compile(r'^####\s+(.*?)\s*\{#([a-z0-9-]+)\}\s*$')
_FENCE_RE = re.compile(r'^```([a-zA-Z0-9-]*)((?:\s+[\w-]+=\S+)*)\s*$')
_TASKS_DIRECTIVE_RE = re.compile(r'^<!--\s*tasks:(\w+)\s*-->$')
_UL_ITEM_RE = re.compile(r'^- (?:\[( |x)\] )?(.*)$')
_OL_ITEM_RE = re.compile(r'^\d+\. (?:\[( |x)\] )?(.*)$')
_TABLE_SEP_RE = re.compile(r'^\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)*\|?$')
_DIV_OPEN_RE = re.compile(r'^:::\s*(?:\{(.*)\}|([a-z][\w-]*))\s*$')
_DIV_ATTR_RE = re.compile(r'([\w-]+)="([^"]*)"')
_FIELD_RE = re.compile(r'^([A-Z][\w ,/-]{0,40}):\s+(.*)$')
_NUM_CELL_RE = re.compile(r'^[~≈]?[$]?\d[\d,.]*\s*(%|x|h|s|ms|KB|MB|GB|k|M)?$')

# Section kinds, keyed by the suffix of a week's h2 id ({#w3-build} -> build): the colour
# family and the icon its header gets. Pages and sections not listed here stay plain.
SECTION_KINDS = {
    'key-idea': ('concept', 'lightbulb'),
    'concepts': ('concept', 'lightbulb'),
    'repository-layout': ('build', 'pin'),
    'day-by-day': ('build', 'clock'),
    'build': ('build', 'hammer'),
    'project-increment': ('build', 'git-commit'),
    'read': ('read', 'book'),
    'experiments': ('experiment', 'flask'),
    'you-should-be-able-to-answer': ('check', 'help'),
    'production-lens': ('concept', 'factory'),
    'not-yet': ('read', 'slash'),
    'checkpoint': ('check', 'flag'),
}

# Task category -> (block kind, label shown on the card).
_TASK_KINDS = {
    'build': ('build', 'Build step'),
    'exp': ('experiment', 'Experiment'),
    'q': ('check', 'Self-check'),
    'check': ('check', 'Checkpoint'),
}

# Typed blocks: type -> (kind, icon, label).
_BLOCK_TYPES = {
    'concept': ('concept', 'lightbulb', 'Concept'),
    'key-idea': ('concept', 'lightbulb', 'Key idea'),
    'production': ('concept', 'factory', 'Production lens'),
    'read': ('read', 'book', 'Read'),
    'pitfall': ('pitfall', 'alert', 'Pitfall'),
    'scope': ('read', 'slash', 'Not yet'),
    'increment': ('build', 'git-commit', 'rig after this week'),
    'block': ('read', 'book', ''),
}


def icon(name):
    return '<svg class="icon" aria-hidden="true"><use href="#i-%s"/></svg>' % name


def _slug(text):
    return re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')[:48]


class _Ctx:
    """Per-page render state: the page id (for task ids) and what blocks hand back to the
    build (the week hero's fields) rather than render inline."""

    def __init__(self, page_id):
        self.page_id = page_id
        self.extras = {}


def _is_div_close(line):
    return line.strip() == ':::'


def _split_blocks(lines):
    """Group raw markdown lines into top-level blocks (list of line-lists).

    A fenced div (`::: type` ... `:::`) is one block, however much it contains: its
    closing line is found by counting nested opens, skipping anything inside code fences.
    """
    blocks = []
    i, n = 0, len(lines)
    while i < n:
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        if _DIV_OPEN_RE.match(line):
            depth, j, in_code = 1, i + 1, False
            while j < n:
                s = lines[j]
                if in_code:
                    in_code = s.strip() != '```'
                elif _FENCE_RE.match(s):
                    in_code = True
                elif _DIV_OPEN_RE.match(s):
                    depth += 1
                elif _is_div_close(s):
                    depth -= 1
                    if depth == 0:
                        break
                j += 1
            if j >= n:
                raise ValueError('unclosed ::: block starting: ' + line)
            blocks.append(lines[i : j + 1])
            i = j + 1
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
        # continuation lines (joined with a space) until a blank line or a div marker.
        j = i
        while j < n and lines[j].strip() and not (j > i and (_DIV_OPEN_RE.match(lines[j]) or _is_div_close(lines[j]))):
            j += 1
        blocks.append(lines[i:j])
        i = j
    return blocks


def _task_item(page_id, cat, idx, title_html, body_html='', assert_id=None):
    """One checkable card. The data-id is positional (page.cat.n) and is what saved
    progress is keyed on; `assert_id` lets a source file state the id it expects."""
    data_id = '%s.%s.%d' % (page_id, cat, idx)
    if assert_id and assert_id != data_id:
        raise ValueError('task id mismatch: source says %s, position gives %s' % (assert_id, data_id))
    kind, _label = _TASK_KINDS.get(cat, ('build', 'Task'))
    cb = 'c-' + data_id.replace('.', '-')
    if cat == 'q':
        # The question is the title; the checkbox itself says what ticking it means.
        head = (
            '<p class="step__title" id="%s-t"><span class="step__n">%d</span>%s</p>'
            '<label class="step__ans" for="%s">I can answer this</label>' % (cb, idx, title_html, cb)
        )
        box = '<input type="checkbox" id="%s" data-id="%s" aria-describedby="%s-t"/>' % (cb, data_id, cb)
    else:
        head = '<label for="%s" class="step__title"><span class="step__n">%d</span>%s</label>' % (cb, idx, title_html)
        box = '<input type="checkbox" id="%s" data-id="%s"/>' % (cb, data_id)
    return '<li class="step step--%s" data-id="%s" id="%s-b">%s<div class="step__body">%s%s</div></li>' % (
        kind,
        data_id,
        cb,
        box,
        head,
        body_html,
    )


def _wrap_tasks(cat, items):
    kind = _TASK_KINDS.get(cat, ('build',))[0]
    ol = '<ol class="steps steps--%s" data-cat="%s">\n%s\n</ol>' % (kind, cat, '\n'.join(items))
    if cat == 'check':
        return (
            '<div class="block block--check block--filled checkpoint">'
            '<p class="block__label">%sCheckpoint</p>'
            '<p class="block__lead">Week done when all are ticked.</p>%s</div>' % (icon('flag'), ol)
        )
    return ol


def render_list_items_html(item_lines, ordered, data_id_prefix=None, cat=None):
    out = []
    for raw in item_lines:
        m = (_OL_ITEM_RE if ordered else _UL_ITEM_RE).match(raw)
        body = m.group(2)
        if data_id_prefix is not None:
            out.append(_task_item(data_id_prefix, cat, len(out) + 1, inline_md_to_html(body)))
        else:
            out.append('<li>%s</li>' % inline_md_to_html(body))
    return out


def _fields_html(item_lines):
    """`- Key: value` lines -> the card's definition list (Files, Done when, Trigger, ...)."""
    rows = []
    for raw in item_lines:
        m = _FIELD_RE.match(_UL_ITEM_RE.match(raw).group(2))
        rows.append('<div><dt>%s</dt><dd>%s</dd></div>' % (_esc(m.group(1)), inline_md_to_html(m.group(2))))
    return '<dl class="step__meta">%s</dl>' % ''.join(rows)


def _is_fields(block):
    return all(_UL_ITEM_RE.match(ln) and _FIELD_RE.match(_UL_ITEM_RE.match(ln).group(2)) for ln in block)


def _render_inner(lines, ctx, fields=False):
    """Render a div's content. With `fields`, a list made only of `Key: value` items
    becomes the card's definition list instead of bullets."""
    out = []
    for b in _split_blocks(lines):
        if fields and (_UL_ITEM_RE.match(b[0])) and _is_fields(b):
            out.append(_fields_html(b))
        else:
            out.append(block_to_html(b, ctx))
    return '\n'.join(out)


def _first_para_as_lead(html, cls='block__lead'):
    return re.sub(r'^<p>', '<p class="%s">' % cls, html, count=1)


def _parse_div(first):
    m = _DIV_OPEN_RE.match(first)
    if m.group(2):
        return {'type': m.group(2)}
    raw = m.group(1)
    attrs = dict(_DIV_ATTR_RE.findall(raw))
    classes = re.findall(r'(?:^|\s)\.([\w-]+)', raw)
    attrs['type'] = classes[0] if classes else 'block'
    return attrs


def _label(kind_icon, text):
    return '<p class="block__label">%s%s</p>' % (icon(kind_icon), _esc(text)) if text else ''


def _render_div(block, ctx):
    a = _parse_div(block[0])
    inner = block[1:-1]
    t = a['type']
    pid = ctx.page_id

    if t == 'lead':
        return '<p class="lead">%s</p>' % inline_md_to_html(' '.join(ln.strip() for ln in inner if ln.strip()))

    if t == 'hero':
        hero = ctx.extras.setdefault('hero', {'outcomes': []})
        for ln in inner:
            if not ln.strip():
                continue
            m = _FIELD_RE.match(_UL_ITEM_RE.match(ln).group(2))
            key, val = m.group(1).lower(), m.group(2)
            if key == 'outcome':
                hero['outcomes'].append(inline_md_to_html(val))
            else:
                hero[key] = inline_md_to_html(val)
        return ''

    if t == 'stats':
        cells = []
        for ln in inner:
            if not ln.strip():
                continue
            val, _, lab = _UL_ITEM_RE.match(ln).group(2).partition(' | ')
            cell = '<div class="stat" role="listitem"><b>%s</b><span>%s</span></div>'
            cells.append(cell % (_esc(val), inline_md_to_html(lab)))
        aria = _esc(a.get('label', 'Key numbers'))
        return '<div class="stats" role="list" aria-label="%s">%s</div>' % (aria, ''.join(cells))

    if t == 'details':
        summary = a.get('summary', 'Details')
        return '<details class="more"><summary>%s</summary>%s</details>' % (
            inline_md_to_html(summary),
            _render_inner(inner, ctx),
        )

    if t == 'tasks':
        cat = a['cat']
        items = []
        for b in _split_blocks(inner):
            idx = len(items) + 1
            if _DIV_OPEN_RE.match(b[0]):
                sa = _parse_div(b[0])
                body = _render_inner(b[1:-1], ctx, fields=True)
                items.append(_task_item(pid, cat, idx, inline_md_to_html(sa['title']), body, sa.get('id')))
            else:
                for ln in b:
                    m = _OL_ITEM_RE.match(ln) or _UL_ITEM_RE.match(ln)
                    items.append(_task_item(pid, cat, len(items) + 1, inline_md_to_html(m.group(2))))
        return _wrap_tasks(cat, items)

    if t == 'timeline':
        return '<ol class="timeline">%s</ol>' % _render_inner(inner, ctx)

    if t == 'day':
        return '<li class="tl"><span class="tl__day">%s</span><div class="tl__body">%s</div></li>' % (
            _esc(a.get('label', '')),
            _render_inner(inner, ctx, fields=True),
        )

    if t == 'sub':
        hid = a['id']
        return (
            '<details class="subsec" data-sub="%s"><summary><h3 id="%s">%s</h3>'
            '<span class="subsec__hint">%s</span></summary>'
            '<div class="subsec__body">%s</div></details>'
            % (hid, hid, inline_md_to_html(a['title']), inline_md_to_html(a.get('hint', '')), _render_inner(inner, ctx))
        )

    if t == 'production':
        # Titles visible, bodies collapsed: each `- **Title** rest` item is one disclosure.
        rows = []
        for ln in inner:
            if not ln.strip():
                continue
            body = _UL_ITEM_RE.match(ln).group(2)
            m = re.match(r'^\*\*(.+?)\*\*[:.]?\s*(.*)$', body)
            rows.append(
                '<details class="more prod"><summary>%s</summary><p>%s</p></details>'
                % (inline_md_to_html(m.group(1)), inline_md_to_html(m.group(2)))
            )
        return '<div class="block block--concept">%s%s</div>' % (_label('factory', 'Production lens'), ''.join(rows))

    if t in _BLOCK_TYPES:
        kind, ic, label = _BLOCK_TYPES[t]
        kind = a.get('kind', kind)
        label = a.get('label', label)
        title = a.get('title', '')
        bid = a.get('id') or ('%s-%s' % (pid, _slug(title)) if title else '')
        cls = 'block block--%s' % kind
        if t in ('key-idea', 'pitfall'):
            cls += ' block--filled'
        if t == 'scope':
            cls += ' block--scope'
        head = _label(a.get('icon', ic), label)
        if title and head:
            head = head.replace('<p class="block__label">', '<span class="block__label">', 1)[: -len('</p>')] + '</span>'
            ttl = inline_md_to_html(title)
            if a.get('href'):
                ttl = '<a href="%s"%s>%s</a>' % (_esc_attr(a['href']), EXTERNAL_LINK_ATTRS, ttl)
            badge = ' <code class="badge">%s</code>' % _esc(a['commit']) if a.get('commit') else ''
            head = '<div class="block__head">%s<h3 class="block__title">%s%s</h3></div>' % (head, ttl, badge)
        body = _render_inner(inner, ctx, fields=t in ('increment', 'block'))
        if title or t in ('pitfall', 'scope', 'key-idea', 'increment'):
            body = _first_para_as_lead(body)
        tag = 'aside' if t == 'pitfall' else 'section'
        idattr = ' id="%s"' % bid if bid else ''
        return '<%s class="%s"%s>%s%s</%s>' % (tag, cls, idattr, head, body, tag)

    raise ValueError('unknown ::: block type %r' % t)


def block_to_html(block, page_id):
    ctx = page_id if isinstance(page_id, _Ctx) else _Ctx(page_id)
    first = block[0]

    if _DIV_OPEN_RE.match(first):
        return _render_div(block, ctx)

    m = _HEADING_RE.match(first)
    if m:
        text, hid = m.group(1), m.group(2)
        return '<h2 id="%s">%s</h2>' % (hid, inline_md_to_html(text))

    m3 = _HEADING3_RE.match(first)
    if m3:
        text, hid = m3.group(1), m3.group(2)
        return '<h3 id="%s">%s</h3>' % (hid, inline_md_to_html(text))

    m4 = _HEADING4_RE.match(first)
    if m4:
        text, hid = m4.group(1), m4.group(2)
        return '<h4 id="%s">%s</h4>' % (hid, inline_md_to_html(text))

    fm = _FENCE_RE.match(first)
    if fm:
        lang = fm.group(1)
        attrs = dict(kv.split('=', 1) for kv in fm.group(2).split())
        code_lines = block[1:-1]
        code = '\n'.join(code_lines)
        if lang == 'raw-html':
            return code
        cls = ' class="language-%s"' % lang if lang else ''
        pairs = (('lang', lang), ('file', attrs.get('file', '')))
        data = ''.join(' data-%s="%s"' % (k, _esc_attr(v)) for k, v in pairs if v)
        return '<div class="code-wrap"%s><pre><code%s>%s</code></pre></div>' % (data, cls, _esc(code))

    directive = _TASKS_DIRECTIVE_RE.match(first.strip())
    if directive:
        cat = directive.group(1)
        item_lines = block[1:]
        ordered = bool(item_lines) and bool(_OL_ITEM_RE.match(item_lines[0]))
        items = render_list_items_html(item_lines, ordered, data_id_prefix=ctx.page_id, cat=cat)
        return _wrap_tasks(cat, items)

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
        label = 'Table: ' + ', '.join(compute_text(inline_md_to_html(c)) for c in header_cells)
        wrap = '<div class="table-wrap" tabindex="0" role="region" aria-label="%s"><table>' % _esc_attr(label)
        out = [wrap, '<thead>', '<tr class="header">']
        out += ['<th>%s</th>' % inline_md_to_html(c) for c in header_cells]
        out += ['</tr>', '</thead>', '<tbody>']
        for idx, r in enumerate(body_rows):
            cells = [c.strip() for c in r.strip('|').split('|')]
            cls = 'odd' if idx % 2 == 0 else 'even'
            out.append('<tr class="%s">' % cls)
            for c in cells:
                td = '<td class="num">%s</td>' if _NUM_CELL_RE.match(c) else '<td>%s</td>'
                out.append(td % inline_md_to_html(c))
            out.append('</tr>')
        out += ['</tbody>', '</table></div>']
        return '\n'.join(out)

    # paragraph: join soft-wrapped lines with a space
    text = ' '.join(ln.strip() for ln in block)
    return '<p>%s</p>' % inline_md_to_html(text)


def _sectioned(blocks_html, page_id):
    """Wrap each h2 and what follows it in a <section>, giving week sections their colour
    family, icon and an empty `n of m` count the app fills in. Anything before the first h2
    on a week page is the untyped week intro."""
    out, open_ = [], False
    is_week = bool(re.match(r'^(w\d+|_components)$', page_id))
    if is_week:
        first_h2 = next((i for i, h in enumerate(blocks_html) if h.startswith('<h2 ')), len(blocks_html))
        intro = '\n'.join(blocks_html[:first_h2])
        blocks_html = (['<div class="week-intro">%s</div>' % intro] if intro.strip() else []) + blocks_html[first_h2:]
    for h in blocks_html:
        m = re.match(r'^<h2 id="([a-z0-9-]+)">(.*)</h2>$', h, re.DOTALL)
        if m:
            if open_:
                out.append('</section>')
            hid, inner = m.group(1), m.group(2)
            suffix = hid.split('-', 1)[1] if '-' in hid else hid
            kind, ic = SECTION_KINDS.get(suffix, ('plain', None)) if is_week else ('plain', None)
            head = icon(ic) if ic else ''
            out.append('<section class="sec sec--%s" data-sec="%s" aria-labelledby="%s">' % (kind, suffix, hid))
            out.append('<h2 id="%s">%s%s<span class="sec-count" data-scount="%s"></span></h2>' % (hid, head, inner, hid))
            open_ = True
        else:
            out.append(h)
    if open_:
        out.append('</section>')
    return out


def md_to_page(md_text, page_id):
    """Render one page: (html, extras). `extras` holds what blocks hand to the build
    instead of rendering inline — today only the week hero's fields."""
    ctx = _Ctx(page_id)
    lines = md_text.split('\n')
    html = [block_to_html(b, ctx) for b in _split_blocks(lines)]
    html = [h for h in html if h]
    return '\n'.join(_sectioned(html, page_id)) + '\n', ctx.extras


def md_to_html(md_text, page_id):
    return md_to_page(md_text, page_id)[0]


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
