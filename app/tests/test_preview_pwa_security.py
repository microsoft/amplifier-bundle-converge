"""Adversarial regression tests for identity-safe caching (converge-lnxu, repair).

An independent security review of the pwa lane's first landing (commit
8a48511) found its stated acceptance "no cross-account cache access after
change/logout" 2/3 unfulfilled: `sw.js` trusted `event.data.user` -- whatever
the PAGE claimed in a `converge-set-principal` message -- as identity, and
persisted it. `test_preview_pwa.py`'s own setPrincipal tests proved this: they
called `window.ConvergePWA.setPrincipal("alice")` / `("bob")` with literal
strings and never a real second session, so they exercised the unsafe seam
rather than closing it.

The fix: `sw.js` no longer treats any page message as identity. On
`converge-set-principal` it makes its OWN same-origin, credentialed fetch of
`/api/boot` and acts only on what the real server says there. A page message
is now only ever a request to check -- see `fetchBootIdentity()` in `sw.js`.

This file proves that fix adversarially: every test here drives a REAL second
server-authenticated session (a genuine signed cookie for a different
fixture user, issued by `app/auth.py`, never a literal handed to
`setPrincipal`), and shows the worker follows the server, not the page, even
when the page actively lies about it.

What is honestly NOT proved here, and why:

* **A response already in flight when a clear happens, arriving after.**
  `sw.js`'s `readApi()` guards this with an epoch captured before the fetch
  and rechecked after (`clearSyncedForNewEpoch()` bumps it on every
  identity-reason clear), but staging "the SW's own internal fetch to
  `/api/...` is slow" from outside the worker needs CDP-level interception of
  the Service Worker's own network requests -- `test_preview_pwa.py`'s own
  docstring already records that Playwright's `page.route()` here does not
  reach requests a Service Worker itself issues, only requests the PAGE
  makes. Proved as a *source* fact below instead (`test_the_epoch_guard...`),
  same convention that file already uses for its own unreachable race.
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

APP = Path(__file__).resolve().parents[1]
SW = APP / "static" / "sw.js"
SW_TEXT = SW.read_text(encoding="utf-8")


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


# --------------------------------------------------------------------------
# a project to serve -- same shape as test_preview_pwa.py's own fixture
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
    tmp_path = tmp_path_factory.mktemp("pwa-security")
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
    return {"config": conf, "secret": tmp_path / "secret", "state": tmp_path / "state.json", "sessions": tmp_path / "sessions.json"}


def _free_port() -> int:
    s = socketlib.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


@pytest.fixture(scope="module")
def server(project):
    import uvicorn

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


def _cookie_for(project, user: str) -> dict:
    sessions = auth.Sessions(auth.read_or_make_secret(project["secret"]))
    return {"name": auth.COOKIE, "value": sessions.issue(user), "domain": "127.0.0.1", "path": "/"}


def _installed(browser, server, project, cookie_user: str):
    """Same shape as test_preview_pwa.py's own `_installed`: open once so the
    worker installs, then reload so it is CONTROLLING the page."""
    ctx = browser.new_context(viewport={"width": 1280, "height": 800})
    ctx.add_cookies([_cookie_for(project, cookie_user)])
    page = ctx.new_page()
    errors: list[str] = []
    page.on("console", lambda m: errors.append(f"console.{m.type}: {m.text}") if m.type == "error" else None)
    page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))

    page.goto(server, wait_until="networkidle")
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
    """Change the REAL, server-verifiable session -- never a page-side claim."""
    ctx.clear_cookies()
    ctx.add_cookies([_cookie_for(project, user)])


# The honest flow: fetch /api/boot, then await setPrincipal with what the
# AUTHENTICATED response named. No argument, because a caller has nothing
# trustworthy to pass except what this itself reads.
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

# The attack this whole file exists to catch: calling the seam directly with
# a literal, as if a page compromised by XSS -- or Shell itself, running
# stale data -- claimed an identity outright rather than asking sw.js to
# check.
FORGE_PRINCIPAL = """
(user) => window.ConvergePWA.setPrincipal(user).then(
  (result) => Object.assign({ rejected: false }, result),
  (e) => ({ rejected: true, ok: false, reason: (e && e.reason) || '',
            user: (e && e.user) || '', cleared: !!(e && e.cleared),
            message: String((e && e.message) || e) }),
)
"""


def _synced_keys(page) -> list[str]:
    return page.evaluate(
        "async () => { const c = await caches.open('converge-synced-v1');"
        " return (await c.keys()).map(r => new URL(r.url).pathname).sort(); }"
    )


# Chromium logs one console line for every non-2xx response, whoever asked
# for it -- a 401/403/503 provoked ON PURPOSE by these tests is that line
# narrating the very thing being tested, not a defect. Same convention as
# test_offline.py's own NARRATED_REFUSAL/_defects.
NARRATED_STATUS = re.compile(r"responded with a status of (401|403|503)")


def _defects(errors: list[str]) -> list[str]:
    return [e for e in errors if not NARRATED_STATUS.search(e)]


def _boot_offline(page) -> dict:
    """What GET /api/boot answers right now, offline included: the same
    request the page itself makes, so a served-from-cache answer is proved
    the same way \u00a710 proves it in test_offline.py -- never a fact about a
    request no real caller ever makes."""
    return page.evaluate(
        """async () => {
            const r = await fetch('/api/boot', {credentials: 'same-origin'});
            let body = null;
            try { body = await r.json(); } catch { body = null; }
            return {status: r.status, offline: r.headers.get('X-Converge-Offline'), body};
        }"""
    )


# --------------------------------------------------------------------------
# 1. Alice's cache, Bob's real session, a forged Alice message
# --------------------------------------------------------------------------


@needs_browser
def test_a_forged_hint_cannot_keep_a_victims_cache_when_the_real_cookie_is_now_someone_elses(
    server, project, browser
):
    """The exact scenario the security review named: Alice's device syncs,
    the browser is then handed to (or hijacked as) Bob, and a forged message
    still claims "alice" -- the one case that must clear, not keep."""
    ctx, page, errors = _installed(browser, server, project, cookie_user="alice")
    confirmed = page.evaluate(CONFIRM_VIA_REAL_BOOT)
    assert confirmed["rejected"] is False, f"a legitimate boot-derived confirmation must resolve: {confirmed}"
    assert confirmed["ok"] and confirmed["user"] == "alice"
    before = _synced_keys(page)
    assert before, "nothing was synced under alice, so this test cannot show it was cleared"

    _switch_cookie(ctx, project, "bob")
    forged = page.evaluate(FORGE_PRINCIPAL, "alice")
    print(f"\nreal cookie is now bob's; forged claim says 'alice': {forged}")

    assert forged["rejected"] is True, (
        f"a hint ('alice') that does not match what the worker actually confirmed must reject, "
        f"not resolve ok=true: {forged}"
    )
    assert forged["reason"] == "mismatch"
    assert forged["user"] == "bob", (
        f"the worker believed the forged page claim instead of its own /api/boot fetch: {forged}"
    )
    assert forged["cleared"] is True, "a real identity change (alice -> bob) was not reported as a clear"
    assert _synced_keys(page) == [], "bob can still read whatever alice's session synced"
    assert not errors, f"the browser reported errors: {errors}"
    ctx.close()


# --------------------------------------------------------------------------
# 2. A forged hint that happens to match the real identity is a pure no-op
# --------------------------------------------------------------------------


@needs_browser
def test_a_forged_hint_that_does_not_match_a_real_change_clears_nothing(server, project, browser):
    """The cookie never changes here -- only the page's claim is adversarial.
    A worker that cleared on this would let ANY page script wipe good offline
    reads just by naming someone else; #2 forbids exactly that."""
    ctx, page, errors = _installed(browser, server, project, cookie_user="alice")
    page.evaluate(CONFIRM_VIA_REAL_BOOT)
    before = _synced_keys(page)
    assert before, "nothing was synced under alice, so this test cannot show it was preserved"

    forged = page.evaluate(FORGE_PRINCIPAL, "mallory")
    print(f"\nreal cookie still alice's; forged claim says 'mallory': {forged}")

    assert forged["rejected"] is True, (
        f"a hint ('mallory') that does not match the real identity must reject: {forged}"
    )
    assert forged["reason"] == "mismatch"
    assert forged["user"] == "alice", f"the worker echoed the forged name instead of the real one: {forged}"
    assert forged["cleared"] is False, "a forged claim with no real identity change still cleared the cache"
    assert _synced_keys(page) == before, "a forged claim changed what was synced even though nothing really did"
    assert not errors, f"the browser reported errors: {errors}"
    ctx.close()


