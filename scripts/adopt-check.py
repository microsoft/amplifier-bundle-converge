#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Did the Converge install take, and has a manager session run here?

Run this straight after installing, and again any time the manager session is
not where you expect it. It answers one question a person cannot answer by
looking:

    Is the manager session available in this Amplifier, on this machine?

There is a known way for the answer to be no while everything looks fine — a
second bundle registered under the `converge` name makes the mode vanish with
no error anywhere (filed as converge-348). This command is how you find that
out in one line instead of by typing a mode name and guessing why nothing
happened.

    # no clone needed
    uv run https://raw.githubusercontent.com/microsoft/amplifier-bundle-converge/main/scripts/adopt-check.py

    # from a checkout of this repository
    uv run scripts/adopt-check.py
    uv run scripts/adopt-check.py --json
    uv run scripts/adopt-check.py --project converge   # also prove the queue answers

It leaves 0 when everything a manager session needs is present, and 1 when
something it needs is absent. A check that could not be performed says so and
never counts as present. Nothing here installs, starts, or changes anything —
it only looks.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from datetime import timezone
from pathlib import Path

# Plain words on the surface; the machine forms stay in the JSON keys.
PRESENT = "present"
ABSENT = "absent"
UNKNOWN = "can't check"

NEEDED = "needed"  # absent -> exit 1
REPORTED = "reported"  # absent -> said plainly, never fatal

MODE_NAME = "converge-manager"
BUNDLE_NAME = "converge"
RAW_URL = (
    "https://raw.githubusercontent.com/microsoft/"
    "amplifier-bundle-converge/main/scripts/adopt-check.py"
)


@dataclass
class Ran:
    code: int | None
    out: str
    err: str
    failure: str | None = None

    @property
    def ok(self) -> bool:
        return self.code == 0

    @property
    def text(self) -> str:
        return f"{self.out}\n{self.err}".strip()


@dataclass
class Finding:
    ident: str
    name: str
    tier: str
    state: str
    detail: str
    remedy: str = ""
    extra: dict = field(default_factory=dict)


def run(cmd: list[str], timeout: float, cwd: Path | None = None) -> Ran:
    """Run a command and never raise. A command that could not run says so."""
    try:
        done = subprocess.run(  # noqa: S603 - fixed argv, no shell
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(cwd) if cwd else None,
            check=False,
        )
    except FileNotFoundError:
        return Ran(None, "", "", failure=f"{cmd[0]} is not on PATH")
    except subprocess.TimeoutExpired:
        return Ran(None, "", "", failure=f"{cmd[0]} did not answer within {timeout:g}s")
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


def check_cli(timeout: float) -> Finding:
    """The Amplifier command itself. Everything below needs it."""
    where = shutil.which("amplifier")
    if where is None:
        return Finding(
            "cli",
            "Amplifier command",
            NEEDED,
            ABSENT,
            "amplifier is not on PATH.",
            "Install Amplifier first, then run this again.",
        )
    ran = run(["amplifier", "--version"], timeout)
    if ran.failure or not ran.ok:
        return Finding(
            "cli",
            "Amplifier command",
            NEEDED,
            UNKNOWN,
            f"amplifier is at {where} but did not answer --version"
            f" ({ran.failure or f'exit {ran.code}'}).",
            "Run `amplifier --version` by hand and read what it says.",
        )
    return Finding(
        "cli",
        "Amplifier command",
        NEEDED,
        PRESENT,
        f"{first_line(ran.text) or 'amplifier'} at {where}.",
        extra={"path": where},
    )


