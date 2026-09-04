"""Rendered-browser tests for three Direction truths (converge-baz, -3al, -4pq).

What is proved here, and why it needs a real browser:

- **converge-baz** — `platform-web.v1` §10 says the helper "serves the documents
  already fetched, each marked with the moment it came from". converge-719 put
  that moment in the offline banner, one chip per stored payload, in the corner
  of the screen. A steward reading a document offline is looking at the
  *document*. So the moment now sits beside the document's own title as well,
  at 1280 and at 390 — read out of the very response the screen was drawn from
  (`X-Converge-Offline` + `X-Converge-Synced-At`, put there by
  `app/static/sw.js`, carried out by `app/static/js/api.js`). None of that
  exists outside a browser with a service worker in it.

- **converge-3al** — `actions.js`'s `sendAsk` used to catch every failure with
  "this app answers no proposal route yet", which was false twice: the route
  landed with converge-ddt, and offline the real refusal is the worker's own
  sentence. The toast now reports what refused and asserts no cause of its own.
  Proved twice below: once with the network off (the worker's sentence reaches
  the toast whole), and once with the network up and the ask route answering
  (a 404 from the ask handler itself, provoked by taking the document away
  underneath it — the toast carries the server's words and claims no missing
  route).

What is NOT covered here, honestly:

- **converge-4pq is not delivered.** Restoring from History still reaches
  exactly one snapshot — the steward's own read point — because the app answers
  no route that reads a document at an arbitrary commit. Adding one means
  `app/serve.py` and `app/writes.py`, which this lane does not own, so it is
  written down for their owner rather than made. The History panel says so on
  the screen; `test_the_history_panel_still_says_what_a_restore_cannot_reach`
  below asserts that the panel keeps telling that truth, which is a test of
  honesty and *not* a test of the acceptance. The acceptance stays open.

If Playwright or its Chromium build is unavailable every browser test skips
with the reason printed, and MANUAL_PROCEDURE below is the check that stands in
for it. The wording tests at the end need no browser and always run.
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

USER = "tester"

APP = Path(__file__).resolve().parents[1]
ACTIONS_JS = APP / "static" / "js" / "actions.js"
API_JS = APP / "static" / "js" / "api.js"
DIRECTION_JS = APP / "static" / "js" / "render" / "direction.js"
DIRECTION_HTML = APP / "templates" / "direction.html"

MANUAL_PROCEDURE = """
MANUAL PROCEDURE — run this by hand if Playwright is unavailable.
Each step says what you must SEE; seeing anything else is a failure.

Setup
  uv run --extra app python -m app.serve --host 127.0.0.1 --port 8788
  Open http://127.0.0.1:8788/, sign in, open a manager and a document.
  Reload once, so the service worker is installed AND controlling the page.

Check — the document carries its own sync moment (converge-baz)
  a. While still online, SEE nothing beside the document's title but its state
     badge and "Updated <date>". Nothing claims the copy is stale, because it
     is not.
  b. Devtools → Network → Offline. Reload.
  c. SEE, beside the document's title, an amber chip reading
     "Stored copy · as of <time>".
  d. SEE the same <time> in the offline banner's chip for that same document.
     Two surfaces, one payload, one moment.
  e. Repeat at 1280x800 and at 390x844. At 390 the chip sits on its own line
     under "Updated <date>" and the page does not widen.
  FAILS IF: the chip appears while online; or the two times disagree; or the
     moment is only in the banner.

Check — Ask reports its real cause (converge-3al)
  f. With the network still off, click "Ask…", write anything, press Ask.
  g. SEE the toast read "Could not ask: you are offline, so nothing was asked —
     reconnect and ask again, or tell the manager session directly."
  FAILS IF: the toast says the app answers no proposal route, or names
     converge-ddt, or shows a status code or "Failed to fetch".
  h. Back online, delete the document file on disk, then Ask again.
  i. SEE the toast carry the server's own words ("no document … to ask about")
     and say nothing about a missing route.

Check — History still says what a restore cannot reach (converge-4pq)
  j. Open History → Details under the restore panel.
  k. SEE it say that a snapshot older than your read point is not offered, and
     name the work item for the route that would make it reachable.
  FAILS IF: a control offers to restore an arbitrary snapshot (there is no
     route behind it), or the panel stops saying what it cannot do.
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

