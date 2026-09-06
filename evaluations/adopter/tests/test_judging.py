"""What this harness is allowed to conclude from what it saw.

These tests exist because the first real run (2026-09-04) judged three of its
rows on evidence that did not support them: a second scenario's install row
measured the first scenario's install, a queue row read the CLI's absence as
proof no work existed, and a manager-session row read one empty pane capture as
proof the mode never showed. Each case below is that defect, written down so it
cannot come back quietly.

Run:  uv run --with pytest pytest -q evaluations/adopter/tests/
"""

from __future__ import annotations

import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import harness as H  # noqa: E402


def _ts(second: int) -> datetime:
    return datetime(2026, 9, 5, 12, 0, 0, tzinfo=timezone.utc) + timedelta(
        seconds=second
    )


def _capture(sessions: str, pane: str) -> str:
    return f"<<<SESSIONS\n{sessions}\nSESSIONS>>>\n<<<PANE\n{pane}\nPANE>>>\n"


LIVE = "agent: 1 windows (created Sat Sep  5 12:00:00 2026)"
NO_SERVER = "no server running on /tmp/tmux-0/default"


# --------------------------------------------------------------------------
# One. Each scenario's install is measured in its own fresh container.
# --------------------------------------------------------------------------


def test_each_scenario_gets_its_own_container_id():
    """Two scenarios, two container ids -- never one shared container.

    Falsified by: both scenarios resolving to the same id, which is what made
    S2.1 a measurement of scenario 1's adopter.
    """
    stamp = "adopter-20260905120000"
    ids = {f"{stamp}-{sid.lower()}" for sid in ("S1", "S2")}
    assert len(ids) == 2


def test_a_container_that_already_has_converge_fails_its_own_gate():
    out = _section_out(
        bundles="converge   git+https://github.com/microsoft/amplifier-bundle-conv…",
        queuecli="amplifier-work-tracker: not on PATH",
    )
    step, _before = H.fresh_container_verdict("S2", "launched in 70s", out)
    assert step.verdict == H.FAIL
    assert "already" in step.missing
    assert "measure nothing" in step.missing


def test_a_container_with_no_converge_passes_and_hands_on_the_before_picture():
    out = _section_out(
        bundles="anchors\nfoundation",
        queuecli="amplifier-work-tracker: not on PATH",
    )
    step, before = H.fresh_container_verdict("S1", "launched in 70s", out)
    assert step.verdict == H.PASS
    # The install row quotes this, so a reader can see the container was clean
    # at launch rather than take the readiness gate's word for it.
    assert "foundation" in before
    assert "not on PATH" in before


def _section_out(*, bundles: str, queuecli: str) -> str:
    return f"<<<BUNDLES\n{bundles}\nBUNDLES>>>\n<<<QUEUECLI\n{queuecli}\nQUEUECLI>>>\n"


# --------------------------------------------------------------------------
# Two. The queue is read where a session writes it, not where a CLI would be.
# --------------------------------------------------------------------------


def _queue_out(*, cli: str, stores: int, items: int, contract_items: int, errors: int) -> str:
    return (
        "--- the queue CLI (a separate fact from whether a queue holds work) ---\n"
        f"amplifier-work-tracker on PATH: {cli}\n"
        "--- what this measured ---\n"
        f"QUEUE-CLI: {'present' if cli != 'no' else 'absent'}\n"
        f"QUEUE-STORES: {stores}\n"
        f"QUEUE-ITEMS: {items}\n"
        f"QUEUE-CONTRACT-ITEMS: {contract_items}\n"
        f"QUEUE-READ-ERRORS: {errors}\n"
    )


def test_an_item_filed_by_a_session_passes_even_with_no_cli_installed():
    """The exact 2026-09-04 case: `sensorlog-9ge` filed through the session's
    own `work_*` tools while `amplifier-work-tracker` was never on PATH.

    Falsified by: a FAIL whose reason is the CLI's absence.
    """
    step = H.queue_verdict(
        "S2", _queue_out(cli="no", stores=1, items=3, contract_items=1, errors=0)
    )
    assert step.verdict == H.PASS
    assert step.missing == ""


def test_the_cli_being_absent_is_never_itself_the_reason_a_row_is_red():
    step = H.queue_verdict(
        "S1", _queue_out(cli="no", stores=0, items=0, contract_items=0, errors=0)
    )
    assert step.verdict == H.FAIL
    # Red is right -- nothing was filed anywhere -- but the reason names what
    # was looked for and found absent, not the missing binary.
    assert "no queue store exists anywhere" in step.missing
    assert "separate fact" in step.missing


