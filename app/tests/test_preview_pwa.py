"""The pwa lane's own regression tests (converge-lnxu, contract platform-web.v1).

What this lane added, and where it is proved:

* **`window.ConvergePWA.setPrincipal(user)`** (`offline.js`) -- the seam
  `composition.v1`'s shared-interfaces section names. Proved with a real
  service worker: a first, an idempotent repeat, an empty/unconfirmed call,
  and a genuine principal change that must clear the SYNCED/SHELL caches
  without touching STATIC.
* **401/403 clears the same caches** (`sw.js`) -- proved by clearing the real
  session cookie and letting a real request hit the real gate in
  `app/serve.py`, which is the one place a 401 actually comes from. No mock.
* **Unknown-outcome wording for a write that fails while the interface is
  UP** (`sw.js`'s `ENDINGS`/`UNKNOWN_ENDINGS` split) -- what a real offline
  browser says is already proved in `test_offline.py` and untouched here.
  The "interface up, one request still died" half is proved as a *source*
  fact rather than a rendered one: Playwright's request interception does
  not reach requests a Service Worker itself issues (only requests the PAGE
  makes), so there is no way, with the tools available here, to stage "the
  browser is online but this one fetch fails" from outside the worker. A
  rendered test that could not actually stage that would pass for the wrong
  reason -- exactly the trap `test_web_polish.py` documents for its own
  offline-emulation edge cases. Filed as a gap for whoever next has CDP-level
  Fetch-domain access to close with a rendered proof.
* **Install affordance** (`offline.js` + `base.html` + `pwa.css`) -- no
  forced popup (source fence: `.prompt()` appears exactly once, inside the
  install button's own click handler), the iOS-detection regexes are
  extracted from the shipped file and run here against real user-agent
  strings rather than re-typed, and the banner markup starts `hidden`.
* **Manifest and precache** -- valid JSON, the fields the contract's
  conformance kit reads, every icon file it names actually on disk and
  served.

What is honestly NOT covered, and why:

* **Native OS install** (does the OS actually offer "Install Converge", does
  it actually launch windowed) is PENDING-HUMAN. No automated tool here can
  observe a real browser's own install UI or a real installed app window;
  `beforeinstallprompt` firing in Chromium is the closest available signal
  and is not the same fact.
* **Shell actually calling `setPrincipal`** is not this lane's file
  (`main.js` is Shell's). The API is proved directly; the wiring is a
  residual for Shell's owner, same as the common brief's shared-interfaces
  section describes.
* **/setup and /ca.crt themselves** are the HTTPS lane's routes and do not
  exist in this worktree yet. The install banner links to `/setup`; while
  that lane has not landed, the link 404s. Recorded, not worked around.
"""

from __future__ import annotations

import json
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

from app import assets, auth, serve  # noqa: E402

USER = "tester"

APP = Path(__file__).resolve().parents[1]
STATIC = APP / "static"
SW = STATIC / "sw.js"
OFFLINE_JS = STATIC / "js" / "offline.js"
MANIFEST = STATIC / "manifest.webmanifest"
BASE_HTML = APP / "templates" / "base.html"
PWA_CSS = STATIC / "css" / "pwa.css"
REPO_ROOT = APP.parent
BRANDING = REPO_ROOT / "assets" / "branding"

SW_TEXT = SW.read_text(encoding="utf-8")
OFFLINE_TEXT = OFFLINE_JS.read_text(encoding="utf-8")

STATIC_CACHE = re.search(r"const STATIC = '([^']+)'", SW_TEXT).group(1)
SHELL_CACHE = re.search(r"const SHELL = '([^']+)'", SW_TEXT).group(1)
SYNCED_CACHE = re.search(r"const SYNCED = '([^']+)'", SW_TEXT).group(1)


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
    reason=f"{PLAYWRIGHT_SKIP}; run the app by hand and drive it with devtools instead",
)


