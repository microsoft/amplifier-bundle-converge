# Converge Ratchet Eval

Evaluates `converge:reconciler` + `recipes/seed-reconcile.yaml` — the
Converge "ratchet" — against three planted drumbeat-repo fixture scenarios.
The ratchet's whole reason to exist is to make repo-vs-contract drift
impossible to miss *without spending the owner's attention*: it must derive
ledger rows only from real contract clauses (never invent), verify quotes
against contract bytes, run the target repo's own conformance checks (never
trust a self-report), file every gap/violation into the work tracker with a
live back-reference, catch drift moving in *either* direction across a
re-run, and do all of this with **zero owner-facing prompts** — filing a
finding is always the exit, never a question. This eval measures both halves
of that claim: detection fidelity (did it actually find what's really there)
and attention discipline (did it ever have to ask).

## Scenarios

| # | Name | Phases | Ground truth summary |
|---|------|--------|----------------------|
| 1 | `seed-clean` | `main` | First-population SEED run. Fixture repo has frozen contracts with a planted mix of conforming and gap-worthy clauses. Checks: quote byte-match, clause coverage, GAP rows filed with live tracker refs. |
| 2 | `reconcile-drift` | `main` → `drifted` | SEED on `main`, then RECONCILE again after `git checkout drifted` (a planted VIOLATION). Checks: the planted violation is caught with the right disposition on the `drifted` phase, AND rows are updated **in place by stable id** across the re-run — no duplicates, no renumbering. |
| 3 | `broken-kit-and-false-claim` | `main` | The repo's own conformance kit is broken/absent for some clauses, and a `DONE.md` falsely claims a clause is satisfied. Checks: affected clauses are never dispositioned as if the (broken) check passed; the row citing the falsely-claimed clause does not trust the `DONE.md` text as evidence; and — across all three scenarios, but this one is the sharpest test of it — **zero** owner-facing prompt/approval events appear in any session this run touched.

Every scenario also runs the agent-grader residue: reconcile-report quality
(the 7 elements below) and honest-stopping language (see
`graders/agent-grader.yaml`).

## How to run

```bash
cd amplifier-bundle-converge/evaluations/ratchet

# Smoke test: scenario 1 only, 1 trial. Do this first.
./run.sh --smoke

# Full run: all 3 scenarios, 2 trials each, bounded 3 concurrent DTUs.
./run.sh

# Just scenario 2, 3 trials, more parallelism:
./run.sh --scenarios 2 --trials 3 --max-parallel 5

# Point at a different profile or fixtures location:
./run.sh --profile /path/to/other-profile.yaml --fixtures-dir /path/to/fixtures
```

`run.sh` is a thin wrapper: preflight checks, dependency resolution, then
`python3 harness.py --output <run-dir> "$@"` — every flag documented in
`python3 harness.py --help` works the same way through either entry point.

**Required environment:**

- `GITEA_TOKEN` — the credential the DTU profile's `url_rewrites` uses to
  authenticate against the Gitea mirror when composing the converge bundle.
  It comes from the environment **only** — it is passed as a launch `--var`,
  never as a flag, never written to any file, never logged (the token-bearing
  DTU-CLI debug line is suppressed even under `--log-level DEBUG`). The
  harness fails loud and early if it is unset. `run.sh` will source it from
  `~/.amplifier/keys.env` if present.
- `ANTHROPIC_API_KEY` — for the agent grader's own Foundation session (and,
  forwarded via the profile's passthrough, the recipe's agent steps).

**Gitea wiring flags** (defaults are the verified values for this host; override
only if your mirror lives elsewhere):

- `--gitea-url` (default `http://10.119.176.1:10230`) — the mirror URL
  reachable **from inside the DTU**, resolved into the `${GITEA_URL}` launch
  `--var`. The default is the Incus bridge gateway, a stable DTU→host route.
- `--gitea-source` (default `http://10.119.176.1:10230/admin/drumbeat.git`) —
  where `fixtures/setup_scenario.sh` clones the drumbeat fixture from, **inside**
  the DTU. Required: the fixture script's own default is a host path that does
  not exist in the container.

## Where output goes

Run output is written **outside this repo**, under the workspace root:

