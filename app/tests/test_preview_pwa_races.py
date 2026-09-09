"""The real race: a response in flight when an account switch happens
(converge-lnxu, pwa-final).

Every previous PWA test proved the epoch guard and the identity-rejection
seam as SOURCE facts or as SEQUENTIAL server calls -- `test_preview_pwa.py`'s
own docstring records why: Playwright's `page.route()` cannot intercept a
request a Service Worker issues itself, only requests the PAGE makes, so
staging "the worker's own fetch is slow, and a clear lands while it is still
in flight" from outside the worker looked impossible with the tools at hand.

It is not impossible -- it just needs the hold on the SERVER side instead of
the browser side. This file adds a fixture ASGI middleware that recognizes
one query-qualified request and pauses it, mid-flight, on a real
`threading.Event` before the real app ever sees it. That lets a test:

  1. fire a real fetch through the real service worker for a marked URL,
  2. block until the middleware confirms that request has reached the real
     backend (a second `threading.Event`, set the instant the hold begins),
  3. perform a real, server-verified account switch or logout while that
     first request is still outstanding,
  4. release the held request, and only THEN observe whether its (now
     stale) answer was allowed to land in the cache or leak to whoever the
     device confirms now.

No source-string matching proves any of this: every assertion below reads
the actual state of Cache Storage or the actual body of a live fetch, after
a real, wall-clock race actually happened.

What this file adds beyond the epoch guard itself:

* **A held response answering under the OLD identity (X-Converge-User) must
  never repopulate the cache once released after a real switch/logout.**
  Covered by `test_a_response_in_flight_during_a_real_switch_is_never_recached`.
* **The same held response, offline right after, must not read back either.**
  Same test -- the strongest single proof available that #2's cache-owner
  binding and #3's reordered epoch both hold under an actual race, not just
  in the sequence the existing tests exercise them in.
* **A confirmation that races a real switch and lands on the wrong side of
  it must reject, not resolve.** `test_setprincipal_rejects_on_a_genuine_mismatch_after_release`
  drives this with the SAME held request, so the "expected boot user" is
  provably stale by the time the rejection is asserted, not merely a forged
  literal (test_preview_pwa_security.py already covers the forged-literal
  case; this covers the same reject path from an honest race instead).
* **An active worker that fails to confirm at all -- a real 500, not a
  dropped connection -- must reject, not resolve `ok:false` for a caller to
  silently ignore.** `test_setprincipal_rejects_when_the_real_boot_recheck_fails`.

What is still honestly NOT staged here, and why: a request the worker
issues to itself (`fetchBootIdentity()`'s own /api/boot re-fetch) cannot be
distinguished, at the ASGI layer, from an ordinary page-driven /api/boot
read -- both are indistinguishable GET /api/boot calls with the same
cookie. Racing that specific internal fetch would need holding EVERY
/api/boot request, including the page's own boot read the test itself
depends on to drive the browser -- which would deadlock the harness, not
prove anything. The mismatch path is instead proved by racing a READ
(`/api/managers/{mid}`) against a real switch and then calling `setPrincipal`
with the now-stale expected user, which exercises the identical
`result.user !== name` branch in offline.js from a genuinely raced state.
"""

from __future__ import annotations

import asyncio
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
    reason=f"{PLAYWRIGHT_SKIP}; run the app by hand and drive it with devtools instead",
)

# Chromium logs one console line for every non-2xx response, whoever asked
# for it -- a 401/403/503 provoked ON PURPOSE by these tests is that line
# narrating the very thing being tested, not a defect. Same convention as
# test_offline.py's own NARRATED_REFUSAL/_defects and
# test_preview_pwa_security.py's NARRATED_STATUS/_defects.
NARRATED_STATUS = re.compile(r"responded with a status of (401|403|500|503)")


def _defects(errors: list[str]) -> list[str]:
    return [e for e in errors if not NARRATED_STATUS.search(e)]


# --------------------------------------------------------------------------
# the fixture ASGI middleware -- the hold this file exists to add
# --------------------------------------------------------------------------


