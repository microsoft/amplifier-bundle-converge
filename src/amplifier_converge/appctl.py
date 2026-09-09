"""The library behind `amplifier-converge start/doctor/register`.

`cli.py` is a thin Click wrapper: every command it offers is one call into a
function here. That split exists so the app's start/doctor/register behavior
is testable, and usable, without going through Click at all.

**Why `bundle_root()` matters more than it looks.** An Amplifier bundle is
installed once, into its own cache directory, wherever that happens to be on
a given machine. A participant working in some OTHER project's workspace
still needs one command that runs THIS bundle's app, its scripts and its
templates -- not a copy they have to clone, and not a second package they
have to separately `pip install`. `bundle_root()` resolves from this very
module's own installed `__file__`, so `start`/`doctor`/`register` always
operate on the bundle's own checkout, wherever the bundle system put it,
regardless of the caller's current working directory.

**What needs the `app` extra, and what does not.** `start` and `register`
only ever shell out (`scripts/run-app.sh`, `scripts/register-manager.py`) or
use the standard library -- they work with the base package alone. `doctor`
is the one command that ALSO wants to import `app.tls`/`app.config` (to read
certificate and workspace state); it does that import lazily, inside a
`try/except`, precisely so it can still answer -- reporting the `app` extra
itself as MISSING -- when that extra was never installed. A base-only
install must never crash on `amplifier-converge doctor`; the whole point of
`doctor` is telling a reader what to install next.
"""

from __future__ import annotations

import importlib.util
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

#: Every module doctor checks for, and what its absence costs. Kept as data,
#: not a chain of `if`s, so adding a dependency is one line.
_DEPENDENCIES: tuple[tuple[str, str], ...] = (
    ("fastapi", "the app itself does not run without it"),
    ("uvicorn", "nothing serves the app's routes without it"),
    ("jinja2", "every HTML page -- login, setup, the shell -- fails to render"),
    ("itsdangerous", "the session cookie cannot be signed or read"),
    ("cryptography", "the local CA and leaf certificate cannot be made -- no HTTPS at all"),
    ("pam", "sign-in has nothing to check a password against"),
)


def bundle_root() -> Path:
    """The absolute root of the checkout this package resolves from.

    This file lives at `<root>/src/amplifier_converge/appctl.py` in a source
    checkout (an editable install, or `uv run --project <root>` -- the
    normal way an Amplifier bundle runs this); `parents[2]` is `<root>` from
    there. That is NOT where `scripts/*` land in a wheel built from this
    project and installed elsewhere (`pip install`, `uv tool install`): the
    wheel's `packages = ["src/amplifier_converge", "app"]` drops the `src/`
    level, so this same file sits at `<site-packages>/amplifier_converge/
    appctl.py` there, and `parents[2]` would escape `site-packages`
    entirely. `_scripts_dir` below is what actually resolves `scripts/*`
    correctly in both cases (converge-b2ak https-repair item 4); this
    function is kept, unchanged, for the source-checkout callers (`start`'s
    subprocess `cwd`, and the doctor checks that `sys.path.insert` it to
    import `app.*` when running from source) that always want THIS
    resolution.
    """
    return Path(__file__).resolve().parents[2]


def _wheel_scripts_dir() -> Path | None:
    """Where `scripts/*` land in a wheel built from this project: a
    top-level sibling of the installed `amplifier_converge` package, named
    `amplifier_converge_scripts` (`pyproject.toml`'s `force-include`).

    None when that sibling is not there at all -- i.e. this is a source
    checkout, not an installed wheel, and `bundle_root() / "scripts"` is the
    right answer instead (see `_scripts_dir`).
    """
    installed_package_dir = Path(__file__).resolve().parent
    candidate = installed_package_dir.parent / "amplifier_converge_scripts"
    return candidate if candidate.is_dir() else None


def running_from_installed_wheel() -> bool:
    """True when `scripts/run-app.sh` is not sitting beside `bundle_root()`
    the way a source checkout has it -- i.e. this package was installed
    from a built wheel into some other environment, and there is no adjacent
    `pyproject.toml`/`uv` project for `run-app.sh`'s own `uv run --extra app`
    to resolve against."""
    return not (bundle_root() / "scripts" / "run-app.sh").is_file()


def _scripts_dir() -> Path:
    """`scripts/` in a source checkout; `amplifier_converge_scripts/` beside
    this package when installed from a built wheel (converge-b2ak
    https-repair item 4 -- see `bundle_root`'s docstring for why these
    differ)."""
    source = bundle_root() / "scripts"
    if source.is_dir():
        return source
    wheel = _wheel_scripts_dir()
    return wheel if wheel is not None else source


def run_app_script() -> Path:
    return _scripts_dir() / "run-app.sh"


def register_manager_script() -> Path:
    return _scripts_dir() / "register-manager.py"


def install_check_script() -> Path:
    return _scripts_dir() / "install-check.py"


# --------------------------------------------------------------------------
# start -- run the app beside this bundle's own checkout
# --------------------------------------------------------------------------


