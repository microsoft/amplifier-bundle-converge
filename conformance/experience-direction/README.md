# experience-direction.v1 conformance kit

The runnable definition of **"Direction keeps its promises."** Point it at the
companion app — the running server, or a snapshot captured from it — and it
mechanically asserts
[`contracts/experience-direction.v1.md`](../../contracts/experience-direction.v1.md)
against what the app actually serves.

Stdlib only, and **no browser is launched**.

## The target is the app, and the app is not a page

`conformance/_superseded/surface/` judged a set of server-rendered HTML pages.
The app that shipped is a different shape: `/` serves one shell, and everything
a steward reads arrives as JSON from `/api/…` and is rendered by the scripts
under `/static/js/`. A kit that only read `/` would see an empty shell and
report a body with no content — the same false FAIL that made converge-e59
necessary.

So a target here is four kinds of thing, and every rule says which it read:

| Kind | What it is |
|---|---|
| `html` | the served shell — the DOM every view renders into |
| `json` | the API payloads — the real project data, no fixtures |
| `js` / `css` | the client the app serves — what it does with that data |
| `openapi` | the app's **own** route table, from `/openapi.json` |

`openapi` carries more weight than it looks. "Which writes exist" is settled
from the app's own machine-readable statement rather than guessed from markup,
so a rule can say *no route can carry this action* and mean it.

## Run it

```sh
# the app, reading your project
uv run --extra app python -m app.serve --port 8788

# a cookie, from the app's own signer — there is NO loopback exemption
export CONVERGE_APP_COOKIE="$(python3 -c "import pathlib;from itsdangerous import \
URLSafeTimedSerializer as S;print(S(pathlib.Path.home().joinpath('.amplifier',\
'converge-app.secret').read_text().strip(), salt='converge-app-session')\
.dumps({'u':'$USER'}))")"

uv run conformance/experience-direction/run.py http://127.0.0.1:8788
```

Output: a JSON report on **stdout**, a human summary on **stderr**, exit **0**
when no rule FAILs and **1** when any does. `--json-only` suppresses the
summary. `--capture <dir>` writes every route it read, with a manifest naming
the route each file came from; that directory is then a target in its own right.

```sh
uv run conformance/experience-direction/run.py conformance/experience-direction/fixtures/sample-good
uv run conformance/experience-direction/run.py conformance/experience-direction/fixtures/sample-bad
```

## What it checks

Rows are numbered to the contract's **Core clause** numbers — rule 7 judges
Core 7 — so a failing rule names the clause it breaks. Where one clause carries
two independent promises the kit emits one row per promise, lettered inside the
clause. **Every one of the eleven Core clauses has a row**, and
`test_every_core_clause_has_a_row` fails if one does not.

| # | Clause | The promise this operationalizes | How the kit checks it, against the app |
|---|---|---|---|
| 1 | Core 1 | "Documents are organized per repository, with an All view across them" | The manager payload must carry `repositories`, each with documents, and the shell must offer an all-repos view across them. A repository with no documents fails. |
| 2a | Core 2 | "Documents render properly, and the source is always one gesture away" | Every document payload must arrive with rendered sections **and** its source, and a control must switch between them. |
| 2b | Core 2 | the same clause's other half — what the render must carry | For each capability the clause names (markdown, tables, images, links between documents, front matter, Mermaid, DOT, embedded HTML), the kit finds documents whose **source** contains it and asserts the **render** shows it. What this target's documents do not contain is reported as *not demonstrated* — named, never passed over. |
| 3 | Core 3 | "A reader can copy, download, zoom, and choose the width" *(IDIOM)* | A control for each ability. The clause names **two** copy abilities — as rendered and as source — so the copy controls are counted, not matched by name: a single control called `copyRendered` cannot stand for both. |
| 4 | Core 4 | "Every document carries four views: Reading · Changes · Review · History" | Exactly the four view controls, no more; and Changes must be sentence by sentence — every change entry a before/now pair. |
| 5 | Core 5 | "Direct editing is offered exactly where it is legal" | An edit control **and** a write route that saves a document, with the control reaching that write. Offered nowhere is not "offered exactly where it is legal". |
| 6 | Core 6 | "Restoring from history is a real action, and it routes through a proposal when the target is locked" | The restore control's own handler must reach a write the app declares. A control that shows a message and forgets is reported as such, with the handler quoted. |
| 7 | Core 7 | "A proposal looks the same whoever proposed it" | One review path lays out what changes · why · the evidence · what does not change · the word to answer with, and offers all four answer words. Evidence before what-changes fails: it asks a reader to judge a case before they know what it is. Two review renderers fail — an origin cannot be *a fact about* a proposal if each origin has its own code. |
| 8 | Core 8 | "Accepting and reverting individual changes constructs *ratified with edits*" | The per-change controls must exist and their handler must reach a write. Whether that write folds them into the one answer is beyond a static read, and the detail says so. |
| 9 | Core 9 | "Ask is a scoped request whose output is always a proposal" | An Ask control at all three scopes **and** a write route that returns a proposal. |
| 10 | Core 10 | "Concurrent editing is met with courtesy presence and reconciliation" *(IDIOM)* | Presence shown while another person edits, and all three collision choices (Use combined · Keep mine · Review both). Where there is no editing surface at all, the row says so and names rule 5 — a derived failure, not a second one. |
| 11 | Core 11 | "The lock control is gated on the four conditions, and they are shown" | All four conditions stated in the gate's own words, with a control beside them. That the control's live/inert state tracks the conditions at runtime is beyond a static read; the row says so rather than implying more. |

