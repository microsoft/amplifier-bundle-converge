# Lock sheet — 2026-09-06

One page for the steward's step 5: **lock in the UX**. For every document this
project governs, it answers the four conditions with the evidence behind each,
says in one sentence what still stands between that document and a lock, and
recommends *lock now* · *hold loosely* · *not a candidate*. Then the five
proposal files waiting for a word, and the pinned rows that are questions rather
than work.

This supersedes the readiness table in
[`GAP-ANALYSIS-2026-09-04.md`](GAP-ANALYSIS-2026-09-04.md). Two days of work sit
between them and most of the numbers moved.

**Nothing here locks anything.** Locking is the steward's word, and the whole
point of this sheet is that the word is the only thing missing in several places.

## The four conditions

From [`../PROTOCOL.md`](../PROTOCOL.md) §5 and
[`../../skills/freeze-bar/SKILL.md`](../../skills/freeze-bar/SKILL.md):

1. **It says what it means** — the promises are written down plainly enough that
   someone who has never opened a code editor knows what they commit to.
2. **It carries a real example of right and wrong** — at least one pair that
   actually tells a conforming target from a non-conforming one.
3. **It can be checked against reality** — a check a machine can run, a real
   implementation that passes it, and the whole thing walked end to end once.
4. **The intent steward has read it and agreed.**

<details><summary>Why the two sources word the fourth condition differently, and how this sheet reconciles them</summary>

`PROTOCOL.md` §5 lists the four as: the spec is written · a machine-checkable
kit with a discriminating good/bad fixture pair · at least one real
implementation passes it · a worked example exists end to end. The `freeze-bar`
skill lists: it says what it means · a real example of right and wrong · it can
be checked against reality *and has been walked end to end once* · the steward
has read it and agreed.

The difference is where the worked example sits. This sheet follows the skill:
the worked example under `docs/examples/` is evidence for **condition 3**, which
is the condition that asks for the end-to-end walk, and **condition 4** is the
steward's word. Nothing is dropped and no condition is counted twice.

The four conditions are not the lock. A document may answer all four and still be
left open on purpose — the *hold loosely* state, which the skill calls a decision
rather than a drift, and which the steward chose for three documents on
2026-09-04.
</details>

## Where the evidence came from

Every number below was printed by a command run **today, 2026-09-06**, against
this tree and against the running app.

| | |
|---|---|
| Repository read | this lane's checkout, content identical to `main` at `c9ca71e` — `git diff --stat HEAD..main` printed nothing |
| App read | `http://127.0.0.1:8788`, served from the `main` checkout at `c9ca71e`, working tree clean |
| Ledger read | `ledger/rows.yaml`, 179 rows, self-checks all clear |
| Ratifications read | `owner-ratifications-2026-09-02` … `-06` in this folder |

<details><summary>The seven kit runs and the ledger gate, verbatim</summary>

```
$ uv run conformance/composition/run.py .
  VERDICT: PASS  (pass=14 fail=0 skip=0)
$ uv run conformance/documents/run.py .
  VERDICT: PASS  (pass=18 fail=0 skip=9)
$ uv run conformance/experience/run.py               http://127.0.0.1:8788
  VERDICT: FAIL  (pass=10 fail=6 skip=2)
$ uv run conformance/experience-direction/run.py     http://127.0.0.1:8788
  VERDICT: PASS  (pass=13 fail=0 skip=0)
$ uv run conformance/experience-operation/run.py     http://127.0.0.1:8788
  VERDICT: PASS  (pass=15 fail=0 skip=0)
$ uv run conformance/experience-console/run.py       http://127.0.0.1:8788
  VERDICT: PASS  (pass=10 fail=0 skip=0)
$ uv run conformance/experience-collaboration/run.py http://127.0.0.1:8788
  VERDICT: PASS  (pass=12 fail=0 skip=2)

$ uv run --with pyyaml ledger/checks/verify.py
[OK  ] parses as YAML; top-level LIST of 179 rows
[OK  ] 178/178 quotes verify byte-for-byte (whitespace-collapsed) against contract bytes
[OK  ] all 8 GAP/VIOLATION rows carry a work ref
[OK  ] no GAP/VIOLATION row cites a resolved or unknown work item (8 red rows
       read against the LIVE queue of converge: 266 items)
ALL LEDGER SELF-CHECKS PASS
```

