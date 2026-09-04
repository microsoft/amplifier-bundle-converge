# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""SUPERSEDED 2026-09-03 — retired kit, kept for the record. See README.md.

surface.v1 conformance kit — the runnable definition of "the companion app keeps its promises".

Point it at the **companion app**: either a running server (a URL) or a
directory of pages rendered from it (`render.py` writes one). It mechanically
asserts the conformance list of ``contracts/surface.v1.md`` against what the
app actually serves.

What this checks, and what it does not
--------------------------------------
The app is server-rendered and carries no script at all, on purpose. So the
promises are kept by *what a page states and where its forms post*, not by
handlers wiring elements together. Every rule here is written against that:

* a place is a link to a real route, and the route must exist;
* the strip's stated length must equal the number of cards on it, so answering
  one demonstrably shortens it;
* the lock control's `disabled` must agree with its own four conditions;
* a write is a form posting to one of exactly four routes, and the surface
  must name the manager-session operation each one is.

An assertion that genuinely needs a browser — a render at two widths, with a
console — reports SKIP with the reason, never a fabricated PASS.

Numbering
---------
Rule numbering follows the contract's **Core clause** numbers, as documents.v1
clause 5 asks: rule 7 judges Core 7, so a failing rule names the clause it
breaks. Where one clause carries several independent promises the kit emits one
row per promise, lettered inside the clause (8a, 8b, 8c). Every one of the ten
Core clauses has a row, and the self-test fails if one does not.

The kit was numbered to the contract's *Conformance kit asserts* bullets until
2026-09-03, when the steward ratified the Core-clause anchor (see
``docs/workflow/owner-ratifications-2026-09-03.md``, call 2). Under the bullets,
five bullets covered ten clauses and Core 4 and Core 5 had no row at all — and a
missing row is invisible, because nothing looks wrong. Rules 4 and 5 are those
rows.

Usage
-----
    uv run conformance/surface/run.py http://127.0.0.1:8091
    uv run conformance/surface/run.py <dir written by render.py>

Output
------
A JSON report on stdout (machine-readable) and a human summary on stderr.
Exit code is 0 when no rule FAILs, 1 when any rule FAILs.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlsplit

# --------------------------------------------------------------------------- #
# the contract's own vocabularies                                              #
# --------------------------------------------------------------------------- #

#: surface.v1 Core 8, first half — the words for a contract checked against
#: reality. Fixed by the contract, not by this kit.
CONTRACT_STATES = ("Kept", "Not yet", "Broken", "Pinned open", "Can't check")

#: surface.v1 Core 8, first half — the words for a lane.
LANE_STATES = ("Working", "Quiet", "Silent — may have died")

#: documents.v1 clause 6 and 10 — a document's own state, and a piece of work's.
DOCUMENT_STATES = ("Draft", "Locked")
WORK_STATES = ("Truly ready", "Waiting on you", "Working", "Stuck", "Done")

#: surface.v1 Core 7 — the lock gate says one of two words about a condition.
GATE_WORDS = ("Green", "Not yet")

#: Every word the surface is allowed to use for a state.
SURFACE_WORDS = tuple(
    dict.fromkeys(CONTRACT_STATES + LANE_STATES + DOCUMENT_STATES + WORK_STATES + GATE_WORDS)
)

#: surface.v1 Core 3 — the four writes, and how a route's name gives it away.
WRITE_FAMILIES = (
    ("answer with a word", r"answer"),
    ("raise or lower a priority", r"priorit|signal"),
    ("drop feedback", r"feedback|drop"),
    ("steer", r"steer"),
)

#: Internal vocabulary the contract keeps behind a Details fold. Every term is
#: one a colleague who is not an engineer would have to look up. Matched
#: whole-word, case-insensitively, against the app's OWN words.
INTERNAL_VOCABULARY = [
    "ledger", "conformance kit", "reconcile", "disposition",
    "bundle", "recipe", "subagent", "sub-agent", "orchestrator",
    "YAML", "JSON", "regex", "stdout", "stderr", "SHA", "worktree",
    "tracker item", "GAP row", "VIOLATION row", "frontmatter",
]

#: A control that stops something. surface.v1 Core 9: "Stopping something is
#: never a board button."
STOP_WORDS = re.compile(r"\b(stop|kill|abort|terminate|halt|cancel)\b", re.IGNORECASE)

#: Rows a static read of served pages cannot close, with the reason each says.
#: Neither reason may claim the app is unbuilt — it ships in src/amplifier_converge/.
UNFIXTURABLE = {
    "10": (
        "needs a real browser at 390 and 1280 pixels with a console, and this kit "
        "launches none. The app asserts the same promise structurally against its "
        "stylesheet in tests/test_renders_at_both_widths.py; a live render at two "
        "widths remains unchecked here (converge-ium)"
    ),
}

RULES = [
    ("1a", 1, "places_switch",
     "places switch — every place link resolves to a page the app serves"),
    ("1b", 1, "answering_shortens_the_strip",
     "answering marks the card and shortens the list"),
    ("2", 2, "answers_land_in_the_record",
     "every answer lands in the dated ratification record"),
    ("3a", 3, "exactly_four_write_paths",
     "exactly four write paths, and no fifth"),
    ("3b", 3, "write_paths_map_to_operations",
     "each write path maps to a named manager-session operation"),
    ("4", 4, "no_data_of_its_own",
     "no data of its own — every page reads back from the project, and says so"),
    ("5", 5, "proposals_look_the_same_whoever_proposed",
     "a proposal shows what changes, the evidence, and what does not change"),
    ("6", 6, "what_changed_shows_removals",
     "what-changed shows removed sentences, not only additions"),
    ("7", 7, "lock_stays_off_until_four_green",
     "the lock control stays off until all four conditions are green"),
    ("8a", 8, "the_surface_says_only_plain_state_words",
     "every state the app shows is one of the plain words"),
    ("8b", 8, "both_state_vocabularies_are_spoken",
     "the contract vocabulary and the lane vocabulary are both actually used"),
    ("8c", 8, "no_internal_vocabulary_outside_details",
     "no internal vocabulary outside Details folds"),
    ("9a", 9, "fill_updates_the_gauge_and_the_board",
     "fill updates the gauge and the board"),
    ("9b", 9, "the_whole_operation_in_view",
     "the whole operation in view, and stopping is never a board button"),
    ("10", 10, "renders_at_390_and_1280",
     "renders at 390 and 1280 pixels with nothing cut off and no console errors"),
]


