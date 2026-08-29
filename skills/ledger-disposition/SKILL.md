---
name: ledger-disposition
description: >
  Assign the right disposition to a conformance-ledger row and understand the
  row schema and bidirectional-drift rule. Use when populating or reviewing the
  ledger (SEED/RECONCILE), when a row's check flips, when deciding CONFORMS vs
  GAP vs VIOLATION vs OPEN-PINNED vs NOT-ASSERTABLE vs EXCLUDED (or DIVERGED for
  external contracts), or when a filed row must map to a tracker item. Applies
  PROTOCOL.md §3.3; full syntax in docs/LEDGER-FORMAT.md.
version: 0.1.0
---

# Ledger dispositions

**Semantics owned by `@converge:docs/PROTOCOL.md` §3.3. Syntax and invariants
owned by `@converge:docs/LEDGER-FORMAT.md`** (a DRAFT convention with a named
promotion trigger — not a contract). This skill summarizes; the docs govern.

Ledger rows are *derived from* contracts — one per checkable clause,
machine-read and CI-executable. Never invent a row that no clause backs.

## The vocabulary (PROTOCOL.md §3.3)

| Disposition | Meaning | Consequence |
|---|---|---|
| `CONFORMS` | check passes | none |
| `GAP` | REQUIRED clause, no implementation | tracker item |
| `VIOLATION` | implementation contradicts a frozen clause | tracker item, or CANDIDATE amendment if evidence says the clause is wrong |
| `OPEN-PINNED` | undecided call; current behavior asserted by a check *without forging a decision* | ledger row, revisited at negotiation — an undecided call is a ledger row, not a vision |
| `NOT-ASSERTABLE` | no machine check possible; judgment-only, named as such | reviewed at cadence, never silently trusted |
| `EXCLUDED` | contract forbids it | presence is a violation |

For **externally-governed** contracts only, LEDGER-FORMAT.md §3 adds
`DIVERGED` — a *decided*, ledgered divergence from an upstream spec this team
does not own (requires a decision-record cite). **Illegal for self-governed
contracts:** if we own the contract and disagree with it, the move is a
CANDIDATE amendment, not a ledgered divergence.

## Drift is bidirectional

Moving *away* from a frozen clause is drift. Silently moving *back* toward spec
from a pinned behavior is **also** drift. Any change in the
spec↔implementation relationship not traceable to a ratified amendment or a
filed work item files a ledger row.

## Row schema (summary — see LEDGER-FORMAT.md §2 for the full form)

- `id` — **stable forever; never renumbered, never reused** (rows are cited by
  tracker items and amendments).
- `contract.quote` — **the binding anchor.** Verbatim, machine-verified against
  the contract's bytes. Line numbers are informational, never asserted.
- `assertion.kind` — `probe` (dedicated check; prefer for load-bearing rows) ·
  `indexed` (cites existing tests, existence-verified statically) · `absence`
  (makes `EXCLUDED` executable) · `none` (**legal only for `NOT-ASSERTABLE`**).
- `justification` — **required** for `OPEN-PINNED` and `NOT-ASSERTABLE`.
- `work` — tracker ref, **required** for `GAP` and `VIOLATION` (a red row
  without a filed item is a ledger that lies).

## Two standing integrity rules

- **SYNC row** (`<PREFIX>-000`) pins the contract file(s) by content hash. A
  mismatch triggers a **mandatory full-ledger re-review — never a silent hash
  bump.**
- **Coverage tripwires** run with the ledger every time: every REQUIRED clause
  of every FROZEN contract is cited by ≥1 row; every divergence/amendment is
  cited; every quote verifies and every `GAP`/`VIOLATION` carries a live `work`
  ref.

## Honest limit

Quote-verification proves the text exists, not that the row reads it correctly;
static cite-verification proves a test exists, not that it still asserts the
claim. Prefer probes for load-bearing rows.
