"""Unit tests for app/tmux_view.py against a real, isolated tmux server.

The socket is ``cvtest`` and nothing here ever touches another socket: the only
destructive command in this file is ``tmux -L cvtest kill-server``.  There is no
``pkill``/``pgrep -f`` anywhere — a pattern that appears in your own command
line kills your own shell (field guide §7).

Skips cleanly when tmux is not installed.

What is covered, and why each one is here:

* the single tmux round-trip (geometry and capture from the same tick)
* the explicit socket, and ``$TMUX`` stripped from the child environment
* the four states — ok / empty / ended / failed — never conflated
* **no fall-through**: a prefix of a live session name resolves to ``ended``,
  not to that session's pane; and a killed session reports ``ended`` fast
  without ever showing another session's text
* the capture cache fans one capture out to many clients
* the trailing newline is stripped
"""

from __future__ import annotations

import asyncio
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app import tmux_view as tv  # noqa: E402

SOCKET = "cvtest"
MARKER = "ZZMARKERZZ"

pytestmark = pytest.mark.skipif(shutil.which("tmux") is None, reason="tmux is not installed")


# --------------------------------------------------------------------------
# fixture: an isolated tmux server with one session per state
# --------------------------------------------------------------------------


def _tmux(*args: str, check: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["tmux", "-L", SOCKET, *args],
        capture_output=True,
        text=True,
        env=tv._env(),
        check=check,
    )


@pytest.fixture(scope="module", autouse=True)
def cvtest_server(tmp_path_factory):
    _tmux("kill-server")
    long_file = tmp_path_factory.mktemp("tmuxview") / "long.txt"
    long_file.write_text("\n".join(str(i) for i in range(1, 5001)) + "\n")

    _tmux(
        "new", "-d", "-s", "colors",
        'while :; do printf "\\033[31mred \\033[32mgreen\\033[0m %s\\n" $(date +%T); sleep 1; done',
        check=True,
    )
    _tmux("new", "-d", "-s", "tui", "top", check=True)
    _tmux("new", "-d", "-s", "altscr", f"less {long_file}", check=True)
    _tmux("new", "-d", "-s", "empty", "sleep 600", check=True)
    _tmux("new", "-d", "-s", "marker", f'while :; do echo {MARKER}; sleep 1; done', check=True)
    _tmux("new", "-d", "-s", "victim", 'while :; do echo VICTIMLINE; sleep 1; done', check=True)
    time.sleep(2.0)  # let the panes paint
    yield
    _tmux("kill-server")


def frame(session: str, lines: int = 200, cache: tv.CaptureCache | None = None) -> tv.Frame:
    cache = cache or tv.CaptureCache()
    return asyncio.run(cache.get(SOCKET, session, lines))


# --------------------------------------------------------------------------
# the round-trip and the socket
# --------------------------------------------------------------------------


def test_one_tmux_round_trip_with_explicit_socket():
    argv = tv.CaptureCache.command(SOCKET, "colors", 200)
    print("\ntmux command:", " ".join(argv))

    assert argv.count("tmux") == 1, "must be a single tmux invocation"
    assert argv[0] == "tmux"
    assert argv[1:3] == ["-L", SOCKET], "explicit socket, never $TMUX"
    assert ";" in argv, "display-message and capture-pane chained in one round-trip"
    sep = argv.index(";")
    assert "display-message" in argv[:sep]
    assert "capture-pane" in argv[sep:]
    assert "-e" in argv, "-e keeps the colours"
    assert "-a" not in argv, "-a returns a blank alt screen (measured)"
    assert argv[-2:] == ["-S", "-200"]


def test_socket_path_form_uses_dash_S():
    assert tv._socket_args("hw") == ["-L", "hw"]
    assert tv._socket_args("/tmp/tmux-1000/hw") == ["-S", "/tmp/tmux-1000/hw"]


def test_child_env_drops_ambient_tmux_but_keeps_tmpdir():
    env = tv._env()
    assert "TMUX" not in env, "$TMUX must never reach the child"
    if "TMUX_TMPDIR" in os.environ:
        assert env["TMUX_TMPDIR"] == os.environ["TMUX_TMPDIR"], "-L resolution needs TMUX_TMPDIR"
    # And we say which server we ignored.
    assert tv.ambient_tmux_ignored() == (os.environ.get("TMUX") or None)


def test_lines_are_bounded():
    argv = tv.CaptureCache.command(SOCKET, "colors", 99999)
    assert argv[-1] == f"-{tv.MAX_LINES}", "capture is bounded at 2000 lines"


# --------------------------------------------------------------------------
# the four states
# --------------------------------------------------------------------------


def test_state_ok_carries_ansi_and_geometry():
    f = frame("colors")
    print(f"\ncolors -> state={f.state} geometry={f.geometry}")
    assert f.state == "ok"
    assert "\x1b[" in f.text, "-e must preserve the escape sequences"
    assert f.geometry["width"] > 0 and f.geometry["height"] > 0
    assert f.session == "colors" and f.socket == SOCKET


def test_state_ok_alternate_screen_is_reported_and_rendered():
    f = frame("altscr")
    print(f"\naltscr -> state={f.state} alternate_on={f.geometry['alternate_on']}")
    assert f.state == "ok"
    assert f.geometry["alternate_on"] is True, "less runs on the alternate screen"
    assert f.text.strip(), "capture-pane -e (without -a) renders an alt-screen TUI"


