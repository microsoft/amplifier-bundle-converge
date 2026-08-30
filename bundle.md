---
bundle:
  name: converge
  version: 0.1.0
  description: >
    Vision-first, contract-driven development. The owner and the orchestrator
    negotiate at the contract level; work is derived from the gap between repo
    reality and the contracts, never invented; a standing conformance ledger
    (the "ratchet") prevents silent backsliding. Build increment 1: the
    knowledge layer (awareness pointer, protocol-authority agent, five procedure
    skills) plus the **reconciler** agent — the ratchet that derives ledger rows
    and detects bidirectional drift. Still deferred: the recipes (encode,
    seed-reconcile, full-wave), the hooks-candidate-guard hook (increment 2), and
    the negotiator/amendment-drafter agents. The orchestration mode is DEFERRED
    by decision (pure delegation + recipe gates + hook instead).

includes:
  - bundle: git+https://github.com/microsoft/amplifier-foundation@main
  # Work-tracker tools (work_list / work_add / work_file) for converge:reconciler.
  # Foundation does NOT provide these. URI verified against a live installation
  # (settings.yaml of a working session composing this exact behavior).
  - bundle: git+https://github.com/microsoft/amplifier-work-tracker@main#subdirectory=behaviors/work-tracker.yaml

# Compose converge's own agents into the coordinator. Without this block the
# agents are DISCOVERABLE (amplifier agents show converge:reconciler) but never
# COMPOSED into coordinator.config["agents"], so recipe execution fails with
# "Agent 'converge:reconciler' not found in configuration". Discovery != composition.
# (Live-verified fix — DTU dogfood, increment 1.)
agents:
  include:
    - converge:reconciler
    - converge:protocol-authority

# Register converge's own skills directory with tool-skills so load_skill() finds
# them in a composed session. Foundation provides the tool-skills MODULE (so
# load_skill exists) but its config.skills points only at foundation's own skills
# dir — converge's five skills would be DISCOVERABLE but not COMPOSED (same
# discovery != composition trap as agents). A top-level `skills:` key is silently
# ignored; the tool-skills config.skills list is the sanctioned wiring.
tools:
  - module: tool-skills
    source: git+https://github.com/microsoft/amplifier-bundle-skills@main#subdirectory=modules/tool-skills
    config:
      skills:
        - "@converge:skills"
---

# Converge

Vision-first, contract-driven development for Amplifier.

Direction changes land in the contract FIRST. Work is derived, never invented:
the gap between repo reality and the ratified contracts becomes tracker items;
autonomous lanes close them; a standing conformance audit — the **ratchet**
(the ledger + reconcile enforcement layer) — keeps the gap ledger honest
between waves and refuses silent drift in either direction.

@converge:context/converge-awareness.md

## What this bundle provides

- **`converge:protocol-authority`** — THE carrier of the ratified protocol.
  Delegate any *interpretive* question ("does this conform? / am I allowed?"):
  the stack, the phases, the lifecycle, the Freeze Bar, the amendment protocol,
  the owner attention budget. It holds the full `docs/PROTOCOL.md` so the root
  session doesn't have to.
- **`converge:reconciler`** — the **ratchet**. SEED and standing RECONCILE:
  derives clause-granular ledger rows from a repo's frozen contracts, runs the
  repo's own conformance kit, detects bidirectional drift, and files
  GAP/VIOLATION rows with tracker refs. The one mutating agent; never
  synchronously interrupts the owner. Carries `docs/LEDGER-FORMAT.md`.
- **Skills** (load on demand for a *procedural* "how do I…" ask):
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

**Build increment 1** — knowledge layer + the `reconciler` (ratchet) agent,
dogfooded against drumbeat's frozen contract. Not yet present: the phase-loop
recipes (`encode`, `seed-reconcile`, `full-wave` — specced in
`docs/design/mechanism-spec.md` §4, authored next via `recipes:recipe-author`),
the `hooks-candidate-guard` hook (increment 2), and the `negotiator` /
`amendment-drafter` agents. The orchestration mode is **DEFERRED by decision**
(pure delegation + recipe gates + hook). This bundle does not own the tracker,
does not ratify, and does not store any repo's vision, contracts, or ledger —
those live in each target repo.

@foundation:context/shared/common-system-base.md
