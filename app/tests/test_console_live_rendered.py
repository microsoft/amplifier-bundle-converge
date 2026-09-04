"""Rendered-browser proof for experience-console.v1 Core 3 and Core 4.

Two promises that only a real browser and a real tmux server together can prove:

**Core 3 — "what you type there is what the manager session receives."**  The
conformance kit says in its own words that it never attempts this: it can see
whether a route exists, not whether a line arrives.  Here a line is typed into
the console *in a browser*, and the assertion is made by asking **tmux itself**,
out of band, what is in the pane.  Nothing in the app is trusted to report it.

**Core 4 — "wide screen: a resizable pane. Small screen: a sliding tray."**  The
kit reads the stylesheet's rules; it says a rendered layout is not judged there.
Here the handle is actually dragged at 1280 and the column actually moves, and
at 390 the handle is gone and the pane is a tray — with the page never wider
than the viewport in either state (the regression converge-c4s pinned).

Everything runs on the tmux socket ``cvlive``; the only destructive command is
``tmux -L cvlive kill-server``.  Skips cleanly, with a manual procedure printed,
where tmux or a browser is unavailable.
"""

from __future__ import annotations

import shutil
import socket as socketlib
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app import auth, serve  # noqa: E402

SOCKET = "cvlive"
SESSION = "mgr"
USER = "tester"
TYPED = "ZZTYPEDINBROWSERZZ"

MANUAL_PROCEDURE = """
MANUAL PROCEDURE — run this by hand if tmux or Playwright is unavailable.
Each step says what you must SEE; seeing anything else is a failure.

Setup
  tmux -L cvlive new -d -s mgr cat
  Point ~/.amplifier/converge-app.toml at a manager with
    tmux_socket = "cvlive"
    manager_tmux = "cvlive:mgr"
  uv run --extra app python -m app.serve --host 127.0.0.1 --port 8788
  Open http://127.0.0.1:8788/ at exactly 1280 CSS px wide.

Check 1 — the console IS the session (Core 3)
  a. SEE: the Manager Console's input is typeable, not greyed out, and the
     footer note reads "not a chat — this pane is the manager session itself".
  b. Type ZZTYPEDINBROWSERZZ and press Enter.
  c. Run: tmux -L cvlive capture-pane -p -t '=mgr:'
  d. SEE: ZZTYPEDINBROWSERZZ in that output.
  FAILS IF: the input is disabled, or the pane does not contain the line —
     then the app relayed a summary, or nothing, rather than being the session.

Check 2 — the pane resizes when wide (Core 4)
  e. SEE: a 6px strip down the console's left edge that shows a col-resize
     cursor; drag it left.
  f. SEE: the console gets wider and the workspace narrower, and the page still
     has NO horizontal scrollbar.

Check 3 — it is a tray when small (Core 4)
  g. Resize the window to 390 wide.
  h. SEE: the console is a floating sheet at the bottom, the resize strip is
     gone, and closing it slides it away.

Teardown
  tmux -L cvlive kill-server
"""


# --------------------------------------------------------------------------
# availability
# --------------------------------------------------------------------------


def _skip_reason() -> str:
    if shutil.which("tmux") is None:
        return "tmux is not installed"
    if shutil.which("git") is None:
        return "git is not installed"
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(args=["--no-sandbox"])
            browser.close()
    except Exception as exc:  # pragma: no cover - environment dependent
        return f"chromium is not launchable: {str(exc).splitlines()[0]}"
    return ""


SKIP = _skip_reason()

needs_live = pytest.mark.skipif(
    bool(SKIP), reason=f"{SKIP}; use MANUAL_PROCEDURE in this file instead"
)


def test_manual_procedure_is_documented():
    """The stand-in when the live pieces are unavailable is a real procedure."""
    assert "capture-pane" in MANUAL_PROCEDURE
    assert "FAILS IF" in MANUAL_PROCEDURE
    if SKIP:
        print(f"\nLive check unavailable ({SKIP}). Manual procedure:\n{MANUAL_PROCEDURE}")


# --------------------------------------------------------------------------
# a real tmux server, a real project, the real app
# --------------------------------------------------------------------------


def _tmux(*args: str, check: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(["tmux", "-L", SOCKET, *args], capture_output=True, text=True, check=check)


def _pane() -> str:
    return _tmux("capture-pane", "-p", "-t", f"={SESSION}:").stdout


@pytest.fixture(scope="module")
def tmux_server():
    if SKIP:
        pytest.skip(SKIP)
    _tmux("kill-server")
    # `cat` echoes what it receives, so the pane's own text is the proof.
    _tmux("new", "-d", "-s", SESSION, "cat", check=True)
    time.sleep(1.0)
    yield
    _tmux("kill-server")


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "user.name=Test", "-c", "user.email=test@example.invalid", *args],
        cwd=repo,
        check=True,
        capture_output=True,
    )


