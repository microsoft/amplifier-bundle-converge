# The lumen gap fixture

A tiny repository with **two planted gaps, in two files that do not touch**.
It is the input the turnkey harness derives work from — the "sample gap" in
`operation.v1`'s turnkey sentence.

```
gap-repo/
  contracts/lumen.v1.md   one LOCKED contract, two Core clauses, two asserts
  src/readings.py         gap 1 lives here: panel_temperature names no unit
  src/report.py           two public entry points
  docs/INDEX.md           gap 2 lives here: render_summary is not named
  check.py                the repository's OWN conformance kit
answer-key.json           what the gaps are, who owns which file, what done means
seed.sh                   materialize gap-repo into a target dir as a git repo
```

## Why two gaps, and why in different files

`operation.v1` clause 6: **width is a collision decision.** Lanes fill only with
items that provably touch different files; adjacent items run as one lane.

So a fixture with one gap could never justify two lanes, and a fixture with two
gaps in the *same* file would have to run them as one. Two gaps in two files
that do not touch is the smallest fixture that makes "run two lanes" the correct
answer rather than an arbitrary one. `tests/test_turnkey.py` asserts that
disjointness, so the fixture cannot quietly drift into a colliding pair.

## The gaps

| Rule | Clause | Quote | Owns | Done means |
|---|---|---|---|---|
| 1 | 1 | "Every reading names its unit." | `src/readings.py` | `check.py` rule 1 reports PASS |
| 2 | 2 | "Every public entry point is named in the index." | `docs/INDEX.md` | `check.py` rule 2 reports PASS |

Both quotes appear verbatim in `contracts/lumen.v1.md`; a test asserts that too,
so the answer key cannot describe a contract the fixture does not have.

## Its own kit is red on purpose

```console
$ cd gap-repo && python3 check.py .
  [FAIL] 1 units: 1 reading(s) name no unit in src/readings.py: panel_temperature.
  [FAIL] 2 index: 1 public entry point(s) in src/report.py are absent from docs/INDEX.md: render_summary.
  VERDICT: FAIL (pass=0 fail=2 skip=0)
$ echo $?
1
```

A fixture that has quietly healed would let a turnkey run report success without
anything having been done. `test_the_fixture_is_red_before_any_work` and
`test_the_answer_key_matches_what_the_fixture_actually_says` exist to catch that.

## Seeding

```console
$ ./seed.sh /tmp/lumen
/tmp/lumen
0ebab226f9aac59368e72882707ac305c4742eaf
```

`seed.sh` refuses a non-empty target rather than mixing two working trees, and
`main` is the base every lane branches from. Non-zero exit with the reason on
stderr is what the harness records as the seeding step's evidence.

---

# The stall fixture

`stall_wave.py` seeds a **second** fixture, and it is not a repository with a
gap in it — it is a **wave that has already happened**, in which one lane
stopped without producing anything.

```console
$ uv run evaluations/turnkey/fixtures/stall_wave.py /tmp/stall-wave
root	/tmp/stall-wave
repo	/tmp/stall-wave/repo
stalled_lane	lumen-index
stalled_branch	lane/lumen-index
stalled_commits	0
moved_lane	lumen-units
moved_commits	1
declared	True

read it with:
  uv run evaluations/turnkey/run.py --env local --steps j \
      --repo /tmp/stall-wave/repo --workspace /tmp/stall-wave
```

## Why it exists

`operation.v1` clause 9 — **stalls are decisions, not loops** — is read by step
(j), and until 2026-09-04 that reading had never had anything to judge. Every
wave on this host finished, so the reading ran, found nothing, and said so:

> Core 9 (CVG-019) SKIP: no lane ended without commits, so no stall exists for
> this reading to judge — the reading ran and found nothing

That is the honest answer and not a pass. What was missing was the **event**, and
a gate that has only ever seen work move cannot say what happens when work stops.

## What it builds, and why every part is real

| | |
|---|---|
| `repo/` | a git repository, `main`, one base commit |
| `lanes/lumen-units/repo` | a real worktree on `lane/lumen-units`, **with** a commit |
| `lanes/lumen-index/repo` | a real worktree on `lane/lumen-index`, **with none** |
| `goals/*.md` | the brief each lane was given, each declaring the paths it owns |
| `manifest.tsv` | the launcher's own record of both lanes, with their base SHA and terminal-session names |
| `HIGHWAY.md` | the manager session's plan record |

Both lanes are real worktrees on real branches, because the stall is read out of
git and a *described* branch proves nothing about git. Neither lane has a live
terminal session, because a stall is a lane that has **stopped** — a lane still
running on an unchanged branch is working, and the reading deliberately refuses
to count it. The seeder checks both of `run.py`'s tmux sockets and refuses to
build at all if a session under either lane's name is live, rather than seeding a
fixture whose central fact is quietly false.

`lumen-units` is the **control**, not decoration: same wave, same manifest, same
absent session, one commit. The reading must leave it alone. A reading that
called every ended lane a stall would go red on every wave that finished.

## The discrimination

The two variants differ by **one plan-record entry** and nothing else — a test
asserts that byte for byte.

| | The plan record says | Step (j) reads | Exit |
|---|---|---|---|
| default | `lumen-index is stuck and is not being relaunched. Its worker session exited with an unchanged branch: …` | `Core 9 (CVG-019) PASS` | 0 |
| `--hidden` | nothing about it; the wave carries on | `Core 9 (CVG-019) FAIL` | 1 |

## What it caught on its first run

**Both variants passed.** The reading asked only whether some record *named* the
stalled lane — and in the hidden variant the entry that **launched** the lane,
three lines up, named it. So did every refill line. A reading that cannot go red
is the fabricated pass this harness exists to refuse, and this fixture is what
made it visible.

The fix is in `run.py`'s `STALL_DECLARED`: a record declares a stall only if it
says the lane **stopped**, in the **same sentence** as the lane's name — so one
entry naming lane A while reporting lane B stuck can never vouch for A. Both
real declarations in this workspace's own plan record still read as declarations
under the stricter rule, and `test_the_declarations_this_workspace_actually_writes_still_read`
holds them there.

## What a PASS here does not prove

- **Not** that the cause the record gives is the real one, or an adequate one.
  The reading shows the words it found and a reader judges them.
- **Not** that the lane had not already been retried. Clause 9's "across
  iterations" needs a count of attempts, and nothing on disk records one.
- **Not** that a manager session on this host would declare a stall. This is a
  fixture. It proves the reading answers, in both directions, when a stall is
  really there — which is the thing that had never been observed.
