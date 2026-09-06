#!/usr/bin/env python3
"""Write this manager session's registration, so the app can find it.

    uv run scripts/register-manager.py --steward <name>

A manager session runs this on **every wake**. It writes
``<workspace>/.converge/<manager-id>/registration.toml`` naming the session -
its name, its steward, its workspace root, the repositories it steers with
their default branches, its plan record, its tmux socket and session, its work
queue - and stamps ``last_seen`` with the moment of the wake.

Why on every wake rather than once
----------------------------------
Two reasons, and the second is the one that matters.

* ``last_seen`` **is** the heartbeat. The app reads it to answer
  ``experience.v1`` Core 1's "quiet or silent", and a stamp written once at
  first wake would say a dead session is alive forever.
* An **existing** manager session - one that started before any of this - has
  no registration and no reason to notice it is missing. Writing
  unconditionally means it appears on Home the next time it wakes, with nobody
  editing a file on its behalf. A "write it if it is not there" version would
  leave every session that already exists invisible, which is the exact defect
  this closes.

The write is cheap: a few hundred bytes to a temp file and a rename.

What is read, and what is never guessed
---------------------------------------
Everything is taken from the surroundings this runs in - the working directory,
git, and a few environment variables - and every one of them can be overridden
by a flag. Nothing is invented:

* ``--workspace`` / the workspace root: the nearest ancestor holding
  ``WORKSPACE-MANIFEST.json``, or ``git rev-parse --show-toplevel`` when there
  is none. Exactly the resolution ``modes/converge-manager.md`` clause 5 gives.
* ``--id``: ``$CONVERGE_MANAGER_ID``, else the batch directory's own name, else
  the workspace root's name.
* ``--steward`` / ``$CONVERGE_STEWARD``: **never** ``$USER``.
  ``experience-collaboration.v1`` Core 8 says whose word counts is settled at
  registration, not inferred from whoever happens to be signed in - and the
  account this process runs as is exactly such an inference. With nothing
  given, the field is written empty and this says so on stdout.
* ``--manager-tmux``: given, or ``$CONVERGE_MANAGER_TMUX``. The ambient
  ``$TMUX`` is deliberately not read: it names the socket and pane this process
  happens to sit in, which is a different fact from the session a steward would
  attach to, and ``app/config.py`` refuses the same inference on the other side.
* repositories: ``--repo`` (repeatable), else every immediate child of the
  workspace root holding a ``.git``. Each one's default branch is read from
  ``origin/HEAD`` when the remote publishes one, else ``main`` or ``master``
  when the repository has one, else its current branch.

It prints the path and the file it wrote, so a wake can paste the evidence.
"""

from __future__ import annotations

import argparse
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

#: Where a manager session's whole operation hangs from, under the workspace
#: root - `modes/converge-manager.md` clause 5. Kept in step with
#: `app/config.py`'s constants of the same name; the app is the reader and this
#: is the writer, and a disagreement between them is a manager nobody can see.
CONVERGE_DIR = ".converge"
REGISTRATION_NAME = "registration.toml"
WORKSPACE_MARKER = "WORKSPACE-MANIFEST.json"
DEFAULT_TMUX_SOCKET = "hw"


def run(args: list[str], cwd: Path | None = None) -> str:
    """Stdout, or an empty string when the command is missing or fails."""
    try:
        done = subprocess.run(
            args,
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
            timeout=10.0,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    return done.stdout.strip() if done.returncode == 0 else ""


def workspace_root(start: Path) -> Path:
    """The nearest ancestor holding the marker, else this repository's root.

    `modes/converge-manager.md` clause 5's resolution, in Python. There is no
    third case: a project with no workspace around it IS its own workspace.
    """
    here = start.resolve()
    for candidate in (here, *here.parents):
        if (candidate / WORKSPACE_MARKER).is_file():
            return candidate
    top = run(["git", "rev-parse", "--show-toplevel"], cwd=here)
    return Path(top) if top else here


def default_branch(repo: Path) -> str:
    """The branch this repository integrates on, read three ways in order.

    `origin/HEAD` is the published answer and is preferred. A repository with
    no remote, or a remote that never set it, is asked whether it has a `main`
    or a `master`. Failing all of that, the branch currently checked out is
    what it has - and saying so is more honest than writing `main` because
    `main` is usually right.
    """
    head = run(["git", "symbolic-ref", "--quiet", "--short", "refs/remotes/origin/HEAD"], cwd=repo)
    if head:
        return head.split("/", 1)[-1]
    for name in ("main", "master"):
        if run(["git", "rev-parse", "--verify", "--quiet", f"refs/heads/{name}"], cwd=repo):
            return name
    return run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=repo)


def repos_under(root: Path) -> list[Path]:
    """Every immediate child of the workspace root that is a git checkout."""
    if not root.is_dir():
        return []
    return sorted(one for one in root.iterdir() if one.is_dir() and (one / ".git").exists())


