"""Unit tests for hooks-candidate-guard.

Follows docs/design/hooks-candidate-guard-spec.md §5.1 Test Plan (U1-U10).
All tests call the pure functions in ``guard.py`` directly with mock
``tool:pre`` data (HOOK_CONTRACT.md "Testing" pattern) -- no live session.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from amplifier_module_hooks_candidate_guard import mount
from amplifier_module_hooks_candidate_guard.guard import GuardConfig, evaluate_tool_pre
from amplifier_module_hooks_candidate_guard.guard import (
    _read_file_text as guard_read_file_text,  # noqa: F401 -- referenced for monkeypatch target below
)

FROZEN_STAMP = "**Status:** FROZEN\n\n"
RATIFIED_STAMP = "ratified by owner\n"


def _write(base: Path, rel: str, content: str) -> Path:
    p = base / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return p


def _config(**overrides) -> GuardConfig:
    return GuardConfig.from_dict(overrides)


# ---------------------------------------------------------------------------
# U1 -- path match
# ---------------------------------------------------------------------------


def test_u1_frozen_path_denied(tmp_path: Path) -> None:
    _write(tmp_path, "contracts/automation-file.v1.md", FROZEN_STAMP + "content")
    config = _config()

    decision = evaluate_tool_pre(
        "write_file",
        {"file_path": "contracts/automation-file.v1.md", "content": "new"},
        config,
        str(tmp_path),
    )

    assert decision.result.action == "deny"


def test_u1_unrelated_path_continues(tmp_path: Path) -> None:
    config = _config()

    decision = evaluate_tool_pre(
        "write_file",
        {"file_path": "src/foo.py", "content": "print(1)"},
        config,
        str(tmp_path),
    )

    assert decision.result.action == "continue"


# ---------------------------------------------------------------------------
# U2 -- frozen-marker gating (DRAFT writable, FROZEN blocked)
# ---------------------------------------------------------------------------


def test_u2_draft_without_marker_is_writable(tmp_path: Path) -> None:
    _write(tmp_path, "contracts/draft.md", "# Draft\n\nNo status stamp yet.\n")
    config = _config(require_frozen_marker=True)

    decision = evaluate_tool_pre(
        "write_file",
        {"file_path": "contracts/draft.md", "content": "more draft text"},
        config,
        str(tmp_path),
    )

    assert decision.result.action == "continue"


def test_u2_same_file_once_frozen_is_blocked(tmp_path: Path) -> None:
    path = _write(tmp_path, "contracts/draft.md", "# Draft\n\nNo status stamp yet.\n")
    config = _config(require_frozen_marker=True)

    # Stamp the file FROZEN (simulating the Freeze Bar being crossed).
    path.write_text(FROZEN_STAMP + "# Draft\n\nNow frozen.\n", encoding="utf-8")

    decision = evaluate_tool_pre(
        "write_file",
        {"file_path": "contracts/draft.md", "content": "an unratified direct edit"},
        config,
        str(tmp_path),
    )

    assert decision.result.action == "deny"


# ---------------------------------------------------------------------------
# U3 -- CANDIDATE allowance (always-allow beats guard, even with FROZEN stamp)
# ---------------------------------------------------------------------------


def test_u3_candidate_write_always_allowed(tmp_path: Path) -> None:
    # Even seeded with a FROZEN stamp, a CANDIDATE-*.md must never be blocked --
    # always_allow_globs is checked before the guarded-path test (spec §2.5).
    _write(
        tmp_path,
        "contracts/CANDIDATE-retry-policy.md",
        FROZEN_STAMP + "proposal text",
    )
    config = _config()

    decision = evaluate_tool_pre(
        "write_file",
        {
            "file_path": "contracts/CANDIDATE-retry-policy.md",
            "content": "revised proposal",
        },
        config,
        str(tmp_path),
    )

    assert decision.result.action == "continue"


# ---------------------------------------------------------------------------
# U4 -- block message shape
# ---------------------------------------------------------------------------


def test_u4_block_message_shape(tmp_path: Path) -> None:
    _write(tmp_path, "contracts/automation-file.v1.md", FROZEN_STAMP + "content")
    config = _config()

    decision = evaluate_tool_pre(
        "write_file",
        {"file_path": "contracts/automation-file.v1.md", "content": "new"},
        config,
        str(tmp_path),
    )

    result = decision.result
    assert result.action == "deny"
    assert result.reason is not None
    assert "contracts/automation-file.v1.md" in result.reason
    assert "PROTOCOL.md §5" in result.reason
    assert "CANDIDATE-" in result.reason
    assert result.user_message_level == "error"


# ---------------------------------------------------------------------------
# U5 -- escape hatch (ratified CANDIDATE)
# ---------------------------------------------------------------------------


def test_u5_ratified_candidate_allows_the_edit(tmp_path: Path) -> None:
    _write(tmp_path, "contracts/x.v1.md", FROZEN_STAMP + "old clause")
    _write(
        tmp_path,
        "contracts/CANDIDATE-x-amendment.md",
        "target: contracts/x.v1.md\n\nproposal...\n\n" + RATIFIED_STAMP,
    )
    config = _config()

    decision = evaluate_tool_pre(
        "write_file",
        {"file_path": "contracts/x.v1.md", "content": "amended clause"},
        config,
        str(tmp_path),
    )

    assert decision.result.action == "continue"
    assert any(name == "converge:guard_allowed_ratified" for name, _ in decision.events)


def test_u5_candidate_without_stamp_still_denies(tmp_path: Path) -> None:
    _write(tmp_path, "contracts/x.v1.md", FROZEN_STAMP + "old clause")
    _write(
        tmp_path,
        "contracts/CANDIDATE-x-amendment.md",
        "target: contracts/x.v1.md\n\nproposal, not yet ratified\n",
    )
    config = _config()

    decision = evaluate_tool_pre(
        "write_file",
        {"file_path": "contracts/x.v1.md", "content": "amended clause"},
        config,
        str(tmp_path),
    )

    assert decision.result.action == "deny"


def test_u5_ratified_candidate_targeting_different_file_still_denies(
    tmp_path: Path,
) -> None:
    _write(tmp_path, "contracts/x.v1.md", FROZEN_STAMP + "old clause")
    _write(
        tmp_path,
        "contracts/CANDIDATE-other-amendment.md",
        "target: contracts/other.v1.md\n\nproposal...\n\n" + RATIFIED_STAMP,
    )
    config = _config()

    decision = evaluate_tool_pre(
        "write_file",
        {"file_path": "contracts/x.v1.md", "content": "amended clause"},
        config,
        str(tmp_path),
    )

    assert decision.result.action == "deny"


# ---------------------------------------------------------------------------
# U6 -- apply_patch multi-file diff handling
# ---------------------------------------------------------------------------


def test_u6_apply_patch_multifile_diff_denied(tmp_path: Path) -> None:
    _write(tmp_path, "contracts/x.v1.md", FROZEN_STAMP + "old clause")
    config = _config()

    diff_body = (
        "*** Update File: contracts/x.v1.md\n"
        "@@\n"
        "-old\n"
        "+new\n"
        "*** Update File: other.md\n"
        "@@\n"
        "-a\n"
        "+b\n"
    )

    decision = evaluate_tool_pre(
        "apply_patch",
        {"type": "update_file", "path": "other.md", "diff": diff_body},
        config,
        str(tmp_path),
    )

    assert decision.result.action == "deny"
    assert decision.result.reason is not None
    assert "contracts/x.v1.md" in decision.result.reason


def test_u6_apply_patch_native_single_file_not_guarded_continues(
    tmp_path: Path,
) -> None:
    """The composed default (native engine) sends one file per call with no
    envelope markers in `diff` -- confirm the ordinary single-file path still
    behaves like a normal write check."""
    config = _config()

    decision = evaluate_tool_pre(
        "apply_patch",
        {"type": "update_file", "path": "src/foo.py", "diff": "@@\n-old\n+new\n"},
        config,
        str(tmp_path),
    )

    assert decision.result.action == "continue"


def test_u6_apply_patch_function_engine_patch_field_multifile_denied(
    tmp_path: Path,
) -> None:
    """If a repo opts apply_patch into the function engine, the multi-file
    V4A envelope arrives in the `patch` field instead of `diff` -- must be
    scanned too (see README T2 confirmation notes)."""
    _write(tmp_path, "contracts/x.v1.md", FROZEN_STAMP + "old clause")
    config = _config()

    patch_body = (
        "*** Begin Patch\n"
        "*** Update File: other.md\n"
        "@@\n-a\n+b\n"
        "*** Update File: contracts/x.v1.md\n"
        "@@\n-old\n+new\n"
        "*** End Patch\n"
    )

    decision = evaluate_tool_pre(
        "apply_patch",
        {"patch": patch_body},
        config,
        str(tmp_path),
    )

    assert decision.result.action == "deny"


# ---------------------------------------------------------------------------
# U7 -- bash scan matrix
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "command",
    [
        "echo x >> contracts/x.v1.md",
        "echo x > contracts/x.v1.md",
        "cat <<EOF > contracts/x.v1.md\nhello\nEOF",
        "echo x | tee contracts/x.v1.md",
        "sed -i 's/a/b/' contracts/x.v1.md",
        "cp /tmp/new.md contracts/x.v1.md",
        "mv /tmp/new.md contracts/x.v1.md",
    ],
    ids=[
        "redirect-append",
        "redirect-overwrite",
        "heredoc-redirect",
        "tee",
        "sed-i",
        "cp-into",
        "mv-into",
    ],
)
def test_u7_bash_write_laundering_denied(tmp_path: Path, command: str) -> None:
    _write(tmp_path, "contracts/x.v1.md", FROZEN_STAMP + "old clause")
    config = _config()

    decision = evaluate_tool_pre("bash", {"command": command}, config, str(tmp_path))

    assert decision.result.action == "deny", f"expected deny for: {command!r}"
    assert decision.result.reason is not None
    assert "via shell" in decision.result.reason


def test_u7_innocuous_bash_continues(tmp_path: Path) -> None:
    config = _config()

    decision = evaluate_tool_pre(
        "bash", {"command": "pytest -q"}, config, str(tmp_path)
    )

    assert decision.result.action == "continue"


def test_u7_documented_non_coverage_gap(tmp_path: Path) -> None:
    """Known, documented gap (spec §2.4): a `python -c` writer is NOT
    detected. This test asserts the gap explicitly rather than silently
    passing -- it documents the limitation, it does not fail the suite."""
    _write(tmp_path, "contracts/x.v1.md", FROZEN_STAMP + "old clause")
    config = _config()

    command = "python -c \"open('contracts/x.v1.md', 'w').write('x')\""
    decision = evaluate_tool_pre("bash", {"command": command}, config, str(tmp_path))

    # Documented non-coverage: this SHOULD be denied in an ideal world, but
    # the scanner cannot see through an arbitrary interpreter's own I/O.
    assert decision.result.action == "continue"


# ---------------------------------------------------------------------------
# U8 -- fail-closed on evaluation error
# ---------------------------------------------------------------------------


def test_u8_fail_closed_on_guarded_path_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write(tmp_path, "contracts/x.v1.md", FROZEN_STAMP + "old clause")
    config = _config(fail_closed_on_error=True)

    import amplifier_module_hooks_candidate_guard.guard as guard_module

    def _raise(_path: Path) -> str:
        raise OSError("simulated read failure")

    monkeypatch.setattr(guard_module, "_read_file_text", _raise)

    decision = evaluate_tool_pre(
        "write_file",
        {"file_path": "contracts/x.v1.md", "content": "new"},
        config,
        str(tmp_path),
    )

    assert decision.result.action == "deny"
    assert decision.result.reason is not None
    assert "guard evaluation error" in decision.result.reason


def test_u8_error_on_non_guarded_path_continues(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = _config(fail_closed_on_error=True)

    import amplifier_module_hooks_candidate_guard.guard as guard_module

    def _raise(_path: Path) -> str:
        raise OSError("simulated read failure")

    monkeypatch.setattr(guard_module, "_read_file_text", _raise)

    decision = evaluate_tool_pre(
        "write_file",
        {"file_path": "src/foo.py", "content": "new"},
        config,
        str(tmp_path),
    )

    assert decision.result.action == "continue"


# ---------------------------------------------------------------------------
# U9 -- within-cwd invariant
# ---------------------------------------------------------------------------


def test_u9_path_outside_cwd_is_out_of_scope(tmp_path: Path) -> None:
    config = _config()
    outside = str(tmp_path.parent / "outside-repo" / "contracts" / "x.v1.md")

    decision = evaluate_tool_pre(
        "write_file",
        {"file_path": outside, "content": "new"},
        config,
        str(tmp_path),
    )

    assert decision.result.action == "continue"


# ---------------------------------------------------------------------------
# U10 -- mount/cleanup
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_u10_mount_registers_on_tool_pre_and_cleanup_unregisters() -> None:
    coordinator = MagicMock()
    unregister_mock = MagicMock()
    coordinator.hooks.register = MagicMock(return_value=unregister_mock)
    coordinator.hooks.emit = AsyncMock()
    coordinator.get_capability = MagicMock(return_value=None)
    coordinator.register_contributor = MagicMock()

    cleanup = await mount(coordinator, {})

    coordinator.hooks.register.assert_called_once()
    args, kwargs = coordinator.hooks.register.call_args
    assert args[0] == "tool:pre"
    assert kwargs.get("priority") == 5
    assert kwargs.get("name") == "candidate-guard"

    assert callable(cleanup)
    cleanup()
    unregister_mock.assert_called_once()


# ---------------------------------------------------------------------------
# Bonus -- rule (b) ENCODE-before-implement (opt-in, not part of the required
# U1-U10 matrix, but exercised here since it's cheap and the spec describes
# it in full).
# ---------------------------------------------------------------------------


def test_rule_b_blocks_implementation_write_without_encode_marker(
    tmp_path: Path,
) -> None:
    config = _config(enforce_encode_before_impl=True)

    decision = evaluate_tool_pre(
        "write_file",
        {"file_path": "src/impl.py", "content": "code"},
        config,
        str(tmp_path),
    )

    assert decision.result.action == "deny"


def test_rule_b_allows_once_encode_marker_present(tmp_path: Path) -> None:
    _write(tmp_path, ".converge/encoded", "encoded at ...\n")
    config = _config(enforce_encode_before_impl=True)

    decision = evaluate_tool_pre(
        "write_file",
        {"file_path": "src/impl.py", "content": "code"},
        config,
        str(tmp_path),
    )

    assert decision.result.action == "continue"


def test_rule_b_off_by_default(tmp_path: Path) -> None:
    config = _config()  # enforce_encode_before_impl defaults False

    decision = evaluate_tool_pre(
        "write_file",
        {"file_path": "src/impl.py", "content": "code"},
        config,
        str(tmp_path),
    )

    assert decision.result.action == "continue"


# ---------------------------------------------------------------------------
# W1 -- both proposal names (contracts/composition.v1.md clause 7)
#
# A locked contract changes by proposal, never by direct edit. Two names are
# sanctioned: `<contract>.vN-candidate.md` (contracts/documents.v1 clause 8)
# and the legacy `CANDIDATE-*.md` (PROTOCOL.md §5). Every OTHER write to the
# locked file is refused, by person or agent.
#
# Acceptance items 1-4 of the lane goal map to the four scenarios below.
# ---------------------------------------------------------------------------


def _frozen_contract(tmp_path: Path) -> GuardConfig:
    """Seed a FROZEN contracts/x.v1.md and return the default config."""
    _write(tmp_path, "contracts/x.v1.md", FROZEN_STAMP + "the locked clause\n")
    return _config()


@pytest.mark.parametrize(
    ("tool_name", "tool_input"),
    [
        ("write_file", {"file_path": "contracts/x.v1.md", "content": "rewritten"}),
        (
            "edit_file",
            {
                "file_path": "contracts/x.v1.md",
                "old_string": "the locked clause",
                "new_string": "a different clause",
            },
        ),
    ],
    ids=["write_file", "edit_file"],
)
def test_w1_locked_contract_write_denied_on_both_tool_paths(
    tmp_path: Path, tool_name: str, tool_input: dict
) -> None:
    """Acceptance 1 -- FROZEN contracts/x.v1.md refuses a direct write.

    Both the write_file and edit_file paths are exercised: they are separate
    entries in ``intercept_tools`` and a guard that only covered one would
    leave the other as a silent hole.
    """
    config = _frozen_contract(tmp_path)

    decision = evaluate_tool_pre(tool_name, tool_input, config, str(tmp_path))

    assert decision.result.action == "deny"
    assert decision.result.reason is not None
    assert "contracts/x.v1.md" in decision.result.reason
    assert [e[0] for e in decision.events] == ["converge:guard_blocked"]

    # Ground truth: the guard is a gate, so the bytes on disk are untouched.
    assert (tmp_path / "contracts/x.v1.md").read_text() == (
        FROZEN_STAMP + "the locked clause\n"
    )


@pytest.mark.parametrize(
    "proposal_rel",
    ["contracts/x.v2-candidate.md", "contracts/CANDIDATE-x.md"],
    ids=["versioned", "legacy"],
)
def test_w1_proposal_beside_locked_contract_allowed(
    tmp_path: Path, proposal_rel: str
) -> None:
    """Acceptance 2 and 3 -- both proposal names are the sanctioned write.

    The proposal file is seeded ALREADY EXISTING and already carrying a
    FROZEN marker, which is the case that actually discriminates. A
    proposal's first part is "the exact change, sentence by sentence"
    (contracts/documents.v1 clause 8), so it routinely quotes the locked
    contract's own status line. Without the allowance the proposal file
    matches `contracts/*.md`, reads as frozen, and revising it gets denied —
    the guard would block the very artifact it demands. Writing to a path
    that does not exist yet proves nothing here: a missing file can never
    read as frozen, so it is admitted either way.
    """
    _write(tmp_path, proposal_rel, FROZEN_STAMP + "quoted from the locked contract\n")
    config = _frozen_contract(tmp_path)

    decision = evaluate_tool_pre(
        "write_file",
        {
            "file_path": proposal_rel,
            "content": "## The exact change\n## The evidence\n## What does NOT change\n",
        },
        config,
        str(tmp_path),
    )

    assert decision.result.action == "continue"


def test_w1_draft_contract_write_allowed(tmp_path: Path) -> None:
    """Acceptance 4 -- the guard keys on LOCKED, not on the path alone.

    `contracts/x.v1.md` in DRAFT is the same path as the frozen case above;
    only the status marker differs. Editing a DRAFT contract during ENCODE
    must stay ordinary work.
    """
    _write(tmp_path, "contracts/x.v1.md", "# Contract x — v1 (DRAFT)\n\nclause\n")
    config = _config()

    decision = evaluate_tool_pre(
        "write_file",
        {"file_path": "contracts/x.v1.md", "content": "revised draft"},
        config,
        str(tmp_path),
    )

    assert decision.result.action == "continue"


@pytest.mark.parametrize(
    "rel",
    [
        "contracts/x.v2-candidate.md",
        "contracts/x.v10-candidate.md",
        "contracts/composition.v2-candidate.md",
        "contracts/nested/deep/y.v3-candidate.md",
        "x.v2-candidate.md",
        "contracts/CANDIDATE-x.md",
        "CANDIDATE-topic.md",
        "contracts/nested/CANDIDATE-topic.md",
    ],
)
def test_w1_every_sanctioned_proposal_name_is_admitted(tmp_path: Path, rel: str) -> None:
    """Both names, at every depth, never blocked — even reading as frozen."""
    _write(tmp_path, rel, FROZEN_STAMP + "quoted clause\n")
    config = _frozen_contract(tmp_path)

    decision = evaluate_tool_pre(
        "write_file", {"file_path": rel, "content": "proposal"}, config, str(tmp_path)
    )

    assert decision.result.action == "continue", rel


@pytest.mark.parametrize(
    "rel",
    [
        "contracts/x.v1.md",  # the locked file itself
        "contracts/x.candidate.md",  # no version segment
        "contracts/x.v-candidate.md",  # 'vN' with no digit
        "contracts/x.v2-candidate.txt",  # not markdown
        "contracts/x.v2-candidates.md",  # near-miss suffix
        "contracts/candidate-x.md",  # lowercase legacy near-miss
    ],
)
def test_w1_near_miss_names_do_not_bypass_the_guard(tmp_path: Path, rel: str) -> None:
    """A name that merely LOOKS like a proposal must not unlock the guard.

    Every path here is checked against ``always_allow_globs`` and must fail
    it. Only ``contracts/x.v1.md`` is additionally guarded (it is the locked
    file), so it is the only one that denies; the rest are simply ordinary
    unguarded writes. The assertion that matters is that none of them is
    admitted *by the proposal allowance*.
    """
    from amplifier_module_hooks_candidate_guard.guard import _glob_match_any

    config = _frozen_contract(tmp_path)
    assert not _glob_match_any(rel, config.always_allow_globs), rel

    decision = evaluate_tool_pre(
        "write_file", {"file_path": rel, "content": "x"}, config, str(tmp_path)
    )
    expected = "deny" if rel == "contracts/x.v1.md" else "continue"
    assert decision.result.action == expected, rel


def test_w1_deny_message_names_both_proposal_names_and_the_three_parts(
    tmp_path: Path,
) -> None:
    """The deny message must name the escape hatch, not just the refusal.

    A block that does not tell the reader what to write instead is how an
    agent ends up retrying the same denied edit.
    """
    config = _frozen_contract(tmp_path)

    decision = evaluate_tool_pre(
        "write_file",
        {"file_path": "contracts/x.v1.md", "content": "rewritten"},
        config,
        str(tmp_path),
    )

    reason = decision.result.reason
    assert reason is not None
    # The concrete next filename, computed from the locked path.
    assert "contracts/x.v2-candidate.md" in reason
    # Both sanctioned names present.
    assert "<contract>.vN-candidate.md" in reason
    assert "CANDIDATE-<topic>.md" in reason
    # The three-part proposal shape (contracts/documents.v1 clause 8).
    assert "exact change" in reason
    assert "evidence" in reason
    assert "what does NOT change" in reason.replace("NOT", "NOT")
    # And the human-facing line names the remedy too.
    assert decision.result.user_message is not None
    assert "contracts/x.v2-candidate.md" in decision.result.user_message


def test_w1_proposal_name_suggestion_handles_vision_and_double_digits() -> None:
    from amplifier_module_hooks_candidate_guard.guard import _proposal_name_for

    assert _proposal_name_for("contracts/x.v1.md") == "contracts/x.v2-candidate.md"
    assert _proposal_name_for("contracts/x.v9.md") == "contracts/x.v10-candidate.md"
    assert _proposal_name_for("docs/VISION.md") == "docs/VISION.v2-candidate.md"


def test_w1_versioned_candidate_is_a_working_escape_hatch(tmp_path: Path) -> None:
    """A ratified `*.vN-candidate.md` lands the amendment, same as the legacy name.

    Admitting the new name only for writing the proposal, while the escape
    hatch still recognised the old name alone, would leave a ratified
    proposal unable to land.
    """
    config = _frozen_contract(tmp_path)
    _write(
        tmp_path,
        "contracts/x.v2-candidate.md",
        "target: contracts/x.v1.md\n\n"
        "## The exact change\n...\n"
        "## The evidence\na failure caught in production\n"
        "## What does NOT change\neverything else\n\n"
        "Ratified as edited — by owner\n",
    )

    decision = evaluate_tool_pre(
        "write_file",
        {"file_path": "contracts/x.v1.md", "content": "the amended clause"},
        config,
        str(tmp_path),
    )

    assert decision.result.action == "continue"
    assert decision.events == [
        (
            "converge:guard_allowed_ratified",
            {"path": "contracts/x.v1.md", "candidate": "contracts/x.v2-candidate.md"},
        )
    ]


def test_w1_unratified_versioned_candidate_does_not_unlock(tmp_path: Path) -> None:
    """Presence of a proposal is not ratification. Only the owner's word is."""
    config = _frozen_contract(tmp_path)
    _write(
        tmp_path,
        "contracts/x.v2-candidate.md",
        "target: contracts/x.v1.md\n\n## The exact change\n...\n",
    )

    decision = evaluate_tool_pre(
        "write_file",
        {"file_path": "contracts/x.v1.md", "content": "the amended clause"},
        config,
        str(tmp_path),
    )

    assert decision.result.action == "deny"


