# Behavioral Model — `converge`

> **Snapshot — 2026-08-29.** A design-time record of what was intended then, kept
> as history. It is not current law and is not maintained against the shipped
> bundle: the rules are `docs/PROTOCOL.md`, the promises are `contracts/`, and
> what actually ships is `README.md`. Where this document and those disagree,
> they win. Known drift since: the `encode` and `full-wave` recipes were retired
> (`seed-reconcile` is the one recipe); `amendment-drafter` is now
> `proposal-drafter`; the bundle assembles on the lean `anchors` base, so read
> any heavy-package helper named below as its lean equivalent.

> Derived **solely** from `docs/design/mechanism-spec.md` (via structured extraction).
> Nothing in this document is inferred beyond that source. Where the spec is silent,
> this document says so rather than filling the gap. Section references (§n) are to
> the mechanism spec / `PROTOCOL.md` as cited in the extraction.

---

## 1. Overview

**Bundle:** `converge`

**Purpose (verbatim from spec):** Vision-first, contract-driven development. The owner and the orchestrator negotiate at the contract level; work is derived from the gap between repo reality and the ratified contracts, never invented; a standing conformance ledger (the "ratchet") refuses silent drift in either direction. Direction changes land in the contract FIRST. The owner's attention is spent only at the contract layer (§6).

**Dependencies (direct, as stated):**

| Dependency | Kind | Notes |
|---|---|---|
| `git+https://github.com/microsoft/amplifier-foundation@main` | bundle dependency | provides `explorer`, `git-ops`, `file-ops`, recipes runtime, common bases |
| `work-tracker` | runtime tool | **reused, not owned** (§C) |

**Installation path:** `amplifier-bundle-converge/` — the ratified spec and ledger convention live under `docs/`.

### Component inventory

