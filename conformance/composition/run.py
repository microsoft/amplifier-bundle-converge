# /// script
# requires-python = ">=3.9"
# dependencies = ["pyyaml"]
# ///
"""composition.v1 conformance kit — the runnable definition of "this repo composes leanly".

Point it at a repository ROOT. It mechanically asserts the promises of
``contracts/composition.v1.md`` — the seven **Core** clauses — over the files
that repository actually loads.

Rule numbering follows the contract's **Core clause** numbers, as documents.v1
clause 5 asks: rule 6a judges Core 6, so a failing rule names the clause it
breaks. Where one clause carries several independent promises, the kit emits
one row per promise, lettered inside the clause (1a, 1b, ...), so a failure
names the exact promise rather than a whole paragraph. Every Core clause has a
row, and the self-test fails if one does not — a clause added later cannot go
unchecked.

Three promises (rules 3b, 6b and 6c) are about a RUNNING session rather than
files. They are judged by ``live.py``, which stands real sessions up through the
installed Amplifier — this file imports nothing from it. Where a live verdict is
genuinely out of reach (no ``amplifier`` on PATH, an interpreter that cannot
import the app, a probe that timed out, or the probe switched off), those rows
report SKIP naming the exact missing capability — never a fabricated PASS.
They are the only rows allowed to decline at all.

6c asks a different question from the other two: not "what does this working
tree do to a neighbour" but "what is the release of this repository ALREADY
INSTALLED on this host doing to one". The two answers disagreed on 2026-09-04 —
this tree was clean, 6a and 6b both PASSed, and a published sibling release
app-installed on the same machine was stripping shell, delegation and skills
from every spawned helper in every session on it (converge-w3v).

The kit was numbered to the contract's *Conformance kit asserts* bullets until
2026-09-03. The steward ratified the Core-clause anchor that day (see
``docs/workflow/owner-ratifications-2026-09-03.md``, call 2), because the bullet
anchor could not show a clause going unchecked: four bullets covered seven
clauses, and Core 3, 4 and 5 had no row at all.

Usage
-----
    uv run conformance/composition/run.py <repo-root>

Output
------
A JSON report on stdout (machine-readable) and a human summary on stderr.
Exit code is 0 when no rule FAILs, 1 when any rule FAILs.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover - surfaced loudly, never silently faked
    sys.stderr.write(
        "error: PyYAML is required to parse bundle/behavior YAML. "
        "Run this kit with `uv run` (it declares pyyaml), or `pip install pyyaml`.\n"
    )
    raise SystemExit(3)

# The live half (rules 3b and 6b). It imports nothing from Amplifier itself —
# it shells out to the installed CLI's own interpreter — so this stays a script
# with one declared dependency. Imported by path so `uv run <this file>` and
# `import run` from the self-test both resolve it.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import live  # noqa: E402


# --------------------------------------------------------------------------- #
# the rule table — numbered to contracts/composition.v1.md's **Core** clauses.  #
# `clause` is the Core clause the row judges; `id` is the row's short name.     #
# --------------------------------------------------------------------------- #
RULES = [
    ("1a", 1, "no_heavy_package_reference",
     "no reference to the heavy foundation package in anything loaded"),
    ("1b", 1, "lean_base_named",
     "the lean base is named where Converge assembles"),
    ("2a", 2, "no_heavy_helper_in_steps",
     "no automated step names a heavy-package helper"),
    ("2b", 2, "steps_are_declared",
     "every automated step file is one the bundle declares"),
    ("3a", 3, "helpers_carry_the_local_rulebook",
     "every one of Converge's own helpers carries the small local rulebook, and borrows nothing else"),
    ("3b", 3, "session_reaches_helpers",
     "a Converge session reaches a lean-base helper and one of Converge's own"),
    ("4", 4, "host_requirement_in_readme",
     "the host requirement is one sentence in the README"),
    ("5", 5, "work_queue_on_both_install_paths",
     "the shared work queue rides on both install paths"),
    ("6a", 6, "no_session_wide_tool_stripping",
     "no session-wide tool-stripping setting anywhere"),
    ("6b", 6, "unrelated_session_keeps_tools",
     "a helper in an unrelated session keeps its shell, delegation, and skills tools"),
    ("6c", 6, "installed_release_keeps_neighbour_tools",
     "on a host where this repository is installed, an unrelated session's helper keeps them too"),
    ("7a", 7, "guard_admits_both_proposal_names",
     "the guard admits a proposal beside a locked contract, under either name"),
    ("7b", 7, "guard_recognizes_locked_marker",
     "the guard's locked-marker test recognizes an H1-parenthetical status"),
]

# Rows that cannot be judged from files at all: they are about a RUNNING
# session. They are not "unfixturable" any more — `live.py` stands the sessions
# up and they return PASS/FAIL like every other row. They remain the ONLY two
# rows allowed to SKIP, and only with a reason naming the exact missing
# capability (`live.MISSING`, or one of the two measurement-baseline reasons).
# The self-test pins that: no other rule may drift into SKIP, and a SKIP here
# must carry a reason from the declared vocabulary.
LIVE_RULES = {
    "3b": "a real session on this repository, and what it composes",
    "6b": "a real unrelated session, with and without this repository installed beside it",
    "6c": "a real unrelated session as THIS host composes it, with the app bundles "
          "actually installed on it",
}

# The heavy package this contract forbids, and the lean base it requires.
HEAVY_NAMESPACE_RE = re.compile(r"@foundation:")
HEAVY_AGENT_RE = re.compile(r"\bfoundation:[A-Za-z0-9_-]+")
LEAN_BASE_RE = re.compile(r"amplifier-foundation.*bundles/anchors/bundle\.md")

# Canonical paths a guard must admit beside a locked contract (both names).
PROPOSAL_PATHS = [
    "contracts/CANDIDATE-retry-clause.md",
    "contracts/composition.v1-candidate.md",
]
# The status form documents.v1 Core 6 fixes: status lives in the H1 parenthetical.
LOCKED_H1 = "# Composition Contract — v1 (FROZEN 2026-09-02)"

# Core 3: "Its own helpers carry a small local rulebook — stop honestly when a
# thing cannot be proven; sign commits; cite locations — and borrow nothing
# else." The rulebook is a file the helpers name; the three rules are its
# sections. A helper that names no rulebook behaves differently on every host,
# which is the drift this catches.
RULEBOOK_RULES = [
    ("stop honestly when a thing cannot be proven", re.compile(r"stop honestly", re.I)),
    ("cite locations", re.compile(r"cite locations?", re.I)),
    ("sign commits", re.compile(r"sign commits?", re.I)),
]
#: An `@namespace:path` mention inside one of Converge's own helper files.
MENTION_RE = re.compile(r"@([A-Za-z0-9_-]+):([\w./-]+)")

# Core 4 (amended 2026-09-04, steward word "ratified"): "The host requirement
# is one sentence in the README. A step that declares no helpers of its own can
# use only those present in the session it runs in ...; a step that declares its
# helpers resolves them from that closure instead, and asks nothing of its host."
# One sentence must carry all three halves -- the host, HOW a step's helpers
# resolve (only the session's, or only the closure it declares), and the lean
# base -- so a reader knows whether their own session can run the steps.
HOST_SENTENCE_TESTS = [
    ("names the host", re.compile(r"\bhost\b", re.I)),
    ("says how a step's helpers resolve: only the session's, or only the closure it declares",
     re.compile(r"only\s+(?:from|in|helpers?\s+present\s+in)\s+the\s+session"
                r"|helpers?\s+only\s+from\s+the\s+session"
                r"|only\s+helpers?\s+present\s+in\s+the\s+session"
                r"|only\s+from\s+(?:that|the|its)\s+(?:declared\s+)?closure"
                r"|declares\s+its\s+own\s+helpers", re.I)),
    ("names the lean base", re.compile(r"anchors|lean\s+base", re.I)),
]

# Core 5: "The shared work queue rides on both install paths." The two paths are
# the root bundle (`bundle.md`) and the standalone behavior that `--app`
# installs, so the queue must be named in BOTH — a queue on one path only means
# the contract checker can file work on one install and not the other.
WORK_QUEUE_RE = re.compile(r"work-tracker")

LOADED_DIRS = ["behaviors", "context"]
LOADED_FILES = ["bundle.md"]


def _result(rid, status, detail, **extra):
    clause = next(r[1] for r in RULES if r[0] == rid)
    name = next(r[2] for r in RULES if r[0] == rid)
    desc = next(r[3] for r in RULES if r[0] == rid)
    out = {
        "rule": rid,
        "clause": clause,
        "id": name,
        "name": desc,
        "status": status,
        "detail": detail,
    }
    out.update(extra)
    return out


def _from_live(rid, row):
    """Wrap a (status, detail, extra) triple from `live.py` as a rule row."""
    status, detail, extra = row
    return _result(rid, status, detail, **(extra or {}))


# --------------------------------------------------------------------------- #
# helpers                                                                      #
# --------------------------------------------------------------------------- #
def glob_to_regex(pattern: str) -> re.Pattern:
    """Translate a path glob to a regex.

    `**/` spans zero or more directories, `**` spans anything, `*` stays inside
    one segment, `?` is one non-separator character, and `[...]` is a character
    class (so `*.v[0-9]*-candidate.md` means what it looks like). Written out
    rather than handed to fnmatch, whose `*` crosses `/` and would silently
    over-match.
    """
    out, i, n = [], 0, len(pattern)
    while i < n:
        c = pattern[i]
        if pattern.startswith("**/", i):
            out.append(r"(?:[^/]+/)*")
            i += 3
        elif pattern.startswith("**", i):
            out.append(r".*")
            i += 2
        elif c == "*":
            out.append(r"[^/]*")
            i += 1
        elif c == "?":
            out.append(r"[^/]")
            i += 1
        elif c == "[":
            j = i + 1
            if j < n and pattern[j] in "!^":
                j += 1
            if j < n and pattern[j] == "]":
                j += 1
            while j < n and pattern[j] != "]":
                j += 1
            if j >= n:  # unterminated class — treat the bracket literally
                out.append(re.escape(c))
                i += 1
                continue
            body = pattern[i + 1 : j]
            if body.startswith(("!", "^")):
                body = "^" + body[1:]
            out.append("[" + body.replace("\\", "\\\\") + "]")
            i = j + 1
        else:
            out.append(re.escape(c))
            i += 1
    return re.compile("^" + "".join(out) + "$")


def glob_match(pattern: str, path: str) -> bool:
    return bool(glob_to_regex(pattern).match(path))


def split_frontmatter(text: str):
    """Return the YAML frontmatter block of a markdown file, or None."""
    lines = text.splitlines()
    if lines and lines[0].startswith("\ufeff"):
        lines[0] = lines[0].lstrip("\ufeff")
    start = 0
    while start < len(lines) and lines[start].strip() == "":
        start += 1
    if start >= len(lines) or lines[start].strip() != "---":
        return None
    for j in range(start + 1, len(lines)):
        if lines[j].strip() == "---":
            return "\n".join(lines[start + 1 : j])
    return None


def load_bundle_frontmatter(root: Path):
    """(mapping, error) for bundle.md's frontmatter."""
    f = root / "bundle.md"
    if not f.exists():
        return None, "no bundle.md at the repository root"
    fm = split_frontmatter(f.read_text(encoding="utf-8", errors="replace"))
    if fm is None:
        return None, "bundle.md has no YAML frontmatter delimited by '---'"
    try:
        meta = yaml.safe_load(fm)
    except yaml.YAMLError as e:
        return None, f"bundle.md frontmatter is not valid YAML: {e}"
    if not isinstance(meta, dict):
        return None, "bundle.md frontmatter did not parse to a mapping"
    return meta, None