# --------------------------------------------------------------------------
# 3. A rejected cookie clears via the real gate, even mid-forgery
# --------------------------------------------------------------------------


@needs_browser
def test_a_rejected_cookie_clears_via_the_real_gate_even_though_a_forged_message_claims_nothing_changed(
    server, project, browser
):
    """A page that is (or is pretending to be) unaware its cookie died cannot
    talk the worker out of the 401 the real server already answered with."""
    ctx, page, errors = _installed(browser, server, project, cookie_user="alice")
    page.evaluate(CONFIRM_VIA_REAL_BOOT)
    assert _synced_keys(page), "nothing was synced under alice, so a later clear proves nothing"

    ctx.clear_cookies()
    forged = page.evaluate(FORGE_PRINCIPAL, "alice")
    print(f"\ncookie removed; forged claim says nothing changed: {forged}")
    # The worker's own /api/boot re-check now 401s. That is neither proof
    # someone new is confirmed nor proof the old principal is still good, so
    # this call alone changes nothing -- it is honestly unable to confirm.
    assert forged["rejected"] is True, (
        f"an unresolved active-worker confirmation (boot unreachable/401) must reject: {forged}"
    )
    assert forged["reason"] == "boot-unreachable"
    assert forged["cleared"] is False
    assert _synced_keys(page), "an unreachable/401 boot check alone wiped the cache -- it should refuse, not guess"

    # The real gate is what actually clears: any ordinary GET now 401s for
    # real, and readApi()'s isAuthLoss branch acts on THAT, not on the message.
    real_check = page.evaluate(
        "async () => { const r = await fetch('/api/managers/demo', {credentials: 'same-origin'});"
        " return {status: r.status}; }"
    )
    print(f"a real GET after the cookie was removed: {real_check}")
    assert real_check["status"] == 401
    print(f"SYNCED after the real 401: {_synced_keys(page)}")
    assert _synced_keys(page) == [], "the real gate's 401 did not clear what alice had synced"
    assert not _defects(errors), f"the browser reported errors: {_defects(errors)}"
    ctx.close()


