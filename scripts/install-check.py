#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Converge install check — every declared dependency, present or missing.

`contracts/operation.v1.md` declares what Converge needs to run and what
breaks when a piece is absent. This command checks each one and, for every
absence, says plainly what degrades.

    ./scripts/install-check.py            # table on stderr, JSON on stdout
    ./scripts/install-check.py --json-only
    ./scripts/install-check.py --project converge   # also prove the queue is live

Exit code is 0 when nothing required is missing, 1 when something required is
absent. A check that cannot be performed reports SKIP with the reason and never
counts as a pass.

Nothing here installs, starts, or changes anything. It only looks.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from datetime import timezone
from pathlib import Path

OK = "OK"
MISSING = "MISSING"
SKIP = "SKIP"

REQUIRED = "required"
OPTIONAL = "optional"

CONTRACT = "operation.v1 — Declared dependencies (checked at install)"


# --------------------------------------------------------------------------
# plumbing
# --------------------------------------------------------------------------


@dataclass
class Context:
    """Everything a check is allowed to know about the machine it runs on."""

    repo_root: Path
    amplifier_home: Path
    project: str | None = None
    timeout: float = 60.0


@dataclass
class Result:
    """One check's verdict: a status and one line of evidence for it."""

    status: str
    detail: str
    extra: dict | None = None


@dataclass
class Check:
    ident: str
    name: str
    requirement: str
    degradation: str
    probe: str
    run: Callable[[Context], Result]


@dataclass
class Ran:
    """A finished command: return code, output, and why it never ran, if so."""

    code: int | None
    out: str
    err: str
    failure: str | None = None

    @property
    def ok(self) -> bool:
        return self.code == 0

    @property
    def text(self) -> str:
        return f"{self.out}\n{self.err}"


def run_command(ctx: Context, cmd: list[str], cwd: Path | None = None) -> Ran:
    """Run a command and never raise. A command that could not run says so."""
    try:
        done = subprocess.run(  # noqa: S603 - fixed argv, no shell
            cmd,
            capture_output=True,
            text=True,
            timeout=ctx.timeout,
            cwd=str(cwd) if cwd else None,
            check=False,
        )
    except FileNotFoundError:
        return Ran(None, "", "", failure=f"{cmd[0]} is not on PATH")
    except subprocess.TimeoutExpired:
        return Ran(
            None, "", "", failure=f"{cmd[0]} did not answer within {ctx.timeout:g}s"
        )
    except OSError as exc:  # pragma: no cover - defensive
        return Ran(None, "", "", failure=f"{cmd[0]} could not be run: {exc}")
    return Ran(done.returncode, done.stdout or "", done.stderr or "")


def squeeze(text: str) -> str:
    """Drop every space and escaped newline so wrapped output still matches."""
    return re.sub(r"\s+", "", text.replace("\\n", ""))


def first_line(text: str) -> str:
    for line in text.splitlines():
        if line.strip():
            return line.strip()
    return ""


# --------------------------------------------------------------------------
# the checks
# --------------------------------------------------------------------------


def check_work_queue_cli(ctx: Context) -> Result:
    """The shared work queue's command line."""
    if shutil.which("amplifier-work-tracker") is None:
        return Result(MISSING, "amplifier-work-tracker is not on PATH.")
    ran = run_command(ctx, ["amplifier-work-tracker", "--help"])
    if ran.failure:
        return Result(
            SKIP, f"Could not ask amplifier-work-tracker for help: {ran.failure}."
        )
    if not ran.ok:
        return Result(MISSING, f"amplifier-work-tracker --help exited {ran.code}.")
    return Result(
        OK,
        f"amplifier-work-tracker answers at {shutil.which('amplifier-work-tracker')}.",
    )


