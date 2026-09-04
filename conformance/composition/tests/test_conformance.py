"""Self-test for the composition.v1 conformance kit.

The kit is only as trustworthy as its own demonstration: it must go GREEN
against a repository that conforms (fixtures/sample-good) and RED — with named
rule failures — against one that does not (fixtures/sample-bad).

The load-bearing test here is `test_every_rule_has_a_negative_fixture`: a rule
nobody can make fail is a rule that proves nothing.

Three rules — 3b, 6b and 6c — are about a RUNNING session rather than files on
disk. 3b and 6b used to SKIP unconditionally. They now stand real sessions up
(see `live.py`) and return PASS/FAIL like every other rule, INCLUDING on
`sample-bad`, so both are proven by a negative fixture rather than exempted
from proof. Those three are the only rules allowed to SKIP at all, and only
when a named capability is missing from the host — `test_only_the_live_rules_may_skip`
pins that, and `test_live_rules_decline_honestly_when_switched_off` exercises
the decline path so the honest-SKIP behaviour is itself tested rather than
merely asserted.

6c is the host half, and it is the one rule a fixture cannot make judge itself:
it asks whether the release of the target ALREADY INSTALLED on this host takes
tools from a neighbour, and no fixture is installed on anybody's host. It
declines on both fixtures for exactly that reason. So it is proven a different
way — `AMPLIFIER_COMPOSITION_KIT_APP_BUNDLES` replaces the host's app list, and
the three tests at the end of this file drive it red, green, and to its
never-blame-a-neighbour decline. A rule nobody can make fail proves nothing,
and that applies to a rule that declines everywhere too.

Runnable two ways (the assertions are identical):
  * with pytest:  uv run --with pytest pytest conformance/composition/tests/ -q
  * no deps:      uv run conformance/composition/tests/test_conformance.py

The kit parses YAML, so it is always invoked through ``uv run`` (which
provisions its declared pyyaml dependency).
"""

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

KIT = Path(__file__).resolve().parent.parent  # conformance/composition/
RUN = KIT / "run.py"
REPO = KIT.parent.parent  # the repository root this kit ships in
GOOD = KIT / "fixtures" / "sample-good"
BAD = KIT / "fixtures" / "sample-bad"

# The only rules that may ever report SKIP: the ones that need a running
# session. Every other rule must reach a verdict from files, always.
LIVE_RULES = {"3b", "6b", "6c"}

# Of those, the two a FIXTURE can make judge itself. 6c is excluded on purpose:
# its subject is the release of the target installed on THIS host, and a fixture
# is installed on nobody's host, so it declines on both fixtures by design. It
# is proven through the app-list seam instead (see the host-half tests below).
FIXTURE_JUDGED = {"3b", "6b"}

# The env switch `live.py` reads. "0" declines the live probes deliberately.
LIVE_TOGGLE = "AMPLIFIER_COMPOSITION_KIT_LIVE"

# The env seam `live.py` reads for rule 6c: whitespace-separated bundle URIs
# that REPLACE the host's own app-bundle list.
APP_BUNDLES = "AMPLIFIER_COMPOSITION_KIT_APP_BUNDLES"


def _uv() -> str:
    uv = shutil.which("uv")
    if not uv:
        raise RuntimeError(
            "uv is required to run the composition kit (it provisions pyyaml)."
        )
    return uv