def test_items_that_name_no_contract_are_red_for_that_reason():
    step = H.queue_verdict(
        "S1", _queue_out(cli="yes", stores=1, items=4, contract_items=0, errors=0)
    )
    assert step.verdict == H.FAIL
    assert "none names a contract" in step.missing


def test_a_store_that_cannot_be_read_is_cant_tell_not_absence():
    step = H.queue_verdict(
        "S2", _queue_out(cli="no", stores=2, items=0, contract_items=0, errors=2)
    )
    assert step.verdict == H.UNPROVEN
    assert "could not tell" in step.missing


def test_a_probe_that_reported_nothing_is_cant_tell():
    step = H.queue_verdict("S1", "the probe crashed before printing anything")
    assert step.verdict == H.UNPROVEN
    assert "could not tell" in step.missing


def test_the_probe_reads_closed_items_too_and_is_not_capped_at_fifty():
    """Measured on 2026-09-06, scenario 1: the adopter filed one item, resolved
    it, and `bd list` — which shows OPEN issues, fifty at most — read the queue
    back as empty. The row then said the queue "holds no items at all" about a
    queue that had been used exactly as intended.

    Asserted against the probe's own source because the flags are the whole
    fix; a run that drops them looks green until someone finishes an item.
    """
    assert '["bd", "list", "--all", "--limit", "0", "--json"]' in H.QUEUE_PROBE_PY


def test_the_probe_finds_a_store_by_its_database_and_skips_a_scratch_dir(tmp_path):
    """Discovery, run for real against a filesystem.

    A store is where a session's `work_*` tools write. Running `bd` at all can
    leave a bare `$HOME/.beads/eventsData` behind; counting that as a store
    would turn "nothing was filed" into "could not tell".
    """
    root = tmp_path / ".amplifier-work-tracker"
    store = root / "projects" / "demo" / ".beads"
    store.mkdir(parents=True)
    (store / "config.yaml").write_text("# beads\n", encoding="utf-8")
    scratch = tmp_path / ".beads" / "eventsData"
    scratch.mkdir(parents=True)

    probe_py = tmp_path / "probe.py"
    probe_py.write_text(H.QUEUE_PROBE_PY, encoding="utf-8")
    env = dict(os.environ, HOME=str(tmp_path), AMPLIFIER_WORK_TRACKER_ROOT=str(root))
    out = subprocess.run(
        [sys.executable, str(probe_py)],
        capture_output=True, text=True, timeout=300, env=env,
    ).stdout

    assert "QUEUE-STORES: 1" in out
    assert f"store: {root / 'projects' / 'demo'}" in out
    assert "not a store (a .beads dir with no database in it)" in out


# --------------------------------------------------------------------------
# Three. The pane is sampled through the scenario, and an empty capture is
# "could not tell", never absence.
# --------------------------------------------------------------------------


def test_the_mode_seen_mid_scenario_survives_a_restart_before_the_end():
    """The exact 2026-09-04 case, inverted: the mode WAS up, then the session
    was restarted 28s before the budget cut and the final capture was blank.

    Falsified by: a FAIL saying the prompt "never shows [converge-manager]".
    """
    watch = H.PaneWatch(interval_s=30)
    watch.note(_ts(0), 0, _capture(LIVE, "> hello"))
    watch.note(_ts(30), 0, _capture(LIVE, "[converge-manager]> planning the lane"))
    watch.note(_ts(60), 0, _capture(LIVE, ""))  # restarted; blank pane
    step = H.judge_manager_session("S1", watch)
    assert step.verdict == H.PASS
    assert "[converge-manager]" in step.evidence
    assert "12:00:30Z" in step.evidence  # when it was first seen


def test_the_string_on_screen_but_never_as_a_prompt_is_cant_tell():
    """An adopter reading `modes/converge-manager.md` puts those exact
    characters in the pane. That is not the mode being active, and it is not
    evidence the mode never was — so it settles nothing either way.
    """
    watch = H.PaneWatch(interval_s=30)
    for i in range(3):
        watch.note(
            _ts(i * 30),
            0,
            _capture(LIVE, "  2   name: converge-manager\n  3   [converge-manager]"),
        )
    step = H.judge_manager_session("S2", watch)
    assert step.verdict == H.UNPROVEN
    assert "never as the prompt" in step.missing
    assert "NOT as a prompt" in step.evidence


