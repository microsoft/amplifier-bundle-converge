"""Rendered-browser tests for the two Direction promises converge-wrx makes real.

`experience-direction.v1` §6 asks that restoring from history be a *real
action* at four scopes — a wording, a paragraph, a section, the whole document
— and that on a locked document the same gesture produce a proposal to answer.
§8 asks that accepting and reverting individual changes *construct* the one
answer `ratified with edits`, rather than being shown and discarded.

Before this lane both were a message. `conformance/experience-direction`
caught that much and no more: it is a deliberately static read, so it can see
that a control exists and that its handler *reaches* a write, and it says so
plainly, but it cannot see a sentence go back into a file, cannot see a kept
mark survive a reload, and cannot see the steward's choices land in the
ratification record. That is the half these tests buy — a real Chromium, the
real app, a real git repository, and the file on disk asserted afterwards.

What is NOT covered here, honestly:

- **Restoring to an arbitrary earlier snapshot.** The only sentences the server
  can still find are the ones in the current reading, so the snapshot a restore
  reaches is the steward's own read point and no other. The screen says this
  rather than implying time travel; the route that would close it is filed as
  converge-4pq, and `test_the_panel_says_what_it_cannot_reach` pins the honesty
  so that when the route lands this test fails and must be rewritten.
- **Whether the ratification record is later read back by anything.** These
  tests assert the file the decision write appends to, which is what §8's
  "written to the dated ratification record" names.

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

Check — restore is offered from History at all four scopes
  a. Click History. SEE, under the snapshot, a panel headed by a line naming
     the commit restoring puts wording back to.
  b. SEE four kinds of button: Restore the whole document, Restore section
     "…", Restore paragraph "…", Restore wording "…".
  FAILS IF: any scope is missing, or a button appears with nothing behind it.

Check — a section restore reaches the file
  c. Click Restore section "…". SEE a dialog naming how many sentences go
     back, to which commit, and that each is committed in your name.
  d. Click the primary button. SEE a message saying how many went back.
  e. In a terminal: `git -C <repo> log --format=%s -n 3` SEE one commit per
     sentence, each naming the section and "restored". `grep` the document
     SEE the earlier wording back in the file.
  FAILS IF: the message appears but the file still says the newer wording.

Check — a locked document is never written to
  f. Open a document whose H1 carries (FROZEN …). Click History.
  g. SEE the panel say the document is FROZEN and that each restore writes a
     proposal beside it.
  h. Click Restore the whole document, then the primary button. SEE a message
     naming a candidate file.
  i. In a terminal SEE `<doc-stem>.vN-candidate.md` exists, and `git status`
     reports the document itself unmodified.
  FAILS IF: the locked document changed at all.

Check — a kept mark survives leaving and coming back
  j. In Changes, click "Keep this change" on one card. SEE it read "✓ Kept".
  k. Reload the page and open the same document and view. SEE it STILL read
     "✓ Kept", and the banner still count it.
  FAILS IF: the mark resets — it is then this browser's, not yours.

Check — the granular choices build the one answer
  l. With a proposal open on the document, in Changes SEE a button reading
     "Answer with these choices".
  m. Click it. SEE the dialog list, by section, which changes are Kept and
     which are Not kept.
  n. Write a wording change and click "Ratify with edits". SEE a message
     naming the record it was written to.
  o. Open `docs/workflow/owner-ratifications-<today>.md`. SEE ONE entry, its
     decision reading "Ratified with edits", carrying your words AND the kept
     and not-kept lists.
  FAILS IF: the record carries only your free text, or more than one entry was
     written for the one answer.

Check — it holds at both widths
  p. Repeat (a)-(b) at 1280x800 and at 390x844. At each, in the devtools
     console run:
       document.documentElement.scrollWidth + ' vs ' + document.documentElement.clientWidth
     SEE the two numbers equal, with the History panel open.
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
# a project to serve: three sections that moved, one draft, one locked
# --------------------------------------------------------------------------
#
# Three sections on purpose. A scope restore is only worth testing if the
# scopes can actually disagree: "Core › 1" is a paragraph inside the section
# "Core", so restoring the section must reach the numbered item and restoring
# one paragraph must leave its neighbours alone.

VISION_FIRST = """# Demo Vision (DRAFT)

