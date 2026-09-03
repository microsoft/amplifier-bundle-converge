# Worked example — Operation v1

Contract: [`../../contracts/operation.v1.md`](../../contracts/operation.v1.md)

One wave: a gap becomes an item, the plan is shown, two lanes run, a note you
dropped mid-wave is triaged, completion is judged by a check the manager session
re-ran itself, and you come back to a brief. Four hours; one word asked of you,
the intent steward.

> Your attention is never the bottleneck: what needs your word is parked, and
> everything else keeps moving.

## The gap becomes an item

The contract check reports one line *Not yet*. That is where the item comes
from — derived, never invented (clause 1):

```
Item      Pins file names only one proposal spelling
Contract  composition.v1, clause 7
Source    contract check, gate 7 — quoted: "the guard recognises both
          proposal names"; the pins file names one.
Done      The pins file names both, and gate 7 reports kept when the
          manager session re-runs it.
```

## The plan, shown with its reasons

Order, dependencies, collisions, and opportunistic picks are visible (clause 2);
you may reorder anything. Width is a collision decision (clause 6) — lanes fill
only with items that provably touch different files:

```
Lane A  pins file          contracts/… none · touches PINS.md only
Lane B  README setup line  blocked — README.md belongs to another lane
                           this wave; run adjacent, not parallel
Parked  ledger reseed      irreversible; waiting on your word (clause 11)
Width   2 of 4 intended — two remaining items collide. Fill from these
        disjoint items, or confirm the lower width? (clause 6)
```

Both lanes are real worker sessions — own working copy, branch, and terminal
session, launched through the parallel-lane tooling (clause 5). No launcher
means failing loudly, never quietly substituting sub-agents.

## Your note, mid-wave

You dropped one line from your phone. It is signal, not a ticket (clause 4):

```
Your note   "board still says two lanes but nothing's moved since lunch"
Read against operation.v1 clauses 6 and 7 · the wave now running · the
            board you saw (this morning's refresh, 11:04)
What it is  two reports sharing one cause. Lane B went silent at 12:10.
            The board was right; the lane was not.
Filed as    verification reopened on lane B, silence window and branch
            attached — not as "board wrong", and not a duplicate item.
Also        unreported by you: lane A finished at 12:40, silently.
```

## Judging

A marker is a claim (clause 7). Lane A's branch carries commits beyond base and
evidence on disk: *done*. Lane B's marker sits on an unchanged branch: *stuck,
with cause* — stuck outranks done, always. No stall ran on unnamed; each was
declared with its cause (clause 9).

It then merges, runs its own verification rather than trusting either lane's
account, runs the post-merge gate because two lanes landed in one repository,
and re-runs the contract check before writing to you (clause 8). Each item was
claimed atomically from the shared queue, held with a heartbeat, and resolved in
words written for whoever asked (clause 12).

## The brief

Plain sentences, appended to a log you can read (clause 10):

```
Away 3 h 40 m.

Finished — the pins file now names both proposal spellings. I re-ran the
check myself: gate 7 reports kept.

Stuck — the README setup line. The lane's marker said done, but its
branch had no commits beyond where it started. Cause: that file belongs
to another lane this wave.

Needs you — one call. Give the README line to the other lane, or hold it
for next wave.

Quietly broken, unreported — the two guards read different locked
markers, so a contract can be locked to one and open to the other. Filed
against composition.v1 and named in next wave's plan.
```

A manager session that had lost its footing would say so, write a hand-off a
fresh session could resume from, and stop (clause 13).

## Clause traceability

| Clause | Where it appears above |
|---|---|
| 1 — work is derived, never invented | the item's `Source` and `Contract` lines |
| 2 — the plan is visible | the plan block, with reasons |
| 3 — never the bottleneck | one word in four hours; the parked item |
| 4 — feedback is signal, not a ticket | "Your note, mid-wave" |
| 5 — lanes are real sessions | copy, branch, terminal session; no launcher → fail loud |
| 6 — width is a collision decision | `Width 2 of 4` and its question |
| 7 — done means the check was re-run | lane A done · lane B stuck, unchanged branch |
| 8 — integrate, verify, re-check | merge → verify → gate → re-check |
| 9 — stalls are decisions, not loops | each stall declared with its cause |
| 10 — a brief on every return | the brief block |
| 11 — four calls reach you | the parked item; the call in the brief |
| 12 — the shared queue, with custody | atomic claim · heartbeat · resolution |
| 13 — hand off when done | the closing sentence |
