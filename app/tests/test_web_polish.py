"""Three web-body defects, fenced where each one actually shows.

All three were written down by earlier lanes that could not reach the file the
fix belonged in. Each is small; each was false in a way a steward would only
meet at the worst moment.

* **converge-9ke — the service worker's precache list had drifted.**
  `PRECACHE` in `app/static/sw.js` names every client module by hand, and it had
  fallen behind by four: `js/presence.js`, `js/tmux.js`, `js/render/collab.js`
  and `css/collab.css`. Online this is invisible — `/static/*` is cache-first
  with runtime caching, so each lands in the STATIC cache the first time it is
  fetched. The cold case is what the precache list exists for: a browser that
  installs the worker and goes offline *before* ever fetching `presence.js`.
  And the cost is not presence — `js/render/direction.js` **imports**
  `presence.js`, and a module whose import fails does not run, so the whole
  Direction surface would have been gone, offline, on a device that had done
  nothing wrong.

* **converge-nxf — on a phone the Manager Console covered Home's own list.**
  `console.css` makes the console a `position:fixed` sheet below 980px and
  `state.js` opens it by default, so at 390x844 it lay over everything below
  about y=197 — which is most of Home, including the list of manager sessions
  `experience.v1` Core 1 says Home *is*. Measured 2026-09-04 before the fix: a
  click on Home's tell-all control (rect [16,418,211,457]) was refused, with
  `#consoleBody` from `<aside id="managerConsole">` intercepting it.

* **converge-gf0 — `main.js` toasted "The console is read-only in this
  version."** Unreachable, because `render/console.js` owns both send paths and
  `preventDefault()`s each before a form submit can happen — and false, because
  the app has taken keystrokes since converge-tfu. A sentence kept alive only by
  an accident of event ordering is a sentence waiting to surface.

## What is proved here, and how

The source fences at the bottom need no browser and never skip. The rendered
tests drive a real Chromium against the real app at 1280 and 390.

For converge-9ke the rendered test does the one thing that actually shows the
cold case: it **empties the STATIC cache and re-installs the worker**, so the
only thing that can have written to that cache afterwards is `install`'s own
`cache.addAll(PRECACHE)` — the page is already loaded and fetches nothing. Then
it goes offline and opens the app. There is a negative control beside it:
evict `presence.js` from that same cache, reload offline, and watch the whole
Direction surface fail to come up. Without the control, "the Direction surface
renders" would not be evidence that precaching `presence.js` is what made it.

Both halves turn on one thing that is easy to assume and was wrong twice, so
both now assert it rather than assume it (converge-9a56): with the network
gone, the worker's cache must be the ONLY place `presence.js` can come from.
Two things break that quietly — Chromium's own HTTP cache, which emulated
offline does not invalidate, and a browser build on which `set_offline` never
reaches the service worker at all. The first is emptied and then proved empty
by asking for the module; the second is proved by asking for a URL nothing has
ever fetched, and where it answers, these two tests report that they cannot be
run rather than pass on a network that was never taken away.

What would falsify each item is written on each test.

If Playwright or its Chromium build is unavailable the browser tests skip with
the reason printed, and MANUAL_PROCEDURE below is the documented check that
stands in for them.
"""

from __future__ import annotations

import re
import shutil
import socket as socketlib
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app import assets, auth, serve  # noqa: E402

USER = "tester"

APP = Path(__file__).resolve().parents[1]
SW = APP / "static" / "sw.js"
TEMPLATES = APP / "templates"
STATIC = APP / "static"
JS = STATIC / "js"
MAIN_JS = JS / "main.js"
CONSOLE_JS = JS / "render" / "console.js"
CONSOLE_CSS = STATIC / "css" / "console.css"

#: The name `sw.js` gives its own static cache. Read from the worker rather than
#: repeated here, so a version bump cannot leave this test quietly checking a
#: cache nobody writes to any more.
STATIC_CACHE = re.search(r"const STATIC = '([^']+)'", SW.read_text(encoding="utf-8")).group(1)

#: converge-moe4: the revision THIS on-disk `app/static/` computes right now --
#: the same pure function `app/serve.py`'s `create_app()` calls, over the same
#: tree, so this test's expectations and the running server's own rendered
#: URLs can never independently drift from each other.
STATIC_REVISION = assets.compute_revision(STATIC)


def _versioned(entry: str) -> str:
    """The REAL key a browser's Cache Storage carries for one PRECACHE entry
    against the running server above -- `entry` unchanged for anything not
    under `/static/` (manifest, branding: never part of this revision)."""
    if not entry.startswith("/static/"):
        return entry
    return f"/static/{STATIC_REVISION}" + entry[len("/static"):]

#: The width below which `console.css` makes the console an OVERLAY rather than
#: a column. Read from the stylesheet for the same reason.
OVERLAY_MAX = 980

