"""Courtesy presence, end to end: two stewards, one section, no lock.

`experience-direction.v1` clause 10 asks for two things, and until this lane
only half of one of them was real:

* **while a person is editing, that section is shown softly** -- which meant,
  before `app/presence.py`, the steward's own open editor in their own browser.
  A second person on a second machine was invisible.
* **the manager session backs off and queues rather than fights** -- which
  nothing told it to do, because nothing told it anything.

What is proved here, and how
----------------------------

The first four tests drive the channel directly: a mark expires, two signed-in
people see each other through the HTTP routes, nothing lands on disk, and a
writer that is not a browser is told to wait and does. The last three drive two
real Chromium contexts, signed in as two different stewards, against one server
and one git repository -- because "the other steward sees it" is a claim about
two browsers and cannot be made by one.

What is deliberately NOT claimed
--------------------------------

* **Nothing here makes a manager session obey.** The app answers "that section
  is held by <person>, for another <n> seconds"; a session that asks and writes
  anyway is beyond what a server can promise. `test_a_manager_session_is_told
  _to_queue_and_the_document_is_untouched` therefore drives a client that
  *does* back off, and asserts the file -- it proves the channel and the
  back-off, not the good manners of every future caller.
* **Presence never blocks a write.** There is no test that a held section
  cannot be written, because it can be, on purpose. What stops two writes from
  overwriting each other is the collision path in `app/writes.py`, and the last
  test is that path reached from two browsers.

If Playwright or its Chromium build is unavailable, the browser tests skip with
the reason printed and MANUAL_PROCEDURE below is the check that stands in.
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
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app import auth, presence as presence_mod, serve  # noqa: E402

ANA = "ana"
BROOK = "brook"
MANAGER_SESSION = "manager-session"


MANUAL_PROCEDURE = """
MANUAL PROCEDURE -- run this by hand if Playwright is unavailable.
Each step says what you must SEE; seeing anything else is a failure.

Setup
  uv run --extra app python -m app.serve --host 0.0.0.0 --port 8788
  Sign in as one person on one machine, and as a DIFFERENT person on another
  (or in a private window). Open the same DRAFT document in both.

Check -- the other steward is shown softly, by name
  a. On machine A, click Edit "..." under a changed paragraph.
  b. On machine B, WITHOUT reloading, wait a few seconds. SEE that paragraph
     tinted, with a line reading "<A> is editing this section (just now).
     Nothing is locked -- if you both write, you are offered a choice."
  c. On machine B, SEE that every control is still live: the edit button under
     that same paragraph is clickable, not greyed out.
  FAILS IF: B sees nothing after ~10s; or B's controls are disabled (that is a
     lock, and the clause asks for courtesy).

Check -- the mark is released, and expires on its own
  d. On machine A, click Cancel. Within a few seconds SEE B's line disappear.
  e. On machine A, open the editor again, then kill the tab outright. Within
     60s SEE B's line disappear by itself.
  FAILS IF: a mark outlives the browser that set it.

Check -- a collision still offers all three choices
  f. On A, open the editor on a paragraph and leave it open.
  g. On B, edit and save that same sentence. SEE B report a commit.
  h. On A, write something else and click Save. SEE "This moved while you were
     writing.", both wordings, and three buttons: Use combined - Keep mine -
     Review both. SEE the file unchanged at this point.
  i. Click Keep mine. SEE a commit, and SEE A's wording in the file.
  FAILS IF: fewer than three choices appear, or anything was written before a
     choice was taken.

Check -- presence is nowhere on disk
  j. With both editors open, run `git status` in the repository: SEE it clean.
     Read ~/.amplifier/converge-app.state.json: SEE no section names in it.
  FAILS IF: a mark about the next sixty seconds was committed to a history
     meant to outlive everyone.
