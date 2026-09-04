"""Self-test for the surface.v1 conformance kit.

The kit must go GREEN against a page set whose promises are kept the way the
shipped app keeps them — links to real routes, forms that post, a count that
agrees with the list (fixtures/sample-good) — and RED, with named rule
failures, against one where the same promises are markup with nothing behind
them (fixtures/sample-bad).

The load-bearing test is `test_every_rule_has_a_negative_fixture`: a rule
nobody can make fail is a rule that proves nothing. The one row that genuinely
needs a browser SKIPs with a reason naming the work that closes it, and the
SKIP set is pinned so a rule cannot quietly drift into SKIP to dodge a failure.

Runnable two ways (the assertions are identical):
  * with pytest:  uv run --with pytest pytest conformance/surface/tests/ -q
  * no deps:      uv run conformance/surface/tests/test_conformance.py
"""

import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

KIT = Path(__file__).resolve().parent.parent  # conformance/surface/
RUN = KIT / "run.py"
CONTRACT = KIT.parent.parent / "contracts" / "surface.v1.md"
GOOD = KIT / "fixtures" / "sample-good"
BAD = KIT / "fixtures" / "sample-bad"

#: The one row a static read of served pages cannot settle.
EXPECTED_SKIPS = {"10"}

#: Every rule the kit emits, and the failure sample-bad is built to produce.
EXPECTED_FAILURES = {"1a", "1b", "2", "3a", "3b", "4", "5", "6", "7",
                     "8a", "8b", "8c", "9a", "9b"}

#: The stale reason converge-e59 was filed about. The app ships in
#: src/amplifier_converge/, so no SKIP may say this ever again.
STALE_REASON = "not built yet"


def _uv() -> str:
    uv = shutil.which("uv")
    if not uv:
        raise RuntimeError("uv is required to run the surface kit.")
    return uv


def run_kit(target, *args):
    proc = subprocess.run(
        [_uv(), "run", str(RUN), str(target), "--json-only", *args],
        capture_output=True, text=True, timeout=300, check=False,
    )
    assert proc.stdout.strip(), f"kit produced no JSON report; stderr:\n{proc.stderr}"
    return proc.returncode, json.loads(proc.stdout)


def by_rule(report):
    return {r["rule"]: r for r in report["results"]}


def _page_set(pages, **manifest):
    """A throwaway page set: {route: html}, written the way render.py writes one."""
    directory = Path(tempfile.mkdtemp(prefix="surface-kit-test-"))
    entries = []
    for index, (route, html) in enumerate(pages.items()):
        name = f"page{index}.html"
        (directory / name).write_text(html, encoding="utf-8")
        entries.append({"route": route, "file": name})
    manifest = {"pages": entries, **manifest}
    (directory / "pages.json").write_text(json.dumps(manifest), encoding="utf-8")
    return directory


# --------------------------------------------------------------------------- #
# GREEN on a conforming page set                                              #
# --------------------------------------------------------------------------- #
def test_good_pages_conform():
    code, report = run_kit(GOOD)
    assert report["verdict"] == "PASS", report
    assert code == 0
    failed = {r["rule"] for r in report["results"] if r["status"] == "FAIL"}
    assert failed == set(), f"sample-good should fail nothing, got {failed}"


def test_good_pages_are_read_as_a_page_set():
    """The kit judges the app across the pages it serves, not one file."""
    _, report = run_kit(GOOD)
    routes = [p["route"] for p in report["pages"]]
    assert routes == ["/", "/direction", "/direction/half.v1", "/operation",
                      "/direction/half.v2-candidate"], routes
    assert report["target_kind"] == "rendered pages", report["target_kind"]


# --------------------------------------------------------------------------- #
# RED on a non-conforming page set, with NAMED rule failures                  #
# --------------------------------------------------------------------------- #
def test_bad_pages_fail_named_rules():
    code, report = run_kit(BAD)
    assert report["verdict"] == "FAIL", report
    assert code == 1
    failed = {r["rule"] for r in report["results"] if r["status"] == "FAIL"}
    assert failed == EXPECTED_FAILURES, failed


def test_bad_failures_carry_readable_detail():
    _, report = run_kit(BAD)
    rules = by_rule(report)
    assert "/nowhere" in rules["1a"]["detail"], rules["1a"]
    assert "card(s) are on the list" in rules["1b"]["detail"], rules["1b"]
    assert "not the ratification record" in rules["2"]["detail"], rules["2"]
    assert "/do/close-lane" in rules["3a"]["detail"], rules["3a"]
    assert "never maps to an operation" in rules["3b"]["detail"], rules["3b"]
    assert "keeps no data of its own" in rules["4"]["detail"], rules["4"]
    assert "what does not change" in rules["5"]["detail"], rules["5"]
    assert "taken away" in rules["6"]["detail"], rules["6"]
    assert "not four" in rules["7"]["detail"], rules["7"]
    assert "held" in rules["8a"]["detail"], rules["8a"]
    assert "Kept" in rules["8b"]["detail"], rules["8b"]
    assert "ledger" in rules["8c"]["detail"], rules["8c"]
    assert "no way to fill" in rules["9a"]["detail"], rules["9a"]
    assert "Stop this lane" in json.dumps(rules["9b"]), rules["9b"]


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


