# Turnkey run result — 2026-09-02

**Verdict: RED.** Both modes, exit 1.

`contracts/operation.v1.md` already records this gate as red — "**Red today** —
this is the work list." This file is what the harness actually reported, with
the failing steps named. It is not a plan; it is a transcript.

| Run | Mode | Command | pass · fail · skip | Exit |
|---|---|---|---|---|
| A | `observed` | `run.py --env local --workspace ~/dev/hw-converge --project converge` | 6 · 2 · 1 | 1 |
| B | `driven` | `run.py --env dtu --project turnkey --ledger-root ~/dev/hw-converge` | 3 · 6 · 0 | 1 |

Both runs were real: run A judged the live `hw-converge` manager wave on this
host; run B stood up an Incus container, installed into it, and tore it down.

---

## Run A — observed, against the live wave (6 PASS · 2 FAIL · 1 SKIP)

```
[SKIP] (a) environment: No fresh environment was stood up; this run judges an existing
           host workspace (/home/bkrabach/dev/hw-converge).
           why skipped: a workspace that is already running is not a fresh environment.
[PASS] (b) install: The one documented install succeeded into a throwaway AMPLIFIER_HOME.
[PASS] (c) install_check: The install check is green: 8 present, 0 not checked.
[PASS] (d) project: Project 'converge' is live in the shared queue with 23 items
           3 deferred, 5 held, 5 open, 10 resolved.
[FAIL] (e) derived: 1 of 23 items do not both name a contract and state what done looks
           like (converge-dxv) — work that cannot point at a gap was invented, not derived.
[PASS] (f) lanes: 6 lanes are real — each has its own worktree registered with git and its
           own terminal session (6 live, 0 ended after running) — and no work item was held
           by a process outside a lane worktree (15 holders checked). 4 lane(s) sit on an
           unchanged branch and are recorded stuck: w3-explainer, w3-guard-2, w3-doc-kit,
           w3-app-vocab. 10 holder(s) could not be placed because their process has exited;
           those are recorded unresolved, not passed.
[PASS] (g) integrated: 11 lane branch(es) are merged into main (newest: 78c549a
           'merge lane/w3-protocol: wave 2/3').
[PASS] (h) rechecked: The contract check was re-run by this harness after integration:
           composition.v1 PASS, documents.v1 PASS.
[FAIL] (i) brief: No return brief at docs/workflow/OWNER-RETURN-LOG.md.

VERDICT: FAIL  (pass=6 fail=2 skip=1)
```

### The two reds are true findings, not harness bugs

**(e) `converge-dxv` names no contract.** Its record reads:

> *title:* Highway: launcher should refuse a lane for an already-held item
> (duplicate lane observed)
> *acceptance:* GIVEN an item already held by a live peer WHEN a manager instance
> tries to launch a lane for it THEN the launch is refused before any worktree or
> tmux session is created…

It states what done looks like, and it is real, useful work discovered by
operating the system. It names no contract. `operation.v1` clause 1: "Every item
traces to a contract gap or to steward feedback, **names its contract**, and
states what done looks like." The fix is one line in the item, not a looser rule.

The check was widened once before this run, and that widening is worth recording
because it cuts the other way. The first version matched only `<name>.vN`, and
flagged `converge-l44` ("Operation §5-6 evidence") — which *does* name its
contract, just not in versioned form. **An over-strict rule fabricates a failure
exactly as badly as a loose one fabricates a pass.** The rule now derives the
contract names from `contracts/*.md` on disk and accepts a bare stem as a *weak*
basis, recorded as weak in the evidence. `converge-l44` passes with that noted;
`converge-dxv` still fails, because it names nothing.

**(i) No `docs/workflow/OWNER-RETURN-LOG.md` exists** — anywhere. Not in this
repository, not in the workspace. `operation.v1` clause 10 requires a brief on
every return, and `context/manager/return-brief.md` names that exact path as
where it is appended. Multiple waves have run and returned. **The durable memory
the convention describes has never been written.** That is the single largest
gap this harness found: everything else in the wave is real and checkable, and
the one artifact the steward is supposed to actually read does not exist.

### What run A proves that no file scan could

- **Lanes are real, measured against the machine.** Six lanes each had a worktree
  registered with git *and* a live terminal session in it.
- **No in-session sub-agent held work.** Fifteen holders were resolved to OS
  processes; every live one was sitting inside a lane worktree. This is the
  assertion acceptance item 3 is about, and on this wave it is green.
- **Four lanes were sitting on unchanged branches** and are recorded stuck
  (clause 7: a marker on an unchanged branch is stuck, whatever the marker says).
  This is a live snapshot, not a defect — those lanes were mid-flight.
- **Ten holders could not be placed** because their processes had exited. Those
  are `unresolved`, never `pass`. Where their resolutions name a lane branch the
  launcher recorded, that is annotated as corroboration and still not a pass:
  prose can be written by a session that never left itself.

---

## Run B — driven, in a fresh container (3 PASS · 6 FAIL)

```
[PASS] (a) environment: DTU instance 'turnkey-20260903T052431Z' is up and answering.
[PASS] (b) install: The one documented install succeeded into /tmp/turnkey-amplifier-home.
[FAIL] (c) install_check: The install check is not green: 1 required dependency missing
           (work-queue-service).
[PASS] (d) project: Project 'turnkey' was started in the shared queue and answers; it holds
           no items yet, which is what the next step derives.
[FAIL] (e) derived: The sample gap is planted and the project is started, but no work has
           been derived from it — the queue is empty.
[FAIL] (f) lanes: Only 0 lane(s) can be shown to have had their own worktree and their own
           terminal session; the turnkey claim needs at least two.
[FAIL] (g) integrated: No lane branch has been merged into main — nothing has been integrated.
[FAIL] (h) rechecked: After integration the fixture's kit still reports rules ['1', '2'] red;
           the wave was supposed to leave none.
[FAIL] (i) brief: No return brief at /opt/converge-under-test/docs/workflow/OWNER-RETURN-LOG.md.

VERDICT: FAIL  (pass=3 fail=6 skip=0)
```

