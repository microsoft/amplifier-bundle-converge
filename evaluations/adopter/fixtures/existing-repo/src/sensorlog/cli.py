"""sensorlog -- print a report or a summary for a sensor log file.

    python -m sensorlog.cli report  samples/day.log
    python -m sensorlog.cli summary samples/day.log
"""

from __future__ import annotations

import sys
from pathlib import Path

from sensorlog.readings import read_log
from sensorlog.report import render_report, render_summary

USAGE = "usage: sensorlog <report|summary> <logfile>"


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 2:
        print(USAGE, file=sys.stderr)
        return 2
    command, raw_path = args
    path = Path(raw_path)
    if not path.exists():
        print(f"sensorlog: no such file: {path}", file=sys.stderr)
        return 1
    readings = read_log(path)
    if command == "report":
        print(render_report(readings))
    elif command == "summary":
        print(render_summary(readings))
    else:
        print(USAGE, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
