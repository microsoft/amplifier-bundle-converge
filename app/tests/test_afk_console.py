"""converge-c6cv: one canonical manager console target, distinct sockets included.

The bug this file proves fixed: a registered steward's live preview logged
``GET /api/tmux/default/vision-focused-team-ci 200`` (the viewer attached
fine) immediately followed by ``POST .../keys 403`` (their own keystrokes
were refused) -- and the toast said "Not delivered to the session: no
session attached", which was false. The session WAS attached; the server's
own send-authorization guard (`config.AppConfig.manager_for_tmux`) simply
did not understand that this manager's own console ran on a DIFFERENT tmux
socket than its worker lanes, because it compared `tmux_socket` (the
lanes' socket) and `manager_tmux` (the console's session name) as two
separate, literal fields -- which only ever matched when both happened to
sit on the same socket. Every test module written before this one for the
console/tmux surfaces (`test_console_live_rendered.py`,
`test_preview_https_instance.py`) used the SAME socket for both, so this
gap had no test at all.

Two things this file proves that nothing else does:

1. A manager whose own console genuinely runs on a different tmux socket
   than its worker lanes can still be typed into -- both at the unit level
   (`config.py`) and end to end, in a real browser against two real,
   independent tmux servers (never the same socket twice, unlike the
   existing rendered-console fixture).
2. A refusal that reaches the gate (steward mismatch) is shown to the
   steward TRUTHFULLY -- the server's own reason, not a swallowed HTTP
   status collapsed into "no session attached".

Socket naming follows `conftest.py`'s convention exactly: `cvafk-<role>-
<pid>-<random>`, so two runs on this host (the normal case here -- ten
lanes at once) can never share, see, or kill each other's tmux server.
This file uses TWO such sockets per browser fixture -- one standing in for
a batch's worker lanes, one for the manager's own console -- specifically
because every prior fixture used one socket for both and could not have
caught this. `conftest.py`'s session-scoped reaper sweeps both by PID at
the end of the run regardless of how this module's own teardown fares.
"""

from __future__ import annotations

import os
import shutil
import socket as socketlib
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app import auth, config, serve  # noqa: E402

GOOD_USER = "tester"
GOOD_PASSWORD = "hunter2"
STRANGER = "someone-else"

#: Two independent sockets, never the same one -- see the module docstring.
#: `-w-` stands for the worker lanes' socket, `-m-` for the manager's OWN
#: console socket. Both carry this run's pid, per `conftest.py`.
WORKER_SOCK = f"cvafk-w-{os.getpid()}-{uuid.uuid4().hex[:8]}"
MGR_SOCK = f"cvafk-m-{os.getpid()}-{uuid.uuid4().hex[:8]}"
SESSION = "mgr"  # the SAME session name exists on BOTH sockets -- see below
MARKER = "ZZAFKCONSOLEZZ"

MANUAL_PROCEDURE = """
MANUAL PROCEDURE -- run this by hand if tmux or Playwright is unavailable.
Each step says what you must SEE; seeing anything else is a failure.

Setup
  WSOCK="cvafk-w-$$"; MSOCK="cvafk-m-$$"     # two DIFFERENT sockets
  tmux -L "$MSOCK" new -d -s mgr cat          # the manager's OWN console
  tmux -L "$WSOCK" new -d -s mgr cat          # a DECOY, same session name,
                                               # different socket -- must
                                               # never receive anything
  Point ~/.amplifier/converge-app.toml at a manager with
    tmux_socket = "$WSOCK"        # the worker lanes' socket
    manager_tmux = "$MSOCK:mgr"   # combined form: a DIFFERENT socket
  uv run --extra app python -m app.serve --host 127.0.0.1 --port 8788
  Sign in, open the manager, open the console.

Check 1 -- the console attaches to the manager's OWN socket
  SEE: the console footer reads "Attached to tmux: $MSOCK:mgr", not $WSOCK.

Check 2 -- typing arrives at the manager's socket, and ONLY that one
  Type ZZAFKCONSOLEZZ and press Enter.
  Run: tmux -L "$MSOCK" capture-pane -p -t '=mgr:'   -- SEE the marker.
  Run: tmux -L "$WSOCK" capture-pane -p -t '=mgr:'   -- SEE it absent.
  FAILS IF: the line 403s, or the decoy on $WSOCK ever shows the marker.

Teardown
  tmux -L "$MSOCK" kill-server
  tmux -L "$WSOCK" kill-server
"""