**What genuinely works end to end in a fresh container:** it launches, the
repository under test arrives with real git history (pushed as a git bundle and
cloned inside, because this checkout is a worktree whose `.git` is a file
pointing at a parent that does not exist in the container), the **one documented
install runs and succeeds**, a project is started in the shared queue, and the
gap fixture is seeded and reports its two planted rules red.

**(c) is a true finding about `profiles/turnkey.yaml`**, not about the install
check. The profile runs the queue's supervisor detached (systemd `--user` is
unavailable to root in an Incus container), so `service status` never reports
`active: true`. `install-check.py` will accept a live `--project` query instead —
but step (c) runs *before* step (d) starts the project, so at that moment there
is nothing live to query. Two honest options, neither taken here because both
change something outside this lane's ownership: teach the profile to register a
managed service, or let the install check accept a foregrounded `serve` the way
work-tracker's own `doctor` already does.

**(e) through (i) fail for one reason, and it is the residual below.**

---

## The residual: the harness drives the environment, not the wave

Steps (e)–(i) in driven mode need a **manager session** to actually run the wave
— derive from the gap, launch two lanes, tend them, judge, integrate, re-check,
brief. The harness does not start one. It stands up the environment, installs,
starts the project, and seeds the gap; then it **judges** whatever happened.

That is a real limit and it is named rather than hidden. It is also precisely
the shape of the contract's own claim: the turnkey sentence is red because the
wave-running half is what does not yet run unattended, and a harness that
pretended otherwise would be worth less than no harness.

In `observed` mode this limit does not apply — a real manager session ran the
wave on this host, and run A judged it with the same assertions. Between the two
runs, every one of the nine steps has been exercised against something real.

---

## A fabricated pass the harness caught itself producing

Worth recording, because it is the exact failure mode this harness exists to
refuse, and it happened here.

The container CLI does **not** pass an inner command's exit code through. It
prints an envelope — `{"id", "command", "exit_code", "stdout", "stderr"}` — and
exits 0 whether the inner command succeeded or not. The first driven run took
that at face value and reported:

```
[PASS] (c) install_check: The install check is green: 0 present, 0 not checked.
```

Zero checks present, reported green. Every command inside the container looked
successful and every output looked like an envelope. Four steps were passing for
no reason at all.

Two fixes, both now covered by tests:

1. `unwrap_dtu_envelope` — the envelope is always unwrapped, and an envelope that
   cannot be parsed is a loud failure rather than an empty success.
2. Step (c) now fails when a report arrives with no `checks` in it. **Treating
   "nothing was checked" as "nothing is missing" is the fabricated pass**, and it
   is now structurally impossible rather than merely unlikely.

`tests/test_turnkey.py::test_a_failing_command_inside_a_container_is_not_a_success`
and its three siblings exist so this cannot come back.

---

## What was verified about the harness itself

```
$ uv run evaluations/turnkey/run.py --self-check
  VERDICT: PASS   (16 of 16 assertions behave as specified)

$ uv run --with pytest pytest evaluations/turnkey -q
  30 passed
```

Every `assert_*` function is exercised against evidence that must make it fail,
and a test asserts that every `assert_*` function appears in the self-check — so
a new assertion cannot be added without being made to fail first.

## Infrastructure

Five containers were launched across the runs that produced this file. Each was
registered in the run's infra ledger **before it existed**, and each was
destroyed. `amplifier-digital-twin list` at the end of this lane shows no
`turnkey-*` instance. Nothing this lane stood up outlived it.

One thing was learned by measuring rather than assuming, and it changed the code.
A ledger row records the command that reclaims a resource, and the sweep closes
the row only when that command exits 0. The harness destroys its own container in
a `finally` block — so by sweep time the container is *already gone*, and
`amplifier-digital-twin destroy <gone>` exits 1. A row registered with the plain
destroy command therefore can never close. Measured, on this lane's own ledger:

```
>> sweeping id=turnkey-20260903T051444Z: amplifier-digital-twin destroy …
   FAILED (rc=1)                                                   -> row stays open
>> sweeping id=turnkey-20260903T051654Z: … destroy … ; ! … status … >/dev/null 2>&1
   swept ok                                                        -> row closes
```

So the registered command is now "destroy it, then assert it is not there",
which is true whether this run or a later sweep removed it, and still fails
loudly if the thing is somehow still running. Three rows in the shared workspace
ledger predate that fix or belong to runs from before it; their containers are
destroyed, and those rows are left for the workspace's own sweep rather than
hand-edited — that file documents itself as having exactly one writer.

## The work list this run produces

| # | Finding | Where it belongs |
|---|---|---|
| 1 | `docs/workflow/OWNER-RETURN-LOG.md` has never been written, though several waves have returned | the manager session's own behaviour — clause 10 |
| 2 | `converge-dxv` names no contract | one line in that item — clause 1 |
| 3 | Driven mode cannot run the wave; it only judges one | this harness, and the launcher it would have to call |
| 4 | `profiles/turnkey.yaml`'s queue is not a managed service, so the install check reports it missing | the profile, or the install check's service probe |

None of these were fixed here: this lane owns `evaluations/turnkey/**`, and
changing a contract, the mode, or the install check to make the harness pass
would be the one move that makes a green report worthless.