class RaceGate:
    """One hold, armed per test. `reached` fires the instant a marked
    request arrives at this middleware -- proof it left the browser, went
    through the real service worker, and hit the real backend. Nothing
    proceeds past that point until the test calls `release()`."""

    def __init__(self) -> None:
        self.reached = threading.Event()
        self.release_flag = threading.Event()
        self.forced_status: int | None = None

    def arm(self) -> None:
        self.reached.clear()
        self.release_flag.clear()
        self.forced_status = None

    def release(self, forced_status: int | None = None) -> None:
        # A held request's cookie already left the browser -- an HTTP
        # request, once sent, carries the headers it carried; clearing the
        # browser's cookie jar afterwards cannot rewrite a request already
        # in flight. `forced_status` is the honest way to stage "this
        # session was invalidated while the request was outstanding": the
        # real server really answers with that real status once released,
        # instead of what the real app would answer for what the request
        # actually still carries.
        self.forced_status = forced_status
        self.release_flag.set()

    def wait_reached(self, timeout: float = 5.0) -> bool:
        return self.reached.wait(timeout=timeout)


class HoldMarkedRequests:
    """Holds exactly the requests carrying `MARKER` in their query string,
    mid-flight, on a real `threading.Event` -- via a thread-pool executor so
    the blocking wait never stalls the event loop itself, letting a second,
    unmarked request (the real switch/logout) complete normally while the
    first is still paused here."""

    MARKER = b"race_hold=1"

    def __init__(self, app, gate: RaceGate) -> None:
        self.app = app
        self.gate = gate

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or self.MARKER not in scope.get("query_string", b""):
            await self.app(scope, receive, send)
            return
        self.gate.reached.set()
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self.gate.release_flag.wait)
        status = getattr(self.gate, "forced_status", None)
        if status is not None:
            await send({
                "type": "http.response.start",
                "status": status,
                "headers": [(b"content-type", b"application/json")],
            })
            await send({"type": "http.response.body", "body": b'{"error": "session invalidated mid-flight"}'})
            return
        await self.app(scope, receive, send)


class ForceBootFailureOnce:
    """A real 500 for exactly the NEXT /api/boot request after `arm()` --
    the honest way to stage 'an active worker's own re-check fails' without
    dropping a connection or mocking anything: the server really answers
    with a real error, once, then goes back to answering normally."""

    def __init__(self, app) -> None:
        self.app = app
        self.armed = False

    def arm(self) -> None:
        self.armed = True

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http" and scope["path"] == "/api/boot" and self.armed:
            self.armed = False
            await send({
                "type": "http.response.start",
                "status": 500,
                "headers": [(b"content-type", b"application/json")],
            })
            await send({"type": "http.response.body", "body": b'{"error": "forced failure"}'})
            return
        await self.app(scope, receive, send)


# --------------------------------------------------------------------------
# a project to serve -- same shape as the other pwa test files' fixtures
# --------------------------------------------------------------------------

VISION = """# Demo Vision (DRAFT)

## Where this is going

One place for direction and one place for operation.
"""

HIGHWAY = """# Highway -- demo

Width 2.
"""

MANIFEST_HEAD = "lane\tworktree\tbranch\tbase\ttmux\tgoal\tlog\tstarted\n"


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "user.name=Test", "-c", "user.email=test@example.invalid", *args],
        cwd=repo, check=True, capture_output=True,
    )


@pytest.fixture(scope="module")
def project(tmp_path_factory) -> dict:
    tmp_path = tmp_path_factory.mktemp("pwa-races")
    repo = tmp_path / "demo-repo"
    (repo / "docs").mkdir(parents=True)
    (repo / "docs" / "VISION.md").write_text(VISION, encoding="utf-8")
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "seed: the vision")

    batch = tmp_path / "hw-demo"
    (batch / "goals").mkdir(parents=True)
    (batch / "HIGHWAY.md").write_text(HIGHWAY, encoding="utf-8")
    (batch / "manifest.tsv").write_text(MANIFEST_HEAD, encoding="utf-8")

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
    secret_path = tmp_path / "secret"
    return {"config": conf, "secret_path": secret_path, "state": tmp_path / "state.json", "sessions": tmp_path / "sessions.json"}


def _free_port() -> int:
    s = socketlib.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


@pytest.fixture(scope="module")
def gate() -> RaceGate:
    return RaceGate()


@pytest.fixture(scope="module")
def server(project, gate):
    import uvicorn

    made = serve.create_app(config_path=project["config"], secret_path=project["secret_path"], state_path=project["state"])
    boot_failure = ForceBootFailureOnce(made)
    held = HoldMarkedRequests(boot_failure, gate)

    port = _free_port()
    config = uvicorn.Config(held, host="127.0.0.1", port=port, log_level="warning")
    uv_server = uvicorn.Server(config)
    thread = threading.Thread(target=uv_server.run, daemon=True)
    thread.start()
    deadline = time.time() + 20
    while not uv_server.started and time.time() < deadline:
        time.sleep(0.05)
    assert uv_server.started, "app server did not start"
    print(f"\napp server: http://127.0.0.1:{port} (in-process, torn down with this module)")
    yield {"url": f"http://127.0.0.1:{port}", "boot_failure": boot_failure}
    uv_server.should_exit = True
    thread.join(timeout=10)


