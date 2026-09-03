# Worked example — Documents v1

Contract: [`../../contracts/documents.v1.md`](../../contracts/documents.v1.md)

Writing one new contract from the template, then proposing a change to it once
it is locked. This is the contract every other document obeys, so the example is
documents themselves — copy the blocks and fill them in.

> A contract can be read in a minute, trusted, and checked — by anyone, with any
> tool. Terms of art are defined at first use or not used (clause 1).

## The new contract, from the template

One file, one contract, about one screen — fifty to a hundred lines (clause 2).
The skeleton, sections fixed in order (clause 4):

```markdown
# Retention Contract — v1 (DRAFT)

**Who builds against this:** everyone who stores anything a person later
asks to have removed — the intake steps, the queue, and whoever
answers it.

## Purpose

<Why this contract exists.>

## Core (the teeth)

1. **Nothing is kept that nobody can name a reason for.** Every stored
   thing carries the reason it is kept and the date that reason expires.
   Without both, it is not stored.
2. **A removal request is answered in one place.** …

## What v1 deliberately does NOT freeze

- Automatic expiry — promoted the first time a manual sweep is missed.

## Conformance kit asserts

- Every stored record carries a reason and an expiry date.

## Reserved / open questions

- Whether backups are in scope.
```

Four things most often got wrong:

- **Line 3 is `**Who builds against this:**`** — two to six lines naming who
  a silent change would surprise (clause 3).
- **Each clause leads with the rule as a fact, in bold,** then one to three
  plain lines of why; numbers match the kit's rule table (clause 5).
- **Status lives in the H1 parenthetical and nowhere else** (clause 6):
  `(DRAFT)` while open, the dated locked marker once the steward locks it. No
  contract carries *Kept* or *Broken*; that lives in the check.
- **A vision is written as though already true** — end state, present tense,
  dated changelog carrying evidence (clause 7). A brief is a few sentences.

## Proposing a change, once it is locked

Nothing edits a locked contract in place. You write a sibling file named
`<contract>.vN-candidate.md` — here `contracts/retention.v2-candidate.md` —
three parts, in order (clause 8):

```markdown
# Retention Contract — v2 (candidate)

## 1 · The exact change

Clause 1, sentence 2. Today: "…the date that reason expires."
Proposed:                     "…the date that reason expires, or the word
                               `indefinite` with a named approver."

## 2 · The evidence

A cost actually paid. On 2026-08-19 the signed-agreements store was swept:
every record needed an expiry date and nobody could name one. Four hours to
restore; two agreements were unrecoverable.

## 3 · What does not change

The reason itself stays mandatory. Records without one are still refused.
The removal-request path is untouched.
```

Preference is not evidence. The original stays law until the intent steward
answers with one word.

## What the change becomes

A work item names its contract in one line, defines done plainly, and quotes
the gap it came from (clause 9). State words are the same everywhere
(clause 10): work reads *Truly ready · Waiting on you · Working · Stuck · Done*,
contracts *Kept · Not yet · Broken · Pinned open · Can't check*, lanes *Working
· Quiet · Silent — may have died*. Technical detail is folded into a marked
section, never the deciding sentence (clause 11).

## What ships alongside

Every converged repository carries the participant kit, so a colleague or an AI
session new to Converge works here correctly (clause 12): a
contracts README (anatomy, index, lock bar, how to propose) · an `AGENTS.md`
addendum · a pins file every lane reads first · a pre-push scan that refuses
edits to locked contracts.

Converge writes its own documents from these templates and passes the same kit
(clause 13) — this file included.

## Clause traceability

| Clause | Where it appears above |
|---|---|
| 1 — written for amplified information workers | no term left undefined |
| 2 — one contract, one file, one screen | "fifty to a hundred lines" |
| 3 — line 3 says who builds against this | the skeleton's line 3 |
| 4 — the same sections, same order | the skeleton's headings |
| 5 — clauses lead with the rule as fact | skeleton clauses 1 and 2 |
| 6 — status in the H1 only | `(DRAFT)`, and the locked marker |
| 7 — visions written as already true | the fourth notice |
| 8 — a proposal is `<contract>.vN-candidate.md` | the candidate, three parts |
| 9 — a work item names its contract | "What the change becomes" |
| 10 — plain state words everywhere | the three vocabularies |
| 11 — technical detail is folded | "never the deciding sentence" |
| 12 — every repository carries the kit | "What ships alongside" |
| 13 — Converge is self-hosting | the closing line |
