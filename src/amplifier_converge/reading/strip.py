"""The short list of things that need your word.

Surface.v1 clauses 1 and 2. At most five, re-ranked each refresh, each one
arriving worked out: what · why now · the recommendation · at most two
trade-offs · the word to answer with. When the list is empty the page says so
as good news, not as a blank.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace

from .documents import lock_conditions
from .ratifications import SETTLING, latest_word_on
from .lanes import SILENT_AFTER_SECONDS
from .snapshot import Snapshot

#: Never more than this many at once. The cap is the promise.
MAX_ITEMS = 5

#: The four words, and nothing else (surface.v1 clause 3).
WORDS = ("ratified", "ratified with edits", "declined", "later")


@dataclass(frozen=True)
class Decision:
    key: str
    what: str
    why_now: str
    recommendation: str
    trade_offs: tuple[str, ...]
    word: str
    place: str  # "direction" | "operation"
    link: str
    rank: int = 50
    words: tuple[str, ...] = field(default=WORDS)
    #: The project's own name for the thing this is about, as it appears
    #: inside `what`. The card marks it, so the sentence around it stays the
    #: page's own words.
    subject: str = ""
    #: Words written by something else — a lane's note, most often. Shown as a
    #: quotation, never as the page speaking.
    quote: str = ""

    def __post_init__(self) -> None:
        if len(self.trade_offs) > 2:
            object.__setattr__(self, "trade_offs", self.trade_offs[:2])


def _document_decisions(snapshot: Snapshot) -> list[Decision]:
    out: list[Decision] = []
    for doc in snapshot.documents.value:
        if doc.locked:
            continue
        conditions = lock_conditions(doc, snapshot.repo)
        green = [c for c in conditions if c[1]]
        unmet = [c[0] for c in conditions if not c[1]]
        # A draft that meets everything except your word is the one waiting on you.
        only_your_word = len(unmet) == 1 and unmet[0].startswith("You have read it")
        if not only_your_word:
            continue
        out.append(
            Decision(
                key=f"doc:{doc.slug}",
                what=f"Put your word on “{doc.title}”.",
                subject=doc.title,
                why_now=(
                    f"It is a draft, and three of the four conditions for locking it are already green. "
                    f"Yours is the one that is missing."
                ),
                recommendation="Read it, then answer ratified — or ratified with edits if you want a change first.",
                trade_offs=(
                    "Locking it turns others loose against it, and changing it afterwards costs evidence.",
                    "Leaving it a draft is free, but nothing downstream can rely on it.",
                ),
                word="ratified",
                place="direction",
                link=f"/direction/{doc.slug}",
                rank=20 - len(green),
            )
        )
    return out


def _proposal_decisions(snapshot: Snapshot) -> list[Decision]:
    out: list[Decision] = []
    for proposal in snapshot.proposals.value:
        if proposal.complete:
            why = f"A change to {proposal.target} is waiting on your word — {proposal.origin_detail}."
            recommendation = "Read the change and its evidence, then answer with one word."
            trade_offs = (
                "Ratifying makes the change and records your word against it.",
                "Later re-ranks it and never dismisses it, so nothing is lost by waiting.",
            )
        else:
            why = (
                f"A change to {proposal.target} arrived without "
                f"{' and '.join(_readable(m) for m in proposal.missing)}."
            )
            recommendation = "Decline it, or ask for the missing part before you decide."
            trade_offs = (
                "A proposal without its evidence cannot be judged on evidence.",
                "Declining is cheap; it can come back complete.",
            )
        out.append(
            Decision(
                key=f"proposal:{proposal.key}",
                what=f"Answer the proposal “{proposal.title}”.",
                subject=proposal.title,
                why_now=why,
                recommendation=recommendation,
                trade_offs=trade_offs,
                word="ratified",
                place="direction",
                link=f"/direction/proposal?key={proposal.key}",
                rank=10 if proposal.origin == "a teammate" else 15,
            )
        )
    return out


def _readable(field_name: str) -> str:
    return {
        "change": "the exact change",
        "evidence": "its evidence",
        "not_change": "what does not change",
    }.get(field_name, field_name)


def _lane_decisions(snapshot: Snapshot) -> list[Decision]:
    board = snapshot.board
    if not board.available:
        return []
    out: list[Decision] = []

    for lane in board.value.lanes:
        if lane.blocked:
            out.append(
                Decision(
                    key=f"lane-stuck:{lane.name}",
                    what=f"The lane “{lane.name}” stopped and said why.",
                    subject=lane.name,
                    why_now="It wrote a note about what it could not get past.",
                    quote=lane.summary,
                    recommendation="Read its note and decide whether to clear the way or set the work aside.",
                    trade_offs=(
                        "Clearing it puts the work back in motion now.",
                        "Setting it aside frees the lane for work that can proceed without you.",
                    ),
                    word="later",
                    place="operation",
                    link=f"/operation#lane-{lane.name}",
                    rank=12,
                )
            )
        elif (
            not lane.finished
            and lane.seconds_since_write is not None
            and lane.seconds_since_write >= SILENT_AFTER_SECONDS
        ):
            out.append(
                Decision(
                    key=f"lane-silent:{lane.name}",
                    what=f"The lane “{lane.name}” has gone silent.",
                    subject=lane.name,
                    why_now=f"It has written nothing for {int(lane.seconds_since_write // 60)} minutes. It may have died.",
                    recommendation="Let it be restarted, or accept whatever it committed and move on.",
                    trade_offs=(
                        "Restarting costs the work it had in flight.",
                        "Waiting longer costs a lane that could be carrying something else.",
                    ),
                    word="later",
                    place="operation",
                    link=f"/operation#lane-{lane.name}",
                    rank=14,
                )
            )

    short_by = board.value.short_by
    if short_by > 0:
        ready = len(snapshot.truly_ready)
        out.append(
            Decision(
                key="fill-lanes",
                what=f"{board.value.gauge}. {short_by} lane{'s' if short_by != 1 else ''} could be carrying work.",
                why_now=(
                    f"There {'is' if ready == 1 else 'are'} {ready} piece{'s' if ready != 1 else ''} of work that need nothing from you."
                    if snapshot.items.available
                    else "Lanes are below the number you set."
                ),
                recommendation="Fill the lanes.",
                trade_offs=(
                    "More lanes running means more work proceeding without you.",
                    "Every lane costs a session, and work that collides cannot share one.",
                ),
                word="fill the lanes",
                place="operation",
                link="/operation#lanes",
                rank=18,
                words=("fill the lanes", "later"),
            )
        )
    return out


#: How far down the list a `later` sends something. Far enough to get out of
#: the way, never far enough to disappear.
DEFERRED_RANK = 90


def build(snapshot: Snapshot, answered: set[str] | None = None) -> list[Decision]:
    """The list, re-ranked and capped.

    A decision already settled by your word — ratified, ratified with edits,
    or declined — leaves the list, because it is answered. A `later` does not:
    it drops to the bottom and comes back. That difference is the whole reason
    `later` is one of the four words.

    What has been answered is read back from the project's own dated record.
    The page keeps no list of its own.
    """
    answered = answered or set()
    decisions = (
        _proposal_decisions(snapshot) + _lane_decisions(snapshot) + _document_decisions(snapshot)
    )

    out: list[Decision] = []
    for decision in decisions:
        if decision.key in answered:
            continue
        word = latest_word_on(snapshot.repo, decision.what)
        if word in SETTLING:
            continue
        if word == "later":
            decision = replace(decision, rank=DEFERRED_RANK)
        out.append(decision)

    out.sort(key=lambda d: (d.rank, d.what))
    return out[:MAX_ITEMS]


def empty_state(snapshot: Snapshot) -> str:
    """What the page says when nothing needs you. It is good news; say it as such."""
    board = snapshot.board
    if board.available and board.value.running:
        return (
            f"Nothing needs your word. {board.value.gauge} — the work is proceeding without you."
        )
    return "Nothing needs your word right now."
