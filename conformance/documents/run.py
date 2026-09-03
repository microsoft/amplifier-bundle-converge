# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""documents.v1 conformance kit — the runnable definition of "these documents keep their shape".

Point it at a repository ROOT. It mechanically asserts the conformance list of
``contracts/documents.v1.md`` over that repository's contracts, its vision, any
proposals beside a locked contract, its participant kit, and the templates it
ships for other projects to adopt.

Rule numbering follows the contract's bullet order. Where one bullet names
several independent promises, the kit emits one row per promise, lettered
inside the bullet (1a, 1b, ...), so a failure names the exact promise rather
than a whole paragraph. Promises that need a person — or a system this kit
cannot read — are reported SKIP with the reason, never a fabricated PASS.

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

RULES = [
    ("1a", 1, "contract_line3_names_who",
     "line 3 of every contract begins '**Who builds against this:**'"),
    ("1b", 1, "contract_section_order",
     "the required sections appear, in the fixed order"),
    ("1c", 1, "contract_length",
     "one contract is about one screen — 50 to 100 lines"),
    ("1d", 1, "contract_status_only_in_h1",
     "status lives in the H1 parenthetical and nowhere else"),
    ("1e", 1, "contract_clauses_bold_led",
     "every Core clause leads with the rule as fact, in bold"),
    ("2a", 2, "vision_not_written_as_a_plan",
     "the vision is written as though already true, not as a roadmap"),
    ("2b", 2, "vision_dated_changelog",
     "the vision carries a dated changelog"),
    ("2c", 2, "vision_present_tense_reading",
     "the vision reads in the present tense throughout"),
    ("3", 3, "proposal_has_three_parts",
     "every proposal has the three parts, in order"),
    ("4", 4, "work_item_names_a_contract",
     "every work item names its contract and quotes its source"),
    ("5a", 5, "participant_kit_present",
     "a converged repository carries the participant kit"),
    ("5b", 5, "workspace_template_complete",
     "the shipped workspace template carries every participant-kit file"),
    ("6", 6, "shipped_templates_carry_the_anatomy",
     "Converge's own templates produce the anatomy they check for"),
    ("7", 7, "non_engineer_reader_recorded",
     "a reader who is not an engineer read these and looked nothing up"),
]