# --------------------------------------------------------------------------
# 4. Multi-tab: a confirmed switch in one tab is not silently ignored by
#    another, and the durable (Cache Storage, not memory) principal record
#    is what a freshly-created tab -- standing in for a freshly-restarted
#    worker, which reads the exact same durable record -- actually sees.
# --------------------------------------------------------------------------


@needs_browser
def test_a_second_tab_reads_the_first_tabs_confirmed_switch_not_the_old_principal(server, project, browser):
    ctx, page_a, errors_a = _installed(browser, server, project, cookie_user="alice")
    page_a.evaluate(CONFIRM_VIA_REAL_BOOT)
    assert _synced_keys(page_a), "nothing was synced under alice in tab A"

    _switch_cookie(ctx, project, "bob")
    switched = page_a.evaluate(CONFIRM_VIA_REAL_BOOT)
    assert switched["rejected"] is False, f"a legitimate boot-derived switch must resolve: {switched}"
    assert switched["ok"] and switched["user"] == "bob" and switched["cleared"] is True

    # A second tab in the SAME context/worker registration. It never itself
    # called setPrincipal; PRINCIPAL/EPOCH live in Cache Storage precisely so
    # a party that did not witness the switch -- a second tab, or this same
    # worker after being stopped and restarted -- still reads the confirmed
    # state rather than some earlier one held only in memory.
    page_b = ctx.new_page()
    errors_b: list[str] = []
    page_b.on("console", lambda m: errors_b.append(f"console.{m.type}: {m.text}") if m.type == "error" else None)
    page_b.goto(server, wait_until="networkidle")
    page_b.wait_for_selector(".home-manager-card", timeout=15000)
    page_b.click(".home-manager-card")
    page_b.wait_for_selector("#directionTab", timeout=15000)
    page_b.click("#directionTab")
    page_b.wait_for_selector("#documentModeContent", timeout=15000)
    page_b.wait_for_function("() => !!navigator.serviceWorker.controller", timeout=15000)

    # The durable record itself (Cache Storage, never memory) is what proves
    # this survives a tab that never witnessed the switch -- or a worker
    # stopped and restarted, which reads this exact same record. A count of
    # what tab B's OWN (legitimately bob-authenticated) boot just synced would
    # prove nothing: that fetch runs under bob's cookie regardless.
    principal_from_b = page_b.evaluate(
        "async () => { const c = await caches.open('converge-principal-v1');"
        " const hit = await c.match('/__converge_principal__'); if (!hit) return null;"
        " const body = await hit.json(); return body.user; }"
    )
    print(f"\ntab B's own read of the durable principal record: {principal_from_b!r}")
    assert principal_from_b == "bob", (
        f"a second tab did not see tab A's confirmed switch to bob: {principal_from_b!r}"
    )
    assert not errors_a, f"tab A reported errors: {errors_a}"
    assert not _defects(errors_b), f"tab B reported errors: {_defects(errors_b)}"
    ctx.close()


