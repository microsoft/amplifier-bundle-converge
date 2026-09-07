#!/usr/bin/env python3
"""Render this repository's own skills-visibility block, twice.

Answers one question with the SHIPPED renderer rather than by reading YAML:
which skills does a real session on `bundle.md` put in the always-on catalog
the model sees on every request -- with the `converge-manager` mode INACTIVE,
and again with it ACTIVE.

How it stays honest, and how it stays safe
------------------------------------------
* It stands up a REAL session (``load_and_prepare_bundle`` -> ``create_session``
  -> ``initialize()``) and asks the mounted ``tool-skills`` instance for its
  effective catalog, then renders it through the very hook that writes the
  block (``SkillsVisibilityHook._format_skills_list``). Nothing here
  re-implements the renderer, so a change in it cannot silently pass this.
* Mode activation goes through the real path: set ``active_mode`` and emit
  ``mode:activated`` on the session's own hook bus, which is what ``tool-mode``
  does. hooks-mode then applies ``contributes`` via ``RuntimeOverlay``, and
  tool-skills picks the result up through the ``runtime_skill_overlay``
  capability. No hand-built overlay.
* It NEVER runs the ``amplifier`` CLI, and never sets ``AMPLIFIER_HOME``.
  Bundles load through a private ``BundleRegistry(home=...)`` -- a throwaway
  directory holding a COPY of the real registry.json and a SYMLINK to the real
  cache -- with ``install_deps=False``. So it registers nothing on the host and
  installs nothing: no package manager runs, no editable ``.pth`` file is
  rewritten. (Same private-home shape as ``conformance/composition/``, and for
  the same reason: a probe must leave no trace on the machine it measures.)

Run it:  python3 docs/lanes/qtwo-converge-catalog-reduction/render_catalog.py

It re-executes itself under the interpreter the installed ``amplifier`` runs
on (read from that entry point's ``#!`` line), because only that interpreter
can import ``amplifier_app_cli``.

Prints one JSON object: per phase, the skill names in the catalog, the count,
and the rendered block; plus a real ``load_skill`` attempt for each of the five
converge skills in each phase.
"""

from __future__ import annotations

import asyncio
import atexit
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
MODE = "converge-manager"

# The lean base composes context-intelligence, whose hook config carries the
# placeholder `${AMPLIFIER_CONTEXT_INTELLIGENCE_LOG_LEVEL:INFO}`. Module
# validation rejects the literal placeholder when the variable is unset, which
# a normal CLI session never hits. Supply the default this probe's own
# subprocess is missing; it changes nothing about the skills catalog.
os.environ.setdefault("AMPLIFIER_CONTEXT_INTELLIGENCE_LOG_LEVEL", "INFO")
CONVERGE_SKILLS = [
    "freeze-bar",
    "lane-brief",
    "ledger-disposition",
    "proposing-a-change",
    "seam-test",
]


# --------------------------------------------------------------------------- #
# re-exec under the interpreter that can import the app                        #
# --------------------------------------------------------------------------- #
def _reexec_if_needed() -> None:
    try:
        import amplifier_app_cli.lib.bundle_loader  # noqa: F401,PLC0415

        return
    except Exception:  # noqa: BLE001
        pass
    if os.environ.get("_CONVERGE_CATALOG_REEXEC"):
        sys.exit("cannot import amplifier_app_cli even after re-exec")
    amp = shutil.which("amplifier")
    if not amp:
        sys.exit("no `amplifier` on PATH -- cannot find the interpreter to use")
    first = Path(amp).read_text(encoding="utf-8", errors="replace").splitlines()[:1]
    if not first or not first[0].startswith("#!"):
        sys.exit(f"{amp} is not a Python entry point (no `#!` line)")
    parts = first[0][2:].strip().split()
    exe = parts[-1] if parts and Path(parts[0]).name == "env" else parts[0]
    env = dict(os.environ, _CONVERGE_CATALOG_REEXEC="1")
    raise SystemExit(
        subprocess.run([exe, str(Path(__file__).resolve()), *sys.argv[1:]], env=env, check=False).returncode
    )


_reexec_if_needed()


# --------------------------------------------------------------------------- #
# a private amplifier home: copy the registry, share the cache, throw it away  #
# --------------------------------------------------------------------------- #
def _private_home() -> Path:
    from amplifier_foundation.paths.resolution import get_amplifier_home  # noqa: PLC0415

    real = get_amplifier_home()
    home = Path(tempfile.mkdtemp(prefix="converge-catalog-probe-home-"))
    (home / "cache").symlink_to(real / "cache", target_is_directory=True)
    registry_json = real / "registry.json"
    if registry_json.is_file():
        shutil.copy2(registry_json, home / "registry.json")
    atexit.register(shutil.rmtree, home, True)
    return home


