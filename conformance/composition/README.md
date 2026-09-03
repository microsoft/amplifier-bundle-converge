# composition.v1 conformance kit

The runnable definition of **"this repository composes leanly."** Point it at a
repository root and it mechanically asserts the conformance list from
[`contracts/composition.v1.md`](../../contracts/composition.v1.md). If it says
PASS, the repository sits on the lean base, its automated steps reach only
lean-base helpers, it sets no session-wide policy that would touch other work,
and its guard admits a proposal beside a locked contract. If it says FAIL, it
names the rule, the file, and the line.

## Run it

```sh
uv run conformance/composition/run.py <repo-root>
```

Output: a JSON report on **stdout** and a human summary on **stderr**. Exit code
is **0** when no rule FAILs, **1** when any rule FAILs. Add `--json-only` to
suppress the stderr summary.

```sh
# a conforming repository  ->  VERDICT: PASS, exit 0
uv run conformance/composition/run.py conformance/composition/fixtures/sample-good

# a broken repository      ->  VERDICT: FAIL (all ten checkable rules), exit 1
uv run conformance/composition/run.py conformance/composition/fixtures/sample-bad

# this repository          ->  the real result, whatever it is
uv run conformance/composition/run.py .
```

## What it checks

Rows are numbered to the contract's **Core clause** numbers — rule 6a judges
Core 6 — so a failing rule names the clause it breaks. Where one clause carries
several independent promises, the kit emits one row per promise, lettered
inside the clause (`1a`, `1b`, …) so a failure names the exact promise rather
than a whole paragraph. **Every one of the seven Core clauses has a row**, and
`test_every_core_clause_has_a_row` fails if one does not.

The kit was numbered to the *Conformance kit asserts* bullets until 2026-09-03,
when the steward ratified the Core-clause anchor
([`docs/workflow/owner-ratifications-2026-09-03.md`](../../docs/workflow/owner-ratifications-2026-09-03.md),
call 2). Under the bullet anchor, four bullets covered seven clauses and Core 3,
4 and 5 had **no row at all** — and a missing row is invisible, because nothing
looks wrong. Rules 4 and 5 below are those rows.

| # | Clause | The contract sentence this operationalizes | How the kit checks it |
|---|---|---|---|
| 1a | Core 1 | "The full foundation package appears nowhere" | Scans every file the bundle loads into a session — `bundle.md`, `behaviors/**`, `context/**` — for `@foundation:`. Reports each hit with file and line. |
| 1b | Core 1 | "Converge assembles its session from the small standard base (the *anchors* bundle …)" | Parses `bundle.md`'s frontmatter and requires an `includes:` entry pointing at `amplifier-foundation .../bundles/anchors/bundle.md`. |
| 2a | Core 2 | "Automated steps use only the lean base's helpers" | Scans every `recipes/**/*.yaml` for a `foundation:`-namespaced helper reference. A step naming one cannot run in a session assembled on the lean base. |
| 2b | Core 2 | the same clause's coverage half | Requires every file under `recipes/` to be named in `bundle.md`. An undeclared step is one nobody reviewed, and one rule 2a scans only by accident. Keeps the step surface exactly what the bundle says it is. |
| 3a | Core 3 | "Its own helpers carry a small local rulebook — stop honestly when a thing cannot be proven; sign commits; cite locations — and borrow nothing else" | Every helper under `agents/` must name a local file that states **all three** rules; that file is the rulebook. The other documents a helper names are domain reading and are not judged — reporting them would be a fabricated finding. "Borrows nothing else" is read as: no helper mentions another bundle's context, which could change under its feet. |
| 3b | Core 3 | the same clause, judged live: a session actually reaches one of Converge's own helpers | **SKIP** — needs a live Amplifier session; this kit reads files only. |
| 4 | Core 4 | "The host requirement is one sentence in the README. Steps can use only helpers present in the session they run in; Converge needs its own full setup or a host on the same lean base." | Reads `README.md`, unwraps block quotes and line wrapping, and requires **one sentence** to carry all three halves: the host, the fact that a step resolves helpers only from the session it runs in, and the lean base. Spread over three paragraphs the requirement is present and unreadable — which is the failure this catches. |
| 5 | Core 5 | "The shared work queue rides on both install paths, so the contract checker can file and read work anywhere." | Requires the work queue to be named on **both** paths: in `bundle.md`'s includes (the root install) and in a `behaviors/*.yaml`'s includes (the `--app` install target). Named on one only, filing work works after one install and silently does not after the other. |
| 6a | Core 6 | "Nothing touches the tools of other work in your session" | Requires no top-level `spawn:` key in `bundle.md`'s frontmatter or in any `behaviors/*.yaml`. A composed `spawn.exclude_tools` strips the named tools from every spawned helper in **every** session that composes the bundle — measured 2026-09-02, including unrelated work. |
| 6b | Core 6 | the same clause, judged live: "After installing Converge beside other work, a helper in an unrelated session keeps its shell, delegation, and skills tools" | **SKIP** — needs two live Amplifier sessions (Converge plus unrelated work) side by side. |
| 7a | Core 7 | "The guard recognizes both proposal names — `<contract>.vN-candidate.md` and the legacy `CANDIDATE-*.md`" | Reads every `hooks-candidate-guard` config in `behaviors/` and tests its `always_allow_globs` and `candidate_glob` against **both** proposal names — `contracts/CANDIDATE-retry-clause.md` and `contracts/composition.v1-candidate.md`. Both must be admitted by both lists. |
| 7b | Core 7 | "… and refuses every other write to a locked contract" | Compiles the config's `frozen_marker_regex` and tests it against `# Composition Contract — v1 (FROZEN 2026-09-02)` — the H1-parenthetical status form `documents.v1` Core 6 fixes. A regex that misses it leaves a locked contract unguarded. |

