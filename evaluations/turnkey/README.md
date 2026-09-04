# The turnkey harness — operation.v1's red gate

`contracts/operation.v1.md` closes with a conformance list whose first bullet is
the whole system in one sentence:

> **Turnkey:** fresh environment → one install → start a project, derive from a
> sample gap, run two lanes, tend, judge, integrate, re-check, brief → green.
> **Red today** — this is the work list.

This directory is the runnable version of that sentence.

**As of 2026-09-04 it runs green** — nine of nine, twice, in fresh containers
([`RESULT.md`](RESULT.md)). The contract still records the gate as red; a
contract changes by proposal and the steward's word, never because a harness
went green, so that line is left exactly as it is and this is the evidence
under it.

```sh
./evaluations/turnkey/run.sh                        # fresh container, real wave
./evaluations/turnkey/run.sh --sync-mirror          # re-sync the mirror first
./evaluations/turnkey/run.sh --self-check           # no environment needed
./evaluations/turnkey/run.sh --env local --workspace ~/dev/hw-converge
uv run evaluations/turnkey/run.py --help            # every flag, unwrapped
```

`run.sh` is a thin entry point: it proves the Gitea mirror the container
installs from matches github before anything launches, resolves the secrets and
the infra ledger, and puts the run's output — including the manager session's
full transcript — outside this repository. Everything else is `run.py`, which is
stdlib-only and needs no install beyond `uv run`.

**What it actually reported the last time it ran is in [`RESULT.md`](RESULT.md)
— currently GREEN, with the four defects it took to get there.**

## The nine steps

| | Step | Asserts | Evidence it reads |
|---|---|---|---|
| a | `environment` | a fresh isolated environment stood up | the container's own status, and a probe command answering inside it |
| b | `install` | the one documented install performed | `README.md`'s own `amplifier bundle add` line, run for real, into a throwaway `AMPLIFIER_HOME` |
| c | `install_check` | `scripts/install-check.py` green inside it | that script's JSON report — every required dependency, named |
| d | `project` | a project started | the shared queue answering for the project, with items in it |
| e | `derived` | work derived from a fixture gap | the fixture's own kit; then every item's record, for a contract it names and a *done* it states |
| f | `lanes` | **two REAL lanes**, tended, judged | `git worktree list`, `tmux list-panes` on the launcher's own socket, `/proc/<pid>/cwd` of every item's holder, commits beyond each lane's base — live where they can still be read, and from readings taken during the wave where they cannot |
| g | `integrated` | results integrated and verified | merge commits naming `lane/*` on the integration branch |
| h | `rechecked` | contracts re-checked | the contract kits, re-run **by this harness** after integration |
| i | `brief` | a plain-sentence return brief | `docs/workflow/OWNER-RETURN-LOG.md` — dated, five parts, written in sentences |

Output is a JSON report on stdout, a human summary on stderr, exit 0 when no
step FAILs and 1 when any does.

## Three statuses, and a SKIP is never a soft pass

| Status | Means |
|---|---|
| `PASS` | The harness checked this and the promise is kept. |
| `FAIL` | The harness checked this and the promise is broken. |
| `SKIP` | The harness **could not check this**, and says why in a `reason` field. |

A step the harness cannot execute is SKIP with a stated reason and never a
fabricated PASS. A green line nobody can back up is the exact failure this
harness exists to prevent — and it has caught itself producing one (see
[`RESULT.md`](RESULT.md), run 2).

## Two run modes, named in every report

**`driven`** (`--env dtu`) — the harness stands the environment up itself,
carries the repository under test into it as a git bundle (so git still has
real history to answer about), runs the one documented install inside it, seeds
the fixture, and then **runs the operation for real**: a headless `amplifier
run` inside the container, told to work in the converge-manager mode against
the fixture, with the objective in [`manager-objective.md`](manager-objective.md).

That manager session is a separate process. This harness does not participate
in the wave it is judging — it holds a deadline and takes readings from
outside, every 15 seconds, of the three systems that can only answer in the
present tense: the multiplexer's session list, git's worktree list, and where
each held item's process is sitting. `--no-wave` stands the environment up
without one, and judges whatever is there.

