"""The wheel this project builds actually carries what a reader needs.

Acceptance #1 (converge-b2ak): "Wheel includes needed app/templates/assets/
scripts. Starting via bundle-resolved absolute root with uv --project and app
extras works without a source clone or second mandatory install."

Two things are proven here, both against a REAL build -- `uv build --wheel`,
not a reading of `pyproject.toml`'s intentions:

1. the wheel's own file listing carries `app/templates`, `app/static`,
   `app/tls.py` and the three `scripts/*` commands a reader is told to run;
2. `amplifier_converge.appctl.bundle_root()` resolves correctly whichever way
   this package got onto `sys.path` -- proving the "no source clone, no
   second install" claim is about where the CODE resolves from, not merely
   about which files a wheel happens to contain.

Building a real wheel is slow enough that this file keeps it to ONE build,
shared by every test via a module-scoped fixture.
"""

from __future__ import annotations

import http.client
import json
import os
import signal
import socket as socketlib
import ssl
import subprocess
import sys
import time
import zipfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def built_wheel(tmp_path_factory: pytest.TempPathFactory) -> Path:
    out = tmp_path_factory.mktemp("wheel-out")
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
def wheel_names(built_wheel: Path) -> list[str]:
    with zipfile.ZipFile(built_wheel) as z:
        return z.namelist()


def test_the_wheel_carries_the_app_templates_and_static_assets(wheel_names: list[str]) -> None:
    must_have = [
        "app/templates/login.html",
        "app/templates/setup.html",
        "app/templates/shell.html",
        "app/static/js/api.js",
        "app/static/js/tmux.js",
        "app/static/manifest.webmanifest",
        "app/static/sw.js",
    ]
    missing = [name for name in must_have if name not in wheel_names]
    assert not missing, f"the wheel is missing: {missing}"


def test_the_wheel_carries_the_https_and_auth_modules(wheel_names: list[str]) -> None:
    must_have = ["app/tls.py", "app/auth.py", "app/serve.py", "app/config.py"]
    missing = [name for name in must_have if name not in wheel_names]
    assert not missing, f"the wheel is missing: {missing}"


def test_the_wheel_carries_the_three_named_scripts(wheel_names: list[str]) -> None:
    """`README.md`/`app/README.md` point a reader at these three by name;
    a wheel install that lacked them would have working code but no
    documented way to run it."""
    must_have = [
        "amplifier_converge_scripts/run-app.sh",
        "amplifier_converge_scripts/register-manager.py",
        "amplifier_converge_scripts/install-check.py",
    ]
    missing = [name for name in must_have if name not in wheel_names]
    assert not missing, f"the wheel is missing: {missing}"


def test_the_wheel_does_not_carry_the_apps_own_test_suite(wheel_names: list[str]) -> None:
    """A reader's install is not obligated to carry the test suite that
    proved it -- and shipping it bloats every install for no reader benefit."""
    leaked = [name for name in wheel_names if name.startswith("app/tests/")]
    assert not leaked, f"the wheel carries test files it should not: {leaked[:5]}"


def test_the_cli_entry_point_is_declared(wheel_names: list[str], built_wheel: Path) -> None:
    with zipfile.ZipFile(built_wheel) as z:
        entry_points = z.read("amplifier_converge-0.1.0.dist-info/entry_points.txt").decode("utf-8")
    assert "amplifier-converge" in entry_points
    assert "amplifier_converge.cli:main" in entry_points


def test_click_is_a_base_dependency_not_only_an_app_extra() -> None:
    """`amplifier_converge.cli` imports `click` unconditionally -- so a
    base-only install (no `--extra app`) must still be able to run
    `amplifier-converge --help` and `doctor`, which is how a reader finds out
    the app extra is what is missing. `doctor` cannot need the extra it
    exists to say is absent."""
    text = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    import re

    base = re.search(r'(?ms)^\[project\]\n.*?^dependencies\s*=\s*\[(.*?)\]', text)
    assert base, "no base [project] dependencies array found"
    assert "click" in base.group(1), (
        "click is not a base dependency -- a base-only install of "
        "amplifier-converge would crash on its own --help"
    )