"""


# --------------------------------------------------------------------------
# the store, on its own
# --------------------------------------------------------------------------


class Clock:
    """A clock a test can move, so a minute costs nothing to wait."""

    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


def test_a_mark_stands_for_a_minute_and_then_stops_standing():
    clock = Clock()
    live = presence_mod.Presence(ttl=60.0, clock=clock)
    live.editing(user=ANA, repo="demo", doc="vision", section="Where this is going")

    at_fifty_nine = live.here(repo="demo", doc="vision")["editing"]
    clock.now += 59
    still = live.here(repo="demo", doc="vision")["editing"]
    clock.now += 2  # 61s since the mark
    gone = live.here(repo="demo", doc="vision")["editing"]

    print(f"\nmarks at 0s: {len(at_fifty_nine)}  at 59s: {len(still)}  at 61s: {len(gone)}")
    assert len(still) == 1, "a mark stopped standing before its minute was up"
    assert still[0]["user"] == ANA
    assert still[0]["ago"] == 59
    assert gone == [], "a mark older than 60s was still being shown as presence"


def test_a_refresh_keeps_a_mark_alive_and_an_empty_section_is_goodbye():
    clock = Clock()
    live = presence_mod.Presence(ttl=60.0, clock=clock)
    live.editing(user=ANA, repo="demo", doc="vision", section="Principles")
    clock.now += 50
    live.editing(user=ANA, repo="demo", doc="vision", section="Principles")  # a beat
    clock.now += 50  # 100s after the first mark, 50s after the beat
    kept = live.here(repo="demo", doc="vision")["editing"]
    print(f"marks 100s after the first beat, refreshed at 50s: {len(kept)}")
    assert len(kept) == 1, "a refreshed mark expired anyway"

    live.editing(user=ANA, repo="demo", doc="vision", section="")
    after = live.here(repo="demo", doc="vision")["editing"]
    print(f"marks after an empty section (goodbye): {len(after)}")
    assert after == []


def test_one_person_holds_one_section_at_a_time():
    """A second mark from the same person is a mark nobody is standing behind."""
    live = presence_mod.Presence()
    live.editing(user=ANA, repo="demo", doc="vision", section="Principles")
    live.editing(user=ANA, repo="demo", doc="vision", section="Where this is going")
    here = live.here(repo="demo", doc="vision")["editing"]
    print(f"\nsections ana holds after opening a second editor: {[r['section'] for r in here]}")
    assert [r["section"] for r in here] == ["Where this is going"]


# --------------------------------------------------------------------------
# a project to serve: one draft document with a sentence that moved
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

HIGHWAY = """# Highway -- demo

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
    tmp_path = tmp_path_factory.mktemp("presence")
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
        "root": tmp_path,
    }


def _signed_in(project, user: str) -> TestClient:
    made = serve.create_app(
        config_path=project["config"], secret_path=project["secret"], state_path=project["state"]
    )
    client = TestClient(made)
    sessions = auth.Sessions(auth.read_or_make_secret(project["secret"]))
    client.cookies.set(auth.COOKIE, sessions.issue(user))
    return client


# --------------------------------------------------------------------------
# the channel over HTTP
# --------------------------------------------------------------------------


def test_two_signed_in_people_see_each_other_through_the_routes(project):
    """One app, two cookies. The mark ana sets is the mark brook reads."""
    app = serve.create_app(
        config_path=project["config"], secret_path=project["secret"], state_path=project["state"]
    )
    sessions = auth.Sessions(auth.read_or_make_secret(project["secret"]))
    client = TestClient(app)

    def as_person(user):
        client.cookies.set(auth.COOKIE, sessions.issue(user))
        return client

    where = {"repoId": "demo-repo", "docId": "vision", "section": "Where this is going"}
    beat = as_person(ANA).post("/api/managers/demo/presence", json=where).json()
    print(f"\nana beats: you={beat['you']} others={beat['others']}")
    assert beat["ok"] and beat["you"] == ANA
    assert beat["others"] == [], "ana was shown her own mark as somebody else's"

    seen = as_person(BROOK).get(
        "/api/managers/demo/presence", params={"repoId": "demo-repo", "docId": "vision"}
    ).json()
    print(f"brook reads: others={[(o['user'], o['section']) for o in seen['others']]} ttl={seen['ttlSeconds']}s")
    assert [(o["user"], o["section"]) for o in seen["others"]] == [(ANA, "Where this is going")]
    assert seen["ttlSeconds"] == 60

    goodbye = as_person(ANA).post(
        "/api/managers/demo/presence", json={**where, "section": ""}
    ).json()
    after = as_person(BROOK).get(
        "/api/managers/demo/presence", params={"repoId": "demo-repo", "docId": "vision"}
    ).json()
    print(f"after ana closes the editor, brook sees: {after['others']}")
    assert goodbye["ok"]
    assert after["others"] == []


