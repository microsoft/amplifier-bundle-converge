"""converge-lf6n -- one continuous steward journey, in a real browser, at both widths.

Every other rendered test in this app proves ONE segment: that a draft edit
lands in the file, that a locked document makes a proposal instead, that Ask
names a proposal, that the reader's badges read honestly.  None of them proves
that a steward who comes back from being away can walk the whole way through --
Home, the manager's return brief, the document, its history, its source, a
wording they save, a wording they propose against a locked document, and the
word they finally give -- without hitting a dead end.  That continuous walk is
what `experience-direction.v1` and `experience-operation.v1` promise together
and what this file measures.

## What it drives, in order, without leaving the browser

1.  **Home** -- the list of manager sessions, one card per session.
2.  **Operation** -- the return brief the manager session left, read as the
    five labelled parts `experience-operation.v1` Core 3 names.
3.  **Direction / Read** -- the draft document, drawn.
4.  **Raw** -- the Markdown source, one gesture away (`experience-direction.v1`
    Core 2), and back again.
5.  **History** -- the document's own commits, each a real sha.
6.  **Changes** -- the sentence that moved since the read point.
7.  **Save a wording** on the DRAFT: the file on disk carries the steward's
    bytes afterwards, and git made a commit for it.
8.  **Download the source**: the bytes the browser saved are byte-for-byte the
    file on disk.
9.  **Propose a wording** on the LOCKED document: a candidate appears beside
    it and the locked file's bytes do not move.
10. **Review** -- that proposal, and the steward's word on it: the ratification
    record on disk names the decision, the document, the proposal and the
    author.
11. **Reload** -- everything above is still true after a full page reload, read
    back from the server rather than from the page that wrote it.
12. **A different signed-in user** is refused the decision, and writes nothing.

Steps 7, 9, 10 and 12 are the four writes; each is awaited on its own HTTP
response and then read back off the filesystem, never slept on.

## What would make this evidence false

* A control clicked through `force=True`, or dispatched in JavaScript, rather
  than clicked where a steward would click it.  Every click here goes through
  `_click`, which first asserts that the point it is about to click actually
  belongs to that control -- an occluded control fails rather than being poked
  through whatever is covering it.
* A production guard relaxed to make a step pass.  Step 9 and step 12 are the
  two guards, and both are asserted to REFUSE.
* An assertion on what the page says instead of on what is on disk.  Every
  write here is checked against the repository, and the repository is a real
  git repository with real commits, built fresh per width.

## Running it by hand, if Playwright is unavailable

    uv run --extra app --with pytest --with httpx --with playwright \
        python -m pytest app/tests/test_hackathon_journey.py -x -s

With no browser, sign in to a served instance and repeat the twelve steps
above at 1280x800 and at 390x844, checking each write in the repository with
`git status` / `git log -p`.

Two managers, two repositories, one per width: the journey WRITES, so the
1280 walk and the 390 walk must not read each other's leavings.  Home showing
both is itself part of step 1.
"""

from __future__ import annotations

import os
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
OTHER_USER = "someone-else"

#: Screenshot destination, configured by the environment or allocated by pytest.
EVIDENCE: Path | None = None


def _evidence_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return Path(
        os.environ.get("CONVERGE_JOURNEY_EVIDENCE")
        or tmp_path_factory.mktemp("journey-evidence")
    )


@pytest.fixture(scope="session", autouse=True)
def evidence_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Keep unconfigured evidence isolated to this pytest session."""
    global EVIDENCE
    EVIDENCE = _evidence_dir(tmp_path_factory)
    return EVIDENCE


def test_evidence_dir_defaults_to_pytest_temp(
    monkeypatch: pytest.MonkeyPatch, tmp_path_factory: pytest.TempPathFactory
) -> None:
    monkeypatch.delenv("CONVERGE_JOURNEY_EVIDENCE", raising=False)
    assert _evidence_dir(tmp_path_factory).parent == tmp_path_factory.getbasetemp()


def test_evidence_dir_honors_override(
    monkeypatch: pytest.MonkeyPatch, tmp_path_factory: pytest.TempPathFactory, tmp_path: Path
) -> None:
    monkeypatch.setenv("CONVERGE_JOURNEY_EVIDENCE", str(tmp_path / "evidence"))
    assert _evidence_dir(tmp_path_factory) == tmp_path / "evidence"


# --------------------------------------------------------------------------
# availability -- the same shape every rendered test in this app uses
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
    reason=f"{PLAYWRIGHT_SKIP}; walk the twelve steps in this file's docstring by hand instead",
)


# --------------------------------------------------------------------------
# the fixture repository: a draft, a locked contract, a return brief, history
# --------------------------------------------------------------------------

VISION_FIRST = """# Steward Demo Vision (DRAFT)

