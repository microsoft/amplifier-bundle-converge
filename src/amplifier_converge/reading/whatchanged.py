"""What changed since you last read this — sentence by sentence.

The measured failure this answers: a regenerated draft came back and the
steward could not tell whether something had been dropped. So removed
sentences are shown, not just added ones (surface.v1 clause 6).

The marker recording what you last read is kept outside the project, under the
app home, so reading a document never touches the project itself.
"""

from __future__ import annotations

import difflib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from ..home import ensure, last_read_dir

# A sentence ends at . ? ! or : followed by space, or at a line break that ends
# a list item or heading. Good enough to make a rewrite checkable, which is the
# job — not to be a grammar engine.
SENTENCE_END = re.compile(r"(?<=[.!?:])\s+(?=[A-Z0-9*_`\-\[(])")


@dataclass(frozen=True)
class WhatChanged:
    seen_before: bool
    last_read_at: str
    added: tuple[str, ...]
    removed: tuple[str, ...]

    @property
    def unchanged(self) -> bool:
        return self.seen_before and not self.added and not self.removed

    @property
    def summary(self) -> str:
        if not self.seen_before:
            return "You have not marked this read before, so there is nothing to compare against yet."
        if self.unchanged:
            return f"Nothing has changed since you read this on {self.last_read_at}."
        parts = []
        if self.added:
            parts.append(f"{len(self.added)} sentence{'s' if len(self.added) != 1 else ''} added")
            parts[-1] = parts[-1]
        if self.removed:
            parts.append(
                f"{len(self.removed)} removed"
                if self.added
                else f"{len(self.removed)} sentence{'s' if len(self.removed) != 1 else ''} removed"
            )
        return f"Since you read this on {self.last_read_at}: " + ", ".join(parts) + "."


#: A line that begins its own unit rather than continuing the one before it.
STARTS_ITS_OWN = ("- ", "* ", "#", "|", "> ")


def _units(block: str) -> list[str]:
    """Rejoin a hard-wrapped paragraph before looking for its sentences.

    Documents here are wrapped at about eighty columns. Splitting on line ends
    would report half a sentence as removed and the other half as added, which
    is exactly the confusion this whole feature exists to remove.
    """
    units: list[str] = []
    for line in block.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        own = stripped.startswith(STARTS_ITS_OWN) or re.match(r"^\d+[.)]\s", stripped)
        if own or not units:
            units.append(stripped)
        else:
            units[-1] = f"{units[-1]} {stripped}"
    return units


def sentences(text: str) -> list[str]:
    out: list[str] = []
    for block in text.split("\n\n"):
        block = block.strip()
        if not block:
            continue
        if block.startswith("```"):
            out.append(block)
            continue
        for unit in _units(block):
            for piece in SENTENCE_END.split(unit):
                piece = piece.strip()
                if piece:
                    out.append(piece)
    return out


def _marker_path(repo: Path, slug: str) -> Path:
    return last_read_dir(repo) / f"{slug}.json"


def read_marker(repo: Path, slug: str) -> dict | None:
    path = _marker_path(repo, slug)
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def mark_read(repo: Path, slug: str, text: str) -> None:
    """Record that the steward has now read this text.

    This is not one of the four writes: nothing about the project changes. It
    is the page remembering, on the steward's behalf, what they have seen.
    """
    path = _marker_path(repo, slug)
    ensure(path.parent)
    payload = {
        "slug": slug,
        "read_at": datetime.now(timezone.utc).strftime("%-d %B %Y at %H:%M UTC"),
        "sentences": sentences(text),
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def what_changed(repo: Path, slug: str, text: str) -> WhatChanged:
    marker = read_marker(repo, slug)
    now = sentences(text)
    if marker is None:
        return WhatChanged(seen_before=False, last_read_at="", added=(), removed=())

    before: list[str] = list(marker.get("sentences", []))
    added: list[str] = []
    removed: list[str] = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(a=before, b=now, autojunk=False).get_opcodes():
        if tag in ("replace", "delete"):
            removed.extend(before[i1:i2])
        if tag in ("replace", "insert"):
            added.extend(now[j1:j2])

    return WhatChanged(
        seen_before=True,
        last_read_at=str(marker.get("read_at", "an earlier visit")),
        added=tuple(added),
        removed=tuple(removed),
    )
