"""A REAL transport outage, and what the app may still read through it.

`platform-web.v1` §10 asks that with the network down the app reads what it
last synced and says when that was. `app/tests/test_offline.py` proves that
with Chromium's own emulated offline state, which is the right instrument for
the banner and the refusal sentences -- but it is not proof of an outage. A
service worker's own `fetch()` is not always subject to that emulation, and the
one thing this file exists to check happens exactly there: the worker's
network-only /api/boot confirmation (converge-ex30).

So here the network is taken away for real. Each scenario owns a real HTTPS
listener -- its own local CA and leaf, its own uvicorn TLS socket on its own
ephemeral port, nothing shared and nothing of anyone else's touched -- warms
identity-bound data through it, then STOPS that listener and proves with a
plain socket connection that the transport is genuinely gone before asking the
browser anything. A window offline flag is still set afterwards, because the
banner's wording is a UI fact and §10 asks for it; it is never what makes the
outage true here.

What is being proved, in the app's own terms:

  1. After the outage, the same controlled client reloads, chooses a manager
     from Home, opens Direction and Operation, and reads what it last synced
     with a visible "as of <time>". Home-first is the app's rule offline as
     well as online -- nothing restores the selection a reload dropped.
  2. The receipt that makes this possible answers for exactly one client, one
     owner and one epoch. A page asking under another name, a device whose
     durable principal is gone, a bumped epoch, and a client that never read a
     validated cached boot at all are each refused -- separately, and each for
     its own reason.
  3. The receipt does not transfer between clients of the SAME browser
     profile: a second controlled document that never read a validated cached
     /api/boot is refused while the first client's receipt is alive and its
     cache untouched, and is allowed only once it has read its own.
  4. Writes are refused throughout, and reconnecting restores live answers.

Nothing here is skipped when a browser is unavailable: the reason is printed
and the tests skip, exactly as the rest of the suite does, and the run that
counts is the one whose output shows them passing.
"""

from __future__ import annotations

import base64
import hashlib
import http.client
import shutil
import socket as socketlib
import ssl
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app import auth, serve, tls  # noqa: E402

USER = "tester"
OTHER_USER = "someone-else"


# --------------------------------------------------------------------------
# availability -- print the reason rather than silently vanishing
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
needs_browser = pytest.mark.skipif(bool(PLAYWRIGHT_SKIP), reason=PLAYWRIGHT_SKIP)


# --------------------------------------------------------------------------
# a project to serve
# --------------------------------------------------------------------------

VISION = """# Demo Vision (DRAFT)

## Where this is going

One place for direction and one place for operation.
"""

MANIFEST_HEAD = "lane\tworktree\tbranch\tbase\ttmux\tgoal\tlog\tstarted\n"


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "user.name=Test", "-c", "user.email=test@example.invalid", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )


@pytest.fixture(scope="module")
def project(tmp_path_factory) -> dict:
    """A real repository with real history -- never fixtures of the answers."""
    tmp_path = tmp_path_factory.mktemp("afk-offline")
    repo = tmp_path / "demo-repo"
    (repo / "docs").mkdir(parents=True)
    (repo / "docs" / "VISION.md").write_text(VISION, encoding="utf-8")
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "seed: the vision")

    batch = tmp_path / "hw-demo"
    (batch / "lanes" / "w1-alpha").mkdir(parents=True)
    (batch / "goals").mkdir()
    (batch / "HIGHWAY.md").write_text("# Highway — demo\n\nWidth 2.\n", encoding="utf-8")
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
    return {"root": tmp_path, "config": conf, "repo": repo}


# --------------------------------------------------------------------------
# one scenario's own HTTPS listener
# --------------------------------------------------------------------------


def _free_port() -> int:
    s = socketlib.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def _spki_sha256_b64(cert_path: Path) -> str:
    """The exact pin `--ignore-certificate-errors-spki-list` wants.

    Pinning ONE leaf's public key -- rather than Playwright's blanket
    `ignore_https_errors`, which stops verifying certificates for every
    connection the browser makes -- keeps the exception as narrow as the run.
    No OS trust store is touched. It also matters for what follows: a page
    served over a certificate the browser merely tolerated is not a secure
    context, and a service worker would never register on it at all.
    """
    from cryptography import x509
    from cryptography.hazmat.primitives import serialization

    cert = x509.load_pem_x509_certificate(cert_path.read_bytes())
    der = cert.public_key().public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return base64.b64encode(hashlib.sha256(der).digest()).decode("ascii")


