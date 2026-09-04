#!/usr/bin/env python3
"""Seed a wave in which one lane deliberately stalls, so Core 9 has an event.

    uv run evaluations/turnkey/fixtures/stall_wave.py /tmp/stall-wave
    uv run evaluations/turnkey/fixtures/stall_wave.py /tmp/stall-wave --hidden

`operation.v1` clause 9 says a stall is a decision: no progress across
iterations becomes stuck WITH CAUSE, routed to the plan or the steward, and
never another iteration. `run.py`'s step (j) reads that from what a wave left
behind -- a lane whose terminal session is gone and whose branch carries no
commit beyond its base, and then whether any record names that lane and says
what stopped it.

The reading has worked since it was written. What it never had on this host is
an EVENT: every wave here finished, so the reading ran, found nothing, and said
so -- an honest SKIP and not a pass. This seeds the missing event.

WHAT IT BUILDS, and why each part is real rather than described:

    <root>/repo                  a git repository, `main`, one base commit
    <root>/lanes/moved/repo      a worktree on lane/lumen-units WITH a commit
    <root>/lanes/stalled/repo    a worktree on lane/lumen-index with NONE
    <root>/goals/*.md            the brief each lane was given
    <root>/manifest.tsv          the launcher's own record of both lanes
    <root>/HIGHWAY.md            the manager session's plan record

Both lanes are real worktrees on real branches, because the stall is read from
git and a described branch proves nothing about git. Neither lane has a live
terminal session, because a stall is a lane that has STOPPED -- a lane still
running on an unchanged branch is working, and the reading deliberately does
not count it. The seeder refuses to run if a terminal session by either lane's
name is live on this host, rather than seeding a fixture whose central fact is
quietly false.

The moved lane is not decoration. It is the control: same wave, same manifest,
same absent session, one commit -- and the reading must leave it alone. A
reading that called every ended lane a stall would be red on every finished
wave, which is the fabricated failure this harness exists to refuse.

THE ONE THING THAT DIFFERS BETWEEN THE TWO VARIANTS is a single plan-record
entry:

    declared (default)  the plan record names lumen-index and says what stopped
                        it -> step (j) reads Core 9 PASS
    --hidden            the same stall, and no record names the lane at all
                        -> step (j) reads Core 9 FAIL

Everything else about the two is byte-identical, so the reading has exactly one
thing to see. That is what makes it a discrimination and not a demonstration.

WHAT THIS FIXTURE DOES NOT PROVE. That a manager session on this host would
declare a stall. It proves that the reading answers, in both directions, when a
stall is actually there -- which is the thing that had never been observed. The
manager session's own habit is read by the same step, on this host's own wave,
and that reading is a separate observation.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

# The two lanes, named after the gaps in the lumen fixture next door, so the
# wave this seeds reads like the wave the rest of this directory describes.
MOVED = "lumen-units"
STALLED = "lumen-index"

# Terminal session names the launcher would have given them. They are recorded
# in the manifest and are deliberately NOT live: that absence is the first half
# of what makes the stalled lane a stall.
SESSIONS = {MOVED: "stall-fixture-lumen-units",
            STALLED: "stall-fixture-lumen-index"}

# The sockets `run.py` reads. Checked before seeding, for the same reason the
# harness reads both: a session live on the launcher's socket is invisible to a
# default-socket-only look.
SOCKETS = (None, "hw")

BRIEF = """# Lane {lane} -- work item `{item}`

Worker session in its own worktree on branch `lane/{lane}`.

**File ownership -- edit ONLY:** `{owns}`

## Outcome

{outcome}
"""

MANIFEST_HEADER = "lane\tworktree\tbranch\tbase_sha\ttmux\tgoal\tlaunched_at"

# The plan record. Entry two is the whole experiment: in the declared variant it
# names the stalled lane and what stopped it; in the hidden variant the same
# wave carries on without ever mentioning it.
PLAN_HEAD = """# Wave record -- the stall fixture

A wave of two lanes on the lumen fixture. One finished. One stopped without
producing anything, which is the event `operation.v1` clause 9 is about.