MANUAL_PROCEDURE = """
MANUAL PROCEDURE — run this by hand if Playwright is unavailable.
Each step says what you must SEE; seeing anything else is a failure.

Setup
  uv run --extra app python -m app.serve --host 127.0.0.1 --port 8788
  Open http://127.0.0.1:8788/ and sign in.

Check — Home is usable on a phone on arrival (converge-nxf)
  a. Size the window to exactly 390 x 844 CSS px and click the Converge logo.
  b. SEE: the list of manager sessions, and no dark console sheet over it.
  c. Tap a manager session card, and tap every control on Home, WITHOUT first
     dismissing anything.
  d. SEE: each one responds to the first tap.
  e. Open a manager session, so Direction is on screen.
  f. SEE: the console sheet is there, over the lower screen, exactly as before,
     and the Manager Console control still pushes it down and pulls it up.
  FAILS IF: anything on Home needs the sheet dismissed first, or the sheet is
     missing from Direction and Operation.

Check — the precache list carries every module (converge-9ke)
  g. In devtools > Application > Service Workers, click Unregister.
  h. In devtools > Application > Cache Storage, delete `converge-static-v4`.
     Then, in Application > Clear storage, tick ONLY "Cached images and files"
     and clear that too. It is a different cache and it is the browser's own;
     leaving it full is how step l passes without the worker doing anything.
  i. Reload once, then in the devtools console run:
       (await (await caches.open('converge-static-v4')).keys())
         .map(r => new URL(r.url).pathname).sort().join('\\n')
  j. SEE: an entry ending in /js/presence.js in that list (it reads
     /static/<revision>/js/presence.js -- <revision> is this server
     generation's own fingerprint, converge-moe4 -- any entry ending that
     way is the one to look for), alongside every other module.
  k. Tick Offline in devtools > Network, and reload.
  l. SEE: the Direction surface, with its document, not a broken page.
  FAILS IF: presence.js is absent from the list, or the page comes up empty
     offline with a module import error in the console.

Check — nothing says the console is read-only (converge-gf0)
  m. In the devtools console run:
       (await (await fetch('/static/js/main.js')).text()).includes('read-only')
  n. SEE: false.
  o. Type a line into the console field and press Enter.
  p. SEE: no toast saying the console is read-only in this version.
  FAILS IF: that sentence is in the file, or a steward can make it appear.
"""


# --------------------------------------------------------------------------
# availability
# --------------------------------------------------------------------------


def _playwright_reason() -> str:
    if shutil.which("git") is None:
        return "git is not installed"
    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:  # pragma: no cover - environment dependent
        return f"playwright is not importable: {exc}"
    try:
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
# two manager sessions over real repositories, and the real app
# --------------------------------------------------------------------------
#
# Two, because Home is "the list of manager sessions" and a list of one is a
# weak thing to claim is reachable.

VISION = """# Demo Vision (DRAFT)

## Where this is going

One place for direction and one place for operation.
"""

HIGHWAY = """# Highway — demo

Width 2.
"""

MANIFEST_HEAD = "lane\tworktree\tbranch\tbase\ttmux\tgoal\tlog\tstarted\n"

MANAGERS = ("alpha", "bravo")


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "user.name=Test", "-c", "user.email=test@example.invalid", *args],
        cwd=repo,
        check=True,
        capture_output=True,
    )


@pytest.fixture(scope="module")
def project(tmp_path_factory) -> dict:
    tmp_path = tmp_path_factory.mktemp("web-polish")
    blocks = []
    repos: dict[str, Path] = {}
    for mid in MANAGERS:
        repo = tmp_path / f"repo-{mid}"
        (repo / "docs").mkdir(parents=True)
        (repo / "docs" / "VISION.md").write_text(VISION, encoding="utf-8")
        _git(repo, "init", "-q", "-b", "main")
        _git(repo, "add", "-A")
        _git(repo, "commit", "-q", "-m", "seed: the vision")
        repos[mid] = repo

        batch = tmp_path / f"hw-{mid}"
        (batch / "goals").mkdir(parents=True)
        (batch / "HIGHWAY.md").write_text(HIGHWAY, encoding="utf-8")
        (batch / ".width").write_text("2\n", encoding="utf-8")
        (batch / "manifest.tsv").write_text(MANIFEST_HEAD, encoding="utf-8")

        blocks.append(
            "[[managers]]\n"
            f'id = "{mid}"\n'
            f'name = "Manager {mid}"\n'
            f'batch_dir = "{batch}"\n'
            f'repos = ["{repo}"]\n'
            'tracker_project = ""\n'
            'tmux_socket = "test-socket-that-does-not-exist"\n'
        )

    conf = tmp_path / "converge-app.toml"
    conf.write_text("".join(blocks), encoding="utf-8")
    # Never the real ~/.amplifier: a test must not move a steward's read point.
    return {"config": conf, "secret": tmp_path / "secret", "state": tmp_path / "state.json", "sessions": tmp_path / "sessions.json",
            "repos": repos}


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
        config_path=project["config"], secret_path=project["secret"], state_path=project["state"], sessions_path=project["sessions"]
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


# --------------------------------------------------------------------------
# driving
# --------------------------------------------------------------------------

#: Every control a steward can reach on Home, and whether the point they would
#: actually tap belongs to that control or to something lying over it.
#:
#: `elementFromPoint` is the whole check: an element moved off-screen by
#: `transform` still takes clicks where it was, and "is it drawn?" would answer
#: yes for a card the console sheet is sitting on top of. Each control is
#: scrolled into view first, because reaching a control by scrolling is reading,
#: not moving something out of the way.
HOME_REACHABLE = """
() => {
  const home = document.getElementById('homeView');
  if (!home || home.classList.contains('hidden')) return {error: 'Home is not on screen'};
  const controls = Array.from(home.querySelectorAll('button, a[href], input, select, textarea'))
    .filter(el => !el.disabled);
  const rows = [];
  for (const el of controls) {
    el.scrollIntoView({block: 'center'});
    const r = el.getBoundingClientRect();
    if (r.width === 0 || r.height === 0) continue;
    const hit = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
    const mine = !!hit && (hit === el || el.contains(hit) || hit.contains(el));
    rows.push({
      name: ((el.id ? '#' + el.id : '') + ' ' + (el.innerText || '').replace(/\\s+/g, ' ').trim())
              .trim().slice(0, 48),
      rect: [r.left, r.top, r.right, r.bottom].map(Math.round),
      reachable: mine,
      coveredBy: mine ? '' : (hit ? ((hit.id ? '#' + hit.id : '') + '.' +
                  String(hit.className || hit.tagName)).slice(0, 48) : '(nothing)'),
    });
  }
  return {count: rows.length, rows};
}
"""

