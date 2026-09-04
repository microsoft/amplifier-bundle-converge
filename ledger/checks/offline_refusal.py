#!/usr/bin/env python3
"""Does the app refuse a write offline in a plain sentence, and for how many writes?

    python3 ledger/checks/offline_refusal.py

Prints one line, and exits 0 whatever it finds, so the row's
`expect.stdout_contains` is the assertion:

    OFFLINE-REFUSAL=PLAIN-SENTENCE-RELAYED WRITES-NAMED=4-OF-5 MISSING=priority

WHY THIS REPLACED A GREP FOR "Could not". Until 2026-09-04 this clause was
watched by `grep -q 'Could not' app/static/js/actions.js`, reported as
OFFLINE-WRITES-FAIL-AS-A-FETCH-ERROR. That string is still there and its
MEANING INVERTED underneath the check: it used to be a raw fetch error shown to
the reader, and it is now the app's own words in front of the service worker's
plain sentence ("Could not ask: you are offline, so nothing was asked --
reconnect and ask again, or tell the manager session directly"). A probe that
greps a string cannot see a meaning change, so it went on reporting a gap that
had been closed.

WHAT IT READS, AND THE CHAIN IT WALKS -- three files, because the sentence is
made in one and shown by another and no single file settles the clause:

  `app/static/sw.js`      makes the sentence: a lead that never claims the wrong
                          failure (`you are offline` vs `Converge could not be
                          reached`, from `navigator.onLine`), an ENDING per write
                          path naming what to do instead, and a JSON body whose
                          `error` carries it.
  `app/static/js/api.js`  carries that sentence OUT as the thrown error rather
                          than replacing it with a status code.
  `app/static/js/actions.js`
                          relays `err.message` to the reader instead of inventing
                          a cause of its own.

THE COUNT IS THE PIN. `WRITES-NAMED` counts how many of the five writes
`experience.v1` Core 4 names have an ENDING of their own in the service worker.
Four do. The fifth -- raise or lower a priority -- has no route to refuse
(converge-a5g), so the clause cannot be fully kept before that one is. Pinning
the count means this row moves when EITHER fact moves: a lost sentence drops the
count, and the missing write's arrival raises it.

WHAT IT DOES NOT PROVE: that a browser with the network pulled shows the
sentence. That is a live round trip, and it is what `app/tests/` drives with a
real service worker. A static read settles that the sentence exists, names what
to do, and is relayed whole -- never that it reaches a screen.
"""

from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
SW = ROOT / "app" / "static" / "sw.js"
API = ROOT / "app" / "static" / "js" / "api.js"
ACTIONS = ROOT / "app" / "static" / "js" / "actions.js"

#: The five writes experience.v1 Core 4 names, and the route-matching literal
#: each one's ENDING entry is keyed on in the service worker.
WRITES = {
    "decision": "/decision$/",
    "feedback": "/feedback$/",
    "steer": "/steer$/",
    "ask": "/ask$/",
    "priority": "/priority$/",
}


def main() -> int:
    for path in (SW, API, ACTIONS):
        if not path.is_file():
            print(f"OFFLINE-REFUSAL-CHANGED-REREAD-THIS-ROW: {path} is gone")
            return 0

    sw = SW.read_text(encoding="utf-8")
    api = API.read_text(encoding="utf-8")
    actions = ACTIONS.read_text(encoding="utf-8")

    # 1. the sentence is made, and it never claims the wrong failure
    plain = (
        "'you are offline'" in sw
        and "'Converge could not be reached'" in sw
        and "navigator.onLine" in sw
        and re.search(r"JSON\.stringify\(\s*\{\s*error: sentence", sw) is not None
    )
    # 2. api.js carries the served sentence out with the error, not a status code
    relayed_out = "body.error" in api and re.search(r"throw refusal", api) is not None
    # 3. actions.js shows what refused in its own words
    relays_message = actions.count("err.message") >= 4

    if not (plain and relayed_out and relays_message):
        print("OFFLINE-REFUSAL-CHANGED-REREAD-THIS-ROW: "
              f"sentence={plain} carried-out={relayed_out} relayed={relays_message}")
        return 0

    endings = re.search(r"const ENDINGS = \[(.*?)\n\];", sw, re.S)
    body = endings.group(1) if endings else ""
    named = [w for w, keyed_on in WRITES.items() if keyed_on in body]
    missing = [w for w in WRITES if w not in named]

    print(f"OFFLINE-REFUSAL=PLAIN-SENTENCE-RELAYED "
          f"WRITES-NAMED={len(named)}-OF-{len(WRITES)} "
          f"MISSING={','.join(missing) or 'none'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
