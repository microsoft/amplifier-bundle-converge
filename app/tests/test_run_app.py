"""The one command that runs the app -- checked by running it.

`converge-sf1u`: `composition.v1` Core 5's shape, applied to the app rather than
to the install -- one command, nothing else to know. The command is
`scripts/run-app.sh`, and what it promises a reader is not "a server starts"
but four specific things:

* it serves HTTPS on the URL it prints, and that URL answers, with a
  certificate the printed CA verifies (converge-b2ak: no plain-HTTP fallback);
* the sign-in it names is the sign-in the page actually asks for;
* it binds every interface by default, because the whole point of this app is
  a phone or a teammate's machine reaching it on the LAN -- `--host 127.0.0.1`
  is the explicit, named way back to loopback-only (the SSH-tunnel case);
* trust instructions are one hop away at `/setup`, and never ask for a
  password over the connection they are helping a reader verify.

Every check below is against a real server this file starts and stops, over
real TLS, verified against the real CA the server generated -- never
`verify=False`. There is no fixture of the answer anywhere here: a wrapper
that printed a URL nothing was listening on, or a URL a generic client could
not actually verify, would pass a mock and fails this.

Two of them read documents instead, because two of `converge-sf1u`'s acceptance
lines are about where a reader finds the command at all -- `README.md` and the
agent context. A command nobody is told about is not one command, it is none.
"""

from __future__ import annotations

import http.client
import os
import re
import signal
import socket as socketlib
import ssl
import subprocess
import sys
import time
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "run-app.sh"

sys.path.insert(0, str(REPO))

from app import auth, tls  # noqa: E402

#: How long to wait for a real server to answer. `uv run` resolves first, and a
#: cold resolve is slower than a warm one; a bare sleep would either flake or
#: waste the difference, so every wait below polls.
BOOT_TIMEOUT = 90.0


def _free_port() -> int:
    """A port nothing is listening on, asked of the kernel rather than picked.

    8788 is the app's default and this host serves the real one there; a test
    that took the default would either fail against a live server or, worse,
    read one as if it were its own.
    """
    s = socketlib.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def _lan_address() -> str:
    """This machine's own non-loopback address, or "" when it has none."""
    s = socketlib.socket(socketlib.AF_INET, socketlib.SOCK_DGRAM)
    try:
        # No packet is sent by connect() on a UDP socket; this only asks the
        # routing table which local address would be used.
        s.connect(("192.0.2.1", 9))  # TEST-NET-1, deliberately unroutable
        addr = s.getsockname()[0]
    except OSError:
        return ""
    finally:
        s.close()
    return "" if addr.startswith("127.") else addr


def _ssl_context(ca_path: Path) -> ssl.SSLContext:
    """A real verifying context against the server's own generated CA --
    never `ssl._create_unverified_context()`. A test that trusted anything
    would not be testing that the certificate is actually right."""
    ctx = ssl.create_default_context(cafile=str(ca_path))
    return ctx


def _get(host: str, port: int, path: str, ca_path: Path, timeout: float = 5.0):
    """(status, location, body) for one request, redirects NOT followed.

    Following them would hide the gate: `/` answering 200 after a redirect to
    `/login` reads exactly like `/` answering 200 because there is no gate.
    """
    conn = http.client.HTTPSConnection(host, port, timeout=timeout, context=_ssl_context(ca_path))
    try:
        conn.request("GET", path)
        r = conn.getresponse()
        body = r.read().decode("utf-8", "replace")
        return r.status, r.headers.get("location", ""), body
    finally:
        conn.close()


