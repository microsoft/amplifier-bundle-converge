"""Self-test for the experience.v1 conformance kit.

The kit is only as trustworthy as its own demonstration: it must go GREEN
against a body that keeps the promises (``fixtures/sample-good``) and RED — with
named rule failures — against one that does not (``fixtures/sample-bad``). Both
fixtures are **captured app snapshots with a repository half**, written by
``make_fixtures.py`` beside the kit, so a fixture is judged through exactly the
code path a live app is.

The load-bearing test is ``test_every_rule_has_a_negative_fixture``: a rule
nobody can make fail is a rule that proves nothing. The SKIP set is pinned to
Core 10 and Core 11 — the two clauses about how a review is *conducted* — so a
rule cannot quietly drift into SKIP to dodge a failure.

Runnable two ways (the assertions are identical):
  * with pytest:  uv run --with pytest pytest conformance/experience/tests/ -q
  * no deps:      python3 conformance/experience/tests/test_conformance.py

The kit declares no dependencies, so the plain interpreter is enough.
"""

import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

KIT = Path(__file__).resolve().parent.parent          # conformance/experience/
RUN = KIT / "run.py"
REPO = KIT.parent.parent                              # the repository root
CONTRACT = REPO / "contracts" / "experience.v1.md"
README = KIT / "README.md"
GOOD = KIT / "fixtures" / "sample-good"
BAD = KIT / "fixtures" / "sample-bad"

#: Rows this kit declares un-judgeable. Core 10 and Core 11 are promises about
#: how a review is CONDUCTED — "is the behavior satisfied?" rather than "does it
#: look the same?", and whether a shape quietly removed a state. Neither leaves
#: an artifact. Pinned here so a rule cannot be moved into SKIP to dodge a
#: failure without this test going red.
EXPECTED_SKIPS = {"10", "11"}


def run_kit(target):
    proc = subprocess.run(
        [sys.executable, str(RUN), str(target), "--json-only"],
        capture_output=True, text=True, timeout=300, check=False,
    )
    assert proc.stdout.strip(), f"kit produced no JSON report; stderr:\n{proc.stderr}"
    return proc.returncode, json.loads(proc.stdout)


def kit_module():
    """The kit itself, loaded from its own path under a unique module name.

    `import run` would collide: every experience kit ships `run.py`, and the
    first one imported wins `sys.modules["run"]` for the whole pytest session.
    """
    import importlib.util
    sys.path.insert(0, str(KIT.parent))          # for `appsnapshot` / `kitreport`
    name = f"kit_{KIT.name.replace('-', '_')}"
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, RUN)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    return sys.modules[name]


def by_rule(report):
    return {r["rule"]: r for r in report["results"]}


def readme_rule_ids():
    """The first column of the README's rule table — what `ledger/checks/verify.py`
    resolves a ledger row's `run.py (rule N)` reference against."""
    return set(re.findall(r"(?m)^\|\s*([\w.]+)\s*\|", README.read_text(encoding="utf-8")))


def core_clause_numbers():
    body = CONTRACT.read_text(encoding="utf-8").split("## Core (the teeth)")[1].split("\n## ")[0]
    return [int(n) for n in re.findall(r"(?m)^(\d+)\.\s", body)]


# --------------------------------------------------------------------------- #
# the two fixtures                                                             #
# --------------------------------------------------------------------------- #
def test_sample_good_passes():
    code, report = run_kit(GOOD)
    failed = [r for r in report["results"] if r["status"] == "FAIL"]
    assert not failed, "sample-good should keep every promise: " + json.dumps(failed, indent=2)
    assert report["verdict"] == "PASS"
    assert code == 0


def test_sample_bad_fails():
    code, report = run_kit(BAD)
    assert report["verdict"] == "FAIL"
    assert code == 1


def test_every_rule_has_a_negative_fixture():
    """Every rule the kit emits either FAILs on sample-bad or is a declared SKIP."""
    _, bad = run_kit(BAD)
    unprovable = [rid for rid, r in by_rule(bad).items()
                  if r["status"] != "FAIL" and rid not in EXPECTED_SKIPS]
    assert not unprovable, f"rules nobody can make fail: {unprovable}"


def test_every_skip_says_why():
    for fixture in (GOOD, BAD):
        _, report = run_kit(fixture)
        for r in report["results"]:
            if r["status"] == "SKIP":
                assert r.get("reason"), f"{r['rule']} SKIPs with no reason"


