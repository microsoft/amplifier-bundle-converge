"""Whether each promise is actually being kept.

This answers a different question from the one a document's own heading answers.
`Draft` and `Locked` say where a promise stands **as a document** — whether it
is still being written or has been settled. *Kept · Not yet · Broken · Pinned
open · Can't check* say whether the promise is **true of the project today**.
surface.v1 clause 8 asks for both, and neither substitutes for the other: a
settled promise can be broken, and a promise still being written can already be
kept.

The reading is the project's own, at `ledger/rows.yaml` — one row per checkable
clause, each carrying that clause's standing. Nothing here writes it, and
nothing here decides a standing: the file says, and this folds what it says into
the one word beside the contract.

Two rules the fold obeys, both from AGENTS.md rule 3:

* **The worst honest word wins.** One broken clause makes the promise broken,
  whatever the other rows say. A contract is not kept on average.
* **A clause nobody can check is never a pass.** A promise whose rows are all
  unverifiable reads *Can't check*, and so does a contract with no rows at all
  and a project keeping no record yet.

Every word returned comes through `words.surface_word`, so a term that appears
in the file tomorrow and nobody has translated arrives as *Can't check* rather
than reaching the page as itself.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..words import UNKNOWN, surface_word
from . import Reading

RELPATH = Path("ledger") / "rows.yaml"

#: The plain sentence beside each word. It says what the word means for this
#: promise, in the terms the reader already has.
SENTENCE = {
    "Kept": "Every part of it that can be checked is being kept.",
    "Not yet": "Some of what it promises is not true yet.",
    "Broken": "Something it promises is not true today.",
    "Pinned open": "Held open on purpose, with your word on it.",
    UNKNOWN: "Nothing here can be checked against reality yet.",
}

#: When the promise has no rows watching it at all — a different silence from
#: "the rows exist and none of them can be checked", and worth saying apart.
NOTHING_WATCHED = "No part of this one is being watched yet."

#: When the project keeps no record of this at all.
NO_RECORD = "This project keeps no record yet of whether its promises are kept."

#: Worst first. The fold walks this and takes the first word it sees, so one
#: broken clause outranks every kept one.
SEVERITY = ("Broken", "Not yet", "Pinned open")


@dataclass(frozen=True)
class Standing:
    """Where one promise stands against reality, in one word."""

    word: str
    #: How many clauses were counted. Zero is not a failure — it is the reason
    #: the word is *Can't check*, and the sentence says so.
    clauses: int = 0
    sentence: str = NO_RECORD


def fold(standings: object) -> str:
    """The one word for a set of clause standings, worst honest word first.

    All kept → *Kept*. Anything broken → *Broken*, whatever else is true. Any
    part not built yet → *Not yet*. Held open → *Pinned open*. Nothing to go
    on, or anything nobody translated → *Can't check*.
    """
    said = {surface_word(one) for one in standings or ()}
    if not said:
        return UNKNOWN
    for word in SEVERITY:
        if word in said:
            return word
    if said == {"Kept"}:
        return "Kept"
    return UNKNOWN


def _standing(words: list[str]) -> Standing:
    if not words:
        return Standing(UNKNOWN, 0, NOTHING_WATCHED)
    word = fold(words)
    return Standing(word, len(words), SENTENCE.get(word, SENTENCE[UNKNOWN]))


# --------------------------------------------------------------------------
# reading the file
# --------------------------------------------------------------------------
#
# The record is a list of blocks, each naming the promise it watches and that
# clause's standing. Only those two fields are read here; everything else in a
# block — the quoted clause, the command that watches it, the notes — is the
# record's own business, and a block of the project's own prose is skipped
# whole rather than half-read.


def _blocks(text: str) -> list[tuple[str, str]]:
    """Every (promise file, clause standing) pair in the record, in order."""
    found: list[tuple[str, str]] = []
    promise = ""
    standing = ""
    inside_the_promise = False
    lines = text.splitlines()
    index = 0

    def close() -> None:
        nonlocal promise, standing
        if promise and standing:
            found.append((promise, standing))
        promise = standing = ""

    while index < len(lines):
        line = lines[index]
        index += 1
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        depth = len(line) - len(line.lstrip())
        if depth == 0 and stripped.startswith("- "):
            close()
            inside_the_promise = False
            stripped = stripped[2:].strip()
            depth = 2  # a block's own fields sit one step in

        name, colon, value = stripped.partition(":")
        if not colon:
            continue
        name = name.strip().lower()
        value = value.strip()

        if value[:1] in ("|", ">"):
            # A run of the project's own prose. Skip past it entirely: a
            # sentence inside it that happens to look like a field is prose.
            while index < len(lines):
                following = lines[index]
                if following.strip() and (len(following) - len(following.lstrip())) <= depth:
                    break
                index += 1
            continue

        if depth <= 2:
            inside_the_promise = name == "contract"
            if name == "disposition":
                standing = value.strip("\"'")
        elif inside_the_promise and name == "file":
            promise = value.strip("\"'").replace("\\", "/")

    close()
    return found


def read_promises(repo: Path) -> Reading[dict[str, Standing]]:
    """Where every promise in this project stands, by the file it lives in.

    A project with no record answers with an empty map rather than a failure:
    each promise then reads *Can't check* on its own row, which is the honest
    word for it and is said where the reader is looking.
    """
    path = Path(repo) / RELPATH
    if not path.is_file():
        return Reading.absent({}, NO_RECORD, detail=f"{RELPATH} is not in this project.")
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return Reading.absent({}, NO_RECORD, detail=f"{RELPATH} could not be read: {exc}")

    counted: dict[str, list[str]] = {}
    for promise, standing in _blocks(text):
        counted.setdefault(promise, []).append(standing)
    return Reading({promise: _standing(words) for promise, words in counted.items()})


def standing_of(relpath: str, promises: dict[str, Standing] | None) -> Standing:
    """The standing for one promise, and the honest silence when there is none."""
    if not promises:
        return Standing(UNKNOWN, 0, NO_RECORD)
    return promises.get(str(relpath).replace("\\", "/"), Standing(UNKNOWN, 0, NOTHING_WATCHED))