def check_work_queue_service(ctx: Context) -> Result:
    """The queue's service — installed and active, or reachable anyway."""
    if shutil.which("amplifier-work-tracker") is None:
        return Result(
            SKIP, "Cannot ask about the service: amplifier-work-tracker is not on PATH."
        )

    status = run_command(ctx, ["amplifier-work-tracker", "service", "status"])
    if status.failure:
        return Result(SKIP, f"Could not read the service status: {status.failure}.")
    active = bool(
        re.search(r"^\s*active:\s*true\s*$", status.text, re.IGNORECASE | re.MULTILINE)
    )
    installed = bool(
        re.search(
            r"^\s*installed:\s*true\s*$", status.text, re.IGNORECASE | re.MULTILINE
        )
    )

    if ctx.project:
        live = run_command(
            ctx,
            ["amplifier-work-tracker", "status", "--project", ctx.project, "--json"],
        )
        if live.failure:
            return Result(
                SKIP,
                f"Could not run a live query on project {ctx.project!r}: {live.failure}.",
            )
        if live.ok:
            return Result(
                OK,
                f"A live query on project {ctx.project!r} answered, so the queue server is reachable.",
                {"managed_service_active": active, "live_query": True},
            )
        return Result(
            MISSING,
            f"A live query on project {ctx.project!r} failed: {first_line(live.text) or f'exit {live.code}'}.",
            {"managed_service_active": active, "live_query": False},
        )

    if active:
        return Result(
            OK,
            "The managed service is installed and active; pass --project NAME to also prove a live query.",
            {"managed_service_active": True, "live_query": False},
        )

    # Not managed, no project named — but the promise this check makes is
    # REACHABILITY ("without a reachable queue service no claim or heartbeat
    # can be recorded"), and a managed unit is one way to be reachable, not
    # the only way. `instances` reads the project list out of the shared
    # server, so a clean exit proves a server is answering right now without
    # needing any project to exist yet.
    #
    # This is not a loosening to make a red go green. It is the same
    # distinction work-tracker's own status draws between "nothing is running"
    # and "something is running that we did not install" — the second is
    # usable as-is. Measured: a container whose queue runs detached (systemd
    # --user is unavailable to root there) served a whole wave — claims,
    # custody and resolutions — while this check called it missing.
    reachable = run_command(ctx, ["amplifier-work-tracker", "instances"])
    if reachable.ok:
        return Result(
            OK,
            "No managed service, but a queue server is answering "
            "(`amplifier-work-tracker instances` succeeded), so claims and "
            "heartbeats can be recorded. It is unmanaged: nothing will restart "
            "it after a reboot.",
            {"managed_service_active": False, "managed_service_installed": installed,
             "reachable_unmanaged": True, "live_query": False},
        )
    return Result(
        MISSING,
        "The managed service is not active"
        + (" (it is installed)." if installed else " and not installed.")
        + " No --project was given, and no unmanaged server answered either: "
        + (first_line(reachable.text) or reachable.failure or f"exit {reachable.code}"),
        {"managed_service_active": False, "reachable_unmanaged": False,
         "live_query": False},
    )


LANE_HELPER_SKILLS = ("ten-lane-highway", "goalify", "goal-batch", "monitor")


def check_lane_helpers(ctx: Context) -> Result:
    """The parallel-lane tooling: four skills plus the built-in /goal command."""
    if shutil.which("amplifier") is None:
        return Result(SKIP, "Cannot list skills: the amplifier command is not on PATH.")

    listing = run_command(
        ctx, ["amplifier", "tool", "invoke", "load_skill", "list=true"]
    )
    if listing.failure:
        return Result(SKIP, f"Could not list skills: {listing.failure}.")
    if not listing.ok:
        return Result(
            SKIP,
            f"Listing skills exited {listing.code}; presence could not be determined.",
        )

    catalogue = squeeze(listing.text)
    found: dict[str, bool] = {
        name: f"**{name}**" in catalogue for name in LANE_HELPER_SKILLS
    }

    goal = run_command(
        ctx,
        [
            "amplifier",
            "tool",
            "invoke",
            "read_file",
            "file_path=@app-cli:docs/GOAL_COMMAND.md",
        ],
    )
    goal_present = goal.ok and "/goal" in goal.text
    found["goal"] = goal_present

    absent = sorted(name for name, present in found.items() if not present)
    if not absent:
        return Result(
            OK,
            "All five lane helpers are present: " + ", ".join(sorted(found)) + ".",
            {"helpers": found},
        )
    return Result(
        MISSING,
        "Not found: " + ", ".join(absent) + ".",
        {"helpers": found},
    )