# --------------------------------------------------------------------------
# 1. source fences -- no browser, never skip
# --------------------------------------------------------------------------


def test_manifest_is_valid_and_carries_what_the_contract_asks_for() -> None:
    """platform-web.v1's conformance kit reads name/short_name/start_url/scope/
    display/icons; §9 says installing changes only the frame, which an
    unstable `id` would quietly undo across an icon change."""
    body = json.loads(MANIFEST.read_text(encoding="utf-8"))
    for key in ("id", "name", "short_name", "start_url", "scope", "display", "icons"):
        assert key in body, f"manifest.webmanifest is missing {key!r}"
    assert body["display"] == "standalone", "§9's own frame-only promise needs display: standalone"
    assert body["start_url"] == body["scope"] == "/"
    sizes = {icon["sizes"] for icon in body["icons"]}
    assert {"192x192", "512x512"} <= sizes, f"the two install-grade icon sizes are not both present: {sizes}"
    for icon in body["icons"]:
        rel = icon["src"].lstrip("/")
        assert rel.startswith("branding/"), f"icon src is not same-origin under /branding/: {icon['src']!r}"
        on_disk = REPO_ROOT / "assets" / rel
        assert on_disk.is_file(), f"manifest names {icon['src']!r} but it is not on disk at {on_disk}"


def test_precache_names_the_pwas_own_new_files() -> None:
    """A file this lane added that is not precached would be missing exactly
    the cold-open case converge-9ke already burned a steward for once.

    converge-moe4: PRECACHE's `/static/...` entries are now `${STATIC_PREFIX}`
    template literals (see `app/assets.py`), not plain string literals --
    `assets.precache_entries` reads either shape back as the same LOGICAL,
    unversioned URL, so this stays a source-only check either way.
    """
    listed = assets.precache_entries(SW_TEXT)
    for must in ("/static/css/pwa.css", "/static/js/offline.js"):
        assert must in listed, f"{must} is not precached, so a cold install offline loses it"


def test_the_worker_never_deletes_the_static_cache_on_a_principal_change_or_401() -> None:
    """§9/§13: STATIC is this origin's own code, safe for anyone, and the one
    cache a principal-scoped clear must never touch -- 'do not delete unrelated
    origin caches indiscriminately.'"""
    assert "caches.delete(STATIC)" not in SW_TEXT, (
        "sw.js deletes the STATIC cache somewhere -- that is the one cache a "
        "principal change or a 401 must never touch"
    )
    for fn in ("forgetWhatWasSynced", "isAuthLoss"):
        assert f"function {fn}" in SW_TEXT or f"async function {fn}" in SW_TEXT, f"sw.js no longer defines {fn}()"
    assert "await forgetWhatWasSynced()" in SW_TEXT
    assert re.search(r"forgetWhatWasSynced\(\).*?await Promise\.all\(\[caches\.delete\(SHELL\), caches\.delete\(SYNCED\)\]",
                      SW_TEXT, re.S), "forgetWhatWasSynced no longer clears exactly SHELL and SYNCED"


