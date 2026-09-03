# Broken Contract

A contract with no who-line on line 3 — VIOLATES 3.

**Status:** DRAFT — VIOLATES 6: a second source of truth for status, outside
the H1 (which carries none at all).

## Core (the teeth)

1. Clauses that do not lead in bold — VIOLATES 5a. The reader skimming the
   bold text reads nothing, because there is none.
2. A second clause, also unbolded. Its state is CONFORMS until the check runs
   — VIOLATES 10a: a machine disposition token standing in prose where a plain
   state word belongs. The plain form is *Kept*.
3. A third clause whose deciding sentence has to be read around the snippet
   below — VIOLATES 11: technical detail among the teeth instead of folded
   into a marked section.

```sh
./scripts/check --strict --format=json | jq '.rows[] | select(.ok == false)'
```

## Purpose

Out of order — VIOLATES 4: Purpose must come before Core.

## Reserved / open questions (NOT frozen)

Also out of order, and the file is far under fifty lines — VIOLATES 2.