def behavior_files(root: Path):
    d = root / "behaviors"
    if not d.is_dir():
        return []
    return sorted(p for p in d.rglob("*") if p.suffix in (".yaml", ".yml") and p.is_file())


def loaded_text_files(root: Path):
    """Every file the bundle loads into a session: bundle.md, behaviors, context."""
    out = []
    for rel in LOADED_FILES:
        p = root / rel
        if p.is_file():
            out.append(p)
    for d in LOADED_DIRS:
        base = root / d
        if base.is_dir():
            out.extend(sorted(p for p in base.rglob("*") if p.is_file()))
    return out


def recipe_files(root: Path):
    d = root / "recipes"
    if not d.is_dir():
        return []
    return sorted(p for p in d.rglob("*") if p.suffix in (".yaml", ".yml") and p.is_file())


def _rel(root: Path, p: Path) -> str:
    try:
        return str(p.relative_to(root))
    except ValueError:
        return str(p)


# --------------------------------------------------------------------------- #
# clauses 1 and 2 — a lean base, and steps that reach only its helpers        #
# --------------------------------------------------------------------------- #
def check_no_heavy_reference(root: Path):
    hits = []
    for p in loaded_text_files(root):
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for i, line in enumerate(text.splitlines(), 1):
            if HEAVY_NAMESPACE_RE.search(line):
                hits.append({"file": _rel(root, p), "line": i, "text": line.strip()[:120]})
    if hits:
        where = ", ".join(f"{h['file']}:{h['line']}" for h in hits[:5])
        return _result(
            "1a", "FAIL",
            f"{len(hits)} heavy-package reference(s) in loaded files: {where}",
            hits=hits,
        )
    return _result(
        "1a", "PASS",
        f"no '@foundation:' reference across {len(loaded_text_files(root))} loaded file(s)",
    )


