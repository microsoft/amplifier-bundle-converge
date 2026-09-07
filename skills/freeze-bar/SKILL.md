---
name: freeze-bar
description: >
  Use before proposing that a draft vision or contract be locked, when reviewing the checks
  behind a lock, when someone calls a document "done", or at the moment of stamping one. Covers
  the four locking conditions, the steward-only decision, the hold-loosely state (meets the bar,
  deliberately left unlocked) and the one-edit rule that keeps a freeze from half-landing.
  Applies VISION principle 2 and PROTOCOL.md §5.
version: 0.3.0
---

# When a document is ready to be locked

A vision or contract starts as a **draft** and becomes **locked** when it meets
four conditions (`docs/PROTOCOL.md` §5 calls those conditions the Freeze Bar and
stamps a locked document `FROZEN`). Locked means it cannot be edited in place by
anyone; it changes only by written proposal, backed by evidence.

## The four conditions — all of them, no substitutions

1. **It says what it means.** The promises are written down, plainly enough that
   someone who has never opened a code editor knows what they commit to.
2. **It carries a real example of right and wrong.** At least one pair that
   actually tells conformant from non-conformant. Prose alone locks nothing — a
   pair of examples that both pass, or that differ in something the contract
   doesn't govern, has not met this condition however much text surrounds it.
3. **It can be checked against reality.** A check exists that a machine can run,
   at least one real implementation passes it, and the whole thing has been
   walked end to end once.
4. **The intent steward has read it and agreed.**

## Only the intent steward locks a document

Locking is one of the four calls that reach the steward. Anyone else — a manager
session, a worker session, a teammate — can show that the four conditions are
met. That is a recommendation. The lock is the steward's word.

## Writing the lock: ONE edit, never two

A document is locked by editing its own H1 — and the record of that lock is
more text in the *same file*. So the two halves must land in **one write**:

1. the H1 stamped `(FROZEN <date>)`, and
2. the `## Changelog` entry recording the ratification,

together, in a single edit and a single commit.

Do it in two edits and the second one is refused, whichever order you pick.
The guard reads the file's own text: the moment the H1 says FROZEN the
document is law, and a locked document takes no edit in place — including the
edit that would say why it was locked. The file is left **half-frozen**: the
status word landed, the record of why it landed did not, and nothing can
repair it in place afterwards.

That is measured, not hypothetical. On 2026-09-06 a manager session locked a
project's vision by stamping the H1, then tried to add the changelog line as a
separate edit; its own guard refused, the vision sat half-frozen, and the
session never got past it (`evaluations/adopter/RESULT.md` scenario 2,
`converge-p17d`).

What the one write looks like:

```markdown
# sensorlog — Vision (FROZEN 2026-09-06)

...

## Changelog

- **2026-09-06 — locked (FROZEN 2026-09-06).** The steward answered the four
  Freeze Bar conditions; they are recorded verbatim in
  `docs/workflow/owner-ratifications-2026-09-06.md`.
- **2026-09-05 — v1 (DRAFT).** First written.
```

The entry is history, not a second status: `documents.v1` Core 6 puts status
in the H1 and nowhere else, and the changelog is not where it looks. Core 7 is
what asks for the entry, and asks it to carry its evidence — so name where the
four answers are kept rather than asserting that they were given.

`hooks-candidate-guard` now refuses the stamp-alone write outright, before
anything is written, so the document stays a draft and the combined write can
simply be re-issued. **If it refuses you, do not reach for the proposal path**
— the document is not locked yet. Put the two halves in one write.

## Hold loosely: met the bar, deliberately left open

A document may meet all four conditions and still be left unlocked on purpose,
while the documents around it mature and are likely to move it. That is the
**hold-loosely** state, and it is legitimate — but it is a decision, not a
drift:

- The bar is met, and that is written down.
- The document is deliberately not locked.
- The steward's call is recorded, with the reason, in the document itself.

An unlocked document that nobody decided to leave unlocked is not holding
loosely; it is a draft that stalled.

## If a condition cannot be met yet, say so

A condition that genuinely cannot be met is a real result. Record it as *can't
check*, with the reason, or write down the blocker and its cause. A missing
answer beats an invented one, and nothing is locked around a gap.