class _Listener:
    """One scenario's own real HTTPS listener, owned start to finish.

    In-process on a daemon thread purely for speed: the socket, the TLS
    handshake and the ASGI app underneath are what `scripts/run-app.sh` runs.
    Only this scenario's own listener is ever started or stopped -- no shared
    service, no host network or firewall state, nothing anyone else is using.
    """

    def __init__(self, project: dict, name: str) -> None:
        root = project["root"] / name
        root.mkdir(parents=True, exist_ok=True)
        self.name = name
        self.secret_path = root / "secret"
        self.certs = tls.ensure(tls_dir=root / "tls", extra_host="127.0.0.1")
        self.app = serve.create_app(
            config_path=project["config"],
            secret_path=self.secret_path,
            state_path=root / "state.json",
            sessions_path=root / "sessions.json",
            tls_dir=self.certs.tls_dir,
        )
        self.port = _free_port()
        self.origin = f"https://127.0.0.1:{self.port}"
        self._server = None
        self._thread: threading.Thread | None = None

    @property
    def spki(self) -> str:
        return _spki_sha256_b64(self.certs.leaf_cert)

    def cookie(self) -> dict:
        sessions = auth.Sessions(auth.read_or_make_secret(self.secret_path))
        return {
            "name": auth.COOKIE,
            "value": sessions.issue(USER),
            "domain": "127.0.0.1",
            "path": "/",
        }

    def start(self) -> None:
        import uvicorn

        config = uvicorn.Config(
            self.app,
            host="127.0.0.1",
            port=self.port,
            log_level="warning",
            ssl_keyfile=str(self.certs.leaf_key),
            ssl_certfile=str(self.certs.leaf_cert),
        )
        self._server = uvicorn.Server(config)
        self._thread = threading.Thread(target=self._server.run, daemon=True)
        self._thread.start()
        deadline = time.time() + 25
        while not self._server.started and time.time() < deadline:
            time.sleep(0.05)
        assert self._server.started, f"{self.name} did not start on {self.origin}"
        self.probe_alive()

    def probe_alive(self) -> None:
        """Verify this listener's own chain and hostname before trusting it."""
        connection = http.client.HTTPSConnection(
            "127.0.0.1",
            self.port,
            context=ssl.create_default_context(cafile=str(self.certs.ca_cert)),
            timeout=5,
        )
        try:
            connection.request("GET", "/healthz")
            response = connection.getresponse()
            assert response.status == 200, f"{self.origin} failed its verified TLS probe"
            response.read()
        finally:
            connection.close()

    def stop(self) -> None:
        """Ask this listener -- and only this one -- to finish and go away."""
        if self._server is not None:
            self._server.should_exit = True
        if self._thread is not None:
            self._thread.join(timeout=15)
            assert not self._thread.is_alive(), f"{self.name} did not stop"
        self._server = None
        self._thread = None

    def probe_outage(self) -> str:
        """Prove the transport is gone, in the plainest terms available.

        A TCP connection to the port this app was serving on, from outside the
        browser entirely. Anything other than a refusal means the assertions
        that follow would be measuring the wrong thing.
        """
        s = socketlib.socket()
        s.settimeout(3)
        try:
            s.connect(("127.0.0.1", self.port))
            return ""
        except OSError as exc:
            return f"{type(exc).__name__}: {exc}"
        finally:
            s.close()


# --------------------------------------------------------------------------
# driving the browser
# --------------------------------------------------------------------------

BANNER = """
() => {
  const el = document.getElementById('offlineBanner');
  if (!el) return null;
  return {hidden: el.hidden, text: el.innerText,
          marks: Array.from(el.querySelectorAll('.offline-mark')).map(li => li.textContent)};
}
"""

# Ask the worker to confirm identity exactly as Shell does, and report how it
# settled. `window.ConvergePWA.setPrincipal` is the real seam -- not a probe
# added for this test -- so what is measured here is what the app itself gets.
ASK_PRINCIPAL = """
async (name) => {
  try {
    const r = await window.ConvergePWA.setPrincipal(name);
    return {settled: 'resolved', ok: !!r.ok, user: r.user || '',
            offlineConfirmed: !!r.offlineConfirmed, reason: r.reason || ''};
  } catch (err) {
    return {settled: 'rejected', ok: false, user: err.user || '',
            offlineConfirmed: false, reason: err.reason || String(err)};
  }
}
"""

# The worker's own caches, addressed by the keys already in them rather than by
# a copy of sw.js's private constants -- a second copy of a name is a second
# thing to keep in step.
ONLY_KEY = """
async (cacheName) => {
  const cache = await caches.open(cacheName);
  const keys = await cache.keys();
  return keys.length ? keys[0].url : '';
}
"""


def _synced_keys(page):
    return page.evaluate(
        "async () => { const c = await caches.open('converge-synced-v1');"
        " return (await c.keys()).map(r => new URL(r.url).pathname).sort(); }"
    )


