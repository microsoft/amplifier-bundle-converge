---
name: candidate-amendment
description: >
  Author a CANDIDATE amendment to a frozen vision or contract clause — a
  sibling proposal file, never a direct edit. Use when a lane or orchestrator
  wants to change a frozen clause, when a measured cost or failure suggests a
  clause is wrong, or when deciding whether a change is convergent (just do it)
  or divergent (owes evidence first). Applies PROTOCOL.md §5 and pillar 3.
version: 0.1.0
---

# Authoring a CANDIDATE amendment

**Semantics owned by `@converge:docs/PROTOCOL.md` §5.** This skill is the
procedure. Amendments are CANDIDATE artifacts, never direct edits — lanes and
orchestrators may propose; **only the owner ratifies, in so many words**
(pillar 3).

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
