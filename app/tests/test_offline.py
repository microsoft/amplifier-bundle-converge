"""Rendered-browser tests for the app with the network off (converge-719).

`platform-web.v1` §10 asks that offline the app reads what it last synced and
says when that was; §11 asks that a write offline is refused in one plain
sentence naming what to do instead. Neither can be proved by reading files: the
whole behaviour lives in a service worker, which only exists inside a real
browser, and the only honest way to see it is to take the network away and look
at the screen.

What these tests drive is the real app over a real git repository, with a real
service worker installed, and then `context.set_offline(True)`. Nothing is
stubbed: the refusal sentences come out of `app/static/sw.js`, the "as of
<time>" comes out of the moment the payload was actually fetched, and the
assertions are made against what is on the page afterwards.

What is NOT covered here, honestly:

- **The per-document mark is in the banner, not on the document itself.**
  §10 says each stored payload is "marked with the moment it came from"; this
  lane owns neither `app/static/js/render/*.js` nor `app/templates/direction.html`,
  so the marks are listed in the offline banner (one chip per payload, each with
  its own time) rather than printed beside each document's title. Filed for the
  owner of the render files.
- **The toast wording for a failed Ask is another lane's.** `actions.js`
  catches every ask failure with "this app answers no proposal route yet",
  which is the wrong cause when the real cause is the network. The refusal
  sentence itself is correct and is what the banner shows; the toast prefix is
  not this lane's file. Filed for its owner.
- **Nothing is queued.** §11 says a browser cannot promise to send something
  later, so no write is held. A test that asserted a queue would be asserting a
  promise this app deliberately does not make.

If Playwright or its Chromium build is unavailable every browser test skips
with the reason printed, and MANUAL_PROCEDURE below is the check that stands in
for it. The two wording tests at the end need no browser and always run.
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

from app import auth, serve  # noqa: E402

USER = "tester"

SW = Path(__file__).resolve().parents[1] / "static" / "sw.js"
OFFLINE_JS = Path(__file__).resolve().parents[1] / "static" / "js" / "offline.js"

MANUAL_PROCEDURE = """
MANUAL PROCEDURE — run this by hand if Playwright is unavailable.
Each step says what you must SEE; seeing anything else is a failure.

Setup
  uv run --extra app python -m app.serve --host 127.0.0.1 --port 8788
  Open http://127.0.0.1:8788/, sign in, open a manager and a document.
  Reload once, so the service worker is installed AND controlling the page.

Check — offline the app opens at all
  a. Devtools → Network → Offline (or pull the cable). Reload the page.
  b. SEE the Converge shell, not the browser's own "no internet" page.
  FAILS IF: the browser's offline error page appears. The app shell itself is
     not stored, so there is nothing to open.

Check — offline it reads what it last synced, and says when
  c. SEE the manager name in the top bar, the document tree populated, and the
     document you were reading still on screen.
  d. SEE a dark banner at the bottom-left reading
     "Offline — showing what was last synced, as of <time>."
  e. SEE inside it one chip per stored payload, each ending "as of <time>".
  FAILS IF: the panels are empty; or a time is shown that is not the moment
     the payload was actually fetched; or no "as of" appears anywhere.

Check — offline each of the five writes is refused in one plain sentence
  f. Click Feedback, write something, Send feedback.
  g. SEE a sentence naming what to do instead — "you are offline, so nothing
     was filed — reconnect and send it again, or tell the manager session
     directly." SEE the same sentence, whole, in the banner.
  h. Repeat for Steer, for a proposal decision, for Ask, and for a change card's
     Keep. Each names its own write.
  FAILS IF: any of them shows a status code, "Failed to fetch", "→ 503", or
     nothing at all. Silence is the only wrong answer.

Check — the Manager Console is never replayed
  i. With the network still off, SEE the console say it is disconnected. It must
     never sit there showing an old frame as if it were live.
  FAILS IF: the terminal pane still shows its last frame with no word about the
     connection.

