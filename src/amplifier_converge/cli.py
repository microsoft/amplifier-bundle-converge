"""`amplifier-converge` — the command that opens the page beside your project."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__

MISSING_WEB = """The web extra is not installed, so the page cannot be served.

Install it and try again:

    uv run --extra web amplifier-converge web --repo . --port 8091

or, if this is installed as a tool:

    uv tool install 'amplifier-converge[web]'
"""


def _project_name(repo: Path, given: str | None) -> str:
    if given:
        return given
    return repo.resolve().name.replace("amplifier-bundle-", "")


def _web(args: argparse.Namespace) -> int:
    repo = Path(args.repo).expanduser().resolve()
    if not repo.is_dir():
        print(f"There is no folder at {repo}.", file=sys.stderr)
        return 2

    try:
        import uvicorn

        from .web.app import create_app
    except ImportError:
        print(MISSING_WEB, file=sys.stderr)
        return 3

    project = _project_name(repo, args.project)
    batch_dir = Path(args.lanes).expanduser().resolve() if args.lanes else None
    app = create_app(
        repo,
        project,
        batch_dir=batch_dir,
        include_remote_proposals=not args.no_remote,
    )

    print(f"Converge — {repo.name}")
    print(f"  reading   {repo}")
    print(f"  queue     project “{project}”")
    print(f"  open      http://{args.host}:{args.port}/")
    print("  This page keeps nothing of its own. Stop it with Ctrl-C.")
    uvicorn.run(app, host=args.host, port=args.port, log_level=args.log_level)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="amplifier-converge",
        description=(
            "The companion page beside your project: Direction, Operation, "
            "and the four things you can do."
        ),
    )
    parser.add_argument("--version", action="version", version=f"amplifier-converge {__version__}")
    subparsers = parser.add_subparsers(dest="command")

    web = subparsers.add_parser("web", help="serve the page on this machine only")
    web.add_argument("--repo", default=".", help="the project to read (default: here)")
    web.add_argument("--port", type=int, default=8091, help="the port to listen on (default: 8091)")
    web.add_argument(
        "--host",
        default="127.0.0.1",
        help="the address to listen on. Loopback by default, on purpose.",
    )
    web.add_argument(
        "--project",
        default=None,
        help="the work-queue project name (default: taken from the folder name)",
    )
    web.add_argument(
        "--lanes",
        default=None,
        help="the lanes directory (default: found beside the project, if there is one)",
    )
    web.add_argument(
        "--no-remote",
        action="store_true",
        help="do not ask GitHub for teammates' proposals",
    )
    web.add_argument("--log-level", default="warning")
    web.set_defaults(func=_web)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "func", None):
        parser.print_help()
        return 1
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
