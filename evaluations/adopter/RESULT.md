# Adopter harness — RESULT

**GREEN** — 19 pass · 0 fail · 0 can't tell · 0 skip, run 2026-09-06T02:07:34+00:00.

What this run asked: can someone holding only `README.md` get a NEW project and an EXISTING project to the point of actually running the Converge way? **Each scenario ran in its own fresh container**, so no row below inherits anything another scenario's adopter did. Every verdict was read out of that container by this harness. The AI user's own account is reported separately, as evidence about the experience — never as evidence about the artifacts.

`CAN'T TELL` is a real verdict here, distinct from `FAIL`: it means the probe could not settle the question. It is never reported as absence and never counted as a pass.

## Provenance

- **started** — `2026-09-06T02:07:34+00:00`
- **finished** — `2026-09-06T03:15:09+00:00`
- **profile** — `/home/bkrabach/dev/vision-focused-team-ci/.converge/converge/lanes/w10-harness-judging/amplifier-bundle-converge/evaluations/adopter/profiles/adopter.yaml`
- **readme_sha256** — `1be929caccd57b212c59505251147cd3f9aebd2d86f29e397fe8e210e943e6e4`
- **readme_matches_origin_main** — `True`
- **bundle_commit** — `52937ba7acb10702fd7f2dd9092d0b04a5e89cb2`
- **pane_sample_interval_s** — `30.0`
- **scenario_budget_s** — `2400.0`
- **output_dir** — `/home/bkrabach/dev/vision-focused-team-ci/.converge/converge/lanes/w10-harness-judging/.amplifier/evaluation/converge-adopter/20260906T020734Z`
- **New project** — container `adopter-20260906020734-s1`
  - registered before launch: `/home/bkrabach/.local/share/uv/tools/amplifier/lib/python3.13/site-packages/amplifier_app_cli/data/skills/ten-lane-highway/scripts/infra_ledger.sh /home/bkrabach/dev/vision-focused-team-ci/.converge/converge add dtu adopter-20260906020734-s1 'amplifier-digital-twin destroy adopter-20260906020734-s1'`
- **Existing project (adopt)** — container `adopter-20260906020734-s2`
  - registered before launch: `/home/bkrabach/.local/share/uv/tools/amplifier/lib/python3.13/site-packages/amplifier_app_cli/data/skills/ten-lane-highway/scripts/infra_ledger.sh /home/bkrabach/dev/vision-focused-team-ci/.converge/converge add dtu adopter-20260906020734-s2 'amplifier-digital-twin destroy adopter-20260906020734-s2'`

## Steps

