#!/usr/bin/env python3
"""Read one turnkey step's recorded verdict, and what that step actually said.

    python3 ledger/checks/turnkey_step.py e "name one of this repository's"

Prints one of:

    TURNKEY-STEP-E-PASS-ASSERTS-THIS
    TURNKEY-STEP-E-CHANGED-REREAD-THIS-ROW: <what was found instead>

and exits 0 either way, so the row's `expect.stdout_contains` is the assertion
and a changed harness result cannot pass as an unchanged one.

WHY A FILE AND NOT A RE-RUN. The harness itself needs a container, a Gitea
mirror and about six minutes; run in observed mode against this host it needs a
wave to be running at that moment, so a row keyed on it would go red whenever
the workspace happened to be idle -- a false alarm, not drift. What it reads
instead is `evaluations/turnkey/RESULT.md`, which `contracts/operation.v1.md`
itself names, in a sentence the steward ratified on 2026-09-04:

    **First green 2026-09-04 -- nine of nine steps, twice, in fresh containers,
    with a manager session that was not the integrator
    (`evaluations/turnkey/RESULT.md`); it re-runs on every merge.

So this reads the contract's own named evidence. CVG-010 already rests on the
same file, by the same reasoning.

WHAT IT DOES NOT PROVE. That the run happened today, or that it would still be
green. It proves what the recorded run reported, step by step -- and it flips
the moment that record changes, which is the whole point of pinning a sentence
rather than a verdict word.
"""

from __future__ import annotations

import pathlib
import re
import sys

RESULT = pathlib.Path("evaluations/turnkey/RESULT.md")
# `[PASS] (f) lanes: <detail>` -- detail runs to the next step line or the
# VERDICT line, wrapped across however many lines the file happens to use.
#
# THE LETTER CLASS IS `[a-z]`, AND IT USED TO BE `[a-i]`. That ceiling was
# written when the harness had exactly nine steps, and it silently became a bug
# the day it grew two more: asked for step (j) this file answered "no step (j)
# is recorded in evaluations/turnkey/RESULT.md" while (j) sat in that file,
# recorded, four lines from (i) -- a false "the record changed" that reads
# exactly like drift and is not. A step letter the harness writes down must be
# readable here; a letter it never wrote still answers "no step (x) is
# recorded", which is the honest sentence for that case and the only one this
# ceiling was ever needed for. converge-saz carries the measurement.
STEP = re.compile(
    r"\[(PASS|FAIL|SKIP)\] \((?P<letter>[a-z])\) (?P<name>\w+): "
    r"(?P<detail>.*?)(?= \[(?:PASS|FAIL|SKIP)\] \(| VERDICT:)"
)


def collapse(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print("usage: turnkey_step.py <step-letter> <fragment the step must say>")
        return 2
    letter, fragment = argv[1].lower(), collapse(argv[2])
    tag = f"TURNKEY-STEP-{letter.upper()}"

    if not RESULT.is_file():
        print(f"{tag}-CHANGED-REREAD-THIS-ROW: {RESULT} does not exist")
        return 0

    steps = {m.group("letter"): m for m in STEP.finditer(collapse(RESULT.read_text()))}
    found = steps.get(letter)
    if found is None:
        print(f"{tag}-CHANGED-REREAD-THIS-ROW: no step ({letter}) is recorded in {RESULT}")
        return 0

    status, detail = found.group(1), collapse(found.group("detail"))
    if status != "PASS":
        print(f"{tag}-CHANGED-REREAD-THIS-ROW: the recorded verdict is {status}, not PASS")
        return 0
    if fragment not in detail:
        print(f"{tag}-CHANGED-REREAD-THIS-ROW: it no longer says {fragment!r}; it says {detail!r}")
        return 0

    print(f"{tag}-PASS-ASSERTS-THIS")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