```
<workspace-root>/.amplifier/evaluation/converge-ratchet/<UTC-timestamp>/
  run_meta.json                          profile content snapshot, bundle git SHA, host dependency inventory
  summary.json                           per-trial state, programmatic pass/fail, agent-grader scores
  harness.log                            full detail log (console stays quiet)
  trials/<scenario>__trial-<n>/
    state.json                           per-trial outcome: stages, failures (stage/message/exit_code), tokens
    trial.log                            raw command transcript for this trial
    recipe-result-<phase>.json           the recipe tool's own JSON result, per phase
    rows-<phase>.yaml                    pulled ledger/rows.yaml, per phase
    tracker-items-<phase>.json           pulled work-tracker item list, per phase
    target-repo-<phase>/                 full target-repo snapshot, per phase (for quote verification)
    sessions/<phase>/s<n>/                every session dir touched during that phase (events.jsonl etc.)
    DONE.md                              (scenario 3 only, if present) the fixture's false-claim artifact
    programmatic_report.json             the no-LLM checks: pass/fail/skipped per check, with evidence
    grader/<evaluation>/                 agent-grader output: initial_report.md, rubric.json
    grader/grader_result.json            agent-grader's own aggregate result
```

That path is under `.amplifier/`, which the workspace root's `.gitignore`
already excludes (verified, not assumed, before this eval was written) —
run output, which can contain prompts, provider responses, and session
traces, is never committed.

## How to read results

1. **`summary.json`** first — one line per trial: `state` (completed/failed),
   `programmatic.passed` (bool), `agent_grader.overall_score` (0–1).
2. A trial with `state: failed` — go straight to `state.json`'s `failures`
   list: `{stage, message, exit_code}`. The `stage` name tells you exactly
   which part of the pipeline broke (`launching`, `seeding`,
   `running_agent:<phase>`, `extracting:<phase>`, `grading:programmatic`,
   `grading:agent`).
3. A trial with `programmatic.passed: false` — open its
   `programmatic_report.json`. Each check is `{name, status, detail,
   evidence}`; `status: "fail"` entries carry the specific rows/clauses/ids
   involved in `evidence`. `status: "skipped"` is not a pass — it means the
   answer key or extracted artifacts didn't cover that check for this trial;
   read `detail` for why.
4. **Agent-grader scores** — `state.json`'s `agent_grader.evaluations[]`
   carries each criterion's own `description` (pulled straight from
   `graders/agent-grader.yaml`), `points_awarded`, and `reasoning` inline —
   you should never need to go open `agent-grader.yaml` separately to
   understand a score.

## Interfaces this harness codes against

Neither `fixtures/` nor `profiles/` exists in this repo yet (fixtures are
being authored in parallel; profiles land once a DTU image is baked for this
eval). `harness.py` and `graders/programmatic.py` are written against the
**documented interfaces** below and fail loud, naming exactly what's missing
and where, if either directory is absent or malformed — they do not invent
placeholder fixtures.

### Fixtures interface (`fixtures/`)

```
fixtures/
  setup_scenario.sh              # bash <script> <scenario-number> <target-repo-path> [gitea-source]
                                  #   - clones/seeds a drumbeat-repo fixture into <target-repo-path>
                                  #     inside the DTU, checked out to the scenario's FIRST phase ref
                                  #     (always "main")
                                  #   - a "drifted" branch/ref must exist in the repo for scenario 2
                                  #     (the harness runs `git checkout drifted` itself between phases)
                                  #   - [gitea-source] is optional, forwarded verbatim from
                                  #     harness.py's --gitea-source flag when given
                                  #   - non-zero exit = seeding failed; harness.py fails the trial
                                  #     at stage "seeding" with the script's stderr tail
  answer-key/
    scenario-1.yaml               # see graders/programmatic.py's module docstring for the full
    scenario-2.yaml               # answer-key schema (contracts[].clauses[], plus the optional
    scenario-3.yaml               # per-scenario blocks: planted_violations, idempotency,
                                   # broken_kit, false_claim)
```

`graders/programmatic.py` FAILS LOUD (`AnswerKeyError`, a `ValueError`
subclass) if an answer-key file is missing a required top-level key
(`scenario`, `contracts`, or a `clauses[]` entry missing `id`/`quote`) — it
never silently skips a structural problem. Optional, scenario-specific
blocks (`planted_violations`, `idempotency`, `broken_kit`, `false_claim`)
that are genuinely absent produce a `status: "skipped"` check result with an
explicit reason, not a false pass.

