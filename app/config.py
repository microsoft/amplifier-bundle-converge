"""What this app is watching, and where.

Managers reach this app two ways, and the difference matters.

**A manager registers itself.** On every wake a manager session writes
`<workspace>/.converge/<manager-id>/registration.toml` — its name, its steward,
its workspace root, the repositories it steers with their default branches, its
plan record, its tmux socket and session, its work queue, and the time it was
last awake. This app scans every workspace root it is told about and reads what
it finds. Nothing is edited by hand for a manager to appear, which is the whole
point: `experience.v1` Core 2 says Home is the list of manager sessions you run,
and a session that only appears after somebody edits a file is not that list.
An existing session appears on its NEXT wake, because the mode writes the file
unconditionally rather than only when it is missing.

**A person names one in the config file.** One `[[managers]]` block per manager
session, naming its batch directory, repositories, tracker project, explicit
tmux socket, and the `steward` whose word counts on it. A hand-written block
still wins over a registration of the same id — a person's answer outranks a
process's — but it takes the registration's last-seen time, because when the
session was last awake is a fact only the session has.

Nothing is guessed from the ambient environment — an ambient `$TMUX` is never
consulted, because the socket a lane runs on and the socket this process
happens to sit in are different facts, and no `steward` is inferred from
whoever is signed in, because who may answer and who is looking are different
facts too.

When the config file is absent the app also discovers managers the old way
rather than showing an empty page: every `~/dev/hw-*/HIGHWAY.md` is a batch, and
its repositories come from that batch's own `manifest.tsv`. A discovered manager
names no steward: it was never registered, so there is nobody to name.
"""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, replace
from pathlib import Path

DEFAULT_CONFIG_PATH = Path.home() / ".amplifier" / "converge-app.toml"
DEFAULT_TMUX_SOCKET = "hw"

#: The directory a manager session hangs its whole operation from, under the
#: workspace root — `modes/converge-manager.md` clause 5.
CONVERGE_DIR = ".converge"

#: What a manager session writes there on every wake.
REGISTRATION_NAME = "registration.toml"

#: Extra workspace roots to scan, `os.pathsep`-separated, for a host whose
#: workspaces do not all sit beside this checkout.
WORKSPACES_ENV = "CONVERGE_WORKSPACES"


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
    #: Whose word counts on this session, settled here at registration.
    #: `experience-collaboration.v1` Core 8: it is a fact about the registered
    #: session, never an inference from whoever happens to be signed in. Empty
    #: when the block does not say — an unnamed steward is a registration that
    #: has not been finished, and guessing one is exactly what Core 8 forbids.
    steward: str = ""
    #: The workspace root the session runs from, as its registration named it.
    workspace: Path | None = None
    #: The plan record — the operating picture the session rewrites each cycle.
    plan_record: Path | None = None
    #: `(repo path, default branch)` for each repository the session steers, as
    #: the registration recorded it. Kept beside `repos` rather than inside it
    #: so a hand-written block, which names paths only, still reads.
    repo_branches: tuple[tuple[str, str], ...] = ()
    #: When the session was last awake, ISO-8601. Empty when nothing has ever
    #: registered this manager — which is a different silence from a stale
    #: heartbeat and is never shown as one.
    last_seen: str = ""
    #: The registration file this was read from, when there was one.
    registration: Path | None = None
    #: One plain sentence saying where this manager came from, for the fold on
    #: Home. Written here because here is where the answer is known.
    origin: str = ""

    @property
    def repo(self) -> Path | None:
        """The first repository — the one a doc request defaults to."""
        return self.repos[0] if self.repos else None

    def branch_of(self, repo: Path | str) -> str:
        """The default branch recorded for one repository, or an empty string."""
        wanted = str(repo)
        for path, branch in self.repo_branches:
            if path == wanted:
                return branch
        return ""

    def console_target(self) -> tuple[str, str] | None:
        """This manager's own console -- (socket, session) -- or None.

        `manager_tmux` is written one of two shapes, and both are legal
        forever (converge-c6cv):

        * a bare session name -- the ordinary case, one socket for a
          manager's worker lanes AND its own console -- which is read
          against THIS manager's own `tmux_socket`;
        * the combined `socket:session` form, for when the manager's own
          console runs on a DIFFERENT socket than its lanes (`--manager-tmux`
          in `scripts/register-manager.py` accepts either verbatim).

        Parsed on the FIRST colon only, exactly as the client parses the
        same string in `state.js`'s `normalizeTmux` -- so a registration and
        the browser reading it can never disagree about what one `manager_tmux`
        value means. An empty result (missing socket or session after a
        colon, or no `manager_tmux` recorded at all) is None, matching
        nothing -- an unfinished registration is refused, never treated as
        "anyone may act".
        """
        raw = (self.manager_tmux or "").strip()
        if not raw:
            return None
        if ":" in raw:
            socket, _, session = raw.partition(":")
            socket, session = socket.strip(), session.strip()
        else:
            socket, session = self.tmux_socket, raw
        if not socket or not session:
            return None
        return (socket, session)