## Where this is going

One place for direction and one place for operation.
The console is a tab you visit when something breaks.

## Core

1. A decision is recorded where the manager session already reads.
2. Nothing is ever overwritten.

## How we work

Work is derived from the gap, never invented.
A lane returns with proof or it returns blocked.
"""

VISION_SECOND = """# Demo Vision (DRAFT)

## Where this is going

One place for direction and one place for operation.
The console is a place you work, not a tab you visit.

## Core

1. A decision is recorded where the manager session already reads, and nowhere else.
2. Nothing is ever overwritten.

## How we work

Work is derived from the gap, never invented.
A lane returns with proof, or it returns blocked and says why.
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

#: An open proposal beside the draft, so §8's one answer has something to
#: answer. `data.candidate_files` finds it by the sibling-stem convention.
VISION_CANDIDATE = """# Demo Vision v2 — candidate

author: A teammate

## The exact change

The console sentence becomes a claim about where work happens.

## The evidence

- A steward opened the console eleven times in one run.

## What does not change

Everything in Core stays as it is.
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


@pytest.fixture
def project(tmp_path_factory) -> dict:
    """A real repository with real history — never fixtures of the answers.

    Function-scoped: every test here WRITES to the document it opens, so a
    shared repository would make each test's evidence depend on the order the
    tests happened to run in.
    """
    tmp_path = tmp_path_factory.mktemp("direction-persist")
    repo = tmp_path / "demo-repo"
    (repo / "docs").mkdir(parents=True)
    (repo / "contracts").mkdir(parents=True)
    (repo / "docs" / "VISION.md").write_text(VISION_FIRST, encoding="utf-8")
    (repo / "contracts" / "demo.v1.md").write_text(LOCKED_FIRST, encoding="utf-8")
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "seed: the vision and one contract")

    # A second commit, so each document has sentences that moved and therefore
    # sentences the restore write can still find.
    (repo / "docs" / "VISION.md").write_text(VISION_SECOND, encoding="utf-8")
    (repo / "contracts" / "demo.v1.md").write_text(LOCKED_SECOND, encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "the console becomes a place; writes name their author")

    # The proposal is left untracked on purpose: a candidate arrives beside a
    # document before anyone has decided to keep it.
    (repo / "docs" / "VISION.v2-candidate.md").write_text(VISION_CANDIDATE, encoding="utf-8")

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
    # Never the real ~/.amplifier: a test must not move a steward's read point
    # or answer a change on their behalf.
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


@pytest.fixture
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
    print(f"\napp server: http://127.0.0.1:{port} (in-process, torn down with this test)")
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
        # reading on a phone does.
        page.click("#consoleToggle")
        page.wait_for_timeout(500)
    return ctx, page, errors


def _open_doc(page, title: str) -> None:
    """Click the named document in the tree and wait for Read to draw it."""
    page.click(f'.repo-doc:has-text("{title}")')
    page.wait_for_selector("#documentModeContent .since-banner, #documentModeContent section", timeout=10000)
    page.wait_for_timeout(400)


def _mode(page, name: str) -> None:
    page.click(f'[data-doc-mode="{name}"]')
    page.wait_for_timeout(400)


def _toast(page) -> str:
    return page.eval_on_selector("#toast", "el => el.textContent || ''")


def _confirm_dialog(page) -> str:
    """Take the dialog's primary action, returning what it said first."""
    page.wait_for_selector("#dialogActions button.primary-button", timeout=5000)
    said = page.eval_on_selector("#dialogContent", "el => el.innerText || ''")
    page.click("#dialogActions button.primary-button")
    return said


def _subjects(repo: Path, n: int = 6) -> list[str]:
    return [s for s in _git(repo, "log", f"-n{n}", "--format=%s").splitlines() if s]


# --------------------------------------------------------------------------
# §6 — restore is offered at all four scopes, from History
# --------------------------------------------------------------------------