def start_argv(
    host: str | None = None,
    port: int | None = None,
    config: str | None = None,
    state: str | None = None,
    tls_dir: str | None = None,
    instance_dir: str | None = None,
    extra_args: tuple[str, ...] = (),
) -> list[str]:
    """The exact command `start` runs -- built here so it can be shown or
    tested without actually launching a server.

    Two shapes, chosen by `running_from_installed_wheel`. A source checkout
    (or `uv run --project <bundle root>`, the normal Amplifier-bundle path)
    runs `scripts/run-app.sh`, unchanged -- it is what prints the friendly
    banner and picks the LAN-by-default bind. An installed wheel has no
    adjacent `pyproject.toml` for that script's own `uv run --extra app` to
    resolve against, so it invokes `app.serve`'s module directly with THIS
    interpreter instead -- the one already running `amplifier-converge`,
    which already has the `app` extra's dependencies installed beside it,
    since that is what installing the extra means (converge-b2ak
    https-repair item 4). `--host` is made explicit in that second shape
    (defaulting to every interface) because the LAN-by-default choice
    normally lives in `run-app.sh`'s own argument parsing, which this path
    bypasses entirely.
    """
    if running_from_installed_wheel():
        argv = [sys.executable, "-m", "app.serve", "--host", host or "0.0.0.0"]
    else:
        argv = [str(run_app_script())]
        if host:
            argv += ["--host", host]
    if port:
        argv += ["--port", str(port)]
    if config:
        argv += ["--config", config]
    if state:
        argv += ["--state", state]
    if tls_dir:
        argv += ["--tls-dir", tls_dir]
    if instance_dir:
        argv += ["--instance-dir", instance_dir]
    argv += list(extra_args)
    return argv


def start(
    host: str | None = None,
    port: int | None = None,
    config: str | None = None,
    state: str | None = None,
    tls_dir: str | None = None,
    instance_dir: str | None = None,
    extra_args: tuple[str, ...] = (),
) -> int:
    """Run the app beside this install -- a source checkout's
    `scripts/run-app.sh`, or an installed wheel's `app.serve` module invoked
    directly with this same interpreter (see `start_argv`).

    This is the whole of what makes "no source clone, no second mandatory
    install" true either way: the script (or the `app` package) and its
    templates and static assets are already sitting wherever the bundle
    system or `pip`/`uv` put them -- so this only ever has to point a
    subprocess at them, never fetch or build anything itself.
    """
    wheel_mode = running_from_installed_wheel()
    if not wheel_mode:
        script = run_app_script()
        if not script.is_file():
            print(
                f"amplifier-converge: no {script} -- this does not look like an "
                "amplifier-converge checkout (bundle_root() resolved to "
                f"{bundle_root()})",
                file=sys.stderr,
            )
            return 1
    argv = start_argv(host, port, config, state, tls_dir, instance_dir, extra_args)
    print(f"amplifier-converge: {' '.join(argv)}", file=sys.stderr)
    # A source checkout's `run-app.sh` wants its own repo root as `cwd`
    # (it `cd`s there itself, but a predictable `cwd` costs nothing); an
    # installed wheel's direct module invocation names everything by
    # absolute/importable paths and needs no particular `cwd` at all, so
    # `bundle_root()` (which is NOT a meaningful directory in that case --
    # see its docstring) is never used for it.
    proc = subprocess.run(argv, cwd=None if wheel_mode else str(bundle_root()))
    return proc.returncode


# --------------------------------------------------------------------------
# register -- wraps scripts/register-manager.py; the logic stays there
# --------------------------------------------------------------------------


