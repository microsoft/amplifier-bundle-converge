"""The live attribution probe targets an explicit integration, never a guess."""

import importlib.util
import subprocess
from pathlib import Path

import pytest


@pytest.fixture
def probe(monkeypatch):
    root = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location(
        "turnkey_clause_branch_test", root / "ledger/checks/turnkey_clause.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "HARNESS", root / "evaluations/turnkey/run.py")
    monkeypatch.setattr(module, "find_workspace", lambda: (None, "unit-test"))
    return module


@pytest.mark.parametrize("branch", [None, "", "preview/unit-check"])
def test_explicit_integration_is_forwarded_without_changing_the_default(
    probe, monkeypatch, branch
):
    if branch is None:
        monkeypatch.delenv("CONVERGE_INTEGRATION_BRANCH", raising=False)
    else:
        monkeypatch.setenv("CONVERGE_INTEGRATION_BRANCH", branch)
    calls = []

    def run(argv, **kwargs):
        calls.append(argv)
        return subprocess.CompletedProcess(argv, 0, stdout='{"clauses": {}}', stderr="")

    monkeypatch.setattr(probe.subprocess, "run", run)
    assert probe.read("k")[0] == {"clauses": {}}
    assert len(calls) == 1
    argv = calls[0]
    if branch:
        index = argv.index("--integration-branch")
        assert argv[index + 1] == branch
    else:
        assert "--integration-branch" not in argv


@pytest.mark.parametrize("record", [None, "", "/tmp/some/external/PLAN.md"])
def test_explicit_plan_record_is_forwarded_for_step_j_without_changing_the_default(
    probe, monkeypatch, record
):
    """CONVERGE_PLAN_RECORD forwards to --plan-record for step (j) only; unset,
    step (j) keeps its legacy HIGHWAY/PLAN/WAVE-LOG search in --workspace
    untouched (converge-51oq). Step (j) needs a workspace to proceed at all, so
    this test supplies one -- unlike the fixture's default, which has none."""
    if record is None:
        monkeypatch.delenv("CONVERGE_PLAN_RECORD", raising=False)
    else:
        monkeypatch.setenv("CONVERGE_PLAN_RECORD", record)
    monkeypatch.setattr(probe, "find_workspace", lambda: (Path("/some/workspace"), "unit-test"))
    calls = []

    def run(argv, **kwargs):
        calls.append(argv)
        return subprocess.CompletedProcess(argv, 0, stdout='{"clauses": {}}', stderr="")

    monkeypatch.setattr(probe.subprocess, "run", run)
    assert probe.read("j")[0] == {"clauses": {}}
    assert len(calls) == 1
    argv = calls[0]
    if record:
        index = argv.index("--plan-record")
        assert argv[index + 1] == record
    else:
        assert "--plan-record" not in argv


@pytest.mark.parametrize("record", [None, "", "/tmp/dangling/does-not-exist/PLAN.md"])
def test_plan_record_is_never_forwarded_for_the_attribution_step_k(
    probe, monkeypatch, record
):
    """Step (k) reads this repository's own git history and nothing else --
    it never touches a manager workspace or a plan record (docstring's (k)
    ATTRIBUTION section). CONVERGE_PLAN_RECORD must never reach step (k)'s
    argv, even when it names an invalid or dangling path: forwarding it there
    would let a broken plan-record override break git-only attribution, which
    the README does not promise and step (k) does not read (converge-51oq)."""
    if record is None:
        monkeypatch.delenv("CONVERGE_PLAN_RECORD", raising=False)
    else:
        monkeypatch.setenv("CONVERGE_PLAN_RECORD", record)
    calls = []

    def run(argv, **kwargs):
        calls.append(argv)
        return subprocess.CompletedProcess(argv, 0, stdout='{"clauses": {}}', stderr="")

    monkeypatch.setattr(probe.subprocess, "run", run)
    assert probe.read("k")[0] == {"clauses": {}}
    assert len(calls) == 1
    assert "--plan-record" not in calls[0]


def test_an_untraceable_target_cannot_become_a_passing_attribution(probe, monkeypatch, capsys):
    report = {"clauses": {"readings": [{
        "row": "CVG-017",
        "attribution": {"verdict": "SKIP", "why": "the integration ref could not be traced"},
    }]}}
    monkeypatch.setattr(probe, "read", lambda letter: (report, "unit-test"))
    assert probe.main(["probe", "--attribution", "CVG-017", "PASS", "any lane merge"]) == 0
    text = capsys.readouterr().out
    assert "CHANGED-REREAD-THIS-ROW" in text
    assert "ASSERTS-THIS" not in text