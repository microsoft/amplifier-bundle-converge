"""The dated ratification record — every word you have given, read back.

This is the one place a steward's word is kept, and it is prose in the project,
not a row in a table somewhere. Reading it back is how the page knows whether
you have already agreed to something.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from . import Reading

RECORD_GLOB = "owner-ratifications-*.md"
RECORD_DIR = Path("docs") / "workflow"

WORD_RE = re.compile(r"\*\*Word,\s*verbatim:\*\*\s*`(?P<word>[^`]+)`", re.IGNORECASE)
HEADING_RE = re.compile(r"^##\s+(?P<subject>.+?)\s*$", re.MULTILINE)

AGREEING = ("ratified", "ratified with edits", "lgtm")


#: Words that settle a question. `later` is deliberately not among them —
#: it re-ranks and never dismisses (surface.v1 clause 3).
SETTLING = ("ratified", "ratified with edits", "declined")


@dataclass(frozen=True)
class Answer:
    day: str
    subject: str
    word: str

    @property
    def agrees(self) -> bool:
        return self.word.strip().lower() in AGREEING

    @property
    def settles(self) -> bool:
        return self.word.strip().lower() in SETTLING

    @property
    def defers(self) -> bool:
        return self.word.strip().lower() == "later"


def latest_word_on(repo: Path, subject: str) -> str:
    """The most recent word given to this exact subject, or an empty string."""
    wanted = _normalise(subject)
    if not wanted:
        return ""
    word = ""
    for answer in read_answers(repo).value:
        if _names_the_same_thing(wanted, _normalise(answer.subject)):
            word = answer.word.strip().lower()
    return word


def read_answers(repo: Path) -> Reading[list[Answer]]:
    directory = Path(repo) / RECORD_DIR
    if not directory.is_dir():
        return Reading(
            [],
            available=True,
            note="",
        )
    answers: list[Answer] = []
    for path in sorted(directory.glob(RECORD_GLOB)):
        day = path.stem.replace("owner-ratifications-", "")
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        # Each `## heading` opens a decision; the word inside it is the answer.
        positions = [(m.start(), m.group("subject")) for m in HEADING_RE.finditer(text)]
        for index, (start, subject) in enumerate(positions):
            end = positions[index + 1][0] if index + 1 < len(positions) else len(text)
            word = WORD_RE.search(text, start, end)
            if word:
                answers.append(Answer(day=day, subject=subject.strip(), word=word.group("word")))
    return Reading(answers)


def _normalise(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


#: Short enough to appear by accident — "v1" must never be a match on its own.
SHORTEST_HONEST_MATCH = 8


def _names_the_same_thing(title: str, subject: str) -> bool:
    """Does this record entry name this document?

    A record says `Cut-out Contract`; the document calls itself `Cut-out
    Contract — v1`. Either may be the longer of the two, so containment is
    checked both ways — with a length floor, so a stray `v1` is never taken
    for agreement.
    """
    if not title or not subject:
        return False
    shorter, longer = sorted((title, subject), key=len)
    if len(shorter) < SHORTEST_HONEST_MATCH:
        return shorter == longer
    return shorter in longer


def has_agreed_to(repo: Path, title: str, relpath: str = "") -> bool:
    """Has the steward given an agreeing word to this document?

    Matched on the document's own title or its path, because that is what the
    record actually names. A record that mentions neither is not agreement.
    """
    wanted = _normalise(title)
    wanted_path = _normalise(relpath) if relpath else ""
    if not wanted and not wanted_path:
        return False
    for answer in read_answers(repo).value:
        if not answer.agrees:
            continue
        body = _normalise(answer.subject)
        if wanted and _names_the_same_thing(wanted, body):
            return True
        if wanted_path and wanted_path in body:
            return True
    # A single word can clear a sheet of decisions: look for the document
    # listed inside an agreeing entry's body as well.
    directory = Path(repo) / RECORD_DIR
    if directory.is_dir():
        for path in sorted(directory.glob(RECORD_GLOB)):
            try:
                text = path.read_text(encoding="utf-8")
            except OSError:
                continue
            if not WORD_RE.search(text):
                continue
            body = _normalise(text)
            if wanted_path and wanted_path in body:
                return True
    return False
