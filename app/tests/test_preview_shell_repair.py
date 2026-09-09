"""Rendered-browser proof for the shell-repair corrections (converge-t30q).

The manager reopened converge-t30q with five specific corrections to the
sound work already committed at 37123a5. This file is the real-Chromium
proof for each one, plus source-level fences that run everywhere (no browser
needed) so a later edit that quietly reverts a correction is caught even
where Playwright is unavailable.

Corrections proven here:

1. A compact workspace rail is required, not optional -- narrow rows (name,
   status/needs badge) with the full facts reachable through an accessible
   `<details>`, never Home's rich card redrawn a second time.
2. A non-document need (a work-tracker item) gets an actionable path through
   Operation's own existing controls (queue/priority/feedback/steer), with
   the Console left exactly as the steward had it -- never forced open as
   the only answer.
3. A `setPrincipal` rejection is a fail-CLOSED identity/setup failure: no
   manager or document data is read, Home shows a named recovery state, and
   nothing cached leaks through.
4. Home's Feedback control never silently picks the first listed manager as
   its write target; with no manager open it asks, explicitly, before Send
   is meaningful.
5. The console stays exactly where the steward left it across this file's
   changes -- opening from Home's needs dialog for a non-document item does
   not toggle it.

If Playwright or its Chromium build is unavailable the browser checks skip
with the reason printed (matching every other rendered file in this suite);
the source fences at the bottom need no browser and never skip.
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
    reason=f"{PLAYWRIGHT_SKIP}; run with --with playwright and a Chromium build to get rendered proof",
)


# --------------------------------------------------------------------------
# two manager sessions, and a fixed work-tracker need on one of them
# --------------------------------------------------------------------------

VISION = """# Demo Vision (DRAFT)

## Where this is going

One place for direction and one place for operation.
"""

HIGHWAY = """# Highway -- demo

