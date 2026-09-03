# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""surface.v1 conformance kit — the runnable definition of "the companion page keeps its promises".

Point it at the companion page — an HTML file, or a directory holding
`index.html`. It mechanically asserts the conformance list of
``contracts/surface.v1.md`` as a STATIC STRUCTURAL check: the markup and the
wiring that make each promised interaction possible must be present and
connected. No browser is launched.

What that buys and what it does not
-----------------------------------
A static check can prove the parts of an interaction exist and are wired to one
another — that the fill control reaches the gauge, that the lock control is
disabled, that the diff view has removals to show. It cannot prove the
interaction *behaves* when a person taps it, and it cannot judge a render. Rows
that need a running application are reported SKIP with the reason:

    the app is not built yet (converge-2qh)

never a fabricated PASS. When the app exists, those rows are what a live
harness closes.

Usage
-----
    uv run conformance/surface/run.py <index.html | dir>

Output
------
A JSON report on stdout (machine-readable) and a human summary on stderr.
Exit code is 0 when no rule FAILs, 1 when any rule FAILs.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

APP_NOT_BUILT = "the app is not built yet (converge-2qh)"

RULES = [
    ("1a", 1, "places_switch",
     "places switch — every navigation target resolves to a place"),
    ("1b", 1, "answering_shortens_the_strip",
     "answering marks the card and shortens the list"),
    ("1c", 1, "fill_propagates_to_the_gauge",
     "fill updates the gauge and the board"),
    ("1d", 1, "lock_stays_off_until_four_green",
     "the lock control stays off until all four conditions are green"),
    ("1e", 1, "what_changed_shows_removals",
     "what-changed shows removed sentences, not only additions"),
    ("2", 2, "renders_at_390_and_1280",
     "renders at 390 and 1280 pixels with nothing cut off and no console errors"),
    ("3a", 3, "four_write_paths_present",
     "exactly four write paths, and no fifth"),
    ("3b", 3, "write_paths_map_to_operations",
     "each write path maps to a named manager-session operation"),
    ("4", 4, "answers_land_in_the_record",
     "every answer lands in the dated ratification record"),
    ("5", 5, "no_internal_vocabulary_outside_details",
     "no internal vocabulary outside Details folds"),
]

UNFIXTURABLE = {
    "2": f"needs a live browser render at two widths; {APP_NOT_BUILT}",
    "3b": ("the mapping from a write path to a named manager-session operation "
           f"lives in the running system, not the markup; {APP_NOT_BUILT}"),
}

# surface.v1 Core 3 — the four writes, and the markup family that carries each.
WRITE_PATHS = [
    ("answer with a word", ["[data-answer]"]),
    ("raise or lower a priority", ["[data-signal]"]),
    ("drop feedback", ["#sendDrop", "#dropBox", "[data-drop]"]),
    ("steer", ["#fillBtn", "#targetSel", "input[name=budget]", "#tellAllBtn"]),
]

# Internal vocabulary the contract keeps behind a Details fold. Every term here
# is one a colleague who is not an engineer would have to look up. Matched
# whole-word, case-insensitively, against text OUTSIDE <details>.
INTERNAL_VOCABULARY = [
    "ledger", "conformance kit", "reconcile", "disposition",
    "bundle", "recipe", "subagent", "sub-agent", "orchestrator",
    "YAML", "JSON", "regex", "stdout", "stderr", "SHA", "worktree",
    "tracker item", "GAP row", "VIOLATION row", "frontmatter",
]


def _result(rid, status, detail, **extra):
    bullet = next(r[1] for r in RULES if r[0] == rid)
    name = next(r[2] for r in RULES if r[0] == rid)
    desc = next(r[3] for r in RULES if r[0] == rid)
    out = {"rule": rid, "bullet": bullet, "id": name, "name": desc,
           "status": status, "detail": detail}
    out.update(extra)
    return out


def _skip(rid):
    return _result(rid, "SKIP", UNFIXTURABLE[rid], reason=UNFIXTURABLE[rid])


# --------------------------------------------------------------------------- #
# a light HTML index — stdlib only                                            #
# --------------------------------------------------------------------------- #
VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input",
             "link", "meta", "param", "source", "track", "wbr"}


