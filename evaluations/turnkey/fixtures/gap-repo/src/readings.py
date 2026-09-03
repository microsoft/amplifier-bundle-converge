"""Lumen readings.

Contract: contracts/lumen.v1.md, Core 1 — every reading names its unit.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Reading:
    """One sensor reading. `unit` is required by lumen.v1 Core 1."""

    name: str
    value: float
    unit: str = ""


def ambient_light() -> Reading:
    return Reading(name="ambient_light", value=412.0, unit="lux")


def panel_temperature() -> Reading:
    # PLANTED GAP (lumen.v1 Core 1): this reading names no unit.
    return Reading(name="panel_temperature", value=31.5)


def all_readings() -> list[Reading]:
    return [ambient_light(), panel_temperature()]