"""

PLAN_LAUNCH = (
    "- 2026-09-04T09:10:00Z cycle 1: launched {moved} and {stalled} at width 2, "
    "because the fixture's two gaps are in files that do not touch and neither "
    "lane's paths collide with the other's.\n"
)

PLAN_DECLARED = (
    "- 2026-09-04T09:41:00Z cycle 2: {stalled} is stuck and is not being "
    "relaunched. Its worker session exited with an unchanged branch: the clause "
    "it was given names a file this fixture does not carry, so there is nothing "
    "for it to change. Routed to the plan as a fixture defect, not retried; "
    "{moved} kept running beside it.\n"
)

PLAN_HIDDEN = (
    "- 2026-09-04T09:41:00Z cycle 2: no refill this cycle, because every ready "
    "item collides with the live lane.\n"
)

PLAN_TAIL = (
    "- 2026-09-04T10:02:00Z cycle 3: merged {moved}; its check is green.\n"
)


class SeedError(RuntimeError):
    """Something is wrong with the ground this fixture would stand on."""


def _git(cwd: Path, *argv: str) -> str:
    done = subprocess.run(  # noqa: S603 -- fixed argv, no shell
        ["git", "-C", str(cwd), *argv],
        capture_output=True, text=True, check=False,
    )
    if done.returncode != 0:
        raise SeedError(f"git {' '.join(argv)} failed: "
                        f"{(done.stderr or done.stdout).strip()[:400]}")
    return done.stdout


def live_sessions(sockets: tuple[str | None, ...] = SOCKETS) -> set[str]:
    """Terminal sessions live on this host, across every socket `run.py` reads."""
    names: set[str] = set()
    for socket in sockets:
        argv = ["tmux"] + (["-L", socket] if socket else []) + [
            "list-sessions", "-F", "#{session_name}"]
        done = subprocess.run(argv, capture_output=True, text=True,  # noqa: S603
                              check=False)
        if done.returncode != 0:
            continue
        names.update(line.strip() for line in done.stdout.splitlines() if line.strip())
    return names


def plan_record(declared: bool) -> str:
    """The manager session's plan record, with or without the declaration."""
    middle = PLAN_DECLARED if declared else PLAN_HIDDEN
    return (PLAN_HEAD
            + PLAN_LAUNCH.format(moved=MOVED, stalled=STALLED)
            + middle.format(moved=MOVED, stalled=STALLED)
            + PLAN_TAIL.format(moved=MOVED))


