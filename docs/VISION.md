# Converge Vision

**Status:** DRAFT

---

## End State

Converge is the Amplifier packaging of the ratified vision-first, contract-driven development protocol (docs/PROTOCOL.md v2, RATIFIED 2026-08-29). Teams of humans and AI agents move fast without direction drift: direction lands in ratified contracts FIRST, and work is derived from the contract-vs-reality gap—never invented. The Ratchet (the conformance ledger plus standing reconcile) only lets state move one way, toward the contract; drift in EITHER direction is caught, named, and filed.

---

## Operating Principles

1. **The Stack** — Strategy → Vision → Contracts → Ledger → Lanes. Each layer converges at a different rate: strategy never; vision slowly by evidence; contracts frozen and versioned; ledger continuously; lanes disposable.

2. **The Loop** — INVESTIGATE → NEGOTIATE → ENCODE → SEED → QUEUE → EXECUTE → MERGE+VERIFY → CLOSE, plus standing RECONCILE. This loop is the automated heart the system carries.

3. **Scope by Seam Test** — A change gets a contract if "silent change breaks someone downstream." The axiom: convergent behavior belongs in the contract or it is debt. No third option.

4. **Owner Attention is Rationed** — Exactly FOUR things reach the human, named in full: (1) ratifying vision/contract changes; (2) irreversible or destructive calls; (3) verification only humans or devices can perform; (4) priority and kill decisions. Anything else reaching the owner is a protocol defect.

5. **Lifecycle: DRAFT → FROZEN** — Owner-only Freeze Bar stamp (four conditions per PROTOCOL §5). Frozen clauses change only via CANDIDATE amendments (sibling file, never edit): exact diff, evidence (real cost paid or real failure caught—preference is not evidence), what does NOT change, literal-word ratification.

6. **Mechanism/Policy Split** (the governing rule for every contract in this repo) — This bundle carries the HOW: a stateless mechanism of 4 agents (protocol-authority, negotiator, reconciler, amendment-drafter), 5 skills (seam-test, candidate-amendment, freeze-bar, ledger-disposition, lane-brief), the candidate-guard hook, 3 recipes (encode, seed-reconcile, full-wave), and ratified protocol texts. Each target repo owns the WHAT: its VISION.md, contracts/, ledger, conformance kit, and tracker items.

---

## Deliberately Resists

- Owning any repo's tracker, vision, contracts, or ledger
- Ratifying anything (only the owner ratifies, in literal words)
- Manufacturing contracts for seamless repos
- Automating the owner's four decisions (automating priority/kill would be a protocol defect)
- Prose-only capability claims (rules are structural: the guard denies frozen-file writes; spawn policy strips tools that prose claims are absent)
- Heavyweight host dependence (calibrated middle ground between foundation's bloat and anchors' minimalism)
- Historical narrative in load-bearing docs (spec of record stays always-true; design records carry point-in-time banners)

---

## Named Residual

The lane launcher/orchestrator itself is OUTSIDE this bundle. full-wave's EXECUTE writes a brief per authorized item, hands each to an external launcher that runs it as a tmux `/goal` session in its own worktree and branch, and reads completion back from the lane's terminal marker and branch tip; it never executes lane work in session, and it fails loud rather than falling back to agent fan-out. What this bundle does not own is lane scheduling: worker-session custody, refill-on-drain, cross-session reclaim. The seam is declared, the handoff is real, and the wave resumes at MERGE from what the lanes actually committed.

*(2026-09-02: narrowed. EXECUTE was previously bounded in-session fan-out and the residual was the whole of durable multi-lane execution; it is now the launcher alone.)*

---

## Evidence Spine

- 6/6 green evaluation run in isolated environments
- Guard probes T1-T6 green (including delegated agent's write to frozen contract DENIED)
- Full 4-gate wave run
- During own final test, system caught its author freezing a contract improperly

---

## Doc Contract

Learners navigate: PROTOCOL.md → README → docs/design/mechanism-spec.md → presentation deck. Spec of record is retconned always-true; behavioral-model and guard-spec carry point-in-time banners.

**Thin Pointer to Governing Contracts**: contracts/composition.v1.md