def _console_state(page) -> dict:
    return page.evaluate(
        """() => {
            const pane = document.getElementById('managerConsole');
            if (!pane) return {interactive: false, pointerEvents: 'no pane'};
            const pe = getComputedStyle(pane).pointerEvents;
            return {interactive: pe !== 'none', pointerEvents: pe};
        }"""
    )


def _warm(page, origin, width):
    """Open the app the way an installed app is opened: not for the first time.

    The worker is not controlling the page on the very first load -- it
    installs during it -- so nothing from /api is stored then. A second load is
    what an installed app always is, and the only state in which §10 can be
    true at all.
    """
    for _ in range(2):
        page.goto(origin, wait_until="networkidle")
        page.wait_for_selector(".home-manager-card", timeout=20000)
        page.click(".home-manager-card")
        page.wait_for_selector("#directionTab", timeout=20000)
        if width < 980 and _console_state(page)["interactive"]:
            page.click("#consoleToggle")
            page.wait_for_timeout(400)
        page.click("#directionTab")
        page.wait_for_selector("#documentModeContent", timeout=20000)
        page.click("#operationTab")
        page.wait_for_timeout(400)
        page.evaluate("async () => { await navigator.serviceWorker.ready; }")
    page.wait_for_function("() => !!navigator.serviceWorker.controller", timeout=20000)
    page.wait_for_timeout(1200)


def _open_manager(page, width):
    """Home, then a manager, then a view -- the steward's own taps.

    A reload never restores the manager and document that were open before it
    (`experience.v1` Core 1; `main.js`'s `boot()` ends on Home whatever the
    boot payload held), so this is what reaching a document offline actually
    costs, and it is made here rather than assumed away.
    """
    page.wait_for_selector(".home-manager-card", timeout=20000)
    page.click(".home-manager-card")
    page.wait_for_selector("#directionTab", timeout=20000)
    if width < 980 and _console_state(page)["interactive"]:
        page.click("#consoleToggle")
        page.wait_for_timeout(500)


WRITES = [
    ("answer with a word", "/api/managers/demo/decision", {"decision": "ratified"}, "was recorded"),
    ("drop feedback", "/api/managers/demo/feedback", {"text": "x", "context": "y"}, "was filed"),
    ("steer", "/api/managers/demo/steer", {"objective": "x", "lanes": 2}, "was sent"),
    ("raise or lower a priority", "/api/managers/demo/steer", {"fill": True}, "was sent"),
    ("ask", "/api/managers/demo/ask", {"scope": "document", "text": "x"}, "was asked"),
]


# --------------------------------------------------------------------------
# 1 -- through a real outage, the same client reads what it last synced
# --------------------------------------------------------------------------