# Rows no file scan can judge. Pinned by the self-test so a rule may not drift
# into SKIP to dodge a failure.
UNFIXTURABLE = {
    "2c": ("mechanical tense detection reports false findings on legitimate "
           "subordinate clauses (\"the project as it will be when it is right\"); "
           "judging the whole document's tense needs a reader. Rule 2a checks the "
           "part that is mechanical — that it is not written as a plan."),
    "4": ("work items live in the work-tracker queue, not in the repository; "
          "this kit reads files"),
    "7": ("needs a named human reader and a date; no file scan can stand in for a "
          "person reporting what they had to look up"),
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
    bullet = next(r[1] for r in RULES if r[0] == rid)
    name = next(r[2] for r in RULES if r[0] == rid)
    desc = next(r[3] for r in RULES if r[0] == rid)
    out = {"rule": rid, "bullet": bullet, "id": name, "name": desc,
           "status": status, "detail": detail}
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
# bullet 1 — every contract                                                    #
# --------------------------------------------------------------------------- #
def _no_contracts(rid):
    return _result(rid, "SKIP",
                   "no contracts/*.md found in the target — nothing to judge",
                   reason="no contracts/*.md found in the target")


def check_line3(root: Path):
    files = contract_files(root)
    if not files:
        return _no_contracts("1a")
    rows = []
    for p in files:
        lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
        line3 = lines[2] if len(lines) >= 3 else ""
        ok = line3.startswith(WHO_MARKER)
        rows.append({"file": _rel(root, p), "status": "PASS" if ok else "FAIL",
                     "detail": ("line 3 names who builds against this" if ok
                                else f"line 3 is {line3[:60]!r}, not {WHO_MARKER!r}")})
    return _roll("1a", rows, "contract(s) name who builds against them on line 3")


def check_section_order(root: Path):
    files = contract_files(root)
    if not files:
        return _no_contracts("1b")
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
    return _roll("1b", rows, "contract(s) carry the required sections in order")


def check_length(root: Path):
    files = contract_files(root)
    if not files:
        return _no_contracts("1c")
    rows = []
    for p in files:
        n = len(p.read_text(encoding="utf-8", errors="replace").splitlines())
        ok = MIN_LINES <= n <= MAX_LINES
        rows.append({"file": _rel(root, p), "lines": n,
                     "status": "PASS" if ok else "FAIL",
                     "detail": (f"{n} lines" if ok
                                else f"{n} lines — outside {MIN_LINES}–{MAX_LINES}")})
    return _roll("1c", rows, f"contract(s) are {MIN_LINES}–{MAX_LINES} lines")


def check_status_only_in_h1(root: Path):
    files = contract_files(root)
    if not files:
        return _no_contracts("1d")
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
    return _roll("1d", rows, "contract(s) keep status in the H1 alone")


def check_clauses_bold_led(root: Path):
    files = contract_files(root)
    if not files:
        return _no_contracts("1e")
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
    return _roll("1e", rows, "contract(s) lead every Core clause in bold")


def _roll(rid, rows, what):
    failed = [r for r in rows if r["status"] == "FAIL"]
    if failed:
        names = "; ".join(f"{r['file']}: {r['detail']}" for r in failed[:4])
        return _result(rid, "FAIL",
                       f"{len(failed)} of {len(rows)} {what.split(' ', 1)[0]} failed — {names}",
                       files=rows)
    return _result(rid, "PASS", f"all {len(rows)} {what}", files=rows)


# --------------------------------------------------------------------------- #
# bullet 2 — the vision                                                        #
# --------------------------------------------------------------------------- #
def check_vision_not_a_plan(root: Path):
    p = vision_file(root)
    if p is None:
        return _result("2a", "FAIL", "no docs/VISION.md or VISION.md in the target")
    hits = []
    for i, line in enumerate(p.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
        m = PLAN_LANGUAGE_RE.search(strip_inline_code(line))
        if m:
            hits.append({"line": i, "phrase": m.group(0), "text": line.strip()[:80]})
    if hits:
        where = ", ".join(f"{h['line']} ({h['phrase']})" for h in hits[:5])
        return _result("2a", "FAIL",
                       f"{_rel(root, p)} reads as a plan, not an end state, at line(s) {where}",
                       hits=hits)
    return _result("2a", "PASS",
                   f"{_rel(root, p)} carries no roadmap language — written as though already true")


def check_vision_changelog(root: Path):
    p = vision_file(root)
    if p is None:
        return _result("2b", "FAIL", "no docs/VISION.md or VISION.md in the target")
    text = p.read_text(encoding="utf-8", errors="replace")
    heads = [h for h, _ in sections_of(text)]
    if not any(h.startswith("Changelog") for h in heads):
        return _result("2b", "FAIL", f"{_rel(root, p)} has no '## Changelog' section")
    dated = [m.group(1) for line in text.splitlines()
             for m in [CHANGELOG_ENTRY_RE.match(line)] if m]
    if not dated:
        return _result("2b", "FAIL",
                       f"{_rel(root, p)} has a Changelog with no dated entry "
                       "(expected '- **YYYY-MM-DD …')")
    return _result("2b", "PASS",
                   f"{_rel(root, p)} carries {len(dated)} dated changelog entry/entries "
                   f"(most recent {max(dated)})", entries=dated)


# --------------------------------------------------------------------------- #
# bullet 3 — proposals                                                         #
# --------------------------------------------------------------------------- #
def check_proposals(root: Path):
    files = proposal_files(root)
    if not files:
        return _result("3", "SKIP",
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
    return _roll("3", rows, "proposal(s) carry the three parts in order")


# --------------------------------------------------------------------------- #
# bullet 5 — the participant kit                                               #
# --------------------------------------------------------------------------- #
def check_participant_kit(root: Path):
    rows = []
    for rel, why in PARTICIPANT_KIT:
        p = root / rel
        ok = p.is_file()
        rows.append({"file": rel, "status": "PASS" if ok else "FAIL",
                     "detail": (f"present — {why}" if ok else f"missing — {why}")})
    return _roll("5a", rows, "participant-kit file(s) present")


def check_workspace_template(root: Path):
    rows = []
    for rel in WORKSPACE_TEMPLATE:
        p = root / rel
        ok = p.is_file()
        rows.append({"file": rel, "status": "PASS" if ok else "FAIL",
                     "detail": "present" if ok else "missing"})
    return _roll("5b", rows, "workspace-template file(s) present")


# --------------------------------------------------------------------------- #
# bullet 6 — the shipped templates carry the anatomy they check for            #
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
    return _roll("6", rows, "shipped template(s) carry the anatomy they check for")


# --------------------------------------------------------------------------- #
# driver                                                                       #
# --------------------------------------------------------------------------- #
def run_conformance(root: Path) -> dict:
    results = [
        check_line3(root),
        check_section_order(root),
        check_length(root),
        check_status_only_in_h1(root),
        check_clauses_bold_led(root),
        check_vision_not_a_plan(root),
        check_vision_changelog(root),
        _skip("2c"),
        check_proposals(root),
        _skip("4"),
        check_participant_kit(root),
        check_workspace_template(root),
        check_templates_carry_anatomy(root),
        _skip("7"),
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
    w(f"asserts: {report['contract']} (\"Conformance kit asserts\")\n")
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
    args = ap.parse_args(argv)

    root = Path(args.repo_root)
    if not root.exists():
        sys.stderr.write(f"error: path not found: {args.repo_root}\n")
        return 3
    if not root.is_dir():
        sys.stderr.write(f"error: not a directory (a target is a repo root): {args.repo_root}\n")
        return 3

    report = run_conformance(root)
    sys.stdout.write(json.dumps(report, indent=2) + "\n")
    if not args.json_only:
        print_human_summary(report)
    return 1 if report["verdict"] == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