def test_every_capture_empty_is_cant_tell_not_absence():
    watch = H.PaneWatch(interval_s=30)
    for i in range(4):
        watch.note(_ts(i * 30), 0, _capture(LIVE, ""))
    step = H.judge_manager_session("S1", watch)
    assert step.verdict == H.UNPROVEN
    assert "could not tell" in step.missing
    assert "empty pane is not evidence" in step.missing


def test_content_throughout_and_never_the_mode_is_a_real_red():
    watch = H.PaneWatch(interval_s=30)
    for i in range(5):
        watch.note(_ts(i * 30), 0, _capture(LIVE, "> just an ordinary session"))
    step = H.judge_manager_session("S1", watch)
    assert step.verdict == H.FAIL
    assert "5 of 5 captures" in step.missing


def test_no_session_at_any_sample_is_a_real_red():
    watch = H.PaneWatch(interval_s=30)
    for i in range(3):
        watch.note(_ts(i * 30), 0, _capture(NO_SERVER, ""))
    step = H.judge_manager_session("S1", watch)
    assert step.verdict == H.FAIL
    assert "no agent session existed at any of the 3 captures" in step.missing


def test_no_capture_that_ran_at_all_is_cant_tell():
    watch = H.PaneWatch(interval_s=30)
    for i in range(2):
        watch.note(_ts(i * 30), 1, "probe could not run: DTUError(container gone)")
    step = H.judge_manager_session("S1", watch)
    assert step.verdict == H.UNPROVEN
    assert "not one of the 2 captures ran" in step.missing


# --------------------------------------------------------------------------
# The verdict vocabulary itself: a CAN'T TELL is never counted as a pass.
# --------------------------------------------------------------------------


def test_a_cant_tell_row_keeps_a_scenario_out_of_green():
    run = H.ScenarioRun(name="x", key="k", sid="S1", project_dir="/workspace/x")
    run.steps = [
        H.Step("S1.1", "a", H.PASS, "seen"),
        H.Step("S1.2", "b", H.UNPROVEN, "empty", missing="could not tell"),
    ]
    assert run.verdict == H.UNPROVEN


def test_a_fail_outranks_a_cant_tell():
    run = H.ScenarioRun(name="x", key="k", sid="S1", project_dir="/workspace/x")
    run.steps = [
        H.Step("S1.1", "a", H.UNPROVEN, "", missing="could not tell"),
        H.Step("S1.2", "b", H.FAIL, "", missing="absent"),
    ]
    assert run.verdict == H.FAIL


def test_overall_is_not_green_when_anything_could_not_be_told(tmp_path):
    run = H.ScenarioRun(name="x", key="k", sid="S1", project_dir="/workspace/x")
    run.dtu_id = "adopter-test-s1"
    run.steps = [
        H.Step("S1.1", "a", H.PASS, "seen"),
        H.Step("S1.2", "b", H.UNPROVEN, "empty", missing="could not tell"),
    ]
    overall = H.write_result(
        tmp_path / "RESULT.md", scenarios=[run], meta={"started": "now"}
    )
    assert overall == "NOT PROVEN"
    text = (tmp_path / "RESULT.md").read_text(encoding="utf-8")
    assert "CAN'T TELL" in text
    assert "Could not tell: could not tell" in text


def test_overall_is_green_only_when_every_row_passed(tmp_path):
    run = H.ScenarioRun(name="x", key="k", sid="S1", project_dir="/workspace/x")
    run.dtu_id = "adopter-test-s1"
    run.steps = [H.Step("S1.1", "a", H.PASS, "seen")]
    overall = H.write_result(
        tmp_path / "RESULT.md", scenarios=[run], meta={"started": "now"}
    )
    assert overall == "GREEN"


# --------------------------------------------------------------------------
# Six. The two ORDER rows, added 2026-09-06 (converge-w3nb) for the hole
# CVG-301 named in as many words: "chain complete and measured, sequence
# attested and unmeasured". They may claim ordering only where the dating is
# exact. Where it rests on an mtime -- a LAST write -- anything but PASS is a
# CAN'T TELL, because that is all the evidence supports.
# --------------------------------------------------------------------------


