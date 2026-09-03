# documents.v1 conformance kit

The runnable definition of **"these documents keep their shape."** Point it at a
repository root and it mechanically asserts the conformance list from
[`contracts/documents.v1.md`](../../contracts/documents.v1.md) over that
repository's contracts, its vision, any proposals beside a contract, its
participant kit, and the templates it ships for other projects to adopt. If it
says PASS, a colleague can pick up any contract there and find the same anatomy.
If it says FAIL, it names the file and the line.

Stdlib only. A document check that needed a package installed would be one more
reason not to run it.

## Run it

```sh
uv run conformance/documents/run.py <repo-root>
```

Output: a JSON report on **stdout** and a human summary on **stderr**. Exit code
is **0** when no rule FAILs, **1** when any rule FAILs. Add `--json-only` to
suppress the stderr summary.

```sh
# a conforming repository  ->  VERDICT: PASS, exit 0
uv run conformance/documents/run.py conformance/documents/fixtures/sample-good

# a broken repository      ->  VERDICT: FAIL (all eighteen checkable rules), exit 1
uv run conformance/documents/run.py conformance/documents/fixtures/sample-bad

# this repository          ->  the real result, whatever it is
uv run conformance/documents/run.py .
```

A work item is not a file in the tree, so rule 9 reads an **export of the work
queue** instead. Point the kit at one, or leave a copy at `docs/work-items.json`
in the target and it is found automatically:

```sh
uv run conformance/documents/run.py . --work-items /tmp/work-items.json
```

The export is a JSON array of objects, or JSONL (one object per line). Each
object may carry `id`, `title`, `description`, `acceptance`, `design`, `notes`.
With no export, rule 9 SKIPs and says so — "nothing to check" and "checked, and
it was fine" are different facts.

## What it checks

**Rows are numbered to the contract's Core clause numbers** — rule 4 judges Core
clause 4 — so a failing rule names the clause it breaks and a reader can go from
a failure straight to the sentence it operationalizes. Where one clause carries
several independent promises, the kit emits one row per promise, lettered inside
the clause (`5a`, `5b`, …). Every row also carries, in the JSON, the `bullet` it
came from in the contract's **Conformance kit asserts** list — or `null`, where
that list names no bullet for the clause at all.

Every Core clause of `documents.v1` has a row here.
`test_every_core_clause_has_a_row` enforces it, so a clause cannot be added to
the contract and quietly go unchecked.

