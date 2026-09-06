# The adopter harness

**The question:** can someone who holds only `README.md`, and knows nothing
about how any of this is built, get from a fresh machine to a project actually
running the Converge way — on a **new** project, and on an **existing** one?

That is the steward's bar for early adopters, and it is not the question the
turnkey harness next door answers.

| | `../turnkey/` | this |
|---|---|---|
| Measures | what a manager session does once it is running | everything **before** that: the install, finding the manager session at all, and a project's first day |
| Converge in the container at launch | **installed** (`turnkey.yaml:157`) | **absent**, and a readiness gate refuses the launch if it is not |
| Who drives | a manager session given an objective | an **AI user** who has read only `README.md` and drives the CLI like a person |
| Starting point | a fixture repo with a locked contract and two planted gaps | a **blank** repo, and a **real small project** with code, tests, and no vision |
| Green means | the operating loop conforms | an adopter can actually get started |

Turnkey being green and this being red is not a contradiction. It is the exact
shape of the finding: the loop works, and the door to it is not documented.
`docs/workflow/ONBOARDING-AUDIT-2026-09-04.md` is the reading half of the same
question; this is the running half.

## Run it

```
export AMPLIFIER_EVALUATION_SRC=/path/to/amplifier-bundle-evaluation
./evaluations/adopter/run.sh                          # both scenarios
./evaluations/adopter/run.sh --scenarios new-project  # just one
./evaluations/adopter/run.sh --sync-mirror            # re-sync the mirror first
./evaluations/adopter/run.sh --keep                   # leave the DTUs up to poke at
```

Each scenario gets its own container, so both scenarios cost two launches.

Result lands in `RESULT.md` beside this file. The AI user's full transcript
lands **outside** the repository, under
`<workspace>/.amplifier/evaluation/converge-adopter/<UTC-timestamp>/` — a
transcript carries prompts and provider responses, and none of that belongs in a
bundle's git history.

**Prerequisites**, all fail loud rather than degrade: `python3`, `uv`, `git`,
`amplifier-digital-twin`, `amplifier-gitea`; `ANTHROPIC_API_KEY` in the
environment or `~/.amplifier/keys.env`; a Gitea environment holding a mirror of
this repository; and `AMPLIFIER_EVALUATION_SRC` pointing at an
`amplifier-bundle-evaluation` checkout, because `amplifier_evaluation` is not on
PyPI and its `AIUser` composes a bundle into the running interpreter — which a
system python refuses. `run.sh` resolves that venv and says so.

## The two scenarios

- **New project** (`scenarios/new-project.md`) — an empty git repository. The
  adopter wants a vision, a contract, a seeded check, and a queue.
- **Existing project** (`scenarios/existing-project.md`) — `sensorlog`, the
  fixture in `fixtures/existing-repo/`: a working Python CLI, seven passing
  tests, and a README naming two things nobody has decided. It has **no** vision,
  **no** contracts and **no** `AGENTS.md`, and that absence is the fixture — a
  fixture that already had them could not test the adopt path. Never this
  repository itself, which knows too much.

`fixtures/seed.sh` materializes either one and refuses to seed over a non-empty
target.

## How it judges

**The AI user's verdict is evidence about the experience, never evidence about
the artifacts.** Every `PASS` in `RESULT.md` comes from a command this harness
ran inside the container, with the output pasted in. An AI user that reports "I
set up the vision" and a container with no vision file on disk produce a `FAIL`.

**One container per scenario.** Each scenario launches, and destroys, its own
DTU, registered in the machine-wide infra ledger before it exists. Sharing one
container makes the second scenario's install row a measurement of the *first*
scenario's adopter — which is exactly what happened on 2026-09-04, and why
`S2.1 PASS` in that run meant nothing.

Judged per scenario, from that container's own state — three setup rows
(`.G1`–`.G4`) and six that answer the question:

1. Converge is installed **and composed** — registered is not composed. The row
   quotes the same container *before* the AI user ran, so it is visibly a
   measurement of this scenario's own install.
2. A manager session is running against the project — a live session whose
   prompt actually shows `[converge-manager]>`. **Sampled every 30 seconds
   throughout the scenario**, not once at the end: a session restarted seconds
   before a single final capture yields a blank pane, and a blank pane is not
   evidence the mode never showed. The **prompt** is the pass; the bare string
   somewhere on screen is `CAN'T TELL`, because an adopter reading
   `modes/converge-manager.md` puts exactly those characters in the pane
   without the mode being active.
3. A vision is written down.
4. At least one contract is written down.
5. The project's contract check is seeded.
6. A queue holds work that names the contracts it serves — read **where a
   session writes it**: `$AMPLIFIER_WORK_TRACKER_ROOT` (default
   `~/.amplifier-work-tracker`), plus any `.beads` store under `/workspace` or
   `$HOME`, read with `bd list --all --limit 0`. An agent files work through
   its session's `work_*` tools; whether the `amplifier-work-tracker` CLI is on
   `PATH` is a separate fact, reported as one, and never the reason this row is
   red. `--all` is not decoration: `bd list` alone shows open issues, fifty at
   most, so an adopter who filed one item and then finished it reads back as a
   queue holding nothing.

### Four verdicts, because three of them lie

| | means |
|---|---|
| `PASS` | the thing was seen, and the evidence shows it |
| `FAIL` | it was looked for where it would be, and was absent |
| `CAN'T TELL` | the probe could not settle the question — an empty capture, a store that could not be read. **Never** reported as absence, never counted as a pass |
| `SKIP` | the step did not apply to this scenario |

A run with a `CAN'T TELL` in it is `NOT PROVEN`, not `GREEN`. Every non-pass row
names what was missing, or what it could not tell, in plain words — a red step
that does not is not a result.

The rules above are asserted in `tests/test_judging.py`, one case per defect the
2026-09-04 run found in its own judging:

```
uv run --with pytest pytest -q evaluations/adopter/tests/
```

## What the profile deliberately does not pre-install

Read this before reading any red row, so an induced failure is never mistaken for
a real one. `profiles/adopter.yaml` provisions an Amplifier CLI, a provider, git,
tmux, and the `bd`/`dolt` binaries — and deliberately **not** the Converge bundle
(it is the system under test), **not** `amplifier-work-tracker` (README.md:64 and
:90 promise the install brings it; pre-installing it would make that promise
untestable), and **not** the queue's service. The profile's own header says this
at length, and two readiness gates — `converge-absent` and `queue-cli-absent` —
refuse the launch if the container is already contaminated.

`bd` being on disk is also what lets the queue row be read honestly: an agent
files work through its session's `work_*` tools, which need no CLI, so the probe
reads the store those tools write rather than testing for a binary.

## Honest status

Red is a real result here. A first run in which every step names what was missing
is worth more than a green one that assumed. `RESULT.md` records what actually
happened the last time this ran, step by step, including its own limits.
