"""Reading the project's truth.

Nothing in this package writes. Each reader answers one question about the
project and, when the thing it reads is simply not there, says so in a
sentence a person can act on instead of showing a zero.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class Reading(Generic[T]):
    """What a reader found, or the plain sentence explaining why it found nothing.

    `available` is False only when the source itself is missing or refused to
    answer — never when the source answered and the answer was empty. That
    distinction is the whole point: "no lanes are running" and "there is no
    lanes directory to read" must never look the same on the page.
    """

    value: T
    available: bool = True
    #: The plain sentence a reader sees. No paths, no commands, no error text.
    note: str = ""
    #: The raw reason, for the Details fold. Technical words live only here
    #: (documents.v1 clause 11 — never in the deciding sentence).
    detail: str = ""

    @classmethod
    def absent(cls, value: T, note: str, detail: str = "") -> "Reading[T]":
        return cls(value=value, available=False, note=note, detail=detail)


__all__ = ["Reading"]
