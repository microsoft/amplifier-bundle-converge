# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""experience-direction.v1 conformance kit — "Direction keeps its promises".

Point it at the companion app — the running server, or a snapshot captured from
it — and it asserts `contracts/experience-direction.v1.md` against what the app
actually serves: the shell it renders into, the API payloads it answers with,
the client it ships, and its own route table at `/openapi.json`.

    uv run conformance/experience-direction/run.py http://127.0.0.1:8788
    uv run conformance/experience-direction/run.py <a --capture directory>

Stdlib only, and **no browser is launched**.

Numbering
---------
Rule ids anchor to the contract's **Core clause** numbers, as `documents.v1`
clause 5 asks and the steward ratified on 2026-09-03: rule 7 judges Core 7, so a
failing rule names the clause it breaks. Where one clause carries several
independent promises the kit emits one row per promise, lettered inside the
clause (`2a`, `2b`). Every one of the eleven Core clauses has a row, and
`test_every_core_clause_has_a_row` fails if one does not.

What a static read buys, and what it does not
---------------------------------------------
It can prove a promise is *reachable*: that a document arrives rendered with its
source beside it, that four view controls exist and Changes carries removed
sentences, that a control the contract requires is present at all, and — the
one that matters most here — that the control which triggers an action reaches
a **write the app declares in its own route table**, rather than only showing a
message and forgetting.

It cannot prove a write records the right thing once it lands. Rules that lean
on the handler read say so in their own detail rather than implying more than
was checked.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from kitreport import Kit, run_cli  # noqa: E402

CONTRACT = "contracts/experience-direction.v1.md"

KIT = Kit(
    "experience-direction.v1",
    CONTRACT,
    rules=[
        ("1", 1, "documents_per_repository_with_an_all_view",
         "documents are organized per repository, with an All view across them"),
        ("2a", 2, "rendered_with_the_source_one_gesture_away",
         "every document arrives rendered, and its source sits beside it"),
        ("2b", 2, "the_render_carries_what_the_documents_contain",
         "what the project's documents contain is what the render shows"),
        ("3", 3, "copy_download_zoom_width",
         "a reader can copy rendered, copy source, download, zoom, and choose the width"),
        ("4", 4, "four_views_and_changes_shows_removals",
         "four views — Reading · Changes · Review · History — and Changes is sentence by sentence"),
        ("5", 5, "editing_offered_where_it_is_legal",
         "direct editing is offered exactly where it is legal"),
        ("6a", 6, "restore_is_a_real_action",
         "restoring from history reaches a write, and routes through a proposal when locked"),
        ("6b", 6, "restore_can_name_a_snapshot",
         "that write can name WHICH snapshot to restore from, not only the reader's own position"),
        ("7", 7, "a_proposal_looks_the_same_whoever_proposed",
         "a proposal shows what changes · why · the evidence · what does not change · the word"),
        ("8", 8, "granular_choices_build_one_answer",
         "accepting and reverting individual changes constructs ratified with edits"),
        ("9", 9, "ask_returns_a_proposal",
         "Ask is a scoped request whose output is always a proposal"),
        ("10", 10, "courtesy_presence_and_reconciliation",
         "concurrent editing is met with courtesy presence and reconciliation"),
        ("11", 11, "the_lock_control_is_gated_and_shown",
         "the lock control is gated on the four conditions, and they are shown"),
    ],
)

#: Core 4 — the contract's own four views, in its own order.
FOUR_VIEWS = ("read", "changes", "review", "history")

#: Core 7 / experience.v1 Core 4 — the four words an answer may be.
ANSWER_WORDS = ("ratified", "ratified with edits", "declined", "later")

#: Core 7 — the five parts a proposal shows, in the contract's order.
PROPOSAL_PARTS = (
    ("what changes", re.compile(r"what\s+changes", re.I)),
    ("why", re.compile(r"\bwhy\b", re.I)),
    ("the evidence", re.compile(r"\bevidence\b", re.I)),
    ("what does not change", re.compile(r"what\s+does\s+not\s+change", re.I)),
    # The review must OFFER the answer; whether the four words themselves are
    # right is the check below, read from the module's own button table.
    ("the word to answer with", re.compile(
        r"ratif(y|ied)|declin(e|ed)|\blater\b|data-decision|DECISION_BUTTONS", re.I)),
)

