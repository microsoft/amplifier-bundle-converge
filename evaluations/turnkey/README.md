# The turnkey harness — operation.v1's gate

`contracts/operation.v1.md` closes with a conformance list whose first bullet is
the whole system in one sentence:

> **Turnkey:** fresh environment → one install → start a project, derive from a
> sample gap, run two lanes, tend, judge, integrate, re-check, brief → green.
> **First green 2026-09-04** — nine of nine steps, twice, in fresh containers,
> with a manager session that was not the integrator
> (`evaluations/turnkey/RESULT.md`); it re-runs on every merge.

This directory is the runnable version of that sentence.

**It ran green on 2026-09-04** — nine of nine, twice, in fresh containers
([`RESULT.md`](RESULT.md)) — and the steward ratified the sentence above on the
same day, which is how the contract came to record it. The contract changed by
proposal and the owner's word, never because a harness went green; this is the
evidence the sentence points at.

The nine steps are that sentence and only that sentence. Two further steps,
(j) and (k), read the Core clauses the sentence never reaches; they are tallied
apart and described under [Two more steps](#two-more-steps--the-clauses-the-sentence-does-not-reach).

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
| i | `brief` | a plain-sentence return brief | `docs/workflow/OWNER-RETURN-LOG.md` — its **newest dated entry**, which is the return this run produced: five labelled parts under one heading, written in sentences. Beside it, stamped returns (`## <date> <HH:MM>`) counted against complete briefs, because clause 10 is a brief on *every* return. The file's header is not an entry and never counts as a brief |

Output is a JSON report on stdout, a human summary on stderr, exit 0 when no
step FAILs and 1 when any does.

## Two more steps — the clauses the sentence does not reach

`operation.v1` has thirteen Core clauses. The nine steps above reach three of
them: clause 1 (work is derived), clause 5 (lanes are real sessions) and
clause 10 (a brief on every return). The ledger's probes for the other ten all
read whether `modes/converge-manager.md` still carries the clause's own section
heading — which proves the rule was written down and says nothing about whether
any manager session followed it.

| | Step | Reads | Clauses |
|---|---|---|---|
| j | `clauses` | the lane briefs the manager session wrote, its own plan record in the workspace, git, the queue | 2 · 3 · 4 · 6 · 9 · 11 · 13 |
| k | `attribution` | which side of a lane merge a check-run record arrived on, and the queue's own resolution text | 7 · 8 · 12 |

**They are not part of the turnkey sentence and never change its verdict.**
The report carries two tallies — `turnkey` (a–i) and `clauses` (j–k) — so a
clause reading going red can never be mistaken for the gate going red, and the
exit code still follows the whole run, because a broken promise is a broken
promise.

Each clause reports PASS, FAIL or SKIP on its own, carrying the ledger row it
would let a reconciler re-derive (`CVG-012` … `CVG-023`). A SKIP **names the
observation it is still waiting on**, in words, in the report — and a clause
that was never exercised (no lane stalled, no feedback arrived) is a SKIP that
says exactly that, never a PASS.

Two of these readings need a convention rather than a cleverer parser, because
what they read is only written down if somebody writes it down. Both are in
`context/manager/wave-record.md` and taught in `modes/converge-manager.md`:

- **The call stamp** (clauses 3 and 11) — one line in the plan record naming
  which of the four calls it is, what it parked, and what kept moving beside it.
  Clause 3's promise is a comparison, so a park recorded on its own cannot be
  told from a wave that stopped. The looser form this workspace's manager
  sessions already write (`Parked: x` beside `Live: a, b`) is read too, and
  every reading says which form answered it.
- **The check record** (clauses 7 and 8) — `docs/workflow/CHECK-RECORD.md`, one
  entry per integration, written in the manager session's own commit. The other
  two files a check run leaves a trace in are edited by lanes, so their newest
  change arrives through a lane merge; on this host that left both clauses
  unattributed while the integrator had demonstrably written seven such records
  before. A file only the manager session writes takes the confound out.

The attribution in (k) is structural rather than nominal: every session in this
system commits as the same person, so an author field settles nothing. A lane
commits on its own branch, so its work reaches the integration branch only as
the second parent of a `merge lane/…` commit — `M^1..M^2` is exactly what that
merge carried in, and a commit outside every such set was the integrator's own
hand. The cheaper "is it on the first-parent line?" test is wrong here and was
measured wrong: lanes merge onto an integration branch that reaches main
through a pull-request merge, so main's first-parent line is almost entirely PR
merges and an integrator's own commit sits off it.

What each reading actually read on a live run, and what the remaining SKIPs wait
on, is in [`RESULT.md`](RESULT.md) under *Two more steps*. These two steps have
run in observed mode only; a driven container has never carried them, and
RESULT.md says so rather than leaving it to be found out. The clause 7 and 8
attribution has been exercised on a purpose-built repository — a real lane merge
and a real integration — in `tests/test_turnkey.py`, which is a fixture and not
this host, and RESULT.md says that too.

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
uv run evaluations/turnkey/run.py --self-check      # 55 cases, no environment needed
uv run --with pytest pytest evaluations/turnkey -q  # 115 tests
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
