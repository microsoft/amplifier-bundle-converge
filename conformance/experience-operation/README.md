# experience-operation.v1 conformance kit

The runnable definition of **"Operation keeps its promises."** Point it at the
companion app — the running server, or a snapshot captured from it — and it
mechanically asserts
[`contracts/experience-operation.v1.md`](../../contracts/experience-operation.v1.md)
against what the app actually serves.

Stdlib only, and **no browser is launched**.

## The target is the app, and the app is not a page

Same target model as the other two experience kits, and the same reason: the app
serves one shell and fills it from `/api/…`. A target is read as four kinds of
thing — the served `html`, the `json` payloads, the `js`/`css` client, and the
app's own `openapi` route table — and every rule says which it read. See
[`../appsnapshot.py`](../appsnapshot.py).

Operation is a **reading surface**, so most of its promises are about what is
shown and in what order — exactly what a served shell plus a real payload can
settle.

## Run it

```sh
uv run --extra app python -m app.serve --port 8788
export CONVERGE_APP_COOKIE="…"     # the app's own signer; no loopback exemption
uv run conformance/experience-operation/run.py http://127.0.0.1:8788
```

A JSON report on **stdout**, a human summary on **stderr**, exit **0** unless a
rule FAILs. `--json-only` suppresses the summary; `--capture <dir>` writes a
snapshot that is a target in its own right.

## What it checks

Rows are numbered to the contract's **Core clause** numbers — rule 7 judges
Core 7. Where one clause carries two independent promises the kit emits one row
per promise, lettered inside the clause. **Every one of the thirteen Core
clauses has a row**, and `test_every_core_clause_has_a_row` fails if one does
not.

| # | Clause | The promise this operationalizes | How the kit checks it, against the app |
|---|---|---|---|
| 1 | Core 1 | "The objective, the limits, and today's strategy stand at the top, in the manager session's own words" | All three must be non-empty in the manager payload, and the elements that carry them must sit **above** the waves and the lanes in the served shell. |
| 2a | Core 2 | "The plan is shown in waves, with the lanes inside them" | Every wave carries its lanes, and every lane names its wave. A wave with nothing in it, or a lane in no wave, fails. |
| 2b | Core 2 | "every grouping carries its reason … when the plan is redrawn, the reason for the redraw is shown too" | A wave must carry a reason. A title whose comma-separated parts are the wave's **own lane names** is a list, not a reason, and is reported as one. |
| 3 | Core 3 | "The return brief is the first thing a returning steward reads" | The brief must exist, sit above the lists of work, and say all five of its parts: time away · what finished · what is stuck · what needs your word · what quietly changed. Read as a keyword pass over the brief's own sentences. |
| 4 | Core 4 | "A confidence timeline … each turn in it opens onto its evidence" | Every timeline entry must carry something to open. An entry that states confidence moved and gives the reader no way to inspect why fails. |
| 5a | Core 5 | "Work derived, resolved, verified, reopened, and stuck say whether things are moving" | All five flow measures shown. Four of five is named, not rounded up. |
| 5b | Core 5 | "Throughput is shown as flow, and never offered as outcome" | Flow and the outcome reading must both be present and shown apart, and no single measure may sum one into the other. |
| 6 | Core 6 | "Lanes running are shown against lanes intended, with the fill control beside them" | Both numbers, the control beside them, and the control reaching a write the app declares — so filling can update the ratio and the plan. |
| 7 | Core 7 | "Work truly ready is shown against work waiting on you" | Two numbers. One of them is the steward's own backlog, and seeing it is what keeps the operation from stalling politely behind a person. |
| 8 | Core 8 | "Each lane carries a plain state word and evidence you can open" | Read over **both** lists of lanes. The kit reads **which field the surface actually shows** for each, and asserts every lane at work is in the lane vocabulary — *Working · Quiet · Silent — may have died* — and every lane that has reported back is in the work vocabulary — *Done · Stuck*. Offending lanes are named, one at a time. Every lane in either list must carry evidence, and **no lane id may appear in both lists**. |
| 9 | Core 9 | "Watch session opens that worker session's live view" *(IDIOM)* | A watch control whose handler targets the lane's **own** session, and lanes that name a session to reach. Where the body also offers Watch on a lane that has **reported back**, that handler is held to the same standard; a body that does not offer it is not faulted for absence. |
| 10 | Core 10 | "Feedback can be dropped in seconds, in whatever form is to hand" *(IDIOM)* | Every form the body claims must work and reach the feedback write. Forms the body does not offer are **named**, because where a body cannot do a thing `experience.v1` clause 14 asks it to say so in the app. |
| 11 | Core 11 | "Steering sets the limits and never assigns the work" | Exactly the five limits — objective, budget, lane count, fill the lanes, have the manager review this — and no control that hands a piece of work to a lane. |
| 12 | Core 12 | "Stopping something is never a board button" | Every control's own label, title and aria-label is read; a stop, kill, abort, terminate or halt control on the board fails. |
| 13 | Core 13 | "Every manager session you run is listed, sorted by which one needs you, and you can tell them all at once" | The list, the sort by what needs you, and one message that reaches all of them. |

