"""Write three: drop feedback.

Just say what you saw. This is deliberately *not* a work item: the manager
session reads the note against the contracts and what is running, and decides
whether it is a bug, a change of plan, or a decision for you. Filing it as work
here would be the system guessing on your behalf.

It lands in the project, under `.converge/feedback/`, because the manager
session must be able to read the same drop.
"""

from __future__ import annotations

import base64
import re
from datetime import datetime, timezone
from pathlib import Path

from .result import WriteResult

FEEDBACK_DIR = Path(".converge") / "feedback"

#: What we will accept alongside a note, and the extension we give it.
IMAGE_TYPES = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/webp": ".webp",
    "image/gif": ".gif",
}


def _slug(text: str) -> str:
    words = re.findall(r"[a-z0-9]+", text.lower())[:6]
    return "-".join(words) or "note"


def drop_feedback(
    repo: Path,
    text: str,
    looking_at: str = "",
    attachment: bytes | None = None,
    attachment_type: str = "",
) -> WriteResult:
    text = (text or "").strip()
    if not text and attachment is None:
        return WriteResult.failed("A feedback drop needs something in it — a sentence, or a picture.")

    now = datetime.now(timezone.utc)
    stem = f"{now.strftime('%Y-%m-%dT%H%M%SZ')}-{_slug(text)}"
    directory = Path(repo) / FEEDBACK_DIR

    attachment_name = ""
    try:
        directory.mkdir(parents=True, exist_ok=True)
        if attachment:
            suffix = IMAGE_TYPES.get(attachment_type, ".bin")
            attachment_name = f"{stem}{suffix}"
            (directory / attachment_name).write_bytes(attachment)

        body = [
            f"# Feedback — {now.strftime('%-d %B %Y, %H:%M UTC')}",
            "",
            "Raw, as it was given. Not a work item: read this against the contracts and",
            "what is running before deciding what it is.",
            "",
            "## What I saw",
            "",
            text or "(no words — see the attached picture)",
            "",
        ]
        if looking_at.strip():
            body += ["## What I was looking at", "", looking_at.strip(), ""]
        if attachment_name:
            body += ["## Attached", "", f"`{attachment_name}`", ""]
        (directory / f"{stem}.md").write_text("\n".join(body), encoding="utf-8")
    except OSError as exc:
        return WriteResult.failed(f"The feedback could not be saved: {exc}.")

    return WriteResult(
        ok=True,
        message="Dropped. The manager session will read it and decide what it is.",
        where=str(FEEDBACK_DIR / f"{stem}.md"),
    )