@pytest.fixture(scope="module")
def browser():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        b = p.chromium.launch(args=["--no-sandbox"])
        yield b
        b.close()


def _cookie_for(project, user: str) -> dict:
    sessions = auth.Sessions(auth.read_or_make_secret(project["secret_path"]))
    return {"name": auth.COOKIE, "value": sessions.issue(user), "domain": "127.0.0.1", "path": "/"}


def _installed(browser, server, project, cookie_user: str):
    ctx = browser.new_context(viewport={"width": 1280, "height": 800})
    ctx.add_cookies([_cookie_for(project, cookie_user)])
    page = ctx.new_page()
    errors: list[str] = []
    page.on("console", lambda m: errors.append(f"console.{m.type}: {m.text}") if m.type == "error" else None)
    page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))

    page.goto(server["url"], wait_until="networkidle")
    page.wait_for_selector(".home-manager-card", timeout=15000)
    page.click(".home-manager-card")
    page.wait_for_selector("#directionTab", timeout=15000)
    page.click("#directionTab")
    page.wait_for_selector("#documentModeContent", timeout=15000)
    page.evaluate("async () => { await navigator.serviceWorker.ready; }")
    page.reload(wait_until="networkidle")
    page.wait_for_selector(".home-manager-card", timeout=15000)
    page.click(".home-manager-card")
    page.wait_for_selector("#directionTab", timeout=15000)
    page.click("#directionTab")
    page.wait_for_selector("#documentModeContent", timeout=15000)
    page.wait_for_function("() => !!navigator.serviceWorker.controller", timeout=15000)
    page.wait_for_timeout(500)
    return ctx, page, errors


def _switch_cookie(ctx, project, user: str) -> None:
    ctx.clear_cookies()
    ctx.add_cookies([_cookie_for(project, user)])


def _synced_keys(page) -> list[str]:
    return page.evaluate(
        "async () => { const c = await caches.open('converge-synced-v1');"
        " return (await c.keys()).map(r => new URL(r.url).pathname + new URL(r.url).search).sort(); }"
    )


CONFIRM_VIA_REAL_BOOT = """
async () => {
  const r = await fetch('/api/boot', {credentials: 'same-origin'});
  const body = await r.json().catch(() => ({}));
  try {
    const result = await window.ConvergePWA.setPrincipal(body.user || '');
    return Object.assign({ rejected: false }, result);
  } catch (e) {
    return { rejected: true, ok: false, reason: (e && e.reason) || '',
             user: (e && e.user) || '', cleared: !!(e && e.cleared),
             message: String((e && e.message) || e) };
  }
}
"""

SET_PRINCIPAL_LITERAL = """
(user) => window.ConvergePWA.setPrincipal(user).then(
  (result) => Object.assign({ rejected: false }, result),
  (e) => ({ rejected: true, ok: false, reason: (e && e.reason) || '',
            user: (e && e.user) || '', cleared: !!(e && e.cleared),
            message: String((e && e.message) || e) }),
)
"""

# Fires a marked GET through the real service worker WITHOUT waiting for it
# -- the arrow function itself returns the instant the fetch is issued; the
# fetch's own completion is stashed on `window` for a later call to collect.
FIRE_HELD_READ = """
() => {
  window.__raceResult = null;
  window.__racePromise = fetch('/api/managers/demo?race_hold=1', {credentials: 'same-origin'})
    .then(async (r) => { window.__raceResult = { status: r.status, offline: r.headers.get('X-Converge-Offline') }; return window.__raceResult; })
    .catch((e) => { window.__raceResult = { error: String(e) }; return window.__raceResult; });
  return true;
}
"""

COLLECT_RACE_RESULT = "async () => { return await window.__racePromise; }"


# --------------------------------------------------------------------------
# 1. the core race: a response answering under the OLD identity, released
#    only after a real switch, must never repopulate the cache or leak
# --------------------------------------------------------------------------