def test_presence_is_nowhere_on_disk(project):
    """A note about the next sixty seconds belongs in neither the repository
    nor the reading store. Both are checked, byte for byte."""
    app = serve.create_app(
        config_path=project["config"], secret_path=project["secret"], state_path=project["state"]
    )
    sessions = auth.Sessions(auth.read_or_make_secret(project["secret"]))
    client = TestClient(app)
    client.cookies.set(auth.COOKIE, sessions.issue(ANA))

    before_state = project["state"].read_text(encoding="utf-8") if project["state"].exists() else ""
    client.post(
        "/api/managers/demo/presence",
        json={"repoId": "demo-repo", "docId": "vision", "section": "Where this is going"},
    )
    after_state = project["state"].read_text(encoding="utf-8") if project["state"].exists() else ""
    dirty = _git(project["repo"], "status", "--porcelain").strip()

    print(f"\ngit status after a beat: {dirty!r}")
    print(f"the reading store changed: {before_state != after_state}")
    print(f"'Where this is going' appears in the reading store: {'Where this is going' in after_state}")
    assert dirty == "", "a presence mark left something in the working tree"
    assert before_state == after_state, "a presence mark was written into the read-point store"
    assert "Where this is going" not in after_state


def test_a_manager_session_is_told_to_queue_and_the_document_is_untouched(project):
    """The clause's second half, driven by a client that is not a browser.

    This is a manager session doing exactly what clause 10 asks: ask first,
    and when the answer is "held", queue rather than write. The document is
    asserted afterwards -- the point is not that the app refused (it never
    refuses), but that a session that asks is told enough to back off, and
    that backing off leaves the file alone.
    """
    app = serve.create_app(
        config_path=project["config"], secret_path=project["secret"], state_path=project["state"]
    )
    sessions = auth.Sessions(auth.read_or_make_secret(project["secret"]))
    client = TestClient(app)
    section = "Where this is going"

    client.cookies.set(auth.COOKIE, sessions.issue(ANA))
    client.post("/api/managers/demo/presence",
                json={"repoId": "demo-repo", "docId": "vision", "section": section})

    before = project["vision"].read_text(encoding="utf-8")

    # The manager session's own turn: read presence, decide, act.
    client.cookies.set(auth.COOKIE, sessions.issue(MANAGER_SESSION))
    here = client.get("/api/managers/demo/presence",
                      params={"repoId": "demo-repo", "docId": "vision"}).json()
    held = [one for one in here["others"] if one["section"] == section]
    print(f"\nthe manager session reads presence and finds: {[(o['user'], o['section']) for o in held]}")
    assert held, "the manager session could not see that a steward had the section open"

    answer = client.post(
        "/api/managers/demo/presence/queue",
        json={"repoId": "demo-repo", "docId": "vision", "section": section,
              "note": "rewording the second sentence"},
    ).json()
    print(f"the app told it: {answer['said']}")
    assert answer["queued"] is True
    assert answer["heldBy"] == ANA
    assert 0 < answer["expiresIn"] <= 60

    # It queued instead of writing, so the file is untouched -- and the steward
    # can see that something is waiting behind them.
    after = project["vision"].read_text(encoding="utf-8")
    waiting = client.get("/api/managers/demo/presence",
                         params={"repoId": "demo-repo", "docId": "vision"}).json()["queued"]
    print(f"the document changed while it waited: {after != before}")
    print(f"queued writes the steward can see: {[(q['user'], q['section'], q['note']) for q in waiting]}")
    assert after == before, "the manager session queued and the document changed anyway"
    assert [(q["user"], q["section"]) for q in waiting] == [(MANAGER_SESSION, section)]

    # ana closes the editor. Asking again now says: write it.
    client.cookies.set(auth.COOKIE, sessions.issue(ANA))
    client.post("/api/managers/demo/presence",
                json={"repoId": "demo-repo", "docId": "vision", "section": ""})
    client.cookies.set(auth.COOKIE, sessions.issue(MANAGER_SESSION))
    clear = client.post(
        "/api/managers/demo/presence/queue",
        json={"repoId": "demo-repo", "docId": "vision", "section": section},
    ).json()
    print(f"once ana closes the editor, the app says: {clear['said']}")
    assert clear["queued"] is False
    assert clear["heldBy"] is None


