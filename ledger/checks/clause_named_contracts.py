#!/usr/bin/env python3
"""Check that every contract a clause names by name exists in `contracts/`.

    python3 ledger/checks/clause_named_contracts.py contracts/experience.v1.md 15

Prints one line, and exits 0 whatever it finds, so the row's
`expect.stdout_contains` is the assertion:

    CLAUSE-15-NAMED-CONTRACTS NAMED=6 PRESENT=4 MISSING=platform-browser.v1,platform-web-app.v1

WHY IT READS THE CLAUSE INSTEAD OF NAMING THE FILES. CVG-114's first probe
hard-coded `platform-browser.v1` and `platform-web-app.v1` and asserted they
were ABSENT. That is true today and would stay true forever -- including after
an amendment that stops mentioning either name, at which point the row would go
on passing while asserting the absence of two names no document holds. A row
that passes for a reason nobody holds is a stale check, not a kept clause
(converge-oye). Reading the names out of the clause makes the row move when the
clause moves, in either direction: amend the clause to name a contract that
exists and this goes green; add a name that does not exist and it goes red.

WHAT COUNTS AS A NAMED CONTRACT. A backticked `<name>.v1` inside the clause,
resolved against `contracts/<name>.v1.md`. A glob (`platform-*.v1`) is NOT a
name and is skipped -- the character class excludes `*` -- because the clause
uses it to describe the family's shape, not to point at a file.

WHERE THE CLAUSE STARTS AND STOPS. The Core list is numbered, so a clause runs
from its own `N.` at the start of a line to the next numbered item or the next
`## ` heading. If the number is not found at all this prints
`CLAUSE-<n>-NOT-FOUND-REREAD-THIS-ROW` rather than an empty, green-looking
count -- a renumbered contract must reach a person, not pass silently.

WHAT IT CANNOT PROVE. That the named contract is the RIGHT one, or that the
family it describes is the family that exists. It proves the umbrella and the
folder agree about the family's membership by name; which of them is wrong when
they disagree is a reading, and a reading is the steward's.
"""

from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
CONTRACTS = ROOT / "contracts"

# A backticked contract name: letters and hyphens, then `.v<digits>`. `*` is not
# in the class, so the clause's own `platform-*.v1` glob is not read as a name.
NAME = re.compile(r"`([a-z][a-z0-9-]*\.v\d+)`")


def clause_text(text: str, number: int) -> str | None:
    """The one numbered Core clause, from its own marker to the next one."""
    start = re.search(rf"(?m)^{number}\.\s", text)
    if start is None:
        return None
    rest = text[start.start():]
    # Search from the clause's own newline, never from index 1: `(?m)^` matches
    # at the start of the string too, so scanning `rest[1:]` matched the tail of
    # this very clause's own `15.` marker and returned a one-character body.
    # Measured 2026-09-04: NAMED=0 on a clause that names six contracts.
    nl = rest.find("\n")
    if nl == -1:
        return rest
    end = re.search(r"(?m)^(?:\d+\.\s|## )", rest[nl:])
    return rest if end is None else rest[: nl + end.start()]


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(f"usage: {argv[0]} <contract-path> <clause-number>", file=sys.stderr)
        return 2
    path, number = ROOT / argv[1], int(argv[2])
    if not path.is_file():
        print(f"CLAUSE-{number}-CONTRACT-MISSING-REREAD-THIS-ROW: {argv[1]}")
        return 0

    body = clause_text(path.read_text(encoding="utf-8"), number)
    if body is None:
        print(f"CLAUSE-{number}-NOT-FOUND-REREAD-THIS-ROW: no '{number}.' item in {argv[1]}")
        return 0

    named = list(dict.fromkeys(NAME.findall(body)))
    missing = [n for n in named if not (CONTRACTS / f"{n}.md").is_file()]
    print(f"CLAUSE-{number}-NAMED-CONTRACTS NAMED={len(named)} "
          f"PRESENT={len(named) - len(missing)} "
          f"MISSING={','.join(missing) if missing else 'none'}")
    for n in named:
        mark = "absent " if n in missing else "present"
        print(f"  {mark} contracts/{n}.md", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