def test_skip_set_is_pinned():
    _, good = run_kit(GOOD)
    _, bad = run_kit(BAD)
    seen = {r["rule"] for rep in (good, bad) for r in rep["results"] if r["status"] == "SKIP"}
    assert seen <= EXPECTED_SKIPS, f"a rule drifted into SKIP: {sorted(seen - EXPECTED_SKIPS)}"


def test_a_skip_names_what_a_machine_cannot_settle():
    """A SKIP is never a soft pass. Each one says what would have to exist."""
    _, report = run_kit(GOOD)
    for r in report["results"]:
        if r["status"] != "SKIP":
            continue
        reason = r["reason"].lower()
        assert len(reason) > 80, f"{r['rule']} SKIPs with a reason too short to be one"
        assert any(w in reason for w in ("person", "two bodies", "artifact", "record")), \
            f"{r['rule']} does not name what a machine cannot settle: {reason}"


def test_no_skip_still_claims_the_app_is_unbuilt():
    """The companion app ships in `app/`. A reason that says otherwise is stale."""
    for fixture in (GOOD, BAD):
        _, report = run_kit(fixture)
        for r in report["results"]:
            reason = (r.get("reason") or "").lower()
            assert "not built" not in reason and "unbuilt" not in reason, \
                f"{r['rule']} claims the app is unbuilt: {reason}"


# --------------------------------------------------------------------------- #
# the kit against its contract                                                 #
# --------------------------------------------------------------------------- #
def test_every_core_clause_has_a_row():
    """A clause with no row is invisible — nothing looks wrong when it is missing."""
    _, report = run_kit(GOOD)
    judged = {r["clause"] for r in report["results"]}
    missing = [n for n in core_clause_numbers() if n not in judged]
    assert not missing, f"Core clauses with no rule row: {missing}"


def test_rule_ids_match_the_readme_table():
    """`ledger/checks/verify.py` resolves a ledger row's `(rule N)` against this
    table, and a ref pointing confidently at the wrong rule is worse than one
    that dangles."""
    _, report = run_kit(GOOD)
    emitted = {r["rule"] for r in report["results"]}
    listed = readme_rule_ids()
    assert emitted <= listed, f"rules the README never lists: {sorted(emitted - listed)}"


def test_the_report_shape_is_the_shared_one():
    _, report = run_kit(GOOD)
    for key in ("kit", "contract", "target", "results", "summary", "verdict"):
        assert key in report, f"the report is missing {key}"
    assert set(r["status"] for r in report["results"]) <= {"PASS", "FAIL", "SKIP"}


# --------------------------------------------------------------------------- #
# the two-target model                                                         #
# --------------------------------------------------------------------------- #
REPO_READING_RULES = {"5b", "7", "9", "12", "13", "15"}


def test_a_missing_repository_half_skips_rather_than_guesses():
    """A snapshot with no `repo/` must not be judged against whatever checkout
    the kit happens to sit in. Every repository-reading rule SKIPs, naming the
    missing half — a guess here would report another repository's contracts as
    this target's."""
    with tempfile.TemporaryDirectory() as tmp:
        half = Path(tmp) / "app-only"
        half.mkdir()
        for f in GOOD.iterdir():
            if f.is_file():
                shutil.copy2(f, half / f.name)
        _, report = run_kit(half)
        rows = by_rule(report)
        for rid in REPO_READING_RULES:
            assert rows[rid]["status"] == "SKIP", \
                f"{rid} judged a repository the target never carried: {rows[rid]['detail']}"
            assert "repo/" in rows[rid]["reason"], \
                f"{rid} does not name the missing half: {rows[rid]['reason']}"


def test_the_repository_read_is_named_in_the_report():
    """Which repository was read is a fact a reader needs, not an assumption."""
    _, report = run_kit(GOOD)
    assert report.get("repository_kind") == "snapshot"
    assert report.get("repository", "").endswith("repo")


