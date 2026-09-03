"""The four things you can do.

Surface.v1 clause 3: **exactly four writes**, and each one is an operation the
manager session can perform the same way. Everything else on the page is read.

The registry below is the whole list. It is checked by a test, and every form
on the page dispatches through it — so a fifth write cannot be added by
accident, only by amending the contract first.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .answer import answer_with_a_word
from .feedback import drop_feedback
from .priority import signal_priority
from .result import WriteResult
from .steer import steer


@dataclass(frozen=True)
class WritePath:
    """One of the four, with the manager-session operation it is the same as."""

    name: str
    label: str
    #: What the manager session runs to do this exact thing, in its own terms.
    manager_operation: str
    #: Where the write lands, in words a reader understands.
    lands_in: str
    handler: Callable[..., WriteResult]


WRITES: tuple[WritePath, ...] = (
    WritePath(
        name="answer-with-a-word",
        label="Answer with a word",
        manager_operation="record-ratification",
        lands_in="the dated ratification record, docs/workflow/owner-ratifications-<date>.md",
        handler=answer_with_a_word,
    ),
    WritePath(
        name="signal-priority",
        label="Raise or lower a priority",
        manager_operation="work-tracker edit --description",
        lands_in="the work queue, against the item itself",
        handler=signal_priority,
    ),
    WritePath(
        name="drop-feedback",
        label="Drop feedback",
        manager_operation="read-feedback-drop",
        lands_in="the project, at .converge/feedback/",
        handler=drop_feedback,
    ),
    WritePath(
        name="steer",
        label="Steer",
        manager_operation="apply-constraints",
        lands_in="the project, at .converge/constraints.yaml",
        handler=steer,
    ),
)

#: The cap is the promise. Adding a fifth means amending surface.v1 first.
EXPECTED_WRITE_COUNT = 4

assert len(WRITES) == EXPECTED_WRITE_COUNT, (
    "surface.v1 clause 3 says exactly four writes. Amend the contract before adding one."
)


def by_name(name: str) -> WritePath | None:
    for write in WRITES:
        if write.name == name:
            return write
    return None


__all__ = [
    "EXPECTED_WRITE_COUNT",
    "WRITES",
    "WritePath",
    "WriteResult",
    "answer_with_a_word",
    "by_name",
    "drop_feedback",
    "signal_priority",
    "steer",
]
