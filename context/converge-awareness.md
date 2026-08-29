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

**Routing:**
- For any question about protocol conformance, the stack, the phases, the
  lifecycle, the Freeze Bar, the amendment protocol, or the owner attention
  budget → delegate to **`converge:protocol-authority`** (it carries the full
  spec).
- For a specific procedure → load the skill: `seam-test`,
  `candidate-amendment`, `freeze-bar`, `ledger-disposition`, `lane-brief`.

**Source of truth:** `@converge:docs/PROTOCOL.md` (ratified v2) and
`@converge:docs/LEDGER-FORMAT.md` (starter ledger convention). Quote or point;
never paraphrase them into drift.

**Status:** knowledge layer only. The phase-loop recipes, orchestrator mode,
enforcement hooks, and negotiator/reconciler agents are not built yet.
