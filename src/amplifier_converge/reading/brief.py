"""The return brief, and the plan in order with its reasons.

Of everything the system made for itself, the only artefact the steward read
was the plain-sentence brief written *for them*. So this is sentences — never a
wrapped table, never a count standing on its own.
"""

from __future__ import annotations

from dataclasses import dataclass

from .lanes import SILENT_AFTER_SECONDS
from .snapshot import Snapshot


@dataclass(frozen=True)
class PlanStep:
    position: int
    id: str
    title: str
    why: str
    state_word: str
    proceeds_without_you: bool


def return_brief(snapshot: Snapshot) -> list[str]:
    """Four or five sentences answering: what happened, what's stuck, what needs me."""
    lines: list[str] = []
    board = snapshot.board

    if board.available:
        lanes = board.value.lanes
        finished = [lane for lane in lanes if lane.finished]
        stuck = [lane for lane in lanes if lane.blocked]
        silent = [
            lane
            for lane in lanes
            if not lane.finished
            and not lane.blocked
            and lane.seconds_since_write is not None
            and lane.seconds_since_write >= SILENT_AFTER_SECONDS
        ]
        lines.append(
            f"{board.value.gauge}."
            + (
                f" {board.value.short_by} more could be carrying work."
                if board.value.short_by
                else " That is the number you set."
                if board.value.width_target
                else ""
            )
        )
        if finished:
            names = ", ".join(f"“{lane.name}”" for lane in finished[:3])
            more = f" and {len(finished) - 3} more" if len(finished) > 3 else ""
            lines.append(f"{len(finished)} finished since this batch began: {names}{more}.")
        if stuck:
            lines.append(
                f"{len(stuck)} stopped and said why: "
                + ", ".join(f"“{lane.name}”" for lane in stuck)
                + "."
            )
        if silent:
            lines.append(
                f"{len(silent)} has gone silent and may have died: "
                + ", ".join(f"“{lane.name}”" for lane in silent)
                + "."
            )
        if not stuck and not silent and lanes:
            lines.append("Nothing has gone quiet.")
    else:
        lines.append(board.note)

    if snapshot.items.available:
        ready = len(snapshot.truly_ready)
        waiting = len(snapshot.waiting_on_you)
        lines.append(
            f"{ready} piece{'s' if ready != 1 else ''} of work {'are' if ready != 1 else 'is'} truly ready — "
            f"needing nothing from you — and {waiting} {'are' if waiting != 1 else 'is'} waiting on you."
        )
    else:
        lines.append(snapshot.items.note)

    if snapshot.git.available:
        lines.append(snapshot.git.value.sentence)

    return [line for line in lines if line]


def plan(snapshot: Snapshot, limit: int = 8) -> list[PlanStep]:
    """What is intended next, in order, each with one line of why."""
    if not snapshot.items.available:
        return []

    ordered = snapshot.working + snapshot.truly_ready + snapshot.waiting_on_you
    steps: list[PlanStep] = []
    for position, item in enumerate(ordered[:limit], start=1):
        if item.status == "held":
            why = f"A lane is carrying this now ({item.holder or 'a worker session'})."
            proceeds = True
        elif item.status == "open":
            why = "Nothing blocks it and it needs nothing from you, so it can start as soon as a lane is free."
            proceeds = True
        elif item.status == "deferred":
            why = "Set aside on purpose. It comes back when you say so."
            proceeds = False
        elif item.status == "blocked":
            why = "Something is in its way. It cannot start until that clears."
            proceeds = False
        else:
            why = "Waiting on you."
            proceeds = False
        steps.append(
            PlanStep(
                position=position,
                id=item.id,
                title=item.title,
                why=why,
                state_word=item.state_word,
                proceeds_without_you=proceeds,
            )
        )
    return steps
