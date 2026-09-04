"""Rendered-browser tests for the two Direction writes converge-6cc adds.

`experience-direction.v1` §5 asks that a draft document be editable in place,
click to save, and that a locked one is refused *by the guard* rather than by a
hidden control. §10 asks that a person editing is shown softly and that a
collision offers Use combined · Keep mine · Review both. §9 asks that Ask be a
scoped request whose output is always a proposal.

None of that can be proved by reading files. `conformance/experience-direction`
is a deliberately static read: it can see that a control exists and that its
handler *reaches* a write, and says so plainly, but it cannot see the sentence
change on disk. These tests drive a real Chromium against the real app over a
real git repository and assert the file afterwards, which is the half the kit
cannot buy.

What is NOT covered here, honestly:

- **Ask returns nothing**, because the app answers no route that makes a
  proposal (`app/serve.py` and `app/writes.py` are another lane's files; the
  server half is filed as converge-ddt). The test below pins the behaviour that
  actually ships today — the ask fails out loud, names the gap, and writes
  nothing — so that when the route lands, this test fails and has to be
  rewritten to assert the proposal. A test that quietly tolerated both would be
  worth nothing.
- **Presence is this browser's own** (converge-wmh). There is no channel that
  carries a second steward, so nothing here claims one.

If Playwright or its Chromium build is unavailable every browser test skips
with the reason printed, and MANUAL_PROCEDURE below is the check that stands in
for it.
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

MANUAL_PROCEDURE = """
MANUAL PROCEDURE — run this by hand if Playwright is unavailable.
Each step says what you must SEE; seeing anything else is a failure.

Setup
  uv run --extra app python -m app.serve --host 127.0.0.1 --port 8788
  Open http://127.0.0.1:8788/ and choose a DRAFT document with changes.

Check — a draft is edited in place, and the save reaches the file
  a. In Read, SEE under a changed paragraph a button reading Edit “…”.
  b. Click it. SEE a box headed "The wording you want instead", carrying the
     sentence as it stands, and SEE the paragraph above it shown softly.
  c. Change the wording and click Save.
  d. SEE a message naming a commit ("Committed as abc1234 — …").
  e. In a terminal: `git -C <repo> log -1 --stat` SEE that commit, and
     `grep` the document SEE your new sentence in the file.
  FAILS IF: no edit control appears on a draft; or the message appears but
     `git log` shows no commit and the file still says the old sentence.

Check — a locked document is refused by the guard, not by the screen
  f. Open a document whose H1 carries (FROZEN …). SEE the same control, now
     reading "Propose wording for …".
  g. Write a wording and click "Propose this wording".
  h. SEE a message naming a candidate file. In a terminal, SEE that
     `<doc-stem>.vN-candidate.md` now exists and that the document itself is
     byte-for-byte unchanged (`git status` reports it unmodified).
  FAILS IF: the locked document changed at all, or the refusal came from the
     browser before any request was made.

Check — a collision offers all three choices
  i. Open the editor on a draft sentence. Leave it open.
  j. In a terminal, change and commit that same sentence out of band.
  k. Click Save. SEE "This moved while you were writing.", both wordings, and
     three buttons: Use combined · Keep mine · Review both.
  l. SEE the file is still unchanged at this point.
  m. Click Keep mine. SEE a commit message, and SEE your wording in the file.
  FAILS IF: fewer than three choices appear, or anything was written before a
     choice was taken.

Check — Ask is offered at all three scopes
  n. SEE an "Ask…" button in the document toolbar, and an
     "Ask about this paragraph" button under each paragraph.
  o. Click "Ask…". SEE a scope chooser offering this paragraph, this document,
     and every document.
  p. Write something and click Ask. SEE a message saying plainly that nothing
     was asked because the app answers no proposal route yet, naming
     converge-ddt.
  FAILS IF: the message implies an ask was recorded, or any file changed.

Check — it holds at both widths
  q. Repeat (a)-(c) at 1280x800 and at 390x844. At each, in the devtools
     console run:
       document.documentElement.scrollWidth + ' vs ' + document.documentElement.clientWidth
     SEE the two numbers equal, with the editor open.
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
# a project to serve: one draft, one locked, each with a sentence that moved
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

