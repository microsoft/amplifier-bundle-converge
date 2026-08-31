# Converge — awareness

This work runs under the **Converge** protocol: vision-first, contract-driven
development. Direction changes land in the contract FIRST. Work is derived from
the gap, never invented. The **ratchet** (conformance ledger + standing
reconcile) refuses silent drift in either direction.

**The stack** (each layer governed by the one above it):
Strategy → Vision → Contracts → Ledger → Lanes.

**Owner attention budget — the owner is in the loop for exactly four things:**
1. Ratifying vision and contract changes (including FROZEN stamps).
2. Irreversible or destructive calls.
3. Verification only a human or a device can perform.
4. Priority and kill decisions.

Anything else that reaches the owner is a protocol defect — file it as one.

**Routing — you (the root session) are the only router.** Route by the *shape*
of the ask:
- **"Am I allowed / does this conform / what does the protocol say?"**
  (interpretive) → delegate to **`converge:protocol-authority`** (it carries the
  full spec). This covers conformance, the stack, the phases, the lifecycle, the
  Freeze Bar, the amendment protocol, and the owner attention budget.
- **"How do I author / perform X?"** (procedural) → load the matching skill:
  `seam-test`, `candidate-amendment`, `freeze-bar`, `ledger-disposition`,
  `lane-brief`.
- **Worker agents return needs; they do not re-route.** When a spawned agent
  (`reconciler`, and later `negotiator` / `amendment-drafter`) reports it needs
  a conformance ruling or a seam judgment, *you* make the call
  (protocol-authority / skill) and feed the answer back — the agent does not
  delegate on its own.

**Source of truth:** `@converge:docs/PROTOCOL.md` (ratified v2) and
`@converge:docs/LEDGER-FORMAT.md` (starter ledger convention). Quote or point;
never paraphrase them into drift.

**Status:** increments 1–4 shipped — the agent roster is complete. Knowledge
layer + `converge:reconciler` (ratchet) + `hooks-candidate-guard` (on by
default, structurally enforcing PROTOCOL.md §5) + `converge:negotiator`
(Phase 1 NEGOTIATE: evidence → decision-level minutes; returns needs,
read-only) + `converge:amendment-drafter` (authors `CANDIDATE-<topic>.md` and
stops; the guard escape hatch's upstream author). All three phase-loop recipes
(`@converge:recipes/seed-reconcile.yaml`, `encode.yaml`, `full-wave.yaml`) ship
in `recipes/` and are live-verified (spec of record: mechanism-spec §4)
in mechanism-spec §4. The orchestration mode is deferred by decision.
