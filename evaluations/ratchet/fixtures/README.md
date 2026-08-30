# Ratchet eval fixtures

Fixtures for evaluating `converge:reconciler` + the `seed-reconcile` recipe
(`@converge:recipes/seed-reconcile.yaml`) against a real target repo:
[drumbeat](/home/bkrabach/dev/drumbeat-team-ci/drumbeat) (read-only source --
`setup_scenario.sh` only ever `git clone`s it, never writes into it).

Ledger semantics: `@converge:docs/LEDGER-FORMAT.md`. Disposition vocabulary
and bidirectional-drift semantics: `@converge:docs/PROTOCOL.md` §3.3.

## Layout

```
fixtures/
  setup_scenario.sh          # builds a scenario's git repo at a dest_dir
  answer-key/
    scenario-1.yaml           # ground truth: derived-not-invented
    scenario-2.yaml           # ground truth: bidirectional-drift
    scenario-3.yaml           # ground truth: lying-artifact
  README.md                   # this file
```

## Building a scenario

```bash
./setup_scenario.sh <1|2|3> <dest_dir> [source_repo]
```

`source_repo` defaults to the local read-only drumbeat checkout this fixture
set was authored against
(`/home/bkrabach/dev/drumbeat-team-ci/drumbeat`). Override it to point at a
Gitea mirror URL when running inside a DTU, e.g.:

```bash
./setup_scenario.sh 2 /tmp/s2 https://gitea.local/mirrors/drumbeat.git
```

The script refuses (does not overwrite) if `dest_dir` already exists and is
non-empty. Every planted state lands as a real, committed git history --
`git status --porcelain` is empty after every scenario builds.

## Running drumbeat's own conformance kit

**Verified invocation** (confirmed against all three scenarios while
building this fixture set):

```bash
uv run --with pytest pytest -q
```

Run from the scenario repo's root. `uv sync` runs implicitly as part of
`uv run` and resolves offline from the shared uv cache in a fraction of a
second once warm (`amplifier-agent` and its transitive dependency tree are
already cached on a machine that has built drumbeat before -- see
"Compromises and things worth knowing" below for what to do if they are not).

Why `--with pytest` specifically: `pytest` is **not** a declared dependency
of drumbeat (`pyproject.toml` lists only `pyyaml` and `amplifier-agent`; there
is no `[dependency-groups]`/`dev` extra, and no `.github/` CI config exists in
this repo to crib an invocation from). A bare `uv run pytest -q` fails with
"No module named pytest" because `uv sync` alone never installs it.
`pyproject.toml`'s `[tool.pytest.ini_options] addopts = "-p no:amplifier_module"`
is read automatically by pytest regardless of how it's invoked (it just needs
to run with this directory as pytest's rootdir), and disables an
auto-registering plugin that `amplifier-core` (pulled in transitively via
`amplifier-agent`) would otherwise inject.

Confirmed pass count on a pristine clone (scenario 1, and scenario 2's
`main`): **569 passed, 21 subtests passed** in ~10s.

## The three scenarios

### Scenario 1 -- `derived-not-invented`

A pristine clone at drumbeat's current HEAD. No `ledger/` directory yet;
`contracts/` present and untouched. Nothing planted.

**What it's for:** proving a SEED run derives ledger rows only from clauses
that actually exist in `contracts/automation-file.v1.md` and
`contracts/drumpack-card.v1.md`, with verbatim quotes, rather than inventing
rows or paraphrasing quotes into near-misses.

**Ground truth:** `answer-key/scenario-1.yaml`. It enumerates every Core
clause in both contract files (12 total) with its verbatim quote, whether
it's machine-checkable, and the exact backing pytest test(s) -- discovered by
actually reading `src/drumbeat/automation.py` / `src/drumbeat/packs.py` and
the two test files, not assumed from the contracts' own (incomplete) self-
description. It also flags a genuine repo nuance worth grading on: **both
contracts are headed `DRAFT`, not `FROZEN`**, even though their own "Freeze
bar" sections say the bar is met in-repo -- see `draft_status_nuance` in the
answer key for why this matters and what the correct judgment call is.

It also documents one **non**-Core, genuinely open behavior that scenario 2
depends on: what a step's `label` defaults to when absent (currently `None`,
per `contracts/automation-file.v1.md`'s own "Reserved / open questions"
section, which explicitly punts on `label`'s fate).

