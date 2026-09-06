# `amplifier_converge` — the readers and the writers

**This is not the app you open beside a project.** That is [`app/`](../../app/),
started with `scripts/run-app.sh` on <http://127.0.0.1:8788>. This package is
the library that turns a repository into the words on a page, and writes the
four things a steward can do back into it. Nothing here is a copy of the truth —
each module answers one question by reading the project itself.

| | What it answers |
|---|---|
| `reading/documents.py` | the vision and the contracts, as documents a person can read |
| `reading/kept.py` | whether each promise is actually being kept, from the ledger |
| `reading/queue.py` | the work queue, through the work-tracker command line |
| `reading/lanes.py` | the lanes, and whether each worker session is still alive |
| `reading/proposals.py` | proposals — a manager session's draft and a teammate's pull request, alike |
| `reading/whatchanged.py` | what changed since you last read this, sentence by sentence |
| `reading/brief.py` · `constraints.py` · `gitfacts.py` · `ratifications.py` · `snapshot.py` · `strip.py` | the return brief, your limits, the code record, your words read back, one gathered look, the short list |
| `writing/` | the four writes `surface.v1` named — answer with a word · priority · feedback · steer (the app carries `experience.v1`'s five) |
| `home.py` | the only two things this package is allowed to remember, both outside the project |
| `words.py` | the plain state words, in one map, said in one place |

**What uses this today:** the repository's own suite (`tests/` — 139 passed,
measured below) and one reader inside the app: `app/data.py` says whether a
promise is Kept on the Direction page through `amplifier_converge.reading.kept`.
The app does the rest of its own reading.

## The earlier page, retired

`web/` held the *first* body: a server-rendered page of the same two places, no
framework, no client-side script, mobile-first, served by an
`amplifier-converge web` subcommand on loopback. It was written against
`contracts/surface.v1.md`, which the experience family superseded on 2026-09-03,
and nothing was written against it after that; the five experience kits read the
app on 8788 instead.

**It was retired on 2026-09-06 on the intent steward's word** — the page, the
subcommand, and the tests that exercised only the page. The readers and writers
above stayed, because `app/` uses them. Its conformance kit stayed too, at
`conformance/_superseded/surface/`: `ledger/checks/surface_clause9.py`,
`conformance/documents/run.py` and `tests/conftest.py` all still read it, so
retiring the page did not retire the kit.

`amplifier-converge` itself remains as the package's command, now with no
subcommand at all.

## Measured on this tree, 2026-09-06

```
$ uv run amplifier-converge --version
amplifier-converge 0.1.0

$ uv run amplifier-converge web
usage: amplifier-converge [-h] [--version]
amplifier-converge: error: unrecognized arguments: web

$ uv run --extra web --with pytest --with httpx pytest -q tests
139 passed in 5.05s
```
