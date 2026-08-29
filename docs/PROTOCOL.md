# Vision-First, Contract-Driven Development — Protocol v2

**Status:** RATIFIED — 2026-08-29, by owner, as written.
**Supersedes:** `drumbeat-team-ci/CONTRACT-DRIVEN-WORKFLOW.md` (v1, 2026-08-25).
**Sources:**
- `foundation:docs/PER_REPO_CONVENTIONS.md` — the VISION.md convention this extends
- `cortex-core` — contract-first governance loop; ~40-lane integration evidence; convergent/divergent change pricing
- `drumbeat-team-ci` — the phase pipeline, proven end-to-end twice (once at 18 items, once 3 hours zero-touch)
- `better-attractor` — conformance matrix, CANDIDATE amendment protocol, disposition vocabulary, 40-hour session forensics
- `~/dev/ai-context/workflows/` — the cross-session corpus these were distilled from

The owner and the orchestrator negotiate at the contract level. Work is
derived, never invented: the gap between repo reality and the contracts
becomes tracker items; autonomous lanes close them; a standing conformance
audit keeps the gap ledger honest between waves. Direction changes land in
the contract FIRST. The owner's attention is spent only at the contract
layer — everything below it that reaches the owner is a protocol defect.

---

## 1. The stack

Five layers. Each converges at a different rate; each is governed by the
layer above it.

| Layer | Artifact | Converges? | Changed by |
|---|---|---|---|
| **Strategy** | the negotiation loop itself | never — permanently open | owner judgment |
| **Vision** | `docs/VISION.md`, one per repo | slowly | evidence-gated, owner-ratified amendment |
| **Contracts** | `contracts/<seam>.v<N>.md` | frozen between amendments | CANDIDATE → ratification |
| **Ledger** | conformance rows, clause-granular | continuously re-derived | machine checks + filed rows |
| **Lanes** | briefs, worktrees, DONE.md | disposable | claimed and closed |

The Strategy layer is named so we stop pretending it's absent: it is the
open, gap-driven, non-converging loop that this whole protocol *is*. A
human occupies its executor seat today. Everything below it exists to make
that seat cheap — and eventually mechanizable.

---

## 2. The pillars

Settled invariants. Each was converged on independently by at least two
sessions; where noted, the failure was *measured*, not hypothesized.

1. **Vision is never status.** The page states the destination as though
   already true. A page that must be edited when a feature ships is a
   status report wearing a vision's name. Shipped/in-flight/sequencing
   live in the tracker.
2. **A self-report is never proof.** Fabricated PASS verdicts were measured
   in two independent sessions. An agent's or monitor's verdict is a raw
   observation; promotion to *proven* requires an artifact check the
   orchestrator runs itself.
3. **Amendments are CANDIDATE artifacts, never direct edits.** Lanes and
   orchestrators may propose; only the owner ratifies, in so many words.
4. **Freeze requires a discriminating example.** A conformance kit must
   include at least one good/bad fixture pair that actually discriminates —
   prose alone freezes nothing.
5. **A missing artifact is a real result.** Honest stopping — `N/A` with a
   reason, `BLOCKED.md` with a cause — always beats fabricated compliance.
   The enemy is the successful-looking run that did nothing.

---

## 3. Artifacts and their scope

The v1 corpus used three contract granularities without reconciling them.
v2 resolves this: they were never competing scopes — they are three
different artifacts.

### 3.1 VISION.md — one per repo

Anatomy (unchanged from the PER_REPO_CONVENTIONS genre, hardened by use):

- The desired end state, written as though already true.
- Operating principles — small, numbered, quotable.
- **What this repo deliberately resists** — required section.
- Dated changelog of ratified amendments. Nothing else.
- Where a governing contract exists, VISION.md is a *thin pointer* to it,
  not a restatement of it.
- A repo with no governing contract does not manufacture one.

### 3.2 Contracts — one per seam

**A seam is a surface someone outside this repo's own commits depends on.**
The test: *if this changed silently, who breaks?* If the answer names
anyone beyond this repo — a sibling client, another team, an automation
consuming a file format, a future machine executor — it is a seam and gets
a contract. An experience class is a seam (cortex's
`client-experience.v1`). A file format is a seam (drumbeat's
`automation-file.v1`). An internal mechanism is not a seam; it gets tests,
not a contract.

Contract anatomy: **Core** (frozen, numbered invariants — kept small) ·
**Backlogged** (candidate clauses with *named promotion triggers*, the
alternative to premature version bumps) · **Conformance** (fixtures, checks)
· **Reserved** (namespace explicitly held) · **Changelog** (dated, ratified
entries only).

Where a contract governs multiple implementations, it carries a
feature × surface matrix with three values: **REQUIRED** (a gap worth
filing), **IDIOM** (platform latitude — may exceed the contract in idiom,
never in features), **EXCLUDED** (deleted rather than built). A capability
that exists on one surface and nowhere else is either convergent behavior
that belongs in the contract, or it is debt. There is no third option.

### 3.3 The conformance ledger — clause-granular, standing

Rows are *derived from* contracts, one per checkable clause, machine-read
(YAML or equivalent) and CI-executable. Each row carries a disposition:

| Disposition | Meaning | Consequence |
|---|---|---|
| `CONFORMS` | check passes | none |
| `GAP` | REQUIRED clause, no implementation | tracker item |
| `VIOLATION` | implementation contradicts a frozen clause | tracker item, or CANDIDATE amendment if evidence says the clause is wrong |
| `OPEN-PINNED` | undecided call; current behavior asserted by a check *without forging a decision* | ledger row, revisited at negotiation — an undecided call is a ledger row, not a vision |
| `NOT-ASSERTABLE` | no machine check possible; judgment-only, named as such | reviewed at cadence, never silently trusted |
| `EXCLUDED` | contract forbids it | presence is a violation |

