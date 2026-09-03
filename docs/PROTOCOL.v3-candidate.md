# Protocol v3 — the plain-language pass (PROPOSAL, NOT RATIFIED)

target: docs/PROTOCOL.md

**This file is a proposal. It is not ratified and it is not in force.**
`docs/PROTOCOL.md` (v2) remains the law, word for word, until the intent
steward — the one person whose direction this work follows — answers below in
their own words. No session may ratify this, including the session that wrote
it. Nobody ratifies their own proposal.

**What it asks for:** that every rule in the protocol survive untouched while
the *words* around them become readable by an amplified information worker —
anyone who has never opened a code editor. Not one rule, phase, gate, or
threshold changes. This is a wording pass, and only a wording pass.

---

## 1. The exact change

Line numbers refer to `docs/PROTOCOL.md` as it stands today (254 lines).
Everything not listed here stays exactly as written.

Three lines in the current text (73, 89–90, 196) name in-house repositories and
documents by shorthand. Those names are elided as `[…]` below rather than
reproduced, because removing reader-specific shorthand is part of what this
proposal is *for*; each is anchored by line number so the replacement is
unambiguous.

### A. Front matter (lines 1–3)

**A1 — line 1.** `# Vision-First, Contract-Driven Development — Protocol v2`
→ `# Vision-First, Contract-Driven Development — Protocol v3 (RATIFIED <the date the steward answers>)`

Status moves into the heading, where a reader meets it first, and nowhere else.
The date is written in only when the steward accepts; until then this heading
does not exist anywhere but in this proposal.

**A2 — line 3.** The status line (currently `**Status:** RATIFIED — 2026-08-29,
by owner, as written.`) is replaced by a line saying who this document is for:

> **Who this is for:** the intent steward who sets direction; the manager
> session that runs the loop; every autonomous work session that closes an item
> against it; and any colleague or coding agent who has to know why work here
> happens the way it does. Its ratification date is in the heading.

Lines 4–10 (what this supersedes, and where the evidence came from) are
untouched.

### B. New section 0 — "Words used here" (inserted after line 10)

The document uses eleven terms of art and defines three of them. This section
adds a table that names each plain word beside the precise word, and defines
both. **It adds no rule.** Every precise term stays valid everywhere it already
appears, so nothing written against v2 — by a person or by an agent — breaks.

> ## 0. Words used here
>
> Every term below is used later in this document. The left column is what to
> say to a colleague; the right column is the precise word this protocol and
> its tooling also use. Both are correct. Neither replaces the other.
>
> | Plain word | Precise term | What it means |
> |---|---|---|
> | intent steward | owner | The one person whose direction this follows, and the only one who can accept a change to a locked document. §6 lists the only four things they are asked. |
> | manager session | orchestrator | The session that runs the loop: gathers evidence, drafts, queues work, merges, and verifies. It proposes. It never accepts its own proposal. |
> | work session | lane | One autonomous session working one item, in its own separate copy of the repository so two sessions never touch the same file. Created for one item, deleted after. |
> | separate copy | worktree | That isolated checkout. |
> | locked | FROZEN | A vision or contract the steward has read and agreed to. Nothing edits a locked document in place — not a person, not an agent. It changes by proposal only (§5). |
> | draft | DRAFT | Written, but not yet agreed to. Still changes by ordinary edit. |
> | proposal | CANDIDATE | The sibling file that asks to change a locked document, named `<contract>.vN-candidate.md`. The older name `CANDIDATE-<topic>.md` still counts. |
> | seam | seam | A surface someone outside this repository's own commits depends on. The full test is in §3.2. |
> | the contract check | conformance kit | The fixtures and machine checks that decide whether a clause is actually kept. |
> | the ledger | conformance ledger | One row per checkable clause, saying whether reality keeps that clause right now. |
> | the lock bar | Freeze Bar | The four conditions in §5 that must *all* be true before the steward locks a document. |
> | toward / away from the contract | convergent / divergent | Which direction a change moves. Toward is cheap; away owes evidence first (§5). |
> | settles | converges | Stops changing, once it is right. |
>
> The six words the ledger uses for a clause's state (§3.3) also have plain
> forms: **Kept** (`CONFORMS`) · **Not yet** (`GAP`) · **Broken**
> (`VIOLATION`) · **Pinned open** (`OPEN-PINNED`) · **Can't check**
> (`NOT-ASSERTABLE`) · **Ruled out** (`EXCLUDED`). The precise names remain the
> ones written in ledger rows; the plain names are for saying out loud.

