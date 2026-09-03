"""Write four: steer.

Today's objective, the budget, how many lanes to run, fill the lanes, and
"have the manager session review this" — surface.v1 clause 3 gathers all of
these under one write, because they are one thing: telling the operation what
to aim at and how wide to run.

They land in the project, at `.converge/constraints.yaml`, which the manager
session reads as its own limits. Asking to fill the lanes or to have a proposal
reviewed is recorded there too, as a standing request — the page does not
launch anything itself, and never stops anything.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from ..reading.constraints import Constraints, parse, path_for, serialise
from .result import WriteResult

#: The requests that steering can carry beyond the three limits.
ASKS = {
    "fill the lanes": "Fill the lanes to the number set above.",
    "review this proposal": "Check the named proposal against the protocol and come back with a recommendation.",
    "": "",
}

BUDGETS = ("until done", "until a time", "until a spend", "")


def steer(
    repo: Path,
    objective: str | None = None,
    budget: str | None = None,
    lane_width: str | None = None,
    ask: str = "",
    about: str = "",
) -> WriteResult:
    ask = (ask or "").strip().lower()
    if ask not in ASKS:
        return WriteResult.failed(
            "That is not something the page can ask for. It can ask to fill the lanes, "
            "or to have a proposal reviewed."
        )
    if budget is not None and budget.strip().lower() not in BUDGETS:
        return WriteResult.failed(
            "A budget is one of: until done, until a time, until a spend."
        )
    if lane_width is not None and lane_width.strip():
        if not lane_width.strip().isdigit() or int(lane_width) < 0:
            return WriteResult.failed("A lane count is a whole number.")

    path = path_for(repo)
    try:
        current = parse(path.read_text(encoding="utf-8")) if path.is_file() else Constraints()
    except OSError as exc:
        return WriteResult.failed(f"Your limits could not be read, so nothing was changed: {exc}.")

    note = current.note
    changed: list[str] = []
    if objective is not None and objective.strip() != current.objective:
        current = Constraints(objective.strip(), current.budget, current.lane_width, note)
        changed.append("today's objective")
    if budget is not None and budget.strip().lower() != current.budget:
        current = Constraints(current.objective, budget.strip().lower(), current.lane_width, note)
        changed.append("the budget")
    if lane_width is not None and lane_width.strip() != current.lane_width:
        current = Constraints(current.objective, current.budget, lane_width.strip(), note)
        changed.append("how many lanes to run")

    if ask:
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        request = ASKS[ask]
        if about.strip():
            request += f" ({about.strip()})"
        note = f"{stamp} — {request}"
        current = Constraints(current.objective, current.budget, current.lane_width, note)
        changed.append(ask)

    if not changed:
        return WriteResult(ok=True, message="Nothing to change — that is already what it says.")

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(serialise(current), encoding="utf-8")
    except OSError as exc:
        return WriteResult.failed(f"Your limits could not be saved: {exc}.")

    return WriteResult(
        ok=True,
        message="Set: " + ", ".join(changed) + ". The manager session reads the same file.",
        where=str(path.relative_to(Path(repo))),
    )
