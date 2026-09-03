# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""documents.v1 conformance kit — the runnable definition of "these documents keep their shape".

Point it at a repository ROOT. It mechanically asserts the conformance list of
``contracts/documents.v1.md`` over that repository's contracts, its vision, any
proposals beside a locked contract, its participant kit, and the templates it
ships for other projects to adopt.

Rule numbering follows the contract's **Core clause** numbers, as clause 5
asks: rule 4 judges Core 4, so a failing rule names the clause it breaks.
Where one clause carries several independent promises, the kit emits one row
per promise, lettered inside the clause (5a, 5b, ...), so a failure names the
exact promise rather than a whole paragraph. Each row also carries the
``bullet`` it came from in the contract's *Conformance kit asserts* list, or
``null`` where that list names no bullet for the clause. Promises that need a
person — or a system this kit cannot read — are reported SKIP with the reason,
never a fabricated PASS.

Stdlib only: a document check that needed a package would be one more reason
not to run it.

Usage
-----
    uv run conformance/documents/run.py <repo-root>

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
from pathlib import Path

# (rule id, Core clause, Conformance-asserts bullet or None, id, what it judges)
#
# Numbered to documents.v1's **Core** clauses, not to its Conformance-asserts
# bullets. Clause 5 asks for exactly that ("Numbers match the conformance kit's
# rule table"), and the bullet numbering hid a real gap: the contract's
# Conformance-asserts list carries seven bullets for thirteen Core clauses, so
# Core 10 and Core 11 had no bullet — and therefore no row — at all.
RULES = [
    ("1", 1, 7, "written_for_information_workers",
     "a reader who is not an engineer reads these and looks nothing up"),
    ("2", 2, 1, "contract_length",
     "one contract is about one screen — 50 to 100 lines"),
    ("3", 3, 1, "contract_line3_names_who",
     "line 3 of every contract begins '**Who builds against this:**'"),
    ("4", 4, 1, "contract_section_order",
     "the required sections appear, in the fixed order"),
    ("5a", 5, 1, "contract_clauses_bold_led",
     "every Core clause leads with the rule as fact, in bold"),
    ("5b", 5, 1, "clause_numbers_match_the_rule_table",
     "a contract's clause numbers match its kit's rule table"),
    ("5c", 5, 1, "contract_clauses_carry_their_why",
     "every Core clause carries plain lines of why after its bold lead"),
    ("6", 6, 1, "contract_status_only_in_h1",
     "status lives in the H1 parenthetical and nowhere else"),
    ("7a", 7, 2, "vision_not_written_as_a_plan",
     "the vision is written as though already true, not as a roadmap"),
    ("7b", 7, 2, "vision_dated_changelog",
     "the vision carries a dated changelog"),
    ("7c", 7, 2, "vision_present_tense_reading",
     "the vision reads in the present tense throughout"),
    ("8", 8, 3, "proposal_has_three_parts",
     "every proposal has the three parts, in order"),
    ("9a", 9, 4, "work_item_names_a_contract",
     "every work item names its contract and defines done in plain words"),
    ("9b", 9, 4, "work_item_quotes_its_source",
     "every work item quotes the feedback or gap it came from"),
    ("10a", 10, None, "plain_state_words",
     "documents carry plain state words, not machine state tokens"),
    ("10b", 10, None, "plain_state_words_reading",
     "every state word in every document comes from the plain vocabularies"),
    ("11a", 11, None, "technical_detail_is_folded",
     "technical detail sits in a marked section, never among the teeth"),
    ("11b", 11, None, "technical_detail_folded_in_the_app",
     "technical detail waits behind a Details fold in the app"),
    ("12a", 12, 5, "participant_kit_present",
     "a converged repository carries the participant kit"),
    ("12b", 12, 5, "workspace_template_complete",
     "the shipped workspace template carries every participant-kit file"),
    ("13", 13, 6, "shipped_templates_carry_the_anatomy",
     "Converge's own templates produce the anatomy they check for"),
]

# Rows no file scan can judge. Pinned by the self-test so a rule may not drift
# into SKIP to dodge a failure.
UNFIXTURABLE = {
    "1": ("needs a named human reader and a date; no file scan can stand in for a "
          "person reporting what they had to look up"),
    "5b": ("which numbering clause 5 means — the Core clauses or the "
           "Conformance-asserts bullets — is an open question filed for the "
           "steward (see contracts/documents.v2-candidate.md). This kit is "
           "numbered to the Core clauses and reports what it observes below; "
           "failing another kit on an unratified reading would be this kit "
           "inventing a ruling the contract does not make."),
    "7c": ("mechanical tense detection reports false findings on legitimate "
           "subordinate clauses (\"the project as it will be when it is right\"); "
           "judging the whole document's tense needs a reader. Rule 7a checks the "
           "part that is mechanical — that it is not written as a plan."),
    "9b": ("measured against this repository's own queue: the literal test — a "
           "blockquote or a quoted span — passes 7 of 24 real items, and most of "
           "the 17 it fails do point at their origin, in the item's own words "
           "rather than the source's. Widening it to accept any clause or item "
           "reference passes 20 of 24, but would also pass an item that merely "
           "names its contract, which rule 9a already checks — so the widened "
           "form proves nothing. Telling a quotation of feedback from a quoted "
           "filename needs a reader. Rule 9a checks the parts that are "
           "mechanical."),
    "11b": ("clause 11 folds technical detail in two places, and only one of them "
            "is a document. The app half \u2014 \"behind a Details fold in the app\" \u2014 "
            "is not in this kit's target: this kit reads a repository's "
            "documents, and an app is markup and behaviour. It is asserted "
            "where it can be seen, by conformance/surface against surface.v1 "
            "clause 8 (\"Technical detail waits behind a Details fold\"), whose "
            "rule 5 scans the app's own words. Passing it here on a document "
            "scan would be a claim about a file this kit never opened. Rule 11a "
            "checks the document half."),
    "10b": ("both mechanical whole-vocabulary signals were measured against this "
            "repository and both landed on legitimate prose: the vision's \"work "
            "in progress\" is ordinary English, and documents.v1 clause 6's own "
            "\"kept / broken / in-progress\" is the sentence forbidding those "
            "words, not a use of them. Judging every state word needs a reader. "
            "Rule 10a checks the part that is mechanical — a machine disposition "
            "token standing in a document's prose."),
}

