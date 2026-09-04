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

# A part is present in an ENTRY when a line of that entry OPENS with the part's
# own label -- the labelled form `modes/converge-manager.md` clause 10 requires
# (`**Time away.** ...`), a list item carrying it, or the bare label closed by
# its punctuation. Asking whether the five words appear ANYWHERE in the file is
# the defect this shape replaces: a header, a footnote, or a paragraph that
# happens to use them passed the old check with no brief in the file at all.
# Prose mentioning a word in passing does not match: the label must open a line
# AND be closed by a bold marker or by `.`/`:`/em-dash.
_PART_LABELS = [
    ("time away", r"time[ \t]+away"),
    ("finished", r"finished"),
    ("stuck", r"stuck"),
    ("needs you", r"needs[ \t]+you"),
    ("quietly broken", r"(?:anything[ \t]+)?quietly[ \t]+broken"),
]


def _part_pattern(label: str) -> re.Pattern:
    return re.compile(
        r"^[ \t]*(?:(?:[-*+>]|\d+[.)])[ \t]*)*"           # a list marker or quote, if any
        r"(?:"
        r"(?:\*\*|__)[ \t]*" + label + r"[ \t]*[.:\u2014]?[ \t]*(?:\*\*|__)"  # **Label.**
        r"|" + label + r"[ \t]*[.:\u2014]"                # Label. / Label: / Label --
        r")",
        re.IGNORECASE | re.MULTILINE,
    )


BRIEF_PART_PATTERNS = [(name, _part_pattern(pat)) for name, pat in _PART_LABELS]

# An entry heading. `\b` after the day rejects an ISO-8601 timestamp's own
# hyphens -- 2026-09-04T04:01Z has a word character where the boundary must be,
# so a perfectly dated brief read as undated (measured, run C). A date followed
# by a time is a date.
ENTRY_DATE = re.compile(r"\b20\d{2}-\d{2}-\d{2}(?![-\d])")

# A STAMPED return: the heading the manager session writes the moment the
# steward's message arrives (`## <date> <HH:MM> - ...`). The stamp is the record
# that a return happened; the five parts under it are the brief. Counting the
# two against each other is the only way to see a return that never got one.
RETURN_STAMP = re.compile(r"^#{2,}[ \t]+(20\d{2}-\d{2}-\d{2})[ \tT]+(\d{2}:\d{2})")

# An entry begins at a dated heading of any depth BELOW the file's own title.
# `#{2,}` on purpose: the title is `# Owner return log`, and treating it as an
# entry is precisely how the file's header came to count as a brief.
ENTRY_HEADING = re.compile(r"^#{2,}[ \t]")

# A line that is a table row or a heading is not a plain sentence. A leading
# list marker is stripped rather than disqualifying: `- **Stuck.** nothing
# stopped.` is a sentence written as a list item, and a rule that scored it zero
# would fabricate a red against a correctly written brief.
_NOT_A_SENTENCE = re.compile(r"^[|#]")
_LEADING_MARKER = re.compile(r"^(?:[-*+]|\d+\.)[ \t]+")

# The terminal-session socket the lane launcher uses (HIGHWAY_TMUX_SOCKET's own
# default). A lane started by the launcher is invisible to a bare `tmux
# list-panes -a`, which reads the DEFAULT socket only -- so every reading here
# unions both, and records which socket answered.
LANE_TMUX_SOCKET = "hw"

# Where the wave's own state lives inside a driven environment.
WAVE_BATCH_IN_ENV = "/workspace/turnkey-batch"
WAVE_OBJECTIVE_IN_ENV = f"{WAVE_BATCH_IN_ENV}/objective.md"
WAVE_LOG_IN_ENV = f"{WAVE_BATCH_IN_ENV}/manager.log"
WAVE_EXIT_IN_ENV = f"{WAVE_BATCH_IN_ENV}/manager.exit"

# The lane launcher, as installed with the amplifier CLI. Probed at wave time
# rather than assumed -- the interpreter version is in the path.
LAUNCHER_GLOBS = [
    "/root/.local/share/uv/tools/amplifier/lib/python*/site-packages/amplifier_app_cli/"
    "data/skills/ten-lane-highway/scripts/launch_lane.sh",
    "/root/.local/share/uv/tools/amplifier/lib/*/site-packages/amplifier_app_cli/"
    "data/skills/ten-lane-highway/scripts/launch_lane.sh",
]

# Holder ids look like "agent-spark-1-425543". The trailing integer is the OS
# pid of the holding process — verified against /proc on this host, 2026-09-02.
# This is an inferred convention, not a documented interface: when it does not
# parse, the check says so and SKIPs rather than guessing.
HOLDER_PID = re.compile(r"-(\d+)$")

# ---------------------------------------------------------------------------
# operation.v1's OTHER clauses — the ones the nine steps never read
# ---------------------------------------------------------------------------
#
# Steps (a)-(i) run the contract's turnkey SENTENCE. Ten Core clauses sit
# outside that sentence, and every one of them is a promise about what a
# MANAGER SESSION does across a wave rather than about what a file contains.
# The ledger's probes for those ten read `modes/converge-manager.md` for the
# clause's own section heading, which proves the rule was written down and
# nothing about whether anybody followed it.
#
# Steps (j) and (k) read what a wave LEFT: the lane briefs the manager session
# wrote, its own plan record, git's first-parent line, the queue's resolutions.
# Never the mode file.
#
# Each clause names its ledger row here, so a reading can be re-derived into
# `ledger/rows.yaml` by whoever owns that file. This harness never writes it.
OPERATION_CLAUSES: dict[int, tuple[str, str]] = {
    2: ("CVG-012", "the plan is visible"),
    3: ("CVG-013", "never the bottleneck"),
    4: ("CVG-014", "feedback is signal, not a ticket"),
    6: ("CVG-016", "width is a collision decision"),
    7: ("CVG-017", "done means the manager session re-ran the check"),
    8: ("CVG-018", "integrate, verify, re-check"),
    9: ("CVG-019", "stalls are decisions, not loops"),
    11: ("CVG-021", "four calls reach the steward"),
    12: ("CVG-022", "the queue is the shared one, with custody"),
    13: ("CVG-023", "hand off when done"),
}

# The manager session's own plan record, in the launcher's workspace beside
# `manifest.tsv`. Several names are looked for and the one that answered is
# reported, so a workspace using another convention is a named SKIP rather
# than a silent one.
PLAN_RECORDS = ("HIGHWAY.md", "PLAN.md", "WAVE-LOG.md")

# A dated entry in that record: `- <ISO timestamp> <what happened>`.
PLAN_ENTRY = re.compile(r"^[-*][ \t]*(20\d{2}-\d{2}-\d{2}T[0-9:Z+-]+)[ \t]+(.*)$",
                        re.MULTILINE)

# A decision about how wide the wave ran, and a reason for it. Clause 2 asks
# for reasons, not announcements: "merged X. Live 4." records what happened;
# "No refill possible without a collision" records why.
PLAN_DECISION = re.compile(r"\b(refill|width|collis|collide|park|merged|launch)", re.I)
PLAN_REASON = re.compile(
    r"\b(because|since|collides?|collision|justified|no ready|no refill|blocked|"
    r"hung|died|stuck|needs|waiting|deferred|parked)", re.I
)

# A close: the manager session ending by choice, which clause 13 says must
# leave a hand-off a fresh session can resume from.
PLAN_CLOSE = re.compile(r"\bCLOSED\b")
# What makes a close resumable: it says what REMAINS, not only what finished.
PLAN_REMAINS = re.compile(
    r"\b(residual|parked|live|open|next|remaining|unexplained|blocked|pending)", re.I
)

# A feedback triage recorded in the plan: raw report in, work item out. The
# item id is what lets the harness put the report and the filing side by side,
# and it is matched against THIS run's project name rather than any dashed
# word, so a lane name in the same sentence is never fetched as an item.
PLAN_FEEDBACK = re.compile(r"feedback", re.I)

# A lane brief's file-ownership split (`skills/lane-brief` calls it "an
# explicit file-ownership split"; every brief in this workspace writes it as
# **File ownership — edit ONLY:** followed by backticked paths).
BRIEF_OWNERSHIP = re.compile(r"^.*file[ \t]+ownership.*$", re.IGNORECASE | re.MULTILINE)
BACKTICKED = re.compile(r"`([^`]+)`")

# Files that record a CHECK HAVING BEEN RUN — the ledger's `RAN <date>` notes
# and this harness's own recorded result. Clause 7 and clause 8 are about who
# re-ran the check, and these were, until the convention below, the only
# artifacts in the repository that a check run leaves behind.
CHECK_RECORDS = ("ledger/rows.yaml", "evaluations/turnkey/RESULT.md")

# The manager session's OWN record of the post-merge re-check, written in its
# own commit on the integration branch. Both files above are edited by lanes, so
# the newest commit touching either arrives through a lane merge — measured on
# this repository 2026-09-04, which is why the attribution below could see seven
# integrator-written records in the history and still not say who verified the
# newest wave. A file only the manager session writes takes the confusion out of
# the question. The convention is written in the file itself and taught in
# `modes/converge-manager.md` clause 8; this harness only reads it.
MANAGER_CHECK_RECORD = "docs/workflow/CHECK-RECORD.md"

# An entry in that record: `## <date> <HH:MM> - <what was integrated>`. The same
# stamped shape a return-log entry carries, for the same reason — a stamp is
# countable by somebody who was not in the session.
CHECK_ENTRY = re.compile(
    r"^#{2,}[ \t]+(20\d{2}-\d{2}-\d{2})[ \tT]+(\d{2}:\d{2})[ \t]*[-:\u2014]?[ \t]*(.*)$",
    re.MULTILINE,
)

# A check RUN leaves a command behind. An entry naming no command is a claim
# that a check happened, which is the one thing this step exists not to take on
# trust. A fenced block counts; so does a backticked command long enough to be
# one.
CHECK_COMMAND = re.compile(r"`([A-Za-z][^`\n]{5,})`")
CHECK_FENCE = re.compile(r"(?:```|~~~)[^\n]*\n(.+?)(?:```|~~~)", re.S)
CHECK_INDENTED = re.compile(r"^[ \t]{4,}(\S.*)$", re.MULTILINE)

# A CALL to the steward, stamped in the plan record. Clause 11 says exactly four
# reach them; clause 3 asks what kept moving while one was outstanding. One line
# carries both:
#
#   - <ISO> CALL ratify - the clause 15 candidate needs your word.
#     Parked: w8-clause15. Continued: console, direction-writes.
#
# The looser form this workspace's manager sessions already write is read too —
# a cycle entry saying `Parked: x` and `Live: a, b` records the same two facts —
# and every reading says which form answered it. `\b` on the park word is not
# decoration: without it `spark-1`, the hostname in this workspace's own plan
# record, was counted as a park (measured, 5 entries where 4 are real).
PARK = re.compile(r"\bpark(?:ed|s|ing)?\b", re.I)
# A sentence break is a period, semicolon or dash FOLLOWED BY A SPACE, so
# `PROTOCOL.md` keeps its dot — splitting on a bare period cut the first real
# park sentence in this workspace's plan record in half (measured).
SENTENCE_BREAK = re.compile(r"(?<=[.;])[ \t]+")
CALL_STAMP = re.compile(r"\bCALL[ \t]+([A-Za-z][A-Za-z ]{2,20}?)[ \t]*[-:\u2014]")
CONTINUED = re.compile(r"\bContinued[ \t]*:[ \t]*([^.;]*)", re.I)
# `Live: a, b` names them; `Live 4` counts them. Both are the same fact, and a
# reading that took only the first would find nothing in this workspace's newer
# entries, which count.
STILL_LIVE = re.compile(r"\bLive[ \t]*(?::[ \t]*([^.;]*)|([0-9]+))", re.I)

# Why nothing else could move while the steward's word was outstanding.
# Deliberately NOT `PLAN_REASON`: that pattern counts the word "parked" itself
# as a reason, so every park would excuse itself and the failing case could
# never fire — measured, the self-check case caught it.
IDLE_REASON = re.compile(
    r"\b(because|since|collides?|collision|no ready|no refill|nothing ready|"
    r"nothing else|everything else|blocked|depends on|the same word|"
    r"awaiting the same)\b", re.I)

# The four calls clause 11 sanctions, each with the words a manager session
# actually writes for it. A call naming none of these is UNREAD, never a
# violation: the clause is broken by a fifth kind of call reaching the steward,
# not by an entry that failed to say which kind it was.
CALL_WORDS = (
    ("ratify", re.compile(r"\bratif\w*", re.I)),
    ("irreversible", re.compile(r"\birreversib\w*|\bdestructive\b", re.I)),
    ("human check", re.compile(r"\bhuman check\b|\bonly a (?:person|human|device)\b",
                               re.I)),
    ("priority", re.compile(r"\bpriorit\w*|\bstop the run\b|\bkill the run\b", re.I)),
)

# What a resolution must not be if it was written for whoever asked: a sha, an
# issue number, a path, a bare status word.
WORD = re.compile(r"[A-Za-z][A-Za-z'\u2019-]+")
POINTER_ONLY = re.compile(r"^(?:[0-9a-f]{7,40}|#\d+|\S+/\S+|done|fixed|ok|wontfix)$", re.I)

# The observations these readings wait on, written out once so a SKIP names the
# same thing every time it is read. Each names something a manager session can
# actually produce — the stamp `modes/converge-manager.md` clauses 3 and 11 ask
# for — rather than a wish. An awaited observation nobody can take is a way of
# never being answerable.
AWAITED = {
    3: "a park stamped in the plan record with what continued beside it — "
       "`CALL <one of four> - <what is asked>. Parked: <items>. Continued: "
       "<what kept moving>` — or a cycle entry that names both a park and the "
       "lanes still live at that moment. Clause 3's promise is a comparison, so "
       "a park recorded alone cannot be told from a wave that stopped",
    11: "a call stamped with which of the four it is — `CALL ratify`, `CALL "
        "irreversible`, `CALL human check`, `CALL priority` — in the plan "
        "record, at the moment of the call. evaluations/ratchet counts "
        "owner-facing events for the RECONCILER; a manager session's calls are "
        "recorded nowhere else, so a call nobody stamped leaves no trace to "
        "classify",
}


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
    # The launcher also records WHERE the brief it was given lives and WHEN it
    # started. Steps (j) and (k) read both; steps (a)-(i) do not, so these stay
    # optional and a manifest without the columns is not a failure.
    goal: str | None = None
    launched_at: str | None = None


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


def read_tmux_panes(env: Env, sockets: tuple[str | None, ...] = (None, LANE_TMUX_SOCKET)
                    ) -> list[dict]:
    """Every live terminal session and the directory its pane is sitting in.

    Reads EVERY socket named, not just the default one. `tmux list-panes -a`
    answers only about the socket it is pointed at, and the lane launcher uses
    `-L hw` -- so a single default-socket reading would report zero lanes in a
    container where two lanes are visibly running, which is a fabricated FAIL
    of exactly the kind this harness exists to refuse.
    """
    panes: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for socket in sockets:
        argv = ["tmux"] + (["-L", socket] if socket else []) + [
            "list-panes", "-a", "-F", "#{session_name}\t#{pane_current_path}"
        ]
        ran = env.run(argv, timeout=60.0)
        if not ran.ok:
            continue
        for line in ran.out.splitlines():
            session, _, path = line.partition("\t")
            session, path = session.strip(), path.strip()
            if not session or (session, path) in seen:
                continue
            seen.add((session, path))
            panes.append({"session": session, "path": path,
                          "socket": socket or "default"})
    return panes


