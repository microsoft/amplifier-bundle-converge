#!/usr/bin/env python3
"""Converge early-adopter harness.

The question this answers -- and it is a different question from the one
`../turnkey/` answers:

    Can someone who has ONLY README.md, and no idea how any of this is built,
    get from a fresh machine to a project actually running the Converge way --
    on a NEW project, and on an EXISTING one?

Turnkey measures what a manager session does once it is running. This measures
everything BEFORE that: the install, finding the manager session at all, and
the first day of a project. Its profile therefore installs no Converge and no
work queue (see `profiles/adopter.yaml`'s header).

Shape of a run -- ONE CONTAINER PER SCENARIO, never one shared:

    for each scenario:  launch a fresh DTU  ->  push README.md and the
    fixtures  ->  seed that scenario's repository  ->  an AI USER who has read
    only that README drives the Amplifier CLI, while this harness SAMPLES the
    container throughout  ->  the harness JUDGES the container's own artifacts,
    never the AI user's account of them  ->  destroy  ->  RESULT.md

The judging discipline, stated once: **the AI user's verdict is evidence about
the experience, never evidence about the artifacts.** Every PASS below comes
from a command this harness ran inside the container, with the output pasted
into RESULT.md. An AI user that says "I set up the vision" and a container with
no vision file on disk produce a FAIL.

**A row never claims more than it measured.** That is why there are four
verdicts and not three:

    PASS        the thing was seen, and the evidence shows it
    FAIL        the thing was looked for where it would be, and was absent
    CAN'T TELL  the probe could not settle the question -- an empty capture,
                a store that could not be read. NEVER reported as absence,
                and never counted as a pass
    SKIP        the step did not apply to this scenario

Red is a real result. A first run where every step names what was missing is
worth more than a green one that assumed -- and a `CAN'T TELL` is worth more
than either, when that is the truth.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import re
import shlex
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

try:
    from amplifier_evaluation.ai_user import AIUser, InteractionResult
    from amplifier_evaluation.harness.dtu import DTU, DTUError, cli_available

    EVALUATION_IMPORT_ERROR = ""
except ModuleNotFoundError as exc:  # pragma: no cover -- see the note below
    # `amplifier_evaluation` ships in the amplifier-bundle-evaluation repo, not
    # on PyPI, and `run.sh` resolves that repo's venv before calling this file.
    # The JUDGING RULES below -- what a row may conclude from what it saw -- do
    # not need any of it, and `tests/test_judging.py` exercises them without it.
    # A real run still fails loud: `amain` refuses to start and names this.
    AIUser = InteractionResult = DTU = object  # type: ignore[assignment,misc]

    class DTUError(Exception):  # type: ignore[no-redef]
        pass

    def cli_available() -> bool:  # type: ignore[misc]
        return False

    EVALUATION_IMPORT_ERROR = str(exc)

HERE = Path(__file__).resolve().parent
BUNDLE_ROOT = HERE.parent.parent

WORKSPACE = "/workspace"
README_IN_DTU = f"{WORKSPACE}/CONVERGE-README.md"

log = logging.getLogger("adopter")


# ---------------------------------------------------------------------------
# Step records
# ---------------------------------------------------------------------------

PASS, FAIL, UNPROVEN, SKIP = "PASS", "FAIL", "UNPROVEN", "SKIP"

MARK = {PASS: "PASS", FAIL: "FAIL", UNPROVEN: "CAN'T TELL", SKIP: "SKIP"}


@dataclass
class Step:
    """One judged step. `evidence` is what was actually printed, verbatim."""

    id: str
    what: str
    verdict: str
    evidence: str
    missing: str = ""
    """When not PASS: what was absent, or -- on a CAN'T TELL -- why the
    question could not be settled, in plain words. Never empty on a FAIL or a
    CAN'T TELL: a row that does not say what it could not see is not a result."""

    def row(self) -> str:
        detail = self.missing if self.verdict != PASS else _one_line(self.evidence)
        return f"| {self.id} | {self.what} | {MARK[self.verdict]} | {_escape(detail)} |"


@dataclass
class ScenarioRun:
    name: str
    key: str
    sid: str
    project_dir: str
    dtu_id: str = ""
    ledger_registration: str = ""
    setup_steps: list[Step] = field(default_factory=list)
    steps: list[Step] = field(default_factory=list)
    interaction: InteractionResult | None = None
    ai_user_error: str = ""

    @property
    def rows(self) -> list[Step]:
        return list(self.setup_steps) + list(self.steps)

    @property
    def verdict(self) -> str:
        rows = self.rows
        if any(s.verdict == FAIL for s in rows):
            return FAIL
        if any(s.verdict == UNPROVEN for s in rows):
            return UNPROVEN
        if not rows or all(s.verdict == SKIP for s in rows):
            return SKIP
        return PASS


def _one_line(text: str, limit: int = 160) -> str:
    flat = " ".join(text.split())
    return flat if len(flat) <= limit else flat[: limit - 1] + "\u2026"


def _escape(text: str) -> str:
    return text.replace("|", "\\|")


def _fence(text: str, limit: int = 2400) -> str:
    body = text.strip()
    if len(body) > limit:
        body = body[:limit] + "\n\u2026 [truncated]"
    return "```\n" + (body or "(no output)") + "\n```"


def _section(text: str, name: str) -> str:
    """Pull the body between `<<<NAME` and `NAME>>>` markers a probe printed.

    Delimiting the parts of a probe's output is what lets a judgement say
    "the pane was empty" without mistaking the probe's own echoed headings
    for pane content.
    """
    m = re.search(rf"^<<<{name}$(.*?)^{name}>>>$", text, re.S | re.M)
    return m.group(1) if m else ""


# ---------------------------------------------------------------------------
# The infra ledger -- a container is machine-wide, so it is registered
# machine-wide, BEFORE it exists. Once per container, and there is now one
# container per scenario.
# ---------------------------------------------------------------------------

