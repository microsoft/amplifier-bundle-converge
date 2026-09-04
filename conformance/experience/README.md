# experience.v1 conformance kit

The runnable definition of **"the umbrella keeps its own promises."** Point it
at the companion app — the running server, or a snapshot captured from it — and
it mechanically asserts
[`contracts/experience.v1.md`](../../contracts/experience.v1.md) against what
the app serves **and** against the repository the app is a body for.

Stdlib only, and **no browser is launched**.

## Why this kit exists

`experience.v1` is the family's umbrella, and most of its clauses are kept by
the section contracts hanging off it — those have their own kits, and the
umbrella's ledger rows cite them. The clauses left over are the umbrella's
**own**, and nothing asserted them. `ledger/rows.yaml` said so, row by row:
CVG-104 (Core 5), CVG-107 (Core 8), CVG-108 (Core 9), CVG-112 (Core 13) and
CVG-113 (Core 14) each named `converge-f1l` as their fix rather than leaving the
silence unexplained. This kit is that fix.

## The target is a pair, because the umbrella makes two kinds of promise

Some clauses are about the **running app**: how many writes exist, how many
things ask for your word, what the app says when it cannot do a thing. Others
are about how the family is **written**: does every behavior carry one of the
four words, is every behavior placed against the three surface classes, do the
contracts this umbrella names exist at all.

| Half | What it is | Rules that read it |
|---|---|---|
| the app | the running server, or a `--capture` directory | 1, 2, 3, 4a, 4b, 5a, 6a, 6b, 8, 12, 14 |
| the repository | where `contracts/`, `docs/workflow/` and `app/` live | 5b, 7, 9, 12, 13, 15 |

The repository half is **resolved, not passed**, so this kit keeps the one
command line every experience kit shares ([`../kitreport.py`](../kitreport.py)):

- target is a URL → the repository is the checkout this kit lives in;
- target is a captured snapshot carrying a `repo/` directory → that;
- target is a captured snapshot **without** one → every repository-reading rule
  reports SKIP naming the missing half.

That last line is the one that matters. A kit which quietly fell back to
whatever checkout it sat in would report *another* repository's contracts as
this target's verdict, and nothing would look wrong.
`test_a_missing_repository_half_skips_rather_than_guesses` holds it.

`--capture` writes the app half only; both halves of a fixture are written by
[`make_fixtures.py`](make_fixtures.py) beside this file.

## Run it

```sh
uv run --extra app python -m app.serve --port 8788

export CONVERGE_APP_COOKIE="$(python3 -c "import pathlib;from itsdangerous import \
URLSafeTimedSerializer as S;print(S(pathlib.Path.home().joinpath('.amplifier',\
'converge-app.secret').read_text().strip(), salt='converge-app-session')\
.dumps({'u':'$USER'}))")"

uv run conformance/experience/run.py http://127.0.0.1:8788
uv run conformance/experience/run.py conformance/experience/fixtures/sample-good
uv run conformance/experience/run.py conformance/experience/fixtures/sample-bad
```

Output: a JSON report on **stdout**, a human summary on **stderr**, exit **0**
when no rule FAILs and **1** when any does. `--json-only` suppresses the
summary.

## What it checks

Rows are numbered to the contract's **Core clause** numbers — rule 8 judges
Core 8 — so a failing rule names the clause it breaks. Where one clause carries
two independent promises the kit emits one row per promise, lettered inside the
clause. **Every one of the fifteen Core clauses has a row**, and
`test_every_core_clause_has_a_row` fails if one does not.

