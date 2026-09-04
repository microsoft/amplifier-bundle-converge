> **SUPERSEDED 2026-09-03 — this kit is retired and no longer runs.**
>
> `surface.v1` was superseded by the experience family on 2026-09-03 (steward's
> word: *"Yes, ratified, please go."* — see
> [`docs/workflow/owner-ratifications-2026-09-03.md`](../../../docs/workflow/owner-ratifications-2026-09-03.md)).
> The promises this kit checked are now held by
> [`experience.v1`](../../../contracts/experience.v1.md) and its section
> contracts, and judged by three kits that read the **companion app** rather
> than a set of rendered pages:
> [`conformance/experience-direction/`](../../experience-direction/) ·
> [`conformance/experience-operation/`](../../experience-operation/) ·
> [`conformance/experience-console/`](../../experience-console/).
>
> **No live ledger row cites a rule in this kit.** It is kept for the record —
> and because the three kits that replaced it inherited its machinery and its
> lessons, which are recorded below. Nothing here is maintained.

# surface.v1 conformance kit

The runnable definition of **"the companion app keeps its promises."** Point it
at the app — the running server, or the pages rendered from it — and it
mechanically asserts the conformance list of
[`contracts/surface.v1.md`](../../contracts/surface.v1.md), plus the three
clause-halves that had no check at all.

Stdlib only, and **no browser is launched**.

## The target is the app, not a mockup

The kit used to look for the mockup's way of keeping the promises: `data-goto`
navigation, a `#needCount`, a `fillLanes` routine, script handlers wiring them
together. The app that shipped keeps the same promises **with no script at
all** — places are links to real routes, answering is a form that posts and
re-renders a shorter list, the lock control is a disabled button, what-changed
is a rendered list of removed and added sentences. So the kit reported FAIL on
seven rules for an app that was not broken, and a steward could not tell a real
defect from a shape mismatch (converge-e59).

Every rule below is now written against what the app serves.

### Point it at the running app

```sh
# one terminal: the app, reading this project
uv run --extra web amplifier-converge web --repo . --port 8091

# another: the kit
uv run conformance/surface/run.py http://127.0.0.1:8091 \
  --changes-nothing '/direction/*/mark-read'
```

It fetches the three places, then every document and proposal they link to (up
to 30 pages), and judges the set.

### Or point it at the pages, written out

```sh
uv run --extra web --with httpx conformance/surface/render.py \
  --repo . --out /tmp/converge-pages --exercise-what-changed

uv run conformance/surface/run.py /tmp/converge-pages
```

[`render.py`](render.py) writes every page the app serves plus a `pages.json`
naming the route each file came from, and copies the app's own
`NON_WRITE_POSTS` into the manifest so `--changes-nothing` is not needed by
hand. It reads your project and never writes to it: the last-read markers go to
a throwaway app home.

`--exercise-what-changed` is the one flag that does more than fetch. "What
changed since you last read this" only has something to show once a document
has been read **and then changed**, so with that flag `render.py` copies
`docs/`, `contracts/` and `conformance/` to a temporary project, marks one
document read through the app's own route, removes a sentence from the copy,
and renders that document page again. The change is real and the page's answer
to it is the app's own — it just happens to a copy rather than to your project.
Without the flag, rule 6 SKIPs and says exactly this.

A lone `index.html` still works, for a quick look at one page. Rules that need
the page set say so rather than failing it.

### `--changes-nothing` is a claim someone has to make

surface.v1 Core 3 says **exactly four writes**. The app puts all four under
`/do/`, and has one further POST — `mark-read` — that changes nothing about the
project (the marker lives outside it). It names that in
`web/app.py` `NON_WRITE_POSTS` precisely so "exactly four" stays a claim anyone
can check.

The kit will not take that on trust from the markup, because a fifth write
would look identical. Any POST outside the write prefix **fails rule 3a** until
someone declares it — with `--changes-nothing`, or in `render.py`'s manifest.
The declaration is visible in the command that produced the report.

## What a static read buys, and what it does not

It can prove a promise is *wired*: that a place link resolves to a page the app
serves, that the strip's stated length agrees with the number of cards on it,
that the lock control's `disabled` agrees with its own four conditions, that a
diff has a removed sentence to show, that the surface names the manager-session
operation each write is. A promise wired to nothing fails, loudly, naming the
missing half.

