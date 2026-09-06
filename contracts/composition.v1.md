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
4. **The host requirement is one sentence in the README.** A step that declares
   no helpers of its own can use only those present in the session it runs in,
   and needs Converge's own full setup or a host on the same lean base; a step
   that declares its helpers resolves them from that closure instead, and asks
   nothing of its host.
5. **One install command is the path an adopter takes.** The README names
   exactly one command as that path — the single command that composes Converge
   onto the session the reader already has — and marks the multi-command
   full-workspace install as the advanced path, saying in one sentence who
   needs it: a host that supplies neither the session base nor the mode
   machinery. Nothing later in the README recommends against the path it just
   named. The shared work queue rides on both, so the contract checker can file
   and read work whichever one was taken. *For you:* you type one line, and
   nothing afterwards tells you that you should have typed the other.
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
- A Converge session reaches a lean-base helper and one of Converge's own.
- After installing Converge beside other work, a helper in an unrelated session
  keeps its shell, delegation, and skills tools.
- The guard denies a write to a locked contract and admits a `*.vN-candidate.md`
  beside it.
- A step that declares its own helpers resolves them from that closure, not
  from the calling session: the recipe validates at `schema_version: 2` and its
  plan names every helper against the dependency that supplies it.
- The README's install section presents exactly one command as the path an
  adopter takes, marks every other path advanced, and nowhere afterwards
  recommends against the path it named.

## Reserved / open questions (NOT frozen)

- A namespace for Converge's own worker helpers, should the lean base's prove
  insufficient.

## Changelog

| Date | Change | Evidence |
|---|---|---|
| 2026-09-04 | Amended (still v1, DRAFT): clause 4's second sentence names the two cases — a step that declares no helpers uses the session's; a step that declares its helpers resolves them from that closure; the "when the engine supports it" item leaves the not-frozen list (condition met); a new not-frozen item tracks a tagged lean-base release; one kit assert added. Proposal: `contracts/composition.v1-candidate.md` (converge-qwk), kept as `docs/workflow/composition.v1-candidate.ratified.md`. Steward's word, verbatim: `ratified, and go ahead w/ that PR, merge it` (PR #25, converge-may). | The recipe failed on a non-anchors host with "Agent 'anchors:explorer' not found in configuration" (2026-09-04); the engine now supports declared helpers — `recipe-runner validate` → schema_version 2, ok; `plan` names both helpers against their suppliers |
| 2026-09-06 | Amended (still v1, DRAFT): Core 5 rewritten — "One install command is the path an adopter takes"; the old promise (the queue rides on both paths) is kept whole as the clause's own second-to-last sentence; one kit assert added, on the README's install section. Proposal: `contracts/composition.v1-candidate.md` (converge-279a), kept as `docs/workflow/composition.v1-candidate.2026-09-06.ratified.md` — dated, because `docs/workflow/composition.v1-candidate.ratified.md` is already the Core 4 archive and overwriting it would erase that record. Steward's word, verbatim: `ratified, please continue` (`docs/workflow/owner-ratifications-2026-09-06.md` round 1). | The README names the `--app` behavior **THE** install path at `:53` and prefers the other path for end-to-end runs at `:93–96`; the stated reason for that preference was made moot by the same commit that wrote it (`49534d6`). One command was measured producing a working manager session with no bundle active — `evaluations/adopter/RESULT.md` S1.1 PASS, S2.2 PASS |