| # | The contract sentence this operationalizes | How the kit checks it |
|---|---|---|
| 1 | Core 1: "Written for amplified information workers … Anyone who has never opened a code editor can read it and know what it means. **Terms of art are defined at first use or not used.**" | **SKIP** — needs a named human reader and a date. No file scan can stand in for a person reporting what they had to look up. This covers **both** halves: whether a term of art needed defining is a judgment about the reader, not about the text. |
| 2 | Core 2: "One contract, one file, about one screen. Fifty to a hundred lines." | Counts lines. Longer is two contracts wearing one filename. |
| 2b | Core 2: "**A vision fits two screens.** A brief is a few sentences." | Counts the vision's lines against **two hundred** — the unit is the contract's own, one sentence earlier ("about one screen. Fifty to a hundred lines"), so two screens is twice it. A ceiling only; the clause sets no floor for a vision. The *brief* half is not asserted: a brief is not an artifact in a repository tree, so there is nothing to point the rule at — said here rather than passed silently. |
| 3 | Core 3: "Line 3 says who builds against this." | Reads line 3 of every `contracts/*.md` and requires the exact `**Who builds against this:**` prefix. |
| 4 | Core 4: "The same sections, in the same order, every time." | Requires *Purpose* → *Core (the teeth)* → *What v1 deliberately does NOT freeze* → *Conformance kit asserts* → *Reserved / open questions*, each present and in that relative order. Headings are matched by prefix, so "Reserved / open questions (NOT frozen)" counts. Any **extra** section is reported in the row's detail rather than failed — the contract fixes the order, and whether extras are permitted is an open question (see below). |
| 5a | Core 5: "Clauses lead with the rule as fact, in bold." | Every numbered clause under `## Core (the teeth)` must continue with `**`. A reader skimming only the bold text has then read the whole contract. |
| 5b | Core 5: "Numbers match the conformance kit's rule table." | **SKIP** — the clause does not say *which* numbering it means, and the kits in this repository disagree. The row still reports what it observes: for every contract with a kit beside it, the contract's Core clause numbers against that kit's rule-table numbers. Deciding is the steward's (see below). |
| 5c | Core 5: "Clauses lead with the rule as fact, in bold, **then one to three plain lines of why**." | Requires a why: every bold-led Core clause must carry plain prose after its bold lead. A clause that asserts and stops is the failure this half of the promise names. The **ceiling** ("one to three") is reported in the row (`observed_why_over_three_source_lines`, `observed_why_over_three_sentences`) and deliberately **not** failed — see below. |
| 6 | Core 6: "Status lives in the H1 parenthetical and nowhere else." | Requires a status parenthetical in the H1 and none anywhere else. Inline `` `code spans` `` are stripped first — clause 6 spells out `(DRAFT)` and `(FROZEN 2026-09-02)` as *examples*, and reading those as a second status would be a fabricated finding. |
| 6b | Core 6: "**Neither vision nor contract carries kept / broken / in-progress;** that lives in the contract check." | Scans the vision **and** every contract — rule 6 reads contracts only. Matched in **status position** alone: inside a parenthetical stamp, or after a `**Status:**` field. A document may say "kept" in a sentence; what clause 6 forbids is a document wearing it as a status. Clause 6 is itself the sentence naming those words, and rule 10b already measured that a prose scan lands on it. |
| 7a | Core 7: "Visions are written as though already true." | Flags roadmap language — "we will build", "we plan to add", "will eventually", "in a future release", "coming soon", "on the roadmap", `TODO`, `TBD`. Deliberately narrow: a bare "will" is legitimate inside a subordinate clause, so only unambiguous plan constructions are flagged. |
| 7b | Core 7: "with a dated changelog whose entries carry evidence" | Requires a `## Changelog` section with at least one `- **YYYY-MM-DD` entry. |
| 7c | Core 7: "end state in the present tense" (the whole-document reading) | **SKIP** — mechanical tense detection reports false findings on legitimate subordinate clauses; judging a whole document's tense needs a reader. Row 7a checks the part that is mechanical. |
| 7d | Core 7: "with a dated changelog **whose entries carry evidence**" | **SKIP** — measured, with the number recorded. This repository's only dated entry names four sources in prose; a literal evidence test (a link, a path, a command, a commit id, a quoted span) fails 1 of 1. Telling evidence-in-prose from an assertion with none is the judgment rule 9b could not make mechanically either. Row 7b checks the mechanical half — that the changelog exists and its entries are dated. |
| 8 | Core 8: "A proposal is `<contract>.vN-candidate.md` and has three parts in order." | For every `*.vN-candidate.md`: requires the exact change, the evidence, and what does not change — present, and **in that order**. SKIPs with a reason when the target has no proposals. |
| 9a | Core 9: "A work item names its contract in one line, defines done in plain words." | Reads a work-queue export (see *Run it*). Per item: it must name a contract that **exists** in the target's `contracts/`, by filename stem and version (`operation.v1`) — a bare prose mention of the word "operation" is not a name a machine can tell from ordinary English — and it must carry a non-empty acceptance, a "Done means", or a `GIVEN`. **"In plain words"** is asserted the way rule 10a asserts it of a document: the sentence that defines done must carry no machine state word. An item is free to quote one in its description — that is how a defect gets reported — but not in its definition of done. SKIPs with a reason when no export is present. |
| 9b | Core 9: "and quotes the feedback or gap it came from" | **SKIP** — measured, with the numbers recorded. Against this repository's live queue the literal test (a blockquote or a quoted span) passes 7 of 24 real items, and most of the 17 it fails *do* point at their origin — in the item's own words rather than the source's. Widening it to accept any clause or item reference passes 20 of 24, but would also pass an item that merely names its contract, which row 9a already checks. Telling a quotation of feedback from a quoted filename needs a reader. The row still reports how many items carry a quotation, in `observed_quoting_a_source` on row 9a. |
| 10a | Core 10: "Plain state words everywhere. Contracts: … Work: … Lanes: …" | Scans every contract and the vision for a **machine** state word standing in prose, across **all three** vocabularies the clause names — contracts (`CONFORMS`, `GAP`, `VIOLATION`, `NOT-ASSERTABLE`, `OPEN-PINNED`, `DIVERGED`, `EXCLUDED`), work (`READY`, `BLOCKED`, `HELD`, `DEFERRED`, `RESOLVED`, `CLOSED`, `IN_PROGRESS`, `IN-PROGRESS`, `WIP`, `TODO`, `DONE`, `WONTFIX`, `BACKLOG`), lanes (`RUNNING`, `IDLE`, `STALE`, `DEAD`). Case-sensitive and word-bounded, with inline code stripped first: a document that must *name* one puts it in a code span; a document that *uses* one as its state word is what clause 10 forbids. Every match on a line is reported, not just the first. |
| 10b | Core 10: the whole-vocabulary reading | **SKIP** — measured, with the finding recorded. Both wider mechanical signals landed on legitimate prose in this repository: the vision's "work in progress" is ordinary English, and clause 6's own "kept / broken / in-progress" is the sentence *forbidding* those words. A rule built on either would be a false-positive machine. Row 10a checks the part that is mechanical. |
| 11a | Core 11: "Technical detail is folded, never in the deciding sentence — … **in a marked section in a document**." | Fails a fenced code block inside a contract's *Purpose* or *Core (the teeth)* — the sections that carry the deciding sentences. Detail belongs in a later, marked section. |
| 11b | Core 11: "… **behind a Details fold in the app** …" | **SKIP** — not this kit's target. This kit reads a repository's documents; an app is markup and behaviour. The promise is asserted where it can be seen: `conformance/surface` rule 5, against `surface.v1` clause 8 ("Technical detail waits behind a Details fold"). Passing it here would be a claim about a file this kit never opened. |
| 12a | Core 12: "Every converged repository carries the participant kit." | Requires `AGENTS.md`, `PINS.md`, `docs/CONTRACTS-README.md`, and `.githooks/pre-push`. |
| 12b | Core 12: the participant kit's source | Requires the five files under `docs/workspace-template/` that a project copies to get that kit. |
| 12c | Core 12: "… **a contracts README (anatomy, index, freeze bar, how to propose), an `AGENTS.md` addendum (converge toward the vision; never edit a locked contract; propose instead; where the ledger is; how to run conformance)** … and a pre-push scan that refuses edits to locked contracts." | Rule 12a asserts those files exist; existence is not the promise. This asserts each file **contains** what clause 12 enumerates for it, topic by topic, and names any topic a file is silent about. `PINS.md` is deliberately absent here: the clause asks it for "hard facts every lane reads first", which enumerates no topic a scan could look for, so only its presence is asserted. |
| 13a | Core 13: "Converge is self-hosting … **its own repository passes the same kit**." | Judges `CONTRACT.md.template` and `VISION.md.template` **as the documents they produce** — the leading HTML instruction comment (which the copier is told to delete) is stripped first. Requires the template to produce line 3 and all five sections, and the vision template to produce a Changelog. |
| 13b | Core 13: "… **its protocol authority checks documents against it** …" | **SKIP** — a claim about a running agent's behaviour in a live session, not about anything in the tree; the same class of promise the composition kit SKIPs as "needs a live Amplifier session". Row 13a checks the half that is a file. |

