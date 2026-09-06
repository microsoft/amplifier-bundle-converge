# Composition Contract — v1 candidate (proposal)

The file this proposal changes, for the guard:

```
target: contracts/composition.v1.md
```

**Who builds against this:** the intent steward, who decides; every early
adopter, who is currently handed two install commands and a comparison table at
the exact moment they are trying to type one line; whoever owns `README.md`,
who cannot make its install section right in either direction while the contract
sanctions two paths; and whoever owns `conformance/composition/run.py`, whose
rule 5 today asserts the sentence this proposal changes.

`composition.v1` Core 5 says, in as many words, "The shared work queue rides on
**both install paths**." The contract assumes two paths and says nothing about
how many an adopter should meet. The steward's readiness bar says "one install
command; nothing else to know." Nothing is broken — the two documents simply
answer different questions, and `README.md` is left trying to satisfy both at
once. It cannot, and today it does not: it names one path **THE** install path
and then, forty lines later, recommends the other for the first thing an adopter
does. `composition.v1` stays the law until the steward answers: *ratified* ·
*ratified with edits* · *declined* · *later*.

**A note on this file.** The previous `contracts/composition.v1-candidate.md`
(Core 4, `converge-qwk`) was ratified on 2026-09-04, applied in commit `0b00fda`,
and archived as `docs/workflow/composition.v1-candidate.ratified.md`. So this
file is new rather than appended-to, and the Core 4 change it carried is already
in the contract and is not re-proposed here. This proposal touches Core 5 and the
asserts list, and nothing else.

## The exact change

Two places in this one contract, in the order they appear.

### 1 · Core 5 — one command is the path an adopter takes

Today Core 5 reads:

```
5. **The shared work queue rides on both install paths,** so the contract
   checker can file and read work anywhere.
```

Replace it with:

```
5. **One install command is the path an adopter takes.** The README names
   exactly one command as that path — the single command that composes Converge
   onto the session the reader already has — and marks the multi-command
   full-workspace install as the advanced path, saying in one sentence who
   needs it: a host that supplies neither the session base nor the mode
   machinery. Nothing later in the README recommends against the path it just
   named. The shared work queue rides on both, so the contract checker can file
   and read work whichever one was taken. *For you:* you type one line, and
   nothing afterwards tells you that you should have typed the other.
```

The old promise is kept whole and is the last sentence of the new one: the queue
still rides on both paths, so `conformance/composition/run.py`'s rule 5 — which
reads `bundle.md` and every behavior file for an include naming the work queue —
is correct exactly as written and needs no change. What is added is the sentence
the bar has been asking for and the contract has never carried: which of the two
a reader is sent to, and that the document may not then argue with itself.

### 2 · Conformance kit asserts — the new claim must be the asserted one

Today the asserts list ends:

```
- A step that declares its own helpers resolves them from that closure, not
  from the calling session: the recipe validates at `schema_version: 2` and its
  plan names every helper against the dependency that supplies it.
```

Add one line after it:

```
- The README's install section presents exactly one command as the path an
  adopter takes, marks every other path advanced, and nowhere afterwards
  recommends against the path it named.
```

This one is load-bearing, and it has a price the steward should see before
answering. `conformance/composition/run.py` has no rule for it today, and
`README.md` as it stands would not pass one: `README.md:53` names the `--app`
behavior **THE** install path, and `README.md:93–96` prefers the other for
end-to-end runs against a target repo. So ratifying this makes the README
rewrite **derived work** — a row that reads *not yet* until it lands — rather
than a good idea somebody might get to. That is the ratchet working as intended,
and it is the whole reason to put the claim in the asserts list instead of
leaving it as prose.

### Which command this names — and the case for the other

The clause above names the path by its shape rather than by a literal command,
so a rename does not silently un-ratify it. On the tree as it stands the shape
resolves to `README.md:56`:

```
amplifier bundle add git+https://github.com/microsoft/amplifier-bundle-converge@main#subdirectory=behaviors/converge.yaml --app
```

— one line — and the advanced path is `README.md:70–71`, two lines
(`bundle add …@main`, then `bundle use converge`).

