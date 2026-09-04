"""Self-test for the experience-collaboration.v1 conformance kit.

The kit is only as trustworthy as its own demonstration: it must go GREEN
against a body that keeps the seam (``fixtures/sample-good``) and RED — with
named rule failures — against one that does not (``fixtures/sample-bad``). Both
fixtures are a **pair**: a captured app snapshot plus a ``repo/`` half, written
by ``make_fixtures.py`` beside the kit.

The load-bearing test is ``test_every_rule_has_a_negative_fixture``: a rule
nobody can make fail is a rule that proves nothing. The SKIP set is pinned to
the two halves that genuinely need a second party on a live host, so a rule
cannot quietly drift into SKIP to dodge a failure.

Runnable two ways (the assertions are identical):
  * with pytest:  uv run --with pytest pytest conformance/experience-collaboration/tests/ -q
  * no deps:      python3 conformance/experience-collaboration/tests/test_conformance.py
"""

import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

KIT = Path(__file__).resolve().parent.parent      # conformance/experience-collaboration/
RUN = KIT / "run.py"
REPO = KIT.parent.parent                          # the repository root
CONTRACT = REPO / "contracts" / "experience-collaboration.v1.md"
README = KIT / "README.md"
GOOD = KIT / "fixtures" / "sample-good"
BAD = KIT / "fixtures" / "sample-bad"

#: The two halves only a person on a live host can settle: a teammate's reply
#: coming back attributed (4b), and a second person's word never reaching the
#: ratification record (8b). Everything else is provable from what the app
#: declares and what the repository holds.
EXPECTED_SKIPS = {"4b", "8b"}


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
    sys.path.insert(0, str(KIT.parent))                  # appsnapshot / kitreport
    sys.path.insert(0, str(KIT.parent / "experience"))   # repotarget
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
    assert not failed, "sample-good should keep the seam: " + json.dumps(failed, indent=2)
    assert report["verdict"] == "PASS"
    assert code == 0


def test_sample_bad_fails():
    code, report = run_kit(BAD)
    assert report["verdict"] == "FAIL"
    assert code == 1


def test_every_rule_has_a_negative_fixture():
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


def test_a_skip_names_the_second_party_it_needs():
    """These two SKIP because a machine has no second person and no live host —
    not because judging them would be awkward. Each reason says so, and points
    at the half that IS checkable."""
    _, report = run_kit(GOOD)
    rows = by_rule(report)
    assert "live host" in rows["4b"]["reason"] and "rule 4a" in rows["4b"]["reason"]
    assert "two people" in rows["8b"]["reason"] and "rule 8a" in rows["8b"]["reason"]


def test_no_skip_still_claims_the_app_is_unbuilt():
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
    _, report = run_kit(GOOD)
    judged = {r["clause"] for r in report["results"]}
    missing = [n for n in core_clause_numbers() if n not in judged]
    assert not missing, f"Core clauses with no rule row: {missing}"


def test_rule_ids_match_the_readme_table():
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
REPO_READING_RULES = {"1", "5a", "7", "9"}


def test_a_missing_repository_half_skips_rather_than_guesses():
    """A snapshot with no `repo/` must not be judged against whatever checkout
    the kit happens to sit in — that would report another repository's write
    path as this target's verdict, and nothing would look wrong."""
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
            assert "repo/" in rows[rid]["reason"]


def test_a_route_only_rule_says_it_read_the_route_table_alone():
    """Rule 2 can still be judged without a repository half — but it must say
    that it read the route table alone, not imply it read the source too."""
    with tempfile.TemporaryDirectory() as tmp:
        half = Path(tmp) / "app-only"
        half.mkdir()
        for f in GOOD.iterdir():
            if f.is_file():
                shutil.copy2(f, half / f.name)
        _, report = run_kit(half)
        row = by_rule(report)["2"]
        assert row["status"] == "PASS"
        assert "route table alone" in row["detail"], row["detail"]


# --------------------------------------------------------------------------- #
# the lessons this kit paid for                                                #
# --------------------------------------------------------------------------- #
def test_a_word_in_a_comment_is_not_a_channel():
    """Measured against the live app: `app/serve.py` explains its auth gate with
    "There is deliberately no exemption for a loopback peer." Read as bare
    words, `peer` in that sentence made rule 2 report a manager-to-manager
    channel in a body that has none — a fabricated finding. A channel is CODE."""
    kit = kit_module()
    prose = ('def gate(request):\n'
             '    """There is deliberately no exemption for a loopback peer."""\n'
             '    # a peer on the loopback is a request like any other\n'
             '    return check(request)\n')
    code = kit.strip_python_prose(prose)
    assert not any(p.search(code) for _n, p in kit.PEER_MARKERS), \
        f"prose still read as a channel: {code!r}"
    real = "PEER_ENDPOINT = other\ndef send(): peer_channel(PEER_ENDPOINT).send(word)\n"
    assert any(p.search(kit.strip_python_prose(real)) for _n, p in kit.PEER_MARKERS)


def test_reaching_the_host_is_not_reaching_another_manager():
    """Core 4 REQUIRES Converge to reach the repository host; Core 2 forbids it
    reaching another manager session. A rule that banned outbound calls outright
    would make the contract self-contradictory and fail a conforming body."""
    kit = kit_module()
    host_call = "def ask(): return gh_pr_comment(number, question)\n"
    assert not any(p.search(kit.strip_python_prose(host_call))
                   for _n, p in kit.PEER_MARKERS)
    assert not kit.PEER_ROUTE.search("/api/managers/{mid}/pulls/{number}/comments")
    assert kit.PEER_ROUTE.search("/api/managers/{mid}/peers/{other}")


def test_a_relayed_comment_is_not_a_second_surface():
    """Core 10 forbids Converge KEEPING a tracker; Core 4 requires it RELAYING a
    comment to the host. `comment` is deliberately absent from the second-surface
    route set, or the bridge rule 4a asks for would fail rule 10."""
    kit = kit_module()
    assert not kit.SECOND_SURFACE_ROUTE.search("/api/managers/{mid}/pulls/{n}/comments")
    for tracker in ("/api/issues", "/api/tickets/{id}", "/api/threads"):
        assert kit.SECOND_SURFACE_ROUTE.search(tracker), tracker


def test_a_drafting_subprocess_is_not_the_manager_session_in_the_hot_path():
    """The live write path starts a fresh headless session for one drafting
    step. That is not the manager session and carries none of its state, so
    Core 7 is kept — but the row names the process rather than staying silent
    about it, because a reader should see what a write starts."""
    _, report = run_kit(GOOD)
    row = by_rule(report)["7"]
    assert row["status"] == "PASS"
    assert "processes_started" in row


def test_a_derived_failure_names_the_rule_it_follows_from():
    """With no mechanism at all (6a), there is nothing for 6b to name. The row
    says so and cites 6a — a derived failure, not a second independent one."""
    _, report = run_kit(BAD)
    assert "rule 6a" in by_rule(report)["6b"]["detail"]


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