def read_tmux_sessions(env: Env, socket: str = LANE_TMUX_SOCKET) -> list[str]:
    """Just the session names on one socket -- what `tmux -L <socket> ls` shows."""
    ran = env.run(["tmux", "-L", socket, "list-sessions", "-F", "#{session_name}"],
                  timeout=60.0)
    return [ln.strip() for ln in ran.out.splitlines() if ln.strip()] if ran.ok else []


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
                goal=record.get("goal") or None,
                launched_at=record.get("launched_at") or None,
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


def commits_beyond(env: Env, repo: str, base: str, branch: str,
                   fallback_repo: str | None = None) -> int | None:
    """How many commits `branch` carries beyond `base`, from any clone that knows.

    `base..branch` is a question about two refs, and any repository holding
    both can answer it. The lane's own worktree is asked first because it is
    the lane's own copy — but a finished wave removes its worktrees after
    merging, and `git -C <a directory that no longer exists>` fails. Measured
    on run E: both lanes came back "git could not count commits", so clause 7's
    commits-beyond-base check was unmeasured on a wave whose branches were
    sitting right there in the main repository, merged.
    """
    for where in [repo, fallback_repo]:
        if not where:
            continue
        ran = env.run(
            ["git", "-C", where, "rev-list", "--count", f"{base}..{branch}"],
            timeout=60.0,
        )
        if ran.ok:
            try:
                return int(ran.out.strip())
            except ValueError:
                return None
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


def changed_files(env: Env, repo: str, base: str, branch: str,
                  fallback_repo: str | None = None) -> list[str] | None:
    """Which files `branch` changed beyond `base`. None when git cannot answer.

    The same two-repository fallback `commits_beyond` uses, for the same
    measured reason: a merged lane's own worktree is gone, and the question is
    about two refs any clone holding both can answer.
    """
    for where in [repo, fallback_repo]:
        if not where:
            continue
        ran = env.run(["git", "-C", where, "diff", "--name-only", f"{base}..{branch}"],
                      timeout=60.0)
        if ran.ok:
            return [line.strip() for line in ran.out.splitlines() if line.strip()]
    return None


def read_plan_record(env: Env, workspace: str) -> tuple[str | None, str | None]:
    """The manager session's own plan record, and where it was found.

    Clause 2 says the plan is VISIBLE — which means visible to somebody who was
    not in the session. The only place that can be true is a file, and the
    launcher's workspace is where this system's manager sessions keep one.
    """
    for name in PLAN_RECORDS:
        path = f"{workspace}/{name}"
        text = env.read(path)
        if text:
            return path, text
    return None, None


def parse_plan_entries(text: str) -> list[dict]:
    """The dated entries of a plan record, each with what it decided and why."""
    entries = []
    for stamp, body in PLAN_ENTRY.findall(text or ""):
        entries.append({
            "at": stamp,
            "text": body.strip(),
            "decision": bool(PLAN_DECISION.search(body)),
            "reason": bool(PLAN_REASON.search(body)),
            "close": bool(PLAN_CLOSE.search(body)),
            "feedback": bool(PLAN_FEEDBACK.search(body)),
        })
    return entries


def _names(blob: str | None) -> list[str]:
    """The names in a comma-separated list, with the words for none dropped."""
    out = []
    for token in re.split(r"[,\u00b7]|\band\b", blob or ""):
        token = token.strip(" .`*-\u2014").strip()
        if not token or token.lower() in ("none", "nothing", "nobody", "no lanes",
                                          "no lane", "n/a"):
            continue
        out.append(token)
    return out


def _what_continued(text: str) -> tuple[int | None, list[str], str | None]:
    """How much kept moving while the steward's word was outstanding.

    Two forms are read, and the reading says which answered. `Continued: a, b`
    is the stamp `modes/converge-manager.md` clause 3 asks for. `Live: a, b` and
    `Live 4` are what this workspace's manager sessions already write in a cycle
    entry, and they record the same fact at the same moment.

    None means the entry never said — which is different from saying nothing
    continued, and is why the two are never collapsed here.
    """
    stamped = CONTINUED.search(text)
    if stamped:
        named = _names(stamped.group(1))
        return len(named), named, "the stamped `Continued:` list"
    live = STILL_LIVE.search(text)
    if live and live.group(1) is not None:
        named = _names(live.group(1))
        return len(named), named, "the entry's own `Live:` list"
    if live and live.group(2) is not None:
        return int(live.group(2)), [], "the entry's own live count"
    return None, [], None


def _call_named(entry: str, park_sentence: str) -> tuple[str | None, str | None]:
    """Which of the four calls this entry names, and the words it named it with.

    Two places are read, and only two. The stamp `CALL <word>` is unambiguous
    wherever it sits in the entry, because nothing else writes it. Failing that,
    the loose form is read from the PARK'S OWN SENTENCE and nowhere else: read
    from the whole entry, a cycle that merged a guard fix mentioning "RATIFIED =
    locked" and separately parked something unrelated came back classified as a
    ratify call — measured on this workspace's plan record, and a classification
    nobody wrote and nobody could defend.

    Returns (call, raw). A stamped `CALL <word>` whose word is none of the four
    comes back as (None, word) — a fifth kind of call reaching the steward, which
    is the defect clause 11 names. An entry that names no call at all comes back
    as (None, None): unread, not a violation.
    """
    stamp = CALL_STAMP.search(entry)
    if stamp:
        raw = stamp.group(1).strip()
        for name, pattern in CALL_WORDS:
            if pattern.search(raw):
                return name, raw
        return None, raw
    for name, pattern in CALL_WORDS:
        hit = pattern.search(park_sentence)
        if hit:
            return name, hit.group(0)
    return None, None


def parse_park_events(entries: list[dict]) -> list[dict]:
    """Every plan entry that records work parked on the steward's word.

    Three things come off each one, and clauses 3 and 11 need different ones:
    what was parked, which of the four calls it waits on, and what kept moving
    beside it. The call is looked for in the park's own sentence rather than the
    whole entry, so a cycle that merged a lane called `ratify-card` and parked
    something unrelated is not read as a ratify call.
    """
    events = []
    for entry in entries:
        text = entry.get("text") or ""
        stamp = CALL_STAMP.search(text)
        if not PARK.search(text) and not stamp:
            continue
        sentences = [s for s in SENTENCE_BREAK.split(text) if PARK.search(s)]
        parked = (sentences[0] if sentences else
                  (stamp.group(0) if stamp else text)).strip()
        call, raw = _call_named(text, parked)
        count, named, source = _what_continued(text)
        events.append({
            "at": entry.get("at"),
            "parked": parked[:200],
            "call": call,
            "call_named": raw,
            "continued": count,
            "continued_names": named[:8],
            "continued_source": source,
            "reason": bool(IDLE_REASON.search(text)),
            "stamped": bool(CALL_STAMP.search(text)),
        })
    return events


def _declaration(line: str) -> str:
    """The part of an ownership line that is the DECLARATION, not the prose.

    Briefs in this workspace write the split as
    `**File ownership — edit ONLY:** `a`, `b`. Never merge to main. Other lanes
    are live on other paths (ask-route: `app/serve.py`)` — so the same line
    carries the lane's own paths AND, sometimes, other lanes' paths named for
    context. Reading the whole line would give every lane its neighbours'
    paths and manufacture a collision in every pair.

    The declaration ends at the first sentence break outside backticks, after
    at least one path has been named. `app/data.py` keeps its dot because the
    break must be a period FOLLOWED BY A SPACE and outside a quote.
    """
    inside, seen_path = False, False
    for i, char in enumerate(line):
        if char == "`":
            inside = not inside
            seen_path = seen_path or not inside
        elif char == "." and not inside and seen_path:
            if i + 1 >= len(line) or line[i + 1] in " \t\n":
                return line[:i]
    return line


def brief_ownership(text: str | None) -> list[str]:
    """The paths a lane brief says its lane owns, normalised for comparison.

    `evaluations/turnkey/**` and `evaluations/turnkey` are the same claim; so
    are `app/data.py` and `` `app/data.py` ``. A backticked token that is prose
    rather than a path is dropped rather than compared, because comparing prose
    produces collisions that are not real ones.
    """
    if not text:
        return []
    line = BRIEF_OWNERSHIP.search(text)
    if not line:
        return []
    out = []
    for token in BACKTICKED.findall(_declaration(line.group(0))):
        path = token.strip()
        if not path or not re.fullmatch(r"[A-Za-z0-9._*/\-]+", path):
            continue
        path = path.rstrip("*").rstrip("/").lstrip("./")
        if path and path not in out:
            out.append(path)
    return out


def _paths_collide(a: str, b: str) -> bool:
    """Do two declared paths overlap? `app` collides with `app/data.py`."""
    pa, pb = a.strip("/").split("/"), b.strip("/").split("/")
    n = min(len(pa), len(pb))
    return pa[:n] == pb[:n]


def _log(env: Env, repo: str, argv: list[str]) -> list[dict]:
    """`git log` with parents, date and subject, parsed into rows."""
    ran = env.run(["git", "-C", repo, "log", "--pretty=format:%H\t%P\t%ci\t%s"] + argv,
                  timeout=90.0)
    if not ran.ok:
        return []
    out = []
    for line in ran.out.splitlines():
        parts = line.split("\t")
        if len(parts) < 4:
            continue
        parents = parts[1].split()
        out.append({"sha": parts[0].strip(), "parents": parents,
                    "merge": len(parents) > 1, "at": parts[2].strip(),
                    "subject": "\t".join(parts[3:]).strip()})
    return out


def lane_authored_commits(env: Env, repo: str, branch: str, limit: int = 120
                          ) -> tuple[dict[str, dict], list[dict], bool]:
    """Every commit a lane merge carried in, and the merges that carried them.

    This is the attribution step (k) rests on, and it is structural rather than
    nominal: every session in this system commits as the same person, so an
    author field settles nothing. What settles it is which side of a merge a
    commit arrived on. A lane commits on its own branch, so its work reaches
    the integration branch ONLY as the second parent of a `merge lane/...`
    commit -- `M^1..M^2` is exactly the set that merge brought in, and a commit
    outside every such set was made by whoever was integrating.

    The cheaper test -- "is it on the integration branch's first-parent line?"
    -- is wrong here, and was measured wrong: on this repository lanes merge
    onto an integration branch which then reaches main through a pull-request
    merge, so main's first-parent line is almost entirely PR merges and an
    integrator's own commit sits off it. Asking which side of the lane merge a
    commit came from does not care how many branches deep the integration went.

    Returns each lane-authored commit mapped to the merge that carried it, the
    lane merges scanned, and whether the scan reached the end of the history.
    When it did not, a commit that is merely ABSENT from the map is reported
    unknown rather than credited to the integrator.
    """
    merges = [m for m in _log(env, repo, [f"--max-count={limit}", "--merges", branch])
              if "lane/" in m["subject"] and len(m["parents"]) >= 2]
    complete = len(merges) < limit
    carried: dict[str, dict] = {}
    for merge in merges:
        ran = env.run(["git", "-C", repo, "rev-list", "--no-merges",
                       f"{merge['parents'][0]}..{merge['parents'][1]}"], timeout=60.0)
        if not ran.ok:
            continue
        brought = [s.strip() for s in ran.out.split() if s.strip()]
        merge["brought"] = len(brought)
        for sha in brought:
            carried.setdefault(sha, merge)
    return carried, merges, complete


def commits_touching(env: Env, repo: str, branch: str, path: str, limit: int = 25
                     ) -> list[dict]:
    """The newest commits on `branch` that changed `path`, newest first."""
    return _log(env, repo, [f"--max-count={limit}", branch, "--", path])


def commit_that_introduced(env: Env, repo: str, branch: str, path: str,
                           needle: str, limit: int = 40) -> dict | None:
    """The commit that ADDED a line to a file, found with git's own pickaxe.

    "The newest commit touching the file" is the wrong question for an append-
    only record: a later commit fixing a typo three entries up would be credited
    with writing the newest entry. `-S` reports the commits where the count of a
    string changed, newest first, so the OLDEST of them is the one that put the
    line there.

    Note this walks the whole history and not the first-parent line, which is
    exactly what the attribution needs: a commit that arrived on a lane branch
    must be findable in order to be recognised as a lane's.
    """
    rows = _log(env, repo, [f"--max-count={limit}", f"-S{needle}", branch, "--", path])
    return rows[-1] if rows else None


def parse_check_entries(text: str | None) -> list[dict]:
    """The stamped entries of the manager session's check record, oldest first.

    Each entry runs from its heading to the next heading of any depth, the same
    way the return log's entries do. What is read off it: the stamp, the
    headline, and the command it says was run — because an entry naming no
    command is a claim that a check happened rather than a record of one.
    """
    if not text:
        return []
    heads = list(CHECK_ENTRY.finditer(text))
    entries = []
    for i, head in enumerate(heads):
        end = heads[i + 1].start() if i + 1 < len(heads) else len(text)
        body = text[head.end():end]
        command = None
        fence = CHECK_FENCE.search(body)
        if fence:
            command = first_line(fence.group(1))
        if not command:
            spanned = CHECK_COMMAND.search(body)
            command = spanned.group(1).strip() if spanned else None
        if not command:
            indented = CHECK_INDENTED.search(body)
            command = indented.group(1).strip() if indented else None
        entries.append({
            "stamp": f"{head.group(1)} {head.group(2)}",
            "headline": head.group(3).strip(),
            "heading": head.group(0).strip(),
            "command": command,
        })
    return entries


def read_manager_check_record(env: Env, repo: str, branch: str,
                              attribute) -> dict:
    """The manager session's own check record, and who wrote its newest entry.

    `attribute` is the same classifier step (k) uses on every other commit, so
    the answer here rests on exactly one fact: which side of a lane merge the
    commit that added the entry arrived on.
    """
    path = f"{repo}/{MANAGER_CHECK_RECORD}"
    if not env.exists(path):
        return {"path": MANAGER_CHECK_RECORD, "exists": False, "entries": 0,
                "newest": None}
    entries = parse_check_entries(env.read(path))
    if not entries:
        return {"path": MANAGER_CHECK_RECORD, "exists": True, "entries": 0,
                "newest": None}
    newest = entries[-1]
    commit = commit_that_introduced(env, repo, branch, MANAGER_CHECK_RECORD,
                                    newest["heading"])
    placed = attribute(commit, MANAGER_CHECK_RECORD) if commit else None
    return {
        "path": MANAGER_CHECK_RECORD, "exists": True, "entries": len(entries),
        "newest": {**newest, "commit": placed},
    }

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


