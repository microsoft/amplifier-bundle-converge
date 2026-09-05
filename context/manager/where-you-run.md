# Where you run - the directory a whole operation hangs from

A manager session's first act is not a decision anybody records. It types a
command in whatever directory the terminal happened to be sitting in, and every
worktree, plan record, goal file, log, and piece of infrastructure the operation
ever stands up hangs from that accident for the rest of its life.

So it is a convention rather than a habit, and it is one line long:

**A manager session runs from the workspace root, and everything it stands up
lives at `<workspace>/.converge/<manager-id>/`.**

## Reading it

- **The workspace root** is the nearest ancestor directory holding
  `WORKSPACE-MANIFEST.json`. A single project with no workspace around it has
  none, and then the workspace root is the project repository's own root. There
  is no third case.
- **`<manager-id>`** is the project's own name - the one its work queue carries.
  Two projects in one workspace get two directories and share nothing, which is
  the whole reason the name is in the path at all.
- **Nowhere else, and never under the home directory.** The plan record, the
  lane worktrees, the pre-composed goal files, the watchdog log, and the infra
  ledger all live under that one directory, so closing the operation is one
  place to look and one place to sweep.

Resolve it once, before the first launch, and paste what it printed:

    W=$(d=$PWD; while [ "$d" != / ] && [ ! -f "$d/WORKSPACE-MANIFEST.json" ]; \
          do d=$(dirname "$d"); done; \
        if [ -f "$d/WORKSPACE-MANIFEST.json" ]; then echo "$d"; \
        else git rev-parse --show-toplevel; fi)
    BATCH_DIR="$W/.converge/<manager-id>"

That `BATCH_DIR` goes to **every** highway or goal-batch launch in the
engagement. A second launch that resolves it again by hand is a second chance to
get it wrong.

## Why it is written down rather than assumed

`contracts/composition.v1.md` clause 2, read plainly: nothing an operation stands
up may land outside the project it serves. `contracts/operation.v1.md` clause 1
starts the steward in their own project, not in a directory only the manager
session knows the name of.

Measured on this host on 2026-09-05: **thirteen** batch directories sat under
`~/dev/hw-*`, outside every workspace root. None of them was a mistake anybody
made deliberately. The `ten-lane-highway` practice's own example reads

> State lives in `BATCH_DIR` (create one per highway, e.g. `~/dev/hw-<name>`)

and a manager session that started wherever the steward happened to type
`amplifier` inherited that example without ever considering it. The cost lands
later and lands on somebody else: a finished run's worktrees, plan record, and
infra ledger outlive the workspace they belonged to, and nothing in the home
directory says which project any of them served.

That example is in the Amplifier CLI's shipped skill and is not ours to edit.
This convention overrides it for a manager session, which is all that is needed
and all this file claims.

## What this can prove, and what it cannot

The path is derivable, so anyone can check it: run the resolution above from the
session's own working directory and compare it against where `BATCH_DIR`
actually points. What it cannot prove is a launch that happened before anybody
read this - a directory already standing outside a workspace root stays where it
is until somebody moves it, and moving one is the steward's call, not a
housekeeping step.
