# Composition Contract — v1 (DRAFT — content owner-ratified 2026-09-02)

**Who builds against this:** everyone who installs Converge, by either path, and
every automated step that expects certain helpers to be present. The most
technical of the four contracts; each clause ends with what it means for you.

## Purpose

Converge must sit lightly on a host — fast sessions, no bloat, and never a side
effect on work that isn't its own — while guaranteeing its automated steps find
the helpers they need.

## Core (the teeth)

1. **A lean base, never a heavy one.** Converge assembles its session from the
   small standard base (the *anchors* bundle in the Amplifier foundation
   repository): session basics, everyday tools, six lightweight helpers. The full
   foundation package appears nowhere. *For you:* sessions stay fast and cheap.
2. **Automated steps use only the lean base's helpers** — a reader for read-only
   steps, a builder for writing, a git helper for version control. *For you:*
   no step secretly depends on the heavy package.
3. **Its own helpers carry a small local rulebook** — stop honestly when a thing
   cannot be proven; sign commits; cite locations — and borrow nothing else.
4. **Automated steps bring their own helpers.** The recipe names the bundles
   that ship each helper it uses, pinned to a release, and resolves helpers only
   from that list — never from whatever session happens to run it. *For you:*
   Converge's recipe runs on any host, and the README says so in one sentence.
5. **The shared work queue rides on both install paths,** so the contract
   checker can file and read work anywhere.
6. **Nothing touches the tools of other work in your session.** A setting that
   stripped tools from every helper in every session was measured in isolation
   on 2026-09-02, confirmed with a control, and removed. Converge's helpers keep
   their limits as stated rules until per-role enforcement exists upstream; the
   guard on locked contracts remains the enforcement that matters.
7. **The guard recognizes both proposal names** — `<contract>.vN-candidate.md`
   and the legacy `CANDIDATE-*.md` — and refuses every other write to a locked
   contract, by person or agent.

## What v1 deliberately does NOT freeze

- Enforced per-role tool limits — promoted when upstream #388 lands.
- A tagged release of the lean base — promoted when the foundation repository
  tags a release that ships `bundles/anchors`; until then Core 4's pin of the
  lean base is its `main` branch, recorded in PINS.md.
- The companion app as its own product — see Surface.

## Conformance kit asserts

- No reference to the heavy package in anything loaded; no automated step names
  a heavy-package helper; the lean base is named where Converge assembles; no
  session-wide tool-stripping setting anywhere.
- The recipe declares `schema_version: 2` and a `dependencies` list naming every
  helper it uses under the bundle that ships it; `recipe-runner validate`
  reports schema_version 2 with no errors; a plan resolves every named helper.
- A Converge session reaches a lean-base helper and one of Converge's own.
- After installing Converge beside other work, a helper in an unrelated session
  keeps its shell, delegation, and skills tools.
- The guard denies a write to a locked contract and admits a `*.vN-candidate.md`
  beside it.

## Reserved / open questions (NOT frozen)

- A namespace for Converge's own worker helpers, should the lean base's prove
  insufficient.

## Changelog

| Date | Change | Evidence |
|---|---|---|
| 2026-09-04 | Amended (still v1, DRAFT — ratified by the steward, word: "ratified … merge it", PR #25): clause 4 replaced — automated steps bring their own pinned helpers instead of borrowing the host session's; the "when the engine supports it" item leaves the not-frozen list; a new not-frozen item tracks a tagged lean-base release; a kit assert covers the manifest | `recipes/seed-reconcile.yaml` v1.4.0 failed on a non-anchors host with "Agent 'anchors:explorer' not found in configuration" (2026-09-04); the engine now supports self-declared helpers (amplifier-recipe-runner 0.1.0, `recipe-runner validate` → schema_version 2, ok) |
