# The contracts

A **contract** is a short promise this project must keep — written for people,
precise enough to check against reality. The **vision** (`docs/VISION.md`) says
where the project is going; the contracts say what must be true along the way.
Together they are the through-line: the same text a colleague reads is the text
every AI session obeys.

New here? Jump to [Quickstart by audience](#quickstart-by-audience).

## The four contracts

| Contract | What it promises | Status |
|---|---|---|
| [`contracts/documents.v1.md`](../contracts/documents.v1.md) | Every vision, contract, proposal, brief, and work item has one readable shape. | Draft |
| [`contracts/operation.v1.md`](../contracts/operation.v1.md) | A manager session carries work from gap to verified result without spending your attention. | Draft |
| [`contracts/surface.v1.md`](../contracts/surface.v1.md) | One place to see direction, one place to see operation; your word asked rarely and answered in seconds. | Draft |
| [`contracts/composition.v1.md`](../contracts/composition.v1.md) | Converge sits lightly on a host and never touches work that isn't its own. | Draft |

## The anatomy every contract follows

One file, one contract, about one screen — fifty to a hundred lines. Same
sections, same order, every time:

1. **H1 with the status in parentheses** — `(DRAFT)` or `(FROZEN <date>)`.
   Status lives here and nowhere else.
2. **Line 3: `**Who builds against this:**`** — two to six lines naming the
   people and systems that would be surprised by a silent change.
3. **Purpose** — why this contract exists, in a short paragraph.
4. **Core (the teeth)** — numbered clauses. Each leads with the rule as a fact,
   in bold, then one to three plain lines of why.
5. **What v1 deliberately does NOT freeze** — each with the trigger that would
   promote it into the teeth.
6. **Conformance kit asserts** — what a machine (or a named reader) checks.
7. **Reserved / open questions** — explicitly not law.
8. **Changelog** — present only once the contract has been amended.

Written for amplified information workers: anyone who has never opened a code
editor can read it and know what it means. Terms of art are defined at first use
or not used. Technical detail is folded into a marked section, never carried in
the deciding sentence.

## When a contract locks

A contract is **draft** until all four are true — then, and only then, the
intent steward locks it and others are turned loose against it:

1. It says what it means.
2. It carries a real example of right and wrong.
3. It can be checked against reality.
4. The steward has read it and agreed.

A contract that meets the bar may be held unlocked on purpose while its
neighbours mature. That is the steward's call, and it is recorded.

Locked contracts carry `(FROZEN <date>)` in the H1. Nothing edits one in place —
not a person, not an AI session. The repository refuses (see `PINS.md`).

## How to propose a change

Write a sibling file named `<contract>.vN-candidate.md` — for example
`contracts/documents.v2-candidate.md`. It has three parts, in order:

1. **The exact change**, sentence by sentence.
2. **The evidence** — a cost actually paid or a failure actually caught.
   Preference is not evidence.
3. **What does *not* change.**

The original stays the law until the steward answers with one word: *ratified* ·
*ratified with edits* · *declined* · *later*. A teammate's proposal and a
manager session's proposal are reviewed identically.

## Quickstart by audience

- **Intent steward** — read `docs/VISION.md`, then the four contracts, then
  `PINS.md`. You make exactly four kinds of call: ratify a change of direction,
  make an irreversible choice, check what only a person or device can check, set
  priority or stop. Anything else that reaches you is a defect — say so.
- **Teammate** — read the one contract your work touches. Disagree with it by
  writing a `<contract>.vN-candidate.md`, not by working around it. Your
  proposal gets the same reading as the manager session's.
- **Coding agent (any tool)** — read `AGENTS.md` first, then `PINS.md`. They
  tell you what converging means here, which files you may never edit, where the
  contract check lives, and which calls go to the steward. You do not need the
  Amplifier bundle to work in this repository correctly.
- **Implementer** — find the contract your change serves and name it in the work
  item. After the change lands, the contract check re-runs and reports in plain
  words: *Kept · Not yet · Broken · Pinned open · Can't check*.

## House rules, stated once

- **Say so rather than pretend.** Where a rule cannot yet be enforced, we write
  that down. A check that cannot run reports *Can't check*, never a pass.
- **Evidence, not preference.** A change to a locked contract owes a cost paid
  or a failure caught. Refinements are cheap; reversals owe evidence first.
- **Derived, never invented.** Every work item traces to the gap between a
  contract and what exists, or to feedback the steward gave, and names the
  contract it serves.
- **Enforced, not aspired to.** Rules that matter are guarded by something that
  refuses, not by an instruction someone might follow.

## Taking this to your own project

`docs/workspace-template/` holds the participant kit: a vision template, a
contract template, an `AGENTS.md` addendum, a pins template, and the pre-push
scan that refuses edits to locked contracts. Copy the five files, fill in the
placeholders, and enable the hook with `git config core.hooksPath .githooks`.
