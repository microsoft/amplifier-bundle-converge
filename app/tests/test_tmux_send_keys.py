"""The write path: a line typed in the console arrives in the manager session.

``experience-console.v1`` Core 3 says the console *is* the manager session —
"what you type there is what the manager session receives, not a summary the app
relays".  The conformance kit deliberately cannot prove that: a static read can
only see whether a route exists at all, and says so in its own detail.  **This
file is where the round trip is actually proved**, against a real tmux server.

The socket is named for **this run** -- ``cvsend-<pid>-<random>`` -- and nothing
here ever touches another socket: the only destructive command in this file is
``tmux -L <that socket> kill-server``.  A fixed name would be machine-wide, and
two lanes testing at once would kill each other's sessions and report the loss
as a failure in a file neither had touched; ``conftest.py`` records the
measurement.  There is no ``pkill``/``pgrep -f`` anywhere, a pattern that kills
your own shell.

What is covered, and why each one is here:

* the round trip itself — the marker leaves the app and shows up in the pane
* **the word ``Enter`` is five letters, not the Return key** — keys are sent as
  code points, so nothing a steward types is looked up as a tmux key name
* a control byte crosses (Ctrl-D ends ``cat``, which nothing else would)
* **no fall-through on a write** — a send to a prefix of a live session name
  reports ``ended`` and leaves that session's pane untouched.  Reading the wrong
  pane is a bad frame; writing to it cannot be taken back
* the write is bounded, and says so when it truncates
* a send to a session that is gone is ``ended``, never a quiet success
* there is **no route that enumerates sessions** (Core 10)
"""

from __future__ import annotations

import asyncio
import os
import shutil
import subprocess
import sys
import time
import uuid
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app import tmux_view as tv  # noqa: E402

#: One server per run, never a fixed machine-wide name.  The convention and the
#: measurement behind it are in ``conftest.py``; the pid is what its end-of-run
#: reaper looks for.
SOCKET = f"cvsend-{os.getpid()}-{uuid.uuid4().hex[:8]}"
MARKER = "ZZSENTZZ"

pytestmark = pytest.mark.skipif(shutil.which("tmux") is None, reason="tmux is not installed")


# --------------------------------------------------------------------------
# fixture: an isolated tmux server whose panes echo whatever they are sent
# --------------------------------------------------------------------------


def _tmux(*args: str, check: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["tmux", "-L", SOCKET, *args],
        capture_output=True,
        text=True,
        env=tv._env(),
        check=check,
    )


def _pane(session: str) -> str:
    return _tmux("capture-pane", "-p", "-t", f"={session}:").stdout


def _refuse_if_a_server_is_already_up() -> None:
    """Say so and stop, rather than kill a server this run did not start.

    On a per-run socket name this should be unreachable.  If it ever fires,
    the naming is wrong, and the honest answer is to report that -- not to
    ``kill-server`` and take someone else's sessions out from under them
    (``contracts/operation.v1.md``: a check that cannot run says so, rather
    than reporting a failure someone else caused).
    """
    found = _tmux("ls")
    if found.returncode == 0:
        pytest.fail(
            f"a tmux server is already running on socket {SOCKET!r}, which this run "
            f"expected to have to itself. Refusing to kill it. Sessions found:\n"
            f"{found.stdout.strip()}"
        )


@pytest.fixture(scope="module", autouse=True)
def cvsend_server():
    _refuse_if_a_server_is_already_up()
    # try/finally, not a bare yield: a `check=True` failure below would
    # otherwise skip the teardown and leak this run's server.
    try:
        # `cat` echoes its own input, so the pane's text is proof the keystrokes
        # arrived at the process, not merely at tmux.
        _tmux("new", "-d", "-s", "typist", "cat", check=True)
        _tmux("new", "-d", "-s", "closer", "cat", check=True)
        _tmux("new", "-d", "-s", "shortest", "cat", check=True)
        _tmux("new", "-d", "-s", "bulk", "cat", check=True)
        _tmux("new", "-d", "-s", "router", "cat", check=True)
        time.sleep(1.0)
        yield
    finally:
        _tmux("kill-server")


def send(session: str, keys: str, enter: bool = False) -> dict:
    return asyncio.run(tv.send_keys(SOCKET, session, keys, enter))


def wait_for(session: str, needle: str, seconds: float = 3.0) -> str:
    deadline = time.time() + seconds
    text = ""
    while time.time() < deadline:
        text = _pane(session)
        if needle in text:
            return text
        time.sleep(0.1)
    return text


# --------------------------------------------------------------------------
# the argv: code points, never key names
# --------------------------------------------------------------------------


def test_keys_are_sent_as_code_points_with_an_explicit_socket():
    argv = tv._keys_argv(SOCKET, "typist", "hi", enter=True)
    print("\ntmux command:", " ".join(argv))

    assert argv[0] == "tmux"
    assert argv[1:3] == ["-L", SOCKET], "explicit socket, never $TMUX"
    assert "send-keys" in argv
    assert "-H" in argv, "-H is what makes every key a code point instead of a name"
    assert argv[-3:] == ["68", "69", "0d"], "h, i, then Return — as hex code points"
    assert argv[argv.index("-t") + 1] == "=typist:", "exact-match target, as the capture uses"


def test_a_word_that_names_a_key_is_sent_as_that_word():
    """The single most important property of ``-H``.

    With key-name lookup a steward typing the word ``Enter`` would press Return,
    and ``C-c`` would interrupt their own session.  As code points they are text.
    """
    argv = tv._keys_argv(SOCKET, "typist", "Enter", enter=False)
    assert argv[-5:] == ["45", "6e", "74", "65", "72"], "five letters, not one keypress"

    send("typist", "Enter", enter=False)
    text = wait_for("typist", "Enter")
    print("pane after sending the word 'Enter':", repr(text.strip().splitlines()[-1:]))
    assert "Enter" in text, "the word must appear in the pane as text"