## What a static read buys, and what it does not

It proves a promise is **reachable**: a document arrives rendered with its
source, four view controls exist, a required control is present at all, and —
the one that matters most — the control that triggers an action reaches a write
the app declares, rather than only showing a message.

It cannot prove what a write records once it lands, and it never judges a
rendered layout. Rules leaning on either say so in their own detail.

### A write is a call, not a word

Rule 8 reported a **fabricated PASS** during this kit's own build. The live
app's per-change handler does one thing — it shows the message *"Restore staged
for the next proposal decision."* — and the word `decision` in that sentence
matched the app's `decision` write. String literals are now blanked before a
handler is read, and `test_a_word_in_a_message_is_not_a_write` keeps it that
way.

Two more reads are narrowed for the same reason, each with its own test:

- a handler is found by its **selector** (`[data-restore]`), never by the same
  attribute inside a markup template, which returns a template interpolation;
- a render that lifts each heading into a section **title** has not dropped
  markdown. Reading headings as the markdown probe reported the app dropping
  markdown on every document — a finding that was entirely the kit's.

## Fixtures (the kit's own proof)

Both fixtures are **captured app snapshots** — a `manifest.json` naming the
route each file came from, plus the files — the same shape `--capture` writes.
So a fixture is judged through exactly the code path a live app is.

- `fixtures/sample-good/` — a body that keeps every promise: repositories with
  documents and an All view, documents rendered beside their source with a table
  and a link that survive the render, two copy controls plus download, zoom and
  width, four views with before/now changes, an edit control reaching a save
  write, restore and per-change controls reaching writes, a review laying out all
  five parts in order, Ask at three scopes, courtesy presence with all three
  collision choices, and a four-condition lock gate. **PASS on all twelve rules.**
- `fixtures/sample-bad/` — the same promises with nothing behind them: an empty
  repository and no All view, a render that drops the table, one copy control and
  no zoom, two views and changes with no before/now, no edit control and no save
  route, restore and per-change handlers that only show a message, a review with
  its evidence first and no *what does not change*, no Ask, no presence, no lock.
  **FAIL on all twelve.**

Both are rewritten in place by
[`../experience-fixtures/make_fixtures.py`](../experience-fixtures/make_fixtures.py),
which is how they are kept in step when a rule is added — not a build step
anyone has to run first.

## Self-test

```sh
uv run --with pytest pytest conformance/experience-direction/tests/ -q
python3 conformance/experience-direction/tests/test_conformance.py   # no deps
```

`test_every_rule_has_a_negative_fixture` is the load-bearing one: every rule the
kit emits must FAIL on `sample-bad` or be a declared SKIP with a reason. This kit
declares **no** SKIPs, and `test_skip_set_is_pinned` fails if one appears.

## Measured against the running app

2026-09-03, against `http://127.0.0.1:8788` reading
`vision-focused-team-ci/amplifier-bundle-converge`: **PASS 5 · FAIL 7 · SKIP 0**.
The seven are true findings against a young body — no editing, no Ask, no lock
gate, restore and per-change choices that show a message and forget, one copy
control, no zoom. Each is filed as work against `app/`; the ledger rows that
carry them are `CVG-1xx` in [`ledger/rows.yaml`](../../ledger/rows.yaml).

A FAIL here is a **true finding, not a bug in the kit to be tuned away.** File
it; do not weaken the rule.