### The SKIPs are honest, and pinned

Eight rows (1, 5b, 7c, 7d, 9b, 10b, 11b, 13b) are judgments this kit
structurally cannot make. Rather than fabricate a PASS it reports `SKIP` with
the reason, and the self-test pins the SKIP set to exactly
`{1, 5b, 7c, 7d, 9b, 10b, 11b, 13b}` — so a rule cannot quietly drift into
SKIP to dodge a failure. Three of the eight (7d, 9b, 10b) carry a **measured**
reason: the mechanical form was built, run against this repository, and
reported the false findings that retired it. Rules 8 and 9a SKIP *conditionally*,
when a target carries no proposal or no work-item export at all, and the
self-test asserts that specifically: absent evidence must SKIP, never vacuously
PASS.

### Test data is not a document

Discovery skips anything under a `fixtures/` directory (and `.git`, `.venv`,
`node_modules`, and friends). A conformance fixture is a deliberately-broken
artifact — the surface and composition kits each ship one, and so does this
kit. Reporting `sample-bad`'s intentionally-malformed proposal as a violation
of *this repository* would be a fabricated finding, and would mean every kit's
own negative fixture failed the repository that ships it.

### Eight places the kit deliberately does not fabricate a finding

- **A template's own instructions.** A template opens with an HTML comment
  telling the copier to delete it. Reading line 3 of the raw file would report
  that comment as a missing who-line. Rule 13 strips it and judges what the
  template produces.
