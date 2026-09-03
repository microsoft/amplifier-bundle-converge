"""The four things a steward can actually do, written where they belong.

Every function here changes a real file in a real repository. That is the
point: a decision the steward makes is their word, and a word that is only
displayed back to them is not a decision at all. There is no demo mode and no
dry-run switch — if a call returns ok, something on disk is different.

Two habits keep that safe rather than reckless. Nothing is ever overwritten:
a decision appends, feedback creates a new file named for its moment, and a
steer rewrites only the one number it is about. And every write records who
made it and when, so the file can be read later as a record and not just as
state.
"""

from __future__ import annotations

import base64
import re
from datetime import datetime, timezone
from pathlib import Path

DECISION_WORDS = {
    "ratified": "Ratified",
    "ratified-with-edits": "Ratified with edits",
    "declined": "Declined",
    "later": "Answer later",
}


def _now() -> datetime:
    return datetime.now(timezone.utc).astimezone()


def _stamp(when: datetime | None = None) -> str:
    return (when or _now()).isoformat(timespec="seconds")


def _safe(text: str, limit: int = 80) -> str:
    """A path-safe fragment of a caller-supplied name. Never a path itself."""
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", (text or "").strip()).strip("-.")
    return (cleaned or "untitled")[:limit]


def record_decision(
    repo: Path,
    *,
    repo_id: str,
    doc_id: str,
    proposal_id: str,
    decision: str,
    note: str = "",
    user: str = "",
    when: datetime | None = None,
) -> dict:
    """Append the steward's word to today's ratification record.

    The file is one day's decisions, in the order they were made. It is created
    with the same header the manager session writes by hand, so a decision made
    here and a decision made there read the same afterwards.
    """
    when = when or _now()
    day = when.strftime("%Y-%m-%d")
    folder = Path(repo) / "docs" / "workflow"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"owner-ratifications-{day}.md"
    if not path.exists():
        path.write_text(
            f"# Owner ratifications — {day}\n\n"
            "Each entry below is the steward's own word on one proposal, recorded when it was given.\n",
            encoding="utf-8",
        )

    word = DECISION_WORDS.get(decision, decision or "Recorded")
    heading = f"{_stamp(when)} — {word}: {doc_id} ({proposal_id or 'no proposal named'})"
    body = [
        "",
        f"## {heading}",
        "",
        f"- **Decision:** {word}",
        f"- **Document:** `{repo_id}` · `{doc_id}`",
        f"- **Proposal:** `{proposal_id}`" if proposal_id else "- **Proposal:** none named",
        f"- **By:** {user or 'unknown'} · {_stamp(when)}",
    ]
    if note.strip():
        body += ["", f"**Note, verbatim:** {note.strip()}"]
    body.append("")
    with path.open("a", encoding="utf-8") as out:
        out.write("\n".join(body))
    return {"ok": True, "recorded": f"{path}#{heading}", "path": str(path), "heading": heading}


def record_feedback(
    repo: Path,
    *,
    text: str,
    context: str = "",
    user: str = "",
    image_data_url: str = "",
    when: datetime | None = None,
) -> dict:
    """Write one piece of feedback as its own dated file, image beside it."""
    when = when or _now()
    stamp = when.strftime("%Y-%m-%dT%H-%M-%S")
    folder = Path(repo) / ".converge" / "feedback"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{stamp}.md"

    image_note = ""
    if image_data_url:
        match = re.match(r"data:image/(png|jpeg|jpg);base64,(.+)$", image_data_url.strip(), re.S)
        if match:
            suffix = "png" if match.group(1) == "png" else "jpg"
            image_path = folder / f"{stamp}.{suffix}"
            try:
                image_path.write_bytes(base64.b64decode(match.group(2)))
                image_note = f"image: {image_path.name}\n"
            except (ValueError, OSError):
                image_note = "image: could not be decoded\n"

    path.write_text(
        "---\n"
        f"context: {context or 'unspecified'}\n"
        f"user: {user or 'unknown'}\n"
        f"time: {_stamp(when)}\n"
        f"{image_note}"
        "---\n\n"
        f"{(text or '').strip()}\n",
        encoding="utf-8",
    )
    return {"ok": True, "path": str(path)}


def _append_weave_in(highway: Path, line: str) -> bool:
    """Add one line under `## Weave-in log`, creating the section if needed."""
    try:
        text = highway.read_text(encoding="utf-8")
    except OSError:
        return False
    if "## Weave-in log" not in text:
        text = text.rstrip("\n") + "\n\n## Weave-in log\n"
    text = text.rstrip("\n") + "\n" + line + "\n"
    highway.write_text(text, encoding="utf-8")
    return True


def steer(
    batch_dir: Path,
    *,
    objective: str = "",
    lanes: int | None = None,
    fill: bool = False,
    note: str = "",
    user: str = "",
    when: datetime | None = None,
) -> dict:
    """Change how wide the run is, and say so where the manager will read it.

    Only `.width` is rewritten, and only when a number was asked for. The
    manager session is what acts on a steer; this records the ask where that
    session already looks, which is why every call appends to the weave-in log
    even when nothing else changed.
    """
    when = when or _now()
    batch = Path(batch_dir)
    changed: list[str] = []

    width_path = batch / ".width"
    if lanes is not None:
        try:
            wanted = max(0, int(lanes))
        except (TypeError, ValueError):
            return {"ok": False, "error": "lanes must be a whole number"}
        batch.mkdir(parents=True, exist_ok=True)
        width_path.write_text(f"{wanted}\n", encoding="utf-8")
        changed.append(f"width → {wanted}")

    said = []
    if lanes is not None:
        said.append(f"lanes {lanes}")
    if fill:
        said.append("fill now")
    if objective.strip():
        said.append(f"objective: {objective.strip()}")
    if note.strip():
        said.append(f"note: {note.strip()}")
    line = f"- {_stamp(when)} steer ({user or 'unknown'}): " + ("; ".join(said) if said else "no change requested")

    highway = batch / "HIGHWAY.md"
    logged = _append_weave_in(highway, line)
    if logged:
        changed.append("weave-in log")
    return {
        "ok": True,
        "changed": changed,
        "line": line,
        "width": str(width_path) if lanes is not None else "",
        "highway": str(highway) if logged else "",
    }


__all__ = ["DECISION_WORDS", "record_decision", "record_feedback", "steer"]