def check_no_heavy_helper_in_steps(root: Path):
    recipes = recipe_files(root)
    if not recipes:
        return _result("2a", "PASS", "no automated steps present to check")
    hits = []
    for p in recipes:
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for i, line in enumerate(text.splitlines(), 1):
            m = HEAVY_AGENT_RE.search(line)
            if m and "amplifier-foundation" not in line:
                hits.append(
                    {"file": _rel(root, p), "line": i, "ref": m.group(0)}
                )
    if hits:
        where = ", ".join(f"{h['file']}:{h['line']} ({h['ref']})" for h in hits[:5])
        return _result(
            "2a", "FAIL",
            f"{len(hits)} automated step(s) name a heavy-package helper: {where}",
            hits=hits,
        )
    return _result(
        "2a", "PASS",
        f"no 'foundation:' helper named across {len(recipes)} automated step file(s)",
    )


def check_lean_base_named(root: Path):
    meta, err = load_bundle_frontmatter(root)
    if err:
        return _result("1b", "FAIL", err)
    includes = meta.get("includes") or []
    uris = []
    if isinstance(includes, list):
        for inc in includes:
            if isinstance(inc, dict) and isinstance(inc.get("bundle"), str):
                uris.append(inc["bundle"])
            elif isinstance(inc, str):
                uris.append(inc)
    matched = [u for u in uris if LEAN_BASE_RE.search(u)]
    if not matched:
        return _result(
            "1b", "FAIL",
            f"bundle.md includes no lean-base (anchors) URI; saw {len(uris)} include(s): {uris}",
            includes=uris,
        )
    return _result("1b", "PASS", f"lean base named in bundle.md includes: {matched[0]}")


