# Conformance kits

Three runnable kits, one per contract. Each is the **executable version of the
promises its contract makes** — point it at a target and it reports, rule by
rule, whether they are kept. Which sentences a kit numbers its rules to
differs by kit today; see *Numbering follows the contract* below.

| Kit | Contract | Target | What it judges |
|---|---|---|---|
| [`composition/`](composition/) | [`composition.v1`](../contracts/composition.v1.md) | a repository root | Does this repository sit lightly on its host, and does its guard protect a locked contract? |
| [`documents/`](documents/) | [`documents.v1`](../contracts/documents.v1.md) | a repository root | Do this repository's contracts, vision, proposals, and participant kit keep their shape? |
| [`surface/`](surface/) | [`surface.v1`](../contracts/surface.v1.md) | the companion page | Are the promised interactions present and wired to one another? |

There is no `operation/` kit here. That contract's promises are about a running
system, and closing them needs the turnkey harness (`converge-qtp`), not a file
scan.

## Run them

```sh
uv run conformance/composition/run.py .
uv run conformance/documents/run.py .
uv run conformance/surface/run.py <path-to-index.html>
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

## Numbering follows the contract — to one of two anchors

Every rule row is numbered to a sentence in its contract, so a reader can go
from a failed rule straight to the promise it operationalizes. Where one
sentence carries several independent promises, the kit emits one row per
promise, lettered inside it (`1a`, `1b`, …) — a failure names the exact
promise rather than a whole paragraph. Each kit's README carries the full
table with the contract sentence quoted beside each row.

**Two kits anchor to the *Conformance kit asserts* bullets; one anchors to the
Core clauses.** That is the current state, measured, not an aspiration:

| Kit | Core clauses | *Conformance kit asserts* bullets | Rule ids | Anchored to |
|---|---|---|---|---|
| `composition/` | 1–7 | 1–4 | 1–4 | the bullets |
| `documents/` | 1–13 | 1–7 | 1–13 | the **Core clauses** |
| `surface/` | 1–10 | 1–5 | 1–5 | the bullets |

The documents kit moved because the bullet anchor **hid a real gap**. A
contract's bullet list is shorter than its Core clause list, so a clause with
no bullet gets no row — and a missing row is invisible: nothing looks wrong.
`documents.v1` clause 10 ("Plain state words everywhere") and clause 11
("Technical detail is folded") had no bullet, therefore no row, therefore no
check, and nobody could see it. The same arithmetic still holds next door:
`composition.v1` has seven Core clauses behind four bullets, `surface.v1` ten
behind five. **Under a bullet anchor no kit can tell you whether a Core clause
went unchecked** — there is no row to be missing. Only the documents kit's
self-test carries `test_every_core_clause_has_a_row`; the other two have no
such test, because under their anchor there is nothing for it to count. That
is a fact about those kits recorded here rather than papered over; changing
them waits on the ruling below.

Which anchor `documents.v1` clause 5 ("Numbers match the conformance kit's rule
table") actually means is an open question for the steward, proposed in
[`contracts/documents.v2-candidate.md`](../contracts/documents.v2-candidate.md).
Until it is answered, the documents kit's rule 5b reports the divergence and
stays `SKIP` rather than failing another kit on an unratified reading. If the
Core-clause reading is ratified, the `composition` and `surface` tables
renumber and this section collapses to one anchor.

Check the table above at any time:

```sh
uv run conformance/documents/run.py . --json-only \
  | python3 -c "import json,sys; print(*[o for o in [r for r in json.load(sys.stdin)['results'] if r['rule']=='5b'][0]['observed']], sep='\n')"
```

## When a kit reports a finding

A `FAIL` against this repository is a **true finding**, not a bug in the kit to
be tuned away. File it; do not weaken the rule. The kits deliberately avoid
several *fabricated* findings — a template's own instruction comment, a status
quoted as an illustration, a project's name matching a jargon term, another
kit's deliberately-broken fixture — and each of those exemptions is documented
in the kit's README and covered by its own test.
