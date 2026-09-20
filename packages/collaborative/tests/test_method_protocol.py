"""Regression checks for shipped guidance, never a live-model conformance claim.

These fail when key refusal/authority boundaries are lost from the distributed
resources. Execution and custody enforcement belong to the runtime/Queue tests.
"""
from importlib.resources import files
from pathlib import Path
import re


ROOT = files("converge_instructions")
MANAGER = " ".join(ROOT.joinpath("instructions/manager.md").read_text().split())
SUPERVISOR = " ".join(ROOT.joinpath("bundle/bundle.md").read_text().split())
PACKAGE = Path(__file__).resolve().parents[1]
MAPPING = (PACKAGE / "METHOD-PROTOCOL.md").read_text()


def require_all(text, fragments):
    for fragment in fragments:
        assert fragment in text, f"Missing guidance boundary: {fragment}"


def test_canonical_map_covers_live_promises_without_reusing_retired_numbers():
    for contract, numbers in {
        "operation.v1": {1, 2, 3, 10, 11},
        "lanes.v1": set(range(1, 7)),
        "wake.v1": set(range(1, 8)),
    }.items():
        rows = re.findall(rf"^\| {re.escape(contract)}:(\d+) \|", MAPPING, re.M)
        assert len(rows) == len(numbers)
        assert {int(n) for n in rows} == numbers
    assert "draft worked reading" in MAPPING
    assert "not a new contract or a" in MAPPING


def test_plan_and_source_precede_real_isolated_lane_launch():
    require_all(MANAGER, (
        "the steward's exact words and where they were given",
        "Write the durable, visible plan before launching work",
        "Read back the stored plan and retain its receipt",
        "its own working copy, its own named branch and its own native session",
        "second session sharing the product working copy, is not a lane",
        "stop that launch; do not substitute an untracked delegate",
    ))
    assert MANAGER.index("Write the durable, visible plan") < MANAGER.index("## 2.")


def test_brief_has_nine_parts_and_a_permitted_outside_marker():
    parts = (
        "what the lane is;", "what to read first;", "the quoted gap;",
        "the honesty gate;", "exact ownership and off-limits paths;",
        "acceptance with evidence and falsifiers;",
        "the two transport exits and fixed stall number;",
        "its marker;", "its boundaries.",
    )
    positions = [MANAGER.index(part) for part in parts]
    assert positions == sorted(positions)
    require_all(MANAGER, (
        "not the manager conversation",
        "absolute marker path outside the working copy",
        "the worker is actually permitted to write",
        "The worker never edits manager-owned plans, checks, custody or closure records",
        "A filesystem or guard refusal is a boundary",
    ))


def test_failed_attempt_bound_cannot_be_reset_by_relabeling_or_healthy_polling():
    require_all(MANAGER, (
        "3 failed attempts against one target",
        "before launch",
        "same refusal is the next attempt, not a fresh target",
    ))
    assert "reaching the limit" in MANAGER.lower()
    require_all(MANAGER, (
        "Healthy waiting is separate from failed attempts",
        "checkpoint, deadline and route",
        "Repeated unchanged healthy polls do not spend the failure budget",
        "Required present checks still run; missing old evidence is reported as missing",
        "An explicit stop takes priority",
    ))


def test_required_sources_are_materialized_before_admission_without_history_rewrite():
    require_all(MANAGER, (
        '`{capability:"direction",document_id,revision}`',
        "exact current revision",
        "body, title, draft/settled state, project, revision and hash",
        "A document ID alone is not source material",
        "fail preflight before custody or an attempt is consumed",
        "or revise an already launched brief",
    ))
    assert "An exact retry keeps the original captured bytes" in MAPPING


