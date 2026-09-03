"""Candidate Guard Hook -- structural enforcement of PROTOCOL.md §5, pillar 3.

Registers a single handler on ``tool:pre`` (priority 5, low = early --
HOOKS_API.md "Parameters -> priority") that denies a direct write/edit/patch
(or a bash write-laundering attempt) targeting a FROZEN contract file or
``VISION.md``. Amendments must go through a sibling proposal file -- named
``<contract>.vN-candidate.md`` (contracts/documents.v1 clause 8) or the legacy
``CANDIDATE-<topic>.md`` (PROTOCOL.md §5), both admitted -- and owner
ratification (see the module README and
``docs/design/hooks-candidate-guard-spec.md`` for the full design).

All the actual decision logic lives in ``guard.py`` as pure, coordinator-free
functions -- this module is just the thin async/coordinator plumbing: build
config, resolve cwd, register on ``tool:pre``, emit whatever events the pure
evaluator asked for, and return an unregister callable from ``mount()``.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from amplifier_core import HookResult

from .guard import GuardConfig, evaluate_tool_pre

logger = logging.getLogger(__name__)

__all__ = ["CandidateGuardHooks", "GuardConfig", "evaluate_tool_pre", "mount"]


class CandidateGuardHooks:
    """Async coordinator-facing wrapper around the pure guard evaluator."""

    def __init__(self, config: GuardConfig, coordinator: Any, cwd: str) -> None:
        self.config = config
        self.coordinator = coordinator
        self.cwd = cwd

    async def handle_tool_pre(self, _event: str, data: dict[str, Any]) -> HookResult:
        """Evaluate a ``tool:pre`` event.

        Outer try/except: any unexpected bug in the handler plumbing itself
        (as opposed to an evaluation error already handled by guard.py's own
        fail-closed logic) must not crash the kernel -- but must also not
        silently defeat the ratchet. We log loudly and fail closed here too,
        since this hook is a validation gate (HOOKS_API.md "Error Handling":
        "unless explicitly intended ... validation failure should return
        deny on purpose").
        """
        tool_name = data.get("tool_name", "")
        tool_input = data.get("tool_input", {}) or {}

        try:
            decision = evaluate_tool_pre(tool_name, tool_input, self.config, self.cwd)
        except Exception as exc:
            logger.warning(
                "candidate-guard: unexpected error evaluating tool_name=%r; "
                "failing closed: %s",
                tool_name,
                exc,
                exc_info=True,
            )
            return HookResult(
                action="deny",
                reason=(
                    "converge/candidate-guard: internal error while evaluating this "
                    f"tool call ({exc}). Failing closed (spec §2.8)."
                ),
                user_message="Candidate guard internal error — failing closed.",
                user_message_level="error",
            )

        for event_name, payload in decision.events:
            try:
                await self.coordinator.hooks.emit(event_name, payload)
            except Exception:
                logger.debug(
                    "candidate-guard: failed to emit %s", event_name, exc_info=True
                )

        return decision.result


async def mount(coordinator: Any, config: dict[str, Any] | None = None) -> Any:
    """Mount the candidate-guard hook.

    Args:
        coordinator: The Amplifier coordinator instance.
        config: Optional config dict -- see GuardConfig for every key and
            its default (spec §2.5/§2.7/§3.1).

    Returns:
        Cleanup function that unregisters the handler (HOOK_CONTRACT.md
        "Entry Point Pattern").
    """
    guard_config = GuardConfig.from_dict(config)

    working_dir: str | None = None
    try:
        working_dir = coordinator.get_capability("session.working_dir")
    except Exception:  # noqa: BLE001 -- capability lookup is best-effort
        working_dir = None
    cwd = str(working_dir) if working_dir else os.getcwd()

    hooks = CandidateGuardHooks(guard_config, coordinator, cwd=cwd)

    unregister = coordinator.hooks.register(
        "tool:pre",
        hooks.handle_tool_pre,
        priority=5,
        name="candidate-guard",
    )

    coordinator.register_contributor(
        "observability.events",
        "hooks-candidate-guard",
        lambda: [
            "converge:guard_blocked",
            "converge:guard_allowed_ratified",
            "converge:guard_unlock_used",
        ],
    )

    logger.info(
        "hooks-candidate-guard mounted: enabled=%s guarded_globs=%s cwd=%s",
        guard_config.enabled,
        guard_config.guarded_globs,
        cwd,
    )

    def cleanup() -> None:
        if callable(unregister):
            unregister()
        logger.info("hooks-candidate-guard unmounted")

    return cleanup