**`observed`** (`--env local`) — the harness judges a manager wave that ran on
this host, against the same assertions and the same evidence. Step (a) is SKIP:
a workspace that is already running is not a fresh environment, and saying
otherwise would be a lie. Every step's `mode` field says which it was.

## The heart of it: how a real lane is told from a sub-agent

`operation.v1` clause 5 says a lane is "a worker session's own working copy,
branch, and terminal session", and that in-session sub-agents serve four roles,
"**none of which executes lane work**".

A manager session that quietly runs lane work in a sub-agent produces artifacts
that look identical from the outside: commits, a resolution, a green check. The
one thing it cannot fake is **where the holding process was sitting**.

A real lane is a separate process whose working directory is its own worktree.
An in-session sub-agent runs inside the manager session's process, so it reports
the manager session's pid and therefore the manager session's directory — which
is never a lane worktree. That is the discriminator:

```python
        cwd = process.get("cwd", "")
        record.update(pid=pid, cwd=cwd)
        lane = next((w for w in lane_worktrees if _within(cwd, w)), None)
        if lane is None:
            record.update(
                verdict=FAIL,
                why=f"held by pid {pid} sitting in {cwd!r}, which is not any lane "
                    "worktree — the signature of work executed inside a session "
                    "rather than in a lane",
            )
            offenders.append(record)
        elif pid in live_pids:
            record.update(
                verdict=FAIL,
                why=f"pid {pid} also holds {live_pids[pid]} — one process cannot be "
                    "two lanes, so at least one of these ran in-session",
            )
            offenders.append(record)
```

`assert_no_subagent_held_work` in [`run.py`](run.py), and the companion
`assert_lane_is_real`, which checks both halves of clause 5 against the systems
that would know — git's own worktree list and the multiplexer's own pane list —
never against a manifest row's say-so.

Two deliberate refusals in that code:

- **An exited holder is unresolved, never a pass.** When the process is gone its
  directory cannot be read. If its resolution names a lane branch the launcher
  recorded, that is *annotated as corroboration* and still not a pass: prose can
  be written by a session that never left itself.
- **A finished lane is not a violation.** Its terminal session is gone precisely
  because it ran and exited. So the verdict is a state — `live`, `ended`,
  `unproven`, `not_a_lane` — and only `not_a_lane` fails. `unproven` is the
  honest middle: what the harness says instead of guessing.

## Proving the assertions can fail

An assertion nobody can make fail proves nothing.

```sh
uv run evaluations/turnkey/run.py --self-check      # 24 cases, no environment needed
uv run --with pytest pytest evaluations/turnkey -q  # 57 tests
```

`--self-check` runs every `assert_*` function against synthetic evidence that
must make it fail, and a test asserts that **every** `assert_*` function appears
in it — so a new assertion cannot be added without being exercised. The pytest
suite additionally proves the fixture is red before any work, that the answer
key says what the fixture actually says, and that the two gaps do not touch.

## The fixture

[`fixtures/`](fixtures/) — a tiny repository with two planted gaps in two files
that do not touch, and its own conformance kit that reports both red. Two
disjoint gaps is the smallest fixture that makes "run two lanes" the correct
answer rather than an arbitrary one (clause 6: width is a collision decision).
See [`fixtures/README.md`](fixtures/README.md).

## Anything it stands up, it tears down

`--env dtu` registers the container in the run's infra ledger **before the
container exists**, and destroys it in a `finally` block. It refuses to launch
at all if the ledger is unreachable: an unregistered container that outlives the
run is worse than a step the run could not perform. `--keep` leaves it up, says
so in the report, and reminds you that you now own it.

## Relationship to the other kits

`conformance/` holds three kits that read files. This is the fourth contract's
kit, and it cannot be one of them: `operation.v1`'s promises are about a
*running* system — processes, terminal sessions, a live queue — so it lives here
under `evaluations/`, beside the [ratchet eval](../ratchet/), whose shape it
follows.