def test_presence_needs_a_sign_in_and_names_what_is_missing(project):
    """The gate is the middleware's, and a malformed ask is refused in words."""
    app = serve.create_app(
        config_path=project["config"], secret_path=project["secret"], state_path=project["state"]
    )
    stranger = TestClient(app)
    shut_out = stranger.post("/api/managers/demo/presence", json={"repoId": "r", "docId": "d"})
    print(f"\nno cookie: {shut_out.status_code} {shut_out.json()}")
    assert shut_out.status_code == 401

    signed = _signed_in(project, ANA)
    vague = signed.post("/api/managers/demo/presence", json={"section": "Principles"})
    nowhere = signed.get("/api/managers/nope/presence", params={"repoId": "r", "docId": "d"})
    print(f"no document named: {vague.status_code} {vague.json()['error']}")
    print(f"no such manager:   {nowhere.status_code} {nowhere.json()['error']}")
    assert vague.status_code == 400 and "document" in vague.json()["error"]
    assert nowhere.status_code == 404


# --------------------------------------------------------------------------
# two browsers, one document
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


def _boot(browser, server, project, user, width=1280, height=800, intercept=False):
    """One signed-in browser context.

    `intercept` blocks the service worker, and it is needed for exactly one
    reason: the app's own worker answers every `/api` fetch itself
    (`app/static/sw.js`), and a request made from inside a worker is not
    reachable by `page.route`. A test that tries to make the presence channel
    fail without this silently gets a working channel and a green assertion
    about nothing.
    """
    sessions = auth.Sessions(auth.read_or_make_secret(project["secret"]))
    ctx = browser.new_context(
        viewport={"width": width, "height": height},
        service_workers="block" if intercept else "allow",
    )
    ctx.add_cookies([{"name": auth.COOKIE, "value": sessions.issue(user),
                      "domain": "127.0.0.1", "path": "/"}])
    page = ctx.new_page()
    errors: list[str] = []
    page.on("console", lambda m: errors.append(f"console.{m.type}: {m.text}") if m.type == "error" else None)
    page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
    page.goto(server, wait_until="networkidle")
    page.wait_for_selector("#documentModeContent", timeout=15000)
    if width < 980:
        page.click("#consoleToggle")
        page.wait_for_timeout(500)
    return ctx, page, errors


#: A refusal the app MEANT to make is still a non-2xx fetch, and Chromium logs
#: every one of those to the console. The collision path is exactly that: the
#: server refuses a sentence that moved, the client catches the refusal and
#: offers the three choices. Counting that as a page error would make the
#: correct behaviour look broken — so it is separated out and PRINTED rather
#: than quietly swallowed, and everything else still has to be empty.
REFUSAL_NOISE = "Failed to load resource"


