"""What the page shows, read from the project rather than invented.

Every reader here answers one question and, where the answer is a fixture
rather than the real thing, says so in the payload itself (``real: false``).
The front end prints that distinction on the surface, so nobody has to guess
which parts of this proof of concept are wired to reality.

Nothing in this module writes. The four writes live in ``serve.py``.
"""

from __future__ import annotations

import csv
import difflib
import json
import re
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from markdown_lite import render as render_markdown
from markdown_lite import split_paragraphs

# The repo's own readers, used read-only. Importing them rather than
# re-deriving keeps one truth about the plain words a reader may see.
from amplifier_converge.reading.whatchanged import sentences as split_sentences
from amplifier_converge.words import UNKNOWN, surface_word

HERE = Path(__file__).resolve().parent
FIXTURES = HERE / "fixtures"

#: A lane that has not written for this long is no longer merely quiet.
#: Same threshold the repo's own lane reader uses.
SILENT_AFTER_SECONDS = 30 * 60
QUIET_AFTER_SECONDS = 5 * 60


# ---------------------------------------------------------------------------
# small helpers
# ---------------------------------------------------------------------------


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def _fixture(name: str) -> object:
    text = _read(FIXTURES / name)
    if not text:
        return {}
    if name.endswith(".json"):
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {}
    return text


def _git(repo: Path, *args: str) -> tuple[bool, str]:
    try:
        done = subprocess.run(
            ["git", "-C", str(repo), *args],
            capture_output=True,
            text=True,
            timeout=20,
        )
    except (OSError, subprocess.SubprocessError) as exc:  # pragma: no cover
        return False, str(exc)
    return done.returncode == 0, (done.stdout or done.stderr).strip()


def _last_sentence(paragraph: str) -> str:
    parts = split_sentences(paragraph)
    return parts[-1].strip() if parts else paragraph.strip()


# ---------------------------------------------------------------------------
# the return brief — real, from the owner return log
# ---------------------------------------------------------------------------


def return_brief(repo: Path) -> dict:
    """The newest brief the manager session wrote for the steward."""
    path = repo / "docs" / "workflow" / "OWNER-RETURN-LOG.md"
    text = _read(path)
    if not text:
        return {
            "real": False,
            "heading": "",
            "sentences": [],
            "note": "There is no return log in this project yet.",
            "source": str(path.relative_to(repo)) if path.is_absolute() else str(path),
        }
    blocks = re.split(r"^## ", text, flags=re.MULTILINE)[1:]
    if not blocks:
        return {"real": False, "heading": "", "sentences": [], "note": "The return log has no entries yet."}
    newest = blocks[-1].strip()
    heading, _, body = newest.partition("\n")
    body = body.strip()
    return {
        "real": True,
        "heading": heading.strip(),
        "sentences": split_sentences(body),
        "note": "",
        "source": "docs/workflow/OWNER-RETURN-LOG.md",
        "entries": len(blocks),
    }


# ---------------------------------------------------------------------------
# the work queue — real, from the exported queue
# ---------------------------------------------------------------------------

#: Queue statuses that mean the steward is the one holding this up.
_WAITING = ("blocked", "deferred", "intake")


def queue(repo: Path) -> dict:
    path = repo / "docs" / "work-items.json"
    text = _read(path)
    if not text:
        return {"real": False, "total": 0, "waiting": 0, "note": "This project keeps no work queue here."}
    try:
        items = json.loads(text)
    except json.JSONDecodeError:
        return {"real": False, "total": 0, "waiting": 0, "note": "The work queue could not be read."}
    waiting = [i for i in items if str(i.get("status", "")).lower() in _WAITING]
    working = [i for i in items if str(i.get("status", "")).lower() == "held"]
    ready = [i for i in items if str(i.get("status", "")).lower() in ("open", "ready")]
    done = [i for i in items if str(i.get("status", "")).lower() == "resolved"]
    return {
        "real": True,
        "total": len(items),
        "waiting": len(waiting),
        "working": len(working),
        "ready": len(ready),
        "done": len(done),
        "source": "docs/work-items.json",
        "waiting_items": [
            {
                "id": i.get("id", ""),
                "title": i.get("title", ""),
                "word": surface_word(i.get("status", "")),
            }
            for i in waiting
        ],
    }


