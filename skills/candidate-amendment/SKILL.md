---
name: candidate-amendment
description: >
  Procedure for authoring a CANDIDATE amendment to a frozen vision or contract
  clause — a sibling proposal file, never a direct edit. Load this for
  procedural asks: "how do I amend a frozen clause?", "how do I author a
  CANDIDATE?", "how do I propose a contract change?", or when a measured cost or
  failure means a divergent change to a frozen clause is warranted. NOT for
  permission/conformance questions ("can I edit this?", "am I allowed to change
  this?", "does this conform?") — those route to converge:protocol-authority.
  Applies PROTOCOL.md §5 and pillar 3.
version: 0.1.0
---

# Authoring a CANDIDATE amendment

**Semantics owned by `@converge:docs/PROTOCOL.md` §5.** This skill is the
procedure. Amendments are CANDIDATE artifacts, never direct edits — lanes and
orchestrators may propose; **only the owner ratifies, in so many words**
(pillar 3).

> **Routing note.** This skill answers *"how do I author an amendment?"* — the
> procedure. A *"can I / am I allowed / does this conform?"* question is
> interpretive and belongs to `converge:protocol-authority`, not here. If you
> arrived via a permission question, get the ruling first, then return here to
> author.

## First: is an amendment even required? (change pricing)

From cortex-core:

- **Convergent change** — *toward* the contract — is cheap. Just do it and let
  the ledger confirm. No amendment needed.
- **Divergent change** — away from the contract — **owes an
  amendment-with-evidence before implementation, or it is debt on arrival.**

Only divergent changes to frozen clauses need this skill.

## The CANDIDATE file

A proposal is a sibling file **`CANDIDATE-<topic>.md`**, never an edit to the
frozen document. It carries exactly:

1. **The exact diff** — the precise clause change proposed.
2. **Evidence citations** — a real cost paid or a real failure caught. **A
   preference is not evidence.**
3. **An explicit "what does NOT change" section.**
4. **A ratification ask.**

## Ratification

The owner answers with the **literal word**:

- *ratified* — the edit lands, with a dated changelog entry.
- *ratified as edited* — the owner's edits apply, then it lands.
- *declined-with-reason.*

No self-ratification — by lanes *or* by the orchestrator (§7). Until the owner
says the word, the frozen document is unchanged and the CANDIDATE just sits
beside it.

## Note on version bumps

If the change removes or makes incompatible a frozen Core clause (existing
conformant implementations would break), that is a **version bump**, not an
amendment — and it owes a migration note for every known implementation.
Consult `converge:protocol-authority` (§5) before proposing one.