@pytest.fixture(scope="module")
def project(tmp_path_factory) -> dict:
    tmp_path = tmp_path_factory.mktemp("console-live")
    repo = tmp_path / "demo-repo"
    (repo / "docs").mkdir(parents=True)
    (repo / "docs" / "VISION.md").write_text(
        "# Demo Vision (DRAFT)\n\n## Where this is going\n\nOne place each.\n", encoding="utf-8"
    )
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "seed: the vision")

    batch = tmp_path / "hw-demo"
    (batch / "lanes").mkdir(parents=True)
    (batch / "goals").mkdir()
    (batch / "HIGHWAY.md").write_text("# Highway — demo\n\nWidth 1.\n", encoding="utf-8")
    (batch / "manifest.tsv").write_text(
        "lane\tworktree\tbranch\tbase\ttmux\tgoal\tlog\tstarted\n", encoding="utf-8"
    )

    conf = tmp_path / "converge-app.toml"
    conf.write_text(
        "[[managers]]\n"
        'id = "demo"\n'
        'name = "Demo manager"\n'
        f'batch_dir = "{batch}"\n'
        f'repos = ["{repo}"]\n'
        'tracker_project = ""\n'
        f'tmux_socket = "{SOCKET}"\n'
        f'manager_tmux = "{SOCKET}:{SESSION}"\n',
        encoding="utf-8",
    )
    # Never the real ~/.amplifier: a test must not move a steward's read point.
    return {"config": conf, "secret": tmp_path / "secret", "state": tmp_path / "state.json"}


def _free_port() -> int:
    s = socketlib.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


@pytest.fixture(scope="module")
def server(project):
    import uvicorn

    made = serve.create_app(
        config_path=project["config"], secret_path=project["secret"], state_path=project["state"]
    )
    port = _free_port()
    uv_server = uvicorn.Server(uvicorn.Config(made, host="127.0.0.1", port=port, log_level="warning"))
    thread = threading.Thread(target=uv_server.run, daemon=True)
    thread.start()
    deadline = time.time() + 20
    while not uv_server.started and time.time() < deadline:
        time.sleep(0.05)
    assert uv_server.started, "app server did not start"
    print(f"\napp server: http://127.0.0.1:{port} (in-process, torn down with this module)")
    yield f"http://127.0.0.1:{port}"
    uv_server.should_exit = True
    thread.join(timeout=10)


@pytest.fixture(scope="module")
def browser():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        b = p.chromium.launch(args=["--no-sandbox"])
        yield b
        b.close()


MEASURE = """
() => {
  const de = document.documentElement;
  return {scrollWidth: de.scrollWidth, clientWidth: de.clientWidth};
}
"""


def _boot(browser, project, server, width, height, errors):
    sessions = auth.Sessions(auth.read_or_make_secret(project["secret"]))
    ctx = browser.new_context(viewport={"width": width, "height": height})
    ctx.add_cookies(
        [{"name": auth.COOKIE, "value": sessions.issue(USER), "domain": "127.0.0.1", "path": "/"}]
    )
    page = ctx.new_page()
    page.on("console", lambda m: errors.append(f"console.{m.type}: {m.text}") if m.type == "error" else None)
    page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
    page.goto(server, wait_until="networkidle")
    page.wait_for_selector("#managerConsole", timeout=15000)
    page.wait_for_timeout(800)  # the first capture tick
    return ctx, page


def _console_column(page) -> float:
    return page.evaluate(
        "() => parseFloat(getComputedStyle(document.querySelector('.body-grid'))"
        ".gridTemplateColumns.split(' ')[2])"
    )


# --------------------------------------------------------------------------
# Core 3 — the console IS the session
# --------------------------------------------------------------------------


@needs_live
def test_the_console_takes_the_keyboard(tmux_server, project, server, browser):
    errors: list[str] = []
    ctx, page = _boot(browser, project, server, 1280, 800, errors)

    live = page.evaluate(
        """() => {
          const form = document.getElementById('consoleForm');
          const field = form.querySelector('input, textarea');
          const send = form.querySelector('button[type="submit"]');
          const note = document.querySelector('.console-readonly-note');
          const view = window.ConvergeTmux && window.ConvergeTmux.current();
          return {field: !field.disabled, send: !send.disabled,
                  note: note ? note.textContent.trim() : '',
                  attached: view ? view.socket + ':' + view.session : null,
                  writable: view ? view.writable : null};
        }"""
    )
    print(f"\nconsole controls: {live}")
    print(f"console errors: {errors or 'none'}")

    assert live["field"], "the console's input must be typeable, or the pane is not the session"
    assert live["send"], "its send control must be live"
    assert live["attached"] == f"{SOCKET}:{SESSION}", "attached to the manager's own session"
    assert live["writable"] is True, "the terminal itself must take keystrokes too"
    assert "not a chat" in live["note"], (
        "the pane must say what it is; clause 9 needs the app to say it is not a native chat"
    )
    ctx.close()


