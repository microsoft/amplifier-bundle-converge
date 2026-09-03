"""Rendered-browser regression tests for the tmux viewer.

The field guide (§6) is blunt about this: **verify in a rendered browser, not
against the JSON.**  Two real defects passed every API-level check and were
caught only by a headless browser reading the rendered page:

1. **Silent re-target** — when the watched session died the client fell through
   to a *different* session and showed that session's blank pane under a
   healthy banner.
2. **Top-row loss** — a full-height alt-screen TUI lost its title bar, because
   the trailing newline from ``capture-pane`` scrolled it off, while every JSON
   field was perfect.

Those are the two tests below.  They assert on the **rendered DOM** — the
banner's CSS class and the text xterm.js actually painted — never on the JSON.

Everything runs in-process: a FastAPI app carrying the real
``tmux_view.router``, the real ``app/static`` mounted at ``/static``, and a
minimal harness page that calls the real ``window.ConvergeTmux.attach``.  The
tmux server is the isolated ``cvtest`` socket, and the only destructive command
in this file is ``tmux -L cvtest kill-server``.

If Playwright or its Chromium build is unavailable, both tests skip with the
reason printed, and ``MANUAL_PROCEDURE`` below is the documented manual check
that stands in for them.
"""

from __future__ import annotations

import asyncio
import shutil
import socket as socketlib
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app import tmux_view as tv  # noqa: E402

SOCKET = "cvtest"
MARKER = "ZZMARKERZZ"
APP_DIR = Path(__file__).resolve().parents[1]

MANUAL_PROCEDURE = """
MANUAL PROCEDURE — run these two checks by hand if Playwright is unavailable.
Each step says what you must SEE; seeing anything else is a failure.

Setup
  tmux -L cvtest new -d -s victim 'while :; do echo VICTIMLINE; sleep 1; done'
  tmux -L cvtest new -d -s marker 'while :; do echo ZZMARKERZZ; sleep 1; done'
  tmux -L cvtest new -d -s tui top
  uv run --extra app python -m app.serve --host 127.0.0.1 --port 8788
  Open http://127.0.0.1:8788/ and attach the console terminal to cvtest/victim
  (or call ConvergeTmux.attach(el, 'cvtest', 'victim') from the devtools console).

Check 1 — killed session renders `ended`, never another session's pane
  a. SEE: the banner element carries class `tmux-ok`, and the terminal shows
     repeating lines reading VICTIMLINE.
  b. Run: tmux -L cvtest kill-session -t '=victim:'
  c. Within ~1 s, SEE: the banner element carries class `tmux-ended`.
  d. SEE: the terminal contains NO line reading ZZMARKERZZ — the viewer must
     not have fallen through to the `marker` session.
  FAILS IF: the banner stays `tmux-ok`/`tmux-empty`, or ZZMARKERZZ appears.

Check 2 — a full-height TUI keeps its top row
  a. Attach to cvtest/tui.
  b. SEE: the FIRST rendered row of the terminal begins with "top - ".
  FAILS IF: the first row is the "Tasks:" line (the trailing newline from
     capture-pane scrolled the title row out of the viewport).

Teardown
  tmux -L cvtest kill-server
"""


# --------------------------------------------------------------------------
# availability
# --------------------------------------------------------------------------


def _playwright_reason() -> str:
    if shutil.which("tmux") is None:
        return "tmux is not installed"
    try:
        from playwright.sync_api import sync_playwright  # noqa: F401
    except Exception as exc:  # pragma: no cover - environment dependent
        return f"playwright is not importable: {exc}"
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(args=["--no-sandbox"])
            browser.close()
    except Exception as exc:  # pragma: no cover - environment dependent
        return f"chromium is not launchable: {str(exc).splitlines()[0]}"
    return ""


PLAYWRIGHT_SKIP = _playwright_reason()

#: Applied to the two browser tests only — the manual-procedure test below must
#: still run (and print the procedure) on a host without a browser.
needs_browser = pytest.mark.skipif(
    bool(PLAYWRIGHT_SKIP),
    reason=f"{PLAYWRIGHT_SKIP}; use MANUAL_PROCEDURE in this file instead",
)


# --------------------------------------------------------------------------
# harness: real router + real static + a minimal page
# --------------------------------------------------------------------------

HARNESS_HTML = """<!doctype html>
<html><head><meta charset="utf-8"><title>tmux viewer harness</title>
<style>html,body{margin:0;background:#0b0d10;color:#d8dee9;font:12px system-ui}
#host{padding:8px}.tmux-banner{padding:4px 8px;font:12px system-ui}
.tmux-ok{background:#123}.tmux-empty{background:#332}.tmux-ended{background:#411}
.tmux-failed{background:#511}.tmux-banner span{margin-right:12px}</style>
</head><body><div id="host"></div>
<script src="/static/js/tmux.js"></script>
<script>
  var q = new URLSearchParams(location.search);
  window.ConvergeTmux.attach(document.getElementById('host'),
                             q.get('socket') || 'cvtest',
                             q.get('session') || 'victim');
</script>
</body></html>
"""


def _free_port() -> int:
    s = socketlib.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def _tmux(*args: str, check: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["tmux", "-L", SOCKET, *args],
        capture_output=True,
        text=True,
        env=tv._env(),
        check=check,
    )


