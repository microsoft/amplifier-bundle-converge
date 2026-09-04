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


def test_sessions_in_one_sample_and_worktrees_in_another_are_unproven_not_passed():
    """The conjunction is per-sample on purpose: two facts are not two lanes.

    But periodic sampling cannot tell "they never overlapped" from "the sampler
    blinked", so this is the honest middle -- reported, never passed.
    """
    apart = [
        {"at": "T1", "sessions": ["hw__b__one", "hw__b__two"], "worktrees": []},
        {"at": "T2", "sessions": [],
         "worktrees": [{"branch": "lane/one"}, {"branch": "lane/two"}]},
    ]
    verdict = run.assert_lanes_observed_live(apart)
    assert verdict["verdict"] == run.SKIP
    assert verdict["verdict"] != run.PASS
    assert "one reading" in verdict["why"]


def test_nothing_lane_shaped_in_any_sample_is_a_real_failure():
    """A manager that ran the work in-session leaves no lane in ANY reading."""
    nothing = [{"at": "T1", "sessions": ["0"], "worktrees": []},
               {"at": "T2", "sessions": [], "worktrees": []}]
    verdict = run.assert_lanes_observed_live(nothing)
    assert verdict["verdict"] == run.FAIL


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


# ---------------------------------------------------------------------------
# a finished wave tidies up — and a tidy repository is not an empty one
# ---------------------------------------------------------------------------


CLEANED_LANE = run.Lane("units-fix", "/w/batch/lanes/units-fix/repo", "lane/units-fix",
                        "base0000", "hw__batch__units-fix")
WHILE_RUNNING = [{"at": "T0", "sessions": ["hw__batch__units-fix"],
                  "worktrees": [{"branch": "lane/units-fix"}]}]


def test_a_merged_and_cleaned_up_lane_is_ended_not_a_fabrication():
    """The measured regression: two real merged lanes reported as 'no lanes'."""
    verdict = run.assert_lane_is_real(CLEANED_LANE, [], [], WHILE_RUNNING)
    assert verdict["state"] == run.ENDED
    assert verdict["ok"] is True
    assert verdict["observed_running"]["at"] == "T0"


def test_a_lane_never_seen_running_and_with_no_worktree_is_still_not_a_lane():
    assert run.assert_lane_is_real(CLEANED_LANE, [], [], [])["state"] == run.NOT_A_LANE


def test_half_an_observation_does_not_resurrect_a_lane():
    """Session seen but its worktree never was: that is not the clause-5 bar."""
    half = [{"at": "T0", "sessions": ["hw__batch__units-fix"], "worktrees": []}]
    assert run.assert_lane_is_real(CLEANED_LANE, [], [], half)["state"] == run.NOT_A_LANE


def test_another_lanes_observation_does_not_vouch_for_this_one():
    other = [{"at": "T0", "sessions": ["hw__batch__index-fix"],
              "worktrees": [{"branch": "lane/index-fix"}]}]
    assert run.assert_lane_is_real(CLEANED_LANE, [], [], other)["state"] == run.NOT_A_LANE


# ---------------------------------------------------------------------------
# a dated brief is dated whether or not a time follows the date
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("heading", ["## 2026-09-04T04:01Z", "## 2026-09-04",
                                     "on 2026-09-04, at last"])
def test_an_iso_timestamp_counts_as_a_dated_entry(heading):
    import re
    pattern = re.compile(r"\b20\d{2}-\d{2}-\d{2}(?![-\d])")
    assert pattern.search(heading), heading


def test_the_brief_check_actually_uses_that_pattern():
    assert r"(?![-\d])" in run.ENTRY_DATE.pattern


def test_an_iso_timestamped_heading_really_opens_an_entry():
    """The pattern is only worth anything if the parser is the thing using it."""
    entries = run.parse_return_log("## 2026-09-04T04:01Z\n**Stuck.** nothing.\n")
    assert len(entries) == 1
    assert entries[0]["parts_present"] == ["stuck"]


# ---------------------------------------------------------------------------
# clause 10 - the five parts are counted INSIDE one entry, never across a file
# ---------------------------------------------------------------------------
#
# The measured defect: step (i) lowercased the whole log and asked whether each
# of the five words appeared anywhere in it. A header, a footnote, or an
# unrelated paragraph passed the check with no brief in the file at all, and
# `docs/workflow/OWNER-RETURN-LOG.md` had to deliberately NOT name the five
# labels in its header to keep the check honest. These fix the scope: an entry.


FIVE_PARTS = (
    "**Time away.** You were gone two hours and one wave ran in that time.\n"
    "**Finished.** Both lanes merged and I re-ran the kit on the merged result.\n"
    "**Stuck.** Nothing stopped; every lane returned with evidence behind it.\n"
    "**Needs you.** Nothing needs you today, and no call waits on your word.\n"
    "**Anything quietly broken.** Nothing broke that you did not know about.\n"
)
BRIEFED_RETURN = "## 2026-09-04 04:01 - the gate went green\n" + FIVE_PARTS