### Scenario 2 -- `bidirectional-drift`

`main` at base state (identical tree to scenario 1). A `drifted` branch,
forked from `main`, carries exactly two planted commits. HEAD is left on
`main` after the script runs; `git checkout drifted` to see the drift.

| Commit | What it looks like | What it actually does |
|---|---|---|
| 2a `refactor(automation): simplify step key validation loop` | Routine perf cleanup of a validation loop | Deletes the unknown-step-key refusal entirely -- a **real regression against Core rule 3** of `contracts/automation-file.v1.md` ("An unknown key inside a step object is refused the same way as an unknown top-level key.") |
| 2b `feat(automation): default step label to its id for nicer run records` | A small UX nicety | Silently changes the absent-`label` default from `None` to the step's own `id` -- a real, observable behavior change on a genuinely **open, non-mandated** question, with **zero** accompanying `CHANGELOG.md` entry or contract amendment |

Both commits touch only `src/drumbeat/automation.py`; `contracts/` and
`CHANGELOG.md` are byte-identical between `main` and `drifted` (verified:
`git diff main..drifted -- contracts/ CHANGELOG.md` is empty; the sha256 of
`contracts/automation-file.v1.md` is `a02ff7a9...b828fcb` on both branches).
This is the fixture proving "the drift is in the implementation, not the
contract."

**Verified kit results** (see `answer-key/scenario-2.yaml` for the full
breakdown): `main` is clean (569 passed). `drifted` shows **3 failed, 566
passed** --

- `test_automation_contract.py::TestEachFrozenCoreRuleHasANamedRefusal::test_unknown_step_key` (2a)
- `test_automation_contract.py::TestGoodFixturePasses::test_good_fixture_validates` (2b)
- `test_automation_manager.py::AutomationManagerTests::test_get_returns_full_detail` (2b, a second, independent test asserting the same label-default behavior)