def _rule(rid):
    return next(r for r in RULES if r[0] == rid)


def _result(rid, status, detail, **extra):
    _, clause, name, desc = _rule(rid)
    out = {"rule": rid, "clause": clause, "id": name, "name": desc,
           "status": status, "detail": detail}
    if status == "SKIP":
        out["reason"] = detail
    out.update(extra)
    return out


def _skip(rid, reason=None):
    return _result(rid, "SKIP", reason or UNFIXTURABLE[rid])


# --------------------------------------------------------------------------- #
# a small HTML tree — stdlib only                                              #
# --------------------------------------------------------------------------- #
VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input",
             "link", "meta", "param", "source", "track", "wbr"}

#: Classes marking text the app is *displaying* rather than saying: a rendered
#: project document, and words quoted from the project. Their wording is the
#: document's business (documents.v1's, and its kit's), not the app's.
BORROWED_CLASSES = ("doc", "docpane", "quote")


class Node:
    __slots__ = ("tag", "attrs", "classes", "id", "parent", "children", "own_text")

    def __init__(self, tag="", attrs=None, parent=None):
        self.tag = tag
        self.attrs = attrs or {}
        self.classes = self.attrs.get("class", "").split()
        self.id = self.attrs.get("id", "")
        self.parent = parent
        self.children = []
        self.own_text = []

    # -- walking ---------------------------------------------------------
    def walk(self):
        for child in self.children:
            yield child
            yield from child.walk()

    def find(self, tag=None, cls=None, node_id=None, attr=None):
        out = []
        for node in self.walk():
            if tag and node.tag != tag:
                continue
            if cls and cls not in node.classes:
                continue
            if node_id and node.id != node_id:
                continue
            if attr and attr not in node.attrs:
                continue
            out.append(node)
        return out

    def first(self, **kw):
        found = self.find(**kw)
        return found[0] if found else None

    def ancestors(self):
        node = self.parent
        while node is not None:
            yield node
            node = node.parent

    def inside(self, tag=None, cls=None):
        for node in self.ancestors():
            if tag and node.tag == tag:
                return True
            if cls and cls in node.classes:
                return True
        return False

    # -- text ------------------------------------------------------------
    def text(self):
        parts = list(self.own_text)
        for child in self.children:
            if child.tag in ("script", "style"):
                continue
            parts.append(child.text())
        return re.sub(r"\s+", " ", "".join(parts)).strip()


class TreeParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node("#document")
        self._cur = self.root

    def handle_starttag(self, tag, attrs):
        a = {k: (v if v is not None else "") for k, v in attrs}
        node = Node(tag, a, self._cur)
        self._cur.children.append(node)
        if tag not in VOID_TAGS:
            self._cur = node

    def handle_startendtag(self, tag, attrs):
        a = {k: (v if v is not None else "") for k, v in attrs}
        self._cur.children.append(Node(tag, a, self._cur))

    def handle_endtag(self, tag):
        node = self._cur
        while node is not self.root:
            if node.tag == tag:
                self._cur = node.parent or self.root
                return
            node = node.parent or self.root
        # a stray close tag closes nothing — markup this broken is its own bug,
        # and the rules below will report what is missing rather than crash.

    def handle_data(self, data):
        self._cur.own_text.append(data)


class Page:
    """One page the app served, parsed once."""

    def __init__(self, route: str, source: str, html: str):
        self.route = route
        self.source = source
        self.html = html
        parser = TreeParser()
        parser.feed(html)
        parser.close()
        self.root = parser.root

    # -- shorthand -------------------------------------------------------
    def find(self, **kw):
        return self.root.find(**kw)

    def first(self, **kw):
        return self.root.first(**kw)

    def label_of(self, node):
        return node.text()

    def own_words(self) -> str:
        """The app's OWN sentences: not a rendered project document, not a
        quotation of the project's words, not text behind a Details fold."""
        parts = []
        for node in self.root.walk():
            if not node.own_text:
                continue
            if node.tag in ("script", "style", "title"):
                continue
            if node.inside(tag="details") or node.tag == "details":
                continue
            if any(node.inside(cls=c) for c in BORROWED_CLASSES):
                continue
            if any(c in node.classes for c in BORROWED_CLASSES):
                continue
            parts.append("".join(node.own_text))
        return re.sub(r"\s+", " ", " ".join(parts)).strip()

    def folded_words(self) -> str:
        parts = []
        for fold in self.find(tag="details"):
            parts.append(fold.text())
        return re.sub(r"\s+", " ", " ".join(parts)).strip()

    # -- shapes ----------------------------------------------------------
    def is_document_page(self) -> bool:
        return bool([n for n in self.find(cls="doc") if n.tag == "article"])

    def is_operation_page(self) -> bool:
        return self.first(node_id="lanes") is not None or self.route.rstrip("/") == "/operation"

    def is_landing_page(self) -> bool:
        if self.route in ("/", ""):
            return True
        return bool(self.find(cls="decision")) or bool(self.find(cls="strip-empty"))

    def forms(self):
        out = []
        for form in self.find(tag="form"):
            method = form.attrs.get("method", "get").lower()
            out.append((form, method, form.attrs.get("action", "")))
        return out

    def post_actions(self):
        return {action for _, method, action in self.forms() if method == "post"}

    def controls(self):
        """Every thing a person can press: buttons, and links styled as one."""
        out = list(self.find(tag="button"))
        out += [a for a in self.find(tag="a") if "word" in a.classes]
        return out


# --------------------------------------------------------------------------- #
# targets: a running app, or the pages rendered from it                        #
# --------------------------------------------------------------------------- #
DEFAULT_ROUTES = ("/", "/direction", "/operation")
MAX_PAGES = 30


def _path_of(href: str) -> str:
    split = urlsplit(href)
    return split.path or "/"


