"""converge-iizz: two real HTTPS preview instances, one real browser cookie jar.

`app/tests/test_preview_https_instance.py` proves instance isolation and
real logout revocation against `fastapi.testclient.TestClient` -- an
in-process ASGI transport with no real socket, no real TLS handshake, and a
`cookies` dict a test hand-assembles to simulate "one shared jar". That is
enough to prove the *server's* logic, but not the actual claim: that two
real HTTPS servers, opened as two tabs in one real browser, behave the way
this app's own cookie namespacing was built for.

This file drives a REAL Chromium (via Playwright), against two REAL uvicorn
servers doing REAL TLS handshakes with two independently-generated local
CAs, sharing exactly ONE browser context -- Playwright's own cookie jar,
scoped the same way a real browser's is (by host, never by port, which is
the whole reason `--instance-dir` namespacing exists at all). Every
certificate is verified by Chromium itself, pinned by its own SPKI hash
(`--ignore-certificate-errors-spki-list`) rather than blanket
`ignore_https_errors` -- the narrow, single-certificate exception the task
calls for, never a general "trust anything" mode, and never a change to
this machine's own OS trust store.

What is proved, end to end, through the real login form and the page's own
`fetch`/cookie/CSRF-header logic (`app/static/js/api.js`'s own convention,
re-run here rather than hand-simulated):

* two instances, one browser jar: each keeps its own namespaced session and
  CSRF cookies, side by side, in the one jar a real browser would hold;
* the first unsafe write against instance A's own namespace/CSRF flow --
  a real tmux keystroke, landing in a real, isolated, named tmux socket;
* logging out of A revokes A's cookie -- proved by a REPLAY against the
  saved value, not merely "the browser's own copy is gone" -- while B's
  session, in the very same jar, is completely unaffected.
"""

from __future__ import annotations

import base64
import hashlib
import http.client
import os
import shutil
import socket as socketlib
import ssl
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app import auth, serve, tls  # noqa: E402

GOOD_USER = "tester"
GOOD_PASSWORD = "two-https-fixture-password"  # noqa: S105 - test fixture, not a real secret


class _FakePam:
    def authenticate(self, username: str, password: str, service: str = "login") -> bool:
        assert service == "login"
        return username == GOOD_USER and password == GOOD_PASSWORD


@pytest.fixture(autouse=True)
def _fake_pam(monkeypatch) -> None:
    monkeypatch.setattr(auth.pam_module, "pam", _FakePam)


# --------------------------------------------------------------------------
# availability -- print the reason rather than silently vanishing
# --------------------------------------------------------------------------


def _skip_reason() -> str:
    if shutil.which("tmux") is None:
        return "tmux is not installed"
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


PLAYWRIGHT_SKIP = _skip_reason()
needs_browser = pytest.mark.skipif(bool(PLAYWRIGHT_SKIP), reason=PLAYWRIGHT_SKIP)


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------


def _free_port() -> int:
    s = socketlib.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def _spki_sha256_b64(cert_path: Path) -> str:
    """The exact pin `--ignore-certificate-errors-spki-list` wants: the
    SHA-256 of ONE certificate's DER-encoded SubjectPublicKeyInfo,
    base64-encoded.

    Pinning this -- rather than Playwright's `ignore_https_errors=True`,
    which disables certificate verification for EVERY connection the
    browser makes for the rest of the run -- keeps the exception narrow:
    only a leaf whose exact public key matches one of these two hashes is
    let through despite its issuer (a locally-generated, un-trusted-by-the-
    OS CA) being unknown to Chromium. No OS trust store is touched, and no
    other certificate -- forged, mismatched, or simply different -- is
    accepted.
    """
    from cryptography import x509
    from cryptography.hazmat.primitives import serialization

    cert = x509.load_pem_x509_certificate(cert_path.read_bytes())
    der = cert.public_key().public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return base64.b64encode(hashlib.sha256(der).digest()).decode("ascii")