# --------------------------------------------------------------------------
# 5. Offline immediately after a switch: the honest answer for the NEW
#    principal is "nothing synced yet", never the old principal's data.
# --------------------------------------------------------------------------


@needs_browser
def test_offline_right_after_a_switch_reads_nothing_of_the_previous_principal(server, project, browser):
    ctx, page, errors = _installed(browser, server, project, cookie_user="alice")
    page.evaluate(CONFIRM_VIA_REAL_BOOT)
    assert _synced_keys(page), "nothing was synced under alice, so this test cannot show it was cleared"

    _switch_cookie(ctx, project, "bob")
    switched = page.evaluate(CONFIRM_VIA_REAL_BOOT)
    assert switched["rejected"] is False, f"a legitimate boot-derived switch must resolve: {switched}"
    assert switched["ok"] and switched["user"] == "bob" and switched["cleared"] is True

    ctx.set_offline(True)
    answer = _boot_offline(page)
    print(f"\noffline /api/boot immediately after the switch to bob: {answer}")
    # \u00a710's honest-refusal shape, not alice's stale payload: nothing has
    # been synced under bob yet, so the worker must say so plainly rather
    # than serve alice's last confirmed boot response back as if it were his.
    assert answer["status"] != 200 or (answer["body"] or {}).get("offline") is True, (
        f"offline read after the switch did not honestly say nothing was synced yet: {answer}"
    )
    if answer["body"]:
        assert answer["body"].get("user") != "alice", f"a stale alice payload was served to bob: {answer}"
    ctx.set_offline(False)
    assert not _defects(errors), f"the browser reported errors: {_defects(errors)}"
    ctx.close()


# --------------------------------------------------------------------------
# 6. The in-flight race across a clear -- proved as a source fact.
#
# Staging "the worker's OWN /api/... fetch is slow, and a clear lands while
# it is still in flight" needs CDP-level interception of the Service
# Worker's own network requests; test_preview_pwa.py's own docstring already
# records that Playwright's page.route() here does not reach those. Proved
# structurally instead, same convention that file uses for its analogous gap.
# --------------------------------------------------------------------------


def test_the_epoch_guard_against_a_late_in_flight_response_exists_in_source() -> None:
    assert "async function currentEpoch()" in SW_TEXT
    assert "async function bumpEpoch()" in SW_TEXT
    assert "async function clearSyncedForNewEpoch()" in SW_TEXT, (
        "every identity-reason clear must bump the epoch, or a response already in flight "
        "when the clear happens could repopulate the cache the clear just emptied"
    )
    # Signature-agnostic on purpose: readApi() gained a `clientId` parameter
    # (converge-ex30) and this test is about the EPOCH guard in its body, not
    # about its argument list. Pinning the exact signature made a correct,
    # unrelated change look like a missing race guard.
    read_fn = re.search(r"async function readApi\([^)]*\) \{(.*?)\n\}", SW_TEXT, re.S)
    assert read_fn, "sw.js no longer has a readApi() function this test can read"
    body = read_fn.group(1)
    assert "const epoch = await currentEpoch();" in body, (
        "readApi() no longer captures the epoch before its own fetch -- the race guard is gone"
    )
    assert "(await currentEpoch()) === epoch" in body, (
        "readApi() no longer rechecks the epoch before writing to the cache -- "
        "a response overtaken by a clear could repopulate it"
    )
    for site in ("readApi", "writeApi"):
        fn = re.search(rf"async function {site}\([^)]*\) \{{(.*?)\n\}}", SW_TEXT, re.S)
        assert fn and "clearSyncedForNewEpoch()" in fn.group(1), (
            f"{site}() no longer bumps the epoch on a 401/403 -- a late in-flight answer for the "
            "session that just lost its cookie could still repopulate the cache"
        )