#: What the console pane is doing right now, in the only terms that decide
#: whether it is in a steward's way.
CONSOLE_SHAPE = """
() => {
  const pane = document.getElementById('managerConsole');
  const grid = pane.parentElement;
  const s = getComputedStyle(pane);
  const r = pane.getBoundingClientRect();
  return {
    position: s.position,
    pointerEvents: s.pointerEvents,
    opacity: Number(s.opacity),
    rect: [r.left, r.top, r.right, r.bottom].map(Math.round),
    gridClosed: grid.classList.contains('console-closed'),
    togglePressed: document.getElementById('consoleToggle').getAttribute('aria-pressed'),
    toggleElsewhere: document.getElementById('consoleToggle').classList.contains('console-elsewhere'),
    toggleTitle: document.getElementById('consoleToggle').getAttribute('title') || '',
    screenHome: document.getElementById('app').classList.contains('screen-home'),
  };
}
"""


def _open(browser, server, project, width: int, height: int, errors: list[str]):
    sessions = auth.Sessions(auth.read_or_make_secret(project["secret"]))
    ctx = browser.new_context(viewport={"width": width, "height": height})
    ctx.add_cookies([{"name": auth.COOKIE, "value": sessions.issue(USER),
                      "domain": "127.0.0.1", "path": "/"}])
    page = ctx.new_page()
    page.on("console", lambda m: errors.append(f"console.{m.type}: {m.text}") if m.type == "error" else None)
    page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
    page.goto(server, wait_until="networkidle")
    page.wait_for_selector("#brandHome", timeout=15000)
    page.wait_for_selector("#consoleToggle", timeout=15000)
    return ctx, page


def _home(page) -> None:
    page.click("#brandHome")
    page.wait_for_selector(".home-manager-card", timeout=15000)


def _workspace(page) -> None:
    """Open a manager session, the way a steward does.

    The app boots to Home and always has since `experience.v1` Core 1 landed
    (converge-t30q): Home is the list of manager sessions, never an
    arbitrarily first-picked one. `_open()` therefore lands on Home, so a test
    that wants to look at the WORKSPACE has to open a manager first -- this
    used to be implicit in `_open()` and stopped being true underneath the one
    test below that never went Home before asking about it.
    """
    page.wait_for_selector(".home-manager-card", timeout=15000)
    page.click(".home-manager-card")
    page.wait_for_selector("#directionTab", timeout=15000)
    page.wait_for_function(
        "() => !document.getElementById('app').classList.contains('screen-home')",
        timeout=15000,
    )


# --------------------------------------------------------------------------
# 1. converge-nxf — Home is usable on a phone, on arrival
# --------------------------------------------------------------------------


@needs_browser
@pytest.mark.parametrize("width,height", [(1280, 800), (390, 844)])
def test_every_control_on_home_can_be_tapped_on_arrival(
    server, project, browser, width, height
) -> None:
    """converge-nxf's acceptance, at the width it is written for and beside it.

    WHAT WOULD FALSIFY THIS: any row below coming back `reachable: false` — the
    steward's tap would land on whatever `coveredBy` names instead.
    """
    errors: list[str] = []
    ctx, page = _open(browser, server, project, width, height, errors)
    _home(page)

    shape = page.evaluate(CONSOLE_SHAPE)
    reach = page.evaluate(HOME_REACHABLE)
    print(f"\n[{width}] console on Home: {shape}")
    assert "error" not in reach, reach.get("error")
    print(f"[{width}] Home offers {reach['count']} controls:")
    for row in reach["rows"]:
        mark = "ok " if row["reachable"] else "COVERED"
        print(f"[{width}]   {mark} {row['name']!r} {row['rect']} {row['coveredBy']}")

    cards = page.eval_on_selector_all(
        "#homeSessionGrid .home-manager-card", "els => els.length"
    )
    assert cards == len(MANAGERS), f"Home lists {cards} manager sessions, expected {len(MANAGERS)}"
    assert reach["count"] > 0, "Home offers no controls at all, so nothing was actually checked"

    covered = [row for row in reach["rows"] if not row["reachable"]]
    assert not covered, (
        f"at {width}px, {len(covered)} of Home's {reach['count']} controls cannot be tapped "
        f"without moving something else first: {covered}"
    )
    assert not errors, f"the browser logged: {errors}"
    ctx.close()


