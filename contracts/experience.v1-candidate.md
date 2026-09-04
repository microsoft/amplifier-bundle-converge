# Experience Contract — v1 candidate (proposal)

**Who builds against this:** the intent steward, who decides; whoever builds the
web body, who is told by this clause how many contracts govern them; the authors
of the four native platform contracts, who follow the same pattern; and anyone
reading the family index, who is currently sent to two files that do not exist.

One sentence of `experience.v1` clause 15 names two platform contracts —
`platform-browser.v1` and `platform-web-app.v1` — that have never existed in
this repository. What exists is one `platform-web.v1`, ratified in the same
pass as the umbrella that names them. This proposal makes the clause name the
contract that exists. `experience.v1` stays the law until the steward answers:
*ratified* · *ratified with edits* · *declined* · *later*.

## The exact change

**Clause 15 — name the web body's contract by the name it actually has.**

Today clause 15 reads:

```
15. **This umbrella governs a family.** The places are held by
    `experience-direction.v1` · `experience-operation.v1` ·
    `experience-console.v1` · `experience-collaboration.v1`; the idioms of one
    body by one `platform-*.v1` — `platform-browser.v1` and
    `platform-web-app.v1` first, then one per native body. A platform contract
    adds no behavior and removes none.
```

Replace it with:

```
15. **This umbrella governs a family.** The places are held by
    `experience-direction.v1` · `experience-operation.v1` ·
    `experience-console.v1` · `experience-collaboration.v1`; the idioms of one
    body by one `platform-*.v1` — `platform-web.v1` first, the browser and the
    installable web app being one body, then one per native body. A platform
    contract adds no behavior and removes none.
```

Six lines before, six lines after: the file stays at a hundred lines, which is
the top of the fifty-to-a-hundred band `documents.v1` clause 2 fixes and the
documents kit's rule 2 measures.

## The evidence

**A failure caught, and re-derived three times.** Seeding the ledger on
2026-09-03, a session could not record whether this clause was kept: it wrote
row CVG-114 with a probe that names both files and reports them absent, and
left the reading to a person. The gap analysis on 2026-09-04 had to carry the
same question forward and schedule a lane for it. This lane re-derived it a
third time. Three sessions have now paid the same cost, and a reader who
follows the clause to `platform-browser.v1` still cannot tell whether a
contract is missing or a name is wrong.

**Neither named file ever existed.** `git log --all --diff-filter=A` over
`contracts/platform-browser.v1.md` and `contracts/platform-web-app.v1.md`
returns nothing. The umbrella was committed at 06:25:39 on 2026-09-03 and the
single `platform-web.v1` at 06:28:57 the same morning; the ratification record
for that day ratifies both in one line. The names were written three minutes
before the file that replaced them, and nothing went back for them.

**Three ratified artifacts already say one body; only this clause says two
contracts.** `platform-web.v1` line 3 reads "whoever builds the browser body of
Amplifier Converge — the first body and, for most people, the only one". Its
clause 9 reads "It installs, and installing changes only the frame — IDIOM …
Nothing gains a behavior by being installed and nothing loses one; there is no
store, no review queue, and no second build." The family index in
`docs/CONTRACTS-README.md` carries one row: "The browser and installable web
app body, in its own idiom" — one body, singular.

**The umbrella's own test settles it.** Clause 15 gives one platform contract
to the idioms of *one body*, and clause 12 lets a body exceed the umbrella in
idiom, never in features. A frame that changes with no behavior gained or lost
is not a second body, so there is no second set of idioms for a second contract
to hold. Writing one anyway would produce a file whose every clause reads "as
`platform-web.v1`" — which `documents.v1` clause 14's merge test already
refuses: a file that cannot fill its own sections belongs inside the contract
it restates.

**What would overturn this.** If a body ever gains or loses a behavior by being
installed — a store, a review queue, a second build, a capability the browser
cannot reach — then the two bodies are genuinely two, and `platform-web.v1`
clause 9 is the seam to split on. Nothing observed today does that.

## What does not change

- **No behavior changes anywhere.** The clause promises that the umbrella
  governs a family and that a platform contract adds no behavior and removes
  none. Both sentences survive word for word.
- **The four section contracts** — `experience-direction.v1`,
  `experience-operation.v1`, `experience-console.v1`,
  `experience-collaboration.v1` — are named exactly as they are today.
- **The four native platform contracts** stay one per native body, unchanged.
- **The umbrella's line 3** still names browser, installable web app, phone and
  desktop among the people who build bodies. It names builders, not contracts,
  and it is not touched.
- **`platform-web.v1` is not touched**, clause 9 included.
- **The file's length and status are untouched** — a hundred lines, still
  `(DRAFT — content owner-ratified 2026-09-03)`.
- **Nothing in `contracts/` is edited by this proposal.** The ledger's hash pin
  of `experience.v1.md` therefore still matches, and row CVG-114 stands at *Not
  yet* until the steward's word lands.

## If the steward reads it the other way

**The decision, in one sentence:** are the browser and the installable web app
one body governed by one contract, or two bodies owed two?

- **One body — this proposal.** Clause 15 names `platform-web.v1`. Cost: one
  sentence, no new file, nothing else moves.
- **Two bodies.** `platform-web.v1` splits at its clause 9; a second contract is
  written and pinned; the family index and the ledger's fourteen web rows are
  re-cut. Cost: a new contract, a re-seeded stretch of the ledger, and a clause
  9 that must state a behavior difference nobody has yet observed.

**Recommended: one body.** It is what was built, what the family index already
says, and what the clause's own "one body, one contract" test yields when
installing changes only the frame. The second reading stays available the day a
behavior differs — and this proposal names that seam so it is not lost.
