import json

import pytest

from amplifier_core import AmplifierSession, ModuleCoordinator

from amplifier_module_hooks_supervisor_entry import mount
from amplifier_module_hooks_supervisor_entry.observe import CAPABILITY
from test_observation import Public

pytestmark = pytest.mark.asyncio


def session(parent=None):
    return AmplifierSession({"session": {"orchestrator": "fixture", "context": "fixture"}},
                            session_id="fixture-session", parent_id=parent)


async def test_opt_in_same_session_only_preserves_tools_and_cleanup():
    s = session()
    c = s.coordinator
    public = Public()
    c.register_capability("session.working_dir", "/work/example")
    c.register_capability(CAPABILITY, public)
    tools = c.get("tools")
    unregister = await mount(c, {"enabled": True, "role": "supervisor"})
    foreign = await c.hooks.emit("prompt:submit", {"session_id": "foreign", "parent_id": s.session_id})
    assert foreign.action == "continue" and not public.calls
    result = await c.hooks.emit("prompt:submit", {})
    assert result.action == "inject_context" and result.ephemeral is True
    assert json.loads(result.context_injection.split("\n", 1)[1])["facts"]["status"] == "matched"
    assert c.get("tools") == tools
    unregister()
    assert (await c.hooks.emit("prompt:submit", {})).action == "continue"


@pytest.mark.parametrize("config", [{}, {"enabled": True}, {"enabled": True, "role": "manager"}])
async def test_not_enabled_for_unrelated_or_manager_composition(config):
    c = session().coordinator
    assert await mount(c, config) is None
    assert (await c.hooks.emit("prompt:submit", {})).action == "continue"


@pytest.mark.parametrize("c", [None, "child"])
async def test_inherited_hook_skips_children_forks_and_unknown_lineage(c):
    coordinator = ModuleCoordinator() if c is None else session("parent").coordinator
    public = Public()
    coordinator.register_capability(CAPABILITY, public)
    await mount(coordinator, {"enabled": True, "role": "supervisor"})
    assert (await coordinator.hooks.emit("prompt:submit", {})).action == "continue"
    assert public.calls == []


async def test_capability_is_resolved_at_prompt_not_mount_and_observation_refreshes():
    c = session().coordinator
    c.register_capability("session.working_dir", "/work/example")
    await mount(c, {"enabled": True, "role": "supervisor"})
    first = await c.hooks.emit("prompt:submit", {})
    assert 'transport_unavailable' in first.context_injection
    public = Public()
    c.register_capability(CAPABILITY, public)
    second = await c.hooks.emit("prompt:submit", {})
    assert 'none_recorded' in second.context_injection
    public.selected(withdrawn=True)
    third = await c.hooks.emit("prompt:submit", {})
    assert 'withdrawn' in third.context_injection and 'none_recorded' not in third.context_injection


@pytest.mark.parametrize("seconds", [0, -1, 6, float("nan"), True])
async def test_invalid_deadline_is_refused(seconds):
    with pytest.raises(ValueError):
        await mount(session().coordinator, {"enabled": True, "role": "supervisor", "deadline_seconds": seconds})
