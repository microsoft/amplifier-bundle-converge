# Vision-First, Contract-Driven Development — Protocol v3 (RATIFIED 2026-09-03)

**Who this is for:** the intent steward who sets direction; the manager
session that runs the loop; every autonomous work session that closes an item
against it; and any colleague or coding agent who has to know why work here
happens the way it does. Its ratification date is in the heading.

## 0. Words used here

Every term below is used later in this document. The left column is what to
say to a colleague; the right column is the precise word this protocol and
its tooling also use. Both are correct. Neither replaces the other.

| Plain word | Precise term | What it means |
|---|---|---|
| intent steward | owner | The one person whose direction this follows, and the only one who can accept a change to a locked document. §6 lists the only four things they are asked. |
| manager session | orchestrator | The session that runs the loop: gathers evidence, drafts, queues work, merges, and verifies. It proposes. It never accepts its own proposal. |
| work session | lane | One autonomous session working one item, in its own separate copy of the repository so two sessions never touch the same file. Created for one item, deleted after. |
| separate copy | worktree | That isolated checkout. |
| locked | FROZEN | A vision or contract the steward has read and agreed to. Nothing edits a locked document in place — not a person, not an agent. It changes by proposal only (§5). |
| draft | DRAFT | Written, but not yet agreed to. Still changes by ordinary edit. |
| proposal | CANDIDATE | The sibling file that asks to change a locked document, named `<contract>.vN-candidate.md`. The older name `CANDIDATE-<topic>.md` still counts. |
| seam | seam | A surface someone outside this repository's own commits depends on. The full test is in §3.2. |
| the contract check | conformance kit | The fixtures and machine checks that decide whether a clause is actually kept. |
| the ledger | conformance ledger | One row per checkable clause, saying whether reality keeps that clause right now. |
| the lock bar | Freeze Bar | The four conditions in §5 that must *all* be true before the steward locks a document. |
| toward / away from the contract | convergent / divergent | Which direction a change moves. Toward is cheap; away owes evidence first (§5). |
| settles | converges | Stops changing, once it is right. |

A ledger row's state word — its **disposition** — is one of six (§3.3), and
each of the six also has a plain form: **Kept** (`CONFORMS`) · **Not yet**
(`GAP`) · **Broken** (`VIOLATION`) · **Pinned open** (`OPEN-PINNED`) ·
**Can't check** (`NOT-ASSERTABLE`) · **Ruled out** (`EXCLUDED`). The precise
names remain the ones written in ledger rows; the plain names are for saying
out loud.

---

**Supersedes:** `drumbeat-team-ci/CONTRACT-DRIVEN-WORKFLOW.md` (v1, 2026-08-25).
**Sources:**
- `foundation:docs/PER_REPO_CONVENTIONS.md` — the VISION.md convention this extends
- `cortex-core` — contract-first governance loop; ~40-lane integration evidence; convergent/divergent change pricing
- `drumbeat-team-ci` — the phase pipeline, proven end-to-end twice (once at 18 items, once 3 hours zero-touch)
- `better-attractor` — conformance matrix, CANDIDATE amendment protocol, disposition vocabulary, 40-hour session forensics
- `~/dev/ai-context/workflows/` — the cross-session corpus these were distilled from

---

The intent steward and the manager session decide together at the level of
the contracts, not the code. Work is derived, never invented: wherever the
repository does not yet keep a contract, that gap becomes a tracker item;
autonomous work sessions close those items; and a standing check re-measures
the gaps between rounds, so the list never goes stale. Direction changes land
in the contract FIRST. The steward's attention is spent only at the contract
layer — everything below it that reaches the steward is a protocol defect.

---

## 1. The stack

Five layers. Each settles at a different speed — that is, stops changing
once it is right; each is governed by the layer above it.

| Layer | Artifact | Converges? | Changed by |
|---|---|---|---|
| **Strategy** | the negotiation loop itself | never — permanently open | owner judgment |
| **Vision** | `docs/VISION.md`, one per repo | slowly | evidence-gated, owner-ratified amendment |
| **Contracts** | `contracts/<seam>.v<N>.md` | locked between changes | proposal → the steward's word |
| **Ledger** | one row per checkable clause | continuously re-derived | machine checks + filed rows |
| **Lanes** | briefs, separate copies of the repo, a DONE file | disposable — made for one item, deleted after | claimed and closed |

