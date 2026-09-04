"""The live half of the composition.v1 kit -- rules 3b, 6b and 6c.

Two of composition.v1's promises are about a RUNNING session, not about files
on disk, and until 2026-09-04 the kit declined both: rule 3b reported "needs a
live Amplifier session; this kit reads files only" and rule 6b "needs two live
Amplifier sessions (Converge plus unrelated work) side by side". A pinned
decline is honest, and it is still an unasserted promise -- and the second of
the two is the promise behind ``PINS.md``'s standing rule, measured once by hand
on 2026-09-02 and re-taken by nothing since.

This module gives both an actual runner.

The split of labour
-------------------
``run.py`` never imports Amplifier. This module finds the interpreter the
installed ``amplifier`` CLI runs on (from the shebang of the ``amplifier`` on
PATH) and executes ``_live_child.py`` with it, one JSON request in, one JSON
line out. So the kit keeps its single declared dependency and still gets to
stand up real sessions.

What "a real verdict" means here
--------------------------------
* **3b** stands up ONE real session on the target's own bundle and asks what it
  composed. Reached means composed: an agent file on disk that no ``agents:``
  block pulls in is discoverable and unreachable, and only the live roster
  tells the two apart.
* **6b** stands up a real UNRELATED session on the lean base -- the control --
  and then the same unrelated session again with the target installed beside
  it, once per install path the target declares -- the treatments. The
  spawned-helper tool surface for each is computed by Amplifier's own
  ``apply_spawn_tool_policy``. The promise holds when installing the target
  takes nothing away from the neighbour.

  The control is what makes the verdict mean anything. A host may already carry
  a session-wide spawn policy of its own (one did, on the machine this was
  built on -- an older Converge release installed as an app bundle was stripping
  ``tool-bash``, ``tool-delegate`` and ``tool-skills`` from every spawned helper
  in every session). Measuring only the treatment would blame the target for
  the host's own setting, or -- worse -- report a green because the tools were
  already gone before the target arrived.
* **6c** is the half that isolation hides. 6b composes the WORKING TREE, so it
  reports what the next release will do; it cannot see what the release a user
  ALREADY installed is doing, and on 2026-09-04 those disagreed: this tree was
  clean, 6a and 6b both PASSed, and a published sibling release of the same
  product -- app-installed on the same machine -- was stripping all three tools
  from every spawned helper in every session on it (converge-w3v). 6c stands up
  the unrelated session the way the HOST actually composes it (the lean base
  plus the host's whole app-bundle list, exactly as ``runtime/config.py`` hands
  ``get_app_bundles()`` to ``load_and_prepare_bundle``), and when that session
  is contaminated it loads each app entry alone to name the one that carries
  the policy.

  Attribution is what keeps 6c from being a rumour. It judges this repository's
  product only: a contaminated host whose carrier is a FOREIGN bundle is
  reported as a SKIP naming that bundle, never as this repository's failure.

When it cannot run
------------------
Every path that cannot reach a verdict returns SKIP naming the **exact** missing
capability (see ``MISSING``), never a fabricated PASS. That is the same rule the
file-reading half has always followed.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CHILD = HERE / "_live_child.py"

#: The lean base composition.v1 Core 1 names -- and, for rule 6b, the
#: "other work" whose session must come through installation unharmed.
LEAN_BASE_URI = (
    "git+https://github.com/microsoft/amplifier-foundation"
    "@main#subdirectory=bundles/anchors/bundle.md"
)
LEAN_BASE_NAMESPACE = "anchors"

#: Set to "0" to decline the live probes deliberately (offline, or a run that
#: must not touch the network). All three live rules then SKIP naming this
#: variable.
ENV_TOGGLE = "AMPLIFIER_COMPOSITION_KIT_LIVE"

#: Whitespace-separated bundle URIs that REPLACE the host's own app-bundle list
#: for rule 6c. The kit's test seam, and the only way the host half can be given
#: a negative fixture -- a rule nobody can make fail proves nothing. Unset (the
#: normal case) means "ask the installed CLI"; set-but-empty means "a host that
#: installs nothing", which 6c declines rather than passes.
ENV_APP_BUNDLES = "AMPLIFIER_COMPOSITION_KIT_APP_BUNDLES"

PROBE_TIMEOUT_S = 900

#: The named missing capabilities. A SKIP quotes one of these verbatim, so
#: "why did this decline?" always has a specific answer rather than a mood.
MISSING = {
    "cli": (
        "no `amplifier` on PATH -- the live probe stands up sessions with the "
        "installed CLI's own interpreter, and there is none to find"
    ),
    "interpreter": (
        "the `amplifier` on PATH is not a Python entry point (no readable "
        "`#!` line), so the interpreter that can import amplifier_app_cli "
        "could not be identified"
    ),
    "app": (
        "the installed Amplifier's interpreter cannot import "
        "amplifier_app_cli.lib.bundle_loader -- the live probe needs the app "
        "package, not just amplifier_core"
    ),
    "disabled": f"live probing switched off by {ENV_TOGGLE}=0",
    "timeout": (
        f"the live probe did not finish within {PROBE_TIMEOUT_S}s -- a first "
        "run fetches the lean base, which needs the network"
    ),
    "no_bundle": "no bundle.md at the repository root -- there is no session to stand up",
    "child": "the live probe returned no parsable result",
}

SENTINEL = "LIVE-RESULT "

#: Module id -> the plain word composition.v1 Core 6 uses for it.
PROMISED_TOOLS = {
    "tool-bash": "shell",
    "tool-delegate": "delegation",
    "tool-skills": "skills",
}


# --------------------------------------------------------------------------- #
# finding the interpreter that can import the app                             #
# --------------------------------------------------------------------------- #
def find_interpreter() -> tuple[str | None, str | None]:
    """(interpreter, missing-key). Exactly one of the two is None."""
    amp = shutil.which("amplifier")
    if not amp:
        return None, "cli"
    try:
        first = Path(amp).read_text(encoding="utf-8", errors="replace").splitlines()[:1]
    except OSError:
        return None, "interpreter"
    if not first or not first[0].startswith("#!"):
        return None, "interpreter"
    interp = first[0][2:].strip().split()
    # `#!/usr/bin/env python3` -> take the argument, not `env`.
    exe = interp[-1] if interp and Path(interp[0]).name == "env" else (interp[0] if interp else "")
    if not exe or not Path(exe).exists():
        return None, "interpreter"
    probe = subprocess.run(  # noqa: S603
        [exe, "-c", "import amplifier_app_cli.lib.bundle_loader"],
        capture_output=True, text=True, timeout=120, check=False,
    )
    if probe.returncode != 0:
        return None, "app"
    return exe, None


# --------------------------------------------------------------------------- #
# the target's own facts, read from files (the caller passes them in)          #
# --------------------------------------------------------------------------- #
def install_paths(root: Path, behaviors: list) -> list:
    """Every path a user could install this repository by, as file:// URIs.

    composition.v1 Core 5 fixes the count at two -- the root bundle and the
    standalone behavior -- so the neighbour promise is tested once per path.
    A promise kept on one install path and broken on the other is broken.
    """
    uris = []
    b = root / "bundle.md"
    if b.is_file():
        uris.append("file://" + str(b.resolve()))
    for p in behaviors:
        uris.append("file://" + str(Path(p).resolve()))
    return uris


# --------------------------------------------------------------------------- #
# running it                                                                   #
# --------------------------------------------------------------------------- #
class LiveProbe:
    """One subprocess, both live rules.

    Constructed once per kit run; ``session_row`` and ``neighbour_row`` read
    the same captured result, so standing up sessions is paid for once.
    """

    def __init__(self, root: Path, own_agents: list, behaviors: list,
                 bundle_names: list | None = None):
        self.root = root.resolve()
        self.own_agents = sorted(own_agents)
        self.paths = install_paths(self.root, behaviors)
        #: The names this repository's product answers to -- its root bundle's
        #: name and each behavior's. Rule 6c matches them against the host's
        #: app-bundle URIs to tell "this product's own release" from a
        #: neighbour's bundle, so a contaminated host is never blamed on the
        #: wrong repository.
        self.bundle_names = sorted({n for n in (bundle_names or []) if len(n) >= 4})
        self.missing: str | None = None
        self.raw: dict = {}
        self._run()

    def owns(self, uri: str) -> bool:
        """Does this URI name this repository's product?"""
        return any(
            re.search(rf"\b{re.escape(n)}\b", uri, re.I) for n in self.bundle_names
        )

    # -- the mechanics ----------------------------------------------------- #
    def _run(self) -> None:
        if os.environ.get(ENV_TOGGLE, "1").strip() == "0":
            self.missing = "disabled"
            return
        if not (self.root / "bundle.md").is_file():
            self.missing = "no_bundle"
            return
        exe, missing = find_interpreter()
        if missing:
            self.missing = missing
            return
        request = {
            "root": str(self.root),
            "bundle_uri": "file://" + str((self.root / "bundle.md").resolve()),
            "lean_base_uri": LEAN_BASE_URI,
            "install_paths": self.paths,
        }
        injected = os.environ.get(ENV_APP_BUNDLES)
        if injected is not None:
            request["host_app_bundles"] = injected.split()
        try:
            proc = subprocess.run(  # noqa: S603
                [str(exe), str(CHILD)],
                input=json.dumps(request),
                capture_output=True, text=True,
                timeout=PROBE_TIMEOUT_S, check=False,
            )
        except subprocess.TimeoutExpired:
            self.missing = "timeout"
            return
        for line in proc.stdout.splitlines():
            if line.startswith(SENTINEL):
                try:
                    self.raw = json.loads(line[len(SENTINEL):])
                except json.JSONDecodeError:
                    continue
        if not self.raw:
            self.missing = "child"

    def _skip(self, extra: dict | None = None) -> tuple:
        reason = MISSING[self.missing or "child"]
        return "SKIP", reason, {"reason": reason, **(extra or {})}

    # -- rule 3b ------------------------------------------------------------ #
    def session_row(self) -> tuple:
        """Core 3, live half: does a real session reach both helper families?

        Two halves, both required: a helper from the lean base, and one of the
        repository's own. The second is the one file-reading cannot judge --
        rule 3a proves the helper carries its rulebook, and a helper can carry
        a perfect rulebook and still never be composed into a session.
        """
        if self.missing:
            return self._skip()
        if "session_error" in self.raw:
            err = self.raw["session_error"]
            return "FAIL", f"a session on this repository could not be stood up: {err}", {
                "session_error": err
            }
        s = self.raw.get("session") or {}
        roster = s.get("roster") or []
        mounted = s.get("mounted_tool_names") or []
        lean = [a for a in roster if a.startswith(LEAN_BASE_NAMESPACE + ":")]
        own = [a for a in roster if a in self.own_agents]
        has_delegate = "delegate" in mounted
        extra = {
            "roster_size": len(roster),
            "lean_base_helpers": lean,
            "own_helpers_composed": own,
            "own_helpers_on_disk": self.own_agents,
            "delegation_tool_mounted": has_delegate,
        }
        problems = []
        if not has_delegate:
            problems.append("the session mounts no delegation tool, so no helper is reachable at all")
        if not lean:
            problems.append(
                f"no lean-base helper in the session's roster of {len(roster)} "
                f"(nothing namespaced '{LEAN_BASE_NAMESPACE}:')"
            )
        if self.own_agents and not own:
            problems.append(
                f"none of this repository's own {len(self.own_agents)} helper(s) "
                f"{self.own_agents} is composed into the session -- they are "
                "discoverable on disk and unreachable from a session"
            )
        if not self.own_agents:
            problems.append("this repository defines no helpers of its own under agents/")
        if problems:
            return "FAIL", "; ".join(problems), extra
        return "PASS", (
            f"a real session on this repository reaches the lean base's {lean[0]} "
            f"and its own {own[0]} (roster of {len(roster)}, delegation tool mounted)"
        ), extra

    # -- rule 6b ------------------------------------------------------------ #
    def neighbour_row(self) -> tuple:
        """Core 6, live half: installing this beside other work takes nothing.

        Control: an unrelated session on the lean base alone. Treatment: the
        same unrelated session with this repository installed beside it, once
        per install path. The verdict is the difference between them, because
        only the difference is this repository's doing.
        """
        if self.missing:
            return self._skip()
        if "neighbour_error" in self.raw:
            err = self.raw["neighbour_error"]
            return "FAIL", f"the unrelated control session could not be stood up: {err}", {
                "neighbour_error": err
            }
        n = self.raw.get("neighbour") or {}
        control = n.get("control") or {}
        c_tools = set(control.get("helper_tools") or [])
        c_promised = sorted(m for m in PROMISED_TOOLS if m in c_tools)
        rows, lost_any = [], []
        for t in n.get("treatments") or []:
            row = {"install_path": t.get("install_path")}
            if "error" in t:
                row["status"] = "SKIP"
                row["detail"] = f"this install path could not be composed: {t['error']}"
                rows.append(row)
                continue
            t_tools = set(t.get("helper_tools") or [])
            lost = sorted(m for m in c_promised if m not in t_tools)
            row["spawn_policy_seen"] = t.get("spawn")
            row["helper_tools"] = sorted(t_tools)
            row["lost"] = lost
            row["status"] = "FAIL" if lost else "PASS"
            row["detail"] = (
                "the neighbour's helper loses "
                + ", ".join(f"{PROMISED_TOOLS[m]} ({m})" for m in lost)
                if lost else
                "the neighbour's helper keeps "
                + ", ".join(f"{PROMISED_TOOLS[m]} ({m})" for m in c_promised)
            )
            if lost:
                lost_any.append(row)
            rows.append(row)
        extra = {
            "control_helper_tools": sorted(c_tools),
            "control_promised_tools_present": c_promised,
            "control_spawn_policy": control.get("spawn"),
            "treatments": rows,
        }
        if not c_promised:
            return "SKIP", (
                "the control session's spawned helper already carries none of "
                f"{sorted(PROMISED_TOOLS)} before this repository is installed, so "
                "installing it cannot be shown to take anything away -- there is "
                "nothing left to lose. Baseline: "
                f"{sorted(c_tools)}"
            ), {"reason": "control baseline carries none of the promised tools", **extra}
        if lost_any:
            where = "; ".join(f"{r['install_path']}: {r['detail']}" for r in lost_any)
            return "FAIL", (
                f"{len(lost_any)} of {len(rows)} install path(s) strip tools from an "
                f"unrelated session's helper -- {where}"
            ), extra
        measured = [r for r in rows if r["status"] == "PASS"]
        if not measured:
            return "SKIP", (
                "none of this repository's install paths could be composed onto the "
                "unrelated control session, so the neighbour promise was not measured"
            ), {"reason": "no install path composed", **extra}
        return "PASS", (
            f"across {len(measured)} install path(s), an unrelated session's spawned "
            f"helper keeps "
            + ", ".join(f"{PROMISED_TOOLS[m]}" for m in c_promised)
            + f" ({', '.join(c_promised)}) -- control and treatment measured side by side"
        ), extra


    # -- rule 6c ------------------------------------------------------------ #
    def host_row(self) -> tuple:
        """Core 6, host half: is the promise kept where this is INSTALLED?

        6b composes the working tree, so it reports what the next release will
        do to a neighbour. This asks what the release already on the host is
        doing to one -- the question that went unasked while a published
        sibling stripped three tools from every session on this machine.

        The rule judges THIS repository's product. A host whose promise is
        broken by a foreign bundle declines with that bundle named: blaming
        this repository for a neighbour's setting is the same mis-attribution
        rule 6b's control exists to prevent.
        """
        if self.missing:
            return self._skip()
        if "host_error" in self.raw:
            err = self.raw["host_error"]
            return "FAIL", f"the host's own session could not be composed: {err}", {
                "host_error": err
            }
        h = self.raw.get("host") or {}
        app = h.get("app_bundles") or []
        source = h.get("app_source") or "unknown"
        baseline = h.get("baseline") or sorted(PROMISED_TOOLS)
        extra = {
            "app_bundle_count": len(app),
            "app_bundle_source": source,
            "app_bundles_naming_this_repository": [u for u in app if self.owns(u)],
            "host_spawn_policy": h.get("spawn"),
            "host_helper_tools": sorted(h.get("helper_tools") or []),
            "host_lost": h.get("lost") or [],
            "baseline_promised_tools": baseline,
            "attribution": h.get("attribution"),
        }
        if not self.bundle_names:
            reason = (
                "this repository declares no bundle name, so an app-installed "
                "release of it cannot be told apart from a neighbour's bundle"
            )
            return "SKIP", reason, {"reason": reason, **extra}
        if not app:
            reason = (
                f"this host composes no app bundles ({source}), so there is no "
                "installed-beside-other-work state to measure"
            )
            return "SKIP", reason, {"reason": reason, **extra}
        mine = extra["app_bundles_naming_this_repository"]
        if not mine:
            reason = (
                f"no app bundle on this host names {self.bundle_names} "
                f"({len(app)} installed, {source}), so this repository is not "
                "installed beside other work here"
            )
            return "SKIP", reason, {"reason": reason, **extra}
        spawn, lost = h.get("spawn"), extra["host_lost"]
        if not spawn and not lost:
            return "PASS", (
                f"with {len(app)} app bundle(s) composed -- {len(mine)} of them this "
                f"repository's -- an unrelated session's mount plan carries no "
                f"session-wide spawn policy and its spawned helper keeps "
                + ", ".join(f"{PROMISED_TOOLS[m]} ({m})" for m in baseline)
            ), extra
        carriers = [r for r in (h.get("attribution") or []) if r.get("spawn")]
        ours = [r for r in carriers if self.owns(r["uri"])]
        harm = (
            "the neighbour's helper loses "
            + ", ".join(f"{PROMISED_TOOLS[m]} ({m})" for m in lost)
            if lost else
            f"the host session carries a session-wide spawn policy {spawn}"
        )
        if ours:
            where = "; ".join(f"{r['uri']} -> spawn {r['spawn']}" for r in ours)
            return "FAIL", (
                f"on this host {harm} -- carried by {len(ours)} app-installed "
                f"release(s) of this repository: {where}"
            ), extra
        if carriers:
            where = "; ".join(f"{r['uri']} -> spawn {r['spawn']}" for r in carriers)
            reason = (
                f"the neighbour promise IS broken on this host ({harm}), but no "
                f"app bundle naming {self.bundle_names} carries the policy -- it "
                f"comes from {where}, which this rule may not blame on this "
                "repository"
            )
            return "SKIP", reason, {"reason": reason, **extra}
        reason = (
            f"the neighbour promise IS broken on this host ({harm}) and no app "
            f"bundle of the {len(app)} installed declares a spawn policy of its "
            "own, so the policy could not be attributed to any of them"
        )
        return "SKIP", reason, {"reason": reason, **extra}


def probe(root: Path, own_agents: list, behaviors: list,
          bundle_names: list | None = None) -> LiveProbe:
    return LiveProbe(root, own_agents, behaviors, bundle_names)


if __name__ == "__main__":  # pragma: no cover - a hand tool for one repo
    r = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    p = probe(r, [], [])
    print(json.dumps(
        {"3b": p.session_row(), "6b": p.neighbour_row(), "6c": p.host_row()},
        indent=2, default=str,
    ))