def check_mode(timeout: float) -> Finding:
    """The manager session itself — the one thing the install is FOR."""
    if shutil.which("amplifier") is None:
        return Finding(
            "mode",
            "Manager session mode",
            NEEDED,
            UNKNOWN,
            "Cannot list modes: the amplifier command is not on PATH.",
            "Install Amplifier first, then run this again.",
        )

    listing = run(["amplifier", "tool", "invoke", "mode", "operation=list"], timeout)
    if listing.failure:
        return Finding(
            "mode",
            "Manager session mode",
            NEEDED,
            UNKNOWN,
            f"Could not list modes: {listing.failure}.",
            "Run `amplifier tool invoke mode operation=list` by hand.",
        )
    if not listing.ok:
        return Finding(
            "mode",
            "Manager session mode",
            NEEDED,
            UNKNOWN,
            f"Listing modes exited {listing.code}; presence could not be read.",
            "Run `amplifier tool invoke mode operation=list` by hand.",
        )

    catalogue = squeeze(listing.text)
    if f"'name':'{MODE_NAME}'" in catalogue or f'"name":"{MODE_NAME}"' in catalogue:
        return Finding(
            "mode",
            "Manager session mode",
            NEEDED,
            PRESENT,
            f"`{MODE_NAME}` is in this session's mode list, so `/mode {MODE_NAME}`"
            " has something to enter.",
            extra={"mode": MODE_NAME},
        )
    return Finding(
        "mode",
        "Manager session mode",
        NEEDED,
        ABSENT,
        f"`{MODE_NAME}` is not in this Amplifier's mode list. Typing"
        f" `/mode {MODE_NAME}` will not start a manager session.",
        "Two known causes, in the order worth checking. One: the bundle is not"
        " installed here — run the install command from the README. Two: a"
        " second bundle is registered under the name `converge`, which makes"
        " the mode vanish with no error (converge-348) — run"
        " `amplifier bundle list --all`, and remove the duplicate with"
        " `amplifier bundle remove <name>`.",
    )


def check_bundle(timeout: float) -> Finding:
    """Is the bundle registered, and registered only once?"""
    if shutil.which("amplifier") is None:
        return Finding(
            "bundle",
            "Converge bundle registered",
            REPORTED,
            UNKNOWN,
            "Cannot list bundles: the amplifier command is not on PATH.",
        )

    listing = run(["amplifier", "bundle", "list"], timeout)
    if listing.failure or not listing.ok:
        return Finding(
            "bundle",
            "Converge bundle registered",
            REPORTED,
            UNKNOWN,
            "Could not list bundles: "
            f"{listing.failure or f'exit {listing.code}'}.",
        )

    names: list[str] = []
    for line in listing.text.splitlines():
        cells = [c.strip() for c in re.split(r"[│┃|]", line) if c.strip()]
        if cells and cells[0] == BUNDLE_NAME:
            names.append(cells[0])

    if len(names) > 1:
        return Finding(
            "bundle",
            "Converge bundle registered",
            REPORTED,
            ABSENT,
            f"The name `{BUNDLE_NAME}` is registered {len(names)} times. A"
            " duplicate namespace makes the manager session mode vanish with"
            " no error (converge-348).",
            "Run `amplifier bundle list --all` to see both, then"
            " `amplifier bundle remove <name>` on the one you do not want.",
            extra={"count": len(names)},
        )
    if names:
        return Finding(
            "bundle",
            "Converge bundle registered",
            REPORTED,
            PRESENT,
            f"`{BUNDLE_NAME}` is registered once.",
            extra={"count": 1},
        )
    return Finding(
        "bundle",
        "Converge bundle registered",
        REPORTED,
        ABSENT,
        f"No bundle named `{BUNDLE_NAME}` is registered here.",
        "Run the install command from the README, then run this again.",
        extra={"count": 0},
    )