Check — it holds at both widths
  j. Repeat (a)-(g) at 1280x800 and at 390x844. At each, in the console run:
       document.documentElement.scrollWidth + ' vs ' + document.documentElement.clientWidth
     SEE the two numbers equal, with the banner showing.
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
# a project to serve
# --------------------------------------------------------------------------

VISION_FIRST = """# Demo Vision (DRAFT)

## Where this is going

One place for direction and one place for operation.
The console is a tab you visit when something breaks.
"""

VISION_SECOND = """# Demo Vision (DRAFT)

## Where this is going

One place for direction and one place for operation.
The console is a place you work, not a tab you visit.
"""

HIGHWAY = """# Highway — demo

Width 2.
"""

MANIFEST_HEAD = "lane\tworktree\tbranch\tbase\ttmux\tgoal\tlog\tstarted\n"


def _git(repo: Path, *args: str) -> str:
    done = subprocess.run(
        ["git", "-c", "user.name=Test", "-c", "user.email=test@example.invalid", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    return done.stdout


@pytest.fixture(scope="module")
def project(tmp_path_factory) -> dict:
    """A real repository with real history — never fixtures of the answers."""
    tmp_path = tmp_path_factory.mktemp("offline")
    repo = tmp_path / "demo-repo"
    (repo / "docs").mkdir(parents=True)
    (repo / "docs" / "VISION.md").write_text(VISION_FIRST, encoding="utf-8")
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "seed: the vision")
    (repo / "docs" / "VISION.md").write_text(VISION_SECOND, encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "the console becomes a place")

    batch = tmp_path / "hw-demo"
    (batch / "lanes" / "w1-alpha").mkdir(parents=True)
    (batch / "goals").mkdir()
    (batch / "HIGHWAY.md").write_text(HIGHWAY, encoding="utf-8")
    (batch / "goals" / "w1-alpha.md").write_text("# Lane alpha\n", encoding="utf-8")
    (batch / "lanes" / "w1-alpha" / "lane.log").write_text("working\n", encoding="utf-8")
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
    return {
        "config": conf,
        "secret": tmp_path / "secret",
        "state": tmp_path / "state.json",
        "repo": repo,
        "vision": repo / "docs" / "VISION.md",
    }


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
# driving
# --------------------------------------------------------------------------

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

BANNER = """
() => {
  const el = document.getElementById('offlineBanner');
  if (!el) return null;
  return {
    hidden: el.hidden,
    text: el.innerText,
    marks: Array.from(el.querySelectorAll('.offline-mark')).map(li => li.textContent),
  };
}
"""


def _installed(browser, server, project, width=1280, height=800):
    """Open the app the way an installed app is opened: not for the first time.

    The service worker is not controlling the page on the very first load — it
    installs during it — so the first visit stores nothing from /api. A second
    load is what an installed app always is, and it is the only state in which
    §10 can be true at all.
    """
    sessions = auth.Sessions(auth.read_or_make_secret(project["secret"]))
    ctx = browser.new_context(viewport={"width": width, "height": height})
    ctx.add_cookies([{"name": auth.COOKIE, "value": sessions.issue(USER),
                      "domain": "127.0.0.1", "path": "/"}])
    page = ctx.new_page()
    errors: list[str] = []
    page.on("console", lambda m: errors.append(f"console.{m.type}: {m.text}") if m.type == "error" else None)
    page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))

    page.goto(server, wait_until="networkidle")
    page.wait_for_selector("#documentModeContent", timeout=15000)
    page.evaluate("async () => { await navigator.serviceWorker.ready; }")

    page.reload(wait_until="networkidle")
    page.wait_for_selector("#documentModeContent", timeout=15000)
    page.wait_for_function("() => !!navigator.serviceWorker.controller", timeout=15000)
    page.wait_for_timeout(1200)
    if width < 980:
        page.click("#consoleToggle")
        page.wait_for_timeout(400)
    return ctx, page, errors


