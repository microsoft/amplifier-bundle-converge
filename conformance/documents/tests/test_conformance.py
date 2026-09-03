"""Self-test for the documents.v1 conformance kit.

The kit must go GREEN against a repository whose documents keep their shape
(fixtures/sample-good) and RED — with named rule failures — against one whose
documents do not (fixtures/sample-bad).

The load-bearing test is `test_every_rule_has_a_negative_fixture`: a rule
nobody can make fail is a rule that proves nothing. Rules that need a person,
or a system this kit cannot read, are SKIPped with a reason, and the SKIP set
is pinned so a rule cannot quietly drift into SKIP to dodge a failure.

Runnable two ways (the assertions are identical):
  * with pytest:  uv run --with pytest pytest conformance/documents/tests/ -q
  * no deps:      uv run conformance/documents/tests/test_conformance.py
"""

import json
import re
import shutil
import subprocess
from pathlib import Path

KIT = Path(__file__).resolve().parent.parent  # conformance/documents/
RUN = KIT / "run.py"
REPO = KIT.parent.parent  # the repository root this kit ships in
GOOD = KIT / "fixtures" / "sample-good"
BAD = KIT / "fixtures" / "sample-bad"

# Declared in run.py as un-judgeable from files. Both fixtures carry a proposal
# and a work-item export, so rules 8 and 9 are checkable in both and are NOT in
# this set.
EXPECTED_SKIPS = {"1", "5b", "7c", "7d", "9b", "10b", "11b", "13b"}

# documents.v1 Core clauses. Every one must be answered by at least one row.
CORE_CLAUSES = set(range(1, 15))


def _uv() -> str:
    uv = shutil.which("uv")
    if not uv:
        raise RuntimeError("uv is required to run the documents kit.")
    return uv


def run_kit(target):
    proc = subprocess.run(
        [_uv(), "run", str(RUN), str(target), "--json-only"],
        capture_output=True, text=True, timeout=300, check=False,
    )
    assert proc.stdout.strip(), f"kit produced no JSON report; stderr:\n{proc.stderr}"
    return proc.returncode, json.loads(proc.stdout)


def by_rule(report):
    return {r["rule"]: r for r in report["results"]}


# --------------------------------------------------------------------------- #
# GREEN on a conforming repository                                            #
# --------------------------------------------------------------------------- #
def test_good_repo_conforms():
    code, report = run_kit(GOOD)
    assert report["verdict"] == "PASS", report
    assert code == 0
    failed = {r["rule"] for r in report["results"] if r["status"] == "FAIL"}
    assert failed == set(), f"sample-good should fail nothing, got {failed}"


# --------------------------------------------------------------------------- #
# RED on a non-conforming repository, with NAMED rule failures                #
# --------------------------------------------------------------------------- #
def test_bad_repo_fails_named_rules():
    code, report = run_kit(BAD)
    assert report["verdict"] == "FAIL", report
    assert code == 1
    failed = {r["rule"] for r in report["results"] if r["status"] == "FAIL"}
    assert failed == {"2", "2b", "3", "4", "5a", "5c", "6", "6b", "7a", "7b",
                      "8", "9a", "10a", "11a", "12a", "12b", "12c", "13a"}, failed


def test_bad_failures_carry_readable_detail():
    _, report = run_kit(BAD)
    rules = by_rule(report)
    assert "line 3" in rules["3"]["detail"]
    assert "missing section" in rules["4"]["detail"]
    assert "outside 50" in rules["2"]["detail"]
    assert "outside the H1" in rules["6"]["detail"]
    assert "bold" in rules["5a"]["detail"]
    assert "without saying why" in rules["5c"]["detail"]
    assert "plan" in rules["7a"]["detail"]
    assert "Changelog" in rules["7b"]["detail"]
    assert "missing part" in rules["8"]["detail"]
    assert "names no contract" in rules["9a"]["detail"]
    assert "machine state word" in rules["9a"]["detail"]
    assert "CONFORMS" in rules["10a"]["detail"]
    assert "among the teeth" in rules["11a"]["detail"]
    assert "past two screens" in rules["2b"]["detail"]
    assert "worn as a status" in rules["6b"]["detail"]
    assert "AGENTS.md" in rules["12a"]["detail"]