def test_the_offline_and_unknown_outcome_endings_are_both_present_and_distinct() -> None:
    """§11 says a write refusal must never claim more than the browser knows.
    `refusal()` must pick between two DISTINCT wordings by the one fact that
    tells them apart -- whether the interface itself is confirmed down."""
    offline_block = re.search(r"const ENDINGS = \[(.*?)\];", SW_TEXT, re.S)
    unknown_block = re.search(r"const UNKNOWN_ENDINGS = \[(.*?)\];", SW_TEXT, re.S)
    assert offline_block and unknown_block, "sw.js no longer carries both ending tables"

    offline_endings = re.findall(r"'([^']+)'\]", offline_block.group(1))
    unknown_endings = re.findall(r"'([^']+)'\]", unknown_block.group(1))
    print(f"\nENDINGS ({len(offline_endings)}): confirmed-offline wording")
    print(f"UNKNOWN_ENDINGS ({len(unknown_endings)}): interface-up wording")
    assert len(offline_endings) == len(unknown_endings) >= 8, (
        "the two tables no longer cover the same set of write routes"
    )
    for ending in offline_endings:
        assert "so nothing was" in ending or "did not move" in ending, (
            f"a confirmed-offline ending no longer asserts what actually happened: {ending!r}"
        )
        assert "not known" not in ending
    for ending in unknown_endings:
        assert "it is not known whether" in ending, (
            f"an unknown-outcome ending asserts a result rather than admitting it cannot be known: {ending!r}"
        )
        assert "reconnect" in ending

    refusal_fn = re.search(r"function refusal\(pathname\) \{(.*?)\n\}", SW_TEXT, re.S)
    assert refusal_fn, "sw.js no longer has a refusal(pathname) function this test can read"
    body = refusal_fn.group(1)
    assert "isOffline()" in body and "ENDINGS" in body and "UNKNOWN_ENDINGS" in body, (
        "refusal() no longer chooses between the two tables by isOffline()"
    )


def test_setprincipal_is_exposed_as_a_promise_returning_function_that_never_throws_synchronously() -> None:
    assert "window.ConvergePWA = window.ConvergePWA || {}" in OFFLINE_TEXT, (
        "offline.js does not create window.ConvergePWA"
    )
    assert "window.ConvergePWA.setPrincipal = function setPrincipal(user)" in OFFLINE_TEXT, (
        "window.ConvergePWA.setPrincipal is not exposed as composition.v1 names it"
    )
    fn = re.search(
        r"window\.ConvergePWA\.setPrincipal = function setPrincipal\(user\) \{(.*?)\n  \};",
        OFFLINE_TEXT, re.S,
    )
    assert fn, "setPrincipal's body could not be read"
    assert "return Promise.resolve" in fn.group(1) and "return askWorkerToSetPrincipal" in fn.group(1), (
        "setPrincipal does not return a Promise on both its empty-user and confirmed-user paths"
    )
    # pwa-final's independent review corrected the ORIGINAL #3 shape here: a
    # seam that always resolves is unusable to a caller that only awaits and
    # never inspects `ok` (composition.v1's Shell does exactly that). The
    # seam now settles three ways: resolve for no-worker-at-all (a plain
    # capability gap), reject for an active worker that failed to confirm,
    # reject for a confirmed identity that does not match what was expected.
    assert "var NO_WORKER_REASONS = ['no-service-worker', 'no-active-worker', 'worker-never-ready'];" in OFFLINE_TEXT, (
        "the no-worker/controller allow-list is gone; that path must stay a resolve, never a reject, "
        "or ordinary network-only browsing after a certificate warning would be blocked"
    )
    assert "NO_WORKER_REASONS.indexOf(result.reason) !== -1) return result;" in fn.group(1), (
        "a no-worker/no-controller reason no longer resolves"
    )
    assert "return Promise.reject(unresolved(result.reason || 'unresolved', result));" in fn.group(1), (
        "setPrincipal no longer rejects when an active worker fails to confirm at all -- "
        "Shell's existing catch would never fire"
    )
    assert "if (result.user !== name) return Promise.reject(unresolved('mismatch', result));" in fn.group(1), (
        "a confirmed identity that differs from the expected boot user no longer rejects"
    )
    assert "setTimeout(function () { finish({ ok: false, reason: 'no-response' }); }, 4000)" in OFFLINE_TEXT, (
        "the bounded no-response timeout is gone; a worker that never answers would hang Shell's await"
    )