def check_queue(timeout: float, project: str | None) -> Finding:
    """The shared work queue — where the manager session files and claims work."""
    if shutil.which("amplifier-work-tracker") is None:
        return Finding(
            "queue",
            "Work queue reachable",
            NEEDED,
            ABSENT,
            "amplifier-work-tracker is not on PATH, so no claim, heartbeat or"
            " filed item can be recorded.",
            "uv tool install"
            " git+https://github.com/microsoft/amplifier-work-tracker@main",
        )

    if project:
        live = run(
            ["amplifier-work-tracker", "status", "--project", project, "--json"],
            timeout,
        )
        if live.failure:
            return Finding(
                "queue",
                "Work queue reachable",
                NEEDED,
                UNKNOWN,
                f"Could not query project {project!r}: {live.failure}.",
                "Run `amplifier-work-tracker status --project"
                f" {project}` by hand.",
            )
        if live.ok:
            return Finding(
                "queue",
                "Work queue reachable",
                NEEDED,
                PRESENT,
                f"A live query on project {project!r} answered, so the queue"
                " server is reachable.",
                extra={"live_query": True},
            )
        return Finding(
            "queue",
            "Work queue reachable",
            NEEDED,
            ABSENT,
            f"A live query on project {project!r} failed: "
            f"{first_line(live.text) or f'exit {live.code}'}.",
            "Run `amplifier-work-tracker service status`; install the service"
            " with `amplifier-work-tracker service install` if nothing is"
            " running.",
            extra={"live_query": False},
        )

    reachable = run(["amplifier-work-tracker", "instances"], timeout)
    if reachable.ok:
        return Finding(
            "queue",
            "Work queue reachable",
            NEEDED,
            PRESENT,
            "A queue server is answering (`amplifier-work-tracker instances`"
            " succeeded). Pass --project NAME to also prove a live query on"
            " one project.",
            extra={"live_query": False},
        )
    return Finding(
        "queue",
        "Work queue reachable",
        NEEDED,
        ABSENT,
        "No queue server answered: "
        f"{first_line(reachable.text) or reachable.failure or f'exit {reachable.code}'}.",
        "Run `amplifier-work-tracker service status`; install the service with"
        " `amplifier-work-tracker service install` if nothing is running.",
    )


def check_guard(root: Path) -> Finding:
    """The locked-contract guard that works without any bundle at all."""
    hook = root / ".githooks" / "pre-push"
    if not hook.is_file():
        return Finding(
            "guard",
            "Locked-contract guard in this repository",
            REPORTED,
            ABSENT,
            f"No pre-push scan at {hook}.",
            "mkdir -p .githooks && curl -fsSL https://raw.githubusercontent.com/"
            "microsoft/amplifier-bundle-converge/main/docs/workspace-template/"
            "pre-push-scan.sh -o .githooks/pre-push && chmod +x"
            " .githooks/pre-push && git config core.hooksPath .githooks",
        )
    if not os.access(hook, os.X_OK):
        return Finding(
            "guard",
            "Locked-contract guard in this repository",
            REPORTED,
            ABSENT,
            f"{hook} is there but not executable, so git will not run it.",
            "chmod +x .githooks/pre-push",
        )

    configured = run(["git", "config", "--get", "core.hooksPath"], 30.0, cwd=root)
    path = first_line(configured.out) if configured.ok else ""
    if path.strip() != ".githooks":
        return Finding(
            "guard",
            "Locked-contract guard in this repository",
            REPORTED,
            ABSENT,
            f"{hook} is executable, but core.hooksPath is "
            + (f"{path!r}" if path else "unset")
            + ", so git runs a different hook directory.",
            "git config core.hooksPath .githooks",
        )
    return Finding(
        "guard",
        "Locked-contract guard in this repository",
        REPORTED,
        PRESENT,
        f"{hook} is executable and core.hooksPath is .githooks, so a push that"
        " edits a locked contract is refused.",
    )


def check_plan_record(start: Path) -> Finding:
    """Has a manager session actually run here yet?"""
    seen: list[dict] = []
    for base in [start, *start.parents][:6]:
        holder = base / ".converge"
        if not holder.is_dir():
            continue
        for plan in sorted(holder.glob("*/HIGHWAY.md")):
            stamp = datetime.fromtimestamp(plan.stat().st_mtime, tz=timezone.utc)
            seen.append(
                {
                    "project": plan.parent.name,
                    "plan": str(plan),
                    "rewritten": stamp.strftime("%Y-%m-%d %H:%M UTC"),
                }
            )
        if seen:
            break

    if not seen:
        return Finding(
            "plan",
            "A manager session has run here",
            REPORTED,
            ABSENT,
            f"No plan record under {start}/.converge/<project>/HIGHWAY.md — no"
            " manager session has run here yet. Before your first one, this is"
            " what it should say.",
            "Start one: `cd` to the workspace root, run `amplifier`, then"
            " `/mode converge-manager`.",
        )
    where = ", ".join(f"{s['project']} (rewritten {s['rewritten']})" for s in seen[:3])
    return Finding(
        "plan",
        "A manager session has run here",
        REPORTED,
        PRESENT,
        f"Plan record found for {where}.",
        extra={"projects": seen},
    )