def _go_offline(ctx, page):
    """Take the network away, and open the app again with it gone.

    The re-assert after the reload is a fact about the harness, not about the
    app: Chromium's emulated offline state does NOT survive a navigation — the
    new document reports `navigator.onLine === true` again while every request
    out of it still dies. Measured here, 2026-09-04. Without re-asserting it
    the browser would be in a state a real machine is never in (interface up,
    nothing reachable), and the tests below would only ever exercise half of
    what the worker says.
    """
    ctx.set_offline(True)
    page.reload(wait_until="load")
    page.wait_for_timeout(2000)
    ctx.set_offline(False)
    ctx.set_offline(True)
    page.wait_for_timeout(1200)
    online_here = page.evaluate("() => navigator.onLine")
    online_there = _worker_online(page)
    print(f"navigator.onLine — page: {online_here}, worker: {online_there}")
    assert online_here is False and online_there is False, (
        "the harness failed to take the network away; every assertion below would be "
        f"measuring the wrong thing (page={online_here}, worker={online_there})"
    )


def _worker_online(page):
    """What the service worker itself believes — it is what words the refusals.

    Read off the same `converge-what-is-synced` answer the banner reads, not a
    probe added for the test: a fact only a test can see is a fact the app is
    not actually using.
    """
    return page.evaluate(
        """async () => {
            const reg = await navigator.serviceWorker.ready;
            const worker = reg.active;
            if (!worker) return 'no active worker';
            return await new Promise((resolve) => {
                const channel = new MessageChannel();
                channel.port1.onmessage = (e) => resolve(e.data && e.data.onLine);
                worker.postMessage({type: 'converge-what-is-synced'}, [channel.port2]);
                setTimeout(() => resolve('no answer'), 3000);
            });
        }"""
    )


def _synced_keys(page):
    return page.evaluate(
        "async () => { const c = await caches.open('converge-synced-v1');"
        " return (await c.keys()).map(r => new URL(r.url).pathname).sort(); }"
    )


def _toast(page) -> str:
    return page.eval_on_selector("#toast", "el => el.textContent || ''")


NOT_A_SENTENCE = re.compile(r"Failed to fetch|NetworkError|→ \d{3}|\b50[0-9]\b|\bTypeError\b")

# Chromium writes one line into its own log for every non-2xx response, whoever
# asked for it. A refused write IS a non-2xx response — that is how `api.js`
# tells a refusal from an answer at all — so these lines are the browser
# narrating the refusal this test deliberately provoked, not a defect. They are
# counted and printed, never silently dropped; everything else still fails the
# test. §14's "no errors in the browser's own log" is asserted whole on the
# rendering tests above, which provoke nothing.
NARRATED_REFUSAL = re.compile(r"Failed to load resource: the server responded with a status of 503")


def _defects(errors: list[str]) -> list[str]:
    return [e for e in errors if not NARRATED_REFUSAL.search(e)]


# --------------------------------------------------------------------------
# §10 — offline it opens, reads what it last synced, and says when that was
# --------------------------------------------------------------------------