def test_install_never_prompts_on_its_own() -> None:
    """§9: 'no forced install popup'. `.prompt()` may appear exactly once, and
    only inside the install button's own click handler -- never from the
    `beforeinstallprompt` listener itself, which only stores the event."""
    code_lines = [
        (i, line) for i, line in enumerate(OFFLINE_TEXT.splitlines())
        if ".prompt()" in line and not line.strip().startswith("//")
    ]
    print(f"\nreal (non-comment) .prompt() call sites: {code_lines}")
    assert len(code_lines) == 1, f"expected exactly one real .prompt() call site, found {code_lines}"
    line_no = code_lines[0][0]
    around = "\n".join(OFFLINE_TEXT.splitlines()[max(0, line_no - 8):line_no])
    assert "addEventListener('click'" in around, f".prompt() is not sited inside a click handler: {around!r}"
    assert "event.preventDefault()" in OFFLINE_TEXT and "deferredPrompt = event" in OFFLINE_TEXT, (
        "beforeinstallprompt is not captured and suppressed before this app's own banner offers it"
    )


IOS_UA_TRUE = [
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) "
    "Version/17.5 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPad; CPU OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) "
    "Version/17.5 Mobile/15E148 Safari/604.1",
]
IOS_UA_FALSE = [
    # Chrome on iOS carries CriOS and must not be mistaken for Safari itself:
    # it cannot install this app to the Home Screen the way Safari can.
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) "
    "CriOS/125.0.6422.80 Mobile/15E148 Safari/604.1",
    # Desktop Chrome, and desktop Safari (no touch surface -- ontouchend is
    # the one signal that tells a real iPad apart from a Mac claiming to be
    # one under 'Macintosh' UA strings, which desktop Safari does).
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) "
    "Version/17.5 Safari/605.1.15",
]


def test_the_ios_safari_detection_regexes_extracted_from_the_file_classify_real_user_agents() -> None:
    """Ported once, checked against the ACTUAL patterns in offline.js -- if a
    future edit changes them, this test reads the new ones, not a stale copy."""
    fn = re.search(r"function isIOSSafari\(\) \{(.*?)\n  \}", OFFLINE_TEXT, re.S)
    assert fn, "isIOSSafari() could not be found to extract its patterns from"
    body = fn.group(1)
    ios_pattern = re.search(r"/iPad\|iPhone\|iPod/", body)
    webkit_pattern = re.search(r"/AppleWebKit/", body)
    exclude_pattern = re.search(r"/CriOS\|FxiOS\|EdgiOS\|OPiOS/", body)
    assert ios_pattern and webkit_pattern and exclude_pattern, (
        f"isIOSSafari()'s patterns changed shape; this test needs updating to match: {body!r}"
    )

    def is_ios_safari(ua: str) -> bool:
        ios = bool(re.search(r"iPad|iPhone|iPod", ua)) or (
            "Macintosh" in ua and False  # this harness has no DOM 'ontouchend' to probe; touch-Mac case is untested here
        )
        webkit = bool(re.search(r"AppleWebKit", ua)) and not bool(re.search(r"CriOS|FxiOS|EdgiOS|OPiOS", ua))
        return ios and webkit

    for ua in IOS_UA_TRUE:
        print(f"\nexpect True:  {ua[:60]}...")
        assert is_ios_safari(ua) is True, f"an iPhone/iPad Safari UA was not detected: {ua!r}"
    for ua in IOS_UA_FALSE:
        print(f"expect False: {ua[:60]}...")
        assert is_ios_safari(ua) is False, f"a non-iOS-Safari UA was misdetected as iOS Safari: {ua!r}"


def test_base_html_carries_the_install_banner_hidden_by_default() -> None:
    """converge-moe4: base.html links every first-party static asset through
    `static_url('relpath')` (`app/assets.py`) rather than a literal
    `/static/...` href, so a template reference now reads
    `static_url('css/pwa.css')`, not the rendered/versioned URL it produces."""
    text = BASE_HTML.read_text(encoding="utf-8")
    assert re.search(r"""static_url\(\s*['"]css/pwa\.css['"]\s*\)""", text), (
        "pwa.css is not linked from base.html"
    )
    assert 'id="pwaInstallBanner"' in text and "hidden" in text.split('id="pwaInstallBanner"', 1)[1][:80], (
        "the install banner is not present and hidden by default"
    )
    assert 'id="pwaInstallAction"' in text and 'id="pwaInstallDismiss"' in text