#: Core 10 — the three choices offered when changes collide.
RECONCILE_CHOICES = ("use combined", "keep mine", "review both")

#: Core 11 — the four conditions the Freeze Bar names, in the gate's own words.
LOCK_CONDITIONS = (
    ("says what it means", re.compile(r"says?\s+what\s+it\s+means", re.I)),
    ("a real example of right and wrong", re.compile(
        r"example.{0,24}(right|wrong)|(right|wrong).{0,24}example", re.I)),
    ("can be checked against reality", re.compile(
        r"check(ed|able)?\s+against\s+reality", re.I)),
    ("the steward has read it and agreed", re.compile(
        r"(read\s+it\s+and\s+agreed|steward\s+has\s+read)", re.I)),
)

#: Core 2 — what the contract asks a render to carry, and how to tell from the
#: SOURCE whether this target's documents even contain one.
RENDER_CAPABILITIES = (
    ("markdown", re.compile(r"\*\*[^*\n]+\*\*"), re.compile(r"<strong[ >]")),
    ("a table", re.compile(r"(?m)^\|.+\|\s*$"), re.compile(r"<table[ >]")),
    ("an image", re.compile(r"!\[[^\]]*\]\("), re.compile(r"<img[ >]")),
    ("a link between documents", re.compile(r"\]\([^)]*\.md[)#]"),
     re.compile(r"<a\s[^>]*href=[\"'][^\"']*\.md")),
    ("front matter", re.compile(r"\A---\r?\n"), re.compile(r"front-?matter|<dl[ >]|<table[ >]")),
    ("a Mermaid diagram", re.compile(r"```\s*mermaid"), re.compile(r"mermaid")),
    ("a DOT diagram", re.compile(r"```\s*(dot|graphviz)"), re.compile(r"(graphviz|\bdot-graph)")),
    ("safely embedded HTML", re.compile(r"(?m)^<(div|table|img|details|svg)\b"),
     re.compile(r"<(div|table|img|details|svg)\b")),
)


# --------------------------------------------------------------------------- #
# reading the client the app ships                                             #
# --------------------------------------------------------------------------- #
def write_tokens(snapshot):
    """The app's own name for each write, taken from its own route table.

    `/api/managers/{mid}/decision` → `decision`. A control "reaches a write"
    when the code path it triggers mentions one of these, or posts directly.
    """
    tokens = set()
    for path in snapshot.write_routes():
        tail = [p for p in path.strip("/").split("/") if not p.startswith("{")]
        if tail:
            tokens.add(tail[-1])
    return tokens


def handler_body(script: str, marker: str, window: int = 900) -> str:
    """The code that runs when the control named by `marker` is used.

    `marker` is the SELECTOR form — `[data-restore]` — so the search lands on
    the wiring rather than on the same attribute inside a markup template.
    Narrow on purpose: from that point, take the enclosing callback by counting
    braces, capped so a missing brace cannot swallow the file. This proves what
    the handler REACHES, never what the write records.
    """
    at = script.find(marker)
    if at < 0:
        return ""
    start = script.find("{", at)
    if start < 0:
        return script[at:at + window]
    depth, i = 0, start
    while i < len(script) and i - start < window * 4:
        if script[i] == "{":
            depth += 1
        elif script[i] == "}":
            depth -= 1
            if depth == 0:
                return script[start:i + 1]
        i += 1
    return script[start:start + window]


def strip_string_literals(code: str) -> str:
    """Blank out '…', "…" and `…` so a WORD in a message cannot pass for a call.

    Measured on this app: the per-change handler shows the message "Restore
    staged for the next proposal decision." and nothing else. Matched as bare
    words, `decision` in that sentence read as a write and the rule reported a
    fabricated PASS. A write is a CALL, so only code is searched.
    """
    return re.sub(r"'[^'\n]*'|\"[^\"\n]*\"|`[^`]*`", "''", code, flags=re.S)