def _skip_reason() -> str:
    if shutil.which("tmux") is None:
        return "tmux is not installed"
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(args=["--no-sandbox"])
            browser.close()
    except Exception as exc:  # pragma: no cover - environment dependent
        return f"chromium is not launchable: {str(exc).splitlines()[0]}"
    return ""


SKIP = _skip_reason()
needs_live = pytest.mark.skipif(bool(SKIP), reason=f"{SKIP}; use MANUAL_PROCEDURE in this file instead")


def test_manual_procedure_is_documented():
    assert "capture-pane" in MANUAL_PROCEDURE
    assert "FAILS IF" in MANUAL_PROCEDURE
    if SKIP:
        print(f"\nLive check unavailable ({SKIP}). Manual procedure:\n{MANUAL_PROCEDURE}")


# ==========================================================================
# 1. unit level -- config.py's canonical target, no tmux process involved
# ==========================================================================


def _manager(**overrides) -> config.ManagerConfig:
    fields = {
        "id": "demo",
        "name": "Demo",
        "tmux_socket": "workersock",
        "manager_tmux": "",
        "steward": "wren",
    }
    fields.update(overrides)
    return config.ManagerConfig(**fields)


def test_console_target_is_none_with_nothing_recorded():
    assert _manager(manager_tmux="").console_target() is None
    assert _manager(manager_tmux="   ").console_target() is None


def test_console_target_bare_form_pairs_with_this_managers_own_tmux_socket():
    """The ordinary case: one socket for a manager's lanes AND its own console."""
    mc = _manager(tmux_socket="workersock", manager_tmux="mgr-session")
    assert mc.console_target() == ("workersock", "mgr-session")


def test_console_target_combined_form_uses_the_named_socket_not_tmux_socket():
    """The regression this file exists for: a manager's own console on a
    DIFFERENT socket than its worker lanes, exactly the shape observed in
    the live preview's registration (`manager_tmux="default:vision-focused-
    team-ci"` while `tmux_socket` named the worker lanes' own socket)."""
    mc = _manager(tmux_socket="workersock", manager_tmux="mgrsock:mgr-session")
    print(f"\ntmux_socket={mc.tmux_socket!r} manager_tmux={mc.manager_tmux!r} "
          f"-> console_target={mc.console_target()}")
    assert mc.console_target() == ("mgrsock", "mgr-session"), (
        "the combined form must resolve to the socket IT names, never the "
        "worker lanes' tmux_socket"
    )


def test_console_target_a_malformed_combined_form_is_none():
    """`socket:` or `:session` -- half of the pair missing -- refuses rather
    than guessing, the same fail-closed rule `steward` follows."""
    assert _manager(manager_tmux="mgrsock:").console_target() is None
    assert _manager(manager_tmux=":mgr-session").console_target() is None


def test_manager_for_tmux_matches_a_console_on_a_different_socket_than_its_lanes():
    """THE regression proof. Before converge-c6cv, `manager_for_tmux` compared
    `tmux_socket`/`manager_tmux` as separate literal fields and this returned
    None -- the exact 403 the live preview hit."""
    app_conf = config.AppConfig(managers=(_manager(tmux_socket="workersock", manager_tmux="mgrsock:mgr-session"),))
    found = app_conf.manager_for_tmux("mgrsock", "mgr-session")
    print(f"\nmanager_for_tmux('mgrsock', 'mgr-session') -> {found.id if found else None}")
    assert found is not None and found.id == "demo"