def _load_register_module():
    """`scripts/register-manager.py`, loaded as a module rather than copied.

    It is a script, not a package member, so the only way to reuse its
    actual logic -- rather than re-typing it here and letting the two drift
    -- is to load it by path and call its own `main()`.
    """
    path = register_manager_script()
    if not path.is_file():
        raise FileNotFoundError(f"no {path} -- is this an amplifier-converge checkout?")
    spec = importlib.util.spec_from_file_location("_amplifier_converge_register_manager", path)
    if spec is None or spec.loader is None:  # pragma: no cover - defensive
        raise ImportError(f"could not load {path} as a module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def register(argv: list[str] | None = None) -> int:
    """This manager session's registration -- `scripts/register-manager.py`'s
    own `main()`, called directly rather than re-implemented."""
    module = _load_register_module()
    return int(module.main(argv))


# --------------------------------------------------------------------------
# doctor -- read-only, side-effect-free
# --------------------------------------------------------------------------

OK = "OK"
MISSING = "MISSING"
SKIP = "SKIP"


@dataclass
class DoctorRow:
    id: str
    status: str
    detail: str
    degradation: str = ""

    def as_dict(self) -> dict:
        row = {"id": self.id, "status": self.status, "detail": self.detail}
        if self.degradation:
            row["degradation"] = self.degradation
        return row


def _check_import(name: str, degradation: str) -> DoctorRow:
    try:
        present = importlib.util.find_spec(name) is not None
    except (ImportError, ValueError):  # pragma: no cover - a broken finder, not a missing module
        present = False
    if present:
        return DoctorRow(name, OK, f"{name} is importable")
    return DoctorRow(name, MISSING, f"{name} is not importable", degradation)


def _check_tmux() -> DoctorRow:
    found = shutil.which("tmux")
    if found:
        return DoctorRow("tmux", OK, f"tmux is on PATH at {found}")
    return DoctorRow("tmux", MISSING, "tmux is not on PATH", "the manager session's console/terminal viewer has nothing to show")


def _check_pam_service() -> DoctorRow:
    """Read-only: does this machine's PAM stack even have a `login` service
    file. Never touches it, never authenticates against it -- authenticate
    calls PAM itself, at sign-in time, and that IS the real check; this only
    says whether the door PAM would use exists at all."""
    candidates = (Path("/etc/pam.d/login"), Path("/etc/pam.d/common-auth"))
    for path in candidates:
        if path.is_file():
            return DoctorRow("pam-service", OK, f"a PAM service file exists at {path}")
    return DoctorRow(
        "pam-service", MISSING,
        f"no PAM service file at any of: {', '.join(str(c) for c in candidates)}",
        "sign-in will fail even with the right password -- PAM has nothing to check it against",
    )


def _check_certificate(tls_dir: str | None, host: str | None) -> DoctorRow:
    root = bundle_root()
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    try:
        from app import tls as app_tls  # noqa: PLC0415 - deliberately lazy, see module docstring
    except ImportError as exc:
        return DoctorRow(
            "certificate", SKIP,
            f"could not import app.tls ({exc}) -- install the `app` extra to check this",
        )
    wanted_hosts, wanted_ips = app_tls.default_names(host)
    insp = app_tls.inspect(Path(tls_dir) if tls_dir else None, hostnames=wanted_hosts, ips=wanted_ips)
    if not insp.ca_present or not insp.leaf_present:
        return DoctorRow(
            "certificate", MISSING,
            f"no certificate at {insp.tls_dir} yet -- `amplifier-converge start` creates one on first run",
        )
    status = OK if not insp.problems else MISSING
    detail = (
        f"leaf expires {insp.leaf_expires}, covers {insp.leaf_sans}"
        if status == OK
        else "; ".join(insp.problems)
    )
    return DoctorRow("certificate", status, detail)


def _check_discovered(host: str | None) -> DoctorRow:
    root = bundle_root()
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    try:
        from app import config as app_config  # noqa: PLC0415
    except ImportError as exc:
        return DoctorRow(
            "workspaces", SKIP,
            f"could not import app.config ({exc}) -- install the `app` extra to check this",
        )
    found = app_config.load()
    return DoctorRow(
        "workspaces", OK,
        f"{len(found.managers)} manager session(s) discovered under: "
        f"{', '.join(str(w) for w in found.workspaces) or '(no workspace roots)'}",
    )


def doctor(host: str | None = None, port: int = 8788, tls_dir: str | None = None) -> dict:
    """Every check, read-only: what would go wrong, and why -- never a side
    effect, never a generated certificate, never a write."""
    rows: list[DoctorRow] = [
        _check_import(name, degradation) for name, degradation in _DEPENDENCIES
    ]
    rows.append(_check_tmux())
    rows.append(_check_pam_service())
    rows.append(_check_certificate(tls_dir, host))
    rows.append(_check_discovered(host))

    bind = f"{host or '0.0.0.0 (every interface, the default)'}:{port}"
    return {
        "bundle_root": str(bundle_root()),
        "intended_bind": bind,
        "checks": [r.as_dict() for r in rows],
        "required_missing": sum(1 for r in rows if r.status == MISSING),
    }


def doctor_ok(report: dict) -> bool:
    return report.get("required_missing", 1) == 0


def render_doctor_table(report: dict) -> str:
    lines = [
        "amplifier-converge doctor",
        f"  bundle root: {report['bundle_root']}",
        f"  intended bind: {report['intended_bind']}",
        "",
    ]
    width = max((len(row["id"]) for row in report["checks"]), default=8)
    for row in report["checks"]:
        mark = {OK: "ok     ", MISSING: "MISSING", SKIP: "skipped"}.get(row["status"], row["status"])
        lines.append(f"  {mark}  {row['id']:<{width}}  {row['detail']}")
        if row.get("degradation"):
            lines.append(f"  {'':7}  {'':<{width}}  -> {row['degradation']}")
    lines.append("")
    missing = report["required_missing"]
    lines.append("nothing missing." if missing == 0 else f"{missing} check(s) need attention above.")
    return "\n".join(lines)


__all__ = [
    "MISSING",
    "OK",
    "SKIP",
    "DoctorRow",
    "bundle_root",
    "doctor",
    "doctor_ok",
    "install_check_script",
    "register",
    "register_manager_script",
    "render_doctor_table",
    "run_app_script",
    "start",
    "start_argv",
]