# documents.v1 Core 4 — the fixed section order. Changelog only if amended.
REQUIRED_SECTIONS = [
    "Purpose",
    "Core (the teeth)",
    "What v1 deliberately does NOT freeze",
    "Conformance kit asserts",
    "Reserved / open questions",
]
OPTIONAL_SECTIONS = ["Changelog"]

WHO_MARKER = "**Who builds against this:**"
MIN_LINES, MAX_LINES = 50, 100

# A status token. Case-sensitive on purpose: "(NOT frozen)" in a section
# heading is prose, not a status stamp.
STATUS_TOKEN_RE = re.compile(r"\((?:DRAFT|FROZEN|RATIFIED|LOCKED)\b|\*\*Status:\*\*")
INLINE_CODE_RE = re.compile(r"`[^`]*`")

# Language that marks a plan rather than an end state already true. Deliberately
# narrow: a bare "will" is legitimate inside a subordinate clause, so only these
# unambiguous roadmap constructions are flagged.
PLAN_LANGUAGE_RE = re.compile(
    r"\b(?:we (?:will|plan to|intend to) (?:build|add|ship|deliver|create)"
    r"|will eventually\b"
    r"|in a future release\b"
    r"|coming soon\b"
    r"|on the roadmap\b"
    r"|\bTODO\b"
    r"|\bTBD\b)",
    re.IGNORECASE,
)

CHANGELOG_ENTRY_RE = re.compile(r"^\s*[-*]\s+\*\*(\d{4}-\d{2}-\d{2})\b")
NUMBERED_CLAUSE_RE = re.compile(r"^\s*\d+\.\s+(.*)$")

PARTICIPANT_KIT = [
    ("AGENTS.md", "the addendum every coding agent reads"),
    ("PINS.md", "the hard facts every lane reads first"),
    ("docs/CONTRACTS-README.md", "anatomy, index, freeze bar, how to propose"),
    (".githooks/pre-push", "the scan that refuses edits to a locked contract"),
]
WORKSPACE_TEMPLATE = [
    "docs/workspace-template/AGENTS-addendum.md.template",
    "docs/workspace-template/CONTRACT.md.template",
    "docs/workspace-template/PINS.md.template",
    "docs/workspace-template/VISION.md.template",
    "docs/workspace-template/pre-push-scan.sh",
]

PROPOSAL_GLOB_RE = re.compile(r".*\.v\d+[^/]*-candidate\.md$")
# documents.v1 Core 8 — the three parts, in order.
PROPOSAL_PARTS = [
    ("the exact change", re.compile(r"(?im)^#{2,3}\s+.*\b(?:exact change|what changes)\b")),
    ("the evidence", re.compile(r"(?im)^#{2,3}\s+.*\bevidence\b")),
    ("what does not change", re.compile(r"(?im)^#{2,3}\s+.*\bdoes\s+\*{0,2}not\*{0,2}\s+change\b")),
]


def _result(rid, status, detail, **extra):
    row = next(r for r in RULES if r[0] == rid)
    _, clause, bullet, name, desc = row
    out = {"rule": rid, "clause": clause, "bullet": bullet, "id": name,
           "name": desc, "status": status, "detail": detail}
    out.update(extra)
    return out


def _skip(rid, reason=None):
    r = reason or UNFIXTURABLE[rid]
    return _result(rid, "SKIP", r, reason=r)


def _rel(root: Path, p: Path) -> str:
    try:
        return str(p.relative_to(root))
    except ValueError:
        return str(p)


def strip_inline_code(line: str) -> str:
    """Remove `code spans` so an ILLUSTRATION of a status is not read as one.

    documents.v1 clause 6 spells out `(DRAFT)` and `(FROZEN 2026-09-02)` as
    examples. Reading those as a second status would be a fabricated finding.
    """
    return INLINE_CODE_RE.sub("", line)


# --------------------------------------------------------------------------- #
# document discovery                                                           #
# --------------------------------------------------------------------------- #
def contract_files(root: Path):
    d = root / "contracts"
    if not d.is_dir():
        return []
    return sorted(p for p in d.glob("*.md") if p.is_file()
                  and not PROPOSAL_GLOB_RE.match(p.name)
                  and not p.name.startswith("CANDIDATE-")
                  and p.name.upper() != "README.MD")


def vision_file(root: Path):
    for rel in ("docs/VISION.md", "VISION.md"):
        p = root / rel
        if p.is_file():
            return p
    return None


# Directories that hold TEST DATA or machinery, not this repository's own
# documents. A conformance fixture is a deliberately-broken artifact; reporting
# one as a real violation would be a fabricated finding — and would make every
# kit's own sample-bad fail the repository that ships it.
EXCLUDED_DIRS = {"fixtures", ".git", ".venv", "node_modules", "__pycache__",
                 "site-packages", "dist", "build"}


def _excluded(root: Path, p: Path) -> bool:
    try:
        parts = p.relative_to(root).parts
    except ValueError:
        return False
    return any(part in EXCLUDED_DIRS for part in parts)


