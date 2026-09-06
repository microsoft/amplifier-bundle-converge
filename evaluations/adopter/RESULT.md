# Adopter harness — RESULT

**RED** — 17 pass · 2 fail · 0 can't tell · 0 skip, run 2026-09-06T03:50:03+00:00.

What this run asked: can someone holding only `README.md` get a NEW project and an EXISTING project to the point of actually running the Converge way? **Each scenario ran in its own fresh container**, so no row below inherits anything another scenario's adopter did. Every verdict was read out of that container by this harness. The AI user's own account is reported separately, as evidence about the experience — never as evidence about the artifacts.

`CAN'T TELL` is a real verdict here, distinct from `FAIL`: it means the probe could not settle the question. It is never reported as absence and never counted as a pass.

## Provenance

- **started** — `2026-09-06T03:50:03+00:00`
- **finished** — `2026-09-06T04:41:06+00:00`
- **profile** — `/home/bkrabach/dev/vision-focused-team-ci/.converge/converge/lanes/w12-adopter-proof/amplifier-bundle-converge/evaluations/adopter/profiles/adopter.yaml`
- **readme_sha256** — `53c2885dabc8a58a7421b118fbb0483aa559d9aa5b5d780b8aee87d173cc9f11`
- **readme_matches_origin_main** — `True`
- **bundle_commit** — `f6b5e30746f11afdccab185c791d81c22795bd6f`
- **pane_sample_interval_s** — `30.0`
- **scenario_budget_s** — `2400.0`
- **output_dir** — `/home/bkrabach/dev/vision-focused-team-ci/.converge/converge/lanes/w12-adopter-proof/.amplifier/evaluation/converge-adopter/20260906T035003Z`
- **New project** — container `adopter-20260906035003-s1`
  - registered before launch: `/home/bkrabach/.local/share/uv/tools/amplifier/lib/python3.13/site-packages/amplifier_app_cli/data/skills/ten-lane-highway/scripts/infra_ledger.sh /home/bkrabach/dev/vision-focused-team-ci/.converge/converge add dtu adopter-20260906035003-s1 'amplifier-digital-twin destroy adopter-20260906035003-s1'`
- **Existing project (adopt)** — container `adopter-20260906035003-s2`
  - registered before launch: `/home/bkrabach/.local/share/uv/tools/amplifier/lib/python3.13/site-packages/amplifier_app_cli/data/skills/ten-lane-highway/scripts/infra_ledger.sh /home/bkrabach/dev/vision-focused-team-ci/.converge/converge add dtu adopter-20260906035003-s2 'amplifier-digital-twin destroy adopter-20260906035003-s2'`

## Steps