class _Instance:
    """One real HTTPS preview instance: its own local CA/leaf, its own
    `--instance-dir` namespace, a real uvicorn TLS listener on a real
    ephemeral port.

    Run in-process on a daemon thread rather than as a subprocess, purely
    for speed -- the socket, the TLS handshake, and the ASGI app underneath
    are exactly what `amplifier-converge start`/`scripts/run-app.sh` runs;
    only the process boundary differs, and nothing about instance isolation
    (the actual subject of this file) depends on that boundary.
    """

    def __init__(self, tmp_path: Path, name: str, *, steward: str, tmux_socket: str = "", manager_tmux: str = "") -> None:
        self.name = name
        tls_dir = tmp_path / f"{name}-tls"
        self.instance_dir = tmp_path / f"{name}-instance"
        conf = tmp_path / f"{name}.toml"
        lines = [
            "[[managers]]\n",
            f'id = "{name}"\n',
            f'name = "{name}"\n',
            f'steward = "{steward}"\n',
        ]
        if tmux_socket:
            lines.append(f'tmux_socket = "{tmux_socket}"\n')
        if manager_tmux:
            lines.append(f'manager_tmux = "{manager_tmux}"\n')
        conf.write_text("".join(lines), encoding="utf-8")

        self.cert_paths = tls.ensure(tls_dir=tls_dir, extra_host="127.0.0.1")
        self.app = serve.create_app(
            config_path=conf,
            state_path=tmp_path / f"{name}-state.json",
            instance_dir=self.instance_dir,
            tls_dir=self.cert_paths.tls_dir,
        )
        self.port = _free_port()
        self.origin = f"https://127.0.0.1:{self.port}"
        self._server = None
        self._thread: threading.Thread | None = None

    @property
    def spki(self) -> str:
        return _spki_sha256_b64(self.cert_paths.leaf_cert)

    def start(self) -> None:
        import uvicorn

        config = uvicorn.Config(
            self.app,
            host="127.0.0.1",
            port=self.port,
            log_level="warning",
            ssl_keyfile=str(self.cert_paths.leaf_key),
            ssl_certfile=str(self.cert_paths.leaf_cert),
        )
        self._server = uvicorn.Server(config)
        self._thread = threading.Thread(target=self._server.run, daemon=True)
        self._thread.start()
        deadline = time.time() + 20
        while not self._server.started and time.time() < deadline:
            time.sleep(0.05)
        assert self._server.started, f"instance {self.name!r} did not start on {self.origin}"
        # Verify this listener's chain and hostname before its exact leaf key
        # is permitted in the disposable Chromium profile.
        connection = http.client.HTTPSConnection(
            "127.0.0.1",
            self.port,
            context=ssl.create_default_context(cafile=str(self.cert_paths.ca_cert)),
            timeout=5,
        )
        try:
            connection.request("GET", "/healthz")
            response = connection.getresponse()
            assert response.status == 200, f"{self.origin} failed its verified TLS probe"
            response.read()
        except BaseException:
            self.stop()
            raise
        finally:
            connection.close()

    def stop(self) -> None:
        if self._server is not None:
            self._server.should_exit = True
        if self._thread is not None:
            self._thread.join(timeout=10)


def _tmux(socket: str, *args: str, check: bool = False) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env.pop("TMUX", None)  # never the ambient server -- see app/tmux_view.py's own rule
    return subprocess.run(["tmux", "-L", socket, *args], capture_output=True, text=True, env=env, check=check)


# --------------------------------------------------------------------------
# the test
# --------------------------------------------------------------------------