def _git_version(text: str) -> tuple[int, int] | None:
    match = re.search(r"git version (\d+)\.(\d+)", text)
    if not match:
        return None
    return int(match.group(1)), int(match.group(2))


def check_git_worktrees(ctx: Context) -> Result:
    """Git, new enough to make a working copy per lane."""
    if shutil.which("git") is None:
        return Result(MISSING, "git is not on PATH.")

    listed = run_command(ctx, ["git", "worktree", "list"], cwd=ctx.repo_root)
    if listed.ok:
        count = len([line for line in listed.out.splitlines() if line.strip()])
        return Result(
            OK, f"git worktree list works here and reports {count} working copies."
        )

    version = run_command(ctx, ["git", "--version"])
    if version.failure:
        return Result(SKIP, f"Could not ask git for its version: {version.failure}.")
    parsed = _git_version(version.text)
    if parsed is None:
        return Result(
            SKIP, f"Could not read a version from {first_line(version.text)!r}."
        )
    if parsed < (2, 5):
        return Result(
            MISSING,
            f"git {parsed[0]}.{parsed[1]} predates worktrees, which arrived in git 2.5.",
        )
    return Result(
        OK,
        f"git {parsed[0]}.{parsed[1]} supports worktrees; the live list did not run here "
        f"({first_line(listed.text) or f'exit {listed.code}'}).",
    )


def check_tmux(ctx: Context) -> Result:
    """A terminal multiplexer, so a lane has a terminal session of its own."""
    if shutil.which("tmux") is None:
        return Result(MISSING, "tmux is not on PATH.")
    ran = run_command(ctx, ["tmux", "-V"])
    if ran.failure:
        return Result(SKIP, f"Could not ask tmux for its version: {ran.failure}.")
    if not ran.ok:
        return Result(MISSING, f"tmux -V exited {ran.code}.")
    return Result(OK, f"{first_line(ran.text)} is installed.")


ANCHORS_MARKERS = ("amplifier-foundation", "bundles/anchors")


def check_anchors_base(ctx: Context) -> Result:
    """The lean base this bundle is assembled on."""
    manifest = ctx.repo_root / "bundle.md"
    if not manifest.is_file():
        return Result(
            SKIP, f"No bundle.md at {manifest}; run this from the bundle checkout."
        )

    text = manifest.read_text(encoding="utf-8", errors="replace")
    declared = [
        line.strip()
        for line in text.splitlines()
        if all(marker in line for marker in ANCHORS_MARKERS)
    ]
    if not declared:
        return Result(MISSING, "bundle.md declares no include for the anchors base.")

    cache = ctx.amplifier_home / "cache"
    checkouts = (
        sorted(cache.glob("*/bundles/anchors/bundle.md")) if cache.is_dir() else []
    )
    if checkouts:
        return Result(
            OK,
            f"bundle.md declares the anchors base and a local copy is at {checkouts[0]}.",
            {"declared": declared[0]},
        )
    return Result(
        SKIP,
        f"bundle.md declares the anchors base, but no local copy was found under {cache}; "
        "fetching it needs the network, which this check does not use.",
        {"declared": declared[0]},
    )


GUARD_MODULE = Path("modules/hooks-candidate-guard")
GUARD_BEHAVIOR = Path("behaviors/converge.yaml")


