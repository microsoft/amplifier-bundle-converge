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
Without the flag, rule 1e SKIPs and says exactly this.

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

# a broken one          -> VERDICT: FAIL (all twelve checkable rules), exit 1
uv run conformance/surface/run.py conformance/surface/fixtures/sample-bad
```

## What it checks

Rows are numbered to the contract's **Conformance kit asserts** bullets, and to
the Core clause each one operationalizes. Bullet 1 names five separate
interactions, so it gets five rows — a failure names the exact interaction
rather than the whole sentence. The last three rows are the clause-halves that
had no check at all before (converge-fmz).

| # | Clause | The promise this operationalizes | How the kit checks it, against the app |
|---|---|---|---|
| 1a | kit 1 / Core 1 | "Places switch" | Every page carries the rail; every `a.place` href must resolve to a route the app actually served; exactly one place is marked `is-on` and it is the page you are on. A place pointing at a route that does not exist is the failure this catches. **SKIP** when the target is a single page — one page cannot show switching. |
| 1b | kit 1 / Core 1 | "answering marks the card and shortens the list" | The list must say how long it is (the heading, the rail badge, or both) and **that number must equal the number of cards on it** — which is what makes answering one demonstrably shorten it in a server-rendered page. Each card must post to a write route, carry a word to press, and say where to come back to. At most five cards (Core 1). |
| 1c | kit 1 / Core 9 | "fill updates the gauge and the board" | The gauge must state *N of M running*, and the fill control must be present **exactly when** the lanes are short. Offering to fill lanes that are all running fails as loudly as offering nothing when they are not. The control must post to a write route. |
| 1d | kit 1 / Core 7 | "the lock control stays off until all four are green" | Every lock gate must state **exactly four** conditions, each in the gate's own two words (Green / Not yet), with a control beside them whose `disabled` **agrees with them**: off unless all four are green, live when they are. An invariant, not a fixed state — all four green with the control still off fails too. |
| 1e | kit 1 / Core 6 | "what-changed shows removed sentences" | Every document page must say what changed since you last read it, and a change list must mark removed sentences apart from added ones. **SKIP** when no document in the target has changed since it was read — nothing has been taken away to show. `render.py --exercise-what-changed` produces one. |
| 2 | kit 2 / Core 10 | "Renders at 390 and 1280 pixels with nothing cut off and no console errors" | **SKIP** — see *The one SKIP*. |
| 3a | kit 3 / Core 3 | "Exactly four write paths" | Exactly four distinct POST actions under the write prefix (`/do/`), covering all four families the contract names. Every other POST fails until declared with `--changes-nothing` — see above. |
| 3b | kit 3 / Core 3 | "each mapped to a named manager-session operation" | The surface must state the mapping in its own words, behind its Details fold: `<write> → <where it lands> — manager operation <op>`, four of them, and every write route found must be one of them. No longer a SKIP: the app publishes this. |
| 4 | kit 4 / Core 2 | "Every answer lands in the dated ratification record" | The surface's own statement of where an answer lands must name the **ratification record** and must be **dated**; and every form that answers must name what it answers, so the record can say. An answer landing in "the session log" fails. |
| 5 | kit 5 / Core 8b | "No internal vocabulary outside Details folds" | Scans **every page the app served** for terms a colleague who is not an engineer would have to look up — ledger, reconcile, recipe, bundle, orchestrator, YAML, stdout, frontmatter, and the rest — and reports the term, the page, and the sentence it appeared in. |
| 8a | Core 8a | "*Kept · Not yet · Broken · Pinned open · Can't check* for contracts; *Working · Quiet · Silent* for lanes" | Every state the app shows (`.chip`, `.state`, `.mark`) must be one of the plain words. A raw token from the machinery — `held`, `CONFORMS` — is the failure. A measure may follow the word: *Quiet 14m* is still Quiet. |
| 8b | Core 8a | the same clause's other half: the vocabularies are actually **used** | At least one lane must be shown in the lane words, and at least one contract in the contract words. Showing only a document's own status (Draft / Locked) leaves a reader unable to see whether the promise is being kept. |
| 9 | Core 9 | "The whole operation in view" | Eight things on one page: lanes running against intended, truly ready against waiting on you, the plan in order with reasons, each lane's state and evidence with a fold to drill into, your limits, the feedback drop, every manager session with "tell all" — and **no control on the board that stops anything**, because "Stopping something is never a board button." |

### The three clause-halves that had no check, and the ledger rows they answer

Three halves of surface.v1 had no assertion anywhere once the app shipped
(converge-fmz). Each now has a rule with a negative fixture:

| Ledger row | The half | The rule that answers it |
|---|---|---|
| CVG-038 | Core 9, "The whole operation in view" | **9** — the eight things on one page, and no stop control on the board. |
| CVG-057 | Core 8, first half — the app must **speak** the plain state words | **8a** (nothing foreign is ever shown as a state) and **8b** (both vocabularies are actually used). |
| CVG-066 | Core 8, second half — no rule-5 equivalent ran against the shipped app | **5** — closed by the target itself: the kit reads the app's own rendered words, on every page it serves. |

A note for whoever owns `ledger/rows.yaml`: CVG-066's `ref` today is
`grep -rl "conformance/surface" tests/`, which asks whether the app's *test
suite* mentions the kit. That is now a second-hand question — the kit reads the
app directly. `uv run conformance/surface/run.py <the app> | jq '.results[]
| select(.rule=="5")'` answers it first-hand, and CVG-038 and CVG-057 have the
same shape with rules 9 and 8a/8b.

