# Conformance kits

Three runnable kits, one per contract. Each is the **executable version of its
contract's "Conformance kit asserts" section** — point it at a target and it
reports, rule by rule, whether the promises are kept.

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

## Numbering follows the contract

Every rule row is numbered to its contract's **Conformance kit asserts** bullet.
Where one bullet carries several independent promises, the kit emits one row per
promise, lettered inside the bullet (`1a`, `1b`, …) — so a failure names the
exact promise rather than a whole paragraph, and a reader can go from a failed
rule straight to the sentence it operationalizes. Each kit's README carries the
full table with the contract sentence quoted beside each row.

## When a kit reports a finding

A `FAIL` against this repository is a **true finding**, not a bug in the kit to
be tuned away. File it; do not weaken the rule. The kits deliberately avoid
several *fabricated* findings — a template's own instruction comment, a status
quoted as an illustration, a project's name matching a jargon term, another
kit's deliberately-broken fixture — and each of those exemptions is documented
in the kit's README and covered by its own test.
