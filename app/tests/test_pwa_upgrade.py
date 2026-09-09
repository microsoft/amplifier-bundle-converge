"""converge-moe4 (contract platform-web.v1 \u00a79): an installed client's static
update must become real without slowing cached startup.

The gap this closes: a previously-installed browser kept executing a retired
renderer after the server had genuinely moved on and after two ordinary,
same-URL navigations -- proved on a real Mac install, not staged. Read-only
diagnosis on that evidence found two plausible mechanisms in `sw.js`'s
runtime-cache branch for `/static/*`:

  1. its `fetch(req)` runs in the request's own cache mode (ordinarily
     'default'), so it can be answered straight out of the browser's OWN
     HTTP cache -- a layer this worker never asked to be bypassed -- without
     ever reaching a server that has since changed;
  2. its Cache Storage `cache.put(...)` ran in a detached `.then()`, never
     kept alive by `event.waitUntil`, so a worker stopped between the
     network answering and the put landing drops the new bytes on the floor.

Both are proved here as REAL browser behaviour -- a real Chromium, a real
service worker, a real HTTP server on a real socket, and the browser's own
HTTP cache -- never a mocked `caches.put`/`caches.match` pair standing in for
either layer.

* `test_old_worker_keeps_serving_stale_static_after_two_ordinary_navigations`
  is the FAILING-BEFORE control: it runs the exact `sw.js` bytes committed at
  944a78d (this lane's own base, fetched from git history, never retyped)
  against a server that changes a same-URL static asset from OLD to NEW
  mid-test, and shows the worker still executes OLD after two ordinary
  reloads -- reproducing converge-moe4 rather than asserting it by
  description.
* `test_fixed_worker_adopts_new_static_without_slowing_cached_startup` runs
  the CURRENT (fixed) `app/static/sw.js` against the same harness and proves
  three things about the fix, in order: (a) a reload answers from the cached
  copy immediately even while the refresh this reload triggers is HELD,
  open, server-side -- so a slow network cannot slow a cached start; (b)
  releasing that hold is what lands the new bytes in Cache Storage, observed
  directly rather than assumed; (c) the very next ordinary reload -- no
  cache-busted URL, no forced reload, no storage clear -- executes NEW.

Both tests drive the same minimal fixture: a raw ASGI app serving a service
worker script at `/sw.js` (root scope, matching `app/serve.py`'s own mount),
one page that registers it, and one same-origin `/static/js/asset.js` file
whose body this fixture can flip between OLD and NEW between requests. It is
deliberately NOT the full `app.serve` application -- `sw.js`'s runtime-cache
branch has no dependency on anything else that app does, and a smaller
fixture keeps the held-response race legible. The asset is served with an
ETag (matching the parent's own CA-verified read of the real `collab.js`:
200, no Cache-Control, ETag present) and an explicit `Cache-Control:
max-age` so the same real browser mechanism -- an HTTP-cache entry the
browser itself still calls fresh -- reproduces deterministically rather than
depending on Chromium's internal heuristic-freshness constant, which this
test does not control and should not have to.
"""

from __future__ import annotations

import asyncio
import hashlib
import shutil
import socket as socketlib
import subprocess
import threading
import time
from pathlib import Path

import pytest

APP = Path(__file__).resolve().parents[1]
REPO_ROOT = APP.parent
BASE_REV = "944a78d"  # this lane's own base commit (GOAL.md) -- the pre-fix sw.js lives here, not retyped
SW_PATH_IN_REPO = "app/static/sw.js"


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


def _fixed_sw_source() -> str:
    """The CURRENT `app/static/sw.js` -- whatever this lane just wrote."""
    return (APP / "static" / "sw.js").read_text(encoding="utf-8")


def _base_sw_source() -> str:
    """The pre-fix `sw.js`, read from this lane's own named base commit
    (GOAL.md: "Base is private 944a78d") -- never retyped into this file,
    so the control can never silently drift from what the bug actually was."""
    out = subprocess.run(
        ["git", "show", f"{BASE_REV}:{SW_PATH_IN_REPO}"],
        cwd=str(REPO_ROOT), check=True, capture_output=True, text=True,
    )
    return out.stdout


def _free_port() -> int:
    s = socketlib.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