The umbrella kit and the collaboration kit each read a repository half beside the
app; that half is resolved by convention, so both read this checkout — the same
bytes as `main`.

One of the umbrella's six failures is the kit's own transcription of the clause
it judges, not a fault in the app — see that contract's block below before
counting it.
</details>

<details><summary>The ledger, contract by contract — Kept · Not yet · Broken · Pinned open · Can't check</summary>

```
contract                                 Kept    Not yet     Broken     Pinned Cant-check   rows
composition.v1.md                          11          0          0          0          0     11
documents.v1.md                            18          0          0          1          9     28
experience-collaboration.v1.md              9          0          0          1          0     10
experience-console.v1.md                   10          0          0          0          0     10
experience-direction.v1.md                 11          0          0          0          0     11
experience-operation.v1.md                 13          0          0          0          0     13
experience.v1.md                            7          5          0          1          2     15
operation.v1.md                            15          2          0          0          0     17
platform-android.v1.md                      0          0          0          0          9      9
platform-ios.v1.md                          0          0          0          0          9      9
platform-macos.v1.md                        0          0          0          0          9      9
platform-web.v1.md                          7          1          0          0          6     14
platform-windows.v1.md                      0          0          0          0          9      9
surface.v1.md                              13          0          0          0          0     13
TOTAL                                     114          8          0          3         53    178
                                     (+ 1 SYNC row = 179)
```

Two days ago the same tally read 66 Kept · 48 Not yet · 1 Pinned open · 59 Can't
check. The vision has no rows of its own; five `documents.v1` rows judge it
(`CVG-048`, `CVG-059`, `CVG-061`, `CVG-062` keep it; `CVG-049` and `CVG-063`
need a reader, not a scan).
</details>

## The answer in one table

| Document | Recommendation | Because |
|---|---|---|
| `docs/VISION.md` | **lock now** | Four conditions answered; the family it was waiting on has moved; nothing proposes changing it. |
| `composition.v1` | **lock now** | Four conditions answered; every row Kept; both 2026-09 amendments applied with their changelog rows. |
| `documents.v1` | hold loosely | Its own clause 5 is pinned open against it — eight of forty-three clauses break the rule it would freeze. |
| `operation.v1` | hold loosely | Two clauses are not yet kept: one waits on an event this host has never had, one is a real miss. |
| `experience.v1` | not a candidate | Clause 15 names two contracts that do not exist, clause 7 is pinned open, and five of its own rules do not pass. |
| `experience-direction.v1` | hold loosely | Kit clear and every row Kept — but a proposal against it is open, and the guard could not apply it if the file were locked. |
| `experience-operation.v1` | hold loosely | The same. |
| `experience-console.v1` | hold loosely | The same, and a ratification was recorded against it on 2026-09-05 that never reached the contract. |
| `experience-collaboration.v1` | hold loosely | The same, plus one pinned open row. |
| `platform-web.v1` | hold loosely | One promise not yet kept, six that need a rendered viewport, and no kit of its own. |
| `platform-ios.v1` | not a candidate | No body exists to judge. |
| `platform-android.v1` | not a candidate | No body exists to judge. |
| `platform-macos.v1` | not a candidate | No body exists to judge. |
| `platform-windows.v1` | not a candidate | No body exists to judge. |
| `surface.v1` | not a candidate | Superseded 2026-09-03 by the experience family. |

Two of fifteen are ready for the word today. Seven are held loosely, and in four
of those the thing being waited on is the same thing: a word on the proposal
sitting beside them. Six are not candidates, and five of those six are honest —
no body, or superseded. The sixth, the umbrella, is the one with real work left.

---

## Per document

### `docs/VISION.md` — lock now

