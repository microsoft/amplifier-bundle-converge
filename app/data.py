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

import difflib
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

STATE_WORD = {
    "working": "Working",
    "quiet": "Quiet",
    "silent": "Silent — may have died",
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
    repo = mc.repo
    if repo and lane.branch:
        count = git(repo, "rev-list", "--count", f"main..{lane.branch}").strip()
        if count.isdigit():
            return f"{count} commits"
    _home, _log, done, blocked = lane_paths(mc, lane)
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
    return ""


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
# sentence-level change since the last commit
# --------------------------------------------------------------------------


def _sentences_with_section(text: str) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    section = ""
    for line in (text or "").splitlines():
        if line.startswith("## "):
            section = line[3:].strip()
            continue
        if line.startswith("# "):
            section = section or line[2:].strip()
            continue
        stripped = line.strip()
        if not stripped or stripped.startswith(("|", "```", "<!--")):
            continue
        stripped = re.sub(r"^[-*+]\s+", "", stripped)
        for piece in _SENTENCE.split(stripped):
            piece = piece.strip()
            if piece:
                out.append((section, piece))
    return out


def changes_for(repo: Path, path: Path, limit: int = 12) -> list[dict]:
    """What changed in this document between its last two commits, by sentence."""
    rel = Path(path).relative_to(repo).as_posix()
    log = git(repo, "log", "--follow", "--format=%H%x1f%s", "-n", "2", "--", rel)
    entries = [line.split("\x1f", 1) for line in log.splitlines() if "\x1f" in line]
    if len(entries) < 2:
        return []
    (new_sha, subject), (old_sha, _older) = entries[0], entries[1]
    new_text = git(repo, "show", f"{new_sha}:{rel}")
    old_text = git(repo, "show", f"{old_sha}:{rel}")
    if not new_text and not old_text:
        return []
    new_pairs = _sentences_with_section(new_text)
    old_pairs = _sentences_with_section(old_text)
    matcher = difflib.SequenceMatcher(None, [s for _, s in old_pairs], [s for _, s in new_pairs])
    made: list[dict] = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        before = [s for _, s in old_pairs[i1:i2]]
        now = [s for _, s in new_pairs[j1:j2]]
        section = (new_pairs[j1][0] if j1 < len(new_pairs) else "") or (old_pairs[i1][0] if i1 < len(old_pairs) else "")
        for index in range(max(len(before), len(now))):
            made.append(
                {
                    "id": len(made) + 1,
                    "section": section,
                    "before": before[index] if index < len(before) else "",
                    "now": now[index] if index < len(now) else "",
                    "source": subject,
                }
            )
            if len(made) >= limit:
                return made
    return made


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


def doc_payload(repo: Path, path: Path) -> dict:
    repo, path = Path(repo), Path(path)
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError:
        raw = ""
    short, full = doc_title(path)
    updated = git(repo, "log", "-1", "--format=%ad by %an", "--date=format:%b %-d, %Y", "--", path.relative_to(repo).as_posix()).strip()
    state = doc_state(repo, path)
    return {
        "path": path.relative_to(repo).as_posix(),
        "title": full or short,
        "updated": f"Updated {updated}" if updated else "Not committed yet",
        "state": state["state"],
        "standing": state["standing"],
        "standingSentence": state["standingSentence"],
        "sections": sections_of(raw),
        "raw": raw,
        "changes": changes_for(repo, path),
        "proposals": proposals_for(path, repo),
        "history": history_for(repo, path),
    }


def throughput(mc: ManagerConfig, merged: int, reopened: int) -> dict:
    """Work done, from the tracker when it is there, from the batch otherwise."""
    made = {"derived": 0, "resolved": 0, "verified": merged, "reopened": reopened, "spark": [], "available": False}
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
        if key == "TOTAL":
            made["derived"] = int(digits.group())
        elif key == "RESOLVED":
            made["resolved"] = int(digits.group())
    made["available"] = True
    return made


def operation_payload(mc: ManagerConfig) -> dict:
    lanes = manifest_lanes(mc)
    live = tmux_sessions(mc.tmux_socket)
    merge_log = git(mc.repo, "log", "--merges", "--format=%s", "-n", "400") if mc.repo else ""

    lane_items: list[dict] = []
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
        lane_items.append(
            {
                "id": one.name,
                "status": state,
                "statusLabel": STATE_WORD[state],
                "title": lane_title(mc, one),
                "worker": f"{one.name} · {one.branch}" if one.branch else one.name,
                "wave": wave_label(key),
                "age": age_words(age),
                "evidence": lane_evidence(mc, one),
                "tmux": {"socket": mc.tmux_socket, "session": one.tmux},
            }
        )

    order = list(by_wave)
    now_index = next((i for i, key in enumerate(order) if wave_live.get(key)), -1)
    waves: list[dict] = []
    board = _lane_board(highway_text(mc))
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
        titles = [board.get(name, "") for name, _flag in items if board.get(name)]
        title = "; ".join(titles[:3]) if titles else ", ".join(name for name, _flag in items[:3])
        waves.append(
            {
                "id": key,
                "label": wave_label(key),
                "title": title,
                "phase": phase,
                "cls": cls,
                "progress": progress,
                "items": [[name, flag] for name, flag in items],
            }
        )

    entries = _owner_log_entries(mc.repo)
    timeline = [[date, heading, first_sentence(body)] for date, heading, body in reversed(entries)]
    brief = sentences(entries[-1][2])[:6] if entries else []
    reopened = len(re.findall(r"\bREOPENED\b", highway_text(mc)))

    return {
        "waves": waves,
        "lanes": lane_items,
        "timeline": timeline,
        "returnBrief": brief,
        "throughput": throughput(mc, merged_count, reopened),
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
    "LaneRow",
    "age_words",
    "blocked_reason",
    "changes_for",
    "confidence",
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
    "proposals_for",
    "repo_docs",
    "repo_id",
    "repositories_payload",
    "run",
    "sections_of",
    "tmux_sessions",
    "_needs_items",
]
