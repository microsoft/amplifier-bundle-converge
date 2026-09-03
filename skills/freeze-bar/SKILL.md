---
name: freeze-bar
description: >
  Check whether a draft vision or contract is ready to be locked. Use before
  proposing that something be locked, when reviewing the checks behind it, or
  when someone says a document is "done". Covers the four conditions for
  locking, the steward-only decision, and the hold-loosely state — a document
  that meets the bar but is deliberately left unlocked. Applies VISION principle
  2 and PROTOCOL.md §5.
version: 0.2.0
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