@needs_browser
@pytest.mark.parametrize("width,height", [(1280, 800), (390, 844)])
def test_after_a_real_outage_the_same_client_reads_what_it_last_synced(
    project, width, height
):
    from playwright.sync_api import sync_playwright

    listener = _Listener(project, f"read-{width}")
    listener.start()
    print(f"\n[{width}] listener up and TLS-verified at {listener.origin}")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            args=["--no-sandbox", f"--ignore-certificate-errors-spki-list={listener.spki}"]
        )
        try:
            ctx = browser.new_context(viewport={"width": width, "height": height})
            ctx.add_cookies([listener.cookie()])
            page = ctx.new_page()
            errors: list[str] = []
            page.on("console", lambda m: errors.append(f"console.{m.type}: {m.text}") if m.type == "error" else None)
            page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))

            _warm(page, listener.origin, width)
            stored = _synced_keys(page)
            print(f"[{width}] payloads stored while the listener was up: {stored}")
            assert "/api/boot" in stored, (
                "the identity-bound boot payload was never stored, so there is nothing "
                f"for the worker to have validated: {stored}"
            )

            # ------------------------------------------------ the outage itself
            listener.stop()
            refused = listener.probe_outage()
            print(f"[{width}] socket probe of 127.0.0.1:{listener.port} after stopping: "
                  f"{refused or 'STILL REACHABLE'}")
            assert refused, (
                "the listener was stopped but its port still accepts connections; every "
                "assertion below would be measuring the wrong thing"
            )
            # The interface flag is set only so the banner says "Offline" rather
            # than "Converge could not be reached" -- §10's own wording. The
            # outage above is what makes the network actually gone.
            ctx.set_offline(True)

            page.reload(wait_until="load")
            page.wait_for_timeout(1500)

            _open_manager(page, width)
            page.click("#directionTab")
            page.wait_for_selector("#documentModeContent", timeout=20000)

            manager = page.eval_on_selector("#managerNameTop", "el => el.textContent.trim()")
            docs = page.eval_on_selector_all(".repo-doc", "els => els.length")
            reading = page.eval_on_selector("#documentModeContent", "el => el.innerText.trim()")
            banner = page.evaluate(BANNER)
            print(f"[{width}] manager named in the top bar: {manager!r}")
            print(f"[{width}] documents in the tree: {docs}")
            print(f"[{width}] reading surface carries: {reading[:80]!r}")
            print(f"[{width}] banner says: {banner['text']}")
            print(f"[{width}] marks: {banner['marks']}")

            assert manager, "the top bar named no manager: nothing was read back through the outage"
            assert docs > 0, "the document tree was empty: the shell rendered with no payload behind it"
            assert reading, "the reading surface was empty after the outage"
            assert banner is not None and banner["hidden"] is False, "nothing on screen said the app was offline"
            assert "as of " in banner["text"], (
                f"§10 asks for a visible 'as of <time>'; the banner said: {banner['text']!r}"
            )
            assert banner["marks"], "no payload was marked with the moment it came from"

            page.click("#operationTab")
            page.wait_for_timeout(600)
            operation = page.eval_on_selector("#operationView", "el => el.innerText.trim()")
            print(f"[{width}] operation surface carries: {operation[:80]!r}")
            assert operation, "Operation was empty after the outage"

            # ------------------------------------------------ writes are refused
            print(f"[{width}] raw writes through the outage:")
            for name, route, payload, own_words in WRITES:
                answer = page.evaluate(
                    """async ([url, body]) => {
                        const r = await fetch(url, {method: 'POST', credentials: 'include',
                            headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body)});
                        let said = '';
                        try { said = (await r.json()).error || ''; } catch { said = '(not JSON)'; }
                        return {status: r.status, said};
                    }""",
                    [route, payload],
                )
                said = answer["said"]
                print(f"  {name:26} -> {said}")
                assert answer["status"] != 200, f"{name} was not refused: {answer}"
                assert own_words in said, f"{name} did not name its own write: {said!r}"
                assert "reconnect" in said, f"{name} did not name what to do instead: {said!r}"

            # One write driven from the screen, so the refusal is shown to a
            # person and not only to the network layer. Steer is the one of the
            # five reachable at BOTH widths (`shell.css` hides #feedbackButton
            # below 980px).
            page.wait_for_selector("#steerButton", state="visible", timeout=10000)
            page.click("#steerButton")
            page.wait_for_selector("#steerObjective", timeout=10000)
            page.fill("#steerNote", "Narrow to the offline work.")
            page.click('#dialogActions button:text-is("Update steering")')
            page.wait_for_timeout(1500)
            toast = page.eval_on_selector("#toast", "el => el.textContent || ''")
            after = page.evaluate(BANNER)
            print(f"[{width}] the toast said:  {toast}")
            print(f"[{width}] the banner says: {after['text']}")
            # Both leads are correct sentences, and WHICH one appears is itself a
            # fact about this scenario rather than a detail to paper over. A
            # stopped listener with the interface still up is exactly the case
            # sw.js splits out: the request may have died in flight, so it says
            # "it is not known whether this was sent" instead of claiming
            # nothing happened. Chromium's emulated offline flag does not always
            # reach the worker (the harness note this file exists for), so the
            # honest assertion is on what §11 actually asks -- one plain
            # sentence, naming this write and what to do instead.
            lead = "you are offline" if "you are offline" in toast else "Converge could not be reached"
            print(f"[{width}] the refusal's lead: {lead!r}")
            assert lead in toast, f"the steward was not shown the refusal: {toast!r}"
            assert "reconnect" in toast, f"the refusal named nothing to do instead: {toast!r}"
            assert "was sent" in toast, f"the refusal did not name this write: {toast!r}"
            assert "was sent" in after["text"] and "reconnect" in after["text"], (
                f"the banner did not carry the whole refusal sentence: {after['text']!r}"
            )

            # ------------------------------------------------ reconnection
            listener.start()
            ctx.set_offline(False)
            print(f"[{width}] listener back up at {listener.origin}")
            page.reload(wait_until="networkidle")
            page.wait_for_selector(".home-manager-card", timeout=20000)
            live = page.evaluate(
                """async () => {
                    const r = await fetch('/api/boot', {credentials: 'include'});
                    const body = await r.json();
                    return {status: r.status, offline: r.headers.get('X-Converge-Offline'),
                            user: r.headers.get('X-Converge-User'), managers: (body.managers || []).length};
                }"""
            )
            print(f"[{width}] reconnected /api/boot -> {live}")
            assert live["status"] == 200, "the app did not come back online"
            assert live["offline"] is None, "a stored payload was still being served after reconnecting"
            assert live["user"] == USER, (
                f"the reconnected answer was for somebody else: {live['user']!r}"
            )
            assert live["managers"] > 0, "the live answer was empty"
            back = page.evaluate(BANNER)
            print(f"[{width}] banner after reconnecting: hidden={back['hidden']}")
            assert back["hidden"] is True, "the offline banner stayed up after reconnecting"

            noise = [e for e in errors if "status of 503" not in e]
            print(f"[{width}] browser lines narrating the refusals: {len(errors) - len(noise)}")
            print(f"[{width}] anything else in the browser's log: {noise or 'none'}")
            assert not noise, f"the browser reported errors: {noise}"
            ctx.close()
        finally:
            browser.close()
            listener.stop()