@needs_browser
def test_a_response_in_flight_during_a_real_switch_is_never_recached(server, project, gate, browser):
    ctx, page, errors = _installed(browser, server, project, cookie_user="alice")
    confirmed = page.evaluate(CONFIRM_VIA_REAL_BOOT)
    assert confirmed["rejected"] is False and confirmed["ok"] and confirmed["user"] == "alice"

    gate.arm()
    fired = page.evaluate(FIRE_HELD_READ)
    assert fired is True

    reached = gate.wait_reached(timeout=5.0)
    assert reached, "the marked request never reached the real backend -- the race was never staged"
    print("\nheld GET /api/managers/demo?race_hold=1 has reached the real backend, under alice's cookie")

    # The real switch happens WHILE alice's read is still paused server-side.
    _switch_cookie(ctx, project, "bob")
    switched = page.evaluate(CONFIRM_VIA_REAL_BOOT)
    assert switched["rejected"] is False
    assert switched["ok"] and switched["user"] == "bob" and switched["cleared"] is True
    print(f"confirmed switch to bob while alice's read is still held: {switched}")
    assert _synced_keys(page) == [], "the switch to bob did not clear what alice had synced"

    # NOW release alice's answer. It arrives under the X-Converge-User: alice
    # header that the real app derives from the cookie that request actually
    # carried, well after bob has been confirmed and the cache cleared for him.
    gate.release()
    result = page.evaluate(COLLECT_RACE_RESULT)
    print(f"alice's held response, released after the switch to bob: {result}")
    assert result.get("status") == 200, f"the held request did not complete normally: {result}"

    after = _synced_keys(page)
    print(f"SYNCED after releasing alice's stale response: {after}")
    assert after == [], (
        "alice's response, answered and released after the switch to bob, repopulated the cache -- "
        "exactly the race #3's epoch-before-clear reorder and #2's owner binding exist to prevent"
    )

    # And the strongest available proof: read the SAME path offline, as bob,
    # right now. If alice's stale answer had snuck into the cache, this
    # would serve it to bob; it must instead honestly say nothing is synced.
    ctx.set_offline(True)
    offline_answer = page.evaluate(
        "async () => { const r = await fetch('/api/managers/demo?race_hold=1', {credentials: 'same-origin'});"
        " let body = null; try { body = await r.json(); } catch { body = null; }"
        " return {status: r.status, offline: r.headers.get('X-Converge-Offline'), body}; }"
    )
    print(f"offline read of the raced path, as bob: {offline_answer}")
    assert offline_answer["status"] != 200 or (offline_answer["body"] or {}).get("offline") is True, (
        f"an offline read after the race served something instead of an honest refusal: {offline_answer}"
    )
    ctx.set_offline(False)

    # #1's mismatch reject, proved from an HONEST race rather than a forged
    # literal: "alice" is what THIS page last confirmed before the switch,
    # and it no longer matches who the server confirms now.
    mismatch = page.evaluate(SET_PRINCIPAL_LITERAL, "alice")
    print(f"setPrincipal('alice') called after the real switch to bob: {mismatch}")
    assert mismatch["rejected"] is True, f"a stale expected-user after a real switch must reject: {mismatch}"
    assert mismatch["reason"] == "mismatch"
    assert mismatch["user"] == "bob"

    assert not _defects(errors), f"the browser reported errors: {_defects(errors)}"
    ctx.close()


# --------------------------------------------------------------------------
# 2. a held response that becomes a 401 mid-flight (cookie cleared while
#    it was outstanding) must clear via the real gate, never crash or leak
# --------------------------------------------------------------------------


@needs_browser
def test_a_held_response_that_becomes_a_401_mid_flight_clears_instead_of_leaking(server, project, gate, browser):
    ctx, page, errors = _installed(browser, server, project, cookie_user="alice")
    confirmed = page.evaluate(CONFIRM_VIA_REAL_BOOT)
    assert confirmed["rejected"] is False and confirmed["ok"]
    assert _synced_keys(page), "nothing was synced under alice, so a later clear proves nothing"

    gate.arm()
    fired = page.evaluate(FIRE_HELD_READ)
    assert fired is True
    assert gate.wait_reached(timeout=5.0), "the marked request never reached the real backend"

    # The browser's cookie is cleared too (the honest logout this stands in
    # for), but an HTTP request already in flight keeps the headers it left
    # with -- clearing the jar afterwards cannot rewrite it. `forced_status`
    # is what actually stages "this session died while the request was
    # outstanding": the real server really answers 401 once released.
    ctx.clear_cookies()
    gate.release(forced_status=401)
    result = page.evaluate(COLLECT_RACE_RESULT)
    print(f"\nheld request released after the session was invalidated mid-flight: {result}")
    assert result.get("status") == 401, f"expected the real gate to refuse once released: {result}"

    print(f"SYNCED after the mid-flight 401: {_synced_keys(page)}")
    assert _synced_keys(page) == [], "a 401 discovered on a released, held request did not clear the cache"
    assert not _defects(errors), f"the browser reported errors: {_defects(errors)}"
    ctx.close()


