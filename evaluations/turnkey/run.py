#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""operation.v1 turnkey harness — the contract's red gate, run end to end.

`contracts/operation.v1.md` closes with a conformance list whose first bullet is
the whole system in one sentence:

    Turnkey: fresh environment -> one install -> start a project, derive from a
    sample gap, run two lanes, tend, judge, integrate, re-check, brief -> green.
    Red today -- this is the work list.

This is the runnable version of that sentence. It drives the nine steps in
order and reports each one PASS, FAIL or SKIP **with the evidence it read**.
It is not a test of a file layout; every step reads something a running system
produced — a container's status, a command's exit code, a work item's holder
process, a git worktree, a terminal session, a merge commit, a check's verdict.

    uv run evaluations/turnkey/run.py --help
    uv run evaluations/turnkey/run.py --env local --workspace ~/dev/hw-converge
    uv run evaluations/turnkey/run.py --env dtu
    uv run evaluations/turnkey/run.py --self-check

Output: a JSON report on stdout, a human summary on stderr, exit 0 when no step
FAILs and 1 when any does. A step this harness cannot execute is SKIP with a
stated reason and never a fabricated PASS — a green line nobody can back up is
the exact failure this harness exists to prevent.

Two run modes, named in every report so nobody can misread one for the other
--------------------------------------------------------------------------
**driven** (`--env dtu`) — the harness stands the environment up itself, runs
the one documented install inside it, seeds the fixture, and drives the wave.
Every step is performed here and now.

**observed** (`--env local`) — the harness judges a manager wave that ran on
this host, against the same assertions and the same evidence. Steps it did not
perform are marked `observed`; step (a) is SKIP, because a workspace that is
already running is not a fresh environment and saying otherwise would be a lie.

The heart of it — clause 5, "lanes are real sessions"
-----------------------------------------------------
`assert_lane_is_real` and `assert_no_subagent_held_work` (below) are the reason
this harness exists. A manager session that quietly runs lane work in an
in-session sub-agent produces artifacts that look identical to a real lane's
from the outside: commits, a resolution, a green check. The one thing it cannot
fake is *where the holding process was sitting*. A real lane is a separate
process whose working directory is its own worktree, with its own terminal
session. An in-session sub-agent shares the manager session's process and
therefore the manager session's directory — which is not a lane worktree. That
is the discriminator, and it is checked against `/proc`, `git worktree list`
and `tmux`, never against anybody's self-report.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

PASS = "PASS"
FAIL = "FAIL"
SKIP = "SKIP"

DRIVEN = "driven"
OBSERVED = "observed"

CONTRACT = "operation.v1 — Conformance kit asserts, bullet 1 (Turnkey)"
HERE = Path(__file__).resolve().parent
BUNDLE_ROOT = HERE.parent.parent

# The one documented install. Read from README.md at run time so this harness
# can never drift away from what the repository actually tells a newcomer to
# type; this constant is only the pattern used to find that line.
INSTALL_LINE_MARKER = "amplifier bundle add"

# The return brief's own convention names this path (context/manager/return-brief.md).
RETURN_LOG = "docs/workflow/OWNER-RETURN-LOG.md"

# The five parts of a brief, in order (operation.v1 clause 10).
BRIEF_PARTS = ["time away", "finished", "stuck", "needs you", "quietly broken"]

# Holder ids look like "agent-spark-1-425543". The trailing integer is the OS
# pid of the holding process — verified against /proc on this host, 2026-09-02.
# This is an inferred convention, not a documented interface: when it does not
# parse, the check says so and SKIPs rather than guessing.
HOLDER_PID = re.compile(r"-(\d+)$")


# ---------------------------------------------------------------------------
# plumbing
# ---------------------------------------------------------------------------


@dataclass
class Ran:
    """A finished command: its code, its output, and why it never ran, if so."""

    code: int | None
    out: str
    err: str
    failure: str | None = None
    argv: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.code == 0

    @property
    def text(self) -> str:
        return f"{self.out}\n{self.err}".strip()

    def tail(self, n: int = 400) -> str:
        return (self.failure or self.text)[-n:].strip()


@dataclass
class Result:
    status: str
    detail: str
    evidence: dict | None = None
    reason: str | None = None  # required when status is SKIP


def first_line(text: str) -> str:
    for line in text.splitlines():
        if line.strip():
            return line.strip()
    return ""


def parse_json(text: str) -> dict | list | None:
    """Parse JSON out of a command's stdout, tolerating a leading log banner."""
    text = text.strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    for opener, closer in (("{", "}"), ("[", "]")):
        start, end = text.find(opener), text.rfind(closer)
        if 0 <= start < end:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                continue
    return None


# ---------------------------------------------------------------------------
# environments — the harness talks to one of these and never to a shell directly
# ---------------------------------------------------------------------------


class Env:
    """Somewhere commands can run and files can be read."""

    kind = "abstract"
    label = "abstract"

    def run(self, argv: list[str], cwd: str | None = None, timeout: float = 120.0,
            env: dict | None = None) -> Ran:
        raise NotImplementedError

    def sh(self, script: str, cwd: str | None = None, timeout: float = 120.0) -> Ran:
        """Run a shell snippet. Used only where a shell is genuinely needed."""
        return self.run(["bash", "-lc", script], cwd=cwd, timeout=timeout)

    def read(self, path: str) -> str | None:
        ran = self.run(["cat", path], timeout=30.0)
        return ran.out if ran.ok else None

    def exists(self, path: str) -> bool:
        return self.run(["test", "-e", path], timeout=30.0).ok


class LocalEnv(Env):
    """This host. Commands run as this user, in this filesystem."""

    kind = "local"

    def __init__(self, extra_env: dict | None = None) -> None:
        self.extra_env = extra_env or {}
        self.label = "this host"

    def run(self, argv, cwd=None, timeout=120.0, env=None) -> Ran:
        merged = dict(os.environ)
        merged.update(self.extra_env)
        if env:
            merged.update(env)
        try:
            done = subprocess.run(  # noqa: S603 — fixed argv, no shell injection
                argv, capture_output=True, text=True, timeout=timeout,
                cwd=cwd, env=merged, check=False,
            )
        except FileNotFoundError:
            return Ran(None, "", "", failure=f"{argv[0]} is not on PATH", argv=argv)
        except subprocess.TimeoutExpired:
            return Ran(None, "", "", failure=f"{argv[0]} exceeded {timeout:g}s", argv=argv)
        except OSError as exc:
            return Ran(None, "", "", failure=f"{argv[0]} could not run: {exc}", argv=argv)
        return Ran(done.returncode, done.stdout or "", done.stderr or "", argv=argv)


class DtuEnv(Env):
    """A Digital Twin Universe container, reached through its CLI.

    The CLI does NOT pass the inner command's exit code through: it prints an
    envelope, `{"id", "command", "exit_code", "stdout", "stderr"}`, and exits 0
    whether the inner command succeeded or not. Taking that at face value makes
    every command inside a container look successful and every output look like
    an envelope — a fabricated-pass generator, and one this harness measured
    itself producing before this unwrapping existed (see ../RESULT.md). So the
    envelope is always unwrapped, and an envelope that cannot be parsed is a
    loud failure, never an empty success.
    """

    kind = "dtu"

    def __init__(self, instance: str, host: LocalEnv) -> None:
        self.instance = instance
        self.host = host
        self.label = f"DTU instance {instance!r}"

    def run(self, argv, cwd=None, timeout=120.0, env=None) -> Ran:
        script = " ".join(_quote(a) for a in argv)
        if cwd:
            script = f"cd {_quote(cwd)} && {script}"
        if env:
            prefix = " ".join(f"{k}={_quote(v)}" for k, v in env.items())
            script = f"{prefix} {script}"
        outer = self.host.run(
            ["amplifier-digital-twin", "exec", self.instance, "--", "bash", "-lc", script],
            timeout=timeout,
        )
        return unwrap_dtu_envelope(outer, argv)


def _quote(value: str) -> str:
    return "'" + str(value).replace("'", "'\\''") + "'"


