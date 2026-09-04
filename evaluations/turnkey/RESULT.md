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

Caught the same way, before it could fabricate a red of its own:
`context/manager/return-brief.md` (as it stands on `main` after
`lane/w8-brief-convention`) prints the five parts as a **numbered** list —
`1. **Time away.** …` — so a manager copying the shape it was shown writes
numbered items. The first draft of this check accepted `-`, `*`, `+` and `>` as
list markers and would have found none of the five. It accepts `1.` and `1)`
now, and a parametrized test runs the whole brief through four markers.

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
is handed, so it is proven where it can be proven exactly: 19 self-test cases,
five of them one per part. Eighteen of the nineteen fail against the pre-fix
`run.py` in a control tree (18 failed, 57 passed); the nineteenth — a missing
log file is a failure — is the one behaviour that did not change. A driven run
would now hold a fixture manager session to the labelled form its mode already
requires; that has not been observed yet and is not claimed here.

```
$ uv run --with pytest pytest evaluations/turnkey -q
........................................................................ [100%]
75 passed in 0.18s

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
the green run above; it is 29 and 75 now.

**Handoff, not done here.** `ledger/rows.yaml` CVG-020 records that "nothing
counts returns", so a brief count has no denominator. Step (i) now produces that
denominator — `stamped_returns` and `complete_briefs`, in its evidence, on every
run. Repointing the row is `converge-4xg`'s job and the ledger is not this
lane's to edit. The same row's note still cites the self-check as "16 of 16",
which was already stale before this change and is now 29.

---

# Two more steps — the clauses the sentence does not reach — 2026-09-04

**Verdict: the clause readings are PASS, 2·0·0, and four of the ten clauses now
carry a live reading of what a manager session did.** The other six say what
they are still waiting on, in words, and none of them says PASS.

`contracts/operation.v1.md` has thirteen Core clauses. The turnkey sentence
above runs nine steps, and between them they reach three of the thirteen —
clause 1 (work is derived), clause 5 (lanes are real sessions) and clause 10
(a brief on every return). The ledger's probes for the other ten all read the
same thing: whether `modes/converge-manager.md` still carries the clause's own
section heading. That proves the rule was written down. It says nothing about
whether any manager session followed it, and both `converge-2ro` and
`converge-6mi` were filed to say so.

Two steps now read what a wave actually left behind.

```
$ uv run evaluations/turnkey/run.py --env local \
      --workspace ~/dev/hw-converge --project converge --steps e,f,g,h,i,j,k

[PASS] (j) clauses: 4 of 7 clauses carry a live reading of what a manager session did,
           and 3 name the observation they still wait on. Core 2 (CVG-012) PASS: 4 lane
           brief(s) each declare the paths that lane owns, and the plan record at
           /home/bkrabach/dev/hw-converge/HIGHWAY.md gives reasons for 11 of its 35
           dated decisions · Core 3 (CVG-013) SKIP: this run can see that work was
           parked on the steward's word and that other lanes kept running (5 plan
           entries record a park), which is the clause's shape but not its promise ·
           Core 4 (CVG-014) PASS: 1 item(s) filed from feedback quote the report and
           name the version it was said about (converge-f5f); 1 triage(s) name no item
           and are unresolved, not passed · Core 6 (CVG-016) PASS: 4 lanes ran at once,
           each brief declares paths that collide with no other lane's, and the actual
           half is unmeasured: only 1 of them has commits yet, and two empty branches
           share no file by not having one · Core 9 (CVG-019) SKIP: no lane ended
           without commits, so no stall exists for this reading to judge — the reading
           ran and found nothing · Core 11 (CVG-021) SKIP: nothing in this run reads a
           prompt as an event, so the four calls cannot be counted or classified · Core
           13 (CVG-023) PASS: each of 2 recorded close(s) names what remained —
           residuals, what was parked, or what was still live — so a fresh session could
           pick the run up from the record alone

