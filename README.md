# Converge

**Vision-first, contract-driven development.**

The owner and the orchestrator negotiate at the **contract** level. Work is
**derived from the gap** between repo reality and the ratified contracts —
never invented. A standing conformance ledger (the **ratchet**) prevents
silent backsliding: drift in either direction files a row. The owner's
attention is spent only at the contract layer; everything below it that
reaches the owner is a protocol defect.

## Status

**Increment 4 build (final) — the agent roster is complete.** This bundle
ships:

- `context/converge-awareness.md` — a thin pointer wired into the root session
- `agents/protocol-authority.md` — THE carrier of the ratified protocol
- `agents/reconciler.md` — the ratchet: SEED + standing RECONCILE
- `agents/negotiator.md` — Phase 1 NEGOTIATE: turns investigation evidence into
  decision-level minutes for the owner (options + recommendation + the one
  decision to make); returns needs rather than re-routing; read-only.
- `agents/amendment-drafter.md` — authors `CANDIDATE-<topic>.md` proposals
  (exact diff · real-evidence bar · "what does NOT change" · ratification ask ·
  the `target:` field the guard escape hatch consumes) and **stops**; never
  edits the frozen file, never self-ratifies, returns needs.
- `skills/` — five procedure skills (seam test, CANDIDATE amendment authoring,
  Freeze Bar checklist, ledger dispositions, lane-brief discipline)
- `modules/hooks-candidate-guard/` — the ratchet's teeth: a `tool:pre` hook,
  wired on by default in `bundle.md`, that structurally enforces PROTOCOL.md
  §5 (no direct write to a FROZEN contract/`VISION.md`; amendments land only
  via a ratified `CANDIDATE-<topic>.md`). See that module's own README for
  the full contract and documented non-coverage.

All three phase-loop recipes are specced as complete recipe-author handoffs in
`docs/design/mechanism-spec.md` §4 — `encode` (§4.1), `seed-reconcile` (§4.2),
`full-wave` (§4.3) — authored via `recipes:recipe-author`, not shipped as
bundle files. The orchestration mode is deferred by decision (pure delegation +
recipe gates + hook instead).

## The authoritative spec

- **`docs/PROTOCOL.md`** — the ratified protocol (v2). The source of truth.
- **`docs/LEDGER-FORMAT.md`** — the starter conformance-ledger format (a DRAFT
  convention with a named promotion trigger; not a contract).

Everything in this bundle quotes or points to those docs rather than
restating them. Read `docs/PROTOCOL.md` first.

## What it does not do

This bundle is stateless know-how. It does **not** own the tracker, does
**not** ratify anything (only the owner does, in literal words), and does
**not** store any repo's VISION.md, contracts, or ledger — those live in each
target repo.
