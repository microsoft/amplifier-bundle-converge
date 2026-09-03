"""The lanes — worker sessions at work, and whether they are still alive.

A lane is one worker session in its own copy of the code. This reader answers
two questions the steward actually asks: how many are running against how many
were intended, and is any of them quietly dead.

Liveness is said in words (documents.v1 clause 10): *Working · Quiet · Silent —
may have died*. Never a spinner, never a percentage.
"""

from __future__ import annotations

import csv
import json
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path

from ..words import UNKNOWN, surface_word
from . import Reading

#: How long a lane may go without writing before we stop calling it Working.
QUIET_AFTER_SECONDS = 8 * 60
SILENT_AFTER_SECONDS = 30 * 60


@dataclass(frozen=True)
class Evidence:
    label: str
    detail: str


@dataclass(frozen=True)
class Lane:
    name: str
    branch: str
    worktree: str
    launched_at: str
    log_path: str
    seconds_since_write: float | None
    finished: bool
    blocked: bool
    outcome: str
    summary: str
    commits: int | None = None
    evidence: tuple[Evidence, ...] = field(default_factory=tuple)

    @property
    def liveness(self) -> str:
        """State in words, every one of them read from the vocabulary map."""
        if self.finished:
            return surface_word("done")
        if self.blocked:
            return surface_word("stuck")
        if self.seconds_since_write is None:
            return UNKNOWN
        if self.seconds_since_write < QUIET_AFTER_SECONDS:
            return surface_word("working")
        if self.seconds_since_write < SILENT_AFTER_SECONDS:
            return f"{surface_word('quiet')} {_minutes(self.seconds_since_write)}"
        return surface_word("silent")

    @property
    def running(self) -> bool:
        return not self.finished and not self.blocked

    @property
    def needs_a_look(self) -> bool:
        return (
            self.blocked
            or (self.seconds_since_write is not None and self.seconds_since_write >= SILENT_AFTER_SECONDS and not self.finished)
        )


@dataclass(frozen=True)
class Board:
    lanes: tuple[Lane, ...]
    width_target: int | None
    batch_dir: str

    @property
    def running(self) -> int:
        return sum(1 for lane in self.lanes if lane.running)

    @property
    def gauge(self) -> str:
        if self.width_target is None:
            return f"{self.running} running"
        return f"{self.running} of {self.width_target} running"

    @property
    def short_by(self) -> int:
        if self.width_target is None:
            return 0
        return max(0, self.width_target - self.running)


def _minutes(seconds: float) -> str:
    minutes = int(seconds // 60)
    if minutes < 60:
        return f"{minutes}m"
    hours, rest = divmod(minutes, 60)
    return f"{hours}h {rest}m" if rest else f"{hours}h"


def default_batch_dir(repo: Path) -> Path | None:
    """Guess the lanes directory: the repo usually sits two levels inside it."""
    repo = Path(repo).resolve()
    for parent in list(repo.parents)[:4]:
        if (parent / "manifest.tsv").is_file() and (parent / "lanes").is_dir():
            return parent
    return None


def _commits_on(worktree: Path, branch: str) -> int | None:
    if not worktree.is_dir():
        return None
    try:
        result = subprocess.run(
            ["git", "rev-list", "--count", f"main..{branch}"],
            cwd=worktree,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    try:
        return int(result.stdout.strip())
    except ValueError:
        return None


def _last_write(paths: list[Path]) -> float | None:
    stamps = [p.stat().st_mtime for p in paths if p.exists()]
    if not stamps:
        return None
    return max(0.0, time.time() - max(stamps))


def read_board(repo: Path, batch_dir: Path | None = None) -> Reading[Board]:
    repo = Path(repo)
    directory = Path(batch_dir) if batch_dir else default_batch_dir(repo)
    if directory is None:
        return Reading.absent(
            Board(lanes=(), width_target=None, batch_dir=""),
            "No lanes directory is set up beside this project, so there is nothing to run lanes from yet. "
            "This does not mean zero lanes are running — it means there is no board to read.",
        )
    manifest = directory / "manifest.tsv"
    if not manifest.is_file():
        return Reading.absent(
            Board(lanes=(), width_target=None, batch_dir=str(directory)),
            f"There is a lanes directory at {directory} but no manifest in it, so no lane can be listed.",
        )

    width_target: int | None = None
    width_file = directory / ".width"
    if width_file.is_file():
        try:
            width_target = int(width_file.read_text(encoding="utf-8").strip())
        except (OSError, ValueError):
            width_target = None

    lanes: list[Lane] = []
    with manifest.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            name = (row.get("lane") or "").strip()
            if not name:
                continue
            lane_dir = directory / "lanes" / name
            done_path = lane_dir / "DONE.json"
            blocked_path = lane_dir / "BLOCKED.md"
            log_path = Path(row.get("log") or (lane_dir / "lane.log"))
            worktree = Path(row.get("worktree") or "")
            branch = (row.get("branch") or "").strip()

            outcome = ""
            summary = ""
            finished = done_path.is_file()
            if finished:
                try:
                    payload = json.loads(done_path.read_text(encoding="utf-8"))
                    outcome = str(payload.get("status", "done"))
                    summary = str(payload.get("summary", ""))
                except (OSError, json.JSONDecodeError):
                    outcome = "done"
                    summary = "Its own note could not be read."

            blocked = blocked_path.is_file()
            if blocked and not summary:
                try:
                    summary = blocked_path.read_text(encoding="utf-8").strip().splitlines()[0]
                except (OSError, IndexError):
                    summary = "It stopped and said why in its own note."

            commits = _commits_on(worktree, branch) if branch else None
            evidence: list[Evidence] = []
            if commits is not None:
                evidence.append(
                    Evidence("Commits", f"{commits} on {branch}" if commits else f"nothing committed on {branch} yet")
                )
            if log_path.exists():
                evidence.append(Evidence("Log", f"{log_path.stat().st_size:,} bytes written"))
            if finished:
                evidence.append(Evidence("Its own note", outcome or "done"))

            lanes.append(
                Lane(
                    name=name,
                    branch=branch,
                    worktree=str(worktree),
                    launched_at=(row.get("launched_at") or "").strip(),
                    log_path=str(log_path),
                    seconds_since_write=_last_write([log_path, done_path, blocked_path]),
                    finished=finished,
                    blocked=blocked,
                    outcome=outcome,
                    summary=summary,
                    commits=commits,
                    evidence=tuple(evidence),
                )
            )

    return Reading(Board(lanes=tuple(lanes), width_target=width_target, batch_dir=str(directory)))