# --------------------------------------------------------------------------
# the fixture: one same-origin static asset this test can flip OLD -> NEW,
# and one gate that can hold the worker's own refresh of it mid-flight on a
# real threading.Event -- same convention test_preview_pwa_races.py uses for
# holding a request server-side rather than trying (and failing) to
# intercept a service worker's own fetch from the page side.
# --------------------------------------------------------------------------

OLD_BODY = b"window.__ASSET_VERSION = 'OLD';\n"
NEW_BODY = b"window.__ASSET_VERSION = 'NEW';\n"


class AssetState:
    def __init__(self) -> None:
        self.body = OLD_BODY

    def set_new(self) -> None:
        self.body = NEW_BODY

    def etag(self) -> str:
        return '"' + hashlib.sha256(self.body).hexdigest()[:16] + '"'


class RefreshGate:
    """Held OFF by default -- every ordinary request to the asset answers at
    once. `arm()` holds exactly the NEXT request to reach the fixture's
    asset route; `wait_reached()` proves it actually got there (left the
    worker, hit this server) before the test releases it."""

    def __init__(self) -> None:
        self.armed = False
        self.reached = threading.Event()
        self.release_flag = threading.Event()

    def arm(self) -> None:
        self.armed = True
        self.reached.clear()
        self.release_flag.clear()

    def release(self) -> None:
        self.release_flag.set()

    def wait_reached(self, timeout: float = 5.0) -> bool:
        return self.reached.wait(timeout=timeout)


INDEX_HTML = (
    "<!doctype html><html><head><meta charset=\"utf-8\"><title>pwa-upgrade fixture</title></head>"
    "<body>"
    "<script>"
    "window.__swReady = ('serviceWorker' in navigator)"
    "  ? navigator.serviceWorker.register('/sw.js').then(() => navigator.serviceWorker.ready)"
    "  : Promise.reject(new Error('no serviceWorker in this context'));"
    "</script>"
    "<script src=\"/static/js/asset.js\"></script>"
    "</body></html>"
)


class Fixture:
    """A raw ASGI app: `/` (the page above), `/sw.js` (whichever source this
    test hands it), and `/static/js/asset.js` (the flip-able, hold-able
    asset). Nothing else `sw.js`'s runtime-cache branch needs comes from
    anywhere but these three routes."""

    def __init__(self, sw_source: str, state: AssetState, gate: RefreshGate) -> None:
        self.sw_source = sw_source.encode("utf-8")
        self.state = state
        self.gate = gate

    async def __call__(self, scope, receive, send):
        if scope["type"] == "lifespan":
            while True:
                message = await receive()
                if message["type"] == "lifespan.startup":
                    await send({"type": "lifespan.startup.complete"})
                elif message["type"] == "lifespan.shutdown":
                    await send({"type": "lifespan.shutdown.complete"})
                    return
            return
        if scope["type"] != "http":
            return

        path = scope["path"]

        if path == "/":
            await self._respond(send, 200, INDEX_HTML.encode("utf-8"), "text/html; charset=utf-8")
            return

        if path == "/sw.js":
            await self._respond(send, 200, self.sw_source, "application/javascript")
            return

        if path == "/static/js/asset.js":
            if self.gate.armed:
                self.gate.armed = False  # one-shot: only the request this arms is held
                self.gate.reached.set()
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, self.gate.release_flag.wait)
            body = self.state.body
            # No Cache-Control here reproduces the parent's own CA-verified
            # read of the real asset (200, no Cache-Control, ETag present);
            # a fixed `max-age` on top of that makes the browser's own
            # heuristic-vs-explicit freshness distinction irrelevant to this
            # test -- either way the mechanism under test is the same request
            # answered out of the browser's HTTP cache without reaching here.
            headers = [
                (b"content-type", b"application/javascript"),
                (b"etag", self.state.etag().encode("ascii")),
                (b"cache-control", b"public, max-age=600"),
            ]
            await self._respond(send, 200, body, extra_headers=headers)
            return

        await self._respond(send, 404, b"not found", "text/plain")

    @staticmethod
    async def _respond(send, status, body, content_type=None, extra_headers=None):
        headers = list(extra_headers) if extra_headers else []
        if content_type is not None:
            headers.append((b"content-type", content_type.encode("ascii")))
        headers.append((b"content-length", str(len(body)).encode("ascii")))
        await send({"type": "http.response.start", "status": status, "headers": headers})
        await send({"type": "http.response.body", "body": body})