@needs_browser
@pytest.mark.parametrize("width,height", [(1280, 800), (390, 844)])
def test_the_console_pane_is_untouched_on_the_two_places_it_belongs_to(
    server, project, browser, width, height
) -> None:
    """The fix must move WHERE the sheet is drawn, and nothing else.

    `platform-web.v1` §6 keeps the sheet on the phone and the gesture that
    raises and lowers it; Core 1 keeps it beside Direction and Operation. So on
    the workspace nothing may have changed: the sheet is still `position:fixed`
    at 390, still takes pointer events, and the Manager Console control still
    pushes it down.

    WHAT WOULD FALSIFY THIS: the pane not being there on the workspace, or the
    toggle no longer closing it — either would mean the fix removed a behavior
    rather than relocating a sheet.
    """
    errors: list[str] = []
    ctx, page = _open(browser, server, project, width, height, errors)
    _workspace(page)
    # The pane is where the steward left it, and a fresh session leaves it down
    # (`state.js`: `consoleOpen: false`, converge-t30q). §6's gesture is what
    # raises it, so this test raises it with that gesture and then asks whether
    # the sheet is what §6 and Core 1 say -- rather than assuming an open pane
    # it never opened.
    if page.evaluate(CONSOLE_SHAPE)["togglePressed"] != "true":
        page.click("#consoleToggle", timeout=5000)
        page.wait_for_function(
            "() => getComputedStyle(document.getElementById('managerConsole')).pointerEvents !== 'none'",
            timeout=5000,
        )

    on_workspace = page.evaluate(CONSOLE_SHAPE)
    print(f"\n[{width}] console on the workspace: {on_workspace}")
    assert on_workspace["screenHome"] is False, "the shell thinks the workspace is Home"
    assert on_workspace["pointerEvents"] != "none", (
        f"the console pane is inert on the workspace at {width}px: {on_workspace}"
    )
    assert on_workspace["togglePressed"] == "true", (
        "the console is not open on the workspace, so this test proves nothing about the fix"
    )
    if width <= OVERLAY_MAX:
        assert on_workspace["position"] == "fixed", (
            f"§6's sheet is gone at {width}px: {on_workspace}"
        )

    # §6's own gesture, still there and still working.
    page.click("#consoleToggle", timeout=5000)
    page.wait_for_function(
        "() => getComputedStyle(document.getElementById('managerConsole')).pointerEvents === 'none'",
        timeout=5000,
    )
    pushed_down = page.evaluate(CONSOLE_SHAPE)
    print(f"[{width}] after the Manager Console control: {pushed_down}")
    assert pushed_down["gridClosed"], "the toggle no longer closes the console"
    assert pushed_down["togglePressed"] == "false", "the control does not say it is off"

    page.click("#consoleToggle", timeout=5000)
    page.wait_for_function(
        "() => getComputedStyle(document.getElementById('managerConsole')).pointerEvents !== 'none'",
        timeout=5000,
    )
    print(f"[{width}] pulled back up: {page.evaluate(CONSOLE_SHAPE)}")

    # And Home stows it without touching that state: the console is still open.
    _home(page)
    on_home = page.evaluate(CONSOLE_SHAPE)
    print(f"[{width}] the same console, on Home: {on_home}")
    assert on_home["screenHome"] is True, "the shell does not know it is on Home"
    assert on_home["gridClosed"] is False, (
        "Home closed the console rather than stowing the sheet — the pane would not be "
        f"as the steward left it when they open a manager session: {on_home}"
    )
    if width <= OVERLAY_MAX:
        assert on_home["pointerEvents"] == "none", (
            f"the sheet still takes clicks over Home at {width}px: {on_home}"
        )
        # converge-30aw. The STATE is untouched (gridClosed is False above), and
        # the CONTROL tells the truth about the screen it is on. This assertion
        # read `togglePressed == "true"` until 2026-09-04, which pinned exactly
        # the defect that item was filed for: measured then at 390x844 on Home,
        # `{pointerEvents: 'none', gridClosed: false, togglePressed: 'true'}`.
        assert on_home["togglePressed"] == "false", (
            "the Manager Console control reads 'on' over a screen with no pane drawn on it "
            f"at {width}px: {on_home}"
        )
        assert on_home["toggleElsewhere"], (
            f"the control is not marked as being about a pane that is elsewhere: {on_home}"
        )
        assert "beside Direction and Operation" in on_home["toggleTitle"], (
            f"the control does not say where the pane actually is: {on_home['toggleTitle']!r}"
        )
    else:
        assert on_home["pointerEvents"] != "none", (
            f"the console stopped being a pane beside Home at {width}px, where it covers "
            f"nothing and costs nothing: {on_home}"
        )
        # Where the pane IS drawn beside Home, nothing changed at all.
        assert on_home["togglePressed"] == "true", (
            f"the console is no longer open beside Home at {width}px: {on_home}"
        )
        assert not on_home["toggleElsewhere"], (
            f"the pane is right there at {width}px, so the control must not say otherwise: {on_home}"
        )

    assert not errors, f"the browser logged: {errors}"
    ctx.close()


@needs_browser
@pytest.mark.parametrize("width,height", [(390, 844)])
def test_tapping_the_console_control_on_home_changes_something_the_steward_sees(
    server, project, browser, width, height
) -> None:
    """converge-30aw: a control that appears dead is worse than one that is.

    On Home below the overlay width the pane is stowed, so the tap has nothing
    on THIS screen to redraw -- it turns the pane off for Direction and
    Operation, which is real but invisible from where the steward is standing.
    Measured 2026-09-04 before the fix: the tap changed nothing a steward could
    see, and the control read 'on' throughout.

    WHAT WOULD FALSIFY THIS: the tap producing no visible change at all, or the
    console's own open state being changed by merely standing on Home -- the
    pane must still be exactly as the steward left it when they open a manager
    session (converge-nxf).
    """
    errors: list[str] = []
    ctx, page = _open(browser, server, project, width, height, errors)
    _home(page)

    before = page.evaluate(CONSOLE_SHAPE)
    print(f"\n[{width}] on Home before the tap: {before}")
    assert before["pointerEvents"] == "none", "the sheet is not stowed, so this proves nothing"

    page.click("#consoleToggle", timeout=5000)
    page.wait_for_function(
        "() => /Manager Console/.test(document.getElementById('toast').textContent || '')",
        timeout=5000,
    )
    said = page.evaluate("() => document.getElementById('toast').textContent")
    after = page.evaluate(CONSOLE_SHAPE)
    print(f"[{width}] the app said: {said}")
    print(f"[{width}] on Home after the tap:  {after}")

    assert "beside Direction and Operation" in said, (
        f"the tap said nothing about where the pane actually is: {said!r}"
    )
    assert "closed there" in said or "open there" in said, (
        f"the tap did not say what it just did to the pane: {said!r}"
    )
    # The gesture still works: the state flipped, for the two screens the pane
    # belongs to.
    assert after["gridClosed"] != before["gridClosed"], (
        f"the tap did not change the console's own open state: {before} -> {after}"
    )
    # And the control still does not claim to be on over an empty screen.
    assert after["togglePressed"] == "false", (
        f"the control reads 'on' on Home after the tap: {after}"
    )

    assert not errors, f"the browser logged: {errors}"
    ctx.close()