def load_from_url(base: str, timeout: float = 10.0):
    """Fetch the places, then everything they link to inside the app."""
    from urllib.error import URLError
    from urllib.request import urlopen

    seen = {}
    order = []
    problems = []

    def fetch(path: str):
        url = urljoin(base, path)
        try:
            with urlopen(url, timeout=timeout) as response:  # noqa: S310 - loopback app
                body = response.read().decode("utf-8", errors="replace")
                return body, response.status
        except URLError as exc:  # pragma: no cover - depends on a live server
            problems.append(f"{path}: {exc}")
            return None, None
        except OSError as exc:  # pragma: no cover
            problems.append(f"{path}: {exc}")
            return None, None

    def add(path: str):
        path = _path_of(path) if path.startswith("http") else path
        path = path.split("#", 1)[0] or "/"  # a fragment is the same page, not another one
        key = path
        if key in seen or len(seen) >= MAX_PAGES:
            return
        body, status = fetch(path)
        if body is None:
            return
        if status and status >= 400:
            problems.append(f"{path}: HTTP {status}")
            return
        page = Page(path.split("?")[0] or "/", urljoin(base, path), body)
        seen[key] = page
        order.append(page)

    for route in DEFAULT_ROUTES:
        add(route)
    # the places the app itself names, and every document or proposal they link to
    links = []
    for page in list(order):
        for anchor in page.find(tag="a"):
            href = anchor.attrs.get("href", "")
            if not href or href.startswith(("#", "mailto:", "http")):
                continue
            path = href
            if path.startswith("/direction") or path.startswith("/operation"):
                links.append(path)
    for path in dict.fromkeys(links):
        if path.endswith("/ask") or "/ask?" in path:
            continue  # a form, reached from a document; not a place of its own
        add(path)

    return order, problems


def load_from_directory(directory: Path):
    """A page set written by render.py — or a lone page, for a quick look."""
    manifest_path = directory / "pages.json"
    if manifest_path.is_file():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        pages = []
        for entry in manifest.get("pages", []):
            path = directory / entry["file"]
            if not path.is_file():
                raise FileNotFoundError(f"{manifest_path} names {entry['file']}, which is not here")
            pages.append(Page(entry.get("route", "/"), str(path),
                              path.read_text(encoding="utf-8", errors="replace")))
        return pages, manifest
    index = directory / "index.html"
    if index.is_file():
        return [Page("/", str(index), index.read_text(encoding="utf-8", errors="replace"))], {}
    raise FileNotFoundError(
        f"{directory} holds neither pages.json (write one with render.py) nor index.html"
    )


def resolve_target(spec: str):
    if spec.startswith(("http://", "https://")):
        pages, problems = load_from_url(spec)
        if not pages:
            raise ConnectionError(
                f"nothing answered at {spec} — start the app first "
                f"(uv run --extra web amplifier-converge web --repo . --port 8091). "
                + "; ".join(problems)
            )
        return pages, {"mode": "running app", "problems": problems}
    path = Path(spec)
    if path.is_dir():
        pages, manifest = load_from_directory(path)
        manifest = dict(manifest)
        manifest.setdefault("mode", "rendered pages")
        return pages, manifest
    if path.is_file():
        return [Page("/", str(path), path.read_text(encoding="utf-8", errors="replace"))], {
            "mode": "one page"
        }
    raise FileNotFoundError(
        f"no companion app at {spec} — give a URL, a directory written by render.py, or one page"
    )


# --------------------------------------------------------------------------- #
# clauses 1, 6, 7 and 9 — the promised interactions                            #
# --------------------------------------------------------------------------- #
def check_places_switch(pages):
    if len(pages) < 2:
        return _skip("1a", "one page cannot show places switching — point the kit at the "
                           "running app, or at a page set written by render.py")
    routes = {p.route.rstrip("/") or "/" for p in pages}
    problems = []
    seen_targets = set()
    for page in pages:
        places = [a for a in page.find(tag="a") if "place" in a.classes]
        if len(places) < 2:
            problems.append(f"{page.route}: fewer than two places in the rail")
            continue
        for anchor in places:
            target = _path_of(anchor.attrs.get("href", "")).rstrip("/") or "/"
            seen_targets.add(target)
            if target not in routes:
                problems.append(f"{page.route}: place “{anchor.text()}” points at {target}, "
                                "which the app did not serve")
        marked = [a for a in places if "is-on" in a.classes]
        if len(marked) != 1:
            problems.append(f"{page.route}: {len(marked)} places are marked as the one you are on, not one")
            continue
        here = _path_of(marked[0].attrs.get("href", "")).rstrip("/") or "/"
        mine = page.route.rstrip("/") or "/"
        if here != mine and not mine.startswith(here.rstrip("/") + "/"):
            problems.append(f"{page.route}: the rail marks {here} as where you are")
    if problems:
        return _result("1a", "FAIL", "; ".join(problems[:6]),
                       routes=sorted(routes), place_targets=sorted(seen_targets))
    return _result("1a", "PASS",
                   f"{len(seen_targets)} places, all resolving, and every one of {len(pages)} "
                   "pages marks the place you are on",
                   routes=sorted(routes), place_targets=sorted(seen_targets))


COUNT_IN_WORDS = re.compile(r"\b(\d+)\s+things?\s+needs?\s+your\s+word", re.IGNORECASE)