[PASS] (k) attribution: 1 of 3 clauses carry a reading of who produced the artifact, not
           only that it exists. Core 7 (CVG-017) SKIP: step (f) PASS: a marker on an
           unchanged branch is recorded stuck; and on the subject of the sentence — the
           newest record of a check run (ledger/rows.yaml at 36bd6572) came in through a
           lane merge, so this wave's verification is unattributed here; the integrator
           has written 6 such record(s) before, most recently 2921181e ('ledger:
           operation.v1 SYNC + quote follow the line-77 repair') · Core 8 (CVG-018)
           SKIP: step (g) PASS: two or more lanes landed in one repository; step (h)
           PASS: the contract check was re-run after integration — by this harness,
           which is the post-merge gate and not the manager session; and on whose
           verification it was — the newest record of a check run (ledger/rows.yaml at
           36bd6572) came in through a lane merge, so this wave's verification is
           unattributed here; the integrator has written 6 such record(s) before, most
           recently 2921181e ('ledger: operation.v1 SYNC + quote follow the line-77
           repair') · Core 12 (CVG-022) PASS: all 79 resolution(s) in the queue are
           written in sentences that answer the asker rather than pointing at a commit

  VERDICT: FAIL  (pass=5 fail=2 skip=0)
  the turnkey sentence (a-i): FAIL 3·2·0   ·   the clause readings (j-k): PASS 2·0·0
```

**Only (j) and (k) are pasted in that block, and that is deliberate.**
`ledger/checks/turnkey_step.py` keys a row on the newest `[STATUS] (letter)`
line in this file. Pasting an observed run's steps (a)–(i) here would silently
re-point CVG-011 and CVG-015 away from the green driven run they were derived
from and onto this host's workspace — a ledger row moved by an editing
decision rather than by a measurement. The two red steps of the same run are
quoted in prose further down instead.

**Observed, on this host's own wave — not driven.** The readings above are of
the W8 wave running in `~/dev/hw-converge` on 2026-09-04: seven lanes launched,
four still live at read time, forty lane branches merged into main. Nothing was
stood up for it and nothing was torn down; a driven run would answer the same
questions about a fixture wave instead.

## What each live reading actually read

**Core 2 — the plan is visible.** Two artifacts, both written by the manager
session before this harness looked: every lane brief in `goals/` carries a
`File ownership — edit ONLY:` line naming the paths that lane owns, and
`HIGHWAY.md` carries dated entries that give the REASON for a width or a
refill — "No refill: every ready item collides with a live lane", "Under-width
by 1 justified: no ready work". A brief with no ownership split fails this; so
does a plan record whose entries only announce what happened. The ownership
line is read to the first sentence break, because the same line names the OTHER
lanes' paths for context and reading the whole line would hand every lane its
neighbours' paths and manufacture a collision in every pair.

**Core 4 — feedback is signal.** The raw report and its filing, side by side.
`HIGHWAY.md` records "steward feedback on the app (Changes view) triaged →
converge-f5f"; the item itself carries "Source — the steward's feedback on the
running app at http://spark-1:8788 (build b7ed3f0, 2026-09-03), quoted: 'The
diff is misaligned …'". Quoted evidence, and the version it was said about. A
triage that names no item id is recorded unresolved and is not a pass.

**Core 6 — width is a collision decision.** The lanes running at the same time,
from the multiplexer's own session list, judged twice: their briefs' declared
paths must not collide, and the files their commits actually changed must not
overlap. On this run four lanes were live and only one had commits yet, so the
second half is reported unmeasured rather than passed — two empty branches
share no file by not having one.

**Core 13 — hand off when done.** Every close recorded in the plan record names
what REMAINED, not only what finished: "Residuals: CVG-051/CVG-020 verify
expectations (pre-existing, honest); gitea mirror needs one push …". A close
that lists only what landed fails this, because a fresh session has nothing to
resume from.

**Core 12 — the resolution was written for whoever asked.** All 79 resolutions
in the queue are written in sentences that answer a person. The queue stores a
string and judges nothing about it, so "done", a bare sha, or an empty
resolution all look closed from every angle; each of those fails here.

## What the six SKIPs are waiting on

| Clause | Row | Waiting on |
|---|---|---|
| Core 3 · never the bottleneck | CVG-013 | a count of the items parked on the steward's word, taken at each park, beside the work that continued — the maximisation is a comparison against work that COULD have proceeded, and nothing stores a park event |
| Core 9 · stalls are decisions | CVG-019 | a lane that ends with an unchanged branch. The reading ran; no lane on this host ended with nothing on its branch, so there was no stall to have been declared |
| Core 11 · four calls reach the steward | CVG-021 | the manager session's owner-facing prompt events, classified into the four. `evaluations/ratchet` counts exactly these — for the reconciler, not for a manager session |
| Core 7 · the manager session re-ran the check | CVG-017 | a check-run record written outside every lane after the newest lane merge, or a reading taken while the check runs of the process running it |
| Core 8 · integrate, verify, re-check | CVG-018 | the same attribution. Its other two parts ARE measured here: step (g) PASS, step (h) PASS |

Clause 9's SKIP and clause 11's SKIP are different animals and the report says
so. Clause 9's reading ran and found nothing to judge; clause 11 has no reading
at all yet. Neither is a pass.

## The attribution, and why it is a SKIP rather than a FAIL

Clause 7's subject is "the MANAGER SESSION re-ran the check" and clause 8's is
"the manager session's own verification, never the worker session's". An
artifact does not record which process made it — but git records which side of
a merge a commit arrived on, and that is enough to tell a lane's own green from
the integrator's.

A lane commits on its own branch, so its work reaches the integration branch
only as the second parent of a `merge lane/…` commit. `M^1..M^2` is exactly the
set that merge carried in; a commit outside every such set was made by whoever
was integrating. The obvious cheaper test — "is it on the first-parent line?" —
is wrong here and was measured wrong: lanes merge onto an integration branch
which reaches main through a pull-request merge, so main's first-parent line is
almost entirely PR merges and the integrator's own commits sit off it.

On this run the newest check-run record (`ledger/rows.yaml` at `36bd6572`) came
in through `merge lane/w8-ledger-followups`, and the integrator has written six
such records before it, most recently `2921181` ("ledger: operation.v1 SYNC +
quote follow the line-77 repair"). That is a SKIP and deliberately not a FAIL:
an integrator who re-ran the check after the last merge and wrote nothing down
leaves exactly this trace, and calling it broken would be a fabricated red of
the kind run C produced three of. A repository where NO check record was ever
written outside a lane does fail, and the self-check proves it.

## The two red steps above are this host's, not these steps'

The same command reports `[FAIL] (e)` — one queue item of forty
(`converge-791`) names no contract and states no done — and `[FAIL] (i)` — the
newest return-log entry is a single paragraph with none of the five labelled
parts. Both are pre-existing readings of this workspace that step (e) and step
(i) have made since before this change; neither is caused by, or judged by, the
new steps. They are named here because a run that prints two reds and does not
say what they are is a run nobody can check. Lanes `w8-return-brief` and
`w8-brief-convention` hold the brief convention; `converge-791` is the queue's.

## What has NOT been run: these two steps in a container

The readings above are observed, on this host. **Steps (j) and (k) have never
run in a driven container**, and nothing here claims they have. Two things
follow, and both are stated rather than discovered later:

- The default `--steps` runs everything, so the next `run.sh` will carry them
  into a fixture wave. On a workspace where nothing is readable they all come
  back SKIP — proven without a container by a test that stands the steps up
  against an environment answering nothing, and asserts every clause is a SKIP
  with a reason and the step itself a SKIP with one.
- Where something IS readable and the promise is broken — a fixture manager
  that writes lane briefs with no ownership split, say — (j) will report FAIL
  and the run's exit code will follow it. That is a true reading of that wave
  and the conformance list's own asserts ("lanes are filled only with disjoint
  items", "no raw feedback becomes work without a quoted source", "a stall is
  declared stuck … a hand-off exists"), not a new gate invented here. It has
  simply never been exercised in a container, and the first driven run may
  report a red the nine steps do not.

## For the reconciler: what these steps let a row re-derive

`ledger/` is not this lane's to edit. What the rows would need is written out
in the work items and repeated here: the readings are addressable exactly the
way CVG-015 already addresses step (f), through
`ledger/checks/turnkey_step.py`, which reads this file.

One residual, and it is one character: that helper's `STEP` regex accepts step
letters `[a-i]`, so it cannot see `(j)` or `(k)` yet. Until it accepts `[a-k]`,
a row keyed on a clause reading reports `CHANGED-REREAD-THIS-ROW`. The step
lines above are written in exactly the form it parses, so the change is the
regex and nothing else. Measured both ways, against this file:

```
$ python3 ledger/checks/turnkey_step.py j "Core 6 (CVG-016) PASS"
TURNKEY-STEP-J-CHANGED-REREAD-THIS-ROW: no step (j) is recorded in evaluations/turnkey/RESULT.md

$ sed 's/\[a-i\]/[a-k]/' ledger/checks/turnkey_step.py > /tmp/turnkey_step_ak.py
$ python3 /tmp/turnkey_step_ak.py j "Core 6 (CVG-016) PASS"
TURNKEY-STEP-J-PASS-ASSERTS-THIS
$ python3 /tmp/turnkey_step_ak.py k "Core 12 (CVG-022) PASS"
TURNKEY-STEP-K-PASS-ASSERTS-THIS
$ python3 ledger/checks/turnkey_step.py f "no work item was held by a process outside a lane worktree"
TURNKEY-STEP-F-PASS-ASSERTS-THIS
```

The last line is the check that this file's new section moved nothing: CVG-015
still reads the green driven run's step (f), not this host's.

That residual and the ten rows it unblocks are filed as **`converge-saz`**,
which names each row, the phrase it would pin, and what the reading does not
prove.

```
$ uv run --with pytest pytest evaluations/turnkey -q
115 passed in 0.14s

$ uv run evaluations/turnkey/run.py --self-check
verdict: PASS | passed: 55 | failed: []
```

Seven new assertions, twenty-six new self-check cases, forty new tests. Every
assertion is exercised against evidence that must make it fail: two lanes given
the same path, a plan record that only announces, a stall nobody named, a
feedback item with no quoted source, a close that lists only what finished, a
resolution reading "Fixed in abc1234.", and a repository whose check records
were only ever written inside a lane.

## Amendment, 2026-09-04 — two conventions, and the three readings they unblock

Three of the clause readings above were not waiting on a cleverer parser. They
were waiting on something nobody had written down, so no parser could ever find
it: **what continued while work was parked on the steward's word** (Core 3),
**which of the four calls a call was** (Core 11), and **who re-ran the check
after integration** (Core 7 and Core 8).

Two small conventions supply exactly those three facts and nothing else. Both
live where a manager session reads them, not in this harness:

| Convention | Where | What it makes readable |
|---|---|---|
| **The call stamp** — `CALL <one of four> - <what is asked>. Parked: <items>. Continued: <what kept moving>.`, one line in the plan record, at the moment of the call | `modes/converge-manager.md` clauses 3 and 11; `context/manager/wave-record.md` | Core 3 · Core 11 |
| **The check record** — one entry per integration in `docs/workflow/CHECK-RECORD.md`, naming the merges it covers, the command re-run, and what it printed, committed by the manager session itself on the integration branch | `modes/converge-manager.md` clause 8; `docs/workflow/CHECK-RECORD.md` carries its own shape | Core 7 · Core 8 |

Neither convention invents a duty. Clause 3 already says what needs the
steward's word is parked and everything else continues; clause 8 already says
the verification is the manager session's own. What was missing was any trace of
either, afterwards, for somebody who was not in the session.

### Core 3 now carries a live reading of this host, and it did not need a new habit

Read on this host on 2026-09-04, against the W8 wave in `~/dev/hw-converge`:

> **Core 3 (CVG-013) PASS:** 3 of 4 recorded park(s) name what kept moving beside
> them (read from the entry's own `Live:` list; fewest at any one park: 1) — the
> wave did not go idle on the steward's word, which is what this reading can say
> and not that nothing more could have proceeded.

The reading accepts the stamp **and** the looser form this workspace's manager
sessions have been writing all along: a cycle entry saying `Parked:
protocol-terms (steward ratify card)` beside `Live: guard-3,
renumber-followup` records the same two facts at the same moment, and the
reading names which form answered it. A convention that could only read its own
stamp would have had nothing to say about eight months of waves that are sitting
right there.

**What it does not prove.** That nothing MORE could have proceeded. Nothing on
disk records the work that was available and not launched, so this says the wave
did not go idle on the steward's word, and no more than that. Its falsity
condition is a park entry naming nothing continuing and giving no reason for it;
`Continued: none, because no ready item fails to collide with it` is a different
fact and is not failed.

One measurement worth keeping: the previous reading counted **five** parks in
this plan record where four are real. The fifth was `http://spark-1:8788` — this
host's own name, matched by a `park` with no word boundary on it.

### Core 11 is still waiting, but now on something a manager session can write

> **Core 11 (CVG-021) SKIP:** 2 of 4 recorded call(s) name which of the four they
> are (ratify: 2); the other 2 name none, so this run cannot say the calls that
> reached the steward were the four.

That is a better sentence than the one it replaces — "nothing in this run reads
a prompt as an event" — because the observation it now awaits is one line in a
file a manager session already writes every cycle.

The classification is deliberately narrow. A stamped `CALL <word>` is read
wherever it sits in the entry; failing that, the loose form is read from the
**park's own sentence and nowhere else**. Read from the whole entry, a cycle
that merged a guard fix mentioning `RATIFIED = locked` and separately parked
something unrelated came back classified as a ratify call — measured on this
plan record, and a classification nobody wrote and nobody could defend. A call
stamped as something that is none of the four is a FAIL, because that is the
defect clause 11 names.

### Core 7 and Core 8: the attribution, answered on a repository built to answer it

The SKIP those two carried was precise and unfixable by reading harder: the
newest record of a check run came in through a lane merge, because both files a
check run used to leave a trace in — `ledger/rows.yaml` and this file — are
edited by lanes. The check record removes the confound at the source, and the
question becomes readable.

Taken on a purpose-built repository — a real `git init`, a real lane branch, a
real `merge lane/one: wave 8`, then an integration commit — with the check
record's newest entry written by **the integrator**:

> **Core 7 (CVG-017) PASS:** step (f) PASS: a marker on an unchanged branch is
> recorded stuck; and on the subject of the sentence — the newest entry in
> docs/workflow/CHECK-RECORD.md (2026-09-04 12:40 — 'wave 8, two lanes merged')
> was added by e19b170c ('check record: wave 8 re-checked after merge'), which is
> on neither side of any lane merge, so it was the manager session's own hand and
> not a lane's; it names the check it ran ('uv run --with pyyaml
> ledger/checks/verify.py -> all pass'). What this does not prove is that the run
> behind it was clean or that it covered every merge — step (h) re-runs the check
> itself and answers that.

Core 8 (CVG-018) carries the same verdict, with its own two measured halves in
front of it (step (g) PASS, step (h) PASS).

The same repository, with one thing changed — the entry appended on the lane
branch instead, so it arrives through the merge:

> **Core 8 (CVG-018) FAIL:** … the newest entry in docs/workflow/CHECK-RECORD.md
> (2026-09-04 12:40) was added by 9d798da1, which reached this branch as the
> second parent of 58727230 ('merge lane/one: wave 8') — a worker session wrote
> the record of the manager session's own verification, which is the half of
> clause 8 that says never the worker session's.

**What this observation does NOT prove.** It is a fixture, not this host. It
proves the reading answers correctly, in both directions, on a repository shaped
the way the convention prescribes — the harness's usual bargain. It says nothing
about whether any manager session on this host has yet written an entry, and the
observed reading below says plainly that none has. Reproduce both with:

```
uv run --with pytest pytest evaluations/turnkey/tests/test_turnkey.py -q \
    -k "check_record or clause"
```

On this host, today, the same step says so in its own words:

> **Core 7 (CVG-017) SKIP:** … the newest record of a check run
> (ledger/rows.yaml at 84e2a39a) came in through a lane merge, so this wave's
> verification is unattributed here; the integrator has written 7 such record(s)
> before, most recently a5ffbf35 — and the record the manager session writes
> itself (docs/workflow/CHECK-RECORD.md) is not in this repository yet.
> *Awaits:* the docs/workflow/CHECK-RECORD.md convention, and the first entry a
> manager session writes into it after integrating a wave.

That awaited observation lands the first time a manager session integrates a
wave after this lane merges. It is one commit, and it is the manager session's
to make.

### What is still waiting, and what each one needs now

| Clause | Row | Waiting on |
|---|---|---|
| Core 9 · stalls are decisions | CVG-019 | a lane that ends with an unchanged branch. Unchanged by this lane: the reading ran and found nothing to judge, which is the honest answer and not a pass. A deliberately stalled fixture wave is the cheapest route |
| Core 11 · four calls reach the steward | CVG-021 | every recorded call naming which of the four it is. Two of four already do; the convention makes the rest one line each |
| Core 7 · the manager session re-ran the check | CVG-017 | on this host: the first `docs/workflow/CHECK-RECORD.md` entry. On a fixture: answered above, both ways |
| Core 8 · integrate, verify, re-check | CVG-018 | the same |

### Why the machine-readable step block above was NOT re-pasted

`ledger/checks/turnkey_step.py` keys a row on the **newest** `[STATUS] (letter)`
line in this file, and four ledger rows currently pin the OLD readings —
`"Core 3 (CVG-013) SKIP"`, `"Core 11 (CVG-021) SKIP"`, `"Core 7 (CVG-017) SKIP"`,
`"Core 8 (CVG-018) SKIP"`. Pasting this run's `(j)`/`(k)` block here would flip
all four to `CHANGED-REREAD-THIS-ROW` and take `uv run --with pyyaml
ledger/checks/verify.py` red on `main`, because that script runs every row's ref
and holds it to its `expect`.

That is drift detection working exactly as designed — the readings genuinely
changed — but `ledger/**` belongs to another lane, and a red `main` is not this
lane's to leave behind. So the verdicts above are quoted in prose, which
`turnkey_step.py` does not read, and the re-derivation is filed as work. The
four rows and the phrases they should pin instead are named in it.

```
$ uv run --with pytest --with pyyaml pytest evaluations/turnkey -q
136 passed

$ uv run evaluations/turnkey/run.py --self-check
verdict: PASS | passed: 71 | failed: []
```

Sixteen new self-check cases and twenty-one new tests. Every new assertion is
exercised against evidence that must make it fail: a park with nothing
continuing and no reason, a call stamped as none of the four, a check-record
entry that arrived through a lane merge, an entry naming no command at all, and
a typo fix three entries up that must not be credited with writing the newest
one.

## Amendment, 2026-09-04 — Core 9 finally had a stall to judge, and could not tell one from a mention

Clause 9's reading was never waiting on a cleverer parser either. It was waiting
on an **event**. Every wave on this host produced commits, so the reading ran,
found nothing, and said so — the honest answer, and not a pass:

> **Core 9 (CVG-019) SKIP:** no lane ended without commits, so no stall exists
> for this reading to judge — the reading ran and found nothing.

`evaluations/turnkey/fixtures/stall_wave.py` seeds the missing event: a wave, in
observed mode, in which one lane really did stop with an unchanged branch and a
second one did not. Both lanes are real worktrees on real branches with a real
launcher manifest; neither has a live terminal session, because a stall is a
lane that has stopped. Git, not this file, is what says so:

```
$ uv run evaluations/turnkey/fixtures/stall_wave.py /tmp/stall-shown
stalled_lane	lumen-index
stalled_branch	lane/lumen-index
stalled_commits	0
moved_lane	lumen-units
moved_commits	1

$ git -C /tmp/stall-shown/repo worktree list
/tmp/stall-shown/repo                    cbe7d95 [main]
/tmp/stall-shown/lanes/lumen-index/repo  cbe7d95 [lane/lumen-index]
/tmp/stall-shown/lanes/lumen-units/repo  3f1ec59 [lane/lumen-units]
```

### The first run of it found a fabricated pass

Two variants, differing by **one plan-record entry** — one where the plan record
declares the stall, one where nothing about it is written down at all. **Both
came back PASS.**

The reading asked only whether some record *named* the stalled lane. In the
hidden variant the entry that **launched** the lane, three lines up, named it.
So does every refill line this workspace's own plan record writes — cycle 32's
entry names `stall-fixture` for exactly that reason. A reading whose two
outcomes are indistinguishable is not a reading, and this is the second time
this harness has caught itself producing a green line nobody could back up.

The fix is `STALL_DECLARED` in `run.py`: a record declares a stall only if it
says the lane **stopped**, **in the same sentence as the lane's name** — so an
entry naming lane A while reporting lane B stuck can never vouch for A.

### The reading now, both ways, on a real stalled lane

Run as `uv run evaluations/turnkey/run.py --env local --steps j --repo
<root>/repo --workspace <root>`, against the two variants:

> **Core 9 (CVG-019) PASS:** 1 lane(s) stopped with an unchanged branch and each
> is named in a record that says it stopped — lumen-index: `'cycle 2:
> lumen-index is stuck and is not being relaunched.'`; this reads that the stop
> was written down, not whether the cause it gives is the real one.
>
> — step (j) itself PASS, run exit 0.

> **Core 9 (CVG-019) FAIL:** 1 lane(s) stopped with an unchanged branch and were
> not declared stuck: lumen-index — named, but no record says the lane stopped;
> the newest one naming lumen-index reads `"cycle 1: launched lumen-units and
> lumen-index at width 2, because the fixture's two gaps are in files that do
> not touch and neither lane's paths collide with th"`, which is a mention and
> not a declaration.
>
> — step (j) itself FAIL, run exit 1.

Both readings name the lane, and both name the record that does or does not say
what stopped it. The control held: `lumen-units` ended with its session gone
too, carries one commit, and is not counted as a stall in either variant —
`stalled_lanes` is `[lumen-index]` both times. A reading that called every ended
lane a stall would go red on every wave that finished, which is the opposite
fabrication and just as false.

### What this does NOT prove

- **Not** that the cause a record gives is the real one, or an adequate one.
  The reading shows the words it found; a reader judges them.
- **Not** that the lane had not already been retried before it was declared.
  Clause 9's "across iterations" needs a count of attempts, and nothing on disk
  here records one. A record that declares the stop and then relaunches in place
  reads as declared, which is the honest limit of an artifact left on disk.
- **Not** that a manager session on this host would declare a stall. This is a
  fixture, not this host's own wave — the same standing this file already gives
  the clause 7 and 8 attribution. This host's habit is a separate observation,
  and it lands the first time a real lane here ends with an unchanged branch.

### Calibration: the stricter rule does not fabricate a red

Requiring the stop word is only worth having if it leaves the declarations a
manager session here already writes standing. Both real ones in
`~/dev/hw-converge/HIGHWAY.md` still read as declarations, and
`test_the_declarations_this_workspace_actually_writes_still_read` holds them
there:

```
w8-ledger-refs relaunched: first attempt hung at the provider-setup prompt.
w6-guard-3 died silently mid-work (0 commits, no markers, logs end mid-thought).
```

The second is lightly edited: the original says "both w6 lanes died", which
names no lane at all, and under this reading that is a FAIL — correctly, because
a lane a record does not name is a lane it cannot be said to be about.

### For the reconciler: CVG-019, and why this file carries no new step block

`ledger/` is not this lane's to edit, and CVG-019's ref currently pins
`"Core 9 (CVG-019) SKIP"` in this file's newest step block. That pin is now the
wrong one: the reading has an event and answers in both directions.

**The step block above was deliberately NOT re-pasted**, for the reason the
previous amendment records — `ledger/checks/turnkey_step.py` keys a row on the
newest `[STATUS] (letter)` line in this file, so pasting one would flip CVG-019
to `CHANGED-REREAD-THIS-ROW`. CVG-019 still routes through that file-reading
helper, not through `ledger/checks/turnkey_clause.py`, which landed on `main`
the same day for the four rows that had moved. Measured on this tree, and
unchanged by this lane:

```
$ python3 ledger/checks/turnkey_step.py j "Core 9 (CVG-019) SKIP"
TURNKEY-STEP-J-PASS-ASSERTS-THIS
$ python3 ledger/checks/turnkey_step.py f "no work item was held by a process outside a lane worktree"
TURNKEY-STEP-F-PASS-ASSERTS-THIS
```

**`verify.py` does not exit 0 on this tree, and it did not before this lane
either.** Saying otherwise would be exactly the unchecked green this file
exists to refuse, so here is the measurement — the whole report, taken with
this lane's changes stashed and again with them applied:

```
$ git stash -u && uv run --with pyyaml ledger/checks/verify.py; echo "exit=$?"
exit=1
$ git stash pop && uv run --with pyyaml ledger/checks/verify.py; echo "exit=$?"
exit=1
$ diff <report before> <report after>
  (no differences)

FAILURES (identical in both):
  - no GAP/VIOLATION row cites a resolved work item (39 red rows read
    against docs/work-items.json)   [35 rows named, e.g. CVG-163 -> converge-tfu]
  - CVG-051 expect NOT met (stdout='WORK-ITEM-CHECK-NOW-RUNS-FAIL-ITEMS=12')
```

Byte-identical reports either side of this lane's diff is the whole claim: both
failures live in `ledger/**`, both predate this work, and this lane neither
caused nor can clear them — `ledger/` is not this lane's to edit. That is a
residual, named here rather than discovered later.

What CVG-019 should pin instead, and what the reading does not prove, is filed
as **`converge-rp7`**, which quotes both new readings and names the three things
a pass on this fixture does not prove. The row's disposition can move on this
fixture only as far as the fixture goes: the reading is exercised, and this
host's own manager sessions are still unobserved on it. This supersedes the
*What is still waiting* row above,
which said CVG-019 waits on "a lane that ends with an unchanged branch" — it has
one now, on a fixture, and what it still waits on is this host's own.

```
$ uv run --with pytest --with pyyaml pytest evaluations/turnkey -q
147 passed

$ uv run evaluations/turnkey/run.py --self-check
verdict: PASS | passed: 74 | failed: []
```

Three new self-check cases and eleven new tests. The new ones are exercised
against evidence that must make them fail: a stall whose only record is the
entry that launched it, a stall whose only record is the refill line that filled
its slot, a stall word written about a different lane in the same entry, and a
seeded wave whose stalled branch must carry zero commits or the fixture refuses
to stand.