@needs_browser
def test_history_offers_restore_at_all_four_scopes(server, project, browser):
    ctx, page, errors = _boot(browser, server, project)
    _open_doc(page, "Vision")
    _mode(page, "history")

    scopes = page.eval_on_selector_all(
        "[data-restore]", "els => els.map(e => e.dataset.restore)")
    labels = page.eval_on_selector_all(
        "[data-restore]", "els => els.map(e => e.innerText.trim())")
    print("\nrestore controls offered in History:")
    for one in labels:
        print(f"  · {one}")
    print(f"scopes present: {sorted(set(scopes))}")
    print(f"console errors: {errors or 'none'}")

    for wanted in ("wording", "paragraph", "section", "document"):
        assert wanted in scopes, (
            f"§6 names four scopes and History offers no `{wanted}` one; it offers {sorted(set(scopes))}"
        )
    assert not errors, f"the page reported errors: {errors}"
    ctx.close()


@needs_browser
def test_the_panel_says_what_it_cannot_reach(server, project, browser):
    """The honesty this lane owes: restore reaches the read point and no other
    snapshot, and the screen says so instead of implying time travel.

    When converge-4pq lands and an arbitrary snapshot IS restorable, this test
    fails and must be rewritten. A test that tolerated both would be worth
    nothing.
    """
    ctx, page, errors = _boot(browser, server, project)
    _open_doc(page, "Vision")
    _mode(page, "history")
    # The limit is one gesture away rather than shouted: open it the way a
    # steward would, then read what they would read.
    page.click(".history-actions details summary")
    page.wait_for_timeout(200)
    said = page.eval_on_selector(".history-snapshot .history-actions", "el => el.innerText || ''")
    print(f"\nthe panel says:\n{said.strip()[:600]}")
    assert "converge-4pq" in said, "the panel does not name the work that would close the gap"
    assert "not offered" in said.lower() or "cannot" in said.lower(), (
        "the panel does not say plainly that an older snapshot is out of reach"
    )
    ctx.close()


# --------------------------------------------------------------------------
# §6 — a section restore reaches the file, and leaves its neighbours alone
# --------------------------------------------------------------------------


@needs_browser
def test_a_section_restore_puts_that_section_back_and_commits_it(server, project, browser):
    ctx, page, errors = _boot(browser, server, project)
    _open_doc(page, "Vision")
    _mode(page, "history")

    before = project["vision"].read_text(encoding="utf-8")
    assert "and nowhere else" in before, "the fixture's Core sentence was not where this test expected it"

    page.click('[data-restore="section"][data-restore-key="Core"]')
    said = _confirm_dialog(page)
    print(f"\nthe dialog said:\n{said.strip()[:300]}")
    page.wait_for_timeout(1500)

    after = project["vision"].read_text(encoding="utf-8")
    subjects = _subjects(project["repo"])
    said_after = _toast(page)
    print(f"the app said: {said_after}")
    print(f"commits now:  {subjects[:3]}")
    print(f"Core is back to the earlier wording: {'and nowhere else' not in after}")
    print(f"the other sections are untouched:    {'The console is a place you work' in after}")
    print(f"console errors: {errors or 'none'}")

    assert after != before, "the restore reported back but the document on disk did not change"
    assert "and nowhere else" not in after, (
        "the section restore did not put Core's earlier wording back into the file"
    )
    assert "A decision is recorded where the manager session already reads." in after
    # Scope means scope: a section restore must not reach into its neighbours.
    assert "The console is a place you work, not a tab you visit." in after, (
        "restoring the section Core also reverted a sentence in another section"
    )
    assert "returns blocked and says why" in after, (
        "restoring the section Core also reverted a sentence in another section"
    )
    assert any("restored" in s for s in subjects), (
        f"no commit names the restore; the log says {subjects[:3]}"
    )
    # A draft is committed, not proposed. Saying otherwise would be the same
    # class of lie this lane exists to remove.
    assert "committed in your name" in said_after, (
        f"the app did not say the restore was committed; it said: {said_after!r}"
    )
    assert "not touched" not in said_after, (
        f"the app claimed a draft was left untouched while committing to it: {said_after!r}"
    )
    assert any("Converge" in s for s in _git(project["repo"], "log", "-n3", "--format=%an").splitlines()), (
        "the restore was not committed in the steward's name"
    )
    assert not errors, f"the page reported errors: {errors}"
    ctx.close()


