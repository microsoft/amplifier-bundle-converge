"""Candidate Guard Hook -- structural enforcement of PROTOCOL.md §5, pillar 3.

Covers BOTH write paths a session can take (see the module README, "The two
write paths"):

1. ``tool:pre`` -- a single handler (priority 5, low = early; HOOKS_API.md
   "Parameters -> priority") that denies a direct write/edit/patch (or a bash
   write-laundering attempt) targeting a FROZEN contract file or ``VISION.md``.
   This is the path the orchestrator takes for every tool call an agent makes.
2. ``tools[name].execute`` -- the same evaluation, installed directly on the
   mounted tool instances. ``amplifier tool invoke`` calls ``execute()``
   itself and never emits ``tool:pre``, so a hook alone cannot see it. Mount
   order makes this possible: ``amplifier_core/_session_init.py`` mounts
   ``tools`` BEFORE ``hooks``, so every tool instance already exists in the
   coordinator when this hook mounts.

Amendments must go through a sibling proposal file -- named
``<contract>.vN-candidate.md`` (contracts/documents.v1 clause 8) or the legacy
``CANDIDATE-<topic>.md`` (PROTOCOL.md §5), both admitted -- and owner
ratification (see the module README and
``docs/design/hooks-candidate-guard-spec.md`` for the full design).

All the actual decision logic lives in ``guard.py`` as pure, coordinator-free
functions -- this module is just the thin async/coordinator plumbing: build
config, resolve cwd, register on ``tool:pre``, wrap the mounted tools, emit
whatever events the pure evaluator asked for, and return an unregister
callable from ``mount()``.
"""

from __future__ import annotations

import inspect
import logging
import os
from typing import Any

from amplifier_core import HookResult

from .guard import GuardConfig, evaluate_tool_pre

logger = logging.getLogger(__name__)

__all__ = [
    "CandidateGuardBlocked",
    "CandidateGuardHooks",
    "GuardConfig",
    "evaluate_tool_pre",
    "mount",
    "wrap_mounted_tools",
]

# Marker attribute stamped on a wrapped ``execute`` so a second mount() in the
# same session never double-wraps (which would evaluate twice and, worse, make
# unwrap order-dependent).
_WRAPPED_ATTR = "__converge_candidate_guard_wrapped__"
_ORIGINAL_ATTR = "__converge_candidate_guard_original__"


class CandidateGuardBlocked(PermissionError):
    """Raised when a guarded write is attempted via direct tool dispatch.

    A raise, not a returned error dict: ``amplifier tool invoke`` prints the
    exception and exits non-zero, so the refusal is fail-loud on a path that
    has no hook channel to carry ``user_message`` on.
    """


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


def _guarded_tool_names(config: GuardConfig) -> set[str]:
    """Every tool name whose ``execute`` is worth wrapping.

    Exactly the set ``evaluate_tool_pre`` can act on: the intercepted write
    tools, their Claude-Code-flavoured aliases, ``apply_patch`` (special-cased
    in the evaluator, so not necessarily in ``intercept_tools``) and -- when
    the bash scan is on -- the shell.
    """
    names = set(config.intercept_tools) | set(config.tool_name_aliases)
    names.add("apply_patch")
    if config.scan_bash:
        names.add(config.bash_tool_name)
    return names


def wrap_mounted_tools(
    tools: dict[str, Any] | None, config: GuardConfig, cwd: str
) -> list[tuple[Any, Any]]:
    """Install the guard on each mounted tool instance's own ``execute``.

    Closes the direct-dispatch path (``amplifier tool invoke``), which never
    emits ``tool:pre``. Returns the ``(instance, original_execute)`` pairs so
    ``mount()``'s cleanup can restore them exactly.

    Wrapping is per **instance**, never on the class: tool instances are
    mounted per session, so an instance-level attribute cannot leak the guard
    into an unrelated session that merely imports the same tool module.
    """
    restored: list[tuple[Any, Any]] = []
    if not config.wrap_tool_execute or not tools:
        return restored

    for tool_name in sorted(_guarded_tool_names(config)):
        instance = tools.get(tool_name)
        if instance is None:
            continue
        original = getattr(instance, "execute", None)
        if original is None or not callable(original):
            continue
        if getattr(original, _WRAPPED_ATTR, False):
            continue  # already wrapped by an earlier mount in this session

        def _make(name: str, inner: Any) -> Any:
            async def guarded_execute(*args: Any, **kw: Any):
                # The composed tools take one positional dict
                # (`async def execute(self, input: dict)`), but accept the
                # keyword spellings too rather than assume a call shape.
                data: dict[str, Any] = {}
                if args and isinstance(args[0], dict):
                    data = args[0]
                else:
                    for key in ("input", "tool_input", "arguments"):
                        value = kw.get(key)
                        if isinstance(value, dict):
                            data = value
                            break
                decision = evaluate_tool_pre(name, data, config, cwd)
                if decision.result.action == "deny":
                    raise CandidateGuardBlocked(
                        decision.result.reason
                        or "converge/candidate-guard: blocked by the "
                        "locked-contract guard."
                    )
                out = inner(*args, **kw)
                if inspect.isawaitable(out):
                    return await out
                return out

            setattr(guarded_execute, _WRAPPED_ATTR, True)
            setattr(guarded_execute, _ORIGINAL_ATTR, inner)
            return guarded_execute

        try:
            instance.execute = _make(tool_name, original)  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001 -- a read-only/slotted tool cannot be wrapped
            logger.warning(
                "candidate-guard: could not wrap execute() on tool %r -- the "
                "tool:pre path still guards it, but direct dispatch "
                "(amplifier tool invoke) will NOT be blocked for this tool.",
                tool_name,
                exc_info=True,
            )
            continue
        restored.append((instance, original))

    if restored:
        logger.info(
            "candidate-guard: wrapped execute() on %d mounted tool(s): %s",
            len(restored),
            ", ".join(sorted(_guarded_tool_names(config) & set(tools))),
        )
    return restored


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

    # Second write path -- direct dispatch, which never emits tool:pre.
    # Safe here because _session_init.py mounts tools BEFORE hooks, so the
    # coordinator's tool dict is already fully populated at this point.
    wrapped: list[tuple[Any, Any]] = []
    try:
        mounted_tools = coordinator.get("tools")
    except Exception:  # noqa: BLE001 -- capability lookup is best-effort
        mounted_tools = None
    if guard_config.wrap_tool_execute and not mounted_tools:
        logger.warning(
            "candidate-guard: no mounted tools visible at mount time -- the "
            "tool:pre path is still guarded, but direct dispatch "
            "(amplifier tool invoke) is NOT."
        )
    wrapped = wrap_mounted_tools(mounted_tools, guard_config, cwd)

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
        "hooks-candidate-guard mounted: enabled=%s guarded_globs=%s cwd=%s "
        "tools_wrapped=%d",
        guard_config.enabled,
        guard_config.guarded_globs,
        cwd,
        len(wrapped),
    )

    def cleanup() -> None:
        if callable(unregister):
            unregister()
        for instance, original in wrapped:
            try:
                instance.execute = original
            except Exception:  # noqa: BLE001 -- unmount must never raise
                logger.debug(
                    "candidate-guard: could not restore execute() on %r",
                    instance,
                    exc_info=True,
                )
        logger.info("hooks-candidate-guard unmounted")

    return cleanup