def seed(root: Path, declared: bool = True, force: bool = False) -> dict:
    """Build the wave. Returns what was built, in the words the run will read.

    Refuses a non-empty target rather than mixing two working trees, the same
    refusal `seed.sh` makes and for the same reason.
    """
    root = Path(root).resolve()
    if root.exists() and any(root.iterdir()):
        if not force:
            raise SeedError(f"target is not empty: {root} "
                            "(refusing to seed over existing work)")
        shutil.rmtree(root)

    clashes = sorted(set(SESSIONS.values()) & live_sessions())
    if clashes:
        raise SeedError(
            f"a terminal session is already live under this fixture's own name: "
            f"{', '.join(clashes)}. The stalled lane's session must be ABSENT for "
            "it to read as a stall, so this refuses rather than seed a fixture "
            "whose central fact is false.")

    repo = root / "repo"
    repo.mkdir(parents=True)
    _git(repo.parent, "init", "-q", "-b", "main", str(repo))
    _git(repo, "config", "user.email", "turnkey@converge.invalid")
    _git(repo, "config", "user.name", "Converge stall fixture")
    (repo / "readings.py").write_text(
        "def panel_temperature():\n    return 41.2\n", encoding="utf-8")
    (repo / "INDEX.md").write_text("# Index\n\n- panel_temperature\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "stall fixture: the base both lanes branch from")
    base = _git(repo, "rev-parse", "HEAD").strip()

    lanes = {}
    for lane, owns in ((MOVED, "readings.py"), (STALLED, "INDEX.md")):
        worktree = root / "lanes" / lane / "repo"
        _git(repo, "worktree", "add", "-q", "-b", f"lane/{lane}", str(worktree), "main")
        lanes[lane] = worktree

    # The lane that worked. One commit beyond base -- the control this reading
    # must leave alone.
    moved = lanes[MOVED]
    (moved / "readings.py").write_text(
        "def panel_temperature() -> float:\n"
        '    """Panel temperature, in degrees Celsius."""\n'
        "    return 41.2\n", encoding="utf-8")
    _git(moved, "commit", "-qam", "readings: name the unit panel_temperature reports")

    # The lane that stalled. Its worktree exists, its branch is real, and it
    # carries nothing: `main..lane/lumen-index` is empty. Nothing is committed
    # here, deliberately.

    goals = root / "goals"
    goals.mkdir()
    (goals / f"{MOVED}.md").write_text(
        BRIEF.format(lane=MOVED, item="lumen-1", owns="readings.py",
                     outcome="Every reading names its unit; the fixture's own "
                             "kit reports rule 1 PASS."),
        encoding="utf-8")
    (goals / f"{STALLED}.md").write_text(
        BRIEF.format(lane=STALLED, item="lumen-2", owns="INDEX.md",
                     outcome="Every public entry point is named in the index; "
                             "the fixture's own kit reports rule 2 PASS."),
        encoding="utf-8")

    rows = [MANIFEST_HEADER]
    for lane in (MOVED, STALLED):
        rows.append("\t".join([
            lane, str(lanes[lane]), f"lane/{lane}", base, SESSIONS[lane],
            str(goals / f"{lane}.md"), "2026-09-04T09:10:00Z",
        ]))
    (root / "manifest.tsv").write_text("\n".join(rows) + "\n", encoding="utf-8")
    (root / "HIGHWAY.md").write_text(plan_record(declared), encoding="utf-8")

    stalled_commits = int(_git(repo, "rev-list", "--count",
                               f"{base}..lane/{STALLED}").strip())
    moved_commits = int(_git(repo, "rev-list", "--count",
                             f"{base}..lane/{MOVED}").strip())
    if stalled_commits != 0 or moved_commits != 1:
        raise SeedError(
            f"the fixture did not come out as specified: lane/{STALLED} carries "
            f"{stalled_commits} commit(s) beyond base and lane/{MOVED} carries "
            f"{moved_commits}; expected 0 and 1")

    return {
        "root": str(root), "repo": str(repo), "base": base,
        "declared": declared,
        "stalled_lane": STALLED, "stalled_branch": f"lane/{STALLED}",
        "stalled_worktree": str(lanes[STALLED]), "stalled_commits": stalled_commits,
        "moved_lane": MOVED, "moved_commits": moved_commits,
        "plan_record": str(root / "HIGHWAY.md"),
        "manifest": str(root / "manifest.tsv"),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="stall_wave.py",
        description="Seed a wave whose second lane ends with an unchanged branch, "
                    "so step (j)'s Core 9 reading has a real stall to judge.",
        epilog="Then read it:\n"
               "  uv run evaluations/turnkey/run.py --env local --steps j \\\n"
               "      --repo <root>/repo --workspace <root>\n",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("root", help="where to build the wave (must be empty or absent)")
    ap.add_argument("--hidden", action="store_true",
                    help="seed the same stall with NO record naming the lane, so "
                         "the reading must report it broken")
    ap.add_argument("--force", action="store_true",
                    help="delete a non-empty target first (off by default)")
    args = ap.parse_args(argv)
    try:
        built = seed(Path(args.root), declared=not args.hidden, force=args.force)
    except SeedError as exc:
        sys.stderr.write(f"stall_wave.py: {exc}\n")
        return 1
    for key in ("root", "repo", "stalled_lane", "stalled_branch",
                "stalled_commits", "moved_lane", "moved_commits", "declared"):
        print(f"{key}\t{built[key]}")
    print()
    print("read it with:")
    print(f"  uv run evaluations/turnkey/run.py --env local --steps j \\\n"
          f"      --repo {built['repo']} --workspace {built['root']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