@needs_browser
@pytest.mark.parametrize("width,height", [(1280, 800), (390, 844)])
def test_offline_the_app_shows_what_it_last_synced_with_a_visible_as_of_time(
    server, project, browser, width, height
):
    ctx, page, errors = _installed(browser, server, project, width, height)

    stored = _synced_keys(page)
    print(f"\n[{width}] payloads stored while online: {stored}")
    assert stored, "nothing from /api was stored while online, so there is nothing to read offline"

    _go_offline(ctx, page)

    opened = page.query_selector("#documentModeContent") is not None
    manager = page.eval_on_selector("#managerNameTop", "el => el.textContent.trim()")
    docs = page.eval_on_selector_all(".repo-doc", "els => els.length")
    reading = page.eval_on_selector("#documentModeContent", "el => el.innerText.trim()")
    banner = page.evaluate(BANNER)

    print(f"[{width}] the shell opened with the network off: {opened}")
    print(f"[{width}] manager named in the top bar: {manager!r}")
    print(f"[{width}] documents in the tree: {docs}")
    print(f"[{width}] reading surface carries: {reading[:90]!r}")
    print(f"[{width}] banner hidden: {banner['hidden']}")
    print(f"[{width}] banner says: {banner['text']}")
    print(f"[{width}] marks: {banner['marks']}")
    print(f"[{width}] console errors: {errors or 'none'}")

    assert opened, "the app did not open at all offline — the shell itself was never stored"
    assert manager, "the top bar named no manager: nothing was read back from the store"
    assert docs > 0, "the document tree was empty: the shell rendered with no payload behind it"
    assert reading, "the reading surface was empty offline"
    assert banner is not None and banner["hidden"] is False, "nothing on screen said the app was offline"
    assert "as of " in banner["text"], (
        f"§10 asks for a visible 'as of <time>'; the banner said: {banner['text']!r}"
    )
    assert banner["marks"], "no payload was marked with the moment it came from"
    for mark in banner["marks"]:
        assert " as of " in mark, f"a stored payload carried no moment: {mark!r}"

    shape = page.evaluate(MEASURE)
    print(f"[{width}] scrollWidth={shape['scrollWidth']} clientWidth={shape['clientWidth']}")
    if shape["past"]:
        print(f"[{width}] boxes past the right edge (diagnostic only): {shape['past']}")
    assert shape["scrollWidth"] <= shape["clientWidth"], (
        f"the offline banner widened the page at {width}: "
        f"{shape['scrollWidth']} > {shape['clientWidth']}; {shape['past']}"
    )
    assert not errors, f"the browser reported errors: {errors}"
    ctx.close()


@needs_browser
def test_a_stored_payload_is_served_only_when_the_request_actually_failed(
    server, project, browser
):
    """§10's other half: nothing that is not current is shown as current.

    While the network is up the network's answer wins and carries no offline
    mark; the moment it is down the same request carries the mark and the time
    it was fetched. Those two facts together are what makes "as of <time>" a
    true statement rather than a decoration.
    """
    ctx, page, errors = _installed(browser, server, project)

    live = page.evaluate("""async () => {
        const r = await fetch('/api/boot', {credentials: 'same-origin'});
        return {status: r.status, offline: r.headers.get('X-Converge-Offline'),
                syncedAt: r.headers.get('X-Converge-Synced-At')};
    }""")
    print(f"\nonline  /api/boot → {live}")
    assert live["status"] == 200
    assert live["offline"] is None, "a live answer was marked as coming from the store"

    ctx.set_offline(True)
    stale = page.evaluate("""async () => {
        const r = await fetch('/api/boot', {credentials: 'same-origin'});
        const body = await r.json();
        return {status: r.status, offline: r.headers.get('X-Converge-Offline'),
                syncedAt: r.headers.get('X-Converge-Synced-At'),
                managers: (body.managers || []).length};
    }""")
    print(f"offline /api/boot → {stale}")
    assert stale["status"] == 200, "the stored payload was not served with the network down"
    assert stale["offline"] == "1", "a stored payload was served with nothing saying so"
    assert stale["syncedAt"], "a stored payload was served without the moment it came from"
    assert stale["managers"] > 0, "the stored payload was empty"

    banner_visible = page.evaluate(
        "() => !document.getElementById('offlineBanner').hidden"
    )
    print(f"banner showing after the stored read: {banner_visible}")
    assert banner_visible, "a stored payload was shown with nothing on screen saying when it came from"
    print(f"console errors: {errors or 'none'}")
    assert not errors, f"the browser reported errors: {errors}"
    ctx.close()


# --------------------------------------------------------------------------
# §11 — offline every write is refused in one plain sentence
# --------------------------------------------------------------------------

