target: docs/PROTOCOL.md

# Proposal — Protocol v3 publication clarification

`docs/PROTOCOL.md` remains the law until the intent steward answers below. This
proposal requests one narrow clarification of §5's publication step; it does
not authorize an edit, ratify itself, or override stricter host instructions.
It uses the required proposal route and shape: `AGENTS.md:46-67`,
`PINS.md:72-100`, `docs/PROTOCOL.md:240-263`, and
`contracts/documents.v1.md:40-44`.

## The exact change

**Change 1 — §5, “Changing a locked clause: the proposal (CANDIDATE) route.”**

Current text:

```
A proposal is a sibling file placed next to the locked one —
`<contract>.vN-candidate.md`, or the older `CANDIDATE-<topic>.md` — never
an edit to the locked file itself. It carries: the exact diff · evidence
citations (a real cost paid or a real failure caught — a preference is not
evidence) · an explicit **"what does NOT change"** section · a ratification
ask. The owner answers with the literal word: *ratified* / *ratified as
edited* / declined-with-reason. On ratification the edit lands with a dated
changelog entry.
```

Replacement:

```
A proposal is a sibling file placed next to the locked one —
`<contract>.vN-candidate.md`, or the older `CANDIDATE-<topic>.md` — never
an edit to the locked file itself. It carries: the exact diff · evidence
citations (a real cost paid or a real failure caught — a preference is not
evidence) · an explicit **"what does NOT change"** section · a ratification
ask. The owner answers with the literal word: *ratified* / *ratified as
edited* / declined-with-reason. On ratification, the approved diff may be
applied to the locked file with a dated changelog entry. That promotion is
limited to the approved diff and changelog. The candidate preserves its
evidence and decision record.
```

## Explanation and evidence

The reported public cost is a finished, owner-ratified nonbreaking amendment
whose publication path is ambiguous: [DotRunner PR #108](https://github.com/microsoft/amplifier-bundle-dot-runner/pull/108)
merged as `2d137d7`, with `contracts/engine-surface.v2-candidate.md`, a separate
September 16 ratification receipt, and subsequent runtime/test implementation.
The frozen v1 text does not contain C15.5 and the ledger does not assert it;
[PR #109](https://github.com/microsoft/amplifier-bundle-dot-runner/pull/109)
(`f3b9c1`) closed migration work only. A clarification could therefore be
ratified while a stronger host no-edit instruction and the unresolved
separate-receipt form still prevent publication.

The proposal payload is its before/after diff and evidence; a later decision
field records its status without changing that payload. Existing guard
documentation is the source for enforcement details (`PINS.md:72-100` and the
guard README); this clarification neither changes those mechanics nor treats
a decision as a bypass. The historical C15.5 candidate, its already-approved
payload, and its original hash receipt remain preserved unless an authorized
owner chooses a separate migration.

## Remaining gates after a ratification — the #68 follow-on

This is the complete stated path, not an additional ratification request:

1. The steward approves this proposed clarification; that approval does not
   automatically overrule stricter host instructions.
2. The authorized host-policy owner explicitly permits ratified promotion in
   the controlling instructions.
3. That owner selects the exact migration for the historical candidate form,
   preserving the already-approved C15.5 payload and original hash receipt;
   this does not re-ratify C15.5.
4. Only then may the approved promotion be applied through the recognized
   guard and dated changelog, followed by the full ledger re-review.

## What does NOT change

- §2.3 still forbids unauthorized direct edits; a refusal remains stop, never
  bypass.
- The four Freeze Bar requirements, owner-only ratification, and the rule that
  acceptance is not proof remain unchanged. Decision and implementation stay separate.
- No promise is removed or made incompatible; the existing §5 version rule
  stays. This does not create a version bump, overlay, index, or new mechanism.
- This neither re-ratifies DotRunner C15.5 nor automatically changes its
  historical candidate, receipt, ledger, runtime/tests, migration, or PRs.
- No `AGENTS.md`, participant-kit, guard, ledger, contract, vision, or code
  update is authorized here. Any later work remains separately scoped.

## The steward's answer

One decision: should this narrow §5 clarification be approved, while leaving
stricter host policy and every stated follow-on gate controlling?

*ratified* · *ratified with edits* · *declined* · *later*

    Steward's answer: ratified
    Date: 2026-09-18