| Type | Count | Names (build state) |
|---|---:|---|
| Context files | 1 | `converge-awareness` (AS-BUILT) |
| Modes | 1 | `converge-orchestration` (**CANDIDATE** — OPEN QUESTION #1) |
| Agents | 4 | `protocol-authority` (AS-BUILT); `negotiator`, `reconciler`, `amendment-drafter` (PLANNED) |
| Skills | 5 | `seam-test`, `candidate-amendment`, `freeze-bar`, `ledger-disposition`, `lane-brief` (all AS-BUILT, all inline) |
| Recipes | 3 | `encode`, `seed-reconcile`, `full-wave` (all PLANNED) |
| Hooks | 1 | `hooks-candidate-guard` (**CANDIDATE** — OPEN QUESTION #2) |

**Build-state distribution:** 6 components exist as built (1 context file, 1 agent, 5 skills… counting the context file as a component: 6 AS-BUILT); 6 are PLANNED (3 agents, 3 recipes); 2 are CANDIDATE and under active evaluation (1 mode, 1 hook). The model below describes *specified* behavior; it does not assert that PLANNED/CANDIDATE components run today.

---

## 2. Tool Governance

Only one mode is specified, and it is a CANDIDATE. The matrix below is the complete tool governance the spec defines.

### 2.1 Tool availability matrix

| Tool / operation | `converge-orchestration` (CANDIDATE) |
|---|---|
| `read_file` | safe |
| `grep` | safe |
| `glob` | safe |
| `work_list` | safe |
| `work_status` | safe |
| `write_file` | warn |
| `edit_file` | warn |
| git-ops destructive operations | confirm |
| `work_resolve` on contract-layer items | confirm |
| *(nothing)* | block — the block list is empty |

**Default action for unlisted tools:** `proceed (general)`. Any tool not named above is permitted without prompt when the mode is active.

**When no mode is active** (the current default, since the mode is a CANDIDATE that may never be adopted): the spec defines no tool governance at all. All governance in that configuration is convention carried by the agents' and skills' behavioral directives — see §9.

### 2.2 The per-path gap (stated in the spec, not inferred)

The spec records a known limitation of this matrix: **tool policies are per-tool, not per-path.** A mode therefore cannot block writes to `contracts/**` or `docs/VISION.md` specifically while allowing writes elsewhere. `write_file`/`edit_file` are either warn-everywhere or block-everywhere.

This is the explicit motivation for OPEN QUESTION #2 (`hooks-candidate-guard`, §2.4 / §7 of this document), which inspects the *target path* and *current phase* — the two things a per-tool policy cannot express (§5.1). Cross-reference §6.1 (owner attention) and verification objective **D5**.

### 2.3 Limitation: what a spec cannot settle

Two governance properties **cannot be derived from this document or its source spec**:

- **Delegation necessity** — whether the root session *must* delegate to an agent to accomplish something (versus being able to do it directly) depends on the resolved tool matrix of the root session *and* every agent, after transitive bundle composition. The spec states direct dependencies and per-agent `tool_requirements` only.
- **Composition loopholes** — whether a tool blocked or confirm-gated in `converge-orchestration` is reachable unrestricted through a delegated agent, a foundation agent (`foundation:file-ops`, `foundation:git-ops`, `foundation:explorer`), or a recipe step depends on resolved policies across the whole composed bundle graph. `converge-orchestration` has an **empty block list**, so no tool is hard-denied at the mode layer; whether any *effective* denial exists elsewhere is not determinable here.

Both require resolving the actual composed bundle, not reading the spec. Flagged, not answered. See §9.

---

## 3. Mode Behaviors

### 3.1 `converge-orchestration` — **CANDIDATE (OPEN QUESTION #1)**

| Property | Value |
|---|---|
| Purpose | Keep loop phase discipline (§4) and reserve owner attention (§6) while a wave runs |
| Status | CANDIDATE — the alternative under evaluation is **no mode at all**: the awareness pointer plus agent/skill routing may be sufficient |
| Tool policy | see §2.1 |
| Default action | `proceed (general)` |
| Companion skill | *none specified* (the spec's `companion_skill` field is empty) |
| Entered | at wave start (**SEED**) |
| Exited | at **CLOSE** |

**Behavioral directives:**

1. **Enforce phase order** — no implementation writes before ENCODE is committed (§4 Phase 2; relates to verification objective **D5**).
2. **Route owner-facing moments to exactly the four §6 items** — treat any fifth as a *protocol defect* (§C).
3. **Acknowledge the per-path gap** — tool policies are per-tool, not per-path, so this mode cannot cleanly protect `contracts/**` or `docs/VISION.md`. This is why `hooks-candidate-guard` exists as OPEN QUESTION #2 (cross-reference §6.1 and §2.2 above).

**Open decision the model must resolve:** whether the mode earns its cost. Directive 1 (phase order) and directive 3 (the per-path gap) both point at enforcement the mode *cannot fully deliver* — which is the substance of the mode-vs-no-mode question. If the hook is adopted, directive 1's enforcement moves to the hook, and the mode's remaining unique contribution is the confirm-gate on git-ops destructive ops and `work_resolve` on contract-layer items.

---

## 4. Agent Behaviors

Four agents. One is built; three are planned. All four are specified with `model_role: [reasoning, general]`.

### 4.1 `protocol-authority` — **AS-BUILT**

| Property | Value |
|---|---|
| Purpose | THE single authority and **context sink** for the ratified protocol. Answers interpretive/conformance questions — "what does the protocol say?" and "does this conform?" — by quoting and citing `PROTOCOL.md` / `LEDGER-FORMAT.md` |
| Model role | reasoning, general |
| Operating modes | `answer-conformance` |
| Tool requirements | `read_file`, `grep` |
| Context loading | `@converge:docs/PROTOCOL.md` · `@converge:docs/LEDGER-FORMAT.md` · `@foundation:context/shared/common-agent-base.md` |
| Exit condition | cited answer delivered; **no repo mutation** |

**Trigger conditions:** any question about protocol conformance · the stack and which layer governs which · the loop phases · the lifecycle (Freeze Bar, CANDIDATE protocol, version bumps, change pricing) · the owner attention budget and whether something reaching the owner is a protocol defect · the pillars and the "no third option" axiom.

**Behavioral directives:**

- Owns **interpretive** questions ("what does the protocol say / does this conform"). **Procedure execution** ("how do I perform X") routes to the skills, not here (verification objective **D1**).
- Quote the governing clause and cite its section; **if the spec is silent, say so — never invent a rule.**
- Does **not** ratify and does **not** decide priority/kill — those are owner acts (§6). Reports what the protocol says.
- Does not act or execute procedures.

**Failure modes the model must exercise (D1):**

| Failure mode | Consequence |
|---|---|
| (a) Root **over-delegates** trivial procedure calls here | The five skills become dead weight — every "how do I…" becomes an agent round-trip |
| (b) Root **never consults** here | Conformance judgment gets silently skipped — the ratchet stops ratcheting |

**Heavy-doc placement tension (D4):** this agent currently carries **both** `PROTOCOL.md` and `LEDGER-FORMAT.md`. The model must test whether carrying the ledger format **dilutes its conformance answers**, versus letting the `ledger-disposition` skill / `reconciler` agent own the ledger detail. Cross-reference §4.3 (`reconciler` loads `LEDGER-FORMAT.md` in full) and §5.4.

### 4.2 `negotiator` — **PLANNED (not built)**

| Property | Value |
|---|---|
| Purpose | Phase 1 **NEGOTIATE** (§4). Turns Phase-0 investigation evidence into decision-level options + a recommendation per open call — *"minutes, not documents."* Surfaces the calls the owner must make; does not make them |
| Model role | reasoning, general |
| Operating modes | `negotiate` |
| Tool requirements | `read_file`, `grep` |
| Context loading | Phase-0 investigation briefs · a **thin** negotiation-relevant slice of `PROTOCOL.md` §1/§4 · consults `converge:protocol-authority` for conformance calls |
| Exit conditions | per-call options + recommendation delivered as minutes; **stops for the owner to decide** |

**Trigger conditions:** entering NEGOTIATE with investigation briefs in hand · owner asks "what are my options here?" at the contract level.

**Behavioral directives:**

- Produce options + a recommendation for each open call; keep it to **minutes, never a document** (§4 Phase 1).
- **Never negotiate from memory** — requires Phase-0 evidence first (§4 Phase 0).
- Does **not** ratify — decisions are owner acts; the negotiator only frames them (§C anti-scope; §6.1).
- Does **not** manufacture a contract for a repo with no seam (§3.2, §7; §C). Defers seam judgment to the `seam-test` skill (§5.1).
- Delegates deep conformance questions to `protocol-authority` rather than carrying the full spec itself (relates to **D4**) — hence the deliberately *thin* context slice.

### 4.3 `reconciler` — **PLANNED (not built)**

| Property | Value |
|---|---|
| Purpose | **SEED** (first ledger population) and the engine of standing **RECONCILE** (§4). Derives clause-granular ledger rows from contracts vs repo reality per `LEDGER-FORMAT.md`, assigns dispositions, detects **bidirectional** drift (away from spec AND silent movement back toward spec both file rows — §3.3) |
| Model role | reasoning, general |
| Operating modes | `seed`, `reconcile` |
| Tool requirements | `read_file`, `grep`, `glob`, `bash`, `write_file`, work-tracker (`work_add` / `work_file`), `git` |
| Context loading | `@converge:docs/LEDGER-FORMAT.md` (**full**) · `PROTOCOL.md` §3.3 · the target repo's `contracts/` and `ledger/` |
| Exit conditions | ledger rows written/updated in the target repo · drift rows and GAP/VIOLATION tracker items filed · coverage tripwires pass (LEDGER-FORMAT §6) · stops |

**Trigger conditions:** SEED (first population) · **every merge** · the scheduled audit · "reconcile the ledger" / "has anything drifted?"

**Behavioral directives:**

- Rows are **derived from contracts**, one per checkable clause — **never invent a row no clause backs** (§3.3; LEDGER-FORMAT §2).
- Assign dispositions from the **fixed vocabulary**: `CONFORMS` · `GAP` · `VIOLATION` · `OPEN-PINNED` · `NOT-ASSERTABLE` · `EXCLUDED`; `DIVERGED` **for external contracts only** (LEDGER-FORMAT §3).
- Every `GAP`/`VIOLATION` row **files a tracker item into work-tracker** and carries a live work ref — *a red row without a filed item is a ledger that lies* (LEDGER-FORMAT §2). work-tracker is authoritative; the reconciler files into it, never replaces it (§C).
- **Invokes the target repo's own conformance kit** (`pytest -q` or equivalent) to run checks; does not reimplement or own the checks (§C; LEDGER-FORMAT §1). This is why `bash` is in its tool requirements.
- Honors the **SYNC row**: a contract-hash mismatch triggers a mandatory full-ledger re-review, **never a silent hash bump** (LEDGER-FORMAT §4).
- **A self-report is never proof** (pillar 2): promotes a check to "passing" only by running the artifact itself.

This is the only agent with write + bash + git + tracker authority — it is the bundle's one mutating agent.

### 4.4 `amendment-drafter` — **PLANNED (not built)**

| Property | Value |
|---|---|
| Purpose | Authors a `CANDIDATE-<topic>.md` proposal to amend a **frozen** vision/contract clause, **and stops** (§5). The proposal is a **sibling file, never a direct edit** |
| Model role | reasoning, general |
| Operating modes | `draft-candidate` |
| Tool requirements | `read_file`, `grep`, `write_file` |
| Context loading | `PROTOCOL.md` §5 · the frozen document being amended · cited evidence artifacts |
| Exit conditions | `CANDIDATE-<topic>.md` authored **beside** the frozen doc · stops for owner ratification · **does not commit the amendment** |

**Trigger conditions:** a divergent change to a frozen clause is warranted · a measured cost/failure suggests a clause is wrong · "draft an amendment for this."

**Behavioral directives:**

- Emits a `CANDIDATE-<topic>.md` carrying **exactly**: the exact diff · evidence citations (a real cost paid or failure caught — **a preference is not evidence**) · an explicit "what does NOT change" section · a ratification ask (§5).
- **Never self-ratifies** and **never edits the frozen doc** — ratification is an owner-only *literal-word* act (`ratified` / `ratified as edited` / `declined-with-reason`) (§5, pillar 3; §C, §7).
- Applies **change pricing**: convergent changes need no amendment; only divergent changes route here (§5). Defers the pricing call to the `candidate-amendment` skill / `protocol-authority`.

---

## 5. Skill Behaviors

All five skills are **AS-BUILT**, **inline** type, and invoked via `load_skill(skill_name=...)`. None declares a mode association (`mode_association` empty for all five) and none declares a delegation pattern — they are knowledge-layer procedures, not orchestrators. Verification objective **D2** covers whether their trigger phrasings actually fire.

| Skill | Purpose (§ref) | Fires on | Feeds |
|---|---|---|---|
| `seam-test` | Decide seam vs internal mechanism → whether a contract is warranted (§3.2) | "is this a seam?", "does this warrant a contract?", "should this get a contract or just tests?" | `negotiator` |
| `candidate-amendment` | How to author a CANDIDATE amendment and how to price the change first (§5) | "can I edit this frozen clause?", "how do I change the contract?", "draft an amendment" | `amendment-drafter` |
| `freeze-bar` | The four-condition DRAFT→FROZEN checklist + discriminating-fixture requirement (§5, pillar 4) | "can we freeze this?", "is this ready to stamp FROZEN?", conformance-kit review | CLOSE phase / owner ratification |
| `ledger-disposition` | Assign the right disposition to a ledger row; row schema, SYNC row, coverage tripwires, bidirectional drift (§3.3; LEDGER-FORMAT §2–6) | a flipped/red ledger row, "what disposition does this get?", "is this drift?", populating/reviewing the ledger | `reconciler` |
| `lane-brief` | Write and judge autonomous lane briefs: honesty gate, file-ownership split, provenance checks, artifacts-not-liveness (§4; pillars 2 & 5) | briefing an EXECUTE-phase lane, "is this lane actually done?", a successful-looking run that may have produced nothing | full-wave EXECUTE/VERIFY |

### 5.1 `seam-test`

**Workflow phases:** apply the who-breaks test → classify seam vs internal → if seam, a contract is warranted; if not, tests only → apply no-third-option (convergent-behavior-or-debt).

**Directives:** A repo with **no seam does not manufacture a contract** (§3.2, §7; §C). Escalate contract anatomy/versioning to `protocol-authority`.

### 5.2 `candidate-amendment`

**Workflow phases:** price the change (convergent → just do it; divergent → amendment owed) → author `CANDIDATE-<topic>.md` (diff · evidence · what-does-NOT-change · ask) → route to owner for literal-word ratification.

**Directives:** No self-ratification by lanes or orchestrator (pillar 3, §7). **A preference is not evidence.** Feeds `amendment-drafter` when built.

### 5.3 `freeze-bar`

**Workflow phases:** check **all four** conditions (spec written · machine kit with ≥1 **discriminating** good/bad fixture pair · ≥1 real implementation passes · worked example end-to-end) → recommend; **the owner stamps**.

**Directives:** Only the owner stamps FROZEN (§6.1). **Prose alone freezes nothing** (pillar 4). Honest stopping beats stamping around a gap (pillar 5).

### 5.4 `ledger-disposition`

**Workflow phases:** identify the backing clause → choose disposition from the vocabulary → attach required fields (work ref for `GAP`/`VIOLATION`; justification for `OPEN-PINNED`/`NOT-ASSERTABLE`) → check drift direction.

**Directives:** Drift is **bidirectional** (§3.3). `DIVERGED` is **illegal for self-governed contracts** (LEDGER-FORMAT §3). Prefer probes for load-bearing rows (LEDGER-FORMAT §8). Feeds `reconciler` when built.

*Cross-reference D4:* this skill and `protocol-authority` both carry ledger-format knowledge. That overlap is the substance of the heavy-doc placement question in §4.1.

### 5.5 `lane-brief`

**Workflow phases:** write brief (honesty gate + file-ownership split + clause-quoting acceptance) → judge completion **only from git artifacts** → check artifact provenance → verify verdicts by artifact, not self-report.

**Directives:** **Inherited-from-fork artifacts are the #1 false signal** (§4). A self-report is never proof (pillar 2). **A missing artifact is a real result** (pillar 5). Feeds full-wave EXECUTE/VERIFY when built.

---

## 6. Context & Cross-Cutting Concerns

### 6.1 Context files

| File | Path | Always loaded | Est. tokens |
|---|---|---|---:|
| `converge-awareness` | `context/converge-awareness.md` | **yes** (into the root session via `bundle.md`) | ~400 |

**Role — AS-BUILT.** A **thin routing pointer**. It:

- states that the stack exists (**Strategy → Vision → Contracts → Ledger → Lanes**);
- states the **four-item owner attention budget verbatim** (§6);
- routes: protocol-conformance questions → `converge:protocol-authority`; specific procedures → the matching skill.

It contains **no protocol rules of its own** — awareness and routing only. Its design intent is to make the root session **delegate**, never to let the root session answer protocol questions from this file (**verification objective D3**).

### 6.2 Token budget

| Layer | Est. tokens | Notes |
|---|---:|---|
| Always-loaded (`converge-awareness`) | ~400 | the entire standing cost stated by the spec |
| `protocol-authority` context | *not estimated* | `PROTOCOL.md` + `LEDGER-FORMAT.md` + common-agent-base — loaded only on delegation |
| `reconciler` context | *not estimated* | `LEDGER-FORMAT.md` full + `PROTOCOL.md` §3.3 + target repo contracts/ledger |
| `negotiator` context | *not estimated* | deliberately a **thin slice** of `PROTOCOL.md` §1/§4 + Phase-0 briefs |
| `amendment-drafter` context | *not estimated* | `PROTOCOL.md` §5 + the frozen doc + evidence |
| Skills (5, inline) | *not estimated* | loaded on demand via `load_skill` |

**~400 tokens is the only figure the spec provides**, and it is an estimate. See §9.

### 6.3 Delegation chains and routing patterns

The bundle's central routing rule is a **two-way split at the root session**:

```
root session (carries converge-awareness only, ~400 tok)
├─ "what does the protocol say?" / "does this conform?"   → converge:protocol-authority   (interpretive)
└─ "how do I perform X?"                                   → load_skill(<matching skill>)  (procedural)
```

D1 names both ways this split fails: over-delegation (skills go dead) and under-consultation (conformance skipped). D3 names the third: the root answering from the awareness file itself.

**Skill → agent feed chains** (skills are the built layer; agents are their planned successors):

| Skill (built) | Feeds agent (planned) |
|---|---|
| `seam-test` | `negotiator` |
| `candidate-amendment` | `amendment-drafter` |
| `ledger-disposition` | `reconciler` |
| `lane-brief` | full-wave EXECUTE/VERIFY steps |
| `freeze-bar` | full-wave CLOSE step |

**Agent → agent delegation** (only one is specified): `negotiator` → `protocol-authority` for conformance calls, so the negotiator can keep a thin context slice (D4).

**Agent → external tool:** `reconciler` → work-tracker (`work_add`/`work_file`) and → the *target repo's own* conformance kit via `bash`. Neither is owned by this bundle (§C).

**Cross-cutting invariants that appear in more than one component:**

| Invariant | Appears in |
|---|---|
| Only the owner ratifies / stamps FROZEN (literal-word act) | `protocol-authority`, `negotiator`, `amendment-drafter`, `candidate-amendment`, `freeze-bar`, mode directive 2 |
| A self-report is never proof (pillar 2) | `reconciler`, `lane-brief`, full-wave merge-verify |
| A missing artifact is a real result / honest stopping (pillar 5) | `lane-brief`, `freeze-bar`, full-wave close |
| Never invent what no clause backs | `protocol-authority` (rules), `reconciler` (rows), `seam-test` (contracts) |
| Owner attention = exactly four items; a fifth is a protocol defect | `converge-awareness`, mode directive 2, `full-wave` gates |

---

## 7. Recipe Workflows

All three recipes are **PLANNED**.

### 7.1 `encode` — staged

**Purpose:** Phase 2 **ENCODE** (§4). Write `VISION.md` + contracts from ratified negotiation decisions and **commit them before any implementation.**

| Step | Agent | Consumes | Produces |
|---|---|---|---|
| `draft-vision-contracts` | `foundation:file-ops` | negotiation minutes (from `negotiator`) | `VISION.md` + contract drafts |
| — **gate: `ratify-encoded`** — | owner | drafts | ratification (`validates_previous`) |
| `commit-encoded` | `foundation:git-ops` | ratified drafts | committed VISION + contracts |

**Data flow:** `negotiator` minutes → drafts → **owner ratification** → commit. The gate sits *between* drafting and committing, so nothing frozen is committed unratified.

**Relationship to modes:** runs under the candidate `converge-orchestration` mode if adopted; the gate enforces **ENCODE-before-implement** (relates to **D5**).

### 7.2 `seed-reconcile` — flat

**Purpose:** SEED (first ledger population) and standing RECONCILE (§4) — **schedulable and run on every merge**. Derive/refresh ledger rows from contracts vs repo reality; detect bidirectional drift. Mechanized on purpose: *"anything that depends on someone remembering to run it will eventually not run"* (§4).

| # | Step | Agent | Consumes | Produces |
|---|---|---|---|---|
| 1 | `load-contracts` | `foundation:explorer` | target repo | contract inventory + tree evidence |
| 2 | `derive-rows` | `converge:reconciler` | contract inventory | ledger rows with dispositions |
| 3 | `run-conformance` | `converge:reconciler` | ledger rows | check results (**invokes repo kit**) |
| 4 | `file-drift` | `converge:reconciler` | check results | filed rows + tracker items (GAP/VIOLATION) + bidirectional drift rows |

**Approval gates:** **none.** This is the standing/background loop — it runs without owner attention by design.

**Relationship to modes:** standing/background; independent of the owner attention budget **except** when a surfaced row needs a decision.

### 7.3 `full-wave` — staged

**Purpose:** The zero-touch wave — **SEED → QUEUE → EXECUTE → MERGE+VERIFY → CLOSE** (§4) — with approval gates at **exactly the four owner-attention points and nowhere else** (§6). Anything else that would reach the owner is a **protocol defect** (§6; §C).

| # | Step | Agent | Consumes | Produces |
|---|---|---|---|---|
| 1 | `seed` | `converge:reconciler` | contracts + tree | populated ledger |
| 2 | `queue` | `converge:reconciler` | ledger rows | tracker items with clause-quoting acceptance (via `lane-brief`) |
| 3 | `execute` | `foundation:explorer` (worktree lanes) | tracker items | lane commits + `DONE.md` |
| 4 | `merge-verify` | `foundation:git-ops` + `converge:reconciler` | lane artifacts | merged main; **each verdict promoted only by its own artifact check** |
| 5 | `close` | `converge:reconciler` | merged state | freeze-bar report; residuals named honestly |

**Approval gates — the four, mapped:**

| Gate | Placed after | Semantic |
|---|---|---|
| `priority-kill` | `queue` | `authorizes_next` |
| `irreversible-ops` | `merge-verify` | `authorizes_next` |
| `human-device-verify` | `merge-verify` | `validates_previous` |
| `ratify-changes` | `close` | `validates_previous` |

**Data flow:** contracts → ledger (seed) → tracker items (queue) → lane commits (execute) → merged main (merge-verify) → freeze-bar report (close). Work is **derived** at step 1–2 from the contract/reality gap — never invented.

**Relationship to modes:** the whole wave runs under the candidate `converge-orchestration` mode if adopted. The four gates map **1:1** to §6's four items; the model must confirm **no fifth gate leaks owner attention below the contract layer** (§C).

*Note:* two gates hang off the single `merge-verify` step (`irreversible-ops` and `human-device-verify`). The spec does not state their relative ordering. Flagged as ambiguous.

### 7.4 `hooks-candidate-guard` — **CANDIDATE (OPEN QUESTION #2)**

Not a recipe, but the enforcement counterpart to them.

| Property | Value |
|---|---|
| Triggers on | pre-tool-use on `write_file`, `edit_file`, `apply_patch` |
| Behavior | inspect the target **path** and current **phase**; if a protected path (`contracts/**`, `docs/VISION.md`, FROZEN-stamped files) is edited directly (not via a `CANDIDATE-<topic>.md`), **or** an implementation write occurs before ENCODE is committed → **block with a remedy message** pointing to the CANDIDATE flow / the ENCODE phase; otherwise allow |
| Fills | the gap the mode cannot — per-path, which per-tool policies cannot express (§5.1) |
| Alternative under evaluation | **no hook** — these hold as convention |

The model must determine whether guidance holds or **structural enforcement** is warranted (**verification objective D5**). Cross-reference §2.2 and §3.1 directive 3.

---

## 8. Behavioral Scenarios

Five scenarios, built only from mechanisms in the extraction. Each names its trigger, the mechanism chain, what context loads where, and the expected outcome.

### Scenario A — Mode-driven interactive flow: "Can I just edit this frozen contract clause?"

**Trigger:** Owner (or a lane) asks to change a clause in a FROZEN contract.

**Mechanism chain:**

1. Root session holds `converge-awareness` (~400 tok) → recognizes this as a **procedure** question, not an interpretive one → routes to a skill, not the agent (§6.3, D3).
2. `load_skill(skill_name="candidate-amendment")` — matches trigger phrasing "can I edit this frozen clause?" (D2).
3. Skill phase 1: **price the change.** Convergent → just do it, no amendment. Divergent → amendment owed.
4. Divergent path → `amendment-drafter` (when built) authors `CANDIDATE-<topic>.md` beside the frozen doc: diff · evidence · what-does-NOT-change · ask.
5. If `converge-orchestration` is active: `write_file` is **warn** (§2.1) — the write proceeds with a warning. If `hooks-candidate-guard` is adopted: a direct edit to the frozen path is **blocked** with a remedy message; the sibling `CANDIDATE-` write is allowed.
6. Agent **stops**. Does not commit, does not self-ratify.

**Context flow:** awareness (root) → `candidate-amendment` skill body (inline, root context) → `amendment-drafter` sub-session loads `PROTOCOL.md` §5 + the frozen doc + evidence artifacts.

**Expected outcome:** A `CANDIDATE-<topic>.md` exists beside the frozen doc; the frozen doc is untouched; the owner is asked for a literal-word ratification (`ratified` / `ratified as edited` / `declined-with-reason`). This consumes one of the four §6 attention items (`ratify-changes`).

**What this scenario tests:** D2 (skill trigger fires), D5 (does convention hold without the hook, at step 5).

### Scenario B — Recipe-driven automated flow: post-merge reconcile

**Trigger:** A merge lands on main (or the scheduled audit fires). No human involved.

**Mechanism chain:** `seed-reconcile` (flat, no gates) runs:

1. `load-contracts` → `foundation:explorer` produces contract inventory + tree evidence.
2. `derive-rows` → `reconciler` derives one row **per checkable clause** — never a row no clause backs. Dispositions from the fixed vocabulary.
3. `run-conformance` → `reconciler` shells out (`bash`) to **the target repo's own kit** (`pytest -q` or equivalent). It does not reimplement the checks.
4. `file-drift` → for each `GAP`/`VIOLATION`, files a tracker item into **work-tracker** and attaches the live work ref. Bidirectional drift rows filed — including *silent movement back toward spec*.
5. SYNC row check: contract-hash mismatch → **mandatory full-ledger re-review**, never a silent bump.
6. Coverage tripwires (LEDGER-FORMAT §6) must pass. Then stop.

**Context flow:** `reconciler` sub-session loads `LEDGER-FORMAT.md` **in full** + `PROTOCOL.md` §3.3 + the target repo's `contracts/` and `ledger/`. Nothing loads into the root session.

**Expected outcome:** Ledger rows written/updated in the target repo; every red row has a filed tracker item (*a red row without a filed item is a ledger that lies*); drift is caught in both directions. **Zero owner attention consumed** — unless a surfaced row needs a decision, at which point it escalates to the `priority-kill` gate in a wave.

**What this scenario tests:** the mechanization premise — *"anything that depends on someone remembering to run it will eventually not run."*

### Scenario C — Agent delegation chain: "What are my options here?" during NEGOTIATE

**Trigger:** Owner asks, at the contract level, "what are my options here?" — with Phase-0 investigation briefs already in hand.

**Mechanism chain:**

1. Root (`converge-awareness`) routes contract-level option framing → `converge:negotiator`.
2. `negotiator` **refuses to negotiate from memory** — it requires the Phase-0 briefs. Absent briefs, it stops (§4 Phase 0).
3. While framing a call, a conformance question arises ("does this shape conform to the contract anatomy the protocol requires?"). `negotiator` carries only a **thin slice** of `PROTOCOL.md` §1/§4 → **delegates to `protocol-authority`** rather than loading the full spec (D4).
4. `protocol-authority` quotes the governing clause and cites its section. If the spec is silent, it **says so**. It does not decide, ratify, or act. Exits with no repo mutation.
5. A "should this even have a contract?" question arises → `negotiator` defers seam judgment to `load_skill("seam-test")`: apply "if this changed silently, who breaks?" → seam vs internal → no-third-option. **A repo with no seam does not get a manufactured contract.**
6. `negotiator` returns **options + a recommendation per open call, as minutes — not a document** — and stops.

**Context flow:** thin `PROTOCOL.md` slice + Phase-0 briefs in `negotiator`; **full** `PROTOCOL.md` + `LEDGER-FORMAT.md` + common-agent-base in the `protocol-authority` sub-session (isolated, not inherited by root); `seam-test` body inline.

**Expected outcome:** Owner receives minutes with a recommendation per call and makes the decisions. The negotiator ratifies nothing. Heavy protocol context stays out of the negotiating context.

**What this scenario tests:** D4 (does context stay where it belongs?), D1 (is `protocol-authority` consulted for interpretive calls, and *only* those?).

### Scenario D — Full wave, with the four gates and no fifth

**Trigger:** Wave start. `converge-orchestration` entered at SEED (if adopted).

**Mechanism chain:** `full-wave` (staged):

1. **seed** — `reconciler` populates the ledger from contracts + tree.
2. **queue** — `reconciler` turns rows into tracker items with clause-quoting acceptance, using `lane-brief` (honesty gate + file-ownership split).
   → **GATE 1 `priority-kill`** (`authorizes_next`) — owner attention item #1.
3. **execute** — `foundation:explorer` runs worktree lanes → lane commits + `DONE.md`.
4. **merge-verify** — `foundation:git-ops` + `reconciler`. Each verdict is promoted **only by its own artifact check**. `lane-brief` discipline applies: judge from **git artifacts**, check **provenance** — *inherited-from-fork artifacts are the #1 false signal*. A `DONE.md` that says "passing" is **not** proof.
   → **GATE 2 `irreversible-ops`** (`authorizes_next`) and **GATE 3 `human-device-verify`** (`validates_previous`) — items #2 and #3. *(Their relative order is not specified — see §7.3.)*
5. **close** — `reconciler` produces a freeze-bar report; residuals are **named honestly** rather than papered over.
   → **GATE 4 `ratify-changes`** (`validates_previous`) — item #4.

**Context flow:** mode active in root; `reconciler` sub-sessions carry `LEDGER-FORMAT.md`; `lane-brief` inline at queue and merge-verify; `freeze-bar` inline at close.

**Expected outcome:** Main merged; ledger current; **exactly four owner-facing moments**, matching §6 1:1. Any fifth interruption is not an inconvenience — it is a **protocol defect** (§C).

**What this scenario tests:** whether the attention budget actually holds under a real wave, and whether mode directive 2 (route to exactly four) is enforceable.

### Scenario E — The failure scenario: an implementation write before ENCODE

**Trigger:** A lane starts writing implementation code while `VISION.md` and the contracts are still unratified drafts.

**Mechanism chain — three possible outcomes, depending on unresolved OPEN QUESTIONS:**

| Configuration | What happens |
|---|---|
| **No mode, no hook** (today) | Nothing structural intervenes. The `encode` recipe's `ratify-encoded` gate would have caught it *if the recipe were running* — but a free-form lane write is unguarded. Convention only. |
| **Mode adopted, no hook** | `write_file`/`edit_file` are **warn** — the operator sees a warning but the write proceeds. Mode directive 1 says "enforce phase order," but per-tool policy **cannot** distinguish an implementation write from any other write (§2.2). The directive is guidance, not a mechanism. |
| **Hook adopted** | `hooks-candidate-guard` fires pre-tool-use, sees an implementation write with ENCODE uncommitted, and **blocks with a remedy message** pointing at the ENCODE phase. |

**Expected outcome:** This scenario is precisely **verification objective D5** — it is the experiment that decides OPEN QUESTION #2. The spec does not pre-answer it. The middle row is the important finding: *adopting the mode alone does not close this gap.*

---

## 9. Spec-Derived Limitations

What **cannot** be determined from the mechanism spec alone, and what would be required to settle each:

| # | Cannot determine | Why | What would settle it |
|---|---|---|---|
| 1 | **Transitive dependency tree** | The spec names direct dependencies only: `amplifier-foundation@main` and `work-tracker`. What foundation itself pulls in — and what those pull in — is not stated. | Resolve the composed bundle graph. |
| 2 | **Composition loopholes** | `converge-orchestration`'s block list is **empty**, and policies are per-tool. Whether a `confirm`-gated operation (git-ops destructive, `work_resolve` on contract-layer items) is reachable unrestricted through `foundation:git-ops`, `foundation:file-ops`, `foundation:explorer`, or a recipe step depends on **resolved** policies across the whole graph. | Resolve tool policies for every composed component, then diff against the mode matrix. |
| 3 | **Delegation necessity map** | Whether the root *must* delegate (versus being able to act directly) requires the full resolved tool matrix for root and every agent. The spec gives per-agent `tool_requirements`, which state what an agent *needs*, not what the root *lacks*. | Full resolved tool matrix, root + agents. |
| 4 | **Actual token counts** | Only one figure exists in the spec — `converge-awareness` at ~400, explicitly an **estimate**. No estimate at all for `PROTOCOL.md`, `LEDGER-FORMAT.md`, the skill bodies, or the agent context loads. §6.2 is therefore mostly empty by necessity. | Measure the real files. |
| 5 | **Whether `converge-orchestration` earns its cost** | OPEN QUESTION #1, explicitly unresolved in the spec. Scenario E shows the mode alone does not close the phase-order gap. | Run the mode-vs-no-mode comparison the spec calls for. |
| 6 | **Whether `hooks-candidate-guard` is warranted** | OPEN QUESTION #2 / D5, explicitly unresolved. | Test whether convention holds without structural enforcement. |
| 7 | **Whether `protocol-authority` should carry `LEDGER-FORMAT.md`** | D4, explicitly flagged as a tension in the spec, not resolved by it. `ledger-disposition` and `reconciler` both also carry ledger knowledge. | Test whether conformance answers degrade when the ledger format is co-resident. |
| 8 | **Gate ordering within `merge-verify`** | Two gates (`irreversible-ops`, `human-device-verify`) attach to the same step with different semantics (`authorizes_next` vs `validates_previous`). Their relative order is not stated. | Ambiguity in the source spec — needs an authoring decision. |
| 9 | **`converge-orchestration`'s companion skill** | The field is empty. Whether that means "deliberately none" or "not yet decided" is not stated. | Ambiguity in the source spec. |
| 10 | **Runtime behavior of PLANNED components** | Three agents and all three recipes are **not built**. Everything in §4.2–4.4 and §7 describes *specified* behavior, not observed behavior. | Build them and observe. |

### Verification objectives referenced in this document

| ID | Objective | Covered in |
|---|---|---|
| D1 | Does the root consult `protocol-authority` for interpretive questions — and *only* those? | §4.1, §6.3, Scenario C |
| D2 | Do the skills' trigger phrasings actually fire? | §5, Scenario A |
| D3 | Does the root **delegate** rather than answer protocol questions from `converge-awareness`? | §6.1, Scenario A |
| D4 | Does carrying `LEDGER-FORMAT.md` dilute `protocol-authority`'s conformance answers? | §4.1, §5.4, Scenario C |
| D5 | Does phase-order convention hold, or is structural enforcement warranted? | §2.2, §3.1, §7.4, Scenario E |