def test_manager_for_tmux_refuses_the_worker_socket_even_with_the_right_session_name():
    """No fall-through, and no permission inferred from a session NAME alone:
    the worker socket paired with the console's session name is still not
    the manager's own console, because the console genuinely lives elsewhere."""
    app_conf = config.AppConfig(managers=(_manager(tmux_socket="workersock", manager_tmux="mgrsock:mgr-session"),))
    found = app_conf.manager_for_tmux("workersock", "mgr-session")
    print(f"\nmanager_for_tmux('workersock', 'mgr-session') -> {found.id if found else None}")
    assert found is None


def test_manager_for_tmux_still_matches_the_legacy_bare_same_socket_form():
    """The ordinary, pre-existing shape must keep working unchanged."""
    app_conf = config.AppConfig(managers=(_manager(tmux_socket="workersock", manager_tmux="mgr-session"),))
    assert app_conf.manager_for_tmux("workersock", "mgr-session") is not None
    assert app_conf.manager_for_tmux("elsewhere", "mgr-session") is None


def test_manager_payload_carries_the_canonical_managerConsole_field():
    from app import data

    mc = _manager(tmux_socket="workersock", manager_tmux="mgrsock:mgr-session")
    payload = data.manager_payload(mc)
    print(f"\nmanagerConsole: {payload['managerConsole']}")
    assert payload["managerConsole"] == {"socket": "mgrsock", "session": "mgr-session"}
    # Legacy fields are untouched -- any consumer reading them directly
    # still gets exactly what it always did.
    assert payload["tmuxSocket"] == "workersock"
    assert payload["managerTmux"] == "mgrsock:mgr-session"


def test_manager_payload_managerConsole_is_none_with_nothing_recorded():
    from app import data

    payload = data.manager_payload(_manager(manager_tmux=""))
    assert payload["managerConsole"] is None


# ==========================================================================
# 2. the HTTP guard, real gate, no real tmux server needed for a refusal
# ==========================================================================


class _FakePam:
    def authenticate(self, username: str, password: str, service: str = "login") -> bool:
        return username == GOOD_USER and password == GOOD_PASSWORD


@pytest.fixture(autouse=True)
def _fake_pam(monkeypatch) -> None:
    monkeypatch.setattr(auth.pam_module, "pam", _FakePam)


def _make_app(tmp_path: Path, *, steward: str | None, tmux_socket: str, manager_tmux: str):
    conf = tmp_path / f"conf-{uuid.uuid4().hex[:6]}.toml"
    lines = [
        "[[managers]]\n",
        'id = "demo"\n',
        'name = "demo"\n',
        f'tmux_socket = "{tmux_socket}"\n',
        f'manager_tmux = "{manager_tmux}"\n',
    ]
    if steward is not None:
        lines.append(f'steward = "{steward}"\n')
    conf.write_text("".join(lines), encoding="utf-8")
    return serve.create_app(
        config_path=conf,
        secret_path=tmp_path / "secret",
        state_path=tmp_path / "state.json",
        sessions_path=tmp_path / "sessions.json",
    )


def _sign_in(client, user: str = GOOD_USER) -> None:
    answer = client.post("/login", data={"username": user, "password": GOOD_PASSWORD, "next": "/"})
    assert answer.status_code == 302, answer.text


def test_keys_delivered_when_the_managers_console_socket_differs_from_its_worker_socket(tmp_path: Path) -> None:
    """The end-to-end guard proof, without a real tmux server: the registered
    steward, sending to the manager's OWN (different) socket, is not 403'd."""
    from fastapi.testclient import TestClient

    app = _make_app(tmp_path, steward=GOOD_USER, tmux_socket="workersock", manager_tmux="mgrsock:mgr-session")
    client = TestClient(app, follow_redirects=False)
    _sign_in(client)
    answer = client.post("/api/tmux/mgrsock/mgr-session/keys", json={"keys": "echo hi", "enter": True})
    print(f"\nPOST to the manager's OWN socket -> {answer.status_code} {answer.text}")
    assert answer.status_code != 403, answer.text


