# Converge — Mechanism Spec (full bundle)

**Status:** DRAFT — input for `@foundation:recipes/spec-to-behavioral-model.yaml`.
**Purpose of this document:** describe the WHOLE intended `converge` bundle as
a set of Amplifier mechanisms, so a behavioral model can be generated and the
PLANNED behavior-heavy parts verified *before* they are built.
**Governing spec (source of truth):** `@converge:docs/PROTOCOL.md` (ratified
v2) and `@converge:docs/LEDGER-FORMAT.md` (starter ledger convention). This
spec quotes or points to those; it does not restate them. Section references
below (§) are to `PROTOCOL.md` unless noted.

### How to read this spec

Every mechanism carries a **STATUS** tag. The tag is written into each
mechanism's `purpose` field (first line) so it survives extraction:

- **AS-BUILT** — committed today in the knowledge layer. The behavioral model
  should confirm it behaves as intended.
- **PLANNED** — behavior-heavy, **not built.** This is what the model exists to
  verify before we build it.
- **CANDIDATE (OPEN QUESTION)** — a proposed mechanism that *was itself* one of
  the open design questions. The spec states it and its named alternative.
- **DECIDED** — an open question the owner has now ratified. Carries the
  decision (`DEFERRED` or `BUILD`) and its rationale inline. As of the
  increment-1 patch (see Patch log at the end), the two former CANDIDATE
  mechanisms are DECIDED: the mode (§5.1) is DEFERRED, the hook (§6.1) is BUILD.

Anti-scope (non-goals) and the five verification objectives are not their own
mechanism types, so they are also woven into individual mechanisms'
`behavioral_directives` (which the extractor captures) — see §C and §D.

