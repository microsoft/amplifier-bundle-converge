#!/usr/bin/env python3
"""Take one turnkey clause reading LIVE, and hold it to what a row claims.

    python3 ledger/checks/turnkey_clause.py CVG-013 PASS "name what kept moving"
    python3 ledger/checks/turnkey_clause.py --attribution CVG-017 PASS "any lane merge"

Prints exactly one of:

    TURNKEY-CLAUSE-CVG-013-ASSERTS-THIS
    TURNKEY-CLAUSE-CVG-013-CHANGED-REREAD-THIS-ROW: <what it says now>
    TURNKEY-CLAUSE-CVG-013-CANNOT-READ-HERE: <why no reading could be taken>

and exits 0 in every case, so the row's `expect.stdout_contains` is the
assertion and a changed reading cannot pass as an unchanged one.

WHY THIS EXISTS BESIDE turnkey_step.py, WHICH READS A FILE. Its sibling reads
the verdict `evaluations/turnkey/RESULT.md` recorded, and that is the right
route for a row whose reading was taken in a DRIVEN container run nobody can
reproduce on demand. It is the wrong route for the four clause readings that
moved on 2026-09-04 (Core 3, 7, 8, 11): the block in that file is written by
whichever lane owns `evaluations/`, so a ledger row keyed on it asserts the last
paste rather than the current reading, and stays confidently green while the
harness says something else. That is exactly what happened -- CVG-013 pinned
`Core 3 (CVG-013) SKIP` for a day after the harness had started answering PASS.

THE OBJECTION THIS FILE HAS TO ANSWER, because the ledger recorded it twice:
"a probe keyed on an OBSERVED run needs a wave to be running at that moment, so
it would go red whenever this workspace happened to be idle -- a false alarm,
not drift" (CVG-017 notes, 2026-09-04). It is answered differently for the two
kinds of reading, and neither answer is "ignore it":

  * (k) ATTRIBUTION -- who wrote the newest `docs/workflow/CHECK-RECORD.md`
    entry -- reads this repository's own git history and nothing else. No wave,
    no workspace, no queue, no network: a clone with full history answers it
    identically on the quietest afternoon of the year. Measured: the same
    verdict with `--workspace` pointed at the manager workspace and with it
    pointed at a directory that has never held a wave.

  * (j) CLAUSE readings -- Core 3 and Core 11 -- genuinely read the manager
    workspace's plan record. When one cannot be found this prints
    CANNOT-READ-HERE and NAMES what it looked for. The row then goes red, which
    is the honest outcome: on a machine with no wave the reading is unavailable,
    and an unavailable reading must not be reported as a kept promise. What it
    must never do is go quietly green, and it cannot.

WHAT IT DOES NOT PROVE. That the reading is right -- only what the harness's own
reader says right now, on this checkout, in its own words. The row's `proves`
carries the limits of the reading itself.
"""

from __future__ import annotations

import json
import os
import pathlib
import re
import subprocess
import sys

HARNESS = pathlib.Path("evaluations/turnkey/run.py")

# Which step letter carries each row's reading. Step (j) reads what a manager
# session left behind in the workspace; step (k) reads who produced an artifact
# in this repository.
STEP_OF = {
    "CVG-012": "j", "CVG-013": "j", "CVG-014": "j", "CVG-016": "j",
    "CVG-019": "j", "CVG-021": "j", "CVG-023": "j",
    "CVG-017": "k", "CVG-018": "k", "CVG-022": "k",
}

# A manager workspace is the directory the plan record and the lane manifest
# live in. Both are required: `HIGHWAY.md` alone matches a documentation
# directory that happens to use the name.
MARKERS = ("HIGHWAY.md", "manifest.tsv")

TIMEOUT_S = 150.0


