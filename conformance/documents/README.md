# documents.v1 conformance kit

The runnable definition of **"these documents keep their shape."** Point it at a
repository root and it mechanically asserts the conformance list from
[`contracts/documents.v1.md`](../../contracts/documents.v1.md) over that
repository's contracts, its vision, any proposals beside a contract, its
participant kit, and the templates it ships for other projects to adopt. If it
says PASS, a colleague can pick up any contract there and find the same anatomy.
If it says FAIL, it names the file and the line.

Stdlib only. A document check that needed a package installed would be one more
reason not to run it.

## Run it

```sh
uv run conformance/documents/run.py <repo-root>
```

Output: a JSON report on **stdout** and a human summary on **stderr**. Exit code
is **0** when no rule FAILs, **1** when any rule FAILs. Add `--json-only` to
suppress the stderr summary.

```sh
# a conforming repository  ->  VERDICT: PASS, exit 0
uv run conformance/documents/run.py conformance/documents/fixtures/sample-good

# a broken repository      ->  VERDICT: FAIL (all eleven checkable rules), exit 1
uv run conformance/documents/run.py conformance/documents/fixtures/sample-bad

# this repository          ->  the real result, whatever it is
uv run conformance/documents/run.py .
```

## What it checks

Rows are numbered to the contract's **Conformance kit asserts** bullets. Where
one bullet carries several independent promises, the kit emits one row per
promise, lettered inside the bullet — so a failure names the exact promise
rather than a whole paragraph.

| # | The contract sentence this operationalizes | How the kit checks it |
|---|---|---|
| 1a | "Every contract: line 3 begins `**Who builds against this:**`" | Reads line 3 of every `contracts/*.md` and requires that exact prefix. |
| 1b | "the section order above" | Requires *Purpose* → *Core (the teeth)* → *What v1 deliberately does NOT freeze* → *Conformance kit asserts* → *Reserved / open questions*, each present and in that relative order. Headings are matched by prefix, so "Reserved / open questions (NOT frozen)" counts. Any **extra** section is reported in the row's detail rather than failed — the contract fixes the order, and whether extras are permitted is an open question (see below). |
| 1c | "50–100 lines" | Counts lines. One contract is about one screen; longer is two contracts wearing one filename. |
| 1d | "status only in the H1" | Requires a status parenthetical in the H1 and none anywhere else. Inline `` `code spans` `` are stripped first — clause 6 of the contract spells out `(DRAFT)` and `(FROZEN 2026-09-02)` as *examples*, and reading those as a second status would be a fabricated finding. |
| 1e | "each clause bold-led" | Every numbered clause under `## Core (the teeth)` must continue with `**`. A reader skimming only the bold text has then read the whole contract. |
| 2a | "Every vision: present tense" | Flags roadmap language — "we will build", "we plan to add", "will eventually", "in a future release", "coming soon", "on the roadmap", `TODO`, `TBD`. Deliberately narrow: a bare "will" is legitimate inside a subordinate clause ("the project as it will be when it is right"), so only unambiguous plan constructions are flagged. The rest of the tense judgment is row 2c. |
| 2b | "dated changelog present" | Requires a `## Changelog` section with at least one `- **YYYY-MM-DD` entry. |
| 2c | "Every vision: present tense" (the reading) | **SKIP** — mechanical tense detection reports false findings on legitimate subordinate clauses; judging a whole document's tense needs a reader. Row 2a checks the part that is mechanical. |
| 3 | "Every proposal named `*.vN-candidate.md` has all three parts" | For every `*.vN-candidate.md`: requires the exact change, the evidence, and what does not change — present, and **in that order**. SKIPs with a reason when the target has no proposals; "nothing to check" and "checked, and it was fine" are different facts. |
| 4 | "Every work item names a contract and quotes its source" | **SKIP** — work items live in the work-tracker queue, not in the repository; this kit reads files. |
| 5a | "A converged repository has all four participant-kit files" | Requires `AGENTS.md`, `PINS.md`, `docs/CONTRACTS-README.md`, and `.githooks/pre-push`. |
| 5b | "A converged repository has all four participant-kit files" (the source) | Requires the five files under `docs/workspace-template/` that a project copies to get that kit. |
| 6 | "Converge's own templates … pass every assertion above" | Judges `CONTRACT.md.template` and `VISION.md.template` **as the documents they produce** — the leading HTML instruction comment (which the copier is told to delete) is stripped first. Requires the template to produce line 3 and all five sections, and the vision template to produce a Changelog. |
| 7 | "A reader who is not an engineer … reports nothing they had to look up — recorded by name and date" | **SKIP** — needs a named human reader and a date. No file scan can stand in for a person reporting what they had to look up. |

### The SKIPs are honest, and pinned

Three rows (2c, 4, 7) are judgments this kit structurally cannot make. Rather
than fabricate a PASS it reports `SKIP` with the reason, and the self-test pins
the SKIP set to exactly `{2c, 4, 7}` — so a rule cannot quietly drift into SKIP
to dodge a failure. Rule 3 SKIPs *conditionally*, when a target carries no
proposals at all, and the self-test asserts that specifically: an absent
document must SKIP, never vacuously PASS.

### Two places the kit deliberately does not fabricate a finding

- **A template's own instructions.** A template opens with an HTML comment
  telling the copier to delete it. Reading line 3 of the raw file would report
  that comment as a missing who-line. Rule 6 strips it and judges what the
  template produces.
- **An illustration of a status.** `documents.v1` clause 6 quotes `(DRAFT)` and
  `(FROZEN 2026-09-02)` inside code spans, as examples of the form. Rule 1d
  strips inline code before looking for a stray status.

Both are checks the kit gets right on purpose; both are covered by a test.

### One open question this kit surfaces rather than decides

`documents.v1` clause 4 says "the same sections, in the same order, every
time," and lists six. It does not say whether a contract may carry a
**seventh**. `contracts/operation.v1.md` in this repository carries "Declared
dependencies (checked at install)". Rule 1b therefore asserts what the contract
unambiguously fixes — presence and order — and reports any extra section in its
detail, so the fact is visible without the kit inventing a ruling the contract
does not make. The question is filed for the steward rather than answered here.

## Fixtures (the kit's own proof)

- `fixtures/sample-good/` — a **conforming** miniature repository: one contract
  with the full anatomy, a vision with a dated changelog, a well-formed
  proposal beside the contract, the four participant-kit files, and the five
  workspace templates. The kit reports **PASS** on all eleven checkable rules.
- `fixtures/sample-bad/` — an **intentionally broken** repository that violates
  every checkable rule at once: no who-line (1a), sections out of order and one
  missing (1b), twenty lines (1c), a `**Status:**` field in the body (1d),
  unbolded clauses (1e), a vision written as a roadmap (2a) with no changelog
  (2b), a proposal missing two of its three parts (3), and no participant kit,
  no templates at all (5a, 5b, 6).

Each fixture file names the rule it violates and why, so the fixture reads as a
worked example of the contract rather than a puzzle.

## Self-test

```sh
uv run --with pytest pytest conformance/documents/tests/ -q
```

`test_every_rule_has_a_negative_fixture` is the load-bearing one: every rule the
kit emits must either FAIL on `sample-bad` or be a declared SKIP with a reason.
A rule nobody can make fail proves nothing.
