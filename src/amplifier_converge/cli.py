"""`amplifier-converge` -- the command line for this package.

The `web` subcommand this command existed to carry served the earlier
server-rendered page in `web/`. Both were retired on 2026-09-06 on the intent
steward's word. The app you open beside a project is `app/`; this command's
job is running it, checking it, and registering a manager session against
it, from wherever this bundle happens to be installed -- `start`, `doctor`,
`register`. Every one of them is a thin wrapper: the actual logic lives in
`appctl.py`, which is what to read (or import directly) for anything more
than what Click's `--help` shows.
"""

from __future__ import annotations

import json

import click

from . import __version__, appctl


@click.group(invoke_without_command=True)
@click.version_option(__version__, prog_name="amplifier-converge")
@click.pass_context
def cli(ctx: click.Context) -> None:
    """The readers and writers behind Converge, and the app beside your project."""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())
        ctx.exit(1)


@cli.command(context_settings={"ignore_unknown_options": True})
@click.option(
    "--host",
    default=None,
    help="Bind address (default: every interface; pass 127.0.0.1 for the SSH-tunnel case)",
)
@click.option("--port", default=None, type=int, help="Port (default: 8788)")
@click.option("--config", default=None, help="Path to converge-app.toml")
@click.option("--state", default=None, help="Path to the read-point/kept-mark store")
@click.option("--tls-dir", default=None, help="Path to the local CA and leaf certificate")
@click.option(
    "--instance-dir",
    default=None,
    help=(
        "Isolate THIS preview's secret, cookie names and logout-revocation store "
        "from any other instance on this host (default: shared machine-wide files -- "
        "wrong for two instances run side by side, since cookies are never scoped "
        "by port)."
    ),
)
@click.argument("extra_args", nargs=-1, type=click.UNPROCESSED)
def start(host: str | None, port: int | None, config: str | None, state: str | None,
          tls_dir: str | None, instance_dir: str | None, extra_args: tuple[str, ...]) -> None:
    """Run the app beside this bundle's own checkout.

    Always HTTPS; there is no plain-HTTP mode. From a source checkout this is
    `scripts/run-app.sh`, run from `appctl.bundle_root()` -- the bundle's own
    resolved path, not wherever this command happens to be invoked from. From
    an installed wheel it is `app.serve` invoked directly with this same
    interpreter instead (see `appctl.start_argv`).
    """
    raise SystemExit(appctl.start(host=host, port=port, config=config, state=state,
                                   tls_dir=tls_dir, instance_dir=instance_dir, extra_args=extra_args))


@cli.command()
@click.option("--host", default=None, help="Bind address doctor should report against (default: every interface)")
@click.option("--port", default=8788, type=int, help="Port doctor should report against")
@click.option("--tls-dir", default=None, help="Path to the local CA and leaf certificate to inspect")
@click.option("--json-only", is_flag=True, help="Print only the JSON report, no table")
def doctor(host: str | None, port: int, tls_dir: str | None, json_only: bool) -> None:
    """Read-only: dependencies, PAM, tmux, certificate state, discovered
    workspaces and registrations, the intended bind. Never a side effect,
    never a generated certificate, never a request for a secret.
    """
    report = appctl.doctor(host=host, port=port, tls_dir=tls_dir)
    if not json_only:
        click.echo(appctl.render_doctor_table(report))
    click.echo(json.dumps(report, indent=2))
    raise SystemExit(0 if appctl.doctor_ok(report) else 1)


@cli.command(context_settings={"ignore_unknown_options": True})
@click.argument("register_args", nargs=-1, type=click.UNPROCESSED)
def register(register_args: tuple[str, ...]) -> None:
    """Write this manager session's registration.

    A thin call into `scripts/register-manager.py`'s own `main()` -- every
    flag it takes (`--workspace`, `--steward`, `--repo`, ...) works
    unchanged; see `scripts/register-manager.py --help`.
    """
    raise SystemExit(appctl.register(list(register_args)))


def main(argv: list[str] | None = None) -> int:
    try:
        cli(args=argv, prog_name="amplifier-converge")
    except SystemExit as exc:
        return int(exc.code or 0)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