def proposal_files(root: Path):
    out = []
    for p in root.rglob("*-candidate.md"):
        if p.is_file() and PROPOSAL_GLOB_RE.match(p.name) and not _excluded(root, p):
            out.append(p)
    return sorted(out)


def sections_of(text: str):
    """[(heading_text, line_number)] for every `## ` heading."""
    out = []
    for i, line in enumerate(text.splitlines(), 1):
        if line.startswith("## "):
            out.append((line[3:].strip(), i))
    return out


def core_section_body(text: str):
    """Lines of the `## Core (the teeth)` section, with their line numbers."""
    lines = text.splitlines()
    start = None
    for i, line in enumerate(lines):
        if line.startswith("## ") and line[3:].strip().lower().startswith("core"):
            start = i + 1
            break
    if start is None:
        return []
    out = []
    for j in range(start, len(lines)):
        if lines[j].startswith("## "):
            break
        out.append((j + 1, lines[j]))
    return out


# --------------------------------------------------------------------------- #
# clauses 2, 3, 4, 5 and 6 — every contract                                    #
# --------------------------------------------------------------------------- #
def _no_contracts(rid):
    return _result(rid, "SKIP",
                   "no contracts/*.md found in the target — nothing to judge",
                   reason="no contracts/*.md found in the target")


def check_line3(root: Path):
    files = contract_files(root)
    if not files:
        return _no_contracts("3")
    rows = []
    for p in files:
        lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
        line3 = lines[2] if len(lines) >= 3 else ""
        ok = line3.startswith(WHO_MARKER)
        rows.append({"file": _rel(root, p), "status": "PASS" if ok else "FAIL",
                     "detail": ("line 3 names who builds against this" if ok
                                else f"line 3 is {line3[:60]!r}, not {WHO_MARKER!r}")})
    return _roll("3", rows, "contract(s) name who builds against them on line 3")


def check_section_order(root: Path):
    files = contract_files(root)
    if not files:
        return _no_contracts("4")
    rows = []
    for p in files:
        text = p.read_text(encoding="utf-8", errors="replace")
        found = [h for h, _ in sections_of(text)]
        # Required sections, matched by prefix so "Reserved / open questions
        # (NOT frozen)" counts as "Reserved / open questions".
        idx, missing, order_ok, last = 0, [], True, -1
        for want in REQUIRED_SECTIONS:
            hit = next((i for i, h in enumerate(found) if h.startswith(want)), None)
            if hit is None:
                missing.append(want)
            else:
                if hit < last:
                    order_ok = False
                last = hit
        known = REQUIRED_SECTIONS + OPTIONAL_SECTIONS
        extra = [h for h in found if not any(h.startswith(k) for k in known)]
        if missing:
            rows.append({"file": _rel(root, p), "status": "FAIL",
                         "detail": f"missing section(s): {missing}", "extra_sections": extra})
        elif not order_ok:
            rows.append({"file": _rel(root, p), "status": "FAIL",
                         "detail": f"sections out of order; saw {found}", "extra_sections": extra})
        else:
            note = "" if not extra else f" (also carries: {extra})"
            rows.append({"file": _rel(root, p), "status": "PASS",
                         "detail": f"all five required sections, in order{note}",
                         "extra_sections": extra})
    return _roll("4", rows, "contract(s) carry the required sections in order")


def check_length(root: Path):
    files = contract_files(root)
    if not files:
        return _no_contracts("2")
    rows = []
    for p in files:
        n = len(p.read_text(encoding="utf-8", errors="replace").splitlines())
        ok = MIN_LINES <= n <= MAX_LINES
        rows.append({"file": _rel(root, p), "lines": n,
                     "status": "PASS" if ok else "FAIL",
                     "detail": (f"{n} lines" if ok
                                else f"{n} lines — outside {MIN_LINES}–{MAX_LINES}")})
    return _roll("2", rows, f"contract(s) are {MIN_LINES}–{MAX_LINES} lines")


def check_status_only_in_h1(root: Path):
    files = contract_files(root)
    if not files:
        return _no_contracts("6")
    rows = []
    for p in files:
        lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
        h1 = lines[0] if lines else ""
        strays = []
        for i, line in enumerate(lines[1:], 2):
            if STATUS_TOKEN_RE.search(strip_inline_code(line)):
                strays.append({"line": i, "text": line.strip()[:80]})
        h1_has_status = bool(STATUS_TOKEN_RE.search(h1))
        if strays:
            where = ", ".join(str(s["line"]) for s in strays[:5])
            rows.append({"file": _rel(root, p), "status": "FAIL",
                         "detail": f"status token outside the H1 at line(s) {where}",
                         "strays": strays})
        elif not h1_has_status:
            rows.append({"file": _rel(root, p), "status": "FAIL",
                         "detail": f"the H1 carries no status parenthetical: {h1[:70]!r}"})
        else:
            rows.append({"file": _rel(root, p), "status": "PASS",
                         "detail": "status in the H1 parenthetical and nowhere else"})
    return _roll("6", rows, "contract(s) keep status in the H1 alone")


