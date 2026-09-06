#!/usr/bin/env python3
"""The live-work tripwire — LEDGER-FORMAT §2 and §6.3, read against the LIVE queue.

§2 makes a `work` ref REQUIRED on every GAP / VIOLATION row ("a red row without
a filed item is a ledger that lies"), and §6.3 demands that ref be **live**. A
ref that merely EXISTS is not the same as a ref that is still live: a reader who
follows a closed cite lands on finished work and learns nothing about what would
close the row.

WHY THIS IS A MODULE, AND WHY IT DOES NOT READ `docs/work-items.json` FIRST.
The rule was added 2026-09-04 (converge-0gb), the third time it had been
enforced by hand — but it was written against `docs/work-items.json`, a
committed snapshot refreshed by a separate manual command
(`scripts/export-work-items.py`) that nothing in the gate runs. Measured
2026-09-04 (converge-j0u5): the snapshot held **76 items against 202 live**, 28
red rows cited items already resolved, five of the cited ids were ABSENT from
the snapshot — and the rule printed `[OK]`. Absent ids were downgraded to
`[INFO]`, so the refs that had drifted furthest were precisely the ones that
could never fail. A tripwire whose input is refreshed by hand cannot fire.

So the queue is read LIVE, through the same CLI `scripts/export-work-items.py`
uses, and:

- a red row citing a **resolved** item FAILS, by row id and ref;
- a red row citing an id that **does not exist** in the project FAILS too — a
  ref the checker cannot resolve is not a note, it is a ref that has stopped
  meaning anything;
- when the queue is **unreachable** the committed snapshot is a fallback under a
  loud `[WARN]` that names the snapshot's age — and if that snapshot is absent
  or older than 24h the rule reports `[FAIL] live-work tripwire could not be
  evaluated`. **This module never returns OK for a verdict it did not reach
  against live data.**

`docs/work-items.json` and `scripts/export-work-items.py` stay: the documents
kit's rule 9a is a different consumer with a different need (it reads item
prose, not liveness, and deliberately takes a repository-shaped input).

Stdlib only — verify.py runs under `uv run --with pyyaml`, with nothing else
available.
"""

from __future__ import annotations

import json
import re
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path

#: The CLI every read goes through. This module never touches tracker storage.
TRACKER = "amplifier-work-tracker"
#: `amplifier-work-tracker list --help`: "max items to return (default 50, max 500)".
CLI_LIMIT = 500
#: bd's status vocabulary: open / held / blocked / deferred are live. Only one is not.
CLOSED = "resolved"
#: The fallback, and only the fallback.
SNAPSHOT = Path("docs/work-items.json")
#: Past this, a fallback snapshot is too old to be evidence about a live ref.
SNAPSHOT_MAX_AGE_H = 24.0
#: A tracker id: `<project>-<suffix>`, whole string, no prose. The project may
#: itself carry hyphens (`my-project-a1b2`); the suffix never does.
REF_RE = re.compile(r"(?P<project>[A-Za-z0-9][\w.-]*)-(?P<suffix>[A-Za-z0-9]+)")


class LiveQueueUnreachable(RuntimeError):
    """The live queue could not be read — binary missing, server down, partial."""


def project_of(ref: str | None) -> str | None:
    """The project a tracker ref names: bd ids are `<project>-<suffix>`.

    The project name is deliberately NOT configured here. `PINS.md` ("Work
    tracking") records that this ledger cites exactly ONE project and that every
    `work:` ref in `rows.yaml` is a `converge-*` id — so the row being judged
    already names the project it wants judging against. Copying `converge` into
    this file would make a third home for the name, beside
    `scripts/export-work-items.py`'s default and the app's `tracker_project`,
    and a third place for it to drift.

    Returns None for anything that is not a tracker id — a `work:` ref holding
    prose ("see the wave-8 thread") names no project and is failed as malformed
    rather than quietly split at its last hyphen.
    """
    m = REF_RE.fullmatch((ref or "").strip())
    return m.group("project") if m else None


