# Turnkey run result — 2026-09-04

**Verdict: GREEN.** Nine steps, nine PASS, no SKIP, exit 0 — twice, in two
fresh containers, with two different manager sessions.

`contracts/operation.v1.md` opens its conformance list with the whole system in
one sentence, and has carried "**Red today** — this is the work list" beside it
since it was written:

> **Turnkey:** fresh environment → one install → start a project, derive from a
> sample gap, run two lanes, tend, judge, integrate, re-check, brief → green.

That sentence now runs, unattended, end to end. This file is what the harness
reported, including the four runs it took to get here and what each one found.

| Run | Instance | Result | What it was for |
|---|---|---|---|
| C | `turnkey-20260904T035511Z` | 5 · 4 · 0, exit 1 | first wave ever driven; found four defects |
| — | `turnkey-20260904T040824Z` | abandoned | cancelled mid-provision to fix the sampling interval |
| D | `turnkey-20260904T041055Z` | 8 · 1 · 0, exit 1 | four fixes in; found a fifth, in the brief |
| E | `turnkey-20260904T042036Z` | **9 · 0 · 0, exit 0** | first green |
| F | `turnkey-20260904T043038Z` | **9 · 0 · 0, exit 0** | green again, with (f) fully measured |

Every one of those containers is destroyed. `amplifier-digital-twin list` shows
none of them.

---

## The green run (F), step by step

```
Converge turnkey — operation.v1 — Conformance kit asserts, bullet 1 (Turnkey)
  mode:        driven (DTU instance 'turnkey-20260904T043038Z')
  repository:  /opt/converge-under-test
  project:     turnkey
  wave:        a manager session ran for 261.5s and finished (exit 0),
               watched from outside in 17 readings

[PASS] (a) environment: DTU instance 'turnkey-20260904T043038Z' is up and answering.
[PASS] (b) install: The one documented install succeeded into /tmp/turnkey-amplifier-home.
[PASS] (c) install_check: The install check is green: 8 present, 0 not checked.
[PASS] (d) project: Project 'turnkey' was started in the shared queue and answers; it
           holds no items yet, which is what the next step derives.
[PASS] (e) derived: All 2 sampled items name one of this repository's 14 contracts and
           state what done looks like; the fixture's own kit reported rules ['1', '2']
           red before the wave and reports [] red now.
[PASS] (f) lanes: 2 lanes are real — each has its own worktree registered with git and
           its own terminal session (0 live, 2 ended after running) — and no work item
           was held by a process outside a lane worktree (2 holders checked). At
           2026-09-04T04:34:24+00:00, 2 lane terminal session(s) and 2 lane worktree(s)
           were visible at once, read from outside the manager session.
[PASS] (g) integrated: 2 lane branch(es) are merged into main (newest: a8a7e21 'merge
           lane/index: lumen.v1 Core 2 index fix'). Two or more lanes landed in one
           repository, so a post-merge gate is required; this harness runs it itself in
           the next step, rather than trusting either lane's green.
[PASS] (h) rechecked: The contract check was re-run by this harness after integration:
           lumen.v1 PASS.
[PASS] (i) brief: A dated return brief is at /workspace/lumen-fixture/docs/workflow/
           OWNER-RETURN-LOG.md with all five parts and 10 plain sentences.

VERDICT: PASS  (pass=9 fail=0 skip=0)
```

Total 366s: about 105s to stand the container up and install into it, 261s for
the wave.

### What each green line actually read

**(a)–(c) One install, from a mirror proven current first.** `run.sh` refuses to
launch until the Gitea mirror the profile installs from matches github:

```
[04:30:38] mirror is current: admin/amplifier-bundle-converge main == github main
           (b7ed3f0f8e4fdf31ea5f508ba8ab3932b3c05100)
```

The command step (b) runs is read out of `README.md` at run time, so the harness
cannot drift from what the repository tells a newcomer to type:

```json
{"command": "amplifier bundle add git+https://github.com/microsoft/amplifier-bundle-converge@main#subdirectory=behaviors/converge.yaml --app",
 "source": "README.md, first 'amplifier bundle add' line of 2",
 "amplifier_home": "/tmp/turnkey-amplifier-home", "exit_code": 0}
```