- **An illustration of a status.** `documents.v1` clause 6 quotes `(DRAFT)` and
  `(FROZEN 2026-09-02)` inside code spans, as examples of the form. Rule 6
  strips inline code before looking for a stray status.
- **A cited gap read as a quoted one.** Row 9b does not fail an item that names
  where it came from without quoting it. Measured, the literal test failed 17 of
  24 real items that mostly *had* named their origin — a rate that says the test
  is wrong, not the queue.
- **Ordinary English that resembles a state word.** Rule 10a matches machine
  tokens only — uppercase and word-bounded. The vision's "work in progress" and
  clause 6's "kept / broken / in-progress" stay unflagged, and `VIOLATES` is not
  `VIOLATION`.
- **A filename in a deciding sentence.** Rule 11a flags a fenced code block, not
  "a path in a bold lead": clause 8's own deciding sentence is "**A proposal is
  `<contract>.vN-candidate.md`**", where the filename *is* the rule.

- **A ceiling that moves when a paragraph is reflowed.** Rule 5c requires a
  why and reports how long it ran; it does not fail a clause for running past
  three of a unit the contract never names.
- **A progress word in an ordinary sentence.** Rule 6b matches a status
  parenthetical or a `**Status:**` field, never loose prose. `documents.v1`
  clause 6 is itself the sentence naming "kept / broken / in-progress".
- **A changelog entry recording which version it described.** This
  repository's vision changelog says "- **2026-09-02 — v1 (DRAFT).**" A status
  stamp outside the H1 is what clause 6 forbids, but a dated entry naming the
  version it recorded is history, not a second source of truth for what the
  document is now. Neither rule 6 nor 6b reaches into it.

Each is covered by its own test.

### Three open questions this kit surfaces rather than decides

**Whether a contract may carry an extra section.** `documents.v1` clause 4 says
"the same sections, in the same order, every time," and lists six. It does not
say whether a contract may carry a **seventh**. `contracts/operation.v1.md` in
this repository carries "Declared dependencies (checked at install)". Rule 4
therefore asserts what the contract unambiguously fixes — presence and order —
and reports any extra section in its detail, so the fact is visible without the
kit inventing a ruling the contract does not make.

