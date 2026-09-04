# The steward's objective for this manager session

This file is what the turnkey harness hands a **manager session** inside a fresh
container. It is written the way a steward writes: an objective, a width, a
deadline, and the facts about where things are. It does not tell the manager how
to derive work, how to write a lane brief, or how to judge one — those are
`contracts/operation.v1.md`'s job and the mode's job, and a harness that supplied
them would be running the wave itself and calling the result turnkey.

`{...}` fields are filled in by `run.py` at wave time from the environment it
just stood up. Everything else is sent verbatim.

---

Work in the converge-manager mode. Before anything else, call
`mode(operation="set", name="converge-manager")`. That call is gated and the
first attempt is refused by design — call it a second time immediately, then
print the active mode's name as the first line of your output. If it will not
activate, say so plainly and stop; do not proceed in an ordinary session.

## The objective

Close the contract gaps in `{fixture_repo}` with {width} real lanes, verify the
result yourself, and brief me.

Done, for this engagement, is all four:

1. `{fixture_repo}`'s own conformance kit reports no red rules.
2. Each gap was closed on its own lane branch and merged into `main`.
3. The queue project `{project}` shows the derived items resolved, each with a
   resolution written for me rather than for a changelog.
4. A return brief is appended to `{fixture_repo}/{return_log}`.

## Width and the deadline

Width is {width}. The repository's own contract and kit will tell you what the
gaps are and which files they live in; fill the lanes only with items that
provably touch different files (clause 6).

You have {deadline_minutes} minutes of wall clock. Take a lane's honest refusal
over a lane's unverified green — a red result with the cause named is a real
result, and the brief is what I actually read.

## Facts about this environment

These are orientation, not method.

| Thing | Where |
|---|---|
| The repository this project operates on | `{fixture_repo}` (git, branch `main`) |
| Its contract | `{fixture_repo}/contracts/` |
| Its own conformance kit | `{check_command}`, run from `{fixture_repo}` |
| The shared queue project (already created, empty) | `{project}` |
| The lane launcher | `{launcher}` |
| Where lane state should live | `{batch_dir}` |
| The terminal-session socket the launcher uses | `tmux -L {tmux_socket}` |

The launcher's own usage line documents its arguments. It is the only writer of
`manifest.tsv`.

## Two things this environment will hold you to

**Lanes are sessions, not sub-agents.** I am watching this container from
outside your session while you work: `git worktree list` in `{fixture_repo}` and
`tmux -L {tmux_socket} ls`. A lane that is not visible there did not happen,
whatever its commits say. If no launcher is reachable, fail loud and say so —
clause 5 — rather than quietly doing the work here.

**Do not end your turn while a lane is still running.** Nothing will wake you in
this container; there is no watcher and no steward at a keyboard. Poll until the
lanes are gone or the deadline passes, then verify, merge, re-run the kit
yourself, and write the brief. A manager session that reports "two lanes
launched" and stops has stopped the whole operation (clause 3).

## When you are done

Write the return log entry first, then print a short closing message naming: how
long you were away, what finished, what is stuck and why, what needs me, and
anything you think is quietly broken.