def _post(host: str, port: int, path: str, form: dict[str, str], ca_path: Path, timeout: float = 5.0):
    """(status, location) for one form post, redirects NOT followed."""
    body = "&".join(f"{k}={v}" for k, v in form.items())
    conn = http.client.HTTPSConnection(host, port, timeout=timeout, context=_ssl_context(ca_path))
    try:
        conn.request(
            "POST", path, body=body, headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        r = conn.getresponse()
        r.read()
        return r.status, r.headers.get("location", "")
    finally:
        conn.close()


def _get_with_cookie(host: str, port: int, path: str, cookie: str, ca_path: Path, timeout: float = 5.0):
    conn = http.client.HTTPSConnection(host, port, timeout=timeout, context=_ssl_context(ca_path))
    try:
        conn.request("GET", path, headers={"Cookie": f"{auth.COOKIE}={cookie}"})
        r = conn.getresponse()
        return r.status, r.read().decode("utf-8", "replace")
    finally:
        conn.close()


class Server:
    """`scripts/run-app.sh` running for real, and stopped when we are done.

    Each instance gets its OWN `--tls-dir` (a fresh temp directory) via
    `$CONVERGE_TLS_DIR` -- a real CA, generated fresh, never the machine's own
    `~/.amplifier/converge-app-tls`. `ca_path` is only valid once the server
    has actually written it, which `wait_until_answering` waits for.
    """

    def __init__(self, *args: str, tls_dir: Path) -> None:
        self.args = args
        self.tls_dir = tls_dir
        self.proc: subprocess.Popen | None = None
        self.out = ""

    @property
    def ca_path(self) -> Path:
        return self.tls_dir / tls.CA_CERT_NAME

    def __enter__(self) -> "Server":
        self.log = open(  # noqa: SIM115 - closed in __exit__
            os.path.join(os.environ.get("TMPDIR", "/tmp"), f"run-app-test-{os.getpid()}.log"),
            "w+",
            encoding="utf-8",
        )
        env = dict(os.environ)
        env["CONVERGE_TLS_DIR"] = str(self.tls_dir)
        self.proc = subprocess.Popen(
            [str(SCRIPT), *self.args],
            cwd=str(REPO),
            stdout=self.log,
            stderr=subprocess.STDOUT,
            env=env,
            # Its own process group: the script `exec`s uv, which starts python.
            # Killing only the pid we hold leaves the server behind, listening.
            start_new_session=True,
        )
        return self

    def banner(self) -> str:
        self.log.flush()
        self.log.seek(0)
        self.out = self.log.read()
        return self.out

    def wait_until_answering(self, host: str, port: int) -> bool:
        deadline = time.time() + BOOT_TIMEOUT
        self.last_error = None
        while time.time() < deadline:
            if self.proc is not None and self.proc.poll() is not None:
                return False
            if self.ca_path.is_file():
                try:
                    status, _, _ = _get(host, port, "/healthz", self.ca_path, timeout=5.0)
                    if status == 200:
                        return True
                except (OSError, ssl.SSLError) as exc:
                    self.last_error = f"{type(exc).__name__}: {exc}"
            time.sleep(0.25)
        return False

    def __exit__(self, *exc) -> None:
        if self.proc is not None and self.proc.poll() is None:
            os.killpg(os.getpgid(self.proc.pid), signal.SIGTERM)
            try:
                self.proc.wait(timeout=10)
            except subprocess.TimeoutExpired:  # pragma: no cover - a wedged server
                os.killpg(os.getpgid(self.proc.pid), signal.SIGKILL)
                self.proc.wait(timeout=10)
        print("\n[run-app] banner:\n" + self.banner())
        self.log.close()


# --------------------------------------------------------------------------
# the script itself
# --------------------------------------------------------------------------


def test_the_command_exists_and_is_runnable() -> None:
    """One command means one file a reader can run, not a line to reassemble."""
    assert SCRIPT.is_file(), f"{SCRIPT} is not there"
    assert os.access(SCRIPT, os.X_OK), (
        f"{SCRIPT} is not executable, so `scripts/run-app.sh` is not a command a "
        "reader can run -- they would have to know to say `bash` first"
    )


def test_help_names_the_decisions() -> None:
    r = subprocess.run([str(SCRIPT), "--help"], cwd=str(REPO), capture_output=True, text=True)
    print(f"\n[run-app] --help exit={r.returncode}\n{r.stdout}")
    assert r.returncode == 0, r.stderr
    assert "--host" in r.stdout and "--port" in r.stdout
    assert "8788" in r.stdout, "the help does not say which port it serves on by default"
    assert "127.0.0.1" in r.stdout, "the help does not name the loopback/SSH-tunnel case"
    assert "HTTPS" in r.stdout, "the help does not say HTTPS is always on"


def test_a_port_that_is_not_a_number_is_refused_before_anything_starts() -> None:
    """Refused by name, and nothing launched -- an exit 2 with no server up.

    The wrong this catches: passing the value straight through and letting
    `app.serve` fail somewhere inside argparse, after `uv` has resolved, with a
    message about a module the reader never typed.
    """
    r = subprocess.run(
        [str(SCRIPT), "--port", "eight-thousand"], cwd=str(REPO), capture_output=True, text=True
    )
    print(f"\n[run-app] --port eight-thousand -> exit={r.returncode}: {r.stderr.strip()}")
    assert r.returncode == 2
    assert "number" in r.stderr.lower()
    assert "eight-thousand" in r.stderr, "the refusal does not name what was actually given"


# --------------------------------------------------------------------------
# the server it starts
# --------------------------------------------------------------------------


def test_the_app_answers_https_on_the_url_the_command_prints(tmp_path: Path) -> None:
    """The acceptance line, read literally: the printed URL answers, over TLS,
    with a certificate the printed CA actually verifies.

    The URL is taken FROM the banner rather than rebuilt from the port, because
    a banner that printed the wrong URL is exactly the defect worth catching and
    a test that composed its own would never see it.
    """
    port = _free_port()
    with Server("--host", "127.0.0.1", "--port", str(port), tls_dir=tmp_path / "tls") as server:
        assert server.wait_until_answering("127.0.0.1", port), (
            f"nothing answered on 127.0.0.1:{port} within {BOOT_TIMEOUT}s "
            f"(last connect error: {server.last_error}):\n{server.banner()}"
        )
        banner = server.banner()
        printed = re.search(r"open:\s+(https://\S+)", banner)
        assert printed, f"the command printed no HTTPS URL to open:\n{banner}"
        url = printed.group(1)
        assert url == f"https://127.0.0.1:{port}", (
            f"the printed URL is not the one it is serving on: {url!r} vs port {port}"
        )
        assert "ca fingerprint" in banner.lower(), "the banner never names the CA fingerprint"
        assert "/setup" in banner, "the banner does not point at the trust-instructions page"

        host, printed_port = url[len("https://") :].split(":")
        status, _, body = _get(host, int(printed_port), "/healthz", server.ca_path)
        print(f"[run-app] GET {url}/healthz -> {status} {body.strip()}")
        assert status == 200, f"the printed URL does not answer: {status}"

        # The gate is up: every other route is behind the sign-in, and a server
        # that answered 200 here would be one with no gate at all.
        status, location, _ = _get(host, int(printed_port), "/", server.ca_path)
        print(f"[run-app] GET {url}/ -> {status} -> {location}")
        assert status in (302, 303, 307), f"/ was not sent to the sign-in: {status}"
        assert "/login" in location, location


def test_the_certificate_fails_closed_without_the_right_ca(tmp_path: Path) -> None:
    """A client that does NOT carry the server's own CA is refused by TLS
    itself -- there is no plain-HTTP fallback and no "trust anything" mode."""
    port = _free_port()
    with Server("--host", "127.0.0.1", "--port", str(port), tls_dir=tmp_path / "tls") as server:
        assert server.wait_until_answering("127.0.0.1", port), server.banner()
        wrong_ca = tmp_path / "unrelated-ca.crt"
        other_dir = tmp_path / "other-tls"
        from app import tls as tls_mod

        made = tls_mod.ensure(tls_dir=other_dir, extra_host="127.0.0.1")
        wrong_ca.write_bytes(made.ca_cert.read_bytes())
        with pytest.raises(ssl.SSLError):
            _get("127.0.0.1", port, "/healthz", wrong_ca, timeout=5.0)
        print("[run-app] a foreign CA does not verify this server's certificate -- fails closed")


def test_the_sign_in_it_names_is_the_sign_in_the_page_asks_for(tmp_path: Path) -> None:
    """The banner's promise, reconciled against the page's own words.

    Two ways this goes wrong and both are silent: the banner naming a sign-in
    the app does not use, or the login page asking for something the banner
    never mentioned. So neither is trusted -- each is read where it lives.
    """
    port = _free_port()
    with Server("--host", "127.0.0.1", "--port", str(port), tls_dir=tmp_path / "tls") as server:
        assert server.wait_until_answering("127.0.0.1", port), server.banner()
        banner = server.banner()
        said = re.search(r"sign in:\s+(.+)", banner)
        assert said, f"the command says nothing about how to get in:\n{banner}"
        print(f"[run-app] banner sign-in: {said.group(1).strip()}")
        assert "account" in said.group(1), said.group(1)
        assert "password" in banner.lower() and "PAM" in banner, (
            "the banner does not name the machine account and the check behind it"
        )

        status, _, page = _get("127.0.0.1", port, "/login", server.ca_path)
        print(f"[run-app] GET /login -> {status}")
        assert status == 200
        for asked in ("Sign in with your account on this machine", "Username", "Password"):
            assert asked in page, (
                f"the sign-in page does not carry {asked!r}, so the banner is describing "
                "a sign-in this app does not offer"
            )


def test_a_wrong_password_is_refused_and_the_issued_cookie_gets_in(tmp_path: Path) -> None:
    """As much of "the reader can sign in" as a test can honestly reach.

    The half a test cannot reach is a real password: this machine's own
    account, and nothing here knows one. That half is a check only a person
    can make, and it is named as one rather than faked with a stub -- a
    monkeypatched `authenticate` would prove the test's own stub answers True.

    The two halves it CAN reach are the two halves that go wrong silently: a
    wrong password quietly letting someone in, and the sign-in issuing a cookie
    the gate then refuses.
    """
    port = _free_port()
    with Server("--host", "127.0.0.1", "--port", str(port), tls_dir=tmp_path / "tls") as server:
        assert server.wait_until_answering("127.0.0.1", port), server.banner()

        status, location = _post(
            "127.0.0.1", port, "/login", {"username": "tester", "password": "definitely-wrong"}, server.ca_path
        )
        print(f"[run-app] POST /login (wrong password) -> {status} -> {location}")
        assert status == 302 and "error=" in location, (
            f"a wrong password was not refused: {status} -> {location!r}"
        )

        # The cookie the sign-in issues, made the way the sign-in makes it --
        # same secret file, same issuer -- and handed back to the running gate.
        cookie = auth.Sessions(auth.read_or_make_secret()).issue("tester")
        status, page = _get_with_cookie("127.0.0.1", port, "/", cookie, server.ca_path)
        print(f"[run-app] GET / with the cookie a sign-in issues -> {status}")
        assert status == 200, f"the cookie a sign-in issues does not open the page: {status}"
        assert "<title>" in page.lower() or "converge" in page.lower(), page[:200]


def test_it_binds_every_interface_unless_asked_for_loopback(tmp_path: Path) -> None:
    """Every interface is the default; `--host 127.0.0.1` is the explicit,
    named way back to loopback-only -- the SSH-tunnel case.

    Checked by connecting from this machine's own LAN address, not by reading
    the flag back out of the banner: the banner is what a wrapper claims and
    the socket is what it did.
    """
    lan = _lan_address()
    if not lan:
        pytest.skip("this machine has no non-loopback address to test the LAN default against")

    quiet = _free_port()
    with Server("--host", "127.0.0.1", "--port", str(quiet), tls_dir=tmp_path / "tls-loopback") as server:
        assert server.wait_until_answering("127.0.0.1", quiet), server.banner()
        assert "bound to 127.0.0.1 only" in server.banner(), server.banner()
        with pytest.raises((OSError, ssl.SSLError)):
            _get(lan, quiet, "/healthz", server.ca_path, timeout=3.0)
        print(f"[run-app] --host 127.0.0.1: {lan}:{quiet} refused, 127.0.0.1:{quiet} answers")

    loud = _free_port()
    with Server("--port", str(loud), tls_dir=tmp_path / "tls-lan") as server:
        assert server.wait_until_answering("127.0.0.1", loud), server.banner()
        status, _, _ = _get(lan, loud, "/healthz", server.ca_path, timeout=5.0)
        print(f"[run-app] default (every interface): GET https://{lan}:{loud}/healthz -> {status}")
        assert status == 200, f"the default did not put the app on this network: {status}"
        assert socketlib.gethostname() in server.banner(), (
            "the default printed no address another device could open"
        )


# --------------------------------------------------------------------------
# where a reader is told about it
# --------------------------------------------------------------------------


def test_the_readme_names_the_command_under_the_start_section() -> None:
    """`converge-sf1u`: "Run the app" sits under the start section and names
    one command, what appears, and how managers show up."""
    text = (REPO / "README.md").read_text(encoding="utf-8")
    start = text.find("## Start your first manager session")
    assert start != -1, "README.md has no start section for the app section to sit under"
    end = text.find("\n## ", start + 1)
    section = text[start : end if end != -1 else len(text)]

    assert re.search(r"^#{3}\s+.*\bRun the app\b", section, re.M), (
        "README.md has no 'Run the app' heading under 'Start your first manager session'"
    )
    assert "scripts/run-app.sh" in section, "the section names no command"
    assert "8788" in section, "the section does not say where the app answers"
    assert re.search(r"\bregist", section), (
        "the section does not say how manager sessions appear -- registration is the answer"
    )
    assert "app/README.md" in section, (
        "the section does not point at app/README.md for running it as a service"
    )
    print(f"\n[run-app] README 'Run the app' section: {len(section.splitlines())} lines")


def test_the_agent_context_tells_a_session_how_to_run_it() -> None:
    """`converge-sf1u`: a reader in any Converge session learns it in one
    paragraph -- so the paragraph has to be in the context every session loads,
    not only in a README nobody in a session reads."""
    text = (REPO / "context" / "converge-awareness.md").read_text(encoding="utf-8")
    assert "scripts/run-app.sh" in text, (
        "context/converge-awareness.md does not name the command that runs the app"
    )
    assert "8788" in text
    assert re.search(r"\bregist", text), (
        "the awareness context does not say how a manager session shows up in the app"
    )


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-s", *sys.argv[1:]]))
