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
    read-only). Still deferred: the phase-loop recipes (encode, seed-reconcile,
    full-wave — encode is specced for recipe-author) and the amendment-drafter
    agent. The orchestration mode is DEFERRED by decision (pure delegation +
    recipe gates + hook instead).

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
    - converge:negotiator

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

# Increment 2 — the ratchet's teeth (mechanism-spec.md §6.1 DECIDED: BUILD).
# Structural enforcement of PROTOCOL.md §5, pillar 3: no direct write to a
# FROZEN contract/VISION.md; amendments land only via a ratified
# CANDIDATE-<topic>.md. On by default (spec §3.2) — a guard that ships
# off-by-default recreates exactly the convention-only gap the behavioral
# model proved insufficient (OQ2). Full design: docs/design/hooks-candidate-guard-spec.md.
#
# Pre-publication note (spec §3.1): amplifier-bundle-converge is not published
# yet, so this uses a same-repo relative path source. Switch to
# `git+https://github.com/microsoft/amplifier-bundle-converge@main#subdirectory=modules/hooks-candidate-guard`
# once the repo is published — never hardcode an absolute filesystem path here.
hooks:
  - module: hooks-candidate-guard
    source: ./modules/hooks-candidate-guard
    config:
      enabled: true
      guarded_globs: ["contracts/*.md", "contracts/**/*.md", "docs/VISION.md", "VISION.md"]
      require_frozen_marker: true
      frozen_marker_regex: '(?im)^\*\*Status:\*\*\s*(?:RATIFIED|FROZEN)|^status:\s*FROZEN'
      always_allow_globs: ["**/CANDIDATE-*.md"]
      intercept_tools: ["write_file", "edit_file", "apply_patch"]
      tool_name_aliases: ["Write", "Edit", "MultiEdit"]
      path_fields: ["file_path", "path"]
      scan_bash: true
      bash_tool_name: "bash"
      escape_mode: "ratified_candidate"        # ratified_candidate | token | both
      candidate_glob: ["**/CANDIDATE-*.md"]
      ratified_stamp_regex: '(?im)^ratified(?:\s+as\s+edited)?\b.*\bby\s+owner\b'
      candidate_target_field: "target"
      allow_emergency_unlock: false
      emergency_unlock_token: ".converge/UNLOCK"
      fail_closed_on_error: true
      enforce_encode_before_impl: false        # rule (b), opt-in — see spec §4.6
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
- **`hooks-candidate-guard`** — the ratchet's teeth. A `tool:pre` hook, on by
  default, that structurally denies a direct write/edit/patch (or a bash
  write-laundering attempt) targeting a FROZEN contract file or `VISION.md`.
  Amendments land only via a ratified `CANDIDATE-<topic>.md` sibling. See
  `modules/hooks-candidate-guard/README.md` for the full contract, the
  config surface, and documented non-coverage.

## The authoritative spec

The ratified protocol is `docs/PROTOCOL.md` (v2). The starter conformance
ledger format is `docs/LEDGER-FORMAT.md` (a DRAFT convention, not a contract).
These docs are the source of truth; everything in this bundle quotes or points
to them rather than restating them.

## Status

**Build increment 1** — knowledge layer + the `reconciler` (ratchet) agent,
dogfooded against drumbeat's frozen contract.

**Build increment 2** — the `hooks-candidate-guard` hook, wired into this
bundle's `hooks:` block, on by default. Structural (not conventional)
enforcement of PROTOCOL.md §5, pillar 3: a direct write/edit/patch/bash
write to a FROZEN `contracts/*.md` or `VISION.md` is denied; amendments land
only via a ratified `CANDIDATE-<topic>.md`. See
`modules/hooks-candidate-guard/README.md` for the T2 tool-shape confirmation,
the escape hatch, and documented non-coverage (bash obfuscation,
unverified delegated-agent propagation — spec §2.9).

**Build increment 3** — the `negotiator` agent (Phase 1 NEGOTIATE), wired
into `agents: include`. It turns Phase-0 investigation evidence into
decision-level minutes for the owner (options + recommendation + the one
decision to make), returns needs rather than re-routing (root-as-router,
Finding #1), and is strictly read-only — it never ratifies and never writes.

Not yet present: the phase-loop recipes (`encode`, `seed-reconcile`,
`full-wave`). `encode` is specced as a complete recipe-author handoff in
`docs/design/mechanism-spec.md` §4.1; `seed-reconcile` in §4.2. The
`amendment-drafter` agent is still deferred. The orchestration mode is
**DEFERRED by decision** (pure delegation + recipe gates + hook). This bundle
does not own the tracker, does not ratify, and does not store any repo's
vision, contracts, or ledger — those live in each target repo.

@foundation:context/shared/common-system-base.md