### C. The opening paragraph (lines 12–17)

Old:

> The owner and the orchestrator negotiate at the contract level. Work is
> derived, never invented: the gap between repo reality and the contracts
> becomes tracker items; autonomous lanes close them; a standing conformance
> audit keeps the gap ledger honest between waves.

New:

> The intent steward and the manager session decide together at the level of
> the contracts, not the code. Work is derived, never invented: wherever the
> repository does not yet keep a contract, that gap becomes a tracker item;
> autonomous work sessions close those items; and a standing check re-measures
> the gaps between rounds, so the list never goes stale.

The last two sentences (lines 15–17: direction changes land in the contract
FIRST; attention below the contract layer is a protocol defect) are unchanged
except that *owner* reads *steward*.

### D. §1 The stack (lines 21–37)

**D1 — line 23.** "Each converges at a different rate" → "Each settles at a
different speed — that is, stops changing once it is right".

**D2 — table cells, lines 30–32.** `frozen between amendments` → `locked
between changes`. `CANDIDATE → ratification` → `proposal → the steward's word`.
`conformance rows, clause-granular` → `one row per checkable clause`.
`briefs, worktrees, DONE.md` → `briefs, separate copies of the repo, a DONE
file`. `disposable` → `disposable — made for one item, deleted after`.

**D3 — lines 34–37.** "it is the open, gap-driven, non-converging loop that
this whole protocol *is*. A human occupies its executor seat today" → "it is
the open-ended, gap-driven loop that this whole protocol *is* — it never
finishes, because there is always a next gap. A person does that job today".
"Everything below it exists to make that seat cheap — and eventually
mechanizable" → "Everything below it exists to make that job cheap — and, one
day, doable by a machine".

### E. §2 The pillars (lines 41–62)

**E1 — lines 43–44.** "Settled invariants." → "Settled rules the rest of this
protocol stands on — an **invariant** is a rule that does not bend."
"converged on independently by at least two sessions" → "reached independently
by at least two separate sessions". "the failure was *measured*, not
hypothesized" → "the failure was *measured in a real run*, not imagined".

**E2 — pillar 2, lines 50–53.** "Fabricated PASS verdicts were measured in two
independent sessions. An agent's or monitor's verdict is a raw observation;
promotion to *proven* requires an artifact check the orchestrator runs itself."
→ "Twice, in separate runs, a session reported PASS for work it had not done.
When an agent or a watching process says something worked, that is an
observation, not a result. It becomes *proven* only when the manager session
checks the actual file, commit, or output for itself."

**E3 — pillar 3, lines 54–55.** "**Amendments are CANDIDATE artifacts, never
direct edits.** Lanes and orchestrators may propose; only the owner ratifies,
in so many words." → "**A locked document changes by proposal, never by direct
edit.** Any session — a work session or the manager session — may write a
proposal (CANDIDATE). Only the steward accepts one, and only by saying so in
words."

**E4 — pillar 4, lines 56–58.** "**Freeze requires a discriminating example.** A
conformance kit must include at least one good/bad fixture pair that actually
discriminates — prose alone freezes nothing." → "**Locking requires an example
that tells right from wrong.** Before a document is locked (FROZEN), the
contract check must carry at least one matched pair — one case that passes, one
that fails — where the check genuinely separates them. Words alone lock
nothing."

**E5 — pillar 5, lines 59–61.** "**A missing artifact is a real result.**
Honest stopping — `N/A` with a reason, `BLOCKED.md` with a cause — always beats
fabricated compliance." → "**Producing nothing is a real answer.** Stopping
honestly — *not applicable, because…*; *blocked, because…* — always beats a
made-up pass." The closing sentence ("The enemy is the successful-looking run
that did nothing") is unchanged.