def reaches_a_write(body: str, tokens) -> bool:
    if not body:
        return False
    if re.search(r"method:\s*['\"]POST['\"]", body, re.I):
        return True
    code = strip_string_literals(body)
    return any(re.search(rf"\w*{re.escape(t)}\w*\s*\(", code, re.I) for t in tokens)


# --------------------------------------------------------------------------- #
# Core 6 — restoring FROM a point in history                                    #
# --------------------------------------------------------------------------- #

#: What a client or a route table calls "which snapshot". Listed rather than
#: guessed at: the rule reports what it looked for when it finds none, so a
#: build that names the idea some other way fails LOUDLY and readably instead
#: of being quietly judged by a regex nobody can see.
SNAPSHOT_WORDS_LIST = ("since", "snapshot", "commit", "sha", "revision")
SNAPSHOT_WORD_RE = re.compile(r"\b(" + "|".join(SNAPSHOT_WORDS_LIST) + r")\b", re.I)

#: A route that puts wording back. The app's own word for this write.
RESTORE_PATH_RE = re.compile(r"/restore\b", re.I)


def blank_string_literals(code: str) -> str:
    """`strip_string_literals`, but LENGTH-PRESERVING, so indices still line up.

    Needed because this rule finds an anchor in the RAW text (a URL lives
    inside a string) and then walks brackets around it. `strip_string_literals`
    rewrites the text to a different length, so an index taken before it means
    nothing after it. Interiors become spaces; the quotes stay where they were.
    """
    out = list(code)
    i, n = 0, len(code)
    while i < n:
        ch = code[i]
        if ch in "'\"`":
            j = i + 1
            while j < n:
                if code[j] == "\\":
                    j += 2
                    continue
                if code[j] == ch:
                    break
                if code[j] == "\n" and ch != "`":
                    break
                j += 1
            for k in range(i + 1, min(j, n)):
                if out[k] != "\n":
                    out[k] = " "
            i = j + 1
            continue
        i += 1
    return "".join(out)


def enclosing_call(code: str, at: int, limit: int = 4000):
    """The `( … )` of the call whose arguments contain index *at*.

    Walked over string-blanked text so a bracket inside a message or a URL
    cannot open or close a call. Returns `(start, end)` over the ORIGINAL
    text's indices, or None.
    """
    blank = blank_string_literals(code)
    depth, i, floor = 0, at, max(0, at - limit)
    while i > floor:
        ch = blank[i]
        if ch == ")":
            depth += 1
        elif ch == "(":
            if depth == 0:
                break
            depth -= 1
        i -= 1
    else:
        return None
    start, depth, j, ceil = i, 0, i, min(len(code), at + limit)
    while j < ceil:
        if blank[j] == "(":
            depth += 1
        elif blank[j] == ")":
            depth -= 1
            if depth == 0:
                return (start, j + 1)
        j += 1
    return None


def client_restore_names_a_snapshot(script: str):
    """Does the client's own restore write carry a snapshot identifier?

    Anchored on the restore URL and bounded to the call expression around it,
    which is what keeps this honest: `render/direction.js` explains `?since=`
    to the reader in prose, and a looser search would read that sentence as
    proof of a capability. Only CODE inside the restore call counts — the same
    lesson `strip_string_literals` was written for.
    """
    for m in RESTORE_PATH_RE.finditer(script):
        span = enclosing_call(script, m.start())
        if not span:
            continue
        start, end = span
        code = blank_string_literals(script[start:end])
        found = SNAPSHOT_WORD_RE.search(code)
        if found:
            return found.group(1), script[start:end]
    return None