| Condition | Answer | Evidence |
|---|---|---|
| 1 says what it means | yes | Sixty-nine lines, inside the two-screen bound — `documents` rule 2b |
| 2 right and wrong | yes | `conformance/documents/` with `fixtures/sample-good` and `fixtures/sample-bad` |
| 3 checked against reality | yes | `documents` rules 2b, 7a, 7b all clear; four ledger rows keep it, two need a reader |
| 4 steward read and agreed | yes | 2026-09-02 (`lgtm`), principle 8 amended 2026-09-03 round 3 |

**What still stands in the way:** nothing but the word — the 2026-09-04 decision
to hold it loosely gave "let the family mature first" as its reason, and the
family has since moved from two passing kits to six of seven.

**Recommendation — lock now.** It has not changed since 2026-09-03, no proposal
asks to change it, and every check that can reach it is clear. One caution: the
hold-loosely call of 2026-09-04 lives only in
[`owner-ratifications-2026-09-03.md`](owner-ratifications-2026-09-03.md) round 4
and not in the vision itself, which is where the `freeze-bar` skill says a
deliberate hold belongs. Locking it settles that; leaving it open does not.

### `contracts/composition.v1.md` — lock now

| Condition | Answer | Evidence |
|---|---|---|
| 1 says what it means | yes | Seven Core clauses, ratified content, shape rules clear |
| 2 right and wrong | yes | `conformance/composition/fixtures/sample-good` and `sample-bad` |
| 3 checked against reality | yes | Kit `PASS 14·0·0` on this tree; worked example `docs/examples/composition.md`; ledger 11 Kept and nothing else |
| 4 steward read and agreed | yes | 2026-09-02; Core 4 amended 2026-09-04; Core 5 rewritten 2026-09-06 round 1 |

**What still stands in the way:** nothing but the word.

**Recommendation — lock now.** This is the strongest candidate on the sheet: no
row is anything but Kept, both amendments are applied in place with their
changelog rows and their archived proposals, and the kit's own guard rules
(`7a`, `7b`) are the ones that will police the lock afterwards. One stale fact to
hand back to its owner: [`../../PINS.md`](../../PINS.md) still says the new Core
5 text has not reached the contract, and it has —
`contracts/composition.v1.md:29` carries it.

### `contracts/documents.v1.md` — hold loosely

| Condition | Answer | Evidence |
|---|---|---|
| 1 says what it means | yes | Fourteen Core clauses, amended twice and ratified twice |
| 2 right and wrong | yes | `conformance/documents/fixtures/sample-good` and `sample-bad` |
| 3 checked against reality | yes | Kit `PASS 18·0·9` on this tree; worked example `docs/examples/documents.md`; ledger 18 Kept, 1 Pinned open, 9 Can't check |
| 4 steward read and agreed | yes | 2026-09-02, amended and ratified again 2026-09-03 round 2 |

**What still stands in the way:** row `CVG-060` is pinned open against this
contract's own clause 5 — the clause asks for one to three plain lines of why,
and eight of forty-three clauses across the repository run past three.

**Recommendation — hold loosely, and answer the pinned row first.** Locking
clause 5 as written would freeze a rule the repository visibly does not keep in
eight places; that is a promise broken at the moment of locking. The question is
one sentence long and it is below.

### `contracts/operation.v1.md` — hold loosely

| Condition | Answer | Evidence |
|---|---|---|
| 1 says what it means | yes | Fourteen Core clauses; Core 14 added and ratified 2026-09-06 |
| 2 right and wrong | yes | No file-scan kit, and none is possible — the turnkey harness is the check, and it has genuinely refused: runs C and D failed before runs E and F passed |
| 3 checked against reality | yes | `evaluations/turnkey/RESULT.md` green nine of nine, twice, in fresh containers; `evaluations/adopter/RESULT.md` green twelve of twelve on 2026-09-06; worked example `docs/examples/operation.md` |
| 4 steward read and agreed | yes | 2026-09-02; turnkey sentence 2026-09-04 round 4; Core 14 2026-09-06 round 1 |

**What still stands in the way:** two clauses are not yet kept, and they are not
the same kind of miss — `CVG-019` (stalls are decisions, not loops) waits on an
event this host has never produced, while `CVG-023` (hand off when done) is a
real one: three of six recorded closes say what finished and never what remains.