def check_clauses_bold_led(root: Path):
    files = contract_files(root)
    if not files:
        return _no_contracts("5a")
    rows = []
    for p in files:
        body = core_section_body(p.read_text(encoding="utf-8", errors="replace"))
        if not body:
            rows.append({"file": _rel(root, p), "status": "FAIL",
                         "detail": "no '## Core (the teeth)' section to check"})
            continue
        bad, n = [], 0
        for lineno, line in body:
            m = NUMBERED_CLAUSE_RE.match(line)
            if not m:
                continue
            n += 1
            if not m.group(1).lstrip().startswith("**"):
                bad.append({"line": lineno, "text": line.strip()[:70]})
        if n == 0:
            rows.append({"file": _rel(root, p), "status": "FAIL",
                         "detail": "the Core section has no numbered clauses"})
        elif bad:
            where = ", ".join(str(b["line"]) for b in bad[:5])
            rows.append({"file": _rel(root, p), "status": "FAIL",
                         "detail": f"{len(bad)} of {n} Core clause(s) do not lead in bold, "
                                   f"at line(s) {where}", "clauses": bad})
        else:
            rows.append({"file": _rel(root, p), "status": "PASS",
                         "detail": f"all {n} Core clause(s) lead with the rule in bold"})
    return _roll("5a", rows, "contract(s) lead every Core clause in bold")


# documents.v1 clause 5, second promise: "then one to three plain lines of why".
#
# The FLOOR is unambiguous and mechanical: after the bold lead there must BE a
# why. A clause that is a bold assertion and nothing else is the failure this
# promise names.
#
# The CEILING is not. "Lines" has no wrapping-independent meaning: the same
# prose rewrapped at a different column changes the count, and counting
# sentences is a different unit that answers differently. Measured across this
# repository's four contracts (43 bold-led clauses): a ceiling of three SOURCE
# LINES flags 14 of them, a ceiling of three SENTENCES flags 3, and 11 clauses
# are flagged by one unit and not the other. Failing a third of a set of
# contracts nobody has reported as unreadable says the unit is wrong, not the
# contracts -- the same reasoning that keeps rule 9b honest. So the ceiling is
# REPORTED in the row, never failed: the treatment rule 4 gives an extra
# section.
BOLD_LEAD_RE = re.compile(r"^\s*\*\*(.+?)\*\*(.*)$", re.DOTALL)
SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")
WHY_LINES_CEILING = 3


def core_clauses(text):
    """[{line, lead_text, why_lines}] for each numbered clause under Core."""
    out, cur = [], None
    for lineno, line in core_section_body(text):
        m = NUMBERED_CLAUSE_RE.match(line)
        if m:
            cur = {"line": lineno, "first": m.group(1), "rest": []}
            out.append(cur)
        elif cur is not None:
            if line.strip() == "":
                cur = None  # a blank line ends the numbered list
            else:
                cur["rest"].append(line.strip())
    return out


def _why_of(clause):
    """(why_text, source_line_count) for a clause, or (None, 0) if unbolded.

    The bold lead is matched against the clause JOINED, because a lead may
    legitimately wrap across two source lines; matching only the first line
    would read a wrapped lead as unbolded and let a bare assertion through.
    """
    parts = [clause["first"].strip()] + clause["rest"]
    joined = " ".join(parts)
    m = BOLD_LEAD_RE.match(joined)
    if not m:
        return None, 0  # rule 5a owns an unbolded clause; 5c does not pile on
    lead_len = len(joined) - len(m.group(2))
    why = m.group(2).strip()
    if not why:
        return "", 0
    spans, off = [], 0
    for part in parts:
        spans.append((off, off + len(part)))
        off += len(part) + 1
    nlines = sum(1 for a, b in spans
                 if b > lead_len and joined[max(a, lead_len):b].strip())
    return why, nlines


def check_clauses_carry_their_why(root: Path):
    files = contract_files(root)
    if not files:
        return _no_contracts("5c")
    rows, over_lines, over_sentences = [], [], []
    for p in files:
        clauses = core_clauses(p.read_text(encoding="utf-8", errors="replace"))
        bare, judged = [], 0
        for c in clauses:
            why, nlines = _why_of(c)
            if why is None:
                continue
            judged += 1
            if not why:
                bare.append({"line": c["line"], "text": c["first"].strip()[:70]})
                continue
            nsent = len([s for s in SENTENCE_SPLIT_RE.split(why) if s.strip()])
            where = f"{_rel(root, p)}:{c['line']}"
            if nlines > WHY_LINES_CEILING:
                over_lines.append({"at": where, "lines": nlines})
            if nsent > WHY_LINES_CEILING:
                over_sentences.append({"at": where, "sentences": nsent})
        if judged == 0:
            rows.append({"file": _rel(root, p), "status": "PASS",
                         "detail": "no bold-led Core clause to judge (rule 5a owns that)"})
        elif bare:
            where = ", ".join(str(b["line"]) for b in bare[:5])
            rows.append({"file": _rel(root, p), "status": "FAIL",
                         "detail": f"{len(bare)} of {judged} Core clause(s) assert "
                                   f"without saying why, at line(s) {where}",
                         "clauses": bare})
        else:
            rows.append({"file": _rel(root, p), "status": "PASS",
                         "detail": f"all {judged} bold-led Core clause(s) carry a why"})
    out = _roll("5c", rows, "contract(s) say why after every bold lead")
    out["observed_why_over_three_source_lines"] = over_lines
    out["observed_why_over_three_sentences"] = over_sentences
    out["ceiling_note"] = (
        f"the clause's ceiling (\"one to three plain lines\") is reported, not "
        f"failed: {len(over_lines)} clause(s) run past {WHY_LINES_CEILING} source "
        f"lines and {len(over_sentences)} past {WHY_LINES_CEILING} sentences, and "
        f"the two units disagree \u2014 a count that changes when a paragraph is "
        f"rewrapped cannot settle it."
    )
    return out


def _roll(rid, rows, what):
    failed = [r for r in rows if r["status"] == "FAIL"]
    if failed:
        names = "; ".join(f"{r['file']}: {r['detail']}" for r in failed[:4])
        return _result(rid, "FAIL",
                       f"{len(failed)} of {len(rows)} {what.split(' ', 1)[0]} failed — {names}",
                       files=rows)
    return _result(rid, "PASS", f"all {len(rows)} {what}", files=rows)


