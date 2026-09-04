#!/usr/bin/env python3
"""Run the shipped surface kit's Core 9 rules against the app's own /operation page.

    uv run --extra web --with httpx python ledger/checks/surface_clause9.py

Prints one line, and exits 0 whatever it finds, so the row's
`expect.stdout_contains` is the assertion:

    SURFACE-CLAUSE-9 SHIPPED-FIXTURE=6-OF-8-GAUGE=SKIP READABLE-SUBJECT=8-OF-8-GAUGE=PASS

TWO SUBJECTS, AND BOTH READINGS ARE PINNED. Until 2026-09-04 this file rendered
the page from ONE subject -- the surface kit's shipped app fixture -- and
reported six of eight in view with the gauge declining. That reading was true
and was read as a fact about the PAGE. It was a fact about the SUBJECT: the
fixture has no lanes directory and no readable work queue, and `pages.py`
returns the queue card and the plan card empty exactly when the queue cannot be
read. So the same page, given a subject it can actually read, was already
showing all eight.

Both are therefore rendered and both are pinned:

`SHIPPED-FIXTURE`   the kit's own `fixtures/app`, untouched -- a project with no
                    lanes and no queue. Six of eight, gauge declines.
`READABLE-SUBJECT`  that same fixture placed inside a lanes directory (a
                    `manifest.tsv`, a `.width`, two lane worktrees) with the
                    work-tracker command answered by a stub on PATH. Nothing
                    about the app is stubbed -- only the two things outside it
                    that a real operation supplies.

Pinning both is what stops either mistake from recurring: a page that regresses
moves `READABLE-SUBJECT`, and a subject quietly swapped for a flattering one
moves `SHIPPED-FIXTURE`. The verdict word alone could tell neither
(LEDGER-FORMAT section 3).

WHAT IT READS. The kit as shipped, imported from where it lives --
`conformance/_superseded/surface/run.py` -- and never reimplemented here. That
is the same subject and the same import path
`tests/test_plain_words_on_the_surface.py` uses for rule 8c, for the reason
CVG-066 records: the kit is the contract's own runnable definition, so its
verdict settles the question rather than this file's opinion of it.

THE QUEUE STUB IS NAMED, NOT HIDDEN. `reading/queue.py` shells out to
`amplifier-work-tracker`; a stub on PATH answers `list`, `status` and
`instances` with four fixed items. What the readable-subject reading therefore
proves is that the PAGE puts all eight in view when the queue is readable --
never that this machine's queue reads. That distinction is the whole reason the
first reading is kept beside it.

`surface.v1` was superseded by the experience family and its kit was retired to
`_superseded/`, so this assertion lives outside the live suite. That is a fact
about where the check lives, not about the page -- the same fact CVG-066
carries.
"""

from __future__ import annotations

import importlib.util
import json
import os
import pathlib
import shutil
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
KIT = ROOT / "conformance" / "_superseded" / "surface" / "run.py"
FIXTURE = ROOT / "conformance" / "_superseded" / "surface" / "fixtures" / "app"

#: What the stubbed work queue answers with. Two items truly ready, one waiting
#: on the steward, one being worked -- enough for the queue card to state two
#: numbers and for the plan to have something to put in order.
ITEMS = {
    "items": [
        {"id": "kt-001", "title": "Wire the kettle", "status": "open", "holder": "", "resolution": ""},
        {"id": "kt-002", "title": "Boil test", "status": "open", "holder": "", "resolution": ""},
        {"id": "kt-003", "title": "Steward: pick a spout", "status": "blocked", "holder": "", "resolution": ""},
        {"id": "kt-004", "title": "Descaling", "status": "held", "holder": "agent-1", "resolution": ""},
    ]
}
SUMMARY = {
    "project": "kettle", "total": 4, "ready": 2, "held": 1,
    "blocked": 1, "deferred": 0, "resolved": 0, "resolved_24h": 0,
}


