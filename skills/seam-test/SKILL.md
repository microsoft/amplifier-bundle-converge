---
name: seam-test
description: >
  Decide whether a surface is a SEAM (and therefore warrants a per-seam
  contract) or an internal mechanism (which gets tests, not a contract). Use
  when scoping contracts, when someone proposes writing a contract, when
  deciding if a repo needs one at all, or when a capability exists on one
  surface and nowhere else. Applies PROTOCOL.md §3.2's seam test and the "no
  third option" axiom.
version: 0.1.0
---

# The seam test

**Semantics owned by `@converge:docs/PROTOCOL.md` §3.2.** This skill is the
procedure; quote the spec, don't paraphrase it.

## The definition and the test

> A seam is a surface someone outside this repo's own commits depends on.

The test: **_if this changed silently, who breaks?_** If the answer names
anyone beyond this repo — a sibling client, another team, an automation
consuming a file format, a future machine executor — it is a seam and gets a
contract.

- An **experience class** is a seam (e.g. cortex's `client-experience.v1`).
- A **file format** is a seam (e.g. drumbeat's `automation-file.v1`).
- An **internal mechanism** is **not** a seam — it gets tests, not a contract.

## Where a contract exists, VISION.md points to it

- `VISION.md` is a *thin pointer* to a governing contract, not a restatement.
- **A repo with no governing contract does not manufacture one.** Manufacturing
  contracts for repos with no seam is something the protocol explicitly resists
  (§7).

## The "no third option" axiom

When a capability exists on one surface and nowhere else, it is one of exactly
two things — there is no third:

1. **Convergent behavior** that belongs in the contract (promote it), or
2. **Debt.**

(For contracts governing multiple implementations, the feature × surface
matrix values are `REQUIRED` / `IDIOM` / `EXCLUDED` — see §3.2.)

## When to escalate

For anything beyond "seam or not" — contract anatomy, versioning, promotion
triggers — consult `converge:protocol-authority`.
