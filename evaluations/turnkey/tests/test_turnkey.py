"""Self-tests for the turnkey harness.

Two things are proven here, in the same spirit as the repository's conformance
kits and their `sample-bad` fixtures:

1. **Every assertion can be made to fail.** An assertion nobody can make fail
   proves nothing, and a harness whose green light cannot go red is decoration.
2. **The fixture really carries its planted gaps**, in files that do not touch,
   and the answer key says what the fixture actually says. A fixture that has
   quietly healed would let the turnkey run pass without doing anything.

    uv run --with pytest pytest evaluations/turnkey -q
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

TURNKEY = Path(__file__).resolve().parent.parent
FIXTURES = TURNKEY / "fixtures"
GAP_REPO = FIXTURES / "gap-repo"


def _load_harness():
    """Import run.py by path. It is a `uv run` script, not an installed module."""
    spec = importlib.util.spec_from_file_location("turnkey_run", TURNKEY / "run.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    # Register before executing: @dataclass resolves its own module out of
    # sys.modules while the class body is being processed.
    sys.modules["turnkey_run"] = module
    spec.loader.exec_module(module)
    return module


run = _load_harness()


# ---------------------------------------------------------------------------
# clause 5 — a lane is a worker session's own working copy AND terminal session
# ---------------------------------------------------------------------------


@pytest.fixture
def lane():
    return run.Lane("a", "/w/lanes/a/repo", "lane/a", "base0000", "tmux-a")


@pytest.fixture
def worktrees():
    return [{"path": "/w/lanes/a/repo", "branch": "lane/a", "sha": "abc"}]


@pytest.fixture
def panes():
    return [{"session": "tmux-a", "path": "/w/lanes/a/repo"}]


def test_a_live_lane_is_live(lane, worktrees, panes):
    assert run.assert_lane_is_real(lane, worktrees, panes)["state"] == run.LIVE


def test_a_lane_without_its_own_worktree_is_not_a_lane(lane, panes):
    verdict = run.assert_lane_is_real(lane, [], panes)
    assert verdict["state"] == run.NOT_A_LANE
    assert not verdict["ok"]
    assert "no worktree registered" in " ".join(verdict["findings"])


def test_a_worktree_on_the_wrong_branch_is_not_a_lane(lane, panes):
    verdict = run.assert_lane_is_real(
        lane, [{"path": "/w/lanes/a/repo", "branch": "main"}], panes
    )
    assert verdict["state"] == run.NOT_A_LANE


def test_a_finished_lane_is_ended_not_a_violation(lane, worktrees):
    """A lane whose session has exited ran; it did not fail to be a lane."""
    verdict = run.assert_lane_is_real(lane, worktrees, [])
    assert verdict["state"] == run.ENDED
    assert verdict["ok"]


def test_a_lane_with_no_session_ever_recorded_is_unproven(worktrees):
    bare = run.Lane("d", "/w/lanes/a/repo", "lane/a")  # launcher recorded nothing
    verdict = run.assert_lane_is_real(bare, worktrees, [])
    assert verdict["state"] == run.UNPROVEN
    assert not verdict["ok"], "unproven must never be counted as a real lane"


def test_two_lanes_sharing_a_worktree_are_one_lane(lane):
    twin = run.Lane("b", "/w/lanes/a/repo", "lane/b", "base0000", "tmux-b")
    assert not run.assert_lanes_are_distinct([lane, twin])["ok"]


def test_two_lanes_sharing_a_branch_are_one_lane(lane):
    twin = run.Lane("b", "/w/lanes/b/repo", "lane/a", "base0000", "tmux-b")
    assert not run.assert_lanes_are_distinct([lane, twin])["ok"]


# ---------------------------------------------------------------------------
# clause 5 — in-session sub-agents never execute lane work
# ---------------------------------------------------------------------------

LANE_WT = ["/w/lanes/a/repo"]
HELD = [{"id": "x-1", "status": "held", "holder": "agent-spark-1-111"}]


def test_work_held_from_inside_a_lane_worktree_passes():
    processes = {111: {"pid": 111, "cwd": "/w/lanes/a/repo", "cmdline": "amplifier"}}
    verdict = run.assert_no_subagent_held_work(HELD, processes, LANE_WT)
    assert verdict["ok"]
    assert verdict["verdicts"][0]["verdict"] == run.PASS


def test_work_held_from_the_managers_own_directory_fails():
    """THE test. This is the in-session sub-agent signature."""
    processes = {111: {"pid": 111, "cwd": "/w", "cmdline": "amplifier"}}
    verdict = run.assert_no_subagent_held_work(HELD, processes, LANE_WT)
    assert not verdict["ok"]
    assert verdict["offenders"][0]["item"] == "x-1"
    assert "not any lane worktree" in verdict["offenders"][0]["why"]


def test_one_process_cannot_hold_two_items():
    two = [
        {"id": "x-1", "status": "held", "holder": "agent-spark-1-111"},
        {"id": "x-2", "status": "held", "holder": "agent-spark-1-111"},
    ]
    processes = {111: {"pid": 111, "cwd": "/w/lanes/a/repo", "cmdline": "amplifier"}}
    verdict = run.assert_no_subagent_held_work(two, processes, LANE_WT)
    assert not verdict["ok"]
    assert "one process cannot be two lanes" in verdict["offenders"][0]["why"]


def test_an_exited_holder_is_unresolved_never_a_pass():
    verdict = run.assert_no_subagent_held_work(HELD, {111: None}, LANE_WT)
    assert verdict["verdicts"][0]["verdict"] == run.SKIP
    assert len(verdict["unresolved"]) == 1


def test_a_resolution_naming_a_lane_branch_corroborates_but_does_not_pass():
    items = [{"id": "x-1", "status": "resolved", "holder": "agent-spark-1-111",
              "resolution": "landed on lane/a"}]
    verdict = run.assert_no_subagent_held_work(items, {111: None}, LANE_WT, ["lane/a"])
    record = verdict["verdicts"][0]
    assert record["verdict"] == run.SKIP, "prose can be written by a session that never left itself"
    assert "corroboration" in record


def test_a_holder_id_carrying_no_pid_is_unresolved():
    items = [{"id": "x-1", "status": "held", "holder": "someone"}]
    verdict = run.assert_no_subagent_held_work(items, {}, LANE_WT)
    assert verdict["verdicts"][0]["verdict"] == run.SKIP


def test_an_item_with_no_holder_is_not_judged():
    items = [{"id": "x-1", "status": "open", "holder": None}]
    assert run.assert_no_subagent_held_work(items, {}, LANE_WT)["checked"] == 0


# ---------------------------------------------------------------------------
# the container CLI's envelope — the fabricated-pass path this harness caught
# itself taking (see ../RESULT.md, run 2)
# ---------------------------------------------------------------------------


def _envelope(exit_code: int, stdout: str = "", stderr: str = "") -> run.Ran:
    payload = json.dumps({"id": "dtu-1", "command": "bash -lc x",
                          "exit_code": exit_code, "stdout": stdout, "stderr": stderr})
    return run.Ran(0, payload, "", argv=["amplifier-digital-twin", "exec"])


def test_a_failing_command_inside_a_container_is_not_a_success():
    """The CLI exits 0 even when the inner command failed. Unwrap, or lie."""
    inner = run.unwrap_dtu_envelope(_envelope(1, stderr="boom"), ["false"])
    assert not inner.ok
    assert inner.code == 1
    assert "boom" in inner.text


def test_the_inner_commands_own_stdout_is_what_comes_back():
    inner = run.unwrap_dtu_envelope(_envelope(0, stdout='{"verdict": "PASS"}'), ["x"])
    assert inner.ok
    assert json.loads(inner.out)["verdict"] == "PASS"


def test_an_unreadable_envelope_is_a_loud_failure_not_an_empty_success():
    outer = run.Ran(0, "not json at all", "", argv=["x"])
    inner = run.unwrap_dtu_envelope(outer, ["x"])
    assert inner.code is None
    assert "no readable result envelope" in (inner.failure or "")


def test_a_failing_container_cli_is_reported_as_such():
    outer = run.Ran(2, "", "no such instance", argv=["x"])
    inner = run.unwrap_dtu_envelope(outer, ["x"])
    assert "the container CLI itself failed" in (inner.failure or "")


# ---------------------------------------------------------------------------
# clause 7 — a marker on an unchanged branch is stuck
# ---------------------------------------------------------------------------


def test_an_unchanged_branch_is_stuck(lane):
    assert run.assert_commits_beyond_base(lane, 0)["verdict"] == run.FAIL


def test_a_branch_with_commits_is_not_stuck(lane):
    assert run.assert_commits_beyond_base(lane, 3)["verdict"] == run.PASS


def test_no_base_sha_is_a_skip_not_a_pass():
    lane = run.Lane("c", "/w/c", "lane/c")
    assert run.assert_commits_beyond_base(lane, None)["verdict"] == run.SKIP


# ---------------------------------------------------------------------------
# the harness's own self-check must be green, and must cover every assertion
# ---------------------------------------------------------------------------


def test_self_check_is_green():
    report = run.self_check()
    assert report["verdict"] == run.PASS, report["failed"]


def test_self_check_covers_every_assertion():
    """Every public assert_* function must appear in the self-check's source."""
    import inspect

    source = inspect.getsource(run.self_check)
    for name in dir(run):
        if name.startswith("assert_"):
            assert name in source, f"{name} is never exercised by --self-check"