### F. §3 Artifacts (lines 65–124)

**F1 — lines 67–69.** "The v1 corpus used three contract granularities without
reconciling them. v2 resolves this" → "An earlier version of this protocol used
the word *contract* at three different sizes without ever saying which was
meant. This version settles it".

**F2 — line 73** (the lead line reading `Anatomy (unchanged from the […]
genre, hardened by use):`) → "**A vision** is one page per repository saying
where that repository is going, written as though it were already true. It
contains:"

**F3 — lines 78–81.** "Dated changelog of ratified amendments. Nothing else."
→ "A dated list of accepted changes, and nothing else." "VISION.md is a *thin
pointer* to it, not a restatement of it" → "the vision points at that contract
in a line and does not repeat it". "A repo with no governing contract does not
manufacture one." → "A repository that no contract governs does not invent one
to have one."

**F4 — lines 89–90.** The two example parentheticals name in-house repositories
(`[…]`). Replace both with self-explanatory examples: "A whole class of
customer-facing behaviour is a seam. A file format that some automation reads
is a seam." The surrounding seam test (lines 85–92) is unchanged, including its
last sentence: an internal mechanism is not a seam; it gets tests, not a
contract.

**F5 — lines 94–98.** After "Contract anatomy:", each of the five named parts
gains a plain gloss in the same parenthetical it already has: **Core** (the
promises that are locked) · **Backlogged** (things deliberately not promised
yet, each with the named trigger that would promote it) · **Conformance** (how
the promises get checked) · **Reserved** (names held back on purpose) ·
**Changelog** (accepted changes, dated).