DEFAULT_LEDGER_SCRIPT = (
    Path.home()
    / ".local/share/uv/tools/amplifier/lib/python3.13/site-packages"
    / "amplifier_app_cli/data/skills/ten-lane-highway/scripts/infra_ledger.sh"
)


def register_infra(ledger_script: Path, ledger_root: Path, dtu_id: str) -> str:
    """Register the instance for teardown. Raises if the ledger is unreachable.

    An unregistered container that outlives the run is worse than a step the
    run could not perform, so this failing is fatal BEFORE anything launches.
    """
    if not ledger_script.exists():
        raise RuntimeError(f"infra ledger script not found: {ledger_script}")
    cmd = [
        str(ledger_script),
        str(ledger_root),
        "add",
        "dtu",
        dtu_id,
        f"amplifier-digital-twin destroy {dtu_id}",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if proc.returncode != 0:
        raise RuntimeError(
            f"infra ledger refused the registration (exit {proc.returncode}): "
            f"{proc.stderr.strip()}"
        )
    return " ".join(shlex.quote(c) for c in cmd)


# ---------------------------------------------------------------------------
# Probes -- every one of these runs INSIDE the container, and its raw output is
# the evidence.
# ---------------------------------------------------------------------------


async def probe(dtu: DTU, script: str, *, timeout_s: float = 120.0) -> tuple[int, str]:
    """Run a shell snippet in the container; return (rc, stdout+stderr)."""
    try:
        res = await dtu.exec_cmd(["bash", "-lc", script], timeout_s=timeout_s)
    except DTUError as exc:  # a probe that cannot run is never a PASS
        return 1, f"probe could not run: {exc}"
    out = res.stdout
    if res.stderr.strip():
        out = f"{out}\n[stderr] {res.stderr}"
    return res.returncode, out


CONVERGE_ABSENT_SCRIPT = (
    "echo '<<<BUNDLES'; amplifier bundle list 2>&1 | head -30; echo 'BUNDLES>>>'; "
    "echo '<<<QUEUECLI'; "
    "command -v amplifier-work-tracker || echo 'amplifier-work-tracker: not on PATH'; "
    "echo 'QUEUECLI>>>'; true"
)


async def judge_fresh_container(
    dtu: DTU, sid: str, launch_note: str
) -> tuple[Step, str]:
    """Did THIS scenario's own container start with no Converge in it?

    The readiness gate `converge-absent` already refuses a contaminated launch,
    but a gate that ran is not evidence a reader can see. This reads the same
    fact back out of the container and pastes it, so the install row below can
    be read as a measurement of THIS scenario's install and nothing else.
    """
    rc, out = await probe(dtu, CONVERGE_ABSENT_SCRIPT)
    return fresh_container_verdict(sid, launch_note, out)


def fresh_container_verdict(sid: str, launch_note: str, out: str) -> tuple[Step, str]:
    bundles = _section(out, "BUNDLES")
    queue_cli = _section(out, "QUEUECLI")
    converge_present = "converge" in bundles.lower()
    evidence = f"{launch_note}\n\n--- read back from the container, before the AI user ---\n{out}"
    if not converge_present:
        return (
            Step(
                f"{sid}.G1",
                "This scenario's own container comes up with no Converge in it",
                PASS,
                evidence,
            ),
            f"{bundles}\n[queue CLI at launch] {queue_cli.strip()}",
        )
    return (
        Step(
            f"{sid}.G1",
            "This scenario's own container comes up with no Converge in it",
            FAIL,
            evidence,
            missing=(
                "a converge row was already in `amplifier bundle list` at launch -- "
                "this scenario's install step would measure nothing"
            ),
        ),
        f"{bundles}\n[queue CLI at launch] {queue_cli.strip()}",
    )


async def judge_install(dtu: DTU, sid: str, before: str) -> Step:
    rc, out = await probe(
        dtu,
        "echo '--- bundle list ---'; amplifier bundle list 2>&1 | head -30; "
        "echo '--- agents list (converge rows) ---'; "
        "amplifier agents list 2>&1 | grep -i converge | head -10; true",
    )
    composed = "converge" in out.lower()
    agent_on = any(
        "[on]" in line and "converge" in line.lower() for line in out.splitlines()
    )
    evidence = (
        "--- at launch, in this scenario's own container, before the AI user ---\n"
        f"{before.strip()}\n\n--- after the AI user stopped ---\n{out}"
    )
    if composed and agent_on:
        return Step(
            f"{sid}.1",
            "Converge installed and composed into the CLI",
            PASS,
            evidence,
        )
    return Step(
        f"{sid}.1",
        "Converge installed and composed into the CLI",
        FAIL,
        evidence,
        missing=(
            "no converge row in `amplifier bundle list`"
            if not composed
            else "converge is registered but no converge agent lists as [on] -- "
            "registered is not composed"
        ),
    )


# ---- the manager session, sampled THROUGHOUT rather than once at the end ----

CAPTURE_SCRIPT = (
    "echo '<<<SESSIONS'; "
    "{ tmux list-sessions 2>&1; tmux -L hw list-sessions 2>&1; } | head -20; "
    "echo 'SESSIONS>>>'; "
    "echo '<<<PANE'; "
    "{ tmux capture-pane -p -t agent -S -60 2>/dev/null; "
    "  tmux -L hw capture-pane -p -t agent -S -60 2>/dev/null; }; "
    "echo 'PANE>>>'; true"
)

MODE_MARKER = "[converge-manager]"
_SESSION_LINE = re.compile(r"^\S+:\s+\d+\s+window", re.M)


@dataclass
class PaneWatch:
    """What the pane showed across a whole scenario, not at one instant.

    The defect this exists for: capturing once, at the end, and reading an
    empty pane as "the prompt never showed the mode". A session restarted
    seconds before the capture produces exactly that empty pane, and the row
    then names a cause the evidence does not support.
    """

    interval_s: float = 30.0
    samples: int = 0
    ok_samples: int = 0
    session_samples: int = 0
    pane_samples: int = 0
    marker_samples: int = 0
    first_marker_at: str = ""
    first_marker_capture: str = ""
    last_capture: str = ""
    last_at: str = ""
    started_at: str = ""
    timeline: list[str] = field(default_factory=list)

    def note(self, ts: datetime, rc: int, out: str) -> None:
        stamp = f"{ts:%H:%M:%S}Z"
        if not self.started_at:
            self.started_at = stamp
        self.samples += 1
        self.last_at = stamp
        self.last_capture = out
        if rc != 0 and out.startswith("probe could not run"):
            self.timeline.append(f"{stamp}  probe failed: {_one_line(out, 60)}")
            return
        self.ok_samples += 1
        sessions = _section(out, "SESSIONS")
        pane = _section(out, "PANE")
        has_session = bool(_SESSION_LINE.search(sessions))
        pane_bytes = len(pane.strip())
        has_marker = MODE_MARKER in pane
        if has_session:
            self.session_samples += 1
        if pane_bytes:
            self.pane_samples += 1
        if has_marker:
            self.marker_samples += 1
            if not self.first_marker_at:
                self.first_marker_at = stamp
                self.first_marker_capture = out
        self.timeline.append(
            f"{stamp}  session={'yes' if has_session else 'no ':3}  "
            f"pane={pane_bytes:>5}B  mode={'YES' if has_marker else 'no'}"
        )

    def summary(self) -> str:
        span = f"{self.started_at} -> {self.last_at}" if self.samples else "(none)"
        return (
            f"sampled every {self.interval_s:.0f}s through the scenario, {span}: "
            f"{self.samples} captures, {self.ok_samples} that ran, "
            f"{self.session_samples} with a live agent session, "
            f"{self.pane_samples} with pane content, "
            f"{self.marker_samples} showing `{MODE_MARKER}`"
            + (f" (first at {self.first_marker_at})" if self.first_marker_at else "")
        )

    def evidence(self) -> str:
        parts = [self.summary(), ""]
        if self.first_marker_capture:
            parts += [
                f"--- first capture showing the mode, {self.first_marker_at} ---",
                self.first_marker_capture.strip(),
                "",
            ]
        else:
            parts += [
                f"--- last capture, {self.last_at or '(none)'} ---",
                (self.last_capture or "(no capture was ever taken)").strip(),
                "",
            ]
        tail = self.timeline[-14:]
        if len(self.timeline) > len(tail):
            parts.append(f"--- timeline (last {len(tail)} of {len(self.timeline)}) ---")
        else:
            parts.append("--- timeline ---")
        parts += tail
        return "\n".join(parts)


async def watch_pane(
    dtu: DTU, watch: PaneWatch, stop: asyncio.Event, interval_s: float
) -> None:
    """Sample the pane until told to stop. Errors are recorded, never raised."""
    watch.interval_s = interval_s
    while not stop.is_set():
        ts = datetime.now(timezone.utc)
        try:
            rc, out = await probe(dtu, CAPTURE_SCRIPT, timeout_s=60.0)
        except Exception as exc:  # noqa: BLE001 -- a sampler must not kill a run
            rc, out = 1, f"probe could not run: {type(exc).__name__}: {exc}"
        watch.note(ts, rc, out)
        try:
            await asyncio.wait_for(stop.wait(), timeout=interval_s)
        except asyncio.TimeoutError:
            pass


def judge_manager_session(sid: str, watch: PaneWatch) -> Step:
    what = "A manager session is running against the project"
    if watch.marker_samples:
        return Step(f"{sid}.2", what, PASS, watch.evidence())
    if watch.ok_samples == 0:
        return Step(
            f"{sid}.2",
            what,
            UNPROVEN,
            watch.evidence(),
            missing=(
                f"could not tell -- not one of the {watch.samples} captures ran, so "
                "nothing was measured either way"
            ),
        )
    if watch.session_samples == 0:
        return Step(
            f"{sid}.2",
            what,
            FAIL,
            watch.evidence(),
            missing=(
                f"no agent session existed at any of the {watch.ok_samples} captures "
                "taken through the scenario"
            ),
        )
    if watch.pane_samples == 0:
        return Step(
            f"{sid}.2",
            what,
            UNPROVEN,
            watch.evidence(),
            missing=(
                f"could not tell -- a session was live at {watch.session_samples} of "
                f"{watch.ok_samples} captures, but every capture came back empty; an "
                f"empty pane is not evidence that the prompt never showed `{MODE_MARKER}`"
            ),
        )
    return Step(
        f"{sid}.2",
        what,
        FAIL,
        watch.evidence(),
        missing=(
            f"{watch.pane_samples} of {watch.ok_samples} captures through the scenario "
            f"showed pane content and none showed `{MODE_MARKER}` -- an ordinary "
            "session is not a manager session"
        ),
    )


async def judge_vision(dtu: DTU, sid: str, project_dir: str) -> Step:
    rc, out = await probe(
        dtu,
        f"cd {shlex.quote(project_dir)} 2>/dev/null || exit 1; "
        "find . -path ./.git -prune -o -iname 'VISION*.md' -print 2>/dev/null; "
        "echo '--- first 15 lines of each ---'; "
        "for f in $(find . -path ./.git -prune -o -iname 'VISION*.md' -print 2>/dev/null); "
        "do echo \"== $f\"; head -15 \"$f\"; done; true",
    )
    found = [ln for ln in out.splitlines() if ln.strip().endswith(".md") and "VISION" in ln.upper()]
    if found:
        return Step(f"{sid}.3", "A vision is written down in the project", PASS, out)
    return Step(
        f"{sid}.3",
        "A vision is written down in the project",
        FAIL,
        out,
        missing="no file matching VISION*.md anywhere in the project",
    )


async def judge_contract(dtu: DTU, sid: str, project_dir: str) -> Step:
    rc, out = await probe(
        dtu,
        f"cd {shlex.quote(project_dir)} 2>/dev/null || exit 1; "
        "ls -1 contracts/*.md 2>/dev/null; "
        "echo '--- headings ---'; "
        "head -1 contracts/*.md 2>/dev/null; true",
    )
    found = [ln for ln in out.splitlines() if ln.strip().startswith("contracts/")]
    if found:
        return Step(f"{sid}.4", "At least one contract is written down", PASS, out)
    return Step(
        f"{sid}.4",
        "At least one contract is written down",
        FAIL,
        out,
        missing="no contracts/*.md in the project",
    )


async def judge_ledger(dtu: DTU, sid: str, project_dir: str) -> Step:
    rc, out = await probe(
        dtu,
        f"cd {shlex.quote(project_dir)} 2>/dev/null || exit 1; "
        "find . -path ./.git -prune -o \\( -name 'rows.yaml' -o -path './ledger/*' \\) "
        "-print 2>/dev/null | head -20; "
        "echo '--- first 20 lines of ledger/rows.yaml ---'; "
        "head -20 ledger/rows.yaml 2>&1; true",
    )
    seeded = "ledger/rows.yaml" in out and "No such file" not in out
    if seeded:
        return Step(f"{sid}.5", "The project's contract check is seeded", PASS, out)
    return Step(
        f"{sid}.5",
        "The project's contract check is seeded",
        FAIL,
        out,
        missing="no ledger/rows.yaml (or equivalent contract check) in the project",
    )


# ---- the queue, read where a SESSION writes it, not where a CLI would be ----

QUEUE_PROBE_PY = r'''
"""Read the work queue the way an agent writes it.

An agent files work through its session's `work_*` tools. Those write to the
work-tracker's own store -- $AMPLIFIER_WORK_TRACKER_ROOT (default
~/.amplifier-work-tracker), one directory per project, each holding a `.beads`
database -- and they do not need the `amplifier-work-tracker` CLI to be on
PATH to do it. A probe that looks only for that CLI measures the CLI, and any
sentence it writes about whether work exists is a claim it did not check.

So: report the CLI as the separate fact it is, then read every store this
container actually has, with `bd`, which the profile provides.
"""

import json
import os
import pathlib
import re
import shutil
import subprocess

CONTRACT = re.compile(
    r"(Contract:\s*\S+|contracts/[A-Za-z0-9._-]+\.md|\b[a-z][a-z0-9-]*\.v[0-9]+\b)"
)

home = pathlib.Path(os.path.expanduser("~"))
root = pathlib.Path(
    os.environ.get("AMPLIFIER_WORK_TRACKER_ROOT", str(home / ".amplifier-work-tracker"))
)

cli = shutil.which("amplifier-work-tracker")
print("--- the queue CLI (a separate fact from whether a queue holds work) ---")
print("amplifier-work-tracker on PATH: %s" % (cli or "no"))

print()
print("--- every queue store in this container ---")
print("work-tracker root: %s (exists: %s)" % (root, root.is_dir()))

MARKERS = ("config.yaml", "metadata.json", "issues.jsonl", "dolt")


def is_store(d):
    """A real queue store, not a stray `.beads` scratch dir.

    Running `bd` at all can leave a bare `$HOME/.beads/eventsData` behind.
    Counting that as a store would turn "nothing was ever filed" into "a store
    exists that I could not read" -- a CAN'T TELL where the truth is a FAIL.
    """
    b = d / ".beads"
    return b.is_dir() and any((b / m).exists() for m in MARKERS)


stores = []
skipped = []
projects_dir = root / "projects"
if projects_dir.is_dir():
    for p in sorted(projects_dir.iterdir()):
        if is_store(p):
            stores.append(p)
        elif (p / ".beads").is_dir():
            skipped.append(p)

# An adopter may also have initialised a queue inside the project itself.
for base in ("/workspace", str(home)):
    b = pathlib.Path(base)
    if not b.is_dir():
        continue
    try:
        out = subprocess.run(
            ["find", base, "-maxdepth", "4", "-type", "d", "-name", ".beads"],
            capture_output=True, text=True, timeout=60,
        ).stdout
    except Exception:
        out = ""
    for line in out.splitlines():
        d = pathlib.Path(line).parent
        if d in stores or d in skipped:
            continue
        (stores if is_store(d) else skipped).append(d)

for s in stores:
    print("store: %s" % s)
for s in skipped:
    print("not a store (a .beads dir with no database in it): %s" % s)
if not stores:
    print("(no queue store anywhere -- nothing a session's work_* tools would write)")

items_total = 0
contract_items = 0
read_errors = 0
examples = []

def read_store(path):
    """(rows, note). Tries `bd` in the store itself first -- no CLI needed."""
    attempts = [(["bd", "list", "--json"], str(path))]
    if cli:
        # A fallback only. The CLI is never the reason a row is red; it is
        # here because when it IS present it manages the queue's service, so
        # it can sometimes read a store that a bare `bd` cannot reach.
        attempts.append(
            ([cli, "list", "--project", path.name, "--json", "--limit", "500"], None)
        )
    notes = []
    for argv, cwd in attempts:
        try:
            proc = subprocess.run(
                argv, cwd=cwd, capture_output=True, text=True, timeout=120
            )
        except Exception as exc:
            notes.append("%s: %s: %s" % (argv[0], type(exc).__name__, exc))
            continue
        if proc.returncode != 0:
            notes.append(
                "%s exit %d: %s"
                % (argv[0], proc.returncode, (proc.stderr or proc.stdout).strip()[:300])
            )
            continue
        try:
            payload = json.loads(proc.stdout or "[]")
        except Exception as exc:
            notes.append("%s: could not parse output: %s" % (argv[0], exc))
            continue
        if isinstance(payload, dict):
            payload = payload.get("items") or payload.get("output") or []
        if isinstance(payload, dict):
            payload = payload.get("items") or []
        if isinstance(payload, list):
            return payload, "read with %s" % argv[0]
        notes.append("%s: unexpected shape %s" % (argv[0], type(payload).__name__))
    return None, "; ".join(notes) or "no reader available"


for s in stores:
    print()
    print("== project %s (%s)" % (s.name, s))
    rows, note = read_store(s)
    print(note)
    if rows is None:
        read_errors += 1
        continue
    if not isinstance(rows, list):
        rows = []
    print("%d item(s)" % len(rows))
    for row in rows:
        items_total += 1
        text = " ".join(
            str(row.get(k) or "")
            for k in ("id", "title", "description", "design", "acceptance_criteria")
        )
        m = CONTRACT.search(text)
        line = "  %s  %s" % (row.get("id"), str(row.get("title") or "")[:100])
        if m:
            contract_items += 1
            line += "\n      names a contract: %s" % m.group(0)[:100]
            if len(examples) < 5:
                examples.append(line)
        print(line)

print()
print("--- what this measured ---")
print("QUEUE-CLI: %s" % ("present" if cli else "absent"))
print("QUEUE-STORES: %d" % len(stores))
print("QUEUE-ITEMS: %d" % items_total)
print("QUEUE-CONTRACT-ITEMS: %d" % contract_items)
print("QUEUE-READ-ERRORS: %d" % read_errors)
'''


def _marker_int(out: str, key: str) -> int:
    m = re.search(rf"^{key}:\s*(-?\d+)\s*$", out, re.M)
    return int(m.group(1)) if m else -1


async def judge_queue(dtu: DTU, sid: str) -> Step:
    script = (
        "cat > /tmp/adopter-queue-probe.py <<'ADOPTER_PY'\n"
        + QUEUE_PROBE_PY
        + "\nADOPTER_PY\n"
        "python3 /tmp/adopter-queue-probe.py 2>&1; true"
    )
    rc, out = await probe(dtu, script, timeout_s=300.0)
    return queue_verdict(sid, out)


def queue_verdict(sid: str, out: str) -> Step:
    """Judge the queue from the probe's own output.

    Pure, so the rule it encodes can be tested without a container: the CLI's
    absence is reported as the separate fact it is, and never as proof that no
    item exists.
    """
    what = "A queue holds work that names the contracts it serves"

    stores = _marker_int(out, "QUEUE-STORES")
    items = _marker_int(out, "QUEUE-ITEMS")
    contract_items = _marker_int(out, "QUEUE-CONTRACT-ITEMS")
    errors = _marker_int(out, "QUEUE-READ-ERRORS")
    cli_present = "QUEUE-CLI: present" in out
    cli_note = (
        "the queue CLI was on PATH"
        if cli_present
        else "the queue CLI never arrived (a separate fact: it is not what was asked here)"
    )

    if stores < 0:
        return Step(
            f"{sid}.6",
            what,
            UNPROVEN,
            out,
            missing=(
                "could not tell -- the queue probe did not report a result, so whether "
                "any work was filed is unmeasured"
            ),
        )
    if contract_items > 0:
        return Step(f"{sid}.6", what, PASS, out)
    if items > 0:
        return Step(
            f"{sid}.6",
            what,
            FAIL,
            out,
            missing=(
                f"the queue holds {items} item(s) and none names a contract "
                f"({cli_note})"
            ),
        )
    if stores == 0:
        return Step(
            f"{sid}.6",
            what,
            FAIL,
            out,
            missing=(
                "no queue store exists anywhere in the container -- nothing a session's "
                f"`work_*` tools would have written is on disk ({cli_note})"
            ),
        )
    if errors > 0:
        return Step(
            f"{sid}.6",
            what,
            UNPROVEN,
            out,
            missing=(
                f"could not tell -- {stores} queue store(s) exist but {errors} could not "
                f"be read, so whether they hold work is unmeasured ({cli_note})"
            ),
        )
    return Step(
        f"{sid}.6",
        what,
        FAIL,
        out,
        missing=f"{stores} queue store(s) exist and hold no items at all ({cli_note})",
    )


# ---------------------------------------------------------------------------
# The run
# ---------------------------------------------------------------------------


async def setup_scenario_container(
    dtu: DTU, readme: Path, sid: str, key: str, project_dir: str
) -> list[Step]:
    """Push the README under test and the fixtures; seed THIS scenario's repo."""
    steps: list[Step] = []

    await dtu.file_push(readme, README_IN_DTU)
    rc, out = await probe(dtu, f"wc -l {README_IN_DTU} && sha256sum {README_IN_DTU}")
    local_sha = subprocess.run(
        ["sha256sum", str(readme)], capture_output=True, text=True
    ).stdout.split()[0]
    ok = rc == 0 and local_sha in out
    steps.append(
        Step(
            f"{sid}.G2",
            "The README under test is in the container, byte for byte",
            PASS if ok else FAIL,
            out + f"\n[host] {local_sha}  {readme}",
            missing="" if ok else "the pushed README's digest does not match the host's",
        )
    )

    await dtu.file_push(HERE / "fixtures", f"{WORKSPACE}/")
    seed_kind = "new" if key == "new-project" else "existing"
    rc, out = await probe(
        dtu,
        f"chmod +x {WORKSPACE}/fixtures/seed.sh && "
        f"{WORKSPACE}/fixtures/seed.sh {seed_kind} {shlex.quote(project_dir)} && "
        f"echo '--- tree ---' && ls -a {shlex.quote(project_dir)}",
        timeout_s=300.0,
    )
    steps.append(
        Step(
            f"{sid}.G3",
            "This scenario's starting repository is seeded",
            PASS if rc == 0 else FAIL,
            out,
            missing="" if rc == 0 else f"seeding exited {rc}",
        )
    )

    if key == "existing-project":
        # The fixture's own tests, BEFORE adoption. A runner that is not
        # installed cannot prove the fixture works -- and it cannot prove it
        # is broken either, so that is a CAN'T TELL, never a pass.
        rc, out = await probe(
            dtu,
            f"cd {shlex.quote(project_dir)} && "
            "if python3 -c 'import pytest' 2>/dev/null; then "
            "  echo '[runner] python3 -m pytest'; python3 -m pytest -q 2>&1 | tail -5; "
            "  exit ${PIPESTATUS[0]}; "
            "elif command -v uv >/dev/null; then "
            "  echo '[runner] uv run --with pytest pytest'; "
            "  uv run --quiet --with pytest pytest -q 2>&1 | tail -5; "
            "  exit ${PIPESTATUS[0]}; "
            "else echo '[runner] none available'; exit 97; fi",
            timeout_s=420.0,
        )
        ran = "[runner] none available" not in out and "No module named pytest" not in out
        if ran and rc == 0:
            step = Step(
                f"{sid}.G4",
                "The existing project's own tests pass before adoption",
                PASS,
                out,
            )
        elif ran:
            step = Step(
                f"{sid}.G4",
                "The existing project's own tests pass before adoption",
                FAIL,
                out,
                missing=f"the fixture's tests ran and did not pass (exit {rc})",
            )
        else:
            step = Step(
                f"{sid}.G4",
                "The existing project's own tests pass before adoption",
                UNPROVEN,
                out,
                missing=(
                    "could not tell -- no test runner was available in the container, so "
                    "the fixture was neither shown to work nor shown to be broken"
                ),
            )
        steps.append(step)

    return steps


async def run_scenario(
    *,
    dtu: DTU,
    ai_user: AIUser,
    run: ScenarioRun,
    scenario_path: Path,
    invocation: str,
    out_dir: Path,
    budget_s: float,
    pane_interval_s: float,
    before_install: str,
) -> None:
    scenario_text = scenario_path.read_text(encoding="utf-8")
    sid = run.sid

    watch = PaneWatch(interval_s=pane_interval_s)
    stop = asyncio.Event()
    watcher = asyncio.create_task(watch_pane(dtu, watch, stop, pane_interval_s))

    log.info("[%s] AI user starting (budget %.0fs)", run.name, budget_s)
    started = time.monotonic()
    try:
        run.interaction = await asyncio.wait_for(
            ai_user.run(
                scenario=scenario_text,
                dtu_id=dtu.id,
                invocation_guide=invocation,
                persona=(
                    "You are a pragmatic senior engineer adopting a new way of "
                    "working. You are comfortable at a terminal and you read "
                    "documentation carefully, but you have no prior knowledge of "
                    "this system and you refuse to guess at commands the "
                    "documentation does not give you -- when you cannot find "
                    "something, you say so plainly rather than inventing it. You "
                    "are the intent steward: you decide, and you do not ratify "
                    "anything you have not read."
                ),
                workspace_dir=run.project_dir,
            ),
            timeout=budget_s,
        )
    except asyncio.TimeoutError:
        run.ai_user_error = f"the AI user did not finish within {budget_s:.0f}s"
        log.warning("[%s] %s", run.name, run.ai_user_error)
    except Exception as exc:  # noqa: BLE001 -- recorded, never swallowed
        run.ai_user_error = f"{type(exc).__name__}: {exc}"
        log.warning("[%s] AI user failed: %s", run.name, run.ai_user_error)
    finally:
        stop.set()
        try:
            await asyncio.wait_for(watcher, timeout=90.0)
        except (asyncio.TimeoutError, asyncio.CancelledError):
            watcher.cancel()
    elapsed = time.monotonic() - started

    # One last sample after the AI user stopped, folded into the same record.
    ts = datetime.now(timezone.utc)
    rc, out = await probe(dtu, CAPTURE_SCRIPT, timeout_s=60.0)
    watch.note(ts, rc, out)

    if run.interaction is not None:
        (out_dir / f"{sid}-ai-user.json").write_text(
            json.dumps(
                {
                    "scenario": run.name,
                    "dtu_id": dtu.id,
                    "elapsed_s": run.interaction.elapsed_s,
                    "session_id": run.interaction.ai_user_session_id,
                    "verdict": getattr(run.interaction.conclude, "verdict", None),
                    "summary": getattr(run.interaction.conclude, "summary", None),
                    "final_text": run.interaction.final_assistant_text,
                },
                indent=2,
                default=str,
            ),
            encoding="utf-8",
        )
    log.info("[%s] AI user done in %.0fs; judging artifacts", run.name, elapsed)

    run.steps = [
        await judge_install(dtu, sid, before_install),
        judge_manager_session(sid, watch),
        await judge_vision(dtu, sid, run.project_dir),
        await judge_contract(dtu, sid, run.project_dir),
        await judge_ledger(dtu, sid, run.project_dir),
        await judge_queue(dtu, sid),
    ]


def write_result(path: Path, *, scenarios: list[ScenarioRun], meta: dict) -> str:
    all_steps = [s for r in scenarios for s in r.rows]
    n_pass = sum(1 for s in all_steps if s.verdict == PASS)
    n_fail = sum(1 for s in all_steps if s.verdict == FAIL)
    n_unproven = sum(1 for s in all_steps if s.verdict == UNPROVEN)
    n_skip = sum(1 for s in all_steps if s.verdict == SKIP)
    if n_fail:
        overall = "RED"
    elif n_unproven:
        overall = "NOT PROVEN"
    elif n_pass:
        overall = "GREEN"
    else:
        overall = "EMPTY"

    lines: list[str] = []
    lines.append("# Adopter harness \u2014 RESULT")
    lines.append("")
    lines.append(
        f"**{overall}** \u2014 {n_pass} pass \u00b7 {n_fail} fail \u00b7 "
        f"{n_unproven} can't tell \u00b7 {n_skip} skip, run {meta['started']}."
    )
    lines.append("")
    lines.append(
        "What this run asked: can someone holding only `README.md` get a NEW "
        "project and an EXISTING project to the point of actually running the "
        "Converge way? **Each scenario ran in its own fresh container**, so no "
        "row below inherits anything another scenario's adopter did. Every "
        "verdict was read out of that container by this harness. The AI user's "
        "own account is reported separately, as evidence about the experience "
        "\u2014 never as evidence about the artifacts."
    )
    lines.append("")
    lines.append(
        "`CAN'T TELL` is a real verdict here, distinct from `FAIL`: it means the "
        "probe could not settle the question. It is never reported as absence "
        "and never counted as a pass."
    )
    lines.append("")
    lines.append("## Provenance")
    lines.append("")
    for k in (
        "started",
        "finished",
        "profile",
        "readme_sha256",
        "readme_matches_origin_main",
        "bundle_commit",
        "pane_sample_interval_s",
        "scenario_budget_s",
        "output_dir",
    ):
        if k in meta:
            lines.append(f"- **{k}** \u2014 `{meta[k]}`")
    for run in scenarios:
        lines.append(f"- **{run.name}** \u2014 container `{run.dtu_id}`")
        if run.ledger_registration:
            lines.append(f"  - registered before launch: `{run.ledger_registration}`")
    lines.append("")

    lines.append("## Steps")
    lines.append("")
    lines.append("| # | What was asked | | What was missing (or, on a pass, what was seen) |")
    lines.append("|---|---|---|---|")
    for run in scenarios:
        lines.append(
            f"| | **{run.name}** \u2014 `{run.project_dir}` in `{run.dtu_id}` "
            f"| **{MARK[run.verdict]}** | |"
        )
        for s in run.rows:
            lines.append(s.row())
    lines.append("")

    lines.append("## What the AI user reported")
    lines.append("")
    lines.append(
        "The AI user read only `CONVERGE-README.md` and drove the Amplifier CLI "
        "as a person would. Where it says it could not find something, that is "
        "the finding this harness exists to surface."
    )
    lines.append("")
    for run in scenarios:
        lines.append(f"### {run.name}")
        lines.append("")
        if run.ai_user_error:
            lines.append(f"The AI user did not conclude: {run.ai_user_error}")
            lines.append("")
            continue
        inter = run.interaction
        if inter is None:
            lines.append("The AI user never ran.")
            lines.append("")
            continue
        verdict = getattr(inter.conclude, "verdict", None)
        summary = getattr(inter.conclude, "summary", None)
        lines.append(f"- **verdict** \u2014 `{verdict}` (after {inter.elapsed_s:.0f}s)")
        lines.append("")
        lines.append(_fence(summary or inter.final_assistant_text, limit=3000))
        lines.append("")

    lines.append("## Evidence, step by step")
    lines.append("")
    lines.append(
        "Verbatim output of the probe behind each row above. A probe that could "
        "not run is recorded as a failure or a `CAN'T TELL`, never as a pass."
    )
    lines.append("")
    for s in all_steps:
        lines.append(f"### {s.id} \u2014 {s.what} \u2014 {MARK[s.verdict]}")
        lines.append("")
        if s.missing:
            label = "Could not tell" if s.verdict == UNPROVEN else "Missing"
            lines.append(f"{label}: {s.missing}")
            lines.append("")
        lines.append(_fence(s.evidence))
        lines.append("")

    text = "\n".join(lines) + "\n"
    path.write_text(text, encoding="utf-8")
    return overall


async def amain(args: argparse.Namespace) -> int:
    logging.basicConfig(
        level=logging.INFO, format="[%(asctime)s] %(levelname)s %(message)s"
    )
    logging.getLogger("amplifier_evaluation.harness.dtu").setLevel(logging.INFO)

    if EVALUATION_IMPORT_ERROR:
        log.error(
            "amplifier_evaluation is not importable under this interpreter (%s). "
            "Run this through ./evaluations/adopter/run.sh, which resolves the "
            "amplifier-bundle-evaluation venv.",
            EVALUATION_IMPORT_ERROR,
        )
        return 2

    if not cli_available():
        log.error("amplifier-digital-twin is not on PATH")
        return 2

    out_dir = Path(args.output).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    readme = BUNDLE_ROOT / "README.md"
    if not readme.exists():
        log.error("README.md not found at %s", readme)
        return 2

    readme_sha = subprocess.run(
        ["sha256sum", str(readme)], capture_output=True, text=True
    ).stdout.split()[0]
    bundle_commit = subprocess.run(
        ["git", "-C", str(BUNDLE_ROOT), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
    ).stdout.strip()
    origin_readme = subprocess.run(
        ["git", "-C", str(BUNDLE_ROOT), "show", "origin/main:README.md"],
        capture_output=True,
        text=True,
    )
    readme_matches_main = (
        "unknown"
        if origin_readme.returncode != 0
        else str(origin_readme.stdout == readme.read_text(encoding="utf-8"))
    )

    run_stamp = args.name or f"adopter-{datetime.now(timezone.utc):%Y%m%d%H%M%S}"

    meta = {
        "started": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "profile": str(args.profile),
        "readme_sha256": readme_sha,
        "readme_matches_origin_main": readme_matches_main,
        "bundle_commit": bundle_commit,
        "pane_sample_interval_s": args.pane_interval,
        "scenario_budget_s": args.scenario_budget,
        "output_dir": str(out_dir),
    }

    variables = {}
    for key in ("GITEA_URL", "GITEA_TOKEN"):
        value = os.environ.get(key)
        if not value:
            log.error("%s is not set; the profile's url_rewrites needs it", key)
            return 2
        variables[key] = value

    plan = [
        ("new-project", "S1", f"{WORKSPACE}/new-project", "New project"),
        (
            "existing-project",
            "S2",
            f"{WORKSPACE}/existing-project",
            "Existing project (adopt)",
        ),
    ]
    wanted = {s.strip() for s in args.scenarios.split(",") if s.strip()}

    ai_user: AIUser | None = None
    scenarios: list[ScenarioRun] = []

    for key, sid, project_dir, label in plan:
        if wanted and key not in wanted:
            continue
        run = ScenarioRun(name=label, key=key, sid=sid, project_dir=project_dir)
        # ONE CONTAINER PER SCENARIO. Sharing one container makes the second
        # scenario's install row a measurement of the first scenario's adopter.
        run.dtu_id = f"{run_stamp}-{sid.lower()}"
        scenarios.append(run)

        dtu: DTU | None = None
        try:
            run.ledger_registration = register_infra(
                Path(args.ledger_script), Path(args.ledger_root), run.dtu_id
            )
            log.info(
                "[%s] registered in the infra ledger before launch: %s",
                label,
                run.ledger_registration,
            )

            log.info("[%s] launching %s from %s", label, run.dtu_id, args.profile)
            launch_started = time.monotonic()
            try:
                dtu = await DTU.launch(
                    args.profile,
                    name=run.dtu_id,
                    variables=variables,
                    launch_timeout_s=args.launch_timeout,
                )
            except DTUError as exc:
                run.setup_steps.append(
                    Step(
                        f"{sid}.G1",
                        "This scenario's own container comes up with no Converge in it",
                        FAIL,
                        str(exc),
                        missing="the container never came up, so nothing after it could run",
                    )
                )
                continue

            launch_note = (
                f"launched {dtu.id} from {args.profile} in "
                f"{time.monotonic() - launch_started:.0f}s; every readiness gate "
                f"passed, including `converge-absent` and `queue-cli-absent`"
            )
            g1, before_install = await judge_fresh_container(dtu, sid, launch_note)
            run.setup_steps.append(g1)
            run.setup_steps.extend(
                await setup_scenario_container(dtu, readme, sid, key, project_dir)
            )

            if ai_user is None:
                log.info("preparing the AI user (composes a foundation session; slow once)")
                ai_user = AIUser()
                await ai_user.setup()

            invocation = (HERE / "invocation.md").read_text(encoding="utf-8")
            await run_scenario(
                dtu=dtu,
                ai_user=ai_user,
                run=run,
                scenario_path=HERE / "scenarios" / f"{key}.md",
                invocation=invocation,
                out_dir=out_dir,
                budget_s=args.scenario_budget,
                pane_interval_s=args.pane_interval,
                before_install=before_install,
            )
        except Exception as exc:  # noqa: BLE001 -- always write a RESULT
            log.error("[%s] aborted: %s: %s", label, type(exc).__name__, exc)
            run.setup_steps.append(
                Step(
                    f"{sid}.G0",
                    "This scenario ran to completion",
                    FAIL,
                    f"{type(exc).__name__}: {exc}",
                    missing="the scenario aborted before it could be judged",
                )
            )
        finally:
            if dtu is not None and not args.keep:
                log.info("[%s] destroying %s", label, dtu.id)
                try:
                    await dtu.destroy()
                    log.info("[%s] destroyed %s", label, dtu.id)
                except Exception as exc:  # noqa: BLE001
                    log.error(
                        "DESTROY FAILED for %s: %s -- the ledger row is open, sweep it",
                        dtu.id,
                        exc,
                    )
            elif dtu is not None:
                log.warning("--keep: %s left running; its ledger row is open", dtu.id)

    meta["finished"] = datetime.now(timezone.utc).isoformat(timespec="seconds")

    result_path = Path(args.result or (HERE / "RESULT.md"))
    overall = write_result(result_path, scenarios=scenarios, meta=meta)
    (out_dir / "report.json").write_text(
        json.dumps(
            {
                "meta": meta,
                "overall": overall,
                "scenarios": [
                    {
                        "name": r.name,
                        "dtu_id": r.dtu_id,
                        "verdict": r.verdict,
                        "steps": [
                            {
                                "id": s.id,
                                "what": s.what,
                                "verdict": s.verdict,
                                "missing": s.missing,
                            }
                            for s in r.rows
                        ],
                    }
                    for r in scenarios
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    log.info("RESULT: %s -> %s", overall, result_path)
    return 0 if overall == "GREEN" else 1


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", required=True, help="run output dir (OUTSIDE this repo)")
    p.add_argument("--result", default=None, help="path for RESULT.md")
    p.add_argument("--profile", default=str(HERE / "profiles" / "adopter.yaml"))
    p.add_argument("--name", default=None, help="explicit run id; each scenario's container is <id>-s1, <id>-s2")
    p.add_argument("--scenarios", default="", help="comma list: new-project,existing-project")
    p.add_argument("--scenario-budget", type=float, default=2700.0)
    p.add_argument("--launch-timeout", type=float, default=1800.0)
    p.add_argument(
        "--pane-interval",
        type=float,
        default=30.0,
        help="seconds between pane samples taken THROUGH each scenario",
    )
    p.add_argument("--keep", action="store_true", help="do not destroy the DTUs")
    p.add_argument("--ledger-root", default=str(BUNDLE_ROOT.parent))
    p.add_argument("--ledger-script", default=str(DEFAULT_LEDGER_SCRIPT))
    args = p.parse_args()
    return asyncio.run(amain(args))


if __name__ == "__main__":
    sys.exit(main())
