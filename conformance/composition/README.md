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

# a broken repository      ->  VERDICT: FAIL (all seven checkable rules), exit 1
uv run conformance/composition/run.py conformance/composition/fixtures/sample-bad

# this repository          ->  the real result, whatever it is
uv run conformance/composition/run.py .
```

## What it checks

Rows are numbered to the contract's **Conformance kit asserts** bullets. Where
one bullet carries several independent promises, the kit emits one row per
promise, lettered inside the bullet — so a failure names the exact promise
rather than a whole paragraph.

| # | The contract sentence this operationalizes | How the kit checks it |
|---|---|---|
| 1a | "No reference to the heavy package in anything loaded" | Scans every file the bundle loads into a session — `bundle.md`, `behaviors/**`, `context/**` — for `@foundation:`. Reports each hit with file and line. |
| 1b | "no automated step names a heavy-package helper" | Scans every `recipes/**/*.yaml` for a `foundation:`-namespaced helper reference. A step naming one cannot run in a session assembled on the lean base. |
| 1c | "the lean base is named where Converge assembles" | Parses `bundle.md`'s frontmatter and requires an `includes:` entry pointing at `amplifier-foundation .../bundles/anchors/bundle.md`. |
| 1d | "no session-wide tool-stripping setting anywhere" | Requires no top-level `spawn:` key in `bundle.md`'s frontmatter or in any `behaviors/*.yaml`. A composed `spawn.exclude_tools` strips the named tools from every spawned helper in **every** session that composes the bundle — measured 2026-09-02, including unrelated work. |
| 1e | "no automated step names a heavy-package helper" (coverage) | Requires every file under `recipes/` to be named in `bundle.md`. An undeclared step is one nobody reviewed, and one rule 1b scans only by accident. Keeps the step surface exactly what the bundle says it is. |
| 2 | "A Converge session reaches a lean-base helper and one of Converge's own" | **SKIP** — needs a live Amplifier session; this kit reads files only. |
| 3 | "After installing Converge beside other work, a helper in an unrelated session keeps its shell, delegation, and skills tools" | **SKIP** — needs two live Amplifier sessions (Converge plus unrelated work) side by side. |
| 4a | "The guard … admits a `*.vN-candidate.md` beside it" | Reads every `hooks-candidate-guard` config in `behaviors/` and tests its `always_allow_globs` and `candidate_glob` against **both** proposal names — `contracts/CANDIDATE-retry-clause.md` and `contracts/composition.v1-candidate.md`. Both must be admitted by both lists. |
| 4b | "The guard denies a write to a locked contract" | Compiles the config's `frozen_marker_regex` and tests it against `# Composition Contract — v1 (FROZEN 2026-09-02)` — the H1-parenthetical status form `documents.v1` Core 6 fixes. A regex that misses it leaves a locked contract unguarded. |

### The two SKIPs are honest, and pinned

Rules 2 and 3 are judgments about a **running session**, not about files on
disk. This kit reads files. Rather than fabricate a PASS it reports `SKIP` with
the reason, and the self-test pins the SKIP set to exactly `{2, 3}` — so a rule
cannot quietly drift into SKIP to dodge a failure. Closing them needs a live
harness (the operation kit, `converge-qtp`), not a cleverer file scan.

### Globs are matched properly, not by `fnmatch`

Rule 4a resolves the configured globs itself: `**/` spans zero or more
directories, `*` stays inside one segment, and `[0-9]` is a real character
class. `fnmatch`'s `*` crosses `/` and would silently over-match — reporting a
guard as safe when it is not.

## Fixtures (the kit's own proof)

- `fixtures/sample-good/` — a **fully-conforming** miniature repository: the
  lean base in `includes:`, one declared automated step using `anchors:explorer`,
  no `spawn:` key, and a guard that admits both proposal names and recognizes
  an H1-parenthetical status. The kit reports **PASS** on all seven checkable
  rules.
- `fixtures/sample-bad/` — an **intentionally broken** repository that violates
  every checkable rule at once, so one run surfaces all of them instead of
  stopping at the first: an `@foundation:` reference in loaded context (1a),
  two steps naming `foundation:` helpers (1b), the heavy package instead of the
  lean base (1c), a top-level `spawn.exclude_tools` (1d), an undeclared
  `stray-step.yaml` (1e), a guard admitting only `CANDIDATE-*.md` (4a), and a
  frozen-marker regex that only recognizes an explicit `**Status:**` field (4b).

Each fixture file carries a comment naming the rule it violates and why, so the
fixture is readable as a worked example of the contract rather than a puzzle.

## Self-test

```sh
uv run --with pytest pytest conformance/composition/tests/ -q
```

`test_every_rule_has_a_negative_fixture` is the load-bearing one: every rule the
kit emits must either FAIL on `sample-bad` or be a declared SKIP with a reason.
A rule nobody can make fail proves nothing.