def load_kit():
    spec = importlib.util.spec_from_file_location("surface_kit", KIT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _render(project: pathlib.Path, into: pathlib.Path) -> pathlib.Path:
    """The app's own /operation page, served from `project`, written to disk."""
    sys.path.insert(0, str(ROOT / "src"))
    from fastapi.testclient import TestClient  # noqa: PLC0415

    from amplifier_converge.web.app import create_app  # noqa: PLC0415

    client = TestClient(create_app(project, "kettle", include_remote_proposals=False))
    into.write_text(client.get("/operation").text, encoding="utf-8")
    return into


def _lanes_around(project: pathlib.Path, board: pathlib.Path) -> None:
    """Give the project a lanes directory the board reader can actually read."""
    rows = ["lane\tbranch\tworktree\tlaunched_at"]
    for name in ("w1-alpha", "w1-beta"):
        lane = board / "lanes" / name
        lane.mkdir(parents=True, exist_ok=True)
        (lane / "lane.log").write_text("at work\n", encoding="utf-8")
        rows.append(f"{name}\tlane/{name}\t{lane}\t2026-09-04T09:00:00Z")
    (board / "manifest.tsv").write_text("\n".join(rows) + "\n", encoding="utf-8")
    (board / ".width").write_text("3\n", encoding="utf-8")


def _queue_stub(binaries: pathlib.Path) -> None:
    """A work-tracker command on PATH that answers, so the queue is readable."""
    binaries.mkdir(parents=True, exist_ok=True)
    shim = binaries / "amplifier-work-tracker"
    shim.write_text(
        "#!/usr/bin/env python3\n"
        "import json, sys\n"
        f"items = {json.dumps(ITEMS)}\n"
        f"summary = {json.dumps(SUMMARY)}\n"
        "verb = sys.argv[1] if len(sys.argv) > 1 else ''\n"
        "if verb == 'list': print(json.dumps(items))\n"
        "elif verb == 'status': print(json.dumps(summary))\n"
        "elif verb == 'instances': print(json.dumps([summary]))\n"
        "else: sys.exit(2)\n",
        encoding="utf-8",
    )
    shim.chmod(0o755)


def _clause9(kit, page: pathlib.Path) -> tuple[str, list[dict]] | None:
    rules = {r["rule"]: r for r in kit.run_conformance(page)["results"]}
    whole, gauge = rules.get("9b"), rules.get("9a")
    if whole is None or gauge is None:
        print("SURFACE-CLAUSE-9-CHANGED-REREAD-THIS-ROW: "
              f"the kit no longer publishes rules 9a and 9b (it has {sorted(rules)})")
        return None
    parts = whole.get("in_view") or []
    if not parts:
        print("SURFACE-CLAUSE-9-CHANGED-REREAD-THIS-ROW: "
              f"rule 9b reported no per-part detail -- {whole.get('detail')}")
        return None
    return gauge["status"], parts


def main() -> int:
    if not KIT.is_file():
        print(f"SURFACE-CLAUSE-9-CHANGED-REREAD-THIS-ROW: no kit at {KIT}")
        return 0
    if not FIXTURE.is_dir():
        print(f"SURFACE-CLAUSE-9-CHANGED-REREAD-THIS-ROW: no fixture project at {FIXTURE}")
        return 0

    tmp = pathlib.Path(tempfile.mkdtemp(prefix="surface-clause9-"))
    try:
        os.environ["AMPLIFIER_CONVERGE_HOME"] = str(tmp / "app-home")
        kit = load_kit()

        # 1. the shipped fixture, exactly as the kit ships it: no lanes, no queue
        bare = tmp / "bare"
        shutil.copytree(FIXTURE, bare)
        first = _clause9(kit, _render(bare, tmp / "bare.html"))
        if first is None:
            return 0

        # 2. the same project, given the two things a real operation supplies
        board = tmp / "board"
        board.mkdir()
        readable = board / "repo"
        shutil.copytree(FIXTURE, readable)
        _lanes_around(readable, board)
        _queue_stub(tmp / "bin")
        os.environ["PATH"] = f"{tmp / 'bin'}{os.pathsep}{os.environ['PATH']}"
        second = _clause9(kit, _render(readable, tmp / "readable.html"))
        if second is None:
            return 0

        def reading(found: tuple[str, list[dict]]) -> str:
            gauge, parts = found
            return f"{sum(1 for p in parts if p['status'] == 'PASS')}-OF-{len(parts)}-GAUGE={gauge}"

        print(f"SURFACE-CLAUSE-9 SHIPPED-FIXTURE={reading(first)} "
              f"READABLE-SUBJECT={reading(second)}")
        for label, found in (("shipped fixture", first), ("readable subject", second)):
            for part in found[1]:
                if part["status"] != "PASS":
                    print(f"  {label}: not in view: {part['in view']} -- {part['detail']}",
                          file=sys.stderr)
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
