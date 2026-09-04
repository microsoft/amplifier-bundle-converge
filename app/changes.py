"""What moved in a document since the steward last read it.

Git already knows what changed. It computed the hunks when the commit was
made, and every hunk says exactly which removed lines correspond to which
added ones. The earlier version of this view threw that away: it diffed the
two texts as flat sentence lists and then paired the results by position, so
one inserted sentence shifted every pair after it and the steward was shown
before/now couples that had never been the same sentence.

So the reading here starts from `git diff <since> <head> -U0` and never leaves
it. Each hunk is aligned on its own; a hunk with no removed lines is an
insertion and is shown as **New** with no Before; one with no added lines is a
deletion and is shown as **Removed**; and a hunk with both is aligned by how
alike the sentences actually are, in order, so a sentence that has no partner
above the likeness floor stays unpaired rather than stealing its neighbour's.

Two labels come out of the same pass and must not be confused, because the
steward noticed they had been:

* **section** is where in the document the sentence lives -- the heading path
  above it plus the numbered item it sits in, e.g. `Principles > 8`.
* **source** is which commit changed it -- subject, short sha, and date, read
  from `git blame` on the line itself, so a range covering several commits
  attributes each sentence to the one that actually touched it.
"""

from __future__ import annotations

import difflib
import hashlib
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .data import git

#: A sentence ends at punctuation followed by space. Deliberately simple: this
#: splits prose, and prose is what a steward reads.
SENTENCE = re.compile(r"(?<=[.!?])\s+")

HUNK = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")
HEADING = re.compile(r"^(#{1,6})\s+(.*)$")
NUMBERED = re.compile(r"^(\d+)[.)]\s+")
LIST_MARK = re.compile(r"^(?:[-*+]\s+|\d+[.)]\s+)")
BLAME_HEAD = re.compile(r"^([0-9a-f]{40})\s+(\d+)\s+(\d+)")

#: How alike two sentences must be before they are called the same sentence
#: reworded. Below this they are a separate removal and a separate addition,
#: which is the honest answer when a sentence was replaced outright.
LIKENESS_FLOOR = 0.45

#: The shortest run of shared characters that may stand as evidence on its own.
#: Below it, "the ", " a ", and "ing" would make any two English sentences look
#: related.
RUN_FLOOR = 12

#: Alignment is quadratic. A hunk larger than this is aligned in order rather
#: than by likeness -- slower is not better if the page never arrives.
ALIGN_CELLS = 4000

SEPARATOR = " \u203a "


# --------------------------------------------------------------------------
# where a line lives: the heading path and the numbered item
# --------------------------------------------------------------------------


def _path_of(stack: list[tuple[int, str]], item: str) -> str:
    parts = [title for level, title in stack if level >= 2]
    if not parts and stack:
        parts = [stack[0][1]]
    if item:
        parts.append(item)
    return SEPARATOR.join(part for part in parts if part)


def heading_paths(text: str) -> dict[int, str]:
    """Every line number mapped to the heading path that governs it.

    The path is the open headings from level two down -- the document's own H1
    is its title and is already on the screen -- with the numbered list item
    appended when the line sits inside one. A blank line closes an item unless
    what follows is indented under it.
    """
    lines = (text or "").splitlines()
    stack: list[tuple[int, str]] = []
    item = ""
    fenced = False
    found: dict[int, str] = {}
    for index, line in enumerate(lines, start=1):
        if line.lstrip().startswith("```"):
            fenced = not fenced
            found[index] = _path_of(stack, item)
            continue
        if fenced:
            # A `# comment` inside a code fence is code, not a heading.
            found[index] = _path_of(stack, item)
            continue
        head = HEADING.match(line)
        if head:
            level = len(head.group(1))
            while stack and stack[-1][0] >= level:
                stack.pop()
            stack.append((level, head.group(2).strip()))
            item = ""
            found[index] = _path_of(stack, "")
            continue
        numbered = NUMBERED.match(line)
        if numbered:
            item = numbered.group(1)
        elif not line.strip():
            following = lines[index] if index < len(lines) else ""
            if not (following.startswith((" ", "\t")) and following.strip()):
                item = ""
        found[index] = _path_of(stack, item)
    return found


