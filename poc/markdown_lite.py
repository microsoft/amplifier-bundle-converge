"""Just enough Markdown to read a vision and a contract.

Small on purpose. Headings, paragraphs, lists, quotes, tables, rules, fenced
code, and the inline four (strong, emphasis, code, link). Every block carries
an anchor, because the ask affordance attaches to a block and needs something
to point at.

Diagram fences (``mermaid``, ``dot``, ``graphviz``) are shown as a labelled
placeholder. Drawing them is a later job; pretending we had would be worse.
"""

from __future__ import annotations

import re

DIAGRAM_LANGUAGES = ("mermaid", "dot", "graphviz", "plantuml")

_LINK = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)")
_STRONG = re.compile(r"\*\*([^*]+)\*\*")
_EM = re.compile(r"(?<![*\w])\*([^*\n]+)\*(?![*\w])")
_CODE = re.compile(r"`([^`\n]+)`")


def escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def inline(text: str) -> str:
    """The inline four, with code spans protected from the rest."""
    held: list[str] = []

    def hold(match: re.Match[str]) -> str:
        held.append(f"<code>{escape(match.group(1))}</code>")
        return f"\x00{len(held) - 1}\x00"

    out = _CODE.sub(hold, text)
    out = escape(out)
    out = _LINK.sub(lambda m: f'<a href="{escape(m.group(2))}" rel="noreferrer">{m.group(1)}</a>', out)
    out = _STRONG.sub(r"<strong>\1</strong>", out)
    out = _EM.sub(r"<em>\1</em>", out)
    for i, piece in enumerate(held):
        out = out.replace(f"\x00{i}\x00", piece)
    return out


def _blocks(text: str) -> list[tuple[str, list[str]]]:
    """The document as a list of (kind, lines) blocks, in order."""
    lines = text.replace("\r\n", "\n").split("\n")
    out: list[tuple[str, list[str]]] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        if line.startswith("```"):
            fence = [line]
            i += 1
            while i < len(lines) and not lines[i].startswith("```"):
                fence.append(lines[i])
                i += 1
            i += 1
            out.append(("fence", fence))
            continue
        if re.match(r"^\s{0,3}#{1,6}\s", line):
            out.append(("heading", [line]))
            i += 1
            continue
        if re.match(r"^\s{0,3}(---+|\*\*\*+|___+)\s*$", line):
            out.append(("rule", [line]))
            i += 1
            continue
        if line.lstrip().startswith(">"):
            quote = []
            while i < len(lines) and lines[i].lstrip().startswith(">"):
                quote.append(lines[i])
                i += 1
            out.append(("quote", quote))
            continue
        if "|" in line and i + 1 < len(lines) and re.match(r"^\s*\|?[\s:|-]+\|[\s:|-]*$", lines[i + 1]):
            table = []
            while i < len(lines) and "|" in lines[i]:
                table.append(lines[i])
                i += 1
            out.append(("table", table))
            continue
        if re.match(r"^\s*([-*+]|\d+[.)])\s+", line):
            listing = []
            while i < len(lines) and lines[i].strip():
                listing.append(lines[i])
                i += 1
            out.append(("list", listing))
            continue
        para = []
        while i < len(lines) and lines[i].strip() and not lines[i].startswith("```"):
            if re.match(r"^\s{0,3}#{1,6}\s", lines[i]) and para:
                break
            para.append(lines[i])
            i += 1
        out.append(("text", para))
    return out


def split_paragraphs(text: str) -> list[dict]:
    """Every block, with the anchor the ask affordance points at."""
    out: list[dict] = []
    for n, (kind, lines) in enumerate(_blocks(text), start=1):
        plain = " ".join(line.strip().lstrip("#>").strip() for line in lines).strip()
        out.append({"anchor": f"b{n}", "kind": kind, "text": plain[:400]})
    return out


def _list_html(lines: list[str]) -> str:
    ordered = bool(re.match(r"^\s*\d+[.)]\s+", lines[0]))
    items: list[str] = []
    for line in lines:
        match = re.match(r"^\s*(?:[-*+]|\d+[.)])\s+(.*)$", line)
        if match:
            items.append(inline(match.group(1).strip()))
        elif items:
            items[-1] += " " + inline(line.strip())
    tag = "ol" if ordered else "ul"
    body = "".join(f"<li>{item}</li>" for item in items)
    return f"<{tag}>{body}</{tag}>"


def _table_html(lines: list[str]) -> str:
    rows = [[cell.strip() for cell in line.strip().strip("|").split("|")] for line in lines]
    head, body = rows[0], rows[2:]
    out = ["<div class='scroller'><table><thead><tr>"]
    out += [f"<th>{inline(cell)}</th>" for cell in head]
    out.append("</tr></thead><tbody>")
    for row in body:
        out.append("<tr>" + "".join(f"<td>{inline(cell)}</td>" for cell in row) + "</tr>")
    out.append("</tbody></table></div>")
    return "".join(out)


def _fence_html(lines: list[str]) -> str:
    language = lines[0][3:].strip().lower()
    body = "\n".join(lines[1:])
    if language in DIAGRAM_LANGUAGES:
        return (
            f"<figure class='diagram'><figcaption>A {escape(language)} diagram — "
            "drawn in the real app, shown as its source here.</figcaption>"
            f"<pre>{escape(body)}</pre></figure>"
        )
    return f"<pre class='code'><code>{escape(body)}</code></pre>"


def render(text: str) -> str:
    """The document as HTML, one anchored element per block."""
    out: list[str] = []
    for n, (kind, lines) in enumerate(_blocks(text), start=1):
        anchor = f"b{n}"
        if kind == "heading":
            match = re.match(r"^\s{0,3}(#{1,6})\s+(.*)$", lines[0])
            level = min(6, len(match.group(1)) + 1) if match else 2
            body = inline(match.group(2).strip()) if match else ""
            out.append(f"<h{level} data-anchor='{anchor}'>{body}</h{level}>")
        elif kind == "rule":
            out.append("<hr>")
        elif kind == "quote":
            body = " ".join(line.lstrip().lstrip(">").strip() for line in lines)
            out.append(f"<blockquote data-anchor='{anchor}'>{inline(body)}</blockquote>")
        elif kind == "list":
            out.append(f"<div data-anchor='{anchor}'>{_list_html(lines)}</div>")
        elif kind == "table":
            out.append(f"<div data-anchor='{anchor}'>{_table_html(lines)}</div>")
        elif kind == "fence":
            out.append(f"<div data-anchor='{anchor}'>{_fence_html(lines)}</div>")
        else:
            out.append(f"<p data-anchor='{anchor}'>{inline(' '.join(line.strip() for line in lines))}</p>")
    return "\n".join(out)
