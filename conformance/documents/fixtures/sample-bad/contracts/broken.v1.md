# Broken Contract

A contract with no who-line on line 3 — VIOLATES 3.

**Status:** DRAFT — VIOLATES 6: a second source of truth for status, outside
the H1 (which carries none at all).

## Core (the teeth)

1. Clauses that do not lead in bold — VIOLATES 5a. The reader skimming the
   bold text reads nothing, because there is none.
2. A second clause, also unbolded. Its state is CONFORMS until the check runs,
   the lane is RUNNING and the item is BLOCKED — VIOLATES 10a: machine state
   words from all three of clause 10's vocabularies standing in prose where
   plain state words belong. The plain forms are *Kept*, *Working*, and
   *Waiting on you*.
3. A third clause whose deciding sentence has to be read around the snippet
   below — VIOLATES 11a: technical detail among the teeth instead of folded
   into a marked section.
4. **A clause that asserts and then stops — VIOLATES 5c: it leads in bold and
   says not one plain line of why.**

```sh
./scripts/check --strict --format=json | jq '.rows[] | select(.ok == false)'
```

## Purpose

Out of order — VIOLATES 4: Purpose must come before Core.

## Reserved / open questions (NOT frozen)

Also out of order, and the file is far under fifty lines — VIOLATES 2.
