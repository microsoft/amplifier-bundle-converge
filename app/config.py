"""What this app is watching, and where.

One TOML file names the managers: the batch directory a manager runs in, the
repositories it steers, the tracker project it files against, and the explicit
tmux socket its lanes live on. Nothing is guessed from the ambient environment
— an ambient `$TMUX` is never consulted, because the socket a lane runs on and
the socket this process happens to sit in are different facts.

When the file is absent the app discovers managers rather than showing an empty
page: every `~/dev/hw-*/HIGHWAY.md` is a batch, and its repositories come from
that batch's own `manifest.tsv`.
"""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_CONFIG_PATH = Path.home() / ".amplifier" / "converge-app.toml"
DEFAULT_TMUX_SOCKET = "hw"


@dataclass(frozen=True)
class ManagerConfig:
    """One manager session: the batch it runs, the repos it steers."""

    id: str
    name: str
    batch_dir: Path | None = None
    repos: tuple[Path, ...] = ()
    tracker_project: str = ""
    tmux_socket: str = DEFAULT_TMUX_SOCKET
    manager_tmux: str = ""

    @property
    def repo(self) -> Path | None:
        """The first repository — the one a doc request defaults to."""
        return self.repos[0] if self.repos else None


@dataclass(frozen=True)
class AppConfig:
    """Every manager this app can show, and where the answer came from."""

    managers: tuple[ManagerConfig, ...] = ()
    source: str = ""
    #: Plain sentence when the configured file was not there. Empty when it was.
    note: str = ""
    discovered: bool = False

    def manager(self, mid: str) -> ManagerConfig | None:
        for one in self.managers:
            if one.id == mid:
                return one
        return None


def _as_path(value: object) -> Path | None:
    if not isinstance(value, str) or not value.strip():
        return None
    return Path(os.path.expanduser(value.strip()))


def _manager_from_table(table: dict, index: int) -> ManagerConfig | None:
    mid = str(table.get("id") or "").strip()
    batch = _as_path(table.get("batch_dir"))
    if not mid:
        mid = batch.name if batch else f"manager-{index}"
    repos = tuple(p for p in (_as_path(r) for r in table.get("repos") or []) if p is not None)
    return ManagerConfig(
        id=mid,
        name=str(table.get("name") or mid).strip() or mid,
        batch_dir=batch,
        repos=repos,
        tracker_project=str(table.get("tracker_project") or "").strip(),
        tmux_socket=str(table.get("tmux_socket") or DEFAULT_TMUX_SOCKET).strip() or DEFAULT_TMUX_SOCKET,
        manager_tmux=str(table.get("manager_tmux") or "").strip(),
    )


def _repos_from_manifest(batch_dir: Path) -> tuple[Path, ...]:
    """Every distinct repository the batch's lanes are working in.

    A lane's worktree is `<batch>/lanes/<lane>/<repo-name>`; the repository it
    belongs to is that worktree's original checkout, which the manifest does not
    name directly. What the manifest does give is the repo NAME, which is enough
    to find the original beside the other checkouts under `~/dev`.
    """
    manifest = batch_dir / "manifest.tsv"
    if not manifest.is_file():
        return ()
    names: list[str] = []
    try:
        lines = manifest.read_text(encoding="utf-8").splitlines()
    except OSError:
        return ()
    for line in lines[1:]:
        parts = line.split("\t")
        if len(parts) < 2 or not parts[1].strip():
            continue
        name = Path(parts[1].strip()).name
        if name and name not in names:
            names.append(name)
    found: list[Path] = []
    dev = Path.home() / "dev"
    for name in names:
        for candidate in sorted(dev.glob(f"*/{name}")) + sorted(dev.glob(name)):
            if (candidate / ".git").exists() and candidate not in found:
                found.append(candidate)
                break
    return tuple(found)


def discover(home: Path | None = None) -> tuple[ManagerConfig, ...]:
    """Every `~/dev/hw-*/HIGHWAY.md` as a manager, repos from its manifest."""
    root = (home or Path.home()) / "dev"
    managers: list[ManagerConfig] = []
    for highway in sorted(root.glob("hw-*/HIGHWAY.md")):
        batch = highway.parent
        mid = batch.name.removeprefix("hw-") or batch.name
        managers.append(
            ManagerConfig(
                id=mid,
                name=mid.replace("-", " ").title(),
                batch_dir=batch,
                repos=_repos_from_manifest(batch),
                tmux_socket=DEFAULT_TMUX_SOCKET,
            )
        )
    return tuple(managers)


def load(path: Path | None = None) -> AppConfig:
    """Read the config file, or discover managers when it is not there."""
    path = Path(path) if path else DEFAULT_CONFIG_PATH
    if not path.is_file():
        found = discover()
        return AppConfig(
            managers=found,
            source=f"discovered from {Path.home() / 'dev'}/hw-*/HIGHWAY.md",
            note=f"No config file at {path}; every hw-* batch under ~/dev is shown instead.",
            discovered=True,
        )
    with path.open("rb") as handle:
        table = tomllib.load(handle)
    managers = []
    for index, one in enumerate(table.get("managers") or []):
        made = _manager_from_table(one, index)
        if made is not None:
            managers.append(made)
    return AppConfig(managers=tuple(managers), source=str(path))


__all__ = [
    "AppConfig",
    "ManagerConfig",
    "DEFAULT_CONFIG_PATH",
    "DEFAULT_TMUX_SOCKET",
    "discover",
    "load",
]