### The two SKIPs are honest, and pinned

Rules 3b and 6b are judgments about a **running session**, not about files on
disk. This kit reads files. Rather than fabricate a PASS it reports `SKIP` with
the reason, and the self-test pins the SKIP set to exactly `{3b, 6b}` — so a
rule cannot quietly drift into SKIP to dodge a failure. Closing them needs a
live harness (the operation kit, `converge-qtp`), not a cleverer file scan.

Both clauses that carry a live half also carry a file-readable one, and that
half is checked rather than waved at: clause 3's rulebook is rule 3a, clause 6's
absent session-wide policy is rule 6a.

### Globs are matched properly, not by `fnmatch`

Rule 7a resolves the configured globs itself: `**/` spans zero or more
directories, `*` stays inside one segment, and `[0-9]` is a real character
class. `fnmatch`'s `*` crosses `/` and would silently over-match — reporting a
guard as safe when it is not.

## Fixtures (the kit's own proof)

- `fixtures/sample-good/` — a **fully-conforming** miniature repository: the
  lean base in `includes:`, one declared automated step using `anchors:explorer`,
  a helper carrying a local rulebook that states all three rules, a README
  stating the host requirement in one sentence, the work queue named on both
  install paths, no `spawn:` key, and a guard that admits both proposal names
  and recognizes an H1-parenthetical status. The kit reports **PASS** on all ten
  checkable rules.
- `fixtures/sample-bad/` — an **intentionally broken** repository that violates
  every checkable rule at once, so one run surfaces all of them instead of
  stopping at the first: an `@foundation:` reference in loaded context (1a),
  the heavy package instead of the lean base (1b), two steps naming
  `foundation:` helpers (2a), an undeclared `stray-step.yaml` (2b), a helper
  carrying no rulebook and borrowing another bundle's preamble (3a), a README
  that never states the host requirement (4), the work queue on the root
  install path only (5), a top-level `spawn.exclude_tools` (6a), a guard
  admitting only `CANDIDATE-*.md` (7a), and a frozen-marker regex that only
  recognizes an explicit `**Status:**` field (7b).

Each fixture file carries a comment naming the rule it violates and why, so the
fixture is readable as a worked example of the contract rather than a puzzle.
`sample-bad/README.md` deliberately does **not** quote the sentence clause 4
asks for: a fixture that quoted it would satisfy the very rule it exists to
break.

## Self-test

```sh
uv run --with pytest pytest conformance/composition/tests/ -q
```

`test_every_rule_has_a_negative_fixture` is the load-bearing one: every rule the
kit emits must either FAIL on `sample-bad` or be a declared SKIP with a reason.
A rule nobody can make fail proves nothing.

`test_every_core_clause_has_a_row` is the one the Core-clause anchor buys: every
numbered clause under `## Core (the teeth)` in `contracts/composition.v1.md`
must have at least one rule row. A clause added to the contract later cannot go
unchecked without this test going red — which is precisely what the bullet
anchor could not do, because under it there was no row to be missing.