**Recommendation — hold loosely.** Fifteen of seventeen rows are Kept and the
harness behind them is green, but one of the two open clauses is a promise the
project is visibly not keeping in half the cases it has produced. Close
`CVG-023` and this becomes the next document to lock.

### `contracts/experience.v1.md` — not a candidate

| Condition | Answer | Evidence |
|---|---|---|
| 1 says what it means | yes | Fifteen Core clauses, ratified 2026-09-03 |
| 2 right and wrong | yes | `conformance/experience/` arrived 2026-09-04 with both fixtures |
| 3 checked against reality | **no** | Kit `FAIL 10·6·2` against the app — rules `4b`, `6a`, `9`, `12`, `13`, `15` do not pass |
| 4 steward read and agreed | yes | 2026-09-03 round 3 |

**What still stands in the way:** the umbrella still names `platform-browser.v1`
and `platform-web-app.v1`, neither of which has ever existed, and five of its own
clauses are not yet kept while a sixth is pinned open.

**Recommendation — not a candidate today, and it is the keystone.** Both open
proposals against it are in one file and either can be answered alone: clause 15
(name the web contract that exists) and clause 7 (say what the app may keep
outside the repository). Rules `9` and `13` come green the moment the four
section proposals are ratified, because those rules read the section contracts,
not the app. Rules `4b` and `12` are the same surplus counted twice — ten routes
that write where the clause allows five, and six features no contract in the
family names — and that is app work, tracked as `CVG-103`.

**One of the six is not a real failure, and the steward should not read it as
one.** Rule `6a` reports the app serving a lane state outside the clause's
vocabulary. The word is *Silent — may have died*, which is verbatim what clause 6
lists; the kit's own copy of that vocabulary keeps only *Silent* and drops the
three words after the dash, so an exact match cannot succeed. The app is right,
the clause is right, and the kit's transcription of the clause is short. Filed as
work. Read honestly, the umbrella has five failing rules, not six.

<details><summary>How this was measured</summary>

```
contracts/experience.v1.md:36
   Stuck · Done*. Lanes: *Working · Quiet · Silent — may have died*.

conformance/experience/run.py:180
    "lanes": ("Working", "Quiet", "Silent"),

read live from the app, GET /api/managers/converge/operation
   lane statusLabels served: ['Silent — may have died']
```
</details>

### `contracts/experience-direction.v1.md` — hold loosely

| Condition | Answer | Evidence |
|---|---|---|
| 1 says what it means | yes | Eleven Core clauses, ratified 2026-09-03 |
| 2 right and wrong | yes | `conformance/experience-direction/fixtures/sample-good` and `sample-bad` |
| 3 checked against reality | yes | Kit `PASS 13·0·0` against the app; worked example `docs/examples/experience-direction.md`; ledger 11 Kept and nothing else |
| 4 steward read and agreed | yes | 2026-09-03 round 3 |

**What still stands in the way:** a proposal against this contract is open and
unanswered, and it carries no `target:` line, so the guard would not be able to
apply it once the contract is locked.

**Recommendation — hold loosely until the proposal is answered.** Every check
that reads this contract is clear, so on its own reading it is ready. But
locking a document that has an unanswered proposal beside it puts the change on
the proposal path — and the proposal path is the one thing measured to be broken
here today, because five of five files in `contracts/` lack the line the guard
reads. Answer the proposal, or add the line, before the lock.

### `contracts/experience-operation.v1.md` — hold loosely

| Condition | Answer | Evidence |
|---|---|---|
| 1 says what it means | yes | Thirteen Core clauses, ratified 2026-09-03 |
| 2 right and wrong | yes | `conformance/experience-operation/fixtures/sample-good` and `sample-bad` |
| 3 checked against reality | yes | Kit `PASS 15·0·0` against the app; worked example `docs/examples/experience-operation.md`; ledger 13 Kept and nothing else |
| 4 steward read and agreed | yes | 2026-09-03 round 3 |