CONTRACT = """# Demo contract (DRAFT)

## Core

A document says when it was last read from the server.
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
    tmp_path = tmp_path_factory.mktemp("direction-polish")
    repo = tmp_path / "demo-repo"
    (repo / "docs").mkdir(parents=True)
    (repo / "contracts").mkdir(parents=True)
    (repo / "docs" / "VISION.md").write_text(VISION_FIRST, encoding="utf-8")
    (repo / "contracts" / "demo.v1.md").write_text(CONTRACT, encoding="utf-8")
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "seed: the vision and one contract")
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
        "contract": repo / "contracts" / "demo.v1.md",
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
  return {scrollWidth: de.scrollWidth, clientWidth: de.clientWidth};
}
"""

#: The mark on the document itself: what it says, whether it is on screen, and
#: whether it really is inside the document surface rather than the banner.
MARK = """
() => {
  const el = document.getElementById('docSyncedAt');
  if (!el) return null;
  const box = el.getBoundingClientRect();
  return {
    hidden: el.hidden,
    text: (el.textContent || '').trim(),
    title: el.getAttribute('title') || '',
    onTheDocument: !!el.closest('#documentSurface'),
    inTheBanner: !!el.closest('#offlineBanner'),
    onScreen: box.width > 0 && box.height > 0,
  };
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
        # Below the breakpoint the Manager Console is a sheet OVER the page, and
        # a reload opens it again; a steward on a phone pushes it down before
        # reaching anything under it.
        page.click("#consoleToggle")
        page.wait_for_timeout(400)
    return ctx, page, errors


def _go_offline(ctx, page):
    """Take the network away, and open the app again with it gone.

    The re-assert after the reload is a fact about the harness, not about the
    app: Chromium's emulated offline state does NOT survive a navigation — the
    new document reports `navigator.onLine === true` again while every request
    out of it still dies (measured in `test_offline.py`, 2026-09-04).
    """
    ctx.set_offline(True)
    page.reload(wait_until="load")
    page.wait_for_timeout(2000)
    ctx.set_offline(False)
    ctx.set_offline(True)
    page.wait_for_timeout(1200)
    online_here = page.evaluate("() => navigator.onLine")
    assert online_here is False, (
        "the harness failed to take the network away; every assertion below would be "
        "measuring the wrong thing"
    )


def _toast(page) -> str:
    return page.eval_on_selector("#toast", "el => el.textContent || ''")


def _time_after_as_of(sentence: str) -> str:
    """The moment out of "… as of 03:09 PM" — the words after the last "as of"."""
    head, _sep, tail = str(sentence).rpartition(" as of ")
    return tail.strip().rstrip(".") if head else ""


# Chromium writes one line into its own log for every non-2xx response, whoever
# asked for it. A refused write IS a non-2xx response — that is how `api.js`
# tells a refusal from an answer at all — so these lines are the browser
# narrating a refusal a test deliberately provoked, not a defect.
def _defects(errors: list[str]) -> list[str]:
    return [e for e in errors if "Failed to load resource" not in e]


# --------------------------------------------------------------------------
# converge-baz — offline, the moment is on the document, not only in the banner
# --------------------------------------------------------------------------


@needs_browser
@pytest.mark.parametrize("width,height", [(1280, 800), (390, 844)])
def test_offline_a_stored_document_carries_its_own_sync_moment(
    server, project, browser, width, height
):
    ctx, page, errors = _installed(browser, server, project, width, height)

    live = page.evaluate(MARK)
    print(f"\n[{width}] with the network up the mark says: {live!r}")
    assert live is not None, "#docSyncedAt is not on the page at all"
    assert live["hidden"] is True and live["onScreen"] is False, (
        f"a document read from the server just now claimed to be a stored copy: {live!r}"
    )

    _go_offline(ctx, page)

    mark = page.evaluate(MARK)
    banner = page.evaluate(BANNER)
    title = page.eval_on_selector("#docTitle", "el => el.textContent.trim()")
    print(f"[{width}] document on screen: {title!r}")
    print(f"[{width}] the mark on the document: {mark['text']!r}")
    print(f"[{width}] its long form: {mark['title']!r}")
    print(f"[{width}] inside #documentSurface: {mark['onTheDocument']} · inside the banner: {mark['inTheBanner']}")
    print(f"[{width}] the banner's own chips: {banner['marks']}")

    assert mark["hidden"] is False and mark["onScreen"], (
        f"offline the document carried no visible mark of when it came from: {mark!r}"
    )
    assert mark["onTheDocument"] and not mark["inTheBanner"], (
        "§10's mark must sit on the document it is about, not only in the banner: "
        f"{mark!r}"
    )
    assert " as of " in mark["text"], (
        f"the mark named no moment: {mark['text']!r}"
    )
    assert "Stored copy" in mark["text"], (
        f"the mark did not say what it is a mark of: {mark['text']!r}"
    )

    # Two surfaces, one payload, one moment. The banner's chip for this document
    # is labelled with its own docId ("vision"), and both are formatted from the
    # same `X-Converge-Synced-At` the worker stored, so the times must agree —
    # a document showing one time while the banner shows another would be worse
    # than either alone.
    chips = [c for c in banner["marks"] if c.startswith("vision as of ")]
    assert chips, f"the banner listed no chip for this document: {banner['marks']}"
    assert _time_after_as_of(mark["text"]) == _time_after_as_of(chips[0]), (
        f"the document and the banner named different moments for one payload: "
        f"{mark['text']!r} vs {chips[0]!r}"
    )

    shape = page.evaluate(MEASURE)
    print(f"[{width}] scrollWidth={shape['scrollWidth']} clientWidth={shape['clientWidth']}")
    assert shape["scrollWidth"] <= shape["clientWidth"], (
        f"the mark widened the page at {width}: {shape['scrollWidth']} > {shape['clientWidth']}"
    )
    assert not _defects(errors), f"the browser reported errors: {_defects(errors)}"
    ctx.close()


@needs_browser
def test_back_online_the_document_stops_claiming_it_is_a_stored_copy(server, project, browser):
    """The mark is a fact about one payload, so it goes when the payload does.

    A mark that outlived the reading it belongs to would be the same defect in
    the other direction: a document read from the server just now, shown as if
    it were an old copy.
    """
    ctx, page, errors = _installed(browser, server, project)
    _go_offline(ctx, page)
    offline_mark = page.evaluate(MARK)
    assert offline_mark["hidden"] is False, "the offline half of this test never happened"

    ctx.set_offline(False)
    page.reload(wait_until="networkidle")
    page.wait_for_selector("#documentModeContent", timeout=15000)
    page.wait_for_timeout(1500)

    mark = page.evaluate(MARK)
    print(f"\noffline the mark said: {offline_mark['text']!r}")
    print(f"back online the mark says: {mark!r}")
    assert mark["hidden"] is True and mark["onScreen"] is False, (
        f"the document still claimed to be a stored copy with the network back: {mark!r}"
    )
    assert not _defects(errors), f"the browser reported errors: {_defects(errors)}"
    ctx.close()


# --------------------------------------------------------------------------
# converge-3al — an ask reports its real cause, and asserts no other
# --------------------------------------------------------------------------


def _ask(page, what: str) -> None:
    page.click("#askButton")
    page.wait_for_selector("#askWhat", timeout=8000)
    page.fill("#askWhat", what)
    page.click('#dialogActions button:text-is("Ask")')
    page.wait_for_timeout(1500)


@needs_browser
def test_offline_an_ask_carries_the_workers_own_refusal_and_claims_nothing_else(
    server, project, browser
):
    ctx, page, errors = _installed(browser, server, project)
    _go_offline(ctx, page)

    _ask(page, "Say the console is a place you work.")
    said = _toast(page)
    banner = page.evaluate(BANNER)
    print(f"\nthe toast said:  {said!r}")
    print(f"the banner says: {banner['text']!r}")

    assert "you are offline" in said, (
        f"the toast did not carry the worker's own refusal: {said!r}"
    )
    assert "nothing was asked" in said and "reconnect and ask again" in said, (
        f"the toast did not carry the sentence whole: {said!r}"
    )
    assert "proposal route" not in said and "converge-ddt" not in said, (
        f"the toast blamed a missing route for a refusal the network caused: {said!r}"
    )
    for wrong in ("Failed to fetch", "NetworkError", "503"):
        assert wrong not in said, f"the steward was shown machine words: {said!r}"
    # The banner and the toast are beside each other on the screen, so they had
    # better not contradict one another — that contradiction is what converge-3al
    # is about.
    assert "nothing was asked" in banner["text"], (
        f"the banner did not carry the same refusal: {banner['text']!r}"
    )
    assert not _defects(errors), f"the browser reported errors: {_defects(errors)}"
    ctx.close()


@needs_browser
def test_with_the_route_answering_a_failed_ask_names_no_missing_route(
    server, project, browser
):
    """The network is up, the ask route answers, and the ask still fails.

    The failure is real and provoked at the source: the document is taken away
    on disk under the open page, so `app/serve.py`'s ask handler itself refuses
    with its own sentence. That sentence coming back is also what proves the
    route answered at all — a route the app did not have could not have written
    it.
    """
    ctx, page, errors = _installed(browser, server, project)

    # Read the contract rather than the vision, so nothing here disturbs the
    # document the other tests in this module are reading. Chosen by the id the
    # tree itself carries (`data.doc_id`), not by its title: the title in the
    # tree is the short one ("Demo"), and matching on the H1 would be matching
    # on a string this test does not own.
    page.click('.repo-doc[data-doc="demo"]')
    page.wait_for_timeout(1200)
    reading = page.eval_on_selector("#docPath", "el => el.textContent.trim()")
    print(f"\nreading: {reading!r}")
    assert "contracts/demo.v1.md" in reading, f"the contract was never opened: {reading!r}"

    kept = project["contract"].read_text(encoding="utf-8")
    project["contract"].unlink()
    try:
        _ask(page, "Add a sentence about stored copies.")
        said = _toast(page)
    finally:
        project["contract"].write_text(kept, encoding="utf-8")

    print(f"the toast said: {said!r}")
    assert "to ask about" in said, (
        f"the toast did not carry the ask route's own refusal: {said!r}"
    )
    assert "proposal route" not in said and "converge-ddt" not in said, (
        f"the toast claimed the route is missing while the route was answering: {said!r}"
    )
    assert "you are offline" not in said, (
        f"the toast blamed the network while the network was up: {said!r}"
    )
    assert not _defects(errors), f"the browser reported errors: {_defects(errors)}"
    ctx.close()


# --------------------------------------------------------------------------
# the wording itself — no browser needed, so these always run
# --------------------------------------------------------------------------


def test_send_ask_reports_what_refused_and_asserts_no_cause():
    text = ACTIONS_JS.read_text(encoding="utf-8")
    head, _, tail = text.partition("export async function sendAsk")
    body = tail.split("\n// ---")[0]
    assert body, "sendAsk is no longer in actions.js"
    assert "toast(`Could not ask: ${err.message}`)" in body, (
        "sendAsk no longer reports the refusal it was handed, in that refuser's own words"
    )
    claim = "answers no proposal route yet"
    assert claim not in text, (
        f"actions.js still tells a steward {claim!r}, which converge-ddt made false"
    )
    print("\nsendAsk's failure path:")
    for line in body.splitlines():
        if "toast(" in line:
            print(f"  {line.strip()}")


def test_the_mark_is_wired_from_the_response_that_drew_the_screen():
    """§10's moment must come from the payload, not from a guess beside it."""
    api = API_JS.read_text(encoding="utf-8")
    render = DIRECTION_JS.read_text(encoding="utf-8")
    html = DIRECTION_HTML.read_text(encoding="utf-8")
    assert "X-Converge-Offline" in api and "X-Converge-Synced-At" in api, (
        "api.js no longer reads the worker's own headers off the response"
    )
    assert "storedCopy" in api and "storedCopy" in render, (
        "the moment api.js reads is not the one the document renders"
    )
    assert 'id="docSyncedAt"' in html, "the document has no place to carry its own mark"
    assert "renderStoredMark" in render, "nothing draws the mark"
    print("\napi.js reads X-Converge-Offline + X-Converge-Synced-At → doc.storedCopy")
    print("render/direction.js draws it as #docSyncedAt, beside the document's title")


def test_the_history_panel_still_says_what_a_restore_cannot_reach():
    """converge-4pq is NOT delivered, and the screen must keep saying so.

    This asserts honesty, not the acceptance: restoring still reaches exactly
    one snapshot — the steward's own read point. Making an arbitrary snapshot
    reachable needs a route in `app/serve.py` and `app/writes.py`, which this
    lane does not own. The panel says that plainly rather than offering a
    control that would look like time travel and not be one.

    This test fails the day someone adds such a control without the route
    behind it — which is the failure it exists to catch.
    """
    render = DIRECTION_JS.read_text(encoding="utf-8")
    head, _, tail = render.partition("function restorePanel(")
    body = tail.split("\nexport function renderHistory")[0]
    assert body, "the restore panel is no longer in render/direction.js"
    assert "older than your read point is not offered" in body, (
        "the History panel stopped saying which snapshots a restore cannot reach"
    )
    assert "arbitrary commit" in body, (
        "the panel no longer says why: there is no route that reads a document at "
        "an arbitrary commit"
    )
    said = [line.strip() for line in body.splitlines() if "not offered" in line]
    print("\nwhat the History panel tells a steward today:")
    for line in said:
        print(f"  {line[:160]}")