| # | Clause | The promise this operationalizes | How the kit checks it |
|---|---|---|---|
| 1 | Core 1 | "Home is the list of manager sessions you run, sorted by which one needs you" | The home renderer must sort by need and each card must carry the four facts the clause names: how many things want your word, lanes running against lanes intended, the last brief line, quiet or silent. |
| 2 | Core 2 | "Two places, and only two" | The workspace switch must offer Direction and Operation and nothing else. A third tab is a third place — and conversation is a modality, not a place. |
| 3 | Core 3 | "The Manager Console is a pane, never a third place" | The console must exist, must not be offered in the workspace switch, and must sit **outside** either view — a console inside a view is torn down by the switch it is supposed to survive. |
| 4a | Core 4 | "Exactly five writes" — that all five exist | Each of answer with a word · raise or lower a priority · drop feedback · steer · ask for a proposal must be a route the app declares in its own `/openapi.json`. |
| 4b | Core 4 | the same clause's other half — "nothing else writes anything" | Every POST route must be one of the five or a **contract-named exemption**: the sign-in gate (`app/auth.py`), and the console's message path (`experience-console.v1` Core 3 and 8 — what you type there is a message, and the console never ratifies). Anything else is named. |
| 5a | Core 5 | "At most five things ask for your word at once" | Counted from `/api/needs/{mid}`, the app's own answer to that question. |
| 5b | Core 5 | "every answer lands in a dated ratification record" | The repository must hold `docs/workflow/owner-ratifications-<date>.md`, **and** the app's own write path must name it. A record nothing writes to is not where answers land. |
| 6a | Core 6 | "Plain state words everywhere" — what the app **serves** | Every state word in the payloads (a manager's state, a document's standing, a lane's state, a wave's phase) must be one of the three vocabularies the clause fixes. |
| 6b | Core 6 | the same clause on the surface — no machine vocabulary outside a fold | The shell and the client are scanned with `<details>…</details>` blanked first. The clause does not ask for silence; it asks for the machine's words to sit behind a fold. |
| 7 | Core 7 | "The app holds no data of its own" | Every store in `app/*.py` is found and named. A store is a defect **unless** the umbrella's own Reserved section leaves that question open — which it does, for the reading cursor. The contract is the arbiter, not the kit's taste. |
| 8 | Core 8 | "Whatever you can do here, the manager session can do too" | For each write the body offers, the served surface must name the manager-session operation that does the same thing. Without it a reader cannot check the claim at all. |
| 9 | Core 9 | "Every behavior carries one of four words" | Read from the section contracts: every Core clause must carry `(REQUIRED)`, `(IDIOM)`, `(OPTIONAL)` or `(EXCLUDED)`. An untagged behavior means nothing either way. |
| 10 | Core 10 | "`IDIOM` means the behavior is required and its shape is not" | **SKIP.** See below. |
| 11 | Core 11 | "Idioms satisfy behaviors; they never subtract them" | **SKIP.** See below. |
| 12 | Core 12 | "A body may exceed in idiom, never in features" | Every write beyond the five must carry a **hand-written, re-read citation** to the clause that names it. A write with none is reported as debt — there is no third thing it can be. |
| 13 | Core 13 | "Three surface classes … every behavior placed against all three" | Each section contract must name full app · quick-access · notification. The clause exists so "nobody thought about the widget" cannot pass as a decision. |
| 14 | Core 14 | "Where a body genuinely cannot do a thing, it says so in the app" | The absences are computed — writes among the five with no route, and feedback forms the body does not **offer** — and for each, the app must say **both halves** the clause asks for: what the limit is, in one statement naming the thing and denying it, and what to do instead, within three statements of it. Silence is the only wrong answer, and half a sentence is most of the way to silence. |
| 15 | Core 15 | "This umbrella governs a family" | Every contract named in clause 15 must exist in `contracts/`. A family member named and unwritten is a promise nothing keeps. |

## What rule 14 paid to learn (converge-gl6)

Rule 14 was coarse in **both** directions, and each half was measured on this
tree on 2026-09-04.

**A sentence saying a form is not taken read as an offer of it.** The third
feedback form was detected with `\bvoice\b` against everything the app serves.
The moment the app added its own Core 14 sentence — *"A voice note is not
recorded here"* — the word appeared, the form stopped being counted absent, and
`cannot_do` went from `[priority, feedback as voice]` to `[priority]`. A body
was rewarded for **saying** it cannot do a thing by no longer being asked about
it, and nothing was left that would notice voice going missing. Every marker is
now offer-shaped — a control, a MIME filter, a recorder API — so prose about an
absence reads as prose.

**Any negation near the word counted as saying the limit.** `says_so` passed on
a negation within 220 characters of the thing. Deleting the whole limit sentence
from `app/templates/shell.html` left only the heading *"Raise or lower a
priority — not here"*, and the rule still PASSed on it. The clause asks for two
things and the rule read one, loosely. Measured before and after, on the same
captured snapshot with that sentence removed:

```
BEFORE  PASS  this body cannot do ['raise or lower a priority (`priority`)'],
              and says so in the app for each
AFTER   FAIL  this body cannot do ['raise or lower a priority (`priority`)',
              'feedback as voice'], and says nothing anywhere about
              ['raise or lower a priority (`priority`)'] — not what the limit
              is, and not what to do instead.
```

Markup is now a delimiter, never content — a `<strong>` heading and the `<span>`
beneath it are two statements, and a tag's own attributes are not something the
app *said*. That second point was itself measured while fixing this: a raw
character window let `<aside aria-label="Manager Console">` stand in as "what to
do instead" for a body that had said nothing of the kind.

Three tests hold this: `test_a_sentence_saying_a_form_is_absent_is_not_an_offer_of_it`,
`test_a_heading_that_says_not_here_is_only_half_the_clause`, and
`test_the_measured_regression_runs_through_the_whole_kit`, which withdraws the
good fixture's voice control and walks silence → limit-only → both halves
through the whole kit.

## The two rules that SKIP, and why

A `SKIP` is never a soft pass. It is the kit refusing to claim work it did not
do, and each reason names what would have to exist for the rule to become
checkable.

