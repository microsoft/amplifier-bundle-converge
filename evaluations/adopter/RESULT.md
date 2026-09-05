# Adopter harness — RESULT

**RED** — 12 pass · 3 fail · 0 skip, run 2026-09-04T14:19:11+00:00 on `adopter-20260904141911`.

What this run asked: can someone holding only `README.md` get a NEW project and an EXISTING project to the point of actually running the Converge way? Every verdict below was read out of the container by this harness AFTER the AI user stopped. The AI user's own account is reported separately, as evidence about the experience — never as evidence about the artifacts.

## Provenance

- **started** — `2026-09-04T14:19:11+00:00`
- **finished** — `2026-09-04T15:16:37+00:00`
- **dtu_id** — `adopter-20260904141911`
- **profile** — `/home/bkrabach/dev/hw-converge/lanes/w9-adopter/amplifier-bundle-converge/evaluations/adopter/profiles/adopter.yaml`
- **readme_sha256** — `9f75e2dfe3980d05b1f07ed281df406f6b241fd19170835d01dbb197fe8dbf16`
- **readme_matches_origin_main** — `True`
- **bundle_commit** — `be5933155bf05cb91af0904fd2bffadfc7dd9e97`
- **ledger_registration** — `/home/bkrabach/.local/share/uv/tools/amplifier/lib/python3.13/site-packages/amplifier_app_cli/data/skills/ten-lane-highway/scripts/infra_ledger.sh /home/bkrabach/dev/hw-converge add dtu adopter-20260904141911 'amplifier-digital-twin destroy adopter-20260904141911'`
- **output_dir** — `/home/bkrabach/dev/hw-converge/lanes/w9-adopter/.amplifier/evaluation/converge-adopter/20260904T141911Z`

## Steps