# --------------------------------------------------------------------------
# the round trip
# --------------------------------------------------------------------------


def test_a_typed_line_arrives_in_the_session():
    answer = send("typist", MARKER, enter=True)
    print("\nsend answer:", answer)
    assert answer["sent"] is True
    assert answer["state"] == "ok"
    assert answer["socket"] == SOCKET and answer["session"] == "typist", "identity echoed back"

    text = wait_for("typist", MARKER)
    print("pane:", repr([ln for ln in text.splitlines() if MARKER in ln][:2]))
    assert MARKER in text, "the line the app sent must be in the pane the app is showing"


def test_the_app_then_shows_it_because_the_pane_did():
    """The app never paints a typed line; the next capture is what shows it."""
    send("typist", "SECONDLINE", enter=True)
    wait_for("typist", "SECONDLINE")
    frame = asyncio.run(tv.CaptureCache().get(SOCKET, "typist"))
    print("\nframe state:", frame.state, "| contains the line:", "SECONDLINE" in frame.text)
    assert frame.state == "ok"
    assert "SECONDLINE" in frame.text


def test_a_control_byte_crosses():
    """Ctrl-D ends ``cat``; nothing but a real control byte would do that."""
    send("closer", "ALIVE", enter=True)
    wait_for("closer", "ALIVE")
    assert asyncio.run(tv.CaptureCache().get(SOCKET, "closer")).state == "ok"
    answer = send("closer", "\x04")
    print("\nsent Ctrl-D:", answer)
    assert answer["sent"] is True

    deadline = time.time() + 5
    state = "ok"
    while time.time() < deadline:
        state = asyncio.run(tv.CaptureCache().get(SOCKET, "closer")).state
        if state == "ended":
            break
        time.sleep(0.2)
    print("state after Ctrl-D:", state)
    assert state == "ended", "the control byte reached the process and it exited"


# --------------------------------------------------------------------------
# no fall-through, on a write
# --------------------------------------------------------------------------


def test_a_prefix_of_a_live_session_never_receives_the_keys():
    """``-t short`` would resolve to ``shortest`` without the ``=`` prefix.

    Measured on tmux 3.4, that is a real re-target.  On a read it shows the
    wrong pane; on a write it types into somebody else's session.
    """
    before = _pane("shortest")
    answer = send("short", "WRONGPANE", enter=True)
    print("\nsend to the prefix 'short':", answer)
    assert answer["sent"] is False
    assert answer["state"] == "ended", "a name that is not a session is gone, not a success"
    assert answer["session"] == "short", "the answer names what was asked for"

    time.sleep(0.6)
    after = _pane("shortest")
    assert "WRONGPANE" not in after, "the keystrokes must not have landed in 'shortest'"
    print("'shortest' pane unchanged:", after.strip() == before.strip())


def test_a_session_that_is_gone_is_ended_not_a_quiet_success():
    answer = send("no-such-session-here", "anything", enter=True)
    print("\nsend to a session that does not exist:", answer)
    assert answer["sent"] is False
    assert answer["state"] == "ended"
    assert answer["detail"], "the reason is said out loud"


# --------------------------------------------------------------------------
# bounds and the empty send
# --------------------------------------------------------------------------


def test_the_write_is_bounded_and_says_so():
    # Its own session: 4096 x's would otherwise scroll every other pane's
    # evidence out of view.
    answer = send("bulk", "x" * (tv.MAX_KEYS + 50))
    print("\noversized send:", {k: answer[k] for k in ("sent", "keys", "truncated", "detail")})
    assert answer["sent"] is True
    assert answer["keys"] == tv.MAX_KEYS
    assert answer["truncated"] is True
    assert str(tv.MAX_KEYS) in answer["detail"], "a silent truncation would be the defect"


def test_nothing_to_send_is_not_a_write():
    answer = send("typist", "", enter=False)
    print("\nempty send:", answer)
    assert answer["sent"] is False
    assert answer["detail"] == "nothing to send"


# --------------------------------------------------------------------------
# the routes: one read, one write, and no way to ask what else is running
# --------------------------------------------------------------------------


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(tv.router)
    return TestClient(app)


def test_the_route_table_is_one_read_and_one_write():
    paths = {(r.path, tuple(sorted(r.methods))) for r in tv.router.routes}
    print("\nroutes:", sorted(paths))
    assert ("/api/tmux/{socket}/{session}", ("GET",)) in paths
    assert ("/api/tmux/{socket}/{session}/keys", ("POST",)) in paths
    assert len(paths) == 2


def test_no_route_enumerates_the_sessions_on_a_socket():
    """experience-console.v1 Core 10 — the reach, not the display.

    The console showed only its own targets even when this route existed; the
    defect was that anything at all could ask what else was running.
    """
    for path, _ in {(r.path, None) for r in tv.router.routes}:
        assert not path.endswith("/sessions"), f"{path} enumerates a socket"
    assert not hasattr(tv, "list_sessions"), "the helper is gone too, not just the route"
    assert _client().get("/api/tmux/sessions").status_code == 404


def test_the_route_carries_the_keystroke_and_echoes_the_identity():
    res = _client().post(
        f"/api/tmux/{SOCKET}/router/keys", json={"keys": "VIAROUTE", "enter": True}
    )
    body = res.json()
    print("\nPOST /keys ->", res.status_code, body)
    assert res.status_code == 200
    assert body["sent"] is True
    assert body["socket"] == SOCKET and body["session"] == "router"
    assert "ambient_tmux_ignored" in body, "a write says which server it went to"
    assert "VIAROUTE" in wait_for("router", "VIAROUTE")
