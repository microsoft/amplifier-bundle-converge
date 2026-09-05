"""Turn parsed readings into the two reports the CLI prints."""

from __future__ import annotations

from sensorlog.readings import Reading


def render_report(readings: list[Reading]) -> str:
    """One line per reading, in file order."""
    lines = []
    for reading in readings:
        unit = reading.unit or "?"
        lines.append(f"{reading.name}: {reading.value} {unit}")
    return "\n".join(lines)


def render_summary(readings: list[Reading]) -> str:
    """Counts, and the mean of every reading that shares the commonest unit."""
    if not readings:
        return "0 readings"
    units = [r.unit for r in readings if r.unit]
    if not units:
        return f"{len(readings)} readings, no units"
    commonest = max(set(units), key=units.count)
    matching = [r.value for r in readings if r.unit == commonest]
    mean = sum(matching) / len(matching)
    return f"{len(readings)} readings, mean {mean:.2f} {commonest} over {len(matching)}"