def test_w1_bash_laundering_into_locked_contract_still_denied(tmp_path: Path) -> None:
    """The two-name change must not open a shell-shaped hole (mirrors T6)."""
    config = _frozen_contract(tmp_path)

    decision = evaluate_tool_pre(
        "bash",
        {"command": "echo 'sneaky' >> contracts/x.v1.md"},
        config,
        str(tmp_path),
    )

    assert decision.result.action == "deny"
    assert decision.result.reason is not None
    assert "via shell" in decision.result.reason


def test_w1_bash_write_to_a_proposal_file_is_allowed(tmp_path: Path) -> None:
    """The shell scan honours the same allowance as the tool path."""
    config = _frozen_contract(tmp_path)

    decision = evaluate_tool_pre(
        "bash",
        {"command": "echo 'proposal' >> contracts/x.v2-candidate.md"},
        config,
        str(tmp_path),
    )

    assert decision.result.action == "continue"


# ---------------------------------------------------------------------------
# W1 -- glob translator character-class support (the mechanism the versioned
# proposal name depends on: 'vN' must require a real digit)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("pattern", "path", "expected"),
    [
        ("**/*.v[0-9]*-candidate.md", "contracts/x.v1-candidate.md", True),
        ("**/*.v[0-9]*-candidate.md", "contracts/x.v42-candidate.md", True),
        ("**/*.v[0-9]*-candidate.md", "x.v1-candidate.md", True),
        ("**/*.v[0-9]*-candidate.md", "contracts/x.vN-candidate.md", False),
        ("**/*.v[0-9]*-candidate.md", "contracts/x.v-candidate.md", False),
        ("[abc].md", "b.md", True),
        ("[abc].md", "d.md", False),
        ("[!abc].md", "d.md", True),
        ("[!abc].md", "a.md", False),
        # A character class never swallows a path separator.
        ("a[b/c]d.md", "a/d.md", False),
        # An unterminated '[' is a literal, not a crash.
        ("a[bc.md", "a[bc.md", True),
    ],
)
def test_w1_glob_character_classes(pattern: str, path: str, expected: bool) -> None:
    from amplifier_module_hooks_candidate_guard.guard import _glob_match_any

    assert _glob_match_any(path, [pattern]) is expected