**The case for naming the other one instead**, stated fairly. The full-workspace
path is self-contained: `bundle.md` pulls the lean `anchors` base itself
(Core 1), and `anchors` ships the mode machinery (`tool-mode` + `hooks-mode`),
so nothing about the host can take the manager session away. On the one-command
path both come from whatever the host already has —
`behaviors/converge.yaml:148–150` says so in as many words. If the bar were
"works on every host no matter what", the two-command path would win it.

It is not that bar. The bar is one command, the one-command path has been
measured delivering the whole product (below), and the residual host risk is
exactly what the advanced path is being kept, documented, and pointed at for.
Naming the two-command path as *the* path would satisfy no reading of the bar at
all, since it is two commands.

## The evidence

A cost paid in the document itself, and a capability measured in a container.
Not a preference.

### The cost paid — the README tells every reader the other path

`README.md:53`:

```
**THE install path — the behavior (`--app`):**
```

`README.md:93–96`, forty lines later:

```
Both paths give the four agents, five skills, guard hook, awareness context, and
work-tracker filing. The root path additionally supplies the base — so for
end-to-end recipe runs against a target repo, prefer `bundle use converge`. For
lightweight composition onto a session that already has its own base, the
`--app` behavior is the quick path.
```

An adopter's first real act on a project is a run against a target repo, so the
same reader is told that path one is *the* path and that path two is preferred
for what they are about to do. This is `docs/workflow/ONBOARDING-AUDIT-2026-09-04.md`
finding a-2, and it is why the audit's verdict on the bar's clause (a) is **not
met**.

**And one half of that contradiction is already stale, which is what makes this
a caught failure rather than a tie of opinion.** The sentence's stated reason —
that the root path "additionally supplies the base" and is therefore preferred
for recipe runs — was made moot by the very commit that wrote it.
`git blame` and `git show` on this tree, 2026-09-05:

```
$ git blame -L 89,89 --date=short README.md
0b00fda7 (Amplifier 2026-09-04 89) | `seed-reconcile` recipe runnable | ✅ the recipe declares its own helpers (`schema_version: 2`) and resolves them from that closure, so this path no longer has to supply them | ✅ |

$ git blame -L 94,95 --date=short README.md
49534d64 (Amplifier 2026-09-04 94) work-tracker filing. The root path additionally supplies the base — so for
49534d64 (Amplifier 2026-09-04 95) end-to-end recipe runs against a target repo, prefer `bundle use converge`. For
```

`49534d6` is *"seed-reconcile v1.4.0: declare its own helpers (schema_version 2)"*.
Its own diff replaced a sentence that had the distinction right —

```
-work-tracker filing. The root path additionally supplies the base, which is why
-it is still the recommendation for everyday work — but that is now a matter of
-what your session has to hand, not of whether the recipe will run: since
-`schema_version: 2` the recipe brings its own helpers either way. For
+work-tracker filing. The root path additionally supplies the base — so for
+end-to-end recipe runs against a target repo, prefer `bundle use converge`. For
```

— with a shorter one that ties the preference back to recipe runs, the exact
thing that same commit had just made host-independent. The comparison table two
lines above it (`README.md:89`) still says the recipe runs on both paths. So the
README contradicts itself twice over: once between `:53` and `:93–96`, and once
between `:89` and `:94–95`. Prose alone cannot be trusted to stay in step with a
clause; a contract sentence and an assert can.

### The measurement — one command produced a working manager session

`evaluations/adopter/` put the Amplifier CLI, a provider, git and tmux in a fresh
container with **Converge deliberately absent** (`profiles/adopter.yaml:13–19`),
and had an AI user reading only `README.md` install it and get to work. Two
things that container recorded, on 2026-09-04:

```
evaluations/adopter/RESULT.md:85   ### S1.1 — Converge installed and composed into the CLI — PASS
evaluations/adopter/RESULT.md:101  Mode: No bundle active (default)
evaluations/adopter/RESULT.md:104    [on]  converge  bundle
evaluations/adopter/RESULT.md:105    [on]  converge-behavior  bundle

evaluations/adopter/RESULT.md:211  ### S2.2 — A manager session is running against the project — PASS
evaluations/adopter/RESULT.md:239  [converge-manager]> Good — hold off on launching the lane for now. …
```

Read those two together. **No bundle was active** — so `amplifier bundle use
converge`, the second command of the two-command path, was not in effect — and
Converge was nonetheless composed (`[on]`, both namespaces) and its manager mode
was live at a real prompt. On that same install the AI user filed a real work
item, `sensorlog-9ge`, through the session's own `work_*` tools
(`RESULT.md:333–336`), which is Core 5's existing promise holding on the
one-command path.