def test_keys_refused_on_the_worker_socket_even_though_the_session_name_matches(tmp_path: Path) -> None:
    """The worker socket is never treated as the manager's console just
    because a session there happens to share its console's session NAME."""
    from fastapi.testclient import TestClient

    app = _make_app(tmp_path, steward=GOOD_USER, tmux_socket="workersock", manager_tmux="mgrsock:mgr-session")
    client = TestClient(app, follow_redirects=False)
    _sign_in(client)
    answer = client.post("/api/tmux/workersock/mgr-session/keys", json={"keys": "echo hi", "enter": True})
    print(f"\nPOST to the WORKER socket -> {answer.status_code} {answer.json()}")
    assert answer.status_code == 403, answer.text
    assert "no registered manager owns this tmux session" in answer.json()["error"]


def test_keys_refused_for_a_stranger_even_on_the_managers_own_distinct_socket(tmp_path: Path) -> None:
    """Distinct sockets do not weaken steward authority: a signed-in user
    who is not the registered steward is still refused, by name."""
    from fastapi.testclient import TestClient

    app = _make_app(tmp_path, steward=STRANGER, tmux_socket="workersock", manager_tmux="mgrsock:mgr-session")
    client = TestClient(app, follow_redirects=False)
    _sign_in(client, GOOD_USER)
    answer = client.post("/api/tmux/mgrsock/mgr-session/keys", json={"keys": "echo hi", "enter": True})
    print(f"\nPOST from a stranger, distinct-socket manager -> {answer.status_code} {answer.json()}")
    assert answer.status_code == 403, answer.text
    said = answer.json()["error"]
    assert STRANGER in said and GOOD_USER in said, said


def test_view_reads_the_managers_own_socket_and_stay_open_to_any_signed_in_user(tmp_path: Path) -> None:
    """The read side is unaffected by the write-only steward gate, and was
    already resolving the combined form correctly before this fix -- this
    just pins that it still does, on the manager's OWN distinct socket."""
    from fastapi.testclient import TestClient

    app = _make_app(tmp_path, steward=STRANGER, tmux_socket="workersock", manager_tmux="mgrsock:mgr-session")
    client = TestClient(app, follow_redirects=False)
    _sign_in(client, GOOD_USER)
    answer = client.get("/api/tmux/mgrsock/mgr-session")
    assert answer.status_code not in (401, 403), answer.text


# ==========================================================================
# 3. real tmux, two real sockets, a real browser -- the round trip itself
# ==========================================================================


def _tmux(socket: str, *args: str, check: bool = False) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env.pop("TMUX", None)
    return subprocess.run(["tmux", "-L", socket, *args], capture_output=True, text=True, env=env, check=check)


def _pane(socket: str, session: str = SESSION) -> str:
    return _tmux(socket, "capture-pane", "-p", "-t", f"={session}:").stdout


def _refuse_if_already_up(socket: str) -> None:
    if _tmux(socket, "ls").returncode == 0:
        pytest.fail(
            f"a tmux server is already running on socket {socket!r}, which this run "
            "expected to have to itself. Refusing to kill it."
        )


@pytest.fixture(scope="module")
def two_tmux_servers():
    """Two INDEPENDENT tmux servers, each with its own `mgr` session.

    The worker socket's `mgr` is a DECOY: it must never receive the marker
    this file sends, because that is exactly the cross-socket bleed the
    original bug's guard could have masked (a session on the wrong socket
    happening to share a name). `cat` echoes what it receives, so each
    pane's own text is the proof, never the app's own report of itself.
    """
    if SKIP:
        pytest.skip(SKIP)
    _refuse_if_already_up(WORKER_SOCK)
    _refuse_if_already_up(MGR_SOCK)
    try:
        _tmux(MGR_SOCK, "new", "-d", "-s", SESSION, "cat", check=True)
        _tmux(WORKER_SOCK, "new", "-d", "-s", SESSION, "cat", check=True)  # the decoy
        time.sleep(1.0)
        yield
    finally:
        _tmux(MGR_SOCK, "kill-server")
        _tmux(WORKER_SOCK, "kill-server")


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "user.name=Test", "-c", "user.email=test@example.invalid", *args],
        cwd=repo, check=True, capture_output=True,
    )


