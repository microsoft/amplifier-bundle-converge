"""Static coverage for manager guidance, not proof that an LLM follows it.

These tests guard the shipped wording and template boundaries. They cannot prove
runtime judgment, a real lane launch, or product acceptance.
"""

from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
MODE = (REPO / "modes" / "converge-manager.md").read_text(encoding="utf-8")
STALLS = (REPO / "context" / "manager" / "stalls.md").read_text(encoding="utf-8")
WAVE = (REPO / "context" / "manager" / "wave-record.md").read_text(encoding="utf-8")
GOAL = (REPO / "docs" / "workspace-template" / "GOAL-FILE.md.template").read_text(
    encoding="utf-8"
)
MANAGER_BRIEF = REPO / "docs" / "workspace-template" / "MANAGER-BRIEF.md.template"


def _normal(text: str) -> str:
    return " ".join(text.split())


def test_ended_work_gets_bounded_integration_priority_not_absolute_refill():
    assert "Integration has bounded priority over refill." in MODE
    assert "This explicitly overrides the `ten-lane-highway` refill-first ordering" in _normal(MODE)
    assert "Refill first if under width" not in MODE
    assert "finite integration pass" in MODE


def test_watchdog_is_advisory_and_healthy_wait_has_a_boundary():
    assert "highway watchdog is **advisory only**" in STALLS
    assert "`LIVE` is observation, not automatic resume" in _normal(STALLS)
    assert "Three identical healthy polls are not a stall" in _normal(STALLS)
    assert "health signal, checkpoint, deadline, and route" in _normal(STALLS)


def test_unchanged_wake_uses_a_short_path_without_erasing_requests():
    normalized = _normal(MODE)
    assert "On an unchanged wake, keep the existing picture" in normalized
    assert "Unknown state is investigation, never a cheap pass." in normalized
    assert "preserve the append-only record and advance a processed offset" in normalized


def test_portable_manager_brief_exists_and_marks_amplifier_preflight():
    assert MANAGER_BRIEF.is_file()
    text = MANAGER_BRIEF.read_text(encoding="utf-8")
    assert "**Amplifier preflight only:**" in text
    assert "`--mode converge-manager`" in text
    assert "full conversation does not provide missing capabilities" in _normal(text)


def test_lane_template_requires_shared_boundary_and_consumer_acceptance():
    for term in (
        "Producer:",
        "consumers:",
        "interface decision owner:",
        "version or fixture:",
        "incoming dependency:",
        "consumer acceptance:",
        "residual destination:",
        "Local success, consumer acceptance, and product acceptance",
    ):
        assert term in _normal(GOAL)


def test_transfer_record_has_scope_rights_receipt_and_stop_boundary():
    for term in (
        "offered; accepted, declined, or unaccepted; returned;",
        "exact scope and revision",
        "interface decision rights",
        "expected receipt",
        "reintegration owner",
        "explicit steward stop",
        "missing receipt is never permission",
    ):
        assert term in _normal(WAVE) or term in _normal(GOAL)


def test_failed_recovery_keeps_numeric_bound_and_compatible_stamp():
    for text in (MODE, STALLS):
        assert "**three no-progress attempts**" in text
        assert "Iterations without progress: 1" in text
        assert "Attempts: 1" not in text
        assert "immediate STOP" in text
        assert "Healthy changed results advance normal integration/reconciliation" in _normal(text)
    assert "or changed result triggers" not in _normal(STALLS)


def test_active_control_is_not_replaced_by_a_watchdog_or_stale_wake_promise():
    assert "make sure something will wake you" not in MODE
    assert "keep an active bounded wait/control path" in _normal(MODE)
    assert "a supported resumer verified for this session" in _normal(MODE)


def test_worker_reports_transfer_without_writing_manager_records():
    assert "The worker never edits manager-owned records" in _normal(GOAL)
    assert "the manager records it in the existing plan or return record" in _normal(GOAL)
    assert "If writing it is denied, stop the write" in _normal(GOAL)


def test_capacity_and_external_execution_scope_are_separate():
    assert "a cap constrains usable capacity, not whether work exists" in _normal(MODE)
    assert "An unaccepted offer remains locally accountable" in MODE
    text = MANAGER_BRIEF.read_text(encoding="utf-8")
    assert "authorized resource cap:" in text
    assert "Transferred execution scope/state:" in text