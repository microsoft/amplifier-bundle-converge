"""Sensor readings, parsed from a log file.

A reading is one line of the log: `<name> <value> [<unit>]`.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Reading:
    """One sensor reading."""

    name: str
    value: float
    unit: str = ""


def parse_line(line: str) -> Reading | None:
    """Parse one log line. Blank lines and `#` comments return None."""
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return None
    parts = stripped.split()
    if len(parts) < 2:
        raise ValueError(f"malformed reading: {line!r}")
    name, raw_value = parts[0], parts[1]
    unit = parts[2] if len(parts) > 2 else ""
    return Reading(name=name, value=float(raw_value), unit=unit)


def read_log(path: Path) -> list[Reading]:
    """Parse every reading in a log file, in file order."""
    readings: list[Reading] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        reading = parse_line(line)
        if reading is not None:
            readings.append(reading)
    return readings