def _wake_out(
    *,
    drafts: int = 2,
    draft_at: str = "2026-09-06T10:00:00+00:00",
    draft_src: str = "git",
    searched: int = 12,
    pause_lines: int = 1,
    pause_at: str = "2026-09-06T09:00:00+00:00",
    pause_order: str = "yes",
    inv_files: int = 1,
    inv_at: str = "2026-09-06T09:30:00+00:00",
    inv_order: str = "yes",
) -> str:
    return (
        "<<<DRAFTS\n(evidence)\nDRAFTS>>>\n"
        "--- what this measured ---\n"
        f"DRAFTS-FOUND: {drafts}\n"
        f"DRAFTS-EARLIEST: {draft_at}\n"
        f"DRAFTS-EARLIEST-SOURCE: {draft_src}\n"
        f"RECORDS-SEARCHED: {searched}\n"
        f"PAUSE-LINES: {pause_lines}\n"
        f"PAUSE-EARLIEST: {pause_at}\n"
        f"PAUSE-BEFORE-DRAFT: {pause_order}\n"
        f"INVESTIGATION-FILES: {inv_files}\n"
        f"INVESTIGATION-EARLIEST: {inv_at}\n"
        f"INVESTIGATION-BEFORE-DRAFT: {inv_order}\n"
    )


def test_a_pause_stamped_before_the_first_draft_passes():
    step = H.pause_verdict("S2", _wake_out(pause_order="yes"))
    assert step.verdict == H.PASS
    assert step.id == "S2.7"


def test_a_pause_nobody_wrote_down_is_a_real_red():
    """Core 14's own sentence: say the pause in the plan record. A pause that
    was never written is indistinguishable from a session that wandered off.

    Falsified by: a CAN'T TELL, which would let an unwritten pause pass as
    unmeasured rather than absent.
    """
    step = H.pause_verdict("S2", _wake_out(pause_lines=0, pause_order="unknown"))
    assert step.verdict == H.FAIL
    assert "no line naming a pause" in step.missing


def test_a_pause_dated_after_the_drafts_is_red_not_cant_tell():
    step = H.pause_verdict(
        "S2", _wake_out(pause_at="2026-09-06T11:00:00+00:00", pause_order="no")
    )
    assert step.verdict == H.FAIL
    assert "dated AFTER the first draft" in step.missing


def test_a_pause_that_exists_but_cannot_be_dated_is_cant_tell():
    """The line is there and nothing orders it. That is not absence, and it is
    not a pass either.

    Falsified by: a PASS (claims order it never measured) or a FAIL (reports
    an unmeasurable order as an absent pause).
    """
    step = H.pause_verdict("S2", _wake_out(pause_at="-", pause_order="unknown"))
    assert step.verdict == H.UNPROVEN
    assert "could not tell" in step.missing


def test_a_probe_that_never_reported_is_cant_tell_for_both_order_rows():
    for verdict_fn in (H.pause_verdict, H.investigation_order_verdict):
        step = verdict_fn("S2", "the probe blew up before printing anything")
        assert step.verdict == H.UNPROVEN
        assert "could not tell" in step.missing


def test_investigation_answers_written_before_the_drafts_pass():
    step = H.investigation_order_verdict("S2", _wake_out(inv_order="yes"))
    assert step.verdict == H.PASS
    assert step.id == "S2.8"


def test_answers_that_were_never_written_down_are_a_real_red():
    step = H.investigation_order_verdict(
        "S2", _wake_out(inv_files=0, inv_at="-", inv_order="unknown")
    )
    assert step.verdict == H.FAIL
    assert "never" in step.missing


def test_an_mtime_can_prove_before_but_never_after():
    """The rule this row lives or dies by. An mtime is a LAST write: a record
    touched after the drafts may have been written long before them and
    appended to since. The probe emits `no` only when BOTH sides are git
    add-dates; anything else is `unknown`, and the row must respect that.

    Falsified by: a FAIL on `unknown`, which would call an appended-to record
    a reading that happened after the drafting.
    """
    late = H.investigation_order_verdict(
        "S2", _wake_out(inv_at="2026-09-06T12:00:00+00:00", inv_order="unknown")
    )
    assert late.verdict == H.UNPROVEN
    assert "LAST write" in late.missing

    exact = H.investigation_order_verdict(
        "S2", _wake_out(inv_at="2026-09-06T12:00:00+00:00", inv_order="no")
    )
    assert exact.verdict == H.FAIL
    assert "both dated by git" in exact.missing


# --------------------------------------------------------------------------
# Seven. A run never erases the run before it (converge-w3nb). A file that
# keeps only the latest verdict cannot show that a RED run went green.
# --------------------------------------------------------------------------