def test_the_offline_boot_receipt_is_guarded_in_source() -> None:
    """converge-ex30's receipt, read directly rather than taken on trust.

    `app/tests/test_afk_offline.py` proves the behaviour through a real
    transport outage. This is the structural half: the one path that may
    answer an unreachable identity check must be gated on all four checks,
    and it must never read the page's own claim.

    WHAT WOULD FALSIFY THIS: an `ok: true` reply on the unreachable branch
    that is not behind `provenPrincipalFor()`, a receipt kept in Cache
    Storage where it would outlive the worker, or a clear path that stops
    emptying it.
    """
    proof_fn = re.search(r"async function provenPrincipalFor\([^)]*\) \{(.*?)\n\}", SW_TEXT, re.S)
    assert proof_fn, "sw.js no longer has a provenPrincipalFor() this test can read"
    body = proof_fn.group(1)
    for needle, why in [
        ("bootProofs.get(clientId)", "the receipt is no longer keyed by the client it was earned by"),
        ("PROOF_TTL_MS", "the receipt no longer expires"),
        ("await storedPrincipal()", "the receipt is no longer matched against the durable principal"),
        ("proof.principal !== principal", "the receipt's owner is no longer compared"),
        ("await currentEpoch()) !== proof.epoch", "the receipt is no longer bound to its epoch"),
    ]:
        assert needle in body, why

    handler = re.search(
        r"if \(kind === 'converge-set-principal'\) \{(.*?)\n  \}\n\n  if \(kind", SW_TEXT, re.S
    )
    assert handler, "sw.js no longer has a converge-set-principal message handler this test can read"
    code = "\n".join(
        line for line in handler.group(1).splitlines() if not line.strip().startswith("//")
    )
    assert "const sourceId = (event.source && event.source.id) || '';" in code, (
        "the handler no longer takes the client id from the user agent's own stamp -- a page "
        "could name the client whose receipt it wants"
    )
    assert "await provenPrincipalFor(sourceId)" in code, (
        "the unreachable branch no longer consults the receipt by client id"
    )
    assert "offlineConfirmed: true" in code and code.index("const proven") < code.index("offlineConfirmed: true"), (
        "an offline confirmation is issued somewhere that is not behind the receipt check -- "
        "that is a universal boot-unreachable allow"
    )
    assert "user: proven" in code, (
        "the offline confirmation no longer reports the worker's OWN principal; anything else "
        "would be the page's claim answering for identity"
    )

    assert "const bootProofs = new Map()" in SW_TEXT, (
        "the receipt is no longer in memory only -- one kept in Cache Storage would outlive the "
        "worker restart that is meant to forget it"
    )
    clear_fn = re.search(r"async function clearSyncedForNewEpoch\(\) \{(.*?)\n\}", SW_TEXT, re.S)
    assert clear_fn and "forgetBootProofs();" in clear_fn.group(1), (
        "an identity-reason clear no longer empties the receipts it invalidates"
    )
    forget_fn = re.search(r"async function forgetPrincipal\(\) \{(.*?)\n\}", SW_TEXT, re.S)
    assert forget_fn and "forgetBootProofs();" in forget_fn.group(1), (
        "forgetting the principal no longer forgets the receipts that pointed at it"
    )


def test_a_page_message_is_never_treated_as_identity_in_source() -> None:
    """The structural fix, read directly: the message handler must derive
    `user` from `fetchBootIdentity()`'s own answer, never from `event.data`."""
    handler = re.search(
        r"if \(kind === 'converge-set-principal'\) \{(.*?)\n  \}\n\n  if \(kind", SW_TEXT, re.S
    )
    assert handler, "sw.js no longer has a converge-set-principal message handler this test can read"
    # Comments explaining the fix legitimately mention event.data.user in
    # prose; only CODE lines matter here.
    code_lines = "\n".join(
        line for line in handler.group(1).splitlines() if not line.strip().startswith("//")
    )
    assert "event.data.user" not in code_lines, (
        "the message handler reads event.data.user directly -- that is the exact seam the "
        "security review found: a page's own claim treated as identity"
    )
    body = handler.group(1)
    assert "fetchBootIdentity()" in body, (
        "the message handler no longer calls the worker's own server-verifying fetch"
    )
    assert "async function fetchBootIdentity()" in SW_TEXT
    boot_fn = re.search(r"async function fetchBootIdentity\(\) \{(.*?)\n\}", SW_TEXT, re.S)
    assert boot_fn and "fetch('/api/boot'" in boot_fn.group(1) and "credentials: 'same-origin'" in boot_fn.group(1), (
        "fetchBootIdentity() no longer makes its own credentialed same-origin request to /api/boot"
    )
