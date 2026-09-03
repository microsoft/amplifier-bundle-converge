"""Your limits — today's objective, the budget, how many lanes to run.

These live in the project, at `.converge/constraints.yaml`, because they are
the project's truth and the manager session must obey the same file. The page
reads and writes that one file; it keeps no copy.

The format is deliberately a handful of `key: value` lines so that a person can
open it in any editor and a session can read it without a library.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from . import Reading

RELPATH = Path(".converge") / "constraints.yaml"

#: The three budget shapes surface.v1 clause 3 settles on for v1.
BUDGETS = ("until done", "until a time", "until a spend")


@dataclass(frozen=True)
class Constraints:
    objective: str = ""
    budget: str = ""
    lane_width: str = ""
    note: str = ""

    @property
    def objective_sentence(self) -> str:
        return self.objective or "No objective is set for today."

    @property
    def budget_sentence(self) -> str:
        return self.budget or "No budget is set — this runs until done."

    @property
    def width_sentence(self) -> str:
        return f"{self.lane_width} lanes" if self.lane_width else "No lane count is set."


def path_for(repo: Path) -> Path:
    return Path(repo) / RELPATH


def parse(text: str) -> Constraints:
    values: dict[str, str] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or ":" not in stripped:
            continue
        key, _, value = stripped.partition(":")
        values[key.strip().lower()] = value.strip().strip("\"'")
    return Constraints(
        objective=values.get("objective", ""),
        budget=values.get("budget", ""),
        lane_width=values.get("lane_width", values.get("lanes", "")),
        note=values.get("note", ""),
    )


def serialise(constraints: Constraints) -> str:
    return (
        "# Your limits. The page and the manager session both read this one file.\n"
        f"objective: {constraints.objective}\n"
        f"budget: {constraints.budget}\n"
        f"lane_width: {constraints.lane_width}\n"
        f"note: {constraints.note}\n"
    )


def read_constraints(repo: Path) -> Reading[Constraints]:
    path = path_for(repo)
    if not path.is_file():
        return Reading(
            Constraints(),
            available=True,
            note="You have not set any limits yet. Setting one writes them into the project, where the manager session reads them too.",
        )
    try:
        return Reading(parse(path.read_text(encoding="utf-8")))
    except OSError as exc:
        return Reading.absent(Constraints(), f"Your limits could not be read from {RELPATH}: {exc}.")
