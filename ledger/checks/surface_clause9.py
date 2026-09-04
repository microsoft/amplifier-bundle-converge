#!/usr/bin/env python3
"""Run the shipped surface kit's Core 9 rules against the app's own /operation page.

    uv run --extra web --with httpx python ledger/checks/surface_clause9.py

Prints one line, and exits 0 whatever it finds, so the row's
`expect.stdout_contains` is the assertion:

    SURFACE-CLAUSE-9-IN-VIEW=6-OF-8-GAUGE=SKIP

WHAT IT READS. The kit as shipped, imported from where it lives --
`conformance/_superseded/surface/run.py` -- and never reimplemented here. That
is the same subject and the same import path
`tests/test_plain_words_on_the_surface.py` uses for rule 8c, for the reason
CVG-066 records: the kit is the contract's own runnable definition, so its
verdict settles the question rather than this file's opinion of it.

`surface.v1` was superseded by the experience family and its kit was retired to
`_superseded/`, so this assertion lives outside the live suite. That is a fact
about where the check lives, not about the page -- the same fact CVG-066
carries.

THE COUNT IS PART OF THE PIN, DELIBERATELY. The verdict word alone cannot tell
2-of-8-missing from 6-of-8-missing, so a page that got better -- or worse --
would go on reporting the same word, and drift toward spec would be enjoyed
silently (LEDGER-FORMAT section 3). Pinning the count makes the row move when
the page moves, in either direction.

The gauge rule (9a) is reported beside it rather than folded in: it declines
when the project it is pointed at has no lanes to count, which is a fact about
the fixture and not about the page.
"""

from __future__ import annotations

import importlib.util
import os
import pathlib
import shutil
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
KIT = ROOT / "conformance" / "_superseded" / "surface" / "run.py"
FIXTURE = ROOT / "conformance" / "_superseded" / "surface" / "fixtures" / "app"


def load_kit():
    spec = importlib.util.spec_from_file_location("surface_kit", KIT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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
        project = tmp / "project"
        shutil.copytree(FIXTURE, project)

        sys.path.insert(0, str(ROOT / "src"))
        from fastapi.testclient import TestClient  # noqa: PLC0415

        from amplifier_converge.web.app import create_app  # noqa: PLC0415

        client = TestClient(create_app(project, "kettle", include_remote_proposals=False))
        page = tmp / "operation.html"
        page.write_text(client.get("/operation").text, encoding="utf-8")

        report = load_kit().run_conformance(page)
        rules = {r["rule"]: r for r in report["results"]}
        whole = rules.get("9b")
        gauge = rules.get("9a")
        if whole is None or gauge is None:
            print("SURFACE-CLAUSE-9-CHANGED-REREAD-THIS-ROW: "
                  f"the kit no longer publishes rules 9a and 9b (it has {sorted(rules)})")
            return 0

        parts = whole.get("in_view") or []
        if not parts:
            print("SURFACE-CLAUSE-9-CHANGED-REREAD-THIS-ROW: "
                  f"rule 9b reported no per-part detail -- {whole.get('detail')}")
            return 0
        in_view = sum(1 for p in parts if p["status"] == "PASS")
        print(f"SURFACE-CLAUSE-9-IN-VIEW={in_view}-OF-{len(parts)}-GAUGE={gauge['status']}")
        for p in parts:
            if p["status"] != "PASS":
                print(f"  not in view: {p['in view']} -- {p['detail']}", file=sys.stderr)
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
