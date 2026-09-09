"""converge-43uv — rendered-browser checks for the Reader lane's acceptance.

These four are the runtime half of the static checks in
``test_preview_reader_static.py``: whether the Tools menu actually opens and
is keyboard-operable, whether the two badges actually read differently
against a real locked-but-unmeasured document, and whether "no documents" and
"a fetch that failed" are actually two different sentences on screen rather
than the same perpetual "Loading…".

If Playwright or its Chromium build is unavailable the browser tests skip
with the reason printed, matching every other rendered test in this app
(`test_direction_final.py`'s own `_playwright_reason`/`needs_browser`).
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
    reason=f"{PLAYWRIGHT_SKIP}; run the app by hand and repeat the steps this file drives",
)


# --------------------------------------------------------------------------
# two projects: one with a locked-but-unmeasured contract, one with no docs
# --------------------------------------------------------------------------

FROZEN_UNMEASURED = """# Frozen Nobody Checks — v1 (FROZEN 2026-09-04)

## Core

1. **Nothing watches this promise.** No ledger row names this file.
"""

MANIFEST_HEAD = "lane\tworktree\tbranch\tbase\ttmux\tgoal\tlog\tstarted\n"


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "user.name=Test", "-c", "user.email=test@example.invalid", *args],
        cwd=repo,
        check=True,
        capture_output=True,
    )


def _free_port() -> int:
    s = socketlib.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


@pytest.fixture(scope="module")
def project(tmp_path_factory) -> dict:
    """One repo with a locked contract nothing measures, plus a second,
    genuinely empty repo — no docs directory, no contracts directory — for
    the honest "no documents" state."""
    tmp_path = tmp_path_factory.mktemp("preview-reader")
    repo = tmp_path / "demo-repo"
    (repo / "contracts").mkdir(parents=True)
    (repo / "contracts" / "frozen.v1.md").write_text(FROZEN_UNMEASURED, encoding="utf-8")
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "seed: a frozen, unmeasured contract")

    empty_repo = tmp_path / "empty-repo"
    empty_repo.mkdir(parents=True)
    _git(empty_repo, "init", "-q", "-b", "main")
    (empty_repo / "README.md").write_text("Nothing this app reads lives here.\n", encoding="utf-8")
    _git(empty_repo, "add", "-A")
    _git(empty_repo, "commit", "-q", "-m", "seed: a repo with no vision or contracts")

    batch = tmp_path / "hw-demo"
    (batch / "goals").mkdir(parents=True)
    (batch / "HIGHWAY.md").write_text(
        "# Highway\n\n## Outcome\nEvery steward reads the reader lane's own fixture.\n", encoding="utf-8"
    )
    (batch / "manifest.tsv").write_text(MANIFEST_HEAD, encoding="utf-8")

    conf = tmp_path / "converge-app.toml"
    conf.write_text(
        "[[managers]]\n"
        'id = "demo"\n'
        'name = "Demo manager"\n'
        f'batch_dir = "{batch}"\n'
        f'repos = ["{repo}", "{empty_repo}"]\n'
        'tracker_project = ""\n'
        'tmux_socket = "test-socket-that-does-not-exist"\n'
        f'steward = "{USER}"\n',
        encoding="utf-8",
    )
    return {
        "config": conf,
        "secret": tmp_path / "secret",
        "state": tmp_path / "state.json", "sessions": tmp_path / "sessions.json",
        "repo": repo,
        "empty_repo": empty_repo,
    }


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


def _boot(browser, server, project, errors: list[str], block_docs: bool = False):
    sessions = auth.Sessions(auth.read_or_make_secret(project["secret"]))
    # `page.route()` intercepts requests the PAGE makes; it does NOT reach a
    # request a Service Worker itself issues (this app's `sw.js` owns
    # `/api/...` fetches once it controls the page -- the same fact
    # `test_preview_pwa.py`'s docstring records). So the moment a worker takes
    # control, the abort below silently stops injecting any fault at all and a
    # CACHED success can be mistaken for proof of a failure. Chromium's own
    # `service_workers="block"` removes the ambiguity at the source: no worker
    # is ever registered, every `/api/...` fetch is the page's own, and the
    # route abort is the only thing that can decide it. That online, worker-free
    # shape is a supported one (converge-04b7) -- proven separately in
    # `test_worker_unavailable_online.py`, and asserted below rather than
    # assumed.
    ctx = browser.new_context(
        viewport={"width": 1280, "height": 800},
        service_workers="block" if block_docs else "allow",
    )
    ctx.add_cookies(
        [{"name": auth.COOKIE, "value": sessions.issue(USER), "domain": "127.0.0.1", "path": "/"}]
    )
    page = ctx.new_page()
    page.on("console", lambda m: errors.append(f"console.{m.type}: {m.text}") if m.type == "error" else None)
    page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
    if block_docs:
        # Registered before goto so the app's OWN boot path (main.js's
        # pickDoc()/loadDoc() auto-opens the first repo's first document on
        # every load) is what fails, not a later click. A later click on the
        # already-open document is a deliberate no-op (render/direction.js's
        # nav-click guard skips a refetch of the doc already on screen), so
        # aborting only after boot never actually exercises the fetch-error
        # path at all.
        page.route("**/api/managers/**/docs/**", lambda route: route.abort())
    page.goto(server, wait_until="networkidle")
    # Boot always lands on Home first, never an auto-picked manager
    # (experience.v1 Core 1, converge-t30q) -- open the one manager session
    # this project registers, then its Direction tab.
    page.wait_for_selector(".home-manager-card", timeout=20000)
    page.click(".home-manager-card")
    page.wait_for_selector("#directionTab", timeout=20000)
    page.click("#directionTab")
    page.wait_for_selector("#directionView:not(.hidden)", timeout=15000)
    if not block_docs:
        page.wait_for_selector("#directionView .lock-gate", state="attached", timeout=15000)
    return ctx, page


def _select_repo(page, repo_name: str) -> None:
    page.select_option("#repoFilter", label=repo_name)
    page.wait_for_timeout(200)


# --------------------------------------------------------------------------
# acceptance 1 — the Tools menu opens, reveals its controls, and is reachable
# by keyboard alone (no mouse), per the disclosure's native contract
# --------------------------------------------------------------------------


@needs_browser
def test_tools_menu_opens_on_click_and_on_keyboard_and_reveals_its_controls(server, project, browser):
    errors: list[str] = []
    ctx, page = _boot(browser, server, project, errors)

    closed = page.evaluate("() => document.getElementById('toolsMenu').open")
    assert closed is False, "the Tools menu is open by default; it should start collapsed"
    hidden = page.evaluate(
        "() => document.getElementById('copyRendered').getBoundingClientRect().height"
    )
    assert hidden == 0, "the Tools menu's controls have a box while it is still closed"

    page.click("#toolsMenu summary")
    page.wait_for_timeout(150)
    opened = page.evaluate("() => document.getElementById('toolsMenu').open")
    revealed = page.evaluate(
        "() => document.getElementById('copyRendered').getBoundingClientRect().height"
    )
    print(f"\n[tools] open={opened} copyRendered height={revealed}")
    assert opened is True, "clicking the summary did not open the Tools menu"
    assert revealed > 0, "the Tools menu opened but its controls have no box"

    # Keyboard alone: focus the summary and press Enter, with no click at all.
    page.click("#toolsMenu summary")  # close it again
    page.wait_for_timeout(150)
    page.focus("#toolsMenu summary")
    page.keyboard.press("Enter")
    page.wait_for_timeout(150)
    via_keyboard = page.evaluate("() => document.getElementById('toolsMenu').open")
    assert via_keyboard is True, "the Tools menu did not open from the keyboard alone"
    assert not errors, f"the page logged errors: {errors}"
    ctx.close()


# --------------------------------------------------------------------------
# acceptance 3 — agreement and conformance read distinctly
# --------------------------------------------------------------------------


@needs_browser
def test_a_locked_unmeasured_document_reads_locked_and_not_checked_never_draft_or_kept(
    server, project, browser
):
    """The exact bug this lane was filed against: a FROZEN document with no
    ledger row watching it used to show one badge reading "DRAFT" — true of
    neither dimension. It must now read "FROZEN" (agreement) beside
    "Not checked" (conformance), and never "Kept"."""
    errors: list[str] = []
    ctx, page = _boot(browser, server, project, errors)
    # The nav list shows each document's *short*, filename-derived title
    # (data.py's doc_title(): "frozen.v1.md" -> "Frozen"), not its full H1
    # ("Frozen Nobody Checks") -- the full title only appears once the
    # document itself is open (docTitle below). Confirmed against the live
    # DOM, and matches every sibling test file's own _open_doc(page, "Frozen")
    # / _open_doc(page, "Vision") convention (test_direction_final.py etc.).
    page.click('.repo-doc:has-text("Frozen")')
    page.wait_for_function(
        "() => (document.getElementById('docTitle').textContent || '').trim().length > 0",
        timeout=10000,
    )
    badges = page.evaluate(
        """() => ({
          agreement: document.getElementById('docStateBadge').textContent.trim(),
          agreementClass: document.getElementById('docStateBadge').className,
          conformance: document.getElementById('docConformanceBadge').textContent.trim(),
          conformanceClass: document.getElementById('docConformanceBadge').className,
        })"""
    )
    print(f"\n[badges] agreement={badges['agreement']!r} ({badges['agreementClass']}) "
          f"conformance={badges['conformance']!r} ({badges['conformanceClass']})")
    assert "FROZEN" in badges["agreement"], f"the agreement badge does not name the lock: {badges}"
    assert "locked" in badges["agreementClass"]
    assert badges["conformance"] == "Not checked", (
        f"an unmeasured promise was labelled {badges['conformance']!r}, not 'Not checked'"
    )
    assert "unchecked" in badges["conformanceClass"]
    assert "Draft" not in badges["agreement"], "a locked document still reads Draft"
    assert "Kept" not in badges["conformance"], "an unmeasured promise reads Kept"
    assert not errors, f"the page logged errors: {errors}"
    ctx.close()


# --------------------------------------------------------------------------
# acceptance 4 — distinct honest states, never a perpetual "Loading…"
# --------------------------------------------------------------------------


@needs_browser
def test_an_empty_repository_says_so_rather_than_loading_forever(server, project, browser):
    errors: list[str] = []
    ctx, page = _boot(browser, server, project, errors)
    _select_repo(page, "EMPTY-REPO")
    page.wait_for_timeout(300)
    text = page.eval_on_selector("#documentModeContent", "el => el.textContent || ''")
    print(f"\n[empty repo] documentModeContent says: {text!r}")
    assert "Loading" not in text, "an empty repository still reads Loading, forever"
    assert "no vision or contracts" in text or "No repositories" in text, (
        f"the empty repository does not say why there is nothing to read: {text!r}"
    )
    assert not errors, f"the page logged errors: {errors}"
    ctx.close()


@needs_browser
def test_a_failed_fetch_is_distinct_from_an_empty_repository_and_offers_retry(server, project, browser):
    errors: list[str] = []
    ctx, page = _boot(browser, server, project, errors, block_docs=True)
    page.wait_for_selector("[data-doc-retry]", timeout=15000)
    # The fault injection is only real while nothing else can answer the fetch.
    # Asserted, not assumed: a worker here would own `/api/...` and could serve
    # a cached success that this test would otherwise read as a failure.
    owns_fetch = page.evaluate(
        "async () => ({ controller: !!navigator.serviceWorker.controller,"
        " registrations: (await navigator.serviceWorker.getRegistrations()).length })"
    )
    assert owns_fetch == {"controller": False, "registrations": 0}, (
        f"a service worker owns this page's fetches, so page.route injected no fault: {owns_fetch}"
    )
    text = page.eval_on_selector("#documentModeContent", "el => el.textContent || ''")
    has_retry = page.evaluate("() => !!document.querySelector('[data-doc-retry]')")
    print(f"\n[fetch error] fault injection is authoritative: {owns_fetch}")
    print(f"[fetch error] documentModeContent says: {text!r}  retry control present={has_retry}")
    assert "Loading" not in text, "a failed fetch still reads Loading, forever"
    assert "could not be read" in text, f"a failed fetch does not say it failed: {text!r}"
    assert has_retry, "a failed fetch offers no next action"
    page.unroute("**/api/managers/**/docs/**")
    with page.expect_response(
        lambda response: "/docs/" in response.url and response.request.method == "GET",
        timeout=15000,
    ) as recovered:
        page.click("[data-doc-retry]")
    assert recovered.value.status == 200, "Retry did not reach the restored document service"
    page.wait_for_selector("#directionView .lock-gate", timeout=15000)
    assert page.query_selector("[data-doc-retry]") is None, "Retry left the failure on screen"
    print("[fetch error] Retry fetched the real document and restored its reading.")
    ctx.close()