LOCKED_FIRST = """# Demo Contract — v1 (FROZEN 2026-09-01)

## Core

1. A decision is recorded where the manager session already reads.
2. Nothing is ever overwritten.
"""

LOCKED_SECOND = """# Demo Contract — v1 (FROZEN 2026-09-01)

## Core

1. A decision is recorded where the manager session already reads.
2. Nothing is ever overwritten, and every write says who made it.
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
    tmp_path = tmp_path_factory.mktemp("direction-writes")
    repo = tmp_path / "demo-repo"
    (repo / "docs").mkdir(parents=True)
    (repo / "contracts").mkdir(parents=True)
    (repo / "docs" / "VISION.md").write_text(VISION_FIRST, encoding="utf-8")
    (repo / "contracts" / "demo.v1.md").write_text(LOCKED_FIRST, encoding="utf-8")
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "seed: the vision and one contract")

    # A second commit, so each document has a sentence that moved and therefore
    # a sentence the document-saving write can still find.
    (repo / "docs" / "VISION.md").write_text(VISION_SECOND, encoding="utf-8")
    (repo / "contracts" / "demo.v1.md").write_text(LOCKED_SECOND, encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "the console becomes a place; writes name their author")

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
        "locked": repo / "contracts" / "demo.v1.md",
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


def _boot(browser, server, project, width=1280, height=800):
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
    if width < 980:
        # Below the breakpoint the Manager Console is a sheet over the page, so
        # it sits on top of the document tree. Closing it is what a steward
        # reading on a phone does; the console's own layout is another test's
        # subject (test_console_overflow_rendered.py).
        page.click("#consoleToggle")
        page.wait_for_timeout(500)
    return ctx, page, errors


def _open_doc(page, title: str) -> None:
    """Click the named document in the tree and wait for Read to draw it.

    The tree shows `data.py`'s SHORT title, not the document's H1 — "Vision"
    for `docs/VISION.md` and "Demo" for `contracts/demo.v1.md`.
    """
    page.click(f'.repo-doc:has-text("{title}")')
    page.wait_for_selector("#documentModeContent .since-banner, #documentModeContent section", timeout=10000)
    page.wait_for_timeout(400)


def _toast(page) -> str:
    return page.eval_on_selector("#toast", "el => el.textContent || ''")


def _save_wording(page, wording: str) -> None:
    page.fill(".change-edit textarea", wording)
    page.click('[data-edit="save"]')
    page.wait_for_timeout(900)


# --------------------------------------------------------------------------
# §5 — a draft is edited in place, and the save reaches the document
# --------------------------------------------------------------------------


@needs_browser
def test_a_draft_paragraph_offers_editing_and_the_save_lands_in_the_file(server, project, browser):
    ctx, page, errors = _boot(browser, server, project)
    _open_doc(page, "Vision")

    controls = page.query_selector_all('[data-edit="open"]')
    print(f"\nedit controls offered in Read on the draft: {len(controls)}")
    assert controls, "a DRAFT document offered no edit control anywhere in Read"

    before = project["vision"].read_text(encoding="utf-8")
    controls[0].click()
    page.wait_for_selector(".change-edit textarea", timeout=5000)

    soft = page.query_selector_all("section.is-editing")
    presence = page.eval_on_selector(".change-edit .lock-note", "el => el.textContent")
    print(f"sections shown softly while editing: {len(soft)}")
    print(f"presence line: {presence.strip()[:110]}…")
    assert soft, "the section being edited was not shown softly (§10 presence)"
    assert "presence" in presence.lower()

    _save_wording(page, "The console is a place you work, and it is where the run is watched.")
    said = _toast(page)
    after = project["vision"].read_text(encoding="utf-8")
    log = _git(project["repo"], "log", "-1", "--format=%s")
    print(f"the app said: {said}")
    print(f"last commit:  {log.strip()}")
    print(f"file now carries the new sentence: {'where the run is watched' in after}")
    print(f"console errors: {errors or 'none'}")

    assert after != before, "the save reported back but the document on disk did not change"
    assert "where the run is watched" in after
    assert "Committed as" in said, f"the app did not report a commit; it said: {said!r}"
    assert "Converge" in log, f"the commit was not made in the steward's name: {log!r}"
    ctx.close()


# --------------------------------------------------------------------------
# §5 — a locked document is refused by the guard, not by the screen
# --------------------------------------------------------------------------


@needs_browser
def test_a_locked_document_is_never_edited_in_place_and_the_guard_makes_a_proposal(
    server, project, browser
):
    ctx, page, errors = _boot(browser, server, project)
    _open_doc(page, "Demo")

    controls = page.query_selector_all('[data-edit="open"]')
    label = controls[0].inner_text() if controls else ""
    print(f"\nedit controls offered on the LOCKED document: {len(controls)}")
    print(f"the control reads: {label!r}")
    assert controls, (
        "the locked document offered no control at all — §5 asks for the refusal to come "
        "from the guard, which means the request has to be allowed to reach it"
    )
    assert "Propose" in label, f"the control on a locked document must not offer a save: {label!r}"

    untouched = project["locked"].read_text(encoding="utf-8")
    controls[0].click()
    page.wait_for_selector(".change-edit textarea", timeout=5000)
    _save_wording(page, "Nothing is ever overwritten, and every write says who made it and when.")

    said = _toast(page)
    candidate = project["repo"] / "contracts" / "demo.v1-candidate.md"
    print(f"the app said: {said}")
    print(f"candidate written: {candidate.is_file()} ({candidate.name})")
    print(f"the locked document is byte-identical: {project['locked'].read_text(encoding='utf-8') == untouched}")
    print(f"console errors: {errors or 'none'}")

    assert project["locked"].read_text(encoding="utf-8") == untouched, (
        "the locked document was written to — the guard is the law and it was not obeyed"
    )
    assert candidate.is_file(), "no proposal was written beside the locked document"
    body = candidate.read_text(encoding="utf-8")
    assert "and when" in body, "the steward's wording is not in the proposal"
    assert "FROZEN" in said, f"the refusal did not name the lock: {said!r}"
    ctx.close()


# --------------------------------------------------------------------------
# §10 — a collision offers all three choices, and writes nothing until one is taken
# --------------------------------------------------------------------------


@needs_browser
def test_a_collision_offers_all_three_choices_and_writes_nothing_until_one_is_taken(
    server, project, browser
):
    ctx, page, errors = _boot(browser, server, project)
    _open_doc(page, "Vision")

    controls = page.query_selector_all('[data-edit="open"]')
    assert controls, "no edit control to collide with"
    controls[0].click()
    page.wait_for_selector(".change-edit textarea", timeout=5000)

    # Someone else's write lands while the steward is typing. Not simulated:
    # a real commit, out of band, to the same sentence.
    vision = project["vision"]
    standing = vision.read_text(encoding="utf-8")
    moved = standing.replace(
        "The console is a place you work, and it is where the run is watched.",
        "The console is a place you work, and someone else rewrote this line.",
    )
    assert moved != standing, "the fixture's sentence was not where this test expected it"
    vision.write_text(moved, encoding="utf-8")
    _git(project["repo"], "commit", "-q", "-m", "someone else: rewrite the console sentence", "--", "docs/VISION.md")
    at_collision = vision.read_text(encoding="utf-8")

    _save_wording(page, "The console is a place you work, and this is the wording I wanted.")

    choices = [b.inner_text().strip() for b in page.query_selector_all("[data-reconcile]")]
    print(f"\nchoices offered on collision: {choices}")
    print(f"the app said: {_toast(page)}")
    print(f"file untouched while the choice is open: {vision.read_text(encoding='utf-8') == at_collision}")
    assert sorted(choices) == ["Keep mine", "Review both", "Use combined"], (
        f"§10 names three choices; this offered {choices}"
    )
    assert vision.read_text(encoding="utf-8") == at_collision, (
        "something was written before the steward chose — a collision must not resolve itself"
    )

    page.click('[data-reconcile="keep-mine"]')
    page.wait_for_timeout(1200)
    after = vision.read_text(encoding="utf-8")
    print(f"after Keep mine, the app said: {_toast(page)}")
    print(f"the steward's wording is in the file: {'this is the wording I wanted' in after}")
    print(f"console errors: {errors or 'none'}")
    assert "this is the wording I wanted" in after, "Keep mine did not keep the steward's wording"
    assert "someone else rewrote this line" not in after
    ctx.close()


# --------------------------------------------------------------------------
# §9 — Ask is offered at all three scopes, and says plainly what it could not do
# --------------------------------------------------------------------------


@needs_browser
def test_ask_is_offered_at_three_scopes_and_never_pretends_it_recorded_anything(
    server, project, browser
):
    ctx, page, errors = _boot(browser, server, project)
    _open_doc(page, "Vision")

    toolbar = page.query_selector('#askButton[data-ask]')
    paragraph = page.query_selector_all('[data-ask][data-ask-scope="paragraph"]')
    print(f"\nAsk in the document toolbar: {bool(toolbar)}")
    print(f"Ask beside a paragraph: {len(paragraph)}")
    assert toolbar, "no Ask control at document scope"
    assert paragraph, "no Ask control at paragraph scope"

    toolbar.click()
    page.wait_for_selector("#askScope", timeout=5000)
    scopes = page.eval_on_selector_all("#askScope option", "els => els.map(e => e.value)")
    labels = page.eval_on_selector_all("#askScope option", "els => els.map(e => e.textContent.trim())")
    print(f"scopes offered: {scopes}")
    print(f"labelled: {labels}")
    assert scopes == ["paragraph", "document", "all"], (
        f"§9 names a paragraph, a document, and every document; this offered {scopes}"
    )

    clean_before = _git(project["repo"], "status", "--porcelain")
    head_before = _git(project["repo"], "rev-parse", "HEAD").strip()
    page.fill("#askWhat", "Say plainly what the console is for.")
    page.click('#dialogActions button:text-is("Ask")')
    page.wait_for_timeout(900)

    said = _toast(page)
    print(f"the app said: {said}")
    print(f"working tree unchanged: {_git(project['repo'], 'status', '--porcelain') == clean_before}")
    print(f"HEAD unchanged: {_git(project['repo'], 'rev-parse', 'HEAD').strip() == head_before}")
    print(f"console errors: {errors or 'none'}")

    # Today the app answers no proposal-producing route (converge-ddt), so the
    # only honest outcome is a refusal that names the gap. When the route lands
    # this assertion must fail and be replaced by one about the proposal.
    assert "Nothing was asked" in said, f"an ask that could not be carried did not say so: {said!r}"
    assert "converge-ddt" in said, "the refusal did not name the work that would fix it"
    assert _git(project["repo"], "status", "--porcelain") == clean_before, (
        "the ask changed a file — §9 says an ask is never a silent edit"
    )
    assert _git(project["repo"], "rev-parse", "HEAD").strip() == head_before
    ctx.close()


# --------------------------------------------------------------------------
# platform-web.v1 — the editing surface holds at both widths
# --------------------------------------------------------------------------


@needs_browser
@pytest.mark.parametrize("width,height", [(1280, 800), (390, 844)])
def test_the_reading_view_holds_at_both_widths_with_the_editor_open(
    server, project, browser, width, height
):
    ctx, page, errors = _boot(browser, server, project, width, height)
    _open_doc(page, "Vision")

    shut = page.evaluate(MEASURE)
    controls = page.query_selector_all('[data-edit="open"]')
    assert controls, "no edit control to open"
    controls[0].click()
    page.wait_for_selector(".change-edit textarea", timeout=5000)
    page.wait_for_timeout(300)
    open_ = page.evaluate(MEASURE)

    print(f"\n[{width}] editor closed: scrollWidth={shut['scrollWidth']} clientWidth={shut['clientWidth']}")
    print(f"[{width}] editor open:   scrollWidth={open_['scrollWidth']} clientWidth={open_['clientWidth']}")
    if open_["past"]:
        print(f"[{width}] boxes past the right edge (diagnostic only): {open_['past']}")
    print(f"[{width}] console errors: {errors or 'none'}")

    assert shut["scrollWidth"] <= shut["clientWidth"], (
        f"Read widened the page at {width}: {shut['scrollWidth']} > {shut['clientWidth']}; {shut['past']}"
    )
    assert open_["scrollWidth"] <= open_["clientWidth"], (
        f"the open editor widened the page at {width}: {open_['scrollWidth']} > "
        f"{open_['clientWidth']}; {open_['past']}"
    )
    assert not errors, f"the browser reported errors: {errors}"
    ctx.close()