# ---------------------------------------------------------------------------
# W3 -- the ratified locked marker, and the second write path
#
# Four reports, one cause: the guard's notion of "a locked contract" and "a
# proposal file" lagged the ratified anatomy, and one write path never reached
# the guard at all.
#
#   converge-diw  the H1 parenthetical `(FROZEN <date>)` -- the ONLY place
#                 contracts/documents.v1 clause 6 allows status to live -- was
#                 not a marker the guard recognised.
#   converge-ksg  the module default globs / deny message vs the new proposal
#                 name `<contract>.vN-candidate.md`.
#   converge-9vw  the shipped behaviors/ config vs that same name.
#   converge-ldz  `amplifier tool invoke` calls tools[name].execute() itself
#                 and never emits tool:pre, so no hook could see the write.
#
# W3a-W3c cover the marker and both proposal names; W3d covers the second
# write path.
# ---------------------------------------------------------------------------

H1_FROZEN = "# Probe Contract — v1 (FROZEN 2026-09-02)\n\n"
H1_DRAFT = "# Probe Contract — v1 (DRAFT)\n\n"
BEHAVIOR_YAML = (
    Path(__file__).resolve().parents[3] / "behaviors" / "converge.yaml"
)


# --- W3a: the H1 locked marker (converge-diw) ------------------------------


@pytest.mark.parametrize(
    ("tool_name", "tool_input"),
    [
        ("write_file", {"file_path": "contracts/x.v1.md", "content": "hijacked"}),
        (
            "edit_file",
            {
                "file_path": "contracts/x.v1.md",
                "old_string": "the locked clause",
                "new_string": "a different clause",
            },
        ),
    ],
    ids=["write_file", "edit_file"],
)
def test_w3a_h1_locked_contract_is_denied(
    tmp_path: Path, tool_name: str, tool_input: dict
) -> None:
    """converge-diw: `(FROZEN <date>)` in the H1 IS the locked marker.

    The file carries no `**Status:**` line at all -- exactly the anatomy
    contracts/documents.v1 clause 6 mandates and .githooks/pre-push checks.
    Before this fix the guard saw no marker and allowed the write.
    """
    _write(tmp_path, "contracts/x.v1.md", H1_FROZEN + "the locked clause\n")

    decision = evaluate_tool_pre(tool_name, tool_input, _config(), str(tmp_path))

    assert decision.result.action == "deny"
    reason = decision.result.reason or ""
    # The remedy names the versioned form, and the concrete path to write.
    assert "contracts/x.v2-candidate.md" in reason
    assert "<contract>.vN-candidate.md" in reason


def test_w3a_h1_draft_contract_stays_writable(tmp_path: Path) -> None:
    """`(DRAFT)` in the H1 is not a lock -- ENCODE must still be able to write."""
    _write(tmp_path, "contracts/x.v1.md", H1_DRAFT + "still being authored\n")

    decision = evaluate_tool_pre(
        "write_file",
        {"file_path": "contracts/x.v1.md", "content": "more drafting"},
        _config(),
        str(tmp_path),
    )

    assert decision.result.action == "continue"


@pytest.mark.parametrize(
    "marker",
    ["**Status:** FROZEN\n\n", "**Status:** RATIFIED\n\n", "status: FROZEN\n\n"],
    ids=["status-frozen", "status-ratified", "front-matter"],
)
def test_w3a_legacy_body_markers_still_detected(tmp_path: Path, marker: str) -> None:
    """Teaching the guard the H1 form must not un-teach it the legacy forms.

    A repo that locked a contract under the older convention would otherwise
    become silently writable on upgrade -- a regression in the direction that
    fails open.
    """
    _write(tmp_path, "contracts/x.v1.md", "# Legacy Contract\n\n" + marker + "text\n")

    decision = evaluate_tool_pre(
        "write_file",
        {"file_path": "contracts/x.v1.md", "content": "hijacked"},
        _config(),
        str(tmp_path),
    )

    assert decision.result.action == "deny"


def test_w3a_module_default_matches_the_shipped_behavior_config(tmp_path: Path) -> None:
    """Drift tripwire (converge-diw + converge-9vw's shared cause).

    The four reports exist because guard.py's defaults and the shipped
    behaviors/converge.yaml config disagreed about what "locked" and
    "proposal" mean. Assert they cannot silently diverge again.
    """
    import re as _re

    text = BEHAVIOR_YAML.read_text(encoding="utf-8")
    config = _config()

    m = _re.search(r"^\s*frozen_marker_regex:\s*'(.+)'\s*$", text, _re.MULTILINE)
    assert m, "behaviors/converge.yaml no longer sets frozen_marker_regex"
    assert m.group(1) == config.frozen_marker_regex

    for key in ("always_allow_globs", "candidate_glob"):
        m = _re.search(rf"^\s*{key}:\s*\[(.+)\]\s*$", text, _re.MULTILINE)
        assert m, f"behaviors/converge.yaml no longer sets {key}"
        shipped = {v.strip().strip("\"'") for v in m.group(1).split(",")}
        assert shipped == set(getattr(config, key))


# --- W3b: both proposal names beside an H1-locked contract (ksg / 9vw) ------


@pytest.mark.parametrize(
    "rel",
    ["contracts/x.v2-candidate.md", "contracts/CANDIDATE-x.md"],
    ids=["versioned", "legacy"],
)
def test_w3b_proposal_beside_h1_locked_contract_is_allowed(
    tmp_path: Path, rel: str
) -> None:
    """Both sanctioned names are writable beside an H1-locked contract.

    The proposal is seeded already carrying the locked H1 -- a proposal quotes
    the contract's own text, status line included, so it reads as locked
    itself. Writing to a path that does not exist yet would prove nothing.
    """
    _write(tmp_path, "contracts/x.v1.md", H1_FROZEN + "the locked clause\n")
    _write(tmp_path, rel, H1_FROZEN + "quoting the locked H1\n")

    decision = evaluate_tool_pre(
        "write_file",
        {"file_path": rel, "content": "target: contracts/x.v1.md\n"},
        _config(),
        str(tmp_path),
    )

    assert decision.result.action == "continue"


def test_w3b_ratified_versioned_proposal_unlocks_an_h1_locked_contract(
    tmp_path: Path,
) -> None:
    """The escape hatch works under the H1 marker AND the versioned name.

    Both halves of converge-ksg in one assertion: admitting the new name for
    *writing* a proposal, while the escape hatch recognised only the old one,
    would leave a ratified proposal unable to land.
    """
    _write(tmp_path, "contracts/x.v1.md", H1_FROZEN + "the locked clause\n")
    _write(
        tmp_path,
        "contracts/x.v2-candidate.md",
        "target: contracts/x.v1.md\n\n# The exact change\n...\n",
    )
    config = _config()
    edit = ("write_file", {"file_path": "contracts/x.v1.md", "content": "amended"})

    # Unratified -> still denied.
    assert evaluate_tool_pre(*edit, config, str(tmp_path)).result.action == "deny"

    # The owner's literal stamp -> the amendment lands.
    _write(
        tmp_path,
        "contracts/x.v2-candidate.md",
        "target: contracts/x.v1.md\n\n# The exact change\n...\n\n" + RATIFIED_STAMP,
    )
    decision = evaluate_tool_pre(*edit, config, str(tmp_path))
    assert decision.result.action == "continue"
    assert decision.events[0][0] == "converge:guard_allowed_ratified"
    assert decision.events[0][1]["candidate"] == "contracts/x.v2-candidate.md"


# --- W3c: bash laundering under the H1 marker -------------------------------


def test_w3c_bash_laundering_into_an_h1_locked_contract_is_denied(
    tmp_path: Path,
) -> None:
    _write(tmp_path, "contracts/x.v1.md", H1_FROZEN + "the locked clause\n")

    decision = evaluate_tool_pre(
        "bash",
        {"command": "echo hijacked > contracts/x.v1.md"},
        _config(),
        str(tmp_path),
    )

    assert decision.result.action == "deny"
    assert "via shell" in (decision.result.reason or "")


# --- W3d: the second write path -- direct dispatch (converge-ldz) -----------
#
# MEASURED, not inferred (2026-09-02): in the session `amplifier tool invoke`
# builds, `candidate-guard` IS registered on tool:pre -- and the write lands
# anyway, because the CLI calls `tools[name].execute(args)` itself and no
# tool:pre is ever emitted. No hook on that event can see it. The guard
# therefore also wraps the mounted tool instances' own execute().


class _FakeTool:
    """Minimal stand-in for a mounted tool: `async execute(input: dict)`."""

    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def execute(self, input: dict) -> dict:  # noqa: A002 -- matches the real signature
        self.calls.append(input)
        return {"file_path": input.get("file_path"), "bytes": 8}


def _wrapped_tools(config: GuardConfig, cwd: str) -> tuple[dict, list]:
    from amplifier_module_hooks_candidate_guard import wrap_mounted_tools

    tools = {"write_file": _FakeTool(), "edit_file": _FakeTool(), "bash": _FakeTool()}
    restored = wrap_mounted_tools(tools, config, cwd)
    return tools, restored


async def test_w3d_direct_execute_on_a_locked_contract_raises(tmp_path: Path) -> None:
    """The write must not land, and the refusal must be loud.

    A returned error dict would be indistinguishable from a successful write
    to a caller that does not inspect it; `amplifier tool invoke` prints a
    raised exception and exits non-zero.
    """
    from amplifier_module_hooks_candidate_guard import CandidateGuardBlocked

    _write(tmp_path, "contracts/x.v1.md", H1_FROZEN + "the locked clause\n")
    tools, _ = _wrapped_tools(_config(), str(tmp_path))

    with pytest.raises(CandidateGuardBlocked) as excinfo:
        await tools["write_file"].execute(
            {"file_path": "contracts/x.v1.md", "content": "hijacked"}
        )

    assert "contracts/x.v2-candidate.md" in str(excinfo.value)
    # The underlying tool was never reached -- not called and then undone.
    assert tools["write_file"].calls == []


async def test_w3d_direct_execute_passes_through_an_unguarded_write(
    tmp_path: Path,
) -> None:
    """The wrapper must not become a second, broader guard."""
    tools, _ = _wrapped_tools(_config(), str(tmp_path))

    result = await tools["write_file"].execute(
        {"file_path": "notes.md", "content": "ordinary"}
    )

    assert result == {"file_path": "notes.md", "bytes": 8}
    assert tools["write_file"].calls == [{"file_path": "notes.md", "content": "ordinary"}]


async def test_w3d_direct_execute_allows_a_proposal_and_a_draft(tmp_path: Path) -> None:
    _write(tmp_path, "contracts/x.v1.md", H1_FROZEN + "the locked clause\n")
    _write(tmp_path, "contracts/x.v2-candidate.md", H1_FROZEN + "quoting\n")
    _write(tmp_path, "contracts/draft.v1.md", H1_DRAFT + "authoring\n")
    tools, _ = _wrapped_tools(_config(), str(tmp_path))

    for rel in ("contracts/x.v2-candidate.md", "contracts/draft.v1.md"):
        assert await tools["write_file"].execute({"file_path": rel, "content": "x"})