# --------------------------------------------------------------------------
# 2. converge-9ke — the cold offline case the precache list exists for
# --------------------------------------------------------------------------

#: Empty the static cache, then install the worker again from nothing.
#:
#: After this the ONLY thing that can have written to that cache is `install`'s
#: own `cache.addAll(PRECACHE)`: the page is already loaded and fetches no
#: module. So the keys it comes back with ARE the precache list, actually
#: executed — which is also the only way to see that `addAll` did not reject.
#: It is all-or-nothing and `sw.js` swallows its rejection, so one bad path
#: would precache nothing at all, silently.
#:
#: The install is forced by registering the SAME worker under a script URL the
#: browser has not seen (`/sw.js?<tag>`; the server ignores the query and serves
#: the same file). Unregistering and re-registering `/sw.js` is NOT enough and
#: quietly proves nothing: measured here 2026-09-04, that path came back
#: `active: true` with **0 keys** — Chromium kept the byte-identical worker,
#: never ran `install`, and the emptied cache simply stayed empty.
FRESH_INSTALL = """
async ([name, tag]) => {
  await caches.delete(name);
  const reg = await navigator.serviceWorker.register('/sw.js?' + tag);
  const deadline = Date.now() + 20000;
  const arrived = () => reg.active && reg.active.scriptURL.includes(tag);
  while (!arrived() && Date.now() < deadline) {
    await new Promise(r => setTimeout(r, 100));
  }
  const cache = await caches.open(name);
  const keys = (await cache.keys()).map(r => new URL(r.url).pathname).sort();
  return {active: arrived(), scriptURL: reg.active ? reg.active.scriptURL : null, keys};
}
"""

EVICT = """
async ([name, path]) => {
  const cache = await caches.open(name);
  const gone = await cache.delete(new Request(new URL(path, location.origin).href));
  const keys = (await cache.keys()).map(r => new URL(r.url).pathname);
  return {deleted: gone, stillThere: keys.includes(path)};
}
"""

#: Something only the module graph can produce. The shell's markup is served
#: whole, so `#directionView` exists whether or not a single script ran; the
#: manager's name in the top bar is written by `render/top.js`, which is
#: reachable only if `main.js` and everything it imports actually loaded.
RENDERED = """
() => ({
  managerName: (document.getElementById('managerNameTop').innerText || '').trim(),
  sections: document.querySelectorAll('#documentModeContent *').length,
})
"""


def _forget_the_http_cache(page) -> None:
    """Empty Chromium's own HTTP cache, which is NOT the worker's cache.

    Without this the whole exercise proves nothing, and it took the negative
    control below to show it: measured 2026-09-04, with `presence.js` deleted
    from the worker's STATIC cache and the network emulated off, the app came up
    anyway — Chromium answered the worker's `fetch()` out of its own HTTP cache,
    where the module had been left by the online visit a moment earlier.
    Emulated offline does not invalidate that cache. Re-measured 2026-09-06 on
    Chromium 151 with this call skipped: the same false green came straight
    back, `{'managerName': 'Manager alpha', 'sections': 11}` (converge-9a56).

    `Network.enable` first, because `clearBrowserCache` is a Network-domain
    command and a domain that was never enabled is not obliged to act on one.

    A browser that installed the worker and went offline before ever fetching
    the module has neither copy, so neither may this test.
    """
    session = page.context.new_cdp_session(page)
    session.send("Network.enable")
    session.send("Network.clearBrowserCache")
    session.detach()


#: Is the network gone from the SERVICE WORKER's point of view? A URL nothing
#: has ever asked for cannot be in any cache, so a 200 for it can only be the
#: worker talking to the live server.
STILL_ON_THE_NETWORK = """
async () => {
  try {
    const res = await fetch('/api/boot?worker-offline-probe=' + Math.random());
    return {answered: !!(res && res.ok), status: res ? res.status : 0};
  } catch (err) { return {answered: false, status: 0, refused: String(err)}; }
}
"""

#: Can the page still get this module from anywhere? Offline and cold, `sw.js`
#: looks in the caches, misses, tries the network and has nothing to answer
#: with — so a 200 here means the browser kept a copy the eviction did not
#: reach, and the eviction did not model a cold browser.
STILL_REACHABLE = """
async (path) => {
  try {
    const res = await fetch(path);
    return {reachable: !!(res && res.ok), status: res ? res.status : 0};
  } catch (err) { return {reachable: false, status: 0, refused: String(err)}; }
}
"""


def _cannot_take_the_network_away(page) -> str:
    """Why this browser cannot be taken offline, or "" if it can.

    Measured 2026-09-06 (converge-9a56): on Chromium 131 (playwright 1.49.0)
    `ctx.set_offline(True)` did not reach the service worker at all — a
    never-seen `/api/boot?<nonce>` came back 200 with live JSON while the page
    reported `navigator.onLine === false`. The negative control below then
    failed (the module came off the live server, so the surface came up) and,
    worse, the positive test beside it PASSED for the wrong reason: the app came
    up offline because it was not offline.

    A check that cannot run reports that it cannot run. It does not pass on the
    strength of a network that was never taken away.
    """
    probe = page.evaluate(STILL_ON_THE_NETWORK)
    if not probe["answered"]:
        return ""
    try:
        version = page.context.browser.version
    except Exception:  # pragma: no cover - version is a courtesy, not the point
        version = "unknown"
    return (
        f"this browser does not take the network away from the service worker: a URL "
        f"nothing has ever fetched still answered {probe['status']} with the network "
        f"emulated off (chromium {version}). The cold case §10 is about cannot be "
        f"staged here; MANUAL_PROCEDURE in this file is the check that stands in for it"
    )