def _split(errors: list[str]) -> tuple[list[str], list[str]]:
    refusals = [one for one in errors if REFUSAL_NOISE in one and "pageerror" not in one]
    return [one for one in errors if one not in refusals], refusals


def _open_doc(page, title: str = "Vision") -> None:
    page.click(f'.repo-doc:has-text("{title}")')
    page.wait_for_selector("#documentModeContent section", timeout=10000)
    page.wait_for_timeout(400)


def _toast(page) -> str:
    return page.eval_on_selector("#toast", "el => el.textContent || ''")


def _open_editor(page):
    """Open the Reading view's editor on the first editable sentence."""
    controls = page.query_selector_all('[data-edit="open"]')
    assert controls, "no edit control was offered on the draft document"
    label = controls[0].inner_text()
    controls[0].click()
    page.wait_for_selector(".change-edit textarea", timeout=5000)
    return label


@needs_browser
@pytest.mark.parametrize("width,height", [(1280, 800), (390, 844)])
def test_the_other_steward_is_shown_softly_by_name(server, project, browser, width, height):
    """Two people, two browsers, one section. Neither is blocked."""
    ana_ctx, ana_page, ana_errors = _boot(browser, server, project, ANA, width, height)
    brook_ctx, brook_page, brook_errors = _boot(browser, server, project, BROOK, width, height)
    _open_doc(ana_page)
    _open_doc(brook_page)

    print(f"\n--- {width}x{height} ---")
    quiet = brook_page.query_selector_all("section.is-editing-elsewhere")
    print(f"brook sees sections held by someone else, before ana opens an editor: {len(quiet)}")
    assert quiet == [], "brook was shown a mark before anyone had an editor open"

    label = _open_editor(ana_page)
    print(f"ana opens: {label!r}")

    brook_page.wait_for_selector("section.is-editing-elsewhere", timeout=20000)
    line = brook_page.eval_on_selector("[data-presence-for]", "el => el.textContent")
    section = brook_page.eval_on_selector(
        "section.is-editing-elsewhere", "el => el.dataset.section")
    print(f"brook sees, within {20}s, on section {section!r}:")
    print(f"  {line}")
    assert ANA in line, f"the mark did not name who is editing: {line!r}"
    assert "editing this section" in line
    assert "not locked" in line.lower() or "Nothing is locked" in line

    # Courtesy, not a lock: every control brook has is still live.
    disabled = brook_page.eval_on_selector_all(
        "section.is-editing-elsewhere button", "els => els.filter(e => e.disabled).length")
    offered = brook_page.query_selector_all('section.is-editing-elsewhere [data-edit="open"]')
    print(f"controls disabled for brook on that section: {disabled}")
    print(f"edit controls still offered to brook on that section: {len(offered)}")
    assert disabled == 0, "presence disabled a control -- that is a lock, not courtesy"
    assert offered, "presence removed brook's own edit control"

    # And the section is actually shown softly, not merely classed as such.
    tint = brook_page.eval_on_selector(
        "section.is-editing-elsewhere", "el => getComputedStyle(el).backgroundImage")
    print(f"the soft marking resolves to: {tint[:60]}…")
    assert tint and tint != "none", "'shown softly' was a class name with no rule behind it"

    # Nothing overflows at either width with the mark on screen.
    for who, page in (("ana", ana_page), ("brook", brook_page)):
        m = page.evaluate(MEASURE)
        print(f"{who}: scrollWidth {m['scrollWidth']} vs clientWidth {m['clientWidth']} past={m['past']}")
        assert m["scrollWidth"] <= m["clientWidth"] + 1, f"{who}'s page overflows: {m['past']}"

    # Ana closes the editor: the mark is released, not left standing.
    ana_page.click('[data-edit="cancel"]')
    brook_page.wait_for_selector("section.is-editing-elsewhere", state="detached", timeout=20000)
    print("ana cancels; brook's mark clears without a reload: yes")

    print(f"console errors — ana: {ana_errors or 'none'}; brook: {brook_errors or 'none'}")
    assert not ana_errors and not brook_errors
    ana_ctx.close()
    brook_ctx.close()


