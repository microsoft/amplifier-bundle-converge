"""Self-test for the surface.v1 conformance kit.

The kit must go GREEN against a companion page whose promised interactions are
present and wired (fixtures/sample-good) and RED — with named rule failures —
against one where they are markup with nothing behind them
(fixtures/sample-bad).

The load-bearing test is `test_every_rule_has_a_negative_fixture`: a rule
nobody can make fail is a rule that proves nothing. Rules that need a running
application are SKIPped with the reason, and the SKIP set is pinned so a rule
cannot quietly drift into SKIP to dodge a failure.

Runnable two ways (the assertions are identical):
  * with pytest:  uv run --with pytest pytest conformance/surface/tests/ -q
  * no deps:      uv run conformance/surface/tests/test_conformance.py
"""

import json
import shutil
import subprocess
from pathlib import Path

KIT = Path(__file__).resolve().parent.parent  # conformance/surface/
RUN = KIT / "run.py"
GOOD = KIT / "fixtures" / "sample-good"
BAD = KIT / "fixtures" / "sample-bad"

# Declared in run.py as un-judgeable without a running application.
EXPECTED_SKIPS = {"2", "3b"}
APP_NOT_BUILT = "the app is not built yet (converge-2qh)"


def _uv() -> str:
    uv = shutil.which("uv")
    if not uv:
        raise RuntimeError("uv is required to run the surface kit.")
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
# GREEN on a conforming page                                                  #
# --------------------------------------------------------------------------- #
def test_good_page_conforms():
    code, report = run_kit(GOOD)
    assert report["verdict"] == "PASS", report
    assert code == 0
    failed = {r["rule"] for r in report["results"] if r["status"] == "FAIL"}
    assert failed == set(), f"sample-good should fail nothing, got {failed}"


# --------------------------------------------------------------------------- #
# RED on a non-conforming page, with NAMED rule failures                      #
# --------------------------------------------------------------------------- #
def test_bad_page_fails_named_rules():
    code, report = run_kit(BAD)
    assert report["verdict"] == "FAIL", report
    assert code == 1
    failed = {r["rule"] for r in report["results"] if r["status"] == "FAIL"}
    assert failed == {"1a", "1b", "1c", "1d", "1e", "3a", "4", "5"}, failed


def test_bad_failures_carry_readable_detail():
    _, report = run_kit(BAD)
    rules = by_rule(report)
    assert "promises" in rules["1a"]["detail"], rules["1a"]
    assert "needCount" in rules["1b"]["detail"], rules["1b"]
    assert "gauge" in rules["1c"]["detail"], rules["1c"]
    assert "not four" in rules["1d"]["detail"], rules["1d"]
    assert "<del>" in rules["1e"]["detail"], rules["1e"]
    assert "write path" in rules["3a"]["detail"], rules["3a"]
    assert "filedList" in rules["4"]["detail"], rules["4"]
    assert "ledger" in rules["5"]["detail"], rules["5"]


# --------------------------------------------------------------------------- #
# THE load-bearing test: no rule proves nothing                               #
# --------------------------------------------------------------------------- #
def test_every_rule_has_a_negative_fixture():
    _, good = run_kit(GOOD)
    _, bad = run_kit(BAD)
    good_rules, bad_rules = by_rule(good), by_rule(bad)
    assert set(good_rules) == set(bad_rules), "the two runs emitted different rule sets"

    unproven = [rule for rule, row in good_rules.items()
                if row["status"] != "SKIP" and bad_rules[rule]["status"] != "FAIL"]
    assert not unproven, (
        f"rules with no negative fixture (they never FAIL on sample-bad): {unproven}"
    )


def test_skips_are_exactly_the_declared_set_and_name_the_app():
    """An honest SKIP names why — and here, names the work that would close it."""
    for fixture in (GOOD, BAD):
        _, report = run_kit(fixture)
        skipped = {r["rule"] for r in report["results"] if r["status"] == "SKIP"}
        assert skipped == EXPECTED_SKIPS, (
            f"{fixture.name}: SKIP set drifted — expected {EXPECTED_SKIPS}, got {skipped}"
        )
        for r in report["results"]:
            if r["status"] == "SKIP":
                assert APP_NOT_BUILT in r["reason"], (
                    f"rule {r['rule']} SKIPs without naming the work that closes it: {r}"
                )


def test_no_rule_is_ever_fabricated():
    for fixture in (GOOD, BAD):
        _, report = run_kit(fixture)
        for r in report["results"]:
            assert r["status"] in {"PASS", "FAIL", "SKIP"}, r
            assert r["detail"].strip(), f"rule {r['rule']} reports no detail"


def test_the_kit_says_it_never_launches_a_browser():
    """The report must state its own scope, so a PASS is never read as a
    render check it did not perform."""
    _, report = run_kit(GOOD)
    assert "no browser" in report["check"].lower(), report["check"]


# --------------------------------------------------------------------------- #
# Two places the scanner must not fabricate a finding                         #
# --------------------------------------------------------------------------- #
def test_a_project_name_is_not_read_as_jargon():
    """`amplifier-bundle-converge` in a header chip is a proper noun, not the
    word "bundle" used as jargon."""
    import tempfile
    page = ('<!doctype html><html><body><span class="project">'
            'amplifier-bundle-converge</span></body></html>')
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "index.html"
        p.write_text(page, encoding="utf-8")
        _, report = run_kit(p)
        assert by_rule(report)["5"]["status"] == "PASS", by_rule(report)["5"]


def test_a_sentence_final_term_is_still_reported():
    """A trailing full stop is a sentence ending, not a path separator — "the
    ledger." is jargon, plainly, and must not slip through the proper-noun
    exemption."""
    import tempfile
    page = ('<!doctype html><html><body><p class="what">'
            'Four rows were filed against the ledger.</p></body></html>')
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "index.html"
        p.write_text(page, encoding="utf-8")
        _, report = run_kit(p)
        row = by_rule(report)["5"]
        assert row["status"] == "FAIL", row
        assert "ledger" in row["detail"], row


def test_a_displayed_document_is_out_of_scope_for_rule_5():
    """A rendered project document is that document's prose. Its vocabulary is
    documents.v1's business, not the app's."""
    import tempfile
    page = ('<!doctype html><html><body><article class="doc">'
            '<p>The bundle installs on a lean host and the recipe reconciles '
            'the ledger.</p></article></body></html>')
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "index.html"
        p.write_text(page, encoding="utf-8")
        _, report = run_kit(p)
        assert by_rule(report)["5"]["status"] == "PASS", by_rule(report)["5"]


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
