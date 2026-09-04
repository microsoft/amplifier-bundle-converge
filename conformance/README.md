# Conformance kits

Five runnable kits, one per contract that has a checkable body. Each is the
**executable version of the promises its contract makes** — point it at a target
and it reports, rule by rule, whether they are kept. All five number their rules
to their contract's Core clauses; see *Numbering follows the contract* below.

| Kit | Contract | Target | What it judges |
|---|---|---|---|
| [`composition/`](composition/) | [`composition.v1`](../contracts/composition.v1.md) | a repository root | Does this repository sit lightly on its host, and does its guard protect a locked contract? |
| [`documents/`](documents/) | [`documents.v1`](../contracts/documents.v1.md) | a repository root | Do this repository's contracts, vision, proposals, and participant kit keep their shape? |
| [`experience-direction/`](experience-direction/) | [`experience-direction.v1`](../contracts/experience-direction.v1.md) | the companion app | Can a steward read the agreement, see what moved, answer a proposal and ask for one, without leaving? |
| [`experience-operation/`](experience-operation/) | [`experience-operation.v1`](../contracts/experience-operation.v1.md) | the companion app | Does the operation show what is being pursued, how it is going, and the evidence behind the claim? |
| [`experience-console/`](experience-console/) | [`experience-console.v1`](../contracts/experience-console.v1.md) | the companion app | Is the console a pane beside the work — carrying the manager session, ratifying nothing, reaching nothing else? |

There is no `operation/` kit here. That contract's promises are about a running
system, and closing them needs the turnkey harness (`converge-qtp`), not a file
scan. There is no `experience/` or `experience-collaboration/` kit either, and no
`platform-*` kit: the umbrella's clauses are kept by the section contracts that
hang off it, collaboration's boundary is a repository-host question, and four of
the five platform bodies do not exist. `ledger/rows.yaml` says so row by row
rather than leaving the silence unexplained.

[`_superseded/`](_superseded/) holds kits whose contract has been superseded.
They are kept for the record and are **not** part of this suite —
`conformance/surface/` moved there on 2026-09-03 when `surface.v1` was
superseded by the experience family.

## Run them

```sh
uv run conformance/composition/run.py .
uv run conformance/documents/run.py .

# the three experience kits read the running app
uv run --extra app python -m app.serve --port 8788 &
export CONVERGE_APP_COOKIE="…"          # see below
uv run conformance/experience-direction/run.py http://127.0.0.1:8788
uv run conformance/experience-operation/run.py http://127.0.0.1:8788
uv run conformance/experience-console/run.py  http://127.0.0.1:8788
```

Every kit behaves the same way, on purpose:

- a **JSON report on stdout**, for a ledger or a script to read
- a **human summary on stderr**, for a person
- **exit 0** when no rule FAILs, **exit 1** when any does
- `--json-only` to suppress the summary

The three experience kits get that shape from one place —
[`kitreport.py`](kitreport.py) — so the promise cannot drift kit by kit.

The documents kit's rule 9a reads the work queue, which is not a file in this
tree — refresh its export with `uv run scripts/export-work-items.py --project
converge --out docs/work-items.json` before you trust that rule's verdict.

### Reading the app needs a cookie, and that is not an oversight

The app gates every route behind its signed session cookie and has **no loopback
exemption** (`app/auth.py`): a request from 127.0.0.1 is a request like any
other, because binding to the LAN is the point. So a live target needs a cookie
minted by the app's own signer:

```sh
export CONVERGE_APP_COOKIE="$(python3 -c "import pathlib;from itsdangerous import \
URLSafeTimedSerializer as S;print(S(pathlib.Path.home().joinpath('.amplifier',\
'converge-app.secret').read_text().strip(), salt='converge-app-session')\
.dumps({'u':'$USER'}))")"
```

Without one the kit fails loudly with that instruction rather than reporting an
empty app — a target that answers the sign-in gate is a target that was never
read, not a body with no content.

`--capture <dir>` writes every route a kit read, with a manifest naming the route
each file came from. That directory is a target in its own right, which is what
the good/bad fixtures are and how a verdict can be re-judged later.

## Three statuses, and only three

| Status | Means |
|---|---|
| `PASS` | The kit checked this and the promise is kept. |
| `FAIL` | The kit checked this and the promise is broken. The detail names the file, the route, and what it expected. |
| `SKIP` | The kit **could not check this**, and says why in a `reason` field. |

**A `SKIP` is never a soft pass.** It is the kit refusing to claim work it did
not do — a rule that needs a live session, a rendered viewport, or a named human
reader cannot be settled by reading files, and pretending otherwise is how a
green report stops meaning anything. Each kit pins its own SKIP set in its
self-test, so a rule cannot quietly drift into SKIP to dodge a failure.

## Every rule has a negative fixture

Each kit ships `fixtures/sample-good` (conforms; the kit reports PASS) and
`fixtures/sample-bad` (violates every checkable rule at once, so one run
surfaces all of them). Each kit's self-test contains
`test_every_rule_has_a_negative_fixture`, which asserts that **every rule the
kit emits either FAILs on `sample-bad` or is a declared SKIP with a reason.**