**F6 — lines 100–105.** "carries a feature × surface matrix with three values"
→ "carries a grid of features against the places they could exist, with three
values". The three values keep their names and gain a gloss: **REQUIRED** (must
exist; if it does not, that is a gap worth filing) · **IDIOM** (this place may
do it in its own style, but may never offer *more* than the contract) ·
**EXCLUDED** (deliberately not built). The closing rule ("There is no third
option") is unchanged.

**F7 — line 107 and lines 109–110.** Heading "The conformance ledger —
clause-granular, standing" → "The ledger — one row per clause, always running".
"Rows are *derived from* contracts, one per checkable clause, machine-read
(YAML or equivalent) and CI-executable" → "Every row comes from a contract
clause — never from someone's memory — one row per clause that can be checked,
in a format a machine reads and re-runs automatically".

**F8 — lines 112–119.** The disposition table keeps all six rows and all six
precise names, and gains a leading column with the plain word from §0. Nothing
in the Meaning or Consequence columns changes.

**F9 — lines 121–124.** "**Drift is bidirectional.**" → "**Drift counts in both
directions.**" "any change in the spec↔implementation relationship not
traceable to a ratified amendment or a filed work item files a ledger row" →
"any change in how the document and reality line up that cannot be traced to an
accepted proposal or a filed work item gets its own ledger row".

### G. §4 The loop (lines 128–171)

**G1 — lines 130–132.** "v1's pipeline survives with one structural change" →
"The earlier sequence survives with one structural change". The change itself
(RECONCILE becomes standing; its old slot becomes SEED) is unchanged.

**G2 — the phase block, lines 134–154.** Every phase keeps its number, its
name, and its meaning. Four descriptions gain plain wording:
Phase 3 SEED → "first pass: compare the repository against the contracts and
write the ledger's opening rows";
Phase 5 EXECUTE → "autonomous work sessions claim and close items, each in its
own copy of the repository, each brief naming up front what *not proven* would
look like";
Phase 6 MERGE+VERIFY → "the manager session merges; no verdict counts until the
manager checks the artifact itself";
Phase 7 CLOSE → "report against the lock bar; anything left over is named
honestly".

**G3 — lines 156–158.** "the one measured tracker bypass happened 'because
reconcile wasn't mechanized.'" → "the one measured case of work skipping the
tracker happened *because reconciliation was not automatic*." The conclusion
("Anything that depends on someone remembering to run it will eventually not
run") is unchanged.

**G4 — lines 160–171, lane discipline.** Heading → "Work-session discipline
(carried over intact, all measured)". "Lane briefs carry an **honesty gate**"
→ "Every brief carries an **honesty gate** — it names what *not proven* looks
like before the work starts". "Two lanes in one repo require an explicit
**file-ownership split**" → "Two work sessions in one repository must be given
an explicit split of which files each one owns". "never from pane or session
liveness" → "never from a window still being open or a session still running".
"**Inherited-from-fork artifacts are the #1 false signal.**" → "**A file
inherited from the copy you branched from is the single most common false
signal.**"

### H. §5 Lifecycle (lines 175–209)

**H1 — line 177.** "### DRAFT → FROZEN: the Freeze Bar" → "### From draft to
locked: the lock bar (Freeze Bar)". Line 179 ("All four, no substitutions; only
the owner stamps FROZEN") → "All four must hold. Nothing substitutes for any of
them. Only the steward marks a document locked (FROZEN)." The four conditions
(lines 181–185) are unchanged.

**H2 — line 187.** "### Amending a frozen clause: the CANDIDATE protocol" →
"### Changing a locked clause: the proposal (CANDIDATE) route".

**H3 — lines 189–194.** "A proposal is a sibling file (`CANDIDATE-<topic>.md`),
never an edit." → "A proposal is a sibling file placed next to the locked one —
`<contract>.vN-candidate.md`, or the older `CANDIDATE-<topic>.md` — never an
edit to the locked file itself." The three required parts, the evidence bar (a
real cost paid or a real failure caught; a preference is not evidence), the
literal ratification words, and the dated changelog entry on acceptance are all
unchanged.

**H4 — line 196.** "**Change pricing** (from […])" → "**What a change costs**".
The rule itself is unchanged: toward the contract is cheap, just do it and let
the ledger confirm; away from the contract owes a proposal with evidence before
implementation, or it is debt on arrival.

**H5 — lines 203–209.** "`v<N>` increments only when frozen Core clauses are
removed or made incompatible — i.e., when existing conformant implementations
would break." → "The version number goes up only when a locked promise is
removed or changed in a way that breaks something already keeping it."
"Lanes mid-flight against a superseded clause finish against the version they
were briefed on" → "A work session already running against a replaced clause
finishes against the version it was briefed on". The rest, including declining
a bump that arrives without a migration note, is unchanged.

### I. §6 The owner attention budget (lines 213–224)

Heading → "### 6. What the steward is asked (and nothing else)". "The owner is
in the loop for exactly four things" → "The steward is asked about exactly four
things". The four items are unchanged, word for word. The closing rule is
unchanged, with *owner* reading *steward*: anything outside these four that
reaches the steward is a protocol defect — file it as one, against the
protocol.

### J. §7 What this protocol deliberately resists (lines 228–240)

All nine bullets keep their meaning. Three are reworded:
"Self-ratified amendments — by lanes *or* by the orchestrator." → "Anyone
accepting their own proposal — a work session or the manager session alike."
"LLM judgment where a machine check is possible; unlabeled judgment where it is
not" → "A model's opinion standing in for a check a machine could run; and
judgment used without being labelled as judgment".
"Trusting a monitor's verdict, a health endpoint, a pane's liveness, or an
inherited artifact." → "Trusting a watcher's verdict, a service replying *I am
alive*, a window still being open, or a file inherited from the copy you
branched from."

---

## 2. The evidence

**The cost, paid in this repository.** This project's own first drafts were
written in vocabulary only their author held. Terms including *Freeze Bar*,
*ledger disposition*, and *spawn policy* went into documents that colleagues
were then expected to work from. The steward said so in review: the documents
were not readable by the people meant to use them. That review is why
`contracts/documents.v1.md` exists at all, and why its very first clause reads
"Written for amplified information workers… Terms of art are defined at first
use or not used", with a conformance assert requiring a non-engineer to read
each document and report nothing they had to look up.

**The failure is still present, and it is measurable.** `docs/PROTOCOL.md` —
the document that governs everything else — fails that clause today. Measured
against the current 254-line file:

| Term | First used | Defined | Gap |
|---|---|---|---|
| `ledger` | line 15 | line 107 | 92 lines after first use |
| `seam` | line 30 | line 85 | 55 lines after first use |
| `Freeze Bar` | line 149 (`freeze-bar report`) | line 177 | 28 lines after first use |
| `orchestrator` | line 12 | — | **never defined** (6 uses) |
| `lane` | line 14 | — | **never defined** (12 uses) |
| `worktree` | line 32 | — | **never defined** |
| `FROZEN` | line 30 | — | **never defined in plain words** (9 uses) |
| `disposition` | line 110 | — | table header only (4 uses) |

Eight terms of art; three defined, and each of those three only after a reader
has already met it. A colleague reading top to bottom hits *orchestrator* in
the first body sentence and never learns what it is.

**This is a caught failure, not a preference.** The document is bound by
`contracts/documents.v1.md` clause 1 and by its own pillar of writing things
down honestly. It does not keep that clause. The proposal above closes the gap
without touching a rule.

---

## 3. What does NOT change

Every rule stays exactly as it is. Specifically, and completely:

- **All five layers** of the stack, their order, what governs what, and which
  of them settles.
- **All five pillars**, unchanged in force: vision is never status; a
  self-report is never proof; changes to a locked document are proposals, never
  edits; locking requires a discriminating example; a missing result is a real
  result.
- **All eight phases** (INVESTIGATE, NEGOTIATE, ENCODE, SEED, QUEUE, EXECUTE,
  MERGE+VERIFY, CLOSE), their numbering, their order, and standing RECONCILE
  running on every merge and on schedule.
- **All six ledger states** — `CONFORMS`, `GAP`, `VIOLATION`, `OPEN-PINNED`,
  `NOT-ASSERTABLE`, `EXCLUDED` — with their meanings and consequences
  identical. The plain words are added beside them, never instead of them.
- **The lock bar**: all four conditions, no substitutions, steward-only.
- **The proposal route**: three parts in order, the evidence bar (a cost paid
  or a failure caught; preference is not evidence), the literal ratification
  words, the dated changelog entry on acceptance.
- **What a change costs**: toward the contract cheap, away from it owing
  evidence first.
- **The version-bump rule**, including declining a bump that arrives without a
  migration note.
- **The four things the steward is asked**, word for word, and the rule that
  anything else reaching them is a protocol defect.
- **All nine things this protocol resists.**
- **The seam test**, including that an internal mechanism gets tests, not a
  contract.
- **The three-value grid** (`REQUIRED`, `IDIOM`, `EXCLUDED`) and "there is no
  third option".
- **Every precise term keeps working.** `FROZEN`, `CANDIDATE`, `orchestrator`,
  `owner`, `lane`, `worktree`, `convergent`, `divergent`, and all six state
  names remain valid and remain in the text. Nothing written against v2 — by a
  person, a script, or an agent — has to be rewritten. The plain words are
  added alongside, never as replacements.
- **Lines 4–10** (what this supersedes, and where the evidence came from) and
  **the changelog** are untouched, except for the one new dated entry that
  acceptance of this proposal would add.
- **No file other than `docs/PROTOCOL.md`** is affected. This proposal edits
  nothing. `docs/PROTOCOL.md` is byte-identical to the version on the main
  branch and stays that way unless and until the steward accepts this.

---

## The steward's answer

This proposal is **not ratified**. Only the intent steward can ratify it, and
only in their own words. No session — not the one that wrote this, not a
manager session, not any later reader — may accept it on their behalf.

The four answers are: *ratified* · *ratified with edits* · *declined* ·
*later*.

    Steward's answer: ______________________________________

    Date: ____________

Until that line is filled in, `docs/PROTOCOL.md` v2 is the law, unchanged.