def check_answering_shortens(pages):
    landing = next((p for p in pages if p.is_landing_page()), None)
    if landing is None:
        return _result("1b", "FAIL", "no page carries the short list")
    cards = landing.find(cls="decision")
    problems = []

    stated = None
    heading = COUNT_IN_WORDS.search(landing.root.text())
    if heading:
        stated = int(heading.group(1))
    badge = None
    for node in landing.find(cls="count"):
        text = node.text().strip()
        if text.isdigit():
            badge = int(text)
    if stated is None and badge is None and cards:
        problems.append("the list never says how long it is, so answering cannot be seen to shorten it")
    for name, value in (("the heading", stated), ("the rail badge", badge)):
        if value is not None and value != len(cards):
            problems.append(f"{name} says {value}, but {len(cards)} card(s) are on the list")

    if not cards:
        if landing.first(cls="strip-empty") is None:
            problems.append("nothing needs your word, but the page does not say so as good news")
        if badge:
            problems.append(f"the rail badge says {badge} with no cards on the list")
    if len(cards) > 5:
        problems.append(f"{len(cards)} cards on the list — surface.v1 Core 1 says at most five")

    for card in cards:
        forms = [(f, m, a) for f, m, a in _forms_of(card) if m == "post"]
        if not forms:
            problems.append(f"a card (“{_heading_of(card)}”) offers no way to answer it")
            continue
        if not any(_field_value(f, "back") for f, _, _ in forms):
            problems.append(f"the answer on “{_heading_of(card)}” does not say where to come back to, "
                            "so the shortened list is never re-drawn")
        if not any(_submit_labels(f) for f, _, _ in forms):
            problems.append(f"the answer on “{_heading_of(card)}” has no word to press")

    if problems:
        return _result("1b", "FAIL", "; ".join(problems[:6]), cards=len(cards), stated=stated)
    return _result("1b", "PASS",
                   f"{len(cards)} card(s) on the list, and the list says so in {'both places' if (stated is not None and badge is not None) else 'its own words'}; "
                   "each card answers by posting and comes back to the list",
                   cards=len(cards), stated=stated, badge=badge)


GAUGE = re.compile(r"(\d+)\s+of\s+(\d+)\s+running", re.IGNORECASE)


def check_fill_updates_the_board(pages):
    operation = next((p for p in pages if p.is_operation_page()), None)
    if operation is None:
        return _result("9a", "FAIL", "no page shows the lanes")
    lanes = operation.first(node_id="lanes")
    if lanes is None:
        return _result("9a", "FAIL", "the operation page states no gauge for the lanes")
    text = lanes.text()
    match = GAUGE.search(text)
    if match is None:
        return _skip("9a", "the lanes cannot be read in this target, so the gauge states no "
                           f"number to check against the fill control — the page says: “{text[:120]}”")
    running, intended = int(match.group(1)), int(match.group(2))
    fill = [f for f, m, _ in _forms_of(lanes) if m == "post"
            and ("fill" in " ".join(_submit_labels(f)).lower()
                 or "fill" in (_field_value(f, "ask") or "").lower())]
    short_by = intended - running
    if short_by > 0 and not fill:
        return _result("9a", "FAIL",
                       f"{running} of {intended} lanes are running and the gauge says so, but the "
                       "board offers no way to fill the rest",
                       running=running, intended=intended)
    if short_by <= 0 and fill:
        return _result("9a", "FAIL",
                       f"every lane you asked for is running ({running} of {intended}), yet the board "
                       "still offers to fill them",
                       running=running, intended=intended)
    if fill:
        action = fill[0].attrs.get("action", "")
        if not action:
            return _result("9a", "FAIL", "the fill control posts nowhere")
        return _result("9a", "PASS",
                       f"the gauge says {running} of {intended} running, and the fill control posts "
                       f"to {action}, which is where the board is changed",
                       running=running, intended=intended, fill_action=action)
    return _result("9a", "PASS",
                   f"the gauge says {running} of {intended} running — nothing is short, and the board "
                   "offers no fill it does not need",
                   running=running, intended=intended)


def check_lock_gated(pages):
    gates = []
    for page in pages:
        for gate in page.find(cls="gate"):
            if gate.tag == "ul":
                gates.append((page, gate))
    if not gates:
        docs = [p for p in pages if p.is_document_page()]
        if not docs:
            return _skip("7", "no document page is in this target, so no lock gate states its "
                               "conditions")
        locked = [p for p in docs if "locked" in p.root.text().lower()]
        if locked:
            return _skip("7", f"every document in this target is already locked ({len(locked)} of "
                               f"{len(docs)}), so no gate is drawn — point the kit at a project with "
                               "a draft document to check the gate")
        return _result("7", "FAIL",
                       f"{len(docs)} document page(s) and not one states the four conditions for locking")
    problems = []
    checked = []
    for page, gate in gates:
        conditions = [li for li in gate.find(tag="li")]
        words = []
        for condition in conditions:
            state = condition.first(cls="state")
            words.append(state.text().strip() if state else "")
        card = gate.parent
        controls = [c for c in (card.find(tag="button") if card else [])
                    if "lock" in c.text().strip().lower()]
        green = [w for w in words if w == GATE_WORDS[0]]
        if len(conditions) != 4:
            problems.append(f"{page.route}: the lock states {len(conditions)} condition(s), not four")
        unknown = [w for w in words if w not in GATE_WORDS]
        if unknown:
            problems.append(f"{page.route}: a condition says {unknown[:2]}, which is neither "
                            f"“{GATE_WORDS[0]}” nor “{GATE_WORDS[1]}”")
        if not controls:
            problems.append(f"{page.route}: the four conditions are stated with no lock control beside them")
            continue
        disabled = any("disabled" in c.attrs for c in controls)
        all_green = len(conditions) == 4 and len(green) == 4
        if all_green and disabled:
            problems.append(f"{page.route}: all four conditions are green and the lock control is "
                            "still off")
        if not all_green and not disabled:
            problems.append(f"{page.route}: {len(green)} of {len(conditions)} conditions are green and "
                            "the lock control is live")
        checked.append({"page": page.route, "conditions": len(conditions),
                        "green": len(green), "control_off": disabled})
    if problems:
        return _result("7", "FAIL", "; ".join(problems[:6]), gates=checked)
    return _result("7", "PASS",
                   f"{len(checked)} lock gate(s), each stating four conditions, and each control off "
                   "exactly when a condition is not yet green",
                   gates=checked)


WHAT_CHANGED = "what changed since you last read this"


