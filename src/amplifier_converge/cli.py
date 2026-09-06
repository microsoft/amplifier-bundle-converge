"""`amplifier-converge` — the command line for this package.

The `web` subcommand this command existed to carry served the earlier
server-rendered page in `web/`. Both were retired on 2026-09-06 on the intent
steward's word. The app you open beside a project is `app/`, started with
`scripts/run-app.sh`; what remains here is the library it reads through.
"""

from __future__ import annotations

import argparse

from . import __version__


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="amplifier-converge",
        description=(
            "The readers and writers behind Converge. There is no subcommand: "
            "the page this command used to serve was retired on 2026-09-06, and "
            "the app you open beside a project is started with scripts/run-app.sh."
        ),
    )
    parser.add_argument("--version", action="version", version=f"amplifier-converge {__version__}")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    parser.parse_args(argv)
    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
