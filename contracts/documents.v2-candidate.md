# Documents Contract — v2 candidate (proposal)

**Who builds against this:** the intent steward, who decides; everyone who
writes or reads a contract under Converge; and the three conformance kits,
whose rule tables are numbered by clause 5 and whose findings change if the
steward rules one way rather than the other.

Three sentences of `documents.v1` do not settle a question a reader keeps
having to re-derive. Each was surfaced by the documents kit, which reported the
fact and refused to invent the ruling. `documents.v1` stays the law until the
steward answers: *ratified* · *ratified with edits* · *declined* · *later*.

## The exact change

**1. Clause 4 — say whether a contract may carry an extra section.**

Today clause 4 reads:

> 4. **The same sections, in the same order, every time.** Purpose → Core (the
>    teeth) → What v1 deliberately does NOT freeze (with promotion triggers) →
>    Conformance kit asserts → Reserved / open questions → Changelog only if
>    amended.

Add one sentence to the end of that clause:

> A contract may carry an additional section of its own, provided it neither
> displaces nor reorders the ones above.

**2. Clause 5 — name which numbering the rule table follows.**

Today clause 5's last sentence reads:

> Numbers match the conformance kit's rule table.

Replace that sentence with:

> The kit's rule table is numbered to these Core clause numbers, so a failing
> rule names the clause it breaks.

**3. Conformance kit asserts — add the two clauses the list omits.**

The *Conformance kit asserts* section carries seven bullets for thirteen Core
clauses, and Core 10 and Core 11 appear in none of them. Add two bullets, after
"Every work item names a contract and quotes its source":

> - No document uses a machine state token where a plain state word belongs.
> - No contract carries technical detail among its deciding sentences.

## The evidence

**Clause 4 — a cost paid twice.** `contracts/operation.v1.md` carries a seventh
section, "Declared dependencies (checked at install)". Building the documents
kit, one session had to stop and work out whether that was a violation; seeding
the ledger, another session had to work out the same thing again and file it a
second time. The clause fixes presence and order and is silent on the set, so
rule 4 asserts only presence and order and reports the extra section in its
detail — the kit refusing to rule on the steward's behalf. Reading the clause as
forbidding an extra section would additionally require an edit to a contract
with no reported defect: no reader has reported being misled by
`operation.v1`'s extra section. Permitting it costs nothing observed; forbidding
it costs an edit to close a question no reader has raised.

**Clause 5 — a failure caught.** The three kits are numbered to the contract's
*Conformance kit asserts* bullets, not to its Core clauses. That numbering hid a
real gap: the bullet list has seven bullets for thirteen clauses, so Core 10 and
Core 11 had **no bullet, therefore no row, and therefore nothing missing to
see**. The absence was invisible until the ledger was seeded by hand and the
clauses were read one by one. The documents kit is now numbered to the Core
clauses, and a test fails if any clause has no row — a check that is only
possible once the numbers are anchored to the clauses. A failing rule now also
names the clause it breaks, which the bullet numbering could not do.

**Bullets for Core 10 and 11 — the same failure, at its source.** The kit can
now check both clauses mechanically, and does. The contract's own list of what
the kit asserts should say so, or the next reader will conclude — as three
readers already have — that the clauses are unchecked.

## What does not change

- **No clause changes its meaning.** Clause 4 still fixes the six sections and
  their order; clause 5 still requires the bold-led rule as fact; the Core
  clauses keep their numbers, and nothing is renumbered.
- **No contract is edited by this proposal.** `documents.v1` stays the law, and
  `operation.v1.md` keeps its seventh section, until the steward answers.
- **The kits' behaviour today.** The documents kit already reports both facts
  and rules on neither: rule 4 reports an extra section without failing it, and
  rule 5b reports the numbering divergence and stays a SKIP with its reason. If
  change 2 is ratified, the `composition` and `surface` kits renumber to their
  contracts' Core clauses; that is work to be filed, not work this proposal
  performs.
- **What the kit cannot check stays honest.** Rules 1, 7c and 10b still report
  SKIP with a reason. A ratified sentence does not make a judgment mechanical.