def _go_offline(ctx, page) -> None:
    """Take the network away, and open the app again with it gone.

    The re-assert after the reload is a fact about the harness, not the app:
    Chromium's emulated offline state does not survive a navigation — the new
    document reports `navigator.onLine === true` again while every request out
    of it still dies (measured in `test_offline.py`, 2026-09-04).
    """
    ctx.set_offline(True)
    page.reload(wait_until="load")
    page.wait_for_timeout(2000)
    ctx.set_offline(False)
    ctx.set_offline(True)
    page.wait_for_timeout(1200)


@needs_browser
def test_a_fresh_install_precaches_every_module_and_the_app_opens_offline(
    server, project, browser
) -> None:
    """converge-9ke's acceptance, driven through a real worker install.

    WHAT WOULD FALSIFY THIS: `/static/js/presence.js` missing from the keys a
    fresh install leaves behind, or the Direction surface not coming up with the
    network gone.
    """
    errors: list[str] = []
    ctx, page = _open(browser, server, project, 1280, 800, errors)
    page.evaluate("async () => { await navigator.serviceWorker.ready; }")
    page.reload(wait_until="networkidle")
    page.wait_for_function("() => !!navigator.serviceWorker.controller", timeout=15000)

    listed = _precache_entries()
    installed = page.evaluate(FRESH_INSTALL, [STATIC_CACHE, "cold-open"])
    print(f"\nfresh install of the worker, {STATIC_CACHE} emptied first: "
          f"active={installed['active']}, {len(installed['keys'])} keys "
          f"({installed['scriptURL']})")
    for key in installed["keys"]:
        print(f"  {key}")

    assert installed["active"], "the re-registered worker never became active"
    assert _versioned("/static/js/presence.js") in installed["keys"], (
        "a fresh install does not carry presence.js, so a browser that goes offline before "
        "ever fetching it loses render/direction.js with it — the whole Direction surface"
    )
    missing = [entry for entry in listed if _versioned(entry) not in installed["keys"]]
    assert not missing, (
        "install ran but these precache entries are not in the cache — `cache.addAll` is "
        f"all-or-nothing and sw.js swallows its rejection, so check they all resolve: {missing}"
    )

    _forget_the_http_cache(page)
    _go_offline(ctx, page)
    online = page.evaluate("() => navigator.onLine")
    assert online is False, "the harness failed to take the network away"
    blocked = _cannot_take_the_network_away(page)
    if blocked:
        pytest.skip(blocked)

    # What the acceptance turns on, asserted rather than assumed: the module is
    # obtainable with the network gone, and the only place it can be coming
    # from is the cache `install` filled. Without this the test would pass on a
    # browser that was never really offline.
    served = page.evaluate(STILL_REACHABLE, _versioned("/static/js/presence.js"))
    rendered = page.evaluate(RENDERED)
    print(f"offline (navigator.onLine={online}): {rendered}")
    print(f"offline, presence.js still answers from the worker's cache: {served}")
    assert served["reachable"], (
        "with the network gone the worker could not produce presence.js, so whatever the "
        f"app just rendered did not come from the precache this test is about: {served}"
    )
    assert rendered["managerName"], (
        "with the network gone the app did not come up at all — nothing rendered into the "
        f"top bar: {rendered}"
    )
    assert not [e for e in errors if "presence" in e], (
        f"the browser complained about presence.js offline: {errors}"
    )
    ctx.close()


@needs_browser
def test_without_presence_js_in_the_cache_the_direction_surface_dies_offline(
    server, project, browser
) -> None:
    """The negative control for the test above.

    Same fresh install, then `presence.js` alone is evicted from the cache
    before going offline. If the app came up anyway, precaching it would not be
    what makes the acceptance true and the test above would be measuring
    nothing.

    WHAT WOULD FALSIFY THIS: the app rendering normally with presence.js evicted
    — which would mean `render/direction.js` no longer imports it and this fence
    has gone stale.
    """
    errors: list[str] = []
    ctx, page = _open(browser, server, project, 1280, 800, errors)
    page.evaluate("async () => { await navigator.serviceWorker.ready; }")
    page.reload(wait_until="networkidle")
    page.wait_for_function("() => !!navigator.serviceWorker.controller", timeout=15000)

    installed = page.evaluate(FRESH_INSTALL, [STATIC_CACHE, "negative-control"])
    assert installed["active"], f"the re-registered worker never became active: {installed}"
    evicted = page.evaluate(EVICT, [STATIC_CACHE, _versioned("/static/js/presence.js")])
    print(f"\nevicted /static/js/presence.js: {evicted}")
    assert evicted["deleted"] and not evicted["stillThere"], f"eviction did not take: {evicted}"

    _forget_the_http_cache(page)
    _go_offline(ctx, page)
    blocked = _cannot_take_the_network_away(page)
    if blocked:
        pytest.skip(blocked)

    # The premise, checked before the conclusion is drawn from it. Evicting the
    # module from the worker's cache only stages the cold case if the browser
    # has no copy of its own left; when it has, the app comes up and the
    # assertion below reads as a statement about precaching when it is really a
    # statement about the harness. That is exactly how this check spent two days
    # calling the app wrong (converge-9a56).
    leftover = page.evaluate(STILL_REACHABLE, _versioned("/static/js/presence.js"))
    rendered = page.evaluate(RENDERED)
    print(f"offline, presence.js is still obtainable: {leftover}")
    print(f"offline with presence.js missing: {rendered}")
    print(f"the browser logged: {errors[:4] or 'nothing'}")
    assert not leftover["reachable"], (
        f"with presence.js evicted and the network gone the browser produced it anyway "
        f"({leftover}), so this control did not stage the cold browser it is about — one "
        "that installed the worker and went offline before ever fetching the module. That "
        "is a fact about the harness's caches, not about what precaching is worth"
    )
    assert not rendered["managerName"], (
        "the app came up offline without presence.js in the cache, so precaching it is not "
        f"what the acceptance turns on and the test above proves less than it claims: {rendered}"
    )
    ctx.close()


