"""Rendered-browser check: the shell's two writes are REACHABLE, at both widths.

Two defects this file fences, both measured against the running app on
2026-09-04 before the fix:

* **converge-nng — on a phone the Feedback write could not be started at all.**
  `app/static/css/shell.css` hid `.feedbackButton` below 980px and every
  `.icon-label-button` below 520px, and `#feedbackButton` is the only way into
  the feedback dialog (`main.js` wires `openFeedback` to it and to nothing
  else). Measured at 390x844: `display: none`, a 0x0 rect. One of the five
  writes `platform-web.v1` Core 1 requires was simply absent at one of the two
  widths §14 names — and `experience.v1` §11's subtraction test says a shape
  that removes a behavior is a divergence, not an idiom.
  Measured in the same run at 1280x800: the control was drawn, but one shared
  `::after { content:"Console" }` gave it the CONSOLE's word — so the laptop
  and the phone did not "show the same words" (`platform-web.v1` §4) even
  where both drew a control.

* **converge-are — Home listed the manager sessions and offered no way to tell
  them all at once.** `experience.v1` Core 1 makes Home the list of manager
  sessions; `experience-operation.v1` Core 13 asks that one message reach every
  one of them. converge-q66 put that control on the Operation surface, leaving
  a steward standing in front of the list itself with nothing on it. Measured:
  no such control in the Home hero at either width.

So this drives a real Chromium against the real app, at 1280 and at 390, and

* finds the Feedback control on the page, inside the viewport, wearing its own
  word, on Home and on the workspace alike;
* clicks it through and reads the file the write left on disk;
* clicks Home's "Tell all manager sessions" through and counts ONE feedback
  file per manager session listed;
* and checks nothing widens the page and nothing lands in the browser's log.

If Playwright or its Chromium build is unavailable the browser tests skip with
the reason printed, and MANUAL_PROCEDURE below is the documented manual check
that stands in for it. The source-level fences at the bottom need no browser
and never skip.
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

from app import auth, data, serve  # noqa: E402

USER = "tester"

#: The word each top-bar control must be read in, at every width. The point is
#: not the string: it is that neither control may wear the other's word.
FEEDBACK_WORD = "Feedback"
CONSOLE_WORD = "Console"

MANUAL_PROCEDURE = """
MANUAL PROCEDURE — run this by hand if Playwright is unavailable.
Each step says what you must SEE; seeing anything else is a failure.

Setup
  uv run --extra app python -m app.serve --host 127.0.0.1 --port 8788
  Open http://127.0.0.1:8788/.

Check — the Feedback write can be started on a phone (converge-nng)
  a. Size the window to exactly 390 x 844 CSS px.
  b. SEE: in the top bar, a control reading "Feedback", whole, not cut off by
     the right edge of the window.
  c. Click it.
  d. SEE: a dialog headed "Tell the manager what you noticed".
  e. Type a sentence and click "Send feedback".
  f. SEE: a dated file under <repo>/.converge/feedback/ containing it.
  FAILS IF: the control is not drawn at 390, cannot be clicked, reads any word
     other than "Feedback", or nothing lands on disk.

Check — the two top-bar controls do not wear each other's word
  g. At 1280 x 800, read the two controls at the top right.
  h. SEE: one reads "Feedback" and the other reads "Console".
  FAILS IF: both read the same word.

Check — Home tells every manager session at once (converge-are)
  i. Click the Converge logo to reach Home. SEE: the list of manager sessions,
     and beside the "decisions across all managers" count, a control reading
     "Tell all manager sessions".
  j. Click it, type a sentence, click "Tell them all".
  k. SEE: one new dated file under EVERY listed manager's own
     <repo>/.converge/feedback/, each containing that sentence.
  FAILS IF: the control is absent from Home, or the message reaches fewer
     sessions than the list shows.

Check — nothing widens the page
  l. In the devtools console run:
       document.documentElement.scrollWidth + ' vs ' + document.documentElement.clientWidth
  m. SEE: the two numbers are equal, at 1280 x 800 and again at 390 x 844, on
     Home and on the workspace alike.
  FAILS IF: scrollWidth is larger, or the page scrolls sideways.
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
# two manager sessions, each with its own repository, and the real app
# --------------------------------------------------------------------------
#
# Two, because "tell them all" is only a claim worth checking when there is
# more than one of them; and each with its OWN repository, because feedback is
# written into the manager's repository and one file per session is exactly
# what converge-are's acceptance asks to see.

