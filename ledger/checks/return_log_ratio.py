#!/usr/bin/env python3
"""Count stamped returns against briefed returns in the owner return log.

    python3 ledger/checks/return_log_ratio.py
    python3 ledger/checks/return_log_ratio.py <some-other-log.md>   # a fixture

Prints one line, and exits 0 whatever it finds, so the row's
`expect.stdout_contains` is the assertion (the row's ref passes no argument;
the optional path is how the count itself is exercised against a fixture log
that has stamps and missing parts in it, which the real log does not yet):

    CLAUSE-10-STAMPED-RETURNS=0 BRIEFED-RETURNS=0 UNBRIEFED=0

WHY TWO NUMBERS. `contracts/operation.v1.md` Core 10 is "a brief on every
return". A count of briefs alone cannot say that -- nine briefs against an
unknown number of returns is a numerator with no denominator, and CVG-020 sat
red on exactly that reading for four reconciles. `modes/converge-manager.md`
clause 10 now makes the manager session stamp the return in the entry heading
the moment the steward's message arrives, and write the five parts under it at
the end of the turn. Written at two different moments, the two are countable
against each other: a return that never got briefed stands in the file as a
stamp with parts missing under it.

WHAT IT READS, AND WHY NOT A GREP. `parse_return_log` from
`evaluations/turnkey/run.py` -- the harness the operation contract names -- is
imported from where it lives and never reimplemented here. Its step (i) counts
these same two numbers, so a second definition of "a complete brief" written in
this file would be a second law for one clause, and the two would drift apart
silently. That is the reasoning `surface_clause9.py` already records for the
surface kit: the runnable definition settles the question rather than this
file's opinion of it.

THE MODE IS CHECKED FIRST, on purpose. Both numbers depend on the stamp being
written at all, so a mode that lost the instruction would report a truthful
`RETURNS=0` that means the opposite of what it looks like. If the mode no
longer encodes the clause and its stamp, this prints
`CLAUSE-10-STATE-CHANGED-REREAD-THIS-ROW` instead of a count.

WHAT IT CANNOT PROVE. A return the manager session never recorded at all leaves
no trace on either side of the ratio -- it is invisible to both counts, and
nothing else in this repository records that a return happened. That is the
honest limit of a record the returning session keeps itself. Closing it would
need a record of returns kept by something other than the session that returns.
"""

from __future__ import annotations

import importlib.util
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
HARNESS = ROOT / "evaluations" / "turnkey" / "run.py"
MODE = ROOT / "modes" / "converge-manager.md"
LOG = ROOT / "docs" / "workflow" / "OWNER-RETURN-LOG.md"

# The two sentences of the mode that make the count mean anything: the clause
# heading, and the instruction to stamp the return before answering it.
MODE_ENCODES = "## Clause 10 - "
MODE_STAMPS = "Stamp the return before you answer it"


def changed(why: str) -> int:
    print(f"CLAUSE-10-STATE-CHANGED-REREAD-THIS-ROW: {why}")
    return 0


def load_harness():
    spec = importlib.util.spec_from_file_location("turnkey_harness", HARNESS)
    module = importlib.util.module_from_spec(spec)
    # Registered before exec on purpose: the harness declares dataclasses, and
    # `@dataclass` resolves `cls.__module__` through `sys.modules`. Without this
    # line the import dies inside dataclasses.py with an AttributeError that
    # says nothing about the real cause (measured 2026-09-04, python 3.12.3).
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def main(argv: list[str]) -> int:
    log = pathlib.Path(argv[1]) if len(argv) > 1 else LOG
    if not MODE.is_file():
        return changed(f"no manager mode at {MODE.relative_to(ROOT)}")
    mode_text = MODE.read_text(encoding="utf-8")
    if MODE_ENCODES not in mode_text:
        return changed(f"the mode no longer carries a heading opening '{MODE_ENCODES}'")
    if MODE_STAMPS not in mode_text:
        return changed(f"the mode no longer says '{MODE_STAMPS}'")
    if not log.is_file():
        return changed(f"no return log at {log}")
    if not HARNESS.is_file():
        return changed(f"no turnkey harness at {HARNESS.relative_to(ROOT)}")

    parse = getattr(load_harness(), "parse_return_log", None)
    if parse is None:
        return changed(f"{HARNESS.relative_to(ROOT)} no longer publishes parse_return_log")

    entries = parse(log.read_text(encoding="utf-8"))
    returns = [e for e in entries if e["stamped"]]
    briefed = [e for e in returns if e["complete"]]
    unbriefed = [e for e in returns if not e["complete"]]
    print(f"CLAUSE-10-STAMPED-RETURNS={len(returns)} "
          f"BRIEFED-RETURNS={len(briefed)} UNBRIEFED={len(unbriefed)}")
    for e in unbriefed:
        print(f"  unbriefed return: {e['heading']} -- missing "
              f"{', '.join(e['parts_missing'])}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