def route_table_names_a_snapshot(snapshot):
    """Does the app's OWN route table declare which snapshot a restore reaches?

    The stronger of the two answers when it is available: a parameter or a body
    property the app documents itself. Returns `(path, what)` or None.
    """
    doc = snapshot.json("/openapi.json") or {}
    schemas = ((doc.get("components") or {}).get("schemas") or {})

    def properties_of(schema, seen=()):
        ref = schema.get("$ref") or ""
        if ref.startswith("#/components/schemas/"):
            name = ref.rsplit("/", 1)[-1]
            if name in seen:
                return []
            return properties_of(schemas.get(name) or {}, seen + (name,))
        return list((schema.get("properties") or {}).keys())

    for path, ops in (doc.get("paths") or {}).items():
        if not RESTORE_PATH_RE.search(path) or not isinstance(ops, dict):
            continue
        for op in ops.values():
            if not isinstance(op, dict):
                continue
            for param in op.get("parameters") or []:
                name = str((param or {}).get("name") or "")
                if SNAPSHOT_WORD_RE.search(name):
                    return path, f"a `{name}` parameter"
            content = ((op.get("requestBody") or {}).get("content") or {})
            for media in content.values():
                for prop in properties_of((media or {}).get("schema") or {}):
                    if SNAPSHOT_WORD_RE.search(prop):
                        return path, f"a `{prop}` property in its body"
    return None


def shell_text(snapshot) -> str:
    return snapshot.html("/").text()


def control_present(snapshot, *patterns) -> bool:
    """Is a control for this ability anywhere in what the app served?"""
    hay = snapshot.text("/") + "\n" + snapshot.script_text()
    return any(re.search(p, hay, re.I) for p in patterns)


# --------------------------------------------------------------------------- #
# rules                                                                        #
# --------------------------------------------------------------------------- #
def check_documents_per_repository(snapshot):
    manager = snapshot.manager()
    if not manager:
        return KIT.bad("1", "the app served no manager payload, so no document tree exists")
    repos = manager.get("repositories") or []
    if not repos:
        return KIT.bad("1", "the manager payload carries no `repositories`")
    empty = [r.get("id") for r in repos if not (r.get("docs") or [])]
    shell = snapshot.html("/")
    all_view = [o for o in shell.find(tag="option")
                if (o.attrs.get("value", "").lower() == "all"
                    or "all repos" in o.text().lower())]
    problems = []
    if empty:
        problems.append(f"repositories with no documents: {empty}")
    if not all_view:
        problems.append("no All view across the repositories (no all-repos option in the shell)")
    if problems:
        return KIT.bad("1", "; ".join(problems), repositories=[r.get("id") for r in repos])
    return KIT.ok(
        "1",
        f"{len(repos)} repository/ies, each with documents "
        f"({sum(len(r.get('docs') or []) for r in repos)} in all), and an All view across them",
        repositories=[{"id": r.get("id"), "documents": len(r.get("docs") or [])} for r in repos],
    )


def check_rendered_with_source(snapshot):
    docs = snapshot.documents()
    if not docs:
        return KIT.bad("2a", "the app served no document payload to read")
    problems, rows = [], []
    for route, doc in docs:
        rendered = "".join(str(s[1]) for s in (doc.get("sections") or []) if len(s) > 1)
        raw = doc.get("raw") or ""
        rows.append({"route": route, "sections": len(doc.get("sections") or []),
                     "rendered_bytes": len(rendered), "source_bytes": len(raw)})
        if not rendered.strip():
            problems.append(f"{doc.get('path', route)} arrives with nothing rendered")
        if not raw.strip():
            problems.append(f"{doc.get('path', route)} arrives with no source beside it")
    if not control_present(snapshot, r"rawToggle", r">\s*Raw\s*<"):
        problems.append("no control puts the source one gesture away")
    if problems:
        return KIT.bad("2a", "; ".join(problems[:6]), documents=rows)
    return KIT.ok("2a",
                  f"all {len(docs)} document(s) arrive rendered with their source beside them, "
                  "and a Raw control switches between them",
                  documents=rows)