def collapse(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def safe(text: str, limit: int = 420) -> str:
    """Never let the harness's own words carry this file's success token."""
    return collapse(text)[:limit].replace("ASSERTS-THIS", "<token>")


def is_workspace(path: pathlib.Path) -> bool:
    return all((path / marker).is_file() for marker in MARKERS)


def registered_worktrees() -> list[pathlib.Path]:
    """Every worktree git knows about -- the lanes of a live wave among them.

    A lane worktree sits at <workspace>/lanes/<lane>/<repo>, so the workspace is
    reachable from any checkout of this repository, including an integration
    checkout that lives somewhere else entirely (measured: main is checked out
    under ~/dev/vision-focused-team-ci while the wave runs in ~/dev/hw-converge).
    """
    try:
        out = subprocess.run(["git", "worktree", "list", "--porcelain"],
                             capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return []
    return [pathlib.Path(line[len("worktree "):].strip())
            for line in out.stdout.splitlines() if line.startswith("worktree ")]


def find_workspace() -> tuple[pathlib.Path | None, str]:
    named = os.environ.get("CONVERGE_MANAGER_WORKSPACE")
    if named:
        path = pathlib.Path(named).expanduser()
        if is_workspace(path):
            return path, "named by CONVERGE_MANAGER_WORKSPACE"
        return None, (f"CONVERGE_MANAGER_WORKSPACE={named} holds no "
                      f"{' + '.join(MARKERS)}")

    here = pathlib.Path.cwd().resolve()
    for start in [here, *registered_worktrees()]:
        for candidate in [start, *start.parents]:
            if is_workspace(candidate):
                return candidate, f"found above {start}"
    return None, (f"no ancestor of {here} or of any registered worktree holds "
                  f"both {' and '.join(MARKERS)}")


def read(letter: str) -> tuple[dict | None, str]:
    """Run the harness for one step and hand back its clause readings."""
    if not HARNESS.is_file():
        return None, f"{HARNESS} does not exist (run from the repository root)"

    cmd = ["uv", "run", str(HARNESS), "--env", "local", "--json-only",
           "--steps", letter]
    workspace, how = find_workspace()
    if workspace is not None:
        cmd += ["--workspace", str(workspace)]
    elif letter == "j":
        # (j) reads the plan record; without one there is nothing to read.
        return None, f"no manager workspace to read a plan record from -- {how}"

    try:
        run = subprocess.run(cmd, capture_output=True, text=True, timeout=TIMEOUT_S)
    except FileNotFoundError:
        return None, "uv is not on PATH, so the harness could not be run"
    except subprocess.TimeoutExpired:
        return None, f"the harness did not finish within {TIMEOUT_S:.0f}s"

    try:
        return json.loads(run.stdout), how
    except json.JSONDecodeError:
        return None, (f"the harness printed no JSON (exit {run.returncode}): "
                      f"{safe(run.stderr or run.stdout, 200)}")


def main(argv: list[str]) -> int:
    args = [a for a in argv[1:] if a != "--attribution"]
    attribution = "--attribution" in argv[1:]
    if len(args) != 3:
        print("usage: turnkey_clause.py [--attribution] <ROW-ID> <VERDICT> "
              "<fragment the reading must say>")
        return 2
    row, want_verdict, fragment = args[0].upper(), args[1].upper(), collapse(args[2])
    tag = f"TURNKEY-CLAUSE-{row}"

    letter = STEP_OF.get(row)
    if letter is None:
        print(f"{tag}-CANNOT-READ-HERE: no turnkey step is known to read {row}")
        return 0

    report, how = read(letter)
    if report is None:
        print(f"{tag}-CANNOT-READ-HERE: {how}")
        return 0

    readings = report.get("clauses", {}).get("readings", [])
    found = next((r for r in readings if r.get("row") == row), None)
    if found is None:
        print(f"{tag}-CHANGED-REREAD-THIS-ROW: step ({letter}) no longer reads "
              f"{row}; it read {[r.get('row') for r in readings]}")
        return 0

    part = found
    if attribution:
        part = found.get("attribution")
        if not part:
            print(f"{tag}-CHANGED-REREAD-THIS-ROW: the reading carries no "
                  f"attribution half any more; it says {safe(found.get('why', ''))}")
            return 0

    verdict, why = part.get("verdict", ""), collapse(part.get("why", ""))
    if verdict != want_verdict:
        print(f"{tag}-CHANGED-REREAD-THIS-ROW: the live verdict is {verdict}, "
              f"not {want_verdict}; it says {safe(why)}")
        return 0
    if fragment not in why:
        print(f"{tag}-CHANGED-REREAD-THIS-ROW: it no longer says "
              f"{safe(fragment, 120)!r}; it says {safe(why)}")
        return 0

    print(f"{tag}-ASSERTS-THIS")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