| # | What was asked | | What was missing (or, on a pass, what was seen) |
|---|---|---|---|
| | **New project** — `/workspace/new-project` in `adopter-20260906020734-s1` | **PASS** | |
| S1.G1 | This scenario's own container comes up with no Converge in it | PASS | launched adopter-20260906020734-s1 from /home/bkrabach/dev/vision-focused-team-ci/.converge/converge/lanes/w10-harness-judging/amplifier-bundle-converge/evalua… |
| S1.G2 | The README under test is in the container, byte for byte | PASS | 274 /workspace/CONVERGE-README.md 1be929caccd57b212c59505251147cd3f9aebd2d86f29e397fe8e210e943e6e4 /workspace/CONVERGE-README.md [host] 1be929caccd57b212c59505… |
| S1.G3 | This scenario's starting repository is seeded | PASS | /workspace/new-project 56b665ae87b00686803209684476f1ae8eef3185 --- tree --- . .. .git |
| S1.1 | Converge installed and composed into the CLI | PASS | --- at launch, in this scenario's own container, before the AI user --- Available Bundles ┏━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━… |
| S1.2 | A manager session is running against the project | PASS | sampled every 30s through the scenario, 02:08:28Z -> 02:40:17Z: 65 captures, 65 that ran, 64 with a live agent session, 64 with pane content, 7 showing `[conve… |
| S1.3 | A vision is written down in the project | PASS | ./docs/VISION.md --- first 15 lines of each --- == ./docs/VISION.md # Readlog — Vision (DRAFT) *Written for the person who wants to know, at a glance, what the… |
| S1.4 | At least one contract is written down | PASS | contracts/storage-schema.v1.md --- headings --- # Storage Schema Contract — v1 (FROZEN 2026-09-06) |
| S1.5 | The project's contract check is seeded | PASS | ./ledger/rows.yaml --- first 20 lines of ledger/rows.yaml --- # Conformance ledger — readlog # # Format: docs/LEDGER-FORMAT.md (Converge starter convention, DR… |
| S1.6 | A queue holds work that names the contracts it serves | PASS | --- the queue CLI (a separate fact from whether a queue holds work) --- amplifier-work-tracker on PATH: no --- every queue store in this container --- work-tra… |
| | **Existing project (adopt)** — `/workspace/existing-project` in `adopter-20260906020734-s2` | **PASS** | |
| S2.G1 | This scenario's own container comes up with no Converge in it | PASS | launched adopter-20260906020734-s2 from /home/bkrabach/dev/vision-focused-team-ci/.converge/converge/lanes/w10-harness-judging/amplifier-bundle-converge/evalua… |
| S2.G2 | The README under test is in the container, byte for byte | PASS | 274 /workspace/CONVERGE-README.md 1be929caccd57b212c59505251147cd3f9aebd2d86f29e397fe8e210e943e6e4 /workspace/CONVERGE-README.md [host] 1be929caccd57b212c59505… |
| S2.G3 | This scenario's starting repository is seeded | PASS | /workspace/existing-project a35a63750618b74fa193290ec122980fd9b2d0e8 --- tree --- . .. .git README.md pyproject.toml samples src tests |
| S2.G4 | The existing project's own tests pass before adoption | PASS | [runner] uv run --with pytest pytest ....... [100%] 7 passed in 0.01s |
| S2.1 | Converge installed and composed into the CLI | PASS | --- at launch, in this scenario's own container, before the AI user --- Available Bundles ┏━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━… |
| S2.2 | A manager session is running against the project | PASS | sampled every 30s through the scenario, 02:41:14Z -> 03:15:04Z: 69 captures, 69 that ran, 67 with a live agent session, 67 with pane content, 18 showing `[conv… |
| S2.3 | A vision is written down in the project | PASS | ./docs/VISION.md --- first 15 lines of each --- == ./docs/VISION.md # sensorlog — Vision (FROZEN) *Written for amplified information workers. Terms of art are … |
| S2.4 | At least one contract is written down | PASS | contracts/log-format.v1.md --- headings --- # Log Format Contract — v1 (FROZEN) |
| S2.5 | The project's contract check is seeded | PASS | ./ledger/rows.yaml ./ledger/checks ./ledger/checks/__pycache__ ./ledger/checks/__pycache__/test_rows.cpython-312-pytest-9.1.1.pyc ./ledger/checks/test_rows.py … |
| S2.6 | A queue holds work that names the contracts it serves | PASS | --- the queue CLI (a separate fact from whether a queue holds work) --- amplifier-work-tracker on PATH: no --- every queue store in this container --- work-tra… |

## What the AI user reported

The AI user read only `CONVERGE-README.md` and drove the Amplifier CLI as a person would. Where it says it could not find something, that is the finding this harness exists to surface.

### New project

- **verdict** — `failure` (after 1909s)

```
Acting as a new adopter, I worked with the Amplifier CLI (Converge bundle) end-to-end: read the README, described a small project (Readlog, a personal reading-log CLI), let the agent draft and I approved a DRAFT vision and a LOCKED storage-schema contract with a passing conformance kit, discovered and worked around an undocumented bundle-activation/session-restart requirement, stood up the work-tracker service by hand after finding a PATH bug, entered converge-manager mode, and had the reconciler seed a ledger (7 rows, all CONFORMS) plus two doc-mismatch queue items — which the agent itself flagged as not actually "serving" the contract, just mentioning it in prose. Those two items were then resolved directly (small in-place fixes), leaving the queue empty. Final honest status, confirmed by the agent's own closing report: bullets 1 (installed), 3 (vision written), and 4 (contract written/locked) are solid; bullet 2 (manager session running) is true but session-bound rather than daemon-bound, contradicting the README's framing; bullet 5 (queue names the contracts it serves) never had a genuine instance — the only queue items were tangential doc fixes, and no structured contract-link mechanism exists.
```

### Existing project (adopt)

- **verdict** — `success` (after 2031s)

```
Acting as intent steward, I used only the Converge README to drive an Amplifier converge-manager session to adopt Converge for the sensorlog project. The agent investigated the actual code and tests before proposing anything, then drafted a vision document and a contract with checkable clauses, which I reviewed and ratified after catching and correcting one bad self-ratification attempt. I required a real contract check plus a work queue naming the contracts served. The agent built a ledger with six rows and two new passing pytest probes, ten of ten tests green. It first claimed zero work-queue items were needed and called that correct. I rejected that, citing a stale contract-prose gap and unreviewed commits to pyproject.toml and a new test file I had never seen before they landed. The agent conceded, filed a real queryable item through the work-tracker tool naming the contract and gap, and retroactively surfaced the prior diffs.
```

## Evidence, step by step

Verbatim output of the probe behind each row above. A probe that could not run is recorded as a failure or a `CAN'T TELL`, never as a pass.

### S1.G1 — This scenario's own container comes up with no Converge in it — PASS

```
launched adopter-20260906020734-s1 from /home/bkrabach/dev/vision-focused-team-ci/.converge/converge/lanes/w10-harness-judging/amplifier-bundle-converge/evaluations/adopter/profiles/adopter.yaml in 51s; every readiness gate passed, including `converge-absent` and `queue-cli-absent`

--- read back from the container, before the AI user ---
<<<BUNDLES
                               Available Bundles                                
┏━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━┓
┃ Name            ┃ Location                                          ┃ Status ┃
┡━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━┩
│ amplifier-dev   │ git+https://github.com/microsoft/amplifier-found… │        │
│ anchors         │ git+https://github.com/microsoft/amplifier-found… │        │
│ anchors-amp-dev │ git+https://github.com/microsoft/amplifier-found… │        │
│ exp-delegation  │ git+https://github.com/microsoft/amplifier-found… │        │
│ foundation      │ git+https://github.com/microsoft/amplifier-found… │        │
└─────────────────┴───────────────────────────────────────────────────┴────────┘

Mode: No bundle active (default)
Use --all to see all bundles including dependencies and nested bundles.
BUNDLES>>>
<<<QUEUECLI
amplifier-work-tracker: not on PATH
QUEUECLI>>>
```

### S1.G2 — The README under test is in the container, byte for byte — PASS

```
274 /workspace/CONVERGE-README.md
1be929caccd57b212c59505251147cd3f9aebd2d86f29e397fe8e210e943e6e4  /workspace/CONVERGE-README.md

[host] 1be929caccd57b212c59505251147cd3f9aebd2d86f29e397fe8e210e943e6e4  /home/bkrabach/dev/vision-focused-team-ci/.converge/converge/lanes/w10-harness-judging/amplifier-bundle-converge/README.md
```

### S1.G3 — This scenario's starting repository is seeded — PASS

```
/workspace/new-project 56b665ae87b00686803209684476f1ae8eef3185
--- tree ---
.
..
.git
```

### S1.1 — Converge installed and composed into the CLI — PASS

```
--- at launch, in this scenario's own container, before the AI user ---
Available Bundles                                
┏━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━┓
┃ Name            ┃ Location                                          ┃ Status ┃
┡━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━┩
│ amplifier-dev   │ git+https://github.com/microsoft/amplifier-found… │        │
│ anchors         │ git+https://github.com/microsoft/amplifier-found… │        │
│ anchors-amp-dev │ git+https://github.com/microsoft/amplifier-found… │        │
│ exp-delegation  │ git+https://github.com/microsoft/amplifier-found… │        │
│ foundation      │ git+https://github.com/microsoft/amplifier-found… │        │
└─────────────────┴───────────────────────────────────────────────────┴────────┘

Mode: No bundle active (default)
Use --all to see all bundles including dependencies and nested bundles.

[queue CLI at launch] amplifier-work-tracker: not on PATH

--- after the AI user stopped ---
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

### S1.2 — A manager session is running against the project — PASS

```
sampled every 30s through the scenario, 02:08:28Z -> 02:40:17Z: 65 captures, 65 that ran, 64 with a live agent session, 64 with pane content, 7 showing `[converge-manager]>` as the prompt (first at 02:36:42Z), 7 with the string anywhere on screen (first at 02:36:42Z)

--- first capture showing the mode as the prompt, 02:36:42Z ---
<<<SESSIONS
agent: 1 windows (created Sun Sep  6 02:29:20 2026)
error connecting to /tmp/tmux-0/hw (No such file or directory)
SESSIONS>>>
<<<PANE

│  📊 Token Usage (anthropic/claude-sonnet-5) [18.5s]
└─ Input: 84,659 (96% cached) | Output: 1,654 | Total: 86,313 | Cost: $0.06

🔧 Using tool: write_file
   content: |
       # Check record

       Append-only. Every entry is written by the manager session's own hand, in
       its own commit on the integration branch — never through a lane merge. Each
   ... (42 more lines)

🔧 Using tool: bash
   command: mkdir -p /workspace/new-project/docs/workflow

🔧 Using tool: write_file
   content: |
       # Owner return log

       Newest entry last. Written by the manager session, before it replies, every
       time the intent steward returns (clock-time heading) or an unprompted brief
   ... (44 more lines)
✅ Tool result: bash
   (no output)

✅ Tool result: write_file
   bytes: 1316
   file_path: /workspace/new-project/docs/workflow/CHECK-RECORD.md

✅ Tool result: write_file
   bytes: 2448
   file_path: /workspace/new-project/docs/workflow/OWNER-RETURN-LOG.md

============================================================================================================================================================================================================================
Thinking:
----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
I should commit this work directly as the manager session rather than through a lane, so I'll check git status first and then commit the files.
============================================================================================================================================================================================================================
🔧 Building tool call: bash…

│  📊 Token Usage (anthropic/claude-sonnet-5) [2.3s]
└─ Input: 86,556 (97% cached) | Output: 104 | Tota
… [truncated]
```

### S1.3 — A vision is written down in the project — PASS

```
./docs/VISION.md
--- first 15 lines of each ---
== ./docs/VISION.md
# Readlog — Vision (DRAFT)

*Written for the person who wants to know, at a glance, what they're reading
and what they finished this year, without any of it living anywhere but their
own machine.*

---

## Where this is going

Readlog is a small command-line tool for tracking personal reading habits. A
reader opens a terminal, types one short command, and either logs a book
they've just started, marks a book finished, or asks to see a list — what
they're currently reading, or what they finished this year. Nothing more
happens: no browser, no account, no sync between devices, no server anywhere.
```

### S1.4 — At least one contract is written down — PASS

```
contracts/storage-schema.v1.md
--- headings ---
# Storage Schema Contract — v1 (FROZEN 2026-09-06)
```

### S1.5 — The project's contract check is seeded — PASS

```
./ledger/rows.yaml
--- first 20 lines of ledger/rows.yaml ---
# Conformance ledger — readlog
#
# Format: docs/LEDGER-FORMAT.md (Converge starter convention, DRAFT — not a
# contract). Semantics of disposition/quote/assertion rules owned by
# PROTOCOL.md §3.3; this file follows the syntax that doc describes.
#
# Seeded 2026-09-06 against the only locked contract in this repo,
# contracts/storage-schema.v1.md (FROZEN 2026-09-06). One row per numbered
# clause in that contract's "Core (the teeth)" section — the only section
# naming checkable promises. The "What v1 deliberately does NOT freeze"
# section is explicitly non-promises (deferred or excluded pending a vision
# amendment) and gets no row: no clause, no row.
#
# All row assertions are `kind: indexed`, citing functions in the project's
# own existing conformance kit (conformance/storage-schema/run.py) — this
# ledger does not reimplement the project's checks, and no ledger/checks/
# probes were authored this run since indexed citation was sufficient for
# every clause. Verified 2026-09-06 by actually running:
#   python3 conformance/storage-schema/run.py
# Real result observed: 11/11 PASS, exit 0 (see report for full output).
```

### S1.6 — A queue holds work that names the contracts it serves — PASS

```
--- the queue CLI (a separate fact from whether a queue holds work) ---
amplifier-work-tracker on PATH: no

--- every queue store in this container ---
work-tracker root: /root/.amplifier-work-tracker (exists: True)
store: /root/.amplifier-work-tracker/projects/readlog
not a store (a .beads dir with no database in it): /root/.amplifier/cache/amplifier-module-hooks-streaming-ui-e6e48235e2ecca64
not a store (a .beads dir with no database in it): /root

== project readlog (/root/.amplifier-work-tracker/projects/readlog)
read with bd
2 item(s) (closed=2)
  readlog-15l  Fix stale "Status of this repository" note in AGENTS.md §1
      names a contract: contracts/storage-schema.v1.md
  readlog-auv  Create docs/CONTRACTS-README.md now that the first contract has locked
      names a contract: contracts/storage-schema.v1.md

--- what this measured ---
QUEUE-CLI: absent
QUEUE-STORES: 1
QUEUE-ITEMS: 2
QUEUE-CONTRACT-ITEMS: 2
QUEUE-READ-ERRORS: 0
```

### S2.G1 — This scenario's own container comes up with no Converge in it — PASS

```
launched adopter-20260906020734-s2 from /home/bkrabach/dev/vision-focused-team-ci/.converge/converge/lanes/w10-harness-judging/amplifier-bundle-converge/evaluations/adopter/profiles/adopter.yaml in 49s; every readiness gate passed, including `converge-absent` and `queue-cli-absent`

--- read back from the container, before the AI user ---
<<<BUNDLES
                               Available Bundles                                
┏━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━┓
┃ Name            ┃ Location                                          ┃ Status ┃
┡━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━┩
│ amplifier-dev   │ git+https://github.com/microsoft/amplifier-found… │        │
│ anchors         │ git+https://github.com/microsoft/amplifier-found… │        │
│ anchors-amp-dev │ git+https://github.com/microsoft/amplifier-found… │        │
│ exp-delegation  │ git+https://github.com/microsoft/amplifier-found… │        │
│ foundation      │ git+https://github.com/microsoft/amplifier-found… │        │
└─────────────────┴───────────────────────────────────────────────────┴────────┘

Mode: No bundle active (default)
Use --all to see all bundles including dependencies and nested bundles.
BUNDLES>>>
<<<QUEUECLI
amplifier-work-tracker: not on PATH
QUEUECLI>>>
```

### S2.G2 — The README under test is in the container, byte for byte — PASS

```
274 /workspace/CONVERGE-README.md
1be929caccd57b212c59505251147cd3f9aebd2d86f29e397fe8e210e943e6e4  /workspace/CONVERGE-README.md

[host] 1be929caccd57b212c59505251147cd3f9aebd2d86f29e397fe8e210e943e6e4  /home/bkrabach/dev/vision-focused-team-ci/.converge/converge/lanes/w10-harness-judging/amplifier-bundle-converge/README.md
```

### S2.G3 — This scenario's starting repository is seeded — PASS

```
/workspace/existing-project a35a63750618b74fa193290ec122980fd9b2d0e8
--- tree ---
.
..
.git
README.md
pyproject.toml
samples
src
tests
```

### S2.G4 — The existing project's own tests pass before adoption — PASS

```
[runner] uv run --with pytest pytest
.......                                                                  [100%]
7 passed in 0.01s
```

### S2.1 — Converge installed and composed into the CLI — PASS

```
--- at launch, in this scenario's own container, before the AI user ---
Available Bundles                                
┏━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━┓
┃ Name            ┃ Location                                          ┃ Status ┃
┡━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━┩
│ amplifier-dev   │ git+https://github.com/microsoft/amplifier-found… │        │
│ anchors         │ git+https://github.com/microsoft/amplifier-found… │        │
│ anchors-amp-dev │ git+https://github.com/microsoft/amplifier-found… │        │
│ exp-delegation  │ git+https://github.com/microsoft/amplifier-found… │        │
│ foundation      │ git+https://github.com/microsoft/amplifier-found… │        │
└─────────────────┴───────────────────────────────────────────────────┴────────┘

Mode: No bundle active (default)
Use --all to see all bundles including dependencies and nested bundles.

[queue CLI at launch] amplifier-work-tracker: not on PATH

--- after the AI user stopped ---
--- bundle list ---
                               Available Bundles                                
┏━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━┓
┃ Name            ┃ Location                                          ┃ Status ┃
┡━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━┩
│ amplifier-dev   │ git+https://github.com/microsoft/amplifier-found… │        │
│ anchors         │ git+https://github.com/microsoft/amplifier-found… │        │
│ anchors-amp-dev │ git+https://github.com/microsoft/amplifier-found… │        │
│ exp-delegation  │ git+https://github.com/microsoft/amplifier-found… │        │
│ foundation      │ git+https://github.com/microsoft/amplifier-found… │        │
│ converge        │ git+https://github.com/microsoft/amplifier-bundl… │ app    │
└─────────────────┴───────────────────────────────────────────────────┴────────┘

Mode: No bundle active (default)
Use --all to see all bundles including dependencies and nested bundles.
--- agents list (converge rows) ---
  [on]  converge  bundle
  [on]  converge-behavior  bundle
```

### S2.2 — A manager session is running against the project — PASS

```
sampled every 30s through the scenario, 02:41:14Z -> 03:15:04Z: 69 captures, 69 that ran, 67 with a live agent session, 67 with pane content, 18 showing `[converge-manager]>` as the prompt (first at 02:45:46Z), 18 with the string anywhere on screen (first at 02:45:46Z)

--- first capture showing the mode as the prompt, 02:45:46Z ---
<<<SESSIONS
agent: 1 windows (created Sun Sep  6 02:43:16 2026)
error connecting to /tmp/tmux-0/hw (No such file or directory)
SESSIONS>>>
<<<PANE
✅ Tool result: glob
   base_path: /workspace/existing-project
   count: 0
   matches: []
   pattern: **/AGENTS.md
   total_files: 0

============================================================================================================================================================================================================================
Thinking:
----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
Everything's clear, so I'll move forward with drafting the response now.
============================================================================================================================================================================================================================


Amplifier:
Confirmed: no AGENTS.md, no docs/ at all — clean slate, as you said. Here's what the code actually does, and what I found while reading it. Nothing below is written to disk or ratified — it's my read, for you to decide
on.


What's actually here

readings.py — parse_line splits a line on whitespace: first token is name, second is value (parsed as float, so a bad number raises ValueError uncaught), third optional token is unit. Blank lines and #-comments return
None and are dropped. Fewer than 2 tokens raises ValueError("malformed reading: ...") — that's the one case that's already a hard error. read_log reads a whole file into an ordered list, preserving file order.

report.py — render_report prints one line per reading, name: value unit, substituting ? when unit == "" (report.py:12). render_summary (report.py:17-27):

 • empty log → "0 readings"
 • no reading has a unit → "N readings, no units"
 • otherwise: finds the modal unit via max(set(units), key=units.count), and averages only readings matching that uni
… [truncated]
```

### S2.3 — A vision is written down in the project — PASS

```
./docs/VISION.md
--- first 15 lines of each ---
== ./docs/VISION.md
# sensorlog — Vision (FROZEN)

*Written for amplified information workers. Terms of art are defined where they
first appear; the specific promises live in `contracts/`.*

---

## Where this is going

sensorlog is the fast way to look at a day's sensor readings without writing a
parser. Point it at a log file and get back either the full ordered list of
readings (`report`) or a one-line digest (`summary`) — nothing more: no unit
conversion, no persistence, no daemon watching a file for new lines.

A **reading** is one line of a log file: a name, a numeric value, and an
```

### S2.4 — At least one contract is written down — PASS

```
contracts/log-format.v1.md
--- headings ---
# Log Format Contract — v1 (FROZEN)
```

### S2.5 — The project's contract check is seeded — PASS

```
./ledger/rows.yaml
./ledger/checks
./ledger/checks/__pycache__
./ledger/checks/__pycache__/test_rows.cpython-312-pytest-9.1.1.pyc
./ledger/checks/test_rows.py
--- first 20 lines of ledger/rows.yaml ---
# Conformance ledger for sensorlog.
# Format: docs/LEDGER-FORMAT.md (Converge). Semantics: PROTOCOL.md §3.3.
# This is the FIRST population (SEED) of this ledger -- there is no prior
# rows.yaml in this repo.

- id: LGR-000
  title: SYNC -- contract hash pin
  contract:
    file: contracts/log-format.v1.md
    clause: SYNC
  disposition: NOT-ASSERTABLE
  assertion:
    kind: none
  justification: >
    This is the hash-pinning row (LEDGER-FORMAT.md §4), not a checkable
    clause -- there is no promise here for a probe/indexed/absence check to
    assert against, only a byte-hash for drift detection. Verified by
    running `sha256sum` directly (below), re-run at every reconciliation.
  notes: >
    Pins contracts/log-format.v1.md as it stood at FREEZE (2026-09-06,
```

### S2.6 — A queue holds work that names the contracts it serves — PASS

```
--- the queue CLI (a separate fact from whether a queue holds work) ---
amplifier-work-tracker on PATH: no

--- every queue store in this container ---
work-tracker root: /root/.amplifier-work-tracker (exists: True)
store: /root/.amplifier-work-tracker/projects/sensorlog
not a store (a .beads dir with no database in it): /root/.amplifier/cache/amplifier-module-hooks-streaming-ui-e6e48235e2ecca64
not a store (a .beads dir with no database in it): /root

== project sensorlog (/root/.amplifier-work-tracker/projects/sensorlog)
read with bd
1 item(s) (open=1)
  sensorlog-6f3  Propose citing LGR-002/LGR-004 probes in log-format.v1's own "Conformance kit asserts" prose
      names a contract: log-format.v1

--- what this measured ---
QUEUE-CLI: absent
QUEUE-STORES: 1
QUEUE-ITEMS: 1
QUEUE-CONTRACT-ITEMS: 1
QUEUE-READ-ERRORS: 0
```

