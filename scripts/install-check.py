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
    return Result(
        MISSING,
        "The managed service is not active"
        + (" (it is installed)." if installed else " and not installed.")
        + " No --project was given, so no live query could confirm another server.",
        {"managed_service_active": False, "live_query": False},
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