def check_no_tool_stripping(root: Path):
    """A top-level `spawn:` key applies to EVERY spawned helper in EVERY session
    that composes this bundle — the session-wide tool-stripping setting the
    contract forbids. Judged on bundle.md's frontmatter and every behavior."""
    offenders = []
    meta, err = load_bundle_frontmatter(root)
    if err:
        return _result("6a", "FAIL", err)
    if "spawn" in meta:
        offenders.append({"file": "bundle.md", "key": "spawn"})
    for p in behavior_files(root):
        try:
            doc = yaml.safe_load(p.read_text(encoding="utf-8", errors="replace"))
        except yaml.YAMLError as e:
            return _result("6a", "FAIL", f"{_rel(root, p)} is not valid YAML: {e}")
        if isinstance(doc, dict) and "spawn" in doc:
            offenders.append({"file": _rel(root, p), "key": "spawn"})
    if offenders:
        where = ", ".join(o["file"] for o in offenders)
        return _result(
            "6a", "FAIL",
            f"session-wide spawn policy present in: {where}",
            offenders=offenders,
        )
    n = 1 + len(behavior_files(root))
    return _result("6a", "PASS", f"no top-level 'spawn:' key in {n} composed file(s)")


def check_steps_are_declared(root: Path):
    """Every automated step file must be one the bundle names. An undeclared
    recipe is a step nobody reviewed — and one rule 1b's scan only covers by
    accident. Keeps the step surface exactly what the bundle says it is."""
    recipes = recipe_files(root)
    if not recipes:
        return _result("2b", "PASS", "no automated steps present to declare")
    f = root / "bundle.md"
    if not f.is_file():
        return _result("2b", "FAIL", "no bundle.md at the repository root")
    declared_text = f.read_text(encoding="utf-8", errors="replace")
    steps = []
    for p in recipes:
        rel = _rel(root, p)
        named = p.name in declared_text or rel in declared_text
        steps.append({"step": rel, "status": "PASS" if named else "FAIL",
                      "detail": "named in bundle.md" if named else "not named in bundle.md"})
    missing = [s for s in steps if s["status"] == "FAIL"]
    if missing:
        return _result(
            "2b", "FAIL",
            f"{len(missing)} of {len(steps)} automated step(s) undeclared: "
            + ", ".join(s["step"] for s in missing[:5]),
            steps=steps,
        )
    return _result(
        "2b", "PASS",
        f"all {len(steps)} automated step file(s) are declared in bundle.md",
        steps=steps,
    )


