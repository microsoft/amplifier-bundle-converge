# Standing rules for this repository

Read these before your first edit. They apply to every session working here —
human, Amplifier, or another tool's coding agent — and they are the same rules
the people here follow. Nothing on this page needs the Amplifier bundle.

Read next: `PINS.md` (hard facts), `docs/CONTRACTS-README.md` (what a contract
is and how to change one).

## Vocabulary

- **Intent steward** — the person who decides where this project is going. Their
  word is the law you obey.
- **Manager session** — the long-running AI session that runs the project's work
  on the steward's behalf: it plans, briefs, launches, verifies, integrates.
- **Worker session** — a short-lived AI session that takes one bounded piece of
  work in its own copy of the code and returns with proof. You are probably one.
- **Contract** — a short promise this project must keep, in `contracts/`. A
  contract is *locked* (its heading carries `(FROZEN <date>)`) or *draft*.

## 1. Converge toward the vision and the contracts

`docs/VISION.md` says where this project is going. The four contracts in
`contracts/` say what must be true along the way. Everything you do moves the
repository toward them.

- **Work is derived, never invented.** Every change traces to the gap between a
  contract and what exists, or to feedback the steward gave. Name the contract
  your change serves — one line, in the work item and in the commit message.
- **If a contract and the code disagree, the contract wins** — unless you have
  evidence the contract is wrong, in which case see rule 2.
- **If no contract covers what you are doing, stop and say so.** Do not invent
  the promise yourself. A missing contract is a decision for the steward.
- **Converge is self-hosting.** This repository passes the same participant kit
  it ships in `docs/workspace-template/`. A rule we do not follow here is not a
  rule we may ship.

## 2. Never edit a locked contract — propose instead

A file whose heading carries `(FROZEN <date>)` does not change in place. Not for
a typo, not "while I'm in there", not because the change is obviously right.

To change one, add a sibling file named `<contract>.vN-candidate.md` — for
example `contracts/documents.v2-candidate.md` — with three parts, in order:

1. **The exact change**, sentence by sentence.
2. **The evidence** — a cost actually paid or a failure actually caught.
   Preference is not evidence.
3. **What does *not* change.**

The original stays the law until the steward answers with one word: *ratified* ·
*ratified with edits* · *declined* · *later*.

Two guards enforce this, and they are not the same guard. `.githooks/pre-push`
refuses a push that edits a locked file without a candidate beside it;
`hooks-candidate-guard` denies write-shaped tool calls inside an Amplifier
session. `PINS.md` records exactly what each one checks, including where they
currently disagree. **If a guard refuses you, do not work around it.** The
refusal is the rule working. If the guard is wrong, file that as work.

All four contracts are `(DRAFT)` today, so neither guard is currently blocking
anything. The rule still holds — write proposals, not edits, the moment one locks.

## 3. Where the contract check lives

The **ledger** at `ledger/rows.yaml` records, one row per checkable clause,
whether that clause is currently *Kept · Not yet · Broken · Pinned open · Can't
check*. Its format is `docs/LEDGER-FORMAT.md`. It is derived from the contracts,
never hand-edited into agreement with the code.

Run the check for one contract:

```
python conformance/<contract>/run.py
```

The documents kit's rule 9a reads the work queue, which is not a file in this tree — refresh its export with `uv run scripts/export-work-items.py --project converge --out docs/work-items.json` before you trust that rule's verdict.

**Neither the ledger nor the kits exist yet** — they are the next wave of work.
Until they do, a claim that a contract is kept is an opinion, and must be
labelled as one.

Rules for the check itself, once it exists:

- **A check that cannot run reports "Can't check", never a pass.** Where a rule
  cannot yet be enforced, say so rather than pretend.
- **Do not weaken a check to make it green.** A failing check is information.
- **Drift is caught in both directions** — a clause quietly broken, and a clause
  quietly kept without anyone recording it.

## 4. What goes to the intent steward — and what does not

Exactly four kinds of call reach the steward:

1. **Ratify** a change to the vision or a contract.
2. **Irreversible or destructive** choices.
3. **Checks only a person or a device can perform.**
4. **Priority, or stop.**

Anything else that reaches them is a defect in how the work is set up — file it
as one. Do not ask permission for work already in your brief. Do not ask which
of two equivalent implementations to use. Do not narrate progress.

When you do need the steward, state the decision in one sentence, give the two
or three options with their consequences, and say which you recommend.

## 5. Finish honestly

- **Done means seen working**, not "the code is written" and not "the tests I
  wrote pass". Paste the output inline as you produce it.
- **Never claim a result you did not observe.** An unverified claim is worse
  than no claim, because the next session builds on it.
- **Stuck is a real answer.** Name the blocker and what you tried. A blocked
  lane that says so is worth more than a green one that guessed.
- **Stay in your lane.** Edit only the files your brief names. If another file
  needs a change, write that fact down for its owner rather than making it.