def check_candidate_guard(ctx: Context) -> Result:
    """Converge's own guard — the thing that keeps a locked contract locked."""
    module = ctx.repo_root / GUARD_MODULE
    package = module / "amplifier_module_hooks_candidate_guard" / "__init__.py"
    if not package.is_file():
        return Result(MISSING, f"No guard module at {module}.")

    behavior = ctx.repo_root / GUARD_BEHAVIOR
    if not behavior.is_file():
        return Result(
            SKIP,
            f"The guard module is present but {behavior} is missing, so wiring cannot be read.",
        )
    if "hooks-candidate-guard" not in behavior.read_text(
        encoding="utf-8", errors="replace"
    ):
        return Result(
            MISSING,
            f"The guard module is present but {GUARD_BEHAVIOR} does not wire it in.",
        )
    return Result(
        OK, f"The guard module is at {GUARD_MODULE} and {GUARD_BEHAVIOR} wires it in."
    )


PACKAGE = "amplifier_converge"
DISTRIBUTION = "amplifier-converge"
CONSOLE_SCRIPT = "amplifier-converge"

# Asked of the interpreter the installed command actually runs under, never of
# this script's own interpreter: `install-check.py` runs under `uv run --script`
# in an environment of its own, which by design cannot see what the machine has
# installed. Everything it prints is a fact about the install, not an opinion.
INSTALLED_PROBE = """
import json

info = {"origin": None, "paths": [], "version": None,
        "editable_source": None, "import_error": None, "dist_error": None}
try:
    import importlib.util
    spec = importlib.util.find_spec("amplifier_converge")
except Exception as exc:
    spec = None
    info["import_error"] = repr(exc)
else:
    if spec is None:
        info["import_error"] = "no module named amplifier_converge"
    else:
        info["origin"] = spec.origin
        info["paths"] = list(spec.submodule_search_locations or [])
try:
    import importlib.metadata as md
    dist = md.distribution("amplifier-converge")
    info["version"] = dist.version
    raw = dist.read_text("direct_url.json")
    if raw:
        from urllib.parse import urlparse
        from urllib.request import url2pathname
        direct = json.loads(raw)
        url = str(direct.get("url", ""))
        if direct.get("dir_info", {}).get("editable") and url.startswith("file://"):
            info["editable_source"] = url2pathname(urlparse(url).path)
except Exception as exc:
    info["dist_error"] = repr(exc)
print(json.dumps(info))
"""


def interpreter_of(script: Path) -> tuple[str | None, str]:
    """The interpreter a console script runs under, read from its own shebang."""
    try:
        with script.open("rb") as handle:
            first = handle.readline(500).decode("utf-8", "replace").strip()
    except OSError as exc:
        return None, f"{script} could not be read: {exc}"
    if not first.startswith("#!"):
        return None, f"{script} does not begin with an interpreter line"
    try:
        parts = shlex.split(first[2:])
    except ValueError as exc:
        return None, f"{script}'s interpreter line could not be read: {exc}"
    if not parts:
        return None, f"{script}'s interpreter line is empty"
    if Path(parts[0]).name.startswith("env"):
        named = [p for p in parts[1:] if not p.startswith("-")]
        if not named:
            return None, f"{script}'s interpreter line names no interpreter"
        found = shutil.which(named[0])
        if found is None:
            return None, f"{script} runs under {named[0]}, which is not on PATH"
        return found, f"{named[0]} on PATH, named by {script}'s interpreter line"
    return parts[0], f"{script}'s own interpreter line"


def _package_dir(probe: dict) -> Path | None:
    origin = probe.get("origin")
    if origin:
        return Path(origin).parent
    paths = probe.get("paths") or []
    return Path(paths[0]) if paths else None


def _under(path: Path, root: Path) -> bool:
    try:
        resolved, base = path.resolve(), root.resolve()
    except OSError:  # pragma: no cover - defensive
        return False
    return resolved == base or base in resolved.parents