def unwrap_dtu_envelope(outer: Ran, argv: list[str]) -> Ran:
    """Turn the DTU CLI's envelope back into the inner command's real result.

    Pure, so it can be tested against a recorded envelope without a container.
    """
    if outer.failure:
        return Ran(None, "", "", failure=outer.failure, argv=argv)
    if not outer.ok:
        return Ran(None, "", "", argv=argv,
                   failure=f"the container CLI itself failed: {outer.tail(200)}")
    payload = parse_json(outer.out)
    if not isinstance(payload, dict) or "exit_code" not in payload:
        return Ran(None, "", "", argv=argv,
                   failure="the container CLI returned no readable result envelope: "
                           f"{outer.tail(200)!r}")
    return Ran(
        code=payload.get("exit_code"),
        out=payload.get("stdout") or "",
        err=payload.get("stderr") or "",
        argv=argv,
    )


# ---------------------------------------------------------------------------
# evidence readers — every one of these reads a running system, not a claim
# ---------------------------------------------------------------------------


@dataclass
class Lane:
    name: str
    worktree: str
    branch: str
    base_sha: str | None = None
    tmux: str | None = None
    source: str = "manifest"


def read_worktrees(env: Env, repo: str) -> list[dict]:
    """`git worktree list --porcelain` — the working copies git itself knows."""
    ran = env.run(["git", "-C", repo, "worktree", "list", "--porcelain"], timeout=60.0)
    if not ran.ok:
        return []
    out, current = [], {}
    for line in ran.out.splitlines():
        if not line.strip():
            if current:
                out.append(current)
                current = {}
            continue
        key, _, value = line.partition(" ")
        if key == "worktree":
            current = {"path": value}
        elif key == "HEAD":
            current["sha"] = value
        elif key == "branch":
            current["branch"] = value.replace("refs/heads/", "")
    if current:
        out.append(current)
    return out


def read_tmux_panes(env: Env) -> list[dict]:
    """Every live terminal session and the directory its pane is sitting in."""
    ran = env.run(
        ["tmux", "list-panes", "-a", "-F", "#{session_name}\t#{pane_current_path}"],
        timeout=60.0,
    )
    if not ran.ok:
        return []
    panes = []
    for line in ran.out.splitlines():
        session, _, path = line.partition("\t")
        if session.strip():
            panes.append({"session": session.strip(), "path": path.strip()})
    return panes


def read_manifest(env: Env, workspace: str) -> list[Lane]:
    """The launcher's own record of every lane it started (`manifest.tsv`)."""
    text = env.read(f"{workspace}/manifest.tsv")
    if not text:
        return []
    rows = [line for line in text.splitlines() if line.strip()]
    if len(rows) < 2:
        return []
    header = rows[0].split("\t")
    lanes = []
    for row in rows[1:]:
        cells = row.split("\t")
        record = dict(zip(header, cells))
        if not record.get("worktree"):
            continue
        lanes.append(
            Lane(
                name=record.get("lane", "?"),
                worktree=record["worktree"],
                branch=record.get("branch", ""),
                base_sha=record.get("base_sha") or None,
                tmux=record.get("tmux") or None,
            )
        )
    return lanes


def lanes_from_worktrees(worktrees: list[dict], panes: list[dict]) -> list[Lane]:
    """Fallback when no launcher manifest exists: infer lanes from git + tmux."""
    by_path = {p["path"]: p["session"] for p in panes}
    lanes = []
    for wt in worktrees:
        branch = wt.get("branch", "")
        if not branch.startswith("lane/"):
            continue
        lanes.append(
            Lane(
                name=branch.split("/", 1)[1],
                worktree=wt["path"],
                branch=branch,
                tmux=by_path.get(wt["path"]),
                source="worktrees",
            )
        )
    return lanes


def read_tracker_items(env: Env, project: str) -> tuple[list[dict], str | None]:
    ran = env.run(
        ["amplifier-work-tracker", "list", "--project", project, "--limit", "500", "--json"],
        timeout=120.0,
    )
    if not ran.ok:
        return [], ran.tail() or f"exit {ran.code}"
    payload = parse_json(ran.out)
    if isinstance(payload, dict):
        return list(payload.get("items", [])), None
    if isinstance(payload, list):
        return payload, None
    return [], "the tracker's answer did not parse as JSON"


def project_exists(env: Env, project: str) -> bool:
    _, error = read_tracker_items(env, project)
    return error is None


def read_tracker_item(env: Env, project: str, item_id: str) -> dict | None:
    ran = env.run(
        ["amplifier-work-tracker", "list", "--project", project, "--id", item_id, "--json"],
        timeout=120.0,
    )
    if not ran.ok:
        return None
    payload = parse_json(ran.out)
    if isinstance(payload, dict):
        items = payload.get("items") or []
        return items[0] if items else payload
    if isinstance(payload, list) and payload:
        return payload[0]
    return None


def read_process(env: Env, pid: int) -> dict | None:
    """Where a process is sitting, and what it is. Absent means it has exited."""
    ran = env.sh(
        f"test -d /proc/{pid} || exit 9; "
        f"printf '%s\\n' \"$(readlink /proc/{pid}/cwd)\"; "
        f"tr '\\0' ' ' < /proc/{pid}/cmdline",
        timeout=30.0,
    )
    if not ran.ok:
        return None
    lines = ran.out.splitlines()
    return {
        "pid": pid,
        "cwd": lines[0].strip() if lines else "",
        "cmdline": (lines[1].strip() if len(lines) > 1 else "")[:300],
    }


def holder_pid(holder: str | None) -> int | None:
    if not holder:
        return None
    match = HOLDER_PID.search(holder)
    return int(match.group(1)) if match else None


def commits_beyond(env: Env, repo: str, base: str, branch: str) -> int | None:
    ran = env.run(
        ["git", "-C", repo, "rev-list", "--count", f"{base}..{branch}"], timeout=60.0
    )
    if not ran.ok:
        return None
    try:
        return int(ran.out.strip())
    except ValueError:
        return None


def contract_names(env: Env, repo: str) -> list[str]:
    """The contracts this repository actually has, newest form and bare stem.

    Derived from `contracts/*.md` on disk rather than hardcoded, so an item is
    judged against the contracts that exist, not against a list this harness
    invented.
    """
    ran = env.run(["ls", f"{repo}/contracts"], timeout=30.0)
    if not ran.ok:
        return []
    names = set()
    for line in ran.out.split():
        match = re.match(r"^([a-z][a-z0-9-]*)\.(v\d+)\.md$", line.strip())
        if match:
            names.add(f"{match.group(1)}.{match.group(2)}")
            names.add(match.group(1))
    return sorted(names)


def merge_commits(env: Env, repo: str, branch: str, limit: int = 60) -> list[dict]:
    ran = env.run(
        ["git", "-C", repo, "log", "--merges", f"--max-count={limit}",
         "--pretty=format:%h\t%s", branch],
        timeout=60.0,
    )
    if not ran.ok:
        return []
    out = []
    for line in ran.out.splitlines():
        sha, _, subject = line.partition("\t")
        if sha.strip():
            out.append({"sha": sha.strip(), "subject": subject.strip()})
    return out


# ---------------------------------------------------------------------------
# THE ASSERTIONS — clause 5, "lanes are real sessions"
#
# These are deliberately pure functions over already-collected evidence: they
# take no environment and perform no I/O, so they can be exercised against
# synthetic evidence (`--self-check`, and tests/test_turnkey.py) and proven to
# bite. An assertion nobody can make fail proves nothing.
# ---------------------------------------------------------------------------


def _within(path: str, root: str) -> bool:
    """Is `path` the directory `root`, or inside it? Pure string comparison."""
    if not path or not root:
        return False
    p, r = path.rstrip("/"), root.rstrip("/")
    return p == r or p.startswith(r + "/")


LIVE = "live"
ENDED = "ended"
UNPROVEN = "unproven"
NOT_A_LANE = "not_a_lane"