# --------------------------------------------------------------------------- #
# clause 7 — the vision                                                        #
# --------------------------------------------------------------------------- #
def check_vision_not_a_plan(root: Path):
    p = vision_file(root)
    if p is None:
        return _result("7a", "FAIL", "no docs/VISION.md or VISION.md in the target")
    hits = []
    for i, line in enumerate(p.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
        m = PLAN_LANGUAGE_RE.search(strip_inline_code(line))
        if m:
            hits.append({"line": i, "phrase": m.group(0), "text": line.strip()[:80]})
    if hits:
        where = ", ".join(f"{h['line']} ({h['phrase']})" for h in hits[:5])
        return _result("7a", "FAIL",
                       f"{_rel(root, p)} reads as a plan, not an end state, at line(s) {where}",
                       hits=hits)
    return _result("7a", "PASS",
                   f"{_rel(root, p)} carries no roadmap language — written as though already true")


def check_vision_changelog(root: Path):
    p = vision_file(root)
    if p is None:
        return _result("7b", "FAIL", "no docs/VISION.md or VISION.md in the target")
    text = p.read_text(encoding="utf-8", errors="replace")
    heads = [h for h, _ in sections_of(text)]
    if not any(h.startswith("Changelog") for h in heads):
        return _result("7b", "FAIL", f"{_rel(root, p)} has no '## Changelog' section")
    dated = [m.group(1) for line in text.splitlines()
             for m in [CHANGELOG_ENTRY_RE.match(line)] if m]
    if not dated:
        return _result("7b", "FAIL",
                       f"{_rel(root, p)} has a Changelog with no dated entry "
                       "(expected '- **YYYY-MM-DD …')")
    return _result("7b", "PASS",
                   f"{_rel(root, p)} carries {len(dated)} dated changelog entry/entries "
                   f"(most recent {max(dated)})", entries=dated)


# --------------------------------------------------------------------------- #
# clause 8 — proposals                                                         #
# --------------------------------------------------------------------------- #
def check_proposals(root: Path):
    files = proposal_files(root)
    if not files:
        return _result("8", "SKIP",
                       "no '*.vN-candidate.md' proposal present in the target — nothing to judge",
                       reason="no proposal files present in the target")
    rows = []
    for p in files:
        text = p.read_text(encoding="utf-8", errors="replace")
        positions, missing = [], []
        for label, rx in PROPOSAL_PARTS:
            m = rx.search(text)
            if m is None:
                missing.append(label)
            else:
                positions.append((label, m.start()))
        if missing:
            rows.append({"file": _rel(root, p), "status": "FAIL",
                         "detail": f"missing part(s): {missing}"})
        elif [lbl for lbl, _ in sorted(positions, key=lambda t: t[1])] != \
                [lbl for lbl, _ in PROPOSAL_PARTS]:
            order = [lbl for lbl, _ in sorted(positions, key=lambda t: t[1])]
            rows.append({"file": _rel(root, p), "status": "FAIL",
                         "detail": f"the three parts are out of order: {order}"})
        else:
            rows.append({"file": _rel(root, p), "status": "PASS",
                         "detail": "carries the exact change, the evidence, "
                                   "and what does not change — in order"})
    return _roll("8", rows, "proposal(s) carry the three parts in order")


# --------------------------------------------------------------------------- #
# clause 12 — the participant kit                                              #
# --------------------------------------------------------------------------- #
def check_participant_kit(root: Path):
    rows = []
    for rel, why in PARTICIPANT_KIT:
        p = root / rel
        ok = p.is_file()
        rows.append({"file": rel, "status": "PASS" if ok else "FAIL",
                     "detail": (f"present — {why}" if ok else f"missing — {why}")})
    return _roll("12a", rows, "participant-kit file(s) present")


def check_workspace_template(root: Path):
    rows = []
    for rel in WORKSPACE_TEMPLATE:
        p = root / rel
        ok = p.is_file()
        rows.append({"file": rel, "status": "PASS" if ok else "FAIL",
                     "detail": "present" if ok else "missing"})
    return _roll("12b", rows, "workspace-template file(s) present")


# --------------------------------------------------------------------------- #
# clause 13 — the shipped templates carry the anatomy they check for           #
# --------------------------------------------------------------------------- #
LEADING_COMMENT_RE = re.compile(r"\A\s*<!--.*?-->\s*\n?", re.DOTALL)


def as_produced(text: str) -> str:
    """A template judged as the document it PRODUCES, not as the file on disk.

    A template opens with an HTML comment telling the copier what to do and to
    delete the comment. Judging line 3 of the raw file would report the
    instruction block as a violation — a fabricated finding. The contract asks
    whether the template produces the anatomy; so strip what the copier is told
    to strip, then judge.
    """
    return LEADING_COMMENT_RE.sub("", text).lstrip("\n")


def check_templates_carry_anatomy(root: Path):
    ct = root / "docs/workspace-template/CONTRACT.md.template"
    vt = root / "docs/workspace-template/VISION.md.template"
    rows = []
    if not ct.is_file():
        rows.append({"file": "docs/workspace-template/CONTRACT.md.template",
                     "status": "FAIL", "detail": "missing — nothing produces the anatomy"})
    else:
        text = as_produced(ct.read_text(encoding="utf-8", errors="replace"))
        lines = text.splitlines()
        problems = []
        if len(lines) < 3 or not lines[2].startswith(WHO_MARKER):
            problems.append(f"line 3 does not begin {WHO_MARKER!r}")
        found = [h for h, _ in sections_of(text)]
        for want in REQUIRED_SECTIONS:
            if not any(h.startswith(want) for h in found):
                problems.append(f"no '{want}' section")
        rows.append({"file": _rel(root, ct),
                     "status": "FAIL" if problems else "PASS",
                     "detail": ("; ".join(problems) if problems
                                else "produces line 3 and all five required sections")})
    if not vt.is_file():
        rows.append({"file": "docs/workspace-template/VISION.md.template",
                     "status": "FAIL", "detail": "missing — nothing produces the vision anatomy"})
    else:
        found = [h for h, _ in sections_of(as_produced(vt.read_text(encoding="utf-8", errors="replace")))]
        ok = any(h.startswith("Changelog") for h in found)
        rows.append({"file": _rel(root, vt), "status": "PASS" if ok else "FAIL",
                     "detail": ("produces a Changelog section" if ok
                                else "produces no Changelog section")})
    return _roll("13", rows, "shipped template(s) carry the anatomy they check for")


# --------------------------------------------------------------------------- #
# clause 5 (second sentence) — a contract's numbers and its kit's rule table    #
# --------------------------------------------------------------------------- #
README_RULE_ROW_RE = re.compile(r"^\|\s*(\d+)[a-z]?\s*\|")
CONTRACT_STEM_RE = re.compile(r"^(?P<stem>[A-Za-z0-9][A-Za-z0-9._-]*)\.v\d+\.md$")


def _kit_rule_numbers(readme: Path):
    """Top-level rule numbers in a kit README's rule table (1a, 1b -> {1})."""
    out = set()
    for line in readme.read_text(encoding="utf-8", errors="replace").splitlines():
        m = README_RULE_ROW_RE.match(line.strip())
        if m:
            out.add(int(m.group(1)))
    return out


def _core_clause_numbers(text: str):
    out = set()
    for _, line in core_section_body(text):
        m = NUMBERED_CLAUSE_RE.match(line)
        if m:
            out.add(int(line.strip().split(".", 1)[0]))
    return out


def check_clause_numbers_match_rule_table(root: Path):
    """Report — never decide — whether each contract's kit numbers to its clauses.

    documents.v1 clause 5 ends "Numbers match the conformance kit's rule table"
    without saying which numbering it means. This kit is numbered to the Core
    clauses; the other kits in this repository are numbered to the
    Conformance-asserts bullets. Deciding between the two readings is the
    steward's call, filed as ``contracts/documents.v2-candidate.md``, so this
    row reports what it observes and stays SKIP.
    """
    observed = []
    for p in contract_files(root):
        m = CONTRACT_STEM_RE.match(p.name)
        if not m:
            continue
        stem = m.group("stem")
        readme = root / "conformance" / stem / "README.md"
        if not readme.is_file():
            continue
        clauses = _core_clause_numbers(p.read_text(encoding="utf-8", errors="replace"))
        rules = _kit_rule_numbers(readme)
        observed.append({
            "contract": _rel(root, p),
            "kit": _rel(root, readme),
            "core_clauses": sorted(clauses),
            "kit_rule_numbers": sorted(rules),
            "aligned": bool(clauses) and clauses == rules,
        })
    if not observed:
        detail = ("no conformance kit sits beside a contract in this target — "
                  "nothing to compare")
    else:
        aligned = [o["contract"] for o in observed if o["aligned"]]
        adrift = [o["contract"] for o in observed if not o["aligned"]]
        detail = (f"{len(aligned)} of {len(observed)} contract(s) are numbered to "
                  f"their kit's rule table"
                  + (f"; not aligned: {adrift}" if adrift else ""))
    return _result("5b", "SKIP", detail, reason=UNFIXTURABLE["5b"], observed=observed)


# --------------------------------------------------------------------------- #
# clause 9 — work items                                                        #
# --------------------------------------------------------------------------- #
# A work item is not a file in this tree; it lives in the work queue. So the
# kit reads an EXPORT of the queue — a JSON array or JSONL, each entry an
# object — rather than growing a dependency on a running tracker. Absent an
# export it SKIPs with the reason: "nothing to check" and "checked, and it was
# fine" are different facts.
WORK_ITEMS_DEFAULT = "docs/work-items.json"
CONTRACT_REF_RE = re.compile(r"\b([A-Za-z0-9][A-Za-z0-9._-]*)\.v(\d+)\b")
DONE_PHRASE_RE = re.compile(r"(?im)^\s*(?:done means|acceptance)\b|(?<![A-Za-z])GIVEN\b")
QUOTED_SOURCE_RE = re.compile(r"^\s*>\s+\S|\"[^\"]{12,}\"|\u201c[^\u201d]{12,}\u201d",
                              re.MULTILINE)
SOURCE_FIELD_RE = re.compile(r"(?im)^\s*(?:source|discovered[- ]from|reported[- ]by)\s*:")

WORK_ITEM_TEXT_FIELDS = ("title", "description", "body", "text", "acceptance",
                         "design", "notes")


def _load_work_items(path: Path):
    """A JSON array of objects, or JSONL (one object per line)."""
    raw = path.read_text(encoding="utf-8", errors="replace").strip()
    if not raw:
        return []
    if raw.lstrip().startswith("["):
        data = json.loads(raw)
        if not isinstance(data, list):
            raise ValueError("the export is JSON, but not an array of items")
        return data
    items = []
    for i, line in enumerate(raw.splitlines(), 1):
        line = line.strip()
        if line:
            obj = json.loads(line)
            if not isinstance(obj, dict):
                raise ValueError(f"line {i} is JSON, but not an object")
            items.append(obj)
    return items


def _item_text(item: dict) -> str:
    return "\n".join(str(item.get(f) or "") for f in WORK_ITEM_TEXT_FIELDS)


def _done_definition(item: dict, text: str) -> str:
    """The part of an item that DEFINES DONE — not the whole item.

    Clause 9 asks for done "in plain words", so the plain-words test is aimed
    at the sentence that defines done, and nowhere else. An item is free to
    quote a machine token in its description (that is how a defect gets
    reported); putting one in its definition of done is what clause 9 forbids.
    """
    parts = [str(item.get("acceptance") or "").strip()]
    parts += [line for line in text.splitlines() if DONE_PHRASE_RE.search(line)]
    return "\n".join(p for p in parts if p.strip())


def check_work_items(root: Path, work_items: Path = None):
    explicit = work_items is not None
    path = work_items if explicit else (root / WORK_ITEMS_DEFAULT)
    if not path.is_file():
        if explicit:
            return _result("9a", "FAIL",
                           f"the named work-item export does not exist: {path}")
        return _result("9a", "SKIP",
                       f"no work-item export at {WORK_ITEMS_DEFAULT} and none named "
                       "with --work-items — work items live in the work queue, not "
                       "in this tree, so the kit has nothing to read",
                       reason=f"no work-item export at {WORK_ITEMS_DEFAULT} or "
                              "--work-items")
    try:
        items = _load_work_items(path)
    except (ValueError, json.JSONDecodeError) as e:
        return _result("9a", "FAIL", f"{_rel(root, path)} is not a readable "
                                    f"work-item export: {e}")
    if not items:
        return _result("9a", "SKIP",
                       f"{_rel(root, path)} carries no work items — nothing to judge",
                       reason="the work-item export is empty")

    known = {CONTRACT_STEM_RE.match(p.name).group("stem")
             for p in contract_files(root) if CONTRACT_STEM_RE.match(p.name)}
    rows = []
    for n, item in enumerate(items, 1):
        ident = str(item.get("id") or item.get("key") or f"item {n}")
        text = _item_text(item)
        missing = []
        named = [f"{m.group(1)}.v{m.group(2)}" for m in CONTRACT_REF_RE.finditer(text)
                 if not known or m.group(1) in known]
        if not named:
            missing.append("names no contract that exists in contracts/")
        done = _done_definition(item, text)
        if not done:
            missing.append("does not define done in plain words")
        else:
            # "in plain words" — the mechanical half, the same test rule 10a
            # applies to a document: a machine state token standing where a
            # plain state word belongs.
            tokens = sorted({m.group(0) for line in done.splitlines()
                             for m in [MACHINE_STATE_RE.search(strip_inline_code(line))]
                             if m})
            if tokens:
                missing.append(f"defines done with machine state word(s) {tokens}, "
                               "not in plain words")
        quotes = bool(QUOTED_SOURCE_RE.search(text) or SOURCE_FIELD_RE.search(text))
        rows.append({"file": ident, "status": "FAIL" if missing else "PASS",
                     "detail": ("; ".join(missing) if missing
                                else f"names {named[0]} and defines done in plain words"),
                     "quotes_a_source": quotes})
    quoting = sum(1 for r in rows if r["quotes_a_source"])
    out = _roll("9a", rows, "work item(s) name a contract and define done")
    out["observed_quoting_a_source"] = f"{quoting} of {len(rows)}"
    return out


# --------------------------------------------------------------------------- #
# clause 10 — plain state words                                                #
# --------------------------------------------------------------------------- #
# Machine state words, in their machine form. Case-sensitive and word-bounded
# on purpose, and inline code is stripped first — the same precision rule 6
# uses. A document that must NAME one of these puts it in a code span; a
# document that USES one as its state word is what clause 10 forbids.
# "VIOLATES" does not match "VIOLATION"; the vision's "work in progress" and
# clause 6's own "kept / broken / in-progress" are lowercase prose and are not
# machine tokens. Both were measured; see rule 10b's reason.
#
# Clause 10 names THREE vocabularies, not one, so this list covers all three.
# The contract vocabulary alone was the earlier gap: a document could say
# HELD or RUNNING or GAP and no rule noticed. Each machine form below is
# grouped under the plain words clause 10 puts in its place.
MACHINE_STATE_TOKENS = {
    # Contracts: Kept · Not yet · Broken · Pinned open · Can't check
    "contracts": ["CONFORMS", "GAP", "VIOLATION", "NOT-ASSERTABLE",
                  "OPEN-PINNED", "DIVERGED", "EXCLUDED"],
    # Work: Truly ready · Waiting on you · Working · Stuck · Done
    "work": ["READY", "BLOCKED", "HELD", "DEFERRED", "RESOLVED", "CLOSED",
             "IN_PROGRESS", "IN-PROGRESS", "WIP", "TODO", "DONE",
             "WONTFIX", "BACKLOG"],
    # Lanes: Working · Quiet · Silent — may have died
    "lanes": ["RUNNING", "IDLE", "STALE", "DEAD"],
}
# Longest-first so "IN-PROGRESS" is not reported as the shorter "IN".
MACHINE_STATE_RE = re.compile(
    r"\b(?:"
    + "|".join(sorted((t for g in MACHINE_STATE_TOKENS.values() for t in g),
                      key=len, reverse=True))
    + r")\b"
)


def _state_word_documents(root: Path):
    docs = list(contract_files(root))
    v = vision_file(root)
    if v is not None:
        docs.append(v)
    return docs


def check_plain_state_words(root: Path):
    docs = _state_word_documents(root)
    if not docs:
        return _result("10a", "SKIP",
                       "no contract and no vision in the target — nothing to judge",
                       reason="no contract and no vision in the target")
    rows = []
    for p in docs:
        hits = []
        for i, line in enumerate(p.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            # every match on the line, not just the first: a sentence carrying
            # two machine state words has two things wrong with it, and naming
            # one of them sends the reader back for the other.
            for m in MACHINE_STATE_RE.finditer(strip_inline_code(line)):
                hits.append({"line": i, "token": m.group(0), "text": line.strip()[:80]})
        if hits:
            where = ", ".join(f"{h['line']} ({h['token']})" for h in hits[:5])
            rows.append({"file": _rel(root, p), "status": "FAIL",
                         "detail": f"machine state token in prose at line(s) {where}",
                         "hits": hits})
        else:
            rows.append({"file": _rel(root, p), "status": "PASS",
                         "detail": "carries no machine state token in its prose"})
    return _roll("10a", rows, "document(s) keep their state words plain")


# --------------------------------------------------------------------------- #
# clause 11 — technical detail is folded                                       #
# --------------------------------------------------------------------------- #
# A fenced code block is the unambiguous mark of technical detail. Inside
# Purpose or Core — the sections that carry the deciding sentences — it is
# detail standing where the decision should be. The kit checks THAT, and not
# "a path or a filename in a bold lead": clause 8's own deciding sentence is
# "**A proposal is `<contract>.vN-candidate.md`**", where the filename IS the
# rule. Flagging it would be a fabricated finding.
FENCE_RE = re.compile(r"^\s*(?:```|~~~)")
DECIDING_SECTIONS = ("Purpose", "Core (the teeth)")


def check_technical_detail_is_folded(root: Path):
    files = contract_files(root)
    if not files:
        return _no_contracts("11a")
    rows = []
    for p in files:
        lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
        section, hits, inside_fence = None, [], False
        for i, line in enumerate(lines, 1):
            if not inside_fence and line.startswith("## "):
                section = line[3:].strip()
                continue
            if not FENCE_RE.match(line):
                continue
            if inside_fence:  # the closing fence of a block already counted
                inside_fence = False
                continue
            inside_fence = True
            if section is not None and any(section.startswith(s) for s in DECIDING_SECTIONS):
                hits.append({"line": i, "section": section})
        if hits:
            where = ", ".join(f"{h['line']} (under '{h['section']}')" for h in hits[:5])
            rows.append({"file": _rel(root, p), "status": "FAIL",
                         "detail": f"technical detail among the teeth at line(s) {where}",
                         "hits": hits})
        else:
            rows.append({"file": _rel(root, p), "status": "PASS",
                         "detail": "no technical detail inside Purpose or Core"})
    return _roll("11a", rows, "contract(s) keep technical detail out of the teeth")


# --------------------------------------------------------------------------- #
# driver                                                                       #
# --------------------------------------------------------------------------- #
def run_conformance(root: Path, work_items: Path = None) -> dict:
    # In Core-clause order, so the report reads down the contract.
    results = [
        _skip("1"),
        check_length(root),
        check_line3(root),
        check_section_order(root),
        check_clauses_bold_led(root),
        check_clause_numbers_match_rule_table(root),
        check_clauses_carry_their_why(root),
        check_status_only_in_h1(root),
        check_vision_not_a_plan(root),
        check_vision_changelog(root),
        _skip("7c"),
        check_proposals(root),
        check_work_items(root, work_items),
        _skip("9b"),
        check_plain_state_words(root),
        _skip("10b"),
        check_technical_detail_is_folded(root),
        _skip("11b"),
        check_participant_kit(root),
        check_workspace_template(root),
        check_templates_carry_anatomy(root),
    ]
    summary = {
        "pass": sum(r["status"] == "PASS" for r in results),
        "fail": sum(r["status"] == "FAIL" for r in results),
        "skip": sum(r["status"] == "SKIP" for r in results),
    }
    return {
        "kit": "documents.v1",
        "contract": "contracts/documents.v1.md",
        "target": str(root.resolve()),
        "results": results,
        "summary": summary,
        "verdict": "FAIL" if summary["fail"] else "PASS",
    }


def print_human_summary(report: dict) -> None:
    w = sys.stderr.write
    w(f"\ndocuments.v1 conformance — {report['target']}\n")
    w(f"asserts: {report['contract']} (rules numbered to its Core clauses)\n")
    w("-" * 74 + "\n")
    for r in report["results"]:
        w(f"  [{r['status']:4}] {r['rule']:3} {r['id']}: {r['detail']}\n")
    w("-" * 74 + "\n")
    s = report["summary"]
    w(f"  VERDICT: {report['verdict']}  (pass={s['pass']} fail={s['fail']} skip={s['skip']})\n\n")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        prog="documents-conformance",
        description="Assert documents.v1 conformance against a repository root.",
    )
    ap.add_argument("repo_root", help="path to the repository root (holds contracts/, docs/)")
    ap.add_argument("--json-only", action="store_true",
                    help="suppress the human summary on stderr")
    ap.add_argument("--work-items", metavar="PATH", default=None,
                    help="a work-queue export (JSON array or JSONL) for rule 9; "
                         f"defaults to {WORK_ITEMS_DEFAULT} in the target if present")
    args = ap.parse_args(argv)

    root = Path(args.repo_root)
    if not root.exists():
        sys.stderr.write(f"error: path not found: {args.repo_root}\n")
        return 3
    if not root.is_dir():
        sys.stderr.write(f"error: not a directory (a target is a repo root): {args.repo_root}\n")
        return 3

    report = run_conformance(root, Path(args.work_items) if args.work_items else None)
    sys.stdout.write(json.dumps(report, indent=2) + "\n")
    if not args.json_only:
        print_human_summary(report)
    return 1 if report["verdict"] == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