## Where this is going

A steward who has been away reads one page and knows where things stand.
The console is a tab you visit when something breaks.
"""

VISION_SECOND = """# Steward Demo Vision (DRAFT)

## Where this is going

A steward who has been away reads one page and knows where things stand.
The console is a place you work, not a tab you visit.
"""

LOCKED_FIRST = """# Steward Demo Contract — v1 (FROZEN 2026-09-01)

## Core

1. A decision is recorded where the manager session already reads.
2. Nothing is ever overwritten.
"""

LOCKED_SECOND = """# Steward Demo Contract — v1 (FROZEN 2026-09-01)

## Core

1. A decision is recorded where the manager session already reads.
2. Nothing is ever overwritten, and every write says who made it.
"""

#: One entry, written to the return-brief convention, so all five of
#: `experience-operation.v1` Core 3's parts are labelled and the page can say
#: so rather than guessing which unlabelled sentence "is really" the stuck one.
RETURN_LOG = """# Owner return log

## 2026-09-08 09:12 - return

**Time away.** Eleven hours, two waves.
**Finished.** The document journey now runs end to end in a real browser.
**Stuck.** Nothing is stuck this turn.
**Needs you.** One proposal against the demo contract is waiting on your word.
**Anything quietly broken.** Nothing quietly broke overnight.
"""

HIGHWAY = """# Highway — steward demo

## Outcome

