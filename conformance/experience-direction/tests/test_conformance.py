"""Self-test for the experience-direction.v1 conformance kit.

The kit is only as trustworthy as its own demonstration: it must go GREEN
against a body that keeps the promises (``fixtures/sample-good``) and RED — with
named rule failures — against one that does not (``fixtures/sample-bad``). Both
fixtures are **captured app snapshots**, the same shape ``run.py --capture``
writes, so they are judged through exactly the code path a live app is.

The load-bearing test is ``test_every_rule_has_a_negative_fixture``: a rule
nobody can make fail is a rule that proves nothing. The SKIP set is pinned, so a
rule cannot quietly drift into SKIP to dodge a failure.

Runnable two ways (the assertions are identical):
  * with pytest:  uv run --with pytest pytest conformance/experience-direction/tests/ -q
  * no deps:      python3 conformance/experience-direction/tests/test_conformance.py

The kit declares no dependencies, so the plain interpreter is enough.
"""

import json
import re
import subprocess
import sys
from pathlib import Path

KIT = Path(__file__).resolve().parent.parent          # conformance/experience-direction/
RUN = KIT / "run.py"
REPO = KIT.parent.parent                              # the repository root
CONTRACT = REPO / "contracts" / "experience-direction.v1.md"
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
def test_a_word_in_a_message_is_not_a_write():
    """Measured against the live app: the per-change handler shows the message
    "Restore staged for the next proposal decision." and nothing else. Matched as
    a bare word, `decision` in that sentence read as a write and rule 8 reported a
    fabricated PASS. A write is a CALL."""
    kit = kit_module()
    tokens = {"decision", "feedback", "steer"}
    message_only = "{ toast('Restore staged for the next proposal decision.'); }"
    assert not kit.reaches_a_write(message_only, tokens)
    real_call = "{ api.decision(mid, { staged: 'keep' }); }"
    assert kit.reaches_a_write(real_call, tokens)


def test_a_handler_is_read_from_its_selector_not_its_markup():
    """`data-restore="document"` appears first inside a markup template; the
    wiring is at `[data-restore]`. Reading the markup returns a template
    interpolation, not the handler."""
    kit = kit_module()
    script = ("const html = `<button data-restore=\"document\">${label}</button>`;\n"
              "qsa('[data-restore]').forEach((b) => b.addEventListener('click', () => {"
              " api.ask(mid, { scope: b.dataset.restore }); }));")
    body = kit.handler_body(script, "[data-restore]")
    assert "api.ask" in body


def test_a_render_that_lifts_headings_into_titles_is_not_a_dropped_render():
    """The app renders each section under its heading, so `##` does not survive as
    `<h2>` in the body. Reading headings as the markdown probe reported the render
    dropping markdown on every document — a fabricated finding."""
    _, report = run_kit(GOOD)
    assert by_rule(report)["2b"]["status"] == "PASS"


def test_the_unjudged_capabilities_are_named():
    """2b never claims more than the target demonstrates: what the documents do
    not contain is reported as unjudged rather than passed over."""
    _, report = run_kit(GOOD)
    row = by_rule(report)["2b"]
    assert "not_demonstrated" in row


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
