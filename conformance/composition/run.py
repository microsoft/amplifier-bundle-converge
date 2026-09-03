# /// script
# requires-python = ">=3.9"
# dependencies = ["pyyaml"]
# ///
"""composition.v1 conformance kit — the runnable definition of "this repo composes leanly".

Point it at a repository ROOT. It mechanically asserts the conformance list of
``contracts/composition.v1.md`` — the four bullets under "Conformance kit
asserts" — over the files that repository actually loads.

Rule numbering follows the contract's bullet order. Where one bullet names
several independent promises, the kit emits one row per promise, lettered
inside the bullet (1a, 1b, ...), so a failure names the exact promise rather
than a whole paragraph. Bullets that need a LIVE Amplifier session to judge
are reported SKIP with the reason — never a fabricated PASS.

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


# --------------------------------------------------------------------------- #
# the rule table — numbered to contracts/composition.v1.md "Conformance kit    #
# asserts". `bullet` is the contract bullet; `id` is the row.                  #
# --------------------------------------------------------------------------- #
RULES = [
    ("1a", 1, "no_heavy_package_reference",
     "no reference to the heavy foundation package in anything loaded"),
    ("1b", 1, "no_heavy_helper_in_steps",
     "no automated step names a heavy-package helper"),
    ("1c", 1, "lean_base_named",
     "the lean base is named where Converge assembles"),
    ("1d", 1, "no_session_wide_tool_stripping",
     "no session-wide tool-stripping setting anywhere"),
    ("1e", 1, "steps_are_declared",
     "every automated step file is one the bundle declares"),
    ("2", 2, "session_reaches_helpers",
     "a Converge session reaches a lean-base helper and one of Converge's own"),
    ("3", 3, "unrelated_session_keeps_tools",
     "a helper in an unrelated session keeps its shell, delegation, and skills tools"),
    ("4a", 4, "guard_admits_both_proposal_names",
     "the guard admits a proposal beside a locked contract, under either name"),
    ("4b", 4, "guard_recognizes_locked_marker",
     "the guard's locked-marker test recognizes an H1-parenthetical status"),
]

# Rows that cannot be judged from files alone. Declared here so the self-test
# can assert the SKIP set is exactly this — a rule may not drift into SKIP.
UNFIXTURABLE = {
    "2": "needs a live Amplifier session; this kit reads files only",
    "3": "needs two live Amplifier sessions (Converge plus unrelated work) side by side",
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

LOADED_DIRS = ["behaviors", "context"]
LOADED_FILES = ["bundle.md"]


def _result(rid, status, detail, **extra):
    bullet = next(r[1] for r in RULES if r[0] == rid)
    name = next(r[2] for r in RULES if r[0] == rid)
    desc = next(r[3] for r in RULES if r[0] == rid)
    out = {
        "rule": rid,
        "bullet": bullet,
        "id": name,
        "name": desc,
        "status": status,
        "detail": detail,
    }
    out.update(extra)
    return out


def _skip(rid):
    return _result(rid, "SKIP", UNFIXTURABLE[rid], reason=UNFIXTURABLE[rid])


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
# bullet 1 — a lean base, and no side effects                                  #
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
        return _result("1b", "PASS", "no automated steps present to check")
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
            "1b", "FAIL",
            f"{len(hits)} automated step(s) name a heavy-package helper: {where}",
            hits=hits,
        )
    return _result(
        "1b", "PASS",
        f"no 'foundation:' helper named across {len(recipes)} automated step file(s)",
    )


def check_lean_base_named(root: Path):
    meta, err = load_bundle_frontmatter(root)
    if err:
        return _result("1c", "FAIL", err)
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
            "1c", "FAIL",
            f"bundle.md includes no lean-base (anchors) URI; saw {len(uris)} include(s): {uris}",
            includes=uris,
        )
    return _result("1c", "PASS", f"lean base named in bundle.md includes: {matched[0]}")


def check_no_tool_stripping(root: Path):
    """A top-level `spawn:` key applies to EVERY spawned helper in EVERY session
    that composes this bundle — the session-wide tool-stripping setting the
    contract forbids. Judged on bundle.md's frontmatter and every behavior."""
    offenders = []
    meta, err = load_bundle_frontmatter(root)
    if err:
        return _result("1d", "FAIL", err)
    if "spawn" in meta:
        offenders.append({"file": "bundle.md", "key": "spawn"})
    for p in behavior_files(root):
        try:
            doc = yaml.safe_load(p.read_text(encoding="utf-8", errors="replace"))
        except yaml.YAMLError as e:
            return _result("1d", "FAIL", f"{_rel(root, p)} is not valid YAML: {e}")
        if isinstance(doc, dict) and "spawn" in doc:
            offenders.append({"file": _rel(root, p), "key": "spawn"})
    if offenders:
        where = ", ".join(o["file"] for o in offenders)
        return _result(
            "1d", "FAIL",
            f"session-wide spawn policy present in: {where}",
            offenders=offenders,
        )
    n = 1 + len(behavior_files(root))
    return _result("1d", "PASS", f"no top-level 'spawn:' key in {n} composed file(s)")


def check_steps_are_declared(root: Path):
    """Every automated step file must be one the bundle names. An undeclared
    recipe is a step nobody reviewed — and one rule 1b's scan only covers by
    accident. Keeps the step surface exactly what the bundle says it is."""
    recipes = recipe_files(root)
    if not recipes:
        return _result("1e", "PASS", "no automated steps present to declare")
    f = root / "bundle.md"
    if not f.is_file():
        return _result("1e", "FAIL", "no bundle.md at the repository root")
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
            "1e", "FAIL",
            f"{len(missing)} of {len(steps)} automated step(s) undeclared: "
            + ", ".join(s["step"] for s in missing[:5]),
            steps=steps,
        )
    return _result(
        "1e", "PASS",
        f"all {len(steps)} automated step file(s) are declared in bundle.md",
        steps=steps,
    )


# --------------------------------------------------------------------------- #
# bullet 4 — the guard                                                         #
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
            "4a", "FAIL",
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
            "4a", "FAIL",
            f"{len(failed)} of {len(rows)} proposal-name check(s) rejected: {names}",
            checks=rows,
        )
    return _result(
        "4a", "PASS",
        f"both proposal names admitted by every guard glob list ({len(rows)} checks)",
        checks=rows,
    )


def check_guard_recognizes_locked_marker(root: Path):
    guards = guard_configs(root)
    if not guards:
        return _result(
            "4b", "FAIL",
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
            "4b", "FAIL",
            "; ".join(f"{r['where']}: {r['detail']}" for r in failed[:3]),
            checks=rows,
        )
    return _result(
        "4b", "PASS",
        f"locked-marker test recognizes the H1-parenthetical form ({len(rows)} guard config(s))",
        checks=rows,
    )


# --------------------------------------------------------------------------- #
# driver                                                                       #
# --------------------------------------------------------------------------- #
def run_conformance(root: Path) -> dict:
    results = [
        check_no_heavy_reference(root),
        check_no_heavy_helper_in_steps(root),
        check_lean_base_named(root),
        check_no_tool_stripping(root),
        check_steps_are_declared(root),
        _skip("2"),
        _skip("3"),
        check_guard_admits_both(root),
        check_guard_recognizes_locked_marker(root),
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
    w(f"asserts: {report['contract']} (\"Conformance kit asserts\")\n")
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