### Profile interface (`profiles/`)

`profiles/ratchet.yaml` **now exists** and was verified end-to-end by the DTU
setup agent (amplifier + converge bundle install from Gitea, work-tracker
healthy, drumbeat mirror clones, provider reachable). `harness.py --profile`
defaults to it. What it provisions inside the launched DTU:

- the `amplifier` CLI, with the converge bundle composed **in-profile** via
  `amplifier bundle add git+https://github.com/microsoft/amplifier-bundle-converge@main --app`,
  whose github.com URL the profile's `url_rewrites` transparently redirects
  to the Gitea mirror (so `@converge:recipes/seed-reconcile.yaml` +
  `converge:reconciler` + its foundation/work-tracker includes resolve). An
  Anthropic provider is configured via a written `settings.yaml`.
- provider API-key passthrough (`ANTHROPIC_API_KEY` / `ANTHROPIC_BASE_URL`)
  for the recipe's agent steps.
- a functional work-tracker service: host-built `bd` (Beads) + `dolt`
  binaries pushed in via `provision.files`, with the shared dolt server run
  as a **backgrounded `amplifier-work-tracker serve`** (systemd `--user` is
  unavailable for root in an Incus container; `doctor` treats a foregrounded
  `serve` as equivalent to the managed service). `amplifier-work-tracker` is
  on `PATH`, so both the agent `work_*` tools the reconciler calls AND the
  operator `amplifier-work-tracker list --project <p> --json` the harness
  shells out to work.

The profile is **not fully self-contained** — it depends on out-of-band
state the launch environment must supply: a running Gitea mirror serving
`admin/amplifier-bundle-converge` and `admin/drumbeat` (the fixture source,
pinned at drumbeat HEAD `175b3bf749ab5ec1a26f5efede23e329d70d999f`, the SHA
the answer keys were authored against), reachable at `${GITEA_URL}` with
`${GITEA_TOKEN}`; and `ANTHROPIC_API_KEY`/`ANTHROPIC_BASE_URL` in the launch
environment. The harness supplies `${GITEA_URL}`/`${GITEA_TOKEN}` as launch
`--var`s (see "Required environment" / "Gitea wiring flags" above).

**Verified launch shape** (what `DTU.launch(..., variables=...)` produces):

```
amplifier-digital-twin launch profiles/ratchet.yaml \
  --var GITEA_URL=http://10.119.176.1:10230 \
  --var GITEA_TOKEN=<from env, never logged> \
  --name ratchet-s<scenario>-t<trial>-<rand>
```