**How long "one to three plain lines of why" is.** Clause 5's second promise
has a floor and a ceiling. The floor is unambiguous, so rule 5c enforces it:
after the bold lead there must *be* a why. The ceiling is not. "Lines" has no
wrapping-independent meaning — the same prose rewrapped at a different column
changes the count — and counting sentences is a different unit that answers
differently. Measured across this repository's four contracts (43 bold-led
clauses): a ceiling of three **source lines** flags 14 of them, a ceiling of
three **sentences** flags 3, and 11 clauses are flagged by one unit and not the
other. Failing a third of a set of contracts nobody has reported as unreadable
says the unit is wrong, not the contracts. So rule 5c reports the ceiling in
its row and refuses to fail on it — the same treatment rule 4 gives an extra
section.

**Which numbering clause 5 means.** Clause 5 ends "Numbers match the conformance
kit's rule table" without saying whether the anchor is the Core clauses or the
*Conformance kit asserts* bullets. This kit is numbered to the Core clauses,
because the bullet numbering hid a real gap (see the changelog). The
`composition` and `surface` kits are still numbered to the bullets. Rule 5b
reports that divergence and stays SKIP rather than failing another kit on a
reading the steward has not ratified.

The first and the third are proposed to the steward in
[`contracts/documents.v2-candidate.md`](../../contracts/documents.v2-candidate.md).
The second needs no ruling to be useful: rule 5c enforces the half that is
unambiguous today and records the half that is not.

## Fixtures (the kit's own proof)

- `fixtures/sample-good/` — a **conforming** miniature repository: one contract
  with the full anatomy, a vision with a dated changelog, a well-formed
  proposal beside the contract, a work-item export whose items name their
  contract and quote their source, the four participant-kit files, and the five
  workspace templates. The kit reports **PASS** on all eighteen checkable rules.
- `fixtures/sample-bad/` — an **intentionally broken** repository that violates
  every checkable rule at once: thirty-three lines (2), no who-line (3),
  sections out of order and two missing (4), unbolded clauses (5a), a clause
  that asserts and says no why (5c), a `**Status:**` field in the body (6), a
  vision written as a roadmap (7a) with no changelog (7b), a proposal missing
  two of its three parts (8), a work item that names no contract and another
  that defines done in machine state words (9a), machine state words from all
  three of clause 10's vocabularies standing in prose (10a), a code block among
  the teeth (11a), a vision that runs past two screens (2b) wearing
  `**Status:** in-progress` (6b), and no participant kit and no templates at
  all (12a, 12b, 12c, 13a).

Each fixture file names the rule it violates and why, so the fixture reads as a
worked example of the contract rather than a puzzle.

## Self-test

```sh
uv run --with pytest pytest conformance/documents/tests/ -q
```

Three tests are load-bearing:

- `test_every_rule_has_a_negative_fixture` — every rule the kit emits must
  either FAIL on `sample-bad` or be a declared SKIP with a reason. A rule
  nobody can make fail proves nothing.
- `test_every_core_clause_has_a_row` — every Core clause of `documents.v1` is
  answered by at least one row. A clause with no row is exactly the failure
  this kit was reported for.
- `test_readme_rule_table_is_numbered_to_the_core_clauses` — the table above is
  numbered to the contract's clauses, not to anything else, so the two cannot
  drift apart silently.

## Changelog

- **2026-09-02 — the six reported ledger rows answered (CVG-058, -059, -061,
  -063, -064, -065).** Every one named a `documents.v1` Core clause whose
  promise no row asserted. Read together they said one thing twice: **the kit
  read the contracts and barely read the vision**, and where it did read a
  file it checked that the file existed rather than what it said.

  *What changed.* Rule **2b** measures the vision against two screens — two
  hundred lines, the unit taken from clause 2's own preceding sentence
  (CVG-059). Rule **6b** scans the vision as well as every contract for a
  progress word worn as a status, in status position only (CVG-061). Rule
  **12c** asserts what each participant-kit file *contains*, topic by topic,
  where 12a asserted only that it exists (CVG-064). Rule 13 split into
  **13a** (the templates, unchanged) and **13b** (CVG-065): whether the
  protocol authority checks documents is a live-session claim, not a file.
  Rule **1**'s reason now names the terms-of-art half explicitly (CVG-058),
  and rule **7d** records, with the measurement, why entry-content inspection
  stays a reader's job (CVG-063).

  *Two new refusals to fabricate.* A progress word in an ordinary sentence is
  not a status — clause 6 is itself the sentence naming those words. A dated
  changelog entry recording which version it described is history, not a
  second status. Both are pinned by tests.

