target: docs/PROTOCOL.md

# Proposal — Protocol v3 publication clarification

`docs/PROTOCOL.md` remains the law until the intent steward answers below. This
proposal requests one narrow clarification of §5's publication step; it does
not authorize an edit or ratify itself. It uses the required proposal route and
shape: `AGENTS.md:46-67`, `PINS.md:72-100`, `docs/PROTOCOL.md:240-263`, and
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
edited* / declined-with-reason. On ratification, after the owner selects the
proposal, applying only its approved diff and a dated changelog entry to the
active file is a ratification-gated promotion, not permission for unreviewed
changes. The candidate's approved before/after diff and evidence remain
unchanged; the owner-selected ratification stamp or decision is recorded in the
candidate's designated decision field and the candidate is preserved as the
ratified record. Where permitted, a copy may also be preserved as the decision
record. The changelog records the exact candidate path and approved scope. If
active bytes change, the full ledger hash review is required. An additive change
is an amendment, not a version bump, under the rule below. This route requires a
matching target, owner ratification recorded in the candidate, and the
consumed-candidate check; it makes no hash-atomicity claim. A stronger host
no-edit policy remains controlling unless owner-approved instructions explicitly
update that policy.
```

## The evidence

The reported public cost is a finished, owner-ratified nonbreaking amendment
whose publication path is ambiguous: [DotRunner PR #108](https://github.com/microsoft/amplifier-bundle-dot-runner/pull/108)
merged as `2d137d7`, with `contracts/engine-surface.v2-candidate.md`, a separate
September 16 ratification receipt, and subsequent runtime/test implementation.
The frozen v1 text does not contain C15.5 and the ledger does not assert it;
[PR #109](https://github.com/microsoft/amplifier-bundle-dot-runner/pull/109)
(`f3b9c1`) closed migration work only. This leaves two readings in practice:
§2.3 forbids an unauthorized direct edit, while §5 says only that a ratified
edit “lands.”

The current guard supports the proposed narrow boundary: a guarded write needs
a sibling candidate declaring `target:`, an owner ratification stamp in that
candidate, and an unspent exact candidate-path token in the target Changelog; a
consumed candidate cannot authorize another edit. It does not itself provide
ledger-hash review or an atomic publication mechanism (guard README:313-342,
492-520). The separate-receipt C15.5 case therefore remains blocked from
publication until the owner explicitly approves how its decision is expressed in
the required candidate form. This clarification applies prospectively: it does
not automatically modify the historical v2 candidate, whose approved payload
and existing bytes remain untouched. Any approved migration is separate follow-on
work, not an automatic repair or a re-ratification of C15.5.

## What does NOT change

- §2.3 still forbids unauthorized direct edits; refusal remains stop, never bypass.
- The four Freeze Bar requirements, owner-only ratification, and the rule that
  acceptance is not proof remain unchanged. Decision and implementation stay separate.
- No promise is removed or made incompatible; the existing §5 version rule stays.
- This neither re-ratifies DotRunner C15.5 nor automatically changes its
  historical v2 candidate, receipt, ledger, runtime/tests, migration, or PRs.
  Under the current policy that historical candidate is not editable; any
  owner-approved migration to the required candidate form is separate follow-on work.
- No awareness, `AGENTS.md`, participant-kit, guard, ledger, contract, vision,
  or code update is authorized here. Any later alignment is separately scoped
  follow-on work with its own exact diff; this proposal does not require redoing
  related files without one.

## The steward's answer

One decision: should this §5 wording define an owner-ratified, exact-diff
promotion as distinct from an unauthorized direct edit?

*ratified* · *ratified with edits* · *declined* · *later*

    Steward's answer: ______________________________
    Date: ____________