WRITES = [
    ("answer with a word", "/api/managers/demo/decision", {"decision": "ratified"}, "was recorded"),
    ("drop feedback", "/api/managers/demo/feedback", {"text": "x", "context": "y"}, "was filed"),
    ("steer", "/api/managers/demo/steer", {"objective": "x", "lanes": 2}, "was sent"),
    ("raise or lower a priority", "/api/managers/demo/steer", {"fill": True}, "was sent"),
    ("ask", "/api/managers/demo/ask", {"scope": "document", "text": "x"}, "was asked"),
]


@needs_browser
def test_offline_each_of_the_five_writes_is_refused_in_one_plain_sentence(
    server, project, browser
):
    ctx, page, errors = _installed(browser, server, project)
    _go_offline(ctx, page)

    print()
    for name, route, payload, own_words in WRITES:
        answer = page.evaluate(
            """async ([url, body]) => {
                const r = await fetch(url, {method: 'POST', credentials: 'same-origin',
                    headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body)});
                let said = '';
                try { said = (await r.json()).error || ''; } catch { said = '(not JSON)'; }
                return {status: r.status, said};
            }""",
            [route, payload],
        )
        said = answer["said"]
        print(f"  {name:26} → {said}")
        assert said, f"{name} offline said nothing at all — silence is the only wrong answer"
        assert not NOT_A_SENTENCE.search(said), (
            f"{name} was refused with a failed-request message, not a sentence: {said!r}"
        )
        assert said.count(".") == 1 and said.endswith("."), (
            f"§11 asks for ONE plain sentence; {name} said: {said!r}"
        )
        assert "you are offline" in said, f"{name} did not say why: {said!r}"
        assert own_words in said, (
            f"{name} did not name its own write; a generic refusal cannot tell a steward "
            f"what was lost: {said!r}"
        )
        assert "reconnect" in said, f"{name} did not name what to do instead: {said!r}"

    print(f"browser lines narrating the refusals: {len(errors) - len(_defects(errors))}")
    print(f"anything else in the browser's log: {_defects(errors) or 'none'}")
    assert not _defects(errors), f"the browser reported errors: {_defects(errors)}"
    ctx.close()


@needs_browser
@pytest.mark.parametrize("width,height", [(1280, 800), (390, 844)])
def test_offline_a_write_driven_from_the_screen_says_the_sentence_on_the_screen(
    server, project, browser, width, height
):
    """The refusal has to reach the steward, not just the network layer.

    Steer is the write driven here because it is the one of the five reachable
    at BOTH widths from the screen: `shell.css` hides `#feedbackButton` below
    980px, so a phone cannot start that write at all. That is another lane's
    rule about another lane's control; it is recorded here rather than worked
    around, because a test that quietly picked a different width would hide it.
    """
    ctx, page, errors = _installed(browser, server, project, width, height)
    _go_offline(ctx, page)

    if width < 980:
        # Below the breakpoint the Manager Console is a sheet OVER the page, and
        # a reload opens it again; a steward on a phone pushes it down before
        # reaching anything under it.
        page.click("#consoleToggle")
        page.wait_for_timeout(500)

    page.click("#operationTab")
    page.wait_for_selector("#steerButton", state="visible", timeout=8000)
    page.click("#steerButton")
    page.wait_for_selector("#steerObjective", timeout=8000)
    page.fill("#steerNote", "Narrow to the offline work.")
    page.click('#dialogActions button:text-is("Update steering")')
    page.wait_for_timeout(1500)

    said = _toast(page)
    banner = page.evaluate(BANNER)
    print(f"\n[{width}] the toast said:  {said}")
    print(f"[{width}] the banner says: {banner['text']}")
    print(f"[{width}] browser lines narrating the refusal: {len(errors) - len(_defects(errors))}")
    print(f"[{width}] anything else in the browser's log: {_defects(errors) or 'none'}")

    assert not NOT_A_SENTENCE.search(said), (
        f"the steward was shown a failed-request message: {said!r}"
    )
    assert "you are offline" in said and "reconnect" in said, (
        f"the toast did not carry the refusal: {said!r}"
    )
    assert "nothing was sent" in banner["text"], (
        f"the banner did not carry the whole refusal sentence: {banner['text']!r}"
    )

    shape = page.evaluate(MEASURE)
    print(f"[{width}] scrollWidth={shape['scrollWidth']} clientWidth={shape['clientWidth']}")
    assert shape["scrollWidth"] <= shape["clientWidth"], (
        f"the refusal widened the page at {width}: {shape['scrollWidth']} > {shape['clientWidth']}"
    )
    assert not _defects(errors), f"the browser reported errors: {_defects(errors)}"
    ctx.close()