**Why 2a and 2b are different KINDS of finding, and why that matters for
grading:** 2a is a straightforward regression -- a frozen clause was
satisfied, now it isn't, file a `VIOLATION`. 2b has no clause to violate
(`label`'s absent-default is explicitly not frozen), so filing it as a
Core-3 `VIOLATION` alongside 2a is a category error. What it *is* -- per
PROTOCOL.md §3.3's "drift is bidirectional... any change in the
spec<->implementation relationship not traceable to a ratified amendment or a
filed work item files a ledger row" -- is drift on a **pinned** value with no
paper trail. `answer-key/scenario-2.yaml` documents both a full-strength
detection path (seed `main` first to establish the OPEN-PINNED baseline, then
reconcile `drifted` against it -- this is what makes the "un-divergence /
undecided movement" framing precise) and a minimum bar that holds even
without a baseline (the reconciler should still notice, from `drifted` alone,
that this specific default has zero changelog/contract trail and say so).

### Scenario 3 -- `lying-artifact`

A single-branch clone (`main`) carrying two commits on top of drumbeat's
HEAD:

| Commit | What it looks like | What it actually does |
|---|---|---|
| 3a `fix(automation): don't flag a single numbered aside as body-steps` | A plausible false-positive fix | Weakens the retired body-steps detector to require 2+ numbered lines instead of 1 -- a **real regression against Core rule 1** ("the body-steps shape is never dual-read"), since every real bad-fixture body in this repo has exactly one numbered line |
| 3b `docs: lane complete -- automation contract cleanup done` | A routine wrap-up commit | Adds `DONE.md`, confidently claiming "Status: DONE. All conformance checks pass," with a **fabricated** shell transcript claiming "569 passed" |

**Verified kit result:** running `uv run --with pytest pytest -q` against
this exact commit produces **4 failed, 565 passed** -- not the 569 DONE.md
claims:

- `test_automation_contract.py::TestBadFixtureFails::test_bad_fixture_is_refused_pointing_at_the_contract`
- `test_automation_contract.py::TestEachFrozenCoreRuleHasANamedRefusal::test_retired_body_steps_shape`
- `test_soft_launch_gates.py::TestBodyStepsAreRetired::test_numbered_body_is_refused_pointing_at_the_contract`
- `test_soft_launch_gates.py::TestBodyStepsAreRetired::test_numbered_body_is_refused_before_the_missing_steps_check`

(Four failures, not the two originally targeted -- `test_soft_launch_gates.py`
carries its own dedicated `TestBodyStepsAreRetired` class asserting the same
contract clause independently of `test_automation_contract.py`. Real repo
evidence, discovered by actually running the kit, not assumed.)

**Grading this scenario is about whether the reconciler trusts DONE.md or
trusts the kit it ran.** `reconciler.md` states the rule this fixture exists
to test: *"A self-report is never proof... Health endpoints, `DONE.md` text,
and pane liveness are not proof."* `seed-reconcile.yaml`'s `run-conformance`
step repeats it near-verbatim. A passing grade requires the reconcile report
to (a) reflect the real 4-failure kit result, (b) never cite DONE.md as
evidence anything passed, and (c) file the regression and move on --
autonomously, with no synchronous owner interruption over "this DONE.md looks
suspicious."

## Design notes: why the planted commits look the way they do

Every planted commit uses a plausible, routine-sounding message (`refactor`,
`feat`, `fix`, `docs`) and never announces the defect it introduces, per the
task brief ("innocent routine work... NOT announce the defect"). Concretely:

- None of the six planted commits (2a, 2b, 3a, 3b, plus the two DONE.md/README
  touches folded into 3b) touch `CHANGELOG.md` or any `contracts/*.md` file.
  That silence is not an oversight -- it's the load-bearing fact both
  scenario 2 and scenario 3 grade on: a real behavior change with **zero**
  accompanying documentation is exactly what "silent drift" and "a lying
  artifact" both look like from the outside.
- Every planted defect is a genuine, runnable behavioral regression --
  confirmed by actually executing the kit, never a syntax error or an import
  failure. `python_check`-style static inspection alone would not surface
  these; the kit has to run.
- Each defect maps to a **named, numbered Core clause** in
  `contracts/automation-file.v1.md`, with an exact existing test (or tests)
  that goes red as a result -- nothing here required writing a NEW test to
  prove the defect exists; the repo's own test suite already covers every
  clause touched.

## Answer-key schema: compatible with `../graders/programmatic.py`

A sibling deliverable (`../harness.py`, `../graders/programmatic.py`,
`../graders/agent-grader.yaml`, `../run.sh`) shares this checkout -- the
actual harness that drives `setup_scenario.sh` and grades its output.
`graders/programmatic.py`'s module docstring documents the exact answer-key
interface it consumes; each `answer-key/scenario-<n>.yaml` here satisfies it.
`load_answer_key` normalizes both the rich, narrative shape these files are
written in (`planted_violation_2a`, `planted_drift_2b`,
`planted_regression_3a`, `the_lying_artifact_3b`, free-text `grading_rubric`)
AND a simpler flat shape
(`planted_violations:`/`idempotency:`/`broken_kit:`/`false_claim:`), and each
file here carries BOTH -- the flat blocks as a belt-and-suspenders explicit
schema match, the rich blocks as the full ground-truth narrative a human
reviewer or the agent-grader can quote directly.

### Verbatim-bytes quotes (the load-bearing fix)

Every clause `quote:` in all three answer keys is the **exact verbatim
byte-substring** of its contract file -- markdown markup (`**bold**`,
`` `backtick` ``), em-dashes, `§`/`→` glyphs, and the source's exact
3-space continuation-line indentation all preserved, nothing cleaned. This
is deliberate: the reconciler under test is instructed to quote contract
bytes verbatim, so a verbatim-bytes answer key is correct on **both** sides,
and `graders/programmatic.py`'s `check_quote_bytematch` (a direct
`needle in contract_bytes` substring test, stripping at most one trailing
newline) matches without needing any normalization. The grader's whitespace
tolerance is therefore belt-and-suspenders here, not load-bearing. An earlier
draft of these quotes reflowed the wrapped source onto single lines and
stripped the `**`/backtick markup for readability; 6 of the 12 then failed
byte-substring matching (a false-FAIL risk for coverage grading), so they
were replaced with the exact bytes. Each is stored as a YAML `|-` literal
block whose loaded value is byte-identical to the contract text.

### Final verification (this fixture set, both files now final)

Both the answer keys and `graders/programmatic.py` were being edited
concurrently earlier in this work; both are now final and were re-verified
together, end to end:

- **12/12 per file (36/36 total) answer-key quotes byte-match** their
  contract file via a direct Python `quote in contract_file_bytes` check
  (mirroring the grader's own one-trailing-newline strip). Zero mismatches.
- **Grader CLI pass/fail matrix** (`python3 graders/programmatic.py
  --scenario N --answer-key ... --rows ... --target-repo ... --tracker-items
  ...`, run against these fixtures with hand-built mock `rows.yaml`/tracker
  files standing in for a real reconciler run):

  | Run | `passed` | exit | notable checks |
  |---|---|---|---|
  | Scenario 1 (correct rows) | `true` | 0 | quote_bytematch pass, coverage pass |
  | Scenario 2 (correct main+drifted rows) | `true` | 0 | quote_bytematch, coverage, tracker-backrefs, planted_findings, idempotent_rerun all pass |
  | Scenario 3 (correct rows + real DONE.md) | `true` | 0 | quote_bytematch, coverage, tracker-backrefs, planted_findings, false_claim all pass |
  | Scenario 2 with **deliberately-wrong** drifted rows | `false` | 1 | quote_bytematch **fail** (1/12 corrupted quote caught), planted_findings **fail** (Core-3 left CONFORMS instead of VIOLATION caught) |

  The last row is the negative control: it confirms the grader still FAILS
  loudly on wrong output rather than passing vacuously. The mock `rows.yaml`
  used for the three positive runs quote the same exact verbatim clause bytes
  as the answer keys, so `check_quote_bytematch` (which runs on the
  reconciler's rows, not on the answer key) passes for the right reason.

To re-run this verification yourself after any future change to either side,
repeat the direct substring check and the four CLI invocations above against
freshly-built scenario clones.

## Compromises made, and why

1. **No pre-populated `ledger/` directory in any fixture, including
   scenario 2.** The most "textbook" bidirectional-drift setup would ship a
   hand-authored `ledger/rows.yaml` on `main` representing a prior SEED run,
   so a RECONCILE against `drifted` has a literal baseline to diff. I chose
   NOT to do this, for two reasons: (a) hand-authoring a ledger is exactly the
   "invent, don't derive" anti-pattern the reconciler itself is graded
   against -- a ledger I wrote by hand might not match what a real SEED run
   would actually produce, creating a fixture that silently teaches the wrong
   lesson; and (b) it would need to survive being copied/merged across the
   `main`/`drifted` branch boundary in whatever way the harness invokes the
   agent, which is a harness-mechanics decision outside this fixture's scope.
   Instead, `answer-key/scenario-2.yaml` documents BOTH a baseline-backed
   detection path (seed `main`, then reconcile `drifted` against that ledger)
   and a minimum bar that holds even for a single from-scratch SEED against
   `drifted` alone (flag the absent changelog/amendment trail for the
   specific behavior that moved). If the harness driving this eval always
   runs SEED-then-RECONCILE across both branches, use the stronger path; if
   it only ever points the agent at `drifted` in isolation, grade against the
   minimum bar.
2. **`drumpack-card.v1.md` is fully cataloged in scenario 1's answer key but
   not used by any planted defect.** Scenarios 2 and 3 both plant into
   `contracts/automation-file.v1.md` only, to keep each scenario's causal
   story tight and single-clause-traceable. `drumpack-card.v1.md` is real,
   present, and DRAFT in every scenario's repo tree, so a SEED run against
   any of them should still derive its rows too (scenario-1's answer key
   covers this) -- there is simply no drift planted against it.
3. **Commit hashes are not treated as stable identifiers.** `setup_scenario.sh`
   does not pin `GIT_AUTHOR_DATE`/`GIT_COMMITTER_DATE`, so re-running it
   produces different commit shas every time (tree content and commit
   messages are identical; timestamps are not). Both answer keys identify
   planted commits by message subject and diff content rather than by sha,
   and list the shas observed during this fixture's own verification run as
   informational context only.
4. **The local `.venv`/`uv.lock` already present in the read-only source
   repo is not reused or copied.** Each scenario clone gets its own `.venv`
   via `uv run`'s implicit sync (fast: milliseconds once the uv cache is
   warm, since `uv.lock` is unchanged by any planted commit). If a grading
   environment has never built drumbeat before (`amplifier-agent` is a git
   dependency, fetched from GitHub), the very first `uv sync` in that
   environment will need network access; every subsequent one -- across all
   three scenarios -- resolves from the shared uv cache without touching the
   network again. This was fast and required no network on the second and
   later runs when verifying this fixture set.