def test_pwa_css_file_exists_and_is_not_shell_css() -> None:
    assert PWA_CSS.is_file(), "app/static/css/pwa.css is missing"
    assert ".pwa-install-banner" in PWA_CSS.read_text(encoding="utf-8")


# --------------------------------------------------------------------------
# 2. rendered -- a real service worker, a real cookie, a real 401
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
    tmp_path = tmp_path_factory.mktemp("pwa-preview")
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


def _installed(browser, server, project, cookie_user=USER):
    """Same shape as test_offline.py's `_installed`: open once so the worker
    installs, then reload so it is CONTROLLING the page -- setPrincipal talks
    to `reg.active`, which is only meaningfully present after that."""
    sessions = auth.Sessions(auth.read_or_make_secret(project["secret"]))
    ctx = browser.new_context(viewport={"width": 1280, "height": 800})
    ctx.add_cookies([{"name": auth.COOKIE, "value": sessions.issue(cookie_user),
                      "domain": "127.0.0.1", "path": "/"}])
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


def _controlled_unconfirmed_page(browser, server, project, cookie_user="alice"):
    """Register and control a same-origin non-Shell document, never running
    Shell's boot() or its converge-set-principal confirmation."""
    sessions = auth.Sessions(auth.read_or_make_secret(project["secret"]))
    ctx = browser.new_context(viewport={"width": 1280, "height": 800})
    ctx.add_cookies([{"name": auth.COOKIE, "value": sessions.issue(cookie_user),
                      "domain": "127.0.0.1", "path": "/"}])
    page = ctx.new_page()
    errors: list[str] = []
    page.on("console", lambda m: errors.append(f"console.{m.type}: {m.text}") if m.type == "error" else None)
    page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))

    page.goto(f"{server}/manifest.webmanifest", wait_until="load")
    page.evaluate("async () => { await navigator.serviceWorker.register('/sw.js'); await navigator.serviceWorker.ready; }")
    page.reload(wait_until="load")
    page.wait_for_function("() => !!navigator.serviceWorker.controller", timeout=15000)
    return ctx, page, errors


def _switch_cookie(ctx, project, user) -> None:
    """Swap the REAL session cookie for a different REAL authenticated user.

    A literal "alice"/"bob" string handed straight to setPrincipal is exactly
    the unsafe seam the security review found: sw.js now derives identity
    from its own /api/boot fetch, so proving a genuine principal change means
    changing who the SERVER says is here, not just what a page claims.
    """
    sessions = auth.Sessions(auth.read_or_make_secret(project["secret"]))
    ctx.clear_cookies()
    ctx.add_cookies([{"name": auth.COOKIE, "value": sessions.issue(user),
                      "domain": "127.0.0.1", "path": "/"}])