# --------------------------------------------------------------------------
# 3. converge-gf0 — nothing says the console is read-only
# --------------------------------------------------------------------------


@needs_browser
@pytest.mark.parametrize("width,height", [(1280, 800), (390, 844)])
def test_the_served_client_never_says_the_console_is_read_only(
    server, project, browser, width, height
) -> None:
    """Read out of the browser, not off the disk: this is the file it runs.

    WHAT WOULD FALSIFY THIS: the sentence appearing in any module the page
    loads, whatever a source fence says about the tree.
    """
    errors: list[str] = []
    ctx, page = _open(browser, server, project, width, height, errors)

    said = page.evaluate(
        """async () => {
          const out = {};
          for (const path of ['/static/js/main.js', '/static/js/render/console.js']) {
            const text = await (await fetch(path)).text();
            out[path] = /read[- ]only in this version/i.test(text);
          }
          return out;
        }"""
    )
    footer = page.inner_text(".console-readonly-note").strip()
    print(f"\n[{width}] 'read-only in this version' in what the browser fetched: {said}")
    print(f"[{width}] the console's own footer reads: {footer!r}")

    for path, present in said.items():
        assert not present, f"{path} still tells a steward the console is read-only"
    assert "not a chat" in footer.lower(), (
        f"the footer no longer says what the console is: {footer!r}"
    )
    assert "read-only" not in footer.lower(), f"the footer says read-only: {footer!r}"
    assert not errors, f"the browser logged: {errors}"
    ctx.close()


# --------------------------------------------------------------------------
# 4. source fences — these need no browser and never skip
# --------------------------------------------------------------------------


def _precache_entries() -> list[str]:
    """Every PRECACHE URL, in its LOGICAL (unversioned) form -- a plain
    literal and a `${STATIC_PREFIX}` template literal both come back the
    same shape. `app/assets.py` owns the parsing; see its own docstring."""
    return assets.precache_entries(SW.read_text(encoding="utf-8"))


def _referenced_by_templates() -> set[str]:
    """Every first-party `/static/` asset the served pages actually ask for,
    in its LOGICAL (unversioned) form.

    converge-moe4: `base.html`/`shell.html`/`collab.html` render every
    first-party static reference through `static_url('relpath')` rather
    than a literal `/static/...` href/src (see `app/assets.py`), so this
    reads the TEMPLATE SOURCE for `static_url(...)` calls -- never the
    rendered HTML, so no server is needed and this stays a source-only
    fence. A template this lane does not own that still writes a literal
    `/static/...` reference is caught too, exactly as before.
    """
    found: set[str] = set()
    for html in sorted(TEMPLATES.glob("*.html")):
        text = html.read_text(encoding="utf-8")
        for rel in re.findall(r"""static_url\(\s*['"]([^'"]+)['"]\s*\)""", text):
            found.add("/static/" + rel.lstrip("/"))
        for ref in re.findall(r"/static/[A-Za-z0-9_./-]+", text):
            found.add(ref)
    # The worker never precaches itself, and the vendored terminal is 488K that
    # only the terminal viewer needs — and by `platform-web.v1` §12 that viewer
    # is disconnected while the network is down anyway. Both stay runtime-cached.
    return {ref for ref in found
            if ref != "/static/sw.js" and not ref.startswith("/static/vendor/")}


def _module_graph(entries: set[str]) -> set[str]:
    """Every module reachable from those entry points, by following imports."""
    seen: set[str] = set()
    queue = [e for e in entries if e.endswith(".js")]
    while queue:
        url = queue.pop()
        if url in seen:
            continue
        seen.add(url)
        path = STATIC / url[len("/static/"):]
        if not path.is_file():
            continue
        for spec in re.findall(r"""(?:from|import)\s+['"]([^'"]+)['"]""",
                               path.read_text(encoding="utf-8")):
            if spec.startswith("/static/"):
                queue.append(spec)
            elif spec.startswith("."):
                queue.append("/static/" + str(
                    (path.parent / spec).resolve().relative_to(STATIC)
                ).replace("\\", "/"))
    return seen


def test_the_precache_list_carries_every_module_the_app_loads() -> None:
    """converge-9ke, derived rather than remembered.

    The list in `sw.js` is hand-kept and has drifted twice. This derives what
    the app actually loads — every `/static/` reference in the templates, plus
    every module reachable from those by following imports — so the third drift
    is caught here rather than by a steward with the network off.

    WHAT WOULD FALSIFY THIS: a module the app loads that PRECACHE does not name.
    """
    referenced = _referenced_by_templates()
    required = referenced | _module_graph(referenced)
    listed = set(_precache_entries())
    missing = sorted(required - listed)
    print(f"\nthe app loads {len(required)} first-party modules; PRECACHE names "
          f"{len(listed)} entries")
    for one in sorted(required):
        print(f"  {'ok ' if one in listed else 'MISSING'} {one}")
    assert not missing, (
        "these modules are loaded by the app and are not precached, so a browser that goes "
        f"offline before fetching one of them loses it and everything importing it: {missing}"
    )