# ---------------------------------------------------------------------------
# the lanes — real, from the run directory beside this repo
# ---------------------------------------------------------------------------


@dataclass
class Run:
    """Where the manager session keeps this run's lanes."""

    root: Path

    @property
    def manifest(self) -> Path:
        return self.root / "manifest.tsv"

    @property
    def available(self) -> bool:
        return self.manifest.is_file()


def find_run(repo: Path) -> Run:
    """The run directory: two levels above a lane's copy of the code."""
    for candidate in (repo.parent.parent, repo.parent, Path.home() / "dev" / "hw-converge"):
        if (candidate / "manifest.tsv").is_file():
            return Run(candidate)
    return Run(repo.parent.parent)


def _lane_word(seconds: float | None) -> str:
    if seconds is None:
        return "Can't check"
    if seconds >= SILENT_AFTER_SECONDS:
        return "Silent — may have died"
    if seconds >= QUIET_AFTER_SECONDS:
        return f"Quiet {int(seconds // 60)}m"
    return "Working"


def lanes(repo: Path) -> dict:
    run = find_run(repo)
    if not run.available:
        return {
            "real": False,
            "lanes": [],
            "running": 0,
            "intended": None,
            "note": "No run directory sits beside this project, so there are no lanes to show.",
        }
    rows: list[dict] = []
    try:
        with run.manifest.open(encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle, delimiter="\t"))
    except OSError:
        pass

    out: list[dict] = []
    for row in rows:
        name = row.get("lane", "")
        finished = (run.root / "logs" / f"{name}.DONE.json").is_file()
        if finished:
            continue
        log = Path(row.get("log", ""))
        age: float | None = None
        if log.is_file():
            age = max(0.0, time.time() - log.stat().st_mtime)
        out.append(
            {
                "name": name,
                "branch": row.get("branch", ""),
                "launched_at": row.get("launched_at", ""),
                "word": _lane_word(age),
                "minutes_since_write": None if age is None else round(age / 60, 1),
                "session": row.get("tmux", ""),
                "goal": Path(row.get("goal", "")).name,
            }
        )
    out.sort(key=lambda lane: lane["launched_at"], reverse=True)
    intended = _intended_width(run.root)
    return {
        "real": True,
        "lanes": out,
        "running": len(out),
        "intended": intended,
        "note": "",
        "source": "manifest.tsv beside this project",
    }


def _intended_width(root: Path) -> int | None:
    text = _read(root / "HIGHWAY.md")
    found = re.findall(r"[Ww]idth (\d+)", text)
    if found:
        return int(found[-1])
    return None


# ---------------------------------------------------------------------------
# the documents — real: the vision and the contracts in this project
# ---------------------------------------------------------------------------

#: A document says its own state in the parenthetical at the end of its H1,
#: and nowhere else (documents.v1 clause 6). Whatever word it uses there is
#: translated by the project's own map in words.py rather than by a second
#: copy of that vocabulary here — so a word retired tomorrow keeps working.
_STATE_RE = re.compile(r"\((?P<state>[A-Za-z][^)]*)\)\s*$")


def _doc_paths(repo: Path) -> list[Path]:
    out: list[Path] = []
    vision = repo / "docs" / "VISION.md"
    if vision.is_file():
        out.append(vision)
    contracts = sorted((repo / "contracts").glob("*.md")) if (repo / "contracts").is_dir() else []
    out.extend(contracts)
    return out


def _title_and_word(text: str, fallback: str) -> tuple[str, str]:
    """A document's title, and the one plain word for where it stands.

    No parenthetical means the document does not say, and the honest answer is
    that we cannot tell — never a guess, and never the friendlier of the two.
    """
    for line in text.splitlines():
        if line.startswith("# "):
            title = line[2:].strip()
            match = _STATE_RE.search(title)
            if not match:
                return title, UNKNOWN
            return title[: match.start()].strip(" —-"), surface_word(match.group("state"))
    return fallback, UNKNOWN