def check_render_carries_what_documents_contain(snapshot):
    docs = snapshot.documents()
    if not docs:
        return KIT.bad("2b", "the app served no document payload to read")
    dropped, demonstrated, absent = [], [], []
    for label, in_source, in_render in RENDER_CAPABILITIES:
        carriers = []
        for route, doc in docs:
            raw = doc.get("raw") or ""
            if not in_source.search(raw):
                continue
            rendered = "".join(str(s[1]) for s in (doc.get("sections") or []) if len(s) > 1)
            carriers.append((doc.get("path", route), bool(in_render.search(rendered))))
        if not carriers:
            absent.append(label)
        elif all(ok for _, ok in carriers):
            demonstrated.append(label)
        else:
            missed = [p for p, ok in carriers if not ok]
            dropped.append(f"{label} (source has it, the render does not: {missed[:3]})")
    if dropped:
        return KIT.bad("2b", "the render drops " + "; ".join(dropped),
                       demonstrated=demonstrated, not_demonstrated=absent)
    return KIT.ok(
        "2b",
        f"the render carries every capability this target's documents contain "
        f"({', '.join(demonstrated) or 'none'}); not demonstrated by this target, "
        f"so unjudged here: {', '.join(absent) or 'none'}",
        demonstrated=demonstrated, not_demonstrated=absent,
    )


def check_copy_download_zoom_width(snapshot):
    abilities = {
        "download the source": (r"downloadDoc|download",),
        "zoom": (r"\bzoom\b|zoomIn|fontScale",),
        "page width or full screen": (r"wideToggle|\bwide\b",),
    }
    missing = [name for name, pats in abilities.items()
               if not control_present(snapshot, *pats)]
    present = [n for n in abilities if n not in missing]
    # The clause names TWO copy abilities — as rendered and as source. Counting
    # the copy controls is the honest test: naming them apart by id would let a
    # single control labelled `copyRendered` pass for both, which is exactly
    # what this app does (that one control copies the SOURCE).
    copies = sorted({n.id or n.text().strip()[:24]
                     for n in snapshot.html("/").walk()
                     if re.search(r"copy", (n.id or "") + " " + " ".join(n.classes)
                                  + " " + "".join(n.own_text), re.I)})
    if len(copies) >= 2:
        present.insert(0, f"two copy controls ({', '.join(copies[:2])})")
    else:
        missing.insert(0, "a second copy ability — the clause names copy as rendered "
                          f"AND copy as source, and this body offers {copies or 'none'}")
    if missing:
        return KIT.bad("3",
                       "no control for " + ", ".join(missing)
                       + f" (present: {', '.join(present) or 'none'}). The shape follows the "
                         "platform; the abilities do not.",
                       present=present, missing=missing)
    return KIT.ok("3", "all five abilities have a control: " + ", ".join(present),
                  present=present)


def check_four_views(snapshot):
    shell = snapshot.html("/")
    modes = [n.attrs.get("data-doc-mode", "").lower()
             for n in shell.find(attr="data-doc-mode")]
    modes = [m for m in modes if m]
    problems = []
    for want in FOUR_VIEWS:
        if want not in modes:
            problems.append(f"no `{want}` view control")
    extra = [m for m in modes if m not in FOUR_VIEWS]
    if extra:
        problems.append(f"views beyond the four the contract names: {sorted(set(extra))}")
    docs = snapshot.documents()
    with_changes = [(r, d) for r, d in docs if d.get("changes")]
    sentence_by_sentence = [
        d.get("path", r) for r, d in with_changes
        if not all(("before" in c and "now" in c) for c in d["changes"])
    ]
    if sentence_by_sentence:
        problems.append("Changes is not sentence by sentence (no before/now pair) on "
                        f"{sentence_by_sentence[:3]}")
    if not with_changes and docs:
        problems.append("no document in this target carries a change list, so Changes "
                        "shows nothing to judge")
    if problems:
        return KIT.bad("4", "; ".join(problems), views=sorted(set(modes)))
    return KIT.ok("4",
                  f"all four views present ({', '.join(FOUR_VIEWS)}); "
                  f"{len(with_changes)} document(s) carry a change list, every entry a "
                  "before/now sentence pair",
                  views=sorted(set(modes)))