def test_every_precached_url_is_answered_by_the_app(server) -> None:
    """`cache.addAll` is all-or-nothing, and `sw.js` swallows its rejection.

    One path in that list that 404s would precache NOTHING, silently, and the
    only symptom would be an app that does not open offline.

    converge-moe4: `_precache_entries()` reads `PRECACHE` back in its LOGICAL
    (unversioned) form -- the same shape every server has ever answered on,
    which a tab or Cache Storage entry from before this lane's URL-versioning
    fix may still be asking for, so that legacy path is checked here exactly
    as before. But it is no longer the URL a REAL browser today ever actually
    requests: `app/serve.py` renders `sw.js` with `STATIC_PREFIX` substituted
    to THIS server generation's own revision (`app/assets.py`'s
    `render_service_worker`), so the PRECACHE entries a running worker's
    `install` handler is actually told to fetch are the VERSIONED URLs
    (`_versioned()`, already used elsewhere in this file for the same reason).
    A legacy-only check here would miss a rendered `sw.js` whose versioned
    entries 404 while the never-served logical form still happily answers.

    WHAT WOULD FALSIFY THIS: any entry -- legacy or the versioned form a real
    worker actually precaches -- that the running app does not answer with 200.
    """
    import httpx

    answers = {}
    with httpx.Client(base_url=server, timeout=10.0) as client:
        for entry in _precache_entries():
            answers[f"legacy   {entry}"] = client.get(entry).status_code
            versioned = _versioned(entry)
            if versioned != entry:
                answers[f"versioned {versioned}"] = client.get(versioned).status_code
    for label, code in answers.items():
        print(f"  {code} {label}")
    bad = {label: code for label, code in answers.items() if code != 200}
    assert not bad, f"these precache entries are not served, so nothing would be precached: {bad}"


def test_main_js_no_longer_says_the_console_is_read_only() -> None:
    """converge-gf0's own falsification test, run exactly as the item words it:
    "grep for 'read-only in this version' in `app/static/js/main.js` returning
    nothing" — the whole file, comments included, so the sentence cannot come
    back as an explanation of itself.
    """
    hits = [line.strip() for line in MAIN_JS.read_text(encoding="utf-8").splitlines()
            if re.search(r"read[- ]only in this version", line, re.I)]
    assert not hits, f"main.js still carries the sentence: {hits}"


def test_main_js_has_no_second_submit_path_for_the_console() -> None:
    """The reason gf0 says to delete rather than reword.

    A second, differently-behaved submit path is the thing that would have made
    the old toast misfire in the first place. There must be exactly one owner of
    what a typed line does, and it is `render/console.js`.

    WHAT WOULD FALSIFY THIS: a `consoleForm` submit listener back in main.js.
    """
    source = MAIN_JS.read_text(encoding="utf-8")
    handler = re.search(r"""\$\(['"]consoleForm['"]\)\s*\.addEventListener""", source)
    near = source[handler.start():handler.start() + 90] if handler else ""
    assert handler is None, (
        "main.js binds the console form again, so what a typed line does has two owners "
        f"with different behaviour: {near!r}"
    )


def test_console_js_still_owns_both_ways_a_line_is_sent() -> None:
    """What actually keeps the form from ever submitting, now that main.js does not.

    `render/console.js` binds Enter on the field and click on the send button,
    and each calls `preventDefault()` before its own `sendLine()`. Those two
    calls are the whole guard: lose one and a steward's Enter reloads the page
    with the line in the query string.

    WHAT WOULD FALSIFY THIS: either handler losing its `preventDefault()`, or
    `sendLine` no longer being what they call.
    """
    source = CONSOLE_JS.read_text(encoding="utf-8")
    enter = re.search(r"c\.field\.addEventListener\('keydown'.*?\}\);", source, re.S)
    click = re.search(r"c\.send\.addEventListener\('click'.*?\}\);", source, re.S)
    assert enter, "console.js no longer binds Enter in the console field"
    assert click, "console.js no longer binds the console's send button"
    for name, block in (("Enter", enter.group(0)), ("the send button", click.group(0))):
        assert "preventDefault()" in block, (
            f"{name} no longer prevents the form submit, so a line typed into the console "
            "would navigate the page away instead of reaching the session"
        )
        assert "sendLine()" in block, f"{name} no longer sends the line"


def _without_comments(source: str) -> str:
    return re.sub(r"/\*.*?\*/", " ", source, flags=re.S)


def test_the_console_sheet_is_stowed_on_home_at_the_overlay_width() -> None:
    """converge-nxf, fenced in the stylesheet and the module that feeds it.

    A rendered check proves the two widths the contract names. This one says the
    reason out loud, so a later edit cannot quietly put the sheet back over the
    list Home is.

    WHAT WOULD FALSIFY THIS: the rule leaving the overlay media block, or
    `main.js` no longer marking which screen the shell is on.
    """
    css = _without_comments(CONSOLE_CSS.read_text(encoding="utf-8"))
    overlay = re.search(r"@media\s*\(max-width:\s*980px\)\s*\{(.*?)\n\}", css, re.S)
    assert overlay, "console.css no longer has the 980px block that makes the console an overlay"
    rule = re.search(r"\.screen-home\s+\.manager-console\s*\{([^}]*)\}", overlay.group(1))
    assert rule, (
        "nothing stows the console sheet on Home at the width where it is an overlay, so it "
        "lies over the list of manager sessions Home is"
    )
    body = rule.group(1)
    print(f"\nthe rule that keeps Home usable: .screen-home .manager-console {{{body.strip()}}}")
    assert re.search(r"pointer-events\s*:\s*none", body), (
        "the sheet is moved but still takes clicks where it was — `transform` alone does not "
        f"stop pointer events: {body!r}"
    )

    main = MAIN_JS.read_text(encoding="utf-8")
    assert "screen-home" in main, (
        "main.js does not mark which screen the shell is on, so the stylesheet rule above can "
        "never match"
    )
    assert re.search(r"classList\.toggle\('screen-home',\s*state\.screen === 'home'\)", main), (
        "the screen-home class is not derived from state.screen, so it can drift from what is "
        "actually on screen"
    )
