#!/usr/bin/env python3
"""Export the work queue to the shape `documents.v1` rule 9a reads.

A work item is not a file in this tree -- it lives in the work queue -- so the
documents conformance kit reads an **export** of that queue instead of growing
a dependency on a running tracker. This script produces that export from the
live queue, so the committed file is derived, never hand-written.

    uv run scripts/export-work-items.py --project converge --out docs/work-items.json
    uv run conformance/documents/run.py . --work-items docs/work-items.json

Stdlib only, plus the `amplifier-work-tracker` binary on PATH. Every read goes
through that CLI; this script never speaks to the tracker's storage directly.

**The export is a snapshot, and a stale one would let rule 9a pass on a queue
that has since changed.** Refresh it in the same pass as any change to the
queue, and read the run in the same breath as the file.

Shape: a JSON array of objects, one per item, sorted by id so the committed
file's diff is meaningful. Per item:

    id           the tracker's own id
    title        the item's one-line title
    status       the tracker's status, verbatim -- reported, never judged
    description  the item's own words about what it serves
    acceptance   the item's definition of done
    design       design notes, or null

    contract_named_on_line_one
                 true when line one of the description (or, for an item with
                 no description, the title) names a contract that EXISTS in
                 the target's contracts/, by stem and version. This is an
                 OBSERVATION recorded beside the item, not an assertion: rule
                 9a makes its own judgment, over the whole item, using its own
                 regex. Recorded because clause 9 says "in one line" and the
                 rule cannot see where a name sat.

`status` is deliberately outside the field set rule 9a scans for prose, so a
machine status word ("resolved") can never be mistaken for the item's own
definition of done.

**`resolution` is deliberately not exported.** The tracker keeps one, and one
item in this queue (converge-2st) names its contract there and nowhere else --
so exporting it as `notes` would turn a real rule 9a failure green. Clause 9
asks that a *work item* name its contract; a resolution is what was written
when the work closed, not the item asking for it. Rule 9a does not read
`resolution` either, so this changes no verdict -- it is recorded here because
the temptation to reshape an item until the check passes is the thing to
refuse.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

TRACKER = "amplifier-work-tracker"
CLI_LIMIT_MAX = 500

# The same two shapes the kit uses, so an observation recorded here and a
# verdict reached there are talking about the same thing.
# conformance/documents/run.py: CONTRACT_REF_RE, CONTRACT_STEM_RE.
CONTRACT_REF_RE = re.compile(r"\b([A-Za-z0-9][A-Za-z0-9._-]*)\.v(\d+)\b")
CONTRACT_STEM_RE = re.compile(r"^(?P<stem>[A-Za-z0-9][A-Za-z0-9._-]*)\.v\d+\.md$")

EXPORT_FIELDS = ("id", "title", "status", "description", "acceptance", "design")


class ExportError(RuntimeError):
    """Something the export cannot honestly work around."""


def tracker_json(args: list[str]) -> dict:
    """Run the tracker CLI and parse its JSON. Loud on any failure."""
    if shutil.which(TRACKER) is None:
        raise ExportError(
            f"{TRACKER} is not on PATH -- the export is derived from the live "
            "queue, and there is no honest substitute for reading it"
        )
    cmd = [TRACKER, *args, "--json"]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise ExportError(
            f"`{' '.join(cmd)}` exited {proc.returncode}: "
            f"{(proc.stderr or proc.stdout).strip()}"
        )
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as e:
        raise ExportError(f"`{' '.join(cmd)}` did not print JSON: {e}") from e


def queue_ids(project: str, limit: int, status: str | None) -> list[str]:
    """Every item id in the project, in the tracker's own order."""
    args = ["list", "--project", project, "--limit", str(limit)]
    if status:
        args += ["--status", status]
    payload = tracker_json(args)
    items = payload.get("items") or []
    if payload.get("truncated"):
        raise ExportError(
            f"the queue has {payload.get('total_count')} items and only "
            f"{payload.get('returned_count')} were returned -- raise --limit "
            "rather than export a partial queue"
        )
    return [str(i["id"]) for i in items]


def full_record(project: str, item_id: str) -> dict:
    """One item's full record -- the list form carries no description."""
    payload = tracker_json(["list", "--project", project, "--id", item_id])
    items = payload.get("items") or []
    if not items:
        raise ExportError(f"{item_id} disappeared from the queue mid-export")
    return items[0]


def known_contract_stems(repo_root: Path) -> set[str]:
    """Contract stems that EXIST in the target, e.g. {'documents', 'surface'}."""
    d = repo_root / "contracts"
    if not d.is_dir():
        return set()
    out = set()
    for p in sorted(d.glob("*.md")):
        m = CONTRACT_STEM_RE.match(p.name)
        if m:
            out.add(m.group("stem"))
    return out


def names_contract_on_line_one(record: dict, known: set[str]) -> bool:
    """Does line one name a contract that exists here?"""
    description = str(record.get("description") or "")
    line = next((ln for ln in description.splitlines() if ln.strip()), "")
    if not line:
        line = str(record.get("title") or "")
    return any(
        not known or m.group(1) in known for m in CONTRACT_REF_RE.finditer(line)
    )


def export(project: str, repo_root: Path, limit: int, status: str | None) -> list[dict]:
    known = known_contract_stems(repo_root)
    items = []
    for item_id in queue_ids(project, limit, status):
        record = full_record(project, item_id)
        row = {f: record.get(f) for f in EXPORT_FIELDS}
        row["contract_named_on_line_one"] = names_contract_on_line_one(record, known)
        items.append(row)
    items.sort(key=lambda r: str(r["id"]))
    return items


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Export a work-tracker queue to the shape documents.v1 "
        "rule 9a reads."
    )
    ap.add_argument("--project", default="converge", help="tracker project name")
    ap.add_argument("--out", default="docs/work-items.json", type=Path,
                    help="where to write the export (default: docs/work-items.json)")
    ap.add_argument("--repo-root", default=Path("."), type=Path,
                    help="repository whose contracts/ names the known contracts")
    ap.add_argument("--limit", default=CLI_LIMIT_MAX, type=int,
                    help=f"max items to read (CLI maximum {CLI_LIMIT_MAX})")
    ap.add_argument("--status", default=None,
                    choices=["open", "held", "blocked", "deferred", "resolved"],
                    help="export only items with this status "
                         "(default: the whole queue, every status)")
    args = ap.parse_args(argv)

    try:
        items = export(args.project, args.repo_root, args.limit, args.status)
    except ExportError as e:
        print(f"export failed: {e}", file=sys.stderr)
        return 2

    if not items:
        print(
            f"export failed: project {args.project!r} returned no work items -- "
            "an empty export is not something rule 9a can judge",
            file=sys.stderr,
        )
        return 1

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(items, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    named = sum(1 for i in items if i["contract_named_on_line_one"])
    by_status: dict[str, int] = {}
    for i in items:
        by_status[str(i["status"])] = by_status.get(str(i["status"]), 0) + 1
    breakdown = ", ".join(f"{k} {v}" for k, v in sorted(by_status.items()))
    print(f"exported {len(items)} work items from project {args.project!r} "
          f"to {args.out}")
    print(f"  by status: {breakdown}")
    print(f"  naming a contract on line one: {named} of {len(items)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