One command. `url_rewrites` sends those bytes to the mirror without changing a
character of the command itself.

**(e) The gaps were there before, and are gone after.**

```json
"fixture_planted": {"verdict": "FAIL", "red_rules": ["1", "2"], "exit_code": 1},
"fixture_planted_read": "before the wave",
"fixture_now":     {"verdict": "PASS", "red_rules": [],        "exit_code": 0}
```

Both derived items name `lumen.v1` and state what done looks like.

**(f) Two lanes, proven four different ways.** This is the step the whole gate is
about, and it is the one that cannot be satisfied by a session doing the work
itself and writing a good report afterwards.

*Their own worktrees and their own terminal sessions, at the same moment, read
from outside the manager's process:*

```json
{"at": "2026-09-04T04:34:24+00:00",
 "lane_sessions":  ["hw__turnkey-batch__index", "hw__turnkey-batch__units"],
 "lane_worktrees": ["lane/index", "lane/units"], "both": 2}
```

*Their holding processes, each sitting inside its own lane worktree — the
discriminator clause 5 actually turns on:*

| Item | Verdict | The holder's working directory | Read at |
|---|---|---|---|
| `turnkey-zf0` | PASS | `/workspace/turnkey-batch/lanes/units/lumen-fixture` | 04:34:40Z |
| `turnkey-69z` | PASS | `/workspace/turnkey-batch/lanes/index/lumen-fixture` | 04:34:57Z |

*Commits beyond each lane's own base (clause 7):* `1 commit(s) beyond 84af18ff`,
both lanes. *And the launcher's manifest as the lane source*, not an inference.

**(g)–(h) Integrated, then re-checked by the harness.** Two lane merges —
`50738fc`, `a8a7e21` — and the fixture's own kit re-run by this harness after
both landed: `lumen.v1 PASS (pass=2 fail=0 skip=0)`. Neither lane's own green
proved the pair; the post-merge gate did.

**(i) A brief a person can read.** All five parts present, 10 plain sentences,
dated, 5050 bytes, at the path the return-brief convention names.

---

## What the manager session did, in its own words

The harness handed it `manager-objective.md` — an objective, a width, a
deadline, and where things are — and then watched. It did not tell it how to
derive work, how to write a lane brief, or how to judge one. From run E's brief:

> **Truly ready.** Both contract gaps are closed on `main` and I re-ran the kit
> myself against the merged result: PASS, no red rules.
>
> **Finished.** Two lanes, one wave, about five minutes wall clock end to end.
> […] I re-ran `python3 check.py .` on `main` myself, after both merges landed
> together (the post-merge gate — neither lane's own green proved the pair)
> […] I read both back with `work_list` before writing this brief, so what's
> quoted above is what's actually stored, not what I intended to store.
>
> **Anything quietly broken.** […] `write_file`/`edit_file` refused to write
> inside `/workspace/turnkey-batch` (outside this project's allowed write
> paths), so I wrote both lane goal files with `bash` heredocs instead.

That last paragraph is a finding the harness could not have produced, reported
by the system under test about itself. It is in the work list below.

---

## The residual this run closed

The previous RESULT.md ended on one:

> **The harness drives the environment, not the wave.** Steps (e)–(i) in driven
> mode need a manager session to actually run the wave […] The harness does not
> start one.

It does now. `drive_wave` starts a headless `amplifier run` inside the
container, told to work in the converge-manager mode against the fixture, and
then does two things and only two: holds a deadline, and takes readings from
outside. The manager session is a separate process; this harness does not
participate in the wave it is judging.

**Watching from outside is not incidental — it is the evidence.** A sub-agent
cannot appear in another process's terminal-session list, and a holder's
working directory can only be read while that process is alive. Both of the
strongest facts in step (f) exist only during the wave, and until something was
watching, nobody was there to take them.

---

## The four defects the first driven wave found, and one it did not

Run C did everything the contract asks — two real lanes, both gaps closed, both
branches merged, the kit green, a five-part brief — and the harness reported 4
of 9 steps red. Three of those reds were the harness's own, and all three are
the same species of error: judging a true thing against a rule that could not
accommodate it.

| | What it said | What was actually true |
|---|---|---|
| (e) | "The fixture is not in its planted state: expected rules ['1','2'] red, found []" | The wave had closed both gaps, which is its job. The planted-state assertion ran *after* it. |
| (f) | "No lanes found: neither a launcher manifest nor a worktree on a lane/* branch exists" | Two lanes had run and merged. A finished wave removes its worktrees; the harness dropped every lane whose worktree was gone — including two it had itself watched running. |
| (i) | "carries no dated entry" | The entry was headed `## 2026-09-04T04:01Z`. The date regex ended in `\b`, which an ISO-8601 *timestamp* fails: the `4` of `04` is followed by `T`. |

Each fix keeps the assertion's teeth:

- The fixture's planted state is now read **at seed time**, before a manager
  session exists to change it, and the current state is reported beside it.
- A lane whose worktree is gone is judged against **a reading taken while the
  wave ran** — but only one carrying *both* halves at once for that lane, which
  is the same bar the live check applies. Half an observation resurrects
  nothing, and another lane's observation vouches for nothing.
- A date followed by a time is a date.

**(c) was not the harness's**, and was fixed where it belonged. The check's own
stated promise is a *reachable* queue service — "without a reachable queue
service no claim or heartbeat can be recorded" — and a managed unit is one way
to be reachable, not the only one. `systemd --user` is unavailable to root in
an Incus container, so the profile runs the queue detached; that queue served
an entire wave — claims, custody, resolutions — while `install-check.py` called
it missing. It now accepts an answering unmanaged server *and says plainly that
nothing will restart it after a reboot*.

Run D then found a fifth, which is **not** fixed here — see the work list.

## Two more the green run found by reading its own evidence

Run E was green, and still had two annotations worth chasing:

**"2 lane(s) have no base SHA to measure progress from"** — actually
`git could not count commits e90dfb0c..lane/units-if6`. `commits_beyond` asked
the *lane's worktree*, which the manager had removed after merging. `base..branch`
is a question about two refs and any clone holding both can answer it; the main
repository was sitting right there with both branches merged into it. Run F
measured what run E could not: `1 commit(s) beyond 84af18ff`, both lanes.

**Four containers registered into a ledger nobody sweeps.** `run.sh` defaulted
`--ledger-root` to the checkout's parent, which is this *lane's* directory, not
the workspace. Every container was destroyed by its own run, so nothing leaked
— but had one survived, its row would have been invisible exactly where someone
would look for it. A container is a machine-wide resource; the default now
prefers the outermost ancestor that already keeps an `infra.tsv`.

```
[04:30:38] infra ledger: /home/bkrabach/dev/hw-converge/infra.tsv
```

---

## Proving the assertions can still fail

```
$ uv run evaluations/turnkey/run.py --self-check
  VERDICT: PASS   (24 of 24 assertions behave as specified)

$ uv run --with pytest pytest evaluations/turnkey -q
  57 passed
```

Every `assert_*` function is exercised against evidence that must make it fail,
and a test asserts that every `assert_*` function appears in the self-check — so
a new assertion cannot be added without being made to fail first. The seven
assertions added or changed here are covered by cases drawn from what actually
went wrong, not from what was convenient:

- a merged, cleaned-up lane reads `ended`; one never seen running does not
- half an observation does not resurrect a lane, and another lane's does not
- an exited holder read *inside* a lane passes; read *outside* one still fails
- two sessions in one reading and two worktrees in another is **not** a pass
- a half that never once reached the width is a real failure, not a miss
- a removed worktree falls back to the repository that still has the refs
- the objective the repository ships can actually be composed

That fourth one is worth its own line. `assert_lanes_observed_live` had two
verdicts, so a sampler that blinked and a manager that never launched lanes
produced the same red. Periodic sampling cannot tell those apart, and this
harness already has a word for that: **unproven**. It is now `SKIP` with the
reason, and `FAIL` is reserved for a half that never once reached the width —
which no sampling interval could have missed. Measured, and the reason it
mattered: run C's lanes had live terminal sessions for about 70 seconds, and
the default interval was 45. It is now 15.

---

## Infrastructure

Five containers were launched. Five are gone.

```
turnkey-20260904T035511Z gone   turnkey-20260904T042036Z gone
turnkey-20260904T040824Z gone   turnkey-20260904T043038Z gone
turnkey-20260904T041055Z gone
```

The two runs that mattered (E and F) ran without `--keep` and destroyed their
own container in a `finally` block, which is the normal path. The three kept
ones were destroyed by hand. Run F's ledger row is left open for the
workspace's own sweep rather than hand-edited — that file documents itself as
having exactly one writer — and its registered reclaim command exits 0 today,
so the sweep will close it cleanly whenever it next runs.

No Gitea instance was stood up. The existing shared mirror was re-synced
(delete-and-recreate: `mirror-from-github` answers 409 on an existing repo and
the CLI has no update verb) and left running, because other evaluations use it.
Tearing down a shared instance this lane did not create would be the wrong kind
of tidy.

---

## The work list this run produces

| # | Finding | Where it belongs |
|---|---|---|
| 1 | A manager session dropped the **Time away** part of its brief, folding its content into *Finished*. `context/manager/return-brief.md` says "The five parts, **in this order**". Run C and runs E–F wrote all five; run D wrote four. Real variance, not incapacity. | the mode's clause 10 — see below |
| 2 | `write_file`/`edit_file` refused paths under the batch directory, so the manager wrote lane goal files with `bash` heredocs. Reported by the manager itself, unprompted, in *anything quietly broken*. | the allowed-write-paths default for a session whose batch dir sits outside its repository |
| 3 | The queue in a container is unmanaged: it answers, but nothing restarts it after a reboot. The install check now says so out loud instead of calling it missing. | the profile, if a managed unit is ever wanted there |

**Why #1 was not fixed here, though the mode is in this lane's ownership.** The
container installs the bundle from the mirror of `origin/main`. An edit to
`modes/converge-manager.md` on this branch does not exist inside the container
and cannot be exercised by this harness until it lands on main and the mirror
re-syncs. Shipping a behavioural edit this run could not observe would be a
claim with no check behind it, which is the one move that makes a green report
worthless. It is filed instead, with the evidence: run D's brief, whose
*Finished* paragraph reads "Two lanes, one wave, about five minutes wall clock
end to end" and which has no **Time away** heading at all.

**Deliberately not done:** widening the brief check to accept that folded form.
The convention names five parts in an order, three of four briefs produced them,
and a rule tuned until the run passes measures nothing. An over-strict rule
fabricates a failure exactly as badly as a loose one fabricates a pass — and the
three harness defects above were all the first kind.

---

## Amendment, 2026-09-04 — step (i) now reads one entry, not the whole file

**What was wrong.** Step (i) lowercased the whole return log and asked whether
each of the five words appeared anywhere in it. Dates and sentence counts were
file-wide too. So any prose satisfied it: a header, a footnote, or an unrelated
paragraph made the step green with no brief in the file at all. It also could
not see an unbriefed return, which is the whole of what clause 10 asks —
*a brief on every return*.

**What it does now.** The log is split into entries at each dated heading.
Everything before the first one is the file's own header and belongs to no
entry. Within an entry, a part counts only when a line *opens* with its label —
the labelled form `modes/converge-manager.md` clause 10 requires
(`**Time away.** …`), a list item carrying it, or the bare label closed by its
punctuation. The verdict rests on the newest entry, which is the return this run
produced. Beside it the step reports two numbers that can now be compared:
stamped returns (`## <date> <HH:MM> — …`) and complete briefs. A stamped return
with a part missing under it fails and names the part.

**Measured, both readings over the same logs.** The old `step_brief` was
restored from git into a temp tree (`git show HEAD:evaluations/turnkey/run.py`)
and run beside the new one:

```
| log under test                                                  | before | after |
|-----------------------------------------------------------------|--------|-------|
| a header alone, no entry at all                                 |  PASS  | FAIL  |
| the five words spread across five entries, none of them a brief |  PASS  | FAIL  |
| one stamped return, all five parts                              |  FAIL  | PASS  |
| one stamped return, Stuck folded away                           |  FAIL  | FAIL  |
| two stamped returns, the second never briefed                   |  FAIL  | FAIL  |
| this repository's own log, as it stands                         |  FAIL  | FAIL  |
```

The first two rows are the falsifier the work item named, and it was real. On a
header with no entry under it at all, the old check said, verbatim:

```
[PASS] A dated return brief is at .../OWNER-RETURN-LOG.md with all five parts
       and 3 plain sentences.
       parts_present: ['time away','finished','stuck','needs you','quietly broken']
```

Row 3 is the second half of the same defect, and it is the kind that fabricates
a red. A brief written exactly as clause 10 now mandates — five sentences, each
opening with its bold label — scored **0 plain sentences** under the old rule,
because that rule discarded every line beginning with `*`. The step would have
failed the one form the mode requires. Sentence counting now strips a leading
list or emphasis marker instead of disqualifying the line behind it.

What the new readings say, in the step's own words:

```
[FAIL] a header alone: The log has no dated entry, so no return has been briefed
       in it. The file's own header is not a brief, whatever words it carries.
       entries=0 stamped_returns=0 complete_briefs=0
[FAIL] Stuck folded away: 1 of 1 stamped return(s) carry no complete brief.
       '2026-09-04 04:01 - the gate went green' is missing 1 of the five parts: stuck.
       entries=1 stamped_returns=1 complete_briefs=0
[FAIL] the second return never briefed: 1 of 2 stamped return(s) carry no complete
       brief. '2026-09-04 09:30 - they came back again' is missing 5 of the five
       parts: time away, finished, stuck, needs you, quietly broken.
       entries=2 stamped_returns=2 complete_briefs=1
[PASS] one stamped return, all five parts: The newest entry carries all five parts
       and 5 plain sentences; 1 stamped return(s) in the log and 1 complete brief(s).
```

**This repository's own log still reads red, and now for the right reason.**
Nine entries, `stamped_returns=0`, `complete_briefs=0`: the nine briefs predate
the stamp and are written as single paragraphs, so no entry carries the five
labelled parts. Before, it read red because two of the five words happened not
to appear anywhere in the file while nine well-written briefs said "nothing
stopped" in their own words. Same colour, exact reason. The check was not tuned
until the repository passed.

**Not re-run in a container.** This is a change to how one step judges text it
is handed, so it is proven where it can be proven exactly: 16 self-test cases,
five of them one per part. Fifteen of the sixteen fail against the pre-fix
`run.py` in a control tree (15 failed, 57 passed); the sixteenth — a missing log
file is a failure — is the one behaviour that did not change. A driven run
would now hold a fixture manager session to the labelled form its mode already
requires; that has not been observed yet and is not claimed here.

```
$ uv run --with pytest pytest evaluations/turnkey -q
........................................................................ [100%]
72 passed in 0.25s

$ uv run evaluations/turnkey/run.py --self-check
verdict: PASS | passed: 29 | failed: []
   True a header carrying the five words is not an entry, so not a brief
   True one entry with all five parts is a brief, and a stamped return
   True a stamped return missing one part names that part
   True the five words spread across separate entries do not combine
   True an unprompted brief keeps a date-only heading and is not a return
```

Five of those cases are new: the environment-free self-check carries the same
two named failures as the pytest suite, so `--self-check` alone still proves
this step can go red. It stood at 24 cases and 57 tests when this file recorded
the green run above; it is 29 and 72 now.

**Handoff, not done here.** `ledger/rows.yaml` CVG-020 records that "nothing
counts returns", so a brief count has no denominator. Step (i) now produces that
denominator — `stamped_returns` and `complete_briefs`, in its evidence, on every
run. Repointing the row is `converge-4xg`'s job and the ledger is not this
lane's to edit. The same row's note still cites the self-check as "16 of 16",
which was already stale before this change and is now 29.