# --------------------------------------------------------------------------
# §6 — a locked document produces a proposal and is never written to
# --------------------------------------------------------------------------


@needs_browser
def test_restoring_a_locked_document_writes_a_proposal_and_touches_no_file(server, project, browser):
    ctx, page, errors = _boot(browser, server, project)
    _open_doc(page, "Demo")
    _mode(page, "history")

    untouched = project["locked"].read_text(encoding="utf-8")
    panel = page.eval_on_selector(".history-snapshot .history-actions", "el => el.innerText || ''")
    print(f"\nthe panel on a LOCKED document says:\n{panel.strip()[:320]}")
    assert "FROZEN" in panel, "the panel does not say the document is locked"

    page.click('[data-restore="document"]')
    said = _confirm_dialog(page)
    print(f"the dialog said:\n{said.strip()[:300]}")
    page.wait_for_timeout(1500)

    candidate = project["repo"] / "contracts" / "demo.v1-candidate.md"
    now = project["locked"].read_text(encoding="utf-8")
    said_after = _toast(page)
    print(f"the app said: {said_after}")
    print(f"proposal written: {candidate.is_file()} ({candidate.name})")
    print(f"the locked document is byte-identical: {now == untouched}")
    print(f"console errors: {errors or 'none'}")

    assert now == untouched, (
        "the locked document was written to — the guard is the law and it was not obeyed"
    )
    assert candidate.is_file(), "no proposal was written beside the locked document"
    body = candidate.read_text(encoding="utf-8")
    assert "every write says who made it" in body, (
        "the proposal does not carry the wording the restore was undoing"
    )
    assert "FROZEN" in body, "the proposal does not name the lock it routed around"
    assert candidate.name in said_after and "not touched" in said_after, (
        f"the app did not say where the wording went, or claimed a write it did not make: {said_after!r}"
    )
    assert len(_subjects(project["repo"])) == 2, (
        "a locked document produced a commit; §6 asks for a proposal instead"
    )
    assert not errors, f"the page reported errors: {errors}"
    ctx.close()


# --------------------------------------------------------------------------
# §8 — a kept mark is the steward's, not this browser's
# --------------------------------------------------------------------------


@needs_browser
def test_a_kept_mark_survives_a_reload_and_a_second_browser(server, project, browser):
    ctx, page, errors = _boot(browser, server, project)
    _open_doc(page, "Vision")
    _mode(page, "changes")

    page.click('.change-card [data-change-action="keep"]')
    page.wait_for_timeout(900)
    marked = page.eval_on_selector_all(".change-card.kept", "els => els.length")
    counted = page.eval_on_selector(".kept-count", "el => el.innerText.trim()")
    print(f"\nafter keeping one change: cards marked kept={marked}, banner says {counted!r}")
    assert marked == 1, "keeping a change did not mark it on the screen"

    page.reload(wait_until="networkidle")
    page.wait_for_selector("#documentModeContent", timeout=15000)
    _open_doc(page, "Vision")
    _mode(page, "changes")
    after_reload = page.eval_on_selector_all(".change-card.kept", "els => els.length")
    print(f"after a reload:            cards marked kept={after_reload}")
    assert after_reload == 1, "the kept mark did not survive a reload — it was this browser's, not the steward's"

    # A different browser context is a different browser as far as storage
    # goes. The mark is the steward's, so it has to be there too.
    other_ctx, other_page, other_errors = _boot(browser, server, project)
    _open_doc(other_page, "Vision")
    _mode(other_page, "changes")
    elsewhere = other_page.eval_on_selector_all(".change-card.kept", "els => els.length")
    print(f"in a second browser:       cards marked kept={elsewhere}")
    print(f"console errors: {errors + other_errors or 'none'}")
    assert elsewhere == 1, "the kept mark was not there in a second browser"
    assert not (errors + other_errors), f"the page reported errors: {errors + other_errors}"
    other_ctx.close()
    ctx.close()