def judge_installed_tree(repo_root: Path, probe: dict) -> Result:
    """Does the installed package resolve to THIS tree, or somewhere else?

    Three answers, and only one of them is a pass:

    - it resolves inside the repository under test - OK, the check about to be
      re-run is about to measure the code that is actually here;
    - it resolves to a path that no longer exists - MISSING, and the path is
      named, because that is a stale editable binding to a working copy
      somebody removed;
    - it resolves to a real path somewhere else - MISSING, and both paths are
      named, because a check run against it measures code from another tree.
    """
    command = probe.get("command") or CONSOLE_SCRIPT
    source = probe.get("editable_source")
    package_dir = _package_dir(probe)
    facts = {"repository": str(repo_root), "package_dir": str(package_dir)
             if package_dir else None, "editable_source": source,
             "version": probe.get("version"),
             "interpreter": probe.get("interpreter")}

    if package_dir is None:
        if source and not Path(source).exists():
            return Result(
                MISSING,
                f"{command} is an editable install bound to {source}, which does "
                "not exist. That is a stale binding to a working copy somebody "
                "removed: nothing can be imported through it, and a check re-run "
                "here would be measuring a tree that is gone.",
                facts,
            )
        if source:
            return Result(
                MISSING,
                f"{command} is an editable install bound to {source}, which "
                f"exists, but its interpreter cannot import {PACKAGE} from it "
                f"({probe.get('import_error')}).",
                facts,
            )
        return Result(
            MISSING,
            f"{command} is on PATH but its interpreter can neither import "
            f"{PACKAGE} ({probe.get('import_error')}) nor read a distribution "
            f"for {DISTRIBUTION} ({probe.get('dist_error')}).",
            facts,
        )

    if not package_dir.exists():
        return Result(
            MISSING,
            f"The installed {PACKAGE} resolves to {package_dir}, which does not "
            "exist. That is a stale editable binding to a working copy somebody "
            "removed, and a check re-run through it measures a tree that is gone.",
            facts,
        )
    if _under(package_dir, repo_root):
        return Result(
            OK,
            f"The installed {PACKAGE} resolves to {package_dir}, inside the "
            f"repository under test ({repo_root}), so a check re-run here "
            "measures this tree.",
            facts,
        )
    return Result(
        MISSING,
        f"The installed {PACKAGE} resolves to {package_dir}, which is NOT inside "
        f"the repository under test ({repo_root}). A check re-run here would pass "
        "or fail on code from another tree; reinstall from this repository before "
        "believing it.",
        facts,
    )


def check_installed_tree(ctx: Context) -> Result:
    """The installed package - is it this repository, or a leftover elsewhere?"""
    found = shutil.which(CONSOLE_SCRIPT)
    if found is None:
        return Result(
            SKIP,
            f"{CONSOLE_SCRIPT} is not on PATH, so there is no installed copy of "
            f"{PACKAGE} for this to resolve.",
        )
    interpreter, how = interpreter_of(Path(found))
    if interpreter is None:
        return Result(SKIP, f"Could not tell which interpreter runs {found}: {how}.")
    if not Path(interpreter).exists():
        return Result(
            MISSING,
            f"{found} runs under {interpreter}, which does not exist. The "
            "environment the command was installed into has been removed.",
            {"command": found, "interpreter": interpreter},
        )
    ran = run_command(ctx, [interpreter, "-c", INSTALLED_PROBE])
    if ran.failure:
        return Result(SKIP, f"Could not ask {interpreter} where {PACKAGE} is: "
                            f"{ran.failure}.")
    probe = None
    for line in reversed(ran.out.splitlines()):
        if line.strip().startswith("{"):
            try:
                probe = json.loads(line)
            except json.JSONDecodeError:
                probe = None
            break
    if probe is None:
        return Result(
            SKIP,
            f"{interpreter} did not answer with a readable report "
            f"(exit {ran.code}): {first_line(ran.text) or 'no output'}.",
        )
    probe["command"] = found
    probe["interpreter"] = interpreter
    probe["interpreter_source"] = how
    return judge_installed_tree(ctx.repo_root, probe)


