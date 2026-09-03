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
import shutil
import subprocess
from pathlib import Path

KIT = Path(__file__).resolve().parent.parent  # conformance/documents/
RUN = KIT / "run.py"
REPO = KIT.parent.parent  # the repository root this kit ships in
GOOD = KIT / "fixtures" / "sample-good"
BAD = KIT / "fixtures" / "sample-bad"

# Declared in run.py as un-judgeable from files. Both fixtures carry a proposal,
# so rule 3 is checkable in both and is NOT in this set.
EXPECTED_SKIPS = {"2c", "4", "7"}


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
    assert failed == {"1a", "1b", "1c", "1d", "1e", "2a", "2b",
                      "3", "5a", "5b", "6"}, failed


def test_bad_failures_carry_readable_detail():
    _, report = run_kit(BAD)
    rules = by_rule(report)
    assert "line 3" in rules["1a"]["detail"]
    assert "missing section" in rules["1b"]["detail"]
    assert "outside 50" in rules["1c"]["detail"]
    assert "outside the H1" in rules["1d"]["detail"]
    assert "bold" in rules["1e"]["detail"]
    assert "plan" in rules["2a"]["detail"]
    assert "Changelog" in rules["2b"]["detail"]
    assert "missing part" in rules["3"]["detail"]
    assert "AGENTS.md" in rules["5a"]["detail"]


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
        assert rules["3"]["status"] == "SKIP", rules["3"]
        assert "no proposal" in rules["3"]["reason"].lower(), rules["3"]
        # Same discipline for the contract rules when there are no contracts.
        for rule in ("1a", "1b", "1c", "1d", "1e"):
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
    assert by_rule(report)["6"]["status"] == "PASS", by_rule(report)["6"]


# --------------------------------------------------------------------------- #
# An illustration of a status is not a status                                 #
# --------------------------------------------------------------------------- #
def test_inline_code_is_not_read_as_a_second_status():
    """documents.v1 clause 6 spells out `(DRAFT)` and `(FROZEN …)` as examples.
    Reading those as a stray status would be a fabricated finding — so this
    repository's own contracts must pass rule 1d."""
    _, report = run_kit(REPO)
    assert by_rule(report)["1d"]["status"] == "PASS", by_rule(report)["1d"]


# --------------------------------------------------------------------------- #
# The rule table in the README stays numbered to the contract                 #
# --------------------------------------------------------------------------- #
def test_readme_rule_table_covers_every_emitted_rule():
    readme = (KIT / "README.md").read_text(encoding="utf-8")
    _, report = run_kit(GOOD)
    for r in report["results"]:
        assert f"| {r['rule']} " in readme, (
            f"rule {r['rule']} is emitted but has no row in the README rule table"
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