@dataclass(frozen=True)
class AppConfig:
    """Every manager this app can show, and where the answer came from."""

    managers: tuple[ManagerConfig, ...] = ()
    source: str = ""
    #: Plain sentence when the configured file was not there. Empty when it was.
    note: str = ""
    discovered: bool = False
    #: Every workspace root scanned for registrations, in the order scanned.
    workspaces: tuple[Path, ...] = ()

    def manager(self, mid: str) -> ManagerConfig | None:
        for one in self.managers:
            if one.id == mid:
                return one
        return None

    def manager_for_tmux(self, tmux_socket: str, session: str) -> ManagerConfig | None:
        """The manager whose own console this (socket, session) pair names,
        or None.

        Matched against each manager's resolved `console_target()` -- a
        manager's OWN console, the only tmux target the app's UI ever opens
        for typing (`console.js` only sets `writable: true` in the manager
        context, never for a lane) -- rather than against `tmux_socket` and
        `manager_tmux` compared as separate, literal fields. That literal
        comparison assumed a manager's own console always ran on the SAME
        socket as its worker lanes; a registration recording the combined
        `socket:session` form for a manager on a DIFFERENT socket then
        matched nothing here even though the read side (`console.js`'s
        `normalizeTmux`) resolved it correctly, so a registered steward
        could watch their own session but not type into it (403 "no
        registered manager owns this tmux session") -- converge-c6cv.

        `console_target()` returning None (no `manager_tmux` recorded yet)
        never matches, so an unfinished registration is refused the same as
        an unrecognized session, never treated as "anyone may act" -- the
        same fail-closed rule `steward` follows. Nothing here reads the
        ambient `$TMUX`, and nothing here infers permission from a session
        NAME alone -- both socket and session of the resolved target must
        match what was asked for.
        """
        if not session:
            return None
        wanted = (tmux_socket, session)
        for one in self.managers:
            if one.console_target() == wanted:
                return one
        return None


def _as_path(value: object) -> Path | None:
    if not isinstance(value, str) or not value.strip():
        return None
    return Path(os.path.expanduser(value.strip()))


def _repos_of(value: object) -> tuple[tuple[Path, ...], tuple[tuple[str, str], ...]]:
    """Repositories in either shape, with whatever branches were recorded.

    A hand-written block writes ``repos = ["/a", "/b"]`` and knows no branches.
    A registration writes ``[[repos]]`` tables carrying ``path`` and
    ``default_branch``, because a manager session knows both. Both are read
    here so nothing downstream has to ask which kind of file it came from.
    """
    paths: list[Path] = []
    branches: list[tuple[str, str]] = []
    for one in value or []:
        if isinstance(one, dict):
            path = _as_path(one.get("path"))
            branch = str(one.get("default_branch") or "").strip()
        else:
            path, branch = _as_path(one), ""
        if path is None:
            continue
        paths.append(path)
        if branch:
            branches.append((str(path), branch))
    return tuple(paths), tuple(branches)