def test_the_three_clause_halves_are_covered_by_a_rule_each():
    """converge-fmz named three halves of surface.v1 with no check at all.

    Core 9 is rules 9a and 9b, Core 8's first half is rules 8a and 8b, and
    Core 8's second half is rule 8c — which now reads the app's own rendered
    words because the kit's target is the app. (The ids moved on 2026-09-03
    when the kit was renumbered to the contract's Core clauses; the rows and
    what they assert did not.)
    """
    _, report = run_kit(GOOD)
    rules = by_rule(report)
    for rule in ("9b", "8a", "8b", "8c"):
        assert rule in rules, f"rule {rule} is not emitted at all"
        assert rules[rule]["status"] == "PASS", rules[rule]
    assert rules["9b"]["clause"] == 9, rules["9b"]
    assert rules["8a"]["clause"] == 8, rules["8a"]
    assert len(rules["9b"]["in_view"]) == 8, rules["9b"]["in_view"]


def test_skips_are_exactly_the_declared_set_and_name_the_work():
    """An honest SKIP names why — and names the work that would close it."""
    for fixture in (GOOD, BAD):
        _, report = run_kit(fixture)
        skipped = {r["rule"] for r in report["results"] if r["status"] == "SKIP"}
        assert skipped == EXPECTED_SKIPS, (
            f"{fixture.name}: SKIP set drifted — expected {EXPECTED_SKIPS}, got {skipped}"
        )
        for r in report["results"]:
            if r["status"] == "SKIP":
                assert "converge-" in r["reason"], (
                    f"rule {r['rule']} SKIPs without naming the work that closes it: {r}"
                )


def test_no_skip_still_claims_the_app_is_unbuilt():
    """The reason converge-e59 was filed. The app ships; a SKIP may not say it does not."""
    for fixture in (GOOD, BAD):
        _, report = run_kit(fixture)
        for r in report["results"]:
            assert STALE_REASON not in json.dumps(r), (
                f"rule {r['rule']} still says the app is not built: {r}"
            )


def test_no_rule_is_ever_fabricated():
    for fixture in (GOOD, BAD):
        _, report = run_kit(fixture)
        for r in report["results"]:
            assert r["status"] in {"PASS", "FAIL", "SKIP"}, r
            assert r["detail"].strip(), f"rule {r['rule']} reports no detail"


def test_the_kit_says_it_never_launches_a_browser():
    """The report states its own scope, so a PASS is never read as a render
    check it did not perform."""
    _, report = run_kit(GOOD)
    assert "no browser" in report["check"].lower(), report["check"]


# --------------------------------------------------------------------------- #
# The app's shape, not the mockup's                                           #
# --------------------------------------------------------------------------- #
def test_a_page_with_no_script_can_still_pass():
    """converge-e59: the app carries no script at all, on purpose. A kit that
    needed handlers would fail it for keeping the promise a different way."""
    for page in GOOD.glob("*.html"):
        assert "<script" not in page.read_text(encoding="utf-8").lower(), page.name
    _, report = run_kit(GOOD)
    assert report["verdict"] == "PASS", report


def test_one_page_cannot_prove_places_switch_and_says_so():
    """A single page is not a false FAIL — the kit reports what it cannot see."""
    directory = _page_set({"/": '<!doctype html><html><body><main>'
                                '<a class="place is-on" href="/">Here</a>'
                                "</main></body></html>"})
    _, report = run_kit(directory)
    row = by_rule(report)["1a"]
    assert row["status"] == "SKIP", row
    assert "one page" in row["reason"], row


def test_an_undeclared_post_is_a_fifth_write_until_someone_says_otherwise():
    """"Exactly four" is only checkable if every other POST is declared. The
    app names its own in web/app.py NON_WRITE_POSTS; the kit makes whoever
    runs it repeat the claim."""
    pages = {"/operation": '<!doctype html><html><body><main>'
                           '<form method="post" action="/do/answer-with-a-word"></form>'
                           '<form method="post" action="/do/signal-priority"></form>'
                           '<form method="post" action="/do/drop-feedback"></form>'
                           '<form method="post" action="/do/steer"></form>'
                           '<form method="post" action="/direction/x/mark-read"></form>'
                           "</main></body></html>"}
    undeclared = _page_set(pages)
    _, report = run_kit(undeclared)
    row = by_rule(report)["3a"]
    assert row["status"] == "FAIL", row
    assert "/direction/x/mark-read" in row["detail"], row

    _, report = run_kit(undeclared, "--changes-nothing", "/direction/*/mark-read")
    row = by_rule(report)["3a"]
    assert row["status"] == "PASS", row
    assert "declared to change nothing" in row["detail"], row