The Strategy layer is named so we stop pretending it's absent: it is the
open-ended, gap-driven loop that this whole protocol *is* — it never
finishes, because there is always a next gap. A person does that job today.
Everything below it exists to make that job cheap — and, one day, doable by
a machine.

---

## 2. The pillars

Settled rules the rest of this protocol stands on — an **invariant** is a
rule that does not bend. Each was reached independently by at least two
separate sessions; where noted, the failure was *measured in a real run*,
not imagined.

1. **Vision is never status.** The page states the destination as though
   already true. A page that must be edited when a feature ships is a
   status report wearing a vision's name. Shipped/in-flight/sequencing
   live in the tracker.
2. **A self-report is never proof.** Twice, in separate runs, a session
   reported PASS for work it had not done. When an agent or a watching
   process says something worked, that is an observation, not a result. It
   becomes *proven* only when the manager session checks the actual file,
   commit, or output for itself.
3. **A locked document changes by proposal, never by direct edit.** Any
   session — a work session or the manager session — may write a proposal
   (CANDIDATE). Only the steward accepts one, and only by saying so in
   words.
4. **Locking requires an example that tells right from wrong.** Before a
   document is locked (FROZEN), the contract check must carry at least one
   matched pair — one case that passes, one that fails — where the check
   genuinely separates them. Words alone lock nothing.
5. **Producing nothing is a real answer.** Stopping honestly — *not
   applicable, because…*; *blocked, because…* — always beats a made-up
   pass. The enemy is the successful-looking run that did nothing.

---

## 3. Artifacts and their scope

An earlier version of this protocol used the word *contract* at three
different sizes without ever saying which was meant. This version settles
it: they were never competing scopes — they are three different artifacts.

### 3.1 VISION.md — one per repo

**A vision** is one page per repository saying where that repository is
going, written as though it were already true. It contains:

- The desired end state, written as though already true.
- Operating principles — small, numbered, quotable.
- **What this repo deliberately resists** — required section.
- A dated list of accepted changes, and nothing else.
- Where a governing contract exists, the vision points at that contract in
  a line and does not repeat it.
- A repository that no contract governs does not invent one to have one.

### 3.2 Contracts — one per seam

**A seam is a surface someone outside this repo's own commits depends on.**
The test: *if this changed silently, who breaks?* If the answer names
anyone beyond this repo — a sibling client, another team, an automation
consuming a file format, a future machine executor — it is a seam and gets
a contract. A whole class of customer-facing behaviour is a seam. A file
format that some automation reads is a seam. An internal mechanism is not a
seam; it gets tests, not a contract.

Contract anatomy: **Core** (the promises that are locked) · **Backlogged**
(things deliberately not promised yet, each with the named trigger that
would promote it) · **Conformance** (how the promises get checked) ·
**Reserved** (names held back on purpose) · **Changelog** (accepted
changes, dated).

Where a contract governs multiple implementations, it carries a grid of
features against the places they could exist, with three values:
**REQUIRED** (must exist; if it does not, that is a gap worth filing),
**IDIOM** (this place may do it in its own style, but may never offer
*more* than the contract), **EXCLUDED** (deliberately not built). A
capability that exists on one surface and nowhere else is either convergent
behavior that belongs in the contract, or it is debt. There is no third
option.

### 3.3 The ledger — one row per clause, always running

Every row comes from a contract clause — never from someone's memory — one
row per clause that can be checked, in a format a machine reads and re-runs
automatically. Each row carries a disposition:

| Plain word | Disposition | Meaning | Consequence |
|---|---|---|---|
| Kept | `CONFORMS` | check passes | none |
| Not yet | `GAP` | REQUIRED clause, no implementation | tracker item |
| Broken | `VIOLATION` | implementation contradicts a frozen clause | tracker item, or CANDIDATE amendment if evidence says the clause is wrong |
| Pinned open | `OPEN-PINNED` | undecided call; current behavior asserted by a check *without forging a decision* | ledger row, revisited at negotiation — an undecided call is a ledger row, not a vision |
| Can't check | `NOT-ASSERTABLE` | no machine check possible; judgment-only, named as such | reviewed at cadence, never silently trusted |
| Ruled out | `EXCLUDED` | contract forbids it | presence is a violation |

