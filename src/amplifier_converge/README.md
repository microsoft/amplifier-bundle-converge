# `amplifier_converge` — the package, and the older page inside it

**This is not the app you open beside a project.** That is [`app/`](../../app/),
started with `scripts/run-app.sh` on <http://127.0.0.1:8788>. This package is
two other things that happen to share a directory.

## 1. The readers and the writers

A library that turns a repository into the words on a page, and writes the four
things a steward can do back into it. Nothing here is a copy of the truth —
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
| `words.py` | the plain state words, in one map, said in one place |

**What uses this today:** the older page below, the repository's own suite
(`tests/` — 187 passed, measured below), and one reader inside the
app: `app/data.py` says whether a promise is Kept on the Direction page through
`amplifier_converge.reading.kept`. The app does the rest of its own reading.

## 2. `web/` — the earlier server-rendered page

The first body of the two halves: server-rendered HTML, no framework, no
client-side script, mobile-first. `home.py` beside it holds the only two things
the page is allowed to remember. It still runs:

```
uv run --extra web amplifier-converge web --repo . --port 8091
```

Loopback by default, on purpose. `--repo` chooses the project it reads;
`--project` names the work queue; `--lanes` points at the lanes directory;
`--no-remote` stops it asking GitHub for teammates' proposals.

**Its contract is superseded.** It was written against `contracts/surface.v1.md`,
which the experience family superseded on 2026-09-03, and its conformance kit
moved to `conformance/_superseded/surface/` with it. Nothing is written against
this page any more; the five experience kits read the app on 8788 instead.

## Measured on this tree, 2026-09-06

```
$ uv run --extra web amplifier-converge --version
amplifier-converge 0.1.0

$ uv run --extra web amplifier-converge web --repo . --port 8915 --no-remote &
$ curl -s -o /dev/null -w "HTTP %{http_code}\n" http://127.0.0.1:8915/
HTTP 200

$ uv run --extra web --with pytest --with httpx pytest -q tests
187 passed, 2 warnings in 61.40s
```

## The open call

It runs, it is tested, and nothing is written against it. Whether the page in
`web/` is retired or kept as a second body is the intent steward's call, and it
sits in one sentence at the end of the README's *What ships* section, answerable
in a word. The readers and writers above stay either way, because `app/` uses
them.
