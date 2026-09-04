"""The **repository half** of a target, for the two kits that need one.

`conformance/appsnapshot.py` models what the app *served*. `experience.v1` and
`experience-collaboration.v1` also make promises about the repository the app is
a body for — how the family is written, where a ratification lands, what the
write path actually runs — so those two kits read a second half, and they read
it the same way, from here.

The convention, and the one line in it that matters
---------------------------------------------------
The repository is **resolved, not passed**, so both kits keep the single command
line every experience kit shares (`conformance/kitreport.py`):

* target is a URL → the repository is the checkout the kit lives in;
* target is a captured snapshot carrying a ``repo/`` directory → that;
* target is a captured snapshot **without** one → :class:`Repo` is falsy, and
  every repository-reading rule must SKIP with :attr:`Repo.missing` as its
  reason.

That last case is why this file exists rather than a one-line fallback in each
kit. A kit that quietly judged whatever checkout it happened to sit in would
report *another* repository's contracts as this target's verdict, and nothing
would look wrong — the same shape of silent-wrong-answer that
`conformance/README.md` calls a fabricated finding.

`--capture` writes the app half only. Both halves of a fixture are written by
the `make_fixtures.py` beside each kit.
"""

from __future__ import annotations

import re
from pathlib import Path

__all__ = ["Repo", "core_clauses", "core_section", "reserved_section", "resolve_repo"]


class Repo:
    """A repository root to read — or an honest absence.

    Falsy when the target carried no repository half. Every rule that reads one
    asks ``if not repo: return KIT.skip(rule, repo.missing)`` first.
    """

    def __init__(self, root=None, kind="absent", missing=""):
        self.root = Path(root) if root else None
        self.kind = kind                     # "checkout" | "snapshot" | "absent"
        self.missing = missing

    def __bool__(self):
        return self.root is not None

    def text(self, rel: str) -> str:
        p = self.root / rel if self.root else None
        try:
            return p.read_text(encoding="utf-8") if p and p.is_file() else ""
        except OSError:
            return ""

    def exists(self, rel: str) -> bool:
        return bool(self.root) and (self.root / rel).exists()

    def glob(self, pattern: str):
        return sorted(self.root.glob(pattern)) if self.root else []

    def rel(self, path) -> str:
        try:
            return str(Path(path).relative_to(self.root))
        except (ValueError, TypeError):
            return str(path)

    def app_sources(self):
        """[(relative path, text), …] for the app's own Python."""
        return [(self.rel(p), p.read_text(encoding="utf-8", errors="replace"))
                for p in self.glob("app/*.py")]

    def contracts(self):
        """Every contract in the repository, by file name — proposals excluded."""
        return {p.name: p.read_text(encoding="utf-8", errors="replace")
                for p in self.glob("contracts/*.md")
                if not p.name.endswith("-candidate.md")
                and not p.name.startswith("CANDIDATE-")
                and p.name.upper() != "README.MD"}

    def family_contracts(self):
        """The section contracts that hang off the experience umbrella."""
        return {n: t for n, t in self.contracts().items() if n.startswith("experience-")}


def resolve_repo(snapshot, kit_file) -> Repo:
    """The repository half of `snapshot`, by convention rather than by flag."""
    if snapshot.kind == "live":
        return Repo(Path(kit_file).resolve().parents[2], "checkout")
    beside = Path(snapshot.base) / "repo"
    if beside.is_dir():
        return Repo(beside, "snapshot")
    return Repo(None, "absent",
                f"{snapshot.base} carries no `repo/` half, so the promises this contract "
                "makes about the repository — how the family is written, where an answer "
                "lands, what the write path runs — have nothing to read. Write one with "
                "the kit's make_fixtures.py, or point the kit at the running app.")


# --------------------------------------------------------------------------- #
# reading a contract's own shape                                               #
# --------------------------------------------------------------------------- #
def core_section(text: str) -> str:
    """A contract's Core clauses, and nothing else."""
    if "## Core" not in text:
        return ""
    return text.split("## Core", 1)[1].split("\n## ", 1)[0]


def reserved_section(text: str) -> str:
    """A contract's Reserved / open questions, and nothing else."""
    if "## Reserved" not in text:
        return ""
    return text.split("## Reserved", 1)[1].split("\n## ", 1)[0]


def core_clauses(text: str):
    """[(number, clause text), …] from a contract's Core section."""
    body = core_section(text)
    if not body:
        return []
    out, current, number = [], [], None
    for line in body.splitlines():
        start = re.match(r"^(\d+)\.\s+(.*)$", line)
        if start:
            if number is not None:
                out.append((number, "\n".join(current)))
            number, current = int(start.group(1)), [start.group(2)]
        elif number is not None:
            current.append(line)
    if number is not None:
        out.append((number, "\n".join(current)))
    return out