def test_state_empty_is_not_a_failure():
    f = frame("empty")
    print(f"\nempty -> state={f.state} geometry={f.geometry}")
    assert f.state == "empty"
    assert f.text == ""
    assert f.geometry is not None, "empty means metadata read fine and the pane is blank"


def test_state_ended_for_a_session_that_does_not_exist():
    f = frame("no-such-session-at-all")
    print(f"\nno-such-session-at-all -> state={f.state} detail={f.detail!r}")
    assert f.state == "ended"
    assert f.text == ""
    assert f.geometry is None


def test_state_failed_when_metadata_is_unreadable():
    # rc == 0 but the metadata line is not the seven numbers we asked for:
    # the observation failed, and that is not the same thing as an empty pane.
    state, text, geometry, detail = tv._classify(0, "not-a-geometry-line\nsome pane text\n", "")
    print(f"\nunreadable metadata -> state={state} detail={detail!r}")
    assert state == "failed"
    assert geometry is None
    assert text == ""

    state, _, _, detail = tv._classify(1, "", "tmux: something went sideways")
    print(f"tmux error -> state={state} detail={detail!r}")
    assert state == "failed"


def test_the_four_states_are_distinct():
    seen = {
        frame("colors").state,
        frame("empty").state,
        frame("no-such-session-at-all").state,
        tv._classify(0, "garbage\n", "")[0],
    }
    print(f"\nstates observed: {sorted(seen)}")
    assert seen == {"ok", "empty", "ended", "failed"}


# --------------------------------------------------------------------------
# no fall-through — the defect the field guide caught in a browser
# --------------------------------------------------------------------------


def test_a_prefix_of_a_live_session_never_resolves_to_it():
    """`tmux -t colo` answers for `colors`.  Ours must not."""
    raw = _tmux("display-message", "-p", "-t", "colo:", "#{session_name}")
    print(f"\nbare tmux -t 'colo:' resolves to: {raw.stdout.strip()!r}")
    assert raw.stdout.strip() == "colors", "tmux really does fall through on a prefix"

    f = frame("colo")
    print(f"viewer 'colo' -> state={f.state} detail={f.detail!r} text={f.text!r}")
    assert f.state == "ended", "the viewer pins an exact session, so a prefix is 'ended'"
    assert f.text == ""


def test_killed_session_reports_ended_fast_and_shows_no_other_session():
    cache = tv.CaptureCache(tick_ms=0)  # no caching: we are timing the transition

    before = asyncio.run(cache.get(SOCKET, "victim", 200))
    assert before.state == "ok" and "VICTIMLINE" in before.text

    marker_frame = asyncio.run(cache.get(SOCKET, "marker", 200))
    assert MARKER in marker_frame.text, "the other session is live and identifiable"

    _tmux("kill-session", "-t", "=victim:")
    t0 = time.monotonic()
    seen = None
    while time.monotonic() - t0 < 2.0:
        seen = asyncio.run(cache.get(SOCKET, "victim", 200))
        if seen.state == "ended":
            break
        time.sleep(0.1)
    elapsed = time.monotonic() - t0
    print(f"\nvictim killed -> state={seen.state} after {elapsed * 1000:.0f} ms; text={seen.text!r}")

    assert seen.state == "ended", "loss renders as ended, never as empty and never as ok"
    assert elapsed < 2.0
    assert MARKER not in seen.text, "never fall through to another session's pane"
    assert seen.text == ""
    assert seen.session == "victim", "the frame still answers for the session we asked about"


# --------------------------------------------------------------------------
# cache fan-out and the trailing newline
# --------------------------------------------------------------------------


def test_cache_fans_one_capture_out_to_many_clients():
    polls = 20

    single = tv.CaptureCache()
    asyncio.run(_poll_serially(single, 1, polls))
    baseline = single.captures

    three = tv.CaptureCache()
    asyncio.run(_poll_serially(three, 3, polls))

    print(f"\ncaptures: 1 client x {polls} polls = {baseline}; 3 clients x {polls} polls = {three.captures}")
    assert three.captures <= baseline, "N tabs must not multiply tmux captures"
    assert baseline < polls, "the cache is actually caching"


async def _poll_serially(cache: tv.CaptureCache, clients: int, polls: int) -> None:
    async def client() -> None:
        for _ in range(polls):
            await cache.get(SOCKET, "colors", 200)
            await asyncio.sleep(0.05)

    await asyncio.gather(*(client() for _ in range(clients)))


def test_trailing_newline_is_stripped():
    head, text = tv._split_capture("80 24 0 2000 0 0 0\nline one\nline two\n")
    assert head == "80 24 0 2000 0 0 0"
    assert text == "line one\nline two", "the trailing newline scrolls a full-height TUI's top row away"

    f = frame("tui")
    print(f"\ntui -> state={f.state}; text ends with newline: {f.text.endswith(chr(10))}")
    assert f.state == "ok"
    assert not f.text.endswith("\n")


def test_top_row_survives_for_a_full_height_tui():
    f = frame("tui", lines=200)
    first = f.text.splitlines()[0] if f.text else ""
    print(f"\ntui first rendered row: {first!r}")
    assert first.startswith("top - "), "the TUI's own top row is the first line we hand the terminal"