@pytest.fixture(scope="module")
def server():
    import uvicorn
    from fastapi import FastAPI
    from fastapi.responses import HTMLResponse
    from fastapi.staticfiles import StaticFiles

    app = FastAPI()
    app.include_router(tv.router)  # the real router, no stubs
    app.mount("/static", StaticFiles(directory=str(APP_DIR / "static")), name="static")

    @app.get("/harness", response_class=HTMLResponse)
    def harness() -> str:
        return HARNESS_HTML

    port = _free_port()
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    uv_server = uvicorn.Server(config)
    thread = threading.Thread(target=uv_server.run, daemon=True)
    thread.start()
    deadline = time.time() + 20
    while not uv_server.started and time.time() < deadline:
        time.sleep(0.05)
    assert uv_server.started, "harness server did not start"
    print(f"\nharness server: http://127.0.0.1:{port} (in-process, torn down with this test module)")
    yield f"http://127.0.0.1:{port}"
    uv_server.should_exit = True
    thread.join(timeout=10)


@pytest.fixture(scope="module")
def sessions():
    _tmux("kill-server")
    _tmux("new", "-d", "-s", "victim", "while :; do echo VICTIMLINE; sleep 1; done", check=True)
    _tmux("new", "-d", "-s", "marker", f"while :; do echo {MARKER}; sleep 1; done", check=True)
    _tmux("new", "-d", "-s", "tui", "top", check=True)
    time.sleep(2.0)
    yield
    _tmux("kill-server")


@pytest.fixture(scope="module")
def browser():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        b = p.chromium.launch(args=["--no-sandbox"])
        yield b
        b.close()


def rendered_rows(page) -> list[str]:
    """The text xterm.js actually painted, row by row, from the DOM."""
    return page.evaluate(
        """() => Array.from(document.querySelectorAll('.xterm-rows > div'))
                     .map(d => d.innerText)"""
    )


def banner_class(page) -> str:
    return page.evaluate("() => (document.querySelector('.tmux-banner') || {}).className || ''")


# --------------------------------------------------------------------------
# 1. the silent re-target
# --------------------------------------------------------------------------


@needs_browser
def test_killed_session_renders_ended_and_never_another_session(server, sessions, browser):
    page = browser.new_page()
    page.goto(f"{server}/harness?socket={SOCKET}&session=victim", wait_until="load")

    page.wait_for_selector(".tmux-banner.tmux-ok", timeout=15000)
    page.wait_for_function(
        """() => Array.from(document.querySelectorAll('.xterm-rows > div'))
                      .some(d => d.innerText.includes('VICTIMLINE'))""",
        timeout=15000,
    )
    print(f"\nbefore kill: banner={banner_class(page)!r}")
    print(f"before kill: first rendered row={rendered_rows(page)[0]!r}")

    _tmux("kill-session", "-t", "=victim:")
    t0 = time.monotonic()
    page.wait_for_selector(".tmux-banner.tmux-ended", timeout=15000)
    elapsed = time.monotonic() - t0

    rows = rendered_rows(page)
    joined = "\n".join(rows)
    print(f"after kill:  banner={banner_class(page)!r} after {elapsed * 1000:.0f} ms")
    print(f"after kill:  ConvergeTmux.current()={page.evaluate('() => window.ConvergeTmux.current()')}")
    print(f"after kill:  marker {MARKER!r} present in rendered terminal: {MARKER in joined}")

    assert "tmux-ended" in banner_class(page), "loss must render ended"
    assert "tmux-ok" not in banner_class(page)
    assert "tmux-empty" not in banner_class(page), "a blank frame must never read as healthy"
    assert MARKER not in joined, "the viewer must never fall through to another session's pane"
    assert page.evaluate("() => window.ConvergeTmux.current().session") == "victim"
    page.close()


# --------------------------------------------------------------------------
# 2. the top-row loss
# --------------------------------------------------------------------------


@needs_browser
def test_full_height_tui_keeps_its_top_row(server, sessions, browser):
    page = browser.new_page()
    page.goto(f"{server}/harness?socket={SOCKET}&session=tui", wait_until="load")

    page.wait_for_selector(".tmux-banner.tmux-ok", timeout=15000)
    page.wait_for_function(
        """() => Array.from(document.querySelectorAll('.xterm-rows > div'))
                      .some(d => d.innerText.startsWith('top - '))""",
        timeout=15000,
    )

    rows = rendered_rows(page)
    print(f"\ntui: rendered {len(rows)} rows; first row={rows[0]!r}")
    print(f"tui: second row={rows[1]!r}")
    print(f"tui: ConvergeTmux.current()={page.evaluate('() => window.ConvergeTmux.current()')}")

    assert rows[0].startswith("top - "), (
        "the TUI's top row must be the first rendered row; if it is the 'Tasks:' "
        "line the trailing newline was not stripped"
    )
    grid = page.evaluate("() => window.ConvergeTmux.current()")
    assert grid["cols"] > 0 and grid["rows"] > 0, "the grid is sized from the pane geometry"
    page.close()


# --------------------------------------------------------------------------
# what runs when the browser cannot
# --------------------------------------------------------------------------


def test_manual_procedure_is_documented():
    """The stand-in when Playwright is unavailable is a real, checkable procedure."""
    assert "tmux-ended" in MANUAL_PROCEDURE
    assert "top - " in MANUAL_PROCEDURE
    assert "FAILS IF" in MANUAL_PROCEDURE
    if PLAYWRIGHT_SKIP:
        print(f"\nPlaywright unavailable ({PLAYWRIGHT_SKIP}). Manual procedure:\n{MANUAL_PROCEDURE}")


def _run_manual_notice() -> None:  # pragma: no cover - convenience
    print(MANUAL_PROCEDURE)


if __name__ == "__main__":  # pragma: no cover
    _run_manual_notice()
    print(asyncio.run(tv.list_sessions(SOCKET)))