def sentences_of(line: str) -> list[str]:
    """The sentences of one line, exactly as they read in the file.

    List markers and heading hashes are dropped because they are scaffolding,
    but nothing else is touched: what comes back can be found again in the file
    verbatim, which is what makes editing and restoring possible at all.
    """
    stripped = (line or "").strip()
    if not stripped or stripped.startswith(("|", "```", "<!--", "-->")):
        return []
    head = HEADING.match(stripped)
    if head:
        return [head.group(2).strip()] if head.group(2).strip() else []
    body = LIST_MARK.sub("", stripped)
    return [piece.strip() for piece in SENTENCE.split(body) if piece.strip()]


# --------------------------------------------------------------------------
# which commit changed which line
# --------------------------------------------------------------------------


def commit_meta(repo: Path, sha: str) -> tuple[str, str, str]:
    """(short sha, subject, YYYY-MM-DD) for one commit, or empty strings."""
    if not sha:
        return "", "", ""
    out = git(repo, "log", "-1", "--format=%h%x1f%s%x1f%ad", "--date=format:%Y-%m-%d", sha).strip()
    parts = out.split("\x1f")
    if len(parts) < 3:
        return sha[:7], "", ""
    return parts[0], parts[1], parts[2]


def source_words(short_sha: str, subject: str, date: str) -> str:
    """`<subject> \u00b7 <7-char sha> \u00b7 <date>` -- the card's provenance line."""
    return " \u00b7 ".join(piece for piece in (subject, short_sha, date) if piece)


def blame_lines(repo: Path, sha: str, rel: str) -> dict[int, tuple[str, str, str]]:
    """Line number -> (short sha, subject, date) for the file at one commit.

    One `git blame` for the whole file rather than one per card: the porcelain
    form names each commit once and then refers back to it, so the whole map
    costs a single process.
    """
    out = git(repo, "blame", "--line-porcelain", sha, "--", rel, timeout=20.0)
    if not out:
        return {}
    known: dict[str, tuple[str, str, str]] = {}
    found: dict[int, str] = {}
    current = ""
    when: dict[str, int] = {}
    zone: dict[str, str] = {}
    subject: dict[str, str] = {}
    for line in out.splitlines():
        head = BLAME_HEAD.match(line)
        if head:
            current = head.group(1)
            found[int(head.group(3))] = current
            continue
        if not current:
            continue
        if line.startswith("summary "):
            subject[current] = line[len("summary ") :].strip()
        elif line.startswith("author-time "):
            try:
                when[current] = int(line.split()[1])
            except (IndexError, ValueError):
                pass
        elif line.startswith("author-tz "):
            zone[current] = line.split()[1] if len(line.split()) > 1 else "+0000"
    for one in set(found.values()):
        stamp = when.get(one)
        date = ""
        if stamp is not None:
            offset = zone.get(one, "+0000")
            try:
                minutes = int(offset[1:3]) * 60 + int(offset[3:5])
                shift = timedelta(minutes=minutes if offset.startswith("+") else -minutes)
            except (ValueError, IndexError):
                shift = timedelta(0)
            date = (datetime.fromtimestamp(stamp, tz=timezone.utc) + shift).strftime("%Y-%m-%d")
        known[one] = (one[:7], subject.get(one, ""), date)
    return {number: known[one] for number, one in found.items() if one in known}


# --------------------------------------------------------------------------
# the commits a reading sits between
# --------------------------------------------------------------------------


def head_of(repo: Path, rel: str) -> str:
    """The last commit that touched this file. Empty when it has never been."""
    return git(repo, "log", "-1", "--format=%H", "--", rel).strip()


def previous_of(repo: Path, rel: str, before: str = "") -> str:
    """The commit before the given one for this file, or before HEAD."""
    args = ["log", "-2", "--format=%H", before or "HEAD", "--", rel]
    lines = [one.strip() for one in git(repo, *args).splitlines() if one.strip()]
    return lines[1] if len(lines) > 1 else ""


# --------------------------------------------------------------------------
# alignment inside one hunk
# --------------------------------------------------------------------------


def likeness(left: str, right: str) -> float:
    """How much two sentences are the same sentence, from 0 to 1.

    Two readings, and the kinder one wins. The first is difflib's ratio, which
    answers well when a sentence was tweaked. The second is the longest shared
    run measured against the shorter sentence, which answers well when a
    sentence was *extended* -- a clause tripling its length drags the ratio
    below any usable floor even though its whole opening survived word for
    word. A run only counts once it is long enough not to be grammar.
    """
    matcher = difflib.SequenceMatcher(None, left, right)
    longest = max((block.size for block in matcher.get_matching_blocks()), default=0)
    shortest = min(len(left), len(right)) or 1
    run = longest / shortest if longest >= RUN_FLOOR else 0.0
    return max(matcher.ratio(), run)


