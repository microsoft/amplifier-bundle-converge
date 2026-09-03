---
name: ledger-disposition
description: >
  Give a contract-check row the right verdict, and report it in the five plain
  words a person reads — Kept · Not yet · Broken · Pinned open · Can't check —
  alongside the ledger's own internal words. Use when populating or reviewing
  the ledger, when a row's check flips, when choosing between CONFORMS, GAP,
  VIOLATION, OPEN-PINNED, NOT-ASSERTABLE and EXCLUDED (or DIVERGED for a
  contract someone else owns), or when a red row must point at a queue item.
  Applies documents.v1 §10 and PROTOCOL.md §3.3; full syntax in
  docs/LEDGER-FORMAT.md.
version: 0.2.0
---

# Verdicts on the contract check

The **contract check** — the ledger — is one row per checkable promise, derived
from the contracts themselves and re-run after every change lands. It is the
ratchet: progress only clicks forward.

Rows are *derived from* contracts. Never invent a row that no clause backs.

Semantics live in `docs/PROTOCOL.md` §3.3; syntax and invariants in
`docs/LEDGER-FORMAT.md`. This skill summarizes; those govern.

## The verdicts, and what a person reads

The ledger keeps precise internal words. Everything shown to the intent steward
uses the five plain ones.

| Internal | Plain word | Meaning | Consequence |
|---|---|---|---|
| `CONFORMS` | **Kept** | the check passes | none |
| `GAP` | **Not yet** | the contract requires it; nothing implements it | a queue item |
| `VIOLATION` | **Broken** | what exists contradicts a locked promise | a queue item — or a proposal to change the contract, if the evidence says the promise is wrong |
| `OPEN-PINNED` | **Pinned open** | undecided; current behavior is pinned by a check without pretending a decision was made | a row, revisited when the direction is next discussed |
| `NOT-ASSERTABLE` | **Can't check** | no machine check is possible; judgment only, named as such | reviewed on a cadence, never silently trusted |
| `EXCLUDED` | **Kept** while absent, **Broken** the moment it appears | the contract forbids it | presence is a violation |

For contracts **someone else owns**, `docs/LEDGER-FORMAT.md` §3 adds `DIVERGED`
— a decided, recorded departure from an upstream spec this team does not
control. It needs a cited decision, and it reads to a person as **Broken, on
purpose, with the decision attached**. It is illegal for a contract we own: if
we own it and disagree with it, the move is a proposal
(`<contract>.vN-candidate.md`), not a recorded divergence.

## Drift runs both ways

Moving away from a locked promise is drift. Silently moving *back* toward it
from a pinned behavior is **also** drift — the second kind is the one everyone
forgets. Any change in the relationship between contract and reality that cannot
be traced to a ratified proposal or a filed item gets a row.

## What a row carries

- `id` — **stable forever; never renumbered, never reused.** Queue items and
  proposals cite it.
- `contract.quote` — **the binding anchor.** Verbatim, checked against the
  contract's actual bytes. Line numbers are informational, never asserted.
- `assertion.kind` — `probe` (its own check; prefer this wherever the row
  matters) · `indexed` (cites existing tests, verified to exist) · `absence`
  (makes `EXCLUDED` runnable) · `none` (**legal only for `NOT-ASSERTABLE`**).
- `justification` — **required** for `OPEN-PINNED` and `NOT-ASSERTABLE`.
- `work` — the queue ref, **required** for `GAP` and `VIOLATION`. A red row with
  no filed item is a ledger that lies.

## Two standing integrity rules

- **The SYNC row** (`<PREFIX>-000`) pins the contract files by content hash. A
  mismatch means the whole ledger is re-reviewed — **never a silent hash bump.**
- **Coverage tripwires** run every time: every required clause of every locked
  contract is cited by at least one row; every divergence and every ratified
  proposal is cited; every quote still verifies; every **Not yet** and **Broken**
  row carries a live queue ref.

## The honest limit

Verifying a quote proves the text exists, not that the row reads it correctly.
Verifying a cited test proves the test exists, not that it still asserts the
claim. Where a row is load-bearing, give it its own check.