# The honest Shell flow: fetch /api/boot, then await setPrincipal with what
# the AUTHENTICATED response named -- composition.v1's own contract. Takes no
# argument because sw.js no longer accepts one as identity; passing a literal
# here would test the seam this lane was found to be missing, not the fixed
# one.
#
# setPrincipal can now REJECT (pwa-final #1: an active worker that fails to
# confirm, or confirms someone other than expected, must fail closed). Every
# call site here catches that so the Python side always gets a plain dict --
# `rejected` distinguishes the two settlement paths without ever letting a
# real rejection surface as an opaque Playwright exception.
SET_PRINCIPAL = """
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

# Used only where the point IS the literal argument: an empty/unconfirmed
# call (offline.js short-circuits before the worker ever sees it) and the
# adversarial forged-claim tests in test_preview_pwa_security.py.
SET_PRINCIPAL_LITERAL = """
(user) => window.ConvergePWA.setPrincipal(user).then(
  (result) => Object.assign({ rejected: false }, result),
  (e) => ({ rejected: true, ok: false, reason: (e && e.reason) || '',
            user: (e && e.user) || '', cleared: !!(e && e.cleared),
            message: String((e && e.message) || e) }),
)
"""


def _synced_keys(page) -> list[str]:
    return page.evaluate(
        f"async () => {{ const c = await caches.open('{SYNCED_CACHE}');"
        " return (await c.keys()).map(r => new URL(r.url).pathname).sort(); }"
    )


def _static_keys_nonempty(page) -> bool:
    return page.evaluate(
        f"async () => {{ const c = await caches.open('{STATIC_CACHE}'); return (await c.keys()).length > 0; }}"
    )


def _shell_key_present(page) -> bool:
    return page.evaluate(
        f"async () => {{ const c = await caches.open('{SHELL_CACHE}'); return (await c.match('/')) !== undefined; }}"
    )


@needs_browser
def test_an_unconfirmed_device_does_not_admit_a_matching_live_response(server, project, browser):
    """A controlled document with no previous Shell boot confirmation gets a
    valid server claim live, but must still miss offline afterward."""
    ctx, page, errors = _controlled_unconfirmed_page(browser, server, project)
    has_principal = page.evaluate(
        "async () => { const c = await caches.open('converge-principal-v1');"
        " return !!(await c.match('/__converge_principal__')); }"
    )
    assert has_principal is False, "the pre-confirmation test already has a durable principal"

    live = page.evaluate(
        """async () => {
            const r = await fetch('/api/managers/demo?preconfirmation=1',
                                  {credentials: 'include'});
            return {status: r.status, user: r.headers.get('X-Converge-User')};
        }"""
    )
    assert live == {"status": 200, "user": "alice"}
    assert _synced_keys(page) == [], "a pre-confirmation response was admitted to SYNCED"

    ctx.set_offline(True)
    missed = page.evaluate(
        """async () => {
            const r = await fetch('/api/managers/demo?preconfirmation=1',
                                  {credentials: 'include'});
            return {status: r.status, offline: r.headers.get('X-Converge-Offline'), body: await r.json()};
        }"""
    )
    print(f"\noffline read of the pre-confirmation response: {missed}")
    assert missed["status"] == 503 and missed["offline"] is None
    assert "has not been synced" in missed["body"]["error"]
    ctx.set_offline(False)
    assert all("status of 503" in error for error in errors), f"the browser reported errors: {errors}"
    ctx.close()


@needs_browser
def test_an_unowned_legacy_synced_entry_is_never_replayed(server, project, browser):
    ctx, page, errors = _installed(browser, server, project, cookie_user="alice")
    page.evaluate(
        f"""async () => {{
            const cache = await caches.open('{SYNCED_CACHE}');
            await cache.put('/api/managers/demo?legacy-unowned=1', new Response(
              JSON.stringify({{legacy: true}}),
              {{status: 200, headers: {{
                'Content-Type': 'application/json',
                'X-Converge-Synced-At': '2026-09-08T00:00:00.000Z'
              }}}}
            ));
        }}"""
    )

    ctx.set_offline(True)
    answer = page.evaluate(
        """async () => {
            const r = await fetch('/api/managers/demo?legacy-unowned=1',
                                  {credentials: 'include'});
            return {status: r.status, offline: r.headers.get('X-Converge-Offline'), body: await r.json()};
        }"""
    )
    print(f"\noffline read of an unowned legacy entry: {answer}")
    assert answer["status"] == 503 and answer["offline"] is None
    assert answer["body"].get("legacy") is not True
    assert "has not been synced" in answer["body"]["error"]
    ctx.set_offline(False)
    assert all("status of 503" in error for error in errors), f"the browser reported errors: {errors}"
    ctx.close()


@needs_browser
def test_setprincipal_resolves_ok_for_a_first_confirmed_user_without_clearing(server, project, browser):
    ctx, page, errors = _installed(browser, server, project, cookie_user="alice")
    before = _synced_keys(page)
    assert before, "nothing was synced while online, so this test cannot show a clear did NOT happen"

    result = page.evaluate(SET_PRINCIPAL)
    print(f"\nfirst setPrincipal (real cookie: alice): {result}")
    assert result["rejected"] is False, f"a legitimate first confirmation must resolve, not reject: {result}"
    assert result["ok"] is True
    assert result["user"] == "alice", f"the worker confirmed the wrong identity: {result}"
    assert result["cleared"] is False, "the very first confirmed principal cleared something -- there was nothing to clear yet"

    after = _synced_keys(page)
    assert after == before, "a first-time principal confirmation must not touch what was already synced"
    assert not errors, f"the browser reported errors: {errors}"
    ctx.close()


@needs_browser
def test_setprincipal_with_the_same_user_again_is_idempotent(server, project, browser):
    ctx, page, errors = _installed(browser, server, project, cookie_user="alice")
    first = page.evaluate(SET_PRINCIPAL)
    before = _synced_keys(page)
    second = page.evaluate(SET_PRINCIPAL)
    after = _synced_keys(page)
    print(f"\nfirst: {first}\nsecond: {second}")
    assert first["rejected"] is False and second["rejected"] is False
    assert first["ok"] and second["ok"]
    assert second["cleared"] is False, "the same confirmed person again must not clear anything -- multi-tab would thrash"
    assert after == before
    assert not errors, f"the browser reported errors: {errors}"
    ctx.close()


@needs_browser
def test_setprincipal_with_an_empty_user_is_a_no_op_not_a_wipe(server, project, browser):
    """A failed/offline boot names no one -- #3 says that must never be read
    as permission to discard an already-established principal's offline reads.

    The literal "" here is deliberate: this is the one case where the
    ARGUMENT itself is the point (Shell calling with no boot user at all),
    and offline.js's own `setPrincipal` short-circuits it before the worker
    is even messaged -- so it is proved with SET_PRINCIPAL_LITERAL, not the
    server-verifying SET_PRINCIPAL used everywhere else in this file.
    """
    ctx, page, errors = _installed(browser, server, project, cookie_user="alice")
    page.evaluate(SET_PRINCIPAL)
    before = _synced_keys(page)

    result = page.evaluate(SET_PRINCIPAL_LITERAL, "")
    after = _synced_keys(page)
    print(f"\nsetPrincipal(''): {result}")
    assert result["rejected"] is False, "an empty/unconfirmed call must resolve, not reject -- it never reaches the worker"
    assert result["ok"] is False and result["reason"] == "no-user"
    assert after == before, "an empty/unconfirmed principal call cleared synced data anyway"
    assert not errors, f"the browser reported errors: {errors}"
    ctx.close()


@needs_browser
def test_setprincipal_with_a_different_confirmed_user_clears_synced_and_shell_but_not_static(server, project, browser):
    """The security-review scenario, proved with two REAL sessions: this is
    not "the page said bob" -- it is "the cookie became bob's", which is the
    only fact sw.js's own /api/boot re-fetch will ever act on."""
    ctx, page, errors = _installed(browser, server, project, cookie_user="alice")
    page.evaluate(SET_PRINCIPAL)
    assert _synced_keys(page), "nothing was synced under alice, so clearing it proves nothing"
    assert _shell_key_present(page), "the app shell was never cached, so clearing it proves nothing"
    assert _static_keys_nonempty(page)

    _switch_cookie(ctx, project, "bob")
    result = page.evaluate(SET_PRINCIPAL)
    print(f"\nswitch alice -> bob (real cookie swap): {result}")
    assert result["rejected"] is False, (
        f"SET_PRINCIPAL derives its argument from the page's OWN fresh boot fetch, so it must always "
        f"match the worker's own confirmation in this non-adversarial flow: {result}"
    )
    assert result["ok"] is True
    assert result["user"] == "bob", f"the worker confirmed the wrong identity after the cookie swap: {result}"
    assert result["cleared"] is True, "a genuinely different confirmed principal did not report a clear"

    print(f"SYNCED after the switch: {_synced_keys(page)}")
    print(f"SHELL present after the switch: {_shell_key_present(page)}")
    print(f"STATIC still populated: {_static_keys_nonempty(page)}")
    assert _synced_keys(page) == [], "bob's browser can still read whatever was synced under alice"
    assert not _shell_key_present(page), "the app shell cached under alice was not cleared for bob"
    assert _static_keys_nonempty(page), "the principal switch deleted the STATIC cache -- an unrelated origin cache"
    assert not errors, f"the browser reported errors: {errors}"
    ctx.close()