def _manager_from_table(table: dict, index: int) -> ManagerConfig | None:
    mid = str(table.get("id") or "").strip()
    batch = _as_path(table.get("batch_dir"))
    if not mid:
        mid = batch.name if batch else f"manager-{index}"
    repos, branches = _repos_of(table.get("repos"))
    return ManagerConfig(
        id=mid,
        name=str(table.get("name") or mid).strip() or mid,
        batch_dir=batch,
        repos=repos,
        tracker_project=str(table.get("tracker_project") or "").strip(),
        tmux_socket=str(table.get("tmux_socket") or DEFAULT_TMUX_SOCKET).strip() or DEFAULT_TMUX_SOCKET,
        manager_tmux=str(table.get("manager_tmux") or "").strip(),
        steward=str(table.get("steward") or "").strip(),
        workspace=_as_path(table.get("workspace")),
        plan_record=_as_path(table.get("plan_record")),
        repo_branches=branches,
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


# --------------------------------------------------------------------------
# registrations: what a manager session writes about itself
# --------------------------------------------------------------------------


def app_repo_root() -> Path:
    """This app's own repository root — the thing the default root hangs off."""
    return Path(__file__).resolve().parents[1]


#: The process's own working directory, captured the moment this module is
#: first imported — before `tls.ensure()`, uvicorn, or anything else run by
#: `app.serve.main()` has any chance to `chdir`. This is the one honest
#: answer to "where was the caller actually standing", captured once here
#: rather than read fresh with `Path.cwd()` on every request, so a later,
#: unrelated `chdir` elsewhere in the process can never change which
#: workspace an installed wheel discovers registrations under.
_CALLER_CWD_AT_IMPORT = Path.cwd()


def _is_source_checkout(root: Path) -> bool:
    """True when `root` is this project's own source checkout — the layout
    `default_workspace_roots` was originally written for, where the app is
    one repository sitting beside the others in the workspace it watches.

    False for an installed wheel: `pip install`/`uv pip install` puts `app/`
    and `amplifier_converge/` side by side under `site-packages`, with no
    `pyproject.toml` or `scripts/run-app.sh` anywhere near them. `parents[1]`
    there resolves to `site-packages` itself (or the Amplifier bundle cache a
    wheel was built from and installed out of) — a real directory, so the
    old, unconditional default silently "worked" by scanning
    `<site-packages-parent>/.converge/*` for registrations, which is never
    where a reader's actual project lives.
    """
    return (root / "pyproject.toml").is_file() and (root / "scripts" / "run-app.sh").is_file()


def default_workspace_roots() -> tuple[Path, ...]:
    """Where this app looks for manager registrations, with no config file
    and no `CONVERGE_WORKSPACES` naming anything.

    A source checkout: the parent of this app's own repository — a workspace
    holds its repositories side by side, so the checkout this module runs
    from sits one level below the workspace root, and that is the correct
    default for the ordinary case.

    An installed wheel (or any layout with no adjacent checkout): the
    caller's own working directory at process start
    (`_CALLER_CWD_AT_IMPORT`) — never `site-packages`, never the Amplifier
    bundle cache the wheel happened to be built from, and never a broad scan
    of `$HOME`. A reader who ran `amplifier-converge start` from their own
    project's workspace is standing in the one directory this can honestly
    call "theirs"; an explicit `workspaces =` in `converge-app.toml`, or
    `$CONVERGE_WORKSPACES`, still wins over this default either way (see
    `load()`).
    """
    root = app_repo_root()
    if _is_source_checkout(root):
        return (root.parent,)
    return (_CALLER_CWD_AT_IMPORT,)


def env_workspace_roots(value: str | None = None) -> tuple[Path, ...]:
    """Whatever `CONVERGE_WORKSPACES` names, `os.pathsep`-separated."""
    raw = os.environ.get(WORKSPACES_ENV, "") if value is None else value
    found: list[Path] = []
    for piece in (raw or "").split(os.pathsep):
        path = _as_path(piece)
        if path is not None and path not in found:
            found.append(path)
    return tuple(found)


def read_registration(path: Path) -> ManagerConfig | None:
    """One `registration.toml`, or None when it cannot be read at all.

    A registration a manager session is halfway through writing, or one whose
    id line is missing, is skipped rather than shown as a manager with no name.
    The write side makes that window as small as it can (it renames a finished
    file into place), and this side is the belt to that brace.
    """
    path = Path(path)
    try:
        with path.open("rb") as handle:
            table = tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError):
        return None
    if not isinstance(table, dict):
        return None
    mid = str(table.get("id") or "").strip()
    if not mid:
        return None
    made = _manager_from_table(table, 0)
    if made is None:
        return None
    batch = made.batch_dir or path.parent
    workspace = made.workspace
    if workspace is None:
        # `<workspace>/.converge/<manager-id>/registration.toml` — two levels
        # up from the directory the file sits in.
        parent = path.parent.parent
        workspace = parent.parent if parent.name == CONVERGE_DIR else None
    return replace(
        made,
        batch_dir=batch,
        workspace=workspace,
        last_seen=str(table.get("last_seen") or "").strip(),
        registration=path,
        origin=f"registered by the manager session itself, at {path}",
    )