# --------------------------------------------------------------------------- #
# clause 3 — its own helpers, and their local rulebook                         #
# --------------------------------------------------------------------------- #
def helper_files(root: Path):
    """The repository's own helper definitions."""
    d = root / "agents"
    if not d.is_dir():
        return []
    return sorted(p for p in d.rglob("*.md") if p.is_file())


def own_bundle_names(root: Path):
    """Every name this repository's product answers to, for rule 6c.

    The root bundle's name and each behavior's. An app-bundle URI on the host
    that names one of them is a release of THIS repository; one that names none
    is a neighbour's, and 6c may not blame a neighbour's setting on this
    repository (the same discipline rule 6b's control enforces).
    """
    names = []
    meta, err = load_bundle_frontmatter(root)
    if not err and isinstance(meta, dict):
        n = ((meta.get("bundle") or {}).get("name") or "").strip()
        if n:
            names.append(n)
    for p in behavior_files(root):
        try:
            doc = yaml.safe_load(p.read_text(encoding="utf-8", errors="replace"))
        except yaml.YAMLError:
            continue
        if isinstance(doc, dict):
            n = ((doc.get("bundle") or {}).get("name") or "").strip()
            if n:
                names.append(n)
    return sorted(set(names))


def own_agent_names(root: Path):
    """The namespaced names of this repository's own helpers.

    ``agents/reconciler.md`` in a bundle named ``converge`` is reachable from a
    session as ``converge:reconciler``. Rule 3b needs the names, not the files:
    what it asks is whether a live session composed one of them, and the
    session's roster speaks in names.
    """
    meta, err = load_bundle_frontmatter(root)
    if err:
        return []
    ns = ((meta.get("bundle") or {}).get("name") or "").strip()
    if not ns:
        return []
    names = []
    for p in helper_files(root):
        text = p.read_text(encoding="utf-8", errors="replace")
        fm = split_frontmatter(text)
        name = p.stem
        if fm:
            try:
                doc = yaml.safe_load(fm)
            except yaml.YAMLError:
                doc = None
            if isinstance(doc, dict):
                candidate = ((doc.get("meta") or {}).get("name")
                             if isinstance(doc.get("meta"), dict) else None)
                if isinstance(candidate, str) and candidate.strip():
                    name = candidate.strip()
        names.append(f"{ns}:{name}")
    return sorted(set(names))


