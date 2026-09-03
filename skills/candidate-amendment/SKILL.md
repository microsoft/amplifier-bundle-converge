---
name: candidate-amendment
description: >
  How to propose a change to a locked vision or contract — a sibling proposal
  file named <contract>.vN-candidate.md, never a direct edit. Load this for
  procedural asks: "how do I propose a contract change?", "how do I write a
  candidate?", "this locked clause is wrong, now what?" — or when a cost paid or
  a failure caught says a locked clause needs to change. NOT for permission
  questions ("am I allowed to edit this?", "does this conform?") — those go to
  converge:protocol-authority. Applies documents.v1 §8 and PROTOCOL.md §5.
version: 0.2.0
---

# Writing a proposal to change a locked document

A **locked** document — a vision or a contract the intent steward has read and
agreed to (`FROZEN` in `docs/PROTOCOL.md`) — cannot be edited in place by
anyone, person or AI. It changes by written proposal, and only the steward
ratifies, in so many words.

This skill is the procedure. Whether a change is *allowed* is a separate,
interpretive question; that one belongs to `converge:protocol-authority`. If you
arrived here from a permission question, get the ruling first, then come back
to write.

## First: does this even need a proposal?

- **A change toward the contract is cheap.** Just make it. The contract check
  will confirm it. No proposal needed.
- **A change away from the contract owes a proposal, with evidence, before the
  work.** Skip that and the change is debt the moment it lands.

Only the second kind needs this skill.

## The proposal file

Write a **sibling** file named after the contract it changes:

```
contracts/operation.v1.md          ← the locked original, untouched
contracts/operation.v1-candidate.md ← your proposal, beside it
```

The name is `<contract>.vN-candidate.md`. Files named `CANDIDATE-<topic>.md` are
the older form and are still honored, so an existing one need not be renamed;
write new proposals under the new name.

A proposal from a teammate and a proposal from a manager session are the same
shape and are reviewed the same way. There is one form, not two.

## The three parts, in this order

1. **The exact change, sentence by sentence.** Old wording, new wording, quoted
   against the locked file as it actually reads, so it applies cleanly when
   ratified. Name the file it targets in one line at the top — that line is what
   lets the guard unlock the right document once the steward has answered.
2. **The evidence: a cost paid or a failure caught.** The outage, the measured
   regression, the concrete failure — with enough detail that someone else can
   verify it. **A preference is not evidence.** If all you have is a preference,
   you do not have a proposal; say so and stop.
3. **What does NOT change.** Bound the blast radius explicitly: what stays as
   it is, which existing work keeps working, what this does not touch.

Then leave a place for the steward's answer. Their word lands in this file, and
the stamped file is what allows the change to be made.

## The original stays the law until ratified

Until the steward answers, the locked document is unchanged and binding. The
proposal simply sits beside it. Nobody — not a worker session, not a manager
session, not the person who wrote the proposal — ratifies their own proposal.

The steward answers with one of four words: **ratified** · **ratified with
edits** · **declined** · **later**.

## When it is a new version rather than a change

If the change removes a promise, or breaks work that currently keeps it, that is
a **new version** of the contract, not a change to this one — and it owes a
migration note for everyone building against the old one. Ask
`converge:protocol-authority` before proposing one.