def toml_string(value: str) -> str:
    """A TOML basic string. Escapes the two characters that can break one."""
    return '"' + str(value).replace("\\", "\\\\").replace('"', '\\"') + '"'


def render(fields: dict, repos: list[tuple[Path, str]]) -> str:
    """The registration file, in the order a person reads it."""
    lines = [
        "# Written by scripts/register-manager.py on every wake of this manager",
        "# session. Do not hand-edit: the next wake overwrites it. To override any",
        "# of it, name the manager in the app's own converge-app.toml instead - a",
        "# hand-written block wins, and still takes this file's last_seen.",
        "",
    ]
    for key in ("id", "name", "steward", "workspace", "batch_dir", "plan_record",
                "tracker_project", "tmux_socket", "manager_tmux", "last_seen"):
        lines.append(f"{key} = {toml_string(fields.get(key, ''))}")
    for path, branch in repos:
        lines += ["", "[[repos]]", f"path = {toml_string(str(path))}", f"default_branch = {toml_string(branch)}"]
    return "\n".join(lines) + "\n"


def write_atomically(path: Path, text: str) -> None:
    """Rename a finished file into place, never a half-written one.

    The app reads this file on every request, so a partial write is a manager
    that vanishes from Home for as long as the write takes. A rename inside one
    directory is atomic, so a reader sees either the previous registration or
    the new one and never a fragment of either.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".writing")
    temp.write_text(text, encoding="utf-8")
    temp.replace(path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="register-manager.py",
        description="Write this manager session's registration so the Converge app can find it.",
    )
    parser.add_argument("--workspace", default=None, help="Workspace root (default: resolved from the working directory)")
    parser.add_argument("--id", default=None, help="Manager id - the project's own name (default: $CONVERGE_MANAGER_ID, else the batch directory's name)")
    parser.add_argument("--name", default=None, help="What a steward should see on Home (default: the id, title-cased)")
    parser.add_argument("--steward", default=None, help="Whose word counts on this session (default: $CONVERGE_STEWARD; never $USER)")
    parser.add_argument("--repo", action="append", default=[], help="A repository this session steers - repeatable")
    parser.add_argument("--plan-record", default=None, help="The plan record (default: <batch>/HIGHWAY.md when it exists)")
    parser.add_argument("--tracker-project", default=None, help="The work queue this session files against (default: $CONVERGE_TRACKER_PROJECT, else the id)")
    parser.add_argument("--tmux-socket", default=None, help=f"The socket the lanes run on (default: $CONVERGE_TMUX_SOCKET, else {DEFAULT_TMUX_SOCKET})")
    parser.add_argument("--manager-tmux", default=None, help="This session's own tmux session name (default: $CONVERGE_MANAGER_TMUX; the ambient $TMUX is never read)")
    parser.add_argument("--print", dest="show", action="store_true", help="Print the file that was written")
    args = parser.parse_args(argv)

    root = Path(args.workspace).expanduser().resolve() if args.workspace else workspace_root(Path.cwd())
    mid = (args.id or os.environ.get("CONVERGE_MANAGER_ID") or "").strip() or root.name
    batch = root / CONVERGE_DIR / mid

    given = [Path(one).expanduser().resolve() for one in args.repo]
    repos = given or repos_under(root)
    with_branches = [(one, default_branch(one)) for one in repos]

    plan = Path(args.plan_record).expanduser() if args.plan_record else batch / "HIGHWAY.md"
    steward = (args.steward or os.environ.get("CONVERGE_STEWARD") or "").strip()

    fields = {
        "id": mid,
        "name": (args.name or "").strip() or mid.replace("-", " ").title(),
        "steward": steward,
        "workspace": str(root),
        "batch_dir": str(batch),
        "plan_record": str(plan) if plan.is_file() else "",
        "tracker_project": (args.tracker_project or os.environ.get("CONVERGE_TRACKER_PROJECT") or "").strip() or mid,
        "tmux_socket": (args.tmux_socket or os.environ.get("CONVERGE_TMUX_SOCKET") or "").strip() or DEFAULT_TMUX_SOCKET,
        "manager_tmux": (args.manager_tmux or os.environ.get("CONVERGE_MANAGER_TMUX") or "").strip(),
        "last_seen": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }

    text = render(fields, with_branches)
    path = batch / REGISTRATION_NAME
    write_atomically(path, text)

    print(f"registered {mid} at {path}")
    print(f"  workspace {root}")
    print(f"  repos {[str(one) for one, _branch in with_branches] or 'none found'}")
    print(f"  last_seen {fields['last_seen']}")
    if not steward:
        print(
            "  NOTE: no steward named. Pass --steward or set $CONVERGE_STEWARD - "
            "the app will not guess one from the signed-in account "
            "(experience-collaboration.v1 Core 8)."
        )
    if not fields["manager_tmux"]:
        print("  NOTE: no manager tmux session named. Pass --manager-tmux or set $CONVERGE_MANAGER_TMUX.")
    if args.show:
        print()
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