# ---------------------------------------------------------------------------
# the fixture — planted gaps, in files that do not touch
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def answer_key():
    return json.loads((FIXTURES / "answer-key.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def fixture_report():
    done = subprocess.run(  # noqa: S603
        [sys.executable, "check.py", ".", "--json-only"],
        cwd=GAP_REPO, capture_output=True, text=True, check=False,
    )
    return json.loads(done.stdout), done.returncode


def test_the_fixture_is_red_before_any_work(fixture_report):
    report, code = fixture_report
    assert report["verdict"] == "FAIL"
    assert code == 1


def test_the_answer_key_matches_what_the_fixture_actually_says(answer_key, fixture_report):
    report, _ = fixture_report
    red = sorted(r["rule"] for r in report["results"] if r["status"] == "FAIL")
    assert red == sorted(answer_key["expected_red_rules_before"])


def test_the_two_gaps_do_not_touch(answer_key):
    """Two gaps in one file could never justify two lanes (clause 6)."""
    owned = [set(gap["owns"]) for gap in answer_key["gaps"]]
    assert len(owned) == answer_key["expected_lane_count"] == 2
    assert owned[0].isdisjoint(owned[1])
    for gap, other in zip(answer_key["gaps"], reversed(answer_key["gaps"])):
        assert set(gap["must_not_touch"]) == set(other["owns"])


def test_every_gap_quote_is_in_the_contract_verbatim(answer_key):
    contract = (GAP_REPO / answer_key["contract_file"]).read_text(encoding="utf-8")
    squeezed = " ".join(contract.split())
    for gap in answer_key["gaps"]:
        assert " ".join(gap["quote"].split()) in squeezed, gap["id"]


def test_seeding_refuses_to_overwrite_existing_work(tmp_path):
    target = tmp_path / "lumen"
    first = subprocess.run(  # noqa: S603
        [str(FIXTURES / "seed.sh"), str(target)], capture_output=True, text=True, check=False
    )
    assert first.returncode == 0, first.stderr
    assert (target / "check.py").is_file()
    second = subprocess.run(  # noqa: S603
        [str(FIXTURES / "seed.sh"), str(target)], capture_output=True, text=True, check=False
    )
    assert second.returncode != 0
    assert "not empty" in second.stderr


# ---------------------------------------------------------------------------
# reporting invariants — a SKIP is never a soft pass
# ---------------------------------------------------------------------------


def test_every_step_is_named_and_ordered():
    letters = [letter for letter, _, _, _ in run.STEPS]
    assert letters == list("abcdefghi")


def test_a_skip_always_carries_a_reason():
    """Structural: every SKIP the harness constructs states why."""
    import inspect

    for name, function in vars(run).items():
        if not name.startswith("step_"):
            continue
        source = inspect.getsource(function)
        for chunk in source.split("Result(")[1:]:
            head = chunk[:200]
            if head.lstrip().startswith("SKIP") or "\n            SKIP" in head:
                assert "reason=" in chunk[:600], f"{name} builds a SKIP with no reason"


# ---------------------------------------------------------------------------
# clause 5, in the present tense — two lanes seen running AT ONCE, from outside
# ---------------------------------------------------------------------------
#
# Every other lane assertion reads what a lane LEFT BEHIND, and everything a
# lane leaves behind can be produced by a session that never left itself. These
# cover the one reading that cannot: the container's own live session list and
# git's own live worktree list, sampled while the manager session was working.


BOTH = {"at": "T0", "sessions": ["hw__b__one", "hw__b__two"],
        "worktrees": [{"branch": "lane/one"}, {"branch": "lane/two"}]}


def test_two_lanes_live_at_once_is_the_concurrency_evidence():
    assert run.assert_lanes_observed_live([BOTH])["verdict"] == run.PASS


def test_sessions_in_one_sample_and_worktrees_in_another_are_not_concurrent():
    """The conjunction is per-sample on purpose: two facts are not two lanes."""
    apart = [
        {"at": "T1", "sessions": ["hw__b__one", "hw__b__two"], "worktrees": []},
        {"at": "T2", "sessions": [],
         "worktrees": [{"branch": "lane/one"}, {"branch": "lane/two"}]},
    ]
    verdict = run.assert_lanes_observed_live(apart)
    assert verdict["verdict"] == run.FAIL
    assert "at once" in verdict["why"]


def test_a_non_lane_session_does_not_count_toward_width():
    noise = [{"at": "T3", "sessions": ["probe", "0", "hw__b__one"],
              "worktrees": [{"branch": "lane/one"}, {"branch": "lane/two"}]}]
    assert run.assert_lanes_observed_live(noise)["verdict"] == run.FAIL


def test_a_non_lane_branch_does_not_count_toward_width():
    noise = [{"at": "T4", "sessions": ["hw__b__one", "hw__b__two"],
              "worktrees": [{"branch": "lane/one"}, {"branch": "main"}]}]
    assert run.assert_lanes_observed_live(noise)["verdict"] == run.FAIL


def test_no_samples_is_a_skip_with_a_reason_never_a_pass():
    verdict = run.assert_lanes_observed_live([])
    assert verdict["verdict"] == run.SKIP
    assert verdict["why"]


def test_width_is_honoured():
    assert run.assert_lanes_observed_live([BOTH], width=3)["verdict"] == run.FAIL


# ---------------------------------------------------------------------------
# the objective handed to the manager session
# ---------------------------------------------------------------------------


OBJECTIVE_FIELDS = {
    "fixture_repo": "/workspace/lumen-fixture", "project": "turnkey", "width": "2",
    "deadline_minutes": "60", "check_command": "python3 check.py .",
    "launcher": "/usr/local/launch_lane.sh", "batch_dir": "/workspace/turnkey-batch",
    "tmux_socket": "hw", "return_log": "docs/workflow/OWNER-RETURN-LOG.md",
}


def test_the_objective_the_repository_ships_can_actually_be_composed():
    """A field the harness cannot fill must be caught here, not at 3am in a DTU."""
    text, why = run.objective_text(TURNKEY / "manager-objective.md", OBJECTIVE_FIELDS)
    assert why is None, why
    assert "{" not in text.replace("{}", "")
    assert "/workspace/lumen-fixture" in text


def test_the_objectives_editorial_preamble_is_never_sent():
    text, _ = run.objective_text(TURNKEY / "manager-objective.md", OBJECTIVE_FIELDS)
    assert "This file is what the turnkey harness hands" not in text


def test_a_missing_field_is_named_rather_than_formatted_into_nonsense(tmp_path):
    draft = tmp_path / "objective.md"
    draft.write_text("preamble\n---\nwork in {nowhere}\n", encoding="utf-8")
    text, why = run.objective_text(draft, OBJECTIVE_FIELDS)
    assert text == ""
    assert "{nowhere}" in why


# ---------------------------------------------------------------------------
# the lane socket — a reading that looks at the wrong socket reports no lanes
# ---------------------------------------------------------------------------


class _FakeEnv(run.Env):
    """An environment where only the `-L hw` socket has anything on it."""

    def __init__(self):
        self.argvs = []

    def run(self, argv, cwd=None, timeout=120.0, env=None):
        self.argvs.append(argv)
        if argv[:3] == ["tmux", "-L", "hw"]:
            return run.Ran(0, "hw__b__one\t/w/lanes/one\n", "", argv=argv)
        return run.Ran(1, "", "no server running", argv=argv)


def test_lanes_on_the_launchers_socket_are_seen():
    """The launcher uses `-L hw`; a default-socket-only reading sees nothing."""
    env = _FakeEnv()
    panes = run.read_tmux_panes(env)
    assert [p["session"] for p in panes] == ["hw__b__one"]
    assert panes[0]["socket"] == "hw"


def test_both_sockets_are_actually_asked():
    env = _FakeEnv()
    run.read_tmux_panes(env)
    assert any("-L" not in a for a in env.argvs)
    assert any(a[:3] == ["tmux", "-L", "hw"] for a in env.argvs)
