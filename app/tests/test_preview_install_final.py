"""converge-iizz: what `tests/test_preview_packaging.py`'s wheel-venv tests do
not yet prove.

Three gaps, named in the acceptance this file exists to close:

1. **Workspace discovery from an installed wheel.** `app/config.py`'s
   `default_workspace_roots()` used to resolve from this app's own installed
   `__file__` -- correct for a source checkout (the app sits one level below
   the workspace it watches), silently wrong for a wheel install (that
   resolves to `site-packages` itself, or the Amplifier bundle cache a wheel
   happened to be built from). `register`, then `start`, from a real
   temporary workspace outside any checkout, proves the fix: the registered
   manager is discovered from the caller's own working directory, never from
   `site-packages`/the bundle cache, and an explicit `workspaces =` in
   `converge-app.toml` still overrides the default.

2. **Referenced runtime assets actually load.** `/login` and `/setup`
   mentioning `<link href="/static/css/...">` in their HTML is not the same
   as that CSS file actually being served -- a 404 with the right
   `Content-Type: text/html` still "mentions" the path. Every asset those two
   pages' rendered HTML references is fetched here and its status, content
   type and non-empty body are checked directly.

Every check below runs the wheel this project builds, installed fresh into a
venv `uv build --wheel` has never touched, from a directory that is not this
checkout, with `PYTHONPATH` stripped -- the same discipline
`tests/test_preview_packaging.py`'s own wheel-venv fixture uses, duplicated
here (rather than imported) so this file's ownership stays self-contained.
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
from urllib.parse import urlsplit

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

#: How long to wait for a real server to answer. Matches test_run_app.py's
#: own budget -- a cold `uv`/interpreter start is slower than a warm one.
BOOT_TIMEOUT = 60.0


def _free_port() -> int:
    s = socketlib.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def _ssl_context(ca_path: Path) -> ssl.SSLContext:
    """A real verifying context against the server's own generated CA --
    never `ssl._create_unverified_context()`."""
    return ssl.create_default_context(cafile=str(ca_path))


def _get(host: str, port: int, path: str, ca_path: Path, timeout: float = 5.0):
    conn = http.client.HTTPSConnection(host, port, timeout=timeout, context=_ssl_context(ca_path))
    try:
        conn.request("GET", path)
        r = conn.getresponse()
        body = r.read()
        return r.status, dict(r.headers), body
    finally:
        conn.close()


# --------------------------------------------------------------------------
# fixture: a real wheel, installed fresh into a venv this repository never
# touches -- built once and shared by every test in this file
# --------------------------------------------------------------------------


@pytest.fixture(scope="module")
def built_wheel(tmp_path_factory: pytest.TempPathFactory) -> Path:
    out = tmp_path_factory.mktemp("install-final-wheel-out")
    result = subprocess.run(
        ["uv", "build", "--wheel", "-o", str(out)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert result.returncode == 0, f"uv build failed:\n{result.stdout}\n{result.stderr}"
    wheels = sorted(out.glob("amplifier_converge-*.whl"))
    assert wheels, f"no wheel produced in {out}: {list(out.iterdir())}"
    return wheels[0]


@pytest.fixture(scope="module")
def installed_wheel_venv(built_wheel: Path, tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A fresh venv, outside any checkout, with this wheel's `app` extra
    installed -- and nothing else of this repository anywhere near it.
    Returns the venv root; `<venv>/bin/amplifier-converge` is under test."""
    venv_dir = tmp_path_factory.mktemp("install-final-wheel-venv") / "venv"
    made = subprocess.run(["uv", "venv", str(venv_dir)], capture_output=True, text=True, timeout=60)
    assert made.returncode == 0, f"uv venv failed:\n{made.stdout}\n{made.stderr}"
    python = venv_dir / "bin" / "python"
    assert python.is_file(), f"no interpreter at {python}"
    installed = subprocess.run(
        ["uv", "pip", "install", "--python", str(python), f"{built_wheel}[app]"],
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert installed.returncode == 0, f"uv pip install failed:\n{installed.stdout}\n{installed.stderr}"
    return venv_dir


def _no_pythonpath_env() -> dict:
    """This process's own environment, with `PYTHONPATH` stripped -- the
    installed console script must resolve `amplifier_converge`/`app` from
    the venv it was installed into, never from a source checkout that
    happens to be on `sys.path` some other way."""
    return {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}


def _isolated_child_env(isolated_home: Path) -> dict:
    """`_no_pythonpath_env()`, plus a `HOME` this repository has never
    touched -- converge-bbow.

    `app/config.py`'s `DEFAULT_CONFIG_PATH`, `app/state_store.py`'s
    `DEFAULT_STATE_PATH`, and `config.discover()`'s `Path.home() / "dev"`
    scan all resolve through `Path.home()`, which reads the `HOME`
    environment variable this process inherited. Leaving the real `HOME`
    in place made the "installed wheel, NO `--config` at all" test read
    THIS machine's own real `~/.amplifier/converge-app.toml` -- which on
    this host names real `workspaces = [...]` -- instead of exercising the
    documented no-config-file default-discovery path; reproduced directly:
    the child process's own banner listed this host's real configured
    workspaces, never the test's temporary caller workspace, and the run
    failed in 3.14s. `isolated_home` must be a fresh directory this test
    created itself (never the real `Path.home()`), with no `.amplifier/`
    inside it, so `config.load()`'s `have_file` is False and it takes its
    documented no-file branch.

    `CONVERGE_WORKSPACES` is stripped too -- the other documented override
    `config.load()` honours ahead of the default -- so a host that happens
    to export it cannot leak into an "installed wheel with no config"
    test the same way a real `converge-app.toml` did. Production
    precedence (an explicit `--config` or `workspaces =` still outranks
    the default) is untouched: this only changes which `HOME` the CHILD
    PROCESS sees, never `config.py`'s own resolution order.
    """
    env = _no_pythonpath_env()
    env["HOME"] = str(isolated_home)
    env.pop("CONVERGE_WORKSPACES", None)
    return env


def _fresh_home(base: Path) -> Path:
    """A new, empty directory under `base` for `_isolated_child_env` --
    never the real `Path.home()`, and never shared between tests."""
    home = base / "isolated-home"
    home.mkdir()
    return home


def _exe(venv_dir: Path) -> Path:
    found = venv_dir / "bin" / "amplifier-converge"
    assert found.is_file(), f"no console script at {found}"
    return found


def _stop_and_capture(proc: subprocess.Popen) -> str:
    """Stop the whole process group and return everything it printed.

    The installed `amplifier-converge start` console script itself spawns a
    CHILD `python -m app.serve` subprocess (`appctl.start`'s own
    `subprocess.run`) -- signalling only the parent pid (`proc.terminate()`/
    `proc.kill()`) leaves that child running, still holding the shared
    stdout pipe open, so `communicate()` never returns. `start_new_session`
    put both processes in one new process group; killing THAT (what every
    other server-process test in this project already does) is what
    actually stops both.
    """
    if proc.poll() is None:
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            proc.wait(timeout=10)
    return proc.stdout.read() if proc.stdout else ""


# --------------------------------------------------------------------------
# 1. help / doctor / register / start, run from an installed wheel, outside
#    any checkout, with no source PYTHONPATH -- and workspace discovery that
#    finds the caller's own workspace, never site-packages/the bundle cache
# --------------------------------------------------------------------------


def test_help_and_doctor_run_outside_any_checkout_with_no_source_path(
    installed_wheel_venv: Path, tmp_path: Path
) -> None:
    elsewhere = tmp_path / "not-a-checkout"
    elsewhere.mkdir()
    env = _isolated_child_env(_fresh_home(tmp_path))

    help_run = subprocess.run(
        [str(_exe(installed_wheel_venv)), "--help"], cwd=str(elsewhere), env=env,
        capture_output=True, text=True, timeout=30,
    )
    print(f"\n[install-final] --help -> {help_run.returncode}\n{help_run.stdout}")
    assert help_run.returncode == 0, help_run.stderr

    doctor_run = subprocess.run(
        [str(_exe(installed_wheel_venv)), "doctor", "--json-only"], cwd=str(elsewhere), env=env,
        capture_output=True, text=True, timeout=30,
    )
    print(f"[install-final] doctor -> {doctor_run.returncode}\n{doctor_run.stdout}")
    assert doctor_run.returncode in (0, 1), doctor_run.stderr  # 1 only for a genuinely-missing dep
    assert str(REPO_ROOT) not in doctor_run.stdout, "doctor resolved back to the source checkout"


def test_register_from_a_caller_workspace_writes_its_registration(
    installed_wheel_venv: Path, tmp_path: Path
) -> None:
    """`amplifier-converge register`, run with cwd inside a brand-new,
    ordinary directory that is not a git repository and holds no
    `WORKSPACE-MANIFEST.json` -- the honest "a project with no workspace
    around it is its own workspace" case `register-manager.py`'s own
    docstring names. No `--workspace` flag: this is the caller's own cwd,
    exactly as a reader typing the command from their project would have."""
    workspace = tmp_path / "caller-workspace"
    workspace.mkdir()
    env = _isolated_child_env(_fresh_home(tmp_path))

    register_run = subprocess.run(
        [str(_exe(installed_wheel_venv)), "register", "--id", "install-final-demo",
         "--steward", "tester", "--manager-tmux", "install-final-demo-console"],
        cwd=str(workspace), env=env, capture_output=True, text=True, timeout=30,
    )
    print(f"\n[install-final] register -> {register_run.returncode}\n{register_run.stdout}\n{register_run.stderr}")
    assert register_run.returncode == 0, register_run.stderr

    written = workspace / ".converge" / "install-final-demo" / "registration.toml"
    assert written.is_file(), f"register did not write {written}"
    text = written.read_text(encoding="utf-8")
    assert 'id = "install-final-demo"' in text
    assert 'steward = "tester"' in text


def test_starting_from_the_callers_workspace_discovers_it_not_site_packages(
    installed_wheel_venv: Path, tmp_path: Path
) -> None:
    """The acceptance line itself: register in a temporary workspace, start
    the installed wheel from that same workspace with NO `--config` at all,
    and the registered manager is discovered -- while the venv's own
    `site-packages` (where this wheel is actually installed) is never the
    workspace root scanned.

    Read off the server's own boot banner (`app/serve.py`'s `main()` prints
    every workspace root it scanned and every manager it found) rather than
    an authenticated API call: doctor and this print are both ordinary,
    unauthenticated ways to observe discovery, and the banner is the
    literal thing a reader watches when they run `start` for real.
    """
    workspace = tmp_path / "caller-workspace-2"
    workspace.mkdir()
    env = _isolated_child_env(_fresh_home(tmp_path))

    register_run = subprocess.run(
        [str(_exe(installed_wheel_venv)), "register", "--id", "install-final-start-demo",
         "--steward", "tester"],
        cwd=str(workspace), env=env, capture_output=True, text=True, timeout=30,
    )
    assert register_run.returncode == 0, register_run.stderr

    port = _free_port()
    tls_dir = tmp_path / "tls"
    instance_dir = tmp_path / "instance"
    proc = subprocess.Popen(
        [str(_exe(installed_wheel_venv)), "start", "--host", "127.0.0.1", "--port", str(port),
         "--tls-dir", str(tls_dir), "--instance-dir", str(instance_dir)],
        cwd=str(workspace), env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        start_new_session=True,
    )
    try:
        ca_path = tls_dir / "ca.crt"
        deadline = time.time() + BOOT_TIMEOUT
        ok = False
        while time.time() < deadline:
            if proc.poll() is not None:
                break
            if ca_path.is_file():
                try:
                    status, _, _ = _get("127.0.0.1", port, "/healthz", ca_path, timeout=5.0)
                    if status == 200:
                        ok = True
                        break
                except (OSError, ssl.SSLError):
                    pass
            time.sleep(0.25)
        assert ok, "the installed wheel's server never answered from the caller workspace"
    finally:
        out = _stop_and_capture(proc)
    print(f"\n[install-final] server banner from {workspace}:\n{out}")

    scanned_lines = [line for line in out.splitlines() if "workspace root scanned:" in line]
    assert f"workspace root scanned: {workspace}" in out, (
        f"the caller's own workspace ({workspace}) was never scanned:\n{out}"
    )
    assert not any(str(installed_wheel_venv) in line for line in scanned_lines), (
        f"the venv/site-packages tree was scanned as a workspace root:\n{scanned_lines}"
    )
    assert "manager install-final-start-demo" in out, (
        f"the registered manager was not discovered when started from its own workspace:\n{out}"
    )


def test_isolated_home_redirects_config_discovery_away_from_the_real_host(
    installed_wheel_venv: Path, tmp_path: Path
) -> None:
    """Synthetic control for `_isolated_child_env` itself -- converge-bbow.

    Proves the isolation mechanism actually redirects `config.load()`'s
    `DEFAULT_CONFIG_PATH` resolution, without ever touching or asserting on
    this machine's real `~/.amplifier/converge-app.toml`. A synthetic
    foreign config is planted at `<isolated_home>/.amplifier/converge-app.toml`
    -- naming a workspace and a manager id this test invents, neither of
    which the caller workspace below ever registers. Starting with NO
    `--config` must read that foreign, synthetic file (proving `HOME` in
    the child's environment governs discovery) and must NOT scan the
    caller workspace, exactly as a real ambient config with its own
    `workspaces = [...]` would override the default for any reader --
    the same mechanism that let this machine's real config leak into the
    no-config test before this fix, reproduced here with data this test
    owns instead of the real host's.
    """
    isolated_home = _fresh_home(tmp_path)
    foreign_workspace = tmp_path / "foreign-workspace-nobody-registers-here"
    foreign_workspace.mkdir()
    amplifier_dir = isolated_home / ".amplifier"
    amplifier_dir.mkdir()
    (amplifier_dir / "converge-app.toml").write_text(
        f'workspaces = ["{foreign_workspace}"]\n\n'
        '[[managers]]\n'
        'id = "synthetic-foreign-manager"\n'
        'name = "Synthetic Foreign Manager"\n',
        encoding="utf-8",
    )
    env = _isolated_child_env(isolated_home)

    caller_workspace = tmp_path / "caller-workspace-synthetic-control"
    caller_workspace.mkdir()
    register_run = subprocess.run(
        [str(_exe(installed_wheel_venv)), "register", "--id", "should-not-appear-either",
         "--steward", "tester"],
        cwd=str(caller_workspace), env=env, capture_output=True, text=True, timeout=30,
    )
    assert register_run.returncode == 0, register_run.stderr

    port = _free_port()
    tls_dir = tmp_path / "tls-synthetic-control"
    instance_dir = tmp_path / "instance-synthetic-control"
    proc = subprocess.Popen(
        [str(_exe(installed_wheel_venv)), "start", "--host", "127.0.0.1", "--port", str(port),
         "--tls-dir", str(tls_dir), "--instance-dir", str(instance_dir)],
        cwd=str(caller_workspace), env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        start_new_session=True,
    )
    try:
        ca_path = tls_dir / "ca.crt"
        deadline = time.time() + BOOT_TIMEOUT
        ok = False
        while time.time() < deadline:
            if proc.poll() is not None:
                break
            if ca_path.is_file():
                try:
                    status, _, _ = _get("127.0.0.1", port, "/healthz", ca_path, timeout=5.0)
                    if status == 200:
                        ok = True
                        break
                except (OSError, ssl.SSLError):
                    pass
            time.sleep(0.25)
        assert ok, "the server with the synthetic foreign config never answered"
    finally:
        out = _stop_and_capture(proc)
    print(f"\n[install-final] server banner with synthetic foreign HOME config:\n{out}")

    assert f"workspace root scanned: {foreign_workspace}" in out, (
        f"the synthetic foreign config's own workspace was never scanned -- HOME "
        f"redirection is not taking effect:\n{out}"
    )
    assert f"workspace root scanned: {caller_workspace}" not in out, (
        "the caller workspace was scanned even though the synthetic foreign "
        f"config named a different one -- HOME redirection is not taking effect:\n{out}"
    )
    assert "should-not-appear-either" not in out, (
        "a manager registered under the caller workspace leaked in despite the "
        f"synthetic foreign config's override:\n{out}"
    )


def test_explicit_workspaces_in_config_overrides_the_default(
    installed_wheel_venv: Path, tmp_path: Path
) -> None:
    """`converge-app.toml`'s own `workspaces = [...]` line replaces the
    default entirely -- a person's explicit answer outranks the discovered
    one, per `app/config.py`'s own `load()`. Started from a caller
    workspace that itself holds a registration, but pointed at a config
    naming a DIFFERENT, empty workspace: only the named one is scanned.
    """
    caller_workspace = tmp_path / "caller-workspace-3"
    caller_workspace.mkdir()
    env = _isolated_child_env(_fresh_home(tmp_path))
    register_run = subprocess.run(
        [str(_exe(installed_wheel_venv)), "register", "--id", "should-not-appear", "--steward", "tester"],
        cwd=str(caller_workspace), env=env, capture_output=True, text=True, timeout=30,
    )
    assert register_run.returncode == 0, register_run.stderr

    named_workspace = tmp_path / "named-workspace"
    named_workspace.mkdir()
    conf = tmp_path / "converge-app.toml"
    conf.write_text(f'workspaces = ["{named_workspace}"]\n', encoding="utf-8")

    port = _free_port()
    tls_dir = tmp_path / "tls-override"
    instance_dir = tmp_path / "instance-override"
    proc = subprocess.Popen(
        [str(_exe(installed_wheel_venv)), "start", "--host", "127.0.0.1", "--port", str(port),
         "--tls-dir", str(tls_dir), "--instance-dir", str(instance_dir), "--config", str(conf)],
        cwd=str(caller_workspace), env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        start_new_session=True,
    )
    try:
        ca_path = tls_dir / "ca.crt"
        deadline = time.time() + BOOT_TIMEOUT
        ok = False
        while time.time() < deadline:
            if proc.poll() is not None:
                break
            if ca_path.is_file():
                try:
                    status, _, _ = _get("127.0.0.1", port, "/healthz", ca_path, timeout=5.0)
                    if status == 200:
                        ok = True
                        break
                except (OSError, ssl.SSLError):
                    pass
            time.sleep(0.25)
        assert ok, "the server with an explicit --config never answered"
    finally:
        out = _stop_and_capture(proc)
    print(f"\n[install-final] server banner with explicit config:\n{out}")
    assert f"workspace root scanned: {named_workspace}" in out
    assert f"workspace root scanned: {caller_workspace}" not in out, (
        "the caller's own workspace was scanned even though the config named a different one"
    )
    assert "should-not-appear" not in out, (
        "a manager registered under the caller's workspace leaked in despite an explicit override"
    )


# --------------------------------------------------------------------------
# 2. every referenced runtime asset actually loads -- status, content type,
#    and a real, non-empty body -- not merely HTML that mentions the path
# --------------------------------------------------------------------------

_ASSET_ATTR = re.compile(r'(?:href|src)="(/(?:static|branding)/[^"]+|/manifest\.webmanifest)"')

#: `Content-Type` a `.css`/`.js`/`.png`/`.ico`/`.json`-shaped path must
#: answer with -- a mismatch (e.g. a 404 page served as `text/html`) is
#: exactly the silent failure this file exists to catch.
_EXPECTED_TYPE = {
    ".css": "text/css",
    ".js": "javascript",
    ".png": "image/png",
    ".ico": "image",
    ".webmanifest": "manifest+json",
}


def _expected_content_type(path: str) -> str | None:
    for suffix, marker in _EXPECTED_TYPE.items():
        if path.endswith(suffix):
            return marker
    return None


@pytest.fixture(scope="module")
def asset_server(installed_wheel_venv: Path, tmp_path_factory: pytest.TempPathFactory):
    """One running installed-wheel instance, shared by every asset test in
    this file -- assets are read-only, so there is no reason to boot a
    fresh server per assertion."""
    tmp_path = tmp_path_factory.mktemp("install-final-assets")
    elsewhere = tmp_path / "not-a-checkout"
    elsewhere.mkdir()
    tls_dir = tmp_path / "tls"
    instance_dir = tmp_path / "instance"
    port = _free_port()
    env = _isolated_child_env(_fresh_home(tmp_path))
    proc = subprocess.Popen(
        [str(_exe(installed_wheel_venv)), "start", "--host", "127.0.0.1", "--port", str(port),
         "--tls-dir", str(tls_dir), "--instance-dir", str(instance_dir)],
        cwd=str(elsewhere), env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        start_new_session=True,
    )
    ca_path = tls_dir / "ca.crt"
    deadline = time.time() + BOOT_TIMEOUT
    ok = False
    while time.time() < deadline:
        if proc.poll() is not None:
            break
        if ca_path.is_file():
            try:
                status, _, _ = _get("127.0.0.1", port, "/healthz", ca_path, timeout=5.0)
                if status == 200:
                    ok = True
                    break
            except (OSError, ssl.SSLError):
                pass
        time.sleep(0.25)
    if not ok:
        out = proc.stdout.read() if proc.stdout else ""
        proc.kill()
        pytest.fail(f"the installed wheel's server never answered:\n{out}")
    yield "127.0.0.1", port, ca_path
    if proc.poll() is None:
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            proc.wait(timeout=10)


@pytest.mark.parametrize("page", ["/login", "/setup"])
def test_the_pages_own_referenced_assets_all_load_for_real(asset_server, page: str) -> None:
    host, port, ca_path = asset_server
    status, headers, body = _get(host, port, page, ca_path)
    assert status == 200, f"{page} did not render: {status}"
    html = body.decode("utf-8", "replace")

    found = sorted(set(_ASSET_ATTR.findall(html)))
    assert found, f"{page} references no static/branding assets to verify -- the scrape itself is broken"
    print(f"\n[install-final] {page} references {len(found)} assets: {found}")

    failures: list[str] = []
    for asset_path in found:
        clean = urlsplit(asset_path).path
        a_status, a_headers, a_body = _get(host, port, clean, ca_path)
        content_type = a_headers.get("content-type", "")
        wanted = _expected_content_type(clean)
        ok = a_status == 200 and len(a_body) > 0 and (wanted is None or wanted in content_type.lower())
        print(f"[install-final]   GET {clean} -> {a_status} {content_type!r} ({len(a_body)} bytes)")
        if not ok:
            failures.append(
                f"{clean}: status={a_status} content-type={content_type!r} bytes={len(a_body)} "
                f"(wanted a {wanted!r} content type)" if wanted else
                f"{clean}: status={a_status} bytes={len(a_body)}"
            )
    assert not failures, "asset(s) referenced by " + page + " did not actually load:\n" + "\n".join(failures)


def test_the_ca_certificate_itself_is_servable_and_content_typed(asset_server) -> None:
    """`/setup` links `/ca.crt` -- not matched by the static/branding scrape
    above, so checked directly: a reader who clicks "download the CA" must
    get real certificate bytes, not an HTML page."""
    host, port, ca_path = asset_server
    status, headers, body = _get(host, port, "/ca.crt", ca_path)
    assert status == 200, status
    assert len(body) > 0
    assert b"BEGIN CERTIFICATE" in body, "/ca.crt did not serve PEM certificate bytes"


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-s", *sys.argv[1:]]))
