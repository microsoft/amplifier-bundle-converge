"""Self-test for the experience-operation.v1 conformance kit.

The kit is only as trustworthy as its own demonstration: it must go GREEN
against a body that keeps the promises (``fixtures/sample-good``) and RED — with
named rule failures — against one that does not (``fixtures/sample-bad``). Both
fixtures are **captured app snapshots**, the same shape ``run.py --capture``
writes, so they are judged through exactly the code path a live app is.

The load-bearing test is ``test_every_rule_has_a_negative_fixture``: a rule
nobody can make fail is a rule that proves nothing. The SKIP set is pinned, so a
rule cannot quietly drift into SKIP to dodge a failure.

Runnable two ways (the assertions are identical):
  * with pytest:  uv run --with pytest pytest conformance/experience-operation/tests/ -q
  * no deps:      python3 conformance/experience-operation/tests/test_conformance.py

The kit declares no dependencies, so the plain interpreter is enough.
"""

import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

KIT = Path(__file__).resolve().parent.parent          # conformance/experience-operation/
RUN = KIT / "run.py"
REPO = KIT.parent.parent                              # the repository root
CONTRACT = REPO / "contracts" / "experience-operation.v1.md"
README = KIT / "README.md"
GOOD = KIT / "fixtures" / "sample-good"
BAD = KIT / "fixtures" / "sample-bad"

#: Rows this kit declares un-judgeable from a served snapshot. Pinned here so a
#: rule cannot be moved into SKIP to dodge a failure without this test going red.
EXPECTED_SKIPS = set()


def run_kit(target):
    proc = subprocess.run(
        [sys.executable, str(RUN), str(target), "--json-only"],
        capture_output=True, text=True, timeout=300, check=False,
    )
    assert proc.stdout.strip(), f"kit produced no JSON report; stderr:\n{proc.stderr}"
    return proc.returncode, json.loads(proc.stdout)