@needs_browser
def test_a_collision_between_two_stewards_offers_the_three_choices(server, project, browser):
    """The half that was already real, now driven by two actual people.

    Presence does not prevent this and is not supposed to. Ana is shown that
    brook is there; she writes anyway; brook's write lands first; and what
    protects ana's sentence is the choice, not a lock.
    """
    ana_ctx, ana_page, ana_errors = _boot(browser, server, project, ANA)
    brook_ctx, brook_page, brook_errors = _boot(browser, server, project, BROOK)
    _open_doc(ana_page)
    _open_doc(brook_page)

    ana_label = _open_editor(ana_page)
    brook_label = _open_editor(brook_page)
    print(f"\nana has open:   {ana_label!r}")
    print(f"brook has open: {brook_label!r}")
    assert ana_label == brook_label, "the two stewards did not open the same sentence"

    # Each one sees the other, by name, before either writes.
    ana_page.wait_for_selector("section.is-editing-elsewhere", timeout=20000)
    brook_page.wait_for_selector("section.is-editing-elsewhere", timeout=20000)
    print(f"ana sees:   {ana_page.eval_on_selector('[data-presence-for]', 'el => el.textContent')}")
    print(f"brook sees: {brook_page.eval_on_selector('[data-presence-for]', 'el => el.textContent')}")

    before = project["vision"].read_text(encoding="utf-8")

    # Brook writes first, through the write path that already existed.
    brook_page.fill(".change-edit textarea", "The console is a place brook works in every day.")
    brook_page.click('[data-edit="save"]')
    brook_page.wait_for_timeout(1200)
    print(f"brook saved, and the app said: {_toast(brook_page)}")
    assert "brook works in every day" in project["vision"].read_text(encoding="utf-8")

    # Ana writes into the sentence that moved underneath her.
    ana_page.fill(".change-edit textarea", "The console is a place ana works in every day.")
    ana_page.click('[data-edit="save"]')
    ana_page.wait_for_selector("[data-reconcile]", timeout=15000)
    choices = [b.inner_text() for b in ana_page.query_selector_all("[data-reconcile]")]
    mid_flight = project["vision"].read_text(encoding="utf-8")
    print(f"ana is offered: {choices}")
    print(f"the app said:   {_toast(ana_page)}")
    print(f"ana's wording is in the file at this point: {'ana works in every day' in mid_flight}")
    assert choices == ["Use combined", "Keep mine", "Review both"]
    assert "ana works in every day" not in mid_flight, "something was written before a choice was taken"

    # The choice is a real write through the same path, not a staged one.
    ana_page.click('[data-reconcile="keep-mine"]')
    ana_page.wait_for_timeout(1500)
    after = project["vision"].read_text(encoding="utf-8")
    log = _git(project["repo"], "log", "-2", "--format=%s")
    print(f"ana chose Keep mine, and the app said: {_toast(ana_page)}")
    print(f"ana's wording is in the file now: {'ana works in every day' in after}")
    print("last two commits:\n  " + "\n  ".join(log.strip().splitlines()))
    assert after != before
    assert "ana works in every day" in after, "the choice reported back but the file did not change"
    assert "Converge" in log

    ana_real, ana_refusals = _split(ana_errors)
    brook_real, brook_refusals = _split(brook_errors)
    print(f"deliberate refusals the browser logged — ana: {ana_refusals or 'none'}; "
          f"brook: {brook_refusals or 'none'}")
    print(f"page errors — ana: {ana_real or 'none'}; brook: {brook_real or 'none'}")
    assert not ana_real and not brook_real
    assert ana_refusals, (
        "the collision was supposed to come from the SERVER refusing a sentence that moved; "
        "no refused request was logged at all, so the choices may have been offered by the "
        "browser deciding for itself"
    )
    ana_ctx.close()
    brook_ctx.close()