async def test_w3d_direct_execute_denies_bash_laundering(tmp_path: Path) -> None:
    from amplifier_module_hooks_candidate_guard import CandidateGuardBlocked

    _write(tmp_path, "contracts/x.v1.md", H1_FROZEN + "the locked clause\n")
    tools, _ = _wrapped_tools(_config(), str(tmp_path))

    with pytest.raises(CandidateGuardBlocked):
        await tools["bash"].execute({"command": "echo x > contracts/x.v1.md"})
    assert tools["bash"].calls == []


def test_w3d_wrapping_is_opt_outable_and_idempotent(tmp_path: Path) -> None:
    """Removal control + double-mount safety.

    Off: nothing is touched, so the pre-fix behaviour (the write lands) is
    exactly recoverable. On, twice: wrapped once, so unwrap is not
    order-dependent and the evaluator does not run twice per call.
    """
    from amplifier_module_hooks_candidate_guard import wrap_mounted_tools

    # NB: `instance.execute` builds a NEW bound-method object on every access,
    # so identity against a previously-read attribute proves nothing. The
    # marker the wrapper stamps is the honest signal.
    def _is_wrapped(t) -> bool:
        return getattr(t.execute, "__converge_candidate_guard_wrapped__", False)

    tools = {"write_file": _FakeTool()}

    assert wrap_mounted_tools(tools, _config(wrap_tool_execute=False), str(tmp_path)) == []
    assert not _is_wrapped(tools["write_file"])

    first = wrap_mounted_tools(tools, _config(), str(tmp_path))
    assert len(first) == 1
    assert _is_wrapped(tools["write_file"])
    wrapped_once = tools["write_file"].execute
    assert wrap_mounted_tools(tools, _config(), str(tmp_path)) == []
    assert tools["write_file"].execute is wrapped_once


def test_w3d_a_tool_that_cannot_be_wrapped_does_not_break_the_guard(
    tmp_path: Path,
) -> None:
    """A slotted/read-only tool must degrade to tool:pre-only, never crash.

    Silent degradation is the failure mode this whole lane is about, so the
    module logs a warning naming the tool; the assertion here is only that
    mounting survives and the wrappable tools are still wrapped.
    """
    from amplifier_module_hooks_candidate_guard import wrap_mounted_tools

    class _Unwrappable:
        __slots__ = ()

        async def execute(self, input: dict) -> dict:  # noqa: A002
            return {}

    tools = {"write_file": _Unwrappable(), "edit_file": _FakeTool()}
    restored = wrap_mounted_tools(tools, _config(), str(tmp_path))

    assert len(restored) == 1
    assert restored[0][0] is tools["edit_file"]


async def test_w3d_mount_wraps_the_mounted_tools_and_cleanup_restores_them(
    tmp_path: Path,
) -> None:
    """End-to-end through mount(): the real wiring, not just the helper.

    Mount order makes this safe -- amplifier_core/_session_init.py mounts
    `tools` before `hooks`, so every tool instance already exists in the
    coordinator when this hook mounts.
    """
    from amplifier_module_hooks_candidate_guard import CandidateGuardBlocked

    _write(tmp_path, "contracts/x.v1.md", H1_FROZEN + "the locked clause\n")
    tool = _FakeTool()

    coordinator = MagicMock()
    coordinator.hooks.register = MagicMock(return_value=MagicMock())
    coordinator.hooks.emit = AsyncMock()
    coordinator.get = MagicMock(
        side_effect=lambda key: {"write_file": tool} if key == "tools" else None
    )
    coordinator.get_capability = MagicMock(return_value=str(tmp_path))

    cleanup = await mount(coordinator, {})

    assert getattr(tool.execute, "__converge_candidate_guard_wrapped__", False)
    with pytest.raises(CandidateGuardBlocked):
        await tool.execute({"file_path": "contracts/x.v1.md", "content": "hijacked"})
    assert tool.calls == []  # the tool was never reached

    cleanup()
    assert not getattr(tool.execute, "__converge_candidate_guard_wrapped__", False)
    # Restored means restored: the same write now reaches the tool.
    assert await tool.execute({"file_path": "contracts/x.v1.md", "content": "x"})
    assert len(tool.calls) == 1


# ---------------------------------------------------------------------------
# W4 -- the validation trial-mount, and the RATIFIED H1 marker
#
# Two reports, two independent causes, both of them silent-in-the-wrong-
# direction:
#
#   converge-drz  mount() is called TWICE. Core's HookValidator trial-mounts
#                 every hook module against a tool-less MockCoordinator before
#                 the real mount, so the "no mounted tools visible" warning
#                 fired on EVERY launch -- telling the user a safety property
#                 was OFF while the real mount was guarding as designed.
#   converge-dwi  the frozen-marker regex accepted `**Status:** RATIFIED` in
#                 the body but only `(FROZEN` in the H1, so the SAME status
#                 word read as locked in one place and unlocked in the other
#                 -- and the H1 is the form contracts/documents.v1 clause 6
#                 mandates. docs/PROTOCOL.md is the live instance.
#
# W4a covers the trial-mount; W4b the marker; W4c the glob coverage.
# ---------------------------------------------------------------------------

H1_RATIFIED = "# Probe Contract — v3 (RATIFIED 2026-09-03)\n\n"

REPO_ROOT = Path(__file__).resolve().parents[3]


def _quiet_coordinator(tools: dict | None) -> MagicMock:
    """A NON-mock-typed coordinator exposing ``tools`` -- the real-mount shape."""
    coordinator = MagicMock()
    coordinator.hooks.register = MagicMock(return_value=MagicMock())
    coordinator.hooks.emit = AsyncMock()
    coordinator.get = MagicMock(side_effect=lambda key: tools if key == "tools" else None)
    coordinator.get_capability = MagicMock(return_value=None)
    return coordinator


def _warnings(caplog) -> list[str]:
    return [r.getMessage() for r in caplog.records if r.levelno >= logging.WARNING]


def _tools_wrapped(caplog) -> int:
    """Read the count out of mount()'s own INFO line -- the same string a
    `-v` run shows the user, not a private attribute invented for the test."""
    for record in caplog.records:
        m = re.search(r"tools_wrapped=(\d+)", record.getMessage())
        if m:
            return int(m.group(1))
    raise AssertionError("mount() logged no tools_wrapped= line")


# --- W4a: no false-positive warning under the validation mock (converge-drz) -


async def test_w4a_mount_against_the_validation_mock_logs_no_warning(caplog) -> None:
    """The exact call core makes: `mount_fn(MockCoordinator(), config)`.

    Falsified by any WARNING record. The real MockCoordinator is used, not a
    stand-in -- the whole defect was a wrong assumption about what core does.
    """
    from amplifier_core.testing import MockCoordinator

    caplog.set_level(logging.DEBUG, logger="amplifier_module_hooks_candidate_guard")
    coordinator = MockCoordinator()

    cleanup = await mount(coordinator, {})

    assert _warnings(caplog) == []
    assert _tools_wrapped(caplog) == 0  # honest: the mock really has no tools
    cleanup()


async def test_w4a_a_real_coordinator_with_no_tools_still_warns(caplog) -> None:
    """Removal control. The fix must silence the FALSE positive only.

    A coordinator that is not the validation mock and genuinely exposes no
    tools is the case the warning exists for; if this went quiet too, the fix
    would have deleted the diagnostic rather than corrected it.
    """
    caplog.set_level(logging.DEBUG, logger="amplifier_module_hooks_candidate_guard")

    cleanup = await mount(_quiet_coordinator({}), {})

    assert any("no mounted tools visible" in w for w in _warnings(caplog))
    cleanup()


def test_w4a_the_mock_is_recognised_by_type_not_by_an_empty_tool_dict() -> None:
    """`is_validation_mock` must not infer the mock from "no tools".

    "No tools" is precisely the condition the warning reports, so inferring
    the mock from it would silence the genuine case (the test above) too.
    """
    from amplifier_core.testing import MockCoordinator
    from amplifier_module_hooks_candidate_guard import is_validation_mock

    assert is_validation_mock(MockCoordinator()) is True
    assert is_validation_mock(_quiet_coordinator({})) is False
    assert is_validation_mock(object()) is False


async def test_w4a_mount_wraps_every_registered_tool(caplog) -> None:
    """`tools_wrapped == N` for a coordinator carrying N tools.

    The four are the four the reporter measured on the real mount
    (`tools_wrapped=4`: apply_patch, bash, edit_file, write_file). Falsified
    by any other count -- including by a fix that suppressed the warning by
    skipping the wrap.
    """
    caplog.set_level(logging.DEBUG, logger="amplifier_module_hooks_candidate_guard")
    tools = {
        name: _FakeTool()
        for name in ("write_file", "edit_file", "apply_patch", "bash")
    }

    cleanup = await mount(_quiet_coordinator(tools), {})

    assert _tools_wrapped(caplog) == len(tools)
    assert _warnings(caplog) == []
    for tool in tools.values():
        assert getattr(tool.execute, "__converge_candidate_guard_wrapped__", False)
    cleanup()


# --- W4b: `(RATIFIED <date>)` in the H1 is a lock (converge-dwi) -------------


@pytest.mark.parametrize(
    ("tool_name", "tool_input"),
    [
        ("write_file", {"file_path": "docs/PROTOCOL.md", "content": "hijacked"}),
        (
            "edit_file",
            {
                "file_path": "docs/PROTOCOL.md",
                "old_string": "the ratified clause",
                "new_string": "a different clause",
            },
        ),
    ],
    ids=["write_file", "edit_file"],
)
def test_w4b_h1_ratified_document_is_locked(
    tmp_path: Path, tool_name: str, tool_input: dict
) -> None:
    """The live shape of docs/PROTOCOL.md: `(RATIFIED <date>)` in the H1 and
    no `**Status:**` line anywhere. Before this fix the guard saw no marker
    at all and allowed the write."""
    _write(tmp_path, "docs/PROTOCOL.md", H1_RATIFIED + "the ratified clause\n")

    decision = evaluate_tool_pre(tool_name, tool_input, _config(), str(tmp_path))

    assert decision.result.action == "deny"


def test_w4b_sibling_proposal_beside_a_ratified_document_is_allowed(
    tmp_path: Path,
) -> None:
    """A locked document must still be amendable by proposal -- otherwise the
    guard is a wall, not a ratchet. The proposal is seeded already carrying
    the locked H1 (a proposal quotes the document it amends, status line
    included), which is the case that actually discriminates."""
    _write(tmp_path, "docs/PROTOCOL.md", H1_RATIFIED + "the ratified clause\n")
    _write(tmp_path, "docs/PROTOCOL.v4-candidate.md", H1_RATIFIED + "quoting\n")

    decision = evaluate_tool_pre(
        "write_file",
        {
            "file_path": "docs/PROTOCOL.v4-candidate.md",
            "content": "target: docs/PROTOCOL.md\n",
        },
        _config(),
        str(tmp_path),
    )

    assert decision.result.action == "continue"


def test_w4b_a_ratified_proposal_unlocks_a_ratified_document(tmp_path: Path) -> None:
    """End of the round trip: proposal written, owner stamps it, edit lands."""
    _write(tmp_path, "docs/PROTOCOL.md", H1_RATIFIED + "the ratified clause\n")
    _write(
        tmp_path,
        "docs/PROTOCOL.v4-candidate.md",
        "target: docs/PROTOCOL.md\n\n" + RATIFIED_STAMP,
    )

    decision = evaluate_tool_pre(
        "write_file",
        {"file_path": "docs/PROTOCOL.md", "content": "the amended clause"},
        _config(),
        str(tmp_path),
    )

    assert decision.result.action == "continue"
    assert [name for name, _ in decision.events] == ["converge:guard_allowed_ratified"]


@pytest.mark.parametrize(
    ("content", "expected"),
    [
        ("# Probe — v1 (FROZEN 2026-09-02)\n\ntext\n", "deny"),
        ("# Probe — v3 (RATIFIED 2026-09-03)\n\ntext\n", "deny"),
        ("# Probe\n\n**Status:** FROZEN\n\ntext\n", "deny"),
        ("# Probe\n\n**Status:** RATIFIED\n\ntext\n", "deny"),
        ("# Probe\n\nstatus: FROZEN\n\ntext\n", "deny"),
        ("# Probe — v1 (DRAFT)\n\ntext\n", "continue"),
    ],
    ids=[
        "h1-frozen",
        "h1-ratified",
        "body-status-frozen",
        "body-status-ratified",
        "front-matter",
        "h1-draft",
    ],
)
def test_w4b_every_marker_form_keeps_its_verdict(
    tmp_path: Path, content: str, expected: str
) -> None:
    """Teaching the H1 branch RATIFIED must not un-teach it anything else.

    All six forms in one table: the two H1 words lock, all three legacy body
    markers still lock, and `(DRAFT)` still does not. A regression in any row
    fails open or freezes authoring.
    """
    _write(tmp_path, "contracts/x.v1.md", content)

    decision = evaluate_tool_pre(
        "write_file",
        {"file_path": "contracts/x.v1.md", "content": "new"},
        _config(),
        str(tmp_path),
    )

    assert decision.result.action == expected