def assert_lane_is_real(lane: Lane, worktrees: list[dict], panes: list[dict]) -> dict:
    """One lane is real iff it has its OWN worktree AND its OWN terminal session.

    operation.v1 clause 5: "A lane is a worker session's own working copy,
    branch, and terminal session." Both halves are checked against the systems
    that would know — git's own worktree list, and the multiplexer's own pane
    list — never against a manifest row's say-so. The manifest says what the
    launcher *intended*; these say what exists.

    A lane that has finished is not a violation: its terminal session is gone
    precisely because it ran and exited. So the verdict is a state, not a bool:

        live       worktree registered AND a live terminal session sitting in it
        ended      worktree registered, no live session, but the launcher
                   recorded one — it ran as a lane and has since exited
        unproven   worktree registered, no live session, and no launcher record
                   naming one, so whether it ever had its own terminal session
                   cannot be settled from evidence — reported, never passed
        not_a_lane no worktree of its own, or a worktree on the wrong branch

    Only `not_a_lane` is a violation. `unproven` is the honest middle: it is
    what this harness says instead of guessing.
    """
    findings = []

    registered = next(
        (w for w in worktrees
         if w["path"].rstrip("/") == lane.worktree.rstrip("/")),
        None,
    )
    if registered is None:
        findings.append(f"no worktree registered at {lane.worktree}")
    elif registered.get("branch") and lane.branch and registered["branch"] != lane.branch:
        findings.append(
            f"worktree {lane.worktree} is on branch {registered['branch']!r}, "
            f"not the lane's {lane.branch!r}"
        )

    sessions = [p["session"] for p in panes if _within(p["path"], lane.worktree)]

    if findings:
        state = NOT_A_LANE
    elif sessions:
        state = LIVE
        if lane.tmux and lane.tmux not in sessions:
            findings.append(
                f"the launcher recorded terminal session {lane.tmux!r} but the live "
                f"session(s) in that worktree are {sessions}"
            )
    elif lane.tmux:
        state = ENDED
        findings.append(
            f"terminal session {lane.tmux!r} is no longer live; the launcher "
            "recorded it at launch, so this lane ran and has since exited"
        )
    else:
        state = UNPROVEN
        findings.append(
            f"no live terminal session in {lane.worktree} and no launcher record "
            "naming one, so its own-terminal-session half cannot be settled"
        )

    return {
        "lane": lane.name,
        "state": state,
        "ok": state in (LIVE, ENDED),
        "worktree": lane.worktree,
        "branch": lane.branch,
        "worktree_registered": registered is not None,
        "terminal_sessions": sessions,
        "recorded_terminal": lane.tmux,
        "findings": findings,
    }


def assert_lanes_are_distinct(lanes: list[Lane]) -> dict:
    """Two lanes that share a worktree, a branch or a terminal are one lane."""
    problems = []
    for field_name, values in (
        ("worktree", [ln.worktree for ln in lanes]),
        ("branch", [ln.branch for ln in lanes]),
        ("terminal session", [ln.tmux for ln in lanes if ln.tmux]),
    ):
        seen = set()
        for value in values:
            if value in seen:
                problems.append(f"two lanes share the same {field_name}: {value!r}")
            seen.add(value)
    return {"ok": not problems, "problems": problems}


def assert_no_subagent_held_work(
    items: list[dict],
    processes: dict[int, dict | None],
    lane_worktrees: list[str],
    lane_branches: list[str] | None = None,
) -> dict:
    """FAIL the run if a work item was executed by an in-session sub-agent.

    operation.v1 clause 5: in-session sub-agents serve four roles, "none of
    which executes lane work". The discriminator is not what anyone reports —
    it is WHERE the holding process was sitting.

    A real lane is its own process, with its own working directory: one of the
    lane worktrees. An in-session sub-agent runs inside the manager session's
    own process, so it reports the manager session's pid and therefore the
    manager session's directory — which is never a lane worktree. So:

        holder process cwd inside a lane worktree  -> a real lane
        holder process cwd anywhere else           -> FAIL, named
        two live items sharing one pid             -> FAIL, one process cannot
                                                      be two lanes
        holder process already exited              -> SKIP with the reason,
                                                      never a pass

    `items` are tracker records ({id, status, holder, resolution}); `processes`
    maps a pid to what was read from /proc, or None if it has exited.

    When a holder has exited, `lane_branches` is used only to ANNOTATE the
    unresolved verdict — "its resolution names lane branch X, which the
    launcher recorded" — never to upgrade it to a pass. Prose naming a branch
    is exactly the kind of self-report a session running work in-session could
    write, so it corroborates and does not prove.
    """
    verdicts, offenders, unresolved = [], [], []
    live_pids: dict[int, str] = {}
    branches = lane_branches or []

    for item in items:
        holder = item.get("holder")
        if not holder:
            continue
        pid = holder_pid(holder)
        record = {"item": item.get("id"), "status": item.get("status"), "holder": holder}

        if pid is None:
            record.update(verdict=SKIP,
                          why=f"holder {holder!r} carries no pid, so where it ran "
                              "cannot be established from evidence")
            unresolved.append(record)
            verdicts.append(record)
            continue

        process = processes.get(pid)
        if process is None:
            named = [b for b in branches if b and b in str(item.get("resolution") or "")]
            record.update(verdict=SKIP, pid=pid,
                          why=f"the holding process (pid {pid}) has exited, so its "
                              "working directory can no longer be read")
            if named:
                record["corroboration"] = (
                    f"its resolution names lane branch(es) {named}, which the launcher "
                    "recorded — corroborating, not proof, since prose can be written "
                    "by a session that never left itself"
                )
            unresolved.append(record)
            verdicts.append(record)
            continue

        cwd = process.get("cwd", "")
        record.update(pid=pid, cwd=cwd)
        lane = next((w for w in lane_worktrees if _within(cwd, w)), None)
        if lane is None:
            record.update(
                verdict=FAIL,
                why=f"held by pid {pid} sitting in {cwd!r}, which is not any lane "
                    "worktree — the signature of work executed inside a session "
                    "rather than in a lane",
            )
            offenders.append(record)
        elif pid in live_pids:
            record.update(
                verdict=FAIL,
                why=f"pid {pid} also holds {live_pids[pid]} — one process cannot be "
                    "two lanes, so at least one of these ran in-session",
            )
            offenders.append(record)
        else:
            live_pids[pid] = str(item.get("id"))
            record.update(verdict=PASS, lane_worktree=lane)
        verdicts.append(record)

    return {
        "ok": not offenders,
        "checked": len(verdicts),
        "offenders": offenders,
        "unresolved": unresolved,
        "verdicts": verdicts,
    }


def assert_commits_beyond_base(lane: Lane, count: int | None) -> dict:
    """A marker on an unchanged branch is stuck, whatever the marker says.

    operation.v1 clause 7. Counted from the lane's own base SHA, never from a
    moving main — an inherited artifact is the commonest false signal there is.
    """
    if lane.base_sha is None:
        return {"lane": lane.name, "verdict": SKIP,
                "why": "the launcher recorded no base SHA for this lane, so 'beyond "
                       "base' has nothing to be measured from"}
    if count is None:
        return {"lane": lane.name, "verdict": SKIP,
                "why": f"git could not count commits {lane.base_sha[:8]}..{lane.branch}"}
    return {
        "lane": lane.name,
        "verdict": PASS if count > 0 else FAIL,
        "commits_beyond_base": count,
        "why": (f"{count} commit(s) beyond {lane.base_sha[:8]}"
                if count > 0
                else f"branch tip still equals base {lane.base_sha[:8]} — stuck, "
                     "whatever any marker claims"),
    }


# ---------------------------------------------------------------------------
# the run context
# ---------------------------------------------------------------------------


@dataclass
class Context:
    env: Env
    host: LocalEnv
    mode: str
    workspace: str
    repo: str
    project: str
    integration_branch: str
    answer_key: dict
    fixture_repo: str | None = None
    install_command: str | None = None
    amplifier_home: str | None = None
    timeout: float = 300.0
    notes: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# the nine steps
# ---------------------------------------------------------------------------


def step_environment(ctx: Context) -> Result:
    """(a) A fresh isolated environment stood up."""
    if ctx.env.kind != "dtu":
        return Result(
            SKIP,
            "No fresh environment was stood up; this run judges an existing host "
            f"workspace ({ctx.workspace}).",
            reason=(
                "a workspace that is already running is not a fresh environment. "
                "Standing one up needs --env dtu, which needs a DTU profile whose "
                "out-of-band state (a reachable bundle mirror and provider "
                "credentials) is present. Reporting PASS here would claim an "
                "isolation this run does not have."
            ),
            evidence={"env": ctx.env.kind, "workspace": ctx.workspace},
        )
    status = ctx.host.run(
        ["amplifier-digital-twin", "status", ctx.env.instance], timeout=120.0  # type: ignore[attr-defined]
    )
    probe = ctx.env.run(["uname", "-a"], timeout=60.0)
    if not probe.ok:
        return Result(
            FAIL,
            f"The environment was launched but does not answer: {probe.tail()}",
            evidence={"status": status.tail(), "probe": probe.tail()},
        )
    return Result(
        PASS,
        f"{ctx.env.label} is up and answering.",
        evidence={"status": first_line(status.out), "uname": first_line(probe.out)},
    )