Stated precisely, because it matters: `RESULT.md` records the resulting **state**,
not the command string the AI user typed. The state is the load-bearing part —
whatever was typed, no bundle was activated, and the capability layer, the manager
mode and the queue were all there. The composed-and-on state with no active bundle
is what an app-level install produces.

Two limits the run itself declares, kept here rather than dropped:
`RESULT.md:324–328` — both scenarios shared one container, so only S1.1 is an
independent install result; and `RESULT.md:341–347` — scenario 1's mode probe
caught a blank pane and proved nothing either way. Neither touches the reading
above, which rests on S1.1 (install) and S2.2 (the live prompt).

### The residual risk this leaves, named rather than hidden

The one-command path takes the session base **and the mode machinery** from the
host (`behaviors/converge.yaml:148–150`). One measured host supplied both; every
host is not one host. And `behaviors/converge.yaml:137–141` records a second,
silent way for the mode to disappear on this path — a duplicate `converge`
namespace from a stale registration wins, `@converge:modes/…` resolves to
nothing, and the mode never lists (filed `converge-348`).

This is not an argument against the clause; it is the clause's own second
sentence doing its job. The advanced path stays supported and stays documented,
and the one sentence the clause requires beside it — who needs it — is exactly
this case.

## What does *not* change

- **Core 5's existing promise.** The shared work queue still rides on both
  install paths, in the same words, in the same clause. Nothing that files or
  reads work changes, and `conformance/composition/run.py`'s rule 5 keeps
  passing unaltered — verified on this tree before this proposal was written.
- **The second path itself.** It is not removed, not deprecated, and not broken.
  `bundle.md` keeps the lean `anchors` base and the work-tracker include exactly
  as they are. Anyone using it today keeps using it; the change is which one a
  *new reader* is sent to first.
- **Core 1, 2, 3, 4, 6 and 7.** Untouched. In particular Core 1's lean base and
  Core 4's amended host requirement — ratified one day before this — are neither
  reopened nor reworded.
- **The "Who builds against this" line,** which already reads "everyone who
  installs Converge, by either path" and stays true, because there are still two
  paths.
- **The not-frozen list and the Reserved section.** Untouched.
- **`README.md` itself,** which this proposal does not rewrite and which this
  lane does not own. The install section stays exactly as it is — honestly
  contradictory — until the steward answers. Ratifying makes that rewrite
  derived work, keyed to this clause; declining leaves the README as it is and
  the audit's finding (a) standing as a known, recorded gap.
- **The bar.** This proposal moves the contract toward the steward's readiness
  bar rather than asking the bar to move. The other way — leaving Core 5 as it
  is and dropping "one install command" from the bar — is the alternative the
  work item names, and it is still open to the steward; declining this is how it
  is chosen.

## The one word

`ratified` · `ratified with edits` · `declined` · `later` — recorded in
`docs/workflow/owner-ratifications-<date>.md`. Until then `composition.v1` Core 5
is the law, and `README.md` says two paths because the contract says two paths.

### The steward's word

```
Word: ratified, please continue
Date: 2026-09-06
Edits (if "ratified with edits"): none — ratified as written
```

Recorded in `docs/workflow/owner-ratifications-2026-09-06.md`, round 1. Applied
to `contracts/composition.v1.md` on 2026-09-06 by `converge-462l`: Core 5
replaced verbatim with the fenced replacement above, and the one new kit-assert
line added directly after the last bullet, verbatim. 71 lines → 82.

**Why this file is dated and the earlier one is not.** The Core 4 archive
already holds the name `docs/workflow/composition.v1-candidate.ratified.md`
(ratified 2026-09-04, converge-qwk), and `contracts/composition.v1.md`'s
changelog cites it by that name. Overwriting it would erase that record, so this
second composition proposal is archived under its ratification date instead. The
convention for a contract's *second* ratified proposal is not written down
anywhere; filed rather than decided here.

The decision is carried in the queue as `converge-279a`, so it stays visible
after the lane that wrote this proposal is gone. Its acceptance is written against
`README.md`, which means it cannot close on this file alone: ratifying it makes
the README edit the next step, and the item is answered when that edit lands.