## Two lists of lanes, and both are judged

The operation payload carries lanes in two: `lanes` (still at work, read in the
lane words *Working · Quiet · Silent — may have died*) and `reported` (already
come back, read in the work words *Done · Stuck*). The split is legitimate — it
is what lets Core 8 be kept without stretching a three-word vocabulary over a
state it has no word for.

What was not legitimate is that until 2026-09-04 rules 8 and 9 read only
`lanes` (work item converge-0w2). Measured against the live app that day: **75
lanes sat in `reported` and none of them was judged by anything.** A reported
lane could have carried any word at all, or no evidence, and this kit would
still have said PASS.

**A list nobody judges is a place to hide a lane.** Both rules now read both
lists, and rule 8 additionally faults a lane id appearing in *both* — the other
way the split could be used to dodge a check, since each list is read in a
different vocabulary and a lane in both is told in two states at once.

`test_a_reported_lane_is_judged_like_a_working_one` instantiates the three
faults directly, by patching a passing snapshot rather than by hand-editing a
generated fixture.

## What a static read buys, and what it does not

It settles order, presence, vocabulary, and whether a control reaches a declared
write. It cannot judge a rendered layout, and it cannot prove what a write
records once it lands.

### A function is read from its definition, not its import

Rule 6 reported a **fabricated FAIL** during this kit's build: `fillLanes` first
appears in `import { … fillLanes … }` at the top of `main.js`, so reading "the
brace after the first mention" returned an import list rather than the function
— and the fill control looked like it reached no write, when it calls
`api.steer` two lines down. `function_body()` now finds the definition, and
`test_a_function_is_read_from_its_definition_not_its_import` keeps it that way.

The same file blanks string literals before reading a handler, for the reason
the direction kit's README records: a write is a **call**, not a word in a
message.

## Fixtures (the kit's own proof)

Both are **captured app snapshots**, the shape `--capture` writes, so they are
judged through exactly the code path a live app is.

- `fixtures/sample-good/` — objective, limits and strategy above the work; waves
  each carrying a reason; a five-part brief; a timeline entry that opens onto its
  evidence; all five flow measures apart from the confidence reading; the lane
  ratio with a fill control that reaches a write; both queue numbers; lanes in the
  lane vocabulary with evidence; Watch session; feedback in three forms; five
  steering limits; no stop control; managers sorted by need with a tell-all.
  **PASS on all fifteen rules.**
- `fixtures/sample-bad/` — an empty objective, an empty wave and an orphan lane,
  titles that are lane-name lists, an empty brief, a timeline with nothing to
  open, two flow measures and no outcome reading, no lane ratio, neither queue
  number, a lane reading `done` with no evidence, no watch control, no feedback,
  one steering limit, a **Stop this lane** button, and an unsorted list with no
  tell-all. **FAIL on all fifteen.**

Both are rewritten by
[`../experience-fixtures/make_fixtures.py`](../experience-fixtures/make_fixtures.py).

## Self-test

```sh
uv run --with pytest pytest conformance/experience-operation/tests/ -q
python3 conformance/experience-operation/tests/test_conformance.py   # no deps
```

`test_every_rule_has_a_negative_fixture` is load-bearing. This kit declares **no**
SKIPs, and `test_skip_set_is_pinned` fails if one appears.

## Measured against the running app

2026-09-03, against `http://127.0.0.1:8788`: **PASS 7 · FAIL 8 · SKIP 0**. The
eight were true findings — waves titled by their lane names with no reason, a
brief that never said what finished or what is stuck, a timeline with nothing to
open, no `stuck` flow measure, no *truly ready* number, 42 lanes reading `done`
and 2 reading `stuck` against a three-word lane vocabulary, four steering limits
of five, and no way to tell every manager session at once.

2026-09-04, against `http://127.0.0.1:8791` reading the same real batch:
**PASS 15 · FAIL 0 · SKIP 0**. The eight have since been repaired by the lanes
that owned them. Rule 8 reads both lists on this run:

    8 PASS - every one of 4 working lane(s) reads as a plain lane word
             (['Working']) and every one of 79 reported lane(s) reads as a
             plain work word (['Done', 'Stuck']); all carry evidence to open,
             and no lane is in both lists

Those **79 reported lanes were judged by nothing at all** until this run — the
number is worth keeping here, because it is the size of what a rule that reads
one of two lists was quietly passing.

A FAIL here is a **true finding, not a bug in the kit to be tuned away.**