| # | What was asked | | What was missing (or, on a pass, what was seen) |
|---|---|---|---|
| G.1 | A fresh environment comes up with no Converge in it | PASS | launched adopter-20260904141911 from /home/bkrabach/dev/hw-converge/lanes/w9-adopter/amplifier-bundle-converge/evaluations/adopter/profiles/adopter.yaml in 73s… |
| G.2 | The README under test is in the container, byte for byte | PASS | 216 /workspace/CONVERGE-README.md 9f75e2dfe3980d05b1f07ed281df406f6b241fd19170835d01dbb197fe8dbf16 /workspace/CONVERGE-README.md [host] 9f75e2dfe3980d05b1f07ed… |
| G.3 | Both starting repositories are seeded and the existing one really works | PASS | /workspace/new-project 4aa88e8444550cb44561762df2c917836f6f7898 /workspace/existing-project 28874aed46622a72c98f2da5de4951849885d16c --- existing-project tests… |
| | **New project** — `/workspace/new-project` | **FAIL** | |
| S1.1 | Converge installed and composed into the CLI | PASS | --- bundle list --- Available Bundles ┏━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━┓ ┃ Name ┃ Location ┃ Status ┃ ┡━━━━━━━━━━… |
| S1.2 | A manager session is running against the project | FAIL | a session is live but its prompt never shows `[converge-manager]` -- an ordinary session is not a manager session |
| S1.3 | A vision is written down in the project | PASS | ./docs/VISION.md --- first 15 lines of each --- == ./docs/VISION.md # linkcheck — Vision (DRAFT) *Written for amplified information workers. Terms of art are d… |
| S1.4 | At least one contract is written down | PASS | contracts/link-checking.v1.md --- headings --- # Link Checking Contract — v1 (DRAFT) |
| S1.5 | The project's contract check is seeded | PASS | ./ledger/rows.yaml ./ledger/checks ./ledger/checks/test_sync.py ./ledger/reconcile-report.md --- first 20 lines of ledger/rows.yaml --- - id: LC-000 title: SYN… |
| S1.6 | A queue holds work that names the contracts it serves | FAIL | the work queue CLI never arrived -- so no item, and no naming of any contract, can exist to be read |
| | **Existing project (adopt)** — `/workspace/existing-project` | **FAIL** | |
| S2.1 | Converge installed and composed into the CLI | PASS | --- bundle list --- Available Bundles ┏━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━┓ ┃ Name ┃ Location ┃ Status ┃ ┡━━━━━━━━━━… |
| S2.2 | A manager session is running against the project | PASS | --- tmux sessions --- agent: 1 windows (created Fri Sep 4 14:55:49 2026) sensorlog-agent: 1 windows (created Fri Sep 4 14:54:57 2026) agent: 1 windows (created… |
| S2.3 | A vision is written down in the project | PASS | ./docs/VISION.md --- first 15 lines of each --- == ./docs/VISION.md # sensorlog — Vision **Status: LOCKED** (steward, 2026-09-04). Written from a direct read o… |
| S2.4 | At least one contract is written down | PASS | contracts/cli-output.v1.md --- headings --- # CLI Output — contract v1 |
| S2.5 | The project's contract check is seeded | PASS | ./ledger/rows.yaml ./ledger/checks ./ledger/checks/test_probes.py ./ledger/checks/__init__.py ./ledger/checks/__pycache__ ./ledger/checks/__pycache__/test_prob… |
| S2.6 | A queue holds work that names the contracts it serves | FAIL | the work queue CLI never arrived -- so no item, and no naming of any contract, can exist to be read |

## What the AI user reported

The AI user read only `CONVERGE-README.md` and drove the Amplifier CLI as a person would. Where it says it could not find something, that is the finding this harness exists to surface.

### New project

The AI user did not conclude: the AI user did not finish within 1800s

### Existing project (adopt)

- **verdict** — `success` (after 1562s)

```
Acting as the intent steward for the existing `sensorlog` CLI project, I asked the Amplifier CLI to read the Converge README and adopt Converge for the project. Over an extended session the agent: installed/confirmed Converge, started a `converge-manager` session scoped to `/workspace/existing-project`, and before proposing anything actually read `src/sensorlog/` and `tests/test_sensorlog.py` (verified — VISION.md and the contract both cite this direct read, not the README, as their basis). It drafted `docs/VISION.md` and `contracts/cli-output.v1.md`, surfaced two genuine open decisions in the contract for me to rule on rather than guessing, consulted `converge:protocol-authority` when the freeze-bar's applicability to a vision document (vs. a contract) was ambiguous, and only locked either document after I explicitly said the word ("ratify" / decisions given by me). It ran a SEED reconcile that built `ledger/rows.yaml` (6 rows citing exact contract-clause quotes, byte-verified against the contract text) and filed a real work-tracker item `sensorlog-9ge` under a new `sensorlog` project, tying two VIOLATION rows to that item. It caught and honestly disclosed that the contract's own Conformance section overclaimed test coverage for two clauses, closing the gap with new ledger-owned probes rather than silently accepting the claim. It also flagged, unprompted, that it was skipping heavier operation.v1.md ceremony (plan records, return logs) because that contract was never adopted by this repo — declining to fabricate machinery nobody asked for. I independently verified via direct file reads (not just agent claims) that `docs/VISION.md` and `contracts/cli-output.v1.md` are both status LOCKED with my name/date, and that `ledger/rows.yaml` contains real, quote-verified rows referencing the filed work item.
```

## Evidence, step by step

Verbatim output of the probe behind each row above. A probe that could not run is recorded as a failure, never as a pass.

### G.1 — A fresh environment comes up with no Converge in it — PASS

```
launched adopter-20260904141911 from /home/bkrabach/dev/hw-converge/lanes/w9-adopter/amplifier-bundle-converge/evaluations/adopter/profiles/adopter.yaml in 73s; every readiness gate passed, including `converge-absent` and `queue-cli-absent`
```

### G.2 — The README under test is in the container, byte for byte — PASS

```
216 /workspace/CONVERGE-README.md
9f75e2dfe3980d05b1f07ed281df406f6b241fd19170835d01dbb197fe8dbf16  /workspace/CONVERGE-README.md

[host] 9f75e2dfe3980d05b1f07ed281df406f6b241fd19170835d01dbb197fe8dbf16  /home/bkrabach/dev/hw-converge/lanes/w9-adopter/amplifier-bundle-converge/README.md
```

### G.3 — Both starting repositories are seeded and the existing one really works — PASS

```
/workspace/new-project 4aa88e8444550cb44561762df2c917836f6f7898
/workspace/existing-project 28874aed46622a72c98f2da5de4951849885d16c
--- existing-project tests, as they stood before adoption ---
/usr/bin/python3: No module named pytest
```

### S1.1 — Converge installed and composed into the CLI — PASS

```
--- bundle list ---
                               Available Bundles                                
┏━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━┓
┃ Name            ┃ Location                                          ┃ Status ┃
┡━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━┩
│ amplifier-dev   │ git+https://github.com/microsoft/amplifier-found… │        │
│ anchors         │ git+https://github.com/microsoft/amplifier-found… │        │
│ anchors-amp-dev │ git+https://github.com/microsoft/amplifier-found… │        │
│ converge        │ git+https://github.com/microsoft/amplifier-bundl… │        │
│ exp-delegation  │ git+https://github.com/microsoft/amplifier-found… │        │
│ foundation      │ git+https://github.com/microsoft/amplifier-found… │        │
└─────────────────┴───────────────────────────────────────────────────┴────────┘

Mode: No bundle active (default)
Use --all to see all bundles including dependencies and nested bundles.
--- agents list (converge rows) ---
  [on]  converge  bundle
  [on]  converge-behavior  bundle
```

### S1.2 — A manager session is running against the project — FAIL

Missing: a session is live but its prompt never shows `[converge-manager]` -- an ordinary session is not a manager session

```
--- tmux sessions ---
agent: 1 windows (created Fri Sep  4 14:50:02 2026)
agent: 1 windows (created Fri Sep  4 14:50:02 2026)
--- agent pane, last 40 lines ---
```

### S1.3 — A vision is written down in the project — PASS

```
./docs/VISION.md
--- first 15 lines of each ---
== ./docs/VISION.md
# linkcheck — Vision (DRAFT)

*Written for amplified information workers. Terms of art are defined where they
first appear; the specific promises live in `contracts/`.*

---

## Where this is going

`linkcheck` is a single-purpose command-line tool: point it at a directory, and
it tells you, precisely and quickly, which relative links between the Markdown
files in that directory are broken. A **relative link** here means any Markdown
link (`[text](path)`) whose target is not a full URL (no `http://`, `https://`,
`mailto:`, or similar scheme) — it is a path meant to resolve to another file on
disk, relative to the file that contains it. A link is **broken** when that path
```

### S1.4 — At least one contract is written down — PASS

```
contracts/link-checking.v1.md
--- headings ---
# Link Checking Contract — v1 (DRAFT)
```

### S1.5 — The project's contract check is seeded — PASS

```
./ledger/rows.yaml
./ledger/checks
./ledger/checks/test_sync.py
./ledger/reconcile-report.md
--- first 20 lines of ledger/rows.yaml ---
- id: LC-000
  title: SYNC — contract file hash pinned (link-checking.v1)
  contract:
    file: contracts/link-checking.v1.md
    clause: "SYNC"
    quote: |
      # Link Checking Contract — v1 (DRAFT)
  disposition: CONFORMS
  assertion:
    kind: probe
    ref: test_row_lc_000
  notes: >
    SEEDED 2026-09-04, first population — ledger/ did not exist before this
    run (confirmed: `ls ledger` failed with ENOENT prior to this write).
    Repo tree at seed time: .amplifier/, .githooks/pre-push, AGENTS.md,
    PINS.md, contracts/link-checking.v1.md, docs/VISION.md — zero source
    files, zero conformance/ directory, zero prior ledger, zero .py files.
    Independently computed this run: sha256(contracts/link-checking.v1.md)
    = 81dd62ace60b9d7af38eacc91b3ba63a6d83e4678b204b7374925cd7625da280,
    verified via `python3 ledger/checks/test_sync.py` (in-process, no
```

### S1.6 — A queue holds work that names the contracts it serves — FAIL

Missing: the work queue CLI never arrived -- so no item, and no naming of any contract, can exist to be read

```
amplifier-work-tracker is not on PATH
```

### S2.1 — Converge installed and composed into the CLI — PASS

```
--- bundle list ---
                               Available Bundles                                
┏━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━┓
┃ Name            ┃ Location                                          ┃ Status ┃
┡━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━┩
│ amplifier-dev   │ git+https://github.com/microsoft/amplifier-found… │        │
│ anchors         │ git+https://github.com/microsoft/amplifier-found… │        │
│ anchors-amp-dev │ git+https://github.com/microsoft/amplifier-found… │        │
│ converge        │ git+https://github.com/microsoft/amplifier-bundl… │        │
│ exp-delegation  │ git+https://github.com/microsoft/amplifier-found… │        │
│ foundation      │ git+https://github.com/microsoft/amplifier-found… │        │
└─────────────────┴───────────────────────────────────────────────────┴────────┘

Mode: No bundle active (default)
Use --all to see all bundles including dependencies and nested bundles.
--- agents list (converge rows) ---
  [on]  converge  bundle
  [on]  converge-behavior  bundle
```

### S2.2 — A manager session is running against the project — PASS

```
--- tmux sessions ---
agent: 1 windows (created Fri Sep  4 14:55:49 2026)
sensorlog-agent: 1 windows (created Fri Sep  4 14:54:57 2026)
agent: 1 windows (created Fri Sep  4 14:55:49 2026)
sensorlog-agent: 1 windows (created Fri Sep  4 14:54:57 2026)
--- agent pane, last 40 lines ---
   with Given/When/Then acceptance mapped to every "Conformance kit asserts" bullet in the contract plus Core 1 (hidden-dir exclusion) and Core 4 (containing-file-relative resolution), each with a stated falsifier,
   ending in a required ledger re-derivation.
 • Filed as one item (width 1), not eight — same root cause, and splitting implementation from its own conformance kit now would manufacture a coordination collision (argument shape vs. invocation shape) rather than
   avoid one.
 • Wrote the plan record (PLAN.md) with dated entries for the SEED and this DERIVE step, plus a checked-and-recorded decision on the DRAFT/FROZEN tension: I ran the freeze-bar's four conditions against it — condition 3
   ("checked against reality, ≥1 real implementation passes it") can't be met with zero implementation, so no CALL ratify was stamped. Sending one now would itself be the clause-11 defect. This is deliberately not a call
   to you yet — it becomes one once linkcheck-c55 lands and its kit passes.
 • Also flagged (not filed, no contract backs it): PINS.md references docs/CONTRACTS-README.md, which doesn't exist.


Not yet done

I haven't briefed or launched a lane for linkcheck-c55 — that's a real worktree/branch/tmux session, a bigger step than "derive and name," so I stopped here rather than spin that up unannounced. Say the word and I'll
write the lane brief (lane-brief skill) and launch it.

│  📊 Token Usage (anthropic/claude-sonnet-5) [16.8s]
└─ Input: 121,661 (98% cached) | Output: 1,563 | Total: 123,224 | Cost: $0.07
💰 Turn: $2.03 | Session: $2.03

[converge-manager]> Good — hold off on launching the lane for now. I want to sit with the current state first: vision, contract, ledger, and
… [truncated]
```

### S2.3 — A vision is written down in the project — PASS

```
./docs/VISION.md
--- first 15 lines of each ---
== ./docs/VISION.md
# sensorlog — Vision

**Status: LOCKED** (steward, 2026-09-04). Written from a direct read of
`src/sensorlog/` and `tests/test_sensorlog.py` (2026-09-04), not from the
README alone. Freeze Bar conditions 2–4 are inherited from
`contracts/cli-output.v1.md` (already LOCKED, per `converge:protocol-authority`
ruling 2026-09-04: a vision that points at its governing contract rather than
repeating it does not grow a conformance kit of its own). Any further change
to this vision requires a proposal beside this file
(`VISION.v2-candidate.md`), never a direct edit — see `docs/PROTOCOL.md` §5
and the `proposing-a-change` skill.

## Where this repository is going

sensorlog is a small, honest command-line tool. Given a sensor log file, it
```

### S2.4 — At least one contract is written down — PASS

```
contracts/cli-output.v1.md
--- headings ---
# CLI Output — contract v1
```

### S2.5 — The project's contract check is seeded — PASS

```
./ledger/rows.yaml
./ledger/checks
./ledger/checks/test_probes.py
./ledger/checks/__init__.py
./ledger/checks/__pycache__
./ledger/checks/__pycache__/test_probes.cpython-312-pytest-9.1.1.pyc
./ledger/checks/__pycache__/__init__.cpython-312.pyc
--- first 20 lines of ledger/rows.yaml ---
# Conformance ledger for the sensorlog repo (docs/LEDGER-FORMAT.md).
# Top-level shape: a plain YAML list of rows. No wrapper mapping, no meta key.
# SYNC row is first, by convention id <PREFIX>-000.
#
# SEED run: 2026-09-04, against contracts/cli-output.v1.md (status: LOCKED,
# steward, 2026-09-04) -- the repo's only locked contract. Checks run via:
#   uv run pytest tests/test_sensorlog.py -v   (the project's own suite)
#   uv run pytest ledger/checks -v             (ledger-owned probes, for the
#                                                two clauses the project's
#                                                own suite does not yet
#                                                discriminate)

- id: LGR-000
  title: SYNC -- contract hash pin (cli-output.v1)
  contract:
    file: contracts/cli-output.v1.md
    sha256: 98a2ad4373875de492fc76efa51cc41b819d222d9af60ca29d3a3507c57241dc
  disposition: NOT-ASSERTABLE
  assertion:
    kind: none
```

### S2.6 — A queue holds work that names the contracts it serves — FAIL

Missing: the work queue CLI never arrived -- so no item, and no naming of any contract, can exist to be read

```
amplifier-work-tracker is not on PATH
```


---

## Limits of this run — read before trusting a row above

Appended by hand after the run, from its own evidence. The harness code was
**not** changed afterwards, so everything above is what the code as committed
actually produced. Each limit below is filed as work rather than quietly fixed.

**1 · S2.1 is not an independent measurement.** Both scenarios ran in one
container, in order. Converge was installed by scenario 1's AI user, so by the
time scenario 2 started it was already there: `S2.1 PASS` says nothing about
whether scenario 2's adopter could have installed it. Only `S1.1 PASS` is a real
install result. A fresh container per scenario is the fix (`converge-f0bj`).

**2 · The queue probe reads the wrong surface, so S1.6 and S2.6 overclaim.**
The probe looks for the `amplifier-work-tracker` **CLI on PATH**, and its
"missing" sentence says no item can exist. That is more than the evidence
supports. `README.md:90` promises the `--app` behavior gives the *session* its
`work_*` filing tools — a different thing from a CLI binary — and scenario 2's AI
user reported filing item `sensorlog-9ge` under a new `sensorlog` project through
exactly that path. So: **the CLI really was absent** (that part is measured), and
**whether a queue held items is unproven** (that part is not). The container is
destroyed, so it cannot be settled after the fact. The probe has to read the
queue the way the agent writes it (`converge-f0bj`).

**3 · S1.2's reason overclaims too.** Its evidence is an *empty* pane: the
scenario-1 AI user restarted its tmux session at 14:50:02, twenty-eight seconds
before the budget cut at 14:50:30, so the capture caught a fresh, blank pane. An
empty pane is not evidence that the prompt never showed `[converge-manager]`. The
honest reading of scenario 1 is that the probe proved nothing either way. The fix
is to sample the pane throughout the scenario rather than once at the end
(`converge-f0bj`).

**4 · Scenario 1's AI user never concluded.** It hit the 1800-second budget with
the conversation still going. That is itself a result worth keeping — thirty
minutes of steward-facing back-and-forth had not reached a stopping point on a
blank repository — but it means there is no scenario-1 verdict to compare against
the artifacts.

## What this run does establish

Stated separately from the table, because a `PASS`/`FAIL` count is not a finding.

- **The manager mode is reachable, and was reached — once.** Scenario 2's pane
  shows a real `[converge-manager]>` prompt (evidence under `S2.2`). So nothing
  is structurally broken about entering the mode. Combined with the audit's
  finding that no document names the command, what this measures is a path that
  works for someone who finds it.
- **Both scenarios produced a vision, a contract, and a seeded ledger** — with no
  documented day-one path anywhere in the repository. The agent improvised the
  sequence both times, and produced different shapes each time: scenario 1
  hand-built the participant kit file by file, scenario 2 ran a seed reconcile
  and filed work. Two adopters would get two different first days.
- **Scenario 2 stayed honest under pressure.** Its own account reports reading
  `src/sensorlog/` before proposing anything, surfacing two open decisions rather
  than guessing, consulting `protocol-authority` on an ambiguity, locking nothing
  until the steward said the word, and disclosing that the contract's
  Conformance section overclaimed its own test coverage. The artifacts back the
  first four: `S2.3`, `S2.4` and `S2.5` all pass on files this harness read
  itself.
- **The cost is real.** Roughly an hour of wall time and two long provider
  sessions to adopt one small project, most of it spent working out what to do
  next rather than doing it.