**Drift counts in both directions.** Moving away from a frozen clause is
drift. Silently moving *back* toward spec from a pinned behavior is also
drift — any change in how the document and reality line up that cannot be
traced to an accepted proposal or a filed work item gets its own ledger row.

---

## 4. The loop

The earlier sequence survives with one structural change: RECONCILE stops
being a phase you can skip and becomes a standing audit. The phase slot it
occupied becomes SEED — the first population of the ledger.

```
Phase 0  INVESTIGATE   never negotiate from memory — disposable explorers
                       gather evidence first (self-contained briefs)
Phase 1  NEGOTIATE     owner + orchestrator at decision level; minutes,
                       not documents — options + recommendation per call
Phase 2  ENCODE        VISION.md + contracts written and COMMITTED before
                       any implementation
Phase 3  SEED          first pass: compare the repository against the
                       contracts and write the ledger's opening rows
Phase 4  QUEUE         ledger rows become tracker items with
                       clause-quoting acceptance criteria
Phase 5  EXECUTE       autonomous work sessions claim and close items, each
                       in its own copy of the repository, each brief naming
                       up front what *not proven* would look like
Phase 6  MERGE+VERIFY  the manager session merges; no verdict counts until
                       the manager checks the artifact itself
Phase 7  CLOSE         report against the lock bar; anything left over is
                       named honestly

Standing RECONCILE     conformance runs on every merge and on schedule;
                       drift in either direction files ledger rows; QUEUE
                       draws from the ledger, not from memory
```

The v1 diagnosis stands as the justification: the one measured case of work
skipping the tracker happened *because reconciliation was not automatic*.
Anything that depends on someone remembering to run it will eventually not
run.

### Work-session discipline (carried over intact, all measured)

- Every brief carries an **honesty gate** — it names what *not proven*
  looks like before the work starts.
- Two work sessions in one repository must be given an explicit split of
  which files each one owns.
- Completion is knowable only from git artifacts (`DONE.md`, commits) —
  never from a window still being open or a session still running.
- **A file inherited from the copy you branched from is the single most
  common false signal.** Check provenance (commit, mtime) before crediting
  any artifact as this lane's work.
- Health endpoints are not a working system. Numbers reported are real or
  absent.

---

## 5. Lifecycle

### From draft to locked: the lock bar (Freeze Bar)

All four must hold. Nothing substitutes for any of them. Only the steward
marks a document locked (FROZEN).

1. The spec is written.
2. A machine-checkable conformance kit exists, with at least one
   discriminating good/bad fixture pair.
3. At least one real implementation passes it.
4. A worked example exists end-to-end.

### Changing a locked clause: the proposal (CANDIDATE) route

A proposal is a sibling file placed next to the locked one —
`<contract>.vN-candidate.md`, or the older `CANDIDATE-<topic>.md` — never
an edit to the locked file itself. It carries: the exact diff · evidence
citations (a real cost paid or a real failure caught — a preference is not
evidence) · an explicit **"what does NOT change"** section · a ratification
ask. The owner answers with the literal word: *ratified* / *ratified as
edited* / declined-with-reason. On ratification the edit lands with a dated
changelog entry.

**What a change costs**: a *convergent* change — toward the contract — is
cheap; just do it and let the ledger confirm. A *divergent* change owes an
amendment-with-evidence before implementation, or it is debt on arrival.

### Version bumps

The version number goes up only when a locked promise is removed or changed
in a way that breaks something already keeping it. Everything else is an
amendment. **Backlogged sections with named promotion triggers exist
precisely so that version bumps are rare.** A bump proposed without a
migration note for every known implementation is declined on form. A work
session already running against a replaced clause finishes against the
version it was briefed on; the ledger files the delta as new rows.

---

## 6. What the steward is asked (and nothing else)

The steward is asked about exactly four things:

1. **Ratifying** vision and contract changes (including FROZEN stamps).
2. **Irreversible or destructive calls.**
3. **Verification only a human or a device can perform.**
4. **Priority and kill decisions.**

Never for lane monitoring, merge mechanics, routine gap-filing, or status
assembly. Anything outside these four that reaches the steward is a
protocol defect — file it as one, against the protocol.

---

## 7. What this protocol deliberately resists

- Editing a vision page into agreement with a drifted tree.
- Status, progress, or sequencing in vision documents.
- Anyone accepting their own proposal — a work session or the manager
  session alike.
