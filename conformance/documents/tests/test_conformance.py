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
EXPECTED_SKIPS = {"1", "5b", "7c", "9b", "10b"}

# documents.v1 Core clauses. Every one must be answered by at least one row.
CORE_CLAUSES = set(range(1, 14))


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
    assert failed == {"2", "3", "4", "5a", "6", "7a", "7b", "8", "9a",
                      "10a", "11", "12a", "12b", "13"}, failed


def test_bad_failures_carry_readable_detail():
    _, report = run_kit(BAD)
    rules = by_rule(report)
    assert "line 3" in rules["3"]["detail"]
    assert "missing section" in rules["4"]["detail"]
    assert "outside 50" in rules["2"]["detail"]
    assert "outside the H1" in rules["6"]["detail"]
    assert "bold" in rules["5a"]["detail"]
    assert "plan" in rules["7a"]["detail"]
    assert "Changelog" in rules["7b"]["detail"]
    assert "missing part" in rules["8"]["detail"]
    assert "names no contract" in rules["9a"]["detail"]
    assert "CONFORMS" in rules["10a"]["detail"]
    assert "among the teeth" in rules["11"]["detail"]
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
        for rule in ("2", "3", "4", "5a", "6"):
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
    assert by_rule(report)["13"]["status"] == "PASS", by_rule(report)["13"]


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
    assert by_rule(report)["11"]["status"] == "PASS", by_rule(report)["11"]


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