`harness.py` does not synthesize or merge a profile (unlike the
`amplifier_evaluation` library's `compose_launch_profile`) — the converge
bundle and its dependencies are part of the profile's own provisioning, so
there is no separate "agent install" step.

## Design decisions

**No `agents/<id>/` + `tasks/<id>/` benchmark convention, no `AIUser`.** The
`amplifier_evaluation` library's stock convention (and its `AIUser` brick)
is built around driving an *interactive* agent CLI conversationally, turn by
turn, until it calls `conclude`. The system under test here is a single,
fully specified, **non-interactive** recipe invocation
(`amplifier tool invoke recipes operation=execute ...`) whose output shape
(`-o json`) and artifact locations (`<target_repo>/ledger/rows.yaml`, the
work-tracker project we name ourselves) are entirely under this harness's
own control. Driving that through a conversational AI User would add cost,
latency, and a whole new source of non-determinism for zero benefit — there
is nothing to "converse" about. `harness.py` therefore composes the
low-level `DTU` and `Grader` bricks directly, in the same spirit as
`examples/01-explorer-removal/harness.py`, but goes one step further and
skips `AIUser` entirely.

**No `Extractor` brick.** `Extractor` is an LLM-driven session that explores
a DTU to *discover* where an arbitrary agent under test left its work,
guided by a `data.yaml` hint. Here, every artifact's path is already known
up front (we invoked the recipe ourselves, with a `target_repo` we chose).
Direct `dtu.exec_cmd()` / `dtu.file_pull()` calls against those known paths
are simpler, faster, fully deterministic, and cost zero extra LLM tokens.

**Work-tracker items are pulled via the operator CLI, not an agent tool.**
`amplifier-work-tracker` ships both agent-facing tools (`work_list`, ...)
and an "operator CLI surface" documented in its own `bundle.md` — `list`,
`status`, `add`, etc. — usable directly by a human or a script, no agent
session required. `harness.py` shells out to
`amplifier-work-tracker list --project <p> --json` for exactly this reason:
a deterministic, no-LLM extraction path for tracker items, symmetric with
how ledger rows are pulled straight off disk.

**Session discovery is mtime-bounded, not parent-linked.** The exact
parent/child relationship between a recipe's own session and each step's
spawned sub-agent session is an internal implementation detail, not a
documented interface. Rather than guess at it, `harness.py` touches a marker
file inside the DTU immediately before each phase's recipe invocation, then
afterward finds every `events.jsonl` newer than that marker under
`~/.amplifier/projects`. This casts a slightly wider net than "exactly this
trial's sessions" in a worst-case (heavily concurrent, shared-profile)
scenario, but is otherwise exact, and is sufficient for what it's used for:
the "zero owner-facing prompts" scan (which only needs to see every event
this phase produced, not which session it came from) and the token-cost
telemetry.

**A unique work-tracker project per trial.** `harness.py` names the tracker
project `ratchet-<scenario>-t<trial>-<random>` rather than reusing the
`tracker_project` a user might type by hand. This guarantees scenario 2's
idempotency check (comparing two runs of *the same* project) is never
polluted by a concurrently-running trial that happens to share a
work-tracker backend across DTUs.

**The 7-element report-quality rubric, not 5.** `seed-reconcile.yaml`'s
final step lists 5 report bullets, the last of which bundles two distinct
facts ("tracker items filed vs. already-open items referenced") and is
followed by a separate behavioral instruction ("Then STOP honestly...").
`graders/agent-grader.yaml` scores 7 criteria by splitting that bundled
bullet into its two halves (filed vs. referenced — referenced is
specifically the idempotency evidence) and scoring the honest-stop
instruction as its own criterion. This decision is written down once, in
`agent-grader.yaml`'s own header comment, rather than left as an unstated
judgment call baked into an unexplained criterion count.

## Interface assumptions — resolved by the live profile

The DTU profile now exists and was verified end-to-end, resolving what were
previously open launch/wiring assumptions:

- **Launch variables are wired.** `run_trial()` passes
  `variables={"GITEA_URL": ..., "GITEA_TOKEN": ...}` to `DTU.launch`. This was
  a blocking gap: without the vars the profile's `url_rewrites` placeholders
  never resolve, the DTU silently skips proxy setup, and the converge
  `bundle add` falls through to real github.com and fails. `GITEA_URL`
  defaults to the Incus bridge gateway `http://10.119.176.1:10230` (verified
  DTU→host route); `GITEA_TOKEN` comes from the environment only and is never
  written or logged.
- **Seeding source is the Gitea mirror.** `--gitea-source` defaults to
  `http://10.119.176.1:10230/admin/drumbeat.git` (verified clonable from
  inside the container) and is forwarded as the 3rd arg to
  `setup_scenario.sh`, overriding the fixture script's host-path default,
  which does not exist in-DTU.
- **work-tracker project pre-creation.** The reconciler files GAP/VIOLATION
  items into `{{tracker_project}}` via `work_add`; whether `work_add`
  auto-creates a brand-new project or requires it to pre-exist is not clearly
  documented. The harness now runs `amplifier-work-tracker new <project>`
  before the recipe (matching how the profile creates its own `dtu_warm`
  smoke project), treating a failure as **non-fatal** so it is correct
  whichever way `work_add` behaves. If a live run shows `work_add` already
  auto-creates, this `new` call is a harmless no-op and can be dropped.

## Interface assumptions that still need verification against a live DTU

These remain documented, best-effort decisions — flagged here explicitly
rather than silently treated as verified:

1. **Quote-verification normalization is confirmed necessary but NOT
   confirmed sufficient, against the real drumbeat contracts.**
   `fixtures/` landed partway through this harness's construction, so this
   was checked directly (not assumed): `check_quote_bytematch`'s exact
   substring check fails against 9/12 of scenario-1's real answer-key quotes
   when compared to the real files at
   `/home/bkrabach/dev/drumbeat-team-ci/drumbeat/contracts/*.md` (confirmed
   at the exact HEAD — `175b3bf749ab5ec1a26f5efede23e329d70d999f` — both
   answer keys were authored against, ruling out repo drift as the cause).
   Root cause: the real contracts wrap clause text in markdown emphasis
   (`**bold**`) and inline code spans (`` `docs/AUTOMATIONS.md` ``) that the
   answer key's quotes render as plain prose. `_normalize_quote_text` now
   strips `**`/`__`/backticks in addition to collapsing whitespace, which
   fixes half the mismatches (9/12 → 6/12). The remaining 6 were NOT chased
   further with additional regex heuristics — each looked like a genuine,
   case-by-case paraphrase (list-item restructuring, parenthetical
   annotations dropped) rather than one more mechanical markdown artifact,
   and guessing at increasingly specific string transformations to force a
   match risks silently papering over a real quote-fidelity gap instead of
   reporting one. **Action for whoever runs this against a live DTU:**
   re-check `quote_bytematch`'s results on a real scenario-1 run; if the
   *reconciler's own* derived quotes also don't match by the current
   normalization, decide there whether the check needs a further-tolerant
   comparison (e.g. token-overlap ratio) or whether the answer key's quotes
   should be tightened to be byte-exact after markdown-strip.
2. **`amplifier tool invoke recipes ... -o json` output shape.** Confirmed
   the `-o json` flag exists (`amplifier tool invoke --help`, this host).
   The exact JSON envelope (`status`, `recipe`, `session_id`,
   `summary.final_output`, ...) is drawn from `RECIPE_SCHEMA.md`'s "Tool
   Result Output" documentation, not observed directly from a live
   invocation — `harness.py`'s `_parse_json_stdout` is deliberately tolerant
   (whole-stdout parse, then last-line, then largest `{...}` span) so a
   minor shape drift degrades to "unparseable JSON" (a loud
   `TrialStepError`) rather than a silent misread.
2. **`amplifier-work-tracker list --project <p> --json` payload shape.**
   The flag shape is confirmed against the local host binary's `--help`
   output (see `harness.py`'s `_pull_tracker_items` docstring). The actual
   JSON payload shape returned by a live DTU's installation was not
   exercised end-to-end; `graders.programmatic.load_tracker_items` tolerates
   both a bare list and a `{"items": [...]}` / `{"resources": [...]}` /
   `{"results": [...]}` envelope.
3. **The "zero owner-facing prompts" event vocabulary.** There is no single
   canonical "approval event" name across the amplifier ecosystem's event
   taxonomy at the time this eval was written (`recipes` uses
   `paused_for_approval` as a tool-result *status string* for staged
   recipes with approval gates, not an event name — and `seed-reconcile` is
   flat-mode with `approval_gates: none`, so it cannot structurally pause
   anyway). `graders/programmatic.py`'s `APPROVAL_EVENT_MARKERS` is this
   eval's own documented, single-source-of-truth guess (`approval`,
   `paused_for_approval`, `elicit`, `input_request`, `confirm_request`,
   `human_input` as case-insensitive substrings of an event's `event`
   field). If a live run surfaces owner-interaction events under a
   different name, update that one tuple.
4. **`DTU.launch`'s `--var` forwarding for `[gitea_source]`.** `harness.py`
   forwards `--gitea-source` as a plain positional argument to
   `setup_scenario.sh`, not as a DTU `launch --var`. If the fixture script
   instead expects `${GITEA_URL}`/`${GITEA_TOKEN}`-style profile
   substitution (the pattern `examples/01-explorer-removal` uses for its
   own Gitea mirrors), that plumbing needs to move to
   `DTU.launch(..., variables={...})` in `run_trial` — a small, localized
   change once the fixtures agent's actual script signature is known.

None of the above could be resolved further without either a live DTU
profile to test against or the fixtures agent's actual `setup_scenario.sh` —
both were absent when this harness was written (per the task's own
constraints). Re-run the smoke test (`./run.sh --smoke`) the moment both
land, and update this section with what was actually observed.
