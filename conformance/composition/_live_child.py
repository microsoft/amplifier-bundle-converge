"""The half of the live probe that runs *inside* the installed Amplifier.

``live.py`` (the kit's half) never imports Amplifier. It finds the interpreter
the installed ``amplifier`` CLI runs on and executes THIS file with it, handing
over one JSON request on stdin and reading one JSON line back. That split is
deliberate: ``run.py`` stays a file-reading script with one declared dependency,
and the live half is free to import the app the way the CLI itself does.

What it actually does, for each of the two live promises:

``session`` (composition.v1 Core 3, live half)
    Stands up a REAL session on the target bundle -- ``load_and_prepare_bundle``
    then ``create_session`` then ``initialize()``, the same three calls
    ``amplifier tool list -b <bundle>`` makes -- and reports the roster of
    helpers that session actually composed, plus whether it mounted a
    delegation tool at all. Composition is the point: an agent file on disk
    that no ``agents:`` block composes is DISCOVERABLE and unreachable, and
    the roster is where that difference shows.

``neighbour`` (composition.v1 Core 6, live half)
    Stands up a real UNRELATED session on the lean base alone (the control),
    then stands up the same unrelated session again with the target composed
    onto it by each of its own declared install paths (the treatments) -- the
    2026-09-02 measurement's control/treatment shape, re-taken. For each, the
    spawned-helper tool surface is computed by the SHIPPED
    ``apply_spawn_tool_policy`` -- the very function whose ``spawn`` handling
    stripped ``bash``, ``delegate`` and ``load_skill`` from an unrelated
    session's helper that day. Nothing here re-implements it.

``host`` (composition.v1 Core 6, host half)
    The same unrelated session AS THIS HOST ACTUALLY COMPOSES IT -- the lean
    base with the host's whole app-bundle list composed onto it, exactly the
    way ``runtime/config.py`` hands ``get_app_bundles()`` to
    ``load_and_prepare_bundle`` as ``compose_behaviors``. ``neighbour`` above
    measures what the WORKING TREE does; this measures what the RELEASE a user
    actually installed does, and the two are not the same repository state.
    Measured 2026-09-04 on the machine this was written on: the working tree
    was clean and a published sibling release of the same product, installed as
    an app bundle, was stripping all three tools from every spawned helper in
    every session on the host (converge-w3v).

    When that session is contaminated, every app entry is loaded on its own and
    asked for its top-level ``spawn`` -- attribution, so the verdict names the
    entry that carries the policy instead of the host in general. Loading is
    used rather than preparing: attribution needs the composed ``spawn`` key,
    not a module download.

Modules are prepared with ``install_deps=False``. This probe measures
COMPOSITION -- what lands in a session's mount plan -- not whether every
module's Python package installs, and installing a whole bundle's dependency
closure on every conformance run would trade a slow, network-dependent check
for no extra signal about the promise under test.

stdin  : one JSON request (see ``main``)
stdout : one line, ``LIVE-RESULT <json>``; anything else on the stream is noise
         from the loader and is ignored by the caller.
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

SENTINEL = "LIVE-RESULT "

#: The three tool modules composition.v1's neighbour promise names by hand:
#: "a helper in an unrelated session keeps its shell, delegation, and skills
#: tools". Module ids, because that is what a spawn policy filters on.
PROMISED = {
    "tool-bash": "shell",
    "tool-delegate": "delegation",
    "tool-skills": "skills",
}


def _tool_modules(plan: dict) -> list:
    return [t.get("module") for t in (plan.get("tools") or []) if isinstance(t, dict)]


def _discovery():
    from amplifier_app_cli.lib.bundle_loader import AppBundleDiscovery  # noqa: PLC0415
    from amplifier_app_cli.paths import get_bundle_search_paths  # noqa: PLC0415

    return AppBundleDiscovery(search_paths=get_bundle_search_paths())


async def _prepare(uri: str, compose: list | None):
    from amplifier_app_cli.lib.bundle_loader import (  # noqa: PLC0415
        load_and_prepare_bundle,
    )

    return await load_and_prepare_bundle(
        uri, _discovery(), compose_behaviors=compose or None, install_deps=False
    )


def _spawned_helper_tools(plan: dict) -> list:
    """The tool modules a spawned helper inherits, per the SHIPPED policy."""
    from amplifier_app_cli.agent_config import apply_spawn_tool_policy  # noqa: PLC0415

    return _tool_modules(apply_spawn_tool_policy(dict(plan)))


async def _session_probe(req: dict) -> dict:
    """Core 3, live half: what does a real session on this bundle reach?"""
    prepared = await _prepare(req["bundle_uri"], None)
    plan = prepared.mount_plan
    session = await prepared.create_session(session_cwd=Path(req["root"]))
    await session.initialize()
    mounted = session.coordinator.get("tools") or {}
    return {
        "bundle_uri": req["bundle_uri"],
        "roster": sorted((plan.get("agents") or {}).keys()),
        "mounted_tool_names": sorted(mounted.keys()),
        "spawn": plan.get("spawn"),
    }


async def _neighbour_probe(req: dict) -> dict:
    """Core 6, live half: control, then one treatment per install path."""
    control_plan = (await _prepare(req["lean_base_uri"], None)).mount_plan
    control = {
        "session_tools": _tool_modules(control_plan),
        "helper_tools": _spawned_helper_tools(control_plan),
        "spawn": control_plan.get("spawn"),
    }
    treatments = []
    for uri in req["install_paths"]:
        row = {"install_path": uri}
        try:
            plan = (await _prepare(req["lean_base_uri"], [uri])).mount_plan
        except Exception as exc:  # noqa: BLE001 - reported, never swallowed
            row["error"] = f"{type(exc).__name__}: {exc}"
        else:
            row["session_tools"] = _tool_modules(plan)
            row["helper_tools"] = _spawned_helper_tools(plan)
            row["spawn"] = plan.get("spawn")
        treatments.append(row)
    return {"control": control, "treatments": treatments}


def _app_bundles(req: dict) -> tuple[list, str]:
    """(the host's app-bundle list, where it came from).

    Normally asked of the SHIPPED accessor, so the list can never drift from
    what the CLI itself composes. ``host_app_bundles`` in the request replaces
    it -- that is the kit's own test seam, and the only way the host half can
    be given a negative fixture (a rule nobody can make fail proves nothing).
    """
    injected = req.get("host_app_bundles")
    if injected is not None:
        return list(injected), "injected (kit test seam)"
    from amplifier_app_cli.lib.settings import get_settings  # noqa: PLC0415

    return list(get_settings().get_app_bundles() or []), (
        "the installed CLI's own get_settings().get_app_bundles()"
    )


async def _attribute(uris: list) -> list:
    """Which app entries carry a session-wide ``spawn`` policy of their own.

    ``load_bundle`` rather than ``_prepare``: the question is which entry
    CONTRIBUTES the key, and ``to_mount_plan()`` answers it after the entry's
    own includes are composed -- so a policy hidden one include deep is still
    attributed to the entry a user would have to remove.
    """
    from amplifier_foundation import load_bundle  # noqa: PLC0415

    registry = _discovery().registry
    rows = []
    for uri in uris:
        row = {"uri": uri}
        try:
            bundle = await load_bundle(uri, registry=registry)
            row["spawn"] = (bundle.to_mount_plan() or {}).get("spawn")
        except Exception as exc:  # noqa: BLE001 - reported, never swallowed
            row["error"] = f"{type(exc).__name__}: {exc}"
        rows.append(row)
    return rows


async def _host_probe(req: dict, control_helper_tools: list | None) -> dict:
    """Core 6, host half: the unrelated session as THIS host composes it."""
    app, source = _app_bundles(req)
    baseline = [
        m for m in PROMISED
        if control_helper_tools is None or m in control_helper_tools
    ]
    out = {"app_bundles": app, "app_source": source, "baseline": baseline}
    if not app:
        return out
    plan = (await _prepare(req["lean_base_uri"], app)).mount_plan
    out["spawn"] = plan.get("spawn")
    out["session_tools"] = _tool_modules(plan)
    out["helper_tools"] = _spawned_helper_tools(plan)
    out["lost"] = [m for m in baseline if m not in out["helper_tools"]]
    if out["spawn"] or out["lost"]:
        out["attribution"] = await _attribute(app)
    return out


async def _run(req: dict) -> dict:
    out = {"ok": True}
    try:
        out["session"] = await _session_probe(req)
    except Exception as exc:  # noqa: BLE001
        out["session_error"] = f"{type(exc).__name__}: {exc}"
    try:
        out["neighbour"] = await _neighbour_probe(req)
    except Exception as exc:  # noqa: BLE001
        out["neighbour_error"] = f"{type(exc).__name__}: {exc}"
    try:
        control = ((out.get("neighbour") or {}).get("control") or {}).get("helper_tools")
        out["host"] = await _host_probe(req, control)
    except Exception as exc:  # noqa: BLE001
        out["host_error"] = f"{type(exc).__name__}: {exc}"
    return out


def main() -> int:
    """Read one JSON request on stdin; write one ``LIVE-RESULT`` line.

    Request keys:
      root              absolute path of the target repository
      bundle_uri        ``file://<root>/bundle.md`` -- the session under test
      lean_base_uri     the unrelated session's bundle (the lean base)
      install_paths     every path a user could install the target by
      host_app_bundles  optional; replaces the host's own app-bundle list
                        (the kit's test seam -- absent means ask the CLI)
    """
    try:
        req = json.loads(sys.stdin.read())
    except Exception as exc:  # noqa: BLE001
        sys.stdout.write(
            SENTINEL + json.dumps({"ok": False, "error": f"bad request: {exc}"}) + "\n"
        )
        return 2
    try:
        result = asyncio.run(_run(req))
    except Exception as exc:  # noqa: BLE001
        result = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    sys.stdout.write(SENTINEL + json.dumps(result, default=str) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