def test_bundle_root_resolves_to_the_repository_this_test_runs_in() -> None:
    """The "bundle-resolved absolute root" claim, proven directly: whatever
    directory this package's own `__file__` sits under is what `start`,
    `doctor` and `register` operate on -- never the caller's cwd."""
    sys.path.insert(0, str(REPO_ROOT / "src"))
    from amplifier_converge import appctl

    root = appctl.bundle_root()
    assert root == REPO_ROOT, f"bundle_root() resolved to {root}, not {REPO_ROOT}"
    assert appctl.run_app_script() == REPO_ROOT / "scripts" / "run-app.sh"
    assert appctl.run_app_script().is_file()


def test_start_argv_never_depends_on_the_current_working_directory(tmp_path: Path) -> None:
    """The same command is built whether invoked from the bundle's own
    checkout or from an unrelated directory -- proving "any workspace"."""
    import os

    sys.path.insert(0, str(REPO_ROOT / "src"))
    from amplifier_converge import appctl

    here = appctl.start_argv(host="127.0.0.1", port=9)
    cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        elsewhere = appctl.start_argv(host="127.0.0.1", port=9)
    finally:
        os.chdir(cwd)
    assert here == elsewhere
    assert here[0] == str(REPO_ROOT / "scripts" / "run-app.sh")


# --------------------------------------------------------------------------
# converge-b2ak https-repair item 4: the wheel this project builds actually
# RUNS, installed fresh into a venv that has never seen this checkout --
# not just "the right files are in the zip" (the tests above), which is
# exactly the gap the review found: `bundle_root()` assumed the source
# checkout's `parents[2]/scripts` layout even inside a wheel install, where
# `scripts/*` land at a top-level `amplifier_converge_scripts/` instead (see
# `appctl.bundle_root`'s docstring). Every one of these tests runs the
# INSTALLED CONSOLE SCRIPT, from a directory that is not this checkout, with
# no source on `sys.path`/`PYTHONPATH` at all.
# --------------------------------------------------------------------------