def _observed_as_lane(lane: Lane, observations: list[dict]) -> dict | None:
    """Was this lane seen with BOTH halves, in one reading, while it ran?

    A finished wave tidies up after itself: the manager merges the branches and
    removes the worktrees, and the terminal sessions exit with the lanes. After
    that, git and the multiplexer are telling the truth when they say there is
    nothing there — but "nothing there NOW" is not "never was", and treating
    the two the same condemns every successfully completed wave as having run
    no lanes at all. (Measured: the first wave this harness drove did exactly
    that, and the harness called two real, merged lanes 'no lanes found'.)

    So a reading taken WHILE the wave ran is admitted as evidence — but only a
    reading that carries both halves at once for this lane, which is the same
    bar `assert_lane_is_real` applies in the present tense.
    """
    for sample in observations or []:
        if lane.tmux and lane.tmux not in sample.get("sessions", []):
            continue
        branches = [w.get("branch") for w in sample.get("worktrees", [])]
        if lane.branch and lane.branch in branches:
            return {"at": sample.get("at"), "session": lane.tmux, "branch": lane.branch}
    return None


def assert_lane_is_real(lane: Lane, worktrees: list[dict], panes: list[dict],
                        observations: list[dict] | None = None) -> dict:
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
    seen_running = _observed_as_lane(lane, observations or [])
    if registered is None and seen_running:
        # Cleaned up after a finished wave, but caught in the act earlier.
        return {
            "lane": lane.name, "state": ENDED, "ok": True,
            "worktree": lane.worktree, "branch": lane.branch,
            "worktree_registered": False, "terminal_sessions": [],
            "recorded_terminal": lane.tmux,
            "observed_running": seen_running,
            "findings": [
                f"no worktree registered at {lane.worktree} now, but at "
                f"{seen_running['at']} this lane's worktree ({lane.branch}) and its "
                f"terminal session ({lane.tmux}) were both live in one reading taken "
                "from outside the manager session; it ran and was cleaned up after"
            ],
        }
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
        "observed_running": seen_running,
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


def _holder_seen_running(pid: int, observations: list[dict]) -> dict | None:
    """Where this pid was sitting, read from /proc while the wave still ran."""
    for sample in reversed(observations or []):
        for holder in sample.get("holders", []):
            if holder.get("pid") == pid and holder.get("cwd"):
                return {"pid": pid, "cwd": holder["cwd"],
                        "cmdline": holder.get("cmdline", ""),
                        "observed_at": sample.get("at")}
    return None