def test_w4b_bash_laundering_into_a_ratified_document_is_denied(
    tmp_path: Path,
) -> None:
    _write(tmp_path, "docs/PROTOCOL.md", H1_RATIFIED + "the ratified clause\n")

    decision = evaluate_tool_pre(
        "bash",
        {"command": "echo hijacked > docs/PROTOCOL.md"},
        _config(),
        str(tmp_path),
    )

    assert decision.result.action == "deny"


# --- W4c: PROTOCOL.md is inside the guarded globs ---------------------------


@pytest.mark.parametrize(
    "rel", ["docs/PROTOCOL.md", "PROTOCOL.md"], ids=["under-docs", "at-root"]
)
def test_w4c_protocol_md_is_covered_by_the_guarded_globs(rel: str) -> None:
    """Marker detection is worth nothing if the path is never a candidate.

    converge-dwi's exposure was exactly this pairing: the H1 word was
    unrecognised AND the path was outside guarded_globs, so the document was
    not guarded either way.
    """
    from amplifier_module_hooks_candidate_guard.guard import _glob_match_any

    assert _glob_match_any(rel, _config().guarded_globs)


def test_w4c_this_repos_own_protocol_reads_as_locked() -> None:
    """The live instance, not a fixture: this repository's docs/PROTOCOL.md
    must be BOTH inside the guarded globs and detected as locked by the
    shipped marker regex. Falsified the day either half drifts."""
    from amplifier_module_hooks_candidate_guard.guard import _glob_match_any

    protocol = REPO_ROOT / "docs" / "PROTOCOL.md"
    assert protocol.is_file(), f"expected {protocol} to exist"
    config = _config()

    assert _glob_match_any("docs/PROTOCOL.md", config.guarded_globs)
    assert re.search(config.frozen_marker_regex, protocol.read_text(encoding="utf-8"))


def test_w4c_guarded_globs_also_match_the_shipped_behavior_config() -> None:
    """Extends the W3a drift tripwire to the fourth value that must agree.

    guarded_globs moved in this change; it was the one list the tripwire did
    not cover, and an uncovered value is exactly how the module and the
    shipped config drifted apart the first time.
    """
    text = BEHAVIOR_YAML.read_text(encoding="utf-8")
    config = _config()

    m = re.search(r"^\s*guarded_globs:\s*\[(.+)\]\s*$", text, re.MULTILINE)
    assert m, "behaviors/converge.yaml no longer sets guarded_globs"
    shipped = {v.strip().strip("\"'") for v in m.group(1).split(",")}
    assert shipped == set(config.guarded_globs)


# ---------------------------------------------------------------------------
# W5 -- the half-freeze: a lock whose record cannot land afterwards
#
#   converge-p17d  A document is locked by editing its own H1, and the record
#                  of that lock is more text in the SAME file. A session that
#                  did it in two edits stamped the H1 first, and its own guard
#                  then refused the changelog edit -- because by then the file
#                  read locked. The vision was left half-frozen: the status
#                  word landed, the record of why it landed did not, and the
#                  session never recovered. Measured 2026-09-06T03:50:03Z,
#                  adopter harness scenario 2 (evaluations/adopter/RESULT.md).
#
# The fix keeps the guard's promise exactly as it was -- no content edit to a
# locked document, ever -- and adds one thing beside it: a write may not LEAVE
# a document locked without, in that same write, the record of its locking.
# The half-frozen state stops being reachable rather than becoming editable.
# ---------------------------------------------------------------------------

DRAFT_VISION = (
    "# Demo \u2014 Vision (DRAFT)\n"
    "\n"
    "## Where this is going\n"
    "\n"
    "One place for direction and one place for operation.\n"
    "\n"
    "## Changelog\n"
    "\n"
    "- **2026-09-05 \u2014 v1 (DRAFT).** First written.\n"
)

#: Edit one of two: the H1 stamped, and nothing else. This is the write that
#: produced the wedge, and the one the guard now refuses.
STAMP_ONLY = DRAFT_VISION.replace(
    "# Demo \u2014 Vision (DRAFT)", "# Demo \u2014 Vision (FROZEN 2026-09-06)"
)

LOCK_ENTRY = (
    "- **2026-09-06 \u2014 v1 (FROZEN 2026-09-06).** Locked on the steward's word; "
    "the four Freeze Bar conditions are recorded in "
    "docs/workflow/owner-ratifications-2026-09-06.md.\n"
)

#: The sanctioned shape: one write, carrying both halves of the freeze.
STAMP_AND_RECORD = STAMP_ONLY.replace(
    "- **2026-09-05 \u2014 v1 (DRAFT).** First written.\n",
    LOCK_ENTRY + "- **2026-09-05 \u2014 v1 (DRAFT).** First written.\n",
)


def test_w5_stamping_the_h1_alone_is_refused(tmp_path: Path) -> None:
    """Edit one of two, refused: this is the write that created the wedge.

    Fails on the pre-fix guard, which returned `continue` here and so let the
    document reach a state its own next edit could not repair.
    """
    _write(tmp_path, "docs/VISION.md", DRAFT_VISION)

    decision = evaluate_tool_pre(
        "write_file",
        {"file_path": "docs/VISION.md", "content": STAMP_ONLY},
        _config(),
        str(tmp_path),
    )

    assert decision.result.action == "deny"
    assert [(name, p["reason_code"]) for name, p in decision.events] == [
        ("converge:guard_blocked", "lock_without_record")
    ]


def test_w5_the_refusal_leaves_the_document_a_draft(tmp_path: Path) -> None:
    """The refusal is what keeps the file repairable: nothing was written, so
    the document is still a draft and the combined write can simply be
    re-issued. A guard that denied AFTER the stamp landed would be the wedge
    itself."""
    path = _write(tmp_path, "docs/VISION.md", DRAFT_VISION)

    decision = evaluate_tool_pre(
        "write_file",
        {"file_path": "docs/VISION.md", "content": STAMP_ONLY},
        _config(),
        str(tmp_path),
    )

    assert decision.result.action == "deny"
    assert path.read_text(encoding="utf-8") == DRAFT_VISION
    assert not re.search(_config().frozen_marker_regex, path.read_text(encoding="utf-8"))


def test_w5_one_write_carrying_both_halves_is_allowed(tmp_path: Path) -> None:
    """The whole point: the freeze is one edit, and one edit goes through."""
    _write(tmp_path, "docs/VISION.md", DRAFT_VISION)

    decision = evaluate_tool_pre(
        "write_file",
        {"file_path": "docs/VISION.md", "content": STAMP_AND_RECORD},
        _config(),
        str(tmp_path),
    )

    assert decision.result.action == "continue"
    assert decision.events == []


def test_w5_the_deny_names_the_one_edit_remedy(tmp_path: Path) -> None:
    """A refusal that does not say what to do instead is how the harness
    session spent twenty minutes grepping for a way out."""
    _write(tmp_path, "docs/VISION.md", DRAFT_VISION)

    decision = evaluate_tool_pre(
        "write_file",
        {"file_path": "docs/VISION.md", "content": STAMP_ONLY},
        _config(),
        str(tmp_path),
    )

    reason = decision.result.reason or ""
    assert "ONE edit" in reason
    assert "Changelog" in reason
    assert "still a draft" in reason
    assert "half-frozen" in reason
    assert "documents.v1" in reason


def test_w5_the_second_edit_of_a_two_edit_freeze_is_still_denied(
    tmp_path: Path,
) -> None:
    """The promise is unchanged, and this is the test that says so.

    Given a document ALREADY half-frozen (the state the harness reached), the
    changelog edit is still refused, exactly as before -- the guard never
    admits a content edit to a locked document. That is why the fix had to
    make the state unreachable rather than make it writable.
    """
    _write(tmp_path, "docs/VISION.md", STAMP_ONLY)

    decision = evaluate_tool_pre(
        "write_file",
        {"file_path": "docs/VISION.md", "content": STAMP_AND_RECORD},
        _config(),
        str(tmp_path),
    )

    assert decision.result.action == "deny"
    assert [(name, p["reason_code"]) for name, p in decision.events] == [
        ("converge:guard_blocked", "frozen_direct_edit")
    ]


def test_w5_an_edit_file_stamp_alone_is_refused(tmp_path: Path) -> None:
    """The tool the harness session actually used was edit_file, which never
    carries the resulting file -- only the span it replaces. The check applies
    the replacement itself rather than declining to look."""
    _write(tmp_path, "docs/VISION.md", DRAFT_VISION)

    decision = evaluate_tool_pre(
        "edit_file",
        {
            "file_path": "docs/VISION.md",
            "old_string": "# Demo \u2014 Vision (DRAFT)",
            "new_string": "# Demo \u2014 Vision (FROZEN 2026-09-06)",
        },
        _config(),
        str(tmp_path),
    )

    assert decision.result.action == "deny"


def test_w5_an_edit_file_carrying_both_halves_is_allowed(tmp_path: Path) -> None:
    _write(tmp_path, "docs/VISION.md", DRAFT_VISION)

    decision = evaluate_tool_pre(
        "edit_file",
        {
            "file_path": "docs/VISION.md",
            "old_string": DRAFT_VISION,
            "new_string": STAMP_AND_RECORD,
        },
        _config(),
        str(tmp_path),
    )

    assert decision.result.action == "continue"


def test_w5_an_apply_patch_stamp_alone_is_refused(tmp_path: Path) -> None:
    _write(tmp_path, "docs/VISION.md", DRAFT_VISION)
    diff = (
        "--- a/docs/VISION.md\n"
        "+++ b/docs/VISION.md\n"
        "@@ -1 +1 @@\n"
        "-# Demo \u2014 Vision (DRAFT)\n"
        "+# Demo \u2014 Vision (FROZEN 2026-09-06)\n"
    )

    decision = evaluate_tool_pre(
        "apply_patch",
        {"type": "update_file", "path": "docs/VISION.md", "diff": diff},
        _config(),
        str(tmp_path),
    )

    assert decision.result.action == "deny"


def test_w5_an_apply_patch_carrying_both_halves_is_allowed(tmp_path: Path) -> None:
    _write(tmp_path, "docs/VISION.md", DRAFT_VISION)
    diff = (
        "--- a/docs/VISION.md\n"
        "+++ b/docs/VISION.md\n"
        "@@ -1 +1 @@\n"
        "-# Demo \u2014 Vision (DRAFT)\n"
        "+# Demo \u2014 Vision (FROZEN 2026-09-06)\n"
        "@@ -9 +9,2 @@\n"
        "+" + LOCK_ENTRY
    )

    decision = evaluate_tool_pre(
        "apply_patch",
        {"type": "update_file", "path": "docs/VISION.md", "diff": diff},
        _config(),
        str(tmp_path),
    )

    assert decision.result.action == "continue"


def test_w5_a_changelog_line_already_on_disk_is_not_a_new_record(
    tmp_path: Path,
) -> None:
    """A document whose changelog already mentions an earlier version's freeze
    must not satisfy the check by accident. The record has to be one THIS
    write adds."""
    stale = DRAFT_VISION.replace(
        "- **2026-09-05 \u2014 v1 (DRAFT).** First written.\n",
        "- **2026-01-01 \u2014 v0 (FROZEN 2026-01-01).** An older version's lock.\n"
        "- **2026-09-05 \u2014 v1 (DRAFT).** First written.\n",
    )
    _write(tmp_path, "docs/VISION.md", stale)
    stamped = stale.replace(
        "# Demo \u2014 Vision (DRAFT)", "# Demo \u2014 Vision (FROZEN 2026-09-06)"
    )

    decision = evaluate_tool_pre(
        "write_file",
        {"file_path": "docs/VISION.md", "content": stamped},
        _config(),
        str(tmp_path),
    )

    assert decision.result.action == "deny"


@pytest.mark.parametrize(
    "content",
    [
        DRAFT_VISION + "\nAnother paragraph while it is still a draft.\n",
        DRAFT_VISION.replace("One place", "Exactly one place"),
    ],
    ids=["append", "reword"],
)
def test_w5_ordinary_draft_writing_is_untouched(tmp_path: Path, content: str) -> None:
    """The check must cost a drafting session nothing. A write that does not
    lock the document is not this check's business."""
    _write(tmp_path, "docs/VISION.md", DRAFT_VISION)

    decision = evaluate_tool_pre(
        "write_file",
        {"file_path": "docs/VISION.md", "content": content},
        _config(),
        str(tmp_path),
    )

    assert decision.result.action == "continue"


