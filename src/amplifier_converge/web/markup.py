"""Turning a document into readable HTML, and nothing more.

Small on purpose. A contract is headings, paragraphs, lists, the odd table and
the odd fenced block. Anything fancier belongs in the document, not here.
"""

from __future__ import annotations

import html
import re

INLINE_CODE = re.compile(r"`([^`]+)`")
BOLD = re.compile(r"\*\*([^*]+)\*\*")
ITALIC = re.compile(r"(?<![*\w])\*([^*\n]+)\*(?!\*)")
LINK = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)")
HEADING = re.compile(r"^(#{1,6})\s+(.*)$")
LIST_ITEM = re.compile(r"^\s*(?:[-*]|\d+[.)])\s+(.*)$")


#: The class that marks words the app is *quoting* rather than saying.
#:
#: A work item's title, a lane's own note, a sentence out of a contract: the
#: app displays them but did not write them, and their vocabulary is the
#: project's business — documents.v1 governs them, and its kit checks them.
#: `doc` is the marker the shipped surface.v1 kit already reads for exactly
#: this reason ("scanning it here would report a contract's vocabulary as an
#: app defect"), so quoting through this class is what makes the boundary
#: checkable rather than a matter of opinion. It is never used for the app's
#: own copy — a separate test reads every string literal in this package to
#: keep that honest.
QUOTED = "doc quote"


def esc(text: object) -> str:
    return html.escape(str(text), quote=True)


def quoted(text: object) -> str:
    """Words borrowed from the project, marked as borrowed."""
    return f'<span class="{QUOTED}">{esc(text)}</span>'


def quoted_markup(rendered: str) -> str:
    """The same, for text already turned into inline markup."""
    return f'<span class="{QUOTED}">{rendered}</span>'


def inline(text: str) -> str:
    out = esc(text)
    out = INLINE_CODE.sub(lambda m: f"<code>{m.group(1)}</code>", out)
    out = BOLD.sub(lambda m: f"<strong>{m.group(1)}</strong>", out)
    out = ITALIC.sub(lambda m: f"<em>{m.group(1)}</em>", out)
    out = LINK.sub(lambda m: f'<a href="{m.group(2)}">{m.group(1)}</a>', out)
    return out


def _table(rows: list[str]) -> str:
    cells = [[c.strip() for c in row.strip().strip("|").split("|")] for row in rows]
    if len(cells) >= 2 and all(set(c) <= set("-: ") for c in cells[1]):
        head, body = cells[0], cells[2:]
    else:
        head, body = [], cells
    parts = ["<table>"]
    if head:
        parts.append("<thead><tr>" + "".join(f"<th>{inline(c)}</th>" for c in head) + "</tr></thead>")
    parts.append("<tbody>")
    for row in body:
        parts.append("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in row) + "</tr>")
    parts.append("</tbody></table>")
    return "".join(parts)


def document_html(text: str, ask_href: str | None = None, heading_shift: int = 0) -> str:
    """Render a document, optionally giving every paragraph a place to ask a question.

    `ask_href` is a URL template with `{anchor}` in it. When given, each
    addressable paragraph carries a small "ask" link — that is the margin
    question, attached to the paragraph it is about.
    """
    lines = text.splitlines()
    out: list[str] = []
    buffer: list[str] = []
    list_buffer: list[str] = []
    table_buffer: list[str] = []
    code_buffer: list[str] | None = None
    counter = 0

    def anchor() -> str:
        nonlocal counter
        counter += 1
        return f"p{counter}"

    def flush_paragraph() -> None:
        if not buffer:
            return
        a = anchor()
        body = inline(" ".join(line.strip() for line in buffer))
        ask = (
            f' <a class="ask" href="{ask_href.format(anchor=a)}">ask about this</a>'
            if ask_href
            else ""
        )
        out.append(f'<div class="para" id="{a}"><p>{body}{ask}</p></div>')
        buffer.clear()

    def flush_list() -> None:
        if not list_buffer:
            return
        a = anchor()
        items = "".join(f"<li>{inline(item)}</li>" for item in list_buffer)
        ask = (
            f'<a class="ask" href="{ask_href.format(anchor=a)}">ask about this</a>'
            if ask_href
            else ""
        )
        out.append(f'<div class="para" id="{a}"><ul class="tradeoffs">{items}</ul>{ask}</div>')
        list_buffer.clear()

    def flush_table() -> None:
        if not table_buffer:
            return
        out.append(_table(table_buffer))
        table_buffer.clear()

    def flush_all() -> None:
        flush_paragraph()
        flush_list()
        flush_table()

    for line in lines:
        if line.strip().startswith("```"):
            if code_buffer is None:
                flush_all()
                code_buffer = []
            else:
                out.append(f"<pre>{esc(chr(10).join(code_buffer))}</pre>")
                code_buffer = None
            continue
        if code_buffer is not None:
            code_buffer.append(line)
            continue

        heading = HEADING.match(line)
        if heading:
            flush_all()
            level = min(6, len(heading.group(1)) + heading_shift)
            out.append(f"<h{level}>{inline(heading.group(2).strip())}</h{level}>")
            continue

        if line.strip().startswith("|"):
            flush_paragraph()
            flush_list()
            table_buffer.append(line)
            continue
        flush_table()

        item = LIST_ITEM.match(line)
        if item:
            flush_paragraph()
            list_buffer.append(item.group(1))
            continue
        flush_list()

        if line.strip() == "---":
            flush_all()
            continue
        if not line.strip():
            flush_all()
            continue
        buffer.append(line)

    if code_buffer is not None:
        out.append(f"<pre>{esc(chr(10).join(code_buffer))}</pre>")
    flush_all()
    return "\n".join(out)
