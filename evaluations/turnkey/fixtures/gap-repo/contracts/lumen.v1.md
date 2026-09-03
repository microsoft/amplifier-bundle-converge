# Lumen Contract — v1 (LOCKED)

**Who builds against this:** anyone reading a Lumen sensor report.

## Purpose

A reading a person cannot interpret is not a reading. Lumen promises that every
number carries its unit, and that every way into the library is written down
where a newcomer will find it.

## Core (the teeth)

1. **Every reading names its unit.** A number without a unit is a bug, not a
   value.
2. **Every public entry point is named in the index.** A caller should never
   have to read the source to find the door.

## Conformance kit asserts

- **1 — units:** every reading constructed in `src/readings.py` names its unit.
- **2 — index:** every public entry point defined in `src/report.py` appears in
  `docs/INDEX.md`.

Run the kit with `python3 check.py` from the repository root.

## Reserved / open questions (NOT frozen)

- Whether a unit may be an empty string for dimensionless readings.