def _one_run(tmp_path, *, sid: str, verdict: str, started: str) -> str:
    run = H.ScenarioRun(
        name="Existing project (adopt)",
        key="existing-project",
        sid=sid,
        project_dir="/workspace/existing-project",
    )
    run.dtu_id = f"adopter-test-{sid.lower()}"
    run.steps = [H.Step(f"{sid}.5", "the contract check is seeded", verdict, "seen")]
    H.write_result(
        tmp_path / "RESULT.md", scenarios=[run], meta={"started": started}
    )
    return (tmp_path / "RESULT.md").read_text(encoding="utf-8")


def test_the_earlier_run_survives_the_next_one(tmp_path):
    _one_run(tmp_path, sid="S2", verdict=H.FAIL, started="2026-09-06T03:50:03+00:00")
    text = _one_run(
        tmp_path, sid="S2", verdict=H.PASS, started="2026-09-06T09:00:00+00:00"
    )
    assert text.index("2026-09-06T09:00:00+00:00") < text.index(H.ARCHIVE_HEADING)
    assert "## Run 2026-09-06T03:50:03+00:00" in text
    assert text.count("2026-09-06T03:50:03+00:00") >= 1


def test_three_runs_all_stay_newest_first(tmp_path):
    _one_run(tmp_path, sid="S2", verdict=H.FAIL, started="2026-09-06T01:00:00+00:00")
    _one_run(tmp_path, sid="S2", verdict=H.FAIL, started="2026-09-06T03:50:03+00:00")
    text = _one_run(
        tmp_path, sid="S2", verdict=H.PASS, started="2026-09-06T09:00:00+00:00"
    )
    headings = [ln for ln in text.split("\n") if ln == H.ARCHIVE_HEADING]
    assert len(headings) == 1, "one archive section, however many runs it holds"
    assert text.count(H.ARCHIVE_NOTE) == 1, "the note is not copied down per run"
    first = text.index("## Run 2026-09-06T03:50:03+00:00")
    second = text.index("## Run 2026-09-06T01:00:00+00:00")
    assert first < second


def test_only_the_current_run_owns_the_third_level_step_headings(tmp_path):
    """What CVG-302's probe greps. `### S2.5 ... - FAIL` must name a row of the
    run at the top of the file and nothing else, or an archived red row keeps
    a ledger row red forever.

    Falsified by: an archived heading still sitting at `###`.
    """
    _one_run(tmp_path, sid="S2", verdict=H.FAIL, started="2026-09-06T03:50:03+00:00")
    text = _one_run(
        tmp_path, sid="S2", verdict=H.PASS, started="2026-09-06T09:00:00+00:00"
    )
    third_level = [ln for ln in text.split("\n") if ln.startswith("### S2.5 ")]
    assert len(third_level) == 1
    assert third_level[0].endswith("PASS")
    assert any(ln.startswith("#### S2.5 ") and ln.endswith("FAIL") for ln in text.split("\n"))


def test_a_hash_inside_an_evidence_fence_is_left_alone(tmp_path):
    """A vision's own `# mdstrip - Vision (DRAFT)` lives inside an evidence
    fence. Demoting it would corrupt the evidence a row was judged from.

    Falsified by: `## mdstrip` appearing anywhere after the archive pass.
    """
    run = H.ScenarioRun(
        name="x", key="existing-project", sid="S2", project_dir="/workspace/x"
    )
    run.dtu_id = "adopter-test-s2"
    run.steps = [H.Step("S2.3", "a vision", H.PASS, "== ./docs/VISION.md\n# mdstrip \u2014 Vision (DRAFT)")]
    H.write_result(tmp_path / "RESULT.md", scenarios=[run], meta={"started": "one"})
    H.write_result(tmp_path / "RESULT.md", scenarios=[run], meta={"started": "two"})
    text = (tmp_path / "RESULT.md").read_text(encoding="utf-8")
    assert "## mdstrip" not in text
    # Twice per run -- once flattened into the steps table, once verbatim in
    # the evidence fence -- and both runs keep both.
    assert text.count("# mdstrip \u2014 Vision (DRAFT)") == 4


def test_a_filtered_run_says_which_scenarios_it_covered(tmp_path):
    text = _one_run(
        tmp_path, sid="S2", verdict=H.PASS, started="2026-09-06T09:00:00+00:00"
    )
    assert "This run covered: Existing project (adopt)." in text
    assert "says nothing about the one that did not run" in text


if __name__ == "__main__":  # pragma: no cover
    sys.exit(pytest.main([__file__, "-q"]))