def check_what_changed(pages):
    documents = [p for p in pages if p.is_document_page()]
    if not documents:
        return _skip("6", "no document page is in this target, so nothing states what changed")
    problems = []
    removed = added = 0
    lists = 0
    for page in documents:
        labels = [n.text().strip().lower() for n in page.find(cls="lbl")]
        if not any(WHAT_CHANGED in label for label in labels):
            problems.append(f"{page.route}: the document does not say what changed since you last read it")
            continue
        for diff in page.find(cls="diff"):
            lists += 1
            items = diff.find(tag="li")
            marked_removed = [i for i in items if "removed" in i.classes]
            marked_added = [i for i in items if "added" in i.classes]
            removed += len(marked_removed)
            added += len(marked_added)
            if items and not marked_removed and not marked_added:
                problems.append(f"{page.route}: the sentences that changed are listed without saying "
                                "which were taken away and which were added")
    if problems:
        return _result("6", "FAIL", "; ".join(problems[:6]), removed=removed, added=added)
    if not lists:
        return _skip("6", "no document in this target has changed since it was last read, so no "
                           "sentence-by-sentence list is drawn — mark a document read, change a "
                           "sentence, and run again (render.py --exercise-what-changed does exactly "
                           "that against a throwaway copy)")
    if not removed:
        return _skip("6", f"{lists} change list(s) are drawn and every sentence in them was added — "
                           "nothing has been taken away yet, so the half a reader cannot otherwise "
                           "check is not on screen to check")
    return _result("6", "PASS",
                   f"{removed} removed sentence(s) are shown alongside {added} added, each marked as "
                   f"which it is, across {lists} change list(s)",
                   removed=removed, added=added, lists=lists)


# --------------------------------------------------------------------------- #
# clause 3 — the four writes                                                   #
# --------------------------------------------------------------------------- #
def _forms_of(node):
    out = []
    for form in node.find(tag="form"):
        out.append((form, form.attrs.get("method", "get").lower(), form.attrs.get("action", "")))
    return out


def _field_value(form, name):
    for field in form.find(tag="input"):
        if field.attrs.get("name") == name:
            return field.attrs.get("value", "")
    return None


def _field_names(form):
    names = set()
    for tag in ("input", "textarea", "select", "button"):
        for field in form.find(tag=tag):
            if field.attrs.get("name"):
                names.add(field.attrs["name"])
    return names


def _submit_labels(form):
    labels = []
    for button in form.find(tag="button"):
        labels.append(button.attrs.get("value") or button.text().strip())
    for field in form.find(tag="input"):
        if field.attrs.get("type") == "submit":
            labels.append(field.attrs.get("value", ""))
    return [label for label in labels if label]


def _heading_of(node):
    for tag in ("h1", "h2", "h3", "h4"):
        found = node.first(tag=tag)
        if found:
            return found.text()[:60]
    return node.text()[:60]


def check_write_paths(pages, write_prefix, changes_nothing):
    actions = {}
    for page in pages:
        for form, method, action in page.forms():
            if method != "post":
                continue
            actions.setdefault(action, []).append(page.route)
    writes = sorted(a for a in actions if a.startswith(write_prefix))
    others = sorted(a for a in actions if not a.startswith(write_prefix))
    undeclared = [a for a in others
                  if not any(fnmatch.fnmatch(a, pattern) for pattern in changes_nothing)]

    problems = []
    if not actions:
        return _result("3a", "FAIL", "no page offers a way to write anything")
    if len(writes) != 4:
        problems.append(f"{len(writes)} write path(s) under {write_prefix}, not four: {writes}")
    missing = [label for label, pattern in WRITE_FAMILIES
               if not any(re.search(pattern, a, re.IGNORECASE) for a in writes)]
    if missing:
        problems.append("no write path for: " + ", ".join(missing))
    for action in undeclared:
        problems.append(f"{action} also changes something and is not one of the four "
                        f"(declare it with --changes-nothing if it changes nothing)")
    if problems:
        return _result("3a", "FAIL", "; ".join(problems[:6]),
                       write_paths=writes, other_posts=others)
    detail = f"exactly four write paths, all under {write_prefix}: " + ", ".join(writes)
    if others:
        detail += (f"; {len(others)} further POST(s) declared to change nothing: "
                   + ", ".join(others))
    return _result("3a", "PASS", detail, write_paths=writes, other_posts=others)


#: How the surface names one write: `<name> → <where it lands> — manager operation <op>`.
#: Read from one line at a time, not from a page-wide blob, so two mappings can
#: never run into each other and be read as one.
MAPPING = re.compile(
    r"^([a-z][\w-]*)\s*(?:→|->)\s*(.+?)\s+[—–-]\s+manager operation\s+(.+)$",
    re.IGNORECASE,
)


def read_declared_writes(pages):
    """The surface's own statement of what each write is, from its Details fold."""
    declared = {}
    for page in pages:
        for fold in page.find(tag="details"):
            for node in fold.walk():
                if not node.own_text:
                    continue
                match = MAPPING.match(node.text())
                if match is None:
                    continue
                name, lands_in, operation = (g.strip() for g in match.groups())
                declared[name] = {"lands_in": lands_in, "manager_operation": operation}
    return declared


def check_write_paths_map_to_operations(pages, write_prefix):
    declared = read_declared_writes(pages)
    if not declared:
        return _result("3b", "FAIL",
                       "the surface never says which manager-session operation a write is — a "
                       "steward cannot tell the app and the manager session do the same thing")
    problems = []
    if len(declared) != 4:
        problems.append(f"{len(declared)} write(s) are named with an operation, not four: "
                        + ", ".join(sorted(declared)))
    for name, entry in sorted(declared.items()):
        if not entry["manager_operation"]:
            problems.append(f"{name} names no manager-session operation")
    routes = set()
    for page in pages:
        for _, method, action in page.forms():
            if method == "post" and action.startswith(write_prefix):
                routes.add(action)
    for route in sorted(routes):
        name = route.rstrip("/").rsplit("/", 1)[-1]
        if name not in declared:
            problems.append(f"{route} is a write the surface never maps to an operation")
    if problems:
        return _result("3b", "FAIL", "; ".join(problems[:6]), declared=declared)
    return _result("3b", "PASS",
                   "all four writes are mapped: "
                   + "; ".join(f"{n} → {d['manager_operation']}" for n, d in sorted(declared.items())),
                   declared=declared)


# --------------------------------------------------------------------------- #
# clause 2 — answers land in the record                                        #
# --------------------------------------------------------------------------- #
DATED = re.compile(r"<date>|\{date\}|\d{4}-\d{2}-\d{2}|dated", re.IGNORECASE)