def documents(repo: Path) -> dict:
    paths = _doc_paths(repo)
    if not paths:
        return {"real": False, "documents": [], "note": "This project has no vision or contracts yet."}
    out = []
    for path in paths:
        text = _read(path)
        title, word = _title_and_word(text, path.stem)
        rel = str(path.relative_to(repo))
        out.append(
            {
                "slug": rel.replace("/", "~"),
                "path": rel,
                "title": title,
                "word": word,
                "kind": "vision" if path.name == "VISION.md" else "contract",
                "words": len(text.split()),
            }
        )
    return {"real": True, "documents": out, "note": "", "source": "docs/ and contracts/ in this project"}


def _path_for(repo: Path, slug: str) -> Path | None:
    rel = slug.replace("~", "/")
    if ".." in rel or rel.startswith("/"):
        return None
    path = repo / rel
    if not path.is_file():
        return None
    return path


def document(repo: Path, slug: str) -> dict:
    path = _path_for(repo, slug)
    if path is None:
        return {"real": False, "note": "That document is not in this project."}
    text = _read(path)
    title, word = _title_and_word(text, path.stem)
    return {
        "real": True,
        "slug": slug,
        "path": str(path.relative_to(repo)),
        "title": title,
        "word": word,
        "html": render_markdown(text),
        "paragraphs": split_paragraphs(text),
        "source_text": text,
    }


def changes(repo: Path, slug: str) -> dict:
    """What changed between the last two saved versions, sentence by sentence."""
    path = _path_for(repo, slug)
    if path is None:
        return {"real": False, "note": "That document is not in this project."}
    rel = str(path.relative_to(repo))
    ok, out = _git(repo, "log", "-n", "2", "--format=%H%x1f%ad%x1f%s", "--date=short", "--", rel)
    versions = [line.split("\x1f") for line in out.splitlines() if line.strip()] if ok else []
    if len(versions) < 2:
        return {
            "real": False,
            "note": "This document has only one saved version, so there is nothing to compare yet.",
            "added": [],
            "removed": [],
        }
    new_sha, new_when, new_subject = versions[0]
    old_sha, old_when, old_subject = versions[1]
    ok_new, new_text = _git(repo, "show", f"{new_sha}:{rel}")
    ok_old, old_text = _git(repo, "show", f"{old_sha}:{rel}")
    if not (ok_new and ok_old):
        return {"real": False, "note": "The saved versions of this document could not be read.", "added": [], "removed": []}
    before = split_sentences(old_text)
    after = split_sentences(new_text)
    matcher = difflib.SequenceMatcher(a=before, b=after, autojunk=False)
    added: list[str] = []
    removed: list[str] = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag in ("replace", "delete"):
            removed.extend(before[i1:i2])
        if tag in ("replace", "insert"):
            added.extend(after[j1:j2])
    return {
        "real": True,
        "slug": slug,
        "added": added,
        "removed": removed,
        "newer": {"when": new_when, "why": new_subject},
        "older": {"when": old_when, "why": old_subject},
        "note": "",
    }


# ---------------------------------------------------------------------------
# proposals — a real one from this project, plus anything you asked for
# ---------------------------------------------------------------------------

_PARTS = (
    ("change", ("the exact change", "exact change", "what changes", "the change")),
    ("evidence", ("the evidence", "evidence")),
    ("not_change", ("what does not change", "not change")),
)


def _section(text: str, names: tuple[str, ...]) -> str:
    lines = text.splitlines()
    wanted = tuple(n.lower() for n in names)
    start: int | None = None
    level = 0
    for i, line in enumerate(lines):
        match = re.match(r"^(#{1,6})\s+(.*)$", line)
        if not match:
            continue
        heading = match.group(2).strip().lower().strip("*_`:")
        if start is None and any(w in heading for w in wanted):
            start, level = i + 1, len(match.group(1))
        elif start is not None and len(match.group(1)) <= level:
            return "\n".join(lines[start:i]).strip()
    return "\n".join(lines[start:]).strip() if start is not None else ""


def _proposal_files(repo: Path) -> list[Path]:
    out: list[Path] = []
    for folder in (repo / "docs" / "workflow", repo / "contracts", repo / "docs"):
        if folder.is_dir():
            out.extend(sorted(p for p in folder.glob("*candidate*.md")))
    return out