def test_w5_a_file_that_does_not_exist_yet_is_out_of_scope(tmp_path: Path) -> None:
    """The honest limit, stated as a test: this check watches the DRAFT ->
    LOCKED transition of a document already on disk. Creating a file that
    already carries a locking word is a different act (an import, a copy, a
    fixture) and the guard has never had an opinion about it."""
    decision = evaluate_tool_pre(
        "write_file",
        {"file_path": "contracts/imported.v1.md", "content": STAMP_ONLY},
        _config(),
        str(tmp_path),
    )

    assert decision.result.action == "continue"


def test_w5_the_check_is_configurable_off(tmp_path: Path) -> None:
    _write(tmp_path, "docs/VISION.md", DRAFT_VISION)

    decision = evaluate_tool_pre(
        "write_file",
        {"file_path": "docs/VISION.md", "content": STAMP_ONLY},
        _config(require_lock_record=False),
        str(tmp_path),
    )

    assert decision.result.action == "continue"


def test_w5_a_contract_is_covered_too_not_only_the_vision(tmp_path: Path) -> None:
    draft = (
        "# Demo Contract \u2014 v1 (DRAFT)\n"
        "\n"
        "## Core (the teeth)\n"
        "\n"
        "**Core 1.** The app shows only what it can read.\n"
    )
    _write(tmp_path, "contracts/demo.v1.md", draft)

    decision = evaluate_tool_pre(
        "write_file",
        {
            "file_path": "contracts/demo.v1.md",
            "content": draft.replace("(DRAFT)", "(FROZEN 2026-09-06)"),
        },
        _config(),
        str(tmp_path),
    )

    assert decision.result.action == "deny"


def test_w5_the_shipped_behavior_config_does_not_disable_the_check() -> None:
    """The W3a drift tripwire, extended to the new key. behaviors/converge.yaml
    may leave it unset -- the module default is on -- but it must never ship
    it off, which would restore the wedge for every repo on the shipped
    config while the module's own tests stayed green."""
    text = BEHAVIOR_YAML.read_text(encoding="utf-8")

    assert _config().require_lock_record is True
    assert not re.search(r"^\s*require_lock_record:\s*false\s*$", text, re.MULTILINE)


def test_w5_the_apps_own_lock_passes_this_guard(tmp_path: Path) -> None:
    """The two halves of the fix, checked against each other.

    `app/writes.py::lock_document` is the OTHER way a document gets locked in
    this project, and it writes files directly -- the guard never sees it. So
    this runs a real lock against a real git repository and then puts the
    guard's own evaluator over the exact before/after text the app produced.

    It is the only test in either suite that would catch the two drifting
    apart: if the app went back to stamping the H1 alone, every test in
    `app/tests/test_lock_write.py` could still be made to pass while a
    session-side lock of the same document was refused.
    """
    import subprocess
    import sys

    sys.path.insert(0, str(REPO_ROOT))
    try:
        from app import writes  # noqa: PLC0415 -- import cost belongs to this test
    except ImportError as exc:  # pragma: no cover -- app/ is stdlib-only today
        pytest.fail(f"app.writes should import with no extra dependencies: {exc}")

    repo = tmp_path / "demo"
    (repo / "docs").mkdir(parents=True)
    doc = repo / "docs" / "VISION.md"
    doc.write_text(DRAFT_VISION, encoding="utf-8")
    for args in (
        ("init", "-q", "-b", "main"),
        ("add", "-A"),
        ("commit", "-q", "-m", "seed"),
    ):
        subprocess.run(
            ["git", "-c", "user.name=T", "-c", "user.email=t@e.invalid", *args],
            cwd=repo,
            check=True,
            capture_output=True,
        )

    before = doc.read_text(encoding="utf-8")
    result = writes.lock_document(
        repo,
        doc,
        conditions=["one", "two", "three", "four"],
        doc_id="vision",
        user="steward",
    )
    assert result["ok"] is True, result
    after = doc.read_text(encoding="utf-8")
    assert re.search(_config().frozen_marker_regex, after), "the app did not lock it"

    doc.write_text(before, encoding="utf-8")  # a draft again, for the probe
    decision = evaluate_tool_pre(
        "write_file",
        {"file_path": "docs/VISION.md", "content": after},
        _config(),
        str(repo),
    )

    assert decision.result.action == "continue", decision.result.reason


# ---------------------------------------------------------------------------
# W6 -- a governed repo BELOW the session cwd
#
#   converge-qfi9  Measured 2026-09-06: with the session cwd at a multi-repo
#                  workspace root, `edit_file` on a FROZEN
#                  `amplifier-work-tracker/contracts/operator-surface.v1.md`
#                  went through THREE times across three sessions, with this
#                  module mounted and evaluating (53 guard events in the
#                  session log). Cause: the target was relativized against the
#                  SESSION cwd, so it read as
#                  `amplifier-work-tracker/contracts/...` and matched no
#                  shipped glob -- `contracts/*.md` is anchored at the start.
#                  The same call with cwd=<the repo> denied.
#
#                  A guarded_glob is a statement about a REPOSITORY's layout,
#                  so a target is now resolved in its own repository's frame:
#                  the nearest ancestor carrying `.git`, bounded at cwd.
# ---------------------------------------------------------------------------


def _below_cwd_repo(tmp_path: Path) -> tuple[Path, Path]:
    """The measured shape: cwd is a workspace root; the governed repo is a
    git repository one level below it. Returns (workspace, repo)."""
    repo = tmp_path / "amplifier-work-tracker"
    (repo / ".git").mkdir(parents=True)
    return tmp_path, repo


def test_w6_frozen_contract_in_a_repo_below_cwd_is_denied(tmp_path: Path) -> None:
    """The reproduction, pinned. Before the fix this returned `continue`."""
    workspace, repo = _below_cwd_repo(tmp_path)
    _write(repo, "contracts/operator-surface.v1.md", FROZEN_STAMP + "body")

    decision = evaluate_tool_pre(
        "edit_file",
        {
            "file_path": str(repo / "contracts" / "operator-surface.v1.md"),
            "old_string": "body",
            "new_string": "tampered",
        },
        _config(),
        str(workspace),
    )

    assert decision.result.action == "deny", decision.result.reason
    assert [e[1]["reason_code"] for e in decision.events] == ["frozen_direct_edit"]


def test_w6_the_h1_form_is_denied_below_cwd_too(tmp_path: Path) -> None:
    """The ratified anatomy (status in the H1) reaches below cwd as well."""
    workspace, repo = _below_cwd_repo(tmp_path)
    _write(repo, "docs/VISION.md", "# Vision v1 (RATIFIED 2026-09-03)\n\nbody\n")

    decision = evaluate_tool_pre(
        "write_file",
        {"file_path": str(repo / "docs" / "VISION.md"), "content": "rewritten"},
        _config(),
        str(workspace),
    )

    assert decision.result.action == "deny", decision.result.reason


def test_w6_the_deny_names_a_path_the_reader_can_use_from_cwd(tmp_path: Path) -> None:
    """Decisions are made in the repo's frame; humans are told the cwd frame.

    Handing a reader `contracts/operator-surface.v2-candidate.md` when their
    cwd is the workspace names a file in the wrong repository.
    """
    workspace, repo = _below_cwd_repo(tmp_path)
    _write(repo, "contracts/operator-surface.v1.md", FROZEN_STAMP + "body")

    decision = evaluate_tool_pre(
        "write_file",
        {
            "file_path": str(repo / "contracts" / "operator-surface.v1.md"),
            "content": "new",
        },
        _config(),
        str(workspace),
    )

    assert decision.result.action == "deny"
    assert (
        "amplifier-work-tracker/contracts/operator-surface.v1.md"
        in decision.result.reason
    )
    assert (
        "amplifier-work-tracker/contracts/operator-surface.v2-candidate.md"
        in decision.result.reason
    )
    assert (
        decision.events[0][1]["path"]
        == "amplifier-work-tracker/contracts/operator-surface.v1.md"
    )


def test_w6_a_stamped_candidate_beside_the_below_cwd_contract_opens_the_hatch(
    tmp_path: Path,
) -> None:
    """The remedy has to reach where the bug did.

    The proposal's `target:` line is written the way a person standing in that
    repo writes it -- relative to THEIR repo. Fixing the deny without this is
    a deny with no reachable remedy: measured, `**/`-prefixed guarded_globs
    (the smaller alternative) leave this case denied.
    """
    workspace, repo = _below_cwd_repo(tmp_path)
    _write(repo, "contracts/operator-surface.v1.md", FROZEN_STAMP + "body")
    _write(
        repo,
        "contracts/operator-surface.v2-candidate.md",
        "target: contracts/operator-surface.v1.md\n\n" + RATIFIED_STAMP,
    )

    decision = evaluate_tool_pre(
        "edit_file",
        {
            "file_path": str(repo / "contracts" / "operator-surface.v1.md"),
            "old_string": "body",
            "new_string": "amended",
        },
        _config(),
        str(workspace),
    )

    assert decision.result.action == "continue", decision.result.reason
    assert decision.events[0][0] == "converge:guard_allowed_ratified"
    assert decision.events[0][1]["candidate"] == (
        "contracts/operator-surface.v2-candidate.md"
    )


def test_w6_an_unratified_candidate_below_cwd_does_not_unlock(tmp_path: Path) -> None:
    workspace, repo = _below_cwd_repo(tmp_path)
    _write(repo, "contracts/operator-surface.v1.md", FROZEN_STAMP + "body")
    _write(
        repo,
        "contracts/operator-surface.v2-candidate.md",
        "target: contracts/operator-surface.v1.md\n\nstill under discussion\n",
    )

    decision = evaluate_tool_pre(
        "edit_file",
        {
            "file_path": str(repo / "contracts" / "operator-surface.v1.md"),
            "old_string": "body",
            "new_string": "amended",
        },
        _config(),
        str(workspace),
    )

    assert decision.result.action == "deny", decision.result.reason


def test_w6_writing_the_proposal_itself_below_cwd_is_allowed(tmp_path: Path) -> None:
    """always_allow_globs still resolve for the below-cwd case."""
    workspace, repo = _below_cwd_repo(tmp_path)
    _write(repo, "contracts/operator-surface.v1.md", FROZEN_STAMP + "body")

    decision = evaluate_tool_pre(
        "write_file",
        {
            "file_path": str(repo / "contracts" / "operator-surface.v2-candidate.md"),
            "content": "target: contracts/operator-surface.v1.md\n\nthe proposal\n",
        },
        _config(),
        str(workspace),
    )

    assert decision.result.action == "continue", decision.result.reason


def test_w6_bash_laundering_into_a_below_cwd_contract_is_denied(
    tmp_path: Path,
) -> None:
    workspace, repo = _below_cwd_repo(tmp_path)
    _write(repo, "contracts/operator-surface.v1.md", FROZEN_STAMP + "body")
    target = repo / "contracts" / "operator-surface.v1.md"

    decision = evaluate_tool_pre(
        "bash",
        {"command": f"echo tampered > {target}"},
        _config(),
        str(workspace),
    )

    assert decision.result.action == "deny", decision.result.reason
    assert decision.events[0][1]["reason_code"] == "frozen_bash_write"


def test_w6_the_half_freeze_check_reaches_a_repo_below_cwd(tmp_path: Path) -> None:
    """W5's check is made in the same frame -- so it works below cwd too."""
    workspace, repo = _below_cwd_repo(tmp_path)
    _write(repo, "docs/VISION.md", "# Vision v1 (DRAFT)\n\nbody\n")

    decision = evaluate_tool_pre(
        "edit_file",
        {
            "file_path": str(repo / "docs" / "VISION.md"),
            "old_string": "# Vision v1 (DRAFT)",
            "new_string": "# Vision v1 (FROZEN 2026-09-06)",
        },
        _config(),
        str(workspace),
    )

    assert decision.result.action == "deny", decision.result.reason
    assert decision.events[0][1]["reason_code"] == "lock_without_record"


def test_w6_a_git_worktree_dot_git_file_is_a_repository_root(tmp_path: Path) -> None:
    """Every Converge lane is a worktree, where `.git` is a FILE, not a dir."""
    workspace = tmp_path
    repo = workspace / "lane-worktree"
    repo.mkdir()
    (repo / ".git").write_text("gitdir: /elsewhere/.git/worktrees/lane\n")
    _write(repo, "contracts/x.v1.md", FROZEN_STAMP + "body")

    decision = evaluate_tool_pre(
        "write_file",
        {"file_path": str(repo / "contracts" / "x.v1.md"), "content": "new"},
        _config(),
        str(workspace),
    )

    assert decision.result.action == "deny", decision.result.reason