def run_kit(target, env_extra=None):
    """Invoke the kit on a target repo root; return (exit_code, parsed_report).

    The live rules stand real sessions up, so the timeout allows for a first
    run that has to fetch the lean base.
    """
    env = dict(os.environ)
    env.update(env_extra or {})
    proc = subprocess.run(
        [_uv(), "run", str(RUN), str(target), "--json-only"],
        capture_output=True, text=True, timeout=1200, check=False, env=env,
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
    assert failed == {
        "1a", "1b", "2a", "2b", "3a", "3b", "4", "5", "6a", "6b", "7a", "7b",
    }, failed


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
    # The two live rules name what a live session showed, not a category.
    assert "anchors:" in rules["3b"]["detail"]
    assert "sample-bad:reader" in rules["3b"]["detail"]
    assert "tool-bash" in rules["6b"]["detail"]
    assert "bundle.md" in rules["6b"]["detail"]


# --------------------------------------------------------------------------- #
# THE load-bearing test: no rule proves nothing                               #
# --------------------------------------------------------------------------- #
def test_every_rule_has_a_negative_fixture():
    """Every rule the kit emits must either FAIL on sample-bad, or be an
    explicitly declared SKIP with a reason. There is no third option — a rule
    that can only ever PASS is decoration.

    A SKIP is exempted here, which would be a hole if the exemption were the
    end of the story. It is not: 6c, the one rule that declines on both
    fixtures, is driven red and green by the host-half tests below.
    """
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


def test_only_the_live_rules_may_skip():
    """A file-readable rule may never SKIP, and any SKIP names why.

    Before 2026-09-04 this test pinned the SKIP set to exactly {3b, 6b}, which
    made an honest decline permanent: both rules were guaranteed to skip and so
    could never be wrong. They now stand sessions up. What is still worth
    pinning is the ceiling — nothing OUTSIDE those two may ever decline, and a
    decline that does happen must say what capability was missing.
    """
    for fixture in (GOOD, BAD):
        _, report = run_kit(fixture)
        skipped = {r["rule"] for r in report["results"] if r["status"] == "SKIP"}
        assert skipped <= LIVE_RULES, (
            f"{fixture.name}: rule(s) {sorted(skipped - LIVE_RULES)} declined, and only "
            f"{sorted(LIVE_RULES)} may — a file-readable rule that SKIPs is dodging a verdict"
        )
        for r in report["results"]:
            if r["status"] == "SKIP":
                assert r.get("reason", "").strip(), f"rule {r['rule']} SKIPs with no reason"


def test_live_rules_reach_a_real_verdict_on_this_host():
    """The live probes actually run here — they do not quietly decline.

    This is the test that would have caught the old state of the world, where
    3b and 6b were guaranteed SKIPs. If the host genuinely cannot run them the
    assertion message names the reason the kit gave, so a red here is readable
    as "this host lacks X", not as a mystery.
    """
    _, report = run_kit(GOOD)
    rows = by_rule(report)
    for rule in sorted(FIXTURE_JUDGED):
        row = rows[rule]
        assert row["status"] in {"PASS", "FAIL"}, (
            f"rule {rule} declined instead of judging: {row.get('reason') or row['detail']}"
        )
    # 6c declines against a fixture, and the decline must say WHY in terms a
    # reader can act on: how many app bundles the host has, where that list
    # came from, and which names it looked for. A bare decline here would hide
    # a probe that silently found nothing to measure.
    host = rows["6c"]
    assert host["status"] == "SKIP", host
    assert host["app_bundle_source"], "6c declined without saying where the app list came from"
    assert "sample-good" in host["reason"], host["reason"]
    # And the verdict is backed by evidence from the run, not by a category.
    assert rows["3b"]["roster_size"] > 0
    assert rows["3b"]["delegation_tool_mounted"] is True
    assert rows["6b"]["control_promised_tools_present"], (
        "the control session carried none of the promised tools, so 6b measured nothing"
    )
    assert rows["6b"]["treatments"], "6b measured no install path"


def test_live_rules_decline_honestly_when_switched_off():
    """With live probing off, both rules SKIP with a named reason — and only those two.

    The honest-decline path is a behaviour, so it is tested rather than trusted:
    switching the probes off must produce a reason a reader can act on, must not
    fabricate a PASS, and must not disturb any file-readable rule.
    """
    _, live_report = run_kit(GOOD)
    _, off_report = run_kit(GOOD, env_extra={LIVE_TOGGLE: "0"})
    off = by_rule(off_report)
    for rule in sorted(LIVE_RULES):
        assert off[rule]["status"] == "SKIP", off[rule]
        assert LIVE_TOGGLE in off[rule]["reason"], (
            f"rule {rule} declined without naming the missing capability: {off[rule]['reason']}"
        )
    unchanged = {
        r["rule"]: r["status"] for r in live_report["results"] if r["rule"] not in LIVE_RULES
    }
    still = {
        r["rule"]: r["status"] for r in off_report["results"] if r["rule"] not in LIVE_RULES
    }
    assert unchanged == still, (
        "switching the live probes off changed a file-readable rule's verdict"
    )


def test_no_rule_is_ever_fabricated():
    """Every emitted status is one of the three honest values."""
    for fixture in (GOOD, BAD, REPO):
        _, report = run_kit(fixture)
        for r in report["results"]:
            assert r["status"] in {"PASS", "FAIL", "SKIP"}, r
            assert r["detail"].strip(), f"rule {r['rule']} reports no detail"


# --------------------------------------------------------------------------- #
# The host half (6c): the release already installed, not the working tree      #
# --------------------------------------------------------------------------- #
def host_row(target, app_bundles):
    """Run the kit against `target` with the host's app list replaced."""
    _, report = run_kit(target, env_extra={APP_BUNDLES: " ".join(app_bundles)})
    return by_rule(report)["6c"]


def uri(fixture):
    return "file://" + str((fixture / "bundle.md").resolve())


def test_host_half_goes_red_when_the_installed_release_strips_tools():
    """The negative fixture 6c could not otherwise have.

    This is the shape of what actually happened on 2026-09-04 (converge-w3v):
    a repository whose own tree passes 6a and 6b, and a release of the SAME
    product installed on the host taking shell, delegation and skills from
    every spawned helper in every session. 6b cannot see it — it composes the
    tree. 6c must, and must name the entry that carries it, because "your host
    is contaminated" is not an actionable finding and "remove this URI" is.
    """
    row = host_row(BAD, [uri(BAD)])
    assert row["status"] == "FAIL", row
    assert "tool-bash" in row["detail"], row["detail"]
    assert "sample-bad" in row["detail"], row["detail"]
    assert row["host_lost"] == ["tool-bash", "tool-delegate", "tool-skills"], row
    carriers = [r for r in row["attribution"] if r.get("spawn")]
    assert len(carriers) == 1, carriers


def test_host_half_goes_green_when_the_installed_release_is_clean():
    """And it is not stuck red: a clean installed release passes."""
    row = host_row(GOOD, [uri(GOOD)])
    assert row["status"] == "PASS", row
    assert row["host_spawn_policy"] is None, row
    assert row["host_lost"] == [], row


def test_host_half_never_blames_a_foreign_bundle():
    """A neighbour's spawn policy is not this repository's failure.

    Same mis-attribution rule 6b's control exists to prevent: a host can be
    contaminated by a bundle that has nothing to do with the target, and a rule
    that reported FAIL there would send someone auditing the wrong repository.
    The decline still has to SAY the promise is broken, and name the carrier.
    """
    row = host_row(GOOD, [uri(GOOD), uri(BAD)])
    assert row["status"] == "SKIP", row
    assert "IS broken on this host" in row["reason"], row["reason"]
    assert "sample-bad" in row["reason"], row["reason"]
    assert row["app_bundles_naming_this_repository"] == [uri(GOOD)], row


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