def check_answers_land_in_the_record(pages, write_prefix):
    declared = read_declared_writes(pages)
    answer = next((name for name in declared if re.search(r"answer", name, re.IGNORECASE)), None)
    problems = []
    if answer is None:
        problems.append("the surface never says where an answer lands")
        return _result("2", "FAIL", "; ".join(problems), declared=declared)
    lands_in = declared[answer]["lands_in"]
    if "ratification" not in lands_in.lower():
        problems.append(f"an answer is said to land in “{lands_in}”, which is not the ratification record")
    if not DATED.search(lands_in):
        problems.append(f"the record an answer lands in is not dated: “{lands_in}”")

    forms = []
    for page in pages:
        for form, method, action in page.forms():
            if method != "post" or not action.startswith(write_prefix):
                continue
            if action.rstrip("/").rsplit("/", 1)[-1] == answer:
                forms.append((page, form))
    if not forms:
        problems.append("no form anywhere answers with a word")
    for page, form in forms:
        names = _field_names(form)
        if "subject" not in names:
            problems.append(f"{page.route}: an answer is sent without saying what it answers, so the "
                            "record cannot name it")
            break
        if not _submit_labels(form):
            problems.append(f"{page.route}: an answer form sends no word")
            break
    if problems:
        return _result("2", "FAIL", "; ".join(problems[:6]), lands_in=lands_in, forms=len(forms))
    return _result("2", "PASS",
                   f"{len(forms)} answer form(s), each naming what it answers, and the surface says "
                   f"every answer lands in {lands_in}",
                   lands_in=lands_in, forms=len(forms))


# --------------------------------------------------------------------------- #
# clause 8 — plain words on the surface                                        #
# --------------------------------------------------------------------------- #
IDENTIFIER_CHARS = "-_/."


def _inside_identifier(text: str, match) -> bool:
    """True when a match sits inside a longer hyphenated or pathed token.

    `amplifier-bundle-converge` is a project's NAME shown in a header chip — a
    proper noun, not the word "bundle" used as jargon. A trailing full stop is
    a sentence ending, not a path separator: "the ledger." is jargon, plainly.
    """
    i, j = match.start(), match.end()
    if i > 0 and text[i - 1] in IDENTIFIER_CHARS:
        if i - 2 >= 0 and (text[i - 2].isalnum() or text[i - 2] == "_"):
            return True
    if j < len(text) and text[j] in IDENTIFIER_CHARS:
        if j + 1 < len(text) and (text[j + 1].isalnum() or text[j + 1] == "_"):
            return True
    return False


def check_vocabulary(pages):
    hits = []
    folded = 0
    for page in pages:
        words = page.own_words()
        folded += len(page.folded_words().split())
        for term in INTERNAL_VOCABULARY:
            for match in re.finditer(r"\b" + re.escape(term) + r"\b", words, re.IGNORECASE):
                if _inside_identifier(words, match):
                    continue
                start = max(0, match.start() - 40)
                hits.append({"page": page.route, "term": term,
                             "context": words[start:match.end() + 40].strip()})
                break
    if hits:
        named = ", ".join(f"{h['term']} ({h['page']})" for h in hits[:6])
        return _result("8c", "FAIL",
                       f"{len(hits)} internal term(s) in the app's own words: {named}",
                       hits=hits)
    return _result("8c", "PASS",
                   f"across {len(pages)} page(s), nothing in the app's own words would send a reader "
                   f"to a glossary; {folded} word(s) of technical detail sit behind Details folds",
                   pages=len(pages), folded_words=folded)


# --------------------------------------------------------------------------- #
# Core 8, first half — the plain state words                                    #
# --------------------------------------------------------------------------- #
STATE_CLASSES = ("chip", "state", "mark")


def _states_on(page):
    out = []
    for cls in STATE_CLASSES:
        for node in page.find(cls=cls):
            text = node.text().strip()
            if text:
                out.append((cls, text, page.route))
    return out


def _is_surface_word(word: str) -> bool:
    """A measure may follow the word — `Quiet 12m` is still Quiet."""
    word = (word or "").strip()
    return any(word == allowed or word.startswith(allowed + " ") for allowed in SURFACE_WORDS)


def check_state_words(pages):
    states = [s for page in pages for s in _states_on(page)]
    if not states:
        return _result("8a", "FAIL",
                       "no page shows the state of anything, so a reader is told nothing in words")
    foreign = [s for s in states if not _is_surface_word(s[1])]
    if foreign:
        named = ", ".join(f"“{word}” ({cls} on {route})" for cls, word, route in foreign[:6])
        return _result("8a", "FAIL",
                       f"{len(foreign)} of {len(states)} states are said in words the contract does "
                       f"not allow: {named}",
                       foreign=[{"class": c, "word": w, "page": r} for c, w, r in foreign])
    said = sorted({s[1] for s in states})
    return _result("8a", "PASS",
                   f"{len(states)} state(s) shown, every one of them a plain word: {said}",
                   words=said)


def check_both_vocabularies(pages):
    lane_words = set()
    contract_words = set()
    chip_words = set()
    for page in pages:
        for cls, word, _ in _states_on(page):
            bare = word.split(" ")[0] if word not in LANE_STATES else word
            if cls == "mark":
                if any(word == state or word.startswith(state.split(" ")[0] + " ")
                       for state in LANE_STATES):
                    lane_words.add(word)
            if cls == "chip":
                chip_words.add(word)
                if word in CONTRACT_STATES or bare in ("Kept", "Broken"):
                    contract_words.add(word)
    problems = []
    if not lane_words:
        problems.append("no lane is shown as " + " · ".join(LANE_STATES))
    if not contract_words:
        problems.append(
            "no contract is shown as " + " · ".join(CONTRACT_STATES)
            + (f" — the state beside each one is {sorted(chip_words)}, which is the document's own "
               "status, not whether the promise is being kept" if chip_words else "")
        )
    if problems:
        return _result("8b", "FAIL", "; ".join(problems),
                       lane_words=sorted(lane_words), contract_words=sorted(contract_words),
                       chip_words=sorted(chip_words))
    return _result("8b", "PASS",
                   f"contracts are shown as {sorted(contract_words)} and lanes as {sorted(lane_words)}",
                   lane_words=sorted(lane_words), contract_words=sorted(contract_words))