# --------------------------------------------------------------------------
# §8 — the granular choices are carried into the one answer
# --------------------------------------------------------------------------


@needs_browser
def test_the_granular_choices_are_carried_into_the_one_answer(server, project, browser):
    ctx, page, errors = _boot(browser, server, project)
    _open_doc(page, "Vision")
    _mode(page, "changes")

    cards = page.eval_on_selector_all(".change-card", "els => els.length")
    print(f"\nchanges in this reading: {cards}")
    assert cards >= 2, "this test needs a change to keep and a change to leave"

    page.click('.change-card [data-change-action="keep"]')
    page.wait_for_timeout(900)

    offered = page.query_selector('[data-decision="ratified-with-edits"]')
    assert offered, (
        "§8 asks that the granular choices build the one answer, and the Changes view "
        "offers no way to answer with them"
    )
    print(f"the answer is offered where the choices are made: {offered.inner_text().strip()!r}")
    offered.click()

    shown = page.eval_on_selector("#dialogContent", "el => el.innerText || ''")
    print(f"the dialog shows:\n{shown.strip()[:400]}")
    assert "Kept" in shown and "Not kept" in shown, (
        "the answer dialog does not show the steward which changes are kept and which are not"
    )

    page.fill("#ratifyEdit", "Say 'a place you work' rather than 'not a tab'.")
    page.click("#dialogActions button.primary-button")
    page.wait_for_timeout(1200)

    records = sorted((project["repo"] / "docs" / "workflow").glob("owner-ratifications-*.md"))
    print(f"the app said: {_toast(page)}")
    print(f"records written: {[p.name for p in records]}")
    assert records, "the answer was reported but no ratification record was written"
    body = records[0].read_text(encoding="utf-8")
    print("--- the record ---")
    print(body.strip()[-700:])
    print("--- end ---")

    assert body.count("## ") == 1, (
        f"§8 asks for ONE answer; the record carries {body.count('## ')} entries"
    )
    assert "Ratified with edits" in body, "the record does not carry the one word in the vocabulary"
    assert "Say 'a place you work'" in body, "the record does not carry the steward's own words"
    assert "Granular choices carried into this answer" in body, (
        "the record does not carry the granular choices at all — they were shown and discarded"
    )
    assert "Kept:" in body and "Not kept:" in body, (
        "the record does not say which changes were kept and which were not"
    )
    assert "1 of " in body, "the record does not say how many of the changes were kept"
    assert not errors, f"the page reported errors: {errors}"
    ctx.close()


# --------------------------------------------------------------------------
# both widths — the panel is usable on a phone, and pushes nothing sideways
# --------------------------------------------------------------------------


@needs_browser
@pytest.mark.parametrize("width,height", [(1280, 800), (390, 844)])
def test_the_restore_panel_holds_at_both_widths(server, project, browser, width, height):
    ctx, page, errors = _boot(browser, server, project, width=width, height=height)
    _open_doc(page, "Vision")
    _mode(page, "history")
    page.wait_for_selector("[data-restore]", timeout=10000)

    measured = page.evaluate(MEASURE)
    controls = page.eval_on_selector_all("[data-restore]", "els => els.length")
    print(f"\n[{width}] restore controls drawn: {controls}")
    print(f"[{width}] scrollWidth={measured['scrollWidth']} clientWidth={measured['clientWidth']}")
    if measured["past"]:
        print(f"[{width}] past the right edge: {measured['past']}")
    print(f"[{width}] console errors: {errors or 'none'}")

    assert controls >= 4, f"the restore panel drew {controls} controls at {width}px"
    assert measured["scrollWidth"] <= measured["clientWidth"] + 1, (
        f"the History view scrolls sideways at {width}px: {measured}"
    )
    assert not measured["past"], f"elements sit past the right edge at {width}px: {measured['past']}"
    assert not errors, f"the page reported errors at {width}px: {errors}"
    ctx.close()