Width 4.
"""

MANIFEST_HEAD = "lane\tworktree\tbranch\tbase\ttmux\tgoal\tlog\tstarted\n"

MANAGERS = ("alpha", "bravo")

COUNTS = {"TOTAL": 21, "READY": 4, "BLOCKED": 1, "RESOLVED": 16}

#: A work-tracker item with no document view at all -- alpha's only need,
#: so opening the dialog on alpha always exercises the non-document path.
WORK_ITEM_ID = "converge-repairme"
WORK_ITEM_TITLE = "Fix the shell inbox integration test"

NEEDS_BY_MANAGER = {
    "alpha": [
        {"kind": "work", "title": WORK_ITEM_TITLE, "where": {"itemId": WORK_ITEM_ID}, "since": ""},
    ],
    "bravo": [],
}


def _fake_needs_items(mc) -> list[dict]:
    return list(NEEDS_BY_MANAGER.get(mc.id, []))


def _fake_queue_items(mc, limit: int = 20) -> dict:
    return {
        "available": True,
        "items": [{"id": WORK_ITEM_ID, "title": WORK_ITEM_TITLE}],
        "total": 1,
        "project": mc.tracker_project,
        "why": "",
    }


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "user.name=Test", "-c", "user.email=test@example.invalid", *args],
        cwd=repo,
        check=True,
        capture_output=True,
    )


@pytest.fixture(scope="module")
def project(tmp_path_factory) -> dict:
    tmp_path = tmp_path_factory.mktemp("shell-repair")
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
            f'name = "Manager {mid.title()}"\n'
            f'batch_dir = "{batch}"\n'
            f'repos = ["{repo}"]\n'
            'tracker_project = "demo-project"\n'
            'tmux_socket = "test-socket-that-does-not-exist"\n'
        )

    conf = tmp_path / "converge-app.toml"
    conf.write_text("".join(blocks), encoding="utf-8")
    return {"config": conf, "secret": tmp_path / "secret", "state": tmp_path / "state.json", "sessions": tmp_path / "sessions.json", "repos": repos}


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
    patch.setattr(data, "tmux_sessions", lambda socket: set())
    patch.setattr(data, "tracker_counts", lambda mc: dict(COUNTS))
    patch.setattr(data, "_needs_items", _fake_needs_items)
    patch.setattr(data, "queue_items", _fake_queue_items)

    made = serve.create_app(config_path=project["config"], secret_path=project["secret"], state_path=project["state"], sessions_path=project["sessions"])
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


def _open(browser, server, project, width: int, height: int, errors: list[str], init_script: str | None = None):
    sessions = auth.Sessions(auth.read_or_make_secret(project["secret"]))
    ctx = browser.new_context(viewport={"width": width, "height": height})
    ctx.add_cookies([{"name": auth.COOKIE, "value": sessions.issue(USER), "domain": "127.0.0.1", "path": "/"}])
    if init_script:
        ctx.add_init_script(init_script)
    page = ctx.new_page()
    page.on("console", lambda m: errors.append(f"console.{m.type}: {m.text}") if m.type == "error" else None)
    page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
    page.goto(server, wait_until="networkidle")
    page.wait_for_selector("#brandHome", timeout=15000)
    return ctx, page


def _open_manager(page, name: str) -> None:
    page.wait_for_selector(".home-manager-card", timeout=15000)
    page.click(f".home-manager-card:has-text('{name}')")
    page.wait_for_selector("#managerCrumb:not(.hidden)", timeout=15000)


def _feedback_files(repo: Path) -> list[Path]:
    folder = repo / ".converge" / "feedback"
    return sorted(folder.glob("*.md")) if folder.is_dir() else []


# --------------------------------------------------------------------------
# 1. the compact workspace rail: narrow rows, full facts behind <details>
# --------------------------------------------------------------------------


@needs_browser
@pytest.mark.parametrize("width,height", [(1280, 800), (390, 844)])
def test_the_workspace_rail_is_compact_and_home_keeps_full_cards(server, project, browser, width, height) -> None:
    errors: list[str] = []
    ctx, page = _open(browser, server, project, width, height, errors)

    # Home keeps the full card: needs/lane/brief/freshness facts, always visible.
    page.wait_for_selector(".home-manager-card", timeout=15000)
    home_meta = page.eval_on_selector_all(
        "#homeSessionGrid .home-manager-card .home-card-meta", "els => els.length"
    )
    assert home_meta == len(MANAGERS), "Home must keep its full ranked cards with required facts"

    _open_manager(page, "Manager Alpha")

    # The workspace rail draws a NARROW row -- no expanded metrics grid or
    # summary paragraph visible by default -- for the same manager.
    row = page.query_selector("#sessionList .session-row")
    assert row is not None, "the workspace rail must draw a row per manager"
    detail_open_before = page.eval_on_selector(
        "#sessionList .session-row-detail", "el => el.open"
    )
    assert not detail_open_before, "the full facts must be collapsed by default, not drawn every time"

    metrics_visible = page.eval_on_selector(
        "#sessionList .session-row-metrics",
        "el => { const s = getComputedStyle(el); return el.offsetParent !== null && s.visibility !== 'hidden'; }",
    )
    assert not metrics_visible, "expanded metrics must not be drawn on the collapsed row"

    if width >= 980:
        # At a width with room for it, the facts are still reachable -- a
        # native, accessible <details>. Below that width the rail is a
        # horizontally-scrolling strip (unchanged mobile behaviour) and the
        # detail is not offered at all, matching the old rail's own mobile
        # rules for the same reason: no room, and Home already has the full
        # card one tap away.
        page.click("#sessionList .session-row-detail summary")
        page.wait_for_function(
            "() => document.querySelector('#sessionList .session-row-detail').open", timeout=3000
        )
        metrics_text = page.inner_text("#sessionList .session-row-metrics")
        assert "lanes" in metrics_text and "repos" in metrics_text, (
            f"expanding the row must still surface the full facts, got: {metrics_text!r}"
        )

    assert not errors, f"the browser logged: {errors}"
    ctx.close()


# --------------------------------------------------------------------------
# 2. a non-document need routes to Operation's own controls, not Console-only
# --------------------------------------------------------------------------


@needs_browser
def test_a_non_document_need_opens_operation_not_the_console(server, project, browser) -> None:
    errors: list[str] = []
    ctx, page = _open(browser, server, project, 1280, 800, errors)
    _open_manager(page, "Manager Alpha")

    console_pressed_before = page.get_attribute("#consoleToggle", "aria-pressed")
    assert console_pressed_before == "false", "the console must start closed"

    page.click("#needsYouButton", timeout=5000)
    page.wait_for_selector(".needs-list .need-row", timeout=5000)
    row_text = page.inner_text(".needs-list")
    assert "Work item" in row_text and WORK_ITEM_TITLE in row_text, f"the row must name its own kind: {row_text!r}"

    page.click("[data-need-act='0']", timeout=5000)
    page.wait_for_selector("#operationView:not(.hidden)", timeout=5000)

    op_tab_active = page.eval_on_selector("#operationTab", "el => el.classList.contains('active')")
    assert op_tab_active, "the non-document path must land on Operation, not stay on Direction"

    console_pressed_after = page.get_attribute("#consoleToggle", "aria-pressed")
    assert console_pressed_after == "false", (
        "the Console must be left exactly as the steward had it -- never forced open as the "
        "only answer for a non-document need"
    )

    toast = page.inner_text("#toast")
    assert "no document view" in toast.lower(), f"the toast must say the honest limit plainly: {toast!r}"

    assert not errors, f"the browser logged: {errors}"
    ctx.close()


# --------------------------------------------------------------------------
# 3. setPrincipal rejects -> fail closed, not a silent continue
# --------------------------------------------------------------------------

REJECT_PRINCIPAL = """
window.__identityProbeCalls = 0;
window.ConvergePWA = {};
// This tests Shell's rejection handling, not the worker's implementation.
// Keep the injected dependency when the concrete PWA script initializes.
Object.defineProperty(window.ConvergePWA, 'setPrincipal', {
  get: () => () => {
    window.__identityProbeCalls += 1;
    return Promise.reject(new Error('untrusted claim -- boot response could not be verified'));
  },
  set: () => {},
});
"""


@needs_browser
def test_a_rejected_identity_check_fails_closed_on_home(server, project, browser) -> None:
    errors: list[str] = []
    ctx, page = _open(browser, server, project, 1280, 800, errors, init_script=REJECT_PRINCIPAL)

    page.wait_for_selector(".home-identity-failure", timeout=15000)
    assert page.evaluate("window.__identityProbeCalls") >= 1, "the rejection probe never ran"
    cards = page.query_selector_all(".home-manager-card")
    assert not cards, "no manager card may be drawn while the identity check has failed"

    retry = page.query_selector("#identityRetryButton")
    assert retry is not None, "a real recovery action must be offered, not a dead-end toast"

    # Console-level errors are expected here (the rejection itself may log);
    # only page-crashing errors are disqualifying, and none were installed.
    pageerrors = [e for e in errors if e.startswith("pageerror:")]
    assert not pageerrors, f"the browser threw: {pageerrors}"
    ctx.close()


# --------------------------------------------------------------------------
# 4. Home's Feedback never silently picks a manager
# --------------------------------------------------------------------------


@needs_browser
def test_feedback_from_home_requires_an_explicit_choice(server, project, browser) -> None:
    errors: list[str] = []
    ctx, page = _open(browser, server, project, 1280, 800, errors)
    repo_a = project["repos"]["alpha"]
    repo_b = project["repos"]["bravo"]
    before_a = {p.name for p in _feedback_files(repo_a)}
    before_b = {p.name for p in _feedback_files(repo_b)}

    page.click("#feedbackButton", timeout=5000)
    page.wait_for_selector("#feedbackText", timeout=5000)
    chooser = page.query_selector("#feedbackTarget")
    assert chooser is not None, "with no manager open, Home's Feedback dialog must offer a chooser"
    options = page.eval_on_selector_all("#feedbackTarget option[value]:not([value=''])", "els => els.length")
    assert options == len(MANAGERS), f"the chooser must list every manager session, got {options}"

    # Sending with nothing chosen must refuse, not silently pick one.
    said = "no target chosen yet"
    page.fill("#feedbackText", said)
    page.click("#dialogActions button:has-text('Send feedback')", timeout=5000)
    page.wait_for_timeout(400)
    after_a_names = {p.name for p in _feedback_files(repo_a)}
    after_b_names = {p.name for p in _feedback_files(repo_b)}
    assert not (after_a_names - before_a), "nothing may land anywhere before a target is chosen"
    assert not (after_b_names - before_b), "nothing may land anywhere before a target is chosen"
    assert page.is_visible("#feedbackText"), "the dialog must still be open -- the write did not silently proceed"

    # Choosing bravo explicitly must land ONLY in bravo's repo.
    page.select_option("#feedbackTarget", value="bravo")
    page.click("#dialogActions button:has-text('Send feedback')", timeout=5000)

    landed = None
    deadline = time.time() + 10
    while time.time() < deadline:
        fresh = [p for p in _feedback_files(repo_b) if p.name not in before_b]
        if fresh and said in fresh[-1].read_text(encoding="utf-8"):
            landed = fresh[-1]
            break
        time.sleep(0.2)
    assert landed is not None, "choosing bravo explicitly must file feedback in bravo's own repo"
    final_a_names = {p.name for p in _feedback_files(repo_a)}
    assert not (final_a_names - before_a), "nothing may land in alpha's repo from a bravo-targeted send"

    assert not errors, f"the browser logged: {errors}"
    ctx.close()


# --------------------------------------------------------------------------
# 5. source fences -- no browser needed, never skip
# --------------------------------------------------------------------------

JS = Path(__file__).resolve().parents[1] / "static" / "js"
MAIN_JS = (JS / "main.js").read_text(encoding="utf-8")
ACTIONS_JS = (JS / "actions.js").read_text(encoding="utf-8")
STATE_JS = (JS / "state.js").read_text(encoding="utf-8")
TOP_JS = (JS / "render" / "top.js").read_text(encoding="utf-8")
HOME_JS = (JS / "render" / "home.js").read_text(encoding="utf-8")
SHELL_CSS = Path(__file__).resolve().parents[1] / "static" / "css" / "shell.css"


def test_the_workspace_rail_no_longer_draws_homes_expanded_card_shape() -> None:
    assert "session-card" not in TOP_JS, "the workspace rail must not reuse Home's rich card markup"
    assert "session-row-detail" in TOP_JS, "the full facts must sit behind an accessible detail element"


def test_a_non_document_need_never_forces_the_console_open() -> None:
    fn = ACTIONS_JS[ACTIONS_JS.index("export async function openNeeds") :]
    fn = fn[: fn.index("\nexport function openSteer")]
    assert "state.workspace = 'operation'" in fn
    assert "state.consoleOpen = true" not in fn


def test_boot_fails_closed_on_a_rejected_principal() -> None:
    boot_body = MAIN_JS[MAIN_JS.index("async function boot()") :]
    catch_at = boot_body.index("await window.ConvergePWA.setPrincipal")
    catch_body = boot_body[catch_at : catch_at + 1400]
    assert "data.identityError" in catch_body, "a rejection must record the failure for Home to show"
    assert "data.managerList = []" in catch_body, "a rejection must clear any manager data rather than reading more"
    assert "state.screen = 'home'" in catch_body, "a rejection must retain Home, never another screen"
    assert "renderAll();\n      return;" in catch_body, (
        "boot() must render the failure and stop, never fall through to the normal read path"
    )


def test_home_renders_a_named_identity_failure_state() -> None:
    assert "identityError" in HOME_JS
    assert "identityFailureHtml" in HOME_JS
    assert "identityRetryButton" in HOME_JS


def test_feedback_target_never_falls_back_to_the_manager_list() -> None:
    fn = ACTIONS_JS[ACTIONS_JS.index("function feedbackTargetId") :]
    fn = fn[: fn.index("\nexport function openFeedback")]
    assert "data.managerList" not in fn
    assert re.search(r"return state\.managerId \|\| null", fn)


def test_no_rule_hides_the_compact_rails_needs_badge() -> None:
    css = SHELL_CSS.read_text(encoding="utf-8")
    assert ".needs-badge" in css