def live_statuses(project: str, *, runner=subprocess.run) -> dict[str, str]:
    """`{id: status}` for every item in `project`, read from the LIVE queue.

    Raises `LiveQueueUnreachable` for every way this can fail to be a complete
    answer — including a truncated page, because a partial queue cannot say
    whether an id is absent, and absence is a verdict here.
    """
    cmd = [TRACKER, "list", "--project", project, "--limit", str(CLI_LIMIT), "--json"]
    printable = " ".join(cmd)
    try:
        proc = runner(cmd, capture_output=True, text=True, timeout=60)
    except FileNotFoundError:
        raise LiveQueueUnreachable(f"{TRACKER} is not on PATH") from None
    except (OSError, subprocess.SubprocessError) as e:
        raise LiveQueueUnreachable(f"`{printable}` did not run: {e}") from e
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip().splitlines()
        raise LiveQueueUnreachable(
            f"`{printable}` exited {proc.returncode}: {detail[-1][:160] if detail else 'no output'}"
        )
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError as e:
        raise LiveQueueUnreachable(f"`{printable}` did not print JSON: {e}") from e
    items = payload.get("items") or []
    if payload.get("truncated"):
        raise LiveQueueUnreachable(
            f"project {project!r} returned {payload.get('returned_count')} of "
            f"{payload.get('total_count')} items — a partial queue cannot say "
            "whether an id is absent"
        )
    if not items:
        raise LiveQueueUnreachable(
            f"project {project!r} returned no items at all — an empty queue is "
            "not something a cite can be judged against"
        )
    return {str(i["id"]): str(i.get("status") or "") for i in items}


def snapshot_statuses(path: Path) -> dict[str, str]:
    """`{id: status}` from the committed export — the fallback's data."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return {str(i["id"]): str(i.get("status") or "") for i in data}


def _git_commit_time(path: Path) -> float | None:
    """When this file's CONTENT last changed in git, or None if git cannot say."""
    try:
        proc = subprocess.run(
            ["git", "log", "-1", "--format=%ct", "--", path.name],
            cwd=str(path.parent or "."),
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    out = proc.stdout.strip()
    if proc.returncode != 0 or not out.isdigit():
        return None
    return float(out)


def snapshot_age_hours(path: Path, now: float | None = None) -> tuple[float, str]:
    """How old the snapshot's content is, in hours, and a stamp naming when.

    mtime alone is not honest: `git checkout` stamps a file with the time of the
    checkout, so in a fresh clone or a worktree — exactly where a stale fallback
    most needs catching — a snapshot exported months ago looks minutes old. The
    age is therefore the OLDER of the file's mtime and its last commit time, and
    the stamp says which one it came from.
    """
    now = time.time() if now is None else now
    stamps = [(path.stat().st_mtime, "mtime")]
    committed = _git_commit_time(path)
    if committed is not None:
        stamps.append((committed, "last commit"))
    when, label = min(stamps)
    stamp = time.strftime("%Y-%m-%dT%H:%M", time.localtime(when))
    return max(0.0, (now - when) / 3600.0), f"{stamp} ({label})"


@dataclass
class Report:
    """What the tripwire saw. `verdict` is one of OK · WARN · FAIL."""

    verdict: str
    summary: str
    detail: list[str] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)
    #: where the verdict came from: "live" · "snapshot" · "none"
    source: str = "none"


def _judge(
    red: list[tuple[str, str | None]],
    statuses: dict[str, str],
    where: str,
    *,
    absent_fails: bool,
) -> tuple[list[str], list[str], list[str]]:
    """Classify each red row against `{id: status}`."""
    detail: list[str] = []
    failures: list[str] = []
    unjudged: list[str] = []
    for row_id, ref in red:
        project = project_of(ref)
        if project is None:
            msg = f"{row_id} cites {ref!r}, which is not a tracker ref (expected <project>-<id>)"
            detail.append(f"  [FAIL] {msg}")
            failures.append(msg)
        elif ref not in statuses:
            if absent_fails:
                msg = f"{row_id} cites {ref}, which does not exist in project {project}"
                detail.append(f"  [FAIL] {msg}")
                failures.append(msg)
            else:
                # Absence from a SNAPSHOT is the snapshot's ignorance, not a
                # verdict — but it is never a pass either.
                msg = f"{row_id} cites {ref}, absent from {where} — UNJUDGED, not passed"
                detail.append(f"  [WARN] {msg}")
                unjudged.append(msg)
        elif statuses[ref] == CLOSED:
            msg = f"{row_id} cites {ref}, which is already resolved"
            detail.append(f"  [FAIL] {msg}")
            failures.append(msg)
    return detail, failures, unjudged