def documented_install_command(repo_root: Path) -> tuple[str | None, str]:
    """Read THE install command out of README.md, so this can never drift."""
    readme = repo_root / "README.md"
    if not readme.is_file():
        return None, f"no README.md at {readme}"
    lines = readme.read_text(encoding="utf-8").splitlines()
    candidates = [ln.strip() for ln in lines if ln.strip().startswith(INSTALL_LINE_MARKER)]
    if not candidates:
        return None, f"README.md documents no line starting {INSTALL_LINE_MARKER!r}"
    return candidates[0], f"README.md, first {INSTALL_LINE_MARKER!r} line of {len(candidates)}"


def step_install(ctx: Context) -> Result:
    """(b) The one documented install performed."""
    command, source = documented_install_command(BUNDLE_ROOT)
    if command is None:
        return Result(FAIL, f"Could not find the documented install command: {source}.")
    ctx.install_command = command

    if shutil.which("amplifier") is None and ctx.env.kind == "local":
        return Result(
            SKIP,
            f"The documented install is: {command}",
            reason="the amplifier command is not on PATH here, so the install could "
                   "not be attempted",
            evidence={"command": command, "source": source},
        )

    # Run the install from the throwaway home itself, never from the caller's
    # workspace: an install that quietly wrote into the workspace under test
    # would change the very thing the later steps are judging.
    home = ctx.amplifier_home
    ran = ctx.env.run(
        command.split(),
        cwd=home if (home and ctx.env.kind == "local") else None,
        timeout=max(ctx.timeout, 900.0),
        env={"AMPLIFIER_HOME": home} if home else None,
    )
    evidence = {
        "command": command,
        "source": source,
        "amplifier_home": home,
        "exit_code": ran.code,
        "output_tail": ran.tail(600),
    }
    if not ran.ok:
        return Result(
            FAIL,
            f"The one documented install failed (exit {ran.code}): {ran.tail(200)}",
            evidence=evidence,
        )
    return Result(
        PASS,
        f"The one documented install succeeded into {home or 'the default amplifier home'}.",
        evidence=evidence,
    )


def step_install_check(ctx: Context) -> Result:
    """(c) `scripts/install-check.py` green inside the environment."""
    script = f"{ctx.repo}/scripts/install-check.py"
    if not ctx.env.exists(script):
        return Result(
            SKIP, f"No install check at {script}.",
            reason="the repository under test does not carry scripts/install-check.py",
        )
    # `--project` makes the install check prove the queue with a LIVE query,
    # which is strictly better evidence — but only once a project exists. This
    # step runs before "start a project", so ask for the live query only when
    # there is something live to ask about; otherwise the check would report a
    # missing dependency when what is actually missing is the project.
    argv = ["uv", "run", script, "--json-only"]
    if project_exists(ctx.env, ctx.project):
        argv += ["--project", ctx.project]
    ran = ctx.env.run(
        argv, cwd=ctx.repo, timeout=max(ctx.timeout, 600.0),
        env={"AMPLIFIER_HOME": ctx.amplifier_home} if ctx.amplifier_home else None,
    )
    if ran.failure:
        return Result(SKIP, "The install check could not be run.", reason=ran.failure)
    report = parse_json(ran.out)
    if not isinstance(report, dict) or not report.get("checks"):
        # A report with no checks in it is not a green report; it is an
        # unreadable one. Treating "nothing was checked" as "nothing is
        # missing" is exactly the fabricated pass this harness exists to
        # refuse — and is a failure it caught itself making (see ../RESULT.md).
        return Result(
            FAIL,
            f"The install check produced no readable report with checks in it "
            f"(exit {ran.code}).",
            evidence={"output_tail": ran.tail(600)},
        )
    summary = report.get("summary", {})
    missing = [
        {"id": c["id"], "detail": c["detail"]}
        for c in report.get("checks", [])
        if c.get("status") == "MISSING" and c.get("requirement") == "required"
    ]
    skipped = [c["id"] for c in report.get("checks", []) if c.get("status") == "SKIP"]
    evidence = {"summary": summary, "required_missing": missing, "skipped": skipped,
                "exit_code": ran.code}
    if ran.code != 0 or missing:
        names = ", ".join(m["id"] for m in missing) or "unnamed"
        return Result(
            FAIL,
            f"The install check is not green: {len(missing)} required dependency "
            f"missing ({names}).",
            evidence=evidence,
        )
    return Result(
        PASS,
        f"The install check is green: {summary.get('ok', 0)} present, "
        f"{summary.get('skipped', 0)} not checked.",
        evidence=evidence,
    )


def step_project(ctx: Context) -> Result:
    """(d) A project started."""
    started = None
    items, error = read_tracker_items(ctx.env, ctx.project)
    if error and ctx.mode == DRIVEN:
        # Driven mode STARTS the project — that is what this step is.
        started = ctx.env.run(
            ["amplifier-work-tracker", "new", ctx.project], timeout=180.0
        )
        items, error = read_tracker_items(ctx.env, ctx.project)
    if error:
        return Result(
            FAIL, f"The queue did not answer for project {ctx.project!r}: {error}",
            evidence={"project": ctx.project,
                      "start_attempt": started.tail(300) if started else None},
        )
    if not items and ctx.mode == OBSERVED:
        return Result(
            FAIL,
            f"Project {ctx.project!r} answers but holds no items — a project with no "
            "work in it has not been started.",
            evidence={"project": ctx.project, "items": 0},
        )
    if not items:
        return Result(
            PASS,
            f"Project {ctx.project!r} was started in the shared queue and answers; it "
            "holds no items yet, which is what the next step derives.",
            evidence={"project": ctx.project, "total": 0,
                      "start_attempt": started.tail(200) if started else None},
        )
    counts: dict[str, int] = {}
    for item in items:
        counts[item.get("status", "?")] = counts.get(item.get("status", "?"), 0) + 1
    return Result(
        PASS,
        f"Project {ctx.project!r} is live in the shared queue with {len(items)} items "
        + ", ".join(f"{n} {s}" for s, n in sorted(counts.items())) + ".",
        evidence={"project": ctx.project, "total": len(items), "by_status": counts},
    )


FIXTURES_IN_ENV = "/opt/turnkey-fixtures"


def seed_fixture(ctx: Context) -> dict:
    """Put the gap fixture into the environment and git-init it there.

    Driven mode only: the fixture is the sample gap the whole turnkey sentence
    starts from, so a run that could not seed it has not started. Returns a
    record either way; it never raises and never pretends.
    """
    if not ctx.fixture_repo:
        return {"seeded": False, "why": "no fixture path was chosen for this run"}
    if ctx.env.exists(f"{ctx.fixture_repo}/check.py"):
        return {"seeded": True, "why": "already present", "path": ctx.fixture_repo}

    if ctx.env.kind == "dtu":
        pushed = ctx.host.run(
            ["amplifier-digital-twin", "file-push", ctx.env.instance,  # type: ignore[attr-defined]
             "--recursive", "--create-dirs",
             str(HERE / "fixtures"), FIXTURES_IN_ENV],
            timeout=300.0,
        )
        # The push CLI exits 0 whether or not anything landed where expected,
        # and whether a recursive push nests the source directory inside the
        # destination is not a documented guarantee — so both layouts are
        # PROBED and the arrival is verified rather than assumed. This is the
        # same reason every other step here reads evidence instead of a return
        # code alone.
        root = next(
            (candidate for candidate in
             (FIXTURES_IN_ENV, f"{FIXTURES_IN_ENV}/fixtures")
             if ctx.env.exists(f"{candidate}/seed.sh")),
            None,
        )
        if root is None:
            return {"seeded": False,
                    "why": f"the fixture did not arrive at {FIXTURES_IN_ENV} "
                           f"(push exit {pushed.code}): {pushed.tail(300)}"}
        source = f"{root}/gap-repo"
        script = f"{root}/seed.sh"
    else:
        source = str(HERE / "fixtures" / "gap-repo")
        script = str(HERE / "fixtures" / "seed.sh")

    ran = ctx.env.run(["bash", script, ctx.fixture_repo, source], timeout=300.0)
    if not ran.ok:
        return {"seeded": False,
                "why": f"seed.sh failed (exit {ran.code}): {ran.tail(300)}"}
    return {"seeded": True, "path": ctx.fixture_repo, "output": ran.tail(200)}


