# Seam: Composition

**Status:** DRAFT

---

## Core

1. **Seam-Test Justification** — This surface passes the seam test: two install paths (bundle use converge; --app behavior) and every recipe execution breaks if composition changes silently.

2. **Composition Stack** — Converge's root bundle.md composes its session scaffold from the anchors bundle (`git+https://github.com/microsoft/amplifier-foundation@main#subdirectory=bundles/anchors/bundle.md`): session orchestration, core tools, tool-delegate/tool-skills/tool-recipes, and six thin anchors agents. The foundation ROOT bundle is NOT included anywhere. Frame as CALIBRATED MIDDLE GROUND with measured evidence: foundation over-delivers (~34KB always-on root floor, ~56KB per-agent-spawn tax via common-agent-base chain); bare anchors under-delivers for converge's recipes (no writing/building executors guaranteed composed).

3. **Recipe Agent References** — Recipe executor steps reference anchors agents only: anchors:explorer (read-only steps: seed-reconcile load-contracts; encode intake-decisions; full-wave parse-authorized-items), anchors:builder (writing/implementation: encode draft-vision-contracts, apply-ratified-edits; full-wave execute-items), anchors:git-ops (git steps: encode commit-encoded; full-wave merge-lanes). No recipe references foundation agents.

4. **Converge-Local Agent Preamble** — Converge's four agents carry a converge-local preamble (context/shared/agent-base.md): honest-stopping evidence protocol, git commit footer with Amplifier co-author attribution, file:line citation convention—nothing else. Zero @foundation: mentions remain in composed surfaces (bundle.md, behaviors/, agents/, context/).

5. **Host Requirement** — Stated plainly in README: recipes resolve only from a composed session (recipe-only agent scoping does not exist in the engine—live-verified twice). Recipes REQUIRE converge's root composition or an anchors-family host on the --app path.

6. **Work-Tracker Behavior** — Include is unchanged (independent of foundation; supplies reconciler's work_* tools on both paths).

---

## Backlogged

| Item | Promotion Trigger |
|------|---|
| Recipe-only agent scoping | Recipe engine ships per-recipe agent registration |
| Wave-highway integration | full-wave's EXECUTE launching durable parallel lanes via external lane orchestrator with converge lane-briefs |

---

## Conformance

**Verification Gates:**

- Grep gates: zero '@foundation:' mentions in bundle.md/behaviors/agents/context; zero 'foundation:' agent references in recipes/*.yaml; bundle.md includes anchors bundle URI
- Live composition check: `amplifier run --bundle converge` resolves anchors:explorer AND converge:reconciler
- Encode recipe end-to-end green on a fixture repo

---

## Reserved

- The converge:exec-* agent namespace (held in case anchors executors prove insufficient and converge must own executor bodies)

---

## Changelog

- v1 drafted 2026-09-01 (provenance: ratified protocol e458d40, full session decision record, negotiator Phase-1 minutes, live probe evidence)
