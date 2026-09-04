"""Rendered-browser regression test: the closed console must not widen the page.

The defect this pins (converge-c4s) was invisible to every API-level check and
to the existing rendered sweep, because the sweep only ever measured overflow
with the console **open**.  With the console **closed** the desktop grid gives
the pane a 0px column — and the page was still 11px wider than the viewport:

    scrollWidth 1291 vs clientWidth 1280 at a 1280x800 viewport

Two things did it, and both are only visible in a real browser:

1. ``.manager-console`` was ``position: static``, so an absolutely positioned
   descendant (the console form's ``.sr-only`` label) was laid out against the
   page, not against the pane, and escaped the pane's ``overflow: hidden``
   entirely.  That was 10 of the 11 pixels.
2. The pane's ``border-left: 1px`` is the pane's whole remaining width when the
   column is 0, and it sits at x=1280 — one pixel past the right edge.

The assertion below is the one from the item's acceptance: at 1280 wide with
the console closed, ``document.documentElement.scrollWidth <= clientWidth``.
It is checked at 390 too, and in both console states, so a fix that trades the
closed state for the open one cannot pass.

If Playwright or its Chromium build is unavailable the browser test skips with
the reason printed, and ``MANUAL_PROCEDURE`` below is the documented manual
check that stands in for it.
"""

from __future__ import annotations

import json
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

USER = "tester"

MANUAL_PROCEDURE = """
MANUAL PROCEDURE — run this by hand if Playwright is unavailable.
Each step says what you must SEE; seeing anything else is a failure.

Setup
  uv run --extra app python -m app.serve --host 127.0.0.1 --port 8788
  Open http://127.0.0.1:8788/ in a browser sized to exactly 1280 CSS px wide
  (devtools device toolbar, "Responsive", 1280 x 800).

Check — the closed console does not push the page sideways
  a. SEE: the Manager Console docked on the right.
  b. Click "Manager Console" in the top bar to CLOSE it.
  c. In the devtools console run:
       document.documentElement.scrollWidth + ' vs ' + document.documentElement.clientWidth
  d. SEE: the two numbers are equal (1280 vs 1280), and there is NO horizontal
     scrollbar along the bottom of the window.
  FAILS IF: scrollWidth is larger than clientWidth (it read 1291 vs 1280 before
     this fix), or the page can be scrolled sideways at all.

Check — the console still looks right in both states
  e. SEE, with the console open: the header reads "Manager Console" with the
     session name under it, and "● Connected"/"● Detached" and the × button sit
     inside the pane's right edge, not clipped and not overhanging.
  f. Repeat (b)-(d) at 390 x 844, where the console is a sheet rather than a dock.
"""


# --------------------------------------------------------------------------
# availability
# --------------------------------------------------------------------------


def _playwright_reason() -> str:
    if shutil.which("git") is None:
        return "git is not installed"
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

needs_browser = pytest.mark.skipif(
    bool(PLAYWRIGHT_SKIP),
    reason=f"{PLAYWRIGHT_SKIP}; use MANUAL_PROCEDURE in this file instead",
)


# --------------------------------------------------------------------------
# a project to serve, and the real app serving it
# --------------------------------------------------------------------------

VISION = """# Demo Vision (DRAFT)

## Where this is going

One place for direction and one place for operation.
"""

HIGHWAY = """# Highway — demo

Width 2.
"""

MANIFEST_HEAD = "lane\tworktree\tbranch\tbase\ttmux\tgoal\tlog\tstarted\n"


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "user.name=Test", "-c", "user.email=test@example.invalid", *args],
        cwd=repo,
        check=True,
        capture_output=True,
    )


