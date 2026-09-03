---
name: seam-test
description: >
  Decide whether a surface is a seam — something outside this project depends on
  it, so it warrants a contract — or an internal mechanism, which gets tests and
  no contract. Use when scoping contracts, when someone proposes writing one,
  when deciding whether a project needs one at all, or when a capability exists
  on one surface and nowhere else. Applies PROTOCOL.md §3.2's seam test and the
  "no third option" rule.
version: 0.2.0
---

# The seam test

Semantics live in `docs/PROTOCOL.md` §3.2. This skill is the procedure — quote
the spec, don't paraphrase it into drift.

## The definition and the test

> A seam is a surface someone outside this project's own commits depends on.

The test is one question: **if this changed silently, who breaks?** If the answer
names anyone beyond this project — another team's client, a colleague's tool, an
automation reading a file format, a machine that will run this later — it is a
seam, and it gets a contract.

- An **experience someone builds against** is a seam.
- A **file format someone else reads** is a seam.
- An **internal mechanism** is not a seam. It gets tests, not a contract.

## Where a contract exists, the vision points at it

The vision is a *thin pointer* to the governing contract, not a restatement of
it. And **a project with no seam does not manufacture a contract.** Inventing
contracts where nothing outside depends on anything is one of the things this
method deliberately refuses to do.

## The "no third option" rule

When a capability exists on one surface and nowhere else, it is one of exactly
two things — there is no third:

1. **Behavior that belongs in the contract**, in which case promote it, or
2. **Debt.**

Where one contract governs several implementations, each capability is marked
required, idiomatic to one surface, or forbidden — see `docs/PROTOCOL.md` §3.2.

## When to escalate

For anything past "seam or not" — what a contract must contain, when a new
version is warranted, what triggers promotion — ask
`converge:protocol-authority`.
