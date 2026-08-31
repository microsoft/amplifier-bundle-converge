"""Unit tests for hooks-candidate-guard.

Follows docs/design/hooks-candidate-guard-spec.md §5.1 Test Plan (U1-U10).
All tests call the pure functions in ``guard.py`` directly with mock
``tool:pre`` data (HOOK_CONTRACT.md "Testing" pattern) -- no live session.
"""

from __future__ import annotations

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