@pytest.fixture(scope="module")
def project(tmp_path_factory) -> dict:
    """A small real repository and a real batch — never fixtures of the answers."""
    tmp_path = tmp_path_factory.mktemp("console-overflow")
    repo = tmp_path / "demo-repo"
    (repo / "docs").mkdir(parents=True)
    (repo / "docs" / "VISION.md").write_text(VISION, encoding="utf-8")
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "seed: the vision")

    batch = tmp_path / "hw-demo"
    (batch / "lanes" / "w1-alpha").mkdir(parents=True)
    (batch / "goals").mkdir()
    (batch / "HIGHWAY.md").write_text(HIGHWAY, encoding="utf-8")
    (batch / "goals" / "w1-alpha.md").write_text("# Lane alpha\n", encoding="utf-8")
    (batch / "lanes" / "w1-alpha" / "lane.log").write_text("working\n", encoding="utf-8")
    (batch / "lanes" / "w1-alpha" / "DONE.json").write_text(
        json.dumps({"status": "success", "summary": "Alpha landed."}), encoding="utf-8"
    )
    (batch / "manifest.tsv").write_text(
        MANIFEST_HEAD
        + f"w1-alpha\t{batch}/lanes/w1-alpha/demo-repo\tlane/w1-alpha\tdeadbee\t"
        f"hw__hw-demo__w1-alpha\t{batch}/goals/w1-alpha.md\t{batch}/lanes/w1-alpha/lane.log\t"
        "2026-09-01T10:00:00Z\n",
        encoding="utf-8",
    )

    conf = tmp_path / "converge-app.toml"
    conf.write_text(
        "[[managers]]\n"
        'id = "demo"\n'
        'name = "Demo manager"\n'
        f'batch_dir = "{batch}"\n'
        f'repos = ["{repo}"]\n'
        'tracker_project = ""\n'
        'tmux_socket = "test-socket-that-does-not-exist"\n',
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
    config = uvicorn.Config(made, host="127.0.0.1", port=port, log_level="warning")
    uv_server = uvicorn.Server(config)
    thread = threading.Thread(target=uv_server.run, daemon=True)
    thread.start()
    deadline = time.time() + 20
    while not uv_server.started and time.time() < deadline:
        time.sleep(0.05)
    assert uv_server.started, "app server did not start"
    print(f"\napp server: http://127.0.0.1:{port} (in-process, torn down with this test module)")
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


# --------------------------------------------------------------------------
# the measurement
# --------------------------------------------------------------------------

#: The acceptance measurement, plus diagnostics. ``scrollWidth`` vs
#: ``clientWidth`` is the assertion; ``past`` is only there so a failure names
#: candidate culprits instead of a bare number. A box in ``past`` may well be
#: harmless — one inside a deliberately clipped or scrollable container cannot
#: widen the page — which is exactly why nothing asserts on it.
MEASURE = """
() => {
  const de = document.documentElement;
  const rows = [];
  document.querySelectorAll('body, body *').forEach(el => {
    const s = getComputedStyle(el);
    if (s.display === 'none' || s.visibility === 'hidden') return;
    const r = el.getBoundingClientRect();
    if (r.right > de.clientWidth + 0.01) {
      rows.push(((el.id ? '#' + el.id : '') + '.' + String(el.className || el.tagName)).slice(0, 50)
                + ' right=' + Math.round(r.right));
    }
  });
  return {scrollWidth: de.scrollWidth, clientWidth: de.clientWidth,
          bodyScrollWidth: document.body.scrollWidth, past: rows.slice(0, 8)};
}
"""


def _is_closed(page) -> bool:
    return page.evaluate("() => document.querySelector('.body-grid').classList.contains('console-closed')")


def _set_console(page, want_open: bool) -> None:
    if _is_closed(page) != want_open:
        return
    page.click("#consoleToggle")
    page.wait_for_timeout(500)  # the grid column animates for .22s


def _boot(browser, server, project, width: int, height: int, errors: list[str]):
    sessions = auth.Sessions(auth.read_or_make_secret(project["secret"]))
    ctx = browser.new_context(viewport={"width": width, "height": height})
    ctx.add_cookies([{"name": auth.COOKIE, "value": sessions.issue(USER),
                      "domain": "127.0.0.1", "path": "/"}])
    page = ctx.new_page()
    page.on("console", lambda m: errors.append(f"console.{m.type}: {m.text}") if m.type == "error" else None)
    page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
    page.goto(server, wait_until="networkidle")
    page.wait_for_selector("#managerConsole", timeout=15000)
    return ctx, page


# --------------------------------------------------------------------------
# 1. the defect itself
# --------------------------------------------------------------------------


@needs_browser
@pytest.mark.parametrize("width,height", [(1280, 800), (390, 844)])
def test_closed_console_does_not_widen_the_page(server, project, browser, width, height):
    errors: list[str] = []
    ctx, page = _boot(browser, server, project, width, height, errors)

    _set_console(page, want_open=False)
    assert _is_closed(page), "the console must actually be closed for this to mean anything"
    closed = page.evaluate(MEASURE)
    print(f"\n[{width}] console CLOSED: scrollWidth={closed['scrollWidth']} "
          f"clientWidth={closed['clientWidth']} bodyScrollWidth={closed['bodyScrollWidth']}")
    if closed["past"]:
        print(f"[{width}] boxes past the right edge (diagnostic only): {closed['past']}")

    _set_console(page, want_open=True)
    assert not _is_closed(page)
    opened = page.evaluate(MEASURE)
    print(f"[{width}] console OPEN:   scrollWidth={opened['scrollWidth']} "
          f"clientWidth={opened['clientWidth']} bodyScrollWidth={opened['bodyScrollWidth']}")
    if opened["past"]:
        print(f"[{width}] boxes past the right edge (diagnostic only): {opened['past']}")
    print(f"[{width}] console errors: {errors or 'none'}")

    assert closed["scrollWidth"] <= closed["clientWidth"], (
        f"the CLOSED console widened the document: scrollWidth={closed['scrollWidth']} > "
        f"clientWidth={closed['clientWidth']}; past the edge: {closed['past']}"
    )
    assert opened["scrollWidth"] <= opened["clientWidth"], (
        f"the OPEN console widened the document: scrollWidth={opened['scrollWidth']} > "
        f"clientWidth={opened['clientWidth']}; past the edge: {opened['past']}"
    )
    assert not errors, "; ".join(errors[:3])
    ctx.close()


# --------------------------------------------------------------------------
# 2. the two rules that fix it, asserted where they are actually applied
# --------------------------------------------------------------------------


@needs_browser
def test_the_pane_clips_its_own_content_and_drops_its_divider_when_closed(server, project, browser):
    """The mechanism, not just the symptom — so a regression names its own cause."""
    errors: list[str] = []
    ctx, page = _boot(browser, server, project, 1280, 800, errors)

    _set_console(page, want_open=True)
    open_style = page.evaluate(
        """() => {
             const s = getComputedStyle(document.getElementById('managerConsole'));
             return {position: s.position, overflowX: s.overflowX, borderLeft: s.borderLeftWidth};
           }"""
    )
    print(f"\nopen:   {open_style}")

    _set_console(page, want_open=False)
    closed_style = page.evaluate(
        """() => {
             const c = document.getElementById('managerConsole');
             const s = getComputedStyle(c);
             const r = c.getBoundingClientRect();
             return {position: s.position, overflowX: s.overflowX, borderLeft: s.borderLeftWidth,
                     width: r.width, right: Math.round(r.right),
                     clientWidth: document.documentElement.clientWidth};
           }"""
    )
    print(f"closed: {closed_style}")

    assert open_style["position"] == "relative", (
        "the pane must be its own containing block, or an absolutely positioned "
        "descendant is laid out against the page and escapes overflow:hidden"
    )
    assert open_style["overflowX"] == "hidden"
    assert open_style["borderLeft"] == "1px", "the docked pane keeps its divider"
    assert closed_style["borderLeft"] == "0px", "a 0px column has no divider to draw"
    assert closed_style["right"] <= closed_style["clientWidth"], (
        f"the closed pane's own box sits past the right edge: {closed_style}"
    )
    assert not errors, "; ".join(errors[:3])
    ctx.close()


# --------------------------------------------------------------------------
# what runs when the browser cannot
# --------------------------------------------------------------------------


def test_manual_procedure_is_documented():
    """The stand-in when Playwright is unavailable is a real, checkable procedure."""
    assert "scrollWidth" in MANUAL_PROCEDURE
    assert "FAILS IF" in MANUAL_PROCEDURE
    assert "1280" in MANUAL_PROCEDURE and "390" in MANUAL_PROCEDURE
    if PLAYWRIGHT_SKIP:
        print(f"\nPlaywright unavailable ({PLAYWRIGHT_SKIP}). Manual procedure:\n{MANUAL_PROCEDURE}")


if __name__ == "__main__":  # pragma: no cover
    print(MANUAL_PROCEDURE)
