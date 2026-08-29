---
bundle:
  name: converge
  version: 0.1.0
  description: >
    Vision-first, contract-driven development. The owner and the orchestrator
    negotiate at the contract level; work is derived from the gap between repo
    reality and the contracts, never invented; a standing conformance ledger
    (the "ratchet") prevents silent backsliding. This is the EARLY build:
    the knowledge layer only (awareness pointer, protocol-authority agent, and
    the procedure skills). The behavior-heavy parts — recipes, modes, hooks,
    and the negotiator/reconciler agents — are deferred pending a behavioral
    model.

includes:
  - bundle: git+https://github.com/microsoft/amplifier-foundation@main
---

# Converge

Vision-first, contract-driven development for Amplifier.

Direction changes land in the contract FIRST. Work is derived, never invented:
the gap between repo reality and the ratified contracts becomes tracker items;
autonomous lanes close them; a standing conformance audit — the **ratchet**
(the ledger + reconcile enforcement layer) — keeps the gap ledger honest
between waves and refuses silent drift in either direction.

@converge:context/converge-awareness.md

## What this bundle provides (knowledge layer)

- **`converge:protocol-authority`** — THE carrier of the ratified protocol.
  Delegate any question about protocol conformance, the stack, the phases, the
  lifecycle, the Freeze Bar, the amendment protocol, or the owner attention
  budget. It holds the full `docs/PROTOCOL.md` so the root session doesn't
  have to.
- **Skills** (load on demand for a specific procedure):
  - `seam-test` — is this a seam? does it warrant a contract?
  - `candidate-amendment` — how to author a `CANDIDATE-<topic>.md` proposal
  - `freeze-bar` — the four-condition DRAFT → FROZEN checklist
  - `ledger-disposition` — the ledger disposition vocabulary + row schema
  - `lane-brief` — honesty gate, file-ownership split, provenance discipline

## The authoritative spec

The ratified protocol is `docs/PROTOCOL.md` (v2). The starter conformance
ledger format is `docs/LEDGER-FORMAT.md` (a DRAFT convention, not a contract).
These docs are the source of truth; everything in this bundle quotes or points
to them rather than restating them.

## Status

Early build — **knowledge layer only.** Not yet present (deferred to a
behavioral-model step): the phase-loop recipes (encode, seed/reconcile, full
wave), an orchestrator mode, enforcement hooks, and the negotiator and
reconciler agents. This bundle does not own the tracker, does not ratify, and
does not store any repo's vision, contracts, or ledger — those live in each
target repo.

@foundation:context/shared/common-system-base.md