def check_helpers_carry_the_rulebook(root: Path):
    """Core 3: "Its own helpers carry a small local rulebook … and borrow
    nothing else."

    Three things are readable from the tree: every helper NAMES a rulebook, the
    rulebook it names EXISTS, and that rulebook states the three rules the
    clause enumerates. "Borrows nothing else" is read as: a helper mentions no
    other bundle's context — a preamble borrowed from elsewhere is one that can
    change under the helper's feet, so the helper stops behaving the same on
    every host.
    """
    helpers = helper_files(root)
    if not helpers:
        return _result("3a", "FAIL",
                       "no helper of its own under agents/ — nothing carries a local rulebook")
    meta, _ = load_bundle_frontmatter(root)
    own = ((meta or {}).get("bundle") or {}).get("name") if isinstance(meta, dict) else None
    rows, rulebooks, borrowed = [], set(), []
    for p in helpers:
        text = p.read_text(encoding="utf-8", errors="replace")
        carried, near_misses = [], []
        for ns, path in MENTION_RE.findall(text):
            if own and ns != own:
                borrowed.append({"file": _rel(root, p), "mention": f"@{ns}:{path}"})
                continue
            f = root / path
            if not f.is_file():
                continue
            body = f.read_text(encoding="utf-8", errors="replace")
            absent = [label for label, rx in RULEBOOK_RULES if not rx.search(body)]
            # A helper names several documents; the RULEBOOK is the one stating
            # the rules clause 3 enumerates. The others are domain reading and
            # are not judged here — reporting them would be a fabricated finding.
            if absent:
                near_misses.append({"file": path, "absent": absent})
            else:
                carried.append(path)
        rows.append({"helper": _rel(root, p),
                     "status": "PASS" if carried else "FAIL",
                     "detail": (f"carries {carried[0]}" if carried
                                else "names no local file stating the three rules clause 3 lists"),
                     "closest": near_misses[:3]})
        rulebooks.update(carried)
    problems = [r for r in rows if r["status"] == "FAIL"]
    if problems:
        where = "; ".join(
            f"{r['helper']} ({'closest: ' + r['closest'][0]['file'] + ' lacks '
                              + str(r['closest'][0]['absent']) if r['closest'] else 'names no local document'})"
            for r in problems[:3])
        return _result("3a", "FAIL",
                       f"{len(problems)} of {len(helpers)} helper(s) carry no local rulebook: {where}",
                       helpers=rows)
    if borrowed:
        where = ", ".join(f"{b['file']} → {b['mention']}" for b in borrowed[:4])
        return _result("3a", "FAIL",
                       f"{len(borrowed)} helper mention(s) borrow another bundle's context: {where}",
                       helpers=rows, borrowed=borrowed)
    return _result("3a", "PASS",
                   f"all {len(helpers)} helper(s) carry a local rulebook "
                   f"({', '.join(sorted(rulebooks))}) stating all "
                   f"{len(RULEBOOK_RULES)} rules clause 3 names, and borrow nothing else",
                   helpers=rows, rulebooks=sorted(rulebooks))


# --------------------------------------------------------------------------- #
# clause 4 — the host requirement                                              #
# --------------------------------------------------------------------------- #
def readme_sentences(root: Path):
    """(sentences, error) for the repository README, one string per sentence.

    Block-quote markers and line wrapping are removed first: the clause asks
    for one sentence, and a sentence that happens to be wrapped over three
    lines, or set as a blockquote, is still one sentence.
    """
    f = root / "README.md"
    if not f.is_file():
        return None, "no README.md at the repository root — the host requirement is stated nowhere"
    text = f.read_text(encoding="utf-8", errors="replace")
    lines = [re.sub(r"^\s*>\s?", "", ln) for ln in text.splitlines()]
    flat = re.sub(r"\s+", " ", " ".join(lines))
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", flat) if s.strip()], None


def check_host_requirement(root: Path):
    """Core 4: "The host requirement is one sentence in the README."

    Judged as the clause states it: ONE sentence must carry all three halves —
    the host, the fact that a step resolves helpers only from the session it
    runs in, and the lean base. Spread across three paragraphs the requirement
    is technically present and practically unreadable, which is the failure
    this catches.
    """
    sentences, err = readme_sentences(root)
    if err:
        return _result("4", "FAIL", err)
    best, best_hits = None, []
    for s in sentences:
        hits = [label for label, rx in HOST_SENTENCE_TESTS if rx.search(s)]
        if len(hits) > len(best_hits):
            best, best_hits = s, hits
        if len(hits) == len(HOST_SENTENCE_TESTS):
            return _result(
                "4", "PASS",
                f"README.md states the host requirement in one sentence: {s[:150]!r}",
                sentence=s,
            )
    absent = [label for label, _ in HOST_SENTENCE_TESTS if label not in best_hits]
    if best is None:
        return _result(
            "4", "FAIL",
            f"no sentence in README.md ({len(sentences)} read) carries any half of the "
            f"host requirement; all three are missing: {absent}",
            closest=None, absent=absent,
        )
    return _result(
        "4", "FAIL",
        f"no single sentence in README.md states the host requirement — the closest "
        f"({best[:90]!r}) says nothing about: {absent}",
        closest=best, absent=absent,
    )


# --------------------------------------------------------------------------- #
# clause 5 — the shared work queue, on both install paths                       #
# --------------------------------------------------------------------------- #
def _include_uris(doc) -> list:
    out = []
    includes = (doc or {}).get("includes") or []
    if isinstance(includes, list):
        for inc in includes:
            if isinstance(inc, dict) and isinstance(inc.get("bundle"), str):
                out.append(inc["bundle"])
            elif isinstance(inc, str):
                out.append(inc)
    return out