def align(old: list[str], new: list[str]) -> list[tuple[int | None, int | None]]:
    """Pair sentences by likeness, keeping their order, leaving gaps honest.

    This is the whole fix for the misalignment the steward reported. A pairing
    is only made when the two sentences are actually alike; a sentence with no
    partner above the floor is returned as a gap and becomes its own New or
    Removed card instead of shifting everything after it by one.
    """
    rows, columns = len(old), len(new)
    if not rows:
        return [(None, j) for j in range(columns)]
    if not columns:
        return [(i, None) for i in range(rows)]
    if rows * columns > ALIGN_CELLS:
        return [(i if i < rows else None, i if i < columns else None) for i in range(max(rows, columns))]

    alike = [[0.0] * columns for _ in range(rows)]
    for i in range(rows):
        for j in range(columns):
            score = likeness(old[i], new[j])
            alike[i][j] = score if score >= LIKENESS_FLOOR else 0.0

    best = [[0.0] * (columns + 1) for _ in range(rows + 1)]
    for i in range(1, rows + 1):
        for j in range(1, columns + 1):
            paired = best[i - 1][j - 1] + alike[i - 1][j - 1] if alike[i - 1][j - 1] > 0 else -1.0
            best[i][j] = max(best[i - 1][j], best[i][j - 1], paired)

    made: list[tuple[int | None, int | None]] = []
    i, j = rows, columns
    while i > 0 and j > 0:
        paired = best[i - 1][j - 1] + alike[i - 1][j - 1] if alike[i - 1][j - 1] > 0 else -1.0
        if alike[i - 1][j - 1] > 0 and abs(best[i][j] - paired) < 1e-9:
            made.append((i - 1, j - 1))
            i -= 1
            j -= 1
        elif abs(best[i][j] - best[i - 1][j]) < 1e-9:
            made.append((i - 1, None))
            i -= 1
        else:
            made.append((None, j - 1))
            j -= 1
    while i > 0:
        made.append((i - 1, None))
        i -= 1
    while j > 0:
        made.append((None, j - 1))
        j -= 1
    made.reverse()
    return made


# --------------------------------------------------------------------------
# the cards
# --------------------------------------------------------------------------


def change_id(rel: str, hunk: str, before: str, now: str) -> str:
    """A card's name, stable for as long as the change itself is.

    It is the file, the hunk header, and both texts -- nothing about the
    request that produced it -- so the same change keeps the same name across
    reloads and that is what a kept mark can be hung on.
    """
    raw = "\x1f".join((rel, hunk, before, now)).encode("utf-8")
    return hashlib.sha1(raw).hexdigest()[:12]


def _card(
    *,
    rel: str,
    hunk: str,
    kind: str,
    before: str,
    now: str,
    section: str,
    source: tuple[str, str, str],
    anchor: int,
) -> dict:
    short, subject, date = source
    return {
        "id": change_id(rel, hunk, before, now),
        "kind": kind,
        "section": section,
        "before": before,
        "now": now,
        "source": source_words(short, subject, date),
        "sourceSha": short,
        "sourceSubject": subject,
        "sourceDate": date,
        "anchor": anchor,
        "hunk": hunk,
        "kept": False,
    }


def _hunks(diff: str) -> list[tuple[str, int, int, list[str], list[str], list[int], list[int]]]:
    """Every hunk as (header, old start, new start, old lines, new lines, ...)."""
    made: list[tuple[str, int, int, list[str], list[str], list[int], list[int]]] = []
    header = ""
    old_at = new_at = 0
    old_lines: list[str] = []
    new_lines: list[str] = []
    old_numbers: list[int] = []
    new_numbers: list[int] = []
    old_cursor = new_cursor = 0

    def close() -> None:
        if header:
            made.append((header, old_at, new_at, list(old_lines), list(new_lines), list(old_numbers), list(new_numbers)))

    for line in diff.splitlines():
        found = HUNK.match(line)
        if found:
            close()
            # Only the range itself, never the trailing context git appends:
            # that context is the line above the change and would make the
            # card's name change whenever an unrelated line moved.
            header = f"@@{line.split('@@')[1]}@@"
            old_at = int(found.group(1))
            new_at = int(found.group(3))
            old_cursor, new_cursor = old_at, new_at
            old_lines, new_lines, old_numbers, new_numbers = [], [], [], []
            continue
        if not header:
            continue
        if line.startswith("-") and not line.startswith("---"):
            old_lines.append(line[1:])
            old_numbers.append(old_cursor)
            old_cursor += 1
        elif line.startswith("+") and not line.startswith("+++"):
            new_lines.append(line[1:])
            new_numbers.append(new_cursor)
            new_cursor += 1
    close()
    return made