def assert_no_subagent_held_work(
    items: list[dict],
    processes: dict[int, dict | None],
    lane_worktrees: list[str],
    lane_branches: list[str] | None = None,
    observations: list[dict] | None = None,
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

    `observations` are readings of the SAME question taken while the wave was
    still running: pid -> the directory it was sitting in, read from /proc at
    the time. A holder that has since exited but WAS read sitting inside a lane
    worktree is a pass, because that reading is the identical fact this
    assertion asks for, taken when it could still be taken. Without it, every
    holder on a completed wave is unresolved — measured: 2 of 2 on run D — and
    the strongest evidence against in-session execution only exists mid-flight.
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

        process = processes.get(pid) or _holder_seen_running(pid, observations or [])
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
        if process.get("observed_at"):
            record["read_at"] = process["observed_at"]
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
            if process.get("observed_at"):
                record["why"] = (
                    f"pid {pid} was read sitting in {cwd!r} at "
                    f"{process['observed_at']}, while the wave was running; it has "
                    "since exited, but that reading is this assertion's own question "
                    "answered at the only time it could be asked"
                )
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


def assert_lanes_observed_live(samples: list[dict], width: int = 2) -> dict:
    """Were `width` lanes ever seen running AT THE SAME TIME, from outside?

    Every other lane assertion here reads the wreckage a lane leaves behind:
    a worktree, a branch, commits, a resolution. All of that is still there
    after the lane exits, and all of it can be produced by a session that never
    left itself. This one reads the two systems that can only answer in the
    present tense — git's worktree list and the multiplexer's session list —
    while the manager session is still running, and from OUTSIDE that session.

    It is deliberately conjunctive within a single sample. Two worktrees seen
    at 12:01 and two terminal sessions seen at 12:09 are not two lanes; they
    are two facts. Only one sample carrying both is evidence of concurrency.

    Pure, over already-collected samples, so the concurrency claim can be made
    to fail without a container.
    """
    if not samples:
        return {"verdict": SKIP, "width": width, "samples": 0,
                "why": "no sample was taken while a manager session was running, so "
                       "concurrency was never observed either way"}
    scored = []
    for sample in samples:
        sessions = [s for s in sample.get("sessions", []) if str(s).startswith("hw__")]
        worktrees = [w for w in sample.get("worktrees", [])
                     if str(w.get("branch", "")).startswith("lane/")]
        scored.append({
            "at": sample.get("at"),
            "lane_sessions": sessions,
            "lane_worktrees": [w.get("branch") for w in worktrees],
            "both": min(len(sessions), len(worktrees)),
        })
    best = max(scored, key=lambda s: s["both"])
    if best["both"] >= width:
        return {
            "verdict": PASS, "width": width, "samples": len(samples), "peak": best,
            "why": f"at {best['at']}, {len(best['lane_sessions'])} lane terminal "
                   f"session(s) and {len(best['lane_worktrees'])} lane worktree(s) "
                   "were visible at once, read from outside the manager session",
        }

    # A half that NEVER reached the width in any reading settles it: there were
    # not `width` lanes, and no amount of sampling luck would have shown them.
    # That is a finding, not a miss.
    most_sessions = max(len(s["lane_sessions"]) for s in scored)
    most_worktrees = max(len(s["lane_worktrees"]) for s in scored)
    if most_sessions < width or most_worktrees < width:
        return {
            "verdict": FAIL, "width": width, "samples": len(samples), "peak": best,
            "why": f"across {len(samples)} samples the most ever seen at once was "
                   f"{most_sessions} lane terminal session(s) and {most_worktrees} "
                   f"lane worktree(s); {width} lanes were asked for, and a half that "
                   "never once reached that count was never there to be missed",
        }
    # Both halves reached the width, but never in the SAME reading. Sampling
    # is periodic and lanes can be short; this cannot distinguish "they did not
    # overlap" from "the sampler blinked". Reported as unproven, which is what
    # this harness says instead of guessing — and never counted as a pass.
    return {
        "verdict": SKIP, "width": width, "samples": len(samples), "peak": best,
        "why": f"{width} lane worktrees and {width} lane terminal sessions were each "
               f"seen across {len(samples)} samples, but never both in one reading "
               f"(the best single reading had {best['both']}); with periodic sampling "
               "that cannot be told apart from a sampler that blinked, so this run "
               "does not claim the lanes overlapped",
    }


# ---------------------------------------------------------------------------
# THE ASSERTIONS — the clauses about what a MANAGER SESSION DID
#
# Same discipline as the clause-5 block above, and for the same reason: pure
# functions over evidence already collected, so every one can be made to fail
# from synthetic input, with no container, no wave and no workspace.
#
# A verdict is one of three things and never a fourth. PASS: the promise was
# kept, and here is the reading. FAIL: it was broken, and here is the reading.
# SKIP: this run could not read it, and here is exactly what it waits on.
#
# A clause that was never EXERCISED — no lane stalled, no feedback arrived, no
# session closed — is a SKIP that says so. Not a PASS: nothing was kept, and a
# green line nobody can back up is the failure this harness exists to prevent.
# ---------------------------------------------------------------------------


def _clause(number: int, verdict: str, why: str, **extra) -> dict:
    """One clause's reading, carrying the ledger row it re-derives."""
    row, title = OPERATION_CLAUSES[number]
    reading = {"clause": f"Core {number}", "row": row, "title": title,
               "verdict": verdict, "why": why}
    reading.update(extra)
    return reading


def assert_plan_is_visible(briefs: list[dict], entries: list[dict],
                           where: str | None, looked_in: str = "") -> dict:
    """Clause 2 — order, dependencies, collisions and picks, shown with reasons.

    "Visible" means visible to somebody who was not in the session, so this
    reads the two artifacts a wave leaves that a stranger could open: the lane
    briefs the manager session wrote (each one declaring the paths its lane
    owns — the collision decision, per lane) and the plan record it keeps
    (dated entries giving the reason for a refill, a width, a park).

    Both halves must hold. A brief with no ownership split is the plan not
    being written down where the lane can see it; a plan record that only
    announces what happened ("merged X, 4 live") is the announcement clause 2
    is explicitly not satisfied by.
    """
    undeclared = [b["lane"] for b in briefs if not b.get("declared")]
    reasoned = [e for e in entries if e.get("decision") and e.get("reason")]
    facts = {"briefs": len(briefs), "briefs_declaring_ownership": len(briefs) - len(undeclared),
             "plan_record": where, "plan_entries": len(entries),
             "entries_with_a_reason": len(reasoned)}
    if not briefs and not entries:
        return _clause(2, SKIP, "no lane brief and no plan record could be read, so "
                                "there is nothing to judge", awaits=looked_in, **facts)
    if undeclared:
        return _clause(
            2, FAIL,
            f"{len(undeclared)} of {len(briefs)} lane brief(s) declare no file "
            f"ownership at all ({', '.join(undeclared)}) — the collision decision "
            "for those lanes is not written anywhere their worker session can read it",
            **facts)
    if where is None:
        return _clause(
            2, SKIP,
            "every lane brief declares the paths it owns, but no plan record was "
            "found, so order and opportunistic picks could not be read",
            awaits=looked_in, **facts)
    if not reasoned:
        return _clause(
            2, FAIL,
            f"the plan record at {where} carries {len(entries)} dated entries and "
            "not one gives a reason for a width, a refill or a park — clause 2 asks "
            "for reasons, and an announcement of what happened is not one",
            **facts)
    return _clause(
        2, PASS,
        f"{len(briefs)} lane brief(s) each declare the paths that lane owns, and the "
        f"plan record at {where} gives reasons for {len(reasoned)} of its "
        f"{len(entries)} dated decisions",
        sample_reason=reasoned[-1]["text"][:200], **facts)


def assert_lanes_touch_different_files(lanes: list[dict]) -> dict:
    """Clause 6 — lanes fill only with items that provably touch different files.

    Two readings, because the clause has two halves and they can disagree:

    - **declared** — what each lane's own brief says it owns. This is the
      manager session's collision DECISION, in the artifact it wrote before the
      work started.
    - **actual** — what each lane's commits changed, from git. This is whether
      the decision held.

    A collision on either side fails. Where fewer than two lanes have commits
    yet, the actual half is reported as unmeasured rather than passed: two
    empty branches touch no file in common and prove nothing by it.
    """
    if len(lanes) < 2:
        return _clause(6, SKIP,
                       f"{len(lanes)} lane(s) were running at once, so no width "
                       "decision was made for this reading to judge",
                       lanes=[ln["lane"] for ln in lanes],
                       awaits="two or more lanes running at the same time")
    declared_hits, actual_hits, unmeasured = [], [], []
    with_files = [ln for ln in lanes if ln.get("touched")]
    for i, a in enumerate(lanes):
        for b in lanes[i + 1:]:
            for pa in a.get("declared", []):
                for pb in b.get("declared", []):
                    if _paths_collide(pa, pb):
                        declared_hits.append({"lanes": [a["lane"], b["lane"]],
                                              "paths": [pa, pb]})
            shared = sorted(set(a.get("touched") or []) & set(b.get("touched") or []))
            if shared:
                actual_hits.append({"lanes": [a["lane"], b["lane"]], "files": shared})
    for lane in lanes:
        if not lane.get("declared"):
            unmeasured.append(f"{lane['lane']} declares no paths")
        if lane.get("touched") is None:
            unmeasured.append(f"{lane['lane']}: git could not name its changed files")
    facts = {"lanes": [ln["lane"] for ln in lanes],
             "declared_collisions": declared_hits, "actual_collisions": actual_hits,
             "lanes_with_commits": len(with_files), "unmeasured": unmeasured}
    if declared_hits:
        first = declared_hits[0]
        return _clause(6, FAIL,
                       f"{len(declared_hits)} pair(s) of lanes running at once were "
                       f"given overlapping paths: {first['lanes'][0]} and "
                       f"{first['lanes'][1]} both own {first['paths'][0]!r}",
                       **facts)
    if actual_hits:
        first = actual_hits[0]
        return _clause(6, FAIL,
                       f"{first['lanes'][0]} and {first['lanes'][1]} ran at once and "
                       f"both changed {', '.join(first['files'][:3])} — the ownership "
                       "split held on paper and not in git",
                       **facts)
    measured = "and their commits touch no file in common" if len(with_files) >= 2 else (
        f"and the actual half is unmeasured: only {len(with_files)} of them has "
        "commits yet, and two empty branches share no file by not having one")
    return _clause(6, PASS,
                   f"{len(lanes)} lanes ran at once, each brief declares paths that "
                   f"collide with no other lane's, {measured}",
                   **facts)


def assert_stalls_are_declared(stalls: list[dict], records: list[dict]) -> dict:
    """Clause 9 — no progress becomes stuck WITH CAUSE, not another iteration.

    A stall this can see: a lane whose terminal session is gone and whose
    branch carries no commit beyond its base. That is the shape clause 7 calls
    stuck, arrived at by a lane that has already stopped — a lane still running
    on an unchanged branch has not stalled, it is working, and counting it here
    would fabricate a red.

    For each, the question is whether anybody wrote down that it stopped and
    why. The record has to name the lane; a record naming no lane cannot be
    said to be about it.
    """
    if not stalls:
        return _clause(9, SKIP,
                       "no lane ended without commits, so no stall exists for this "
                       "reading to judge — the reading ran and found nothing",
                       stalls=0, records=len(records),
                       awaits="a lane that ends with an unchanged branch")
    undeclared, declared = [], []
    for stall in stalls:
        hit = next((r for r in records if stall["lane"] in (r.get("text") or "")), None)
        (declared if hit else undeclared).append(
            {"lane": stall["lane"], "record": (hit or {}).get("text", "")[:160] or None})
    facts = {"stalled": [s["lane"] for s in stalls], "declared": declared,
             "undeclared": [u["lane"] for u in undeclared]}
    if undeclared:
        return _clause(9, FAIL,
                       f"{len(undeclared)} lane(s) stopped with an unchanged branch "
                       f"and no record names them or says why: "
                       f"{', '.join(u['lane'] for u in undeclared)}",
                       **facts)
    return _clause(9, PASS,
                   f"{len(declared)} lane(s) stopped with an unchanged branch and each "
                   "is named in a record that says what stopped it",
                   **facts)


def assert_parks_kept_the_wave_moving(parks: list[dict]) -> dict:
    """Clause 3 — what needs their word is parked; everything else continues.

    The clause is a MAXIMISATION, and a maximisation is a comparison. What can
    be compared here is narrow and worth saying plainly: at the moment work was
    parked on the steward's word, did anything else keep moving? A park recorded
    on its own is indistinguishable from a wave that stopped, which is why the
    stamp asks for both halves on one line.

    A park with nothing continuing is only a FAIL when the entry gives no reason
    for it. "Everything else is blocked on this same word" and "no ready item
    that does not collide" are the honest cases, and a rule that could not tell
    them from giving up would fabricate a red on a manager session doing exactly
    the right thing.

    What a PASS does NOT prove: that nothing MORE could have proceeded. Nothing
    on disk records the work that was available and not launched, so this says
    the wave did not go idle on the steward's word, and no more than that.
    """
    if not parks:
        return _clause(3, SKIP,
                       "no park is recorded in the plan record, so nothing was "
                       "waiting on the steward for this reading to judge — the "
                       "reading ran and found nothing",
                       awaits=AWAITED[3], parks=0)
    judged = [p for p in parks if p["continued"] is not None]
    idle = [p for p in judged if p["continued"] == 0 and not p["reason"]]
    excused = [p for p in judged if p["continued"] == 0 and p["reason"]]
    moving = [p for p in judged if (p["continued"] or 0) > 0]
    facts = {"parks": len(parks), "judged": len(judged), "moving": len(moving),
             "idle": len(idle), "idle_with_a_reason": len(excused),
             "events": parks[:8],
             "stamped": len([p for p in parks if p["stamped"]])}
    if idle:
        first = idle[0]
        return _clause(3, FAIL,
                       f"{len(idle)} of {len(parks)} park(s) record nothing "
                       f"continuing beside them and give no reason for it: at "
                       f"{first['at']}, {first['parked'][:90]!r} — a wave that "
                       "waits on a person while nothing else moves is the one "
                       "thing this clause forbids",
                       **facts)
    if not moving:
        return _clause(3, SKIP,
                       f"{len(parks)} park(s) are recorded and none names what "
                       "continued beside it, so the comparison the clause promises "
                       "cannot be made",
                       awaits=AWAITED[3], **facts)
    fewest = min(p["continued"] for p in moving)
    source = moving[0]["continued_source"]
    return _clause(3, PASS,
                   f"{len(moving)} of {len(parks)} recorded park(s) name what kept "
                   f"moving beside them (read from {source}; fewest at any one "
                   f"park: {fewest})"
                   + (f", and {len(excused)} park(s) with nothing continuing say "
                      "why" if excused else "")
                   + " — the wave did not go idle on the steward's word, which is "
                     "what this reading can say and not that nothing more could "
                     "have proceeded",
                   **facts)


def assert_calls_are_one_of_the_four(parks: list[dict]) -> dict:
    """Clause 11 — exactly four kinds of call reach the steward.

    A call a manager session makes is recorded in one place: the plan record's
    own entry, at the moment it made it. This reads those, and classifies each
    into ratify · irreversible · human check · priority.

    Three outcomes, and the difference between the last two is the whole point:

    - FAIL — a call was stamped with a word that is none of the four. That is
      the defect the clause names, standing in plain sight.
    - PASS — every recorded call names one of the four.
    - SKIP — some recorded call names none, so the set cannot be said to be the
      four. An entry that failed to say which kind of call it was is unread, not
      a violation.

    What a PASS does NOT prove: that no OTHER call reached the steward. A call
    nobody stamped leaves no trace, and this reads what a wave left behind.
    """
    if not parks:
        return _clause(11, SKIP,
                       "no call to the steward is recorded in the plan record, so "
                       "there is nothing to count or classify — the reading ran "
                       "and found nothing",
                       awaits=AWAITED[11], calls=0)
    outside = [p for p in parks if p["call_named"] and not p["call"]]
    named = [p for p in parks if p["call"]]
    unnamed = [p for p in parks if not p["call_named"]]
    tally = {}
    for park in named:
        tally[park["call"]] = tally.get(park["call"], 0) + 1
    facts = {"calls": len(parks), "classified": len(named),
             "unclassified": len(unnamed), "outside_the_four": len(outside),
             "tally": tally, "events": parks[:8]}
    if outside:
        first = outside[0]
        return _clause(11, FAIL,
                       f"{len(outside)} call(s) reached the steward stamped as "
                       f"something that is none of the four: {first['call_named']!r} "
                       f"at {first['at']} — clause 11 says anything else is a "
                       "defect to file",
                       **facts)
    if not named:
        return _clause(11, SKIP,
                       f"{len(parks)} call(s) are recorded and none says which of "
                       "the four it is, so they cannot be classified",
                       awaits=AWAITED[11], **facts)
    if unnamed:
        return _clause(11, SKIP,
                       f"{len(named)} of {len(parks)} recorded call(s) name which "
                       f"of the four they are ({', '.join(f'{k}: {v}' for k, v in tally.items())}); "
                       f"the other {len(unnamed)} name none, so this run cannot say "
                       "the calls that reached the steward were the four",
                       awaits=AWAITED[11], **facts)
    return _clause(11, PASS,
                   f"every one of {len(parks)} call(s) recorded in the plan record "
                   f"is one of the four ({', '.join(f'{k}: {v}' for k, v in tally.items())}) "
                   "— a call stamped as anything else would be the defect this "
                   "clause names, and none is; a call nobody stamped leaves no "
                   "trace here either way",
                   **facts)


def assert_feedback_was_enriched(pairings: list[dict]) -> dict:
    """Clause 4 — no raw report becomes work without a quoted source.

    Reads the raw report and the item filed from it side by side: the plan
    record's own triage entry names the item, and the item's record either
    carries the report's words and the version they were said about, or it does
    not. An entry that names no item id is UNRESOLVED, never a pass — the same
    refusal `assert_no_subagent_held_work` makes for an exited holder.
    """
    if not pairings:
        return _clause(4, SKIP,
                       "no feedback triage is recorded in the plan record, so no "
                       "report and filing exist to put side by side",
                       awaits="a plan entry recording feedback, naming the item "
                              "filed from it")
    thin, unresolved, good = [], [], []
    for pair in pairings:
        item = pair.get("item")
        if item is None:
            unresolved.append(pair)
            continue
        text = f"{item.get('title', '')}\n{item.get('description', '') or ''}"
        quoted = bool(re.search(r"quoted:|[\"“”].{20,}", text, re.S))
        version = bool(re.search(r"\b[0-9a-f]{7,40}\b|build |20\d{2}-\d{2}-\d{2}|v\d+\.\d+",
                                 text))
        record = {"item": item.get("id"), "quoted": quoted, "named_version": version}
        (good if (quoted and version) else thin).append(record)
    facts = {"pairings": len(pairings), "enriched": good, "thin": thin,
             "unresolved": [p.get("entry", "")[:120] for p in unresolved]}
    if thin:
        first = thin[0]
        missing = "quotes the report" if not first["quoted"] else "names the version seen"
        return _clause(4, FAIL,
                       f"{len(thin)} item(s) filed from feedback carry no enrichment: "
                       f"{first['item']} never {missing}",
                       **facts)
    if not good:
        return _clause(4, SKIP,
                       f"{len(unresolved)} feedback triage(s) are recorded and none "
                       "names the item it produced, so no filing could be read back",
                       awaits="a triage record that names the item id it filed",
                       **facts)
    return _clause(4, PASS,
                   f"{len(good)} item(s) filed from feedback quote the report and name "
                   f"the version it was said about ({', '.join(g['item'] for g in good)})"
                   + (f"; {len(unresolved)} triage(s) name no item and are unresolved, "
                      "not passed" if unresolved else ""),
                   **facts)


def assert_handoff_on_close(closes: list[dict]) -> dict:
    """Clause 13 — a session that ends by choice leaves a resumable hand-off.

    A close that lists only what finished is a report. A close a fresh session
    can resume from also says what REMAINS — residuals, what is parked, what is
    still live. That is the difference this reads, and it is the difference
    between a hand-off and a farewell.
    """
    if not closes:
        return _clause(13, SKIP,
                       "no session close is recorded, so no hand-off is owed",
                       awaits="a plan entry recording a manager session ending by "
                              "choice")
    bare = [c for c in closes if not PLAN_REMAINS.search(c.get("text", ""))]
    facts = {"closes": len(closes), "resumable": len(closes) - len(bare),
             "newest": closes[-1].get("text", "")[:200]}
    if bare:
        return _clause(13, FAIL,
                       f"{len(bare)} of {len(closes)} recorded close(s) say only what "
                       "finished and never what remains, so a fresh session has "
                       "nothing to resume from",
                       bare=[c.get("text", "")[:160] for c in bare], **facts)
    return _clause(13, PASS,
                   f"each of {len(closes)} recorded close(s) names what remained — "
                   "residuals, what was parked, or what was still live — so a fresh "
                   "session could pick the run up from the record alone",
                   **facts)


def assert_resolutions_written_for_the_asker(items: list[dict]) -> dict:
    """Clause 12 — "resolution written for whoever asked".

    The queue stores a string and judges nothing about it, so a resolved item
    can carry "done", a bare sha, or nothing at all and look closed from every
    angle. Three things are read, and each names what makes it false:

    - it exists (a resolved item with an empty resolution is the commonest);
    - it is written in sentences — at least one of six words or more, so
      "fixed" and "see abc1234" do not qualify;
    - it says something beyond a pointer: eight words that are not a sha, an
      issue number or a path.

    What this does NOT judge is whether the sentences are TRUE. Nothing here
    can, and pretending otherwise would be the fabricated green again.
    """
    resolved = [i for i in items if str(i.get("status", "")).lower() == "resolved"]
    if not resolved:
        return _clause(12, SKIP,
                       "no resolved item is in the queue, so no resolution exists to "
                       "read",
                       awaits="an item this wave resolved")
    offenders = []
    for item in resolved:
        text = (item.get("resolution") or "").strip()
        words = WORD.findall(text)
        plain = [w for w in text.split() if not POINTER_ONLY.match(w.strip(".,;:()"))]
        sentences = [s for s in re.split(r"(?<=[.!?])[ \t\n]+", text)
                     if len(WORD.findall(s)) >= 6]
        if not text:
            why = "is empty — the item is closed and says nothing to whoever asked"
        elif not sentences:
            why = f"has no sentence in it ({text[:60]!r})"
        elif len(words) < 12 or len(plain) < 8:
            why = f"is a pointer, not an answer ({text[:60]!r})"
        else:
            continue
        offenders.append({"item": item.get("id"), "why": why})
    facts = {"resolved": len(resolved), "offenders": offenders}
    if offenders:
        first = offenders[0]
        return _clause(12, FAIL,
                       f"{len(offenders)} of {len(resolved)} resolution(s) were not "
                       f"written for whoever asked: {first['item']} {first['why']}",
                       **facts)
    return _clause(12, PASS,
                   f"all {len(resolved)} resolution(s) in the queue are written in "
                   "sentences that answer the asker rather than pointing at a commit",
                   **facts)


def assert_check_record_attributed(newest: list[dict], history: list[dict]) -> dict:
    """Clauses 7 and 8 — WHO re-ran the check, read from git's own shape.

    The nine steps read artifacts, and an artifact does not record which
    process made it. This reads that, for the only artifacts a check run leaves
    behind in the repository: the ledger's `RAN` notes and this harness's own
    recorded result.

    `lane_authored_commits` supplies the discriminator — which side of a lane
    merge a commit arrived on. A record written outside every lane merge was
    written by whoever was integrating; a record that came in as a lane merge's
    second parent is the lane's own green, which is precisely what clause 8
    says the verification may not be.

    Three outcomes, and the middle one matters most:

    - PASS — the newest record of a check run was written outside every lane.
    - SKIP — the newest records all came in through a lane merge, but the
      integrator HAS written such records before. That does not show the
      promise broken: an integrator who re-ran the check after the last merge
      and wrote nothing down leaves exactly this trace. What it needs is named.
    - FAIL — no check record in this repository was EVER written outside a
      lane. Then the only verification on record is the worker session's own.

    What a PASS does not prove: that the check was re-run for THIS wave, or
    that the run behind the record was clean. Step (h) re-runs the check itself
    and answers that; this answers who.
    """
    if not newest:
        return {"verdict": SKIP,
                "why": "no check-run record was found in the repository",
                "awaits": "a file recording a check having been run ("
                          + ", ".join(CHECK_RECORDS) + ")",
                "records": [], "by_integrator": 0, "by_lane": 0}
    integrator = [r for r in newest if r.get("author") == "integrator"]
    by_lane = [r for r in newest if r.get("author") == "lane"]
    unknown = [r for r in newest if r.get("author") not in ("integrator", "lane")]
    ever = [h for h in history if h.get("author") == "integrator"]
    facts = {"records": newest, "by_integrator": len(integrator),
             "by_lane": len(by_lane), "unknown": len(unknown),
             "integrator_records_in_history": len(ever),
             "history_examined": len(history)}
    if integrator:
        best = integrator[0]
        merge = best.get("lane_merge_before")
        return {
            "verdict": PASS,
            "why": (f"the newest record of a check run, {best['path']} at "
                    f"{best['sha'][:8]} ({best['subject']!r}), was written outside "
                    "every lane merge — a lane's work reaches this branch only as a "
                    "merge's second parent, and this commit is on neither, so it was "
                    "the integrator's own hand and not the lane whose work was checked"
                    + (f"; the lane merge before it is {merge['sha'][:8]} "
                       f"({merge['subject']!r})" if merge else
                       "; no lane merge precedes it, so its position relative to an "
                       "integration is unread")),
            **facts,
        }
    if unknown and not by_lane:
        return {
            "verdict": SKIP,
            "why": (f"{len(unknown)} check record(s) could not be placed on either "
                    "side of a lane merge, so who wrote them is unread"),
            "awaits": "a git history this run can read to the end",
            **facts,
        }
    if ever:
        newest_ever = ever[0]
        return {
            "verdict": SKIP,
            "why": (f"the newest record of a check run ({by_lane[0]['path']} at "
                    f"{by_lane[0]['sha'][:8]}) came in through a lane merge, so this "
                    f"wave's verification is unattributed here; the integrator has "
                    f"written {len(ever)} such record(s) before, most recently "
                    f"{newest_ever['sha'][:8]} ({newest_ever['subject']!r})"),
            "awaits": ("a check-run record written outside every lane after the "
                       "newest lane merge — or a reading taken while the check runs, "
                       "of the process running it, which only a driven wave can take"),
            **facts,
        }
    return {
        "verdict": FAIL,
        "why": (f"no check-run record in this repository was ever written outside a "
                f"lane ({len(history)} change(s) to {', '.join(CHECK_RECORDS)} "
                "examined, every one carried in by a lane merge) — the only "
                "verification on record is the worker session's own, which is the "
                "half of clause 8 that says never the worker session's"),
        **facts,
    }


def assert_manager_check_record(record: dict) -> dict:
    """Clauses 7 and 8 — the record the MANAGER SESSION writes about its own re-run.

    `assert_check_record_attributed` below reads the two files a check run used
    to leave a trace in, and both are edited by lanes, so its answer on this host
    is almost always "the newest record came in through a lane merge". That is
    an honest reading of a confounded artifact, not a reading of the promise.

    The convention removes the confound: `docs/workflow/CHECK-RECORD.md` is
    written only by the manager session, in its own commit, after integrating.
    Then one fact settles the clause — which side of a lane merge the commit that
    added the newest entry arrived on.

    Five outcomes:

    - PASS — the newest entry was added outside every lane merge, and it names
      the check that was run.
    - FAIL — the newest entry came in through a lane merge. The record of the
      manager session's own verification was written by a worker session, which
      is the half of clause 8 that says never the worker session's.
    - SKIP (no file) — the convention is not in this repository yet.
    - SKIP (no entry) — the convention is written down and nothing has followed
      it here.
    - SKIP (a claim, not a record) — the newest entry names no command, so
      nothing says a check was actually run.

    What a PASS does NOT prove: that the run behind the entry was clean, or that
    it covered every merge. Step (h) re-runs the check itself and answers that;
    this answers who.
    """
    path = record.get("path", MANAGER_CHECK_RECORD)
    if not record.get("exists"):
        return {"verdict": SKIP,
                "short": f"({path}) is not in this repository yet",
                "why": f"the record the manager session writes itself ({path}) is "
                       "not in this repository yet, so nothing here says who "
                       "re-ran the check",
                "awaits": f"the {path} convention, and the first entry a manager "
                          "session writes into it after integrating a wave",
                "entries": 0}
    if not record.get("entries"):
        return {"verdict": SKIP,
                "short": f"({path}) carries no entry yet",
                "why": f"the record the manager session writes itself ({path}) "
                       "exists and carries no entry yet — the convention is "
                       "written down and no wave has followed it here",
                "awaits": f"one entry in {path}, added by the manager session's "
                          "own commit after it re-ran the check",
                "entries": 0}
    newest = record["newest"]
    commit = newest.get("commit")
    facts = {"entries": record["entries"], "newest_stamp": newest.get("stamp"),
             "newest_headline": newest.get("headline"),
             "newest_command": newest.get("command"), "commit": commit}
    if commit is None:
        return {"verdict": SKIP,
                "short": f"({path}) carries an entry no commit could be found for",
                "why": f"the newest entry in {path} ({newest.get('stamp')}) could "
                       "not be traced to the commit that added it, so who wrote it "
                       "is unread",
                "awaits": "a git history this run can read to the end",
                **facts}
    author = commit.get("author")
    if author == "lane":
        merge = commit.get("lane_merge_before") or {}
        return {"verdict": FAIL,
                "short": f"({path})'s newest entry came in through a lane merge",
                "why": (f"the newest entry in {path} ({newest.get('stamp')}) was "
                        f"added by {commit['sha'][:8]}, which reached this branch "
                        f"as the second parent of {merge.get('sha', '?')[:8]} "
                        f"({merge.get('subject', 'a lane merge')!r}) — a worker "
                        "session wrote the record of the manager session's own "
                        "verification, which is the half of clause 8 that says "
                        "never the worker session's"),
                **facts}
    if author != "integrator":
        return {"verdict": SKIP,
                "short": f"({path})'s newest entry could not be placed",
                "why": (f"the commit that added the newest entry in {path} "
                        f"({commit['sha'][:8]}) could not be placed on either side "
                        "of a lane merge, so who wrote it is unread"),
                "awaits": "a git history this run can read to the end",
                **facts}
    if not newest.get("command"):
        return {"verdict": SKIP,
                "short": f"({path})'s newest entry names no check that was run",
                "why": (f"the newest entry in {path} ({newest.get('stamp')}) was "
                        "written outside every lane merge, and it names no command "
                        "— it is a claim that a check happened rather than a record "
                        "of one"),
                "awaits": f"an entry in {path} naming the command it re-ran",
                **facts}
    return {"verdict": PASS,
            "short": f"({path})'s newest entry is the manager session's own",
            "why": (f"the newest entry in {path} ({newest.get('stamp')} — "
                    f"{newest.get('headline')!r}) was added by "
                    f"{commit['sha'][:8]} ({commit.get('subject')!r}), which is on "
                    "neither side of any lane merge, so it was the manager "
                    f"session's own hand and not a lane's; it names the check it "
                    f"ran ({newest.get('command')!r}). What this does not prove is "
                    "that the run behind it was clean or that it covered every "
                    "merge — step (h) re-runs the check itself and answers that"),
            **facts}


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
    wave: dict | None = None
    batch_dir: str = WAVE_BATCH_IN_ENV
    width: int = 2
    # Rows already produced by this run, in order. Step (k) reports the halves
    # of clauses 7 and 8 that steps (f), (g) and (h) measured, and it names the
    # step that measured them rather than measuring them a second time. Empty
    # when those steps were not asked for, which is a SKIP and says so.
    results: list[dict] = field(default_factory=list)

    # The repository the WAVE happens in, and where its lane state lives.
    #
    # These are not the same as `repo`/`workspace` in driven mode, and
    # conflating them is how a run ends up looking for lane worktrees in the
    # bundle checkout while the lanes are all in the fixture. `repo` is the
    # system under test (the converge bundle); `wave_repo` is the repository
    # the manager session was told to operate ON.

    @property
    def wave_repo(self) -> str:
        return self.fixture_repo if (self.mode == DRIVEN and self.fixture_repo) else self.repo

    @property
    def wave_workspace(self) -> str:
        return self.batch_dir if (self.mode == DRIVEN and self.fixture_repo) else self.workspace


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
    fixture_now = _fixture_gap_state(ctx)
    # "Were the gaps really there?" is a question about the fixture BEFORE the
    # wave. When a wave ran, that reading was taken at seed time and is the
    # only honest basis; the current reading answers a different question and
    # is reported beside it, never in place of it.
    planted = (ctx.wave or {}).get("fixture_before") or fixture_now
    planted_when = "before the wave" if (ctx.wave or {}).get("fixture_before") else "now"
    items, error = read_tracker_items(ctx.env, ctx.project)
    if error:
        return Result(SKIP, "The queue did not answer.", reason=error)

    if ctx.mode == DRIVEN and planted:
        expected = set(ctx.answer_key.get("expected_red_rules_before", []))
        actual = set(planted.get("red_rules", []))
        if expected and expected != actual:
            return Result(
                FAIL,
                f"The fixture was not in its planted state ({planted_when}): expected "
                f"rules {sorted(expected)} red, found {sorted(actual)}.",
                evidence={"fixture_planted": planted, "fixture_now": fixture_now},
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
    evidence = {"seeding": seeding, "fixture_planted": planted,
                "fixture_planted_read": planted_when, "fixture_now": fixture_now,
                "sampled": len(sampled),
                "contracts_in_repo": contracts,
                "named_only_by_bare_stem": weakly,
                "without_contract_or_done": offenders}
    if not sampled and not items:
        return Result(
            FAIL,
            "The sample gap is planted and the project is started, but no work has "
            "been derived from it — the queue is empty.",
            evidence=evidence,
        )
    if not sampled:
        return Result(SKIP, "No item records could be read.",
                      reason=f"the queue returned {len(items)} items but none of their "
                             "full records read back")
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
    if planted:
        detail += (f"; the fixture's own kit reported rules "
                   f"{planted.get('red_rules')} red {planted_when}")
    if fixture_now and fixture_now is not planted:
        detail += f" and reports {fixture_now.get('red_rules')} red now"
    return Result(PASS, detail + ".", evidence=evidence)


def step_lanes(ctx: Context) -> Result:
    """(f) Two REAL lanes — own worktree, own terminal session — tended and judged.

    This is the step acceptance item 3 is about. See `assert_lane_is_real` and
    `assert_no_subagent_held_work` above for the assertions themselves.
    """
    worktrees = read_worktrees(ctx.env, ctx.wave_repo)
    panes = read_tmux_panes(ctx.env)
    lanes = (read_manifest(ctx.env, ctx.wave_workspace)
             or lanes_from_worktrees(worktrees, panes))
    samples = (ctx.wave or {}).get("samples", [])
    # A lane whose worktree is gone is NOT dropped here. A finished wave
    # removes its worktrees after merging, and discarding those rows turned a
    # completed two-lane wave into "no lanes found" (measured, run C). Such a
    # lane is kept and judged by assert_lane_is_real, which can place it from
    # a reading taken while it ran; only a lane with neither a worktree nor an
    # observation is dropped, and it is counted so the drop is never silent.
    kept, vanished = [], []
    for lane in lanes:
        if ctx.env.exists(lane.worktree) or _observed_as_lane(lane, samples):
            kept.append(lane)
        else:
            vanished.append(lane.name)
    lanes = kept

    # Concurrency, read while the wave was still running (the wave driver's
    # samples). Everything else in this step reads what a lane LEFT; this is
    # the only reading that could only have been true in the present tense.
    observed = assert_lanes_observed_live(samples, ctx.width)

    if not lanes:
        return Result(
            FAIL,
            "No lanes found: neither a launcher manifest nor a worktree on a "
            "lane/* branch exists. Clause 5 fails loud rather than falling back "
            "to running the work in-session.",
            evidence={"repo_read": ctx.wave_repo, "workspace_read": ctx.wave_workspace,
                      "worktrees": len(worktrees), "terminal_panes": len(panes),
                      "dropped_no_worktree_no_observation": vanished,
                      "observed_live": observed},
        )

    reality = [assert_lane_is_real(ln, worktrees, panes, samples) for ln in lanes]
    distinct = assert_lanes_are_distinct(lanes)
    real = [r for r in reality if r["ok"]]
    impostors = [r for r in reality if r["state"] == NOT_A_LANE]
    unproven_lanes = [r for r in reality if r["state"] == UNPROVEN]

    items, tracker_error = read_tracker_items(ctx.env, ctx.project)
    pids = {p for p in (holder_pid(i.get("holder")) for i in items) if p is not None}
    processes = {pid: read_process(ctx.env, pid) for pid in pids}
    subagents = assert_no_subagent_held_work(
        items, processes, [ln.worktree for ln in lanes],
        [ln.branch for ln in lanes], samples,
    )

    progress = [
        assert_commits_beyond_base(
            ln, commits_beyond(ctx.env, ln.worktree, ln.base_sha, ln.branch,
                               ctx.wave_repo)
            if ln.base_sha else None,
        )
        for ln in lanes
    ]

    evidence = {
        "repo_read": ctx.wave_repo,
        "workspace_read": ctx.wave_workspace,
        "lane_source": lanes[0].source,
        "dropped_no_worktree_no_observation": vanished,
        "lanes": [{"name": ln.name, "worktree": ln.worktree, "branch": ln.branch,
                   "terminal": ln.tmux} for ln in lanes],
        "lane_reality": reality,
        "distinct": distinct,
        "no_subagent_held_work": subagents,
        "commits_beyond_base": progress,
        "observed_live": observed,
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
    if len(real) < ctx.width:
        return Result(
            FAIL,
            f"Only {len(real)} lane(s) can be shown to have had their own worktree "
            f"and their own terminal session; the turnkey claim needs at least "
            f"{ctx.width}.",
            evidence=evidence,
        )
    if observed["verdict"] == FAIL:
        return Result(
            FAIL,
            f"The lanes left the right wreckage, but {observed['why']}.",
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
    if observed["verdict"] == PASS:
        detail += " " + observed["why"][0].upper() + observed["why"][1:] + "."
    elif observed["verdict"] == SKIP:
        detail += (
            " Concurrency itself was not observed: "
            + observed["why"] + " — the lanes are real by their artifacts, but this "
            "run cannot say they overlapped."
        )
    return Result(PASS, detail, evidence=evidence)


def step_integrated(ctx: Context) -> Result:
    """(g) Results integrated and verified."""
    merges = merge_commits(ctx.env, ctx.wave_repo, ctx.integration_branch)
    lane_merges = [m for m in merges if re.search(r"lane/", m["subject"])]
    evidence = {
        "repo_read": ctx.wave_repo,
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


def plain_sentences(text: str) -> list[str]:
    """The lines of `text` a person would read as sentences.

    A table row and a heading are not sentences. A leading list marker is
    stripped rather than disqualifying the line behind it.
    """
    out = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or _NOT_A_SENTENCE.match(line):
            continue
        line = _LEADING_MARKER.sub("", line).strip()
        if line.endswith(".") and len(line.split()) >= 6:
            out.append(line)
    return out


def parse_return_log(text: str) -> list[dict]:
    """Split a return log into its dated entries, one dict each.

    An entry begins at a DATED heading and runs to the next one. Everything
    before the first dated heading is the file's own header and belongs to no
    entry: a header that carries the five words is not a brief, and reading the
    whole file for them let exactly that pass. An undated heading inside an
    entry (`### Technical detail`) stays part of the entry it sits in, so a
    brief written with subsections is not silently truncated.

    Each entry reports whether it is STAMPED (a heading carrying a clock time,
    which is the record that a return happened) and which of the five parts are
    written under it.
    """
    entries: list[dict] = []
    current: dict | None = None
    for line in text.splitlines():
        if ENTRY_HEADING.match(line) and ENTRY_DATE.search(line):
            current = {
                "heading": line.lstrip("#").strip(),
                "stamped": bool(RETURN_STAMP.match(line)),
                "lines": [],
            }
            entries.append(current)
        elif current is not None:
            current["lines"].append(line)

    for entry in entries:
        body = "\n".join(entry.pop("lines"))
        entry["parts_present"] = [n for n, p in BRIEF_PART_PATTERNS if p.search(body)]
        entry["parts_missing"] = [n for n, p in BRIEF_PART_PATTERNS if not p.search(body)]
        entry["complete"] = not entry["parts_missing"]
        entry["plain_sentences"] = len(plain_sentences(body))
    return entries


def step_brief(ctx: Context) -> Result:
    """(i) A plain-sentence return brief produced.

    Judged on ONE entry -- the newest, which is the return this run produced --
    and never on the file as a whole. Two numbers are reported beside it: how
    many returns are stamped in the log, and how many of those carry a complete
    brief. Clause 10 is "a brief on every return", so a stamped return with a
    part missing under it is the failure the count exists to catch.
    """
    # The brief belongs to the repository the wave operated on. In driven mode
    # that is the fixture, not the bundle checkout; both are looked in, and the
    # one that answered is named, so a brief is never credited to the wrong repo.
    candidates = [f"{root}/{RETURN_LOG}" for root in
                  dict.fromkeys([ctx.wave_repo, ctx.repo])]
    where, text = next(
        ((path, body) for path in candidates
         if (body := ctx.env.read(path)) is not None),
        (candidates[0], None),
    )
    if text is None:
        return Result(
            FAIL,
            "No return brief at " + " or ".join(candidates) +
            ". Clause 10 requires one on every return, and the return-brief "
            "convention names this exact path.",
            evidence={"expected_paths": candidates},
        )

    entries = parse_return_log(text)
    returns = [e for e in entries if e["stamped"]]
    briefs = [e for e in entries if e["complete"]]
    unbriefed = [e for e in returns if not e["complete"]]
    evidence = {
        "path": where, "bytes": len(text), "dated_entries": len(entries),
        "stamped_returns": len(returns), "complete_briefs": len(briefs),
        "unbriefed_returns": [{"heading": e["heading"], "missing": e["parts_missing"]}
                              for e in unbriefed],
        "judged": entries[-1] if entries else None,
    }
    if not entries:
        return Result(
            FAIL,
            f"The log at {where} has no dated entry, so no return has been briefed "
            "in it. The file's own header is not a brief, whatever words it carries.",
            evidence=evidence,
        )

    if unbriefed:
        first = unbriefed[0]
        return Result(
            FAIL,
            f"{len(unbriefed)} of {len(returns)} stamped return(s) in {where} carry "
            f"no complete brief. '{first['heading']}' is missing "
            f"{len(first['parts_missing'])} of the five parts: "
            f"{', '.join(first['parts_missing'])}.",
            evidence=evidence,
        )

    judged = entries[-1]
    if judged["parts_missing"]:
        return Result(
            FAIL,
            f"The newest entry in {where} ('{judged['heading']}') is missing "
            f"{len(judged['parts_missing'])} of the five required parts: "
            f"{', '.join(judged['parts_missing'])}. Counted in the log: dated "
            f"entries {len(entries)}, stamped returns {len(returns)}, complete "
            f"briefs {len(briefs)}.",
            evidence=evidence,
        )
    if judged["plain_sentences"] < 3:
        return Result(
            FAIL,
            f"The newest entry in {where} ('{judged['heading']}') has "
            f"{judged['plain_sentences']} plain sentences; a brief is written in "
            "sentences, not a status table.",
            evidence=evidence,
        )
    return Result(
        PASS,
        f"The newest entry in {where} ('{judged['heading']}') carries all five "
        f"parts and {judged['plain_sentences']} plain sentences; "
        f"{len(returns)} stamped return(s) in the log and "
        f"{len(briefs)} complete brief(s).",
        evidence=evidence,
    )


def _lanes_running_at_once(ctx: Context, lanes: list[Lane], panes: list[dict]
                           ) -> tuple[list[Lane], str]:
    """The lanes that were running AT THE SAME TIME, and how that was read.

    Two sources, in order of strength. The multiplexer's live session list is
    the present tense and needs no wave to have been recorded. The readings
    taken while a driven wave ran answer for a wave that has since finished and
    tidied its sessions away — the same evidence `assert_lanes_observed_live`
    rests on, reused rather than re-invented.
    """
    live_sessions = {p["session"] for p in panes}
    live = [ln for ln in lanes if ln.tmux and ln.tmux in live_sessions]
    best, source = live, "the multiplexer's live session list"
    for sample in (ctx.wave or {}).get("samples", []):
        seen = [ln for ln in lanes if ln.tmux and ln.tmux in sample.get("sessions", [])]
        if len(seen) > len(best):
            best, source = seen, f"the reading taken at {sample.get('at')} while the wave ran"
    return best, source


def step_clauses(ctx: Context) -> Result:
    """(j) The seven Core clauses the nine steps never read.

    Every reading here is taken from something a wave LEFT — a lane brief, the
    plan record, git, the queue — and never from `modes/converge-manager.md`,
    which says only that the rule was written down. A clause with no reading yet
    names the observation it waits on instead of being quietly dropped, and the
    observation it names is one a manager session can actually take.

    Clauses 3 and 11 are read from the same artifact, because they are about the
    same moment: a call to the steward, what it parked, and what kept moving
    beside it.
    """
    repo, workspace = ctx.wave_repo, ctx.wave_workspace
    panes = read_tmux_panes(ctx.env)
    worktrees = read_worktrees(ctx.env, repo)
    lanes = read_manifest(ctx.env, workspace) or lanes_from_worktrees(worktrees, panes)
    where, plan_text = read_plan_record(ctx.env, workspace)
    entries = parse_plan_entries(plan_text or "")
    looked_in = "a plan record in " + workspace + " (" + ", ".join(PLAN_RECORDS) + ")"

    # --- the lanes that ran at once, with what they were told to own and what
    # --- they actually changed
    concurrent, concurrency_source = _lanes_running_at_once(ctx, lanes, panes)
    briefs, measured_lanes = [], []
    for lane in concurrent:
        text = ctx.env.read(lane.goal) if lane.goal else None
        declared = brief_ownership(text)
        briefs.append({"lane": lane.name, "goal": lane.goal,
                       "brief_read": text is not None, "declared": declared})
        measured_lanes.append({
            "lane": lane.name,
            "declared": declared,
            "touched": (changed_files(ctx.env, lane.worktree, lane.base_sha,
                                      lane.branch, repo)
                        if lane.base_sha else None),
        })

    # --- lanes that stopped without producing anything
    live_sessions = {p["session"] for p in panes}
    stalls = []
    for lane in lanes:
        if lane.tmux and lane.tmux in live_sessions:
            continue  # still working; an unchanged branch is not yet a stall
        if not lane.base_sha:
            continue
        count = commits_beyond(ctx.env, lane.worktree, lane.base_sha, lane.branch, repo)
        if count == 0:
            stalls.append({"lane": lane.name, "branch": lane.branch})
    return_log = ctx.env.read(f"{repo}/{RETURN_LOG}") or ""
    records = entries + [{"text": e["heading"] + " " + str(e.get("parts_present"))}
                         for e in parse_return_log(return_log)]

    # --- feedback: the raw report and the item filed from it, side by side
    pairings = []
    for entry in [e for e in entries if e["feedback"]]:
        ids = re.findall(rf"\b{re.escape(ctx.project)}-[a-z0-9]{{3,}}\b", entry["text"])
        if not ids:
            pairings.append({"entry": entry["text"], "item": None})
            continue
        for item_id in dict.fromkeys(ids):
            pairings.append({"entry": entry["text"],
                             "item": read_tracker_item(ctx.env, ctx.project, item_id)})

    parks = parse_park_events(entries)
    readings = [
        assert_plan_is_visible(briefs, entries, where, looked_in),
        assert_parks_kept_the_wave_moving(parks),
        assert_feedback_was_enriched(pairings),
        assert_lanes_touch_different_files(measured_lanes),
        assert_stalls_are_declared(stalls, records),
        assert_calls_are_one_of_the_four(parks),
        assert_handoff_on_close([e for e in entries if e["close"]]),
    ]

    evidence = {
        "repo_read": repo, "workspace_read": workspace,
        "plan_record": where, "plan_entries": len(entries),
        "lanes_running_at_once": [ln.name for ln in concurrent],
        "concurrency_source": concurrency_source,
        "briefs": briefs, "stalled_lanes": stalls,
        "feedback_pairings": len(pairings),
        "park_events": parks,
        "clause_readings": readings,
    }
    detail = " · ".join(f"{r['clause']} ({r['row']}) {r['verdict']}: {r['why']}"
                        for r in readings)
    fails = [r for r in readings if r["verdict"] == FAIL]
    live = [r for r in readings if r["verdict"] == PASS]
    waiting = [r for r in readings if r["verdict"] == SKIP]
    if fails:
        return Result(
            FAIL,
            f"{len(fails)} of {len(readings)} clause readings say the promise was "
            f"broken. {detail}",
            evidence=evidence,
        )
    if not live:
        return Result(
            SKIP,
            f"None of the {len(readings)} clauses could be read on this run. {detail}",
            reason=("no lane brief, plan record, stall, feedback triage or session "
                    "close was readable here; each clause above names the observation "
                    "it waits on"),
            evidence=evidence,
        )
    return Result(
        PASS,
        f"{len(live)} of {len(readings)} clauses carry a live reading of what a "
        f"manager session did, and {len(waiting)} name the observation they still "
        f"wait on. {detail}",
        evidence=evidence,
    )


def step_attribution(ctx: Context) -> Result:
    """(k) Who produced the artifact — clauses 7, 8 and 12.

    Steps (f), (g) and (h) measure the halves of clauses 7 and 8 that live in
    an artifact: commits beyond base, a lane merge, a contract check re-run.
    None of them can say WHO. This step reads that from git's own shape and
    from the queue's own text, and where it cannot, it says what it waits on.

    Two records are read, in order of strength. The manager session's own check
    record (`docs/workflow/CHECK-RECORD.md`) is written by nobody else, so the
    commit that added its newest entry answers the question directly. The older
    pair — the ledger and this harness's own result file — are edited by lanes,
    so their newest change usually arrives through a lane merge and can only say
    that the question is unanswered here.
    """
    repo, branch = ctx.wave_repo, ctx.integration_branch
    carried, lane_merges, complete = lane_authored_commits(ctx.env, repo, branch)

    def classify(commit: dict, path: str) -> dict:
        if commit["sha"] in carried:
            # The merge that carried it is known exactly, not guessed by date.
            author, merge = "lane", carried[commit["sha"]]
        elif complete:
            author, merge = "integrator", next(
                (m for m in lane_merges if m["at"] <= commit["at"]), None)
        else:
            author, merge = "unknown", None
        return {"path": path, "sha": commit["sha"], "at": commit["at"],
                "subject": commit["subject"], "author": author,
                "lane_merge_before": ({"sha": merge["sha"], "subject": merge["subject"]}
                                      if merge else None)}

    newest, history = [], []
    for path in CHECK_RECORDS:
        if not ctx.env.exists(f"{repo}/{path}"):
            continue
        touches = [classify(c, path) for c in commits_touching(ctx.env, repo, branch, path)]
        if touches:
            newest.append(touches[0])
            history.extend(touches)
    history.sort(key=lambda r: r["at"], reverse=True)
    # The manager session's own record is asked first, because it is the only
    # one of the three files a lane never writes. The older pair is still read
    # and still reported — a repository that has not adopted the convention gets
    # exactly the reading it got before, plus a named way to answer it.
    record = read_manager_check_record(ctx.env, repo, branch, classify)
    manager = assert_manager_check_record(record)
    others = assert_check_record_attributed(newest, history)
    if manager["verdict"] in (PASS, FAIL):
        attribution = {**manager, "other_check_records": others}
    else:
        attribution = {
            **others,
            "why": f"{others['why']}; and the record the manager session writes "
                   f"itself {manager['short']}",
            "awaits": manager["awaits"],
            "manager_check_record": manager,
        }

    items, tracker_error = read_tracker_items(ctx.env, ctx.project)
    resolutions = assert_resolutions_written_for_the_asker(items)

    measured = {row["step"]: row for row in ctx.results}

    def half(letter: str, what: str) -> tuple[str, str]:
        row = measured.get(letter)
        if row is None:
            return SKIP, f"step ({letter}) did not run in this invocation, so {what} is unread"
        return row["status"], f"step ({letter}) {row['status']}: {what}"

    def weakest(*verdicts: str) -> str:
        if FAIL in verdicts:
            return FAIL
        if SKIP in verdicts:
            return SKIP
        return PASS

    f_status, f_said = half("f", "a marker on an unchanged branch is recorded stuck")
    g_status, g_said = half("g", "two or more lanes landed in one repository")
    h_status, h_said = half("h", "the contract check was re-run after integration")

    seven = _clause(
        7, weakest(f_status, attribution["verdict"]),
        f"{f_said}; and on the subject of the sentence — {attribution['why']}",
        measured_half=f_said, attribution=attribution)
    eight = _clause(
        8, weakest(g_status, h_status, attribution["verdict"]),
        f"{g_said}; {h_said} — by this harness, which is the post-merge gate and not "
        f"the manager session; and on whose verification it was — {attribution['why']}",
        measured_halves=[g_said, h_said], attribution=attribution)
    twelve = dict(resolutions)
    if tracker_error:
        twelve = _clause(12, SKIP, f"the queue did not answer: {tracker_error}",
                         awaits="a reachable work queue")

    readings = [seven, eight, twelve]
    evidence = {
        "repo_read": repo, "integration_branch": branch,
        "lane_merges_scanned": len(lane_merges),
        "lane_authored_commits": len(carried),
        "history_reached_the_end": complete,
        "check_records": newest,
        "check_record_history": len(history),
        "manager_check_record": record,
        "tracker_error": tracker_error,
        "clause_readings": readings,
    }
    detail = " · ".join(f"{r['clause']} ({r['row']}) {r['verdict']}: {r['why']}"
                        for r in readings)
    fails = [r for r in readings if r["verdict"] == FAIL]
    live = [r for r in readings if r["verdict"] == PASS]
    if fails:
        return Result(FAIL,
                      f"{len(fails)} of {len(readings)} attribution readings say the "
                      f"promise was broken. {detail}",
                      evidence=evidence)
    if not live:
        return Result(
            SKIP,
            f"None of the {len(readings)} clauses could be attributed on this run. "
            f"{detail}",
            reason=("neither a check-run record on the integration branch nor a "
                    "resolution in the queue could be read here"),
            evidence=evidence,
        )
    return Result(PASS,
                  f"{len(live)} of {len(readings)} clauses carry a reading of who "
                  f"produced the artifact, not only that it exists. {detail}",
                  evidence=evidence)


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
    # (a)-(i) are the contract's turnkey SENTENCE. (j) and (k) are not part of
    # that sentence and never change its verdict: they read the Core clauses
    # the sentence does not reach, and the report keeps the two tallies apart
    # so a clause reading can never be mistaken for the gate going green.
    ("j", "clauses", "the seven Core clauses the nine steps never read", step_clauses),
    ("k", "attribution", "who produced the artifact, not only that it exists",
     step_attribution),
]

# The steps that ARE the turnkey sentence. Everything else is a clause reading.
TURNKEY_STEPS = "abcdefghi"


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
               timeout: float, variables: dict[str, str] | None = None
               ) -> tuple[DtuEnv | None, str]:
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
    argv = ["amplifier-digital-twin", "launch", str(profile), "--name", name]
    for key, value in (variables or {}).items():
        argv += ["--var", f"{key}={value}"]
    ran = host.run(argv, timeout=max(timeout, 2400.0))
    if not ran.ok:
        return None, f"launch failed (exit {ran.code}): {ran.tail(400)}"
    named = ", ".join(sorted(variables or {}))
    return DtuEnv(name, host), (
        f"launched {name}" + (f" with --var {named}" if named else "")
    )


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
# the wave — a manager session that is NOT this harness runs the operation
# ---------------------------------------------------------------------------
#
# Until this existed, driven mode stood the environment up and then JUDGED
# whatever had happened, which in a fresh container was nothing: steps (e)
# through (i) failed for one reason, recorded in RESULT.md as "the harness
# drives the environment, not the wave".
#
# What runs here is a headless `amplifier run` inside the container, told to
# work in the converge-manager mode against the fixture. It is a separate
# process with its own session; this harness does not participate in it. The
# harness's only jobs during the wave are to watch from outside and to hold a
# deadline — and watching from outside is itself the evidence for clause 5,
# because a sub-agent cannot appear in another process's terminal-session list.


def resolve_launcher(env: Env) -> str | None:
    """Find the lane launcher inside the environment. Probed, never assumed."""
    for pattern in LAUNCHER_GLOBS:
        ran = env.run(["bash", "-lc", f"ls -1 {pattern} 2>/dev/null | head -1"],
                      timeout=60.0)
        path = first_line(ran.out)
        if path and env.exists(path):
            return path
    return None


def objective_text(path: Path, fields: dict[str, str]) -> tuple[str, str | None]:
    """Read the objective template, drop its editorial preamble, fill it in.

    The file's first `---` line separates the note explaining what the file is
    (for a human reading the repository) from the text actually sent. Returns
    the text and, on a missing field, the reason it could not be composed.
    """
    raw = path.read_text(encoding="utf-8")
    _, sep, body = raw.partition("\n---\n")
    text = (body if sep else raw).strip()
    missing = [f"{{{k}}}" for k in re.findall(r"\{(\w+)\}", text) if k not in fields]
    if missing:
        return "", f"the objective names fields this run cannot fill: {missing}"
    return text.format(**fields), None


def sample_lanes(ctx: Context) -> dict:
    """One reading of the three systems that can only answer in the present tense.

    Terminal sessions, worktrees, and — the one that matters most for clause 5
    — where each item's HOLDING PROCESS is sitting. A holder's working
    directory is readable only while that process is alive, so a wave that has
    finished can never be asked; this is that question, asked in time.
    """
    holders = []
    items, error = read_tracker_items(ctx.env, ctx.project)
    for item in items if not error else []:
        pid = holder_pid(item.get("holder"))
        if pid is None:
            continue
        process = read_process(ctx.env, pid)
        if process:
            holders.append({"item": item.get("id"), "pid": pid,
                            "cwd": process.get("cwd", ""),
                            "cmdline": process.get("cmdline", "")})
    return {
        "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "sessions": read_tmux_sessions(ctx.env, LANE_TMUX_SOCKET),
        "worktrees": [w for w in read_worktrees(ctx.env, ctx.wave_repo)
                      if str(w.get("branch", "")).startswith("lane/")],
        "holders": holders,
    }


def drive_wave(ctx: Context, objective: Path, deadline_s: float,
               poll_s: float = 15.0) -> dict:
    """Start a manager session in the environment and watch it from outside.

    Returns a record either way. A wave that could not be started is recorded
    as not started, with the reason — never as a wave that ran and did nothing.
    """
    record: dict = {"started": False, "samples": [], "objective": str(objective)}

    seeding = seed_fixture(ctx)
    record["seeding"] = seeding
    if not seeding.get("seeded"):
        record["why"] = f"the fixture could not be seeded: {seeding.get('why')}"
        return record

    # The planted state, read BEFORE a manager session exists to change it.
    # Step (e) asserts the gaps were really there; once the wave has closed
    # them, that assertion can only be made against this reading. Taking it
    # afterwards is how the harness accused its own successful wave of
    # arriving at a fixture that was never red (measured, run C).
    record["fixture_before"] = _fixture_gap_state(ctx)

    launcher = resolve_launcher(ctx.env)
    record["launcher"] = launcher
    if launcher is None:
        # Clause 5: fail loud. A wave with no launcher can only produce
        # in-session work, which is the one thing this gate exists to catch.
        record["why"] = ("no lane launcher was found in the environment, so a "
                         "manager session there could only have run the work "
                         "in-session — clause 5 says fail loud instead")
        return record

    check = " ".join(ctx.answer_key.get("check", ["python3", "check.py", "."]))
    text, why = objective_text(objective, {
        "fixture_repo": ctx.wave_repo,
        "project": ctx.project,
        "width": str(ctx.width),
        "deadline_minutes": str(int(deadline_s // 60)),
        "check_command": check,
        "launcher": launcher,
        "batch_dir": ctx.batch_dir,
        "tmux_socket": LANE_TMUX_SOCKET,
        "return_log": RETURN_LOG,
    })
    if why:
        record["why"] = why
        return record
    record["objective_bytes"] = len(text)

    wrote = ctx.env.run(["bash", "-c", (
        f"mkdir -p {WAVE_BATCH_IN_ENV} && cat > {WAVE_OBJECTIVE_IN_ENV} "
        f"<<'TURNKEY_OBJECTIVE_EOF'\n{text}\nTURNKEY_OBJECTIVE_EOF"
    )], timeout=120.0)
    if not wrote.ok:
        record["why"] = f"the objective could not be written into the environment: {wrote.tail(200)}"
        return record

    # Detached, with every descriptor closed, so the container CLI's exec
    # returns instead of waiting on the manager session's whole run. The exit
    # file is how completion is known: a log that stopped growing proves
    # nothing about whether the process is alive.
    started = ctx.env.run(["bash", "-c", (
        f"cd {ctx.wave_repo} && rm -f {WAVE_EXIT_IN_ENV} && "
        f"setsid bash -lc 'amplifier run \"$(cat {WAVE_OBJECTIVE_IN_ENV})\" "
        f"> {WAVE_LOG_IN_ENV} 2>&1; echo $? > {WAVE_EXIT_IN_ENV}' "
        f"</dev/null >/dev/null 2>&1 & echo started $!"
    )], timeout=180.0)
    if not started.ok:
        record["why"] = f"the manager session would not start: {started.tail(300)}"
        return record
    record["started"] = True
    record["start_output"] = started.tail(120)

    began = time.time()
    while time.time() - began < deadline_s:
        if ctx.env.exists(WAVE_EXIT_IN_ENV):
            break
        record["samples"].append(sample_lanes(ctx))
        time.sleep(poll_s)
    # One last reading either way: a wave that finished between two samples
    # still deserves to be looked at once more before its lanes are judged.
    record["samples"].append(sample_lanes(ctx))

    record["elapsed_s"] = round(time.time() - began, 1)
    exit_text = ctx.env.read(WAVE_EXIT_IN_ENV)
    record["finished"] = exit_text is not None
    record["exit_code"] = int(first_line(exit_text)) if exit_text and \
        first_line(exit_text).isdigit() else None
    if not record["finished"]:
        record["why"] = (f"the manager session was still running when the "
                         f"{deadline_s / 60:.0f}-minute deadline passed; what follows "
                         "judges an unfinished wave, and says so")
    log = ctx.env.read(WAVE_LOG_IN_ENV) or ""
    record["log_bytes"] = len(log)
    record["log_tail"] = log[-4000:]
    record["log_head"] = log[:1500]
    return record


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
    watched = assert_no_subagent_held_work(
        items, {111: None}, ["/w/lanes/a/repo"], None,
        [{"at": "T0", "holders": [{"item": "x-1", "pid": 111,
                                   "cwd": "/w/lanes/a/repo"}]}],
    )
    cases.append(("an exited holder READ IN A LANE while it ran is a pass",
                  watched["verdicts"][0]["verdict"] == PASS))
    elsewhere = assert_no_subagent_held_work(
        items, {111: None}, ["/w/lanes/a/repo"], None,
        [{"at": "T0", "holders": [{"item": "x-1", "pid": 111, "cwd": "/w"}]}],
    )
    cases.append(("an exited holder read OUTSIDE every lane while it ran FAILS",
                  elsewhere["ok"] is False))
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

    both = {"at": "T0", "sessions": ["hw__b__a", "hw__b__b"],
            "worktrees": [{"branch": "lane/a"}, {"branch": "lane/b"}]}
    only_sessions = {"at": "T1", "sessions": ["hw__b__a", "hw__b__b"], "worktrees": []}
    only_worktrees = {"at": "T2", "sessions": [],
                      "worktrees": [{"branch": "lane/a"}, {"branch": "lane/b"}]}
    cases.append(("two lanes seen live at once is the concurrency evidence",
                  assert_lanes_observed_live([only_sessions, both])["verdict"] == PASS))
    cases.append(("two sessions in one sample and two worktrees in ANOTHER is not "
                  "a pass",
                  assert_lanes_observed_live(
                      [only_sessions, only_worktrees])["verdict"] == SKIP))
    cases.append(("nothing lane-shaped in any sample FAILS",
                  assert_lanes_observed_live(
                      [{"at": "T5", "sessions": [], "worktrees": []}])["verdict"] == FAIL))
    cases.append(("one lane is not two",
                  assert_lanes_observed_live(
                      [{"at": "T3", "sessions": ["hw__b__a"],
                        "worktrees": [{"branch": "lane/a"}]}])["verdict"] == FAIL))
    cases.append(("a session that is not a lane does not count",
                  assert_lanes_observed_live(
                      [{"at": "T4", "sessions": ["probe", "0"],
                        "worktrees": [{"branch": "lane/a"}, {"branch": "lane/b"}]}]
                  )["verdict"] == FAIL))
    cases.append(("no samples is a skip, never a pass",
                  assert_lanes_observed_live([])["verdict"] == SKIP))

    # clause 10 -- the five parts belong to ONE entry, and a stamped return
    # with no brief under it is the thing a file-wide read could never see.
    five = ("**Time away.** You were gone two hours and one wave ran in it.\n"
            "**Finished.** Both lanes merged and I re-ran the kit myself.\n"
            "**Stuck.** Nothing stopped; every lane returned with evidence.\n"
            "**Needs you.** Nothing needs you, and no call waits on your word.\n"
            "**Anything quietly broken.** Nothing broke that you did not know.\n")
    header_only = ("# Owner return log\n\nEvery entry names five parts: time away, "
                   "finished, stuck, needs you, and anything quietly broken, "
                   "newest last, each one dated 2026-09-04 or before.\n")
    briefed = "## 2026-09-04 04:01 - the gate went green\n" + five
    holed = "\n".join(ln for ln in briefed.splitlines()
                      if not ln.startswith("**Stuck.")) + "\n"
    cases.append(("a header carrying the five words is not an entry, so not a brief",
                  parse_return_log(header_only) == []))
    cases.append(("one entry with all five parts is a brief, and a stamped return",
                  parse_return_log(briefed)[0]["complete"] is True
                  and parse_return_log(briefed)[0]["stamped"] is True))
    cases.append(("a stamped return missing one part names that part",
                  parse_return_log(holed)[0]["parts_missing"] == ["stuck"]))
    cases.append(("the five words spread across separate entries do not combine",
                  not any(e["complete"] for e in parse_return_log(
                      "## 2026-09-01 - one\ntime away: two hours and no more.\n"
                      "## 2026-09-02 - two\nfinished: the lane merged, nothing else.\n"
                      "## 2026-09-03 - three\nstuck: nothing stopped in this wave.\n"
                      "## 2026-09-04 - four\nneeds you: nothing needs you today.\n"
                      "## 2026-09-05 - five\nquietly broken: nothing broke at all.\n"))))
    cases.append(("an unprompted brief keeps a date-only heading and is not a return",
                  parse_return_log("## 2026-09-04 - a wave landed\n" + five)[0]["stamped"]
                  is False))

    # --- steps (j) and (k): the clauses about what a MANAGER SESSION did.
    # Same bar as everything above: each assertion is shown failing on evidence
    # that must make it fail, and passing on evidence that must not.

    brief_ok = [{"lane": "a", "declared": ["evaluations/turnkey"]}]
    brief_bare = [{"lane": "a", "declared": []}]
    reasoned = [{"at": "T0", "decision": True, "reason": True, "close": False,
                 "feedback": False,
                 "text": "cycle 4: merged x. No refill possible without a collision."}]
    announced = [{"at": "T0", "decision": True, "reason": False, "close": False,
                  "feedback": False, "text": "cycle 4: merged x. 4 live."}]
    cases.append(("a lane brief with no file-ownership split fails clause 2",
                  assert_plan_is_visible(brief_bare, reasoned, "P")["verdict"] == FAIL))
    cases.append(("a plan record that only announces what happened fails clause 2",
                  assert_plan_is_visible(brief_ok, announced, "P")["verdict"] == FAIL))
    cases.append(("declared ownership plus a reasoned plan entry is clause 2 kept",
                  assert_plan_is_visible(brief_ok, reasoned, "P")["verdict"] == PASS))
    cases.append(("no brief and no plan record is a skip naming where it looked",
                  assert_plan_is_visible([], [], None, "looked in W")["awaits"]
                  == "looked in W"))

    disjoint = [{"lane": "a", "declared": ["app/data.py"], "touched": ["app/data.py"]},
                {"lane": "b", "declared": ["ledger/rows.yaml"],
                 "touched": ["ledger/rows.yaml"]}]
    overlapping = [{"lane": "a", "declared": ["app"], "touched": []},
                   {"lane": "b", "declared": ["app/data.py"], "touched": []}]
    collided = [{"lane": "a", "declared": ["app/x.py"], "touched": ["app/shared.py"]},
                {"lane": "b", "declared": ["app/y.py"], "touched": ["app/shared.py"]}]
    cases.append(("two concurrent lanes owning the same path FAIL clause 6",
                  assert_lanes_touch_different_files(overlapping)["verdict"] == FAIL))
    cases.append(("two concurrent lanes that changed one file FAIL clause 6 even when "
                  "their briefs were disjoint",
                  assert_lanes_touch_different_files(collided)["verdict"] == FAIL))
    cases.append(("disjoint briefs and disjoint commits are clause 6 kept",
                  assert_lanes_touch_different_files(disjoint)["verdict"] == PASS))
    cases.append(("one lane is not a width decision, so it is a skip",
                  assert_lanes_touch_different_files(disjoint[:1])["verdict"] == SKIP))

    cases.append(("a lane that stopped with nothing and is named nowhere FAILS clause 9",
                  assert_stalls_are_declared(
                      [{"lane": "w6-x"}], [{"text": "cycle 3: merged y"}]
                  )["verdict"] == FAIL))
    cases.append(("a stall named with its cause is clause 9 kept",
                  assert_stalls_are_declared(
                      [{"lane": "w6-x"}],
                      [{"text": "cycle 3: w6-x died at the provider prompt"}]
                  )["verdict"] == PASS))
    cases.append(("no stall at all is a skip, never a pass",
                  assert_stalls_are_declared([], [])["verdict"] == SKIP))

    quoted = {"id": "p-1", "title": "the changes view is misaligned",
              "description": "Source — the steward on build b7ed3f0, quoted: 'the "
                             "diff is misaligned and the rows are off by one'"}
    unquoted = {"id": "p-2", "title": "the changes view is wrong",
                "description": "the changes view is wrong and should be fixed"}
    cases.append(("an item filed from feedback with no quoted source FAILS clause 4",
                  assert_feedback_was_enriched(
                      [{"entry": "feedback triaged", "item": unquoted}]
                  )["verdict"] == FAIL))
    cases.append(("an item quoting the report and naming the version is clause 4 kept",
                  assert_feedback_was_enriched(
                      [{"entry": "feedback triaged", "item": quoted}]
                  )["verdict"] == PASS))
    cases.append(("a feedback entry naming no item is unresolved, never a pass",
                  assert_feedback_was_enriched(
                      [{"entry": "feedback triaged", "item": None}]
                  )["verdict"] == SKIP))

    cases.append(("a close that says only what finished FAILS clause 13",
                  assert_handoff_on_close(
                      [{"text": "CLOSED: three lanes merged"}])["verdict"] == FAIL))
    cases.append(("a close that names what remains is clause 13 kept",
                  assert_handoff_on_close(
                      [{"text": "CLOSED: three lanes merged. Residuals: two parked"}]
                  )["verdict"] == PASS))
    cases.append(("no close is a skip: no hand-off is owed",
                  assert_handoff_on_close([])["verdict"] == SKIP))

    answered = {"id": "p-1", "status": "resolved",
                "resolution": "The export now refreshes before rule 9a runs, so the "
                              "kit reads the queue as it stands rather than as it "
                              "stood yesterday."}
    empty = {"id": "p-2", "status": "resolved", "resolution": ""}
    pointer = {"id": "p-3", "status": "resolved", "resolution": "Fixed in abc1234."}
    cases.append(("a resolved item with an empty resolution FAILS clause 12",
                  assert_resolutions_written_for_the_asker([empty])["verdict"] == FAIL))
    cases.append(("'Fixed in abc1234.' is a pointer, not an answer",
                  assert_resolutions_written_for_the_asker([pointer])["verdict"] == FAIL))
    cases.append(("a resolution written in sentences is clause 12 kept",
                  assert_resolutions_written_for_the_asker([answered])["verdict"] == PASS))
    cases.append(("no resolved item is a skip, never a pass",
                  assert_resolutions_written_for_the_asker(
                      [{"id": "p-4", "status": "open"}])["verdict"] == SKIP))

    by_integrator = [{"path": "ledger/rows.yaml", "sha": "a" * 40, "at": "T2",
                      "subject": "ledger: re-derived from a live run",
                      "author": "integrator",
                      "lane_merge_before": {"sha": "b" * 40,
                                            "subject": "merge lane/x"}}]
    through_a_merge = [{"path": "ledger/rows.yaml", "sha": "c" * 40, "at": "T1",
                        "subject": "ledger: row", "author": "lane",
                        "lane_merge_before": None}]
    unplaceable = [{"path": "ledger/rows.yaml", "sha": "d" * 40, "at": "T0",
                    "subject": "ledger: row", "author": "unknown",
                    "lane_merge_before": None}]
    cases.append(("a check record only ever written inside a lane FAILS the "
                  "attribution",
                  assert_check_record_attributed(
                      through_a_merge, through_a_merge)["verdict"] == FAIL))
    cases.append(("a check record written outside every lane is the integrator's own",
                  assert_check_record_attributed(
                      by_integrator, by_integrator)["verdict"] == PASS))
    cases.append(("a newest record from a lane, where the integrator has written one "
                  "before, is a skip and not a failure",
                  assert_check_record_attributed(
                      through_a_merge, through_a_merge + by_integrator)["verdict"]
                  == SKIP))
    cases.append(("a record that cannot be placed either side of a merge is unknown, "
                  "never credited",
                  assert_check_record_attributed(
                      unplaceable, unplaceable)["verdict"] == SKIP))
    cases.append(("no check record at all is a skip naming what it looked for",
                  assert_check_record_attributed([], [])["verdict"] == SKIP))

    def _record(author: str, command: str | None = "uv run ledger/checks/verify.py"):
        return {"path": MANAGER_CHECK_RECORD, "exists": True, "entries": 1,
                "newest": {"stamp": "2026-09-04 12:40", "headline": "wave 8",
                           "heading": "## 2026-09-04 12:40 - wave 8",
                           "command": command,
                           "commit": {"sha": "e" * 40, "at": "T3",
                                      "subject": "check record: wave 8",
                                      "author": author,
                                      "lane_merge_before": {"sha": "f" * 40,
                                                            "subject": "merge lane/x"}}}}

    cases.append(("the manager session's own entry, outside every lane, is the "
                  "attribution answered",
                  assert_manager_check_record(_record("integrator"))["verdict"] == PASS))
    cases.append(("an entry that came in through a lane merge FAILS clause 8",
                  assert_manager_check_record(_record("lane"))["verdict"] == FAIL))
    cases.append(("an entry naming no command is a claim, not a record",
                  assert_manager_check_record(
                      _record("integrator", None))["verdict"] == SKIP))
    cases.append(("an entry nobody can place is unknown, never credited",
                  assert_manager_check_record(_record("unknown"))["verdict"] == SKIP))
    cases.append(("no check record file is a skip naming the convention",
                  assert_manager_check_record(
                      {"path": MANAGER_CHECK_RECORD, "exists": False,
                       "entries": 0, "newest": None})["verdict"] == SKIP))
    cases.append(("the file with no entry in it is a skip, never a pass",
                  assert_manager_check_record(
                      {"path": MANAGER_CHECK_RECORD, "exists": True,
                       "entries": 0, "newest": None})["verdict"] == SKIP))

    def _park(text: str, at: str = "T0"):
        return parse_park_events([{"at": at, "text": text}])

    moving = _park("cycle 24: CALL ratify - the candidate needs your word. "
                   "Parked: protocol-terms. Continued: guard-3, renumber-followup.")
    idle = _park("cycle 24: parked protocol-terms on your word. Continued: none.")
    excused = _park("cycle 24: parked protocol-terms on your word. Continued: none, "
                    "because no ready item does not collide with it.")
    silent = _park("cycle 24: Parked: protocol-terms.")
    cases.append(("a park with work continuing beside it is clause 3 kept",
                  assert_parks_kept_the_wave_moving(moving)["verdict"] == PASS))
    cases.append(("a park with nothing continuing and no reason FAILS clause 3",
                  assert_parks_kept_the_wave_moving(idle)["verdict"] == FAIL))
    cases.append(("a park with nothing continuing that says why is not a failure",
                  assert_parks_kept_the_wave_moving(excused)["verdict"] != FAIL))
    cases.append(("a park that never says what continued is a skip, never a pass",
                  assert_parks_kept_the_wave_moving(silent)["verdict"] == SKIP))
    cases.append(("no park at all is a skip: nothing was waiting on the steward",
                  assert_parks_kept_the_wave_moving([])["verdict"] == SKIP))

    outside = _park("cycle 24: CALL design opinion - which shade of blue? "
                    "Parked: none. Continued: guard-3.")
    cases.append(("every recorded call naming one of the four is clause 11 kept",
                  assert_calls_are_one_of_the_four(moving)["verdict"] == PASS))
    cases.append(("a call stamped as none of the four FAILS clause 11",
                  assert_calls_are_one_of_the_four(outside)["verdict"] == FAIL))
    cases.append(("a call that names no kind at all is unread, never a pass",
                  assert_calls_are_one_of_the_four(silent)["verdict"] == SKIP))
    cases.append(("no call at all is a skip, never a pass",
                  assert_calls_are_one_of_the_four([])["verdict"] == SKIP))
    cases.append(("a hostname containing 'park' is not a park",
                  parse_park_events(
                      [{"at": "T0", "text": "app live at http://spark-1:8788"}]) == []))

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


def _wave_summary(wave: dict | None) -> dict | None:
    """What the wave did, without the whole transcript in the middle of it."""
    if wave is None:
        return None
    keep = ("started", "why", "launcher", "objective", "objective_bytes",
            "elapsed_s", "finished", "exit_code", "log_bytes", "log_tail")
    summary = {k: wave[k] for k in keep if k in wave}
    summary["samples"] = wave.get("samples", [])
    return summary


def _tally(rows: list[dict]) -> dict:
    return {
        "pass": sum(r["status"] == PASS for r in rows),
        "fail": sum(r["status"] == FAIL for r in rows),
        "skip": sum(r["status"] == SKIP for r in rows),
    }


def build_report(ctx: Context, rows: list[dict], started: float) -> dict:
    summary = _tally(rows)
    # The turnkey SENTENCE and the clause readings are tallied apart on
    # purpose. The contract's conformance list records a green gate for the
    # nine steps; a clause reading going red is a different fact about a
    # different promise, and rolling them into one number would make each one
    # unreadable through the other. Both are reported; the exit code follows
    # the whole run, because a broken promise is a broken promise.
    turnkey_rows = [r for r in rows if r["step"] in TURNKEY_STEPS]
    clause_rows = [r for r in rows if r["step"] not in TURNKEY_STEPS]
    return {
        "tool": "converge-turnkey",
        "schema": 1,
        "contract": CONTRACT,
        "run_mode": ctx.mode,
        "environment": {"kind": ctx.env.kind, "label": ctx.env.label},
        "workspace": ctx.workspace,
        "repository": ctx.repo,
        "wave_repository": ctx.wave_repo,
        "project": ctx.project,
        "integration_branch": ctx.integration_branch,
        "wave": _wave_summary(ctx.wave),
        "ran_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "elapsed_s": round(time.time() - started, 1),
        "steps": rows,
        "summary": summary,
        "turnkey": {
            "steps": [r["step"] for r in turnkey_rows],
            "summary": _tally(turnkey_rows),
            "verdict": FAIL if any(r["status"] == FAIL for r in turnkey_rows) else PASS,
        },
        "clauses": {
            "steps": [r["step"] for r in clause_rows],
            "summary": _tally(clause_rows),
            "verdict": FAIL if any(r["status"] == FAIL for r in clause_rows) else PASS,
            "readings": [reading for r in clause_rows
                         for reading in (r.get("evidence") or {}).get("clause_readings", [])],
        },
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
    wave = report.get("wave")
    if wave:
        lines[-1:] = [
            "  wave:        " + (
                f"a manager session ran for {wave.get('elapsed_s')}s and "
                f"{'finished' if wave.get('finished') else 'was still running at the deadline'}"
                f" (exit {wave.get('exit_code')}), watched from outside in "
                f"{len(wave.get('samples', []))} readings"
                if wave.get("started") else
                f"NOT RUN — {wave.get('why')}"
            ),
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
    ]
    turnkey, clauses = report.get("turnkey"), report.get("clauses")
    if turnkey and clauses and clauses["steps"]:
        t, c = turnkey["summary"], clauses["summary"]
        lines += [
            f"  the turnkey sentence (a-i): {turnkey['verdict']} "
            f"{t['pass']}·{t['fail']}·{t['skip']}   ·   "
            f"the clause readings (j-k): {clauses['verdict']} "
            f"{c['pass']}·{c['fail']}·{c['skip']}",
        ]
        for reading in clauses["readings"]:
            lines.append(f"         {reading['clause']:8} {reading['row']} "
                         f"[{reading['verdict']:4}] {reading['title']}")
    lines.append("")
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
            "Beyond the sentence, reading the Core clauses it does not reach\n"
            "(tallied apart, so a clause reading is never mistaken for the gate):\n"
            "  j clauses        Core 2, 3, 4, 6, 9, 11, 13 — read from the lane\n"
            "                   briefs, the plan record, git and the queue, never\n"
            "                   from the mode file; a clause with no reading yet\n"
            "                   names the observation it waits on, and names one a\n"
            "                   manager session can actually take\n"
            "  k attribution    Core 7, 8, 12 — WHO re-ran the check and who the\n"
            "                   resolution was written for, from the manager\n"
            "                   session's own check record, which side of a lane\n"
            "                   merge a commit arrived on, and the queue's own text\n"
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
    ap.add_argument("--wave", dest="wave", action="store_true", default=None,
                    help="in a driven environment, run the operation for real: a "
                         "headless manager session in the converge-manager mode, "
                         "watched from outside while it works (default on)")
    ap.add_argument("--no-wave", dest="wave", action="store_false",
                    help="stand the environment up but do not run a manager "
                         "session; steps (e)-(i) then judge whatever is there")
    ap.add_argument("--wave-timeout", type=float, default=3600.0,
                    help="seconds the manager session gets before the run judges "
                         "an unfinished wave and says so (default 3600)")
    ap.add_argument("--wave-poll", type=float, default=15.0,
                    help="seconds between readings of the container's lane state "
                         "while the wave runs (default 15). Measured: a two-lane "
                         "wave on the fixture had both terminal sessions live for "
                         "about 70 seconds, so a coarse interval can miss the only "
                         "window in which concurrency is visible.")
    ap.add_argument("--objective", type=Path, default=HERE / "manager-objective.md",
                    help="the steward objective handed to the manager session")
    ap.add_argument("--width", type=int, default=2,
                    help="how many lanes the wave is asked for, and how many this "
                         "run requires to have been seen running at once (default 2)")
    ap.add_argument("--wave-log", type=Path, default=None,
                    help="write the manager session's full transcript here (outside "
                         "this repository; run.sh sets it)")
    ap.add_argument("--var", action="append", default=[], metavar="KEY=VALUE",
                    help="a launch variable for the DTU profile (repeatable). "
                         "GITEA_URL/GITEA_TOKEN are also read from the environment.")
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

    variables = {k: v for k, _, v in (pair.partition("=") for pair in args.var) if k}
    for name in ("GITEA_URL", "GITEA_TOKEN"):
        if name not in variables and os.environ.get(name):
            variables[name] = os.environ[name]

    env: Env = host
    mode = OBSERVED
    launched: DtuEnv | None = None
    if args.env in ("dtu", "auto"):
        launched, why = launch_dtu(host, args.profile, ledger_root, args.timeout,
                                   variables)
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
        timeout=args.timeout, notes=notes, width=args.width,
    )

    # The wave runs between (d) and (e): the project must exist before a
    # manager session can derive into it, and (e) onward judge what the wave
    # did. It is a phase, not a tenth step -- the contract's sentence has nine.
    wave_after = "d" if (wanted is None or "d" in wanted) else None
    want_wave = (args.wave is not False) and mode == DRIVEN and (
        wanted is None or bool(wanted & set("efghijk"))
    )
    if args.wave is False:
        notes.append("--no-wave: no manager session was run; steps (e)-(i) judge "
                     "whatever was already in this environment")
    elif want_wave and wave_after is None:
        notes.append("the wave was skipped: --steps did not include (d), so no "
                     "project is known to have been started for it to derive into")

    rows = []
    try:
        for letter, name, description, run_step in STEPS:
            if wanted and letter not in wanted:
                continue
            if want_wave and letter == "e" and ctx.wave is None:
                sys.stderr.write(
                    f"\n  running the wave: a manager session in the "
                    f"converge-manager mode, up to {args.wave_timeout / 60:.0f} "
                    f"minutes, watched from outside\n"
                )
                ctx.wave = drive_wave(ctx, args.objective, args.wave_timeout,
                                      args.wave_poll)
                notes.append(
                    f"a manager session ran the wave for real "
                    f"({ctx.wave.get('elapsed_s', 0)}s, exit "
                    f"{ctx.wave.get('exit_code')}); this harness watched from "
                    f"outside it and took {len(ctx.wave.get('samples', []))} "
                    "readings of the container's lane state"
                    if ctx.wave.get("started") else
                    f"the wave did NOT run: {ctx.wave.get('why')}"
                )
                if args.wave_log:
                    args.wave_log.parent.mkdir(parents=True, exist_ok=True)
                    full = env.read(WAVE_LOG_IN_ENV) or ctx.wave.get("log_tail", "")
                    args.wave_log.write_text(full, encoding="utf-8")
                    notes.append(f"the manager session's transcript is at {args.wave_log}")
            try:
                result = run_step(ctx)
            except Exception as exc:  # noqa: BLE001 — a broken step must not fake a pass
                result = Result(SKIP, f"The step itself raised {exc!r}.",
                                reason="the harness failed while running this step")
            row = {
                "step": letter, "name": name, "asserts": description,
                "mode": ctx.mode if letter in "defghijk" else DRIVEN,
                "status": result.status, "detail": result.detail,
            }
            if result.reason:
                row["reason"] = result.reason
            if result.evidence is not None:
                row["evidence"] = result.evidence
            rows.append(row)
            # Step (k) reports the halves of clauses 7 and 8 that earlier steps
            # measured, and names the step that measured them.
            ctx.results.append(row)
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
