"""The one command that runs the app -- checked by running it.

`converge-sf1u`: `composition.v1` Core 5's shape, applied to the app rather than
to the install -- one command, nothing else to know. The command is
`scripts/run-app.sh`, and what it promises a reader is not "a server starts"
but three specific things:

* it serves on the URL it prints, and that URL answers;
* the sign-in it names is the sign-in the page actually asks for;
* it stays on loopback unless asked for the network, because putting the page
  on a network is a decision.

Every check below is against a real server this file starts and stops. There is
no fixture of the answer anywhere here: a wrapper that printed a URL nothing
was listening on would pass a mock and fails this.

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
import subprocess
import sys
import time
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "run-app.sh"

sys.path.insert(0, str(REPO))

from app import auth  # noqa: E402

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


def _get(host: str, port: int, path: str, timeout: float = 5.0):
    """(status, location, body) for one request, redirects NOT followed.

    Following them would hide the gate: `/` answering 200 after a redirect to
    `/login` reads exactly like `/` answering 200 because there is no gate.
    """
    conn = http.client.HTTPConnection(host, port, timeout=timeout)
    try:
        conn.request("GET", path)
        r = conn.getresponse()
        body = r.read().decode("utf-8", "replace")
        return r.status, r.headers.get("location", ""), body
    finally:
        conn.close()


def _post(host: str, port: int, path: str, form: dict[str, str], timeout: float = 5.0):
    """(status, location) for one form post, redirects NOT followed."""
    body = "&".join(f"{k}={v}" for k, v in form.items())
    conn = http.client.HTTPConnection(host, port, timeout=timeout)
    try:
        conn.request(
            "POST", path, body=body, headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        r = conn.getresponse()
        r.read()
        return r.status, r.headers.get("location", "")
    finally:
        conn.close()


def _get_with_cookie(host: str, port: int, path: str, cookie: str, timeout: float = 5.0):
    conn = http.client.HTTPConnection(host, port, timeout=timeout)
    try:
        conn.request("GET", path, headers={"Cookie": f"{auth.COOKIE}={cookie}"})
        r = conn.getresponse()
        return r.status, r.read().decode("utf-8", "replace")
    finally:
        conn.close()


class Server:
    """`scripts/run-app.sh` running for real, and stopped when we are done."""

    def __init__(self, *args: str) -> None:
        self.args = args
        self.proc: subprocess.Popen | None = None
        self.out = ""

    def __enter__(self) -> "Server":
        self.log = open(  # noqa: SIM115 - closed in __exit__
            os.path.join(os.environ.get("TMPDIR", "/tmp"), f"run-app-test-{os.getpid()}.log"),
            "w+",
            encoding="utf-8",
        )
        self.proc = subprocess.Popen(
            [str(SCRIPT), *self.args],
            cwd=str(REPO),
            stdout=self.log,
            stderr=subprocess.STDOUT,
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
        while time.time() < deadline:
            if self.proc is not None and self.proc.poll() is not None:
                return False
            try:
                status, _, _ = _get(host, port, "/healthz", timeout=2.0)
                if status == 200:
                    return True
            except OSError:
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


def test_help_names_the_two_decisions() -> None:
    r = subprocess.run([str(SCRIPT), "--help"], cwd=str(REPO), capture_output=True, text=True)
    print(f"\n[run-app] --help exit={r.returncode}\n{r.stdout}")
    assert r.returncode == 0, r.stderr
    assert "--lan" in r.stdout and "--port" in r.stdout
    assert "8788" in r.stdout, "the help does not say which port it serves on by default"


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


def test_the_app_answers_on_the_url_the_command_prints() -> None:
    """The acceptance line, read literally: the printed URL answers.

    The URL is taken FROM the banner rather than rebuilt from the port, because
    a banner that printed the wrong URL is exactly the defect worth catching and
    a test that composed its own would never see it.
    """
    port = _free_port()
    with Server("--port", str(port)) as server:
        assert server.wait_until_answering("127.0.0.1", port), (
            f"nothing answered on 127.0.0.1:{port} within {BOOT_TIMEOUT}s:\n{server.banner()}"
        )
        banner = server.banner()
        printed = re.search(r"open:\s+(http://\S+)", banner)
        assert printed, f"the command printed no URL to open:\n{banner}"
        url = printed.group(1)
        assert url == f"http://127.0.0.1:{port}", (
            f"the printed URL is not the one it is serving on: {url!r} vs port {port}"
        )

        host, printed_port = url[len("http://") :].split(":")
        status, _, body = _get(host, int(printed_port), "/healthz")
        print(f"[run-app] GET {url}/healthz -> {status} {body.strip()}")
        assert status == 200, f"the printed URL does not answer: {status}"

        # The gate is up: every other route is behind the sign-in, and a server
        # that answered 200 here would be one with no gate at all.
        status, location, _ = _get(host, int(printed_port), "/")
        print(f"[run-app] GET {url}/ -> {status} -> {location}")
        assert status in (302, 303, 307), f"/ was not sent to the sign-in: {status}"
        assert "/login" in location, location


def test_the_sign_in_it_names_is_the_sign_in_the_page_asks_for() -> None:
    """The banner's promise, reconciled against the page's own words.

    Two ways this goes wrong and both are silent: the banner naming a sign-in
    the app does not use, or the login page asking for something the banner
    never mentioned. So neither is trusted -- each is read where it lives.
    """
    port = _free_port()
    with Server("--port", str(port)) as server:
        assert server.wait_until_answering("127.0.0.1", port), server.banner()
        banner = server.banner()
        said = re.search(r"sign in:\s+(.+)", banner)
        assert said, f"the command says nothing about how to get in:\n{banner}"
        print(f"[run-app] banner sign-in: {said.group(1).strip()}")
        assert "account" in said.group(1), said.group(1)
        assert "password" in banner.lower() and "PAM" in banner, (
            "the banner does not name the machine account and the check behind it"
        )

        status, _, page = _get("127.0.0.1", port, "/login")
        print(f"[run-app] GET /login -> {status}")
        assert status == 200
        for asked in ("Sign in with your account on this machine", "Username", "Password"):
            assert asked in page, (
                f"the sign-in page does not carry {asked!r}, so the banner is describing "
                "a sign-in this app does not offer"
            )


def test_a_wrong_password_is_refused_and_the_issued_cookie_gets_in() -> None:
    """As much of "the reader can sign in" as a test can honestly reach.

    The half a test cannot reach is a real password: PAM checks it against this
    machine's own account, and nothing here knows one. That half is a check only
    a person can make, and it is named as one rather than faked with a stub --
    a monkeypatched `authenticate` would prove the test's own stub answers True.

    The two halves it CAN reach are the two halves that go wrong silently: a
    wrong password quietly letting someone in, and the sign-in issuing a cookie
    the gate then refuses.
    """
    port = _free_port()
    with Server("--port", str(port)) as server:
        assert server.wait_until_answering("127.0.0.1", port), server.banner()

        status, location = _post(
            "127.0.0.1", port, "/login", {"username": "tester", "password": "not-the-password"}
        )
        print(f"[run-app] POST /login (wrong password) -> {status} -> {location}")
        assert status == 302 and "error=" in location, (
            f"a wrong password was not refused: {status} -> {location!r}"
        )

        # The cookie the sign-in issues, made the way the sign-in makes it --
        # same secret file, same issuer -- and handed back to the running gate.
        cookie = auth.Sessions(auth.read_or_make_secret()).issue("tester")
        status, page = _get_with_cookie("127.0.0.1", port, "/", cookie)
        print(f"[run-app] GET / with the cookie a sign-in issues -> {status}")
        assert status == 200, f"the cookie a sign-in issues does not open the page: {status}"
        assert "<title>" in page.lower() or "converge" in page.lower(), page[:200]


def test_it_stays_on_loopback_unless_asked_for_the_network() -> None:
    """Loopback is the default; `--lan` is the decision, and it is a real one.

    Checked by connecting from this machine's own LAN address, not by reading
    the flag back out of the banner: the banner is what a wrapper claims and
    the socket is what it did.
    """
    lan = _lan_address()
    if not lan:
        pytest.skip("this machine has no non-loopback address to test --lan against")

    quiet = _free_port()
    with Server("--port", str(quiet)) as server:
        assert server.wait_until_answering("127.0.0.1", quiet), server.banner()
        assert "loopback only" in server.banner(), server.banner()
        with pytest.raises(OSError):
            _get(lan, quiet, "/healthz", timeout=3.0)
        print(f"[run-app] default: {lan}:{quiet} refused, 127.0.0.1:{quiet} answers")

    loud = _free_port()
    with Server("--lan", "--port", str(loud)) as server:
        assert server.wait_until_answering("127.0.0.1", loud), server.banner()
        status, _, _ = _get(lan, loud, "/healthz", timeout=5.0)
        print(f"[run-app] --lan: GET http://{lan}:{loud}/healthz -> {status}")
        assert status == 200, f"--lan did not put the app on this network: {status}"
        assert socketlib.gethostname() in server.banner(), (
            "--lan printed no address another device could open"
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
