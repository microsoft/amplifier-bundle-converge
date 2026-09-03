#!/usr/bin/env python3
"""lumen.v1 conformance kit — the runnable definition of the contract's asserts.

Two rules, one per "Conformance kit asserts" bullet in
`contracts/lumen.v1.md`. Both can fail, and in this fixture's initial state
both DO fail — that is the planted gap the turnkey harness derives work from.

    python3 check.py [repo-root]

JSON report on stdout, human summary on stderr. Exit 0 when no rule FAILs,
1 when any does. Same three statuses as every other kit in this repository:
PASS, FAIL, SKIP — and a SKIP is never a soft pass.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from pathlib import Path

CONTRACT = "contracts/lumen.v1.md"


def _reading_calls(tree: ast.AST) -> list[ast.Call]:
    return [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "Reading"
    ]


def rule_units(root: Path) -> dict:
    """Core 1 — every reading names its unit."""
    source = root / "src" / "readings.py"
    if not source.is_file():
        return {
            "rule": "1",
            "id": "units",
            "status": "SKIP",
            "detail": f"{source} does not exist, so no reading could be read.",
            "reason": "source file absent",
        }
    tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
    offenders = []
    for call in _reading_calls(tree):
        unit = next((kw for kw in call.keywords if kw.arg == "unit"), None)
        named = (
            unit is not None
            and isinstance(unit.value, ast.Constant)
            and isinstance(unit.value.value, str)
            and unit.value.value.strip() != ""
        )
        if not named:
            label = next(
                (
                    kw.value.value
                    for kw in call.keywords
                    if kw.arg == "name" and isinstance(kw.value, ast.Constant)
                ),
                f"line {call.lineno}",
            )
            offenders.append({"reading": label, "line": call.lineno})
    if offenders:
        names = ", ".join(str(o["reading"]) for o in offenders)
        return {
            "rule": "1",
            "id": "units",
            "status": "FAIL",
            "detail": f"{len(offenders)} reading(s) name no unit in src/readings.py: {names}.",
            "evidence": {"offenders": offenders},
        }
    return {
        "rule": "1",
        "id": "units",
        "status": "PASS",
        "detail": "Every Reading(...) in src/readings.py names a non-empty unit.",
    }


def rule_index(root: Path) -> dict:
    """Core 2 — every public entry point is named in the index."""
    source = root / "src" / "report.py"
    index = root / "docs" / "INDEX.md"
    if not source.is_file():
        return {
            "rule": "2",
            "id": "index",
            "status": "SKIP",
            "detail": f"{source} does not exist, so no entry point could be read.",
            "reason": "source file absent",
        }
    if not index.is_file():
        return {
            "rule": "2",
            "id": "index",
            "status": "FAIL",
            "detail": f"{index} does not exist, so no entry point is named anywhere.",
        }
    tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
    public = [
        node.name
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and not node.name.startswith("_")
    ]
    text = index.read_text(encoding="utf-8")
    named = {name for name in public if re.search(rf"`{re.escape(name)}`", text)}
    missing = [name for name in public if name not in named]
    if missing:
        return {
            "rule": "2",
            "id": "index",
            "status": "FAIL",
            "detail": (
                f"{len(missing)} public entry point(s) in src/report.py are absent "
                f"from docs/INDEX.md: {', '.join(missing)}."
            ),
            "evidence": {"public": public, "named": sorted(named), "missing": missing},
        }
    return {
        "rule": "2",
        "id": "index",
        "status": "PASS",
        "detail": f"All {len(public)} public entry point(s) are named in docs/INDEX.md.",
    }


def run(root: Path) -> dict:
    results = [rule_units(root), rule_index(root)]
    summary = {
        "pass": sum(r["status"] == "PASS" for r in results),
        "fail": sum(r["status"] == "FAIL" for r in results),
        "skip": sum(r["status"] == "SKIP" for r in results),
    }
    return {
        "kit": "lumen.v1",
        "contract": CONTRACT,
        "target": str(root.resolve()),
        "results": results,
        "summary": summary,
        "verdict": "FAIL" if summary["fail"] else "PASS",
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        prog="lumen-check", description="Assert lumen.v1 conformance."
    )
    ap.add_argument("root", nargs="?", default=".", help="repository root")
    ap.add_argument("--json-only", action="store_true")
    args = ap.parse_args(argv)

    report = run(Path(args.root))
    sys.stdout.write(json.dumps(report, indent=2) + "\n")
    if not args.json_only:
        w = sys.stderr.write
        w(f"\nlumen.v1 conformance — {report['target']}\n")
        for r in report["results"]:
            w(f"  [{r['status']:4}] {r['rule']} {r['id']}: {r['detail']}\n")
        s = report["summary"]
        w(
            f"  VERDICT: {report['verdict']} "
            f"(pass={s['pass']} fail={s['fail']} skip={s['skip']})\n\n"
        )
    return 1 if report["verdict"] == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