- **Core 10** asks that review question *"is the behavior satisfied?"* rather
  than *"does it look the same?"*. That is a fact about how a **person** read
  the work, and no artifact records it. It becomes checkable the day a review
  leaves a record naming the behavior it judged.
- **Core 11**'s subtraction and transfer tests compare **two bodies** — whether
  a shape removed a state or a refusal reason, and whether the person was
  surprised or merely found it elsewhere. This family has one body, so there is
  nothing to compare against; and transfer needs a person who learned the
  behavior in the other one.

`test_skip_set_is_pinned` fails if any other rule drifts into SKIP.

## What a static read buys, and what it does not

It proves a promise is **reachable and declared**: that a write exists in the
app's own route table, that a card carries a fact, that a contract tags a
behavior, that a limit is stated somewhere. It cannot prove what a write records
once it lands, and it never judges a rendered layout. Rules leaning on either
say so in their own detail.

### A keyword is not a citation

Rule 12 reported a **fabricated PASS** during this kit's build. It linked a
route to a contract clause by searching for the route's own word, and every link
it produced was wrong:

| route | "citation" it produced | what that clause actually says |
|---|---|---|
| `…/changes/{id}/keep` | collaboration Core 2 | "…**keeps** a teammate on plain tooling a first-class participant" |
| `…/docs/{…}/read` | collaboration Core 2 | "…the seam something a person can **read**" |
| `…/ask` | collaboration Core 4 | "A question **asked** in Converge arrives as a comment" |

A contract names behaviors in prose; it does not name routes. The kit now
carries a small hand-written table, and **re-reads every citation against the
repository on every run** — a clause that moved or was reworded makes the
citation stale, and the write falls back to being reported as debt.
`test_a_keyword_is_not_a_citation` and
`test_every_citation_still_reads_true_in_this_repository` hold both halves.

### A comparator's own parentheses are not the end of the sort

Rule 1 reported the live app as unsorted. The app sorts with
`.sort((a, b) => b.needs - a.needs || …)`, and the probe `\.sort\([^)]*needs`
stops at the **comparator's** closing parenthesis — it never reaches `needs` at
all. A fixed window is read instead, and
`test_a_sort_comparators_own_parentheses_do_not_hide_the_sort` keeps it that way.

### A payload is not a surface

Rule 6b reads what the app **writes down**; a word rendered out of a payload is
rule 6a's to judge. Reading payloads in 6b would report one defect twice and
name the wrong fix — the repair for `phase: "DONE"` is in the payload, not in
the markup. `test_a_payload_is_not_a_surface` holds the line.

## Fixtures (the kit's own proof)

Both fixtures are a **pair**: a captured app snapshot — a `manifest.json` naming
the route each file came from, plus the files, the same shape `--capture` writes
— and a `repo/` half carrying the contracts, the ratification record and the app
source the umbrella's own clauses are about.

- `fixtures/sample-good/` — a body that keeps every promise: home sorted by need
  with all four facts, two places and a console beside them, exactly the five
  writes, three things asking for a word, a dated ratification record the write
  path names, plain state words and machine words behind a fold, no store of its
  own, a published manager-session operation for every write, and a family whose
  contracts are all written, all tagged and all placed. **PASS on all sixteen
  checkable rules.**
- `fixtures/sample-bad/` — the same promises with nothing behind them: an
  unsorted home, a Console tab and a console nested inside a view, two writes
  missing and one no contract names, seven things asking at once, no ratification
  record, `RESOLVED` and `DEAD` on the surface, a database of its own, no
  operation mapping, and a family untagged, unplaced and half unwritten.
  **FAIL on all sixteen.**

Both are rewritten in place by [`make_fixtures.py`](make_fixtures.py) — how they
are kept in step when a rule is added, not a build step anyone has to run first.

## Self-test

```sh
uv run --with pytest pytest conformance/experience/tests/ -q
python3 conformance/experience/tests/test_conformance.py   # no deps
```

`test_every_rule_has_a_negative_fixture` is the load-bearing one: every rule the
kit emits must FAIL on `sample-bad` or be a declared SKIP with a reason.

## Measured against the running app

2026-09-04, against `http://127.0.0.1:8823` reading
`vision-focused-team-ci/amplifier-bundle-converge`: **PASS 8 · FAIL 8 · SKIP 2**.

The eight failures are true findings against a young body and a young family —
no priority write and four writes beyond the five (Core 4), a wave's phase
served as `DONE` (Core 6), no manager-session operation published anywhere
(Core 8), two section contracts tagging no behavior (Core 9), no contract
placing a behavior against the three surface classes (Core 13), two limits the
app never states (Core 14), and two contracts the umbrella names that do not
exist (Core 15).

A FAIL here is a **true finding, not a bug in the kit to be tuned away.** File
it; do not weaken the rule.