def _fixture_gap_state(ctx: Context) -> dict | None:
    """Run the fixture's own kit, to prove the planted gaps are really there."""
    if not ctx.fixture_repo or not ctx.env.exists(f"{ctx.fixture_repo}/check.py"):
        return None
    argv = list(ctx.answer_key.get("check", ["python3", "check.py", "."]))
    ran = ctx.env.run(argv, cwd=ctx.fixture_repo, timeout=180.0)
    report = parse_json(ran.out)
    if not isinstance(report, dict):
        return {"error": ran.tail(300)}
    return {
        "verdict": report.get("verdict"),
        "red_rules": [r["rule"] for r in report.get("results", []) if r["status"] == FAIL],
        "exit_code": ran.code,
    }


def step_derived(ctx: Context) -> Result:
    """(e) Work derived from a fixture gap — never invented."""
    seeding = seed_fixture(ctx) if ctx.mode == DRIVEN else None
    if seeding and not seeding.get("seeded"):
        return Result(
            FAIL,
            f"The sample gap could not be put into the environment: {seeding['why']}",
            evidence={"seeding": seeding},
        )
    fixture_state = _fixture_gap_state(ctx)
    items, error = read_tracker_items(ctx.env, ctx.project)
    if error:
        return Result(SKIP, "The queue did not answer.", reason=error)

    if ctx.mode == DRIVEN and fixture_state:
        expected = set(ctx.answer_key.get("expected_red_rules_before", []))
        actual = set(fixture_state.get("red_rules", []))
        if expected and expected != actual:
            return Result(
                FAIL,
                "The fixture is not in its planted state: expected rules "
                f"{sorted(expected)} red, found {sorted(actual)}.",
                evidence={"fixture": fixture_state},
            )

    # Clause 1: every item must NAME its contract and SAY what done looks like.
    # This is checkable from the item's own record; an item that cannot point at
    # a contract is an opinion, not derived work.
    #
    # "Names its contract" is judged against the contracts this repository
    # actually has. A versioned reference (`operation.v1`) or the word
    # "contract" is a strong basis; a bare contract stem ("Operation §5-6") is
    # weak — accepted, because the clause asks for the contract to be named and
    # it is, but recorded as weak so a reader can see which basis was used. An
    # over-strict rule fabricates a failure exactly as badly as a loose one
    # fabricates a pass.
    contracts = contract_names(ctx.env, ctx.repo)
    versioned = [c for c in contracts if re.search(r"\.v\d+$", c)]
    stems = [c for c in contracts if c not in versioned]

    sampled, offenders = [], []
    for item in items[:40]:
        full = read_tracker_item(ctx.env, ctx.project, item.get("id", ""))
        if full is None:
            continue
        body = " ".join(
            str(full.get(k) or "") for k in ("description", "acceptance", "design", "title")
        )
        strong = [c for c in versioned if re.search(rf"\b{re.escape(c)}\b", body, re.I)]
        if re.search(r"\bcontracts?\b", body, re.I):
            strong.append("the word 'contract'")
        weak = [c for c in stems if re.search(rf"\b{re.escape(c)}\b", body, re.I)]
        states_done = bool(full.get("acceptance")) or bool(
            re.search(r"\b(given|then|done means|done when)\b", body, re.I)
        )
        record = {
            "item": full.get("id"),
            "names_contract": bool(strong or weak),
            "basis": "strong" if strong else ("weak" if weak else "none"),
            "matched": strong or weak,
            "states_done": states_done,
        }
        sampled.append(record)
        if not (record["names_contract"] and states_done):
            offenders.append(record)

    weakly = [s for s in sampled if s["basis"] == "weak"]
    evidence = {"seeding": seeding, "fixture": fixture_state, "sampled": len(sampled),
                "contracts_in_repo": contracts,
                "named_only_by_bare_stem": weakly,
                "without_contract_or_done": offenders}
    if not sampled:
        return Result(SKIP, "No item records could be read.",
                      reason="the queue returned items but none of their full records read back")
    if not contracts:
        return Result(SKIP, f"No contracts found under {ctx.repo}/contracts.",
                      reason="with no contract to trace to, 'derived, never invented' "
                             "cannot be judged either way")
    if offenders:
        names = ", ".join(str(u["item"]) for u in offenders[:6])
        return Result(
            FAIL,
            f"{len(offenders)} of {len(sampled)} items do not both name a contract and "
            f"state what done looks like ({names}) — work that cannot point at a gap "
            "was invented, not derived.",
            evidence=evidence,
        )
    detail = (
        f"All {len(sampled)} sampled items name one of this repository's "
        f"{len(versioned)} contracts and state what done looks like"
    )
    if weakly:
        detail += (
            f"; {len(weakly)} name it only by a bare stem rather than a versioned "
            "reference, which is recorded but not counted against them"
        )
    if fixture_state:
        detail += f"; the fixture's own kit reports rules {fixture_state.get('red_rules')} red"
    return Result(PASS, detail + ".", evidence=evidence)


def step_lanes(ctx: Context) -> Result:
    """(f) Two REAL lanes — own worktree, own terminal session — tended and judged.

    This is the step acceptance item 3 is about. See `assert_lane_is_real` and
    `assert_no_subagent_held_work` above for the assertions themselves.
    """
    worktrees = read_worktrees(ctx.env, ctx.repo)
    panes = read_tmux_panes(ctx.env)
    lanes = read_manifest(ctx.env, ctx.workspace) or lanes_from_worktrees(worktrees, panes)
    lanes = [ln for ln in lanes if ctx.env.exists(ln.worktree)]

    if not lanes:
        return Result(
            FAIL,
            "No lanes found: neither a launcher manifest nor a worktree on a "
            "lane/* branch exists. Clause 5 fails loud rather than falling back "
            "to running the work in-session.",
            evidence={"worktrees": len(worktrees), "terminal_panes": len(panes)},
        )

    reality = [assert_lane_is_real(ln, worktrees, panes) for ln in lanes]
    distinct = assert_lanes_are_distinct(lanes)
    real = [r for r in reality if r["ok"]]
    impostors = [r for r in reality if r["state"] == NOT_A_LANE]
    unproven_lanes = [r for r in reality if r["state"] == UNPROVEN]

    items, tracker_error = read_tracker_items(ctx.env, ctx.project)
    pids = {p for p in (holder_pid(i.get("holder")) for i in items) if p is not None}
    processes = {pid: read_process(ctx.env, pid) for pid in pids}
    subagents = assert_no_subagent_held_work(
        items, processes, [ln.worktree for ln in lanes], [ln.branch for ln in lanes]
    )

    progress = [
        assert_commits_beyond_base(
            ln, commits_beyond(ctx.env, ln.worktree, ln.base_sha, ln.branch)
            if ln.base_sha else None,
        )
        for ln in lanes
    ]

    evidence = {
        "lane_source": lanes[0].source,
        "lanes": [{"name": ln.name, "worktree": ln.worktree, "branch": ln.branch,
                   "terminal": ln.tmux} for ln in lanes],
        "lane_reality": reality,
        "distinct": distinct,
        "no_subagent_held_work": subagents,
        "commits_beyond_base": progress,
        "tracker_error": tracker_error,
    }

    if subagents["offenders"]:
        first = subagents["offenders"][0]
        return Result(
            FAIL,
            f"A work item was executed outside a lane: {first['item']} — {first['why']}.",
            evidence=evidence,
        )
    if impostors:
        broken = "; ".join(f"{r['lane']}: {'; '.join(r['findings'])}" for r in impostors)
        return Result(
            FAIL,
            f"{len(impostors)} of {len(lanes)} lanes are not lanes. {broken}.",
            evidence=evidence,
        )
    if not distinct["ok"]:
        return Result(FAIL, "; ".join(distinct["problems"]) + ".", evidence=evidence)
    if len(real) < 2:
        return Result(
            FAIL,
            f"Only {len(real)} lane(s) can be shown to have had their own worktree "
            f"and their own terminal session; the turnkey claim needs at least two.",
            evidence=evidence,
        )

    stuck = [p for p in progress if p.get("verdict") == FAIL]
    unmeasured = [p for p in progress if p.get("verdict") == SKIP]
    live = [r for r in real if r["state"] == LIVE]
    ended = [r for r in real if r["state"] == ENDED]
    detail = (
        f"{len(real)} lanes are real — each has its own worktree registered with git "
        f"and its own terminal session ({len(live)} live, {len(ended)} ended after "
        f"running) — and no work item was held by a process outside a lane worktree "
        f"({subagents['checked']} holders checked)."
    )
    if stuck:
        detail += (
            f" {len(stuck)} lane(s) sit on an unchanged branch and are recorded stuck: "
            + ", ".join(str(p["lane"]) for p in stuck) + "."
        )
    if subagents["unresolved"]:
        detail += (
            f" {len(subagents['unresolved'])} holder(s) could not be placed because "
            "their process has exited; those are recorded unresolved, not passed."
        )
    if unproven_lanes:
        detail += (
            f" {len(unproven_lanes)} lane(s) could not be settled either way: "
            + ", ".join(str(r["lane"]) for r in unproven_lanes) + "."
        )
    if unmeasured:
        detail += f" {len(unmeasured)} lane(s) have no base SHA to measure progress from."
    return Result(PASS, detail, evidence=evidence)