def check_work_queue_on_both_paths(root: Path):
    """Core 5: "The shared work queue rides on both install paths."

    Path one is the root bundle (`bundle.md`); path two is the standalone
    behavior a host session installs on its own. The queue must be named on
    BOTH — named on one only, the contract checker can file work after one
    install and silently cannot after the other.
    """
    paths = []
    meta, err = load_bundle_frontmatter(root)
    if err:
        return _result("5", "FAIL", err)
    root_uris = [u for u in _include_uris(meta) if WORK_QUEUE_RE.search(u)]
    paths.append({"path": "bundle.md (the root install)", "status": "PASS" if root_uris else "FAIL",
                  "detail": (f"names the work queue: {root_uris[0]}" if root_uris
                             else "no include names the shared work queue")})
    behavior_hits = []
    for p in behavior_files(root):
        try:
            doc = yaml.safe_load(p.read_text(encoding="utf-8", errors="replace"))
        except yaml.YAMLError as e:
            return _result("5", "FAIL", f"{_rel(root, p)} is not valid YAML: {e}")
        if not isinstance(doc, dict):
            continue
        for u in _include_uris(doc):
            if WORK_QUEUE_RE.search(u):
                behavior_hits.append({"file": _rel(root, p), "uri": u})
    paths.append({"path": "the standalone behavior (the --app install)",
                  "status": "PASS" if behavior_hits else "FAIL",
                  "detail": (f"{behavior_hits[0]['file']} names the work queue: "
                             f"{behavior_hits[0]['uri']}" if behavior_hits
                             else "no behavior includes the shared work queue")})
    missing = [p for p in paths if p["status"] == "FAIL"]
    if missing:
        return _result(
            "5", "FAIL",
            "the shared work queue does not ride on "
            + "; ".join(f"{m['path']} — {m['detail']}" for m in missing),
            paths=paths,
        )
    return _result(
        "5", "PASS",
        "the shared work queue rides on both install paths "
        f"(bundle.md and {behavior_hits[0]['file']})",
        paths=paths,
    )


# --------------------------------------------------------------------------- #
# clause 7 — the guard                                                         #
# --------------------------------------------------------------------------- #
def guard_configs(root: Path):
    """Every hooks-candidate-guard config block found across the behaviors."""
    found = []
    for p in behavior_files(root):
        try:
            doc = yaml.safe_load(p.read_text(encoding="utf-8", errors="replace"))
        except yaml.YAMLError:
            continue
        if not isinstance(doc, dict):
            continue
        for hook in doc.get("hooks") or []:
            if isinstance(hook, dict) and hook.get("module") == "hooks-candidate-guard":
                found.append((_rel(root, p), hook.get("config") or {}))
    return found


def check_guard_admits_both(root: Path):
    guards = guard_configs(root)
    if not guards:
        return _result(
            "7a", "FAIL",
            "no hooks-candidate-guard config found in behaviors/ — nothing guards a locked contract",
        )
    rows = []
    for where, cfg in guards:
        for key in ("always_allow_globs", "candidate_glob"):
            globs = cfg.get(key) or []
            if isinstance(globs, str):
                globs = [globs]
            for path in PROPOSAL_PATHS:
                ok = any(glob_match(g, path) for g in globs)
                rows.append({
                    "where": where, "key": key, "proposal": path,
                    "status": "PASS" if ok else "FAIL",
                    "detail": (f"admitted by {globs}" if ok
                               else f"not admitted by any of {globs}"),
                })
    failed = [r for r in rows if r["status"] == "FAIL"]
    if failed:
        names = ", ".join(f"{r['key']} rejects {r['proposal']}" for r in failed[:4])
        return _result(
            "7a", "FAIL",
            f"{len(failed)} of {len(rows)} proposal-name check(s) rejected: {names}",
            checks=rows,
        )
    return _result(
        "7a", "PASS",
        f"both proposal names admitted by every guard glob list ({len(rows)} checks)",
        checks=rows,
    )