# --------------------------------------------------------------------------- #
# THE load-bearing test: no rule proves nothing                               #
# --------------------------------------------------------------------------- #
def test_every_rule_has_a_negative_fixture():
    """Every rule the kit emits must either FAIL on sample-bad, or be a
    declared SKIP with a reason. A rule that can only ever PASS is decoration."""
    _, good = run_kit(GOOD)
    _, bad = run_kit(BAD)
    good_rules, bad_rules = by_rule(good), by_rule(bad)
    assert set(good_rules) == set(bad_rules), "the two runs emitted different rule sets"

    unproven = [rule for rule, row in good_rules.items()
                if row["status"] != "SKIP" and bad_rules[rule]["status"] != "FAIL"]
    assert not unproven, (
        f"rules with no negative fixture (they never FAIL on sample-bad): {unproven}"
    )


def test_skips_are_exactly_the_declared_set_and_carry_a_reason():
    for fixture in (GOOD, BAD):
        _, report = run_kit(fixture)
        skipped = {r["rule"] for r in report["results"] if r["status"] == "SKIP"}
        assert skipped == EXPECTED_SKIPS, (
            f"{fixture.name}: SKIP set drifted — expected {EXPECTED_SKIPS}, got {skipped}"
        )
        for r in report["results"]:
            if r["status"] == "SKIP":
                assert r.get("reason", "").strip(), f"rule {r['rule']} SKIPs with no reason"


def test_absent_evidence_skips_rather_than_passing(tmp_path=None):
    """A target with no proposal must SKIP rule 3, not PASS it vacuously.

    'Nothing to check' and 'checked, and it was fine' are different facts, and
    a kit that conflates them reports work it never did.
    """
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        empty = Path(d)
        (empty / "contracts").mkdir()
        _, report = run_kit(empty)
        rules = by_rule(report)
        assert rules["8"]["status"] == "SKIP", rules["8"]
        assert "no proposal" in rules["8"]["reason"].lower(), rules["8"]
        # Same for the work-item export: absent is SKIP, never a vacuous PASS.
        assert rules["9a"]["status"] == "SKIP", rules["9a"]
        assert "work-item export" in rules["9a"]["reason"], rules["9a"]
        # Same discipline for the contract rules when there are no contracts.
        for rule in ("2", "2b", "3", "4", "5a", "5c", "6", "6b"):
            assert rules[rule]["status"] == "SKIP", rules[rule]
            assert rules[rule].get("reason", "").strip(), rules[rule]


def test_no_rule_is_ever_fabricated():
    for fixture in (GOOD, BAD, REPO):
        _, report = run_kit(fixture)
        for r in report["results"]:
            assert r["status"] in {"PASS", "FAIL", "SKIP"}, r
            assert r["detail"].strip(), f"rule {r['rule']} reports no detail"


# --------------------------------------------------------------------------- #
# The kit must not report a template's own instructions as a violation        #
# --------------------------------------------------------------------------- #
def test_template_is_judged_as_the_document_it_produces():
    """A template opens with an HTML comment telling the copier to delete it.
    Judging line 3 of the raw file would be a fabricated finding."""
    _, report = run_kit(GOOD)
    assert by_rule(report)["13a"]["status"] == "PASS", by_rule(report)["13a"]


# --------------------------------------------------------------------------- #
# An illustration of a status is not a status                                 #
# --------------------------------------------------------------------------- #
def test_inline_code_is_not_read_as_a_second_status():
    """documents.v1 clause 6 spells out `(DRAFT)` and `(FROZEN …)` as examples.
    Reading those as a stray status would be a fabricated finding — so this
    repository's own contracts must pass rule 1d."""
    _, report = run_kit(REPO)
    assert by_rule(report)["6"]["status"] == "PASS", by_rule(report)["6"]


# --------------------------------------------------------------------------- #
# Every Core clause is answered — by a rule, or by a SKIP with a reason        #
# --------------------------------------------------------------------------- #
def _core_clause_numbers_of_the_contract():
    text = (REPO / "contracts" / "documents.v1.md").read_text(encoding="utf-8")
    lines, out, inside = text.splitlines(), set(), False
    for line in lines:
        if line.startswith("## "):
            inside = line[3:].strip().lower().startswith("core")
            continue
        if inside and re.match(r"^\s*\d+\.\s+", line):
            out.add(int(line.strip().split(".", 1)[0]))
    return out