# --------------------------------------------------------------------------
# 3. an active worker's own re-check genuinely fails (a real 500, not a
#    dropped connection) -- must reject, never resolve silently
# --------------------------------------------------------------------------


@needs_browser
def test_setprincipal_rejects_when_the_real_boot_recheck_fails(server, project, browser):
    ctx, page, errors = _installed(browser, server, project, cookie_user="alice")
    confirmed = page.evaluate(CONFIRM_VIA_REAL_BOOT)
    assert confirmed["rejected"] is False and confirmed["ok"]
    before = _synced_keys(page)
    assert before, "nothing was synced under alice, so this test cannot show it was preserved"

    server["boot_failure"].arm()
    failed = page.evaluate(SET_PRINCIPAL_LITERAL, "alice")
    print(f"\nsetPrincipal('alice') while the real /api/boot recheck answers a forced 500: {failed}")
    assert failed["rejected"] is True, f"a real, confirmed re-check failure must reject: {failed}"
    assert failed["reason"] == "boot-unreachable"
    assert failed["cleared"] is False
    assert _synced_keys(page) == before, "a failed re-check alone must never touch what was already synced"
    assert not _defects(errors), f"the browser reported errors: {_defects(errors)}"
    ctx.close()


@needs_browser
def test_a_failed_first_confirmation_cannot_admit_a_later_live_response(server, project, browser):
    """With no durable principal, a failed worker-owned /api/boot recheck
    leaves later matching live reads out of SYNCED until a recheck succeeds."""
    ctx, page, errors = _installed(browser, server, project, cookie_user="alice")
    page.evaluate(
        "async () => { await caches.delete('converge-principal-v1');"
        " await caches.delete('converge-synced-v1'); }"
    )

    server["boot_failure"].arm()
    failed = page.evaluate(SET_PRINCIPAL_LITERAL, "alice")
    print(f"\nfirst setPrincipal('alice') while its real /api/boot recheck answers 500: {failed}")
    assert failed["rejected"] is True and failed["reason"] == "boot-unreachable"
    assert page.evaluate(
        "async () => { const c = await caches.open('converge-principal-v1');"
        " return !!(await c.match('/__converge_principal__')); }"
    ) is False, "a failed boot recheck recorded a principal anyway"

    live = page.evaluate(
        """async () => {
            const r = await fetch('/api/managers/demo?failed_first_confirmation=1',
                                  {credentials: 'include'});
            return {status: r.status, user: r.headers.get('X-Converge-User')};
        }"""
    )
    assert live == {"status": 200, "user": "alice"}
    assert _synced_keys(page) == [], "an unconfirmed device admitted a live response after its boot recheck failed"

    ctx.set_offline(True)
    missed = page.evaluate(
        """async () => {
            const r = await fetch('/api/managers/demo?failed_first_confirmation=1',
                                  {credentials: 'include'});
            return {status: r.status, offline: r.headers.get('X-Converge-Offline'), body: await r.json()};
        }"""
    )
    print(f"offline read after the failed first confirmation: {missed}")
    assert missed["status"] == 503 and missed["offline"] is None
    assert "has not been synced" in missed["body"]["error"]
    ctx.set_offline(False)

    recovered = page.evaluate(SET_PRINCIPAL_LITERAL, "alice")
    assert recovered["rejected"] is False and recovered["ok"] and recovered["user"] == "alice"
    admitted = page.evaluate(
        """async () => {
            const r = await fetch('/api/managers/demo?after_successful_confirmation=1',
                                  {credentials: 'include'});
            return {status: r.status, user: r.headers.get('X-Converge-User')};
        }"""
    )
    assert admitted == {"status": 200, "user": "alice"}
    assert "/api/managers/demo?after_successful_confirmation=1" in _synced_keys(page)
    assert not _defects(errors), f"the browser reported errors: {_defects(errors)}"
    ctx.close()