def evaluate(
    red,
    *,
    statuses_for=live_statuses,
    snapshot: Path | str = SNAPSHOT,
    now: float | None = None,
    age_of=snapshot_age_hours,
) -> Report:
    """Judge every red row's `work` ref. `red` is `(row_id, work_ref)` pairs."""
    red = [(rid, ref) for rid, ref in red]
    if not red:
        return Report(
            "OK",
            "no GAP/VIOLATION rows to judge, so none can cite finished work",
            source="none",
        )

    projects = sorted({p for p in (project_of(ref) for _, ref in red) if p})
    statuses: dict[str, str] = {}
    unreachable: str | None = None
    for p in projects:
        try:
            statuses.update(statuses_for(p))
        except LiveQueueUnreachable as e:
            unreachable = str(e)
            break

    if unreachable is None:
        named = ", ".join(projects) or "no project"
        detail, failures, _ = _judge(red, statuses, "the live queue", absent_fails=True)
        if failures:
            return Report(
                "FAIL",
                f"{len(failures)} of {len(red)} GAP/VIOLATION row(s) cite work that is "
                f"finished or unknown ({len(statuses)} items read LIVE from {named})",
                detail,
                failures,
                "live",
            )
        return Report(
            "OK",
            f"no GAP/VIOLATION row cites a resolved or unknown work item "
            f"({len(red)} red rows read against the LIVE queue of {named}: "
            f"{len(statuses)} items)",
            detail,
            [],
            "live",
        )

    # --- the live queue could not be read; the snapshot is a fallback, not a pass ---
    lines = [f"  [WARN] the live queue is UNREACHABLE: {unreachable}"]
    snapshot = Path(snapshot)
    if not snapshot.is_file():
        msg = (
            f"live-work tripwire could not be evaluated: the live queue is unreachable "
            f"({unreachable}) and there is no snapshot at {snapshot} to fall back to"
        )
        return Report("FAIL", msg, lines, [msg], "none")

    hours, stamp = age_of(snapshot, now)
    if hours > SNAPSHOT_MAX_AGE_H:
        msg = (
            f"live-work tripwire could not be evaluated: the live queue is unreachable "
            f"({unreachable}) and the only fallback, {snapshot} of {stamp}, is "
            f"{hours:.1f}h old (limit {SNAPSHOT_MAX_AGE_H:.0f}h) — too stale to say "
            "whether a ref is still live"
        )
        return Report("FAIL", msg, lines, [msg], "snapshot")

    try:
        statuses = snapshot_statuses(snapshot)
    except (OSError, ValueError, KeyError, TypeError) as e:
        msg = (
            f"live-work tripwire could not be evaluated: the live queue is unreachable "
            f"({unreachable}) and the fallback {snapshot} could not be read: {e}"
        )
        return Report("FAIL", msg, lines, [msg], "none")

    lines.append(
        f"  [WARN] falling back to the committed snapshot {snapshot} of {stamp}, "
        f"{hours:.1f}h old — this verdict is a SNAPSHOT's and cannot be trusted "
        "for this rule"
    )
    detail, failures, unjudged = _judge(red, statuses, str(snapshot), absent_fails=False)
    lines += detail
    tail = f"; {len(unjudged)} ref(s) UNJUDGED" if unjudged else ""
    if failures:
        return Report(
            "FAIL",
            f"{len(failures)} of {len(red)} GAP/VIOLATION row(s) cite a resolved item "
            f"even by the stale reckoning of {snapshot}{tail}",
            lines,
            failures,
            "snapshot",
        )
    return Report(
        "WARN",
        f"live-work tripwire NOT evaluated against live data: {len(red)} red rows read "
        f"against {snapshot} ({hours:.1f}h old){tail} — re-run with the tracker reachable",
        lines,
        [],
        "snapshot",
    )
