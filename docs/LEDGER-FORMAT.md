# Conformance Ledger — Starter Format

**Status:** DRAFT convention — deliberately **not** a contract.
**Promotion trigger (named):** the moment a *second* repo adopts this format,
or the first real cross-repo ledger query is needed, this crosses the seam
test ("if this changed silently, who breaks?"). At that point: author
`ledger-format.v1.md` in the shared contracts repo and take it through the
Freeze Bar. Until then, adopting repos may deviate freely — deviations are
data for v1.
**Derived from:** better-attractor's spec-conformance matrix
(`DESIGN-conformance-matrix.md`, ~154 rows, probes measured passing) — the
only working implementation. Portable parts kept; engine-specific parts
stripped (see §7).
**Semantics owned by:** `PROTOCOL.md` §3.3. This file is syntax and
invariants only.

---

## 1. Placement

In each adopting repo:

```
ledger/
  rows.yaml          # the ledger (may be split by contract, e.g. rows-<seam>.yaml)
  checks/            # probe functions the rows reference (plain test code)
```

Checks run inside the repo's existing test job (`pytest -q` or equivalent).
No new CI job. In-process only: no LLM, no network, no subprocess. The
source implementation's full probe corpus ran in ~0.25s — slow ledgers
don't get run, and a ledger that isn't run is a remembered audit.

## 2. Row schema

```yaml
- id: LGR-011                    # stable forever; never renumbered, never reused
  title: unknown-key refusal (automation file)
  contract:
    file: contracts/automation-file.v1.md
    clause: "Core 3"             # the numbered invariant this row asserts
    quote: |                     # verbatim from the contract; machine-verified
      An unknown key is refused loudly with a remedy.
  disposition: CONFORMS          # see §3
  assertion:
    kind: probe                  # probe | indexed | absence | none
    ref: test_row_lgr_011        # function in ledger/checks/ (existence-verified)
  notes: >
    Optional. Load-bearing context, paired guards, etc.
```

Field rules:

| Field | Rule |
|---|---|
| `id` | Stable forever. Never renumbered, never reused — rows are cited from tracker items and amendments. |
| `contract.quote` | **The binding anchor.** Verbatim, machine-verified against the contract file's bytes. Line numbers may be stored but are informational — never asserted. |
| `assertion.kind: probe` | A dedicated check function; bidirectional probe↔row-id cross-check enforced. |
| `assertion.kind: indexed` | Cites existing test(s) by file+name; existence verified **statically** (parse, don't import) so cites may cross environment boundaries. Proves the test exists — not that it still asserts the claim. Prefer `probe` for load-bearing rows. |
| `assertion.kind: absence` | Asserts a capability is *absent* (e.g. a grep count of 0). Makes EXCLUDED executable: a future silent implementation flips the row red. |
| `assertion.kind: none` | Legal **only** for `NOT-ASSERTABLE`. |
| `justification` | Required for `OPEN-PINNED` and `NOT-ASSERTABLE`. |
| `work` | Tracker item ref; required for `GAP` and `VIOLATION` (a red row without a filed item is a ledger that lies). |

## 3. Dispositions

The vocabulary is PROTOCOL.md §3.3's, unchanged: `CONFORMS · GAP ·
VIOLATION · OPEN-PINNED · NOT-ASSERTABLE · EXCLUDED`.

One addition for externally-governed contracts only:

| Disposition | Meaning |
|---|---|
| `DIVERGED` | A *decided*, ledgered divergence from a contract this team does not own (an upstream spec). Requires a decision record cite. **Illegal for self-governed contracts** — if we own the contract and disagree with it, the move is a CANDIDATE amendment, not a ledgered divergence. |

`DIVERGED` rows assert **both halves**: the documented behavior occurs AND
the contract behavior does not. Silently re-aligning to the upstream spec
("un-diverging") fails as loudly as regressing — drift is bidirectional.

## 4. The SYNC row

Row `<PREFIX>-000` pins the contract file(s): path + content hash (and
`repo@sha` when the contract lives elsewhere). A hash mismatch triggers a
**mandatory full-ledger re-review — never a silent hash bump.** Quote
verification proves the quoted text still exists; only the re-review
confirms each row's *reading* of it is still correct.

## 5. Flip messages

Generated from row fields by one shared helper — never hand-written. Seven
fixed parts: greppable banner → contract anchor + quote → disposition +
cites → direction (`REGRESSION` / `UN-DIVERGENCE` / `UNDECIDED-MOVEMENT` /
`LEDGER-INTEGRITY`) → observed vs expected → the two legal exits (revert,
or in the same change: update the contract/amendment + row + guards) →
closing invariant: *"Doing neither means main carries a ledger that lies.
That is drift."*

## 6. Coverage tripwires

Run with the ledger, every time:

1. Every `REQUIRED` clause of every FROZEN contract is cited by ≥1 row.
2. Every ledgered divergence/amendment is cited by ≥1 row.
3. Every row's quote verifies against contract bytes; every assertion ref
   resolves; every `GAP`/`VIOLATION` row carries a live `work` ref.

## 7. Stripped from the source implementation (on purpose)

Engine-specific seams (mock backends, event-capture doubles), the
per-module-venv constraint that *forced* static cite-verification (kept as
an option, not a mandate), the source repo's ledger-file grammar and row
prefixes, and its specific `NOT-ASSERTABLE` judgment calls. Also renamed:
`DIVERGE-DECIDED`→`DIVERGED`; `EXTENSION` dropped (the protocol routes
beyond-contract behavior to IDIOM latitude or the "no third option" axiom);
`NOT-IMPLEMENTED-DECIDED` dropped (that's `EXCLUDED` or a Backlogged clause
here, since we own our contracts).

## 8. Honest limits

- Quote-verification proves text exists, not that the row reads it correctly.
- Static cite-verification proves a test exists, not that it still asserts
  the claim. Prefer probes for load-bearing rows.
- A repo with no contracts gets a test suite from this pattern, not a drift
  detector. The format's first demand on such a repo is: write the contract.

---

## Changelog

- **2026-08-29 — Starter format drafted** from better-attractor's
  conformance-matrix design; vocabulary reconciled to PROTOCOL.md §3.3
  (+`DIVERGED` for external contracts). DRAFT convention with named
  promotion trigger; not a contract.
