# Worked example — Experience: Operation v1

Contract: [`../../contracts/experience-operation.v1.md`](../../contracts/experience-operation.v1.md)
Kit: [`../../conformance/experience-operation/`](../../conformance/experience-operation/)

A steward comes back after four hours and asks one question: can I still trust
this? Every block below is output from a command run on 2026-09-04 against this
repository at `f718a20`, with the app served from this worktree on port 8811.

> Operation is where confidence is regained, not where activity is watched. The
> kit judges exactly that difference — a body can show every lane moving and
> still fail, because movement is not the same as trust.

## Start with one promise

Clause 3, in full:

> **The return brief is the first thing a returning steward reads.**
> *(REQUIRED)* Time away · what finished · what is stuck · what needs your
> word · what quietly changed. The story is told in sentences, never inferred
> from charts.

Five parts. A brief with four is not four fifths of a brief — it is a brief
that quietly drops the part a steward came back for.

## Right and wrong, told apart

The kit ships two captured app snapshots. `sample-good` keeps every promise;
`sample-bad` breaks every one at once, so a single run surfaces them all:

```
$ uv run conformance/experience-operation/run.py conformance/experience-operation/fixtures/sample-good --json-only
exit=0  {"pass": 15, "fail": 0, "skip": 0}  PASS

$ uv run conformance/experience-operation/run.py conformance/experience-operation/fixtures/sample-bad --json-only
exit=1  {"pass": 0, "fail": 15, "skip": 0}  FAIL
```

Fifteen rules, and every one of them separates the pair. A rule nobody can make
fail proves nothing; that is why the kit's own self-test asserts each rule fails
on the bad target.

## The same check against the real body

```
$ uv run conformance/experience-operation/run.py http://127.0.0.1:8811

   1 PASS  the objective, the limits, and today's strategy stand above the work
  2a PASS  the plan is shown in waves, with the lanes inside them
  2b FAIL  every grouping carries its reason, and a redrawn plan shows why
   3 FAIL  the return brief is read first and carries all five of its parts
   4 FAIL  every entry on the confidence timeline opens onto its evidence
  5a FAIL  work derived, resolved, verified, reopened and stuck are shown as flow
  5b PASS  flow is never offered as outcome — the two readings are shown apart
   6 PASS  lanes running, lanes intended, and the fill control appear together
   7 FAIL  work truly ready is shown against work waiting on you, as two numbers
   8 FAIL  each lane carries a plain lane state word and evidence you can open
   9 PASS  Watch session opens that worker session's live view
  10 PASS  feedback can be dropped in seconds, in every form this body claims
  11 FAIL  steering offers exactly the five limits and no way to assign work
  12 PASS  no control on the board stops work by moving it
  13 FAIL  every manager session is listed, sorted by which needs you

   VERDICT: FAIL  (pass=7 fail=8 skip=0)
```

Seven of thirteen clauses are kept in this body today. The rest are Not yet, and
the kit names each one rather than reporting a score.

## What a failure actually says

Rule 3, in the kit's own words:

```
the brief never says what needs your word
```

Four parts of five are present. The missing one is the part the whole clause
exists for — a steward who reads that brief learns what happened and not what
is waiting on them, which is precisely the polite stall clause 7 also warns
about.

Rule 7 catches the same shape from the other side:

```
only ['waiting on you'] is shown; the clause asks for two numbers, and the
second — the steward's own backlog — is what keeps the operation from stalling
politely behind a person
```

And rule 2b names the difference between a plan and a list of work:

```
12 of 12 waves carry no reason — only their lane names
(['Engine', 'Ai', 'Wave 1', 'Wave 2', 'Wave 3']);
nothing shows why the plan was redrawn when it is
```

Both findings are carried by work items already filed — `converge-lwa` for the
plan and the brief, `converge-q66` for the numbers and the steering.

## A rule that passes and still tells you something

Rule 10 is Kept, and its report is worth reading anyway:

```
[PASS] 10  feedback is accepted in every form this body claims
           (text, a screenshot) and reaches the feedback write;
           not offered here: voice — where a body cannot do a thing,
           experience.v1 clause 14 asks it to say so in the app
```

The section clause asks only about the forms this body claims, so it is kept.
The umbrella's clause 14 asks a harder question — does the app *say* it cannot
take a voice note — and the answer there is silence. Two contracts, one screen,
and they disagree on purpose. The umbrella's own worked example follows that
thread: [`experience.md`](experience.md).

## Clause traceability

| Clause | Rule | Where it appears above |
|---|---|---|
| 1 — objective, limits, strategy above the work | 1 | live run, Kept |
| 2 — waves and lanes, every grouping with its reason | 2a, 2b | "What a failure actually says" |
| 3 — the return brief, all five parts | 3 | "Start with one promise"; the quoted failure |
| 4 — the confidence timeline opens onto evidence | 4 | live run, Not yet |
| 5 — throughput as flow, never as outcome | 5a, 5b | live run — flow Not yet, the separation Kept |
| 6 — lanes running against lanes intended | 6 | live run, Kept |
| 7 — truly ready against waiting on you | 7 | the quoted failure |
| 8 — a plain lane word, and evidence you can open | 8 | live run, Not yet |
| 9 — Watch session opens the live view | 9 | live run, Kept |
| 10 — feedback in whatever form is to hand | 10 | "A rule that passes and still tells you something" |
| 11 — steering sets limits, never assigns work | 11 | live run, Not yet |
| 12 — stopping is never a board button | 12 | live run, Kept |
| 13 — every manager session listed, told at once | 13 | live run, Not yet |

No claim here the contract does not make, and no verdict here that was not run.
