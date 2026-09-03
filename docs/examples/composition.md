# Worked example — Composition v1

Contract: [`../../contracts/composition.v1.md`](../../contracts/composition.v1.md)

One fresh install onto a workspace that already holds other work, and the text
gates that run afterwards — including the one that catches a real mistake. This
is the most technical of the four contracts, so every step below is shown as
what you would actually see on screen.

> Converge sits lightly on a host and never touches work that isn't its own,
> while guaranteeing its automated steps find the helpers they need. A gate that
> cannot run reports *Can't check* — never a pass.

## The install

Two paths, and the contract governs both (clause 5 — the shared work queue rides
on either, so the manager session and the contract check can file and read work
from anywhere).

- **Add the capability layer** to a session you already have: agents, skills,
  the guard, and the queue arrive; the session keeps the base it was on.
- **Make Converge the whole workspace**: the same layer, plus the lean base
  (clause 1) — session basics, everyday tools, six lightweight helpers. The
  heavy foundation package appears nowhere, which is why sessions stay fast.

The host requirement is one sentence, and it lives in the README (clause 4):

> An automated step can use only the helpers present in the session it runs in,
> so running Converge's steps needs either Converge's own full setup or a host
> already on the same lean base.

That sentence is also why lanes are governed here: a worker session runs in its
own session, so it needs the same lean base for Converge's steps to find their
helpers.

## The gates, run against the fresh install

The conformance kit for this contract is a rule table read in plain words. Each
line is one clause. Run against the install above:

```
1  a lean base, never a heavy one .................... kept
2  steps use only the lean base's helpers ............ kept
3  own helpers carry the small local rulebook ........ kept
4  the host requirement is one sentence in the README  kept
5  the shared work queue rides on both install paths . kept
6  nothing touches the tools of other work ........... BROKEN
7  the guard recognises both proposal names .......... kept

6 kept · 1 broken · 0 can't check
```

## What gate 6 caught

A well-meant edit had added a session-wide setting that strips tools from
helpers. The gate quotes the offending line back:

```
behaviors/converge.yaml:41
    spawn:
      exclude_tools: [bash, delegate, load_skill]

  A top-level setting like this strips those tools from every helper in
  every session on the host, not only Converge's. Measured in isolation
  on 2026-09-02 and confirmed with a control: an unrelated session's
  read-only helper lost all three.
```

Clause 6 is the reason the setting is gone rather than tuned. Until per-role
limits can be enforced from outside, Converge's own helpers keep their limits as
stated rules in their own small rulebook (clause 3) — stop honestly when a thing
cannot be proven, sign commits, cite locations — and the guard on locked
contracts stays the enforcement that actually refuses.

## What gate 7 admits, and what it refuses

Gate 7 is the guard, exercised twice against a locked contract:

```
write contracts/documents.v1.md
  → denied. That contract is locked. Propose instead:
    contracts/documents.v2-candidate.md

write contracts/documents.v2-candidate.md
  → allowed. Proposal names are admitted beside a locked contract, in the
    versioned form above and in the older CANDIDATE-<topic>.md form.
```

Both refusals apply to a person and to an AI session identically. Nothing else
reaches a locked contract, and only the intent steward's word changes one.

## Clause traceability

Every moment above is drawn from `contracts/composition.v1.md`:

| Clause | Where it appears above |
|---|---|
| 1 — a lean base, never a heavy one | "Make Converge the whole workspace"; gate 1 |
| 2 — steps use only the lean base's helpers | gate 2 |
| 3 — own helpers carry a small local rulebook | "What gate 6 caught", closing lines |
| 4 — host requirement is one sentence in the README | the quoted sentence |
| 5 — the queue rides on both install paths | "Two paths, and the contract governs both" |
| 6 — nothing touches the tools of other work | the caught setting and its measurement |
| 7 — the guard recognises both proposal names | the two writes, denied and allowed |

No claim here that the contract does not make.
