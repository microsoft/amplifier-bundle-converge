# Worked example — Experience: Direction v1

Contract: [`../../contracts/experience-direction.v1.md`](../../contracts/experience-direction.v1.md)
Kit: [`../../conformance/experience-direction/`](../../conformance/experience-direction/)

A steward opens the agreement, and the kit that decides whether they could.
Every block below is output from a command run on 2026-09-04 against this
repository at `f718a20`, with the app served from this worktree on port 8811.

> Direction is where the agreement lives. The kit does not ask whether the
> screen looks right; it asks whether a steward could read what was agreed, see
> what moved, answer a proposal, and ask for one, without leaving.

## Start with one promise

Clause 5 of the contract, in full:

> **Direct editing is offered exactly where it is legal, and the guard is the
> law.** *(REQUIRED)* A draft document may be edited in place, click to save.
> A locked one may not, and the refusal comes from the guard that refuses —
> never from a hidden control or an instruction someone might follow.

Two things could go wrong, and they are not the same thing: a body that offers
editing where it is illegal, and a body that offers it nowhere at all. Rule 5
of the kit judges both.

## Right and wrong, told apart

The kit ships two captured app snapshots. `sample-good` keeps every promise;
`sample-bad` breaks every one at once, so a single run surfaces them all. Run
against both:

```
$ uv run conformance/experience-direction/run.py conformance/experience-direction/fixtures/sample-good --json-only
exit=0  {"pass": 12, "fail": 0, "skip": 0}  PASS

$ uv run conformance/experience-direction/run.py conformance/experience-direction/fixtures/sample-bad --json-only
exit=1  {"pass": 0, "fail": 12, "skip": 0}  FAIL
```

Twelve rules, and each one separates the pair. That is what the contract's
lock bar means by a real example of right and wrong: not an assertion that the
kit works, but a target it passes and a target it refuses.

## The same check against the real body

Point the same command at the running app instead of a fixture:

```
$ uv run conformance/experience-direction/run.py http://127.0.0.1:8811

   1 PASS  documents are organized per repository, with an All view across them
  2a PASS  every document arrives rendered, and its source sits beside it
  2b PASS  what the project's documents contain is what the render shows
   3 FAIL  a reader can copy rendered, copy source, download, zoom, and choose the width
   4 PASS  four views — Reading · Changes · Review · History — and Changes shows removals
   5 FAIL  direct editing is offered exactly where it is legal
   6 FAIL  restoring from history reaches a write, and routes through a proposal
   7 PASS  a proposal shows what changes · why · the evidence · what does not change
   8 PASS  accepting and reverting individual changes constructs ratified with edits
   9 FAIL  Ask is a scoped request whose output is always a proposal
  10 FAIL  concurrent editing is met with courtesy presence and reconciliation
  11 FAIL  the lock control is gated on the four conditions, and they are shown

   VERDICT: FAIL  (pass=6 fail=6 skip=0)
```

Six of eleven clauses are kept in this body today. The other five are Not yet,
and each names its own reason rather than a score.

## What a failure actually says

Rule 5, in the kit's own words:

```
a document-saving write route exists but nothing offers it
```

That is a precise finding, and it is not "editing is missing". The route landed;
no surface reaches it. A reader can go from that sentence to the clause, and
from the clause to the work — this one is carried by `converge-6cc`.

Rule 11 is the one that matters for the contract's own future:

```
no lock control and none of the four conditions appear anywhere the app serves,
so nothing gates a document being locked — and nothing shows a steward why it
is not yet lockable
```

The clause the app cannot yet keep is the clause about keeping clauses. Until
it does, locking stays where it already is: the steward's word, recorded by
hand.

## Clause traceability

| Clause | Rule | Where it appears above |
|---|---|---|
| 1 — documents per repository, with an All view | 1 | live run, Kept |
| 2 — documents render, source one gesture away | 2a, 2b | live run, Kept |
| 3 — copy, download, zoom, choose the width | 3 | live run, Not yet — one copy ability of two |
| 4 — four views, and Changes shows removals | 4 | live run, Kept |
| 5 — editing offered exactly where legal | 5 | "Start with one promise"; "What a failure actually says" |
| 6 — restore routes through a proposal when locked | 6 | live run, Not yet |
| 7 — a proposal looks the same whoever proposed it | 7 | live run, Kept |
| 8 — granular choices build ratified with edits | 8 | live run, Kept |
| 9 — Ask returns a proposal, at every scope | 9 | live run, Not yet — the fifth write is absent |
| 10 — courtesy presence and reconciliation | 10 | live run, Not yet |
| 11 — the lock control is gated on four conditions | 11 | "What a failure actually says" |

No claim here the contract does not make, and no verdict here that was not run.
