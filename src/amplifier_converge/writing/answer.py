"""Write one: answer with a word.

Four words and no others: *ratified · ratified with edits · declined · later*.
`later` re-ranks and never dismisses — nothing is lost by answering it.

Every answer lands in the dated ratification record, because the steward's
literal word is the thing every session afterwards obeys. The record is
append-only prose: one home per decision, readable by anyone.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from .result import WriteResult

WORDS = ("ratified", "ratified with edits", "declined", "later")

RECORD_DIR = Path("docs") / "workflow"


def record_path(repo: Path, on: date | None = None) -> Path:
    day = (on or date.today()).isoformat()
    return Path(repo) / RECORD_DIR / f"owner-ratifications-{day}.md"


def _header(day: str) -> str:
    return (
        f"# Owner ratifications — {day}\n\n"
        "One home per decision. Each entry records the steward's literal word, "
        "what it ratified, and what did not land as ratified content.\n"
    )


def answer_with_a_word(
    repo: Path,
    subject: str,
    word: str,
    note: str = "",
    on: date | None = None,
) -> WriteResult:
    word = (word or "").strip().lower()
    if word not in WORDS:
        return WriteResult.failed(
            f"“{word}” is not one of the four words. Answer with ratified, "
            "ratified with edits, declined, or later."
        )
    subject = (subject or "").strip()
    if not subject:
        return WriteResult.failed("An answer needs to say what it is answering.")

    day = (on or date.today()).isoformat()
    path = record_path(repo, on)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        existing = path.read_text(encoding="utf-8") if path.is_file() else ""
        if not existing.strip():
            existing = _header(day)
        entry = [
            "",
            f"## {subject}",
            "",
            f"**Word, verbatim:** `{word}`",
            "",
        ]
        if note.strip():
            entry += [f"**In your words:** {note.strip()}", ""]
        if word == "later":
            entry += [
                "**What this word did:** re-ranked this decision. It is not dismissed "
                "and will come back.",
                "",
            ]
        elif word == "declined":
            entry += ["**What this word did:** declined the change. The original stands.", ""]
        elif word == "ratified with edits":
            entry += [
                "**What this word did:** ratified the change with the edits recorded above, "
                "and nothing beyond them.",
                "",
            ]
        else:
            entry += ["**What this word did:** ratified the change as written.", ""]

        path.write_text(existing.rstrip("\n") + "\n" + "\n".join(entry), encoding="utf-8")
    except OSError as exc:
        return WriteResult.failed(f"Your word could not be recorded: {exc}.")

    return WriteResult(
        ok=True,
        message=f"Recorded: “{word}” on {subject}.",
        where=str(path.relative_to(Path(repo))),
    )