def test_w6_the_deepest_repository_governs(tmp_path: Path) -> None:
    """cwd is itself a repo, and the target lives in a nested one.

    The nested repo's own layout wins -- its `contracts/` is the one the
    glob is a statement about.
    """
    workspace = tmp_path
    (workspace / ".git").mkdir()
    inner = workspace / "vendor" / "inner-repo"
    (inner / ".git").mkdir(parents=True)
    _write(inner, "contracts/x.v1.md", FROZEN_STAMP + "body")

    decision = evaluate_tool_pre(
        "write_file",
        {"file_path": str(inner / "contracts" / "x.v1.md"), "content": "new"},
        _config(),
        str(workspace),
    )

    assert decision.result.action == "deny", decision.result.reason


def test_w6_cwd_as_the_repo_root_is_unchanged(tmp_path: Path) -> None:
    """The pre-existing shape: cwd IS the governed repo. Both frames agree."""
    (tmp_path / ".git").mkdir()
    _write(tmp_path, "contracts/x.v1.md", FROZEN_STAMP + "body")

    decision = evaluate_tool_pre(
        "write_file",
        {"file_path": "contracts/x.v1.md", "content": "new"},
        _config(),
        str(tmp_path),
    )

    assert decision.result.action == "deny"
    assert decision.events[0][1]["path"] == "contracts/x.v1.md"


def test_w6_a_repository_outside_cwd_is_still_out_of_scope(tmp_path: Path) -> None:
    """U9's within-cwd invariant is untouched: the root search is bounded at
    cwd, so a sibling repository is still not this hook's business."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    outside = tmp_path / "outside-repo"
    (outside / ".git").mkdir(parents=True)
    _write(outside, "contracts/x.v1.md", FROZEN_STAMP + "body")

    decision = evaluate_tool_pre(
        "write_file",
        {"file_path": str(outside / "contracts" / "x.v1.md"), "content": "new"},
        _config(),
        str(workspace),
    )

    assert decision.result.action == "continue"


def test_w6_a_non_repository_directory_below_cwd_is_the_documented_limit(
    tmp_path: Path,
) -> None:
    """The honest limit, pinned rather than left to be discovered.

    A directory below cwd that is not a git repository has no repository
    frame, so it falls back to cwd and is matched exactly as before. Stated
    in the module README under "Which repository a path belongs to".
    """
    workspace = tmp_path
    notes = workspace / "notes"  # deliberately NOT a repo
    _write(notes, "contracts/x.v1.md", FROZEN_STAMP + "body")

    decision = evaluate_tool_pre(
        "write_file",
        {"file_path": str(notes / "contracts" / "x.v1.md"), "content": "new"},
        _config(),
        str(workspace),
    )

    assert decision.result.action == "continue"


def test_w6_the_break_glass_token_is_read_in_the_repos_own_frame(
    tmp_path: Path,
) -> None:
    """One frame for the whole decision: the token lives in the repo whose
    document it unlocks, and its `file:` line is that repo's path."""
    workspace, repo = _below_cwd_repo(tmp_path)
    _write(repo, "contracts/x.v1.md", FROZEN_STAMP + "body")
    _write(
        repo,
        ".converge/UNLOCK",
        "file: contracts/x.v1.md\nreason: incident\nby: steward\n",
    )
    config = _config(escape_mode="token", allow_emergency_unlock=True)

    decision = evaluate_tool_pre(
        "write_file",
        {"file_path": str(repo / "contracts" / "x.v1.md"), "content": "new"},
        config,
        str(workspace),
    )

    assert decision.result.action == "continue", decision.result.reason
    assert decision.events[0][0] == "converge:guard_unlock_used"


# ---------------------------------------------------------------------------
# W7 -- single-use: a ratified candidate already recorded is spent
#
#   converge-wu3y  MEASURED 2026-09-06:
#                  `contracts/operator-surface.v2-candidate.md` was ratified,
#                  applied to the locked target via PR #90, and then LEFT IN
#                  PLACE with its `target:` line unchanged. Result: the
#                  escape hatch stayed open indefinitely for anyone, because
#                  `_find_ratified_candidate` had no way to tell "already
#                  landed" from "still pending". The fix: a candidate whose
#                  amendment is already recorded in the target's own
#                  `## Changelog` (by the candidate's own repo-relative path,
#                  never a bare date or a fuzzy substring) no longer opens
#                  the hatch; a still-unspent candidate for the same target
#                  is unaffected.
# ---------------------------------------------------------------------------

SPENT_CONTRACT = (
    FROZEN_STAMP
    + "# X Contract - v1 (FROZEN 2026-09-06)\n\n"
    "amended clause\n\n"
    "## Changelog\n\n"
    "- **2026-09-06 -- v1 (FROZEN 2026-09-06).** Amendment landed from "
    "`contracts/x.v2-candidate.md`.\n"
)

SPENT_CANDIDATE = (
    "target: contracts/x.v1.md\n\nproposal, already applied...\n\n" + RATIFIED_STAMP
)


def test_w7_a_candidate_recorded_in_the_targets_changelog_no_longer_unlocks(
    tmp_path: Path,
) -> None:
    """The reproduction, pinned. Before the fix this returned `continue` and
    emitted `converge:guard_allowed_ratified` -- the spent candidate reopened
    the hatch indefinitely."""
    _write(tmp_path, "contracts/x.v1.md", SPENT_CONTRACT)
    _write(tmp_path, "contracts/x.v2-candidate.md", SPENT_CANDIDATE)
    config = _config()

    decision = evaluate_tool_pre(
        "write_file",
        {"file_path": "contracts/x.v1.md", "content": "tampered"},
        config,
        str(tmp_path),
    )

    assert decision.result.action == "deny", decision.result.reason
    assert [e[1]["reason_code"] for e in decision.events] == ["frozen_direct_edit"]
    assert not any(name == "converge:guard_allowed_ratified" for name, _ in decision.events)


def test_w7_an_unspent_candidate_still_unlocks_positive_control(
    tmp_path: Path,
) -> None:
    """Positive control: identical fixture, but the target's Changelog does
    NOT yet name the candidate -- the hatch must still open. This is the
    existing-behavior guarantee the fix must not regress."""
    unspent_contract = (
        FROZEN_STAMP
        + "# X Contract - v1 (FROZEN 2026-09-06)\n\n"
        "old clause\n\n"
        "## Changelog\n\n"
        "- **2026-09-06 -- v1 (FROZEN 2026-09-06).** Locked on the steward's word.\n"
    )
    _write(tmp_path, "contracts/x.v1.md", unspent_contract)
    _write(tmp_path, "contracts/x.v2-candidate.md", SPENT_CANDIDATE)
    config = _config()

    decision = evaluate_tool_pre(
        "write_file",
        {"file_path": "contracts/x.v1.md", "content": "amended clause"},
        config,
        str(tmp_path),
    )

    assert decision.result.action == "continue", decision.result.reason
    assert any(name == "converge:guard_allowed_ratified" for name, _ in decision.events)


def test_w7_a_different_unrelated_candidate_for_the_same_target_still_unlocks(
    tmp_path: Path,
) -> None:
    """One candidate landing must not close the door on a SEPARATE, later
    proposal for the same target. The search must continue past a spent
    candidate to find an unspent one, not stop at the first match."""
    _write(tmp_path, "contracts/x.v1.md", SPENT_CONTRACT)
    _write(tmp_path, "contracts/x.v2-candidate.md", SPENT_CANDIDATE)
    _write(
        tmp_path,
        "contracts/x.v3-candidate.md",
        "target: contracts/x.v1.md\n\na second, later proposal...\n\n" + RATIFIED_STAMP,
    )
    config = _config()

    decision = evaluate_tool_pre(
        "write_file",
        {"file_path": "contracts/x.v1.md", "content": "second amendment"},
        config,
        str(tmp_path),
    )

    assert decision.result.action == "continue", decision.result.reason
    assert any(name == "converge:guard_allowed_ratified" for name, _ in decision.events)


def test_w7_a_similar_date_in_the_changelog_does_not_accidentally_spend_a_different_candidate(
    tmp_path: Path,
) -> None:
    """No fuzzy substring/date matching (goal instruction, converge-wu3y):
    a Changelog entry that shares a date with an unrelated, still-pending
    candidate must not be read as recording THAT candidate. Only the
    candidate's own path counts."""
    contract = (
        FROZEN_STAMP
        + "# X Contract - v1 (FROZEN 2026-09-06)\n\n"
        "clause\n\n"
        "## Changelog\n\n"
        "- **2026-09-06 -- v1 (FROZEN 2026-09-06).** Locked on the steward's word.\n"
    )
    _write(tmp_path, "contracts/x.v1.md", contract)
    # This candidate's own path never appears in the changelog above, even
    # though the date "2026-09-06" does.
    _write(tmp_path, "contracts/x.v2-candidate.md", SPENT_CANDIDATE)
    config = _config()

    decision = evaluate_tool_pre(
        "write_file",
        {"file_path": "contracts/x.v1.md", "content": "amended clause"},
        config,
        str(tmp_path),
    )

    assert decision.result.action == "continue", decision.result.reason


def test_w7_workspace_relative_target_below_cwd_a_spent_candidate_still_denies(
    tmp_path: Path,
) -> None:
    """The single-use check reaches where converge-qfi9's governing-root fix
    reaches: a spent candidate beside a contract in a repo BELOW the session
    cwd must not unlock it either."""
    workspace, repo = _below_cwd_repo(tmp_path)
    _write(repo, "contracts/x.v1.md", SPENT_CONTRACT)
    _write(repo, "contracts/x.v2-candidate.md", SPENT_CANDIDATE)

    decision = evaluate_tool_pre(
        "write_file",
        {"file_path": str(repo / "contracts" / "x.v1.md"), "content": "tampered"},
        _config(),
        str(workspace),
    )

    assert decision.result.action == "deny", decision.result.reason


def test_w7_workspace_relative_target_below_cwd_an_unspent_candidate_still_unlocks(
    tmp_path: Path,
) -> None:
    """Positive control for the below-cwd frame: an unspent candidate there
    must still open the hatch, exactly as before this fix."""
    workspace, repo = _below_cwd_repo(tmp_path)
    unspent_contract = (
        FROZEN_STAMP
        + "# X Contract - v1 (FROZEN 2026-09-06)\n\n"
        "old clause\n\n"
        "## Changelog\n\n"
        "- **2026-09-06 -- v1 (FROZEN 2026-09-06).** Locked on the steward's word.\n"
    )
    _write(repo, "contracts/x.v1.md", unspent_contract)
    _write(repo, "contracts/x.v2-candidate.md", SPENT_CANDIDATE)

    decision = evaluate_tool_pre(
        "write_file",
        {
            "file_path": str(repo / "contracts" / "x.v1.md"),
            "content": "amended clause",
        },
        _config(),
        str(workspace),
    )

    assert decision.result.action == "continue", decision.result.reason


def test_w7_malformed_no_changelog_section_falls_back_to_unspent(
    tmp_path: Path,
) -> None:
    """Malformed input: a FROZEN contract with no ``## Changelog`` heading at
    all. Nothing can be "recorded" in a section that does not exist, so the
    candidate is treated as not-yet-landed -- the pre-existing behavior,
    unchanged by this fix."""
    contract = FROZEN_STAMP + "# X Contract - v1 (FROZEN 2026-09-06)\n\nclause\n"
    _write(tmp_path, "contracts/x.v1.md", contract)
    _write(tmp_path, "contracts/x.v2-candidate.md", SPENT_CANDIDATE)
    config = _config()

    decision = evaluate_tool_pre(
        "write_file",
        {"file_path": "contracts/x.v1.md", "content": "amended clause"},
        config,
        str(tmp_path),
    )

    assert decision.result.action == "continue", decision.result.reason


def test_w7_malformed_empty_changelog_section_falls_back_to_unspent(
    tmp_path: Path,
) -> None:
    """Malformed input: a ``## Changelog`` heading present but with no body
    before EOF -- must not raise, and must not be read as recording
    anything."""
    contract = (
        FROZEN_STAMP + "# X Contract - v1 (FROZEN 2026-09-06)\n\nclause\n\n## Changelog\n"
    )
    _write(tmp_path, "contracts/x.v1.md", contract)
    _write(tmp_path, "contracts/x.v2-candidate.md", SPENT_CANDIDATE)
    config = _config()

    decision = evaluate_tool_pre(
        "write_file",
        {"file_path": "contracts/x.v1.md", "content": "amended clause"},
        config,
        str(tmp_path),
    )

    assert decision.result.action == "continue", decision.result.reason