def check_editing_offered_where_legal(snapshot):
    tokens = write_tokens(snapshot)
    edit_control = control_present(snapshot, r"data-edit\b", r"editDoc|editToggle|saveDoc")
    save_write = any(re.search(r"(edit|save|document)", p, re.I)
                     for p in snapshot.write_routes())
    if not edit_control and not save_write:
        return KIT.bad(
            "5",
            "no edit control and no write route that saves a document, so a DRAFT "
            "document cannot be edited in place anywhere — the clause asks for editing "
            "exactly where it is legal, and this offers it nowhere",
            write_routes=snapshot.write_routes())
    if edit_control and not save_write:
        return KIT.bad("5", "an edit control exists but no write route saves a document",
                       write_routes=snapshot.write_routes())
    if save_write and not edit_control:
        return KIT.bad("5", "a document-saving write route exists but nothing offers it",
                       write_routes=snapshot.write_routes())
    body = handler_body(snapshot.script_text(), "[data-edit]")
    if not reaches_a_write(body, tokens):
        return KIT.bad("5", "the edit control does not reach any write the app declares")
    return KIT.ok("5", "editing is offered and reaches a document-saving write; the guard "
                       "beyond it is the repository's, not this kit's to prove",
                  write_routes=snapshot.write_routes())


def check_restore_is_real(snapshot):
    script = snapshot.script_text()
    tokens = write_tokens(snapshot)
    has_control = control_present(snapshot, r"data-restore\b", r"restoreDoc|>\s*Restore")
    if not has_control:
        return KIT.bad("6a", "nothing offers a restore from history at any scope "
                             "(a wording, a paragraph, a section, the whole document)")
    body = handler_body(script, "[data-restore]")
    if not reaches_a_write(body, tokens):
        return KIT.bad(
            "6a",
            "the restore control is offered but its handler reaches no write the app "
            "declares — it shows a message and forgets, so restoring is not a real "
            "action and cannot produce the proposal a locked document requires",
            handler_excerpt=re.sub(r"\s+", " ", body)[:220],
            write_routes=snapshot.write_routes())
    return KIT.ok("6a", "restore reaches a write the app declares; on a locked document that "
                        "write is the proposal path",
                  handler_excerpt=re.sub(r"\s+", " ", body)[:160])


def check_restore_can_name_a_snapshot(snapshot):
    """Core 6's other half: restoring FROM somewhere.

    Rule 6a proves the restore control reaches a write. It says nothing about
    WHICH wording that write can put back, and for the whole life of
    converge-4pq that silence was expensive: the app could reach exactly one
    snapshot out of however many the History view listed, said so on screen in
    its own words, and this kit read PASS on both sides of the fix. A rule that
    reads the same before and after the work it is meant to judge is not
    measuring its clause.

    "Restore a wording, a paragraph, a section, or the whole document" is a
    restore FROM a point in history, so the question this rule asks is whether
    the restore write can be told which point. Two places can answer it from a
    static read, and either is enough:

    * the app's own route table, when the restore write declares a parameter or
      a body property naming a snapshot; and
    * the client the app ships, when the call that posts to the restore write
      carries a snapshot identifier with it.

    A live FastAPI route that reads its body straight off the request declares
    no body schema, so the route table alone cannot answer for this app today
    -- which is why the client is read too, and why the detail always says
    which of the two answered.

    What it still does not prove, said here rather than implied: that the
    server honours the snapshot it is handed, or that a commit which never
    touched this document is refused. Both need a request, and no browser is
    launched. This rule proves the app can be ASKED for a particular snapshot;
    `app/tests/test_direction_restore.py` is where the answer is driven.
    """
    script = snapshot.script_text()
    if not script and not snapshot.api_routes():
        return KIT.skip(
            "6b",
            "the app served neither a client nor a route table, so there is nothing "
            "to read for which snapshot a restore can reach — a static read cannot "
            "answer this, and says so rather than passing")

    from_routes = route_table_names_a_snapshot(snapshot)
    if from_routes:
        path, where = from_routes
        return KIT.ok("6b",
                      f"the app's own route table declares a snapshot on the restore write: "
                      f"{path} takes {where} — so a restore can name a point in the "
                      "document's history, not only the reader's own position",
                      evidence_from="route table")

    from_client = client_restore_names_a_snapshot(script)
    if from_client:
        word, span = from_client
        return KIT.ok("6b",
                      f"the client's restore write carries `{word}`, so the app can be asked "
                      "for a wording from a snapshot other than the reader's own read point; "
                      "the route table reads its body off the request and declares no schema, "
                      "so this was read from the client the app ships",
                      evidence_from="client",
                      restore_call=re.sub(r"\s+", " ", span)[:200])

    restore_writes = [p for p in snapshot.write_routes() if RESTORE_PATH_RE.search(p)]
    return KIT.bad(
        "6b",
        "nothing lets a restore name WHICH snapshot to put back: neither the route table "
        "nor the client the app ships carries a snapshot identifier on the restore write, "
        "so restore can only reach the reader's own read point — one snapshot, however "
        "many the History view lists",
        restore_write_routes=restore_writes,
        looked_for=sorted(SNAPSHOT_WORDS_LIST))