@needs_live
def test_a_line_typed_in_the_browser_arrives_in_the_manager_session(
    tmux_server, project, server, browser
):
    """The round trip the conformance kit says it will not attempt."""
    errors: list[str] = []
    ctx, page = _boot(browser, project, server, 1280, 800, errors)

    before = _pane()
    assert TYPED not in before

    field = page.locator("#consoleForm input")
    field.fill(TYPED)
    field.press("Enter")

    deadline = time.time() + 8
    text = ""
    while time.time() < deadline:
        text = _pane()
        if TYPED in text:
            break
        time.sleep(0.2)

    print(f"\ntmux -L {SOCKET} capture-pane -p -t '={SESSION}:' says:")
    print("  " + "\n  ".join(ln for ln in text.splitlines() if ln.strip())[:400])
    print(f"console errors: {errors or 'none'}")

    assert TYPED in text, (
        "the line typed in the browser never reached the tmux session — the pane is showing "
        "the session but is not it"
    )
    assert page.evaluate("() => document.querySelector('#consoleForm input').value") == "", (
        "a delivered line clears the field; a kept line would mean it was not sent"
    )
    # And the app shows it because the PANE echoed it, not because we typed it.
    page.wait_for_timeout(1200)
    on_screen = page.evaluate("() => document.querySelector('#consoleBody').innerText")
    print(f"the app's own terminal shows it: {TYPED in on_screen}")
    assert TYPED in on_screen, "the next capture of the pane must bring the line back"
    assert not errors, f"the page reported errors: {errors}"
    ctx.close()


# --------------------------------------------------------------------------
# Core 4 — a resizable pane when wide, a tray when small
# --------------------------------------------------------------------------


@needs_live
def test_the_pane_resizes_at_1280(tmux_server, project, server, browser):
    errors: list[str] = []
    ctx, page = _boot(browser, project, server, 1280, 800, errors)

    handle = page.locator(".console-resize")
    assert handle.count() == 1, "a wide screen offers a resize handle"
    box = handle.bounding_box()
    assert box is not None and box["width"] > 0, "the handle must be a real, hittable strip"

    before = _console_column(page)
    page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
    page.mouse.down()
    page.mouse.move(box["x"] - 140, box["y"] + box["height"] / 2, steps=8)
    page.mouse.up()
    page.wait_for_timeout(500)  # the grid column animates for .22s
    after = _console_column(page)
    measured = page.evaluate(MEASURE)

    print(f"\nconsole column: {before:.0f}px -> {after:.0f}px after dragging 140px left")
    print(f"page after resize: scrollWidth={measured['scrollWidth']} clientWidth={measured['clientWidth']}")
    print(f"console errors: {errors or 'none'}")

    assert after > before + 100, (
        f"dragging the handle must widen the pane; it went {before:.0f} -> {after:.0f}"
    )
    assert measured["scrollWidth"] <= measured["clientWidth"], (
        "a resized pane must not push the page sideways"
    )
    assert not errors, f"the page reported errors: {errors}"
    ctx.close()


@needs_live
def test_the_pane_is_a_dismissible_tray_at_390(tmux_server, project, server, browser):
    errors: list[str] = []
    ctx, page = _boot(browser, project, server, 390, 844, errors)

    shape = page.evaluate(
        """() => {
          const pane = document.getElementById('managerConsole');
          const handle = pane.querySelector('.console-resize');
          return {position: getComputedStyle(pane).position,
                  handle: handle ? getComputedStyle(handle).display : 'absent'};
        }"""
    )
    open_measure = page.evaluate(MEASURE)
    page.click("#consoleToggle")
    page.wait_for_timeout(500)
    closed = page.evaluate(
        "() => document.querySelector('.body-grid').classList.contains('console-closed')"
    )
    closed_measure = page.evaluate(MEASURE)

    print(f"\n[390] pane: {shape}")
    print(f"[390] open:   scrollWidth={open_measure['scrollWidth']} clientWidth={open_measure['clientWidth']}")
    print(f"[390] closed: scrollWidth={closed_measure['scrollWidth']} clientWidth={closed_measure['clientWidth']}")
    print(f"console errors: {errors or 'none'}")

    assert shape["position"] == "fixed", "a tray floats over the places rather than taking a column"
    assert shape["handle"] == "none", "a full-width tray is not dragged, so it offers no handle"
    assert closed, "the tray gets out of the way on demand"
    for name, m in (("open", open_measure), ("closed", closed_measure)):
        assert m["scrollWidth"] <= m["clientWidth"], f"the {name} tray widened the page: {m}"
    assert not errors, f"the page reported errors: {errors}"
    ctx.close()
