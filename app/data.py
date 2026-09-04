"""Everything the screens show, read from the project as it actually is.

There are no fixtures in this module. Each field traces to one of five real
sources — the batch directory's own files (`HIGHWAY.md`, `.width`,
`manifest.tsv`, `lanes/<lane>/…`), the repository's git history, the
repository's markdown, the repository's conformance ledger, and the tmux
sockets the lanes are actually running on — and when a source is not there the
answer says so in a sentence rather than filling the hole with a placeholder.

Two habits are load-bearing, both from the field guide:

* **The tmux socket is always explicit.** Every tmux call passes `-L <socket>`
  from the config. An ambient `$TMUX` is never read: the socket this process
  sits in is a different fact from the socket the lanes run on.
* **A lane's state comes from its own traces, never from how a pane looks.**
  Liveness is a session listing, freshness is a log file's mtime, and finished
  or stuck is a marker file. Nothing here reads a screen.
"""

from __future__ import annotations

import json
import re
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .config import ManagerConfig

# --------------------------------------------------------------------------
# running commands, carefully
# --------------------------------------------------------------------------


def run(args: list[str], cwd: Path | None = None, timeout: float = 8.0) -> str:
    """Stdout, or an empty string when the command is missing or fails.

    A tool that is not installed is a normal condition here — the page then
    says that part is unavailable rather than failing the whole request.
    """
    try:
        done = subprocess.run(
            args,
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    if done.returncode != 0:
        return ""
    return done.stdout


def git(repo: Path | None, *args: str, timeout: float = 8.0) -> str:
    if not repo or not Path(repo).exists():
        return ""
    return run(["git", *args], cwd=Path(repo), timeout=timeout)


def tmux_sessions(socket: str) -> set[str]:
    """Live session names on ONE explicit socket. Never reads `$TMUX`."""
    if not socket:
        return set()
    out = run(["tmux", "-L", socket, "list-sessions", "-F", "#{session_name}"], timeout=5.0)
    return {line.strip() for line in out.splitlines() if line.strip()}


# --------------------------------------------------------------------------
# small shared shapes
# --------------------------------------------------------------------------

_SENTENCE = re.compile(r"(?<=[.!?])\s+")


def sentences(text: str) -> list[str]:
    """Sentences of a paragraph run, with markdown scaffolding left out."""
    out: list[str] = []
    for line in (text or "").splitlines():
        line = line.strip()
        if not line or line.startswith(("#", "|", "```", "<!--")):
            continue
        line = re.sub(r"^[-*+]\s+", "", line)
        for piece in _SENTENCE.split(line):
            piece = piece.strip()
            if piece:
                out.append(piece)
    return out


def first_sentence(text: str) -> str:
    found = sentences(text)
    return found[0] if found else ""


def age_words(seconds: float | None) -> str:
    """A duration a person reads at a glance. Empty when nothing is known."""
    if seconds is None or seconds < 0:
        return ""
    minutes = int(seconds // 60)
    if minutes < 1:
        return "just now"
    if minutes < 60:
        return f"{minutes}m"
    hours = minutes // 60
    if hours < 48:
        return f"{hours}h"
    return f"{hours // 24}d"


def mtime_age(path: Path) -> float | None:
    try:
        return max(0.0, time.time() - path.stat().st_mtime)
    except OSError:
        return None


def render_markdown(text: str) -> str:
    """Markdown to HTML, server-side, with fenced code kept."""
    try:
        from markdown_it import MarkdownIt

        return MarkdownIt("commonmark", {"html": False}).enable("table").render(text or "")
    except Exception:
        escaped = (text or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        return f"<pre>{escaped}</pre>"


# --------------------------------------------------------------------------
# the batch directory: HIGHWAY.md, .width, manifest.tsv, lanes/
# --------------------------------------------------------------------------


def highway_text(mc: ManagerConfig) -> str:
    if not mc.batch_dir:
        return ""
    path = Path(mc.batch_dir) / "HIGHWAY.md"
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def section_body(text: str, heading_prefix: str) -> str:
    """The body under the first `## <prefix>…` heading, or an empty string."""
    lines = (text or "").splitlines()
    body: list[str] = []
    inside = False
    for line in lines:
        if line.startswith("## "):
            if inside:
                break
            inside = line[3:].strip().lower().startswith(heading_prefix.lower())
            continue
        if inside:
            body.append(line)
    return "\n".join(body).strip()


def width_of(mc: ManagerConfig) -> int | None:
    if not mc.batch_dir:
        return None
    try:
        return int((Path(mc.batch_dir) / ".width").read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return None


@dataclass(frozen=True)
class LaneRow:
    """One lane as the batch records it, before any liveness is asked about."""

    name: str
    worktree: str = ""
    branch: str = ""
    tmux: str = ""
    goal: str = ""
    log: str = ""
    launched_at: str = ""


def manifest_lanes(mc: ManagerConfig) -> list[LaneRow]:
    """Every lane this batch launched, in launch order, plus any on disk."""
    if not mc.batch_dir:
        return []
    batch = Path(mc.batch_dir)
    rows: list[LaneRow] = []
    seen: set[str] = set()
    manifest = batch / "manifest.tsv"
    if manifest.is_file():
        try:
            lines = manifest.read_text(encoding="utf-8").splitlines()
        except OSError:
            lines = []
        for line in lines[1:]:
            parts = (line.split("\t") + [""] * 8)[:8]
            name = parts[0].strip()
            if not name or name in seen:
                continue
            seen.add(name)
            rows.append(
                LaneRow(
                    name=name,
                    worktree=parts[1].strip(),
                    branch=parts[2].strip(),
                    tmux=parts[4].strip(),
                    goal=parts[5].strip(),
                    log=parts[6].strip(),
                    launched_at=parts[7].strip(),
                )
            )
    lanes_dir = batch / "lanes"
    if lanes_dir.is_dir():
        for child in sorted(p for p in lanes_dir.iterdir() if p.is_dir()):
            if child.name in seen:
                continue
            seen.add(child.name)
            rows.append(
                LaneRow(
                    name=child.name,
                    branch=f"lane/{child.name}",
                    tmux=f"hw__{batch.name}__{child.name}",
                    log=str(child / "lane.log"),
                )
            )
    return rows


def wave_key(lane_name: str) -> str:
    """The group a lane belongs to — its own name's first token."""
    return lane_name.split("-", 1)[0] or lane_name


def wave_label(key: str) -> str:
    match = re.fullmatch(r"([a-z])(\d+)", key)
    if match:
        word = {"w": "Wave", "e": "Experience"}.get(match.group(1), match.group(1).upper())
        return f"{word} {match.group(2)}"
    return key.replace("-", " ").title()


# --------------------------------------------------------------------------
# lane state — field guide §5, from traces only
# --------------------------------------------------------------------------

WORKING_SECONDS = 5 * 60
QUIET_SECONDS = 25 * 60

#: The only words a LANE may be shown in — `experience.v1` Core 6, quoted by
#: `experience-operation.v1` Core 8. All three are readings of one thing: is
#: this lane still doing anything? A lane that has reported back is no longer
#: answering that question at all, which is why it is carried apart (see
#: `OUTCOME_WORD`) rather than told in a word this vocabulary does not have.
LANE_WORD = {
    "working": "Working",
    "quiet": "Quiet",
    "silent": "Silent — may have died",
}

#: What a lane that has reported back produced, told in the WORK words of
#: `experience.v1` Core 6 — because that is what these two states are: work
#: finished, and work stopped. Neither is a lane word, and neither is shown as
#: one.
OUTCOME_WORD = {
    "done": "Done",
    "stuck": "Stuck",
}


def lane_paths(mc: ManagerConfig, lane: LaneRow) -> tuple[Path, Path, Path, Path]:
    batch = Path(mc.batch_dir) if mc.batch_dir else Path(".")
    home = batch / "lanes" / lane.name
    log = Path(lane.log) if lane.log else home / "lane.log"
    return home, log, home / "DONE.json", home / "BLOCKED.md"


def lane_state(mc: ManagerConfig, lane: LaneRow, live: set[str]) -> tuple[str, float | None]:
    _home, log, done, blocked = lane_paths(mc, lane)
    age = mtime_age(log)
    if done.is_file():
        return "done", age
    if blocked.is_file():
        return "stuck", age
    if lane.tmux not in live:
        return "silent", age
    if age is None:
        return "silent", age
    if age < WORKING_SECONDS:
        return "working", age
    if age < QUIET_SECONDS:
        return "quiet", age
    return "silent", age


def lane_title(mc: ManagerConfig, lane: LaneRow) -> str:
    """The lane's own goal file says what it is for. Its H1 is that sentence."""
    goal = Path(lane.goal) if lane.goal else None
    if goal is None and mc.batch_dir:
        goal = Path(mc.batch_dir) / "goals" / f"{lane.name}.md"
    try:
        text = goal.read_text(encoding="utf-8") if goal else ""
    except OSError:
        text = ""
    for line in text.splitlines():
        if line.startswith("# "):
            title = line[2:].strip()
            return title.split(" — ", 1)[-1].strip() if " — " in title else title
    return lane.name


def lane_evidence(mc: ManagerConfig, lane: LaneRow) -> str:
    """What the lane actually produced — `experience-operation.v1` Core 8.

    Commits first, then the marker a lane leaves when it reports back. A lane
    that has just started has neither, and the honest answer there is what this
    reading found rather than a claim about what exists: a branch that cannot
    be counted may be a branch that is not there yet, and saying "0 commits"
    would be asserting more than was read. When even the log is missing the
    answer is empty, so a lane with no trace at all is reported as one instead
    of being papered over with a sentence.
    """
    repo = mc.repo
    if repo and lane.branch:
        count = git(repo, "rev-list", "--count", f"main..{lane.branch}").strip()
        if count.isdigit():
            return f"{count} commits"
    _home, log, done, blocked = lane_paths(mc, lane)
    if done.is_file():
        try:
            payload = json.loads(done.read_text(encoding="utf-8"))
            return first_sentence(str(payload.get("summary") or "")) or "finished"
        except (OSError, ValueError):
            return "finished"
    if blocked.is_file():
        try:
            text = blocked.read_text(encoding="utf-8")
        except OSError:
            return "stopped, reason recorded"
        return blocked_reason(text)
    if log.is_file():
        return f"no commits found yet · {log.name}"
    return ""


#: How many of a lane's commits the fold carries. A lane with more says so.
PRODUCED_LIMIT = 12


def lane_produced(mc: ManagerConfig, lane: LaneRow) -> list[dict]:
    """What the lane actually produced, item by item — `experience-operation.v1` Core 8.

    `lane_evidence` above answers "how much?" in one line — *3 commits*. That
    is a claim, and Core 8 asks for the opposite: "Underneath sits what the
    lane actually produced, so a claim can be inspected rather than believed."
    A number cannot be inspected. This reads the things themselves off the
    machine — the commit subjects on the lane's own branch, and whatever the
    lane wrote into its report-back marker — so a steward can open the claim
    and read what it is made of.

    Every row says where it was read from. Nothing is invented: a lane with no
    branch, no commits and no marker yields an empty list, and the surface
    then says there is nothing to open rather than drawing an empty fold.
    """
    made: list[dict] = []
    repo = mc.repo
    if repo and lane.branch:
        out = git(repo, "log", "--format=%h %s", f"main..{lane.branch}", "-n", str(PRODUCED_LIMIT + 1))
        subjects = [line.strip() for line in out.splitlines() if line.strip()]
        for line in subjects[:PRODUCED_LIMIT]:
            made.append({"kind": "commit", "text": line, "source": f"git log main..{lane.branch}"})
        if len(subjects) > PRODUCED_LIMIT:
            made.append(
                {
                    "kind": "more",
                    "text": f"and more, beyond the {PRODUCED_LIMIT} newest shown here",
                    "source": f"git log main..{lane.branch}",
                }
            )
    _home, _log, done, blocked = lane_paths(mc, lane)
    if done.is_file():
        try:
            payload = json.loads(done.read_text(encoding="utf-8"))
            said = str(payload.get("summary") or "").strip()
        except (OSError, ValueError):
            said = ""
        if said:
            made.append({"kind": "finished", "text": said, "source": f"{done.name} beside the lane"})
    if blocked.is_file():
        try:
            said = blocked_reason(blocked.read_text(encoding="utf-8"))
        except OSError:
            said = ""
        if said:
            made.append({"kind": "stopped", "text": said, "source": f"{blocked.name} beside the lane"})
    return made


def blocked_reason(text: str) -> str:
    """The sentence a stopped lane leads with, out of its own marker file.

    A marker opens with a heading and bold metadata fields — a date, a branch —
    and none of those is a reason. The named fields that ARE a reason are
    preferred; failing those, the first paragraph of plain prose. Lines are
    rejoined into paragraphs first, so the answer is a whole sentence rather
    than the fragment that happened to fit one line.
    """
    named = ("outcome", "cause", "reason", "why", "blocked")
    fields: list[tuple[str, list[str]]] = []
    prose: list[list[str]] = []
    label = ""
    run: list[str] = []

    def close() -> None:
        nonlocal label, run
        if run:
            (fields if label else prose).append((label, run) if label else run)  # type: ignore[arg-type]
        label, run = "", []

    for line in (text or "").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith(("#", ">", "|", "```")):
            close()
            continue
        match = re.match(r"^\*\*([^*]+?):?\*\*:?\s*(.*)$", stripped)
        if match:
            close()
            label = match.group(1).strip().lower()
            run = [match.group(2)] if match.group(2) else []
            continue
        run.append(stripped)
    close()

    def first(paragraph: list[str]) -> str:
        for piece in _SENTENCE.split(" ".join(word for word in paragraph if word)):
            piece = piece.strip()
            if len(piece) >= 20:
                return piece
        return ""

    for wanted in named:
        for name, paragraph in fields:
            if name.startswith(wanted):
                found = first(paragraph)
                if found:
                    return found
    for paragraph in prose:
        found = first(paragraph)
        if found:
            return found
    return "stopped, reason recorded"


def lane_merged(mc: ManagerConfig, lane: LaneRow, merge_subjects: str) -> bool:
    _home, _log, done, _blocked = lane_paths(mc, lane)
    if done.is_file():
        return True
    return bool(lane.branch) and lane.branch in merge_subjects


# --------------------------------------------------------------------------
# the repository: docs, ledger, git
# --------------------------------------------------------------------------

SKIP_DOC = ("-candidate.md", ".superseded.md")


def repo_id(repo: Path) -> str:
    return Path(repo).name


def doc_id(path: Path, repo: Path) -> str:
    rel = Path(path).relative_to(repo).as_posix()
    if rel.lower() == "docs/vision.md":
        return "vision"
    return Path(rel).name.split(".")[0].lower()


def repo_docs(repo: Path) -> list[Path]:
    """The documents a steward steers by: the vision and the contracts."""
    found: list[Path] = []
    vision = Path(repo) / "docs" / "VISION.md"
    if vision.is_file():
        found.append(vision)
    contracts = Path(repo) / "contracts"
    if contracts.is_dir():
        for one in sorted(contracts.glob("*.v1.md")):
            if any(one.name.endswith(tail) for tail in SKIP_DOC):
                continue
            found.append(one)
    return found


def _ledger(repo: Path):
    try:
        from amplifier_converge.reading import kept

        return kept, kept.read_promises(Path(repo))
    except Exception:
        return None, None


def doc_state(repo: Path, path: Path, reading=None, kept_module=None) -> dict:
    """One word for whether this promise is being kept, from the ledger only.

    `kept` when the ledger's own fold says Kept. `gap` when the ledger watches
    this promise and says anything else. `draft` when nothing watches it — no
    ledger at all, or no rows naming this file — which is a different silence
    from a measured gap and is said apart.
    """
    if kept_module is None or reading is None:
        kept_module, reading = _ledger(repo)
    if kept_module is None or reading is None or not reading.available:
        return {"state": "draft", "standing": "", "standingSentence": "No conformance ledger in this project yet.", "clauses": 0}
    rel = Path(path).relative_to(repo).as_posix()
    standing = kept_module.standing_of(rel, reading.value)
    if standing.clauses == 0:
        state = "draft"
    elif standing.word == "Kept":
        state = "kept"
    else:
        state = "gap"
    return {
        "state": state,
        "standing": standing.word,
        "standingSentence": standing.sentence,
        "clauses": standing.clauses,
    }


def doc_title(path: Path) -> tuple[str, str]:
    """(short title, full title) — the document's own H1 when it has one."""
    try:
        text = Path(path).read_text(encoding="utf-8")
    except OSError:
        return Path(path).stem, Path(path).stem
    full = ""
    for line in text.splitlines():
        if line.startswith("# "):
            full = line[2:].strip()
            break
    name = Path(path).name
    if name.lower() == "vision.md":
        short = "Vision"
    else:
        short = name.split(".")[0].replace("-", " ").title()
    return short, (full or short)


def confidence(repo: Path) -> dict:
    """How much of what this project promises is being kept, clause by clause."""
    rows_path = Path(repo) / "ledger" / "rows.yaml"
    counts = {"kept": 0, "notyet": 0, "broken": 0, "pinned": 0, "cantcheck": 0}
    if not rows_path.is_file():
        return {"pct": 0, **{k: counts[k] for k in ("kept", "notyet", "broken")}, "available": False}
    try:
        import yaml

        rows = yaml.safe_load(rows_path.read_text(encoding="utf-8")) or []
    except Exception:
        return {"pct": 0, "kept": 0, "notyet": 0, "broken": 0, "available": False}
    bucket = {
        "CONFORMS": "kept",
        "GAP": "notyet",
        "VIOLATION": "broken",
        "DIVERGED": "broken",
        "OPEN-PINNED": "pinned",
        "NOT-ASSERTABLE": "cantcheck",
        "EXCLUDED": "cantcheck",
    }
    for row in rows:
        if not isinstance(row, dict):
            continue
        where = bucket.get(str(row.get("disposition") or "").strip().upper())
        if where:
            counts[where] += 1
    checkable = counts["kept"] + counts["notyet"] + counts["broken"]
    pct = round(100 * counts["kept"] / checkable) if checkable else 0
    return {
        "pct": pct,
        "kept": counts["kept"],
        "notyet": counts["notyet"],
        "broken": counts["broken"],
        "pinnedOpen": counts["pinned"],
        "cantCheck": counts["cantcheck"],
        "available": True,
    }


# --------------------------------------------------------------------------
# proposals — the candidate siblings beside a document
# --------------------------------------------------------------------------


def _headed(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    key = ""
    body: list[str] = []
    for line in (text or "").splitlines():
        if line.startswith("## "):
            if key:
                out[key] = "\n".join(body).strip()
            key = line[3:].strip().lower()
            body = []
            continue
        body.append(line)
    if key:
        out[key] = "\n".join(body).strip()
    return out


def _bullets(text: str) -> list[str]:
    return [re.sub(r"^[-*+]\s+", "", line.strip()) for line in (text or "").splitlines() if line.strip().startswith(("-", "*", "+"))]


def candidate_files(path: Path) -> list[Path]:
    """Every open proposal against this document, by the repo's conventions.

    Two names are in use: a sibling `<stem>…-candidate.md` beside the document,
    and a `CANDIDATE-<topic>.md` whose `target:` line names this file.
    """
    path = Path(path)
    base = path.name.split(".")[0]
    found: list[Path] = []
    for sibling in sorted(path.parent.glob("*.md")):
        name = sibling.name
        if sibling == path:
            continue
        if "candidate" in name.lower() and name.split(".")[0] == base:
            found.append(sibling)
        elif name.startswith("CANDIDATE-"):
            try:
                head = sibling.read_text(encoding="utf-8")[:1500]
            except OSError:
                continue
            if re.search(rf"^target:\s*\S*{re.escape(path.name)}", head, re.M):
                found.append(sibling)
    return found


def proposals_for(path: Path, repo: Path) -> list[dict]:
    made: list[dict] = []
    for one in candidate_files(path):
        try:
            text = one.read_text(encoding="utf-8")
        except OSError:
            continue
        heads = _headed(text)
        title = ""
        for line in text.splitlines():
            if line.startswith("# "):
                title = line[2:].strip()
                break
        evidence_key = next((k for k in heads if "evidence" in k), "")
        unchanged_key = next((k for k in heads if "not change" in k or "does not change" in k), "")
        change_key = next((k for k in heads if "exact change" in k or "the change" in k), "")
        source = "Manager session"
        match = re.search(r"^(?:author|source|proposed-by):\s*(.+)$", text[:1500], re.M)
        if match:
            source = match.group(1).strip()
        made.append(
            {
                "id": one.stem,
                "title": title or one.stem,
                "source": source,
                "why": first_sentence(heads.get(change_key, "")) if change_key else "",
                "recommendation": "",
                "tradeoffs": [],
                "evidence": _bullets(heads.get(evidence_key, "")) if evidence_key else [],
                "unchanged": heads.get(unchanged_key, "") if unchanged_key else "",
                "file": Path(one).relative_to(repo).as_posix(),
            }
        )
    return made


# --------------------------------------------------------------------------
# sentence-level change since the steward last read
# --------------------------------------------------------------------------


def changes_for(repo: Path, path: Path, since: str = "", limit: int = 40) -> list[dict]:
    """What moved in this document since `since`, sentence by sentence.

    The reading itself lives in `app/changes.py`, which starts from git's own
    hunks rather than from a flat sentence diff. It is imported here rather
    than at the top of the module because that module reads this one's `git`.
    """
    from . import changes as change_reading

    return change_reading.changes_for(repo, path, since=since, limit=limit)


def history_for(repo: Path, path: Path, limit: int = 8) -> list[dict]:
    rel = Path(path).relative_to(repo).as_posix()
    log = git(repo, "log", "--follow", f"--format=%H%x1f%ad%x1f%s", "--date=format:%b %-d · %H:%M", "-n", str(limit), "--", rel)
    made: list[dict] = []
    for index, line in enumerate(log.splitlines()):
        parts = line.split("\x1f")
        if len(parts) < 3:
            continue
        sha, date, subject = parts[0], parts[1], parts[2]
        made.append(
            {
                "id": "now" if index == 0 else sha[:8],
                "label": "Current" if index == 0 else date.split(" · ")[0],
                "date": date,
                "note": subject,
                "sha": sha[:8],
            }
        )
    return made


def sections_of(text: str) -> list[list[str]]:
    """`## ` sections as [title, html], with any preamble kept under the H1."""
    lines = (text or "").splitlines()
    made: list[list[str]] = []
    title = ""
    body: list[str] = []
    for line in lines:
        if line.startswith("## "):
            if body and "".join(body).strip():
                made.append([title or "Overview", render_markdown("\n".join(body))])
            title = line[3:].strip()
            body = []
            continue
        if line.startswith("# ") and not made and not body:
            title = line[2:].strip()
            continue
        body.append(line)
    if body and "".join(body).strip():
        made.append([title or "Overview", render_markdown("\n".join(body))])
    return made


# --------------------------------------------------------------------------
# why a batch exists, and why the plan changed — experience-operation.v1 Core 2
# --------------------------------------------------------------------------

#: The steward-facing record, relative to the repository root.
OWNER_LOG = "docs/workflow/OWNER-RETURN-LOG.md"

#: A weave-in line opens with the stamp the manager session wrote it at.
_WEAVE_LINE = re.compile(r"^\s*[-*+]\s*(\d{4}-\d\d-\d\dT[\d:]+Z)?\s*(.*)$")

#: Core 2's second sentence — "when the plan is redrawn, the reason for the
#: redraw is shown too". A redraw is written into the weave-in log as REOPENED:
#: the run had closed and the steward's word opened it again.
_REDRAW = re.compile(r"\bREOPENED\b")

#: What a wave carries when no record names it. It is not a reason and must
#: never be dressed as one — a steward reading this learns that the manager
#: session never wrote down why this batch was grouped, which is true and
#: useful, and is the one thing a list of lane names never says.
NO_REASON_ON_RECORD = "The plan does not record why this batch was grouped."


def weave_log(text: str) -> list[tuple[str, str]]:
    """(stamp, what was said) for every line of HIGHWAY.md's weave-in log.

    This is the manager session's own running account of the run: one line per
    launch, cycle, merge, incident and reopen. It is where a batch's reason is
    actually written down, so it is the first place read for one.
    """
    made: list[tuple[str, str]] = []
    for line in section_body(text, "weave-in log").splitlines():
        if not line.strip().startswith(("-", "*", "+")):
            continue
        match = _WEAVE_LINE.match(line)
        if not match:
            continue
        said = (match.group(2) or "").strip()
        if said:
            made.append(((match.group(1) or "").strip(), said))
    return made


def _named_by(*words: str) -> list:
    return [re.compile(rf"\b{re.escape(w)}\b", re.I) for w in words if w]


#: How a wave is named in prose: `wave 2`, `wave-1`, `experience wave e1`, `W8`.
_WAVE_MENTION = re.compile(r"\b(?:(wave|experience)\s*-?\s*|([we]))(\d+)\b", re.I)


def waves_named_in(said: str) -> set[str]:
    """Every wave a sentence names, as keys — `wave-1` and `W1` are both `w1`."""
    found: set[str] = set()
    for word, letter, number in _WAVE_MENTION.findall(said or ""):
        head = (letter or word[:1]).lower()
        found.add(f"{head}{int(number)}")
    return found


def wave_reason(
    key: str,
    label: str,
    members: list[str],
    weave: list[tuple[str, str]],
    entries: list[tuple[str, str, str]],
) -> dict:
    """Why this batch of work exists, quoted from the record that says so.

    Two records are read, in the order they were written for: HIGHWAY.md's
    weave-in log (where a launch is recorded, with the word that authorised
    it), then the owner return log (where the manager session told the steward
    what a wave was for). Nothing is composed here — the reason is the record's
    own sentence, and `source` names which record and which line it came from.

    The weave-in log is a launch record and the manager session writes a wave
    into it as an identifier (`W8:`, `w8-gap`), so a bare key is safe there.

    The owner log is prose and two things are refused in it. A bare key or a
    one-word label is never matched — measured 2026-09-04, both `app` and its
    label `App` match "the companion app's first pass", a sentence about a
    different thing entirely. And a sentence that names *more than one* wave is
    refused as well: "…verified all four wave-1 lanes…and refilled with wave 2"
    names two and says what neither is for, so it is not either one's reason.
    """
    for stamp, said in weave:
        if any(p.search(said) for p in _named_by(key, *members)):
            where = "HIGHWAY.md · weave-in log"
            return {"reason": said, "recorded": True, "source": f"{where} · {stamp}" if stamp else where}
    numbered = label if re.fullmatch(r"[A-Za-z]+ \d+", label or "") else ""
    for _date, heading, body in entries:
        for said in sentences(body):
            if not any(p.search(said) for p in _named_by(numbered, *members)):
                continue
            if waves_named_in(said) - {key}:
                continue
            return {"reason": said, "recorded": True, "source": f"{OWNER_LOG} · {heading}"}
    return {"reason": NO_REASON_ON_RECORD, "recorded": False, "source": ""}


def plan_redraws(text: str) -> list[dict]:
    """Every time the plan was redrawn, and why, in the record's own words."""
    return [
        {"when": stamp, "why": said}
        for stamp, said in weave_log(text)
        if _REDRAW.search(said)
    ]


# --------------------------------------------------------------------------
# the return brief — experience-operation.v1 Core 3
# --------------------------------------------------------------------------

#: The five parts, in the clause's order. `label` is the contract's own wording
#: (Core 3), because that is what a steward reads. `opens` matches the label a
#: manager session writes into the log, which is the return-brief convention's
#: (`context/manager/return-brief.md`) — the two vocabularies are deliberately
#: not merged: one is what the page says, the other is what the file says.
BRIEF_PARTS = (
    ("timeAway", "Time away", re.compile(r"^\**\s*time away\b", re.I)),
    ("finished", "What finished", re.compile(r"^\**\s*finished\b", re.I)),
    ("stuck", "What is stuck", re.compile(r"^\**\s*stuck\b", re.I)),
    ("needsYou", "What needs your word", re.compile(r"^\**\s*needs? you\b", re.I)),
    ("quietlyChanged", "What quietly changed", re.compile(r"^\**\s*(anything quietly broken|quietly)\b", re.I)),
)


def brief_parts(body: str) -> list[dict]:
    """The labelled parts of one return-brief entry, in the clause's order.

    A part starts at the line that opens with its bold label and runs to the
    next labelled line, so a part written as two sentences is not cut in half.
    An entry that labels nothing yields nothing — this reads a shape, it never
    decides which unlabelled sentence "is really" the stuck part.
    """
    found: dict[str, list[str]] = {}
    holding = ""
    for line in (body or "").splitlines():
        text = line.strip()
        if not text or text.startswith(("#", "|", "```", "<!--")):
            continue
        opened = next((part for part, _label, rx in BRIEF_PARTS if rx.match(text)), "")
        if opened:
            holding = opened
            text = re.sub(r"^\**\s*[^*.:]{0,32}[.:]\**\s*", "", text, count=1).strip()
        if holding and text:
            found.setdefault(holding, []).append(text)
    return [
        {"part": part, "label": label, "text": " ".join(found[part]).strip()}
        for part, label, _rx in BRIEF_PARTS
        if found.get(part)
    ]


def return_brief(entries: list[tuple[str, str, str]]) -> list[str]:
    """What a returning steward reads first — the newest entry, whole.

    Nothing here is truncated. The reading this replaces kept the entry's first
    six sentences, and measured against the real log on 2026-09-04 that is how
    the one part a steward most needs — what needs their word — fell off the
    end of a fifteen-sentence entry and the kit reported the brief never said
    it. Six sentences is not one of the clause's five parts.

    An entry written to the convention is returned as its five labelled parts,
    each opening with the label Core 3 gives it. An entry that labels nothing —
    every entry written before the convention landed — is returned as its own
    sentences, unlabelled and complete. No sentence is ever given a label the
    manager session did not write: the brief a steward reads is the brief that
    was written, and `brief_reading` says plainly which parts are missing.
    """
    if not entries:
        return []
    body = entries[-1][2]
    parts = brief_parts(body)
    if parts:
        return [f"{one['label']}: {one['text']}" for one in parts]
    return sentences(body)


def brief_reading(entries: list[tuple[str, str, str]]) -> dict:
    """Which of Core 3's five parts the newest entry actually labels.

    Shown beside the brief so an absent part is visible as an absence. A brief
    with a part missing is a real, countable defect (the convention: "a return
    that never got briefed stands in the file as a stamp with parts missing"),
    and hiding it behind prose is how it stays missing.
    """
    if not entries:
        return {"entry": "", "date": "", "source": OWNER_LOG, "labelled": False, "parts": []}
    date, heading, body = entries[-1]
    said = {one["part"]: one for one in brief_parts(body)}
    return {
        "entry": heading,
        "date": date,
        "source": f"{OWNER_LOG} · {heading}",
        "labelled": bool(said),
        "parts": [
            {"part": part, "label": label, "recorded": part in said}
            for part, label, _rx in BRIEF_PARTS
        ],
    }


# --------------------------------------------------------------------------
# the confidence timeline — experience-operation.v1 Core 4
# --------------------------------------------------------------------------


def owner_log_commits(repo: Path | None) -> dict[str, tuple[str, str]]:
    """Entry heading → (short sha, date) of the commit that first recorded it.

    One `git log -p` over one small file, read for the `## ` headings each
    commit *added*. That is what makes a turn on the timeline inspectable
    outside this app: a steward can run `git show <sha>` and read the same
    words the page is showing them.

    The date returned is the *commit's*, which is a different fact from the
    date in the entry's own heading and is not corrected to match it — the
    newest entry here is headed 2026-09-04 and was committed on 2026-09-03.
    """
    if not repo:
        return {}
    out = git(repo, "log", "--reverse", "--format=%x01%h%x09%ad", "--date=short", "-p", "-U0", "--", OWNER_LOG)
    made: dict[str, tuple[str, str]] = {}
    sha = when = ""
    for line in out.splitlines():
        if line.startswith("\x01"):
            sha, _tab, when = line[1:].partition("\t")
            continue
        if line.startswith("+## "):
            heading = _split_heading(line[4:].strip())[1]
            made.setdefault(heading, (sha, when))
    return made


def confidence_timeline(entries: list[tuple[str, str, str]], repo: Path | None) -> list[list]:
    """The turns that changed how sure the manager session is, newest first.

    Core 4 asks for two things and the old reading gave one: it said *that*
    confidence moved and left no way to inspect *why*. Each turn now carries
    its evidence — the whole entry the one-sentence summary was cut from, the
    file it lives in, and the commit that recorded it — so the claim can be
    opened rather than believed.

    A turn stays the row the surface already read, `[date, title, sentence]`,
    with the evidence appended as a fourth place rather than the row being
    replaced by an object. Adding to a shape breaks nothing that reads it by
    position; changing the shape breaks every reader at once.
    """
    commits = owner_log_commits(repo)
    made: list[list] = []
    for date, heading, body in reversed(entries):
        said = sentences(body)
        sha, when = commits.get(heading, ("", ""))
        made.append(
            [
                date,
                heading,
                said[0] if said else "",
                {
                    "kind": "return brief",
                    "source": OWNER_LOG,
                    "section": heading,
                    "ref": f"{OWNER_LOG} § {heading}",
                    "commit": sha,
                    "committedOn": when,
                    "sentences": said,
                },
            ]
        )
    return made


# --------------------------------------------------------------------------
# the three payloads
# --------------------------------------------------------------------------


def _owner_log_entries(repo: Path | None) -> list[tuple[str, str, str]]:
    """(date, heading, body) for every owner-return entry, newest last."""
    if not repo:
        return []
    path = Path(repo) / "docs" / "workflow" / "OWNER-RETURN-LOG.md"
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return []
    made: list[tuple[str, str, str]] = []
    heading = ""
    body: list[str] = []
    for line in text.splitlines():
        if line.startswith("## "):
            if heading:
                made.append((*_split_heading(heading), "\n".join(body).strip()))
            heading = line[3:].strip()
            body = []
            continue
        body.append(line)
    if heading:
        made.append((*_split_heading(heading), "\n".join(body).strip()))
    return made


def _split_heading(heading: str) -> tuple[str, str]:
    parts = re.split(r"\s+[—-]\s+", heading, maxsplit=1)
    if len(parts) == 2:
        return parts[0].strip(), parts[1].strip()
    return heading.strip(), heading.strip()


def _needs_items(mc: ManagerConfig) -> list[dict]:
    """Open proposals across the repos, plus tracker items waiting on a person."""
    made: list[dict] = []
    for repo in mc.repos:
        if not Path(repo).exists():
            continue
        for doc in repo_docs(repo):
            for one in proposals_for(doc, repo):
                made.append(
                    {
                        "kind": "proposal",
                        "title": one["title"],
                        "where": {"repoId": repo_id(repo), "docId": doc_id(doc, repo)},
                        "since": _file_since(Path(repo) / one["file"]),
                    }
                )
    if mc.tracker_project:
        out = run(["amplifier-work-tracker", "list", "--project", mc.tracker_project, "--status", "blocked"], timeout=10.0)
        for line in out.splitlines():
            line = line.strip()
            if not line or line.lower().startswith(("id", "total", "no ")):
                continue
            made.append({"kind": "work", "title": line[:120], "where": {"itemId": line.split()[0]}, "since": ""})
    made.sort(key=lambda one: one.get("since") or "", reverse=True)
    return made


def _file_since(path: Path) -> str:
    try:
        return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat(timespec="seconds")
    except OSError:
        return ""


def manager_payload(mc: ManagerConfig) -> dict:
    """The manager card — status, lanes, objective, and what needs a person."""
    text = highway_text(mc)
    lanes = manifest_lanes(mc)
    live = tmux_sessions(mc.tmux_socket)
    active = [one for one in lanes if one.tmux in live]
    width = width_of(mc)
    needs = _needs_items(mc)

    ages = [a for a in (mtime_age(lane_paths(mc, one)[1]) for one in lanes) if a is not None]
    youngest = min(ages) if ages else (mtime_age(Path(mc.batch_dir) / "HIGHWAY.md") if mc.batch_dir else None)

    if needs:
        status, label = "waiting", "Waiting on you"
    elif active:
        status, label = "running", "Running"
    else:
        status, label = "idle", "Idle"

    outcome = section_body(text, "outcome")
    rationale = section_body(text, "priority rationale")
    outcome_sentences = sentences(outcome)
    waves = sorted({wave_key(one.name) for one in lanes})

    deadline = ""
    for line in text.splitlines():
        if line.strip().lower().startswith("deadline:"):
            deadline = line.split(":", 1)[1].strip()
            break

    entries = _owner_log_entries(mc.repo)
    summary = ""
    if entries:
        last = sentences(entries[-1][2])
        summary = last[-1] if last else ""

    return {
        "id": mc.id,
        "name": mc.name,
        "status": status,
        "statusLabel": label,
        "age": age_words(youngest),
        "summary": summary,
        "objective": outcome_sentences[0] if outcome_sentences else "",
        "deadline": deadline,
        "strategy": f"{len(waves)} waves" if waves else "Continuous",
        "lanesMax": width if width is not None else len(active),
        "lanesActive": len(active),
        "needs": len(needs),
        "repos": len(mc.repos),
        "projects": 1 if mc.tracker_project else 0,
        "strategyNarrative": " ".join(sentences(rationale)[:2]) or " ".join(outcome_sentences[1:3]),
        "batchDir": str(mc.batch_dir or ""),
        "tmuxSocket": mc.tmux_socket,
        "managerTmux": mc.manager_tmux,
    }


def repositories_payload(mc: ManagerConfig) -> list[dict]:
    made: list[dict] = []
    for repo in mc.repos:
        repo = Path(repo)
        if not repo.exists():
            made.append({"id": repo.name, "name": repo.name.upper(), "path": str(repo), "docs": [], "note": "This repository is not on this machine."})
            continue
        kept_module, reading = _ledger(repo)
        docs = []
        for one in repo_docs(repo):
            short, full = doc_title(one)
            state = doc_state(repo, one, reading, kept_module)
            docs.append(
                {
                    "id": doc_id(one, repo),
                    "title": short,
                    "fullTitle": full,
                    "state": state["state"],
                    "standing": state["standing"],
                    "standingSentence": state["standingSentence"],
                    "clauses": state["clauses"],
                    "path": one.relative_to(repo).as_posix(),
                }
            )
        made.append({"id": repo_id(repo), "name": repo.name.upper(), "path": str(repo), "docs": docs})
    return made


def find_doc(mc: ManagerConfig, repo_ident: str, doc_ident: str) -> tuple[Path, Path] | None:
    for repo in mc.repos:
        repo = Path(repo)
        if repo_id(repo) != repo_ident:
            continue
        for one in repo_docs(repo):
            if doc_id(one, repo) == doc_ident:
                return repo, one
    return None


def doc_payload(repo: Path, path: Path, *, since: str = "", kept: set[str] | None = None) -> dict:
    """One document as a screen reads it, from that steward's own last reading.

    `since` is the commit this steward has already read up to and `kept` the
    changes they have already answered for. Both are the caller's to supply,
    because both belong to a person rather than to the document.
    """
    from . import changes as change_reading
    from . import writes

    repo, path = Path(repo), Path(path)
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError:
        raw = ""
    short, full = doc_title(path)
    updated = git(repo, "log", "-1", "--format=%ad by %an", "--date=format:%b %-d, %Y", "--", path.relative_to(repo).as_posix()).strip()
    state = doc_state(repo, path)
    already = kept or set()
    moved = changes_for(repo, path, since=since)
    for one in moved:
        one["kept"] = one["id"] in already
    lock = writes.document_lock(path)
    return {
        "path": path.relative_to(repo).as_posix(),
        "title": full or short,
        "updated": f"Updated {updated}" if updated else "Not committed yet",
        "state": state["state"],
        "standing": state["standing"],
        "standingSentence": state["standingSentence"],
        "locked": lock,
        "editable": not lock,
        "sections": sections_of(raw),
        "raw": raw,
        "changes": moved,
        "reading": change_reading.reading_point(repo, path, since),
        "proposals": proposals_for(path, repo),
        "history": history_for(repo, path),
    }


def tracker_counts(mc: ManagerConfig) -> dict:
    """The work queue's own counts, one entry per status word it prints.

    Read once and handed to everything that needs a number out of it, so a
    single reading of the queue stands behind the flow measures and the two
    queue numbers rather than two readings that can disagree.
    """
    made: dict[str, int] = {}
    if not mc.tracker_project:
        return made
    out = run(["amplifier-work-tracker", "status", "--project", mc.tracker_project], timeout=12.0)
    if not out.strip():
        return made
    for line in out.splitlines():
        name, _colon, value = line.partition(":")
        digits = re.search(r"\d+", value)
        if not digits:
            continue
        key = name.strip().upper()
        made[key] = int(digits.group())
    return made


def throughput(counts: dict, merged: int, reopened: int) -> dict:
    """Whether work is moving — the five measures `experience-operation.v1`
    Core 5 names, and no sixth.

    Derived · resolved · verified · reopened · stuck. Stuck is the queue's own
    blocked count: work that has stopped moving. It says nothing about whether
    reality is moving toward the agreement, which is a separate reading and the
    one that counts (Core 5 again) — the two are never summed.
    """
    made = {
        "derived": 0,
        "resolved": 0,
        "verified": merged,
        "reopened": reopened,
        "stuck": 0,
        "spark": [],
        "available": False,
    }
    if not counts:
        return made
    made["derived"] = counts.get("TOTAL", 0)
    made["resolved"] = counts.get("RESOLVED", 0)
    made["stuck"] = counts.get("BLOCKED", 0)
    made["available"] = True
    return made


def queue_reading(counts: dict) -> dict:
    """Work truly ready — the first of Core 7's two numbers.

    The second, work waiting on you, is the manager card's own `needs` count
    and is not copied here: one truth, one place. A surface shows them side by
    side, which is what the clause asks for.
    """
    return {"trulyReady": counts.get("READY", 0), "available": bool(counts)}


def operation_payload(mc: ManagerConfig) -> dict:
    """The manager session at work.

    Lanes arrive in two lists, because a lane is in one of two situations and
    they are read in different words. `lanes` are the lanes at work — each one
    told in a lane word (`LANE_WORD`), which answers "is this still doing
    anything?". `reported` are the lanes that have already come back, told in
    the work words `OUTCOME_WORD` — finished, or stopped. Every lane appears in
    exactly one of the two, and both carry the evidence the lane produced.
    """
    lanes = manifest_lanes(mc)
    live = tmux_sessions(mc.tmux_socket)
    merge_log = git(mc.repo, "log", "--merges", "--format=%s", "-n", "400") if mc.repo else ""

    lane_items: list[dict] = []
    reported_items: list[dict] = []
    by_wave: dict[str, list[tuple[str, int]]] = {}
    wave_live: dict[str, bool] = {}
    merged_count = 0
    for one in lanes:
        state, age = lane_state(mc, one, live)
        key = wave_key(one.name)
        is_merged = lane_merged(mc, one, merge_log)
        merged_count += 1 if is_merged else 0
        by_wave.setdefault(key, []).append((one.name, 1 if is_merged else 0))
        wave_live[key] = wave_live.get(key, False) or (one.tmux in live)
        row = {
            "id": one.name,
            "title": lane_title(mc, one),
            "worker": f"{one.name} · {one.branch}" if one.branch else one.name,
            "wave": wave_label(key),
            "age": age_words(age),
            "evidence": lane_evidence(mc, one),
            # Core 8 — the claim above, and the things it is made of, so the
            # claim can be opened instead of believed.
            "produced": lane_produced(mc, one),
            "live": one.tmux in live,
            "tmux": {"socket": mc.tmux_socket, "session": one.tmux},
        }
        if state in LANE_WORD:
            row["status"] = state
            row["statusLabel"] = LANE_WORD[state]
            lane_items.append(row)
        else:
            row["outcome"] = state
            row["outcomeLabel"] = OUTCOME_WORD[state]
            reported_items.append(row)

    order = list(by_wave)
    now_index = next((i for i, key in enumerate(order) if wave_live.get(key)), -1)
    waves: list[dict] = []
    highway = highway_text(mc)
    board = _lane_board(highway)
    weave = weave_log(highway)
    log_entries = _owner_log_entries(mc.repo)
    for index, key in enumerate(order):
        items = by_wave[key]
        done = sum(flag for _name, flag in items)
        progress = round(100 * done / len(items)) if items else 0
        if progress == 100:
            phase, cls = "DONE", "done"
        elif index == now_index:
            phase, cls = "NOW", "now"
        elif now_index >= 0 and index < now_index:
            phase, cls = "DONE" if progress == 100 else "STRETCH", "stretch"
        elif index == now_index + 1:
            phase, cls = "NEXT", "next"
        else:
            phase, cls = "STRETCH", "stretch"
        names = [name for name, _flag in items]
        # Core 2: a wave says what a batch of work is FOR. The lane board is
        # the manager session's own one-line-per-lane summary and is used when
        # the batch keeps one; otherwise the reason is quoted from the record.
        # What is never used again is the lane names joined by commas: that is
        # a list of members, which is exactly what the clause says a wave is
        # not, and it was this page's title for all eleven waves until now.
        titles = [board.get(name, "") for name in names if board.get(name)]
        why = wave_reason(key, wave_label(key), names, weave, log_entries)
        waves.append(
            {
                "id": key,
                "label": wave_label(key),
                "title": "; ".join(titles[:3]) if titles else why["reason"],
                "reason": why["reason"],
                "reasonRecorded": why["recorded"],
                "reasonSource": why["source"],
                "phase": phase,
                "cls": cls,
                "progress": progress,
                "items": [[name, flag] for name, flag in items],
            }
        )

    reopened = len(_REDRAW.findall(highway))
    counts = tracker_counts(mc)

    return {
        "waves": waves,
        "redraws": plan_redraws(highway),
        "lanes": lane_items,
        "reported": reported_items,
        "timeline": confidence_timeline(log_entries, mc.repo),
        "returnBrief": return_brief(log_entries),
        "briefReading": brief_reading(log_entries),
        "throughput": throughput(counts, merged_count, reopened),
        "queue": queue_reading(counts),
        "confidence": confidence(mc.repo) if mc.repo else {"pct": 0, "kept": 0, "notyet": 0, "broken": 0, "available": False},
    }


def _lane_board(text: str) -> dict[str, str]:
    """`## Lane board` rows, when the batch keeps one: lane name → item."""
    body = section_body(text, "lane board")
    made: dict[str, str] = {}
    for line in body.splitlines():
        if not line.strip().startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) < 2 or not cells[0] or set(cells[0]) <= set("-: "):
            continue
        if cells[0].lower() == "lane":
            continue
        made[cells[0]] = cells[1]
    return made


__all__ = [
    "BRIEF_PARTS",
    "LANE_WORD",
    "NO_REASON_ON_RECORD",
    "OUTCOME_WORD",
    "OWNER_LOG",
    "LaneRow",
    "age_words",
    "blocked_reason",
    "brief_parts",
    "brief_reading",
    "changes_for",
    "confidence",
    "confidence_timeline",
    "doc_id",
    "doc_payload",
    "doc_state",
    "find_doc",
    "git",
    "history_for",
    "lane_state",
    "manager_payload",
    "manifest_lanes",
    "operation_payload",
    "owner_log_commits",
    "plan_redraws",
    "proposals_for",
    "queue_reading",
    "repo_docs",
    "repo_id",
    "repositories_payload",
    "return_brief",
    "run",
    "sections_of",
    "throughput",
    "tmux_sessions",
    "tracker_counts",
    "wave_reason",
    "waves_named_in",
    "weave_log",
    "_needs_items",
]