# The header the real log cannot currently write, because the old check would
# have taken it for a brief and gone green on it.
HEADER_WITH_THE_FIVE_WORDS = (
    "# Owner return log\n\n"
    "Each entry carries five parts: time away, finished, stuck, needs you, and\n"
    "anything quietly broken. Newest last, and every entry is dated 2026-09-04\n"
    "or later, which is the shape this file has always had.\n"
)


class _LogEnv(run.Env):
    """An environment whose only fact is the text of one return log."""

    def __init__(self, text=None):
        self.text = text

    def run(self, argv, cwd=None, timeout=120.0, env=None):
        return run.Ran(1, "", "nothing runs here", argv=argv)

    def read(self, path):
        return self.text


def judge_log(text):
    ctx = run.Context(env=_LogEnv(text), host=None, mode=run.OBSERVED,
                      workspace="/w", repo="/w/repo", project="p",
                      integration_branch="main", answer_key={})
    return run.step_brief(ctx)


def test_a_header_carrying_the_five_words_is_not_a_brief():
    """The falsifier, stated as a test: prose is not a return brief."""
    verdict = judge_log(HEADER_WITH_THE_FIVE_WORDS)
    assert verdict.status == run.FAIL
    assert "no dated entry" in verdict.detail
    assert verdict.evidence["dated_entries"] == 0


def test_the_five_words_spread_across_separate_entries_do_not_combine():
    """A file-wide read passes this log. No single entry is a brief."""
    scattered = (
        "## 2026-09-01 - one\ntime away: two hours, and that is all it says here.\n"
        "## 2026-09-02 - two\nfinished: the lane merged and nothing else happened.\n"
        "## 2026-09-03 - three\nstuck: nothing stopped anywhere in this wave.\n"
        "## 2026-09-04 - four\nneeds you: nothing at all needs you this time.\n"
        "## 2026-09-05 - five\nquietly broken: nothing broke that you should know.\n"
    )
    assert all(part in scattered.lower() for part in run.BRIEF_PARTS)  # the old read
    verdict = judge_log(scattered)
    assert verdict.status == run.FAIL
    assert verdict.evidence["complete_briefs"] == 0


def test_one_entry_carrying_all_five_parts_passes():
    verdict = judge_log(HEADER_WITH_THE_FIVE_WORDS + "\n" + BRIEFED_RETURN)
    assert verdict.status == run.PASS, verdict.detail
    assert verdict.evidence["stamped_returns"] == 1
    assert verdict.evidence["complete_briefs"] == 1
    assert verdict.evidence["judged"]["parts_missing"] == []


@pytest.mark.parametrize("part,line", [
    ("time away", "**Time away.**"), ("finished", "**Finished.**"),
    ("stuck", "**Stuck.**"), ("needs you", "**Needs you.**"),
    ("quietly broken", "**Anything quietly broken.**"),
])
def test_a_stamped_return_missing_one_part_fails_naming_that_part(part, line):
    """Each of the five, one at a time -- an assertion nobody can fail proves nothing."""
    holed = "\n".join(ln for ln in BRIEFED_RETURN.splitlines()
                      if not ln.startswith(line)) + "\n"
    verdict = judge_log(holed)
    assert verdict.status == run.FAIL
    assert part in verdict.detail
    assert verdict.evidence["unbriefed_returns"][0]["missing"] == [part]


def test_a_stamped_return_with_no_brief_under_it_is_counted_against_the_briefs():
    """Clause 10 is a brief on EVERY return, so the two numbers are compared."""
    unbriefed = BRIEFED_RETURN + (
        "\n## 2026-09-04 09:30 - they came back again\n"
        "I read the queue and answered them, and wrote none of this down.\n"
    )
    verdict = judge_log(unbriefed)
    assert verdict.status == run.FAIL
    assert verdict.evidence["stamped_returns"] == 2
    assert verdict.evidence["complete_briefs"] == 1
    assert "09:30" in verdict.evidence["unbriefed_returns"][0]["heading"]


def test_an_unprompted_brief_keeps_its_date_only_heading_and_is_not_a_return():
    """A wave landed while the steward was away: a brief with no return behind it."""
    verdict = judge_log("## 2026-09-04 - a wave landed while you were away\n" + FIVE_PARTS)
    assert verdict.status == run.PASS, verdict.detail
    assert verdict.evidence["stamped_returns"] == 0
    assert verdict.evidence["complete_briefs"] == 1


@pytest.mark.parametrize("marker", ["- ", "* ", "1. ", ""])
def test_the_parts_may_be_written_as_a_list_and_still_count_as_sentences(marker):
    """A rule that scored a correctly-written brief zero would fabricate a red.

    `context/manager/return-brief.md` prints the five parts as a NUMBERED list,
    so a manager session copying the shape it was shown writes `1. **Time
    away.** ...`. A check that read only the bare form would miss all five.
    """
    listed = "## 2026-09-04 04:01 - list form\n" + "".join(
        marker + ln + "\n" for ln in FIVE_PARTS.splitlines())
    verdict = judge_log(listed)
    assert verdict.status == run.PASS, verdict.detail
    assert verdict.evidence["judged"]["parts_missing"] == []
    assert verdict.evidence["judged"]["plain_sentences"] >= 3