def check_proposal_shape(snapshot):
    review = snapshot.script_named("render/direction.js") or snapshot.script_text()
    at = review.find("function renderReview")
    region = review[at:at + 4000] if at >= 0 else review
    found, missing = {}, []
    for label, rx in PROPOSAL_PARTS:
        m = rx.search(region)
        if m:
            found[label] = m.start()
        else:
            missing.append(label)
    problems = []
    if missing:
        problems.append("the review lays out no " + ", no ".join(missing))
    if "what changes" in found and "the evidence" in found:
        if found["the evidence"] < found["what changes"]:
            problems.append("the evidence is laid out before what changes, which asks a "
                            "reader to judge a case before they know what it is")
    # The four words are declared in the module's own decision-button table,
    # which sits outside renderReview's body — read them from the whole file.
    words = [w for w in ANSWER_WORDS
             if re.search(re.escape(w).replace(r"\ ", r"[\s-]+"), review, re.I)]
    if len(words) < len(ANSWER_WORDS):
        problems.append(f"the answer offers {words}, not all four of {list(ANSWER_WORDS)}")
    renderers = len(re.findall(r"function\s+renderReview", review))
    if renderers > 1:
        problems.append(f"{renderers} review renderers — a proposal's origin cannot be a "
                        "fact about it if each origin is laid out by its own code")
    if problems:
        return KIT.bad("7", "; ".join(problems), parts_found=sorted(found))
    return KIT.ok("7",
                  "one review path lays out all five parts in the contract's order, and "
                  "offers all four answer words",
                  parts_found=sorted(found, key=found.get))


def check_granular_choices(snapshot):
    script = snapshot.script_text()
    tokens = write_tokens(snapshot)
    has_controls = control_present(snapshot, r"data-change-action\b", r"keepChange|revertChange")
    if not has_controls:
        return KIT.bad("8", "no per-change accept/revert controls exist, so nothing can "
                            "construct `ratified with edits` out of granular choices")
    body = handler_body(script, "[data-change-action]")
    if not reaches_a_write(body, tokens):
        return KIT.bad(
            "8",
            "per-change controls exist but their handler reaches no write the app "
            "declares, so a steward's kept-and-dropped choices are not carried into the "
            "one answer — they are shown and discarded",
            handler_excerpt=re.sub(r"\s+", " ", body)[:220])
    return KIT.ok("8", "per-change choices reach a write the app declares; whether that "
                       "write folds them into the one answer is beyond a static read",
                  handler_excerpt=re.sub(r"\s+", " ", body)[:160])


def check_ask(snapshot):
    has_control = control_present(snapshot, r"data-ask\b", r"askButton|>\s*Ask\s*<",
                                  r"\bopenAsk\b")
    ask_write = [p for p in snapshot.write_routes() if re.search(r"ask|propos", p, re.I)]
    if not has_control and not ask_write:
        return KIT.bad(
            "9",
            "Ask is offered nowhere and no write route produces a proposal, so the fifth "
            "write the umbrella names does not exist in this body",
            write_routes=snapshot.write_routes())
    if not ask_write:
        return KIT.bad("9", "an Ask control exists but no write route returns a proposal",
                       write_routes=snapshot.write_routes())
    if not has_control:
        return KIT.bad("9", f"a proposal-producing write exists ({ask_write}) but nothing "
                            "offers Ask at any scope")
    scopes = [s for s, pat in (("a paragraph", r"ask.{0,20}paragraph|scope=[\"']paragraph"),
                               ("a document", r"ask.{0,20}document|scope=[\"']document"),
                               ("every document", r"ask.{0,20}(all|every)|scope=[\"']all"))
              if control_present(snapshot, pat)]
    if len(scopes) < 3:
        return KIT.bad("9", f"Ask is offered at {scopes or 'no named scope'}, not at all "
                            "three the clause names", scopes=scopes)
    return KIT.ok("9", "Ask is offered at all three scopes and its write returns a proposal",
                  scopes=scopes, write_routes=ask_write)