**Routing authority (Finding #1 — RESOLVED).** The **root session is the only
router.** It holds `converge-awareness` and decides, per utterance, whether to
consult `protocol-authority` (interpretive/conformance), load a skill
(procedure), or spawn a worker agent (`negotiator` / `reconciler` /
`amendment-drafter`). **Sub-agents return needs; they do not re-route.** A
worker that discovers mid-task that it needs a conformance ruling or a seam
judgment **returns that need** to the root (e.g. *"needs a conformance ruling
on X"*); the root makes the call and feeds the answer back. No agent in this
bundle spawns another agent or loads a skill on its own behalf — the delegation
graph stays one level deep and the router stays single.

---

## 0. Bundle identity

- **name:** converge
- **purpose:** Vision-first, contract-driven development. The owner and the
  orchestrator negotiate at the contract level; work is *derived* from the gap
  between repo reality and the ratified contracts, never invented; a standing
  conformance ledger (the "ratchet") refuses silent drift in either direction.
  Direction changes land in the contract FIRST. The owner's attention is spent
  only at the contract layer (§6).
- **dependencies:**
  - `git+https://github.com/microsoft/amplifier-foundation@main` (bundle
    dependency; provides `explorer`, `git-ops`, `file-ops`, recipes runtime,
    common bases).
  - `work-tracker` (runtime tool, **reused, not owned** — see §C).
- **installation_paths:** `amplifier-bundle-converge/` (bundle root; the
  ratified spec and ledger convention live under `docs/`).

---

## 1. Context files (always-loaded root context)

### 1.1 converge-awareness — **AS-BUILT**

- **name:** converge-awareness (`context/converge-awareness.md`)
- **purpose:** AS-BUILT. A thin routing pointer, always loaded into the root
  session via `bundle.md`. It states that the stack exists
  (Strategy → Vision → Contracts → Ledger → Lanes), states the four-item owner
  attention budget verbatim (§6), and carries **the disambiguating routing
  rule (Finding #2):** *"am I allowed / does this conform?"* → consult
  `converge:protocol-authority` (interpretive); *"how do I author / perform X?"*
  → load the matching skill (procedural). **It contains NO protocol rules of its
  own — only awareness and routing.** Its design intent is to make the root
  session *delegate*, never to let the root session answer protocol questions
  from this file (verification objective D3). The root is the **only** router
  (see the Routing authority note above §2).
- **estimated_tokens:** 400
- **always_loaded:** true

> Note: the full `PROTOCOL.md` (~2.5k tokens) and `LEDGER-FORMAT.md` (~1.5k
> tokens) are deliberately **NOT** always-loaded. They are carried by
> `protocol-authority` as a context sink and load only when that agent is
> spawned (see §2.1). This is the core context-economics decision of the
> bundle.

---

## 2. Agents

### 2.1 protocol-authority — **AS-BUILT**

- **name:** protocol-authority
- **purpose:** AS-BUILT. THE single authority and context sink for the ratified
  protocol. Answers interpretive/conformance questions — *"what does the
  protocol say?"* and *"does this conform?"* — by quoting and citing
  `PROTOCOL.md` / `LEDGER-FORMAT.md`. It does not act, ratify, or execute
  procedures.
- **model_role:** reasoning
- **trigger_conditions:** any question about protocol conformance; the stack
  and which layer governs which; the loop phases; the lifecycle (Freeze Bar,
  CANDIDATE protocol, version bumps, change pricing); the owner attention
  budget and whether something reaching the owner is a protocol defect; the
  pillars and the "no third option" axiom.
- **operating_modes:** [answer-conformance] (single mode — interpret and cite)
- **behavioral_directives:**
  - Owns the *interpretive* questions ("what does the protocol say / does this
    conform"). **Procedure execution ("how do I perform X") routes to the
    skills, not here** (verification objective D1).
  - Quote the governing clause and cite its section; if the spec is silent, say
    so — never invent a rule.
  - Does NOT ratify and does NOT decide priority/kill — those are the owner's
    (§6). Reports what the protocol says.
  - **Failure modes the model must exercise (D1):** (a) the root over-delegates
    trivial procedure calls here, making the skills dead weight; (b) the root
    never consults here, so conformance judgment gets silently skipped.
  - **Heavy-doc placement tension (D4):** this agent currently carries BOTH
    `PROTOCOL.md` and `LEDGER-FORMAT.md`. The model must test whether carrying
    the ledger format dilutes its conformance answers versus letting the
    `ledger-disposition` skill / `reconciler` own the ledger detail.
- **tool_requirements:** read_file, grep (read-only; reasons over carried docs)
- **context_loading:** `@converge:docs/PROTOCOL.md`,
  `@converge:docs/LEDGER-FORMAT.md`, `@foundation:context/shared/common-agent-base.md`
- **exit_conditions:** cited answer delivered; no repo mutation.

### 2.2 negotiator — **PLANNED**

- **name:** negotiator
- **purpose:** PLANNED (not built). Phase 1 NEGOTIATE (§4). Turns Phase-0
  investigation evidence into **decision-level options + a recommendation per
  open call** — "minutes, not documents." Surfaces the calls the owner must
  make; it does not make them.
- **model_role:** reasoning
- **trigger_conditions:** entering NEGOTIATE with investigation briefs in hand;
  owner asks "what are my options here?" at the contract level.
- **operating_modes:** [negotiate]
- **behavioral_directives:**
  - Produce options + a recommendation for each open call; keep it to minutes,
    never a document (§4 Phase 1).
  - **Never negotiate from memory** — requires Phase-0 evidence first (§4
    Phase 0).
  - **Does NOT ratify** — decisions are owner acts; the negotiator only frames
    them (§C anti-scope; §6.1).
  - **Does NOT manufacture a contract for a repo with no seam** (§3.2, §7; §C).
  - **Returns needs; does not re-route (Finding #1).** When a conformance
    ruling or a seam judgment is required, the negotiator **returns the need**
    to the root (e.g. *"needs a conformance ruling on X"* / *"needs a seam
    judgment on Y"*); the **root** calls `protocol-authority` or loads
    `seam-test` and feeds the answer back. The negotiator never spawns another
    agent or loads a skill itself — it carries no delegation tools, which is
    why a thin context slice is sufficient (relates to D4).
- **tool_requirements:** read_file, grep (reads investigation briefs; produces
  text minutes). **No delegation/spawn/`load_skill` tools** — consistent with
  returning needs to the root (Finding #1).
- **context_loading:** Phase-0 investigation briefs; a thin negotiation-
  relevant slice of `PROTOCOL.md` §1/§4. Does **not** load the full spec and
  does **not** consult other agents directly; surfaces a conformance/seam
  *need* to the root instead.
- **exit_conditions:** per-call options + recommendation delivered as minutes;
  any conformance/seam needs surfaced to the root; stops for the owner to
  decide.

### 2.3 reconciler — **PLANNED**

- **name:** reconciler
- **purpose:** PLANNED (not built). SEED (first ledger population) and the
  engine of standing RECONCILE (§4). Derives clause-granular ledger rows from
  contracts vs repo reality per `LEDGER-FORMAT.md`, assigns dispositions, and
  detects **bidirectional drift** (away from spec AND silent movement back
  toward spec both file rows — §3.3).
- **model_role:** reasoning
- **trigger_conditions:** SEED (first population); every merge; the scheduled
  audit; "reconcile the ledger" / "has anything drifted?"
- **operating_modes:** [seed, reconcile]
- **behavioral_directives:**
  - Rows are **derived from contracts, one per checkable clause** — never
    invent a row no clause backs (§3.3; LEDGER-FORMAT §2).
  - Assign dispositions from the fixed vocabulary (`CONFORMS · GAP · VIOLATION
    · OPEN-PINNED · NOT-ASSERTABLE · EXCLUDED`; `DIVERGED` for external
    contracts only) — LEDGER-FORMAT §3.
  - Every `GAP`/`VIOLATION` row **files a tracker item INTO work-tracker and
    carries a live `work` ref** — a red row without a filed item is a ledger
    that lies (LEDGER-FORMAT §2). **work-tracker is authoritative; the
    reconciler files into it, never replaces it** (§C).
  - **Invokes the target repo's own conformance kit** (`pytest -q` or
    equivalent) to run checks; **does not reimplement or own the checks** (§C;
    LEDGER-FORMAT §1).
  - Honors the SYNC row: a contract-hash mismatch triggers a **mandatory
    full-ledger re-review, never a silent hash bump** (LEDGER-FORMAT §4).
  - A self-report is never proof (pillar 2): promotes a check to "passing" only
    by running the artifact itself.
  - **Never synchronously interrupts the owner (Finding #4).** A finding that
    needs an owner decision is filed as a ledger row + tracker item and the
    reconciler **stops**; the decision is taken asynchronously at the next
    `full-wave` `priority-kill` gate, drawn from the ledger/tracker (§4.2).
  - **Returns needs; does not re-route (Finding #1).** For an interpretive
    conformance call (e.g. *"is this clause REQUIRED or IDIOM?"*) the reconciler
    **returns the need** to the root rather than spawning `protocol-authority`
    itself. Its tools are execution tools only — no delegation/spawn/`load_skill`.
- **tool_requirements:** read_file, grep, glob, bash (run the repo's kit),
  write_file (ledger rows in the target repo), work-tracker (`work_list` for
  read/idempotency lookup, `work_add` / `work_file` to file), git (provenance,
  content hash). **No delegation/spawn/`load_skill` tools** (Finding #1).
- **context_loading:** `@converge:docs/LEDGER-FORMAT.md` (full), `PROTOCOL.md`
  §3.3 (for its own reading; interpretive calls it cannot settle are returned to
  the root, not resolved by loading the full spec); the target repo's
  `contracts/` and `ledger/`.
- **exit_conditions:** ledger rows written/updated in the target repo; drift
  rows and GAP/VIOLATION tracker items filed (with live `work` refs); coverage
  tripwires pass (LEDGER-FORMAT §6); any owner-decision needs left as filed
  rows/items for the next wave; stops without interrupting the owner.

### 2.4 amendment-drafter — **PLANNED**

- **name:** amendment-drafter
- **purpose:** PLANNED (not built). Authors a `CANDIDATE-<topic>.md` proposal to
  amend a frozen vision/contract clause **and stops** (§5). The proposal is a
  sibling file, never a direct edit.
- **model_role:** reasoning
- **trigger_conditions:** a divergent change to a frozen clause is warranted;
  a measured cost/failure suggests a clause is wrong; "draft an amendment for
  this."
- **operating_modes:** [draft-candidate]
- **behavioral_directives:**
  - Emits a `CANDIDATE-<topic>.md` carrying exactly: the exact diff · evidence
    citations (a real cost paid or failure caught — **a preference is not
    evidence**) · an explicit "what does NOT change" section · a ratification
    ask (§5).
  - **Never self-ratifies and never edits the frozen doc** — ratification is an
    owner-only literal-word act (*ratified / ratified as edited /
    declined-with-reason*) (§5, pillar 3; §C, §7).
  - Applies change pricing: convergent changes need no amendment; only
    *divergent* changes route here (§5). Defers the pricing call to the
    `candidate-amendment` skill / `protocol-authority`.
- **tool_requirements:** read_file, grep, write_file (the CANDIDATE file only)
- **context_loading:** `PROTOCOL.md` §5; the frozen document being amended;
  cited evidence artifacts.
- **exit_conditions:** `CANDIDATE-<topic>.md` authored beside the frozen doc;
  stops for owner ratification. Does not commit the amendment.

---

## 3. Skills (AS-BUILT — knowledge layer)

All five are **inline** skills: procedure knowledge loaded on demand into the
current session via `load_skill`. None fork; none delegate. Each answers
*"how do I perform this procedure"* — the counterpart to `protocol-authority`'s
*"what does the protocol say"* (verification objective D1). Each grounds in
`PROTOCOL.md` / `LEDGER-FORMAT.md`.

### 3.1 seam-test

- **name:** seam-test
- **type:** inline
- **purpose:** AS-BUILT. Decide seam vs internal mechanism, and thus whether a
  contract is warranted (§3.2). Applies the test *"if this changed silently,
  who breaks?"* and the "no third option" axiom.
- **invocation:** `load_skill(skill_name="seam-test")`; **triggered by** "is
  this a seam?", "does this warrant a contract?", "should this get a contract
  or just tests?" (verification objective D2).
- **workflow_phases:** apply the who-breaks test → classify seam vs internal →
  if seam, a contract is warranted; if not, tests only → apply no-third-option
  (convergent-behavior-or-debt).
- **behavioral_directives:** A repo with no seam does not manufacture a contract
  (§3.2, §7; §C). Escalate contract anatomy/versioning to `protocol-authority`.
- **mode_association:** "" (usable from the root session or the candidate
  orchestration mode)
- **delegation_pattern:** none

### 3.2 candidate-amendment

- **name:** candidate-amendment
- **type:** inline
- **purpose:** AS-BUILT. How to author a CANDIDATE amendment file and how to
  price the change first (convergent vs divergent) (§5).
- **invocation:** `load_skill(skill_name="candidate-amendment")`; **triggered
  by procedural phrasings** — "how do I amend a frozen clause?", "how do I
  author a CANDIDATE?", "how do I propose a contract change?" (Finding #2:
  procedural forms only). **Permission/conformance phrasings** ("*can I* edit
  this?", "*am I allowed* to change this?", "does this conform?") route to
  `protocol-authority` instead, per the §1.1 routing rule (verification
  objective D2).
- **workflow_phases:** price the change (convergent → just do it; divergent →
  amendment owed) → author `CANDIDATE-<topic>.md` (diff · evidence · what-does-
  NOT-change · ask) → route to owner for literal-word ratification.
- **behavioral_directives:** No self-ratification by lanes or orchestrator
  (pillar 3, §7). A preference is not evidence. Feeds the `amendment-drafter`
  agent when built.
- **mode_association:** ""
- **delegation_pattern:** none

### 3.3 freeze-bar

- **name:** freeze-bar
- **type:** inline
- **purpose:** AS-BUILT. The four-condition DRAFT→FROZEN checklist and the
  discriminating-fixture requirement (§5, pillar 4).
- **invocation:** `load_skill(skill_name="freeze-bar")`; **triggered by** "can
  we freeze this?", "is this ready to stamp FROZEN?", conformance-kit review.
- **workflow_phases:** check all four conditions (spec written · machine kit
  with ≥1 discriminating good/bad fixture pair · ≥1 real implementation passes ·
  worked example end-to-end) → recommend; the owner stamps.
- **behavioral_directives:** Only the owner stamps FROZEN (§6.1). Prose alone
  freezes nothing (pillar 4). Honest stopping beats stamping around a gap
  (pillar 5).
- **mode_association:** ""
- **delegation_pattern:** none

### 3.4 ledger-disposition

- **name:** ledger-disposition
- **type:** inline
- **purpose:** AS-BUILT. Assign the right disposition to a ledger row;
  understand the row schema, the SYNC row, coverage tripwires, and
  bidirectional drift (§3.3; LEDGER-FORMAT §2–6).
- **invocation:** `load_skill(skill_name="ledger-disposition")`; **triggered
  by** a flipped/red ledger row, "what disposition does this get?", "is this
  drift?", populating or reviewing the ledger (verification objective D2).
- **workflow_phases:** identify the backing clause → choose disposition from the
  vocabulary → attach required fields (`work` ref for GAP/VIOLATION;
  `justification` for OPEN-PINNED/NOT-ASSERTABLE) → check drift direction.
- **behavioral_directives:** Drift is bidirectional (§3.3). `DIVERGED` is illegal
  for self-governed contracts (LEDGER-FORMAT §3). Prefer probes for load-bearing
  rows (LEDGER-FORMAT §8). Feeds the `reconciler` agent when built.
- **mode_association:** ""
- **delegation_pattern:** none

### 3.5 lane-brief

- **name:** lane-brief
- **type:** inline
- **purpose:** AS-BUILT. Write and judge autonomous lane briefs with the
  required discipline: honesty gate, file-ownership split, provenance checks,
  artifacts-not-liveness (§4 lane discipline; pillars 2 & 5).
- **invocation:** `load_skill(skill_name="lane-brief")`; **triggered by**
  briefing an EXECUTE-phase lane, "is this lane actually done?", a
  successful-looking run that may have produced nothing.
- **workflow_phases:** write brief (honesty gate + file-ownership split +
  clause-quoting acceptance) → judge completion only from git artifacts →
  check artifact provenance → verify verdicts by artifact, not self-report.
- **behavioral_directives:** Inherited-from-fork artifacts are the #1 false
  signal (§4). A self-report is never proof (pillar 2). A missing artifact is a
  real result (pillar 5). Feeds `full-wave` EXECUTE/VERIFY when built.
- **mode_association:** ""
- **delegation_pattern:** none

---

## 4. Recipes — **all PLANNED (not built)**

### 4.1 encode — **PLANNED**

- **name:** encode
- **purpose:** PLANNED. Phase 2 ENCODE (§4). Take the owner's **already-ratified**
  negotiation decisions and author `VISION.md` + `contracts/<seam>.v1.md` as
  **DRAFT** artifacts, present them for the owner's literal-word ratification,
  and **commit them before any implementation** — the commit being the
  ratification record. The recipe does **not** run negotiation (that is the
  interactive owner+`negotiator` work of Phase 1, upstream) and it **never
  stamps FROZEN** (owner-only, Freeze Bar §5).
- **execution_mode:** staged
- **schedulable:** no — interactive, owner-gated (one owner ratification).
- **inputs (recipe context):**
  - `target_repo` (required) — path to the repo being encoded (must be the
    session cwd or within it; see the within-cwd constraint below).
  - `negotiated_decisions` (required) — the **intake** context var carrying the
    owner-approved Phase-1 minutes: for each call, the decision the owner made
    (which seams get contracts, each contract's Core/Backlogged/Conformance/
    Reserved intent, and the VISION end-state + principles + "deliberately
    resists" content). The recipe consumes this; it does not re-derive it.
  - `seams` (optional, default derived from `negotiated_decisions`) — the list
    of seam names → one `contracts/<seam>.v1.md` each.
  - `vision_path` (default `docs/VISION.md`), `contracts_dir` (default
    `contracts/`).
- **outputs:**
  - `{{vision_path}}` written as **DRAFT** (genre per PROTOCOL.md §3.1: desired
    end state as though already true · numbered operating principles · required
    "What this repo deliberately resists" · dated changelog — nothing else;
    thin-pointer to a governing contract where one exists);
  - one `{{contracts_dir}}/<seam>.v1.md` per seam, **DRAFT** (anatomy per §3.2:
    Core · Backlogged with named promotion triggers · Conformance · Reserved ·
    Changelog);
  - a git commit on `target_repo` recording the ratified DRAFT artifacts, whose
    message embeds the ratification record (see step 3);
  - an **encode report** naming files written, seams covered, and the explicit
    residual: these are DRAFT — the Freeze Bar (§5) is a later, owner-only act.
- **steps:**
  | id | agent | consumes | produces |
  |---|---|---|---|
  | intake-decisions | foundation:file-ops (or a read-only prep step) | `negotiated_decisions`, `target_repo` | a normalized plan: seam→contract map + vision outline (no repo writes) |
  | draft-vision-contracts | foundation:file-ops | intake plan | `VISION.md` (DRAFT) + `contracts/<seam>.v1.md` (DRAFT), written to `target_repo` |
  | commit-encoded | foundation:git-ops | ratified DRAFT artifacts + gate approval message | a commit recording the encoded artifacts + ratification record |
- **approval_gates:**
  | name | placed_after_step | semantic | §6 owner-attention item |
  |---|---|---|---|
  | ratify-encoded | draft-vision-contracts | validates_previous | §6 #1 — ratify vision/contract changes |
  - `ratify-encoded` presents the drafted `VISION.md` + contract DRAFTs to the
    owner, who answers with the **literal word** (`ratified` / `ratified as
    edited` / declined-with-reason). No self-ratification (§C, pillar 3). The
    gate's approval message (the owner's literal word + any edits) is passed to
    `commit-encoded` and embedded in the commit body as the ratification record.
    A decline stops the recipe before any commit; "ratified as edited" loops
    back to a re-draft of the named edits before committing.
- **constraints (hard — recipe-author must honor, zero design latitude):**
  - **Within-cwd invariant (increment-1 v1.2.0):** every write and the commit
    target must resolve inside the session cwd / `target_repo`. No writes
    outside the workspace.
  - **Write-denial / candidate-guard interplay (increment-2):** the
    `hooks-candidate-guard` hook is composed and on. **DRAFT contracts and a
    DRAFT VISION.md are writable by design** — the guard only denies writes to
    files carrying the FROZEN/RATIFIED marker. Therefore `draft-vision-contracts`
    **must write DRAFT status** (`**Status:** DRAFT`) and must **never** write
    the FROZEN/RATIFIED marker into these files. If encode ever targeted an
    already-FROZEN file it would (correctly) be denied — encode's job is initial
    authoring of DRAFTs, not amending frozen artifacts (that is the CANDIDATE
    flow, a different mechanism).
  - **Never stamp FROZEN.** Stamping FROZEN is an owner-only Freeze Bar act
    (§5, §6.1); the recipe stops at DRAFT + committed. The encode report must
    state this residual honestly.
  - **Derive nothing new.** The recipe encodes the owner's ratified decisions;
    it does not invent contract clauses or vision content beyond
    `negotiated_decisions`. A genuinely missing decision is surfaced back to the
    owner, not filled in (pillar 5).
- **relationship_to_modes:** runs under **no dedicated mode** (the orchestration
  mode is DEFERRED, §5.1). The single `ratify-encoded` gate is the whole
  owner-attention surface; ENCODE-before-implement is enforced downstream by the
  guard's opt-in `enforce_encode_before_impl` (spec §4.6 of the hook spec) and
  by sequencing — implementation lanes (EXECUTE) run only after encode has
  committed. Relates to D5.

### 4.2 seed-reconcile — **PLANNED**

- **name:** seed-reconcile
- **purpose:** PLANNED. SEED (first ledger population) and standing RECONCILE
  (§4) — **schedulable and run on every merge.** Derive/refresh ledger rows
  from contracts vs repo reality; detect bidirectional drift. Mechanized on
  purpose: "anything that depends on someone remembering to run it will
  eventually not run" (§4).
- **execution_mode:** flat
- **schedulable:** yes — designed to run unattended on every merge and on a
  schedule (no owner in the loop).
- **inputs (recipe context):**
  - `target_repo` (required) — path to the repo being reconciled (increment-1
    dogfood target: `drumbeat` and its frozen contract).
  - `contracts_glob` (default `contracts/*.md`) — where the seam contracts live.
  - `ledger_dir` (default `ledger/`) — where `rows.yaml` and `checks/` live
    (LEDGER-FORMAT §1).
  - `tracker_project` (required) — the work-tracker project GAP/VIOLATION items
    are filed into.
- **outputs:**
  - updated ledger rows file(s) in `{{ledger_dir}}/rows.yaml` (dispositions +
    required fields);
  - work-tracker items for every `GAP`/`VIOLATION` row (with the row id as the
    back-reference);
  - a **reconcile report** (stdout/file) summarizing rows by disposition, drift
    detected (both directions), SYNC-row status, and coverage-tripwire results.
- **steps:**
  | id | agent | consumes | produces |
  |---|---|---|---|
  | load-contracts | foundation:explorer | `target_repo`, `contracts_glob` | contract inventory + tree evidence |
  | derive-rows | converge:reconciler | contract inventory, existing `ledger_dir` | ledger rows with dispositions (SYNC row incl.) |
  | run-conformance | converge:reconciler | ledger rows, target repo kit | check results (invokes repo kit via `bash`) |
  | file-drift | converge:reconciler | check results, `tracker_project` | filed rows + tracker items (GAP/VIOLATION) + bidirectional drift rows + reconcile report |
- **approval_gates:** none.
- **owner_interaction (Finding #4):** **This loop NEVER synchronously
  interrupts the owner.** It has zero gates and zero owner-facing moments. A
  finding that needs an owner decision (a priority/kill call, an irreversible
  fix) is **filed as a ledger row + a work-tracker item and left there**; the
  decision is taken asynchronously at the **next `full-wave` `priority-kill`
  gate**, which draws from the ledger/tracker. Nothing here pages the owner —
  that is what keeps standing reconcile inside the §6 attention budget.
- **relationship_to_modes:** standing/background; fully independent of the owner
  attention budget (decisions are deferred to the next wave, never surfaced
  synchronously).

### 4.3 full-wave — **PLANNED**

- **name:** full-wave
- **purpose:** PLANNED. The owner-gated wave — SEED/RECONCILE → QUEUE → EXECUTE
  → MERGE → VERIFY → CLOSE (§4) — with approval gates at **exactly the four
  owner-attention points and nowhere else** (§6). Anything else that would reach
  the owner is a protocol defect (§6; §C).
- **execution_mode:** staged · **schedulable:** no (owner-gated).

- **ENGINE SEMANTICS — read first (increment-3 hard-won lesson):**
  1. **Gates fire AFTER the declaring stage's steps complete; a gate governs the
     transition to the NEXT stage.** So a gate is **declared on the PRIOR
     stage**, and the steps that must act on the owner's answer live in the
     **NEXT stage**. (encode v1.0.0 inverted this — commit ran before the ask;
     v1.1.0 fixed it to this shape.)
  2. **`{{_approval_message}}` holds ONLY the most-recent gate's message.** A
     multi-gate recipe (this one has four) **must persist each gate's record**
     the moment it is consumed — write it to a file under the workspace (e.g.
     `.converge/wave/<gate>.approval`) via an update-step in the consuming stage
     — because a later stage's `{{_approval_message}}` will have been overwritten
     by the intervening gate.
  3. **Fail loud on empty approvals.** Every stage that consumes a gate must run
     a bash assert that the approval record is non-empty (and, where the protocol
     needs it, contains the literal ratifying word) — an empty/auto-approved
     record must **halt the wave**, never silently proceed. (This is the encode
     v1.1.0 fail-loud assert, generalized to four gates.)

- **stages (each stage = ordered steps; the gate a stage DECLARES fires after
  that stage, gating entry to the next):**

  | stage | steps (agents) | declares gate (fires after this stage) | consumes prior gate's record |
  |---|---|---|---|
  | **S0 seed** | invoke `seed-reconcile` as a sub-recipe (flat, gateless) → populated/ refreshed ledger + filed GAP/VIOLATION tracker items | — | — |
  | **S1 queue** | `converge:reconciler` turns READY ledger rows into tracker items with clause-quoting acceptance (applies `lane-brief` discipline: honesty gate + file-ownership split) → a **candidate queue** for the owner to pick/kill | **priority-kill** (§6 #4) | — |
  | **S2 execute** | assert+persist `priority-kill` record → work ONLY the owner-authorized item set (see EXECUTOR below) → lane commits + `DONE.md` per item | **irreversible-ops** (§6 #2) | `priority-kill` |
  | **S3 merge** | assert+persist `irreversible-ops` record → `foundation:git-ops` merges the authorized, completed lanes to main | **human-device-verify** (§6 #3) | `irreversible-ops` |
  | **S4 verify** | assert+persist `human-device-verify` record → `converge:reconciler` re-runs the ledger post-merge; **each verdict promoted only by its own artifact check** (pillar 2; `lane-brief` provenance — inherited-from-fork artifacts are the #1 false signal) → verify report | **ratify-changes** (§6 #1) | `human-device-verify` |
  | **S5 close** | assert+persist `ratify-changes` record → `converge:reconciler` emits the **freeze-bar report** (residuals named honestly per §5/pillar 5); if the owner's ratify message stamped any DRAFT→FROZEN or amendment, record it (the recipe still **does not stamp FROZEN itself** — it records the owner's literal word) | — | `ratify-changes` |

- **approval_gates (exactly four — 1:1 with §6, no fifth) — under post-stage semantics:**
  | gate | DECLARED on stage | FIRES before stage | CONSUMED by stage | semantic | §6 item |
  |---|---|---|---|---|---|
  | **priority-kill** | S1 queue | S2 execute | S2 execute | authorizes_next | §6 #4 — owner picks/kills queued items before any work runs |
  | **irreversible-ops** | S2 execute | S3 merge | S3 merge | authorizes_next | §6 #2 — owner authorizes the irreversible merge |
  | **human-device-verify** | S4 verify | S5 close | S5 close | validates_previous | §6 #3 — owner/device confirms the post-merge verification |
  | **ratify-changes** | S4 verify → gate before S5 close | S5 close | S5 close | validates_previous | §6 #1 — owner ratifies any vision/contract change / FROZEN stamp surfaced by the wave |
  - **Ordering note (two gates around the merge→close boundary).** `human-device-
    verify` and `ratify-changes` are BOTH `validates_previous`-style and both sit
    late. Under this engine a single stage boundary carries a single gate, so
    they must occupy **distinct boundaries**: place `human-device-verify` after
    **S4 verify** (gating entry to S5), and `ratify-changes` after a short
    **S4b ratify-review** stage (a no-op review stage between verify and close)
    so each has its own clean post-stage gate. Net stages: S0,S1,S2,S3,S4,S4b,S5
    — still exactly four gates, still 1:1 with §6, **no fifth owner-facing gate.**
  - Each of the four §6 items is covered exactly once; every other transition is
    gateless. A fifth owner-facing gate would be a protocol defect (§C).

- **EXECUTOR — honest v1 scope (what a recipe CAN deliver):**
  - **Deliverable now:** a **`foreach` over the owner-authorized queued items**,
    each handled by a **work-capable agent step** that claims the tracker item
    (`work_claim`), does the bounded change **within cwd**, writes `DONE.md` +
    commits, and resolves/records the item. Bounded parallelism via the engine's
    `foreach` concurrency cap. This is real, in-engine, and testable.
  - **Residual (NOT deliverable as a recipe — named, not hidden):** full
    **autonomous lane orchestration with true parallel worktree custody** (the
    cortex-style N-lane highway with per-lane tmux/worktree lease management) is
    **out of scope for the recipe engine.** A recipe `foreach` is bounded
    fan-out, not durable multi-session custody: no cross-session lease/reclaim,
    no per-lane liveness independent of the wave, no worktree-per-lane isolation
    guarantee. `full-wave` v1 therefore executes items **sequentially or in
    bounded `foreach` batches inside the wave's own session**, and DEFERS true
    lane custody to an external orchestrator (the ten-lane-highway / goal-batch
    tooling) invoked *outside* the recipe. The `lane-brief` skill still governs
    how each item is briefed and how completion is judged (git artifacts, not
    liveness) — that discipline holds regardless of executor.

- **inputs (recipe context):** `target_repo` (required; = session cwd or within
  it) · `contracts_glob`, `ledger_dir`, `tracker_project` (passed through to the
  `seed-reconcile` sub-recipe) · `authorized_items` (populated from the
  `priority-kill` gate message; the item ids the owner picked) · `wave_dir`
  (default `.converge/wave/`, where gate records persist).
- **outputs:** refreshed ledger + filed tracker items (from S0) · lane commits +
  `DONE.md` per executed item · merged main (S3) · post-merge verify report (S4)
  · freeze-bar report with honestly-named residuals (S5) · four persisted gate
  records under `wave_dir` (the wave's owner-decision audit trail).
- **constraints (hard — recipe-author honors, zero latitude):**
  - **Within-cwd invariant (v1.2.0):** every write, merge, and commit resolves
    inside cwd / `target_repo`.
  - **Write-denial doctrine (increment 2):** `hooks-candidate-guard` is on. The
    wave writes ledger rows, tracker items, lane code, `DONE.md`, and reports —
    none of which are FROZEN contract/`VISION.md` files, so none are guard-
    denied. The wave **never** writes a FROZEN file directly; any vision/contract
    change rides the CANDIDATE flow and lands only via the owner's `ratify-
    changes` word. The wave **never stamps FROZEN itself** (owner-only, §5).
  - **Tracker via `work_*` tools:** items are claimed/filed/resolved through
    work-tracker (`work_claim`/`work_add`/`work_file`/`work_resolve`); the wave
    files into the tracker, never replaces it (§C).
  - **Fail-loud empties (encode lesson):** every gate-consuming stage asserts a
    non-empty approval record (and the literal ratifying word where §5 requires
    it) via bash, and **halts the wave** on empty — never proceeds on an
    auto-approved or missing record.
  - **Derive nothing new:** work is drawn from the ledger/tracker gap, never
    invented (§C); S0's `seed-reconcile` is the only source of queued work.
- **relationship_to_modes:** runs under **no dedicated mode** (the
  `converge-orchestration` mode is DEFERRED, §5.1); phase discipline is carried
  by the recipe's stage structure + the `hooks-candidate-guard` hook (§6.1) +
  root-as-router agent/skill routing. The four gates map 1:1 to §6's four items;
  **any fifth owner-facing gate is a protocol defect** (§C).

---

## 5. Modes

### 5.1 converge-orchestration — **DECIDED: DEFERRED (was OPEN QUESTION #1)**

> **DECIDED — DEFERRED (owner-ratified, increment-1 patch).** Phase discipline
> does **not** warrant a dedicated mode. **Rationale:** the mode's residual
> value is subsumed — phase-order enforcement moves to `hooks-candidate-guard`
> (§6.1); the four owner-attention moments are delivered by the `full-wave`
> recipe gates (§4.3), not by mode policy; and the mode's only unique remaining
> contribution (confirm-gates on git-ops-destructive / `work_resolve`) is itself
> defeated by composition loopholes (empty block list, per-tool policies
> bypassable through delegated foundation agents). **Chosen path:** pure
> delegation + recipe gates + hook. This section is retained as a record and a
> re-open trigger, **not** as something to build.

- **name:** converge-orchestration
- **purpose:** DECIDED: DEFERRED. Was a proposed orchestrator mode to keep loop
  phase discipline (§4) and reserve owner attention (§6) during a wave. Not
  being built. **Re-open trigger:** a concrete need for session-wide
  confirm-gating that the recipe gates and the hook demonstrably do not cover.
- **tool_policies:**
  - **safe:** read_file, grep, glob, work_list, work_status
  - **warn:** write_file, edit_file (see the per-tool-not-per-path limitation
    below)
  - **confirm:** git-ops destructive operations, work_resolve on contract-layer
    items
  - **block:** (none at mode level; hard path-protection is the hook's open
    question — §6.1)
- **default_action:** proceed (general)
- **companion_skill:** "" (leans on multiple inline skills via awareness
  routing rather than a single companion)
- **transitions:** entered at wave start (SEED); exits at CLOSE.
- **behavioral_directives:**
  - Enforce phase order — no implementation writes before ENCODE is committed
    (§4 Phase 2; relates to D5).
  - Route owner-facing moments to exactly the four §6 items; treat any fifth as
    a protocol defect (§C).
  - **Known limitation the model must weigh:** tool policies are *per-tool, not
    per-path*, so a mode cannot cleanly `block` writes to `contracts/**` or
    `docs/VISION.md` specifically. This is precisely why OPEN QUESTION #2 (a
    hook) exists — cross-reference §6.1.

---

## 6. Hooks

### 6.1 hooks-candidate-guard — **DECIDED: BUILD (increment 2) (was OPEN QUESTION #2)**

> **DECIDED — BUILD (owner-ratified, increment-1 patch; scheduled increment 2).**
> "CANDIDATE-not-direct-edit" (§5, pillar 3) and "ENCODE-before-implement" (§4
> Phase 2) **do** need structural enforcement. **Rationale (from the model,
> Scenario E):** a per-tool policy cannot distinguish an implementation write
> from any other write, nor a frozen-path edit from any other path, so neither
> convention nor the (now-deferred) mode closes the gap; only a path+phase-aware
> hook does. **Hard build requirement:** the hook MUST intercept writes made by
> *delegated foundation agents* (`file-ops`, `git-ops`, worktree lanes), not
> only root-session writes — otherwise the composition loophole (§ limitations)
> reopens the very hole the hook closes.

- **name:** hooks-candidate-guard
- **purpose:** DECIDED: BUILD (increment 2). A pre-tool-use hook that intercepts
  file-writing tools and (a) blocks/redirects direct edits to `contracts/**`,
  `docs/VISION.md`, or FROZEN-stamped files into the CANDIDATE amendment flow,
  and (b) blocks implementation writes before ENCODE is committed. Fills the gap
  the (deferred) mode cannot — per-path + per-phase, which per-tool policies
  cannot express (§5.1). Closes verification objective D5's finding.
- **triggers_on:** the `tool:pre` event (kernel `HOOK_CONTRACT.md`) for
  `write_file`, `edit_file`, `apply_patch` (+ configurable aliases), and a
  best-effort `bash` write-scan; **coverage across delegated sub-agent sessions
  is a live-verified property, not a kernel guarantee** — see the implementation
  spec §2.9.
- **behavior:** inspect the target path; if it is a FROZEN guarded file
  (`contracts/**`, `docs/VISION.md`) edited directly rather than via a
  `CANDIDATE-<topic>.md` — and no ratified CANDIDATE escape applies — **deny**
  with a remedy message naming the file, PROTOCOL.md §5, and the CANDIDATE flow.
  ENCODE-before-implement is an opt-in secondary rule. Deny is non-bypassable
  (`HOOKS_API.md` action precedence); fail-closed on guarded-path errors.
- **IMPLEMENTATION SPEC:** `@converge:docs/design/hooks-candidate-guard-spec.md`
  — the build-ready spec (event/deny cited to the hook contract; guarded-path +
  FROZEN-marker mechanism; the ratified-CANDIDATE escape hatch; the bash
  best-effort-deny doctrine; the delegated-agent coverage finding with its
  `SESSION_FORK_SPECIFICATION.md` citation; wiring block; unit + live-probe test
  plan). `modular-builder` implements from that doc.

---

## C. Anti-scope (non-goals)

These bound the bundle. Each is also encoded into the relevant mechanism's
`behavioral_directives` above so it survives extraction and shows up in the
model. The behavioral model should show the bundle **declining** each of these.

1. **Does not own the tracker.** `work-tracker` stays authoritative; the
   `reconciler` and `full-wave` file rows/items *into* it (§2.3, §4.3).
2. **Does not ratify.** Ratification is an owner-only literal-word act (§5,
   §6.1). `negotiator`, `amendment-drafter`, and every `encode`/`full-wave`
   gate frame decisions for the owner but never make them.
3. **Does not store vision/contracts/ledger.** Those are artifacts in each
   *target* repo. The bundle is stateless know-how; agents read/write the
   target repo's files, the bundle stores none.
4. **Does not run (own) repo conformance checks.** The target repo owns its
   conformance kit; the `reconciler` *invokes* it (`pytest -q` or equivalent)
   and never reimplements the checks (§2.3; LEDGER-FORMAT §1).
5. **Does not manufacture contracts for seamless repos.** A repo with no seam
   does not get a contract (§3.2, §7; enforced via `seam-test` and encoded on
   `negotiator`).
6. **Reuses foundation, does not rebuild it.** Phase 0 INVESTIGATE uses
   `foundation:explorer`; merges use `foundation:git-ops`; encode writes use
   `foundation:file-ops`. No bespoke explorer/git/file agents.

---

## D. Verification objectives (scenario targets for the behavioral model)

These are the five things the behavioral model **must exercise as scenarios**.
They are the acceptance checklist for the generated model: when reviewing the
model's "Behavioral Scenarios" section, confirm each objective below appears as
a scenario with its failure mode probed. The underlying tensions are encoded
into the mechanism `behavioral_directives` above so the synthesized scenarios
have the material to exercise them.

- **D1 — Agent-vs-skill routing.** `protocol-authority` owns *"what does the
  protocol say / does this conform"*; the five skills own *"how do I perform
  this procedure."* Exercise **both** failure directions: (a) over-delegation
  to the authority making the skills dead weight; (b) never consulting the
  authority so conformance judgment gets skipped. (Encoded on §2.1, §3.)
  **POST-BUILD LIVE-EVAL TARGET:** a from-spec model can only depict the
  intended split; both failure directions are runtime-routing behaviors that
  require a live session (or `bundle-behavioral-model` on the built bundle) to
  exercise. Carry D1 into the DTU eval harness, not just the model review.

- **D2 — Skill trigger routing.** "Is this a seam?" → `seam-test`; **"how do I
  amend a frozen clause?"** → `candidate-amendment` (procedural phrasing per
  Finding #2; the permission form *"can I edit…"* routes to `protocol-authority`
  instead); a flipped/red ledger row → `ledger-disposition`. Exercise that the
  trigger phrases pull the right skill. (Encoded on §3.1, §3.2, §3.4
  `invocation`.)

- **D3 — Thin-pointer handoff.** A protocol question arriving in the root
  session must cause **delegation** to `protocol-authority`, not a wung answer
  from the ~400-token `converge-awareness` file. Exercise the temptation to
  answer locally. (Encoded on §1.1 `purpose`.) **POST-BUILD LIVE-EVAL TARGET:**
  like D1, the failure (root answers locally) is a runtime behavior — carry it
  into the live eval harness, not just the from-spec model.

- **D4 — Heavy-doc placement.** Test whether `protocol-authority` carrying
  `LEDGER-FORMAT.md` (alongside `PROTOCOL.md`) dilutes its conformance answers
  versus the `ledger-disposition` skill / `reconciler` owning the ledger
  detail. Exercise a ledger-detail question and a pure-conformance question in
  sequence. (Encoded on §2.1 directives + `context_loading`.)

- **D5 — Convention vs hook.** Exercise scenarios where a session is tempted to
  **directly edit a frozen contract** (bypassing the CANDIDATE flow) or to
  **implement before ENCODE is committed.** Does guidance (the
  `candidate-amendment` skill + `protocol-authority` + the candidate mode's
  directives) hold, or is the `hooks-candidate-guard` (§6.1) structurally
  required? This is the empirical input to OPEN QUESTIONS #1 and #2. (Encoded
  on §5.1, §6.1.)

---

## Notes for the model generator

- **Status is load-bearing.** Distinguish AS-BUILT (confirm behavior), PLANNED
  (verify before build), and DECIDED (question settled — build or defer per the
  recorded decision). The status tag is the first token of each mechanism's
  `purpose`.
- **The two former CANDIDATE mechanisms are now DECIDED** (increment-1 patch):
  the mode (§5.1) is **DEFERRED** (do not build); the hook (§6.1) is **BUILD**
  (increment 2, must intercept delegated-agent writes). A re-run of the
  behavioral model should treat them accordingly, not as open questions.
- **Owner-attention gates must number exactly four** in `full-wave` (§4.3),
  mapping 1:1 to §6 (each item once, no fifth). A fifth gate would itself be a
  protocol defect.

---

## Patch log

- **2026-08-29 — increment-1 patch (owner-ratified).** Applied the behavioral
  model's findings and recorded the two open-question decisions:
  - **Finding #1 (RESOLVED, option b):** the **root is the only router**;
    worker agents (`negotiator`, `reconciler`, `amendment-drafter`) **return
    needs, they do not re-route**. Added the Routing authority note (above §2);
    updated `negotiator` (§2.2) and `reconciler` (§2.3) to carry no
    delegation/spawn/`load_skill` tools.
  - **Finding #2 (disambiguation):** added the *"am I allowed / does this
    conform"* → authority vs *"how do I author/perform X"* → skill rule to §1.1;
    reworded `candidate-amendment` triggers (§3.2) to procedural forms. Mirrored
    into the built `skills/candidate-amendment/SKILL.md` and
    `context/converge-awareness.md`.
  - **Finding #3:** split `full-wave`'s `merge-verify` into `merge` | `verify`
    (§4.3) so the two owner gates attach to clean boundaries; ordering ambiguity
    resolved.
  - **Finding #4:** stated explicitly that standing reconcile (§4.2, §2.3)
    **never synchronously interrupts the owner** — decisions defer to the next
    wave's `priority-kill` gate via the ledger/tracker.
  - **Finding #5 (fidelity):** confirmed §4.3's gate→§6 mapping is correct
    (priority-kill→§6 #4, ratify-changes→§6 #1); the numeric-annotation drift
    lived only in `behavioral-model.md` (immutable) and is noted there, not
    here. No inventory arithmetic exists in this spec to correct.
  - **Decisions (Finding #6):** §5.1 mode → **DECIDED: DEFERRED**; §6.1 hook →
    **DECIDED: BUILD (increment 2)**. D1 and D3 marked **post-build live-eval
    targets** (runtime-routing behaviors a from-spec model cannot exercise).
  - **Build order confirmed:** increment 1 = `reconciler` + `seed-reconcile`
    (this patch); increment 2 = `hooks-candidate-guard`; then
    `negotiator`+`encode`; then `full-wave`. Mode held per §5.1.
  - `behavioral-model.md` left **untouched** as the immutable artifact of the
    model run.

- **2026-08-30 — increment-1 DTU dogfood: composition defect (live-verified).**
  The evaluation harness caught a real composition bug of exactly the class the
  behavioral model flagged as needing *live* verification (limitation #2,
  composition loopholes; and the D1/D3 post-build live-eval targets).
  **Defect — discovery ≠ composition:** `bundle.md` declared `includes:` but no
  `agents:` block, so `converge:reconciler` / `converge:protocol-authority` were
  *discoverable* (`amplifier agents show converge:reconciler` → on) yet never
  *composed* into `coordinator.config["agents"]`; recipe execution failed with
  *"Agent 'converge:reconciler' not found in configuration."* `amplifier bundle
  show converge` listed 41 composed agents, zero `converge:*`.
  **Fix (proven live — a probe recipe spawning `converge:reconciler` returned
  `reconciler-resolved`):** added an `agents: include:` block naming both
  agents.
  **Same-class audit — skills:** the five skills were subject to the identical
  trap. Foundation supplies the `tool-skills` *module* (so `load_skill` exists),
  but its `config.skills` points only at foundation's own skills dir, and
  `converge` had no `tools:` block — so the five `SKILL.md`s were discoverable
  but not composed. **Fix:** added a `tools: - module: tool-skills` block with
  `config.skills: ["@converge:skills"]` (the sanctioned wiring per the skills
  bundle's own convention; a top-level `skills:` key is silently ignored).
  **Lesson for the provenance chain:** in this ecosystem, *discovery is not
  composition* — an artifact showing green in `agents show` / skills visibility
  can still be absent from the composed coordinator. Every agent needs an
  `agents:` entry and every shipped skills dir needs a `tool-skills`
  `config.skills` entry; neither is auto-composed from mere presence on disk.
  Files changed: `bundle.md` (agents + tools blocks). Behavioral-model artifact
  left untouched.

- **2026-08-30 — increment-2 kickoff: hooks-candidate-guard implementation spec.**
  Authored `@converge:docs/design/hooks-candidate-guard-spec.md` (build-ready for
  `modular-builder`) from PROTOCOL.md §5 + the behavioral model's OQ2/Scenario-E
  evidence + the increment-1 review flags. Settled every mechanism decision
  against the kernel contracts: event = `tool:pre` and deny-shape
  (`HOOK_CONTRACT.md` / `HOOKS_API.md`, deny is highest-precedence and
  non-bypassable); guarded-path = `guarded_globs` AND a FROZEN-marker read (so a
  DRAFT contract stays writable during ENCODE, `CANDIDATE-*.md` always allowed);
  block message names file + §5 + remedy; escape hatch = a **ratified CANDIDATE**
  sibling (explicit/auditable/file-scoped/protocol-native — env var rejected as
  ambient), token break-glass as opt-in fallback; `bash` = best-effort literal
  redirect/heredoc scan → deny on match, obfuscation documented as non-coverage;
  fail-closed on guarded-path evaluation error. **Delegated-agent coverage
  settled from the contract, not assumed:** `SESSION_FORK_SPECIFICATION.md`
  Kernel Guarantee #4 ("Independence") + "Configuration Policy" non-provision
  mean the kernel gives **no** hook-inheritance guarantee — sub-sessions mount
  their own config — so §6.1's "must intercept delegated agents" is a
  **live-verified** acceptance property (Test §T5), with compose-into-overlays
  and a target-repo git pre-commit backstop as the mitigations if propagation
  does not hold. Wiring: own-repo `git+…#subdirectory=modules/hooks-candidate-guard`
  (matches attractor's local-module convention), **on by default** (the ratchet's
  teeth). Honest gaps flagged for the owner: (1) real `tool_name`/`tool_input`
  field names at `tool:pre` need a live probe (Test §T2) — defaults are a
  hypothesis; (2) delegated-agent coverage is unprovable from contracts and must
  be closed live (Test §T5). §6.1 updated with the pointer.

- **2026-08-31 — post-publication validation remediation (Finding #1: the
  agents' negative-capability claims were prose-only).** The three worker agents
  ASSERTED capabilities they did not structurally lack: negotiator "no write",
  reconciler + amendment-drafter "no delegation/spawn/load_skill" — all three
  actually INHERITED those tools. Same convention-gap class as OQ2. Initially
  fixed structurally (bundle-level spawn excludes), **revised 2026-09-02 to
  behavioral rules after DTU evidence** — mechanics below retained as the
  verified record of why:
  - **Mechanics (verified):** `agent_config.py:16-65 apply_spawn_tool_policy`
    strips `spawn.exclude_tools` modules from the PARENT tool list on **every**
    spawn; `agent_config.py:99`/`session_spawner.py:298 merge_configs` is the
    real spawn path (recipe steps included); an agent that RE-DECLARES a tool in
    its own frontmatter gets it back (`session_spawner.py:72-132 _filter_tools`:
    `final = (inherited − excluded) + explicit`).
  - **Scope safety (verified by reading foundation frontmatter):** `git-ops`
    declares `tool-bash`+`tool-filesystem`; `modular-builder` declares
    `tool-filesystem/tool-search/tool-bash/tool-lsp`; `file-ops` and `explorer`
    declare filesystem/search(/lsp). **All re-declare the tools they need**, so
    excluding `tool-bash` does NOT strip git/build shell from the live-verified
    recipes; **none declares or needs `tool-delegate`/`tool-skills`**, so
    excluding those is safe.
  - **Decision (revised 2026-09-02, DTU evidence):** NO session-wide
    `spawn.exclude_tools` anywhere in the bundle — neither `bundle.md` nor
    `behaviors/converge.yaml`. A live DTU probe (the probe the old PROPAGATION
    CAVEAT asked for) proved a composed bundle's top-level `spawn:` DOES merge
    into the session mount plan **including via `--app`**, and the exclusion
    then strips bash/delegate/load_skill from EVERY spawned sub-agent in EVERY
    session: `foundation:explorer` in a plain foundation session lost all
    three (functional proof: asked to run a shell command it replied
    BASH_ABSENT); removing both converge registry entries restored a
    byte-identical baseline (causal control). Unacceptable blast radius for a
    composable surface. The agents' negative-capability rules ("no delegation /
    no load_skill / no shell") are now BEHAVIORAL, carried in each agent body;
    each agent declares an explicit self-contained `tools:` block (retained —
    reconciler keeps filesystem/search/bash/work-tracker with sources); the
    candidate-guard hook remains the structural enforcement that matters.
    Per-agent spawn tool policy is filed upstream as the mechanism that would
    make these rules structural without collateral.
  - **RESIDUAL (honest gap — did NOT ship an unverified mechanism):** per-agent
    filesystem-WRITE cannot be removed structurally in this engine (overlay
    `tools:` is additive; the only lever is a `tool-filesystem` `config`
    write-path allowlist whose key I could **not** verify from local sources —
    the module isn't vendored). Rather than ship a config that might silently
    no-op and FALSELY assert "read-only" (re-creating the very defect), the
    negotiator's "no write" is now a **behavioral** instruction ("you must not
    write repo files; your product is minutes") with the residual named here.
    To close it structurally, verify the tool-filesystem write-allowlist config
    key and add `config` to a re-declared `tool-filesystem` for the negotiator.
  - Also fixed: descriptions trimmed under the 600-tok budget (amendment-drafter
    749→477, negotiator 731→560, reconciler 666→529, protocol-authority
    497→442; all `<commentary>` deleted, 2 examples each, WHEN + NOT-authoritative
    boundaries preserved); `protocol-authority` gained `model_role: reasoning`.
  - Note: the original "bundle-global is safe here because no needed agent
    relies on inherited delegate/skills/bash" assumption was FALSIFIED by the
    2026-09-02 DTU probe — the exclusion is session-global across ALL agents
    (host, custom, and foundation alike), and it propagates on the `--app`
    path; hence the revised decision above. Recipe ERRORs + 8/10 recipe
    warnings were triaged as validator-engine/known-agents false positives and
    not acted on.
