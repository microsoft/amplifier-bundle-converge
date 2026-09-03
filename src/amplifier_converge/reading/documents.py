"""The vision and the contracts, read as documents a person can read.

A document's state comes from its H1 parenthetical and nowhere else — that is
documents.v1 clause 6, and reading it anywhere else would be inventing a second
copy of the truth.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from . import Reading

H1_RE = re.compile(r"^#\s+(?P<title>.+?)\s*$")
STATE_RE = re.compile(r"\((?P<state>DRAFT|FROZEN[^)]*|LOCKED[^)]*|HOLD[^)]*)\)\s*$", re.IGNORECASE)
HEADING_RE = re.compile(r"^(?P<hashes>#{1,6})\s+(?P<text>.+?)\s*$")

#: The four lock conditions, in the steward's own words (VISION.md principle 2).
LOCK_CONDITIONS = (
    "It says what it means.",
    "It carries a real example of right and wrong.",
    "It can be checked against reality.",
    "You have read it and agreed.",
)


@dataclass(frozen=True)
class Paragraph:
    """One addressable block of a document — what a margin question attaches to."""

    anchor: str
    kind: str  # "heading" | "text" | "list" | "code" | "table"
    level: int
    text: str


@dataclass(frozen=True)
class Document:
    slug: str
    path: Path
    relpath: str
    title: str
    state: str
    kind: str  # "vision" | "contract"
    text: str
    paragraphs: tuple[Paragraph, ...] = field(default_factory=tuple)

    @property
    def locked(self) -> bool:
        return self.state.upper().startswith(("FROZEN", "LOCKED"))

    @property
    def state_word(self) -> str:
        """The state in the words a reader uses: Draft, or Locked."""
        if self.locked:
            return "Locked"
        return "Draft"


def _split_paragraphs(text: str) -> tuple[Paragraph, ...]:
    out: list[Paragraph] = []
    block: list[str] = []
    in_code = False
    counter = 0

    def flush(kind_hint: str = "") -> None:
        nonlocal counter, block
        if not block:
            return
        body = "\n".join(block).strip()
        block = []
        if not body:
            return
        counter += 1
        kind = kind_hint
        if not kind:
            first = body.lstrip()
            if first.startswith(("- ", "* ", "1.")):
                kind = "list"
            elif first.startswith("|"):
                kind = "table"
            else:
                kind = "text"
        out.append(Paragraph(anchor=f"p{counter}", kind=kind, level=0, text=body))

    for line in text.splitlines():
        if line.strip().startswith("```"):
            if in_code:
                block.append(line)
                flush("code")
                in_code = False
            else:
                flush()
                in_code = True
                block.append(line)
            continue
        if in_code:
            block.append(line)
            continue

        heading = HEADING_RE.match(line)
        if heading:
            flush()
            counter += 1
            out.append(
                Paragraph(
                    anchor=f"p{counter}",
                    kind="heading",
                    level=len(heading.group("hashes")),
                    text=heading.group("text"),
                )
            )
            continue

        if not line.strip():
            flush()
            continue
        block.append(line)

    flush()
    return tuple(out)


def _title_and_state(text: str, fallback: str) -> tuple[str, str]:
    for line in text.splitlines():
        h1 = H1_RE.match(line)
        if h1:
            raw = h1.group("title").strip()
            match = STATE_RE.search(raw)
            if match:
                state = match.group("state").strip()
                title = STATE_RE.sub("", raw).strip().rstrip("—-").strip()
                return title or fallback, state
            return raw, ""
    return fallback, ""


def read_document(path: Path, kind: str, repo: Path) -> Document:
    text = path.read_text(encoding="utf-8")
    fallback = path.stem
    title, state = _title_and_state(text, fallback)
    return Document(
        slug=path.stem,
        path=path,
        relpath=str(path.relative_to(repo)),
        title=title,
        state=state,
        kind=kind,
        text=text,
        paragraphs=_split_paragraphs(text),
    )


def read_direction(repo: Path) -> Reading[list[Document]]:
    """The vision and every contract, in reading order."""
    repo = Path(repo)
    docs: list[Document] = []
    missing: list[str] = []

    vision = repo / "docs" / "VISION.md"
    if vision.is_file():
        docs.append(read_document(vision, "vision", repo))
    else:
        missing.append("docs/VISION.md")

    contracts_dir = repo / "contracts"
    if contracts_dir.is_dir():
        for path in sorted(contracts_dir.glob("*.md")):
            if path.name.lower() in {"readme.md"} or "-candidate" in path.name:
                continue
            docs.append(read_document(path, "contract", repo))
    else:
        missing.append("contracts/")

    if not docs:
        where = " and ".join(missing) or "docs/VISION.md and contracts/"
        return Reading.absent(
            [],
            f"This folder has no Converge documents yet — {where} is not here. "
            "Direction will fill in as soon as a vision or a contract is written.",
        )
    if missing:
        return Reading(
            docs,
            available=True,
            note=f"Not found in this project: {', '.join(missing)}.",
        )
    return Reading(docs)


def find_document(repo: Path, slug: str) -> Document | None:
    for doc in read_direction(repo).value:
        if doc.slug == slug:
            return doc
    return None


def lock_conditions(doc: Document, repo: Path | None = None) -> list[tuple[str, bool, str]]:
    """The four conditions, each with whether it is green and why.

    The page never decides to lock. It shows which conditions are met so the
    steward can see the control is off, and why (surface.v1 clause 7).

    Each is checked against something real, never assumed:
    a contract must carry its Purpose and its numbered promises; it must point
    at a worked example, either in its own words or as a conformance folder in
    the project; it must say how it would be checked; and your agreeing word
    must be in the dated ratification record.
    """
    text = doc.text
    lowered = text.lower()
    repo = Path(repo) if repo is not None else doc.path.parent.parent

    if doc.kind == "vision":
        says_what_it_means = "## principles" in lowered or "## where this is going" in lowered
        checkable = "## changelog" in lowered
        has_example = "## what we have seen" in lowered
    else:
        says_what_it_means = "## purpose" in lowered and "core (the teeth)" in lowered
        checkable = "conformance kit asserts" in lowered
        has_example = ("example" in lowered or "fixtures" in lowered) or _has_conformance_folder(
            repo, doc.slug
        )

    if doc.locked:
        agreed = True
    else:
        from .ratifications import has_agreed_to

        agreed = has_agreed_to(repo, doc.title, doc.relpath)

    return [
        (
            LOCK_CONDITIONS[0],
            says_what_it_means,
            "Purpose and the numbered promises are both present."
            if says_what_it_means
            else "It still needs a Purpose and its numbered promises.",
        ),
        (
            LOCK_CONDITIONS[1],
            has_example,
            "It points at a worked example of right and wrong."
            if has_example
            else "No worked example of right and wrong is named yet.",
        ),
        (
            LOCK_CONDITIONS[2],
            checkable,
            "It lists what a machine or a named reader checks."
            if checkable
            else "Nothing says how this would be checked against reality.",
        ),
        (
            LOCK_CONDITIONS[3],
            agreed,
            "Your agreeing word is in the dated ratification record."
            if agreed
            else "Your word is not on this one yet.",
        ),
    ]


def _has_conformance_folder(repo: Path, slug: str) -> bool:
    """A contract named `surface.v1` is examined by `conformance/surface/`."""
    stem = slug.split(".")[0]
    directory = repo / "conformance" / stem
    if not directory.is_dir():
        return False
    return any(directory.iterdir())


def lock_is_available(doc: Document, repo: Path | None = None) -> bool:
    return all(green for _, green, _ in lock_conditions(doc, repo))