@pytest.fixture(scope="module")
def project(tmp_path_factory) -> dict:
    tmp_path = tmp_path_factory.mktemp("afk-console")
    repo = tmp_path / "demo-repo"
    (repo / "docs").mkdir(parents=True)
    (repo / "docs" / "VISION.md").write_text(
        "# Demo Vision (DRAFT)\n\n## Where this is going\n\nOne place each.\n", encoding="utf-8"
    )
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "seed")

    batch = tmp_path / "hw-demo"
    (batch / "lanes").mkdir(parents=True)
    (batch / "goals").mkdir()
    (batch / "HIGHWAY.md").write_text("# Highway\n\nWidth 1.\n", encoding="utf-8")
    (batch / "manifest.tsv").write_text("lane\tworktree\tbranch\tbase\ttmux\tgoal\tlog\tstarted\n", encoding="utf-8")

    conf = tmp_path / "converge-app.toml"
    conf.write_text(
        "[[managers]]\n"
        'id = "demo"\n'
        'name = "Demo manager"\n'
        f'batch_dir = "{batch}"\n'
        f'repos = ["{repo}"]\n'
        'tracker_project = ""\n'
        'steward = "tester"\n'
        # The core of this fixture: two DIFFERENT sockets, never the same
        # one -- the shape every prior fixture in this repo never used.
        f'tmux_socket = "{WORKER_SOCK}"\n'
        f'manager_tmux = "{MGR_SOCK}:{SESSION}"\n',
        encoding="utf-8",
    )
    return {"config": conf, "secret": tmp_path / "secret", "state": tmp_path / "state.json",
            "sessions": tmp_path / "sessions.json"}


def _free_port() -> int:
    s = socketlib.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


@pytest.fixture(scope="module")
def server(project):
    import uvicorn

    made = serve.create_app(
        config_path=project["config"], secret_path=project["secret"],
        state_path=project["state"], sessions_path=project["sessions"],
    )
    port = _free_port()
    uv_server = uvicorn.Server(uvicorn.Config(made, host="127.0.0.1", port=port, log_level="warning"))
    thread = threading.Thread(target=uv_server.run, daemon=True)
    thread.start()
    deadline = time.time() + 20
    while not uv_server.started and time.time() < deadline:
        time.sleep(0.05)
    assert uv_server.started, "app server did not start"
    print(f"\napp server: http://127.0.0.1:{port}")
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


def _boot(browser, project, server, user, errors):
    sessions = auth.Sessions(auth.read_or_make_secret(project["secret"]))
    ctx = browser.new_context(viewport={"width": 1280, "height": 800})
    ctx.add_cookies([{"name": auth.COOKIE, "value": sessions.issue(user), "domain": "127.0.0.1", "path": "/"}])
    page = ctx.new_page()
    page.on("console", lambda m: errors.append(f"console.{m.type}: {m.text}") if m.type == "error" else None)
    page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
    page.goto(server, wait_until="networkidle")
    page.wait_for_selector(".home-manager-card", timeout=15000)
    page.click(".home-manager-card")
    page.wait_for_selector("#managerConsole", state="attached", timeout=15000)
    page.wait_for_function(
        "() => document.getElementById('consoleContextTitle').textContent.trim() !== '\u2014'",
        timeout=15000,
    )
    if page.evaluate("() => document.querySelector('.body-grid').classList.contains('console-closed')"):
        page.click("#consoleToggle")
        page.wait_for_timeout(300)
    page.wait_for_timeout(800)  # the first capture tick
    return ctx, page