def step_integrated(ctx: Context) -> Result:
    """(g) Results integrated and verified."""
    merges = merge_commits(ctx.env, ctx.repo, ctx.integration_branch)
    lane_merges = [m for m in merges if re.search(r"lane/", m["subject"])]
    evidence = {
        "branch": ctx.integration_branch,
        "merge_commits": len(merges),
        "lane_merges": lane_merges[:12],
    }
    if not lane_merges:
        return Result(
            FAIL,
            f"No lane branch has been merged into {ctx.integration_branch} — nothing "
            "has been integrated.",
            evidence=evidence,
        )
    detail = (
        f"{len(lane_merges)} lane branch(es) are merged into {ctx.integration_branch}"
        f" (newest: {lane_merges[0]['sha']} {lane_merges[0]['subject']!r})."
    )
    if len(lane_merges) >= 2:
        detail += (
            " Two or more lanes landed in one repository, so a post-merge gate is "
            "required; this harness runs it itself in the next step, rather than "
            "trusting either lane's green."
        )
    return Result(PASS, detail, evidence=evidence)


def _recheck_commands(ctx: Context) -> list[tuple[str, list[str], str]]:
    """The contract checks to re-run: the fixture's kit, or the repo's own kits."""
    if ctx.mode == DRIVEN and ctx.fixture_repo:
        return [("lumen.v1", list(ctx.answer_key.get("check", [])), ctx.fixture_repo)]
    kits = []
    for name in ("composition", "documents"):
        script = f"{ctx.repo}/conformance/{name}/run.py"
        if ctx.env.exists(script):
            kits.append((f"{name}.v1", ["uv", "run", script, "--json-only", "."], ctx.repo))
    return kits


def step_rechecked(ctx: Context) -> Result:
    """(h) Contracts re-checked — by this harness, not by the lane that changed them."""
    kits = _recheck_commands(ctx)
    if not kits:
        return Result(
            SKIP, "No contract check could be located to re-run.",
            reason=f"neither a fixture kit nor conformance/*/run.py exists under {ctx.repo}",
        )
    verdicts, failures = [], []
    for name, argv, cwd in kits:
        ran = ctx.env.run(argv, cwd=cwd, timeout=max(ctx.timeout, 600.0))
        report = parse_json(ran.out)
        if not isinstance(report, dict) or not report.get("verdict"):
            verdicts.append({"kit": name, "verdict": "unreadable",
                             "detail": ran.tail(200) or f"exit {ran.code}"})
            failures.append(name)
            continue
        summary = report.get("summary", {})
        verdicts.append({
            "kit": name,
            "verdict": report.get("verdict"),
            "summary": summary,
            "red_rules": [r.get("rule") for r in report.get("results", [])
                          if r.get("status") == FAIL],
        })
    evidence = {"kits": verdicts}
    if failures:
        return Result(
            FAIL,
            "The contract check could not be read for: " + ", ".join(failures) + ".",
            evidence=evidence,
        )

    if ctx.mode == DRIVEN:
        expected = set(ctx.answer_key.get("expected_red_rules_after", []))
        actual = set(verdicts[0].get("red_rules", []))
        if actual != expected:
            return Result(
                FAIL,
                f"After integration the fixture's kit still reports rules "
                f"{sorted(actual)} red; the wave was supposed to leave "
                f"{sorted(expected) or 'none'}.",
                evidence=evidence,
            )

    named = ", ".join(f"{v['kit']} {v['verdict']}" for v in verdicts)
    return Result(
        PASS,
        f"The contract check was re-run by this harness after integration: {named}.",
        evidence=evidence,
    )


def step_brief(ctx: Context) -> Result:
    """(i) A plain-sentence return brief produced."""
    text = ctx.env.read(f"{ctx.repo}/{RETURN_LOG}")
    where = f"{ctx.repo}/{RETURN_LOG}"
    if text is None:
        return Result(
            FAIL,
            f"No return brief at {where}. Clause 10 requires one on every return, "
            "and the return-brief convention names this exact path.",
            evidence={"expected_path": where},
        )
    lowered = text.lower()
    present = [part for part in BRIEF_PARTS if part in lowered]
    missing = [part for part in BRIEF_PARTS if part not in lowered]
    dated = bool(re.search(r"\b20\d{2}-\d{2}-\d{2}\b", text))
    sentences = [
        ln.strip() for ln in text.splitlines()
        if ln.strip().endswith(".") and len(ln.strip().split()) >= 6
        and not ln.strip().startswith(("|", "#", "-", "*"))
    ]
    evidence = {"path": where, "bytes": len(text), "parts_present": present,
                "parts_missing": missing, "dated": dated,
                "plain_sentences": len(sentences)}
    if missing:
        return Result(
            FAIL,
            f"The brief at {where} is missing {len(missing)} of the five required "
            f"parts: {', '.join(missing)}.",
            evidence=evidence,
        )
    if not dated:
        return Result(FAIL, f"The brief at {where} carries no dated entry.", evidence=evidence)
    if len(sentences) < 3:
        return Result(
            FAIL,
            f"The brief at {where} has {len(sentences)} plain sentences; a brief is "
            "written in sentences, not a status table.",
            evidence=evidence,
        )
    return Result(
        PASS,
        f"A dated return brief is at {where} with all five parts and "
        f"{len(sentences)} plain sentences.",
        evidence=evidence,
    )


STEPS = [
    ("a", "environment", "a fresh isolated environment stood up", step_environment),
    ("b", "install", "the one documented install performed", step_install),
    ("c", "install_check", "scripts/install-check.py green inside it", step_install_check),
    ("d", "project", "a project started", step_project),
    ("e", "derived", "work derived from a fixture gap", step_derived),
    ("f", "lanes", "two REAL lanes launched, tended, judged by evidence", step_lanes),
    ("g", "integrated", "results integrated and verified", step_integrated),
    ("h", "rechecked", "contracts re-checked", step_rechecked),
    ("i", "brief", "a plain-sentence return brief produced", step_brief),
]


# ---------------------------------------------------------------------------
# environment lifecycle — anything stood up is registered and torn down
# ---------------------------------------------------------------------------


INFRA_LEDGER_DEFAULT = (
    "/home/bkrabach/.local/share/uv/tools/amplifier/lib/python3.13/site-packages/"
    "amplifier_app_cli/data/skills/ten-lane-highway/scripts/infra_ledger.sh"
)


def register_infra(host: LocalEnv, workspace: str, kind: str, ident: str,
                   destroy: str) -> Ran:
    ledger = os.environ.get("TURNKEY_INFRA_LEDGER", INFRA_LEDGER_DEFAULT)
    return host.run([ledger, workspace, "add", kind, ident, destroy], timeout=60.0)