**What still stands in the way:** the same open proposal and the same missing
`target:` line.

**Recommendation — hold loosely until the proposal is answered.** Identical
reading to Direction: the contract's own checks are clear and the only thing
open is the word on its proposal.

### `contracts/experience-console.v1.md` — hold loosely

| Condition | Answer | Evidence |
|---|---|---|
| 1 says what it means | yes | Ten Core clauses, ratified 2026-09-03 |
| 2 right and wrong | yes | `conformance/experience-console/fixtures/sample-good` and `sample-bad` |
| 3 checked against reality | yes | Kit `PASS 10·0·0` against the app; worked example `docs/examples/experience-console.md`; ledger 10 Kept and nothing else |
| 4 steward read and agreed | yes, and this is the one to look at | 2026-09-03 round 3; a further word on its proposal recorded 2026-09-05 at 20:01:47 |

**What still stands in the way:** the record says this contract's proposal was
ratified on 2026-09-05, and the contract has not changed since 2026-09-04 —
its ten clauses still carry none of the four words the proposal adds.

**Recommendation — hold loosely, and settle the ratification first.** This is
the sheet's one genuine surprise and it is worth a moment: the app's decision
write appends the steward's word to the day's ratification record and does not
touch the contract, so a word given in the app leaves the change unapplied unless
someone applies it. Either the 2026-09-05 word is live and owed an apply, or it
was a trial of the write and the record overstates it. Locking this contract
before that is settled would freeze the text the steward already agreed to
replace. Filed as work.

<details><summary>How this was measured</summary>

```
$ git log --oneline -2 -- contracts/experience-console.v1.md
19a3d7b H1 status: record the steward's given words … — nothing locked
95d2a06 contracts: experience-console.v1 (DRAFT) — the Manager Console

$ grep -c "REQUIRED\|IDIOM\|EXCLUDED" contracts/experience-console.v1.md
0
$ grep -n "Changelog" contracts/experience-console.v1.md
(no match)
```

and, from `conformance/experience/run.py` against the app today:

```
[FAIL] 9  section contracts with behaviors carrying none of ['REQUIRED', 'IDIOM',
          'OPTIONAL', 'EXCLUDED']: experience-collaboration.v1.md (10 of 10);
          experience-console.v1.md (10 of 10)
```

`app/writes.py:record_decision` — *"Append the steward's word to today's
ratification record."* The composition and operation entries recorded the same
day did reach their contracts, each with a changelog row; this one did not.
</details>

### `contracts/experience-collaboration.v1.md` — hold loosely

| Condition | Answer | Evidence |
|---|---|---|
| 1 says what it means | yes | Ten Core clauses, ratified 2026-09-03 |
| 2 right and wrong | yes | `conformance/experience-collaboration/fixtures/sample-good` and `sample-bad` |
| 3 checked against reality | yes | Kit `PASS 12·0·2` against the app and this repository; worked example `docs/examples/experience-collaboration.md`; ledger 9 Kept, 1 Pinned open |
| 4 steward read and agreed | yes | 2026-09-03 round 3 |

**What still stands in the way:** the same open proposal and missing `target:`
line, plus row `CVG-186`, pinned open on whether the app's headless drafting
session puts the manager session in the hot path.

**Recommendation — hold loosely.** Two things to settle rather than one, and the
pinned row is a question for the steward, not work for a lane. Its two skipped
rules are honest: a teammate's comment coming back from a real host, and a second
person's word reaching the ratification record, need two people and a live host.

### `contracts/platform-web.v1.md` — hold loosely

| Condition | Answer | Evidence |
|---|---|---|
| 1 says what it means | yes | Fourteen Core clauses, ratified 2026-09-03 |
| 2 right and wrong | partly | No kit of its own; its rows lean on the section kits and on direct reads of the app, and the worked example runs a real browser at 390 and 1280 |
| 3 checked against reality | **no** | Ledger 7 Kept, 1 Not yet (`CVG-210`, offline refusal of the five writes), 6 Can't check — all six need a rendered viewport |
| 4 steward read and agreed | yes | 2026-09-03 round 3 |

