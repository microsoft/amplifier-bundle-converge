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
- **CANDIDATE (OPEN QUESTION)** — a proposed mechanism that *is itself* one of
  the open design questions. The spec states it and its named alternative; the
  model must help decide whether it is warranted. **The spec does not
  pre-decide it.**

Anti-scope (non-goals) and the five verification objectives are not their own
mechanism types, so they are also woven into individual mechanisms'
`behavioral_directives` (which the extractor captures) — see §C and §D.

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
  attention budget verbatim (§6), and routes: protocol-conformance questions →
  `converge:protocol-authority`; specific procedures → the matching skill. **It
  contains NO protocol rules of its own — only awareness and routing.** Its
  design intent is to make the root session *delegate*, never to let the root
  session answer protocol questions from this file (verification objective D3).
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
    Defers seam judgment to the `seam-test` skill.
  - Delegates deep conformance questions to `protocol-authority` rather than
    carrying the full spec itself (relates to D4).
- **tool_requirements:** read_file, grep (reads investigation briefs; produces
  text minutes)
- **context_loading:** Phase-0 investigation briefs; a thin negotiation-
  relevant slice of `PROTOCOL.md` §1/§4; consults `converge:protocol-authority`
  for conformance calls.
- **exit_conditions:** per-call options + recommendation delivered as minutes;
  stops for the owner to decide.

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
- **tool_requirements:** read_file, grep, glob, bash (run the repo's kit),
  write_file (ledger rows in the target repo), work-tracker (`work_add` /
  `work_file`), git (provenance, content hash)
- **context_loading:** `@converge:docs/LEDGER-FORMAT.md` (full), `PROTOCOL.md`
  §3.3; the target repo's `contracts/` and `ledger/`.
- **exit_conditions:** ledger rows written/updated in the target repo; drift
  rows and GAP/VIOLATION tracker items filed; coverage tripwires pass
  (LEDGER-FORMAT §6); stops.

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
  by** "can I edit this frozen clause?", "how do I change the contract?", "draft
  an amendment" (verification objective D2).
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
- **purpose:** PLANNED. Phase 2 ENCODE (§4). Write VISION.md + contracts from
  ratified negotiation decisions and **commit them before any implementation.**
- **execution_mode:** staged
- **steps:**
  | id | agent | produces | consumes |
  |---|---|---|---|
  | draft-vision-contracts | foundation:file-ops | VISION.md + contract drafts | negotiation minutes (from `negotiator`) |
  | commit-encoded | foundation:git-ops | committed VISION + contracts | ratified drafts |
- **approval_gates:**
  | name | placed_after_step | semantic |
  |---|---|---|
  | ratify-encoded | draft-vision-contracts | validates_previous |
  - `ratify-encoded` = owner attention item #1 (§6.1): the owner ratifies the
    drafted vision/contracts in literal words before they are committed. No
    self-ratification (§C).
- **relationship_to_modes:** runs under the candidate `converge-orchestration`
  mode if adopted; the gate enforces ENCODE-before-implement (relates to D5).

### 4.2 seed-reconcile — **PLANNED**

- **name:** seed-reconcile
- **purpose:** PLANNED. SEED (first ledger population) and standing RECONCILE
  (§4) — **schedulable and run on every merge.** Derive/refresh ledger rows
  from contracts vs repo reality; detect bidirectional drift. Mechanized on
  purpose: "anything that depends on someone remembering to run it will
  eventually not run" (§4).
- **execution_mode:** flat
- **steps:**
  | id | agent | produces | consumes |
  |---|---|---|---|
  | load-contracts | foundation:explorer | contract inventory + tree evidence | target repo |
  | derive-rows | converge:reconciler | ledger rows with dispositions | contract inventory |
  | run-conformance | converge:reconciler | check results (invokes repo kit) | ledger rows |
  | file-drift | converge:reconciler | filed rows + tracker items (GAP/VIOLATION) + bidirectional drift rows | check results |
- **approval_gates:** none (autonomous audit; surfaces a decision only when one
  arises).
- **relationship_to_modes:** standing/background; independent of the owner
  attention budget except when a surfaced row needs a decision.

### 4.3 full-wave — **PLANNED**

- **name:** full-wave
- **purpose:** PLANNED. The zero-touch wave — SEED → QUEUE → EXECUTE →
  MERGE+VERIFY → CLOSE (§4) — with approval gates at **exactly the four owner-
  attention points and nowhere else** (§6). Anything else that would reach the
  owner is a protocol defect (§6; §C).
- **execution_mode:** staged
- **steps:**
  | id | agent | produces | consumes |
  |---|---|---|---|
  | seed | converge:reconciler | populated ledger | contracts + tree |
  | queue | converge:reconciler | tracker items with clause-quoting acceptance (via lane-brief) | ledger rows |
  | execute | foundation:explorer (worktree lanes) | lane commits + DONE.md | tracker items |
  | merge-verify | foundation:git-ops + converge:reconciler | merged main; each verdict promoted only by its own artifact check | lane artifacts |
  | close | converge:reconciler | freeze-bar report; residuals named honestly | merged state |
- **approval_gates:**
  | name | placed_after_step | semantic | owner-attention item |
  |---|---|---|---|
  | priority-kill | queue | authorizes_next | #4 priority/kill before lanes launch |
  | irreversible-ops | merge-verify | authorizes_next | #2 irreversible/destructive calls |
  | human-device-verify | merge-verify | validates_previous | #3 verification only a human/device can do |
  | ratify-changes | close | validates_previous | #1 ratify any vision/contract change or FROZEN stamp |
- **relationship_to_modes:** the whole wave runs under the candidate
  `converge-orchestration` mode if adopted. The four gates map 1:1 to §6's four
  items; the model must confirm **no fifth gate** leaks owner attention below
  the contract layer (§C).

---

## 5. Modes

### 5.1 converge-orchestration — **CANDIDATE (OPEN QUESTION #1)**

> **Open design question, not pre-decided.** Does phase discipline warrant a
> mode, or does pure delegation (the `converge-awareness` pointer + agent
> routing, no mode) suffice? Modes carry real adoption friction. The behavioral
> model must help decide. Both options are stated; neither is chosen here.

- **name:** converge-orchestration
- **purpose:** CANDIDATE (OPEN QUESTION #1). A proposed orchestrator mode that
  keeps loop phase discipline (§4) and reserves owner attention (§6) while a
  wave runs. **ALTERNATIVE UNDER EVALUATION:** no mode — the awareness pointer
  plus agent/skill routing may be enough. The model must determine whether the
  mode earns its cost.
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

### 6.1 hooks-candidate-guard — **CANDIDATE (OPEN QUESTION #2)**

> **Open design question, not pre-decided.** Do "CANDIDATE-not-direct-edit"
> (§5, pillar 3) and "ENCODE-before-implement" (§4 Phase 2) need *structural*
> enforcement (a hook), or do they hold as *convention* via the
> `candidate-amendment` skill + `protocol-authority` guidance? The spec states
> the hook and its alternative; the model must help decide.

- **name:** hooks-candidate-guard
- **purpose:** CANDIDATE (OPEN QUESTION #2). A proposed pre-tool-use hook that
  intercepts file-writing tools and (a) blocks/redirects direct edits to
  `contracts/**`, `docs/VISION.md`, or FROZEN-stamped files into the CANDIDATE
  amendment flow, and (b) blocks implementation writes before ENCODE is
  committed. **ALTERNATIVE UNDER EVALUATION:** no hook — these hold as
  convention. The model must determine whether guidance holds or structural
  enforcement is warranted (verification objective D5).
- **triggers_on:** pre-tool-use on `write_file`, `edit_file`, `apply_patch`.
- **behavior:** inspect the target path and current phase; if a protected path
  is edited directly (not via a `CANDIDATE-<topic>.md`), or an implementation
  write occurs before ENCODE is committed, **block with a remedy message**
  pointing to the CANDIDATE flow / the ENCODE phase; otherwise allow. Fills the
  gap the mode cannot (per-path, which per-tool policies cannot express — §5.1).

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

- **D2 — Skill trigger routing.** "Is this a seam?" → `seam-test`; "can I edit
  this frozen clause?" → `candidate-amendment`; a flipped/red ledger row →
  `ledger-disposition`. Exercise that the trigger phrases pull the right skill.
  (Encoded on §3.1, §3.2, §3.4 `invocation`.)

- **D3 — Thin-pointer handoff.** A protocol question arriving in the root
  session must cause **delegation** to `protocol-authority`, not a wung answer
  from the ~400-token `converge-awareness` file. Exercise the temptation to
  answer locally. (Encoded on §1.1 `purpose`.)

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
  (verify before build), and CANDIDATE/OPEN-QUESTION (help decide, do not
  assume built). The status tag is the first token of each mechanism's
  `purpose`.
- **The two CANDIDATE mechanisms (mode §5.1, hook §6.1) are open questions.**
  Model them as proposed, present their stated alternatives, and let the
  scenarios (esp. D5) inform the decision. Do not treat their existence in this
  spec as a commitment to build them.
- **Owner-attention gates must number exactly four** in `full-wave` (§4.3),
  mapping 1:1 to §6. A fifth gate would itself be a modeled protocol defect.