def test_w7_malformed_candidate_path_mentioned_outside_the_changelog_does_not_spend_it(
    tmp_path: Path,
) -> None:
    """Malformed/adversarial input: the candidate's path appears in the
    document's PROSE (not under Changelog) -- must not count as a record.
    Only text actually inside the Changelog section is evidence of landing."""
    contract = (
        FROZEN_STAMP + "# X Contract - v1 (FROZEN 2026-09-06)\n\n"
        "See contracts/x.v2-candidate.md for background.\n\n"
        "## Changelog\n\n"
        "- **2026-09-06 -- v1 (FROZEN 2026-09-06).** Locked on the steward's word.\n"
    )
    _write(tmp_path, "contracts/x.v1.md", contract)
    _write(tmp_path, "contracts/x.v2-candidate.md", SPENT_CANDIDATE)
    config = _config()

    decision = evaluate_tool_pre(
        "write_file",
        {"file_path": "contracts/x.v1.md", "content": "amended clause"},
        config,
        str(tmp_path),
    )

    assert decision.result.action == "continue", decision.result.reason


def test_w7_regression_the_target_is_read_only_once_for_the_escape_hatch_check(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Removal control for the defect-1 fix (converge-wu3y): with the
    default `require_frozen_marker: true`, the guarded target's content,
    once successfully read to determine it is guarded (step 6), must be
    REUSED for the already-landed check (step 7) rather than read a second
    time. Counts every read of the target file specifically."""
    _write(tmp_path, "contracts/x.v1.md", SPENT_CONTRACT)
    _write(tmp_path, "contracts/x.v2-candidate.md", SPENT_CANDIDATE)
    config = _config()

    import amplifier_module_hooks_candidate_guard.guard as guard_module

    real_read = guard_module._read_file_text
    target_reads = {"n": 0}

    def counting_read(path: Path) -> str:
        if Path(path).name == "x.v1.md":
            target_reads["n"] += 1
        return real_read(path)

    monkeypatch.setattr(guard_module, "_read_file_text", counting_read)

    decision = evaluate_tool_pre(
        "write_file",
        {"file_path": "contracts/x.v1.md", "content": "tampered"},
        config,
        str(tmp_path),
    )

    assert decision.result.action == "deny", decision.result.reason
    assert target_reads["n"] == 1, target_reads


def test_w7_an_unreadable_target_during_the_escape_hatch_check_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The reproduction of defect 1, pinned. With `require_frozen_marker`
    disabled -- so the guarded-path check (step 6) never reads the target
    and there is no already-read content to reuse -- the escape hatch's own
    read of that SAME target file, to check whether a ratified candidate is
    already spent, is the only read left. A failure on THAT read must DENY
    the write (`fail_closed_on_error` defaults `true`), never silently fall
    back to "not yet recorded" and let the write through.

    Before the fix, `_candidate_already_landed` caught the `OSError` and
    returned `False` ("not recorded" -- unspent), so the ratified candidate
    was treated as still valid and the write was allowed (`continue`)
    despite `fail_closed_on_error: true`. That is the defect: an I/O error
    on the guard's own re-read silently reopened the hatch instead of
    denying."""
    _write(tmp_path, "contracts/x.v1.md", SPENT_CONTRACT)
    _write(tmp_path, "contracts/x.v2-candidate.md", SPENT_CANDIDATE)
    config = _config(require_frozen_marker=False)

    import amplifier_module_hooks_candidate_guard.guard as guard_module

    real_read = guard_module._read_file_text

    def flaky_read(path: Path) -> str:
        if Path(path).name == "x.v1.md":
            raise OSError("simulated transient I/O failure")
        return real_read(path)

    monkeypatch.setattr(guard_module, "_read_file_text", flaky_read)

    decision = evaluate_tool_pre(
        "write_file",
        {"file_path": "contracts/x.v1.md", "content": "tampered"},
        config,
        str(tmp_path),
    )

    assert decision.result.action == "deny", decision.result.reason


def test_w7_an_unreadable_target_with_fail_closed_disabled_still_does_not_unlock(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Even with `fail_closed_on_error: false`, an error while checking the
    escape hatch must never be read as "an escape hatch was found" -- it
    degrades to the ordinary "no escape hatch" outcome (deny for this
    guarded path), never to an allow. Only the SHAPE of the deny (the
    generic guard-evaluation-error message vs. the ordinary frozen-file
    message) is gated by the flag; the direction never is."""
    _write(tmp_path, "contracts/x.v1.md", SPENT_CONTRACT)
    _write(tmp_path, "contracts/x.v2-candidate.md", SPENT_CANDIDATE)
    config = _config(require_frozen_marker=False, fail_closed_on_error=False)

    import amplifier_module_hooks_candidate_guard.guard as guard_module

    real_read = guard_module._read_file_text

    def flaky_read(path: Path) -> str:
        if Path(path).name == "x.v1.md":
            raise OSError("simulated transient I/O failure")
        return real_read(path)

    monkeypatch.setattr(guard_module, "_read_file_text", flaky_read)

    decision = evaluate_tool_pre(
        "write_file",
        {"file_path": "contracts/x.v1.md", "content": "tampered"},
        config,
        str(tmp_path),
    )

    assert decision.result.action == "deny", decision.result.reason


# ---------------------------------------------------------------------------
# W8 -- exact path-token matching for the single-use check (converge-wu3y
# defect 2): the previous `candidate_rel in changelog or candidate_path.name
# in changelog` was a substring-OR-basename test, which read two different
# documents as "the same candidate".
# ---------------------------------------------------------------------------


def test_w8_a_changelog_naming_a_longer_similar_filename_does_not_spend_the_candidate(
    tmp_path: Path,
) -> None:
    """Defect 2a: `contracts/x.v2-candidate.md` must not read as
    already-landed just because the changelog names a LONGER, different
    file that happens to start with the same text --
    `contracts/x.v2-candidate.md.bak`. Before the fix, a raw substring
    search matched this (the shorter path is a literal prefix of the longer
    one) and wrongly spent a candidate that was, in truth, still valid --
    denying a write a genuinely unspent, ratified candidate should have
    allowed."""
    contract = (
        FROZEN_STAMP
        + "# X Contract - v1 (FROZEN 2026-09-06)\n\n"
        "clause\n\n"
        "## Changelog\n\n"
        "- **2026-09-06 -- v1 (FROZEN 2026-09-06).** See the backup at "
        "contracts/x.v2-candidate.md.bak for the pre-amendment text.\n"
    )
    _write(tmp_path, "contracts/x.v1.md", contract)
    _write(tmp_path, "contracts/x.v2-candidate.md", SPENT_CANDIDATE)
    config = _config()

    decision = evaluate_tool_pre(
        "write_file",
        {"file_path": "contracts/x.v1.md", "content": "amended clause"},
        config,
        str(tmp_path),
    )

    assert decision.result.action == "continue", decision.result.reason
    assert any(name == "converge:guard_allowed_ratified" for name, _ in decision.events)


def test_w8_a_changelog_naming_a_same_basename_in_a_different_directory_does_not_spend_it(
    tmp_path: Path,
) -> None:
    """Defect 2b: `contracts/proposals/x.v2-candidate.md` must not read as
    already-landed just because the changelog names a file with the SAME
    BASENAME in a DIFFERENT directory -- `notes/x.v2-candidate.md`. Before
    the fix, the basename-only fallback (`candidate_path.name in
    changelog`) matched this regardless of directory."""
    contract = (
        FROZEN_STAMP
        + "# X Contract - v1 (FROZEN 2026-09-06)\n\n"
        "clause\n\n"
        "## Changelog\n\n"
        "- **2026-09-06 -- v1 (FROZEN 2026-09-06).** See notes/x.v2-candidate.md "
        "for background.\n"
    )
    _write(tmp_path, "contracts/x.v1.md", contract)
    _write(
        tmp_path,
        "contracts/proposals/x.v2-candidate.md",
        "target: contracts/x.v1.md\n\nproposal, still pending...\n\n" + RATIFIED_STAMP,
    )
    config = _config()

    decision = evaluate_tool_pre(
        "write_file",
        {"file_path": "contracts/x.v1.md", "content": "amended clause"},
        config,
        str(tmp_path),
    )

    assert decision.result.action == "continue", decision.result.reason
    assert any(name == "converge:guard_allowed_ratified" for name, _ in decision.events)


def test_w8_a_trailing_period_with_no_backticks_still_spends_the_candidate(
    tmp_path: Path,
) -> None:
    """The exact-path-token rule must not be so strict that ordinary prose
    -- the candidate's path followed directly by a sentence-ending period,
    with no backticks -- fails to register as a record. Only a LONGER,
    different filename (defect 2a) is rejected; trailing sentence
    punctuation with no backticks is still a valid record."""
    contract = (
        FROZEN_STAMP
        + "# X Contract - v1 (FROZEN 2026-09-06)\n\n"
        "amended clause\n\n"
        "## Changelog\n\n"
        "- **2026-09-06 -- v1 (FROZEN 2026-09-06).** Amendment landed from "
        "contracts/x.v2-candidate.md.\n"
    )
    _write(tmp_path, "contracts/x.v1.md", contract)
    _write(tmp_path, "contracts/x.v2-candidate.md", SPENT_CANDIDATE)
    config = _config()

    decision = evaluate_tool_pre(
        "write_file",
        {"file_path": "contracts/x.v1.md", "content": "tampered"},
        config,
        str(tmp_path),
    )

    assert decision.result.action == "deny", decision.result.reason


def test_w8_a_markdown_link_form_still_spends_the_candidate(
    tmp_path: Path,
) -> None:
    """The path-token boundary works for a Markdown link's parenthesised
    target too -- `[label](contracts/x.v2-candidate.md)` -- with no special
    handling needed for that form specifically."""
    contract = (
        FROZEN_STAMP
        + "# X Contract - v1 (FROZEN 2026-09-06)\n\n"
        "amended clause\n\n"
        "## Changelog\n\n"
        "- **2026-09-06 -- v1 (FROZEN 2026-09-06).** See "
        "[the landed proposal](contracts/x.v2-candidate.md) for detail.\n"
    )
    _write(tmp_path, "contracts/x.v1.md", contract)
    _write(tmp_path, "contracts/x.v2-candidate.md", SPENT_CANDIDATE)
    config = _config()

    decision = evaluate_tool_pre(
        "write_file",
        {"file_path": "contracts/x.v1.md", "content": "tampered"},
        config,
        str(tmp_path),
    )

    assert decision.result.action == "deny", decision.result.reason


def test_w8_a_different_final_extension_does_not_spend_the_candidate(
    tmp_path: Path,
) -> None:
    """Defect 2, one more adversarial shape: a changelog naming
    `contracts/x.v2-candidate.mdx` (a real, different file with a longer
    extension) must not spend `contracts/x.v2-candidate.md`."""
    contract = (
        FROZEN_STAMP
        + "# X Contract - v1 (FROZEN 2026-09-06)\n\n"
        "clause\n\n"
        "## Changelog\n\n"
        "- **2026-09-06 -- v1 (FROZEN 2026-09-06).** See "
        "contracts/x.v2-candidate.mdx for the rendered version.\n"
    )
    _write(tmp_path, "contracts/x.v1.md", contract)
    _write(tmp_path, "contracts/x.v2-candidate.md", SPENT_CANDIDATE)
    config = _config()

    decision = evaluate_tool_pre(
        "write_file",
        {"file_path": "contracts/x.v1.md", "content": "amended clause"},
        config,
        str(tmp_path),
    )

    assert decision.result.action == "continue", decision.result.reason
    assert any(name == "converge:guard_allowed_ratified" for name, _ in decision.events)


def test_w8_changelog_records_candidate_unit_table(tmp_path: Path) -> None:
    """Direct unit coverage of `_changelog_records_candidate`, pinning the
    exact-token rule independent of the full `evaluate_tool_pre` plumbing."""
    from amplifier_module_hooks_candidate_guard.guard import (
        _changelog_records_candidate,
    )

    rel = "contracts/x.v2-candidate.md"
    cases: list[tuple[str, bool]] = [
        ("Amendment landed from `contracts/x.v2-candidate.md`.", True),
        ("See the backup at contracts/x.v2-candidate.md.bak instead.", False),
        ("See notes/x.v2-candidate.md for background.", False),
        ("Amendment landed from contracts/x.v2-candidate.md.", True),
        ("See [it](contracts/x.v2-candidate.md) here.", True),
        ("See contracts/x.v2-candidate.mdx instead.", False),
        ("No mention of any candidate here.", False),
        ("(contracts/x.v2-candidate.md)", True),
    ]
    for changelog_text, expected in cases:
        assert _changelog_records_candidate(changelog_text, rel) is expected, (
            changelog_text,
            expected,
        )