# --------------------------------------------------------------------------- #
# the lessons this kit paid for                                                #
# --------------------------------------------------------------------------- #
def test_a_sort_comparators_own_parentheses_do_not_hide_the_sort():
    """Measured against the live app: home.js sorts with
    `.sort((a, b) => b.needs - a.needs || …)`. A `\\.sort\\([^)]*needs` probe stops
    at the comparator's OWN closing parenthesis — it never reaches `needs` — and
    reported a correctly-sorted body as unsorted. A fabricated finding."""
    kit = kit_module()
    home = "const s = [...list].sort((a, b) => b.needs - a.needs || 0);"
    hits = [m for m in re.finditer(r"\.sort\(", home)]
    assert any("needs" in home[m.end():m.end() + 160] for m in hits)
    assert not re.search(r"\.sort\([^)]*needs", home), \
        "the narrow probe would have matched, so this test proves nothing"


def test_a_keyword_is_not_a_citation():
    """Rule 12 once linked a route to a clause by searching for the route's own
    word, and every link it produced was fabricated: `keep` matched "keeps a
    teammate on plain tooling a first-class participant", `read` matched
    "something a person can read". The kit now carries hand-written citations
    and re-reads each one."""
    kit = kit_module()
    prose = ("Two stewards both running Converge still meet as Converge · host · "
             "Converge, and that keeps a teammate on plain tooling a first-class "
             "participant, and keeps the seam something a person can read.")
    for token in ("keep", "read"):
        assert re.search(rf"\b{token}", prose, re.I), "the bad match is the premise"
    assert all(not p.search("/api/managers/{mid}/publish")
               for p, _, _, _ in kit.CONTRACT_NAMED_WRITES), \
        "a write no contract names must have no citation"


def test_every_citation_still_reads_true_in_this_repository():
    """A citation nobody re-reads is a citation that rots. Each entry in the
    table must still be findable in the clause it names, in THIS repository."""
    kit = kit_module()
    import repotarget
    repo = repotarget.Repo(REPO, "checkout")
    for _pattern, contract, clause, phrase in kit.CONTRACT_NAMED_WRITES:
        where = kit.verify_citation(repo, contract, clause, phrase)
        assert where, (f"stale citation: {contract} "
                       f"{'Core %s' % clause if clause else 'Reserved'} no longer says "
                       f"{phrase.pattern!r}")


def test_a_details_fold_is_where_a_machine_word_belongs():
    """Core 6 does not ask for silence. A machine word inside a Details fold is
    the clause being KEPT, and reading it as a violation would report the app's
    own good behaviour as a defect."""
    kit = kit_module()
    folded = "<p>Working</p><details><summary>Details</summary><p>RESOLVED</p></details>"
    assert not kit.MACHINE_STATE_RE.search(kit.strip_details_folds(folded))
    exposed = "<p>RESOLVED</p>"
    assert kit.MACHINE_STATE_RE.search(kit.strip_details_folds(exposed))


def test_the_plain_word_and_the_machine_word_differ_only_by_case():
    """`Done` is the plain word and `DONE` is the machine's. The match is
    case-sensitive on purpose: making it insensitive erases the whole clause."""
    kit = kit_module()
    assert kit.MACHINE_STATE_RE.search("phase: DONE")
    assert not kit.MACHINE_STATE_RE.search("phase: Done")


def test_a_payload_is_not_a_surface():
    """Rule 6b reads what the app WRITES DOWN; a word rendered out of a payload
    is rule 6a's to judge. Reading payloads here would report every row twice
    and name the wrong fix."""
    _, report = run_kit(BAD)
    exposed = by_rule(report)["6b"].get("exposed") or {}
    assert not [r for r in exposed if r.startswith("/api/")], \
        f"6b judged an API payload: {sorted(exposed)}"


def test_an_exempt_route_is_exempt_because_a_contract_says_what_it_is():
    """A route is exempt from the five-writes count because a contract names it,
    never because counting it would be inconvenient."""
    kit = kit_module()
    for route in ("/login", "/logout", "/api/tmux/hw/session/keys"):
        why = kit.exempt_write(route)
        assert why and ("app/auth.py" in why or "experience-console.v1" in why), \
            f"{route} is exempt with no contract behind it: {why}"
    assert kit.exempt_write("/api/managers/{mid}/publish") is None


if __name__ == "__main__":
    failures = []
    for name, fn in sorted(list(globals().items())):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"  ok    {name}")
            except AssertionError as exc:
                failures.append(name)
                print(f"  FAIL  {name}: {exc}")
    print(f"\n{len(failures)} failure(s)")
    raise SystemExit(1 if failures else 0)
