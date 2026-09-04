# Composition Contract — v1 candidate (proposal)

**Who builds against this:** the intent steward, who decides; anyone who runs
`recipes/seed-reconcile.yaml` and is currently told they need a particular kind
of host; whoever writes the next automated step and needs to know whether
declaring its own helpers is allowed or merely tolerated; and whoever owns
`conformance/composition/run.py`, whose rule 4 asserts the sentence this
proposal changes.

`composition.v1` Core 4 says a step "can use only helpers present in the session
they run in." That was true of every step this project had when the clause was
written. It is no longer true of the one recipe this project ships.
`composition.v1` stays the law until the steward answers: *ratified* ·
*ratified with edits* · *declined* · *later*.

**A note on this file's name.** Every candidate in `contracts/` is named
`<contract>.v1-candidate.md` — a proposal *against* v1 — and this file follows
that. The work item that asked for it (`converge-qwk`) named
`composition.v2-candidate.md`, reading the same `<contract>.vN-candidate.md`
pattern in `documents.v1` clause 8 and `composition.v1` Core 7 as "a candidate
*for* v2". Both readings fit the pattern, the six candidates already in this
folder use the first, and the guard's glob accepts either. Filed as
`converge-t18` so the pattern is written down once instead of decided again per
proposal.

## The exact change

Three places in this one contract, in the order they appear.

### 1 · Core 4 — a step may declare the closure it resolves from

Today Core 4 reads:

```
4. **The host requirement is one sentence in the README.** Steps can use only
   helpers present in the session they run in; Converge needs its own full setup
   or a host on the same lean base.
```

Replace it with:

```
4. **The host requirement is one sentence in the README.** A step that declares
   no helpers of its own can use only those present in the session it runs in,
   and needs Converge's own full setup or a host on the same lean base; a step
   that declares its helpers resolves them from that closure instead, and asks
   nothing of its host.
```

The first sentence is untouched: the host requirement is still one sentence in
the README, and rule 4 still judges that. What changes is the second — it stops
stating one rule for every step and starts naming the two cases that now exist.

### 2 · The not-frozen list — the condition on this item has been met

Today the list reads:

```
- Enforced per-role tool limits — promoted when upstream #388 lands.
- Automated steps that bring their own helpers — when the engine supports it.
- The companion app as its own product — see Surface.
```

Remove the middle line, leaving:

```
- Enforced per-role tool limits — promoted when upstream #388 lands.
- The companion app as its own product — see Surface.
```

That item was deliberately left open "when the engine supports it." The engine
supports it, and the evidence below is the engine doing it. An item whose
condition has been met and which stays on the not-frozen list is a promise that
has quietly stopped meaning anything.

### 3 · Conformance kit asserts — the new claim must be the asserted one

Today the asserts list ends:

```
- The guard denies a write to a locked contract and admits a `*.vN-candidate.md`
  beside it.
```

Add one line after it:

```
- A step that declares its own helpers resolves them from that closure, not
  from the calling session: the recipe validates at `schema_version: 2` and its
  plan names every helper against the dependency that supplies it.
```

This one is load-bearing and is the reason this proposal is not just prose.
`conformance/composition/run.py` rule 4 reads `README.md` for the
host-requirement sentence, and its `HOST_SENTENCE_TESTS` currently require that
sentence to say a step's helpers come **only from the session it runs in**. The
rule PASSes today on the old wording. So until this amendment is answered, a
README rewritten to state the new truth plainly would either fail rule 4 or —
worse — pass it while asserting something the contract does not say. Ratifying
this change makes updating that rule the required next step rather than a
tempting one; declining it keeps README's sentence as it is, honestly labelled.

## The evidence

A cost actually paid, and a capability actually reproduced. Not a preference.

**The cost.** On a host whose active bundle is not on the *anchors* base, the
recipe failed at its very first step with `Agent '…' not found in
configuration`. That failure is what Core 4's second sentence exists to warn
about, and it was real.

**The capability.** `recipes/seed-reconcile.yaml` carries `schema_version: 2`
and a dependency manifest (commit `ac8d687`), so its `agent:` references resolve
from the declared closure rather than from the calling session's agent map.
Reproduced on this tree, 2026-09-04, independently of the work item that
reported it:

```
$ recipe-runner validate recipes/seed-reconcile.yaml
recipe: recipes/seed-reconcile.yaml
status: ok
schema_version: 2

$ recipe-runner plan recipes/seed-reconcile.yaml
schema_version: 2
recipe_digest: sha256:b7ac49610fbaa72bf57c8763a9263234889ce3694787018f8277818fd72e4a53
lock_mode: locked
trust_policy: interactive
isolated: True
dependencies (1):
  - git+https://github.com/microsoft/amplifier-bundle-converge@main [bundle]
      -> 4507e462d1e801a2b0080c58417ec9647b313880
agents (12):
  - anchors:explorer <- git+https://github.com/microsoft/amplifier-bundle-converge@main
  - converge:reconciler <- git+https://github.com/microsoft/amplifier-bundle-converge@main
  … 10 more, every one against the same dependency
steps: load-contracts, derive-rows, run-conformance, file-drift

Amplifier recipes tool, validate:
  {"execution_mode": "runner-isolated", "schema_version": 2, "status": "valid"}
```

Two things in that output matter more than the exit status. Every agent is
listed **against the dependency that supplies it** — including
`anchors:explorer`, the read-only intake step whose absence caused the failure
above — so the resolution is demonstrably not coming from the calling session.
And the mode is `runner-isolated`: the closed world is not a mode the recipe
asks for politely, it is where the run happens.

`PINS.md` records four further facts about that manifest, each reproduced rather
than assumed: why one dependency and not two, why the self-reference is
required, why `@main` and not a SHA, and the `runner-isolated` mode. They are
context for this decision, not part of it.

## What does *not* change

- **Core 1 — the lean base.** Converge still assembles on *anchors*, and the
  full foundation package still appears nowhere. A step declaring its own
  closure declares a lean one; this is not a door to the heavy package.
- **Core 2 — automated steps use only the lean base's helpers.** Unchanged and
  still binding. This proposal changes *where a step's helpers are resolved
  from*, never *which helpers it may name*.
- **Core 3 — the local rulebook.** Stop honestly, sign commits, cite locations,
  borrow nothing else. Untouched.
- **Core 5 — the queue on both install paths.** Untouched.
- **Core 6 — nothing touches the tools of other work.** Untouched, and the
  measurement behind it (2026-09-02, confirmed with a control) still stands. No
  session-wide `spawn:` block returns by this door.
- **Core 7 — the guard recognizes both proposal names.** Untouched.
- **The first sentence of Core 4.** The host requirement is still one sentence
  in the README, and rule 4 still judges exactly that.
- **The other two not-frozen items,** and the Reserved section.
- **`README.md` itself,** which this proposal does not rewrite. Its
  host-requirement sentence is handled by `converge-yj3`, which states the truth
  now and names this clause as not yet amended — precisely so that ratifying,
  declining, or deferring this proposal all leave the README honest.

## The one word

`ratified` · `ratified with edits` · `declined` · `later` — recorded in
`docs/workflow/owner-ratifications-<date>.md`. Until then `composition.v1` is
the law, and `README.md` says so in as many words.

The decision itself is carried in the queue as `converge-may`, with the options
and what each one costs, so it stays visible after the lane that wrote this
proposal is gone.