def check_presence_and_reconciliation(snapshot):
    hay = snapshot.text("/") + "\n" + snapshot.script_text()
    presence = bool(re.search(r"presence|is-editing|editing-by|someone is editing", hay, re.I))
    choices = [c for c in RECONCILE_CHOICES if re.search(re.escape(c).replace(r"\ ", r"\s+"), hay, re.I)]
    editing = control_present(snapshot, r"data-edit\b", r"editDoc|editToggle|saveDoc")
    if not editing:
        return KIT.bad(
            "10",
            "there is no editing surface at all in this body (see rule 5), so the courtesy "
            "presence and the collision choices this clause requires have nothing to attach "
            "to; none of Use combined · Keep mine · Review both appears either",
            presence_shown=presence, choices_offered=choices)
    problems = []
    if not presence:
        problems.append("nothing shows that another person is editing a section")
    if len(choices) < 3:
        problems.append(f"the collision choices offered are {choices or 'none'}, not all of "
                        f"{list(RECONCILE_CHOICES)}")
    if problems:
        return KIT.bad("10", "; ".join(problems), choices_offered=choices)
    return KIT.ok("10", "editing shows courtesy presence and offers all three collision "
                        "choices", choices_offered=choices)


def check_lock_gate(snapshot):
    hay = snapshot.text("/") + "\n" + snapshot.script_text()
    control = re.search(r"lockButton|data-lock\b|>\s*Lock\b", hay, re.I)
    stated = [name for name, rx in LOCK_CONDITIONS if rx.search(hay)]
    if not control and not stated:
        return KIT.bad(
            "11",
            "no lock control and none of the four conditions appear anywhere the app "
            "serves, so nothing gates a document being locked — and nothing shows a "
            "steward why it is not yet lockable",
            conditions_shown=stated)
    if len(stated) < 4:
        return KIT.bad("11", f"the gate states {len(stated)} of the four conditions "
                             f"({stated or 'none'})", conditions_shown=stated)
    if not control:
        return KIT.bad("11", "the four conditions are shown but no control sits beside them",
                       conditions_shown=stated)
    disabled = bool(re.search(r"lock[^<>]{0,60}disabled|disabled[^<>]{0,60}lock", hay, re.I))
    return KIT.ok("11",
                  "the gate states all four conditions with a control beside them "
                  f"(a disabled state is expressed: {disabled}); that the control's live/inert "
                  "state tracks the conditions at runtime is beyond a static read",
                  conditions_shown=stated)


# --------------------------------------------------------------------------- #
# driver                                                                       #
# --------------------------------------------------------------------------- #
def run_conformance(snapshot):
    results = [
        check_documents_per_repository(snapshot),              # 1
        check_rendered_with_source(snapshot),                  # 2a
        check_render_carries_what_documents_contain(snapshot),  # 2b
        check_copy_download_zoom_width(snapshot),              # 3
        check_four_views(snapshot),                            # 4
        check_editing_offered_where_legal(snapshot),           # 5
        check_restore_is_real(snapshot),                       # 6a
        check_restore_can_name_a_snapshot(snapshot),           # 6b
        check_proposal_shape(snapshot),                        # 7
        check_granular_choices(snapshot),                      # 8
        check_ask(snapshot),                                   # 9
        check_presence_and_reconciliation(snapshot),           # 10
        check_lock_gate(snapshot),                             # 11
    ]
    return KIT.report(snapshot, results,
                      documents_read=len(snapshot.doc_routes()),
                      write_routes=snapshot.write_routes())


def main(argv=None) -> int:
    return run_cli("experience-direction-conformance",
                   "Assert experience-direction.v1 against the companion app.",
                   run_conformance, argv)


if __name__ == "__main__":
    raise SystemExit(main())