# --------------------------------------------------------------------------- #
# Core 9 — the whole operation in view                                          #
# --------------------------------------------------------------------------- #
def check_whole_operation_in_view(pages):
    operation = next((p for p in pages if p.is_operation_page()), None)
    if operation is None:
        return _result("9b", "FAIL", "no page shows the operation")

    text = operation.root.text()
    checks = []

    def note(name, ok, detail):
        checks.append({"in view": name, "status": "PASS" if ok else "FAIL", "detail": detail})

    lanes = operation.first(node_id="lanes")
    note("lanes running against lanes intended, with the fill control",
         lanes is not None and bool(GAUGE.search(lanes.text()) or lanes.text()),
         "the lanes card states the gauge" if lanes is not None else "no lanes card")

    ready = "Truly ready" in text
    waiting = "Waiting on you" in text
    note("truly ready against waiting on you", ready and waiting,
         f"truly ready: {ready}, waiting on you: {waiting}")

    steps = [s for s in operation.find(cls="step") if s.first(cls="n")]
    with_reasons = [s for s in steps if s.first(cls="why")]
    note("the plan in order, with reasons", bool(steps) and len(with_reasons) == len(steps),
         f"{len(steps)} numbered step(s), {len(with_reasons)} of them giving a reason"
         if steps else "no plan is in order on the page")

    lane_cards = [c for c in operation.find(tag="article") if c.id.startswith("lane-")]
    complete = [c for c in lane_cards
                if c.first(cls="mark") and (c.first(cls="evidence") or c.first(cls="badge"))
                and c.first(tag="details")]
    if lane_cards:
        note("each lane's state and evidence, with drill-in",
             len(complete) == len(lane_cards),
             f"{len(complete)} of {len(lane_cards)} lane(s) show a state, evidence and a fold")
    else:
        said_why = lanes is not None and len(lanes.text()) > 20
        note("each lane's state and evidence, with drill-in", said_why,
             "no lane is running, and the lanes card says so" if said_why
             else "no lane card and no word about why")

    limits = operation.first(node_id="limits")
    limit_fields = _field_names(limits.first(tag="form")) if limits and limits.first(tag="form") else set()
    note("your limits", limits is not None and len(limit_fields & {"objective", "budget", "lane_width"}) == 3,
         f"fields: {sorted(limit_fields)}" if limits else "no limits card")

    feedback = operation.first(node_id="feedback")
    note("the feedback drop", feedback is not None and feedback.first(tag="textarea") is not None,
         "a place to say what you saw" if feedback else "no feedback drop")

    managers = operation.first(node_id="managers")
    tell_all = managers is not None and any(
        "tell all" in " ".join(_submit_labels(f)).lower() for f, _, _ in _forms_of(managers))
    note("every manager session you run, with “tell all”", managers is not None and tell_all,
         "listed, with one thing you can tell them all" if tell_all
         else ("no way to tell them all" if managers else "no manager sessions card"))

    stops = []
    for control in operation.controls():
        label = control.text().strip() or control.attrs.get("value", "")
        if STOP_WORDS.search(label):
            stops.append(label[:40])
    note("stopping something is never a board button", not stops,
         f"stop-shaped control(s): {stops}" if stops else "no control on the board stops anything")

    missing = [c for c in checks if c["status"] == "FAIL"]
    if missing:
        return _result("9b", "FAIL",
                       f"{len(missing)} of {len(checks)} not in view: "
                       + "; ".join(f"{c['in view']} ({c['detail']})" for c in missing[:5]),
                       in_view=checks)
    return _result("9b", "PASS",
                   f"all {len(checks)} parts of the operation are on one page, and nothing on the "
                   "board stops anything",
                   in_view=checks)


# --------------------------------------------------------------------------- #
# clause 4 — no data of its own                                                #
# --------------------------------------------------------------------------- #
#: The surface saying, in its own words, where the truth it shows lives.
KEEPS_NOTHING_RE = re.compile(
    r"keeps? nothing of its own|holds no data of its own|no data of its own", re.I
)
#: A project artifact named on the page — the file a document page is a view of.
PROJECT_PATH_RE = re.compile(r"\b[\w.-]+/[\w.-]+\.(?:md|yaml|yml|json|py|html)\b")


def check_no_data_of_its_own(pages):
    """Core 4: "No data of its own. … No second copy of the truth."

    Two halves are readable from what the app serves. Every page must SAY the
    surface keeps nothing of its own — a reader who cannot tell whether they
    are looking at the project or at the app's private copy has to go and check
    the repository, which is the trip this promise exists to remove. And every
    document page must NAME the project artifact it is a view of, so the claim
    is checkable on the page rather than taken on trust.

    What a static read cannot do is prove a private store does not exist behind
    the page; that is the app's own test suite's job, and the detail below says
    so rather than implying more than was checked.
    """
    problems = []
    silent = [p.route for p in pages if not KEEPS_NOTHING_RE.search(p.own_words())]
    if silent:
        problems.append(
            f"{len(silent)} of {len(pages)} page(s) never say the surface keeps no data "
            f"of its own: {silent[:4]}"
        )
    docs = [p for p in pages if p.is_document_page()]
    unattributed = [p.route for p in docs if not PROJECT_PATH_RE.search(p.html)]
    if unattributed:
        problems.append(
            f"{len(unattributed)} of {len(docs)} document page(s) name no project file they "
            f"are a view of: {unattributed[:4]}"
        )
    if problems:
        return _result("4", "FAIL", "; ".join(problems), silent=silent,
                       unattributed=unattributed)
    attributed = (f"{len(docs)} document page(s) name the project file they show"
                  if docs else "no document page in this target to attribute")
    return _result(
        "4", "PASS",
        f"all {len(pages)} page(s) say the surface keeps no data of its own, and "
        f"{attributed}; whether a private store sits behind them is not readable here",
        documents=len(docs),
    )


# --------------------------------------------------------------------------- #
# clause 5 — proposals look the same whoever proposed                          #
# --------------------------------------------------------------------------- #
#: surface.v1 Core 5, and documents.v1 Core 8: the three parts, in this order.
PROPOSAL_PARTS = (
    ("what changes", re.compile(r"the exact change", re.I)),
    ("the evidence", re.compile(r"the evidence", re.I)),
    ("what does not change", re.compile(r"what does\s+(?:\*\*)?not(?:\*\*)?\s+change", re.I)),
)


