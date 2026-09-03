"""The words this page says, and the words it never says.

One map, in one module. Every state the page shows is looked up here, and the
test that walks every page reads its list of internal terms from here too, so
the vocabulary and the check on it cannot drift apart.

The plain state words are not this module's invention. They are fixed by
surface.v1 clause 8 and documents.v1 clause 10, and they are the whole of what
a reader ever sees:

* a contract:  Kept · Not yet · Broken · Pinned open · Can't check
* a document:  Draft · Locked
* work:        Truly ready · Waiting on you · Working · Stuck · Done
* a lane:      Working · Quiet · Silent — may have died

Everything else — the words the machinery uses among itself — is either
translated through `surface_word` or shown as a quotation of the project's own
words. It is never the page speaking.
"""

from __future__ import annotations

import re

# --------------------------------------------------------------------------
# the plain words, by what they describe
# --------------------------------------------------------------------------

#: A contract, checked against reality (surface.v1 clause 8).
CONTRACT_STATES = ("Kept", "Not yet", "Broken", "Pinned open", "Can't check")

#: A document's own state, from its H1 and nowhere else (documents.v1 clause 6).
DOCUMENT_STATES = ("Draft", "Locked")

#: A piece of work (documents.v1 clause 10).
WORK_STATES = ("Truly ready", "Waiting on you", "Working", "Stuck", "Done")

#: A lane — a worker session at work (documents.v1 clause 10).
LANE_STATES = ("Working", "Quiet", "Silent — may have died")

#: The lock gate's two words (surface.v1 clause 7): a condition is met, or it
#: is not met yet. The gate is the one place the page says a word about a
#: condition rather than about a thing, so its words live here too.
GATE_WORDS = ("Green", "Not yet")

#: What the page says when it genuinely cannot tell. Never a guess, never a zero.
UNKNOWN = "Can't check"

#: Every word the page is allowed to use for a state. A word that is not here
#: has no business on the surface.
SURFACE_WORDS = tuple(
    dict.fromkeys(
        CONTRACT_STATES + DOCUMENT_STATES + WORK_STATES + LANE_STATES + GATE_WORDS + (UNKNOWN,)
    )
)


# --------------------------------------------------------------------------
# the map: what the machinery calls it -> what the reader reads
# --------------------------------------------------------------------------

#: Internal token → the word on the surface. Keys are matched without regard
#: to case, spacing, or whether they are written with a hyphen or a space.
SURFACE_WORD = {
    # a contract's conformance ledger, row by row
    "conforms": "Kept",
    "gap": "Not yet",
    "gap row": "Not yet",
    "violation": "Broken",
    "violation row": "Broken",
    "diverged": "Broken",
    "open pinned": "Pinned open",
    "pinned": "Pinned open",
    "not assertable": UNKNOWN,
    "excluded": UNKNOWN,
    "unknown": UNKNOWN,
    # a document's H1 parenthetical
    "draft": "Draft",
    "frozen": "Locked",
    "locked": "Locked",
    "hold": "Draft",
    "hold loosely": "Draft",
    # the work queue's own statuses
    "open": "Truly ready",
    "ready": "Truly ready",
    "held": "Working",
    "in progress": "Working",
    "blocked": "Waiting on you",
    "deferred": "Waiting on you",
    "intake": "Waiting on you",
    "resolved": "Done",
    "closed": "Done",
    "done": "Done",
    "success": "Done",
    "stuck": "Stuck",
    # a lane's own liveness
    "working": "Working",
    "quiet": "Quiet",
    "silent": "Silent — may have died",
}


def _key(raw: object) -> str:
    """A token, however it was written, reduced to how it is looked up."""
    text = re.sub(r"[\s_-]+", " ", str(raw or "").strip().lower())
    # `FROZEN 2026-09-02` and `HOLD LOOSELY UNTIL …` carry their date or reason
    # with them; the state is the word at the front.
    for candidate in (text, " ".join(text.split()[:2]), text.split(" ")[0] if text else ""):
        if candidate in SURFACE_WORD:
            return candidate
    return text


def surface_word(raw: object, *, unknown: str = UNKNOWN) -> str:
    """The plain word for an internal state token.

    An unrecognised token is never shown as-is. It becomes `unknown` — because
    a token nobody translated is exactly the internal vocabulary this module
    exists to keep off the surface.
    """
    return SURFACE_WORD.get(_key(raw), unknown)


def is_surface_word(word: str) -> bool:
    """True when this is one of the words the page is allowed to say.

    A measure may follow the word — `Quiet 12m` is still Quiet, and the
    measure is evidence, not vocabulary.
    """
    word = (word or "").strip()
    return any(word == allowed or word.startswith(f"{allowed} ") for allowed in SURFACE_WORDS)


# --------------------------------------------------------------------------
# the words that never reach the surface
# --------------------------------------------------------------------------

#: Terms a colleague who is not an engineer would have to look up. This is the
#: surface.v1 kit's own list (conformance/surface/run.py), plus the tokens the
#: contract check and the lanes use among themselves. The test that walks every
#: page reads it from here, so adding a term to the map above and forgetting to
#: check for it is not possible.
INTERNAL_TERMS = (
    "ledger",
    "disposition",
    "CONFORMS",
    "GAP",
    "VIOLATION",
    "FROZEN",
    "CANDIDATE",
    "spawn",
    "worktree",
    "tmux",
    "session id",
    "reconcile",
    "recipe",
    "bundle",
    "orchestrator",
    "subagent",
    "sub-agent",
    "conformance kit",
    "tracker item",
    "frontmatter",
    "YAML",
    "JSON",
    "regex",
    "stdout",
    "stderr",
)

#: Characters that make a term part of a longer name rather than jargon:
#: `amplifier-bundle-converge` is a project's name, `the ledger.` is jargon.
_JOINERS = "-_./"


def _inside_a_name(text: str, start: int, end: int) -> bool:
    if start > 0 and text[start - 1] in _JOINERS:
        if start - 2 >= 0 and (text[start - 2].isalnum() or text[start - 2] == "_"):
            return True
    if end < len(text) and text[end] in _JOINERS:
        if end + 1 < len(text) and (text[end + 1].isalnum() or text[end + 1] == "_"):
            return True
    return False


def internal_terms_in(text: str) -> list[str]:
    """Every internal term used as jargon in this text, in the order found."""
    found: list[str] = []
    for term in INTERNAL_TERMS:
        for match in re.finditer(r"\b" + re.escape(term) + r"\b", text, re.IGNORECASE):
            if _inside_a_name(text, match.start(), match.end()):
                continue
            found.append(term)
            break
    return found


def reads_plainly(text: str) -> bool:
    """True when nothing in this text would send a reader to a glossary."""
    return not internal_terms_in(text)