It cannot judge a render. That row reports `SKIP` with its reason, never a
fabricated PASS — see *The one SKIP* below.

## Run it

```sh
uv run conformance/surface/run.py <url | dir | page>
```

Output: a JSON report on **stdout** and a human summary on **stderr**. Exit
code is **0** when no rule FAILs, **1** when any rule FAILs. Add `--json-only`
to suppress the stderr summary.

```sh
# a conforming page set -> VERDICT: PASS, exit 0
uv run conformance/surface/run.py conformance/surface/fixtures/sample-good

# a broken one          -> VERDICT: FAIL (all fourteen checkable rules), exit 1
uv run conformance/surface/run.py conformance/surface/fixtures/sample-bad
```

## What it checks

Rows are numbered to the contract's **Core clause** numbers — rule 7 judges
Core 7 — so a failing rule names the clause it breaks. Where one clause carries
several independent promises the kit emits one row per promise, lettered inside
the clause (`8a`, `8b`, `8c`), so a failure names the exact promise rather than
the whole sentence. **Every one of the ten Core clauses has a row**, and
`test_every_core_clause_has_a_row` fails if one does not.

The kit was numbered to the *Conformance kit asserts* bullets until 2026-09-03,
when the steward ratified the Core-clause anchor
([`docs/workflow/owner-ratifications-2026-09-03.md`](../../docs/workflow/owner-ratifications-2026-09-03.md),
call 2). Under the bullet anchor, five bullets covered ten clauses and Core 4
and Core 5 had **no row at all** — and a missing row is invisible, because
nothing looks wrong. Rules 4 and 5 below are those rows.

| # | Clause | The promise this operationalizes | How the kit checks it, against the app |
|---|---|---|---|
| 1a | Core 1 | "Places switch" | Every page carries the rail; every `a.place` href must resolve to a route the app actually served; exactly one place is marked `is-on` and it is the page you are on. A place pointing at a route that does not exist is the failure this catches. **SKIP** when the target is a single page — one page cannot show switching. |
| 1b | Core 1 | "answering marks the card and shortens the list" | The list must say how long it is (the heading, the rail badge, or both) and **that number must equal the number of cards on it** — which is what makes answering one demonstrably shorten it in a server-rendered page. Each card must post to a write route, carry a word to press, and say where to come back to. At most five cards (Core 1). |
| 2 | Core 2 | "Every answer lands in the dated ratification record" | The surface's own statement of where an answer lands must name the **ratification record** and must be **dated**; and every form that answers must name what it answers, so the record can say. An answer landing in "the session log" fails. |
| 3a | Core 3 | "Exactly four writes" | Exactly four distinct POST actions under the write prefix (`/do/`), covering all four families the contract names. Every other POST fails until declared with `--changes-nothing` — see above. |
| 3b | Core 3 | "Each is an operation the manager session can perform the same way" | The surface must state the mapping in its own words, behind its Details fold: `<write> → <where it lands> — manager operation <op>`, four of them, and every write route found must be one of them. No longer a SKIP: the app publishes this. |
| 4 | Core 4 | "No data of its own. … No second copy of the truth." | Every page must **say**, in the app's own words, that it keeps no data of its own — and every document page must **name the project file it is a view of**, so the claim is checkable on the page rather than taken on trust. What a static read cannot do is prove no private store sits behind the page; the row's detail says so rather than implying more than was checked. |
| 5 | Core 5 | "Proposals look the same whoever proposed: what changes, sentence by sentence · the evidence · what does not change" | Every proposal page must lay out all three parts, **in that order**, in the surface's own words — evidence before the change asks a reader to judge a case before they know what it is. **SKIP** when no proposal is open in the target. |
| 6 | Core 6 | "What changed since you last read this … sentence by sentence" | Every document page must say what changed since you last read it, and a change list must mark removed sentences apart from added ones. **SKIP** when no document in the target has changed since it was read — nothing has been taken away to show. `render.py --exercise-what-changed` produces one. |
| 7 | Core 7 | "Locking is gated … the control is live only when all four are met" | Every lock gate must state **exactly four** conditions, each in the gate's own two words (Green / Not yet), with a control beside them whose `disabled` **agrees with them**: off unless all four are green, live when they are. An invariant, not a fixed state — all four green with the control still off fails too. |
| 8a | Core 8 | "*Kept · Not yet · Broken · Pinned open · Can't check* for contracts; *Working · Quiet · Silent* for lanes" | Every state the app shows (`.chip`, `.state`, `.mark`) must be one of the plain words. A raw token from the machinery — `held`, `CONFORMS` — is the failure. A measure may follow the word: *Quiet 14m* is still Quiet. |
| 8b | Core 8 | the same clause's other half: the vocabularies are actually **used** | At least one lane must be shown in the lane words, and at least one contract in the contract words. Showing only a document's own status (Draft / Locked) leaves a reader unable to see whether the promise is being kept. |
| 8c | Core 8 | "Technical detail waits behind a Details fold" | Scans **every page the app served** for terms a colleague who is not an engineer would have to look up — ledger, reconcile, recipe, bundle, orchestrator, YAML, stdout, frontmatter, and the rest — and reports the term, the page, and the sentence it appeared in. |
| 9a | Core 9 | "Lanes running against lanes intended, with the fill control" | The gauge must state *N of M running*, and the fill control must be present **exactly when** the lanes are short. Offering to fill lanes that are all running fails as loudly as offering nothing when they are not. The control must post to a write route. |
| 9b | Core 9 | "The whole operation in view" | Eight things on one page: lanes running against intended, truly ready against waiting on you, the plan in order with reasons, each lane's state and evidence with a fold to drill into, your limits, the feedback drop, every manager session with "tell all" — and **no control on the board that stops anything**, because "Stopping something is never a board button." |
| 10 | Core 10 | "Renders at 390 and 1280 pixels with nothing cut off and no console errors" | **SKIP** — see *The one SKIP*. |