def _serve(sw_source: str, state: AssetState, gate: RefreshGate):
    import uvicorn

    app = Fixture(sw_source, state, gate)
    port = _free_port()
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.time() + 20
    while not server.started and time.time() < deadline:
        time.sleep(0.05)
    assert server.started, "fixture server did not start"
    return server, thread, f"http://127.0.0.1:{port}"


@pytest.fixture()
def browser():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        b = p.chromium.launch(args=["--no-sandbox"])
        yield b
        b.close()


def _defects(errors: list[str]) -> list[str]:
    # Neither fixture route here ever answers a page-driven request with a
    # non-2xx status, so unlike the other pwa test files' NARRATED_STATUS
    # filter there is nothing expected to narrate away -- any page error at
    # all is a real defect in this test's own harness or in sw.js.
    return list(errors)


def _asset_version(page) -> str:
    return page.evaluate("() => window.__ASSET_VERSION")


def _synced_static_body(page) -> str | None:
    return page.evaluate(
        "async () => {"
        " const c = await caches.open('converge-static-v4');"
        " const hit = await c.match('/static/js/asset.js');"
        " if (!hit) return null;"
        " return await hit.text();"
        "}"
    )


class Navigator:
    """One ordinary same-URL navigation per call -- a genuinely NEW page in
    the same browser context, not `page.reload()`.

    Measured directly against this fixture: Chromium's own per-frame memory
    cache can satisfy a reloaded `<script src>` without ever dispatching a
    `fetch` event to the service worker at all -- confirmed by instrumenting
    `sw.js` with a `console.log` at the top of the runtime-cache branch and
    seeing it fire once (the first load) and then NEVER AGAIN across several
    `page.reload()` calls, even though the asset's Cache-Control and this
    worker's own logic both say it should be asked again every time. A fresh
    `Page` for each navigation -- same origin, same context, so the Service
    Worker registration and Cache Storage it owns persist exactly as they
    would across real separate visits -- does not share that memory cache,
    so every navigation genuinely reaches the worker's `fetch` handler. This
    is closer to \"ordinary navigation\" than `reload()` turned out to be:
    the parent's own report was two ordinary visits to the same URL, not two
    in-place reloads of one already-open tab.
    """

    def __init__(self, ctx, url: str) -> None:
        self.ctx = ctx
        self.url = url
        self.errors: list[str] = []
        self.page = None

    def go(self):
        if self.page is not None:
            self.page.close()
        page = self.ctx.new_page()
        page.on("pageerror", lambda e: self.errors.append(f"pageerror: {e}"))
        page.goto(self.url, wait_until="load")
        self.page = page
        return page

    def close(self):
        if self.page is not None:
            self.page.close()
            self.page = None


def _open_and_wait_for_sw(browser, url: str):
    ctx = browser.new_context(viewport={"width": 1280, "height": 800})
    nav = Navigator(ctx, url)
    page = nav.go()
    page.evaluate("async () => { await window.__swReady; }")
    return ctx, nav


# --------------------------------------------------------------------------
# 1. failing-before control -- the bug, reproduced with the base commit's own
#    bytes, not asserted by description
# --------------------------------------------------------------------------


@needs_browser
def test_old_worker_keeps_serving_stale_static_after_two_ordinary_navigations(browser):
    state = AssetState()
    gate = RefreshGate()  # unused here -- the bug does not need a held response to show
    server, thread, url = _serve(_base_sw_source(), state, gate)
    try:
        ctx, nav = _open_and_wait_for_sw(browser, url)

        # First controlled navigation: no Cache Storage entry yet, so this
        # one populates STATIC with OLD via the runtime-cache branch.
        page = nav.go()
        page.wait_for_function("() => window.__ASSET_VERSION === 'OLD'", timeout=10000)
        assert _synced_static_body(page) == OLD_BODY.decode()

        # The server moves on -- a real, verified change, same URL.
        state.set_new()

        # Two ordinary, same-URL navigations -- exactly what the parent's
        # evidence named (GOAL.md). Each is a genuinely new visit (see
        # `Navigator`), not an in-place reload of the same tab.
        page = nav.go()
        first_after_change = _asset_version(page)
        page = nav.go()
        second_after_change = _asset_version(page)

        print(f"\n[control] first ordinary navigation after server change: {first_after_change}")
        print(f"[control] second ordinary navigation after server change: {second_after_change}")
        print(f"[control] STATIC cache body now: {_synced_static_body(page)!r}")

        assert first_after_change == "OLD", (
            "expected the pre-fix worker to reuse a fresh HTTP-cache entry on the first "
            f"ordinary navigation after the server changed; got {first_after_change!r} instead -- "
            "the control no longer reproduces converge-moe4"
        )
        assert second_after_change == "OLD", (
            "expected the pre-fix worker to still be serving the retired asset after TWO "
            f"ordinary navigations (the parent's own observation); got {second_after_change!r}"
        )
        assert _defects(nav.errors) == [], f"unexpected page errors during the control: {nav.errors}"

        nav.close()
        ctx.close()
    finally:
        server.should_exit = True
        thread.join(timeout=10)