def test_missing_worker_context_returns_stuck_without_private_source_discovery():
    require_all(MANAGER, (
        "exact scoped `converge_project` call shapes",
        "`operations.read`, `return_lane` and `record_attempt`",
        "including required outcome fields and stable request IDs",
        "return `stuck-with-cause`, name the missing material and route it to the manager",
        "Do not search host directories, package installations, caches, logs, native history or private databases",
        "General filesystem tools do not expand a lane's permitted reading boundary",
        "application policy, not a claim of OS sandbox enforcement",
    ))
    require_all(MANAGER, (
        "`brief.read_only:true` and `owned_paths:[]`",
        "Do not invent writable paths",
        "stays clean at its admitted base revision",
    ))


def test_worker_claim_is_never_manager_proof_or_final_closure():
    require_all(MANAGER, (
        "A worker's green is a claim",
        "run the acceptance commands yourself",
        "Do not copy worker output into a check",
        "after each landed change, in both directions",
        "Only close an item after the manager's required checks",
        "component checks do not prove whole-product or visual acceptance",
        "If integration is not authorized",
    ))
    assert MANAGER.index("5. `verify_lane`") < MANAGER.index("6. `close_item`")
    assert "then `verify_lane` again against the integration target" in MANAGER


def test_exact_domain_outcomes_and_wire_spellings_preserve_two_transport_exits():
    text = ROOT.joinpath("instructions/manager.md").read_text()
    endings = re.findall(r"^- \*\*([^*]+)\*\* —", text, re.M)
    assert endings == ["done with proof", "stuck with a named cause", "waiting on the steward"]
    require_all(MANAGER, (
        "`done-with-proof` → done with proof",
        "`stuck-with-cause` → stuck with a named cause",
        "`waiting-on-steward` → waiting on the steward",
        "`SUCCESS` maps only to the worker's",
        "`BLOCKED` maps to",
        "not extra domain outcomes",
        "what landed, what did not, evidence for each",
    ))


def test_four_decision_calls_leave_independent_work_running():
    section = MANAGER.split("## 6.", 1)[1].split("## 7.", 1)[0]
    calls = re.findall(r"\d\. \*\*([^*]+)\*\*", section)
    assert calls == ["ratify", "allow", "check", "priority"]
    require_all(section, (
        "record what continued",
        "Continue every independent authorized item",
        "not a fifth call",
        "Do not ask again for an already authorized action",
        "not human approval",
    ))


def test_protocol_names_match_the_coordinated_public_actions():
    for action in ("initialize_workspace", "file_item", "plan_wave", "run_lane", "return_lane", "verify_lane",
                   "integrate_lane", "close_item", "answer_call", "finish_wave", "record_attempt"):
        assert any(token in MANAGER for token in (f"`{action}`", f"`{action}:", f"`operations.{action}`"))
        assert f"| {action} |" in MAPPING
    require_all(MANAGER, (
        'source:{kind:"promise"|"steward",reference,text}',
        "`expected_target_head`", "`check_id`",
        "resolution:{what_is_live,what_changed,caveat,check}",
        "`allow_irreversible`", "`human_check`", "`priority_or_stop`",
    ))
    require_all(MANAGER, (
        "`record_attempt`", "per-target", "total admitted lane launches",
        "At the fixed limit it returns stuck",
        "optional `finish_wave`", "refuses until all lanes are closed",
    ))


def test_supervisor_uses_real_tools_and_keeps_product_work_with_manager():
    require_all(SUPERVISOR, (
        "Use the installed Smart Tools to manage the dedicated project manager",
        "Do not edit product files",
        "pass `require_wave: true`",
        "A read-only information request may remain a finite turn",
        "Inspect actual Operations records",
        "rather than repeating a start to poll",
        "The final report names actual wave, item, lane and manager-check IDs",
    ))


def test_upgrade_is_explicit_preserves_native_history_and_does_not_claim_live_proof():
    require_all(MANAGER, (
        "saved-hash-to-new-hash migration in the same native session",
        "do not clear history",
        "or replay old input",
        "no model-supplied project-complete flag",
    ))
    require_all(SUPERVISOR, (
        "Confirm it before an instruction upgrade",
        "actual instruction hash and tools",
    ))
    assert "Neither proves that a real model" in MAPPING
    assert "not this protocol's adoption" in MAPPING
