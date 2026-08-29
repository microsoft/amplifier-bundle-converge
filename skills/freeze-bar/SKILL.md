---
name: freeze-bar
description: >
  Check whether a DRAFT vision or contract may be stamped FROZEN. Use before
  proposing a FROZEN stamp, when reviewing a conformance kit, or when someone
  claims a spec is "done." Enforces PROTOCOL.md §5's Freeze Bar — four
  conditions, no substitutions, owner-only stamp — and pillar 4 (freeze
  requires a discriminating example).
version: 0.1.0
---

# The Freeze Bar

**Semantics owned by `@converge:docs/PROTOCOL.md` §5.** This skill is the
checklist.

## All four conditions — no substitutions

A DRAFT may be stamped FROZEN only when every one of these holds:

1. **The spec is written.**
2. **A machine-checkable conformance kit exists, with at least one
   discriminating good/bad fixture pair.**
3. **At least one real implementation passes it.**
4. **A worked example exists end-to-end.**

## Only the owner stamps FROZEN

The stamp is an owner-attention item (§6.1 — ratifying, including FROZEN
stamps). No one else stamps; presenting the four conditions as met is a
*recommendation*, not the stamp.

## Why condition 2 is not negotiable (pillar 4)

> Freeze requires a discriminating example. A conformance kit must include at
> least one good/bad fixture pair that actually discriminates — prose alone
> freezes nothing.

A kit whose fixtures do not actually distinguish conformant from
non-conformant behavior has not met condition 2, regardless of how much prose
it carries.

## Related honest-stopping rule (pillar 5)

If a condition genuinely cannot be met yet, that is a real result — say so
(`N/A` with a reason, `BLOCKED.md` with a cause). A missing artifact beats a
fabricated one. Do not stamp around a gap.
