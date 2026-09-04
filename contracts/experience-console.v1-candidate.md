# Proposal — experience-console.v1 (candidate, 2026-09-04)

**What this asks for:** that every behavior in
`contracts/experience-console.v1.md` carries one of the four words, and that each is
placed against the three surface classes.

**Which promise it serves:** `contracts/experience.v1.md` Core 9 ("Every
behavior carries one of four words — `REQUIRED`, `IDIOM`, `OPTIONAL`,
`EXCLUDED`") and Core 13 ("Three surface classes, named once: full app ·
quick-access · notification. Every behavior is placed against all three").
Raised by work item `converge-er6`. The original stays the law until the
steward answers: *ratified · ratified with edits · declined · later*.

## The exact change

### 1. The inheritance paragraph — what the tags mean, and where the behaviors sit

Current:

```
the authors of `experience.v1`, the umbrella this contract hangs off.
```

Replacement:

```
the authors of `experience.v1`, the umbrella this contract hangs off. It
inherits that umbrella's platform mechanism: every clause below carries one of
its four words — `REQUIRED` (present and behaving as written), `IDIOM`
(required; its shape follows the platform), or `EXCLUDED` (a body must not
carry it, and its presence is the defect) — and is placed against its three
surface classes. The
tag is the clause's **full app** placement; **quick-access** and
**notification** are `EXCLUDED` throughout, because a console is one live session
beside the work, and clause 7 already keeps anything needing your word from
arriving only here.
```

### 2. Core clause 1 carries its word

Current:

```
1. **The console is a pane, not a place.** It opens beside Direction or
   Operation, and switching between them does not close it, restart it, or lose
   a line of what was said.
```

Replacement:

```
1. **The console is a pane, not a place.** `(REQUIRED)` It opens beside
   Direction or Operation, and switching between them does not close it,
   restart it, or lose a line of what was said.
```

### 3. Core clause 2 carries its word

Current:

```
2. **V1 carries the manager session exactly as it already runs.** The pane
   embeds the live command-line session through the tmux connector — tmux being
   the tool that lets a long-running terminal session be attached to from
   somewhere else. Nothing about the manager has to be redesigned to ship.
```

Replacement:

```
2. **V1 carries the manager session exactly as it already runs.** `(REQUIRED)`
   The pane embeds the live command-line session through the tmux connector —
   tmux being the tool that lets a long-running terminal session be attached to
   from somewhere else. Nothing about the manager has to be redesigned to ship.
```

### 4. Core clause 3 carries its word

Current:

```
3. **One console, one manager session, and it *is* that session.** What you type
   there is what the manager session receives, not a summary the app relays — so
   there is no second conversation to keep in step with the first.
```

Replacement:

```
3. **One console, one manager session, and it *is* that session.** `(REQUIRED)`
   What you type there is what the manager session receives, not a summary the
   app relays — so there is no second conversation to keep in step with the
   first.
```

### 5. Core clause 4 carries its word

Current:

```
4. **Wide screen: a resizable pane. Small screen: a sliding tray.** This is
   idiom, and the umbrella governs it — the shape follows the platform; the
   behaviors (stays open, keeps its conversation, gets out of the way on demand)
   do not change.
```

Replacement:

```
4. **Wide screen: a resizable pane. Small screen: a sliding tray.** `(IDIOM)`
   The umbrella governs it — the shape follows the platform; the behaviors
   (stays open, keeps its conversation, gets out of the way on demand) do not
   change.
```

### 6. Core clause 5 carries its word

Current:

```
5. **Watch session reuses this pane.** Watching a lane's live worker session
   from Operation opens here rather than in a new place, and leaving it returns
   the manager conversation where it stood.
```

Replacement:

```
5. **Watch session reuses this pane.** `(REQUIRED)` Watching a lane's live
   worker session from Operation opens here rather than in a new place, and
   leaving it returns the manager conversation where it stood.
```

### 7. Core clause 6 carries its word

Current:

```
6. **The console is never the dashboard.** Raw agent and tool activity is not
   how the operation is understood; Operation is. Nothing there may require
   reading the console to make sense.
```

Replacement:

```
6. **The console is never the dashboard.** `(EXCLUDED)` Raw agent and tool
   activity is not how the operation is understood; Operation is. Nothing there
   may require reading the console to make sense.
```

### 8. Core clause 7 carries its word

Current:

```
7. **Nothing that needs your word arrives only here.** Every decision reaches
   you through the short list and its ratification sheet, so a steward who never
   opens the console misses nothing and can answer everything.
```

Replacement:

```
7. **Nothing that needs your word arrives only here.** `(REQUIRED)` Every
   decision reaches you through the short list and its ratification sheet, so a
   steward who never opens the console misses nothing and can answer everything.
```

### 9. Core clause 8 carries its word

Current:

```
8. **The console never ratifies.** A word typed here is a message to the manager
   session; any decision it produces comes back through the ordinary path and
   lands in the dated ratification record.
```

Replacement:

```
8. **The console never ratifies.** `(EXCLUDED)` A word typed here is a message
   to the manager session; any decision it produces comes back through the
   ordinary path and lands in the dated ratification record.
```

### 10. Core clause 9 carries its word

Current:

```
9. **It is not a native chat in V1,** and nothing may be built to depend on it
   being one. A native conversation later replaces the connector underneath
   without changing one behavior above.
```

Replacement:

```
9. **It is not a native chat in V1.** `(EXCLUDED)` Nothing may be built to
   depend on it being one; a native conversation later replaces the connector
   underneath without changing one behavior above.
```

### 11. Core clause 10 carries its word

Current:

```
10. **It shows one manager session's own work and reaches nothing else.** The
    machine may hold other terminal sessions, checkouts, and queues; none of
    them appear merely because they exist.
```

Replacement:

```
10. **It shows one manager session's own work and reaches nothing else.**
    `(REQUIRED)` The machine may hold other terminal sessions, checkouts, and
    queues; none of them appear merely because they exist.
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

**The words chosen, clause by clause.** Six clauses are `REQUIRED`. Clause 4
is `IDIOM` — its own text already said so ("This is idiom, and the umbrella
governs it"), and the tag now says it in the family's vocabulary. Three are
`EXCLUDED`, because each names a behavior a body must *not* have: the console
as the dashboard (6), the console ratifying (8), and a native chat depended on
in V1 (9). Tagging those `REQUIRED` would have been the easy and wrong reading.

**Placement, in this contract's own words.** The console is one live session
beside the work; there is no version of it that fits in a widget or a banner
without becoming a second conversation, which clause 3 forbids. So
**quick-access** and **notification** are `EXCLUDED` throughout — and clause 7
already guarantees that costs a steward nothing, since nothing needing your
word arrives only here.


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
- **Two clauses change their wording, and only in the way the tag makes
  redundant.** Clause 4's "This is idiom, and the umbrella governs it" becomes
  "`(IDIOM)` The umbrella governs it" — the sentence that announced the idiom
  is replaced by the tag that records it. Clause 9's bold lead ends in a period
  rather than a comma, so the tag can follow it, and its two sentences are
  rejoined with a semicolon: "It is not a native chat in V1." then "Nothing may
  be built to depend on it being one; a native conversation later replaces the
  connector underneath without changing one behavior above." Nothing either
  clause requires is altered.
- **The tmux connector, the watch-session reuse, and the "never the dashboard"
  boundary all stand exactly as written.**

