"""Lumen report — the public entry points.

Contract: contracts/lumen.v1.md, Core 2 — every public entry point is named in
`docs/INDEX.md`.
"""

from __future__ import annotations

from readings import all_readings


def render_report() -> str:
    """Public entry point. Named in docs/INDEX.md."""
    lines = []
    for reading in all_readings():
        unit = reading.unit or "?"
        lines.append(f"{reading.name}: {reading.value} {unit}")
    return "\n".join(lines)


def render_summary() -> str:
    """Public entry point.

    PLANTED GAP (lumen.v1 Core 2): this one is absent from docs/INDEX.md.
    """
    return f"{len(all_readings())} readings"