def test_every_core_clause_has_a_row():
    """No clause of documents.v1 may be silently absent from the kit.

    A clause with no row is the failure that produced this kit's three GAP
    rows: the table used to be numbered to the Conformance-asserts bullets,
    and Core 10 and Core 11 have no bullet, so they had no row either.
    """
    contract_clauses = _core_clause_numbers_of_the_contract()
    assert contract_clauses == CORE_CLAUSES, (
        f"documents.v1 Core is no longer clauses {sorted(CORE_CLAUSES)}: "
        f"{sorted(contract_clauses)}"
    )
    _, report = run_kit(GOOD)
    answered = {r["clause"] for r in report["results"]}
    missing = CORE_CLAUSES - answered
    assert not missing, f"Core clause(s) with no row in the kit: {sorted(missing)}"
    for r in report["results"]:
        if r["status"] == "SKIP":
            assert r.get("reason", "").strip(), f"rule {r['rule']} SKIPs with no reason"


# --------------------------------------------------------------------------- #
# The rule table in the README stays numbered to the contract's Core clauses  #
# --------------------------------------------------------------------------- #
def test_readme_rule_table_covers_every_emitted_rule():
    readme = (KIT / "README.md").read_text(encoding="utf-8")
    _, report = run_kit(GOOD)
    for r in report["results"]:
        assert f"| {r['rule']} " in readme, (
            f"rule {r['rule']} is emitted but has no row in the README rule table"
        )


def test_readme_rule_table_is_numbered_to_the_core_clauses():
    """documents.v1 clause 5: "Numbers match the conformance kit's rule table."

    A failing rule must name the clause it breaks, so the table's top-level
    numbers are exactly the contract's Core clause numbers — no more, no fewer.
    """
    readme = (KIT / "README.md").read_text(encoding="utf-8")
    numbers = {int(m.group(1))
               for line in readme.splitlines()
               for m in [re.match(r"^\|\s*(\d+)[a-z]?\s*\|", line.strip())] if m}
    assert numbers == CORE_CLAUSES, (
        f"the README rule table is numbered {sorted(numbers)}, not to "
        f"documents.v1's Core clauses {sorted(CORE_CLAUSES)}"
    )


# --------------------------------------------------------------------------- #
# The new rules are not false-positive machines                               #
# --------------------------------------------------------------------------- #
def test_plain_prose_is_not_read_as_a_machine_state_token():
    """Rule 10a must stay quiet on this repository's own documents.

    Measured: the vision says "work in progress" (ordinary English) and
    documents.v1 clause 6 says "kept / broken / in-progress" (the sentence
    forbidding those words). Flagging either would be a fabricated finding.
    """
    _, report = run_kit(REPO)
    assert by_rule(report)["10a"]["status"] == "PASS", by_rule(report)["10a"]


def test_a_filename_in_a_deciding_sentence_is_not_technical_detail():
    """Rule 11 must stay quiet on documents.v1 clause 8, whose deciding
    sentence is "**A proposal is `<contract>.vN-candidate.md`**" — there the
    filename IS the rule, not detail that belongs in a marked section."""
    _, report = run_kit(REPO)
    assert by_rule(report)["11a"]["status"] == "PASS", by_rule(report)["11a"]


def test_rule_10a_covers_all_three_vocabularies_clause_10_names():
    """Clause 10 names three vocabularies — contracts, work, lanes — so the
    machine forms of all three must be catchable, not just the contract's.

    The earlier rule listed only the ledger dispositions, so a document could
    say HELD or RUNNING and no rule noticed. sample-bad now carries one word
    from each vocabulary; rule 10a must name them.
    """
    _, report = run_kit(BAD)
    row = by_rule(report)["10a"]
    assert row["status"] == "FAIL", row
    tokens = {h["token"] for f in row["files"] for h in f.get("hits", [])}
    for vocabulary, token in (("contracts", "CONFORMS"),
                              ("work", "BLOCKED"),
                              ("lanes", "RUNNING")):
        assert token in tokens, f"the {vocabulary} vocabulary is unguarded: {tokens}"


