"""Git facts — the code record, said as evidence rather than as claims.

Nothing here is a worker session's account of itself. It is what the repository
actually contains (surface.v1 clause 8).
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from . import Reading


@dataclass(frozen=True)
class Commit:
    sha: str
    when: str
    author: str
    subject: str


@dataclass(frozen=True)
class GitFacts:
    branch: str = ""
    clean: bool = True
    changed_files: int = 0
    recent: tuple[Commit, ...] = field(default_factory=tuple)

    @property
    def sentence(self) -> str:
        """The code record, in words rather than in git's words."""
        if self.clean:
            return "Everything here is saved into the code record."
        if self.changed_files == 1:
            return "One change here is not saved into the code record yet."
        return f"{self.changed_files} changes here are not saved into the code record yet."

    @property
    def detail(self) -> str:
        return f"branch {self.branch}; {self.changed_files} path(s) dirty"


def _git(repo: Path, *args: str) -> tuple[bool, str]:
    try:
        result = subprocess.run(
            ["git", *args], cwd=repo, capture_output=True, text=True, timeout=15
        )
    except (OSError, subprocess.SubprocessError):
        return False, ""
    return result.returncode == 0, result.stdout


def read_git(repo: Path, limit: int = 8) -> Reading[GitFacts]:
    repo = Path(repo)
    ok, branch = _git(repo, "rev-parse", "--abbrev-ref", "HEAD")
    if not ok:
        return Reading.absent(
            GitFacts(),
            "This folder keeps no code record, so there is nothing to show from it.",
            detail="not a git repository",
        )
    ok, status = _git(repo, "status", "--porcelain")
    changed = len([line for line in status.splitlines() if line.strip()]) if ok else 0

    ok, log = _git(repo, "log", f"-{limit}", "--format=%h%x1f%ad%x1f%an%x1f%s", "--date=format:%-d %b %H:%M")
    commits: list[Commit] = []
    if ok:
        for line in log.splitlines():
            parts = line.split("\x1f")
            if len(parts) == 4:
                commits.append(Commit(sha=parts[0], when=parts[1], author=parts[2], subject=parts[3]))

    return Reading(
        GitFacts(
            branch=branch.strip(),
            clean=changed == 0,
            changed_files=changed,
            recent=tuple(commits),
        )
    )