| # | What was asked | | What was missing (or, on a pass, what was seen) |
|---|---|---|---|
| | **New project** — `/workspace/new-project` in `adopter-20260906035003-s1` | **PASS** | |
| S1.G1 | This scenario's own container comes up with no Converge in it | PASS | launched adopter-20260906035003-s1 from /home/bkrabach/dev/vision-focused-team-ci/.converge/converge/lanes/w12-adopter-proof/amplifier-bundle-converge/evaluati… |
| S1.G2 | The README under test is in the container, byte for byte | PASS | 316 /workspace/CONVERGE-README.md 53c2885dabc8a58a7421b118fbb0483aa559d9aa5b5d780b8aee87d173cc9f11 /workspace/CONVERGE-README.md [host] 53c2885dabc8a58a7421b11… |
| S1.G3 | This scenario's starting repository is seeded | PASS | /workspace/new-project 16b470ad604272a69ce444071882d29980596550 --- tree --- . .. .git |
| S1.1 | Converge installed and composed into the CLI | PASS | --- at launch, in this scenario's own container, before the AI user --- Available Bundles ┏━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━… |
| S1.2 | A manager session is running against the project | PASS | sampled every 30s through the scenario, 03:51:00Z -> 04:18:58Z: 57 captures, 57 that ran, 55 with a live agent session, 55 with pane content, 11 showing `[conv… |
| S1.3 | A vision is written down in the project | PASS | ./docs/VISION.md --- first 15 lines of each --- == ./docs/VISION.md # mdstrip — Vision (DRAFT) *Written for amplified information workers. Terms of art are def… |
| S1.4 | At least one contract is written down | PASS | contracts/conversion.v1.md --- headings --- # Markdown-to-Text Conversion Contract — v1 (DRAFT) |
| S1.5 | The project's contract check is seeded | PASS | ./ledger/rows.yaml ./ledger/checks ./ledger/checks/test_conversion.py ./ledger/checks/__pycache__ ./ledger/checks/__pycache__/test_conversion.cpython-312-pytes… |
| S1.6 | A queue holds work that names the contracts it serves | PASS | --- the queue CLI (a separate fact from whether a queue holds work) --- amplifier-work-tracker on PATH: /root/.local/bin/amplifier-work-tracker --- every queue… |
| | **Existing project (adopt)** — `/workspace/existing-project` in `adopter-20260906035003-s2` | **FAIL** | |
| S2.G1 | This scenario's own container comes up with no Converge in it | PASS | launched adopter-20260906035003-s2 from /home/bkrabach/dev/vision-focused-team-ci/.converge/converge/lanes/w12-adopter-proof/amplifier-bundle-converge/evaluati… |
| S2.G2 | The README under test is in the container, byte for byte | PASS | 316 /workspace/CONVERGE-README.md 53c2885dabc8a58a7421b118fbb0483aa559d9aa5b5d780b8aee87d173cc9f11 /workspace/CONVERGE-README.md [host] 53c2885dabc8a58a7421b11… |
| S2.G3 | This scenario's starting repository is seeded | PASS | /workspace/existing-project 634776a4e6ad811295b18d0eb800059059e9a30d --- tree --- . .. .git README.md pyproject.toml samples src tests |
| S2.G4 | The existing project's own tests pass before adoption | PASS | [runner] uv run --with pytest pytest ....... [100%] 7 passed in 0.01s |
| S2.1 | Converge installed and composed into the CLI | PASS | --- at launch, in this scenario's own container, before the AI user --- Available Bundles ┏━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━… |
| S2.2 | A manager session is running against the project | PASS | sampled every 30s through the scenario, 04:20:02Z -> 04:41:02Z: 43 captures, 43 that ran, 42 with a live agent session, 42 with pane content, 3 showing `[conve… |
| S2.3 | A vision is written down in the project | PASS | ./docs/VISION.md --- first 15 lines of each --- == ./docs/VISION.md # sensorlog — Vision (FROZEN 2026-09-06) *Written for amplified information workers. Terms … |
| S2.4 | At least one contract is written down | PASS | contracts/cli-behavior.v1.md --- headings --- # CLI Behavior Contract — v1 (DRAFT) |
| S2.5 | The project's contract check is seeded | FAIL | no ledger/rows.yaml (or equivalent contract check) in the project |
| S2.6 | A queue holds work that names the contracts it serves | FAIL | no queue store exists anywhere in the container -- nothing a session's `work_*` tools would have written is on disk (the queue CLI was on PATH) |

## What the AI user reported

The AI user read only `CONVERGE-README.md` and drove the Amplifier CLI as a person would. Where it says it could not find something, that is the finding this harness exists to surface.

### New project

- **verdict** — `success` (after 1678s)

```
Starting from just the CONVERGE-README.md and an empty repo at /workspace/new-project, I worked with the Amplifier CLI agent to adopt Converge end-to-end. The agent read the README, installed/activated Converge (converge-manager mode), and started a persistent manager session against the project (the same tmux session throughout). I described the project ("mdstrip" — a CLI that strips Markdown to plain text, preserving paragraph shape) since none existed yet; the agent drafted docs/VISION.md and contracts/conversion.v1.md and I ratified both after reading them. The manager then filed a work item (mdstrip-c9t), seeded ledger/rows.yaml with GAP rows quoting the contract's four core clauses, launched a worker lane in an isolated git worktree, and the lane implemented src/mdstrip (core.py + cli.py) plus a real pytest conformance kit (ledger/checks/test_conversion.py, 4 substantive tests). The manager independently re-verified the lane's claims (read the tests, ran pytest itself, ran the CLI on fixtures, checked determinism), merged to main, flipped the ledger rows to CONFORMS, wrote a CHECK-RECORD.md entry and an OWNER-RETURN-LOG.md brief, and reported back. I then independently ran the check myself from a clean shell and caught a real bug the agent had missed: its "post-merge, on main" verification was silently resolving mdstrip through a stale `pip install -e` binding to the lane's worktree (not main), so once the manager cleaned up the worktree, main was left with a broken install and a failing check. I reported this; the agent owned it plainly, explained the exact root cause, reinstalled editable from main for real, re-verified genuinely (4 passed, deterministic CLI output), and — good discipline — appended an honest correction to CHECK-RECORD.md/HIGHWAY.md rather than silently rewriting its earlier claim. I then re-verified everything myself one final time: pytest passes, pip's editable location now correctly points at /workspace/new-project, git history shows the full commit chain including the correction, and the work tracker shows item mdstrip-c9t (resolved) explicitly naming conversion.v1 clauses 1-4.

Findings / places the README didn't specify next steps and I had to rely on the agent's judgment or push back myself: (1) the README describes the manager as verifying "by its own re-run check rather than a worker's account," but doesn't warn that an editable-install's bound path can silently survive worktree cleanup and invalidate that very re-run — this was a genuine gap the agent didn't catch on its own, only when I ran the check myself; (2) once the single work item resolved, the queue emptied entirely, so "there is work in a queue naming the contracts it serves" holds only in the sense that the tracker retains the resolved item's record (which does name conversion.v1) — there is no currently open/pending item, and the README doesn't say whether a healthy project's queue should always keep something pending.

All five required end-states w
… [truncated]
```

### Existing project (adopt)

- **verdict** — `failure` (after 1260s)

```
Acting as the intent-steward persona, I drove a manager session through Converge adoption for the sensorlog project: the README was read, the manager investigated the actual code before drafting docs/VISION.md and a CLI-behavior contract, and I reviewed and explicitly ratified both against what I know of the code. Attempting to then 'lock' the ratified vision, the agent froze VISION.md's heading and only afterward tried to add the matching changelog entry in a separate edit, which its own lock guard rejected — leaving the file half-frozen. The agent recognized this was a self-inflicted sequencing bug and tried to recover via grep/delegation, but the session then hung with no progress for over 20 minutes of continuous polling. The remaining required end-states (AGENTS.md/PINS.md, ledger, HIGHWAY.md, alignment queue, contract-serving work items) were never reached.
```

## Evidence, step by step

Verbatim output of the probe behind each row above. A probe that could not run is recorded as a failure or a `CAN'T TELL`, never as a pass.

### S1.G1 — This scenario's own container comes up with no Converge in it — PASS

```
launched adopter-20260906035003-s1 from /home/bkrabach/dev/vision-focused-team-ci/.converge/converge/lanes/w12-adopter-proof/amplifier-bundle-converge/evaluations/adopter/profiles/adopter.yaml in 53s; every readiness gate passed, including `converge-absent` and `queue-cli-absent`

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
316 /workspace/CONVERGE-README.md
53c2885dabc8a58a7421b118fbb0483aa559d9aa5b5d780b8aee87d173cc9f11  /workspace/CONVERGE-README.md

[host] 53c2885dabc8a58a7421b118fbb0483aa559d9aa5b5d780b8aee87d173cc9f11  /home/bkrabach/dev/vision-focused-team-ci/.converge/converge/lanes/w12-adopter-proof/amplifier-bundle-converge/README.md
```

### S1.G3 — This scenario's starting repository is seeded — PASS

```
/workspace/new-project 16b470ad604272a69ce444071882d29980596550
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

### S1.2 — A manager session is running against the project — PASS

```
sampled every 30s through the scenario, 03:51:00Z -> 04:18:58Z: 57 captures, 57 that ran, 55 with a live agent session, 55 with pane content, 11 showing `[converge-manager]>` as the prompt (first at 03:58:03Z), 11 with the string anywhere on screen (first at 03:58:03Z)

--- first capture showing the mode as the prompt, 03:58:03Z ---
<<<SESSIONS
agent: 1 windows (created Sun Sep  6 03:57:04 2026)
error connecting to /tmp/tmux-0/hw (No such file or directory)
SESSIONS>>>
<<<PANE
Bundle 'anchors' prepared successfully
✓ Resuming most recent session: 19b5481a-2b87-435a-b188-493ea5a93d32
  Messages: 44
  Using saved bundle: anchors

╭─────────────────────────────────────────────────────╮
│ Amplifier Interactive Session (Resumed)             │
│ Session: 19b5481a... | Started: 4m ago              │
│ Bundle: bundle:anchors | Model: claude-sonnet-5     │
│ Commands: /help | Multi-line: Ctrl-J | Exit: Ctrl-D │
╰─────────────────────────────────────────────────────╯

... 18 earlier messages. Use --full-history to see all


Amplifier:
This container doesn't have a systemd user session available (no dbus, no XDG_RUNTIME_DIR), so service install can't register a systemd unit here. The CLI has a fallback for exactly this: serve runs the supervisor
directly in the foreground. I'll run it in the background instead.

Amplifier:
This container has no user systemd bus (XDG_RUNTIME_DIR unset, systemctl --user fails), so service install can't work here. The tool provides a foreground alternative (serve) meant to be run as a supervised background
process instead. I'll run that in the background.

Amplifier:
The supervisor is up and running (dolt server accepting connections on 127.0.0.1:3308). Let's verify the adopt-check now passes for the work queue.

Amplifier:
All required checks pass now (exit code 0): "The install took. The manager session is available here."

Summary of what's in place:

 • ✅ Amplifier CLI present
 • ✅ converge-manager mode available
 • ✅ converge bundle registered once
 • ✅ Work queue reachable — amplifier-work-tracker serve running in the background (dolt server on 127.0.0.1:3308, PID 6524)

One caveat worth flagging: I started the queue server as a background process rather than a systemd user service, because this container has no user D-Bus/systemd session (systemctl --user failed — no XDG_RUNTIME_DIR).
That means it won't survive a container restart
… [truncated]
```

### S1.3 — A vision is written down in the project — PASS

```
./docs/VISION.md
--- first 15 lines of each ---
== ./docs/VISION.md
# mdstrip — Vision (DRAFT)

*Written for amplified information workers. Terms of art are defined where they
first appear; the specific promises live in `contracts/`.*

---

## Where this is going

mdstrip takes a directory of Markdown files and writes a mirrored directory of
plain-text files, one per input file, with every piece of Markdown formatting
gone and every paragraph the author wrote still standing exactly where it was.
A **paragraph** here is a run of one or more non-blank lines separated from its
neighbors by at least one blank line — the same shape a person sees when they
read the source file.
```

### S1.4 — At least one contract is written down — PASS

```
contracts/conversion.v1.md
--- headings ---
# Markdown-to-Text Conversion Contract — v1 (DRAFT)
```

### S1.5 — The project's contract check is seeded — PASS

```
./ledger/rows.yaml
./ledger/checks
./ledger/checks/test_conversion.py
./ledger/checks/__pycache__
./ledger/checks/__pycache__/test_conversion.cpython-312-pytest-7.4.4.pyc
--- first 20 lines of ledger/rows.yaml ---
# Conformance ledger for mdstrip.
# Format: docs/LEDGER-FORMAT.md (DRAFT convention, not itself a contract).
# Semantics: PROTOCOL.md §3.3. Checks (when written) run inside the repo's
# own test job -- no new CI job, in-process only.
#
# Seeded 2026-09-06 on ratification of contracts/conversion.v1.md (still
# DRAFT -- no conformance kit or passing implementation exists yet, so the
# freeze bar is not met). Every checkable clause starts at the verdict the
# repository actually earns today: GAP. There is no code, so nothing here
# is CONFORMS yet -- seeding any row CONFORMS before a probe exists would be
# exactly the silent drift this ledger exists to catch.

- id: LGR-000
  title: SYNC - contracts/conversion.v1.md
  contract:
    file: contracts/conversion.v1.md
    clause: "SYNC"
    quote: ""
  disposition: NOT-ASSERTABLE
  assertion:
```

### S1.6 — A queue holds work that names the contracts it serves — PASS

```
--- the queue CLI (a separate fact from whether a queue holds work) ---
amplifier-work-tracker on PATH: /root/.local/bin/amplifier-work-tracker

--- every queue store in this container ---
work-tracker root: /root/.amplifier-work-tracker (exists: True)
store: /root/.amplifier-work-tracker/projects/mdstrip
not a store (a .beads dir with no database in it): /root/.amplifier/cache/amplifier-module-hooks-streaming-ui-e6e48235e2ecca64
not a store (a .beads dir with no database in it): /root

== project mdstrip (/root/.amplifier-work-tracker/projects/mdstrip)
read with bd
1 item(s) (closed=1)
  mdstrip-c9t  Implement mdstrip core conversion + CLI, satisfying conversion.v1 clauses 1-4, with its conformance 
      names a contract: conversion.v1

--- what this measured ---
QUEUE-CLI: present
QUEUE-STORES: 1
QUEUE-ITEMS: 1
QUEUE-CONTRACT-ITEMS: 1
QUEUE-READ-ERRORS: 0
```

### S2.G1 — This scenario's own container comes up with no Converge in it — PASS

```
launched adopter-20260906035003-s2 from /home/bkrabach/dev/vision-focused-team-ci/.converge/converge/lanes/w12-adopter-proof/amplifier-bundle-converge/evaluations/adopter/profiles/adopter.yaml in 54s; every readiness gate passed, including `converge-absent` and `queue-cli-absent`

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
316 /workspace/CONVERGE-README.md
53c2885dabc8a58a7421b118fbb0483aa559d9aa5b5d780b8aee87d173cc9f11  /workspace/CONVERGE-README.md

[host] 53c2885dabc8a58a7421b118fbb0483aa559d9aa5b5d780b8aee87d173cc9f11  /home/bkrabach/dev/vision-focused-team-ci/.converge/converge/lanes/w12-adopter-proof/amplifier-bundle-converge/README.md
```

### S2.G3 — This scenario's starting repository is seeded — PASS

```
/workspace/existing-project 634776a4e6ad811295b18d0eb800059059e9a30d
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
sampled every 30s through the scenario, 04:20:02Z -> 04:41:02Z: 43 captures, 43 that ran, 42 with a live agent session, 42 with pane content, 3 showing `[converge-manager]>` as the prompt (first at 04:26:05Z), 3 with the string anywhere on screen (first at 04:26:05Z)

--- first capture showing the mode as the prompt, 04:26:05Z ---
<<<SESSIONS
agent: 1 windows (created Sun Sep  6 04:25:23 2026)
error connecting to /tmp/tmux-0/hw (No such file or directory)
SESSIONS>>>
<<<PANE
Registered once as converge-behavior (no duplicate-name collision — checked first).


Verified (adopt-check.py → exit 0, "the install took")


 Check                                            Status
 ────────────────────────────────────────────────────────────────────────────────────
 converge-manager mode available                  present
 Converge bundle registered (once, no collision)  present
 Work queue reachable (amplifier-work-tracker)    present
 Locked-contract guard in this repo               present
 A manager session has run here                   absent — expected, none started yet


Two things beyond the bare bundle add were needed to get a clean check, so I did them too:

 • Installed amplifier-work-tracker (uv tool install git+https://github.com/microsoft/amplifier-work-tracker@main) — the reconciler's queue backend. Its published package is missing an httpx dependency declaration, so I
   installed it --with httpx to work around that.
 • Installed the locked-contract guard into this repo: .githooks/pre-push (executable) + git config core.hooksPath .githooks. It's untracked in git — worth committing.

One thing I did not get running: amplifier-work-tracker service install failed because this container has no user systemd/dbus session (systemctl --user → "No medium found"). The work queue is still reachable for now
(ad-hoc), but there's no persistent service surviving a reboot. That's an environment limitation, not a Converge issue — worth knowing if this container is ephemeral.


Not done, on purpose

Starting the manager session itself. That's not an install step — it's the moment you state the outcome and how the work should be found, and per the protocol the first wake on a repo with existing code pauses and
proposes a vision + contracts for your ratification before anything is queued. That's yours to kick off:

───────────────────────────────────────────────────────
… [truncated]
```

### S2.3 — A vision is written down in the project — PASS

```
./docs/VISION.md
--- first 15 lines of each ---
== ./docs/VISION.md
# sensorlog — Vision (FROZEN 2026-09-06)

*Written for amplified information workers. Terms of art are defined where they
first appear; the specific promises live in `contracts/`.*

---

## Where this is going

sensorlog is a small command-line tool that turns a sensor log file into
something a person can read at a glance. Someone runs it against a log —
`report` for the full list, `summary` for one line — and gets back exactly
that: no configuration file to write first, no service to start, no network
call to wait on. The **log** is a plain text file, one **reading** per line
(`<name> <value> [<unit>]`), written by whatever produced the sensor data;
```

### S2.4 — At least one contract is written down — PASS

```
contracts/cli-behavior.v1.md
--- headings ---
# CLI Behavior Contract — v1 (DRAFT)
```

### S2.5 — The project's contract check is seeded — FAIL

Missing: no ledger/rows.yaml (or equivalent contract check) in the project

```
--- first 20 lines of ledger/rows.yaml ---
head: cannot open 'ledger/rows.yaml' for reading: No such file or directory
```

### S2.6 — A queue holds work that names the contracts it serves — FAIL

Missing: no queue store exists anywhere in the container -- nothing a session's `work_*` tools would have written is on disk (the queue CLI was on PATH)

```
--- the queue CLI (a separate fact from whether a queue holds work) ---
amplifier-work-tracker on PATH: /root/.local/bin/amplifier-work-tracker

--- every queue store in this container ---
work-tracker root: /root/.amplifier-work-tracker (exists: False)
not a store (a .beads dir with no database in it): /root/.amplifier/cache/amplifier-module-hooks-streaming-ui-e6e48235e2ecca64
not a store (a .beads dir with no database in it): /root
(no queue store anywhere -- nothing a session's work_* tools would write)

--- what this measured ---
QUEUE-CLI: present
QUEUE-STORES: 0
QUEUE-ITEMS: 0
QUEUE-CONTRACT-ITEMS: 0
QUEUE-READ-ERRORS: 0
```