def kit_module():
    """The kit itself, loaded from its own path under a unique module name.

    `import run` would collide: all three experience kits ship `run.py`, and the
    first one imported wins `sys.modules["run"]` for the whole pytest session —
    measured, and it made this file assert against a sibling kit's constants.
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


def run_kit_on_a_changed_good(change):
    """`sample-good`, with its operation payload changed, judged as a target.

    The fixture on disk is written by `../../experience-fixtures/make_fixtures.py`
    and is deliberately NOT hand-edited here: an edit would be erased the next
    time that script runs, and this kit's own proof would quietly stop proving
    anything. So the change is made to a copy, at the moment it is needed, and
    goes through exactly the code path a live app does.
    """
    tmp = tempfile.mkdtemp(prefix="experience-operation-kit-")
    try:
        target = Path(tmp) / "snapshot"
        shutil.copytree(GOOD, target)
        payload_path = target / "api__managers__m1__operation.json"
        payload = json.loads(payload_path.read_text(encoding="utf-8"))
        change(payload)
        payload_path.write_text(json.dumps(payload, indent=1), encoding="utf-8")
        return run_kit(target)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def a_reported_lane(lane_id, word="Done", evidence="2 commits"):
    """One entry of the `reported` list.

    Both `outcome` and `outcomeLabel` carry the word: which of the two the kit
    reads is decided by what the body's own client hands to `laneCard`, and this
    file is testing the RULE, not the fixture's stub client.
    """
    return {"id": lane_id, "title": f"the {lane_id} thing", "worker": lane_id,
            "wave": "Wave 1", "age": "3h", "evidence": evidence,
            "outcome": word, "outcomeLabel": word}


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
# the lessons this kit paid for                                                #
# --------------------------------------------------------------------------- #
def test_a_function_is_read_from_its_definition_not_its_import():
    """`script.find("fillLanes")` lands on `import { … fillLanes … }` at the top of
    main.js and returns whatever brace follows. Measured: that read reported the
    fill control reaching no write, when `fillLanes` calls `api.steer`."""
    kit = kit_module()
    script = ("import { openSteer, fillLanes } from './actions.js';\n"
              "const other = { a: 1 };\n"
              "export function fillLanes() { api.steer(mid, { fill: true }); }")
    body = kit.function_body(script, "fillLanes")
    assert "api.steer" in body
    assert kit.reaches_a_write(body, {"steer"})


def test_a_word_in_a_message_is_not_a_write():
    kit = kit_module()
    assert not kit.reaches_a_write("{ toast('the steer landed'); }", {"steer"})


def test_a_wave_title_that_repeats_its_lane_names_is_not_a_reason():
    """Every wave in the live app is titled with its own lane names. A reason says
    what a batch is FOR; a list of its members does not."""
    _, report = run_kit(BAD)
    row = by_rule(report)["2b"]
    assert row["status"] == "FAIL" and "only their lane names" in row["detail"]


def test_the_lane_vocabulary_is_the_contracts_not_the_kits():
    """Working · Quiet · Silent — may have died. A work word shown for a lane
    (`Done`) is reported, not quietly accepted."""
    kit = kit_module()
    assert kit.LANE_WORDS == ("working", "quiet", "silent")


def test_the_work_vocabulary_is_the_contracts_not_the_kits():
    """Done · Stuck — `experience.v1` Core 6's WORK words, which are what a lane
    that has already come back is read in."""
    kit = kit_module()
    assert kit.WORK_WORDS == ("done", "stuck")


def test_a_well_formed_reported_lane_is_accepted():
    """The control for the three faults below: adding a sound `reported` list to
    a passing body must not make anything go red, or the faults prove nothing."""
    code, report = run_kit_on_a_changed_good(
        lambda p: p.update({"reported": [a_reported_lane("w1-done"),
                                         a_reported_lane("w1-stopped", word="Stuck")]}))
    row = by_rule(report)["8"]
    assert row["status"] == "PASS", f"a sound reported list was faulted: {row['detail']}"
    assert row["reported_words_shown"], "the rule did not read the reported list at all"
    assert code == 0


def test_a_reported_lane_is_judged_like_a_working_one():
    """converge-0w2, in its own words.

    "GIVEN an operation payload whose `reported` list carries a lane with a word
    outside the work vocabulary, or no evidence, or an id that also appears in
    `lanes` WHEN the kit runs THEN it reports FAIL naming that lane."

    Each fault is introduced alone, into a body that otherwise keeps every
    promise, so a red row can only be the fault under test. Each is asserted to
    name the offending LANE — the reader's next question after "something is
    wrong" is always "which one?".
    """
    # 1. a word outside the work vocabulary. `Working` is a real plain word, and
    #    still wrong here: it is the LANE vocabulary, and a lane that has come
    #    back is not answering the lane question at all.
    _, report = run_kit_on_a_changed_good(
        lambda p: p.update({"reported": [a_reported_lane("w1-astray", word="Working")]}))
    row = by_rule(report)["8"]
    assert row["status"] == "FAIL", "a reported lane read in a lane word was accepted"
    assert "w1-astray" in row["detail"], f"the failure did not name the lane: {row['detail']}"
    assert "'Working'" in row["detail"], f"the failure did not quote the word: {row['detail']}"

    # 2. no evidence to open. Core 8: "Underneath sits what the lane actually
    #    produced, so a claim can be inspected rather than believed."
    _, report = run_kit_on_a_changed_good(
        lambda p: p.update({"reported": [a_reported_lane("w1-unproven", evidence="")]}))
    row = by_rule(report)["8"]
    assert row["status"] == "FAIL", "a reported lane with nothing to open was accepted"
    assert "w1-unproven" in row["detail"], f"the failure did not name the lane: {row['detail']}"

    # 3. an id in both lists. Each list is read in a different vocabulary, so a
    #    lane in both is told in two states at once — and is one rename away
    #    from being judged by neither.
    def in_both(payload):
        first = (payload.get("lanes") or [{}])[0].get("id")
        assert first, "sample-good stopped carrying a lane at work"
        payload["reported"] = [a_reported_lane(first)]

    _, report = run_kit_on_a_changed_good(in_both)
    row = by_rule(report)["8"]
    assert row["status"] == "FAIL", "a lane in both lists was accepted"
    assert "w1-kit" in row["detail"], f"the failure did not name the lane: {row['detail']}"
    assert row["in_both_lists"] == ["w1-kit"], row


def test_a_list_nobody_judges_is_a_place_to_hide_a_lane():
    """The regression this rule exists to stop.

    Before converge-0w2 the rule read `op["lanes"]` and nothing else, so moving
    an offending lane into `reported` turned a FAIL into a PASS. Measured
    against the live app on 2026-09-04: 75 lanes sat in `reported`, judged by
    nothing at all.
    """
    _, report = run_kit_on_a_changed_good(
        lambda p: p.update({"reported": [a_reported_lane("w1-hidden", word="RESOLVED",
                                                         evidence="")]}))
    row = by_rule(report)["8"]
    assert row["status"] == "FAIL", (
        "a lane carrying the machine's own word and no evidence passed unseen because it "
        "sat in the list the rule did not read")
    assert "w1-hidden" in row["detail"]


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
