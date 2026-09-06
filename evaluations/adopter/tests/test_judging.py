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


if __name__ == "__main__":  # pragma: no cover
    sys.exit(pytest.main([__file__, "-q"]))