- **2026-09-02 — six rules tightened to what their clauses actually say.**
  A follow-up report said six rows under Core 5, 9, 10 and 11 asserted less
  than their clause text. Read against the contract, each was a clause with
  more than one promise where the kit answered only one of them.

  *What changed.* Clause 5's second promise ("then one to three plain lines of
  why") gained rule **5c**: a bold assertion with no why now FAILs, and the
  ceiling is reported rather than failed, because the two candidate units
  disagree — measured, 14 clauses over three source lines against 3 over three
  sentences. Rule **9a** now asserts "in plain words" and not merely "done is
  defined": a definition of done carrying a machine state word FAILs. Rule
  **10a** now covers all three vocabularies clause 10 names — contracts, work
  and lanes — where it previously listed only the ledger dispositions, and
  had no `GAP` at all; every match on a line is reported, not just the first.
  Rule 11 split into **11a** (the document half, unchanged) and **11b** (the
  app half), because "behind a Details fold in the app" is not a document and
  this kit never opens the app — 11b SKIPs and names `conformance/surface`
  rule 8c as the place that does assert it.

  *What did not change.* Rules **5b**, **9b** and **10b** were already honest
  SKIPs carrying their measurement, and stay as they are. `sample-bad` gained
  a negative fixture for each tightening; the SKIP set is re-pinned to
  `{1, 5b, 7c, 9b, 10b, 11b}`.

- **2026-09-02 — numbered to the Core clauses; Core 9, 10 and 11 answered.**
  Three reports said the kit was quiet where the contract has teeth. They shared
  one root cause and one consequence.

  *Root cause.* The rule table was numbered to the contract's **Conformance kit
  asserts** bullets. That list carries **seven bullets for thirteen Core
  clauses** — and Core 10 ("Plain state words everywhere") and Core 11
  ("Technical detail is folded") have no bullet at all. Numbering to the bullets
  therefore made a clause with no bullet *invisible*: there was no row to be
  missing, so nothing looked wrong. Core 9 was visible but SKIPped for a second,
  narrower reason — the kit read only the file tree, and a work item lives in
  the work queue.

  *What changed.* Rows are now numbered to the Core clauses, so every clause has
  a row and a failing rule names the clause it breaks. Rule 9 reads a work-queue
  export (`--work-items`, or `docs/work-items.json`) instead of skipping.
  Rule 10a checks the mechanical part of clause 10 — a machine disposition token
  in a document's prose — and 10b records, with the measurement, why the wider
  reading stays a reader's job. Rule 11 fails a fenced code block among the
  teeth. `test_every_core_clause_has_a_row` now makes a missing clause a test
  failure rather than an absence nobody can see.

  *What is still open.* Clause 5 does not say which numbering it means, and
  clause 4 does not say whether an extra section is permitted. Both are proposed
  to the steward in `contracts/documents.v2-candidate.md`; rules 5b and 4 report
  what they observe and refuse to rule. The `composition` and `surface` kits
  remain numbered to the bullets — they are outside this change, and rule 5b
  names them.
| 14 | Right-sized: one domain component per contract (50–100 lines, one who-builds, one kit) | SKIP — size is checked by rule 2; componentization is a judgment the steward makes; see docs/RIGHT-SIZING.md | — |
