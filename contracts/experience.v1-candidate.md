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

**This file now carries TWO independent proposals against `experience.v1`.** The
first, below, is clause 15. The second, added 2026-09-04 and starting at *The
second exact change* near the end, is clause 7. They touch different clauses and
do not depend on each other: either may be ratified, declined, or deferred on its
own, and each carries its own evidence and its own *what does not change*.

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

---

## The second exact change — clause 7 (added 2026-09-04)

**Who builds against this:** the intent steward, who decides whose data a
reading is; whoever builds any body, who is told by this clause what may and may
not be kept outside the repository; and whoever reads row CVG-106 in
`ledger/rows.yaml`, which is pinned open on exactly this question.

**Clause 7 — say that the app keeps no copy of the project's truth, and that
your own reading is not the project's truth.**

Today clause 7 reads:

```
7. **The app holds no data of its own.** It shows the project's documents, code
   record, work queue, lanes, return log, and pending decisions. A second copy
   of the truth is a defect, not a cache.
```

Replace it with:

```
7. **The app holds no copy of the project's truth.** It shows the project's
   documents, code record, work queue, lanes, return log, and pending
   decisions, and keeps none of them; a second copy of the truth is a defect,
   not a cache. Your own reading — where you have read to, what you are
   keeping — is yours, kept per person outside the repository.
```

And delete the Reserved / open question this answers, which today reads:

```
- Where the reading cursor behind "what changed since you last read" is kept,
  given the app holds no data of its own.
```

**The arithmetic, because `documents.v1` clause 2 fixes the band at fifty to a
hundred lines and `experience.v1.md` is at exactly a hundred today.** Clause 7
goes from three lines to five (+2); the Reserved bullet is two lines (−2). The
file stays at exactly one hundred lines. No line exceeds eighty characters; the
longest of the five is seventy-seven.

## The evidence

**A cost actually paid, twice, and a check that could not see the thing it was
watching for.** Since converge-f5f (wave 7's Changes view) the app has written
`~/.amplifier/converge-app.state.json` — `app/state_store.py`, with `--state`
overriding the path. Per steward it holds exactly two things: the read point (the
commit that steward has read a document up to) and the kept marks (which changes
that steward has said they are keeping). Read live on 2026-09-04:

```
$ ls -l ~/.amplifier/converge-app.state.json
-rw------- 1 bkrabach bkrabach 251 Sep  3 23:25
top-level keys: ['stewards']
steward 'bkrabach' read keys: ['amplifier-bundle-converge/vision'] kept keys: []
  read amplifier-bundle-converge/vision ->
    {'at': '2026-09-03T23:25:47-07:00', 'sha': 'afd83c8b457da6b8c98e40346d85d485b457ace0'}
```

Two hundred and fifty-one bytes: one steward, one commit sha, one timestamp. No
document text, no work item, no lane state, no return log, no pending decision.

The ledger row that watches this clause, CVG-106, went on printing
`APP-KEEPS-NO-STORE-OF-ITS-OWN` for a whole wave after that file appeared,
because its probe grepped `app/*.py` for `sqlite3|shelve|pickle.dump` and a plain
JSON file is none of those three words. The reconcile after wave 8
(converge-dgc) had to rebuild the probe to read what the store *holds* rather
than what it is spelled — and then could not honestly call the row green or red,
because the clause's letter and the clause's teeth disagree.

**The contract already asked this question and never answered it.**
`experience.v1`'s own Reserved / open questions section reads: "Where the reading
cursor behind 'what changed since you last read' is kept, given the app holds no
data of its own." That is this question, in the clause author's own words. A
Reserved question that the code has since answered in practice, while the clause
still forbids the answer, is drift the ledger cannot record either way.

**The browser was tried and rejected for a stated reason.**
`app/state_store.py`'s own docstring records it: keeping the read point in the
browser "would have been easier and wrong — the steward reads on a laptop and
again on a phone, and the same person must see the same reading." So the choice
was never store-or-no-store. It is whose data this is.

**Why it is the steward's and not the project's.** Where you have read to is not
a fact about the project. Two stewards reading the same repository have
different, equally correct answers, and neither belongs in the repository's
history — committing one would make one person's reading everyone's. The same is
true of a kept mark, which is an answer in progress, not an answer given: the
answers that *are* given still land in the dated ratification record, unchanged
by this proposal.

**What would overturn this.** If that store ever holds a document, a lane, a
work item or a decision — anything the project is the author of — then it is a
second copy of the truth and the old wording was right. CVG-106's rebuilt probe
fires on exactly that: a third per-steward key flips it red. Nothing observed
today does it.

## What does not change

- **"A second copy of the truth is a defect, not a cache" survives word for
  word.** It is the clause's teeth and this proposal keeps them.
- **The six things the app shows** — documents, code record, work queue, lanes,
  return log, pending decisions — are named exactly as they are today, and the
  new wording adds "and keeps none of them", which is stricter, not looser.
- **No behavior changes.** This proposal edits no code and asks for none. It
  describes what `app/state_store.py` already does and decides whether it is
  allowed.
- **The five writes, the ratification record, and clause 8's
  "whatever you can do here, the manager session can do too" are untouched.** A
  read point is not one of the five writes and does not become one.
- **`platform-web.v1` clause 2 is not touched**, though it repeats "It holds no
  data of its own" as the umbrella's requirement. If this proposal is ratified,
  that sentence should follow in its own pass — named here so it is not lost,
  not smuggled into this one.
- **The file's length and status are untouched** — one hundred lines, still
  `(DRAFT — content owner-ratified 2026-09-03)`.
- **Nothing in `contracts/` is edited by this proposal.** The ledger's hash pin
  of `experience.v1.md` still matches, and CVG-106 stands at *Pinned open* until
  the steward's word lands.
- **The clause 15 proposal above is independent.** Ratifying one does not ratify
  the other.

## If the steward reads it the other way

**The decision, in one sentence:** is a steward's own reading — where they have
read to, what they have said they are keeping — the project's data, or theirs?

- **Theirs — this proposal.** Clause 7 says the app keeps no copy of the
  project's truth, and names your reading as yours. Cost: five lines for three,
  one Reserved question closed, CVG-106 becomes *Kept*. `app/state_store.py`
  stays as built.
- **The project's.** Then the store is a defect and must go. The read point and
  the kept marks move into the repository — a per-steward file committed to the
  project's history — or they are dropped, and "what changed since you last
  read" goes back to answering "what changed in the last two commits", which
  converge-f5f was raised to fix. Cost: the Changes view is rebuilt or reduced,
  and every steward's reading becomes part of the project's record.
- **Neither yet.** CVG-106 stays *Pinned open*, the store stays, and the clause
  goes on forbidding in words what the code does in fact. Cost: the ledger
  cannot report this clause either way, and the next reconcile pays the same
  cost a third time.

**Recommended: theirs.** It is the only reading under which both the clause and
the code can be true at once, it keeps the sentence that carries the clause's
teeth, and it answers a question the contract itself left open. The opposite
reading stays available the day the store holds something the project authored —
and CVG-106's probe is set to catch exactly that day.