def check_session_history(ctx: Context) -> Result:
    """Optional: the session-history service, which records provenance."""
    cache = ctx.amplifier_home / "cache"
    checkouts = sorted(cache.glob("*context-intelligence*")) if cache.is_dir() else []
    if checkouts:
        return Result(
            OK,
            f"The session-history bundle is installed at {checkouts[0]}; "
            "whether its server is running is not checked here.",
        )
    return Result(MISSING, f"No session-history bundle found under {cache}.")


CHECKS: list[Check] = [
    Check(
        ident="work-queue-cli",
        name="Work queue command",
        requirement=REQUIRED,
        degradation="Without the work queue command there is no shared queue, so the manager session stops before planning.",
        probe="amplifier-work-tracker --help",
        run=check_work_queue_cli,
    ),
    Check(
        ident="work-queue-service",
        name="Work queue service",
        requirement=REQUIRED,
        degradation="Without a reachable queue service no claim or heartbeat can be recorded, so the manager session stops before planning.",
        probe="amplifier-work-tracker service status (and status --project NAME --json when a project is given)",
        run=check_work_queue_service,
    ),
    Check(
        ident="lane-helpers",
        name="Parallel-lane helpers",
        requirement=OPTIONAL,
        degradation="Without the parallel-lane helpers work runs one lane at a time, and the manager session says so aloud.",
        probe="amplifier tool invoke load_skill list=true, plus the /goal command's own documentation",
        run=check_lane_helpers,
    ),
    Check(
        ident="git-worktrees",
        name="Git worktrees",
        requirement=REQUIRED,
        degradation="Without worktrees a lane has no working copy of its own, so no lanes launch.",
        probe="git worktree list in the repository, falling back to git --version",
        run=check_git_worktrees,
    ),
    Check(
        ident="tmux",
        name="Terminal multiplexer",
        requirement=REQUIRED,
        degradation="Without a terminal multiplexer a lane has no terminal session of its own, so no lanes launch.",
        probe="tmux -V",
        run=check_tmux,
    ),
    Check(
        ident="anchors-base",
        name="Lean base (anchors)",
        requirement=REQUIRED,
        degradation="Without the lean base a session has no everyday tools and no helper agents, so nothing runs.",
        probe="the anchors include in bundle.md, and a local copy under the amplifier cache",
        run=check_anchors_base,
    ),
    Check(
        ident="candidate-guard",
        name="Locked-contract guard",
        requirement=REQUIRED,
        degradation="Without the guard a locked contract can be edited in place, and the ratchet loses its teeth.",
        probe="the module under modules/hooks-candidate-guard and its wiring in behaviors/converge.yaml",
        run=check_candidate_guard,
    ),
    Check(
        ident="installed-tree",
        name="Installed package is this tree",
        requirement=REQUIRED,
        degradation="Without the installed package resolving to this repository, a check re-run after merging measures code from somewhere else and can certify a tree nobody tested.",
        probe=f"the {CONSOLE_SCRIPT} command's own interpreter, asked where it imports {PACKAGE} from and what source an editable install records",
        run=check_installed_tree,
    ),
    Check(
        ident="session-history",
        name="Session history (optional)",
        requirement=OPTIONAL,
        degradation="Without the session-history service provenance is not recorded; everything else works unchanged.",
        probe="a session-history bundle under the amplifier cache",
        run=check_session_history,
    ),
]


# --------------------------------------------------------------------------
# running and reporting
# --------------------------------------------------------------------------