@needs_browser
def test_two_https_instances_share_one_browser_jar_first_write_and_isolated_logout(
    tmp_path: Path,
) -> None:
    # A per-run, named tmux socket -- never the ambient $TMUX, never a
    # fixed/shared name (two lanes testing at once would otherwise kill
    # each other's sessions; see app/tests/test_tmux_send_keys.py's own
    # convention, followed here rather than reinvented).
    tmux_socket = f"cvtwo-{os.getpid()}-{uuid.uuid4().hex[:8]}"
    tmux_session = "manA-console"
    found = _tmux(tmux_socket, "ls")
    assert found.returncode != 0, (
        f"a tmux server is already up on socket {tmux_socket!r}; refusing to touch it"
    )
    try:
        # `cat` echoes its own input -- the pane's text is proof the
        # keystrokes reached the real process, not merely tmux.
        _tmux(tmux_socket, "new", "-d", "-s", tmux_session, "cat", check=True)
        time.sleep(0.5)

        a = _Instance(tmp_path, "insta", steward=GOOD_USER, tmux_socket=tmux_socket, manager_tmux=tmux_session)
        b = _Instance(tmp_path, "instb", steward=GOOD_USER)
        a.start()
        b.start()
        try:
            from playwright.sync_api import sync_playwright

            pins = ",".join(sorted({a.spki, b.spki}))
            with sync_playwright() as p:
                browser = p.chromium.launch(
                    args=["--no-sandbox", f"--ignore-certificate-errors-spki-list={pins}"]
                )
                # ONE context == one real cookie jar, exactly as one browser
                # window with two tabs (one per instance) would hold.
                ctx = browser.new_context()
                page = ctx.new_page()
                console_errors: list[str] = []
                page.on("console", lambda m: console_errors.append(m.text) if m.type == "error" else None)

                # ---------------------------------------------------- sign in to A
                page.goto(f"{a.origin}/login", wait_until="networkidle")
                page.fill("#username", GOOD_USER)
                page.fill("#password", GOOD_PASSWORD)
                with page.expect_navigation(timeout=10000):
                    page.click("button.login-submit")
                assert "/login" not in page.url, f"sign-in to A did not leave /login: {page.url}"

                # ---------------------------------------------------- sign in to B
                page.goto(f"{b.origin}/login", wait_until="networkidle")
                page.fill("#username", GOOD_USER)
                page.fill("#password", GOOD_PASSWORD)
                with page.expect_navigation(timeout=10000):
                    page.click("button.login-submit")
                assert "/login" not in page.url, f"sign-in to B did not leave /login: {page.url}"

                jar = {c["name"]: c["value"] for c in ctx.cookies()}
                print(f"\n[two-https] one browser jar after both sign-ins: {sorted(jar)}")
                assert a.app.state.session_cookie in jar, "A's own session cookie is not in the shared jar"
                assert b.app.state.session_cookie in jar, "B's own session cookie is not in the shared jar"
                assert jar[a.app.state.session_cookie] != jar[b.app.state.session_cookie], (
                    "A and B ended up with the same session cookie value"
                )

                # ---------------------------------------- first unsafe write on A
                #
                # A real tmux keystroke, sent through the page's own fetch --
                # reading the namespaced CSRF cookie NAME off the
                # X-Converge-Csrf-Cookie response header, exactly the way
                # app/static/js/api.js's own `request()` does it, and echoing
                # it back as the X-CSRF-Token header -- this is instance A's
                # actual namespace/CSRF flow, not a hand-waved bypass of it.
                page.goto(a.origin, wait_until="networkidle")
                write_result = page.evaluate(
                    """
                    async ([socket, session]) => {
                      const r0 = await fetch('/api/boot', {credentials: 'same-origin'});
                      const cookieName = r0.headers.get('X-Converge-Csrf-Cookie') || 'cv_csrf';
                      const m = document.cookie.match(new RegExp(`(?:^|; )${cookieName}=([^;]*)`));
                      const token = m ? decodeURIComponent(m[1]) : '';
                      const r1 = await fetch(`/api/tmux/${socket}/${session}/keys`, {
                        method: 'POST', credentials: 'same-origin',
                        headers: {'Content-Type': 'application/json', 'X-CSRF-Token': token},
                        body: JSON.stringify({keys: 'HELLO-FROM-BROWSER', enter: true}),
                      });
                      return {status: r1.status, body: await r1.json()};
                    }
                    """,
                    [tmux_socket, tmux_session],
                )
                print(f"[two-https] first unsafe write (tmux keys) on A -> {write_result}")
                assert write_result["status"] == 200, write_result
                assert write_result["body"]["sent"] is True, write_result

                deadline = time.time() + 5
                pane_text = ""
                while time.time() < deadline:
                    pane_text = _tmux(tmux_socket, "capture-pane", "-p", "-t", f"={tmux_session}:").stdout
                    if "HELLO-FROM-BROWSER" in pane_text:
                        break
                    time.sleep(0.2)
                assert "HELLO-FROM-BROWSER" in pane_text, (
                    f"the browser's keystroke never reached the real tmux pane:\n{pane_text}"
                )

                # ------------------------------------------- logout of A only
                page.goto(a.origin, wait_until="networkidle")
                saved_a_cookie = jar[a.app.state.session_cookie]
                logout_status = page.evaluate(
                    """
                    async () => {
                      const r0 = await fetch('/api/boot', {credentials: 'same-origin'});
                      const cookieName = r0.headers.get('X-Converge-Csrf-Cookie') || 'cv_csrf';
                      const m = document.cookie.match(new RegExp(`(?:^|; )${cookieName}=([^;]*)`));
                      const token = m ? decodeURIComponent(m[1]) : '';
                      const r1 = await fetch('/logout', {
                        method: 'POST', credentials: 'same-origin', headers: {'X-CSRF-Token': token},
                      });
                      return r1.status;
                    }
                    """
                )
                print(f"[two-https] POST /logout on A -> {logout_status}")
                assert logout_status in (200, 302), logout_status

                # B's own cookie, in the very same jar, is untouched.
                jar_after = {c["name"]: c["value"] for c in ctx.cookies()}
                assert jar_after.get(b.app.state.session_cookie) == jar[b.app.state.session_cookie], (
                    "logging out of A changed B's own session cookie in the shared jar"
                )
                page.goto(b.origin, wait_until="networkidle")
                b_status = page.evaluate(
                    "async () => (await fetch('/api/boot', {credentials: 'same-origin'})).status"
                )
                print(f"[two-https] GET /api/boot on B after A's logout -> {b_status}")
                assert b_status == 200, "instance B stopped working after logging out of A"

                # A's own saved (pre-logout) cookie value must now be dead --
                # a REPLAY, not merely "the browser's live copy is gone". Back
                # on A's own origin first: a relative fetch() resolves
                # against whatever page is currently loaded, and the last
                # navigation above left it sitting on B's.
                page.goto(a.origin, wait_until="networkidle")
                a_status_live = page.evaluate(
                    "async () => (await fetch('/api/boot', {credentials: 'same-origin'})).status"
                )
                print(f"[two-https] GET /api/boot on A after its own logout -> {a_status_live}")
                assert a_status_live == 401, "A's session was not actually revoked by its own logout"

                replay_ctx = browser.new_context()
                replay_ctx.add_cookies(
                    [{
                        "name": a.app.state.session_cookie,
                        "value": saved_a_cookie,
                        "domain": "127.0.0.1",
                        "path": "/",
                    }]
                )
                replay_page = replay_ctx.new_page()
                replay_page.goto(a.origin, wait_until="networkidle")
                replay_status = replay_page.evaluate(
                    "async () => (await fetch('/api/boot', {credentials: 'same-origin'})).status"
                )
                print(f"[two-https] replaying A's PRE-LOGOUT cookie in a fresh context -> {replay_status}")
                assert replay_status == 401, (
                    "a cookie saved before logout still worked after logout -- the session was never really revoked"
                )
                replay_ctx.close()

                # A 401 the browser logs to its own console is Chromium
                # narrating the deliberately-revoked/replayed requests this
                # test just made -- expected noise, not a page defect.
                unexpected = [e for e in console_errors if "401" not in e]
                assert not unexpected, f"the page logged unexpected console errors: {unexpected}"
                ctx.close()
                browser.close()
        finally:
            a.stop()
            b.stop()
    finally:
        _tmux(tmux_socket, "kill-server")


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-s", *sys.argv[1:]]))
