"""The work queue, read through the work-tracker command line.

The page holds no queue of its own. If the work-tracker command is not
installed, or the project is unknown to it, the page says exactly that — it
never shows a zero that reads like "there is nothing to do".
"""

from __future__ import annotations

import html
import json
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from ..home import cache_dir, ensure
from . import Reading

CLI = "amplifier-work-tracker"

#: Plain state words (documents.v1 clause 10), mapped from the queue's own.
STATE_WORDS = {
    "open": "Truly ready",
    "held": "Working",
    "blocked": "Waiting on you",
    "deferred": "Waiting on you",
    "resolved": "Done",
    "intake": "Waiting on you",
}


@dataclass(frozen=True)
class WorkItem:
    id: str
    title: str
    status: str
    holder: str
    resolution: str

    @property
    def state_word(self) -> str:
        return STATE_WORDS.get(self.status, "Can't check")

    @property
    def truly_ready(self) -> bool:
        return self.status == "open"

    @property
    def waiting_on_you(self) -> bool:
        return self.status in ("blocked", "deferred", "intake")


@dataclass(frozen=True)
class QueueSummary:
    project: str
    total: int = 0
    ready: int = 0
    held: int = 0
    blocked: int = 0
    deferred: int = 0
    resolved: int = 0
    resolved_24h: int = 0
    oldest_unclaimed_age_seconds: float = 0.0


def _missing(project: str) -> str:
    return (
        f"The work queue cannot be read: `{CLI}` is not installed on this machine. "
        "Nothing here says the queue is empty — only that we cannot see it."
    )


def _run(args: list[str], repo: Path) -> tuple[bool, str, str]:
    if shutil.which(CLI) is None:
        return False, "", "not installed"
    try:
        result = subprocess.run(
            [CLI, *args], cwd=repo, capture_output=True, text=True, timeout=30
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return False, "", str(exc)
    if result.returncode != 0:
        return False, "", (result.stderr or result.stdout or "the command failed").strip()
    return True, result.stdout, ""


def read_items(repo: Path, project: str) -> Reading[list[WorkItem]]:
    ok, out, err = _run(["list", "--project", project, "--json", "--limit", "200"], Path(repo))
    if not ok:
        if err == "not installed":
            return Reading.absent([], _missing(project))
        return Reading.absent(
            [],
            f"The work queue for “{project}” could not be read just now, so nothing here says "
            "what is ready or what is being worked on.",
            detail=err.strip(),
        )
    try:
        payload = json.loads(out or "{}")
    except json.JSONDecodeError:
        return Reading.absent([], "The work queue answered with something we could not read.")
    items = [
        WorkItem(
            id=row.get("id", ""),
            title=html.unescape(row.get("title", "")),
            status=row.get("status", ""),
            holder=row.get("holder") or "",
            resolution=row.get("resolution") or "",
        )
        for row in payload.get("items", [])
    ]
    return Reading(items)


def read_summary(repo: Path, project: str) -> Reading[QueueSummary]:
    ok, out, err = _run(["status", "--project", project, "--json"], Path(repo))
    if not ok:
        if err == "not installed":
            return Reading.absent(QueueSummary(project=project), _missing(project))
        return Reading.absent(
            QueueSummary(project=project),
            f"The queue for “{project}” could not be summarised just now.",
            detail=err.strip(),
        )
    try:
        payload = json.loads(out or "{}")
    except json.JSONDecodeError:
        return Reading.absent(QueueSummary(project=project), "The queue answered with something we could not read.")
    return Reading(
        QueueSummary(
            project=payload.get("project", project),
            total=int(payload.get("total", 0)),
            ready=int(payload.get("ready", 0)),
            held=int(payload.get("held", 0)),
            blocked=int(payload.get("blocked", 0)),
            deferred=int(payload.get("deferred", 0)),
            resolved=int(payload.get("resolved", 0)),
            resolved_24h=int(payload.get("resolved_24h", 0)),
            oldest_unclaimed_age_seconds=float(payload.get("oldest_unclaimed_age_seconds", 0) or 0),
        )
    )


def read_managers(repo: Path, timeout: float = 12.0) -> Reading[list[QueueSummary]]:
    """Every manager session you run — one per project the queue knows about.

    This is the answer to a measured failure: one incident hand-carried into
    four sessions in fourteen minutes. Seeing them all in one place is the
    point, so a slow answer is cached rather than dropped.
    """
    repo = Path(repo)
    cached = _cache_read(repo, "managers.json")
    if shutil.which(CLI) is None:
        if cached is not None:
            return Reading(
                _managers_from(cached["payload"]),
                available=True,
                note=f"`{CLI}` is not installed now; this is what it last said, on {cached['at']}.",
            )
        return Reading.absent([], _missing(""))

    try:
        result = subprocess.run(
            [CLI, "instances", "--json"], cwd=repo, capture_output=True, text=True, timeout=timeout
        )
        payload = json.loads(result.stdout or "[]") if result.returncode == 0 else None
    except subprocess.TimeoutExpired:
        payload = None
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError):
        payload = None

    if payload is None:
        if cached is not None:
            return Reading(
                _managers_from(cached["payload"]),
                available=True,
                note=f"The full list of manager sessions took too long to fetch; this is what it last said, on {cached['at']}.",
            )
        return Reading.absent(
            [],
            "The list of your other manager sessions took too long to fetch. "
            "This says nothing about whether they are running — only that we did not wait.",
        )

    _cache_write(repo, "managers.json", payload)
    return Reading(_managers_from(payload))


def _managers_from(payload: object) -> list[QueueSummary]:
    rows = payload if isinstance(payload, list) else []
    out = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        out.append(
            QueueSummary(
                project=row.get("project", ""),
                total=int(row.get("total", 0)),
                ready=int(row.get("ready", 0)),
                held=int(row.get("held", 0)),
                blocked=int(row.get("blocked", 0)),
                deferred=int(row.get("deferred", 0)),
                resolved=int(row.get("resolved", 0)),
                resolved_24h=int(row.get("resolved_24h", 0)),
                oldest_unclaimed_age_seconds=float(row.get("oldest_unclaimed_age_seconds", 0) or 0),
            )
        )
    return out


def _cache_read(repo: Path, name: str) -> dict | None:
    path = cache_dir(repo) / name
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _cache_write(repo: Path, name: str, payload: object) -> None:
    try:
        path = ensure(cache_dir(repo)) / name
        path.write_text(
            json.dumps(
                {"at": datetime.now(timezone.utc).strftime("%-d %B at %H:%M UTC"), "payload": payload},
                indent=2,
            ),
            encoding="utf-8",
        )
    except OSError:
        pass