def run_checks(ctx: Context, checks: list[Check] | None = None) -> list[dict]:
    rows: list[dict] = []
    for check in checks if checks is not None else CHECKS:
        try:
            result = check.run(ctx)
        except Exception as exc:  # noqa: BLE001 - a broken check must not fake a pass
            result = Result(SKIP, f"The check itself failed: {exc!r}.")
        row = {
            "id": check.ident,
            "name": check.name,
            "requirement": check.requirement,
            "status": result.status,
            "detail": result.detail,
            "degradation": check.degradation,
            "probe": check.probe,
        }
        if result.extra:
            row["evidence"] = result.extra
        rows.append(row)
    return rows


def summarise(rows: list[dict]) -> dict:
    return {
        "ok": sum(1 for r in rows if r["status"] == OK),
        "missing": sum(1 for r in rows if r["status"] == MISSING),
        "skipped": sum(1 for r in rows if r["status"] == SKIP),
        "required_missing": sum(
            1 for r in rows if r["status"] == MISSING and r["requirement"] == REQUIRED
        ),
    }


def exit_code(rows: list[dict]) -> int:
    return 1 if summarise(rows)["required_missing"] else 0


def render_table(rows: list[dict], ctx: Context) -> str:
    width = max(len(r["name"]) for r in rows)
    lines = [
        "Converge install check",
        f"  contract: {CONTRACT}",
        f"  repository: {ctx.repo_root}",
        "",
    ]
    for row in rows:
        mark = {OK: "ok     ", MISSING: "MISSING", SKIP: "skipped"}[row["status"]]
        tail = "" if row["requirement"] == REQUIRED else "  (optional)"
        lines.append(f"  {mark}  {row['name']:<{width}}  {row['detail']}{tail}")
        if row["status"] != OK:
            lines.append(f"  {'':7}  {'':<{width}}  -> {row['degradation']}")
    counts = summarise(rows)
    lines.append("")
    lines.append(
        f"  {counts['ok']} present, {counts['missing']} missing, {counts['skipped']} not checked."
    )
    if counts["required_missing"]:
        lines.append(
            f"  {counts['required_missing']} required dependency is missing."
            if counts["required_missing"] == 1
            else f"  {counts['required_missing']} required dependencies are missing."
        )
    elif counts["missing"]:
        lines.append(
            "  Nothing required is missing; what is missing degrades as described above."
        )
    if counts["skipped"]:
        lines.append(
            "  A skipped check is not a pass. Its reason is on the line above it."
        )
    lines.append("")
    return "\n".join(lines)


def build_report(rows: list[dict], ctx: Context) -> dict:
    return {
        "tool": "converge-install-check",
        "schema": 1,
        "contract": CONTRACT,
        "repository": str(ctx.repo_root),
        "checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "summary": summarise(rows),
        "exit_code": exit_code(rows),
        "checks": rows,
    }


def default_repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def default_amplifier_home() -> Path:
    override = os.environ.get("AMPLIFIER_HOME")
    return Path(override).expanduser() if override else Path.home() / ".amplifier"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="install-check.py",
        description="Check every dependency operation.v1 declares, and say what each absence costs.",
    )
    parser.add_argument(
        "--json-only", action="store_true", help="print only the JSON report, no table"
    )
    parser.add_argument(
        "--repo-root", type=Path, default=None, help="the bundle checkout to inspect"
    )
    parser.add_argument(
        "--amplifier-home", type=Path, default=None, help="the amplifier data directory"
    )
    parser.add_argument(
        "--project",
        default=None,
        help="work queue project to use for a live reachability query",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=60.0,
        help="seconds to wait for any one command",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    ctx = Context(
        repo_root=(args.repo_root or default_repo_root()).resolve(),
        amplifier_home=(args.amplifier_home or default_amplifier_home()).expanduser(),
        project=args.project,
        timeout=args.timeout,
    )
    rows = run_checks(ctx)
    if not args.json_only:
        sys.stderr.write(render_table(rows, ctx))
        sys.stderr.flush()
    sys.stdout.write(json.dumps(build_report(rows, ctx), indent=2) + "\n")
    return exit_code(rows)


if __name__ == "__main__":
    raise SystemExit(main())