**8b FAILs against the app today**, and that is the finding, not a bug in the
rule: Direction chips every promise `Draft`, its own status, and never says
whether it is Kept. Filed as converge-6s8 against
`src/amplifier_converge/reading/` and `web/pages.py`.

### Rule 5 scans the app's own words, and says so

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

### The one SKIP, and why it is not two

Rule 2 needs a real browser at two widths with a console, and this kit launches
none. Its reason names `converge-ium`, the work that closes it. The app covers
the same promise structurally against its stylesheet in
`tests/test_renders_at_both_widths.py`; what remains genuinely unchecked is a
live render.

Rule 3b used to SKIP too, with the reason *"the app is not built yet
(converge-2qh)"*. The app ships in `src/amplifier_converge/`, so that reason
was false; the mapping it wanted is published on the Operation page and is now
checked. `test_no_skip_still_claims_the_app_is_unbuilt` makes sure neither that
reason nor any like it comes back.

Two further rows SKIP **conditionally**, and only when the target genuinely
cannot show them: 1a on a single page, 1e when nothing has changed since it was
read. Both reasons say how to produce a target that can.

## Fixtures (the kit's own proof)

Both fixtures are **page sets** — several pages and a `pages.json`, the shape
`render.py` writes — because the app is several pages and rules like 1a and 3a
only mean something across them.

- `fixtures/sample-good/` — a **conforming** surface: three places that
  resolve, a list whose stated length matches its cards, a gauge short by one
  with the fill control beside it, a four-condition lock with the control off,
  a change list carrying removals, four writes each mapped to an operation,
  both state vocabularies spoken, and the whole operation on one page. The kit
  reports **PASS** on all twelve checkable rules. It carries no `<script>`, on
  purpose — a kit that needed handlers would fail the app for keeping its
  promises a different way.
- `fixtures/sample-bad/` — the same promises as markup with nothing behind
  them: a place pointing at `/nowhere` (1a), a badge saying four over two cards
  and a card with no way to answer (1b), a gauge short by four with no fill
  control (1c), a three-condition lock with a live control (1d), a change list
  that never says what was taken away (1e), a fifth write (3a), a fold naming
  three writes (3b), an answer landing in "the session log" (4), the ledger and
  a GAP row in the card copy (5), a lane whose state is `held` (8a), promises
  chipped only Draft and no lane words anywhere (8b), and a board with no
  limits, no manager sessions, and a **Stop this lane** button (9).

Each fixture opens with a comment naming the rules it demonstrates and why, so
it reads as a worked example of the contract rather than a puzzle.

## Self-test

```sh
uv run --with pytest pytest conformance/surface/tests/ -q
```

`test_every_rule_has_a_negative_fixture` is the load-bearing one: every rule
the kit emits must either FAIL on `sample-bad` or be a declared SKIP with a
reason. A rule nobody can make fail proves nothing.

Three others are worth knowing about:

- `test_no_skip_still_claims_the_app_is_unbuilt` — the stale reason that made
  converge-e59 necessary can never return.
- `test_an_undeclared_post_is_a_fifth_write_until_someone_says_otherwise` — the
  `--changes-nothing` escape hatch is not a hole: undeclared, it fails.
- `test_a_page_with_no_script_can_still_pass` — the shape mismatch that made
  the app fail seven rules is now a test.