def _spread(lines: list[str], numbers: list[int]) -> list[tuple[str, int]]:
    made: list[tuple[str, int]] = []
    for line, number in zip(lines, numbers):
        for piece in sentences_of(line):
            made.append((piece, number))
    return made


def changes_for(repo: Path, path: Path, *, since: str = "", limit: int = 40) -> list[dict]:
    """Every sentence that moved between `since` and the file's last commit.

    With no `since` the reading starts at the commit before the last one, so a
    steward who has never opened this document still sees the most recent
    change rather than an empty page.
    """
    repo, path = Path(repo), Path(path)
    rel = Path(path).relative_to(repo).as_posix()
    head = head_of(repo, rel)
    if not head:
        return []
    since = since or previous_of(repo, rel)
    if not since or since == head:
        return []

    diff = git(repo, "diff", since, head, "-U0", "--", rel, timeout=20.0)
    if not diff.strip():
        return []

    new_paths = heading_paths(git(repo, "show", f"{head}:{rel}"))
    old_paths = heading_paths(git(repo, "show", f"{since}:{rel}"))
    blamed = blame_lines(repo, head, rel)
    fallback = commit_meta(repo, head)

    made: list[dict] = []
    for header, _old_at, new_at, old_lines, new_lines, old_numbers, new_numbers in _hunks(diff):
        old_pieces = _spread(old_lines, old_numbers)
        new_pieces = _spread(new_lines, new_numbers)
        if not old_pieces and not new_pieces:
            continue

        steps: list[tuple[int | None, int | None]] = []
        if not old_pieces or not new_pieces:
            steps = align([text for text, _ in old_pieces], [text for text, _ in new_pieces])
        else:
            sequence = difflib.SequenceMatcher(
                None, [text for text, _ in old_pieces], [text for text, _ in new_pieces], autojunk=False
            )
            for tag, i1, i2, j1, j2 in sequence.get_opcodes():
                if tag == "equal":
                    continue
                block = align([text for text, _ in old_pieces[i1:i2]], [text for text, _ in new_pieces[j1:j2]])
                steps += [
                    (None if left is None else i1 + left, None if right is None else j1 + right) for left, right in block
                ]

        for left, right in steps:
            before = old_pieces[left][0] if left is not None else ""
            now = new_pieces[right][0] if right is not None else ""
            if right is not None:
                line = new_pieces[right][1]
                section = new_paths.get(line, "")
                source = blamed.get(line, fallback)
                anchor = line
            else:
                section = old_paths.get(old_pieces[left][1], "") if left is not None else ""
                source = fallback
                anchor = new_at
            kind = "changed" if before and now else ("new" if now else "removed")
            made.append(
                _card(
                    rel=rel,
                    hunk=header,
                    kind=kind,
                    before=before,
                    now=now,
                    section=section,
                    source=source,
                    anchor=anchor,
                )
            )
            if len(made) >= limit:
                return made
    return made


def reading_point(repo: Path, path: Path, since: str = "") -> dict:
    """The two commits a Changes view sits between, said in plain words."""
    repo, path = Path(repo), Path(path)
    rel = Path(path).relative_to(repo).as_posix()
    head = head_of(repo, rel)
    since = since or previous_of(repo, rel)
    head_short, head_subject, head_date = commit_meta(repo, head)
    since_short, since_subject, since_date = commit_meta(repo, since)
    return {
        "headSha": head,
        "headShort": head_short,
        "headSource": source_words(head_short, head_subject, head_date),
        "sinceSha": since,
        "sinceShort": since_short,
        "sinceSource": source_words(since_short, since_subject, since_date),
        "sinceDate": since_date,
    }


def find_change(repo: Path, path: Path, change: str, *, since: str = "") -> dict | None:
    for one in changes_for(repo, path, since=since):
        if one["id"] == change:
            return one
    return None


__all__ = [
    "LIKENESS_FLOOR",
    "align",
    "blame_lines",
    "change_id",
    "changes_for",
    "commit_meta",
    "find_change",
    "head_of",
    "heading_paths",
    "previous_of",
    "reading_point",
    "sentences_of",
    "source_words",
]
