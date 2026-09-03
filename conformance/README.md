# Conformance kits

Three runnable kits, one per contract. Each is the **executable version of the
promises its contract makes** — point it at a target and it reports, rule by
rule, whether they are kept. All three number their rules to their contract's
Core clauses; see *Numbering follows the contract* below.

| Kit | Contract | Target | What it judges |
|---|---|---|---|
| [`composition/`](composition/) | [`composition.v1`](../contracts/composition.v1.md) | a repository root | Does this repository sit lightly on its host, and does its guard protect a locked contract? |
| [`documents/`](documents/) | [`documents.v1`](../contracts/documents.v1.md) | a repository root | Do this repository's contracts, vision, proposals, and participant kit keep their shape? |
| [`surface/`](surface/) | [`surface.v1`](../contracts/surface.v1.md) | the companion app (running, or its rendered pages) | Are the promised interactions present and wired to one another? |

There is no `operation/` kit here. That contract's promises are about a running
system, and closing them needs the turnkey harness (`converge-qtp`), not a file
scan.

## Run them

```sh
uv run conformance/composition/run.py .
uv run conformance/documents/run.py .
uv run conformance/surface/run.py <running app URL, or a page set written by conformance/surface/render.py>
```

Every kit behaves the same way, on purpose:

- a **JSON report on stdout**, for a ledger or a script to read
- a **human summary on stderr**, for a person
- **exit 0** when no rule FAILs, **exit 1** when any does
- `--json-only` to suppress the summary

## Three statuses, and only three

| Status | Means |
|---|---|
| `PASS` | The kit checked this and the promise is kept. |
| `FAIL` | The kit checked this and the promise is broken. The detail names the file, the line, and what it expected. |
| `SKIP` | The kit **could not check this**, and says why in a `reason` field. |

**A `SKIP` is never a soft pass.** It is the kit refusing to claim work it did
not do — a rule that needs a live session, a running application, or a named
human reader cannot be settled by reading files, and pretending otherwise is
how a green report stops meaning anything. Each kit pins its own SKIP set in
its self-test, so a rule cannot quietly drift into SKIP to dodge a failure.

## Every rule has a negative fixture

Each kit ships `fixtures/sample-good` (conforms; the kit reports PASS) and
`fixtures/sample-bad` (violates every checkable rule at once, so one run
surfaces all of them). Each kit's self-test contains
`test_every_rule_has_a_negative_fixture`, which asserts that **every rule the
kit emits either FAILs on `sample-bad` or is a declared SKIP with a reason.**

A rule nobody can make fail proves nothing. That test is what stops this
directory from becoming decoration.

```sh
uv run --with pytest pytest conformance/ -q          # all three kits
uv run --with pytest pytest conformance/documents/ -q # one kit
```

## Numbering follows the contract — one anchor, the Core clauses

Every rule row is numbered to the **Core clause** it judges, so a failing rule
names the clause it breaks and a reader can go straight from the failure to the
promise. Where one clause carries several independent promises, the kit emits
one row per promise, lettered inside it (`1a`, `1b`, …) — a failure names the
exact promise rather than a whole paragraph. Each kit's README carries the full
table with the contract sentence quoted beside each row.

**All three kits anchor to their contract's Core clauses**, and every clause has
a row:

| Kit | Core clauses | Rule ids | Every clause has a row |
|---|---|---|---|
| `composition/` | 1–7 | 1a–7b | `test_every_core_clause_has_a_row` |
| `documents/` | 1–13 | 1–13 | `test_every_core_clause_has_a_row` |
| `surface/` | 1–10 | 1a–10 | `test_every_core_clause_has_a_row` |

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
`documents.v1` §5 as written. The `composition` and `surface` tables were
renumbered to match, and each grew the rows its uncovered clauses needed.
`test_every_core_clause_has_a_row` — which only means anything under this anchor
— now runs in all three kits, so a clause added to a contract later cannot go
unchecked without a test going red.

Check the alignment at any time:

```sh
uv run conformance/documents/run.py . --json-only \
  | python3 -c "import json,sys; print(*[o for o in [r for r in json.load(sys.stdin)['results'] if r['rule']=='5b'][0]['observed']], sep='\n')"
```

## The 2026-09-03 renumbering, and what still points at the old ids

Two tables moved. Nothing about what a rule asserts changed — only its number.

| composition, was | now | surface, was | now |
|---|---|---|---|
| `1a` no heavy-package reference | `1a` | `1a` places switch | `1a` |
| `1c` lean base named | `1b` | `1b` answering shortens the strip | `1b` |
| `1b` no heavy helper in a step | `2a` | `4` answers land in the record | `2` |
| `1e` every step is declared | `2b` | `3a` exactly four writes | `3a` |
| `2` a session reaches both helpers | `3b` | `3b` writes map to operations | `3b` |
| `1d` no session-wide tool stripping | `6a` | `1e` what-changed shows removals | `6` |
| `3` an unrelated session keeps its tools | `6b` | `1d` the lock gate | `7` |
| `4a` guard admits both proposal names | `7a` | `5` no internal vocabulary | `8c` |
| `4b` guard knows the locked marker | `7b` | `1c` fill updates the gauge | `9a` |
| — | `3a`, `4`, `5` are **new** rows | `9` the whole operation in view | `9b` |
| | | `2` renders at two widths | `10` |
| | | — | `4`, `5` are **new** rows |

`ledger/checks/verify.py` names every ledger row still pointing at an old id.
Measured 2026-09-03, four rows need re-pointing (this lane does not own
`ledger/`):

| Row | Clause | `ref` today | should name |
|---|---|---|---|
| CVG-001 | composition Core 1 | `run.py (rules 1a, 1b, 1c)` | `rules 1a, 1b` |
| CVG-002 | composition Core 2 | `run.py (rules 1b, 1e)` | `rules 2a, 2b` |
| CVG-006 | composition Core 6 | `run.py (rule 1d)` | `rules 6a, 6b` |
| CVG-007 | composition Core 7 | `… + run.py (rules 4a, 4b)` | `rules 7a, 7b` |

**CVG-001 and CVG-002 both name `1b`, which still resolves — to a different
rule.** That is the failure mode `verify.py`'s rule-id tripwire exists for: a
ref pointing confidently at the wrong rule is worse than one that dangles.

Two further consequences, neither of them this directory's to fix:

- `tests/test_plain_words_on_the_surface.py:427` selects the surface kit's
  vocabulary rule by id (`== "5"`, now `"8c"`) — one line, and the row it wants
  is the one that moved. CVG-066's probe runs that very test, so that row goes
  green again the moment the line changes.
- `composition` Core 3, 4 and 5 and `surface` Core 4 and 5 now have kit rules
  (3a, 4, 5 and 4, 5). Their ledger rows — CVG-003/004/005, CVG-033/034 — are
  hand-written probes or point at the app's own tests; each could now name a kit
  rule instead. That is an upgrade, not a defect.

## When a kit reports a finding

A `FAIL` against this repository is a **true finding**, not a bug in the kit to
be tuned away. File it; do not weaken the rule. The kits deliberately avoid
several *fabricated* findings — a template's own instruction comment, a status
quoted as an illustration, a project's name matching a jargon term, another
kit's deliberately-broken fixture — and each of those exemptions is documented
in the kit's README and covered by its own test.