def discover_registrations(roots: tuple[Path, ...]) -> tuple[ManagerConfig, ...]:
    """Every `<root>/.converge/*/registration.toml`, in the order the roots came.

    The first registration for an id wins, so the order of the roots is the
    order of preference — and it is the caller's order, never a sort.
    """
    found: list[ManagerConfig] = []
    seen: set[str] = set()
    for root in roots:
        base = Path(root) / CONVERGE_DIR
        if not base.is_dir():
            continue
        for path in sorted(base.glob(f"*/{REGISTRATION_NAME}")):
            one = read_registration(path)
            if one is None or one.id in seen:
                continue
            seen.add(one.id)
            found.append(one)
    return tuple(found)


def merge(hand_written: tuple[ManagerConfig, ...], registered: tuple[ManagerConfig, ...]) -> tuple[ManagerConfig, ...]:
    """Hand-written blocks first and unchanged, registrations after.

    On a conflict the hand-written block wins — a person's answer outranks a
    process's — and appears **once**. What it takes from the registration is
    the last-seen time and the registration's own path, because when a session
    was last awake, and where it said so, are facts only the session has. It
    also takes the workspace root and the plan record where the block did not
    name them: filling a hole is not overruling an answer.
    """
    by_id = {one.id: one for one in registered}
    made: list[ManagerConfig] = []
    taken: set[str] = set()
    for one in hand_written:
        found = by_id.get(one.id)
        if found is None:
            made.append(replace(one, origin=one.origin or "named by hand in this app's config file"))
            continue
        taken.add(one.id)
        made.append(
            replace(
                one,
                last_seen=found.last_seen,
                registration=found.registration,
                workspace=one.workspace or found.workspace,
                plan_record=one.plan_record or found.plan_record,
                repo_branches=one.repo_branches or found.repo_branches,
                origin=(
                    "named by hand in this app's config file, and registering "
                    f"itself at {found.registration}"
                ),
            )
        )
    for one in registered:
        if one.id not in taken:
            made.append(one)
    return tuple(made)


def load(path: Path | None = None) -> AppConfig:
    """Every manager this app can show: registered, hand-written, or discovered.

    Registrations are read whether or not a config file exists, because a
    manager session that has registered itself has done everything it was asked
    to do and should not need a file edited on its behalf.
    """
    path = Path(path) if path else DEFAULT_CONFIG_PATH
    table: dict = {}
    have_file = path.is_file()
    if have_file:
        try:
            with path.open("rb") as handle:
                table = tomllib.load(handle)
        except (OSError, tomllib.TOMLDecodeError):
            table = {}

    named_roots = [p for p in (_as_path(one) for one in table.get("workspaces") or []) if p is not None]
    roots: list[Path] = named_roots or list(default_workspace_roots())
    for extra in env_workspace_roots():
        if extra not in roots:
            roots.append(extra)
    registered = discover_registrations(tuple(roots))

    hand_written: list[ManagerConfig] = []
    for index, one in enumerate(table.get("managers") or []):
        made = _manager_from_table(one, index)
        if made is not None:
            hand_written.append(made)

    if not have_file:
        # No file at all: the old `~/dev/hw-*` discovery still stands, so a host
        # that has never registered anything is not shown an empty page. A
        # registration of the same id wins, because it is the session's own word.
        found = discover()
        known = {one.id for one in registered}
        older = tuple(
            replace(one, origin=f"discovered from {one.batch_dir}/HIGHWAY.md")
            for one in found
            if one.id not in known
        )
        managers = merge(older, registered)
        where = ", ".join(str(one) for one in roots)
        return AppConfig(
            managers=managers,
            source=f"registrations under {where}; and {Path.home() / 'dev'}/hw-*/HIGHWAY.md",
            note=(
                f"No config file at {path}; manager sessions that registered themselves are "
                "shown, and every hw-* batch under ~/dev beside them."
            ),
            discovered=True,
            workspaces=tuple(roots),
        )

    where = ", ".join(str(one) for one in roots)
    return AppConfig(
        managers=merge(tuple(hand_written), registered),
        source=f"{path}; registrations under {where}",
        workspaces=tuple(roots),
    )


__all__ = [
    "CONVERGE_DIR",
    "DEFAULT_CONFIG_PATH",
    "DEFAULT_TMUX_SOCKET",
    "REGISTRATION_NAME",
    "WORKSPACES_ENV",
    "AppConfig",
    "ManagerConfig",
    "app_repo_root",
    "default_workspace_roots",
    "discover",
    "discover_registrations",
    "env_workspace_roots",
    "load",
    "merge",
    "read_registration",
]