@needs_browser
def test_the_channel_going_away_does_not_take_the_reading_with_it(server, project, browser):
    """A courtesy that interrupts the reading is worse than one that is absent.

    The channel is made to fail (its route is answered with a 500 in the
    browser) and the document is asserted afterwards: still readable, still
    editable, no error on the screen, and the Details fold says plainly that
    presence is not answering rather than implying company that is not there.
    """
    ctx, page, errors = _boot(browser, server, project, ANA, intercept=True)
    page.route("**/api/managers/*/presence", lambda route: route.fulfill(
        status=500, content_type="application/json", body='{"error": "the presence channel is down"}'))
    _open_doc(page)
    label = _open_editor(page)
    page.wait_for_timeout(5000)  # more than one beat

    standing = page.eval_on_selector("[data-presence-standing]", "el => el.textContent")
    marks = page.query_selector_all("section.is-editing-elsewhere")
    own = page.query_selector_all("section.is-editing")
    toast = _toast(page)
    print(f"\nwith the channel refusing, the editor still opened on: {label!r}")
    print(f"sections marked as somebody else's: {len(marks)}")
    print(f"the steward's own section still shown softly: {len(own)}")
    print(f"the Details fold says: {standing}")
    print(f"anything shouted at the steward: {toast!r}")
    assert marks == [], "a failing channel invented company"
    assert own, "a failing channel took the steward's own soft marking with it"
    assert "not answering" in standing, f"the fold did not say the channel was down: {standing!r}"
    assert "presence" not in toast.lower(), "a courtesy interrupted the reading with a message"
    real, refusals = _split(errors)
    print(f"the refused beats the browser logged: {len(refusals)}")
    print(f"page errors: {real or 'none'}")
    assert refusals, "the channel was supposed to be failing and nothing failed"
    assert not real, "a failing courtesy threw an exception into the page"
    ctx.close()


@needs_browser
def test_offline_the_beat_stands_down_instead_of_shouting(server, project, browser):
    """With the network down there is nobody to tell, so nothing is sent.

    Beating anyway would reach the app's own service worker, which refuses a
    write while the network is down, logs it, and tells the page a write
    failed -- a message about a signal the steward never asked for, on the one
    screen already saying the app is offline. `test_offline.py` asserts that
    screen carries no browser errors, and a heartbeat is exactly the kind of
    thing that quietly breaks that.
    """
    ctx, page, errors = _boot(browser, server, project, ANA)
    _open_doc(page)
    _open_editor(page)
    page.wait_for_timeout(1000)

    asked: list[str] = []
    page.on("request", lambda r: asked.append(r.url) if "/presence" in r.url else None)
    ctx.set_offline(True)
    page.wait_for_timeout(9000)  # two beats' worth
    standing = page.eval_on_selector("[data-presence-standing]", "el => el.textContent")
    real, refusals = _split(errors)

    print(f"\npresence requests attempted while offline: {len(asked)}")
    print(f"the Details fold says: {standing}")
    print(f"page errors: {real or 'none'}; refused fetches: {refusals or 'none'}")
    assert asked == [], f"the beat shouted into a dead network: {asked}"
    assert "offline" in standing, f"the fold did not say why presence is quiet: {standing!r}"
    assert not real and not refusals, "beating offline put an error on a screen that is already offline"

    # And it comes back on its own. The second witness (the worker's own news
    # that something did not arrive) is read with a clock rather than as a
    # flag precisely so this cannot get stuck; the wait below is longer than
    # that clock, so a beat that never returns is a real failure and not a
    # race.
    ctx.set_offline(False)
    for _ in range(16):
        if asked:
            break
        page.wait_for_timeout(1000)
    print(f"presence requests once the network is back: {len(asked)}")
    assert asked, "the beat never restarted after the network came back"
    ctx.close()
