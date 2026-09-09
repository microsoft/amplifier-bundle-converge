"""converge-04b7 — ordinary authenticated ONLINE browsing where service workers
are explicitly unavailable, without relaxing the identity fail-closed path.

Full regression testing found a genuine progressive-enhancement gap. With
``service_workers="block"`` Chromium keeps ``navigator.serviceWorker`` present,
but ``register()`` produces no registration and ``navigator.serviceWorker.ready``
never settles at all. ``setPrincipal()``'s 4s bound therefore answered
``no-response`` — an ACTIVE worker's silence — and ``main.js`` correctly failed
closed on it, throwing away a perfectly valid authenticated ``/api/boot``. The
app before the PWA landed worked fine online without a PWA; that had to stay
true.

**The shortcut this file exists to refuse.** The tempting fix is
``if (!navigator.serviceWorker.controller) proceed``. It is wrong, and wrong in
the dangerous direction: a normal FIRST page load also has no controller while
registration and activation are in flight, so the shortcut would wave the
identity check through exactly where ``clients.claim()`` is about to hand the
page a worker with someone else's caches behind it. Two negative controls below
would both pass under that shortcut's opposite — they fail loudly under the
shortcut itself:

* ``test_a_registration_that_exists_but_never_answers_still_fails_closed`` —
  same blocked page, same absent controller, but the published registration
  outcome says a worker EXISTS. Must reject. Under the bare no-controller
  shortcut this resolves, and the test fails.
* ``test_a_real_worker_still_refuses_a_user_the_server_does_not_hold`` —
  workers ALLOWED, a real registered worker, a name the server does not agree
  with. Must reject on mismatch. Measured: this page IS controlled by the time
  the seam is called, so the uncontrolled half of the claim is carried by
  control A above, which is where it is actually proved.

If Playwright or its Chromium build is unavailable the browser tests skip with
the reason printed, matching every other rendered test in this app.
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
OTHER = "someone-else"


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
# fixtures — one manager, one repo carrying one readable document
# --------------------------------------------------------------------------

FROZEN = """# Frozen Nobody Checks — v1 (FROZEN 2026-09-04)

## Core

1. **Nothing watches this promise.** No ledger row names this file.
"""

MANIFEST_HEAD = "lane\tworktree\tbranch\tbase\ttmux\tgoal\tlog\tstarted\n"

MANAGER_NAME = "Demo manager"
PRIVATE_MARKER = "Nothing watches this promise"


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
    tmp_path = tmp_path_factory.mktemp("worker-unavailable")
    repo = tmp_path / "demo-repo"
    (repo / "contracts").mkdir(parents=True)
    (repo / "contracts" / "frozen.v1.md").write_text(FROZEN, encoding="utf-8")
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "seed: a frozen, unmeasured contract")

    batch = tmp_path / "hw-demo"
    (batch / "goals").mkdir(parents=True)
    (batch / "HIGHWAY.md").write_text(
        "# Highway\n\n## Outcome\nEvery steward can still read this without a PWA.\n",
        encoding="utf-8",
    )
    (batch / "manifest.tsv").write_text(MANIFEST_HEAD, encoding="utf-8")

    conf = tmp_path / "converge-app.toml"
    conf.write_text(
        "[[managers]]\n"
        'id = "demo"\n'
        f'name = "{MANAGER_NAME}"\n'
        f'batch_dir = "{batch}"\n'
        f'repos = ["{repo}"]\n'
        'tracker_project = ""\n'
        'tmux_socket = "test-socket-that-does-not-exist"\n',
        encoding="utf-8",
    )
    return {
        "config": conf,
        "secret": tmp_path / "secret",
        "state": tmp_path / "state.json",
        "sessions": tmp_path / "sessions.json",
        "repo": repo,
    }


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


def _cookie(project, user: str = USER) -> dict:
    sessions = auth.Sessions(auth.read_or_make_secret(project["secret"]))
    return {"name": auth.COOKIE, "value": sessions.issue(user), "domain": "127.0.0.1", "path": "/"}


def _context(browser, project, *, workers: str):
    """A real signed-in browser context. ``workers='block'`` is Chromium's own
    switch, not a page-level stub: the app's own registration call is what
    fails, exactly as it does behind an enterprise policy or a non-secure
    origin."""
    ctx = browser.new_context(viewport={"width": 1280, "height": 800}, service_workers=workers)
    ctx.add_cookies([_cookie(project)])
    return ctx


def _watch(page, errors: list[str]) -> None:
    page.on("console", lambda m: errors.append(f"console.{m.type}: {m.text}") if m.type == "error" else None)
    page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))


# The exact seam under test, called the way Shell calls it. Returns a plain
# record so a rejection is data rather than an exception crossing the bridge.
SET_PRINCIPAL = """
  async (who) => {
    if (!window.ConvergePWA || typeof window.ConvergePWA.setPrincipal !== 'function') {
      return { settled: 'missing' };
    }
    try {
      const value = await window.ConvergePWA.setPrincipal(who);
      return { settled: 'resolved', ok: !!value.ok, reason: value.reason || '', user: value.user || '' };
    } catch (err) {
      return { settled: 'rejected', reason: (err && err.reason) || '', message: (err && err.message) || '' };
    }
  }
