"""Self-test for the composition.v1 conformance kit.

The kit is only as trustworthy as its own demonstration: it must go GREEN
against a repository that conforms (fixtures/sample-good) and RED — with named
rule failures — against one that does not (fixtures/sample-bad).

The load-bearing test here is `test_every_rule_has_a_negative_fixture`: a rule
nobody can make fail is a rule that proves nothing. Rules that cannot be judged
from files at all are SKIPped with a reason, and the SKIP set is pinned so a
rule cannot quietly drift into SKIP to avoid a failure.

Runnable two ways (the assertions are identical):
  * with pytest:  uv run --with pytest pytest conformance/composition/tests/ -q
  * no deps:      uv run conformance/composition/tests/test_conformance.py

The kit parses YAML, so it is always invoked through ``uv run`` (which
provisions its declared pyyaml dependency).
"""

import json
import re
import shutil
import subprocess
from pathlib import Path

KIT = Path(__file__).resolve().parent.parent  # conformance/composition/
RUN = KIT / "run.py"
REPO = KIT.parent.parent  # the repository root this kit ships in
GOOD = KIT / "fixtures" / "sample-good"
BAD = KIT / "fixtures" / "sample-bad"

# Declared in run.py as un-judgeable from files. Pinned here so a rule cannot
# be moved into SKIP to dodge a failure without this test going red.
EXPECTED_SKIPS = {"3b", "6b"}


def _uv() -> str:
    uv = shutil.which("uv")
    if not uv:
        raise RuntimeError(
            "uv is required to run the composition kit (it provisions pyyaml)."
        )
    return uv


def run_kit(target):
    """Invoke the kit on a target repo root; return (exit_code, parsed_report)."""
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
    assert failed == {"1a", "1b", "2a", "2b", "3a", "4", "5", "6a", "7a", "7b"}, failed


def test_bad_failures_carry_readable_detail():
    _, report = run_kit(BAD)
    rules = by_rule(report)
    assert "context/awareness.md" in rules["1a"]["detail"]
    assert "anchors" in rules["1b"]["detail"].lower()
    assert "foundation:" in rules["2a"]["detail"]
    assert "stray-step.yaml" in rules["2b"]["detail"]
    assert "rulebook" in rules["3a"]["detail"]
    assert "host requirement" in rules["4"]["detail"].lower()
    assert "--app" in rules["5"]["detail"]
    assert "bundle.md" in rules["6a"]["detail"]
    assert "candidate" in rules["7a"]["detail"].lower()
    assert "FROZEN" in rules["7b"]["detail"]


# --------------------------------------------------------------------------- #
# THE load-bearing test: no rule proves nothing                               #
# --------------------------------------------------------------------------- #
def test_every_rule_has_a_negative_fixture():
    """Every rule the kit emits must either FAIL on sample-bad, or be an
    explicitly declared SKIP with a reason. There is no third option — a rule
    that can only ever PASS is decoration."""
    _, good = run_kit(GOOD)
    _, bad = run_kit(BAD)
    good_rules = by_rule(good)
    bad_rules = by_rule(bad)
    assert set(good_rules) == set(bad_rules), "the two runs emitted different rule sets"

    unproven = []
    for rule, row in good_rules.items():
        if row["status"] == "SKIP":
            continue
        if bad_rules[rule]["status"] != "FAIL":
            unproven.append(rule)
    assert not unproven, (
        f"rules with no negative fixture (they never FAIL on sample-bad): {unproven}"
    )


def test_skips_are_exactly_the_declared_set_and_carry_a_reason():
    """An honest SKIP names why. A rule may not drift into SKIP silently."""
    for fixture in (GOOD, BAD):
        _, report = run_kit(fixture)
        skipped = {r["rule"] for r in report["results"] if r["status"] == "SKIP"}
        assert skipped == EXPECTED_SKIPS, (
            f"{fixture.name}: SKIP set drifted — expected {EXPECTED_SKIPS}, got {skipped}"
        )
        for r in report["results"]:
            if r["status"] == "SKIP":
                assert r.get("reason", "").strip(), f"rule {r['rule']} SKIPs with no reason"


def test_no_rule_is_ever_fabricated():
    """Every emitted status is one of the three honest values."""
    for fixture in (GOOD, BAD, REPO):
        _, report = run_kit(fixture)
        for r in report["results"]:
            assert r["status"] in {"PASS", "FAIL", "SKIP"}, r
            assert r["detail"].strip(), f"rule {r['rule']} reports no detail"


# --------------------------------------------------------------------------- #
# The Core-clause anchor, and what it buys                                    #
# --------------------------------------------------------------------------- #
CONTRACT = REPO / "contracts" / "composition.v1.md"


def core_clause_numbers():
    """Every numbered clause under '## Core (the teeth)' in the contract."""
    body = CONTRACT.read_text(encoding="utf-8").split("## Core (the teeth)")[1]
    body = body.split("\n## ")[0]
    return {int(m.group(1)) for m in re.finditer(r"(?m)^(\d+)\.\s", body)}


def test_every_rule_id_is_a_core_clause_number():
    """A rule id is <clause>[letter], and <clause> is a Core clause that exists.

    This is the anchor the steward ratified on 2026-09-03: a failing rule names
    the clause it breaks. An id pointing at a clause the contract does not have
    would send a reader looking for a promise that is not there.
    """
    clauses = core_clause_numbers()
    _, report = run_kit(GOOD)
    for r in report["results"]:
        m = re.fullmatch(r"(\d+)([a-z])?", r["rule"])
        assert m, f"rule id {r['rule']!r} is not <clause>[letter]"
        assert int(m.group(1)) in clauses, (
            f"rule {r['rule']} names Core clause {m.group(1)}, which "
            f"{CONTRACT.name} does not have (it has {sorted(clauses)})"
        )
        assert r["clause"] == int(m.group(1)), (
            f"rule {r['rule']} reports clause {r['clause']}, which its id contradicts"
        )


def test_every_core_clause_has_a_row():
    """Every Core clause of the contract is judged by at least one rule.

    This is what the Core-clause anchor buys and the bullet anchor could not:
    under the bullets there was no row to be missing, so a clause could go
    unchecked invisibly. A clause added to the contract later fails here.
    """
    _, report = run_kit(GOOD)
    covered = {r["clause"] for r in report["results"]}
    missing = sorted(core_clause_numbers() - covered)
    assert not missing, (
        f"Core clause(s) {missing} of {CONTRACT.name} have no rule row — "
        f"the kit judges {sorted(covered)}"
    )


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
# Dependency-free runner (so the self-test works without pytest installed)     #
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
        except Exception as e:  # noqa: BLE001 - surface any error loudly
            failures += 1
            print(f"ERROR {name}: {type(e).__name__}: {e}")
        else:
            print(f"PASS {name}")
    total = len(tests)
    print(f"\n{total - failures}/{total} passed")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(_main())
