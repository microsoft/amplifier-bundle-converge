"""The things a steward can actually do, written where they belong.

Every function here changes a real file in a real repository. That is the
point: a decision the steward makes is their word, and a word that is only
displayed back to them is not a decision at all. There is no demo mode and no
dry-run switch — if a call returns ok, something on disk is different.

Two habits keep that safe rather than reckless. Nothing is ever overwritten:
a decision appends, feedback creates a new file named for its moment, and a
steer rewrites only the one number it is about. And every write records who
made it and when, so the file can be read later as a record and not just as
state.

Rewording a sentence from the Changes view is the one write that touches a
governed document, and it is the one place the lock is the law rather than a
convention. The check is made here, in the writer, on the document's own H1 —
not in the browser, which can be told anything. A draft is committed in the
steward's name; a locked document is never touched at all and gets a proposal
beside it in the shape `documents.v1` §8 requires.
"""

from __future__ import annotations

import base64
import re
import subprocess
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


# --------------------------------------------------------------------------
# rewording one sentence: a commit on a draft, a proposal on a locked document
# --------------------------------------------------------------------------

#: The words that make a document law. They are matched in capitals only,
#: because a contract's H1 may well say "owner-ratified" in prose about how it
#: got here while still being a DRAFT — and reading that as a lock would put
#: every draft out of the steward's reach.
LOCK_WORD = re.compile(r"\b(FROZEN|RATIFIED|LOCKED)\b")

VERSIONED = re.compile(r"\.v\d+$")


def document_lock(path: Path) -> str:
    """The locking word in a document's H1, or an empty string for a draft.

    Only the first `# ` line is read. `documents.v1` §6 puts status in the H1
    parenthetical and nowhere else, so anywhere else is not a status.
    """
    try:
        text = Path(path).read_text(encoding="utf-8")
    except OSError:
        return ""
    for line in text.splitlines():
        if line.startswith("# "):
            found = LOCK_WORD.search(line)
            return found.group(1) if found else ""
    return ""


def candidate_path(path: Path) -> Path:
    """`<doc-stem>.vN-candidate.md`, beside the document it proposes against."""
    path = Path(path)
    stem = path.stem
    if not VERSIONED.search(stem):
        stem = f"{stem}.v1"
    return path.with_name(f"{stem}-candidate.md")


