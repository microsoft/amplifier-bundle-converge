# Proposal — experience-operation.v1 (candidate, 2026-09-04)

**What this asks for:** that every behavior in
`contracts/experience-operation.v1.md` carries one of the four words, and that each is
placed against the three surface classes.

**Which promise it serves:** `contracts/experience.v1.md` Core 9 ("Every
behavior carries one of four words — `REQUIRED`, `IDIOM`, `OPTIONAL`,
`EXCLUDED`") and Core 13 ("Three surface classes, named once: full app ·
quick-access · notification. Every behavior is placed against all three").
Raised by work item `converge-er6`. The original stays the law until the
steward answers: *ratified · ratified with edits · declined · later*.

## The exact change

### 1. Tag form — the required tag becomes a code span (clauses 1–8, 11–13)

Current:

```
*(REQUIRED)*
```

Replacement:

```
`(REQUIRED)`
```

### 2. Tag form — the idiom tag becomes a code span (clauses 9 and 10)

Current:

```
*(IDIOM)*
```

Replacement:

```
`(IDIOM)`
```

### 3. Surface placement — one sentence added to the inheritance paragraph

Current:

```
question is whether the behavior is satisfied). An idiom satisfies a behavior;
it never subtracts one.
```

Replacement:

```
question is whether the behavior is satisfied). An idiom satisfies a behavior;
it never subtracts one. Every clause is also placed against the umbrella's three
surface classes: the tag is its **full app** placement; **quick-access** carries
clauses 6 and 7 (`OPTIONAL`) and **notification** clause 8 (`OPTIONAL`); what a
class is not given, it is `EXCLUDED` from.
```

## The evidence

**A failure caught, twice measured.** Run on 2026-09-04 against this repository
and the app on 127.0.0.1:8811, `uv run conformance/experience/run.py <app>`
reported:

```
[FAIL] 9  every_behavior_carries_one_of_four_words: section contracts with
behaviors carrying none of ['REQUIRED', 'IDIOM', 'OPTIONAL', 'EXCLUDED']:
experience-collaboration.v1.md (10 of 10); experience-console.v1.md (10 of 10).
```

```
[FAIL] 13 every_behavior_placed_against_three_surface_classes:
experience-collaboration.v1.md places behavior against none;
experience-console.v1.md places behavior against none;
experience-direction.v1.md places behavior against none;
experience-operation.v1.md places behavior against none — the three classes are
['full app', 'quick-access', 'notification']
```

Rule 13 is the harder one: not one of the four section contracts so much as
named `quick-access`, while all five platform contracts do. So "nobody thought
about the widget" could still pass as a decision — the exact failure the clause
exists to stop.

**The same two rules pass with this proposal applied.** The replacements in
this candidate and its three siblings were written into a scratch copy of this
repository and the kit re-run against the same app:

```
[PASS] 9  every behavior in every section contract carries one of the four
words: experience-collaboration.v1.md (10); experience-console.v1.md (10);
experience-direction.v1.md (11); experience-operation.v1.md (13)
[PASS] 13 every section contract places its behaviors against all three
surface classes
```

**A second failure caught while drafting: the tag form.** Written the obvious
way — `*(EXCLUDED)*`, matching the italic `*(REQUIRED)*` the two tagged
contracts already use — the documents kit failed:

```
[FAIL] 10a plain_state_words: 4 of 15 document(s) failed —
contracts/experience-collaboration.v1.md: machine state token in prose at
line(s) 10 (EXCLUDED), 12 (EXCLUDED), 14 (EXCLUDED), 29 (EXCLUDED), 58
(EXCLUDED); contracts/experience-console.v1.md: … ; contracts/
experience-direction.v1.md: … ; contracts/experience-operation.v1.md: …
```

`EXCLUDED` is one of the ledger's disposition tokens, and `documents.v1`
clause 10 forbids a machine state token in a contract's prose. The kit's own
remedy is the code span: a document that must NAME one of these puts it in
backticks. So the tag is `` `(REQUIRED)` `` rather than `*(REQUIRED)*`, which
is also how `experience.v1` clause 9 already writes all four words. With that
form the documents kit returns PASS (18 pass, 0 fail, 9 skip), including
rule 2 (length), rule 5a (bold-led clauses), rule 5c (every clause says why)
and rule 10a.

**A cost that shaped the shape.** `experience-direction.v1` and
`experience-operation.v1` were 96 lines each, against the 100 that
`documents.v1` clause 2 allows. A placement table — heading, blank, header row,
separator and one row per clause — is at least seven lines and would have put
both contracts over. So placement is one sentence, added to the paragraph that
already explains the tags. Both land at 99 lines; console at 90 and
collaboration at 96.

**Placement, in this contract's own words.** Operation is where confidence is
regained, and two of its facts are genuinely glanceable: lanes running against
lanes intended (clause 6) and work truly ready against work waiting on you
(clause 7). Those are `OPTIONAL` on **quick-access** — a body may carry them in
a widget, tray or menu bar, and none is at fault for leaving them out. A lane
falling to *Silent — may have died* (clause 8) is the one thing worth
interrupting for, so it is `OPTIONAL` on **notification**. Everything else on
both classes is `EXCLUDED`: a strategy, a plan, a confidence timeline and a
steering control are not things a widget can carry without subtracting from
them.


## What does not change

- **No clause is added, removed, renumbered, or reworded in what it requires.**
  Every replacement above inserts a tag; the word-level difference between each
  current block and its replacement was checked, and apart from the exceptions
  named below the only difference is the tag itself and where the line wraps.
- **The section order, the H1 status, and `(DRAFT)` stand.** This proposal adds
  no section, and it does not lock anything.
- **The Conformance kit asserts, What v1 deliberately does NOT freeze, and
  Reserved / open questions sections are untouched.**
- **No file outside `contracts/` changes** — not the app, not the ledger, not
  the kits. Rules 9 and 13 read `contracts/` directly, so ratifying this text
  is the whole of the fix.
- **The umbrella is not amended.** `experience.v1` already carries Core 9 and
  Core 13; this proposal keeps them in a section contract rather than changing
  what they ask for.
- **Every clause keeps the word it already carried** — the eleven `REQUIRED`
  and the two `IDIOM` tags say exactly what they said before; only their
  typography changes, from italic to a code span.

