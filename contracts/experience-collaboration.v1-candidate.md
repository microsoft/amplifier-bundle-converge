# Proposal — experience-collaboration.v1 (candidate, 2026-09-04)

**What this asks for:** that every behavior in
`contracts/experience-collaboration.v1.md` carries one of the four words, and that each is
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
the review experience in Direction and the intake that feeds it.
```

Replacement:

```
the review experience in Direction and the intake that feeds it. This contract
is one section of the `experience.v1` umbrella (`contracts/experience.v1.md`)
and inherits its platform mechanism: every clause below carries one of its four
words — `REQUIRED` (present and behaving as written), `IDIOM` (required; its
shape follows the platform), or `EXCLUDED` (a body must not carry it, and its
presence is the defect) — and is placed against its three surface classes. The
tag is the
clause's **full app** placement; **quick-access** is `EXCLUDED` throughout, and
**notification** may carry clause 6 (`OPTIONAL`), an inbound proposal arriving,
and is `EXCLUDED` for the rest.
```

### 2. Core clause 1 carries its word

Current:

```
1. **Git is the protocol; Converge is the lens.** Collaboration between people
   happens through the shared repository host — commits, pull requests, and
   their comments. Converge renders that flow; it never replaces it.
```

Replacement:

```
1. **Git is the protocol; Converge is the lens.** `(REQUIRED)` Collaboration
   between people happens through the shared repository host — commits, pull
   requests, and their comments. Converge renders that flow; it never replaces
   it.
```

### 3. Core clause 2 carries its word

Current:

```
2. **Manager sessions never talk to each other directly.** Two stewards both
   running Converge still meet as Converge · host · Converge, and neither
   manager session knows the other exists. That is what keeps a teammate on
   plain tooling a first-class participant, and keeps the seam between two
   parties something a person can read.
```

Replacement:

```
2. **Manager sessions never talk to each other directly.** `(EXCLUDED)` Two
   stewards both running Converge still meet as Converge · host · Converge, and
   neither manager session knows the other exists. That is what keeps a teammate
   on plain tooling a first-class participant, and keeps the seam between two
   parties something a person can read.
```

### 4. Core clause 3 carries its word

Current:

```
3. **Three origins, one review.** A proposal from your manager session, from a
   teammate, or from a pull request is shown identically: what changes sentence
   by sentence · the evidence · what does not change. Where it came from is a
   fact about the proposal, never a different experience.
```

Replacement:

```
3. **Three origins, one review.** `(REQUIRED)` A proposal from your manager
   session, from a teammate, or from a pull request is shown identically: what
   changes sentence by sentence · the evidence · what does not change. Where it
   came from is a fact about the proposal, never a different experience.
```

### 5. Core clause 4 carries its word

Current:

```
4. **Pull-request comments are a two-way bridge.** A question asked in Converge
   arrives as a comment; the reply arrives back inside the same review. The
   teammate never leaves their tools, and the steward never copies a judgment
   between tools.
```

Replacement:

```
4. **Pull-request comments are a two-way bridge.** `(REQUIRED)` A question
   asked in Converge arrives as a comment; the reply arrives back inside the
   same review. The teammate never leaves their tools, and the steward never
   copies a judgment between tools.
```

### 6. Core clause 5 carries its word

Current:

```
5. **Your answer returns where the proposal came from.** *ratified · ratified
   with edits · declined · later* — written to the dated ratification record and
   posted back to the origin, in the steward's own words.
```

Replacement:

```
5. **Your answer returns where the proposal came from.** `(REQUIRED)` *ratified
   · ratified with edits · declined · later* — written to the dated ratification
   record and posted back to the origin, in the steward's own words.
```

### 7. Core clause 6 carries its word

Current:

```
6. **Inbound changes arrive without you asking for them.** Webhooks where the
   host offers them, polling as the honest fallback. Freshness is never made the
   steward's job, and the fallback is named rather than assumed.
```

Replacement:

```
6. **Inbound changes arrive without you asking for them.** `(IDIOM)` Webhooks
   where the host offers them, polling as the honest fallback. Freshness is
   never made the steward's job, and the fallback is named rather than assumed.
```

### 8. Core clause 7 carries its word

Current:

```
7. **The manager session is not in the hot path.** A write made in the app goes
   through the ordinary repository and proposal mechanism directly; the manager
   session learns of it as an event and folds it into its next turn.
```

Replacement:

```
7. **The manager session is not in the hot path.** `(REQUIRED)` A write made in
   the app goes through the ordinary repository and proposal mechanism directly;
   the manager session learns of it as an event and folds it into its next turn.
```

### 9. Core clause 8 carries its word

Current:

```
8. **One steward per manager session.** Whose word counts is settled when the
   session is registered, not inferred from whoever is looking. Everyone else is
   a teammate, whose proposals get the same reading and none of the authority.
```

Replacement:

```
8. **One steward per manager session.** `(REQUIRED)` Whose word counts is
   settled when the session is registered, not inferred from whoever is looking.
   Everyone else is a teammate, whose proposals get the same reading and none of
   the authority.
```

### 10. Core clause 9 carries its word

Current:

```
9. **A ratification is a change to the repository, made the ordinary way.** The
   word is recorded and the text it ratifies is committed, so what was agreed
   has one record, and it is the one everybody already reads.
```

Replacement:

```
9. **A ratification is a change to the repository, made the ordinary way.**
   `(REQUIRED)` The word is recorded and the text it ratifies is committed, so
   what was agreed has one record, and it is the one everybody already reads.
```

### 11. Core clause 10 carries its word

Current:

```
10. **Converge adds no second collaboration surface.** Not another issue
    tracker, another document store, or a code-review tool. What a teammate
    needs to see is visible on the host, in the host's own terms.
```

Replacement:

```
10. **Converge adds no second collaboration surface.** `(EXCLUDED)` Not another
    issue tracker, another document store, or a code-review tool. What a
    teammate needs to see is visible on the host, in the host's own terms.
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

**The words chosen, clause by clause.** Seven clauses are `REQUIRED`. Clause 6
is `IDIOM`: inbound changes must arrive without the steward asking, and the
shape follows the host — webhooks where it offers them, polling as the honest
fallback. Two are `EXCLUDED`, because each names a behavior that must not
exist: a direct channel between two manager sessions (2), and a second
collaboration surface of Converge's own (10). Both are prohibitions, and
`EXCLUDED` is the word for a prohibition.

**Placement, in this contract's own words.** **Quick-access** is `EXCLUDED`
throughout: reviewing a proposal and answering a teammate are reading work, and
a widget that showed a count would be showing `experience.v1` clause 5's short
list, not this contract's behaviors. **Notification** may carry clause 6
(`OPTIONAL`) — that something arrived from the host is precisely the fact worth
surfacing without being asked, and clause 6 is the clause that promises it
arrives. The rest is `EXCLUDED`.


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
- **Every clause keeps its meaning; only clause 1 and clause 8 rewrap** to fit
  their tag, and no word in either is altered.
- **The boundary itself is untouched** — git stays the protocol, manager
  sessions still never talk to each other, and one steward per manager session
  stands.