**Drift is bidirectional.** Moving away from a frozen clause is drift.
Silently moving *back* toward spec from a pinned behavior is also drift —
any change in the spec↔implementation relationship not traceable to a
ratified amendment or a filed work item files a ledger row.

---

## 4. The loop

v1's pipeline survives with one structural change: RECONCILE stops being a
phase you can skip and becomes a standing audit. The phase slot it occupied
becomes SEED — the first population of the ledger.

```
Phase 0  INVESTIGATE   never negotiate from memory — disposable explorers
                       gather evidence first (self-contained briefs)
Phase 1  NEGOTIATE     owner + orchestrator at decision level; minutes,
                       not documents — options + recommendation per call
Phase 2  ENCODE        VISION.md + contracts written and COMMITTED before
                       any implementation
Phase 3  SEED          first reconciliation: repo vs contract populates
                       the conformance ledger
Phase 4  QUEUE         ledger rows become tracker items with
                       clause-quoting acceptance criteria
Phase 5  EXECUTE       autonomous lanes claim and close items
                       (worktree-isolated; honesty gate in every brief)
Phase 6  MERGE+VERIFY  orchestrator merges; every verdict promoted only by
                       its own artifact check
Phase 7  CLOSE         freeze-bar report; residuals named honestly

Standing RECONCILE     conformance runs on every merge and on schedule;
                       drift in either direction files ledger rows; QUEUE
                       draws from the ledger, not from memory
```

The v1 diagnosis stands as the justification: the one measured tracker
bypass happened "because reconcile wasn't mechanized." Anything that
depends on someone remembering to run it will eventually not run.

### Lane discipline (imported intact from cortex-core, all measured)

- Lane briefs carry an **honesty gate**: name what "not proven" looks like
  before work starts.
- Two lanes in one repo require an explicit **file-ownership split**.
- Completion is knowable only from git artifacts (`DONE.md`, commits) —
  never from pane or session liveness.
- **Inherited-from-fork artifacts are the #1 false signal.** Check
  provenance (commit, mtime) before crediting any artifact as this lane's
  work.
- Health endpoints are not a working system. Numbers reported are real or
  absent.

---

## 5. Lifecycle

### DRAFT → FROZEN: the Freeze Bar

All four, no substitutions; only the owner stamps FROZEN:

1. The spec is written.
2. A machine-checkable conformance kit exists, with at least one
   discriminating good/bad fixture pair.
3. At least one real implementation passes it.
4. A worked example exists end-to-end.

### Amending a frozen clause: the CANDIDATE protocol

A proposal is a sibling file (`CANDIDATE-<topic>.md`), never an edit. It
carries: the exact diff · evidence citations (a real cost paid or a real
failure caught — a preference is not evidence) · an explicit **"what does
NOT change"** section · a ratification ask. The owner answers with the
literal word: *ratified* / *ratified as edited* / declined-with-reason.
On ratification the edit lands with a dated changelog entry.

**Change pricing** (from cortex-core): a *convergent* change — toward the
contract — is cheap; just do it and let the ledger confirm. A *divergent*
change owes an amendment-with-evidence before implementation, or it is
debt on arrival.

### Version bumps

`v<N>` increments only when frozen Core clauses are removed or made
incompatible — i.e., when existing conformant implementations would break.
Everything else is an amendment. **Backlogged sections with named promotion
triggers exist precisely so that version bumps are rare.** A bump proposed
without a migration note for every known implementation is declined on
form. Lanes mid-flight against a superseded clause finish against the
version they were briefed on; the ledger files the delta as new rows.

---

## 6. The owner attention budget

The owner is in the loop for exactly four things:

1. **Ratifying** vision and contract changes (including FROZEN stamps).
2. **Irreversible or destructive calls.**
3. **Verification only a human or a device can perform.**
4. **Priority and kill decisions.**

Never for lane monitoring, merge mechanics, routine gap-filing, or status
assembly. Anything outside these four that reaches the owner is a protocol
defect — file it as one, against the protocol.

---

## 7. What this protocol deliberately resists

- Editing a vision page into agreement with a drifted tree.
- Status, progress, or sequencing in vision documents.
- Self-ratified amendments — by lanes *or* by the orchestrator.
- One-shot reconciliation and remembered audits.
- LLM judgment where a machine check is possible; unlabeled judgment where
  it is not (`NOT-ASSERTABLE` exists so judgment is named, never smuggled).
- Manufacturing contracts for repos with no seam.
- Version bumps used to dodge amendment evidence.
- Trusting a monitor's verdict, a health endpoint, a pane's liveness, or an
  inherited artifact.
- The owner's attention anywhere below the contract layer.

---

## Changelog

- **2026-08-29 — RATIFIED.** Owner ratified v2 as written.
- **2026-08-26 — v2 DRAFT.** Synthesized from cortex-core, drumbeat-team-ci,
  and better-attractor session evidence plus the `ai-context/workflows`
  corpus. Structural changes from v1: RECONCILE becomes a standing audit
  (phase slot renamed SEED); contract scope resolved as one-per-seam with
  the ledger as a distinct clause-granular layer; disposition vocabulary
  adopted (`OPEN-PINNED`, `NOT-ASSERTABLE`); Strategy layer named; owner
  attention budget made an enumerated contract with defect-filing teeth.
  Awaiting owner ratification.