# --------------------------------------------------------------------------
# 2 -- the receipt answers for one client, one owner, one epoch, and no more
# --------------------------------------------------------------------------


@needs_browser
def test_the_offline_receipt_answers_only_for_this_client_owner_and_epoch(project):
    """Each refusal is provoked separately, and each names its own cause.

    A single "it refused" would not tell a universal boot-unreachable allow
    from a real check. So the honest confirmation is measured first, then each
    guard is broken on its own and the app asked again.
    """
    from playwright.sync_api import sync_playwright

    listener = _Listener(project, "guards")
    listener.start()

    with sync_playwright() as p:
        browser = p.chromium.launch(
            args=["--no-sandbox", f"--ignore-certificate-errors-spki-list={listener.spki}"]
        )
        try:
            ctx = browser.new_context(viewport={"width": 1280, "height": 800})
            ctx.add_cookies([listener.cookie()])
            page = ctx.new_page()

            _warm(page, listener.origin, 1280)
            listener.stop()
            refused = listener.probe_outage()
            print(f"\n[guards] socket probe after stopping: {refused or 'STILL REACHABLE'}")
            assert refused, "the listener was stopped but its port still accepts connections"
            ctx.set_offline(True)

            page.reload(wait_until="load")
            page.wait_for_timeout(1500)
            page.wait_for_selector(".home-manager-card", timeout=20000)

            # The honest case: this client just read a cached /api/boot the
            # worker had already validated, and asks under the name the worker
            # itself holds.
            honest = page.evaluate(ASK_PRINCIPAL, USER)
            print(f"[guards] this client, its own owner   -> {honest}")
            assert honest["settled"] == "resolved" and honest["ok"], (
                f"a validated cached boot did not confirm offline: {honest}"
            )
            assert honest["offlineConfirmed"], (
                "the confirmation did not say it came from the worker's own receipt rather "
                f"than a live server: {honest}"
            )
            assert honest["user"] == USER, f"the worker confirmed the wrong person: {honest}"

            # A page asking under a name the worker does not hold. The reply
            # carries the worker's own principal, so the seam catches it.
            forged = page.evaluate(ASK_PRINCIPAL, OTHER_USER)
            print(f"[guards] this client, a forged owner  -> {forged}")
            assert forged["settled"] == "rejected", (
                f"a page asking under another name was let through: {forged}"
            )
            assert not forged["offlineConfirmed"], f"a forged owner was confirmed: {forged}"

            still = page.evaluate(ASK_PRINCIPAL, USER)
            print(f"[guards] honest ask again             -> {still}")
            assert still["ok"], f"the forged ask damaged the honest one: {still}"

            # A device with no durable principal at all -- nothing confirmed
            # here, so nothing for a receipt to match.
            principal_key = page.evaluate(ONLY_KEY, "converge-principal-v1")
            assert principal_key, "the worker recorded no durable principal to begin with"
            saved = page.evaluate(
                """async ([name, key]) => {
                    const c = await caches.open(name);
                    const hit = await c.match(key);
                    const body = hit ? await hit.text() : '';
                    await c.delete(key);
                    return body;
                }""",
                ["converge-principal-v1", principal_key],
            )
            unconfirmed = page.evaluate(ASK_PRINCIPAL, USER)
            print(f"[guards] no durable principal         -> {unconfirmed}")
            assert unconfirmed["settled"] == "rejected", (
                f"an unconfirmed device was allowed to boot from a receipt: {unconfirmed}"
            )
            assert unconfirmed["reason"] == "boot-unreachable", (
                f"the refusal did not name its own cause: {unconfirmed}"
            )

            page.evaluate(
                """async ([name, key, body]) => {
                    const c = await caches.open(name);
                    await c.put(key, new Response(body, {headers: {'Content-Type': 'application/json'}}));
                }""",
                ["converge-principal-v1", principal_key, saved],
            )
            restored = page.evaluate(ASK_PRINCIPAL, USER)
            print(f"[guards] durable principal restored   -> {restored}")
            assert restored["ok"], (
                f"restoring the principal did not restore the honest answer: {restored}"
            )

            # An epoch that has moved on. Bumped the way the app itself bumps
            # it -- a real /logout, which sw.js answers by clearing the synced
            # caches, forgetting the principal and moving the epoch on -- rather
            # than by writing a fabricated entry into the worker's own epoch
            # cache, which would only prove this test can write to a cache.
            page.evaluate("async () => { try { await fetch('/logout'); } catch { /* the network is gone */ } }")
            page.wait_for_timeout(1200)
            after_logout = page.evaluate(ASK_PRINCIPAL, USER)
            print(f"[guards] after a logout               -> {after_logout}")
            assert after_logout["settled"] == "rejected", (
                f"a receipt survived a logout: {after_logout}"
            )
            assert after_logout["reason"] == "boot-unreachable", (
                f"the refusal did not name its own cause: {after_logout}"
            )

            # The same person's durable principal put back, byte for byte. The
            # receipt is still dead: the epoch moved when the caches behind it
            # were emptied, and every proof went with it. This is the check that
            # separates "the owner matches" from "this exact read was validated
            # at this exact epoch".
            page.evaluate(
                """async ([name, key, body]) => {
                    const c = await caches.open(name);
                    await c.put(key, new Response(body, {headers: {'Content-Type': 'application/json'}}));
                }""",
                ["converge-principal-v1", principal_key, saved],
            )
            spent = page.evaluate(ASK_PRINCIPAL, USER)
            print(f"[guards] same owner, moved epoch      -> {spent}")
            assert spent["settled"] == "rejected", (
                "the same owner reappearing revived a receipt written before the epoch "
                f"moved; it must be gone for good: {spent}"
            )

            emptied = _synced_keys(page)
            print(f"[guards] payloads left after logout: {emptied}")
            assert "/api/boot" not in emptied, (
                f"the logout left the boot payload behind for the next person: {emptied}"
            )

            # A client that never read a validated cached boot at all -- which
            # is what makes this a per-client receipt and not a universal
            # "unreachable means allowed".
            fresh = ctx.new_page()
            fresh.goto(listener.origin, wait_until="load")
            fresh.wait_for_timeout(2500)
            asked = fresh.evaluate(ASK_PRINCIPAL, USER)
            cards = fresh.eval_on_selector_all(".home-manager-card", "els => els.length")
            body = fresh.eval_on_selector("body", "el => el.innerText.trim()")
            print(f"[guards] a client with no cached boot -> {asked}")
            print(f"[guards] manager sessions it can read: {cards}")
            print(f"[guards] what that client is shown: {body[:110]!r}")
            assert asked["settled"] == "rejected", (
                f"a client that never read a validated cached boot was confirmed: {asked}"
            )
            assert cards == 0, (
                "a client that could not confirm identity was still shown manager sessions; "
                f"the fail-closed clear did not happen: {cards}"
            )
            # The logout emptied SHELL along with SYNCED, so this client cannot
            # even open the app -- it gets the worker's own honest page saying
            # nothing is stored here to read, and `window.ConvergePWA` does not
            # exist on it at all. That is a stronger outcome than a refused
            # confirmation, and it is the one that matters for the next person
            # at this browser: no receipt, no shell, and nothing of the last
            # person's left to read.
            assert "offline" in body.lower(), (
                f"the client with nothing stored was not told so plainly: {body[:200]!r}"
            )
            ctx.close()
        finally:
            browser.close()
            listener.stop()