**What still stands in the way:** one promise is not yet kept — offline, the app
must refuse the five writes in a plain sentence — and six more cannot be judged
without a rendered-width harness nobody has built.

**Recommendation — hold loosely.** Six of fourteen rows unjudgeable is too much
silence to freeze around; a body contract locked on a check that cannot see most
of it is a promise nobody can hold anyone to.

### `contracts/platform-ios.v1.md` · `-android` · `-macos` · `-windows` — not a candidate

| Condition | Answer | Evidence |
|---|---|---|
| 1 says what it means | yes | Nine Core clauses each, ratified 2026-09-03 |
| 2 right and wrong | **no** | No kit; a platform contract is entirely about the shape a behaviour takes in one body |
| 3 checked against reality | **no** | No body; all nine rows on each are Can't check, thirty-six in total |
| 4 steward read and agreed | yes | 2026-09-03 round 3 |

**What still stands in the way:** there is no iOS, Android, macOS or Windows body
to point a check at, so an example could only describe a screen nobody has built.

**Recommendation — not a candidate, and this is not neglect.**
[`docs/examples/README.md`](../examples/README.md) records the same reading, and
each has a filed item deferred as a sub-project with its own repository, steward
and Converge instance. When a body exists, its example is written the way
`platform-web.md` was and these four come back to this sheet.

### `contracts/surface.v1.md` — not a candidate

Superseded on 2026-09-03 by the experience family; its kit moved to
`conformance/_superseded/`. Thirteen rows, all Kept, kept for the record. Build
against the family, not against this.

---

## The five proposals waiting for a word

Five files sit in `contracts/` beside the contracts they change, carrying six
proposals between them — the umbrella's file holds two, against different clauses.
The steward answers each with one word: ***ratified*** · ***ratified with edits***
· ***declined*** · ***later***. Every one may be answered on its own.

**Before any of them:** five of five carry no `target:` line, which is the line
the guard reads to find which contract a proposal amends. While every contract is
a draft nothing notices. The day one of these contracts is locked and its
proposal is ratified, the guard will not find the proposal and the ratified
change cannot be applied through the sanctioned path. Open as `converge-jews`.

<details><summary>Measured on this tree today</summary>

```
$ for f in contracts/*-candidate.md; do grep -qiE '^target:[[:space:]]*.+' "$f" \
    && echo "HAS target: $f" || echo "no target:  $f"; done
no target:  contracts/experience-collaboration.v1-candidate.md
no target:  contracts/experience-console.v1-candidate.md
no target:  contracts/experience-direction.v1-candidate.md
no target:  contracts/experience-operation.v1-candidate.md
no target:  contracts/experience.v1-candidate.md
```
</details>

### File 1 of 5 · `contracts/experience.v1-candidate.md` — clause 15

Clause 15 names `platform-browser.v1` and `platform-web-app.v1` as the web body's
contracts; neither has ever existed, and what exists is one `platform-web.v1`,
ratified in the same pass as the umbrella that names them. The change replaces
the two names with the one real name. A family member named and unwritten is a
promise nothing keeps, and the umbrella's own rule 15 fails on exactly this today.
Nothing else in clause 15 moves. Raised by `converge-d3n`, watched by `CVG-114`.
**Your word:** *ratified* · *ratified with edits* · *declined* · *later*.

### File 1 of 5, second proposal · same file — clause 7

The same file carries a second, independent proposal, answerable on its own.
Clause 7 says the app holds no data of its own; the app has kept each steward's
read point and kept marks outside the repository since wave 7, and the contract's
own Reserved section already asked where that cursor should live. The change says
the app holds no copy of the project's *truth*, and that your own reading is
yours, kept per person outside the repository — then deletes the Reserved
question it answers. The file stays at exactly one hundred lines; this is what
row `CVG-106` is pinned on.
**Your word:** *ratified* · *ratified with edits* · *declined* · *later*.

### File 2 of 5 · `contracts/experience-direction.v1-candidate.md`

