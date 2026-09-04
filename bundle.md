---
bundle:
  name: converge
  version: 0.1.0
  description: >
    Vision-first, contract-driven development. The intent steward and the
    manager session negotiate at the contract level; work is derived from the
    gap between repo reality and the contracts, never invented; a standing
    conformance ledger (the "ratchet") prevents silent backsliding. Ships four
    agents (protocol-authority, reconciler, negotiator, proposal-drafter),
    five procedure skills, the hooks-candidate-guard hook (structural
    enforcement of PROTOCOL.md §5), the thin awareness context, and one
    recipe — seed-reconcile, the ratchet loop. Assembles on the lean anchors
    base; the full foundation package appears nowhere.

includes:
  # The LEAN BASE (composition.v1 Core 1). `anchors` carries the session block,
  # the everyday tool roster, delegate/skills/recipes, and six thin agents
  # (explorer, builder, git-ops, architect, debugger, researcher). Converge's
  # recipe steps use only these. The heavy full-foundation package is NOT
  # included: sessions stay fast and cheap.
  - bundle: git+https://github.com/microsoft/amplifier-foundation@main#subdirectory=bundles/anchors/bundle.md
  # Work-tracker BEHAVIOR — supplies converge:reconciler's work_list/work_add/
  # work_file tools (the lean base does NOT provide these). behaviors/converge.yaml
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

# NO top-level `spawn:` block — deliberately (composition.v1 Core 6, measured
# 2026-09-02). A composed bundle's `spawn.exclude_tools` applies to EVERY spawned
# sub-agent in EVERY session it composes into — including via `--app` (live probe:
# an unrelated session's own helper lost bash/delegate/load_skill; the removal
# control restored a byte-identical baseline). That blast radius is unacceptable
# for a composable surface. The agents' "no delegate / no skills / no shell" rules
# are BEHAVIORAL (their body instructions + explicit tools: blocks); the
# candidate-guard hook remains the structural enforcement that matters. Do NOT
# reintroduce a session-wide spawn policy here — per-role spawn tool policy is an
# upstream feature request.
#
# Absence HERE is not the same as absence on a user's machine. Measured
# 2026-09-04 (converge-w3v): this file was clean, the kit's rules 6a and 6b both
# PASSed, and a published fork of this same bundle — app-installed on the same
# host — was stripping tool-bash, tool-delegate and tool-skills from every
# spawned helper in every session on it, unrelated work included. Rule 6c of
# conformance/composition/ is the standing check for that case: it composes the
# neighbour's session the way the HOST does, and names the installed entry that
# carries the policy.
---

# Converge

Vision-first, contract-driven development for Amplifier.

Direction changes land in the contract FIRST. Work is derived, never invented:
the gap between repo reality and the ratified contracts becomes tracker items;
autonomous worker sessions close them; a standing conformance audit — the
**ratchet** (the ledger + reconcile enforcement layer) — keeps the gap ledger
honest between waves and refuses silent drift in either direction.

> The capability payload (agents, skills, hook, awareness context) lives in
> `behaviors/converge.yaml`, which this bundle includes and which is also THE
> standalone install target (`--app`). The awareness context loads via that
> behavior's `context.include` — it is deliberately not re-`@`-mentioned here to
> avoid double-loading. See **Install** in `README.md` for the two paths.

## What this bundle provides

- **`converge:protocol-authority`** — THE carrier of the ratified rules.
  Delegate any *interpretive* question ("does this conform? / am I allowed?"):
  the layers and which governs which, the loop, the four conditions for locking
  a document, how a locked document changes by proposal, and the four calls that
  reach the intent steward. It holds the full `docs/PROTOCOL.md` so the root
  session doesn't have to.
- **`converge:reconciler`** — the **ratchet**. SEED and standing RECONCILE:
  derives clause-granular ledger rows from a repo's locked contracts, runs the
  repo's own conformance kit, detects bidirectional drift, and files
  GAP/VIOLATION rows with tracker refs. The one mutating agent; never
  synchronously interrupts the intent steward. Carries `docs/LEDGER-FORMAT.md`.
- **`converge:negotiator`** — Phase 1 NEGOTIATE. Turns investigation evidence
  into decision-level minutes: options, a recommendation, and the one decision
  the intent steward must make. Returns needs; never re-routes; read-only.
- **`converge:proposal-drafter`** — authors a proposal beside a locked contract
  and stops. Never edits the locked file, never self-ratifies.
- **Skills** (load on demand for a *procedural* "how do I…" ask):
  - `seam-test` — is this a seam? does it warrant a contract?
  - `proposing-a-change` — how to author a proposal beside a locked contract
  - `freeze-bar` — the four-condition DRAFT → locked checklist
  - `ledger-disposition` — the ledger disposition vocabulary + row schema
  - `lane-brief` — honesty gate, file-ownership split, real lanes (never in-session sub-agents), evidence the evaluator can see
- **`hooks-candidate-guard`** — the ratchet's teeth. A `tool:pre` hook, on by
  default, that structurally denies a direct write/edit/patch (or a bash
  write-laundering attempt) targeting a locked contract file or `VISION.md`.
  Changes land only via a ratified proposal beside it. See
  `modules/hooks-candidate-guard/README.md` for the full contract, the
  config surface, and documented non-coverage.
- **Recipe** — one, `@converge:recipes/seed-reconcile.yaml`: SEED + standing
  RECONCILE. Derives/refreshes the ledger from a target repo's contracts,
  detects bidirectional drift, files GAP/VIOLATION tracker items. Spec of
  record: `docs/design/mechanism-spec.md` §4.2. Its steps use only the lean
  base's helpers (`anchors:explorer` for read-only intake) and Converge's own
  `reconciler` for every write.

## The authoritative spec

The ratified protocol is `docs/PROTOCOL.md` (v2). The starter conformance
ledger format is `docs/LEDGER-FORMAT.md` (a DRAFT convention, not a contract).
These docs are the source of truth; everything in this bundle quotes or points
to them rather than restating them.

## Status

**Live**: 4 agents (protocol-authority, reconciler, negotiator,
proposal-drafter), 5 skills, candidate-guard hook, 1 recipe (seed-reconcile).

See `README.md` for what ships and where everything lives.
`docs/design/mechanism-spec.md` is a dated design snapshot, read as history.