# --------------------------------------------------------------------------
# 3 -- the receipt is this client's, and no other client in the same profile
#      may spend it
# --------------------------------------------------------------------------

# A second controlled client's own half of the seam, written out by hand
# because this client deliberately never ran `offline.js`. The message is the
# app's real one -- same type, same MessageChannel reply port -- so what is
# measured is the worker's own answer to a real `converge-set-principal`, and
# the `event.source.id` behind it is the user agent's stamp on THIS document,
# never a value this test chose.
BORROW = """
async (user) => {
  const controller = navigator.serviceWorker && navigator.serviceWorker.controller;
  if (!controller) return {settled: 'no-controller'};
  return await new Promise((resolve) => {
    const channel = new MessageChannel();
    const timer = setTimeout(() => resolve({settled: 'no-response'}), 8000);
    channel.port1.onmessage = (event) => {
      clearTimeout(timer);
      const data = event.data || {};
      resolve({settled: 'replied', ok: !!data.ok, user: data.user || '',
               offlineConfirmed: !!data.offlineConfirmed, reason: data.reason || '',
               cleared: !!data.cleared});
    };
    controller.postMessage({type: 'converge-set-principal', user: user}, [channel.port2]);
  });
}
"""

# What this second client can see of itself: whether the worker controls it,
# which script that worker is, whether the app's own page code ever ran here,
# and whether anything under /api was ever requested from it.
BORROWER_STATE = """
() => {
  const c = navigator.serviceWorker && navigator.serviceWorker.controller;
  return {
    controlled: !!c,
    script: c ? new URL(c.scriptURL).pathname : '',
    hasPageCode: typeof window.ConvergePWA !== 'undefined',
    apiRequests: performance.getEntriesByType('resource')
      .map(e => new URL(e.name).pathname).filter(p => p.startsWith('/api/')),
  };
}
"""