def _proposal_pages(pages):
    out = []
    for p in pages:
        if "proposal" in p.route.lower() or "candidate" in p.route.lower():
            out.append(p)
        elif PROPOSAL_PARTS[0][1].search(p.own_words()):
            out.append(p)
    return out


def check_proposals_look_the_same(pages):
    """Core 5: "Proposals look the same whoever proposed."

    The clause fixes the shape: what changes, sentence by sentence · the
    evidence · what does not change. The kit reads the page's OWN words, not
    the proposal's, because the promise is that the SURFACE lays every proposal
    out the same way — a manager session's draft and a teammate's pull request
    reaching a reader in two different shapes is the failure. Order matters:
    evidence before the change asks a reader to judge a case before they know
    what it is.
    """
    proposals = _proposal_pages(pages)
    if not proposals:
        return _skip(
            "5",
            "no proposal is open in this target, so no page lays one out — point the "
            "kit at an app whose project carries a `*.vN-candidate.md`, or at a page "
            "set rendered from one",
        )
    problems, checked = [], []
    for p in proposals:
        words = p.own_words()
        at = {label: rx.search(words) for label, rx in PROPOSAL_PARTS}
        missing = [label for label, m in at.items() if m is None]
        row = {"route": p.route, "missing": missing}
        if missing:
            problems.append(f"{p.route} shows no {', no '.join(missing)}")
        else:
            order = [at[label].start() for label, _ in PROPOSAL_PARTS]
            row["order"] = order
            if order != sorted(order):
                problems.append(
                    f"{p.route} lays the three parts out in the wrong order "
                    f"({[l for l, _ in PROPOSAL_PARTS]} at {order})"
                )
        checked.append(row)
    if problems:
        return _result("5", "FAIL", "; ".join(problems[:6]), proposals=checked)
    return _result(
        "5", "PASS",
        f"all {len(proposals)} proposal page(s) show what changes, the evidence, and "
        "what does not change — in that order, whoever proposed",
        proposals=checked,
    )


# --------------------------------------------------------------------------- #
# driver                                                                       #
# --------------------------------------------------------------------------- #
def run_conformance(target, *, write_prefix: str = "/do/", changes_nothing=()):
    """Judge one target — a URL, a page set, or a single page.

    The target is resolved here rather than by the caller, so anything holding
    the kit can hand it a path and get a report back:

        report = run_conformance(Path("…/page.html"))

    which is how `tests/test_plain_words_on_the_surface.py` reads rule 5's
    verdict on each page the app serves.
    """
    pages, meta = resolve_target(str(target))
    changes_nothing = list(changes_nothing) + list(meta.get("changes_nothing", []))
    results = [
        check_places_switch(pages),                                  # 1a
        check_answering_shortens(pages),                             # 1b
        check_answers_land_in_the_record(pages, write_prefix),       # 2
        check_write_paths(pages, write_prefix, changes_nothing),     # 3a
        check_write_paths_map_to_operations(pages, write_prefix),    # 3b
        check_no_data_of_its_own(pages),                             # 4
        check_proposals_look_the_same(pages),                        # 5
        check_what_changed(pages),                                   # 6
        check_lock_gated(pages),                                     # 7
        check_state_words(pages),                                    # 8a
        check_both_vocabularies(pages),                              # 8b
        check_vocabulary(pages),                                     # 8c
        check_fill_updates_the_board(pages),                         # 9a
        check_whole_operation_in_view(pages),                        # 9b
        _skip("10"),
    ]
    summary = {
        "pass": sum(r["status"] == "PASS" for r in results),
        "fail": sum(r["status"] == "FAIL" for r in results),
        "skip": sum(r["status"] == "SKIP" for r in results),
    }
    return {
        "kit": "surface.v1",
        "contract": "contracts/surface.v1.md",
        "target": str(target),
        "target_kind": meta.get("mode", "unknown"),
        "pages": [{"route": p.route, "source": p.source} for p in pages],
        "check": "static — read from what the app served; no browser is launched",
        "changes_nothing": list(changes_nothing),
        "results": results,
        "summary": summary,
        "verdict": "FAIL" if summary["fail"] else "PASS",
    }


def print_human_summary(report: dict) -> None:
    write = sys.stderr.write
    write(f"\nsurface.v1 conformance — {report['target']} ({report['target_kind']}, "
          f"{len(report['pages'])} page(s))\n")
    write(f"asserts: {report['contract']} — {report['check']}\n")
    write("-" * 78 + "\n")
    for result in report["results"]:
        write(f"  [{result['status']:4}] {result['rule']:3} {result['id']}: {result['detail']}\n")
    write("-" * 78 + "\n")
    s = report["summary"]
    write(f"  VERDICT: {report['verdict']}  (pass={s['pass']} fail={s['fail']} skip={s['skip']})\n\n")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="surface-conformance",
        description="Assert surface.v1 conformance against the companion app.",
    )
    parser.add_argument("target",
                        help="the running app (http://127.0.0.1:8091), a directory of pages "
                             "written by render.py, or one page")
    parser.add_argument("--write-prefix", default="/do/",
                        help="the path every write posts under (default: /do/)")
    parser.add_argument("--changes-nothing", action="append", default=[], metavar="GLOB",
                        help="a POST route that changes nothing about the project, so it is not one "
                             "of the four writes. Repeatable. Naming it here is the claim; the app "
                             "names the same routes in web/app.py NON_WRITE_POSTS.")
    parser.add_argument("--json-only", action="store_true",
                        help="suppress the human summary on stderr")
    args = parser.parse_args(argv)

    try:
        report = run_conformance(args.target, write_prefix=args.write_prefix,
                                 changes_nothing=args.changes_nothing)
    except (FileNotFoundError, ConnectionError, ValueError, json.JSONDecodeError) as exc:
        sys.stderr.write(f"error: {exc}\n")
        return 3

    sys.stdout.write(json.dumps(report, indent=2) + "\n")
    if not args.json_only:
        print_human_summary(report)
    return 1 if report["verdict"] == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