# --------------------------------------------------------------------------
# running and reporting
# --------------------------------------------------------------------------


def collect(args: argparse.Namespace) -> list[Finding]:
    root = args.repo_root
    return [
        check_cli(args.timeout),
        check_mode(args.mode_timeout),
        check_bundle(args.timeout),
        check_queue(args.timeout, args.project),
        check_guard(root),
        check_plan_record(root),
    ]


def verdict(findings: list[Finding]) -> tuple[int, str]:
    needed_absent = [
        f for f in findings if f.tier == NEEDED and f.state in (ABSENT, UNKNOWN)
    ]
    mode = next(f for f in findings if f.ident == "mode")
    if not needed_absent:
        return 0, (
            "The install took. The manager session is available here — start it"
            " with `amplifier`, then `/mode converge-manager`."
        )
    if mode.state == ABSENT:
        return 1, (
            "The install did not take. `converge-manager` is not in this"
            " Amplifier's mode list, so there is no manager session to start."
            " Read the remedy on that line."
        )
    names = ", ".join(f.name.lower() for f in needed_absent)
    return 1, (
        f"Something a manager session needs is not here: {names}. Read the"
        " remedy on each line above."
    )


def render(findings: list[Finding], code: int, sentence: str) -> str:
    width = max(len(f.name) for f in findings)
    lines = [
        "Converge adopt check — is the manager session available here?",
        "-" * 74,
    ]
    for f in findings:
        mark = {PRESENT: "present ", ABSENT: "absent  ", UNKNOWN: "can't   "}[f.state]
        tier = "needed" if f.tier == NEEDED else "reported"
        lines.append(f"  [{mark}] {f.name:<{width}}  ({tier})")
        lines.append(f"      {f.detail}")
        if f.state != PRESENT and f.remedy:
            label = "Fix" if f.tier == NEEDED else "Next"
            lines.append(f"      {label}: {f.remedy}")
    lines.append("-" * 74)
    lines.append(f"  {sentence}")
    lines.append(f"  (leaving {code})")
    return "\n".join(lines)


def report(findings: list[Finding], code: int, sentence: str) -> dict:
    return {
        "check": "converge adopt check",
        "ran_at": datetime.now(tz=timezone.utc).isoformat(timespec="seconds"),
        "source": RAW_URL,
        "verdict": sentence,
        "exit_code": code,
        "findings": [
            {
                "id": f.ident,
                "name": f.name,
                "tier": f.tier,
                "state": f.state,
                "detail": f.detail,
                "remedy": f.remedy,
                **({"extra": f.extra} if f.extra else {}),
            }
            for f in findings
        ],
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Say whether the Converge install took, and whether a manager"
            " session has run here."
        )
    )
    parser.add_argument(
        "--json", action="store_true", help="print the JSON report instead of the table"
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path.cwd(),
        help="the directory to look in (default: where you are standing)",
    )
    parser.add_argument(
        "--project",
        default=None,
        help="work queue project to use for a live reachability query",
    )
    parser.add_argument(
        "--timeout", type=float, default=90.0, help="seconds to wait for any one command"
    )
    parser.add_argument(
        "--mode-timeout",
        type=float,
        default=240.0,
        help="seconds to wait for the mode listing, which prepares a bundle first",
    )
    args = parser.parse_args(argv)
    args.repo_root = args.repo_root.resolve()
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    findings = collect(args)
    code, sentence = verdict(findings)
    if args.json:
        print(json.dumps(report(findings, code, sentence), indent=2))
    else:
        print(render(findings, code, sentence))
    return code


if __name__ == "__main__":
    sys.exit(main())