A rule nobody can make fail proves nothing. That test is what stops this
directory from becoming decoration.

The three experience kits' fixtures are **captured app snapshots** — the same
shape `--capture` writes — so a fixture is judged through exactly the code path a
live app is. They are rewritten in place by
[`experience-fixtures/make_fixtures.py`](experience-fixtures/make_fixtures.py),
which is how they are kept in step when a rule is added; it is not a build step
anyone has to run first.

```sh
uv run --with pytest pytest conformance/ -q             # every live kit
uv run --with pytest pytest conformance/documents/ -q   # one kit
python3 conformance/experience-console/tests/test_conformance.py   # no deps
```

## Numbering follows the contract — one anchor, the Core clauses

Every rule row is numbered to the **Core clause** it judges, so a failing rule
names the clause it breaks and a reader can go straight from the failure to the
promise. Where one clause carries several independent promises, the kit emits
one row per promise, lettered inside it (`1a`, `1b`, …) — a failure names the
exact promise rather than a whole paragraph. Each kit's README carries the full
table with the contract sentence quoted beside each row.

**All five kits anchor to their contract's Core clauses**, and every clause has
a row:

| Kit | Core clauses | Rule ids | Every clause has a row |
|---|---|---|---|
| `composition/` | 1–7 | 1a–7b | `test_every_core_clause_has_a_row` |
| `documents/` | 1–14 | 1–14 | `test_every_core_clause_has_a_row` |
| `experience-direction/` | 1–11 | 1–11 | `test_every_core_clause_has_a_row` |
| `experience-operation/` | 1–13 | 1–13 | `test_every_core_clause_has_a_row` |
| `experience-console/` | 1–10 | 1–10 | `test_every_core_clause_has_a_row` |

It was not always one anchor. Two kits were numbered to their contract's
*Conformance kit asserts* bullets, and that **hid a real gap**: a contract's
bullet list is shorter than its Core clause list, so a clause with no bullet got
no row — and a missing row is invisible, because nothing looks wrong.
`documents.v1` clause 10 ("Plain state words everywhere") and clause 11
("Technical detail is folded") had no bullet, therefore no row, therefore no
check, and nobody could see it. The same arithmetic held next door:
`composition.v1` has seven Core clauses behind four bullets, `surface.v1` ten
behind five — and under the bullets, `composition.v1` Core 3, 4 and 5 and
`surface.v1` Core 4 and 5 had no row at all.

The steward settled it on 2026-09-03 (see
[`docs/workflow/owner-ratifications-2026-09-03.md`](../docs/workflow/owner-ratifications-2026-09-03.md),
call 2): **conformance-kit rule ids anchor to the contract's clause numbers**,
`documents.v1` §5 as written. The three experience kits were built under that
anchor from the start, and each carries
`test_every_core_clause_has_a_row` and `test_rule_ids_match_the_readme_table`
— the second because `ledger/checks/verify.py` resolves a ledger row's
`run.py (rule N)` reference against the kit README's table, and a ref pointing
confidently at the wrong rule is worse than one that dangles.

Check a kit's alignment at any time:

```sh
uv run conformance/documents/run.py . --json-only \
  | python3 -c "import json,sys; print(*[o for o in [r for r in json.load(sys.stdin)['results'] if r['rule']=='5b'][0]['observed']], sep='\n')"
```

## When a kit reports a finding

A `FAIL` against this repository or its app is a **true finding**, not a bug in
the kit to be tuned away. File it; do not weaken the rule.

The kits deliberately avoid several *fabricated* findings, and each exemption is
documented in the kit's README and covered by its own test — a template's own
instruction comment, a status quoted as an illustration, a project's name
matching a jargon term, another kit's deliberately-broken fixture. The three
experience kits added three more, each caught while they were being built and
each now a test:

- **A write is a call, not a word in a message.** The app's per-change handler
  shows *"Restore staged for the next proposal decision."* — and `decision`
  matched the app's decision write, so the rule reported a PASS for a control
  that does nothing. String literals are blanked before a handler is read.
- **A handler is found by its selector**, `[data-restore]`, not by the same
  attribute inside a markup template, which returns a template interpolation.
- **A function is read from its definition, not its import.** `fillLanes` first
  appears in `import { … } from './actions.js'`, and reading the brace after it
  reported the fill control reaching no write when it calls `api.steer`.

## What each kit will not claim

| Kit | The line it does not cross |
|---|---|
| `composition/` | it reads a repository's files, never a live session's tool set |
| `documents/` | it reads documents, never the app's markup — rule 11b SKIPs and says where the app-side promise is judged instead |
| `experience-direction/` | it never proves what a write records once it lands, and never judges a render |
| `experience-operation/` | the same, and it reads the brief's five parts as a keyword pass over the brief's own sentences |
| `experience-console/` | it never claims a typed line **arrived** (rule 3 judges only that a path exists), and rule 4 reads the stylesheet's rules, not a viewport |