# --------------------------------------------------------------------------
# 2. the fix -- held-response ordering, then eventual, ordinary adoption
# --------------------------------------------------------------------------


@needs_browser
def test_fixed_worker_adopts_new_static_without_slowing_cached_startup(browser):
    state = AssetState()
    gate = RefreshGate()
    server, thread, url = _serve(_fixed_sw_source(), state, gate)
    try:
        ctx, nav = _open_and_wait_for_sw(browser, url)

        # Populate STATIC with OLD, same as the control.
        page = nav.go()
        page.wait_for_function("() => window.__ASSET_VERSION === 'OLD'", timeout=10000)
        assert _synced_static_body(page) == OLD_BODY.decode()

        state.set_new()

        # Arm the gate: the NEXT request to the asset (this navigation's own
        # background refresh) will be held open, server-side, on a real
        # threading.Event -- not a mock, not a sleep.
        gate.arm()

        start = time.monotonic()
        page = nav.go()
        elapsed = time.monotonic() - start
        version_at_load = _asset_version(page)
        print(f"\n[fix] navigation completed in {elapsed:.3f}s while its own refresh is HELD open")
        print(f"[fix] cached code executed at load: {version_at_load}")

        # (a) the page must not have been made to wait on the held network
        # request for its own load to complete -- a cached hit answers a
        # navigation immediately; only the background refresh is held.
        assert version_at_load == "OLD", (
            f"expected the immediate cached response (OLD) while the refresh is held; got "
            f"{version_at_load!r} -- a hit must never wait on the network behind it"
        )
        assert elapsed < 5.0, (
            f"the page took {elapsed:.3f}s to load while its background refresh was held open -- "
            "slow networking must never become slow cached startup (platform-web.v1 \u00a79)"
        )

        reached = gate.wait_reached(timeout=5.0)
        assert reached, "the held request never reached the fixture server -- the refresh was never staged"
        print("[fix] the reload's own background refresh has reached the server, still held")

        # Cache Storage must still read OLD -- the fix must not have adopted
        # NEW before the network answer it depends on was ever released.
        assert _synced_static_body(page) == OLD_BODY.decode(), (
            "Cache Storage already reads NEW before the held refresh was released"
        )

        # NOW release it.
        gate.release()

        # Poll (event-driven, not a sleep) until the release's own effect --
        # the refresh landing in Cache Storage -- is actually observed.
        page.wait_for_function(
            "async () => {"
            " const c = await caches.open('converge-static-v4');"
            " const hit = await c.match('/static/js/asset.js');"
            " if (!hit) return false;"
            " const body = await hit.text();"
            " return body === \"window.__ASSET_VERSION = 'NEW';\\n\";"
            "}",
            timeout=10000,
        )
        landed = _synced_static_body(page)
        print(f"[fix] Cache Storage after releasing the held refresh: {landed!r}")
        assert landed == NEW_BODY.decode(), f"NEW never landed in Cache Storage after release: {landed!r}"

        # The next ORDINARY navigation -- no cache-busted URL, no forced
        # reload, no storage clear -- must now execute NEW.
        page = nav.go()
        next_version = _asset_version(page)
        print(f"[fix] next ordinary navigation executes: {next_version}")
        assert next_version == "NEW", f"the next ordinary navigation still executed {next_version!r}, not NEW"

        assert _defects(nav.errors) == [], f"unexpected page errors during the fix proof: {nav.errors}"

        nav.close()
        ctx.close()
    finally:
        server.should_exit = True
        thread.join(timeout=10)