def test_rule_9a_requires_done_in_plain_words_not_just_present():
    """Clause 9 asks for done "in plain words".

    An item that defines done at all used to pass. sample-bad's third item
    defines done entirely in machine state words, and must FAIL for that
    reason and be named for it.
    """
    _, report = run_kit(BAD)
    row = by_rule(report)["9a"]
    bad3 = next(f for f in row["files"] if f["file"] == "bad-3")
    assert bad3["status"] == "FAIL", bad3
    assert "machine state word" in bad3["detail"], bad3
    assert "GAP" in bad3["detail"] or "CONFORMS" in bad3["detail"], bad3


def test_rule_5c_fails_a_clause_that_asserts_without_saying_why():
    """Clause 5: "Clauses lead with the rule as fact, in bold, then one to
    three plain lines of why." A bold assertion with no why breaks it."""
    _, good = run_kit(GOOD)
    _, bad = run_kit(BAD)
    assert by_rule(good)["5c"]["status"] == "PASS", by_rule(good)["5c"]
    row = by_rule(bad)["5c"]
    assert row["status"] == "FAIL", row
    assert "without saying why" in row["detail"], row


def test_rule_5c_reports_the_line_ceiling_and_does_not_fail_on_it():
    """The ceiling ("one to three plain lines") is reported, never failed.

    "Lines" has no wrapping-independent meaning, and the two candidate units
    answer differently: measured against this repository, a source-line
    ceiling flags many more clauses than a sentence ceiling. A verdict that
    flips when a paragraph is reflowed would be a false-positive machine, so
    the row must carry the observation AND still PASS.
    """
    _, report = run_kit(REPO)
    row = by_rule(report)["5c"]
    assert row["status"] == "PASS", row
    over_lines = row["observed_why_over_three_source_lines"]
    over_sentences = row["observed_why_over_three_sentences"]
    assert over_lines, "the observation is empty — the ceiling is not being reported"
    assert len(over_lines) > len(over_sentences), (
        "the two units no longer disagree; re-measure before enforcing a ceiling"
    )
    assert row["ceiling_note"].strip()


def test_rule_11_is_split_and_the_app_half_says_where_it_is_checked():
    """Clause 11 folds detail in two places. This kit reads documents, so the
    app half is a SKIP that names the kit which does assert it — not a pass
    on a file this kit never opened."""
    _, report = run_kit(REPO)
    row = by_rule(report)["11b"]
    assert row["status"] == "SKIP", row
    assert "surface" in row["reason"], row
    assert by_rule(report)["11a"]["clause"] == row["clause"] == 11


# --------------------------------------------------------------------------- #
# The six ledger rows this kit was reported for (CVG-058/059/061/063/064/065)  #
# --------------------------------------------------------------------------- #
# Each names a documents.v1 Core clause whose promise the kit did not assert.
# Every one must now be answered by a row -- a real PASS/FAIL, or a SKIP with
# a reason. A clause answered by nothing is exactly what those rows recorded.
LEDGER_ROWS_UNDER_REPAIR = {
    "CVG-058": (1, "terms of art are defined at first use or not used"),
    "CVG-059": (2, "a vision fits two screens"),
    "CVG-061": (6, "neither vision nor contract carries kept / broken / in-progress"),
    "CVG-063": (7, "changelog entries carry evidence"),
    "CVG-064": (12, "what each participant-kit file must contain"),
    "CVG-065": (13, "the protocol authority checks documents against this anatomy"),
}


def test_every_reported_ledger_row_has_an_answering_row():
    _, report = run_kit(GOOD)
    rows = report["results"]
    for ledger_id, (clause, promise) in LEDGER_ROWS_UNDER_REPAIR.items():
        answering = [r for r in rows if r["clause"] == clause]
        assert answering, f"{ledger_id} (Core {clause}, {promise!r}) has no row"
        for r in answering:
            assert r["status"] in {"PASS", "FAIL", "SKIP"}, r
            if r["status"] == "SKIP":
                assert r.get("reason", "").strip(), (
                    f"{ledger_id}: rule {r['rule']} SKIPs with no reason"
                )