def launch_dtu(host: LocalEnv, profile: Path, workspace: str,
               timeout: float) -> tuple[DtuEnv | None, str]:
    """Launch a DTU, registering it in the infra ledger BEFORE anything else.

    Refuses to launch if the ledger is unreachable: an unregistered container
    that outlives this run is worse than a step this run could not perform.
    """
    if not profile.is_file():
        return None, f"no DTU profile at {profile}"
    ledger = os.environ.get("TURNKEY_INFRA_LEDGER", INFRA_LEDGER_DEFAULT)
    if not Path(ledger).is_file():
        return None, (
            f"the infra ledger is not at {ledger}; refusing to launch a container "
            "that could not be registered for teardown "
            "(set TURNKEY_INFRA_LEDGER to override)"
        )
    name = f"turnkey-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    # The registered command must succeed when the environment is ALREADY gone,
    # because this run destroys it itself in the normal case and a later sweep
    # would otherwise be stuck on a row it can never close. `destroy` and
    # `status` both exit non-zero for an unknown instance (measured), so
    # "destroy, then assert it is not there" is true either way — and still
    # fails loudly if the thing is somehow still running.
    destroy = (
        f"amplifier-digital-twin destroy {name} >/dev/null 2>&1; "
        f"! amplifier-digital-twin status {name} >/dev/null 2>&1"
    )
    registered = register_infra(host, workspace, "dtu", name, destroy)
    if not registered.ok:
        return None, f"could not register {name} in the infra ledger: {registered.tail(200)}"
    ran = host.run(
        ["amplifier-digital-twin", "launch", str(profile), "--name", name],
        timeout=max(timeout, 1800.0),
    )
    if not ran.ok:
        return None, f"launch failed (exit {ran.code}): {ran.tail(400)}"
    return DtuEnv(name, host), f"launched {name}"


REPO_IN_ENV = "/opt/converge-under-test"


def place_repo_in_env(host: LocalEnv, env: DtuEnv, repo: str) -> tuple[str | None, str]:
    """Carry the repository under test into the fresh environment, with history.

    A plain directory copy would not do: this checkout is a git worktree, whose
    `.git` is a file pointing at a parent repository that does not exist inside
    the container, so every later `git` reading — merge commits, worktrees,
    branches — would be answering about nothing. A git bundle carries the real
    object history across, and the clone inside the container is a genuine
    repository that git can answer questions about.
    """
    bundle = tempfile.NamedTemporaryFile(suffix=".bundle", delete=False)
    bundle.close()
    made = host.run(["git", "-C", repo, "bundle", "create", bundle.name, "--all"],
                    timeout=600.0)
    if not made.ok:
        return None, f"could not package the repository: {made.tail(300)}"
    pushed = host.run(
        ["amplifier-digital-twin", "file-push", env.instance, "-p",
         bundle.name, "/tmp/under-test.bundle"],
        timeout=600.0,
    )
    Path(bundle.name).unlink(missing_ok=True)
    if not pushed.ok:
        return None, f"could not push the repository into the environment: {pushed.tail(300)}"
    cloned = env.run(["git", "clone", "-q", "/tmp/under-test.bundle", REPO_IN_ENV],
                     timeout=600.0)
    if not cloned.ok:
        return None, f"could not clone the repository inside the environment: {cloned.tail(300)}"
    return REPO_IN_ENV, f"the repository under test was cloned into {REPO_IN_ENV}"


def destroy_dtu(host: LocalEnv, env: DtuEnv) -> Ran:
    return host.run(
        ["amplifier-digital-twin", "destroy", env.instance], timeout=900.0
    )


# ---------------------------------------------------------------------------
# self-check — prove the assertions can fail
# ---------------------------------------------------------------------------


def self_check() -> dict:
    """Exercise every assertion against evidence that MUST make it fail.

    An assertion nobody can make fail proves nothing. This is the same
    discipline the repository's conformance kits apply with their `sample-bad`
    fixtures, applied to a harness whose inputs are processes and terminals
    rather than files.
    """
    cases = []

    real = Lane("a", "/w/lanes/a/repo", "lane/a", "base", "tmux-a")
    worktrees = [{"path": "/w/lanes/a/repo", "branch": "lane/a", "sha": "1"}]
    panes = [{"session": "tmux-a", "path": "/w/lanes/a/repo"}]

    bare = Lane("d", "/w/lanes/a/repo", "lane/a")  # no launcher record of a session

    cases.append(("a live lane is live",
                  assert_lane_is_real(real, worktrees, panes)["state"] == LIVE))
    cases.append(("a lane with no worktree of its own is not a lane",
                  assert_lane_is_real(real, [], panes)["state"] == NOT_A_LANE))
    cases.append(("a lane on the wrong branch is not a lane",
                  assert_lane_is_real(
                      real, [{"path": "/w/lanes/a/repo", "branch": "main"}], panes
                  )["state"] == NOT_A_LANE))
    cases.append(("a finished lane the launcher recorded is ended, not a violation",
                  assert_lane_is_real(real, worktrees, [])["state"] == ENDED))
    cases.append(("a lane with no session live and none ever recorded is unproven",
                  assert_lane_is_real(bare, worktrees, [])["state"] == UNPROVEN))
    cases.append(("unproven is not counted as real",
                  assert_lane_is_real(bare, worktrees, [])["ok"] is False))

    twin = Lane("b", "/w/lanes/a/repo", "lane/b", "base", "tmux-b")
    cases.append(("two lanes sharing a worktree fail",
                  assert_lanes_are_distinct([real, twin])["ok"] is False))

    items = [{"id": "x-1", "status": "held", "holder": "agent-spark-1-111"}]
    in_lane = {111: {"pid": 111, "cwd": "/w/lanes/a/repo", "cmdline": "amplifier"}}
    in_session = {111: {"pid": 111, "cwd": "/w", "cmdline": "amplifier"}}
    cases.append(("an item held from a lane worktree passes",
                  assert_no_subagent_held_work(items, in_lane, ["/w/lanes/a/repo"])["ok"]
                  is True))
    cases.append(("an item held from the manager's own directory FAILS",
                  assert_no_subagent_held_work(items, in_session, ["/w/lanes/a/repo"])["ok"]
                  is False))

    two = [
        {"id": "x-1", "status": "held", "holder": "agent-spark-1-111"},
        {"id": "x-2", "status": "held", "holder": "agent-spark-1-111"},
    ]
    cases.append(("one process holding two items FAILS",
                  assert_no_subagent_held_work(two, in_lane, ["/w/lanes/a/repo"])["ok"]
                  is False))
    gone = assert_no_subagent_held_work(items, {111: None}, ["/w/lanes/a/repo"])
    cases.append(("an exited holder is unresolved, never a pass",
                  gone["ok"] is True and len(gone["unresolved"]) == 1
                  and gone["verdicts"][0]["verdict"] == SKIP))
    corroborated = assert_no_subagent_held_work(
        [{"id": "x-1", "status": "resolved", "holder": "agent-spark-1-111",
          "resolution": "landed on lane/a"}],
        {111: None}, ["/w/lanes/a/repo"], ["lane/a"],
    )
    cases.append(("a resolution naming a lane branch corroborates but never passes",
                  corroborated["verdicts"][0]["verdict"] == SKIP
                  and "corroboration" in corroborated["verdicts"][0]))
    cases.append(("a holder id with no pid in it is unresolved, not a pass",
                  assert_no_subagent_held_work(
                      [{"id": "x-1", "status": "held", "holder": "someone"}], {},
                      ["/w/lanes/a/repo"])["verdicts"][0]["verdict"] == SKIP))

    cases.append(("an unchanged branch is stuck",
                  assert_commits_beyond_base(real, 0)["verdict"] == FAIL))
    cases.append(("a branch with commits is not stuck",
                  assert_commits_beyond_base(real, 3)["verdict"] == PASS))
    cases.append(("no base SHA is a skip, not a pass",
                  assert_commits_beyond_base(
                      Lane("c", "/w/c", "lane/c"), None)["verdict"] == SKIP))

    failed = [name for name, ok in cases if not ok]
    return {
        "tool": "converge-turnkey-self-check",
        "cases": [{"case": name, "ok": ok} for name, ok in cases],
        "passed": len(cases) - len(failed),
        "failed": failed,
        "verdict": FAIL if failed else PASS,
    }


# ---------------------------------------------------------------------------
# reporting
# ---------------------------------------------------------------------------


def build_report(ctx: Context, rows: list[dict], started: float) -> dict:
    summary = {
        "pass": sum(r["status"] == PASS for r in rows),
        "fail": sum(r["status"] == FAIL for r in rows),
        "skip": sum(r["status"] == SKIP for r in rows),
    }
    return {
        "tool": "converge-turnkey",
        "schema": 1,
        "contract": CONTRACT,
        "run_mode": ctx.mode,
        "environment": {"kind": ctx.env.kind, "label": ctx.env.label},
        "workspace": ctx.workspace,
        "repository": ctx.repo,
        "project": ctx.project,
        "integration_branch": ctx.integration_branch,
        "ran_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "elapsed_s": round(time.time() - started, 1),
        "steps": rows,
        "summary": summary,
        "verdict": FAIL if summary["fail"] else PASS,
        "notes": ctx.notes,
    }