FETCH_JSON = """
async (path) => {
  const r = await fetch(path, {credentials: 'include'});
  let user = '';
  try { user = (await r.json()).user || ''; } catch { user = '(not JSON)'; }
  return {status: r.status, fromCache: r.headers.get('X-Converge-Offline'), user};
}
"""

FETCH_TEXT = """
async (path) => {
  const r = await fetch(path, {credentials: 'include'});
  const body = await r.text();
  return {status: r.status, bytes: body.length};
}
"""


@needs_browser
def test_one_clients_offline_receipt_cannot_be_spent_by_another_client(project):
    """A receipt is for the client that earned it -- not for the profile.

    The existing fresh-client check in this file proves something adjacent but
    weaker: after a logout has emptied every cache, a new client is refused.
    That is an empty-cache refusal, and it cannot tell a per-client receipt
    from a rule as loose as "this device confirmed someone once, so anything
    in it may read". This one leaves the first client's receipt alive and its
    cache full, and asks the same worker, in the same profile, under the same
    signed-in cookie, from a second controlled document.

    The second client is a same-origin document that never executes `main.js`.
    A static text resource cannot be used as that document: `sw.js` answers
    EVERY navigation from the SHELL cache (`req.mode === 'navigate'` is
    checked before anything else), so navigating anywhere offline serves the
    app shell, whose `boot()` immediately reads the cached /api/boot -- which
    would hand this client the very receipt the test exists to withhold. So
    the document is created in the profile instead, and its control by this
    worker is confirmed twice: by the controller it reports, and by a real
    cacheable same-origin static text resource it fetches successfully
    THROUGH the outage, which nothing but this worker could have answered.
    """
    from playwright.sync_api import sync_playwright

    listener = _Listener(project, "receipt")
    listener.start()
    print(f"\n[receipt] listener up and TLS-verified at {listener.origin}")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            args=["--no-sandbox", f"--ignore-certificate-errors-spki-list={listener.spki}"]
        )
        try:
            ctx = browser.new_context(viewport={"width": 1280, "height": 800})
            ctx.add_cookies([listener.cookie()])
            page = ctx.new_page()

            # ------------------------------------------------ A, warmed for real
            _warm(page, listener.origin, 1280)
            stored = _synced_keys(page)
            print(f"[receipt] A stored while the listener was up: {stored}")
            assert "/api/boot" in stored, (
                f"A never stored an owner-validated boot payload: {stored}"
            )

            # ------------------------------------------------ the outage itself
            listener.stop()
            refused = listener.probe_outage()
            print(f"[receipt] socket probe of 127.0.0.1:{listener.port}: "
                  f"{refused or 'STILL REACHABLE'}")
            assert refused, (
                "the listener was stopped but its port still accepts connections; every "
                "assertion below would be measuring the wrong thing"
            )
            ctx.set_offline(True)

            page.reload(wait_until="load")
            page.wait_for_timeout(1500)
            page.wait_for_selector(".home-manager-card", timeout=20000)

            # A reads the cached boot itself -- the read that earns the receipt.
            a_boot = page.evaluate(FETCH_JSON, "/api/boot")
            print(f"[receipt] A's own cached /api/boot     -> {a_boot}")
            assert a_boot["status"] == 200, f"A could not read its cached boot: {a_boot}"
            assert a_boot["fromCache"] == "1", (
                f"A's boot answer did not come from the worker's store: {a_boot}"
            )
            assert a_boot["user"] == USER, f"A's cached boot was for somebody else: {a_boot}"

            a_confirmed = page.evaluate(ASK_PRINCIPAL, USER)
            print(f"[receipt] A confirms offline          -> {a_confirmed}")
            assert a_confirmed["ok"] and a_confirmed["offlineConfirmed"], (
                f"A did not earn a receipt from its validated cached boot: {a_confirmed}"
            )

            # ------------------------------------------------ B, controlled, no boot
            page.evaluate(
                """() => new Promise((resolve) => {
                    const f = document.createElement('iframe');
                    f.name = 'borrower';
                    f.setAttribute('title', 'borrower');
                    f.srcdoc = '<!doctype html><meta charset="utf-8">'
                             + '<title>borrower</title><p>a plain same-origin document</p>';
                    f.onload = () => resolve(true);
                    document.body.appendChild(f);
                })"""
            )
            borrower = page.frame(name="borrower")
            assert borrower is not None, "the second client's document never appeared"

            state = borrower.evaluate(BORROWER_STATE)
            print(f"[receipt] B's own view of itself      -> {state}")
            assert state["controlled"], (
                "the second document is not controlled by this worker, so its refusal "
                f"would prove nothing about receipts: {state}"
            )
            assert state["script"].endswith("/sw.js"), (
                f"B is controlled by something other than this app's worker: {state}"
            )
            assert not state["hasPageCode"], (
                f"the app's own page code ran in B; it is not a naive client: {state}"
            )
            assert state["apiRequests"] == [], (
                f"B had already requested something under /api before being asked: {state}"
            )

            # Control confirmed by behaviour, not only by a flag: a cacheable
            # same-origin static text resource, answered through a dead
            # transport. Only this worker could have served it.
            #
            # converge-moe4: tokens.css is now served from a per-generation
            # VERSIONED URL (app/assets.py) -- only THAT exact URL was ever
            # precached/runtime-cached by A, so a hardcoded, unversioned
            # '/static/css/tokens.css' is a guaranteed cache miss (and, with
            # the network down, a hard failure) regardless of what this test
            # is actually trying to prove. Read the real, current URL A's own
            # rendered page used, rather than assume its shape.
            tokens_css_path = page.eval_on_selector(
                'link[href*="/css/tokens.css"]', "el => new URL(el.href).pathname"
            )
            css = borrower.evaluate(FETCH_TEXT, tokens_css_path)
            print(f"[receipt] B reads a static resource   -> {css}")
            assert css["status"] == 200 and css["bytes"] > 0, (
                f"B's own requests are not reaching this worker: {css}"
            )

            # ------------------------------------------------ the borrow, refused
            borrowed = borrower.evaluate(BORROW, USER)
            print(f"[receipt] B asks to be confirmed      -> {borrowed}")
            assert borrowed["settled"] == "replied", (
                f"the worker never answered B's real message: {borrowed}"
            )
            assert not borrowed["ok"], (
                "a client that never read a validated cached boot was confirmed offline "
                f"while another client's receipt was alive: {borrowed}"
            )
            assert borrowed["reason"] == "boot-unreachable", (
                f"the refusal did not name its own cause: {borrowed}"
            )
            assert not borrowed["offlineConfirmed"], f"B was handed a receipt: {borrowed}"
            assert not borrowed["cleared"], (
                f"B's refused ask cleared what A had synced: {borrowed}"
            )

            # The refusal was not an empty-cache refusal: A's receipt and A's
            # stored payloads are both still there, and A still confirms.
            survived = _synced_keys(page)
            still = page.evaluate(ASK_PRINCIPAL, USER)
            print(f"[receipt] A's payloads after B's ask: {survived}")
            print(f"[receipt] A confirms again            -> {still}")
            assert "/api/boot" in survived, (
                f"B's refused ask cost A the payload it was reading: {survived}"
            )
            assert still["ok"] and still["offlineConfirmed"], (
                "B was refused while A's receipt was already dead, so the refusal proves "
                f"nothing about transfer: {still}"
            )

            # ------------------------------------------------ B earns its own
            b_boot = borrower.evaluate(FETCH_JSON, "/api/boot")
            print(f"[receipt] B's own cached /api/boot    -> {b_boot}")
            assert b_boot["status"] == 200 and b_boot["fromCache"] == "1", (
                f"B could not read the cached boot the owner check allows it: {b_boot}"
            )
            assert b_boot["user"] == USER, f"B was served somebody else's boot: {b_boot}"

            earned = borrower.evaluate(BORROW, USER)
            print(f"[receipt] B asks again, after reading -> {earned}")
            assert earned["ok"] and earned["offlineConfirmed"], (
                "a client that HAS read a validated cached boot was still refused; the "
                f"legitimate offline reload is broken: {earned}"
            )
            assert earned["user"] == USER, f"B was confirmed as somebody else: {earned}"

            # ------------------------------------------------ the claim never selects
            # B now holds a real receipt, and asks under a name the worker does
            # not hold. The answer carries the worker's OWN principal -- the
            # page's claim cannot choose who a receipt speaks for.
            claimed = borrower.evaluate(BORROW, OTHER_USER)
            print(f"[receipt] B asks under another name   -> {claimed}")
            assert claimed["user"] == USER, (
                f"a page's claimed user selected who the receipt answered for: {claimed}"
            )
            assert not claimed["cleared"], (
                f"a page's claimed user cleared this device's caches: {claimed}"
            )

            # And the page-side seam still refuses that mismatch outright, which
            # is what Shell's own fail-closed `await` depends on.
            forged = page.evaluate(ASK_PRINCIPAL, OTHER_USER)
            print(f"[receipt] A's seam, another name      -> {forged}")
            assert forged["settled"] == "rejected" and not forged["offlineConfirmed"], (
                f"the page-side seam stopped refusing a wrong user: {forged}"
            )
            ctx.close()
        finally:
            browser.close()
            listener.stop()