def test_prose_that_merely_uses_a_part_word_does_not_count_as_that_part():
    """`nine well-written briefs say "nothing stopped" in their own words`."""
    prose = ("## 2026-09-04 04:01 - a paragraph, not a brief\n"
             "Finished lanes were merged and nothing needed you afterwards, and\n"
             "no time away was recorded because stuck lanes never happened here.\n")
    verdict = judge_log(prose)
    assert verdict.status == run.FAIL
    assert verdict.evidence["judged"]["parts_present"] == []


def test_a_missing_log_is_still_a_failure_that_names_both_paths():
    verdict = judge_log(None)
    assert verdict.status == run.FAIL
    assert run.RETURN_LOG in verdict.detail


def test_a_subsection_inside_an_entry_does_not_truncate_it():
    """`### Technical detail` is part of the brief it sits in, not a new entry."""
    with_detail = ("## 2026-09-04 04:01 - the gate went green\n"
                   "**Time away.** You were gone two hours and one wave ran in it.\n"
                   "### Technical detail\n" + FIVE_PARTS.split("\n", 1)[1])
    entries = run.parse_return_log(with_detail)
    assert len(entries) == 1
    assert entries[0]["complete"] is True


# ---------------------------------------------------------------------------
# the holder question, asked at the only time it can be answered
# ---------------------------------------------------------------------------
#
# A holder's working directory is readable only while that process is alive.
# Measured on run D: every holder on a finished wave was unresolved, so the
# strongest evidence against in-session execution existed only mid-flight.


HELD_ONE = [{"id": "x-1", "status": "resolved", "holder": "agent-spark-1-111"}]
IN_LANE_AT_T0 = [{"at": "T0", "holders": [{"item": "x-1", "pid": 111,
                                           "cwd": "/w/lanes/a/repo"}]}]


def test_an_exited_holder_read_inside_a_lane_while_it_ran_passes():
    verdict = run.assert_no_subagent_held_work(
        HELD_ONE, {111: None}, ["/w/lanes/a/repo"], None, IN_LANE_AT_T0)
    assert verdict["verdicts"][0]["verdict"] == run.PASS
    assert verdict["verdicts"][0]["read_at"] == "T0"
    assert verdict["unresolved"] == []


def test_an_exited_holder_read_outside_every_lane_while_it_ran_still_fails():
    """The observation is evidence, not amnesty."""
    outside = [{"at": "T0", "holders": [{"item": "x-1", "pid": 111, "cwd": "/w"}]}]
    verdict = run.assert_no_subagent_held_work(
        HELD_ONE, {111: None}, ["/w/lanes/a/repo"], None, outside)
    assert verdict["ok"] is False
    assert verdict["offenders"]


def test_an_observation_of_a_different_pid_does_not_place_this_holder():
    other = [{"at": "T0", "holders": [{"item": "x-9", "pid": 999,
                                       "cwd": "/w/lanes/a/repo"}]}]
    verdict = run.assert_no_subagent_held_work(
        HELD_ONE, {111: None}, ["/w/lanes/a/repo"], None, other)
    assert verdict["verdicts"][0]["verdict"] == run.SKIP


def test_a_live_reading_still_wins_over_an_observation():
    """Present-tense evidence is preferred; the observation is the fallback."""
    live = {111: {"pid": 111, "cwd": "/w/lanes/a/repo", "cmdline": "amplifier"}}
    verdict = run.assert_no_subagent_held_work(
        HELD_ONE, live, ["/w/lanes/a/repo"], None, IN_LANE_AT_T0)
    assert verdict["verdicts"][0]["verdict"] == run.PASS
    assert "read_at" not in verdict["verdicts"][0]


# ---------------------------------------------------------------------------
# base..branch is a question about refs, not about a directory
# ---------------------------------------------------------------------------


class _RepoOnlyEnv(run.Env):
    """A worktree that has been removed; the main repository still has both refs."""

    def __init__(self, alive="/w/repo"):
        self.alive = alive
        self.asked = []

    def run(self, argv, cwd=None, timeout=120.0, env=None):
        where = argv[argv.index("-C") + 1]
        self.asked.append(where)
        if where == self.alive:
            return run.Ran(0, "3\n", "", argv=argv)
        return run.Ran(128, "", f"cannot change to '{where}'", argv=argv)


def test_a_removed_worktree_falls_back_to_the_repository_that_still_has_the_refs():
    env = _RepoOnlyEnv()
    assert run.commits_beyond(env, "/w/gone/lane", "base", "lane/a", "/w/repo") == 3
    assert env.asked == ["/w/gone/lane", "/w/repo"]


def test_the_lanes_own_worktree_is_asked_first():
    env = _RepoOnlyEnv(alive="/w/gone/lane")
    assert run.commits_beyond(env, "/w/gone/lane", "base", "lane/a", "/w/repo") == 3
    assert env.asked == ["/w/gone/lane"]


def test_no_repository_that_can_answer_is_still_unmeasured_not_zero():
    env = _RepoOnlyEnv(alive="/nowhere")
    assert run.commits_beyond(env, "/w/gone/lane", "base", "lane/a", "/w/repo") is None