@pytest.fixture(scope="module")
def installed_wheel_venv(built_wheel: Path, tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A fresh venv, outside any checkout, with this wheel's `app` extra
    installed into it -- and nothing else of this repository anywhere near
    it. Returns the venv's root; `<venv>/bin/amplifier-converge` is the
    console script under test."""
    venv_dir = tmp_path_factory.mktemp("wheel-venv") / "venv"
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


def _run_installed(venv_dir: Path, *args: str, cwd: Path, timeout: float = 30.0) -> subprocess.CompletedProcess:
    """The installed console script, run from `cwd` (deliberately NOT this
    checkout) with no source `PYTHONPATH` -- proving resolution comes from
    the installed package's own `__file__`, never this repository."""
    exe = venv_dir / "bin" / "amplifier-converge"
    assert exe.is_file(), f"no console script at {exe}"
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    return subprocess.run(
        [str(exe), *args], cwd=str(cwd), capture_output=True, text=True, timeout=timeout, env=env
    )


def test_help_and_doctor_run_from_an_installed_wheel_outside_any_checkout(
    installed_wheel_venv: Path, tmp_path: Path
) -> None:
    elsewhere = tmp_path / "not-a-checkout"
    elsewhere.mkdir()
    help_run = _run_installed(installed_wheel_venv, "--help", cwd=elsewhere)
    print(f"\n[wheel-venv] --help -> {help_run.returncode}\n{help_run.stdout}")
    assert help_run.returncode == 0, help_run.stderr

    doctor_run = _run_installed(installed_wheel_venv, "doctor", "--json-only", cwd=elsewhere)
    print(f"[wheel-venv] doctor -> {doctor_run.returncode}\n{doctor_run.stdout}")
    report = json.loads(doctor_run.stdout)
    # The whole point: `bundle_root` no longer needs to BE the checkout for
    # doctor to find its dependencies and its own certificate/workspace
    # checks -- it now resolves wherever this wheel actually landed, which is
    # somewhere under this installed venv, never this repository.
    print(f"[wheel-venv] doctor bundle_root: {report['bundle_root']}")
    assert str(REPO_ROOT) not in report["bundle_root"], (
        "doctor resolved back to the source checkout instead of the installed wheel"
    )
    # "certificate" is honestly MISSING here -- nothing has called `start`
    # yet in this venv to generate one, which is doctor's own documented
    # story ("amplifier-converge start creates one on first run"), not a
    # packaging defect. Every dependency/tooling/PAM row must be OK, though:
    # that IS what installing the `app` extra into this venv promised.
    missing = [row for row in report["checks"] if row["status"] == "MISSING" and row["id"] != "certificate"]
    assert not missing, f"doctor reports missing dependencies inside its own venv: {missing}"


def test_start_actually_serves_https_from_an_installed_wheel(installed_wheel_venv: Path, tmp_path: Path) -> None:
    """The full runtime proof: `amplifier-converge start`, installed fresh,
    invoked from an unrelated directory, actually answers HTTPS -- with
    templates/static assets served and a real CA-verified TLS handshake --
    which a wheel that only *looked* complete (the earlier tests in this
    file) would not prove."""
    elsewhere = tmp_path / "not-a-checkout"
    elsewhere.mkdir()
    tls_dir = tmp_path / "tls"
    instance_dir = tmp_path / "instance"

    s = socketlib.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()

    exe = installed_wheel_venv / "bin" / "amplifier-converge"
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    proc = subprocess.Popen(
        [
            str(exe), "start", "--host", "127.0.0.1", "--port", str(port),
            "--tls-dir", str(tls_dir), "--instance-dir", str(instance_dir),
        ],
        cwd=str(elsewhere),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        start_new_session=True,
    )
    try:
        ca_path = tls_dir / "ca.crt"
        deadline = time.time() + 60
        ok = False
        last_error = ""
        while time.time() < deadline:
            if proc.poll() is not None:
                break
            if ca_path.is_file():
                try:
                    ctx = ssl.create_default_context(cafile=str(ca_path))
                    conn = http.client.HTTPSConnection("127.0.0.1", port, timeout=5.0, context=ctx)
                    conn.request("GET", "/healthz")
                    r = conn.getresponse()
                    if r.status == 200:
                        ok = True
                        conn.close()
                        break
                    conn.close()
                except (OSError, ssl.SSLError) as exc:
                    last_error = f"{type(exc).__name__}: {exc}"
            time.sleep(0.25)
        assert ok, f"the installed wheel's server never answered (last error: {last_error})"

        # Served templates/assets/icons, per the acceptance line: /login and
        # /setup are read-only HTML the wheel must carry (see the earlier
        # wheel-contents tests), and this proves they actually RENDER, not
        # merely that the files exist in the zip.
        ctx = ssl.create_default_context(cafile=str(ca_path))
        for path in ("/login", "/setup"):
            conn = http.client.HTTPSConnection("127.0.0.1", port, timeout=5.0, context=ctx)
            conn.request("GET", path)
            r = conn.getresponse()
            r.read()
            print(f"[wheel-venv] GET {path} -> {r.status}")
            assert r.status == 200, f"{path} did not render from the installed wheel: {r.status}"
            conn.close()
        assert instance_dir.joinpath("secret").is_file(), (
            "an isolated --instance-dir did not get its own secret file"
        )
    finally:
        if proc.poll() is None:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                proc.wait(timeout=10)
        out = proc.stdout.read() if proc.stdout else ""
        print(f"[wheel-venv] server output:\n{out}")