def test_the_lock_control_must_agree_with_its_own_conditions_both_ways():
    """Rule 1d is an invariant, not a fixed state: all four green with the
    control still off fails exactly as loudly as the reverse."""
    gate = ("<article><ul class=\"gate\">"
            + "".join('<li><span class="state green">Green</span><span>done</span></li>'
                      for _ in range(4))
            + '</ul><form method="post" action="/do/answer-with-a-word">'
              '<button disabled>Lock it</button></form></article>')
    page = ('<!doctype html><html><body><main><article class="card doc"><p>x</p></article>'
            + gate + "</main></body></html>")
    directory = _page_set({"/direction/x": page})
    _, report = run_kit(directory)
    row = by_rule(report)["7"]
    assert row["status"] == "FAIL", row
    assert "still off" in row["detail"], row


def test_the_kit_can_be_imported_and_handed_one_page():
    """`tests/test_plain_words_on_the_surface.py` holds this kit and asks it for
    the vocabulary rule's verdict on each page the app serves, one page at a
    time (rule 8c since the 2026-09-03 renumbering; rule 5 before it):

        report = kit.run_conformance(target_path)

    That is a real caller in another directory, so the one-argument call has to
    keep working — resolving the target is the kit's job, not its caller's.
    """
    import importlib.util

    spec = importlib.util.spec_from_file_location("surface_kit_under_test", RUN)
    kit = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(kit)

    page = GOOD / "operation.html"
    report = kit.run_conformance(page)
    assert report["target"] == str(page)
    assert by_rule(report)["8c"]["status"] == "PASS", by_rule(report)["8c"]


# --------------------------------------------------------------------------- #
# Three places the scanner must not fabricate a finding                       #
# --------------------------------------------------------------------------- #
def _one_page(html):
    directory = _page_set({"/": html})
    _, report = run_kit(directory)
    return by_rule(report)["8c"]


def test_a_project_name_is_not_read_as_jargon():
    """`amplifier-bundle-converge` in a header chip is a proper noun, not the
    word "bundle" used as jargon."""
    row = _one_page('<!doctype html><html><body><span class="project">'
                    "amplifier-bundle-converge</span></body></html>")
    assert row["status"] == "PASS", row


def test_a_sentence_final_term_is_still_reported():
    """A trailing full stop is a sentence ending, not a path separator — "the
    ledger." is jargon, plainly, and must not slip through the exemption."""
    row = _one_page('<!doctype html><html><body><p class="why">'
                    "Four rows were filed against the ledger.</p></body></html>")
    assert row["status"] == "FAIL", row
    assert "ledger" in row["detail"], row


def test_a_displayed_document_is_out_of_scope_for_rule_5():
    """A rendered project document is that document's prose. Its vocabulary is
    documents.v1's business, not the app's."""
    row = _one_page('<!doctype html><html><body><article class="doc">'
                    "<p>The bundle installs on a lean host and the recipe reconciles "
                    "the ledger.</p></article></body></html>")
    assert row["status"] == "PASS", row


def test_words_quoted_from_the_project_are_out_of_scope_for_rule_5():
    """The app marks borrowed words as borrowed. A lane that called itself
    "the ledger reconcile lane" is the lane's wording, not the app's."""
    row = _one_page('<!doctype html><html><body><p class="why">The lane says: '
                    '<span class="doc quote">reconcile the ledger, then stop</span>'
                    "</p></body></html>")
    assert row["status"] == "PASS", row


def test_technical_detail_behind_a_fold_is_out_of_scope_for_the_vocabulary_rule():
    """That is precisely where the contract says technical detail belongs."""
    row = _one_page("<!doctype html><html><body><details><summary>Details</summary>"
                    "<p>branch lane/w5, worktree /tmp/lanes/w5, YAML at .converge/</p>"
                    "</details></body></html>")
    assert row["status"] == "PASS", row


# --------------------------------------------------------------------------- #
# The Core-clause anchor, and what it buys                                    #
# --------------------------------------------------------------------------- #
def core_clause_numbers():
    """Every numbered clause under '## Core (the teeth)' in the contract."""
    body = CONTRACT.read_text(encoding="utf-8").split("## Core (the teeth)")[1]
    body = body.split("\n## ")[0]
    return {int(m.group(1)) for m in re.finditer(r"(?m)^(\d+)\.\s", body)}


def test_every_rule_id_is_a_core_clause_number():
    """A rule id is <clause>[letter], and <clause> is a Core clause that exists.

    The anchor the steward ratified on 2026-09-03: a failing rule names the
    clause it breaks. An id pointing at a clause the contract does not have
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
    under the bullets there was no row to be missing, so Core 4 and Core 5 went
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
# The README stays honest about what the kit emits                            #
# --------------------------------------------------------------------------- #
def test_readme_rule_table_covers_every_emitted_rule():
    readme = (KIT / "README.md").read_text(encoding="utf-8")
    _, report = run_kit(GOOD)
    for r in report["results"]:
        assert f"| {r['rule']} " in readme, (
            f"rule {r['rule']} is emitted but has no row in the README rule table"
        )


def test_readme_documents_both_ways_to_point_the_kit_at_the_app():
    readme = (KIT / "README.md").read_text(encoding="utf-8")
    assert "amplifier-converge web" in readme, "the README never says how to run the app"
    assert "render.py" in readme, "the README never says how to write the pages out"


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
