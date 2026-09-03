"""Where the page keeps the two things it is allowed to remember.

The page owns no data (surface.v1 clause 4). It is allowed exactly two
exceptions, and both live OUTSIDE the project so they can never be mistaken
for the project's own truth:

- a **last-read marker** per document, so "what changed since you last read
  this" has something to compare against;
- a **cache** of expensive reads, which is disposable by definition.

Everything else on the page is read live from the repository, git, the work
queue, or the lanes directory.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

#: The two directory names this package is permitted to own, and nothing else.
OWNED_SUBDIRS = ("last-read", "cache")


def app_home() -> Path:
    """The out-of-repo directory holding the last-read markers and the cache."""
    override = os.environ.get("AMPLIFIER_CONVERGE_HOME")
    if override:
        return Path(override).expanduser()
    return Path.home() / ".amplifier" / "converge"


def repo_key(repo: Path) -> str:
    """A short, stable name for one project's corner of the app home."""
    resolved = str(Path(repo).resolve())
    digest = hashlib.sha256(resolved.encode("utf-8")).hexdigest()[:12]
    return f"{Path(resolved).name}-{digest}"


def last_read_dir(repo: Path) -> Path:
    return app_home() / "last-read" / repo_key(repo)


def cache_dir(repo: Path) -> Path:
    return app_home() / "cache" / repo_key(repo)


def ensure(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path