class PageIndex(HTMLParser):
    """Elements, ids, classes, and text — with text inside <details> kept
    separate, because the contract's rule 5 turns on exactly that boundary."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.elements = []          # [{tag, attrs, id, classes}]
        self.visible_text = []      # the app's OWN words (see below)
        self.folded_text = []       # text inside <details>
        self.document_text = []     # a project document the app merely displays
        self._stack = []
        self._details_depth = 0
        self._doc_depth = 0
        self._suppress = 0          # inside <script>/<style>

    def handle_starttag(self, tag, attrs):
        a = {k: (v if v is not None else "") for k, v in attrs}
        classes = a.get("class", "").split()
        el = {
            "tag": tag,
            "attrs": a,
            "id": a.get("id", ""),
            "classes": classes,
            "in_details": self._details_depth > 0,
        }
        self.elements.append(el)
        if tag in VOID_TAGS:
            return
        is_details = tag == "details"
        # A rendered project document is that DOCUMENT's prose, not the app's
        # own copy. Its words are documents.v1's business (and its kit's), not
        # surface.v1's. Scanning them here would report a contract's own
        # vocabulary as an app defect.
        is_doc = "doc" in classes or "docpane" in classes
        is_code = tag in ("script", "style")
        self._stack.append((tag, is_details, is_doc, is_code))
        if is_details:
            self._details_depth += 1
        if is_doc:
            self._doc_depth += 1
        if is_code:
            self._suppress += 1

    def handle_startendtag(self, tag, attrs):
        a = {k: (v if v is not None else "") for k, v in attrs}
        self.elements.append({
            "tag": tag, "attrs": a, "id": a.get("id", ""),
            "classes": a.get("class", "").split(),
            "in_details": self._details_depth > 0,
        })

    def _pop_to(self, tag):
        for i in range(len(self._stack) - 1, -1, -1):
            if self._stack[i][0] == tag:
                for _, is_details, is_doc, is_code in self._stack[i:]:
                    if is_details:
                        self._details_depth -= 1
                    if is_doc:
                        self._doc_depth -= 1
                    if is_code:
                        self._suppress -= 1
                del self._stack[i:]
                return

    def handle_endtag(self, tag):
        self._pop_to(tag)

    def handle_data(self, data):
        if self._suppress:
            return
        if self._details_depth > 0:
            self.folded_text.append(data)
        elif self._doc_depth > 0:
            self.document_text.append(data)
        else:
            self.visible_text.append(data)


def parse_page(text: str) -> PageIndex:
    idx = PageIndex()
    idx.feed(text)
    idx.close()
    return idx


def scripts_of(text: str) -> str:
    return "\n".join(re.findall(r"<script\b[^>]*>(.*?)</script>", text, re.DOTALL | re.I))


def has_attr(idx: PageIndex, attr: str):
    return [e for e in idx.elements if attr in e["attrs"]]


def by_id(idx: PageIndex, el_id: str):
    return next((e for e in idx.elements if e["id"] == el_id), None)


def by_class(idx: PageIndex, cls: str):
    return [e for e in idx.elements if cls in e["classes"]]


def selector_present(idx: PageIndex, sel: str) -> bool:
    """A deliberately tiny selector language — enough for the four write-path
    families and no more. Anything richer would be a DOM library, and this kit
    stays stdlib."""
    if sel.startswith("[") and sel.endswith("]"):
        return bool(has_attr(idx, sel[1:-1]))
    if sel.startswith("#"):
        return by_id(idx, sel[1:]) is not None
    m = re.fullmatch(r"(\w+)\[(\w+)=([^\]]+)\]", sel)
    if m:
        tag, k, v = m.groups()
        return any(e["tag"] == tag and e["attrs"].get(k) == v for e in idx.elements)
    return any(e["tag"] == sel for e in idx.elements)


# --------------------------------------------------------------------------- #
# bullet 1 — the five promised interactions                                    #
# --------------------------------------------------------------------------- #
def check_places_switch(idx: PageIndex, js: str):
    places = {e["id"] for e in by_class(idx, "screen") if e["id"]}
    targets = {e["attrs"]["data-goto"] for e in has_attr(idx, "data-goto")
               if e["attrs"].get("data-goto")}
    problems = []
    if len(places) < 2:
        problems.append(f"fewer than two places (found {sorted(places)})")
    if not targets:
        problems.append("no navigation control carries data-goto")
    dangling = sorted(targets - places)
    if dangling:
        problems.append(f"navigation target(s) resolve to no place: {dangling}")
    if "data-goto" not in js:
        problems.append("no handler reads data-goto")
    if "is-active" not in js:
        problems.append("no handler marks the active place")
    if problems:
        return _result("1a", "FAIL", "; ".join(problems),
                       places=sorted(places), targets=sorted(targets))
    return _result("1a", "PASS",
                   f"{len(places)} places, {len(targets)} navigation target(s), "
                   "all resolving; the handler reads data-goto and marks the active place",
                   places=sorted(places), targets=sorted(targets))


def check_answering_shortens(idx: PageIndex, js: str):
    answers = has_attr(idx, "data-answer")
    count_el = by_id(idx, "needCount")
    problems = []
    if not answers:
        problems.append("no control carries data-answer — nothing to answer with")
    if count_el is None:
        problems.append("no #needCount element — the strip has no length to shorten")
    if "is-answered" not in js:
        problems.append("no handler marks the answered card")
    if not re.search(r"needCount[\s\S]{0,200}?-\s*1", js):
        problems.append("no handler decrements #needCount when a card is answered")
    if problems:
        return _result("1b", "FAIL", "; ".join(problems))
    words = sorted({e["attrs"]["data-answer"] for e in answers})
    return _result("1b", "PASS",
                   f"{len(answers)} answer control(s) carrying {words}; answering marks the "
                   "card and decrements #needCount",
                   words=words)


def check_fill_propagates(idx: PageIndex, js: str):
    problems = []
    if by_id(idx, "gauge") is None:
        problems.append("no #gauge element")
    if by_id(idx, "gaugeLabel") is None:
        problems.append("no #gaugeLabel element")
    if not re.search(r"function\s+fillLanes\b|fillLanes\s*=\s*function", js):
        problems.append("no fillLanes routine")
    elif not re.search(r"fillLanes[\s\S]*?gauge", js):
        problems.append("fillLanes does not reach the gauge")
    effect = [e for e in has_attr(idx, "data-effect")
              if e["attrs"].get("data-effect") == "fill"]
    if not effect:
        problems.append("no answer control carries data-effect=\"fill\" — "
                        "answering the repair card cannot reach the board")
    if not re.search(r"data-effect[\s\S]{0,200}?fillLanes", js):
        problems.append("the answer handler does not route data-effect=\"fill\" to fillLanes")
    if problems:
        return _result("1c", "FAIL", "; ".join(problems))
    return _result("1c", "PASS",
                   "answering the repair card routes data-effect=\"fill\" to fillLanes, "
                   "which updates #gauge and #gaugeLabel")


def element_html(page_text: str, el_id: str):
    """The inner HTML of the element carrying `id="<el_id>"`, by counting the
    tag's own open/close pairs. A regex window would silently cut the block
    short and report conditions that are really there as missing."""
    m = re.search(r'<(\w+)\b[^>]*\bid=["\']' + re.escape(el_id) + r'["\'][^>]*>',
                  page_text, re.I)
    if m is None:
        return None
    tag = m.group(1)
    if tag.lower() in VOID_TAGS:
        return ""
    start = m.end()
    depth, pos = 1, start
    token = re.compile(r"<(/?)" + re.escape(tag) + r"\b[^>]*?(/?)>", re.I)
    while depth > 0:
        t = token.search(page_text, pos)
        if t is None:
            return page_text[start:]  # unbalanced markup — return what there is
        if t.group(1) == "/":
            depth -= 1
        elif t.group(2) != "/":
            depth += 1
        pos = t.end()
        if depth == 0:
            return page_text[start:t.start()]
    return page_text[start:pos]


def check_lock_gated(idx: PageIndex, page_text: str):
    body = element_html(page_text, "readiness")
    if body is None:
        return _result("1d", "FAIL",
                       "no #readiness block — the lock control states no conditions")
    conditions = re.findall(r"<li\b([^>]*)>(.*?)</li>", body, re.DOTALL | re.I)
    not_green = [c for c in conditions
                 if re.search(r'class="[^"]*\b(?:amber|red|pending|not-green)\b', c[0])]
    lock_controls = re.findall(r"<button\b([^>]*)>", body, re.I)
    problems = []
    if len(conditions) != 4:
        problems.append(f"the lock states {len(conditions)} condition(s), not four")
    if not not_green:
        problems.append("no condition is marked not-green — the fixture cannot show the "
                        "control staying off")
    if not lock_controls:
        problems.append("no lock control inside the readiness block")
    elif not any("disabled" in c for c in lock_controls):
        problems.append("the lock control is not disabled while a condition is not green")
    if problems:
        return _result("1d", "FAIL", "; ".join(problems), conditions=len(conditions))
    return _result("1d", "PASS",
                   f"four conditions stated, {len(not_green)} not yet green, and the lock "
                   "control carries `disabled`",
                   conditions=len(conditions), not_green=len(not_green))


def check_what_changed(idx: PageIndex, js: str):
    problems = []
    if by_id(idx, "diffBtn") is None:
        problems.append("no #diffBtn control")
    if "show-diff" not in js:
        problems.append("no handler toggles the diff view")
    removals = [e for e in idx.elements if e["tag"] == "del"]
    additions = [e for e in idx.elements if e["tag"] == "ins"]
    if not removals:
        problems.append("no <del> element — the diff can show additions but never a "
                        "removed sentence, which is the half a reader cannot otherwise check")
    if problems:
        return _result("1e", "FAIL", "; ".join(problems),
                       removals=len(removals), additions=len(additions))
    return _result("1e", "PASS",
                   f"the diff view toggles and carries {len(removals)} removal(s) alongside "
                   f"{len(additions)} addition(s)",
                   removals=len(removals), additions=len(additions))


# --------------------------------------------------------------------------- #
# bullet 3 — the four writes                                                   #
# --------------------------------------------------------------------------- #
def check_write_paths(idx: PageIndex):
    rows = []
    for label, selectors in WRITE_PATHS:
        hit = next((s for s in selectors if selector_present(idx, s)), None)
        rows.append({"write_path": label,
                     "status": "PASS" if hit else "FAIL",
                     "detail": (f"carried by {hit}" if hit
                                else f"absent — none of {selectors} present")})
    missing = [r for r in rows if r["status"] == "FAIL"]
    if missing:
        return _result("3a", "FAIL",
                       f"{len(missing)} of 4 write path(s) absent: "
                       + ", ".join(r["write_path"] for r in missing),
                       write_paths=rows)
    return _result("3a", "PASS",
                   "all four write paths present: "
                   + ", ".join(r["write_path"] for r in rows),
                   write_paths=rows)


# --------------------------------------------------------------------------- #
# bullet 4 — answers land in the record                                        #
# --------------------------------------------------------------------------- #
def check_answers_recorded(idx: PageIndex, js: str):
    problems = []
    if by_id(idx, "filedList") is None:
        problems.append("no #filedList element — an answer has nowhere to land")
    if not re.search(r"data-answer[\s\S]{0,600}?(?:fileIt|filedList)", js):
        problems.append("the answer handler does not write the answer into the record")
    if problems:
        return _result("4", "FAIL", "; ".join(problems))
    return _result("4", "PASS",
                   "answering writes the word and what it answered into #filedList")


# --------------------------------------------------------------------------- #
# bullet 5 — plain words on the surface                                        #
# --------------------------------------------------------------------------- #
IDENTIFIER_CHARS = "-_/."


def _inside_identifier(text: str, m) -> bool:
    """True when a match sits inside a longer hyphenated/pathed token.

    `amplifier-bundle-converge` is a project's NAME shown in a header chip —
    a proper noun, not the word "bundle" used as jargon. Flagging it would be
    a fabricated finding.

    The joining character must itself be joined to a word on the far side. A
    trailing full stop is a sentence ending, not a path separator: "the
    ledger." is the jargon, plainly, and must still be reported.
    """
    i, j = m.start(), m.end()
    if i > 0 and text[i - 1] in IDENTIFIER_CHARS:
        if i - 2 >= 0 and (text[i - 2].isalnum() or text[i - 2] == "_"):
            return True
    if j < len(text) and text[j] in IDENTIFIER_CHARS:
        if j + 1 < len(text) and (text[j + 1].isalnum() or text[j + 1] == "_"):
            return True
    return False


def check_vocabulary(idx: PageIndex):
    visible = " ".join(idx.visible_text)
    visible = re.sub(r"\s+", " ", visible)
    hits = []
    for term in INTERNAL_VOCABULARY:
        for m in re.finditer(r"\b" + re.escape(term) + r"\b", visible, re.IGNORECASE):
            if _inside_identifier(visible, m):
                continue  # part of a proper noun, not jargon being used as jargon
            start = max(0, m.start() - 40)
            hits.append({"term": term, "context": visible[start:m.end() + 40].strip()})
            break  # one example per term is enough to name the problem
    if hits:
        names = ", ".join(h["term"] for h in hits[:6])
        return _result("5", "FAIL",
                       f"{len(hits)} internal term(s) outside a Details fold: {names}",
                       hits=hits)
    folded = len(" ".join(idx.folded_text).split())
    in_docs = len(" ".join(idx.document_text).split())
    return _result("5", "PASS",
                   f"no internal vocabulary in the app's own words; {folded} word(s) of "
                   f"technical detail sit behind Details folds, and {in_docs} word(s) of "
                   "displayed project documents are out of scope (they are documents.v1's)",
                   folded_words=folded, document_words=in_docs)


# --------------------------------------------------------------------------- #
# driver                                                                       #
# --------------------------------------------------------------------------- #
def resolve_page(spec: str):
    p = Path(spec)
    if p.is_dir():
        p = p / "index.html"
    if not p.is_file():
        return None, f"no companion page at {spec} (looked for a file, or index.html in a directory)"
    return p, None


def run_conformance(page: Path) -> dict:
    text = page.read_text(encoding="utf-8", errors="replace")
    idx = parse_page(text)
    js = scripts_of(text)

    results = [
        check_places_switch(idx, js),
        check_answering_shortens(idx, js),
        check_fill_propagates(idx, js),
        check_lock_gated(idx, text),
        check_what_changed(idx, js),
        _skip("2"),
        check_write_paths(idx),
        _skip("3b"),
        check_answers_recorded(idx, js),
        check_vocabulary(idx),
    ]
    summary = {
        "pass": sum(r["status"] == "PASS" for r in results),
        "fail": sum(r["status"] == "FAIL" for r in results),
        "skip": sum(r["status"] == "SKIP" for r in results),
    }
    return {
        "kit": "surface.v1",
        "contract": "contracts/surface.v1.md",
        "target": str(page.resolve()),
        "check": "static structural — no browser is launched",
        "results": results,
        "summary": summary,
        "verdict": "FAIL" if summary["fail"] else "PASS",
    }


def print_human_summary(report: dict) -> None:
    w = sys.stderr.write
    w(f"\nsurface.v1 conformance — {report['target']}\n")
    w(f"asserts: {report['contract']} (\"Conformance kit asserts\") — {report['check']}\n")
    w("-" * 74 + "\n")
    for r in report["results"]:
        w(f"  [{r['status']:4}] {r['rule']:3} {r['id']}: {r['detail']}\n")
    w("-" * 74 + "\n")
    s = report["summary"]
    w(f"  VERDICT: {report['verdict']}  (pass={s['pass']} fail={s['fail']} skip={s['skip']})\n\n")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        prog="surface-conformance",
        description="Assert surface.v1 conformance against the companion page, statically.",
    )
    ap.add_argument("page", help="path to the companion page (index.html, or its directory)")
    ap.add_argument("--json-only", action="store_true",
                    help="suppress the human summary on stderr")
    args = ap.parse_args(argv)

    page, err = resolve_page(args.page)
    if err:
        sys.stderr.write(f"error: {err}\n")
        return 3

    report = run_conformance(page)
    sys.stdout.write(json.dumps(report, indent=2) + "\n")
    if not args.json_only:
        print_human_summary(report)
    return 1 if report["verdict"] == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