A returning steward walks from Home to a recorded decision without a dead end.
"""

MANIFEST_HEAD = "lane\tworktree\tbranch\tbase\ttmux\tgoal\tlog\tstarted\n"

#: (manager id, viewport width, viewport height, screenshot tag)
WIDTHS = [
    ("wide", 1280, 800, "1280"),
    ("narrow", 390, 844, "390"),
]


def _git(repo: Path, *args: str) -> str:
    done = subprocess.run(
        ["git", "-c", "user.name=Test", "-c", "user.email=test@example.invalid", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    return done.stdout


def _seed_repo(root: Path, name: str) -> Path:
    """A real repository with real history -- never a fixture of the answers."""
    repo = root / name
    (repo / "docs" / "workflow").mkdir(parents=True)
    (repo / "contracts").mkdir(parents=True)
    (repo / "docs" / "VISION.md").write_text(VISION_FIRST, encoding="utf-8")
    (repo / "contracts" / "demo.v1.md").write_text(LOCKED_FIRST, encoding="utf-8")
    (repo / "docs" / "workflow" / "OWNER-RETURN-LOG.md").write_text(RETURN_LOG, encoding="utf-8")
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "seed: the vision, one contract, and the return log")

    # A second commit, so each document has a sentence that MOVED -- which is
    # what a change card is, and what the Changes view has to have to offer an
    # edit at all.
    (repo / "docs" / "VISION.md").write_text(VISION_SECOND, encoding="utf-8")
    (repo / "contracts" / "demo.v1.md").write_text(LOCKED_SECOND, encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "the console becomes a place; writes name their author")
    return repo


@pytest.fixture(scope="module")
def project(tmp_path_factory) -> dict:
    tmp_path = tmp_path_factory.mktemp("hackathon-journey")
    repos = {tag: _seed_repo(tmp_path, f"{mid}-repo") for mid, _w, _h, tag in WIDTHS}

    blocks = []
    for (mid, _w, _h, tag) in WIDTHS:
        batch = tmp_path / f"hw-{mid}"
        (batch / "goals").mkdir(parents=True)
        (batch / "lanes" / "w1-alpha").mkdir(parents=True)
        (batch / "HIGHWAY.md").write_text(HIGHWAY, encoding="utf-8")
        (batch / "goals" / "w1-alpha.md").write_text("# Lane alpha\n", encoding="utf-8")
        (batch / "lanes" / "w1-alpha" / "lane.log").write_text("working\n", encoding="utf-8")
        (batch / "manifest.tsv").write_text(
            MANIFEST_HEAD
            + f"w1-alpha\t{batch}/lanes/w1-alpha/demo-repo\tlane/w1-alpha\tdeadbee\t"
            f"hw__hw-{mid}__w1-alpha\t{batch}/goals/w1-alpha.md\t"
            f"{batch}/lanes/w1-alpha/lane.log\t2026-09-08T10:00:00Z\n",
            encoding="utf-8",
        )
        blocks.append(
            "[[managers]]\n"
            f'id = "{mid}"\n'
            f'name = "Steward demo {mid}"\n'
            f'batch_dir = "{batch}"\n'
            f'repos = ["{repos[tag]}"]\n'
            f'steward = "{USER}"\n'
            'tracker_project = ""\n'
            'tmux_socket = "test-socket-that-does-not-exist"\n'
        )

    conf = tmp_path / "converge-app.toml"
    conf.write_text("\n".join(blocks), encoding="utf-8")
    # Never the real ~/.amplifier: a test must not move a steward's read point,
    # and must not touch a live manager session or a real project.
    return {
        "config": conf,
        "secret": tmp_path / "secret",
        "state": tmp_path / "state.json",
        "sessions": tmp_path / "sessions.json",
        "repos": repos,
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
        config_path=project["config"],
        secret_path=project["secret"],
        state_path=project["state"],
        sessions_path=project["sessions"],
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
# driving -- clicks a steward could make, waits on things that actually happen
# --------------------------------------------------------------------------


#: Is the point we are about to click actually this control's own point?  A
#: control covered by a sheet, a banner or a dialog answers no, and the click
#: that follows would land on the coverer -- silently, with no error, which is
#: exactly the shape of failure a screenshot review misses.
HIT = """
(el) => {
  if (!el) return {found: false};
  const r = el.getBoundingClientRect();
  if (r.width === 0 || r.height === 0) return {found: true, box: false};
  const x = Math.round(r.left + r.width / 2);
  const y = Math.round(r.top + r.height / 2);
  const at = document.elementFromPoint(x, y);
  return {
    found: true,
    box: true,
    inViewport: r.top >= 0 && r.left >= 0
      && r.bottom <= document.documentElement.clientHeight
      && r.right <= document.documentElement.clientWidth,
    hit: !!(at && (at === el || el.contains(at) || at.contains(el))),
    covering: at ? ((at.id ? '#' + at.id : '') + '.' + String(at.className || at.tagName)).slice(0, 80) : 'nothing',
  };
}
"""


def _click(page, selector: str, *, what: str = "") -> None:
    """Click a control the way a steward would, and refuse to fake it.

    `page.click` already declines a hidden or disabled control.  What it does
    NOT decline is a control whose centre is covered by something else and
    which therefore takes the click on a different element's behalf.  So the
    hit test runs first, after scrolling the control into view, and an
    occluded control fails the test by name instead of being forced.
    """
    label = what or selector
    # `page.locator`, not `document.querySelector`: several selectors here are
    # Playwright's own (`:has-text(...)`), which the DOM does not parse.
    where = page.locator(selector).first
    where.wait_for(state="visible", timeout=15000)
    where.evaluate("el => el.scrollIntoView({block: 'center'})")
    page.wait_for_timeout(60)
    state = where.evaluate(HIT)
    assert state.get("found"), f"{label}: no such control on the page ({selector})"
    assert state.get("box"), f"{label}: the control has no box, so nothing could be clicked"
    assert state.get("hit"), (
        f"{label}: the centre of this control belongs to {state.get('covering')!r}, "
        "so a click there would land somewhere else"
    )
    where.click()  # never force=True: an unclickable control is a defect


def _boot(browser, server, project, *, width: int, height: int, user: str = USER):
    sessions = auth.Sessions(auth.read_or_make_secret(project["secret"]))
    ctx = browser.new_context(viewport={"width": width, "height": height}, accept_downloads=True)
    ctx.add_cookies(
        [{"name": auth.COOKIE, "value": sessions.issue(user), "domain": "127.0.0.1", "path": "/"}]
    )
    page = ctx.new_page()
    errors: list[str] = []
    page.on("console", lambda m: errors.append(f"console.{m.type}: {m.text}") if m.type == "error" else None)
    page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
    page.goto(server, wait_until="networkidle")
    page.wait_for_selector("[data-home-manager]", timeout=15000)
    _stow_console(page, width)
    return ctx, page, errors


def _stow_console(page, width: int) -> bool:
    """Below the breakpoint, put the Manager Console away before reading.

    The console is a SHEET over the page below 980px, so while it is open it
    genuinely covers the document tree -- `_click`'s hit test says so by name.
    Stowing it is the gesture a steward makes on a phone, through the console's
    own visible toggle, and it is idempotent: an already-stowed console is left
    alone rather than toggled back open.

    It is called again after each screen change because `state.consoleOpen`
    lives in the page, and a reload starts a fresh page with the console open
    again -- which is the app's own default, not something this test may
    quietly rewrite.
    """
    if width >= 980:
        return False
    pressed = page.eval_on_selector(
        "#consoleToggle", "el => el.getAttribute('aria-pressed')"
    )
    if pressed != "true":
        return False
    _click(page, "#consoleToggle", what="stow the Manager Console sheet")
    page.wait_for_function(
        "() => document.getElementById('consoleToggle').getAttribute('aria-pressed') === 'false'",
        timeout=10000,
    )
    page.wait_for_timeout(250)
    return True


def _shot(page, tag: str, name: str) -> Path:
    assert EVIDENCE is not None, "pytest did not initialize the evidence directory"
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    path = EVIDENCE / f"{tag}-{name}.png"
    page.screenshot(path=str(path), full_page=False)
    return path


def _toast(page) -> str:
    return page.eval_on_selector("#toast", "el => el.textContent || ''").strip()


def _await_toast(page, timeout: int = 15000) -> str:
    """Wait for the app to actually say something, then read it.

    The prior toast has naturally hidden before the action raises a new one, so a
    stale line left over from the previous step can never be read as this
    step's success -- the one mistake a journey test cannot afford.
    """
    page.wait_for_function(
        """() => {
          const el = document.getElementById('toast');
          return el && !el.classList.contains('hidden') && el.textContent.trim().length > 0;
        }""",
        timeout=timeout,
    )
    return _toast(page)


def _clear_toast(page) -> None:
    # Observe the app's own dismissal; mutating the DOM could hide an overlay.
    page.wait_for_function(
        "() => document.getElementById('toast').classList.contains('hidden')",
        timeout=10000,
    )


def _open_doc(page, title: str) -> None:
    """Open the named document from the tree and wait for Read to draw it.

    The tree carries `data.py`'s SHORT, filename-derived title -- "Vision" for
    `docs/VISION.md`, "Demo" for `contracts/demo.v1.md` -- not the H1.
    """
    _click(page, f'.repo-doc:has-text("{title}")', what=f"the {title} document")
    page.wait_for_selector("#documentModeContent .since-banner, #documentModeContent section", timeout=15000)
    page.wait_for_function(
        "() => (document.getElementById('docTitle').textContent || '').trim().length > 0",
        timeout=15000,
    )


def _mode(page, mode: str) -> None:
    _click(page, f'[data-doc-mode="{mode}"]', what=f"the {mode} tab")
    page.wait_for_timeout(250)


def _head(repo: Path) -> str:
    return _git(repo, "rev-parse", "HEAD").strip()


def _status(repo: Path) -> set[str]:
    return {line[3:].strip() for line in _git(repo, "status", "--porcelain").splitlines() if line.strip()}


def _save_wording(page, wording: str, *, expect_label: str, what: str) -> tuple[int, dict]:
    """Open the editor on the first change card, type, save, await the answer.

    Returns the write's HTTP status and its decoded body -- what the SERVER
    did, not what the page then chose to draw.
    """
    _click(page, '.change-card [data-change-action="edit"]', what="Edit wording on the first change")
    page.wait_for_selector(".change-card .change-edit:not(.hidden) textarea", timeout=10000)
    label = page.eval_on_selector(
        '.change-card .change-edit:not(.hidden) [data-change-action="save-edit"]',
        "el => el.textContent.trim()",
    )
    assert label == expect_label, (
        f"{what}: the save control reads {label!r}, not {expect_label!r} -- "
        "the page is offering the wrong write for this document's lock state"
    )
    page.fill(".change-card .change-edit:not(.hidden) textarea", wording)
    _clear_toast(page)
    with page.expect_response(
        lambda r: "/changes/" in r.url and r.request.method == "POST", timeout=20000
    ) as caught:
        _click(page, '.change-card .change-edit:not(.hidden) [data-change-action="save-edit"]', what=label)
    response = caught.value
    said = _await_toast(page)
    print(f"    [{what}] {response.status} {response.url.split('/api/')[-1]}  app said: {said!r}")
    body = response.json()
    return response.status, body


# --------------------------------------------------------------------------
# the journey
# --------------------------------------------------------------------------


@needs_browser
@pytest.mark.parametrize("manager_id,width,height,tag", WIDTHS, ids=[w[3] for w in WIDTHS])
def test_a_returning_steward_walks_home_to_a_recorded_decision_without_a_dead_end(
    server, project, browser, manager_id, width, height, tag
):
    repo: Path = project["repos"][tag]
    vision = repo / "docs" / "VISION.md"
    locked = repo / "contracts" / "demo.v1.md"
    candidate = repo / "contracts" / "demo.v1-candidate.md"
    print(f"\n=== {width}x{height} · manager {manager_id} · {repo} ===")

    ctx, page, errors = _boot(browser, server, project, width=width, height=height)
    try:
        # -- 1. Home ---------------------------------------------------------
        cards = page.eval_on_selector_all(
            "[data-home-manager]", "els => els.map(e => e.dataset.homeManager)"
        )
        summary = page.eval_on_selector(
            f'[data-home-manager="{manager_id}"] p', "el => el.textContent.trim()"
        )
        print(f"  1. Home lists {cards}; {manager_id} says: {summary!r}")
        assert sorted(cards) == sorted(m for m, *_ in WIDTHS), (
            f"Home did not list both manager sessions: {cards}"
        )
        assert summary and "Loading" not in summary, f"the card says nothing useful: {summary!r}"
        _shot(page, tag, "01-home")

        # -- 2. Operation: the return brief, in five labelled parts ----------
        _click(page, f'[data-home-manager="{manager_id}"]', what=f"the {manager_id} session card")
        page.wait_for_selector("#operationView:not(.hidden)", timeout=15000)
        _stow_console(page, width)
        page.wait_for_selector("#returnBrief .brief-item", timeout=15000)
        brief = page.eval_on_selector("#returnBrief", "el => el.textContent.trim()")
        parts = page.eval_on_selector("#briefParts", "el => el.textContent.trim()")
        print(f"  2. Operation brief: {brief[:110]!r}…\n     five parts: {parts!r}")
        assert "The document journey now runs end to end" in brief, (
            f"the return brief on screen is not the one the manager session wrote: {brief!r}"
        )
        assert "All five parts are labelled in this brief." in parts, (
            f"the five parts were not read off the brief: {parts!r}"
        )
        for label in ("Time away", "What finished", "What is stuck", "What needs your word", "What quietly changed"):
            assert label in parts, f"the brief reading never names {label!r}: {parts!r}"
        _shot(page, tag, "02-operation-return-brief")

        # -- 3. Direction / Read --------------------------------------------
        _click(page, "#directionTab", what="the Direction tab")
        page.wait_for_selector("#directionView:not(.hidden)", timeout=15000)
        _stow_console(page, width)
        _open_doc(page, "Vision")
        read_text = page.eval_on_selector("#documentModeContent", "el => el.textContent")
        badge = page.eval_on_selector("#docStateBadge", "el => el.textContent.trim()")
        print(f"  3. Read draws {len(read_text)} chars; agreement badge={badge!r}")
        assert "The console is a place you work" in read_text, (
            "the draft's current wording is not in the rendered Read view"
        )
        assert badge == "Draft", f"a DRAFT document's agreement badge reads {badge!r}"
        _shot(page, tag, "03-direction-read")

        # -- 4. Raw, and back ------------------------------------------------
        _click(page, "#rawToggle", what="the Raw toggle")
        page.wait_for_timeout(300)
        raw_text = page.eval_on_selector("#documentModeContent", "el => el.textContent")
        assert "# Steward Demo Vision (DRAFT)" in raw_text, (
            f"Raw does not show the Markdown source: {raw_text[:160]!r}"
        )
        print(f"  4. Raw shows the source ({len(raw_text)} chars), H1 included")
        _shot(page, tag, "04-direction-raw")
        _click(page, "#rawToggle", what="the Raw toggle (off)")
        page.wait_for_timeout(250)

        # -- 5. History ------------------------------------------------------
        _mode(page, "history")
        page.wait_for_selector("[data-history]", timeout=15000)
        shas = page.eval_on_selector_all(
            "[data-history]", "els => els.map(e => e.dataset.historySha).filter(Boolean)"
        )
        real = _git(repo, "log", "--format=%h", "--", "docs/VISION.md").split()
        print(f"  5. History offers {len(shas)} commits {shas}; git knows {real}")
        assert len(shas) >= 2, f"a document with two commits offered {len(shas)} history rows"
        assert any(any(s.startswith(r) or r.startswith(s) for r in real) for s in shas), (
            f"the history rows name shas this repository does not have: {shas} vs {real}"
        )
        _shot(page, tag, "05-direction-history")

        # -- 6/7. Changes, and a wording saved into the DRAFT -----------------
        _mode(page, "changes")
        page.wait_for_selector(".change-card", timeout=15000)
        count = len(page.query_selector_all(".change-card"))
        before_bytes = vision.read_bytes()
        before_head = _head(repo)
        print(f"  6. Changes shows {count} card(s); HEAD before the save is {before_head[:8]}")
        assert count >= 1, "a document whose sentence moved offered no change card"
        _shot(page, tag, "06-direction-changes")

        wording = f"The console is a place you work, and this sentence was written at {tag} by a steward."
        status, body = _save_wording(
            page, wording, expect_label="Save and commit", what="7. draft save"
        )
        assert status == 200 and body.get("ok"), f"the draft save was refused: {status} {body}"
        page.wait_for_timeout(400)
        after_bytes = vision.read_bytes()
        after_head = _head(repo)
        print(
            f"  7. VISION.md {len(before_bytes)}B -> {len(after_bytes)}B; "
            f"HEAD {before_head[:8]} -> {after_head[:8]}; dirty={sorted(_status(repo))}"
        )
        assert wording.encode("utf-8") in after_bytes, (
            "the steward's bytes are not in the file on disk after the save"
        )
        assert after_bytes != before_bytes, "the file on disk did not change at all"
        assert after_head != before_head, "the draft save made no commit"
        assert "docs/VISION.md" not in _status(repo), (
            f"the saved document was left uncommitted: {sorted(_status(repo))}"
        )

        # -- 8. Download the source -------------------------------------------
        _mode(page, "read")
        _click(page, "#toolsMenu summary", what="the Tools menu")
        page.wait_for_timeout(200)
        with page.expect_download(timeout=20000) as caught:
            _click(page, "#downloadDoc", what="Download")
        download = caught.value
        EVIDENCE.mkdir(parents=True, exist_ok=True)
        saved = EVIDENCE / f"{tag}-downloaded-{download.suggested_filename}"
        download.save_as(str(saved))
        got = saved.read_bytes()
        print(
            f"  8. downloaded {download.suggested_filename!r} -> {saved} "
            f"({len(got)}B); file on disk is {len(after_bytes)}B"
        )
        assert got == after_bytes, (
            "the downloaded source is not byte-for-byte the document on disk "
            f"({len(got)}B vs {len(after_bytes)}B)"
        )
        assert wording.encode("utf-8") in got, "the download predates the steward's own save"
        _click(page, "#toolsMenu summary", what="the Tools menu (closed)")

        # -- 9. The locked document: a proposal, never an edit in place --------
        _open_doc(page, "Demo")
        lock_badge = page.eval_on_selector("#docStateBadge", "el => el.textContent.trim()")
        assert "FROZEN" in lock_badge, f"the locked contract's badge reads {lock_badge!r}"
        _mode(page, "changes")
        page.wait_for_selector(".change-card", timeout=15000)
        locked_before = locked.read_bytes()
        assert not candidate.exists(), "a candidate existed before the steward proposed anything"

        proposed = f"Nothing is ever overwritten, every write says who made it, and {tag} proves it."
        status, body = _save_wording(
            page, proposed, expect_label="Propose this wording", what="9. locked propose"
        )
        page.wait_for_timeout(400)
        print(
            f"  9. mode={body.get('mode')!r} file={body.get('file')!r}; "
            f"locked file {len(locked_before)}B -> {len(locked.read_bytes())}B"
        )
        assert status == 200 and body.get("ok"), f"the proposal write failed: {status} {body}"
        assert body.get("mode") == "candidate", (
            f"a locked document took an edit in place instead of proposing: {body}"
        )
        assert locked.read_bytes() == locked_before, (
            "THE GUARD FAILED: the locked document's own bytes moved"
        )
        assert candidate.is_file(), f"no candidate was written beside the locked document: {body}"
        candidate_text = candidate.read_text(encoding="utf-8")
        assert proposed in candidate_text, "the candidate does not carry the steward's wording"
        _shot(page, tag, "07-locked-proposal")

        # -- 10. Review, and the steward's word --------------------------------
        _mode(page, "review")
        page.wait_for_selector("[data-decision]", timeout=15000)
        offered = page.eval_on_selector_all("[data-decision]", "els => els.map(e => e.dataset.decision)")
        heading = page.eval_on_selector(".review-hero h2", "el => el.textContent.trim()")
        print(f" 10. Review shows {heading!r}; decisions offered: {offered}")
        assert "ratified" in offered and "declined" in offered and "later" in offered, (
            f"the Review sheet does not offer the steward's four words: {offered}"
        )
        record_dir = repo / "docs" / "workflow"
        before_records = set(record_dir.glob("owner-ratifications-*.md"))
        _clear_toast(page)
        with page.expect_response(
            lambda r: r.url.endswith("/decision") and r.request.method == "POST", timeout=20000
        ) as caught:
            _click(page, '[data-decision="ratified"]', what="Ratify")
        decision_response = caught.value
        said = _await_toast(page)
        decision_body = decision_response.json()
        print(f"     decision {decision_response.status}: app said {said!r}")
        assert decision_response.status == 200 and decision_body.get("ok"), (
            f"the decision was not recorded: {decision_response.status} {decision_body}"
        )
        assert "Recorded in" in said, f"the app did not confirm the record: {said!r}"

        records = set(record_dir.glob("owner-ratifications-*.md")) - before_records
        assert len(records) == 1, f"the decision wrote {len(records)} records, not one: {records}"
        record = records.pop()
        record_text = record.read_text(encoding="utf-8")
        print(f"     record {record.name}:\n       " + "\n       ".join(
            line for line in record_text.splitlines() if line.strip().startswith("- **")
        ))
        assert "**Decision:** Ratified" in record_text, f"the record's word is wrong:\n{record_text}"
        assert f"**By:** {USER}" in record_text, f"the record does not name the author:\n{record_text}"
        assert "demo.v1-candidate" in record_text, "the record does not name the proposal decided"
        assert "demo" in record_text, "the record does not name the document decided"
        _shot(page, tag, "08-review-decision")

        # -- 11. Reload: every write above survives a fresh read ---------------
        page.reload(wait_until="networkidle")
        page.wait_for_selector("[data-home-manager]", timeout=15000)
        _stow_console(page, width)
        _click(page, f'[data-home-manager="{manager_id}"]', what=f"the {manager_id} session card")
        page.wait_for_selector("#operationView:not(.hidden)", timeout=15000)
        _stow_console(page, width)
        _click(page, "#directionTab", what="the Direction tab")
        page.wait_for_selector("#directionView:not(.hidden)", timeout=15000)
        _stow_console(page, width)

        _open_doc(page, "Vision")
        reread = page.eval_on_selector("#documentModeContent", "el => el.textContent")
        assert wording in reread, (
            "after a reload the saved wording is not what the server serves back"
        )
        _open_doc(page, "Demo")
        _mode(page, "review")
        page.wait_for_selector(".review-hero h2", timeout=15000)
        reread_proposal = page.eval_on_selector(".review-hero", "el => el.textContent.trim()")
        print(f" 11. after reload: the saved wording is served back, and Review still shows "
              f"{reread_proposal.splitlines()[0][:80]!r}")
        assert "demo.v1-candidate" in reread_proposal, (
            f"after a reload the proposal is gone from Review: {reread_proposal!r}"
        )
        _shot(page, tag, "09-after-reload")

        assert not errors, f"the page logged errors during the journey: {errors}"
    finally:
        ctx.close()

    # -- 12. A different signed-in user sees the decision controls disabled
    #        and explained BEFORE any attempt (converge-8crs), and a direct
    #        request to the same route -- bypassing the disabled control, as
    #        a forged request would -- still refuses server-side and writes
    #        nothing --------------------------------------------------------
    #
    # Signed in proves who is asking, never that their word counts here
    # (`app/serve.py`'s `_steward_denied`).  render/direction.js now renders
    # every `[data-decision]` control `disabled` for a non-steward, with an
    # inline note naming the registered steward -- so 12a checks that first,
    # the way a teammate would actually experience it (Playwright's own
    # `_click` refuses to force a click through a disabled control, on
    # purpose: see its docstring). Client guidance is not security and must
    # not be the only thing tested, so 12b bypasses the disabled control
    # exactly the way a forged request would -- a direct call to the app's
    # own `api.decision`, from this same signed-in browser -- and checks the
    # refusal and the record on disk, same as before: a guard that only
    # refuses in a unit test is a guard a steward can still walk around.
    records_before = sorted(p.name for p in (repo / "docs" / "workflow").glob("owner-ratifications-*.md"))
    sizes_before = {p.name: p.stat().st_size for p in (repo / "docs" / "workflow").glob("owner-ratifications-*.md")}
    other_ctx, other_page, other_errors = _boot(
        browser, server, project, width=width, height=height, user=OTHER_USER
    )
    try:
        _click(other_page, f'[data-home-manager="{manager_id}"]', what=f"the {manager_id} card")
        other_page.wait_for_selector("#operationView:not(.hidden)", timeout=15000)
        _stow_console(other_page, width)
        _click(other_page, "#directionTab", what="the Direction tab")
        other_page.wait_for_selector("#directionView:not(.hidden)", timeout=15000)
        _stow_console(other_page, width)
        _open_doc(other_page, "Demo")
        _mode(other_page, "review")
        other_page.wait_for_selector("[data-decision]", timeout=15000)

        # 12a. Disabled and explained, before any attempt.
        disabled = other_page.eval_on_selector_all("[data-decision]", "els => els.map(e => e.disabled)")
        gate_note = other_page.eval_on_selector(".steward-gate-note", "el => el.textContent.trim()")
        print(f" 12a. {OTHER_USER} sees decisions disabled={disabled}; explanation: {gate_note!r}")
        assert disabled and all(disabled), (
            f"a user who is not the registered steward saw a live decision control: {disabled}"
        )
        assert USER in gate_note, (
            f"the disabled explanation does not name the registered steward ({USER}): {gate_note!r}"
        )
        _shot(other_page, tag, "10-wrong-user-disabled")

        # 12b. A direct request to the same route still refuses server-side.
        direct = other_page.evaluate(
            """async (decision) => {
                try {
                    // converge-moe4: main.js is now served from a per-generation
                    // VERSIONED URL (app/assets.py), so importing an absolute,
                    // unversioned '/static/js/state.js' here would load a SECOND,
                    // empty module instance rather than the one the running page
                    // already populated -- resolved relative to the script the
                    // page itself loaded, exactly like main.js's own import does,
                    // so this always shares the SAME singleton.
                    const mainSrc = document.querySelector('script[type="module"][src*="/js/main.js"]').src;
                    const { state, data } = await import(new URL('./state.js', mainSrc).href);
                    const { api } = await import(new URL('./api.js', mainSrc).href);
                    const proposalId = (data.doc && (data.doc.proposals || [])[0] && data.doc.proposals[0].id) || null;
                    if (!proposalId) return { error: 'no open proposal id available client-side' };
                    await api.decision(state.managerId, {
                        repoId: state.repoId, docId: state.docId, proposalId, decision, note: '',
                    });
                    return { ok: true };
                } catch (err) {
                    return { status: err.status, said: err.message };
                }
            }""",
            "declined",
        )
        print(f" 12b. {OTHER_USER} direct decision request -> {direct}")
        assert direct.get("status") == 403, (
            f"a direct decision request from a user who is not the registered steward was not refused: {direct}"
        )
        sizes_after = {p.name: p.stat().st_size for p in (repo / "docs" / "workflow").glob("owner-ratifications-*.md")}
        assert sorted(sizes_after) == records_before, (
            f"the refused decision created a record: {sorted(sizes_after)} vs {records_before}"
        )
        assert sizes_after == sizes_before, (
            f"the refused decision appended to a record: {sizes_after} vs {sizes_before}"
        )
        # Chromium logs every failed network response to the console itself, so
        # a refusal that WORKS necessarily leaves one `403 (Forbidden)` line
        # here. Asserting "no errors at all" would therefore mean asserting the
        # guard did not fire. What must not appear is anything else -- a
        # `pageerror`, or a second failed request the refusal dragged down with
        # it -- so that is what is checked.
        unexpected = [
            line for line in other_errors
            if not (line.startswith("console.error: Failed to load resource") and "403" in line)
        ]
        print(f"     console lines on the refusal: {other_errors}")
        assert len(other_errors) == 1, (
            f"the refusal cost more than the one 403 the browser always logs: {other_errors}"
        )
        assert not unexpected, f"the second user's page logged real errors: {unexpected}"
        _shot(other_page, tag, "11-wrong-user-refused")
    finally:
        other_ctx.close()

    print(f"  ✓ {width}x{height}: twelve steps, four writes, two refusals held.")