def test_the_vision_is_now_scanned_not_only_the_contracts():
    """CVG-059 and CVG-061 both said the same thing: the vision went unread.

    Rules 2b and 6b must both name the vision file, on a target that has one.
    """
    _, report = run_kit(GOOD)
    rules = by_rule(report)
    assert "VISION.md" in rules["2b"]["detail"], rules["2b"]
    scanned = {f["file"] for f in rules["6b"]["files"]}
    assert any("VISION.md" in f for f in scanned), scanned


def test_rule_12c_catches_a_kit_file_that_exists_but_says_nothing():
    """CVG-064: presence was all that was checked.

    sample-bad has no participant kit at all, so its 12c failure only proves
    the missing-file path. This builds a target where the four files EXIST and
    are empty of what clause 12 asks for -- 12a passes, 12c must not.
    """
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        (root / "contracts").mkdir()
        (root / "docs").mkdir()
        (root / ".githooks").mkdir()
        (root / "AGENTS.md").write_text("# Agents\n\nBe nice to the codebase.\n")
        (root / "PINS.md").write_text("# Pins\n\nNothing pinned.\n")
        (root / "docs" / "CONTRACTS-README.md").write_text("# Contracts\n\nThey exist.\n")
        (root / ".githooks" / "pre-push").write_text("#!/bin/sh\nexit 0\n")
        _, report = run_kit(root)
        rules = by_rule(report)
        assert rules["12a"]["status"] == "PASS", rules["12a"]
        assert rules["12c"]["status"] == "FAIL", rules["12c"]
        assert "says nothing about" in rules["12c"]["detail"], rules["12c"]


def test_a_changelog_entry_is_not_failed_for_citing_its_evidence_in_prose():
    """CVG-063 asked for entry content to be inspected. Measured, a literal
    evidence test fails this repository's only entry, which does carry its
    evidence -- in prose. So 7d SKIPs with that measurement rather than
    manufacturing a failure, and 7b still checks the mechanical half."""
    _, report = run_kit(REPO)
    rules = by_rule(report)
    assert rules["7d"]["status"] == "SKIP", rules["7d"]
    assert "1 of 1" in rules["7d"]["reason"], rules["7d"]
    assert rules["7b"]["status"] == "PASS", rules["7b"]


def test_a_progress_word_in_prose_is_not_read_as_a_status():
    """documents.v1 clause 6 is itself the sentence naming "kept / broken /
    in-progress". Rule 6b matches status position only, so this repository --
    which contains that very sentence -- must stay green."""
    _, report = run_kit(REPO)
    assert by_rule(report)["6b"]["status"] == "PASS", by_rule(report)["6b"]


def test_a_changelog_entry_naming_a_version_is_not_a_second_status():
    """This repository's vision changelog carries "- **2026-09-02 - v1
    (DRAFT).**" A status stamp outside the H1 is what clause 6 forbids, but a
    changelog entry recording which version it described is history, not a
    second source of truth for what the document is now. Rule 6b does not
    reach into the changelog, and rule 6 reads contracts. Neither fabricates
    that finding."""
    _, report = run_kit(REPO)
    rules = by_rule(report)
    assert rules["6"]["status"] == "PASS", rules["6"]
    assert rules["6b"]["status"] == "PASS", rules["6b"]
    vision = (REPO / "docs" / "VISION.md").read_text(encoding="utf-8")
    assert "(DRAFT)" in vision.split("## Changelog", 1)[1], (
        "the case this test guards is gone; re-check whether 6b should widen"
    )


# --------------------------------------------------------------------------- #
# Dependency-free runner                                                       #
# --------------------------------------------------------------------------- #
def _main():
    tests = sorted(k for k, v in globals().items()
                   if k.startswith("test_") and callable(v))
    failures = 0
    for name in tests:
        try:
            globals()[name]()
        except AssertionError as e:
            failures += 1
            print(f"FAIL {name}: {e}")
        except Exception as e:  # noqa: BLE001
            failures += 1
            print(f"ERROR {name}: {type(e).__name__}: {e}")
        else:
            print(f"PASS {name}")
    total = len(tests)
    print(f"\n{total - failures}/{total} passed")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(_main())
