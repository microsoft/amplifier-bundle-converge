target: docs/PROTOCOL.md
ratified by owner 2026-09-18

# Publication clarification record — PR #68

## Purpose and preserved record

This is the unique legacy-form publication record for the already-ratified PR
#68 clarification. It replaces no artifact and asks for no new decision. The
new identity is required because `docs/PROTOCOL.v3-candidate.md` was consumed
for the unrelated 2026-09-03 Protocol v3 wording publication; `docs/PROTOCOL.md`
records that consumption at Changelog lines 309–312. The historical original
therefore remains the audit record, including its proposal, decision, evidence,
and original approved SHA-256
`79ed03d4fbaaadcb9008c6c0f2549c7e450f0668b0c3b7464186aa6fb86e6b25`.

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

## Evidence and decision

The steward's exact decision, `Ok, ratified for #68.`, is recorded in
[PR #68](https://github.com/microsoft/amplifier-bundle-converge/pull/68).
The approved revision is `9a4c5267934a499c04ad3f096b76cf0c59ed477c`.
Commit `415172c5d905f20f13795b4757b590f7bbef2115` records only the decision
and date; its file SHA-256 is
`742c062dfc525a429db3d43880290390eab0be749f4ce6bad76124737f075d95`.
The ratified source payload remains in `docs/PROTOCOL.v3-candidate.md`.
The earlier candidate’s different, consumed purpose is preserved at
`docs/PROTOCOL.md:309-312`; the collision is a real naming collision, not a
guard defect or a permission bypass.

## What does NOT change

The approved diff, evidence, public-review decision, and original audit record
remain unchanged. No frozen document, current proposal, guidance, ledger,
guard, proof condition, or version claim changes here. This is form
reconciliation under the two admitted candidate filenames, not a new policy or
ratification. The ratified rule remains: publication applies only the approved
diff and dated changelog while preserving proposal and decision evidence.

## Publication state

Ready but unapplied, pending correct loaded instructions. A future promotion
must add a dated entry to `docs/PROTOCOL.md`’s own Changelog naming exactly
`docs/CANDIDATE-publication-clarification-20260918.md`; that path is consumed
once. It must not use a root `CHANGELOG`.

## The steward's answer

*ratified* · *ratified with edits* · *declined* · *later*

    Steward's answer: ratified
    Date: 2026-09-18