VISION = """# Demo Vision (DRAFT)

## Where this is going

One place for direction and one place for operation.
"""

HIGHWAY = """# Highway — demo

Width 4.
"""

MANIFEST_HEAD = "lane\tworktree\tbranch\tbase\ttmux\tgoal\tlog\tstarted\n"

MANAGERS = ("alpha", "bravo")

COUNTS = {"TOTAL": 21, "READY": 4, "BLOCKED": 1, "RESOLVED": 16}


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "user.name=Test", "-c", "user.email=test@example.invalid", *args],
        cwd=repo,
        check=True,
        capture_output=True,
    )


@pytest.fixture(scope="module")
def project(tmp_path_factory) -> dict:
    tmp_path = tmp_path_factory.mktemp("shell-home")
    repos: dict[str, Path] = {}
    blocks = []
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
        (batch / ".width").write_text("4\n", encoding="utf-8")
        (batch / "manifest.tsv").write_text(MANIFEST_HEAD, encoding="utf-8")

        blocks.append(
            "[[managers]]\n"
            f'id = "{mid}"\n'
            f'name = "Manager {mid}"\n'
            f'batch_dir = "{batch}"\n'
            f'repos = ["{repo}"]\n'
            'tracker_project = "demo-project"\n'
            'tmux_socket = "test-socket-that-does-not-exist"\n'
        )

    conf = tmp_path / "converge-app.toml"
    conf.write_text("".join(blocks), encoding="utf-8")
    # Never the real ~/.amplifier: a test must not move a steward's read point.
    return {"config": conf, "secret": tmp_path / "secret", "state": tmp_path / "state.json",
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

    patch = pytest.MonkeyPatch()
    # Two seams, both facts about this machine rather than about the shell:
    # which tmux sessions are alive, and what the work queue would answer.
    patch.setattr(data, "tmux_sessions", lambda socket: set())
    patch.setattr(data, "tracker_counts", lambda mc: dict(COUNTS))

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
    patch.undo()


@pytest.fixture(scope="module")
def browser():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        b = p.chromium.launch(args=["--no-sandbox"])
        yield b
        b.close()


# --------------------------------------------------------------------------
# what the browser is asked
# --------------------------------------------------------------------------

#: Everything drawn that reaches past the viewport's right edge, named. An
#: empty list is the only passing answer.
MEASURE = """
() => {
  const de = document.documentElement;
  const past = [];
  document.querySelectorAll('body, body *').forEach(el => {
    const s = getComputedStyle(el);
    if (s.display === 'none' || s.visibility === 'hidden') return;
    const r = el.getBoundingClientRect();
    if (r.right > de.clientWidth + 0.01) {
      past.push(((el.id ? '#' + el.id : '') + '.' + String(el.className || el.tagName)).slice(0, 50)
                + ' right=' + Math.round(r.right));
    }
  });
  return {scrollWidth: de.scrollWidth, clientWidth: de.clientWidth, past: past.slice(0, 8)};
}
"""

#: A control as the eye meets it: is it drawn, where, and in what word. The
#: word may arrive from the element's own text or from CSS `content`, so both
#: are read and the answer is whichever is actually there.
CONTROL = """
(id) => {
  const el = document.getElementById(id);
  if (!el) return null;
  const de = document.documentElement;
  const style = getComputedStyle(el);
  const rect = el.getBoundingClientRect();
  const after = getComputedStyle(el, '::after').content;
  const before = getComputedStyle(el, '::before').content;
  const clean = (v) => (!v || v === 'none' || v === 'normal') ? '' : v.replace(/^"|"$/g, '');
  const word = [(el.innerText || '').trim(), clean(before), clean(after)].filter(Boolean).join(' ').trim();
  return {
    display: style.display,
    drawn: rect.width > 0 && rect.height > 0,
    rect: [rect.left, rect.top, rect.right, rect.bottom].map(Math.round),
    inside: rect.left >= -0.01 && rect.top >= -0.01
            && rect.right <= de.clientWidth + 0.01 && rect.bottom <= de.clientHeight + 0.01,
    word,
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
    # Boot lands on the workspace; the shell is the same chrome on both screens.
    page.wait_for_selector("#feedbackButton", timeout=15000)
    return ctx, page


def _home(page) -> None:
    page.click("#brandHome")
    page.wait_for_selector(".home-manager-card", timeout=15000)


def _push_the_console_sheet_down(page, width: int) -> bool:
    """On a phone the Manager Console is a sheet lying over the lower screen.

    `console.css` makes it `position:fixed`, `z-index:50`, `bottom:6px`,
    `height:76vh` below 520px — and `state.js` opens it by default — so at
    390x844 it covers everything below about y=197. Measured 2026-09-04:
    a click on Home's tell-all control (rect [16,418,211,457]) is intercepted
    by `#consoleBody`.

    `platform-web.v1` §6 names exactly this gesture — "on the phone you pull it
    up when you want it and push it down when you do not" — so pushing it down
    is what a steward does, not a workaround. That the sheet is UP on arrival,
    covering Home's own list of manager sessions, is a separate defect in
    another lane's files (`app/static/css/console.css`, `app/static/js/state.js`)
    and is filed rather than patched here.
    """
    if width > 520:
        return False
    page.click("#consoleToggle", timeout=5000)
    page.wait_for_function(
        "() => getComputedStyle(document.getElementById('managerConsole')).pointerEvents === 'none'",
        timeout=5000,
    )
    print(f"[{width}] the Manager Console sheet was pushed down first (platform-web.v1 §6)")
    return True


def _feedback_files(repo: Path) -> list[Path]:
    folder = repo / ".converge" / "feedback"
    return sorted(folder.glob("*.md")) if folder.is_dir() else []


# --------------------------------------------------------------------------
# 1. converge-nng — the Feedback control is on the page, at both widths
# --------------------------------------------------------------------------


@needs_browser
@pytest.mark.parametrize("width,height", [(1280, 800), (390, 844)])
@pytest.mark.parametrize("screen", ["workspace", "home"])
def test_the_feedback_control_is_drawn_whole_and_in_its_own_word(
    server, project, browser, width, height, screen
) -> None:
    errors: list[str] = []
    ctx, page = _open(browser, server, project, width, height, errors)
    if screen == "home":
        _home(page)

    feedback = page.evaluate(CONTROL, "feedbackButton")
    console = page.evaluate(CONTROL, "consoleToggle")
    print(f"\n[{width} · {screen}] feedback: {feedback}")
    print(f"[{width} · {screen}] console:  {console}")

    assert feedback is not None, "#feedbackButton is not in the document at all"
    assert feedback["drawn"], (
        f"the Feedback control is not drawn at {width}px (display: {feedback['display']}) — "
        "the feedback write cannot be started here, and it is the only way into the dialog"
    )
    assert feedback["inside"], (
        f"the Feedback control is cut off at {width}px: rect {feedback['rect']} against a "
        f"{width}x{height} viewport"
    )
    assert FEEDBACK_WORD.lower() in feedback["word"].lower(), (
        f"the Feedback control reads {feedback['word']!r} at {width}px, not {FEEDBACK_WORD!r}"
    )
    assert CONSOLE_WORD.lower() not in feedback["word"].lower(), (
        f"the Feedback control is wearing the Console's word at {width}px: {feedback['word']!r}"
    )
    assert console and CONSOLE_WORD.lower() in console["word"].lower(), (
        f"the Manager Console control reads {console and console['word']!r} at {width}px"
    )

    assert not errors, f"the browser logged: {errors}"
    ctx.close()


@needs_browser
@pytest.mark.parametrize("width,height", [(1280, 800), (390, 844)])
@pytest.mark.parametrize("screen", ["workspace", "home"])
def test_the_feedback_control_opens_the_feedback_dialog(
    server, project, browser, width, height, screen
) -> None:
    errors: list[str] = []
    ctx, page = _open(browser, server, project, width, height, errors)
    if screen == "home":
        _home(page)

    # Playwright's own actionability checks are the point of this click: it
    # refuses a control that is invisible, unstable, disabled, or covered by
    # something else. "Present in the DOM" was never the claim.
    page.click("#feedbackButton", timeout=5000)
    page.wait_for_selector("#feedbackText", timeout=5000)
    title = page.inner_text("#dialogTitle").strip()
    print(f"\n[{width} · {screen}] clicking Feedback opened: {title!r}")
    assert "noticed" in title.lower(), f"clicking Feedback opened {title!r}"

    assert not errors, f"the browser logged: {errors}"
    ctx.close()


@needs_browser
def test_the_feedback_write_finishes_from_the_phone(server, project, browser) -> None:
    """converge-nng's acceptance, carried through to the file on disk."""
    errors: list[str] = []
    ctx, page = _open(browser, server, project, 390, 844, errors)
    repo = project["repos"][MANAGERS[0]]
    before = {p.name for p in _feedback_files(repo)}

    said = "the lane words on this page do not match the contract"
    page.click("#feedbackButton", timeout=5000)
    page.wait_for_selector("#feedbackText", timeout=5000)
    page.fill("#feedbackText", said)
    page.click("#dialogActions button:has-text('Send feedback')", timeout=5000)

    landed = None
    deadline = time.time() + 10
    while time.time() < deadline:
        fresh = [p for p in _feedback_files(repo) if p.name not in before]
        if fresh and said in fresh[-1].read_text(encoding="utf-8"):
            landed = fresh[-1]
            break
        time.sleep(0.2)

    print(f"\n[390] feedback landed at: {landed}")
    assert landed is not None, (
        f"nothing new under {repo / '.converge' / 'feedback'} after sending feedback at 390px"
    )
    print(landed.read_text(encoding="utf-8"))
    assert not errors, f"the browser logged: {errors}"
    ctx.close()


# --------------------------------------------------------------------------
# 2. converge-are — Home tells every manager session at once
# --------------------------------------------------------------------------


@needs_browser
@pytest.mark.parametrize("width,height", [(1280, 800), (390, 844)])
def test_home_tells_every_listed_manager_session_at_once(
    server, project, browser, width, height
) -> None:
    errors: list[str] = []
    ctx, page = _open(browser, server, project, width, height, errors)
    _home(page)

    listed = page.eval_on_selector_all(
        "#homeSessionGrid .home-manager-card h2", "els => els.map(e => e.textContent.trim())"
    )
    print(f"\n[{width}] Home lists: {listed}")
    assert len(listed) == len(MANAGERS), f"Home lists {listed}, expected {len(MANAGERS)} sessions"

    control = page.evaluate(CONTROL, "homeTellAllButton")
    print(f"[{width}] tell-all control: {control}")
    assert control is not None, "Home has no control that addresses every session listed"
    assert control["drawn"] and control["inside"], (
        f"Home's tell-all control is not drawn whole at {width}px: {control}"
    )
    assert "tell all" in control["word"].lower(), f"it reads {control['word']!r}"

    before = {mid: {p.name for p in _feedback_files(repo)}
              for mid, repo in project["repos"].items()}

    said = f"hold new work until the release lands ({width})"
    _push_the_console_sheet_down(page, width)
    page.click("#homeTellAllButton", timeout=5000)
    page.wait_for_selector("#homeTellAllText", timeout=5000)
    page.fill("#homeTellAllText", said)
    page.click("#dialogActions button:has-text('Tell them all')", timeout=5000)

    landed: dict[str, list[Path]] = {}
    deadline = time.time() + 15
    while time.time() < deadline:
        landed = {
            mid: [p for p in _feedback_files(repo)
                  if p.name not in before[mid] and said in p.read_text(encoding="utf-8")]
            for mid, repo in project["repos"].items()
        }
        if all(landed.values()):
            break
        time.sleep(0.2)

    for mid, files in landed.items():
        print(f"[{width}] {mid}: {[str(p) for p in files]}")
    missed = [mid for mid, files in landed.items() if not files]
    assert not missed, (
        f"one message from Home reached {len(landed) - len(missed)} of {len(landed)} manager "
        f"sessions — nothing landed for {missed}"
    )
    for mid, files in landed.items():
        assert len(files) == 1, f"{mid} took {len(files)} feedback writes from one message, not 1"
        print(files[0].read_text(encoding="utf-8"))

    assert not errors, f"the browser logged: {errors}"
    ctx.close()


# --------------------------------------------------------------------------
# 3. neither width is widened by any of it
# --------------------------------------------------------------------------


@needs_browser
@pytest.mark.parametrize("width,height", [(1280, 800), (390, 844)])
@pytest.mark.parametrize("screen", ["workspace", "home"])
def test_nothing_widens_the_page(server, project, browser, width, height, screen) -> None:
    errors: list[str] = []
    ctx, page = _open(browser, server, project, width, height, errors)
    if screen == "home":
        _home(page)

    measured = page.evaluate(MEASURE)
    print(f"\n[{width} · {screen}] {measured}")
    assert measured["scrollWidth"] == measured["clientWidth"], (
        f"the page scrolls sideways at {width}px on {screen}: {measured}"
    )
    assert not measured["past"], f"drawn past the right edge at {width}px: {measured['past']}"
    assert not errors, f"the browser logged: {errors}"
    ctx.close()


# --------------------------------------------------------------------------
# 4. source fences — these need no browser and never skip
# --------------------------------------------------------------------------

SHELL_CSS = Path(__file__).resolve().parents[1] / "static" / "css" / "shell.css"
HOME_HTML = Path(__file__).resolve().parents[1] / "templates" / "home.html"
HOME_JS = Path(__file__).resolve().parents[1] / "static" / "js" / "render" / "home.js"


def _without_comments(source: str) -> str:
    return re.sub(r"/\*.*?\*/", " ", source, flags=re.S)


#: The control itself, not something inside it: `.icon-label-button span` may
#: be hidden (the word then arrives from CSS `content`), the button may not.
TARGETS = ("#feedbackButton", ".feedbackButton", ".icon-label-button")


def _rules_hiding_the_control(source: str) -> list[str]:
    """Every `display:none` rule whose subject is one of the controls itself."""
    found = []
    for match in re.finditer(r"([^{}]+)\{([^{}]*)\}", _without_comments(source)):
        selector, body = match.group(1).strip(), match.group(2)
        if not re.search(r"display\s*:\s*none", body):
            continue
        for one in selector.split(","):
            subject = re.split(r"[\s>+~]+", one.strip())[-1]
            if any(target in subject for target in TARGETS):
                found.append(f"{one.strip()} {{{body.strip()}}}")
    return found


def test_no_rule_takes_the_feedback_control_off_any_width() -> None:
    """The exact shape of converge-nng, fenced in the stylesheet itself.

    A rendered check proves the two widths this contract names. This one says
    the reason out loud, so a third width added later cannot quietly re-hide
    the only way into the feedback dialog.
    """
    hiding = _rules_hiding_the_control(SHELL_CSS.read_text(encoding="utf-8"))
    assert not hiding, (
        "a rule hides the Feedback control, which is the only way into the feedback "
        f"dialog: {hiding}"
    )


def test_the_two_top_bar_controls_do_not_share_one_generated_word() -> None:
    """`.icon-label-button::after { content:"Console" }` labelled both."""
    source = _without_comments(SHELL_CSS.read_text(encoding="utf-8"))
    shared = re.findall(r"\.icon-label-button::after\s*\{[^}]*content[^}]*\}", source)
    assert not shared, (
        f"one generated word is shared by every top-bar control, so one wears the other's: {shared}"
    )


def test_home_carries_the_control_that_addresses_the_list_it_draws() -> None:
    """converge-are, fenced where the list and the control both live."""
    html = HOME_HTML.read_text(encoding="utf-8")
    js = HOME_JS.read_text(encoding="utf-8")
    assert 'id="homeTellAllButton"' in html, "Home's hero has no tell-all control"
    assert re.search(r"tell all", html, re.I), "Core 13 — one message reaches every session"
    assert "api.feedback(" in js, "the tell-all must make the feedback write, per session"
    assert "data.managerList" in js, "it must address the sessions Home actually lists"