def _git(repo: Path, *args: str, timeout: float = 20.0) -> tuple[bool, str, str]:
    """Run one git command and say plainly whether it worked."""
    try:
        done = subprocess.run(
            ["git", *args],
            cwd=str(repo),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as problem:
        return False, "", str(problem)
    return done.returncode == 0, done.stdout, done.stderr


def _reword(text: str, *, now: str, anchor: int, replacement: str) -> tuple[str, str]:
    """The document with one sentence replaced, added, or taken back out.

    A sentence is found by its own words rather than by a line number, because
    the line number is only true for the diff that produced it and the words
    are true for the file. The hunk's line is still tried first, so a sentence
    that happens to appear twice is changed where the steward was looking at
    it rather than wherever it happens to appear first. When there is no
    sentence to find — the card is a removal being put back — the anchor is
    all there is, and it says where it belongs.
    """
    lines = (text or "").split("\n")
    if now:
        at = anchor - 1
        order = [at] if 0 <= at < len(lines) and now in lines[at] else []
        order += [index for index in range(len(lines)) if index != at and now in lines[index]]
        for index in order:
            made = lines[index].replace(now, replacement, 1)
            if made.strip():
                lines[index] = made
            else:
                del lines[index]
            return "\n".join(lines), ""
        return "", "that sentence is no longer in the file as it was written"
    if not replacement.strip():
        return "", "there is nothing to write"
    at = max(0, min(len(lines), anchor))
    lines.insert(at, replacement)
    return "\n".join(lines), ""


def _candidate_block(*, section: str, current: str, replacement: str) -> str:
    shown = current.strip() or "(the sentence was not there)"
    becomes = replacement.strip() or "(the sentence is removed)"
    return (
        f"**{section or 'the document'}** — the sentence below becomes the one under it.\n\n"
        "```text\n"
        f"{shown}\n"
        "```\n\n"
        "```text\n"
        f"{becomes}\n"
        "```\n"
    )


def _candidate_text(
    *,
    rel: str,
    title: str,
    lock: str,
    block: str,
    user: str,
    when: datetime,
    action: str,
) -> str:
    reason = (
        "The steward read this change in Converge and wrote the wording they wanted instead."
        if action == "edit"
        else "The steward read this change in Converge and asked for the previous wording back."
    )
    return (
        f"# {title} — proposed wording\n\n"
        f"target: {rel}\n"
        f"author: {user or 'unknown'} via Converge\n"
        f"date: {_stamp(when)}\n\n"
        f"This document is {lock}, so nothing in it has been touched. What follows is the\n"
        "proposal the steward's word makes, for someone to answer.\n\n"
        "## The exact change\n\n"
        f"{block}\n"
        "## The evidence\n\n"
        f"- {reason}\n"
        f"- The change was shown to them in the Changes view of `{rel}` on {when.strftime('%Y-%m-%d')}.\n\n"
        "## What does not change\n\n"
        f"Every other sentence in `{rel}` stands exactly as it was ratified.\n"
    )


def _merge_candidate(existing: str, block: str) -> str:
    """Add one more change to an open proposal, keeping §8's three-part order."""
    marker = "\n## The evidence"
    at = existing.find(marker)
    if at < 0:
        return existing.rstrip("\n") + "\n\n" + block
    return existing[:at].rstrip("\n") + "\n\n" + block + existing[at:]


def apply_change(
    repo: Path,
    path: Path,
    *,
    change: dict,
    text: str,
    action: str = "edit",
    user: str = "",
    when: datetime | None = None,
) -> dict:
    """The steward's wording, into the document or into a proposal beside it.

    One function for both Edit and Restore because they differ only in what
    the replacement text is — the steward's own words, or the wording that was
    there before. Everything after that is the same question: may this
    document be written to, and the answer comes from the document.
    """
    when = when or _now()
    repo, path = Path(repo), Path(path)
    rel = path.relative_to(repo).as_posix()
    section = str(change.get("section") or "").strip()
    now = str(change.get("now") or "")
    before = str(change.get("before") or "")
    anchor = int(change.get("anchor") or 0)
    replacement = (text or "").strip()

    if action == "edit" and not replacement:
        return {"ok": False, "error": "an edit needs some words"}

    lock = document_lock(path)
    if lock:
        block = _candidate_block(section=section, current=now or before, replacement=replacement)
        target = candidate_path(path)
        title = path.stem
        if target.exists():
            try:
                whole = _merge_candidate(target.read_text(encoding="utf-8"), block)
            except OSError:
                return {"ok": False, "error": f"could not read {target.name}"}
        else:
            whole = _candidate_text(
                rel=rel, title=title, lock=lock, block=block, user=user, when=when, action=action
            )
        target.write_text(whole, encoding="utf-8")
        return {
            "ok": True,
            "mode": "candidate",
            "locked": lock,
            "path": str(target),
            "file": target.relative_to(repo).as_posix(),
            "said": f"{path.name} is {lock}. Your wording is waiting in {target.name} for an answer.",
        }

    # The commit below names this one path, which means it would carry any
    # other uncommitted edit to the same file along with the steward's
    # sentence. Refusing is the honest answer: their word should be their word
    # and nothing else's.
    dirty = _git(repo, "status", "--porcelain", "--", rel)[1].strip()
    if dirty:
        return {
            "ok": False,
            "error": f"{rel} has uncommitted changes, so this edit would carry them too. Commit or discard them first.",
        }

    try:
        original = path.read_text(encoding="utf-8")
    except OSError:
        return {"ok": False, "error": f"could not read {rel}"}
    made, trouble = _reword(original, now=now, anchor=anchor, replacement=replacement)
    if trouble:
        return {"ok": False, "error": trouble}
    if made == original:
        return {"ok": False, "error": "that wording is already what the file says"}
    path.write_text(made, encoding="utf-8")

    who = f"{user or 'A steward'} via Converge"
    verb = "reworded" if action == "edit" else "restored"
    subject = f"{path.stem}: {section or 'one sentence'} {verb} by {user or 'a steward'} in Converge"
    ok, _out, problem = _git(
        repo,
        "-c",
        f"user.name={who}",
        "-c",
        f"user.email={_safe(user or 'steward')}@converge.invalid",
        "commit",
        "-q",
        "-m",
        subject,
        "--",
        rel,
    )
    if not ok:
        path.write_text(original, encoding="utf-8")
        return {"ok": False, "error": f"the commit did not go through: {problem.strip()[:200]}"}
    sha = _git(repo, "log", "-1", "--format=%H")[1].strip()
    return {
        "ok": True,
        "mode": "commit",
        "locked": "",
        "path": str(path),
        "file": rel,
        "sha": sha[:7],
        "author": who,
        "subject": subject,
        "said": f"Committed as {sha[:7]} — {subject}",
    }


__all__ = [
    "DECISION_WORDS",
    "LOCK_WORD",
    "apply_change",
    "candidate_path",
    "document_lock",
    "record_decision",
    "record_feedback",
    "steer",
]