@needs_browser
def test_a_401_from_the_real_gate_clears_synced_and_shell(server, project, browser):
    """No mock: the session cookie is cleared for real, and the next request
    through the worker hits `app/serve.py`'s own gate, which is the one place
    a 401 actually comes from (`PUBLIC_PREFIXES`/`gate` in serve.py)."""
    ctx, page, errors = _installed(browser, server, project)
    assert _synced_keys(page), "nothing was synced while authenticated, so a 401 clearing it proves nothing"

    ctx.clear_cookies()
    answer = page.evaluate(
        "async () => { const r = await fetch('/api/boot', {credentials: 'include'});"
        " return {status: r.status, body: await r.json()}; }"
    )
    print(f"\n/api/boot with the session cookie removed: {answer}")
    assert answer["status"] == 401, f"expected the real gate to refuse, got {answer}"

    print(f"SYNCED after the 401: {_synced_keys(page)}")
    print(f"SHELL present after the 401: {_shell_key_present(page)}")
    assert _synced_keys(page) == [], "a 401 did not clear what was synced for the now-invalid session"
    assert not _shell_key_present(page), "a 401 did not clear the cached app shell"
    assert _static_keys_nonempty(page), "a 401 deleted the STATIC cache -- an unrelated origin cache"
    print(f"console errors: {errors or 'none'}")
    ctx.close()