Direction already tags each of its eleven clauses with one of the four words, so
this proposal only adds the missing half: where each behavior sits across full
app · quick-access · notification. It excludes both other classes throughout,
because reading and answering a document needs the document. It also turns the
tag from italic to a code span, because the plain-words rule reads an unquoted
`EXCLUDED` as a machine state token in prose. Raised by `converge-er6`; the open
item is `converge-pip`. **Your word:** *ratified* · *ratified with edits* ·
*declined* · *later*.

### File 3 of 5 · `contracts/experience-operation.v1-candidate.md`

The same shape as Direction: thirteen clauses already tagged, the placement added,
the tag form corrected. It gives quick-access clauses 6 and 7 and notification
clause 8 as optional, because lanes running against intended and a lane falling
silent are the two genuinely glanceable facts. Applying this and the other three
is what turns the umbrella's rules 9 and 13 green — no code and no ledger edit.
Length after the change: ninety-nine lines, inside the bound.
**Your word:** *ratified* · *ratified with edits* · *declined* · *later*.

### File 4 of 5 · `contracts/experience-console.v1-candidate.md`

Console tags nothing today — ten of ten clauses carry no word — so this proposal
adds both halves at once: six required, one idiom, three excluded, and both other
surface classes excluded throughout, a console being one live session beside the
work. The three exclusions are real refusals, not blanks: the console as the
dashboard, the console ratifying, and a native chat depended on in v1.
**This one may already have your word**, recorded 2026-09-05 and never applied —
see that contract's block above before answering again.
**Your word:** *ratified* · *ratified with edits* · *declined* · *later*.

### File 5 of 5 · `contracts/experience-collaboration.v1-candidate.md`

Collaboration also tags nothing today, ten of ten. The proposal gives it seven
required, one idiom and two excluded, and places them: quick-access excluded
throughout, notification carrying clause 6 as optional — an inbound proposal
arriving being the one thing here worth a glance. Its two exclusions are a direct
channel between two manager sessions, and a second collaboration surface.
Length after the change: ninety-six lines, inside the bound.
**Your word:** *ratified* · *ratified with edits* · *declined* · *later*.

---

## The pinned rows — questions, not work

A pinned row is a place where the contract and the code disagree and the
disagreement is a decision only the steward makes. Each is one sentence.

**`CVG-106` / `converge-71q` — the app's own reading store.** The app keeps, per
steward and outside the repository, two things: which commit you have read a
document up to, and which changes you said you are keeping — 339 bytes on this
host, with no document text, no work item and no lane state; is that "data of
its own", which `experience.v1` clause 7 forbids, or is your own reading simply
not the project's truth? *(A proposal is already written for the second answer —
file 1's second proposal, above.)*

**`CVG-186` / `converge-nn6` — the headless drafting session.** The app's write
path can start a second process, a headless drafting session, off by default; is
that "the manager session in the hot path", which `experience-collaboration.v1`
clause 7 forbids, or is an opt-in helper on a write path something else? *(No
proposal is written; the answer decides whether one is needed.)*

**`CVG-060` — the length of a reason.** `documents.v1` clause 5 asks every Core
clause for one to three plain lines of why, and eight of forty-three clauses run
past three; does the clause move to fit the writing, or does the writing come
back to fit the clause? *(This one gates the `documents.v1` lock.)*

---

## What this lane changed

This file, and nothing else. Four things it found and filed rather than fixed,
because they are outside this lane's ownership:

- `converge-5i5m` — the 2026-09-05 ratification of the console proposal that
  never reached the contract, and the fact that nothing reports the gap;
- `converge-fgct` — the umbrella kit's copy of clause 6's lane vocabulary, which
  drops three words and so reports a correct app as wrong;
- `converge-0ket` — the 2026-09-04 decision to hold three documents loosely,
  recorded in the ratification record but not in the documents themselves, where
  the `freeze-bar` skill says a deliberate hold belongs;
- `converge-ao32` — `PINS.md`'s note that the new `composition.v1` Core 5 text
  has not landed, which it has.

And one thing it deliberately did not do: nothing here changes a contract, a
kit, or the ledger. A sheet that fixed what it found would be a sheet the
steward could not trust as a reading of what is.
