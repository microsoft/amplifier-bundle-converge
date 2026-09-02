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
    and detects bidirectional drift. Build increment 2: the
    **hooks-candidate-guard** hook — structural enforcement of PROTOCOL.md §5
    (no direct write to a FROZEN contract or VISION.md; amendments land only
    via a ratified CANDIDATE-<topic>.md). Build increment 3: the
    **negotiator** agent — Phase 1 NEGOTIATE, turning investigation evidence
    into decision-level minutes for the owner (returns needs, never re-routes;
    read-only). Build increment 4 (final): the **amendment-drafter** agent —
    authors CANDIDATE-<topic>.md proposals and stops (the guard escape hatch's
    upstream author) — completing the four-agent roster. All three phase-loop
    recipes (encode, seed-reconcile, full-wave) SHIP in recipes/ and are
    live-verified (spec of record: docs/design/mechanism-spec.md §4). The
    orchestration mode is DEFERRED by decision (pure delegation +
    recipe gates + hook instead).

includes:
  - bundle: git+https://github.com/microsoft/amplifier-foundation@main
  # Work-tracker BEHAVIOR — supplies converge:reconciler's work_list/work_add/
  # work_file tools (foundation does NOT provide these). behaviors/converge.yaml
  # ALSO includes this same behavior (behavior-includes-behavior, the standard
  # pattern) so tracker filing works on the --app path too; declaring it here as
  # well keeps the root path self-contained and lets composition dedupe the two
  # references (identical URI) to one instance.
  - bundle: git+https://github.com/microsoft/amplifier-work-tracker@main#subdirectory=behaviors/work-tracker.yaml
  # Converge's own capability payload — agents, skills, hook, awareness context —
  # lives in the behavior, which is ALSO the standalone --app install target.
  # bundle.md includes it so the full-workspace (root) path and the --app path
  # compose the identical capability (DRY; mirrors work-tracker's own bundle.md,
  # which includes work-tracker:behaviors/work-tracker). The `converge:` namespace
  # resolves to this repo's checkout root (bundle.md is the root, name: converge).
  - bundle: converge:behaviors/converge

# NO top-level `spawn:` block — deliberately (DTU-verified 2026-09-02).
# A composed bundle's `spawn.exclude_tools` applies to EVERY spawned sub-agent in
# EVERY session it composes into — including via `--app` (live probe: a plain
# foundation session's foundation:explorer lost bash/delegate/load_skill; the
# removal control restored a byte-identical baseline). That blast radius is
# unacceptable for a composable surface. The agents' "no delegate / no skills /
# no shell" rules are BEHAVIORAL (their body instructions + explicit tools:
# blocks); the candidate-guard hook remains the structural enforcement that
# matters. Do NOT reintroduce a session-wide spawn policy here — per-agent spawn
# tool policy is an upstream feature request.
---

# Converge

Vision-first, contract-driven development for Amplifier.

Direction changes land in the contract FIRST. Work is derived, never invented:
the gap between repo reality and the ratified contracts becomes tracker items;
autonomous lanes close them; a standing conformance audit — the **ratchet**
(the ledger + reconcile enforcement layer) — keeps the gap ledger honest
between waves and refuses silent drift in either direction.

> The capability payload (agents, skills, hook, awareness context) lives in
> `behaviors/converge.yaml`, which this bundle includes and which is also THE
> standalone install target (`--app`). The awareness context loads via that
> behavior's `context.include` — it is deliberately not re-`@`-mentioned here to
> avoid double-loading. See **Install** in `README.md` for the two paths.

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
- **`hooks-candidate-guard`** — the ratchet's teeth. A `tool:pre` hook, on by
  default, that structurally denies a direct write/edit/patch (or a bash
  write-laundering attempt) targeting a FROZEN contract file or `VISION.md`.
  Amendments land only via a ratified `CANDIDATE-<topic>.md` sibling. See
  `modules/hooks-candidate-guard/README.md` for the full contract, the
  config surface, and documented non-coverage.
- **Recipes** (the phase loop — ship in `recipes/`, live-verified; spec of
  record `docs/design/mechanism-spec.md` §4):
  - `@converge:recipes/seed-reconcile.yaml` — SEED + standing RECONCILE:
    derive/refresh the ledger from a target repo's contracts, detect
    bidirectional drift, file GAP/VIOLATION tracker items (§4.2).
  - `@converge:recipes/encode.yaml` — Phase 2 ENCODE: draft `VISION.md` +
    per-seam contracts as DRAFT, owner-gated ratify, then commit (§4.1).
  - `@converge:recipes/full-wave.yaml` — the owner-gated wave
    SEED→QUEUE→EXECUTE→MERGE→VERIFY→CLOSE with the four §6 attention gates
    (§4.3, post-stage gate semantics).

## The authoritative spec

The ratified protocol is `docs/PROTOCOL.md` (v2). The starter conformance
ledger format is `docs/LEDGER-FORMAT.md` (a DRAFT convention, not a contract).
These docs are the source of truth; everything in this bundle quotes or points
to them rather than restating them.

## Status

**Live**: 4 agents (protocol-authority, reconciler, negotiator, amendment-drafter), 5 skills, candidate-guard hook, 3 recipes — all live-verified. Eval harness 6/6.

See `README.md` for build history. Spec of record: `docs/design/mechanism-spec.md`.

@foundation:context/shared/common-system-base.md
