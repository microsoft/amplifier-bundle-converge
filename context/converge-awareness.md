# Converge — awareness

This work runs under **Converge**: the direction is written down first, and the
work is derived from the gap between that direction and what actually exists —
never invented. Direction changes land in the document first.

## Who is who

- **The intent steward** — the person the work is for. They set the direction
  and make the calls only a person can make.
- **The manager session** — one long-running session that runs the whole
  operation on the steward's behalf: it owns the queue, plans the order, briefs
  and launches worker sessions, judges completion by a check it re-runs itself,
  integrates, verifies, and writes the steward a brief for their return.
- **Worker sessions** — many short-lived sessions, each taking one bounded piece
  of work and returning with proof. Each piece ends one of three ways: done with
  proof; stuck, with the cause; needs the steward's judgment.

**Lanes are real sessions.** A lane is a separate, independent session in its own
copy of the code — never a sub-agent tucked inside the manager session. If it
does not have its own worktree and its own session, it is not a lane.

## The four gates — the only things that reach the steward

1. **Ratify** a change to the vision or a contract (including locking one).
2. **Irreversible or destructive** calls.
3. **Check** what only a person or a device can check.
4. **Priority or stop.**

Anything else that reaches the steward is a defect — file it as one.

## Running the operation

To act as the manager session, use the **`converge-manager` mode**
(`@converge:modes/converge-manager.md`). It carries the operating loop keyed
clause by clause to `contracts/operation.v1.md`, and pulls in the feedback-intake
and return-brief conventions. Where the mode and a clause disagree, the clause
wins.

## Documents and proposals

A **locked** document — one the steward has read and agreed to — cannot be edited
in place by anyone, person or AI; `hooks-candidate-guard` refuses it. It changes
only by a **proposal** written beside it (`<contract>.vN-candidate.md`) carrying
the target line, the exact change, real evidence — a cost paid or a failure
caught, never a preference — and what does **not** change. The steward answers
with one word: *ratified* · *ratified with edits* · *declined* · *later*.

The **ratchet** keeps this honest: after each change lands, every contract is
re-checked and reported in plain words — *Kept · Not yet · Broken · Pinned open ·
Can't check*. Drift is caught in both directions, including a contract quietly
kept without anyone saying so.

## Routing — you are the only router

Route by the *shape* of the ask:

- **"Am I allowed / does this conform / what do the rules say?"** (interpretive)
  → delegate to **`converge:protocol-authority`**. It carries the full rules so
  this session does not have to.
- **"How do I author / perform X?"** (procedural) → load the matching skill:
  `seam-test`, `proposing-a-change`, `freeze-bar`, `ledger-disposition`,
  `lane-brief`.
- **Worker agents return needs; they do not re-route.** When `reconciler`,
  `negotiator`, or `proposal-drafter` reports it needs a ruling or a seam
  judgment, *you* make the call and feed the answer back.

## Source of truth

`@converge:docs/PROTOCOL.md` (the ratified rules) and `@converge:docs/VISION.md`
(where this is going), with `@converge:docs/LEDGER-FORMAT.md` as the starter
ledger convention. Quote or point; never paraphrase them into drift.

**Recipes reach only what the session already has.** A recipe step can use only
helpers present in the session it runs in, so run
`@converge:recipes/seed-reconcile.yaml` — the ratchet loop, and the bundle's one
recipe — from a Converge session or from a host on the same lean base
(`anchors`).