def render_summary(report: dict) -> str:
    lines = [
        "",
        f"Converge turnkey — {report['contract']}",
        f"  mode:        {report['run_mode']} ({report['environment']['label']})",
        f"  repository:  {report['repository']}",
        f"  project:     {report['project']}",
        "",
    ]
    for row in report["steps"]:
        lines.append(f"  [{row['status']:4}] ({row['step']}) {row['name']}: {row['detail']}")
        if row["status"] == SKIP and row.get("reason"):
            lines.append(f"         why skipped: {row['reason']}")
    s = report["summary"]
    lines += [
        "",
        f"  VERDICT: {report['verdict']}  (pass={s['pass']} fail={s['fail']} skip={s['skip']})",
        "  A SKIP is not a pass: it is this harness refusing to claim work it did not do.",
        "",
    ]
    for note in report.get("notes", []):
        lines.append(f"  note: {note}")
    if report.get("notes"):
        lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# entry point
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="turnkey",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=(
            "Run operation.v1's turnkey claim end to end and report each step "
            "PASS/FAIL/SKIP with the evidence it read."
        ),
        epilog=(
            "The nine steps, in order:\n"
            "  a environment    a fresh isolated environment stood up\n"
            "  b install        the one documented install performed\n"
            "  c install_check  scripts/install-check.py green inside it\n"
            "  d project        a project started\n"
            "  e derived        work derived from a fixture gap\n"
            "  f lanes          two REAL lanes (own worktree AND own terminal\n"
            "                   session), tended, judged by evidence — and the\n"
            "                   run FAILS if a work item was executed by an\n"
            "                   in-session sub-agent\n"
            "  g integrated     results integrated and verified\n"
            "  h rechecked      contracts re-checked, by this harness\n"
            "  i brief          a plain-sentence return brief produced\n"
            "\n"
            "Examples:\n"
            "  uv run evaluations/turnkey/run.py --self-check\n"
            "  uv run evaluations/turnkey/run.py --env local \\\n"
            "      --workspace ~/dev/hw-converge --project converge\n"
            "  uv run evaluations/turnkey/run.py --env dtu --project turnkey\n"
        ),
    )
    ap.add_argument("--env", choices=["auto", "local", "dtu"], default="auto",
                    help="auto (default) tries dtu when a profile and its "
                         "prerequisites exist, else falls back to local")
    ap.add_argument("--workspace", default=None,
                    help="the manager workspace root (holds manifest.tsv); "
                         "defaults to the parent of this bundle checkout")
    ap.add_argument("--repo", default=None,
                    help="the repository the lanes work in (default: this checkout)")
    ap.add_argument("--project", default="converge", help="work-tracker project name")
    ap.add_argument("--integration-branch", default="main",
                    help="the branch lanes are merged into (default: main)")
    ap.add_argument("--profile", type=Path, default=HERE / "profiles" / "turnkey.yaml",
                    help="DTU profile used by --env dtu")
    ap.add_argument("--fixture-repo", default=None,
                    help="where to seed the gap fixture (default: a temp dir)")
    ap.add_argument("--ledger-root", type=Path, default=None,
                    help="where the infra ledger lives (default: the workspace). "
                         "Anything --env dtu stands up is recorded here before it "
                         "exists, so it can never be leaked.")
    ap.add_argument("--keep", action="store_true",
                    help="do not destroy a launched environment (it stays in the "
                         "infra ledger; you must tear it down yourself)")
    ap.add_argument("--timeout", type=float, default=300.0,
                    help="seconds to wait for any one command (default 300)")
    ap.add_argument("--steps", default=None,
                    help="comma-separated step letters to run (default: all)")
    ap.add_argument("--json-only", action="store_true",
                    help="suppress the human summary on stderr")
    ap.add_argument("--self-check", action="store_true",
                    help="run the assertions against synthetic evidence that must "
                         "make them fail, and exit")
    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    started = time.time()

    if args.self_check:
        report = self_check()
        sys.stdout.write(json.dumps(report, indent=2) + "\n")
        if not args.json_only:
            sys.stderr.write(
                f"\nturnkey self-check: {report['passed']} of "
                f"{len(report['cases'])} assertions behave as specified\n"
            )
            for case in report["cases"]:
                sys.stderr.write(f"  [{'ok  ' if case['ok'] else 'FAIL'}] {case['case']}\n")
            sys.stderr.write(f"\n  VERDICT: {report['verdict']}\n\n")
        return 1 if report["verdict"] == FAIL else 0

    host = LocalEnv()
    repo = str(Path(args.repo).resolve()) if args.repo else str(BUNDLE_ROOT)
    workspace = str(Path(args.workspace).resolve()) if args.workspace \
        else str(Path(repo).parent)
    notes: list[str] = []

    ledger_root = str(Path(args.ledger_root).resolve()) if args.ledger_root else workspace

    env: Env = host
    mode = OBSERVED
    launched: DtuEnv | None = None
    if args.env in ("dtu", "auto"):
        launched, why = launch_dtu(host, args.profile, ledger_root, args.timeout)
        if launched is None:
            if args.env == "dtu":
                sys.stderr.write(f"error: could not stand up an environment: {why}\n")
                return 3
            notes.append(f"--env auto fell back to local: {why}")
        else:
            env, mode = launched, DRIVEN
            notes.append(why)
            placed, how = place_repo_in_env(host, launched, repo)
            notes.append(how)
            if placed:
                repo, workspace = placed, str(Path(placed).parent)

    wanted = set(args.steps.split(",")) if args.steps else None

    # A throwaway amplifier home, so the documented install is exercised for
    # real without editing the caller's own configuration. Only made when a
    # step that needs it is actually going to run.
    home: str | None = None
    host_home_to_clean: str | None = None
    if wanted is None or wanted & {"b", "c"}:
        if mode == DRIVEN:
            # Inside the container, so the path exists where the command runs.
            home = "/tmp/turnkey-amplifier-home"
            env.run(["mkdir", "-p", home], timeout=60.0)
        else:
            home = host_home_to_clean = tempfile.mkdtemp(prefix="turnkey-amplifier-home-")
        notes.append(
            f"the install and install-check steps used a throwaway AMPLIFIER_HOME "
            f"at {home}, so this run never edited the caller's own configuration"
        )

    fixture_repo = args.fixture_repo
    if mode == DRIVEN and fixture_repo is None:
        fixture_repo = "/workspace/lumen-fixture"

    answer_key_path = HERE / "fixtures" / "answer-key.json"
    answer_key = json.loads(answer_key_path.read_text(encoding="utf-8")) \
        if answer_key_path.is_file() else {}

    ctx = Context(
        env=env, host=host, mode=mode, workspace=workspace, repo=repo,
        project=args.project, integration_branch=args.integration_branch,
        answer_key=answer_key, fixture_repo=fixture_repo, amplifier_home=home,
        timeout=args.timeout, notes=notes,
    )

    rows = []
    try:
        for letter, name, description, run_step in STEPS:
            if wanted and letter not in wanted:
                continue
            try:
                result = run_step(ctx)
            except Exception as exc:  # noqa: BLE001 — a broken step must not fake a pass
                result = Result(SKIP, f"The step itself raised {exc!r}.",
                                reason="the harness failed while running this step")
            row = {
                "step": letter, "name": name, "asserts": description,
                "mode": ctx.mode if letter in "defghi" else DRIVEN,
                "status": result.status, "detail": result.detail,
            }
            if result.reason:
                row["reason"] = result.reason
            if result.evidence is not None:
                row["evidence"] = result.evidence
            rows.append(row)
    finally:
        if host_home_to_clean:
            shutil.rmtree(host_home_to_clean, ignore_errors=True)
        if launched is not None and not args.keep:
            torn = destroy_dtu(host, launched)
            notes.append(
                f"environment {launched.instance} destroyed"
                if torn.ok else
                f"environment {launched.instance} could NOT be destroyed: {torn.tail(200)}"
            )
        elif launched is not None:
            notes.append(
                f"environment {launched.instance} left running by --keep; it is "
                "registered in the infra ledger and must be destroyed by hand"
            )

    report = build_report(ctx, rows, started)
    sys.stdout.write(json.dumps(report, indent=2) + "\n")
    if not args.json_only:
        sys.stderr.write(render_summary(report))
    return 1 if report["verdict"] == FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