def proposals(repo: Path, asks: list[dict] | None = None) -> dict:
    out: list[dict] = []
    for path in _proposal_files(repo):
        text = _read(path)
        title, _word = _title_and_word(text, path.stem)
        out.append(
            {
                "key": path.stem,
                "title": title,
                "from": "your manager session",
                "where": str(path.relative_to(repo)),
                "target": _target_of(path.name),
                "change": render_markdown(_section(text, _PARTS[0][1])),
                "evidence": render_markdown(_section(text, _PARTS[1][1])),
                "not_change": render_markdown(_section(text, _PARTS[2][1])),
                "real": True,
            }
        )
    for ask in asks or []:
        out.append(
            {
                "key": ask.get("key", ""),
                "title": ask.get("title", "A proposal you asked for"),
                "from": "you asked for this",
                "where": "poc/asks.jsonl",
                "target": ask.get("target", ""),
                "change": "<p>Not drafted yet. Your manager session has the request and will bring back a proposal.</p>",
                "evidence": f"<blockquote>{_escape(ask.get('paragraph', ''))}</blockquote>",
                "not_change": "<p>Nothing changes until you answer with a word.</p>",
                "real": True,
                "asked_at": ask.get("at", ""),
                "question": ask.get("question", ""),
            }
        )
    return {"real": bool(out), "proposals": out, "note": "" if out else "Nothing is waiting for your word."}


def _target_of(filename: str) -> str:
    match = re.match(r"^(?P<target>.+)\.v(?P<version>\d+)-candidate", filename)
    return f"{match.group('target')}.v{int(match.group('version')) - 1}" if match else ""


def _escape(text: str) -> str:
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


# ---------------------------------------------------------------------------
# manager sessions — the home screen
# ---------------------------------------------------------------------------


def manager_sessions(repo: Path) -> list[dict]:
    """One card per manager session, sorted by which one needs you most."""
    brief = return_brief(repo)
    work = queue(repo)
    board = lanes(repo)
    pending = proposals(repo)["proposals"]
    run = find_run(repo)

    needs_you = len(pending) + int(work.get("waiting", 0))
    last_line = _last_sentence(" ".join(brief.get("sentences", []))) if brief.get("sentences") else ""

    cards = [
        {
            "id": "converge-experience",
            "name": "Amplifier Converge — the experience wave",
            "anchor": str(run.root) if run.available else str(repo),
            "repos": ["amplifier-bundle-converge"],
            "needs_you": needs_you,
            "needs_you_parts": [
                f"{len(pending)} waiting for your word" if pending else "",
                f"{work.get('waiting', 0)} pieces of work waiting on you" if work.get("waiting") else "",
            ],
            "running": board.get("running", 0),
            "intended": board.get("intended"),
            "last_line": last_line,
            "quiet": needs_you == 0,
            "real": True,
        },
        {
            "id": "converge-repo",
            "name": "Amplifier Converge — the method itself",
            "anchor": str(repo),
            "repos": ["amplifier-bundle-converge"],
            "needs_you": 0,
            "needs_you_parts": [],
            "running": 0,
            "intended": None,
            "last_line": (
                f"{work.get('done', 0)} of {work.get('total', 0)} pieces of work are done; "
                f"the vision and {max(0, len(documents(repo)['documents']) - 1)} contracts are in the code record."
            ),
            "quiet": True,
            "real": True,
        },
    ]
    cards.sort(key=lambda card: (-card["needs_you"], card["name"]))
    return cards


# ---------------------------------------------------------------------------
# the fixtures, plainly labelled
# ---------------------------------------------------------------------------


def strategy() -> dict:
    return {"real": False, "text": str(_fixture("strategy.md")).strip(), "note": "Written by hand for this proof of concept."}


def waves() -> dict:
    payload = _fixture("waves.json")
    if isinstance(payload, dict):
        payload.setdefault("real", False)
        return payload
    return {"real": False, "waves": []}


def confidence() -> dict:
    payload = _fixture("confidence.json")
    if isinstance(payload, dict):
        payload.setdefault("real", False)
        return payload
    return {"real": False, "points": []}


def console_transcript() -> str:
    return str(_fixture("console-transcript.txt"))
