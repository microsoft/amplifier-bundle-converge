"""What a write reports back — in the same plain words the page is written in."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class WriteResult:
    ok: bool
    #: One sentence for the steward. Never a stack trace, never a path alone.
    message: str
    #: Where it landed, relative to the project, for the Details fold.
    where: str = ""

    @classmethod
    def failed(cls, message: str, where: str = "") -> "WriteResult":
        return cls(ok=False, message=message, where=where)