### The three clause-halves that had no check, and the ledger rows they answer

Three halves of surface.v1 had no assertion anywhere once the app shipped
(converge-fmz). Each now has a rule with a negative fixture:

| Ledger row | The half | The rule that answers it |
|---|---|---|
| CVG-038 | Core 9, "The whole operation in view" | **9b** — the eight things on one page, and no stop control on the board. |
| CVG-057 | Core 8, first half — the app must **speak** the plain state words | **8a** (nothing foreign is ever shown as a state) and **8b** (both vocabularies are actually used). |
| CVG-066 | Core 8, second half — no vocabulary rule ran against the shipped app | **8c** — closed by the target itself: the kit reads the app's own rendered words, on every page it serves. |

A note for whoever owns `ledger/rows.yaml`: CVG-066's `ref` today is
`grep -rl "conformance/surface" tests/`, which asks whether the app's *test
suite* mentions the kit. That is now a second-hand question — the kit reads the
app directly. `uv run conformance/surface/run.py <the app> | jq '.results[]
| select(.rule=="8c")'` answers it first-hand, and CVG-038 and CVG-057 have the
same shape with rules 9b and 8a/8b.

8b **used to FAIL** against the app: Direction chipped every promise `Draft`,
its own status, and never said whether it was Kept. That was a true finding,
filed as converge-6s8 and since closed — measured 2026-09-03 against the running
app, 8b PASSes (contracts shown as `['Not yet']`, lanes as `['Working']`).

### Rule 8c scans the app's own words, and says so

Three spans of text are deliberately **out of scope**, and each has its own
test, because each is a place a careless scanner would invent a finding:

- **Text inside a `<details>` fold** — that is precisely where the contract
  says technical detail belongs.
- **A rendered project document** (`.doc` / `.docpane`) — a contract's own
  prose is that *document's* responsibility, checked by the `documents.v1`
  kit. Scanning it here would report a contract's vocabulary as an app defect.
- **Words quoted from the project** (`.doc.quote`) — the app marks borrowed
  words as borrowed. A lane that described itself as "reconciling the ledger"
  is that lane's wording, not the app's.

The scanner also skips a term inside a longer hyphenated token:
`amplifier-bundle-converge` in a header chip is a project's **name**, not the
word "bundle" used as jargon. A trailing full stop does **not** earn that
exemption — "filed against the ledger." is jargon, plainly, and is reported.

### One caller outside this directory reads a rule id