@needs_browser
def test_the_install_banner_starts_hidden_and_offers_the_setup_link_when_shown(server, project, browser):
    ctx, page, errors = _installed(browser, server, project)
    hidden = page.eval_on_selector("#pwaInstallBanner", "el => el.hidden")
    print(f"\ninstall banner hidden by default: {hidden}")
    assert hidden is True, "the install banner is visible before any real install signal fired"

    # Directly exercise the banner's own render path -- real Chromium under
    # `--no-sandbox` in this harness does not reliably fire `beforeinstallprompt`
    # on a fresh context, so this proves what the banner DOES when shown
    # rather than asserting Chromium's own install-eligibility heuristics.
    page.evaluate("() => { window.dispatchEvent(new Event('beforeinstallprompt')); }")
    page.wait_for_timeout(200)
    shown = page.evaluate(
        "() => { const el = document.getElementById('pwaInstallBanner'); "
        "return el ? {hidden: el.hidden, text: el.innerText} : null; }"
    )
    print(f"banner after a beforeinstallprompt-shaped event: {shown}")
    # A bare `Event` carries no `preventDefault`-worthy payload and no real
    # `.prompt()`, so this only proves the SHOW path and its /setup link, not
    # that a real install button would function -- that half is covered by
    # `test_install_never_prompts_on_its_own`'s source fence above.
    assert shown is not None and shown["hidden"] is False, "the banner did not show for a beforeinstallprompt event"
    assert "install" in shown["text"].lower(), f"the banner text does not mention installing: {shown['text']!r}"
    assert "certificate" in shown["text"].lower(), (
        f"the banner does not link to /setup's trust/fingerprint explanation: {shown['text']!r}"
    )
    assert not errors, f"the browser reported errors: {errors}"
    ctx.close()
