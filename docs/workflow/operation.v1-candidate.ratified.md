# Proposal — operation.v1 (candidate, 2026-09-05)

**What this asks for:** one new Core clause in `contracts/operation.v1.md`
saying what a manager session does on a project that has no contracts yet —
both a blank repository and a repository that already holds code — and where
its own work comes from when there is no gap to derive from.

**Which promise it serves:** `operation.v1` Core 1, "Work is derived, never
invented", which today has no answer for a project with nothing to derive from.
Raised by work item `converge-jyg0`, from the onboarding audit
(`docs/workflow/ONBOARDING-AUDIT-2026-09-04.md`, findings c-3, c-4, and "Two
things no contract covers", 2). The original stays the law until the steward
answers: *ratified · ratified with edits · declined · later*.

## The exact change

Target file: `contracts/operation.v1.md`. Four changes, in the order they appear
in that file.

### 1. Purpose — the arc starts at the first wake, not at a contract gap

Current:

```
The manager session carries a project from contract gap to verified result so
that the steward's attention is spent only where a person is irreplaceable.
Waiting on the steward is never the bottleneck.
```

Replacement:

```
The manager session carries a project from first wake to verified result so that
the steward's attention is spent only where a person is irreplaceable. Waiting
on the steward is never the bottleneck.
```

Three lines before, three lines after. "Contract gap" moves out of the Purpose
because Core 1 already carries it, and because a Purpose that begins at a
contract gap contradicts the clause added below.

### 2. A new Core clause 14 — the first wake

Current (the Core list ends at clause 13):

```
13. **Hand off when done.** A manager session that has lost its footing says so,
    writes a hand-off a fresh session can resume from, and stops.
```

Replacement:

```
13. **Hand off when done.** A manager session that has lost its footing says so,
    writes a hand-off a fresh session can resume from, and stops.
14. **The first wake is investigate, then propose.** A project with no contracts
    has no gap to derive from, so the first work is drafting — clause 1's one
    exception. A blank repository starts at the vision; one that already holds
    code is adopted, and the work in flight pauses first. Both read what is
    there, then propose a vision and first contracts as drafts. On the steward's
    word the ledger is seeded and the queue derived; until it lands, no lane fills.
```

Six lines, the same length as the file's longest existing clause (clause 4).
It keys both paths the steward named: a blank repository — investigate, draft a
vision, draft contracts, seed the ledger, derive the queue; and an existing
repository — pause the work in flight, investigate what is there, propose the
vision and contracts as drafts, wait for the steward's word, then seed and file
the items that bring the repository into alignment.

### 3. Five bullets re-wrapped — the same words, fewer lines

`contracts/operation.v1.md` is 97 lines and `documents.v1` Core 2 bounds a
contract at 100. Changes 2 and 4 add seven lines, which would put the file at
104. Five bullets whose second line is a short remainder are re-wrapped onto one
line each, which is what the file already does at its two longest lines (77 and
97). **No word changes in any of the five.** The result is 99 lines.

Current:

```
- Manager sessions coordinating directly — promoted the second time one message
  must reach several.
```

Replacement:

```
- Manager sessions coordinating directly — promoted the second time one message must reach several.
```

Current:

```
- Every lane has a terminal session and working copy on disk; in-session
  sub-agents never hold work items.
```

Replacement:

```
- Every lane has a terminal session and working copy on disk; in-session sub-agents never hold work items.
```

Current:

```
- A marker on an unchanged branch is recorded stuck; a post-merge gate runs for
  multi-lane merges; every done has evidence the manager session re-ran.
```

Replacement:

```
- A marker on an unchanged branch is recorded stuck; a post-merge gate runs for multi-lane merges; every done has evidence the manager session re-ran.
```

Current:

```
- A stall is declared stuck; a brief exists for every return; a hand-off exists
  for every manager session that ended by choice.
```

Replacement:

```
- A stall is declared stuck; a brief exists for every return; a hand-off exists for every manager session that ended by choice.
```

Current:

```
- A namespace for Converge's own worker helpers, should the standard ones prove
  insufficient.
```

Replacement:

```
- A namespace for Converge's own worker helpers, should the standard ones prove insufficient.
```

### 4. A changelog row

Current (the last row):

```
| 2026-09-04 | Turnkey sentence: red → first green recorded (owner word "ratified") | evaluations/turnkey/RESULT.md GREEN 9·0·0 ×2; docs/workflow/owner-ratifications-2026-09-03.md round 4 |
```

Replacement:

```
| 2026-09-04 | Turnkey sentence: red → first green recorded (owner word "ratified") | evaluations/turnkey/RESULT.md GREEN 9·0·0 ×2; docs/workflow/owner-ratifications-2026-09-03.md round 4 |
| 2026-09-05 | New Core clause 14 (the first wake); Purpose starts at first wake; five bullets re-wrapped to stay inside the 100-line bound | docs/workflow/ONBOARDING-AUDIT-2026-09-04.md c-3, c-4, "Two things no contract covers" 2; modes/converge-manager.md:348 |
```

## The evidence

**A failure caught: on a project with no contracts, a conforming manager session
correctly does nothing.** `modes/converge-manager.md:348` heads the operating
loop "on every wake", and its first three steps are heartbeat, status, and
refill to width (`:358–362`). Each of those presupposes contracts, a ledger, a
queue with ready items, and a width already set. There is no branch for wake
one, and clause 1 forbids improvising one (`:53–55`):

> Nothing enters the queue because it seemed like a good idea. If you cannot
> name the contract, you do not have a work item - you have an opinion.

**The mode cannot be fixed first.** `modes/converge-manager.md:36–38` — "Every
section below is keyed to one clause and adds nothing the clause does not
already say." A day-one section with no clause behind it breaks the mode's own
rule, so the clause has to come first. Run in this working copy on 2026-09-05:

```
$ grep -nic "first wake\|blank repo\|adopt\|day one\|first day" modes/converge-manager.md
0
```

Not one mention. The mode is complete for the project it is already running and
silent on the project it is not yet running.

**A cost already paid: the most valuable path Converge has is held in one
person's head.** The audit records
(`docs/workflow/ONBOARDING-AUDIT-2026-09-04.md:205–213`, c-5) that the steward has driven
the adopt path by hand twice, in `cortex-core` and `drumbeat`, and that neither
run left a procedure in this repository — no adopt recipe, no adopt skill, no
section in the mode.

**A chain whose first two links have no mechanism.** Audit c-4 (same file,
`:196–203`): of
`blank repo → vision → contracts → seed → queue`, only *seed* has a documented
mechanism, `recipes/seed-reconcile.yaml`, and it derives the ledger from a
target repository's contracts. The recipe cannot run until something has
produced contracts, and nothing written down produces contracts.

**Work is stopped behind this decision right now.** `converge-njaj`, the item
that would write the adoption path down, says so in its own description: "Note
the ordering: this needs converge-jyg0 answered first, because a documented path
with no clause behind it is the thing modes/converge-manager.md:35-37 forbids."
(Quoted as filed; that sentence has since moved to `:36–38`.)

**The amended contract was checked, not assumed.** Run on 2026-09-05 in this
working copy: a scratch script read the eight before/after pairs above straight
out of this file, applied each to `contracts/operation.v1.md` — every one
matched exactly once — and ran the documents kit's contract rules against the
result.

```
pairs found: 8
  pair 1: applies  [The manager session carries a project from contract gap to verif...]
  pair 2: applies  [13. **Hand off when done.** A manager session that has lost its ...]
  pair 3: applies  [- Manager sessions coordinating directly — promoted the second t...]
  pair 4: applies  [- Every lane has a terminal session and working copy on disk; in...]
  pair 5: applies  [- A marker on an unchanged branch is recorded stuck; a post-merg...]
  pair 6: applies  [- A stall is declared stuck; a brief exists for every return; a ...]
  pair 7: applies  [- A namespace for Converge's own worker helpers, should the stan...]
  pair 8: applies  [| 2026-09-04 | Turnkey sentence: red → first green recorded (own...]
target lines: 97 -> 99
[PASS] 2    contract_length: all 1 contract(s) are 50–100 lines
[PASS] 4    contract_section_order: all 1 contract(s) carry the required sections in order
[PASS] 5a   contract_clauses_bold_led: all 1 contract(s) lead every Core clause in bold
[PASS] 5c   contract_clauses_carry_their_why: all 1 contract(s) say why after every bold lead
[PASS] 6    contract_status_only_in_h1: all 1 contract(s) keep status in the H1 alone
[PASS] 6b   no_progress_words_as_status: all 1 document(s) leave progress out of their status
[PASS] 10a  plain_state_words: all 1 document(s) keep their state words plain
[PASS] 11a  technical_detail_is_folded: all 1 contract(s) keep technical detail out of the teeth
Core clauses after: 14
```

The amended file is 99 lines, one inside the bound, and every mechanical rule
the documents kit applies to a contract passes on it.

## What does not change

- **No existing clause changes its meaning, its number, or its words.** Clauses
  1 through 13 read exactly as they read today; clause 14 is added after them.
  The five re-wrapped bullets are word-for-word identical to their current text.
- **Nothing is locked.** The H1 keeps `(DRAFT — content owner-ratified
  2026-09-02)`, and this proposal does not ask for a freeze.
- **The section order and the section list stand.** No section is added, removed
  or reordered; the changelog gains one row.
- **The conformance kit asserts are untouched, on purpose.** The turnkey run
  recorded green on 2026-09-04 exercised nine steps that begin from a sample
  gap. It does not exercise a first wake, and this proposal does not reword that
  bullet to imply it does. Extending the kit is work to be filed, not work this
  proposal performs.
- **No file outside `contracts/operation.v1.md` changes when this is ratified.**
  In particular the mode is not edited by this proposal.
- **Nothing here writes the first-wake procedure.** This proposal supplies the
  clause a procedure can be keyed to. The mode section, the adopt path and any
  recipe are `converge-njaj`, which this decision unblocks.

**One consequence to expect, named rather than discovered later:** the ledger's
own check requires every Core clause to be cited by at least one row
(`ledger/checks/verify.py`, §6.1). Today it reports `operation.v1.md 13 Core
clauses, cited 13/13 OK`. On the day clause 14 lands it will report `13/14
MISSING ['Core 14']` and exit non-zero until a row exists. That row is derived
work, and it starts at *Not yet* — the clause will be true of nothing until the
procedure behind it is written.

## The steward's word

One of four: *ratified* · *ratified with edits* · *declined* · *later*.

Answer here:

```
Word: ratified, please continue
Date: 2026-09-06
Edits (if "ratified with edits"): none — ratified as written
```

Recorded in `docs/workflow/owner-ratifications-2026-09-06.md`, round 1. Applied
to `contracts/operation.v1.md` on 2026-09-06 by `converge-462l` — all eight
before/after pairs above, verbatim, 97 lines → 99. This file is the archive of
the proposal as it was answered; the contract is the law.