"""

WORKER_FACTS = """
  async () => {
    const sw = navigator.serviceWorker;
    let regs = 'unreadable';
    try { regs = (await sw.getRegistrations()).length; } catch (e) { regs = 'threw'; }
    return {
      apiPresent: 'serviceWorker' in navigator,
      controller: !!sw.controller,
      registrations: regs,
    };
  }
"""


# --------------------------------------------------------------------------
# acceptance 1 — a live authenticated server, workers blocked, real content
# --------------------------------------------------------------------------


@needs_browser
def test_workers_blocked_still_reaches_home_a_named_manager_and_a_document(server, project, browser):
    errors: list[str] = []
    ctx = _context(browser, project, workers="block")
    page = ctx.new_page()
    _watch(page, errors)
    page.goto(server, wait_until="networkidle")

    # Home, with the manager the server actually configured — not a shell.
    page.wait_for_selector(".home-manager-card", timeout=20000)
    home_text = page.eval_on_selector("#homeSessionGrid", "el => el.textContent || ''")
    assert MANAGER_NAME in home_text, f"Home reached but names no manager: {home_text!r}"

    # No identity failure screen: this is the exact regression — a valid online
    # boot discarded because there was no worker to answer.
    identity = page.evaluate("() => !!document.querySelector('[data-identity-error]')")
    assert "Identity check failed" not in home_text, (
        f"a valid authenticated boot was discarded as an identity failure: {home_text!r}"
    )

    # And a real document, read through the live server.
    page.click(".home-manager-card")
    page.wait_for_selector("#directionTab", timeout=20000)
    # No click here on purpose: main.js's own boot path auto-opens the first
    # repo's first document, so the document on screen is one the LIVE server
    # answered for during an ordinary load -- not one a test steered it to.
    page.wait_for_function(
        "() => (document.getElementById('docTitle').textContent || '').trim().length > 0",
        timeout=15000,
    )
    doc_text = page.eval_on_selector("#documentModeContent", "el => el.textContent || ''")

    facts = page.evaluate(WORKER_FACTS)
    seam = page.evaluate(SET_PRINCIPAL, USER)
    print(f"\n[blocked] worker facts={facts}")
    print(f"[blocked] setPrincipal({USER!r}) -> {seam}")
    print(f"[blocked] home names manager={MANAGER_NAME!r}; identity-error element present={identity}")
    print(f"[blocked] document text starts: {doc_text[:120]!r}")

    assert PRIVATE_MARKER in doc_text, f"the document did not render from the live server: {doc_text[:200]!r}"

    # PWA/offline is NOT falsely confirmed: the seam settles, and settles as an
    # honest capability gap, never as a confirmed identity.
    assert facts["apiPresent"] is True, "this context has no navigator.serviceWorker at all"
    assert facts["controller"] is False, "a worker is controlling a context that blocks workers"
    assert facts["registrations"] == 0, f"a blocked context reports registrations: {facts}"
    assert seam["settled"] == "resolved", f"setPrincipal did not resolve on a worker-free page: {seam}"
    assert seam["ok"] is False, f"a page with no worker claimed a CONFIRMED identity: {seam}"
    assert seam["reason"] == "no-worker-registration", (
        f"the capability gap was reported as something else: {seam}"
    )
    assert not errors, f"the page logged errors: {errors}"
    ctx.close()


# --------------------------------------------------------------------------
# acceptance 2 — negative control A: a registration exists, no reply, no
# controller. The bare `!controller` shortcut passes this page through; the
# evidence-based check must still reject.
# --------------------------------------------------------------------------


@needs_browser
def test_a_registration_that_exists_but_never_answers_still_fails_closed(server, project, browser):
    errors: list[str] = []
    ctx = _context(browser, project, workers="block")
    page = ctx.new_page()
    _watch(page, errors)
    page.goto(server, wait_until="networkidle")
    page.wait_for_selector(".home-manager-card", timeout=20000)

    # Replace ONLY the published registration outcome — the observation the
    # page makes about itself — with one that says a worker exists and is
    # installing. Nothing about the page's controller changes: it is still
    # null, exactly as on a first uncontrolled load. `ready` still never
    # settles here, so the only honest answer left is the 4s no-response
    # rejection.
    staged = page.evaluate(
        SET_PRINCIPAL.replace(
            "async (who) => {",
            "async (who) => {\n"
            "    window.ConvergePWA.registration = Promise.resolve("
            "{ active: null, installing: {}, waiting: null });",
        ),
        USER,
    )
    controller = page.evaluate("() => !!navigator.serviceWorker.controller")
    print(f"\n[negative control A] controller={controller} setPrincipal -> {staged}")

    assert controller is False, "this control is only meaningful while the page is uncontrolled"
    assert staged["settled"] == "rejected", (
        "a worker that exists and never answered was waved through on an uncontrolled page "
        f"— this is the bare !controller shortcut: {staged}"
    )
    assert staged["reason"] == "no-response", f"rejected for the wrong reason: {staged}"
    assert not errors, f"the page logged errors: {errors}"
    ctx.close()


# --------------------------------------------------------------------------
# acceptance 2 — negative control B: workers ALLOWED, a real registered worker,
# a user the server does not agree with. Must reject on mismatch rather than
# resolve as a capability gap. (Measured on this host: the worker has already
# claimed this page by the time the seam is called — `controller` is true — so
# the UNCONTROLLED case is proved by control A, not here. Printed, not assumed.)
# --------------------------------------------------------------------------


@needs_browser
def test_a_real_worker_still_refuses_a_user_the_server_does_not_hold(server, project, browser):
    errors: list[str] = []
    ctx = _context(browser, project, workers="allow")
    page = ctx.new_page()
    _watch(page, errors)
    page.goto(server, wait_until="networkidle")
    page.wait_for_selector(".home-manager-card", timeout=20000)
    page.wait_for_function(
        "() => !!navigator.serviceWorker.controller", timeout=20000
    )

    facts = page.evaluate(WORKER_FACTS)
    seam = page.evaluate(SET_PRINCIPAL, OTHER)
    print(f"\n[negative control B] worker facts={facts}")
    print(f"[negative control B] setPrincipal({OTHER!r}) -> {seam}")

    assert facts["registrations"] and facts["registrations"] != "threw", (
        f"workers were allowed but nothing registered: {facts}"
    )
    assert facts["controller"] is True, f"the mismatch probe had no controlling worker: {facts}"
    assert seam["settled"] == "rejected", (
        "a page asking under a name the server does not hold was NOT refused — "
        f"a capability gap was claimed where a real worker exists: {seam}"
    )
    assert seam["reason"] == "mismatch", f"the live worker did not prove the identity mismatch: {seam}"
    assert not errors, f"the page logged errors: {errors}"
    ctx.close()


# --------------------------------------------------------------------------
# acceptance 3 — offline, with no worker, exposes no cached private content
# --------------------------------------------------------------------------


@needs_browser
def test_offline_without_a_worker_exposes_no_cached_private_content(server, project, browser):
    errors: list[str] = []
    ctx = _context(browser, project, workers="block")
    page = ctx.new_page()
    _watch(page, errors)
    page.goto(server, wait_until="networkidle")
    page.wait_for_selector(".home-manager-card", timeout=20000)
    page.click(".home-manager-card")
    page.wait_for_selector("#directionTab", timeout=20000)
    # No click here on purpose: main.js's own boot path auto-opens the first
    # repo's first document, so the document on screen is one the LIVE server
    # answered for during an ordinary load -- not one a test steered it to.
    page.wait_for_function(
        "() => (document.getElementById('docTitle').textContent || '').trim().length > 0",
        timeout=15000,
    )
    online_text = page.eval_on_selector("#documentModeContent", "el => el.textContent || ''")
    assert PRIVATE_MARKER in online_text, "precondition failed: the document never rendered online"

    ctx.set_offline(True)
    try:
        page.reload(wait_until="domcontentloaded", timeout=15000)
    except Exception as exc:  # the browser's own error page is a normal outcome here
        print(f"\n[offline reload] navigation failed as expected: {str(exc).splitlines()[0]}")
    page.wait_for_timeout(1200)
    after = page.content()
    try:
        facts = page.evaluate(WORKER_FACTS)
    except Exception as exc:  # Chromium's own offline error page runs no app script
        facts = f"unreadable ({str(exc).splitlines()[0]})"
    print(f"[offline reload] worker facts={facts}")
    print(f"[offline reload] page length={len(after)} names manager={MANAGER_NAME in after} "
          f"names private doc={PRIVATE_MARKER in after}")

    assert PRIVATE_MARKER not in after, (
        "private document content was served from a cache on a device with no service worker"
    )
    assert MANAGER_NAME not in after, (
        "a manager session's name was served from a cache on a device with no service worker"
    )
    ctx.close()