# --------------------------------------------------------------------------
# §12 — the Manager Console is never replayed from the store
# --------------------------------------------------------------------------


@needs_browser
def test_the_console_is_never_stored_and_never_replayed(server, project, browser):
    ctx, page, errors = _installed(browser, server, project)

    page.evaluate("""async () => {
        await fetch('/api/tmux/test-socket-that-does-not-exist/demo', {credentials: 'same-origin'})
            .catch(() => undefined);
    }""")
    page.wait_for_timeout(400)
    stored = _synced_keys(page)
    print(f"\npayloads stored: {stored}")
    assert not any(p.startswith("/api/tmux") for p in stored), (
        "a console frame was stored — §12 says the console is live or plainly disconnected, "
        "and a stored frame is exactly the in-between it forbids"
    )

    ctx.set_offline(True)
    answer = page.evaluate("""async () => {
        const r = await fetch('/api/tmux/test-socket-that-does-not-exist/demo',
                              {credentials: 'same-origin'});
        let said = '';
        try { said = (await r.json()).error || ''; } catch { said = '(not JSON)'; }
        return {status: r.status, said};
    }""")
    print(f"offline /api/tmux/... → {answer}")
    assert answer["status"] != 200, "an old console frame was replayed as if it were live"
    assert "disconnected" in answer["said"], (
        f"the console did not say plainly that it was disconnected: {answer['said']!r}"
    )
    print(f"console errors: {errors or 'none'}")
    ctx.close()


# --------------------------------------------------------------------------
# the wording rules, without a browser
# --------------------------------------------------------------------------
#
# These two hold the shape of what the browser tests above prove the behaviour
# of. They are cheap, they run everywhere, and they catch the one regression a
# hurried edit makes: a refusal that goes back to being a status code.


def test_every_refusal_the_worker_can_utter_is_a_plain_sentence():
    text = SW.read_text(encoding="utf-8")
    endings = re.findall(r"^\s*\[/[^,]+,\s*'([^']+)'\]", text, flags=re.MULTILINE)
    endings += re.findall(r"^const FALLBACK_ENDING = '([^']+)'", text, flags=re.MULTILINE)
    print(f"\nrefusal endings in sw.js: {len(endings)}")
    assert len(endings) >= 9, f"expected every write route to have its own words; found {endings}"
    for ending in endings:
        print(f"  …{ending}.")
        assert ending.startswith("so "), f"an ending does not follow the cause: {ending!r}"
        assert not NOT_A_SENTENCE.search(ending), f"a refusal carries a status code: {ending!r}"
        assert "reconnect" in ending, f"a refusal names nothing to do instead: {ending!r}"
        assert "." not in ending, f"a refusal is more than one sentence: {ending!r}"


def test_the_worker_still_refuses_to_store_the_two_things_it_must_not():
    text = SW.read_text(encoding="utf-8")
    print("\nnever-cached rules still in sw.js:")
    for needle, why in [
        ("/login", "the sign-in page must never be replayed"),
        ("/logout", "signing out must empty what was kept"),
        ("/api/tmux", "the console must never be replayed as if it were live"),
    ]:
        print(f"  {needle}: {needle in text}")
        assert needle in text, why
    assert "caches.delete(SYNCED)" in text, (
        "signing out no longer empties the store — the next person at this browser "
        "would read the last person's documents offline"
    )
    assert OFFLINE_JS.is_file(), "the banner script named by the precache list is missing"
    assert "/static/js/offline.js" in text, "offline.js is not precached, so the banner dies offline"