def check_guard_recognizes_locked_marker(root: Path):
    guards = guard_configs(root)
    if not guards:
        return _result(
            "7b", "FAIL",
            "no hooks-candidate-guard config found in behaviors/ — nothing guards a locked contract",
        )
    rows = []
    for where, cfg in guards:
        if not cfg.get("require_frozen_marker", False):
            rows.append({
                "where": where, "status": "PASS",
                "detail": "require_frozen_marker is off; every guarded file is treated as locked",
            })
            continue
        pattern = cfg.get("frozen_marker_regex")
        if not isinstance(pattern, str) or not pattern:
            rows.append({
                "where": where, "status": "FAIL",
                "detail": "require_frozen_marker is on but frozen_marker_regex is missing or empty",
            })
            continue
        try:
            rx = re.compile(pattern)
        except re.error as e:
            rows.append({"where": where, "status": "FAIL",
                         "detail": f"frozen_marker_regex does not compile: {e}"})
            continue
        ok = bool(rx.search(LOCKED_H1))
        rows.append({
            "where": where, "regex": pattern,
            "status": "PASS" if ok else "FAIL",
            "detail": (f"matches {LOCKED_H1!r}" if ok
                       else f"does NOT match {LOCKED_H1!r} — a locked contract in the "
                            "H1-parenthetical form documents.v1 fixes would be left unguarded"),
        })
    failed = [r for r in rows if r["status"] == "FAIL"]
    if failed:
        return _result(
            "7b", "FAIL",
            "; ".join(f"{r['where']}: {r['detail']}" for r in failed[:3]),
            checks=rows,
        )
    return _result(
        "7b", "PASS",
        f"locked-marker test recognizes the H1-parenthetical form ({len(rows)} guard config(s))",
        checks=rows,
    )


# --------------------------------------------------------------------------- #
# driver                                                                       #
# --------------------------------------------------------------------------- #
def run_conformance(root: Path) -> dict:
    # One live probe serves every live row: standing sessions up is the
    # expensive part, and 3b, 6b and 6c read the same captured run.
    probe = live.probe(
        root, own_agent_names(root), behavior_files(root), own_bundle_names(root)
    )
    results = [
        check_no_heavy_reference(root),        # 1a
        check_lean_base_named(root),           # 1b
        check_no_heavy_helper_in_steps(root),  # 2a
        check_steps_are_declared(root),        # 2b
        check_helpers_carry_the_rulebook(root),  # 3a
        _from_live("3b", probe.session_row()),
        check_host_requirement(root),          # 4
        check_work_queue_on_both_paths(root),  # 5
        check_no_tool_stripping(root),         # 6a
        _from_live("6b", probe.neighbour_row()),
        _from_live("6c", probe.host_row()),
        check_guard_admits_both(root),         # 7a
        check_guard_recognizes_locked_marker(root),  # 7b
    ]
    summary = {
        "pass": sum(r["status"] == "PASS" for r in results),
        "fail": sum(r["status"] == "FAIL" for r in results),
        "skip": sum(r["status"] == "SKIP" for r in results),
    }
    return {
        "kit": "composition.v1",
        "contract": "contracts/composition.v1.md",
        "target": str(root.resolve()),
        "results": results,
        "summary": summary,
        "verdict": "FAIL" if summary["fail"] else "PASS",
    }


def print_human_summary(report: dict) -> None:
    w = sys.stderr.write
    w(f"\ncomposition.v1 conformance — {report['target']}\n")
    w(f"asserts: {report['contract']} (\"Core (the teeth)\", clause by clause)\n")
    w("-" * 74 + "\n")
    for r in report["results"]:
        w(f"  [{r['status']:4}] {r['rule']:3} {r['id']}: {r['detail']}\n")
    w("-" * 74 + "\n")
    s = report["summary"]
    w(f"  VERDICT: {report['verdict']}  (pass={s['pass']} fail={s['fail']} skip={s['skip']})\n\n")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        prog="composition-conformance",
        description="Assert composition.v1 conformance against a repository root.",
    )
    ap.add_argument("repo_root", help="path to the repository root (holds bundle.md)")
    ap.add_argument("--json-only", action="store_true",
                    help="suppress the human summary on stderr")
    args = ap.parse_args(argv)

    root = Path(args.repo_root)
    if not root.exists():
        sys.stderr.write(f"error: path not found: {args.repo_root}\n")
        return 3
    if not root.is_dir():
        sys.stderr.write(f"error: not a directory (a target is a repo root): {args.repo_root}\n")
        return 3

    report = run_conformance(root)
    sys.stdout.write(json.dumps(report, indent=2) + "\n")
    if not args.json_only:
        print_human_summary(report)
    return 1 if report["verdict"] == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