async def _session():
    from amplifier_app_cli.lib.bundle_loader import (  # noqa: PLC0415
        AppBundleDiscovery,
        load_and_prepare_bundle,
    )
    from amplifier_app_cli.paths import get_bundle_search_paths  # noqa: PLC0415
    from amplifier_foundation import BundleRegistry  # noqa: PLC0415

    discovery = AppBundleDiscovery(
        search_paths=get_bundle_search_paths(),
        registry=BundleRegistry(home=_private_home()),
    )
    prepared = await load_and_prepare_bundle(
        "file://" + str(REPO / "bundle.md"), discovery, install_deps=False
    )
    # The same expansion the CLI applies to a composed bundle config
    # (amplifier_app_cli/runtime/config.py). Without it the lean base's
    # context-intelligence hook config keeps a literal
    # `${AMPLIFIER_CONTEXT_INTELLIGENCE_LOG_LEVEL:INFO}` and module validation
    # refuses to mount it -- a difference between this probe and a real
    # session, not a difference in the bundle. Applying it removes that gap.
    from amplifier_app_cli.runtime.config import expand_env_vars  # noqa: PLC0415

    prepared.mount_plan = expand_env_vars(prepared.mount_plan)
    session = await prepared.create_session(session_cwd=REPO)
    await session.initialize()
    return session, prepared.mount_plan


# --------------------------------------------------------------------------- #
# reading the block the way the session writes it                              #
# --------------------------------------------------------------------------- #
def _skills_tool(session):
    for name, tool in (session.coordinator.get("tools") or {}).items():
        if hasattr(tool, "get_effective_skills"):
            return name, tool
    return None, None


def _visibility_config(mount_plan: dict) -> dict:
    """This session's own `visibility:` config for tool-skills, or defaults."""
    for entry in mount_plan.get("tools") or []:
        if isinstance(entry, dict) and entry.get("module") == "tool-skills":
            return (entry.get("config") or {}).get("visibility", {}) or {}
    return {}


def _visibility_hook(session, mount_plan, tool):
    """A SkillsVisibilityHook built exactly as tool-skills' own mount builds it.

    The registered instance is not reachable through the Rust hook registry
    (it exposes handler names, not the bound objects), so the hook is
    constructed here with the same class, the same session config, the same
    coordinator and the same tool reference the mount path passes. The
    rendering code exercised is the shipped one, not a copy.
    """
    from amplifier_module_tool_skills.hooks import SkillsVisibilityHook  # noqa: PLC0415

    return SkillsVisibilityHook(
        tool.skills,
        _visibility_config(mount_plan),
        coordinator=session.coordinator,
        tool=tool,
    )


def _phase(session, hook, tool) -> dict:
    catalog = tool.get_effective_skills()
    block = hook._format_skills_list(catalog)  # noqa: SLF001 - the shipped renderer
    return {
        "count": len(catalog),
        "names": sorted(catalog),
        "converge_skills_present": sorted(n for n in CONVERGE_SKILLS if n in catalog),
        "block": block,
    }


async def _load_each(tool) -> dict:
    out = {}
    for name in CONVERGE_SKILLS:
        try:
            result = await tool.execute({"skill_name": name})
            ok = bool(getattr(result, "success", False))
            out[name] = {
                "loaded": ok,
                "detail": ("" if ok else str(getattr(result, "output", ""))[:200]),
            }
        except Exception as exc:  # noqa: BLE001 - reported, never swallowed
            out[name] = {"loaded": False, "detail": f"{type(exc).__name__}: {exc}"}
    return out


async def main() -> int:
    session, mount_plan = await _session()
    tool_name, tool = _skills_tool(session)
    if tool is None:
        print(json.dumps({"error": "no tool-skills tool mounted in this session"}, indent=2))
        return 2
    hook = _visibility_hook(session, mount_plan, tool)

    out: dict = {"bundle": "file://" + str(REPO / "bundle.md"), "skills_tool": tool_name, "mode": MODE}
    out["inactive"] = _phase(session, hook, tool)
    out["inactive"]["load_skill"] = await _load_each(tool)

    session.coordinator.session_state["active_mode"] = MODE
    await session.coordinator.hooks.emit("mode:activated", {"name": MODE})

    out["active"] = _phase(session, hook, tool)
    out["active"]["load_skill"] = await _load_each(tool)
    out["delta"] = out["active"]["count"] - out["inactive"]["count"]

    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