- One-shot reconciliation and remembered audits.
- A model's opinion standing in for a check a machine could run; and
  judgment used without being labelled as judgment (`NOT-ASSERTABLE` exists
  so judgment is named, never smuggled).
- Manufacturing contracts for repos with no seam.
- Version bumps used to dodge amendment evidence.
- Trusting a watcher's verdict, a service replying *I am alive*, a window
  still being open, or a file inherited from the copy you branched from.
- The owner's attention anywhere below the contract layer.

---

## Changelog

- **2026-09-03 — v3 wording fix (`converge-3l7`).** §0 "Words used here" now
  sits above the Supersedes/Sources credits, and a ledger row's state word is
  named there as its *disposition*, so *lane*, *CANDIDATE*, *disposition* and
  *convergent / divergent* are each defined at their first use in this file
  (documents.v1 clause 1). Placement and one gloss only — no rule, gate,
  phase, threshold or freeze condition changed in meaning, and the
  rule-by-rule table below is untouched.
- **2026-09-03 — v3 RATIFIED.** The steward ratified
  `docs/PROTOCOL.v3-candidate.md` with the word *"ok, all lgtm, continue"*;
  the record is `docs/workflow/owner-ratifications-2026-09-03.md`, and the
  candidate file stays in the tree as the decision record. **A wording pass,
  and only a wording pass.** §0 "Words used here" was added; every term of
  art is now defined at first use; a plain word is placed beside each
  precise one (intent steward/owner, manager session/orchestrator, work
  session/lane, separate copy/worktree, locked/FROZEN, draft/DRAFT,
  proposal/CANDIDATE, the contract check/conformance kit, the
  ledger/conformance ledger, the lock bar/Freeze Bar, toward-or-away/
  convergent-or-divergent, settles/converges). Every precise term remains
  valid everywhere it already appeared, so nothing written against v2 — by
  a person, a script, or an agent — has to be rewritten. Three lines that
  named in-house repositories and documents by shorthand (the VISION
  anatomy lead, the two seam examples, and the change-pricing attribution)
  now read as self-explanatory prose. No rule, gate, phase, threshold, or
  freeze condition changed in meaning. That claim is checked rule by rule
  below.

  | v2 rule, gate or phase | Status | Where it now reads in v3 |
  |---|---|---|
  | Stack: five layers, each governed by the layer above | unchanged in meaning | §1 lead — "settles at a different speed" replaces "converges at a different rate" |
  | Stack: Strategy — never converges, changed by owner judgment | unchanged in meaning | §1 table, row *Strategy* — verbatim |
  | Stack: Vision — slow, evidence-gated, owner-ratified amendment | unchanged in meaning | §1 table, row *Vision* — verbatim |
  | Stack: Contracts — frozen between amendments, CANDIDATE → ratification | unchanged in meaning | §1 table, row *Contracts* — "locked between changes", "proposal → the steward's word" |
  | Stack: Ledger — clause-granular, continuously re-derived | unchanged in meaning | §1 table, row *Ledger* — "one row per checkable clause" |
  | Stack: Lanes — disposable, claimed and closed | unchanged in meaning | §1 table, row *Lanes* — "separate copies of the repo, a DONE file … made for one item, deleted after" |
  | Strategy layer is the open, non-converging loop; a human holds it today | unchanged in meaning | §1 closing paragraph — "open-ended … it never finishes … a person does that job today" |
  | Pillar 1 — vision is never status | unchanged in meaning | §2.1 — verbatim |
  | Pillar 2 — a self-report is never proof; only an artifact check promotes to *proven* | unchanged in meaning | §2.2 — reworded, same bar |
  | Pillar 3 — amendments are CANDIDATE artifacts, never direct edits; only the owner ratifies | unchanged in meaning | §2.3 — "a locked document changes by proposal, never by direct edit" |
  | Pillar 4 — freeze requires a discriminating good/bad fixture pair | unchanged in meaning | §2.4 — "locking requires an example that tells right from wrong" |
  | Pillar 5 — a missing artifact is a real result | unchanged in meaning | §2.5 — "producing nothing is a real answer"; closing sentence verbatim |
  | VISION.md is one per repo | unchanged in meaning | §3.1 heading and lead |
  | VISION anatomy — end state written as though already true | unchanged in meaning | §3.1 bullet 1 — verbatim |
  | VISION anatomy — operating principles, small, numbered, quotable | unchanged in meaning | §3.1 bullet 2 — verbatim |
  | VISION anatomy — "What this repo deliberately resists" is required | unchanged in meaning | §3.1 bullet 3 — verbatim |
  | VISION anatomy — dated changelog of ratified amendments, nothing else | unchanged in meaning | §3.1 bullet 4 — "a dated list of accepted changes, and nothing else" |
  | VISION is a thin pointer to a governing contract, not a restatement | unchanged in meaning | §3.1 bullet 5 |
  | A repo with no governing contract does not manufacture one | unchanged in meaning | §3.1 bullet 6 |
  | Seam definition and the test "if this changed silently, who breaks?" | unchanged in meaning | §3.2 — verbatim; only the two examples are de-branded |
  | An internal mechanism is not a seam; it gets tests, not a contract | unchanged in meaning | §3.2 closing sentence — verbatim |
  | Contract anatomy — Core · Backlogged · Conformance · Reserved · Changelog | unchanged in meaning | §3.2 — all five parts, glosses in plain words |
  | Backlogged clauses carry named promotion triggers | unchanged in meaning | §3.2 — "each with the named trigger that would promote it" |
  | Feature × surface matrix with three values | unchanged in meaning | §3.2 — "a grid of features against the places they could exist" |
  | REQUIRED / IDIOM / EXCLUDED, and idiom may never exceed the contract in features | unchanged in meaning | §3.2 — names kept, glosses added |
  | "There is no third option" | unchanged in meaning | §3.2 — verbatim |
  | Ledger rows are derived from contracts, one per checkable clause, machine-read and CI-executable | unchanged in meaning | §3.3 — "never from someone's memory … a machine reads and re-runs automatically" |
  | Six dispositions, their meanings and their consequences | unchanged in meaning | §3.3 table — all six rows and both columns verbatim; a plain-word column added in front |
  | Drift is bidirectional; an untraceable change files a ledger row | unchanged in meaning | §3.3 — "drift counts in both directions" |
  | RECONCILE is standing, not a skippable phase; its old slot becomes SEED | unchanged in meaning | §4 lead — verbatim |
  | Phase 0 INVESTIGATE | unchanged in meaning | §4 block — verbatim |
  | Phase 1 NEGOTIATE | unchanged in meaning | §4 block — verbatim |
  | Phase 2 ENCODE — written and COMMITTED before any implementation | unchanged in meaning | §4 block — verbatim |
  | Phase 3 SEED — first reconciliation populates the ledger | unchanged in meaning | §4 block — "first pass: compare the repository against the contracts" |
  | Phase 4 QUEUE — clause-quoting acceptance criteria | unchanged in meaning | §4 block — verbatim |
  | Phase 5 EXECUTE — worktree-isolated lanes, honesty gate in every brief | unchanged in meaning | §4 block — "its own copy of the repository … what *not proven* would look like" |
  | Phase 6 MERGE+VERIFY — every verdict promoted only by its own artifact check | unchanged in meaning | §4 block — "no verdict counts until the manager checks the artifact itself" |
  | Phase 7 CLOSE — freeze-bar report, residuals named honestly | unchanged in meaning | §4 block — "report against the lock bar; anything left over is named honestly" |
  | Standing RECONCILE — every merge and on schedule; QUEUE draws from the ledger, not memory | unchanged in meaning | §4 block — verbatim |
  | The tracker-bypass diagnosis justifying a standing audit | unchanged in meaning | §4 — "because reconciliation was not automatic"; conclusion verbatim |
  | Lane discipline — honesty gate in every brief | unchanged in meaning | §4, work-session discipline, bullet 1 |
  | Lane discipline — file-ownership split for two lanes in one repo | unchanged in meaning | §4, work-session discipline, bullet 2 |
  | Lane discipline — completion is knowable only from git artifacts | unchanged in meaning | §4, work-session discipline, bullet 3 |
  | Lane discipline — inherited artifacts are the #1 false signal | unchanged in meaning | §4, work-session discipline, bullet 4 |
  | Lane discipline — health endpoints are not a working system | unchanged in meaning | §4, work-session discipline, bullet 5 — verbatim |
  | Freeze Bar — all four, no substitutions, owner-only stamp | unchanged in meaning | §5 — "all four must hold … only the steward marks a document locked (FROZEN)" |
  | Freeze Bar 1 — the spec is written | unchanged in meaning | §5 — verbatim |
  | Freeze Bar 2 — a machine-checkable kit with a discriminating good/bad pair | unchanged in meaning | §5 — verbatim |
  | Freeze Bar 3 — at least one real implementation passes it | unchanged in meaning | §5 — verbatim |
  | Freeze Bar 4 — a worked example exists end-to-end | unchanged in meaning | §5 — verbatim |
  | A proposal is a sibling file, never an edit | unchanged in meaning | §5 — both sanctioned filenames named |
  | A proposal carries diff · evidence · "what does NOT change" · ratification ask | unchanged in meaning | §5 — verbatim |
  | Evidence bar — a real cost paid or a real failure caught; preference is not evidence | unchanged in meaning | §5 — verbatim |
  | The owner answers with the literal word | unchanged in meaning | §5 — verbatim |
  | On ratification the edit lands with a dated changelog entry | unchanged in meaning | §5 — verbatim |
  | Change pricing — convergent is cheap; divergent owes evidence before implementation | unchanged in meaning | §5 — "what a change costs"; rule verbatim |
  | Version bump only when frozen Core clauses are removed or made incompatible | unchanged in meaning | §5 — "a locked promise … removed or changed in a way that breaks something already keeping it" |
  | Everything else is an amendment | unchanged in meaning | §5 — verbatim |
  | Backlogged sections with named triggers exist so bumps are rare | unchanged in meaning | §5 — verbatim |
  | A bump without a migration note is declined on form | unchanged in meaning | §5 — verbatim |
  | Mid-flight lanes finish against the version they were briefed on; the ledger files the delta | unchanged in meaning | §5 — "a work session already running against a replaced clause" |
  | The owner is in the loop for exactly four things | unchanged in meaning | §6 — "the steward is asked about exactly four things" |
  | Owner call 1 — ratifying vision and contract changes, including FROZEN stamps | unchanged in meaning | §6, item 1 — word for word |
  | Owner call 2 — irreversible or destructive calls | unchanged in meaning | §6, item 2 — word for word |
  | Owner call 3 — verification only a human or a device can perform | unchanged in meaning | §6, item 3 — word for word |
  | Owner call 4 — priority and kill decisions | unchanged in meaning | §6, item 4 — word for word |
  | Never for lane monitoring, merge mechanics, routine gap-filing, or status assembly | unchanged in meaning | §6 closing — verbatim |
  | Anything else reaching the owner is a protocol defect — file it as one | unchanged in meaning | §6 closing |
  | Resists — editing a vision page into agreement with a drifted tree | unchanged in meaning | §7 bullet 1 — verbatim |
  | Resists — status, progress or sequencing in vision documents | unchanged in meaning | §7 bullet 2 — verbatim |
  | Resists — self-ratified amendments, by lanes or by the orchestrator | unchanged in meaning | §7 bullet 3 — "anyone accepting their own proposal" |
  | Resists — one-shot reconciliation and remembered audits | unchanged in meaning | §7 bullet 4 — verbatim |
  | Resists — LLM judgment where a machine check is possible; unlabeled judgment where it is not | unchanged in meaning | §7 bullet 5 — reworded; `NOT-ASSERTABLE` clause verbatim |
  | Resists — manufacturing contracts for repos with no seam | unchanged in meaning | §7 bullet 6 — verbatim |
  | Resists — version bumps used to dodge amendment evidence | unchanged in meaning | §7 bullet 7 — verbatim |
  | Resists — trusting a monitor, a health endpoint, a pane's liveness, or an inherited artifact | unchanged in meaning | §7 bullet 8 — reworded, same four |
  | Resists — the owner's attention below the contract layer | unchanged in meaning | §7 bullet 9 — verbatim |

- **2026-08-29 — RATIFIED.** Owner ratified v2 as written.
- **2026-08-26 — v2 DRAFT.** Synthesized from cortex-core, drumbeat-team-ci,
  and better-attractor session evidence plus the `ai-context/workflows`
  corpus. Structural changes from v1: RECONCILE becomes a standing audit
  (phase slot renamed SEED); contract scope resolved as one-per-seam with
  the ledger as a distinct clause-granular layer; disposition vocabulary
  adopted (`OPEN-PINNED`, `NOT-ASSERTABLE`); Strategy layer named; owner
  attention budget made an enumerated contract with defect-filing teeth.
  Awaiting owner ratification.
