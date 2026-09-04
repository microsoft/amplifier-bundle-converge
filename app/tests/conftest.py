"""Shared ground for the app tests.

**The rule this file exists to keep: no test may name a tmux socket that another
run on this machine could also name.**

A tmux session name is scoped to a server, and a server is identified by its
socket, so the socket name is the only machine-wide name in play.  Two runs that
share one -- ten lanes on one machine is the normal case here -- see each other's
sessions, fail to create a session name the other already took, and kill each
other's server mid-run.  The failure lands in whichever run loses the race, and
it names a file that run never touched.

Measured 2026-09-04, two overlapping runs of the tmux view tests on one fixed
socket name: one reported ``15 passed``, the other ``15 errors``, reading

    subprocess.CalledProcessError: Command '['tmux', '-L', 'cvbaseline', 'new',
    '-d', '-s', 'colors', ...]' returned non-zero exit status 1.

## The convention

A tmux test module builds its socket name like this, at import:

    SOCKET = f"cvthing-{os.getpid()}-{uuid.uuid4().hex[:8]}"

The pid says *this run owns it*; the random suffix keeps two modules in one run
apart, and survives the fact that pids get reused.  Each module keeps its own
copy of that line rather than importing one from here, because a test module
cannot safely import its own ``conftest`` (two ``conftest.py`` files in this
repository would collide under one module name).  The convention is written
down here; the reaper below is what depends on it.

Two consequences of per-run names, and both are the point:

* another run cannot see, name, or kill anything on our socket, and we cannot
  touch theirs -- so a run's verdict is about its own code and nothing else;
* a run that finds a server already up on its own socket **says so and stops**,
  rather than killing what it found (``contracts/operation.v1.md``: a check that
  cannot run says so, rather than reporting a failure someone else caused).

The cost is that what a run leaves behind is permanent rather than self-limiting:
a crashed run leaks a server under a name nobody will reuse, and even a clean
``kill-server`` leaves the empty socket file in the directory.
``_reap_this_runs_tmux_sockets`` closes both: at the end of the session it kills
any server, and removes any socket file, whose name carries ``PID_MARK`` --
whatever happened to the module fixtures.  It touches nothing else: a socket
without our mark belongs to someone else, and killing that is the very defect
this file is about.

There is deliberately no ``pkill``/``pgrep -f`` here: that pattern appears in
your own command line and kills your own shell (field guide section 7).
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

#: In the name of every socket this run owns, and in no other run's.
PID_MARK = f"-{os.getpid()}-"


def tmux_env() -> dict[str, str]:
    """The environment a tmux child gets: ours, minus an ambient ``$TMUX``.

    ``TMUX_TMPDIR`` is kept -- ``-L`` needs it to resolve to the same socket
    directory the caller's own tmux uses.
    """
    env = dict(os.environ)
    env.pop("TMUX", None)
    return env


def socket_dir() -> Path:
    """Where ``tmux -L <name>`` puts its socket."""
    return Path(os.environ.get("TMUX_TMPDIR") or "/tmp") / f"tmux-{os.getuid()}"


def _tmux(socket: str, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["tmux", "-L", socket, *args],
        capture_output=True,
        text=True,
        env=tmux_env(),
        check=False,  # a dead socket answering non-zero is the normal case here
    )


@pytest.fixture(scope="session", autouse=True)
def _reap_this_runs_tmux_sockets():
    """Leave nothing of this run behind, and touch nothing else.

    Two things get left behind otherwise, and per-run names make both permanent
    rather than self-limiting:

    * a module fixture that dies before its teardown leaks a **server** under a
      name no future run will reuse;
    * even after a clean ``kill-server``, tmux leaves the empty **socket file**
      in place -- measured, one file per run, growing without bound.

    Only names carrying ``PID_MARK`` are touched: those are this run's, and
    nothing else's.
    """
    yield
    directory = socket_dir()
    if not directory.is_dir():
        return
    ours = sorted((entry for entry in directory.iterdir() if PID_MARK in entry.name), key=lambda p: p.name)
    still_serving = []
    for path in ours:
        if _tmux(path.name, "ls").returncode == 0:
            still_serving.append(path.name)
            _tmux(path.name, "kill-server")
        if _tmux(path.name, "ls").returncode != 0:
            path.unlink(missing_ok=True)
    if ours:
        names = ", ".join(path.name for path in ours)
        print(
            f"\ncleared {len(ours)} tmux socket(s) this run created "
            f"({len(still_serving)} still had a live server): {names}"
        )