`tests/test_plain_words_on_the_surface.py` holds this kit and asks it for the
**vocabulary** rule's verdict on each page the app serves. It selects that rule
by id:

```python
rule = next(r for r in report["results"] if r["rule"] == "5")   # line 427
```

The 2026-09-03 renumbering moved that row from `5` to **`8c`** (rule `5` is now
Core 5, proposals). Measured after the renumbering: that one test fails with
`- PASS / + SKIP`, because rule 5 SKIPs on a single page with no proposal on it.
The fix is one line — `== "8c"` — in a file this kit's lane does not own, and it
is filed rather than made here. Nothing else in the repository selects a kit
rule by id except `ledger/rows.yaml`, whose stale refs `ledger/checks/verify.py`
names for you.

### The one SKIP, and why it is not two

Rule 10 needs a real browser at two widths with a console, and this kit launches
none. Its reason names `converge-ium`, the work that closes it. The app covers
the same promise structurally against its stylesheet in
`tests/test_renders_at_both_widths.py`; what remains genuinely unchecked is a
live render.

Rule 3b used to SKIP too, with the reason *"the app is not built yet
(converge-2qh)"*. The app ships in `src/amplifier_converge/`, so that reason
was false; the mapping it wanted is published on the Operation page and is now
checked. `test_no_skip_still_claims_the_app_is_unbuilt` makes sure neither that
reason nor any like it comes back.

Three further rows SKIP **conditionally**, and only when the target genuinely
cannot show them: 1a on a single page, 6 when nothing has changed since it was
read, and 5 when no proposal is open in the target. Each reason says how to
produce a target that can.

## Fixtures (the kit's own proof)

Both fixtures are **page sets** — several pages and a `pages.json`, the shape
`render.py` writes — because the app is several pages and rules like 1a and 3a
only mean something across them.

- `fixtures/sample-good/` — a **conforming** surface: three places that
  resolve, a list whose stated length matches its cards, a gauge short by one
  with the fill control beside it, a four-condition lock with the control off,
  a change list carrying removals, four writes each mapped to an operation,
  a proposal laid out in its three parts in order, every page saying it keeps
  no data of its own, both state vocabularies spoken, and the whole operation
  on one page. The kit reports **PASS** on all fourteen checkable rules. It
  carries no `<script>`, on purpose — a kit that needed handlers would fail the
  app for keeping its promises a different way.
- `fixtures/sample-bad/` — the same promises as markup with nothing behind
  them: a place pointing at `/nowhere` (1a), a badge saying four over two cards
  and a card with no way to answer (1b), an answer landing in "the session log"
  (2), a fifth write (3a), a fold naming three writes (3b), a proposal page that
  never says the surface keeps no data of its own and a document page naming no
  project file (4), a proposal with its evidence before its change and no "what
  does not change" at all (5), a change list that never says what was taken away
  (6), a three-condition lock with a live control (7), a lane whose state is
  `held` (8a), promises chipped only Draft and no lane words anywhere (8b), the
  ledger and a GAP row in the card copy (8c), a gauge short by four with no fill
  control (9a), and a board with no limits, no manager sessions, and a **Stop
  this lane** button (9b).

Each fixture opens with a comment naming the rules it demonstrates and why, so
it reads as a worked example of the contract rather than a puzzle.

## Self-test

```sh
uv run --with pytest pytest conformance/surface/tests/ -q
```

`test_every_rule_has_a_negative_fixture` is the load-bearing one: every rule
the kit emits must either FAIL on `sample-bad` or be a declared SKIP with a
reason. A rule nobody can make fail proves nothing.

`test_every_core_clause_has_a_row` is the one the Core-clause anchor buys: every
numbered clause under `## Core (the teeth)` in `contracts/surface.v1.md` must
have at least one rule row, so a clause added later cannot go unchecked without
this test going red. Under the bullet anchor there was no row to be missing.

Three others are worth knowing about:

- `test_no_skip_still_claims_the_app_is_unbuilt` — the stale reason that made
  converge-e59 necessary can never return.
- `test_an_undeclared_post_is_a_fifth_write_until_someone_says_otherwise` — the
  `--changes-nothing` escape hatch is not a hole: undeclared, it fails.
- `test_a_page_with_no_script_can_still_pass` — the shape mismatch that made
  the app fail seven rules is now a test.
