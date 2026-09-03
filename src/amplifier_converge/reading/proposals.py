"""Proposals — a manager session's draft and a teammate's pull request, alike.

Surface.v1 clause 5: whoever proposed it, the reader sees the same three
things in the same order — what changes, the evidence, what does *not* change.
Where it came from is a line of provenance, not a different experience.
"""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from . import Reading

#: The three parts documents.v1 clause 8 requires of every proposal.
PART_HEADINGS = (
    ("change", ("the exact change", "exact change", "what changes", "the change")),
    ("evidence", ("evidence",)),
    ("not_change", ("what does not change", "what does NOT change", "not change")),
)

CANDIDATE_RE = re.compile(r"^(?P<target>.+)\.v(?P<version>\d+)-candidate\.md$")
LEGACY_RE = re.compile(r"^CANDIDATE-(?P<topic>.+)\.md$")


@dataclass(frozen=True)
class Proposal:
    key: str
    title: str
    origin: str  # "this project" | "a teammate"
    origin_detail: str
    target: str
    change: str
    evidence: str
    not_change: str
    url: str = ""
    #: Exactly where it is kept — a path, or a pull request number. A path is
    #: technical detail, so it is shown behind a Details fold and never in the
    #: sentence a steward decides on (documents.v1 clause 11).
    where: str = ""
    complete: bool = True
    missing: tuple[str, ...] = ()


def _section(text: str, names: tuple[str, ...]) -> str:
    lines = text.splitlines()
    wanted = tuple(n.lower() for n in names)
    start = None
    level = 0
    for i, line in enumerate(lines):
        m = re.match(r"^(#{1,6})\s+(.*)$", line)
        if not m:
            continue
        heading = m.group(2).strip().lower().strip("*_`:")
        heading = re.sub(r"^\d+[.)]\s*", "", heading)
        if start is None and any(w in heading for w in wanted):
            start = i + 1
            level = len(m.group(1))
        elif start is not None and len(m.group(1)) <= level:
            return "\n".join(lines[start:i]).strip()
    if start is not None:
        return "\n".join(lines[start:]).strip()
    return ""


def parse_proposal(
    text: str,
    key: str,
    title: str,
    origin: str,
    origin_detail: str,
    target: str,
    url: str = "",
    where: str = "",
) -> Proposal:
    found: dict[str, str] = {}
    missing: list[str] = []
    for field, names in PART_HEADINGS:
        body = _section(text, names)
        if body:
            found[field] = body
        else:
            missing.append(field)
            found[field] = ""
    return Proposal(
        key=key,
        title=title,
        origin=origin,
        origin_detail=origin_detail,
        target=target,
        change=found["change"],
        evidence=found["evidence"],
        not_change=found["not_change"],
        url=url,
        where=where,
        complete=not missing,
        missing=tuple(missing),
    )


def _local_proposals(repo: Path) -> list[Proposal]:
    out: list[Proposal] = []
    for directory in (repo / "contracts", repo / "docs"):
        if not directory.is_dir():
            continue
        for path in sorted(directory.glob("*.md")):
            candidate = CANDIDATE_RE.match(path.name)
            legacy = LEGACY_RE.match(path.name)
            if not candidate and not legacy:
                continue
            text = path.read_text(encoding="utf-8")
            first_line = next(
                (ln[2:].strip() for ln in text.splitlines() if ln.startswith("# ")),
                path.stem,
            )
            if candidate:
                target = f"{candidate.group('target')}.v{candidate.group('version')}.md"
            else:
                target = _declared_target(text) or "a locked document"
            out.append(
                parse_proposal(
                    text=text,
                    key=f"file:{path.relative_to(repo)}",
                    title=first_line,
                    origin="this project",
                    origin_detail="proposed here, in this project",
                    target=target,
                    where=f"It is kept at {path.relative_to(repo)}.",
                )
            )
    return out


def _declared_target(text: str) -> str:
    m = re.search(r"^target:\s*(?P<t>.+)$", text, re.MULTILINE | re.IGNORECASE)
    return m.group("t").strip() if m else ""


def _github_proposals(repo: Path) -> tuple[list[Proposal], str]:
    """Open pull requests touching the contracts or the vision.

    Needs the `gh` command and a GitHub remote. When either is absent the page
    says so rather than implying there are none.
    """
    try:
        remote = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=repo,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return [], "This project has no git remote, so there are no teammates' proposals to fetch."
    if remote.returncode != 0 or "github" not in remote.stdout.lower():
        return [], "No GitHub remote is configured, so teammates' pull requests are not shown here."

    try:
        result = subprocess.run(
            [
                "gh",
                "pr",
                "list",
                "--state",
                "open",
                "--limit",
                "20",
                "--json",
                "number,title,body,author,url,files",
            ],
            cwd=repo,
            capture_output=True,
            text=True,
            timeout=20,
        )
    except FileNotFoundError:
        return [], "The GitHub command line tool is not installed here, so teammates' pull requests are not shown."
    except (OSError, subprocess.SubprocessError):
        return [], "GitHub could not be reached just now, so teammates' pull requests are not shown."
    if result.returncode != 0:
        return [], "GitHub declined the request for open pull requests, so teammates' proposals are not shown."

    try:
        rows = json.loads(result.stdout or "[]")
    except json.JSONDecodeError:
        return [], "GitHub's answer could not be read, so teammates' proposals are not shown."

    out: list[Proposal] = []
    for row in rows:
        files = [f.get("path", "") for f in row.get("files", [])]
        touching = [f for f in files if f.startswith("contracts/") or f == "docs/VISION.md"]
        if not touching:
            continue
        author = (row.get("author") or {}).get("login", "a teammate")
        out.append(
            parse_proposal(
                text=row.get("body") or "",
                key=f"pr:{row.get('number')}",
                title=row.get("title", f"Pull request #{row.get('number')}"),
                origin="a teammate",
                origin_detail=f"{author} opened pull request #{row.get('number')}",
                target=", ".join(touching),
                where=f"It changes {', '.join(touching)}.",
                url=row.get("url", ""),
            )
        )
    return out, ""


def read_proposals(repo: Path, include_remote: bool = True) -> Reading[list[Proposal]]:
    repo = Path(repo)
    local = _local_proposals(repo)
    remote: list[Proposal] = []
    note = ""
    if include_remote:
        remote, note = _github_proposals(repo)
    proposals = local + remote
    if note:
        return Reading(proposals, available=True, note=note)
    return Reading(proposals)


def find_proposal(repo: Path, key: str, include_remote: bool = True) -> Proposal | None:
    for proposal in read_proposals(repo, include_remote=include_remote).value:
        if proposal.key == key:
            return proposal
    return None