@needs_live
def test_the_console_attaches_to_the_managers_own_socket_not_the_worker_socket(
    two_tmux_servers, project, server, browser
):
    errors: list[str] = []
    ctx, page = _boot(browser, project, server, GOOD_USER, errors)

    live = page.evaluate(
        """() => {
          const view = window.ConvergeTmux && window.ConvergeTmux.current();
          return {socket: view ? view.socket : null, session: view ? view.session : null,
                  writable: view ? view.writable : null};
        }"""
    )
    print(f"\nattached view: {live}")
    print(f"console errors: {errors or 'none'}")
    assert live["socket"] == MGR_SOCK, (
        f"attached to {live['socket']!r}, expected the manager's OWN socket {MGR_SOCK!r} "
        f"-- not the worker lanes' socket {WORKER_SOCK!r}"
    )
    assert live["session"] == SESSION
    assert live["writable"] is True
    assert not errors, f"the page reported errors: {errors}"
    ctx.close()


@needs_live
def test_a_line_typed_arrives_only_at_the_managers_own_socket(two_tmux_servers, project, server, browser):
    """THE end-to-end regression proof: before converge-c6cv this send 403'd
    (the guard could not resolve the manager's own, differently-socketed,
    console), and the steward saw a false "no session attached"."""
    errors: list[str] = []
    ctx, page = _boot(browser, project, server, GOOD_USER, errors)

    before_mgr = _pane(MGR_SOCK)
    before_worker = _pane(WORKER_SOCK)
    assert MARKER not in before_mgr and MARKER not in before_worker

    field = page.locator("#consoleForm input")
    field.fill(MARKER)
    field.press("Enter")

    deadline = time.time() + 8
    mgr_text = ""
    while time.time() < deadline:
        mgr_text = _pane(MGR_SOCK)
        if MARKER in mgr_text:
            break
        time.sleep(0.2)

    worker_text = _pane(WORKER_SOCK)
    print(f"\ntmux -L {MGR_SOCK} capture-pane (manager's own socket): {mgr_text.strip()!r}")
    print(f"tmux -L {WORKER_SOCK} capture-pane (worker socket, decoy): {worker_text.strip()!r}")
    print(f"console errors: {errors or 'none'}")

    assert MARKER in mgr_text, (
        "the typed line never reached the manager's OWN (distinct) tmux socket -- "
        "this is the exact 403 converge-c6cv fixes"
    )
    assert MARKER not in worker_text, (
        "the line leaked onto the WORKER socket's decoy session of the same name -- "
        "a cross-socket bleed, never acceptable on a write"
    )
    assert not errors, f"the page reported errors: {errors}"
    ctx.close()


@needs_live
def test_a_stranger_sees_the_real_refusal_reason_not_no_session_attached(
    two_tmux_servers, project, server, browser
):
    """converge-c6cv's third proof: a refusal that reaches the gate must be
    shown truthfully. Before this fix, `tmux.js` discarded the 403 body and
    the toast read a generic, false "no session attached" regardless of the
    real cause."""
    errors: list[str] = []
    ctx, page = _boot(browser, project, server, STRANGER, errors)

    field = page.locator("#consoleForm input")
    field.fill("this should be refused")
    field.press("Enter")
    page.wait_for_timeout(1200)

    note = page.evaluate(
        "() => { const v = window.ConvergeTmux && window.ConvergeTmux.current(); "
        "return v && v.last_send ? v.last_send.detail : null; }"
    )
    print(f"\nlast_send.detail for a non-steward: {note!r}")
    print(f"console errors: {errors or 'none'}")

    assert note, "no refusal detail was recorded at all"
    assert "no session attached" not in note.lower(), (
        f"the real refusal reason was swallowed and replaced with the generic phrase: {note!r}"
    )
    assert "steward" in note.lower() or STRANGER in note or GOOD_USER in note, (
        f"the UI did not carry the server's real reason: {note!r}"
    )

    after_mgr = _pane(MGR_SOCK)
    assert "this should be refused" not in after_mgr, "a refused keystroke must never reach the pane"
    # Chromium logs a devtools console.error for ANY non-2xx fetch response
    # -- "Failed to load resource: ... 403" -- regardless of how the page's
    # own JS handles it; that is the browser reporting the refusal we asked
    # for, not a page bug, so it is the one error text excluded here.
    real_errors = [e for e in errors if "403 (Forbidden)" not in e]
    assert not real_errors, f"the page reported errors: {real_errors}"
    ctx.close()
