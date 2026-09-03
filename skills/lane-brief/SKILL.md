---
name: lane-brief
description: >
  Write and judge autonomous lane briefs with the discipline the protocol
  requires — an honesty gate, a file-ownership split when lanes share a repo,
  and provenance checks so completion is credited from git artifacts, never
  from liveness or self-report. Use when briefing an EXECUTE-phase lane, when
  deciding whether a lane is actually done, or when a run looks successful but
  may have produced nothing. Applies PROTOCOL.md §4 (lane discipline) and
  pillars 2 and 5.
version: 0.2.0
---

# Lane briefs and honest completion

**Owned by `@converge:docs/PROTOCOL.md` §4 (lane discipline, imported intact
from cortex-core — all measured) and pillars 2 & 5.** This skill is the
procedure.

## Runtime: a lane is a tmux `/goal` session, not an in-session agent

Every lane runs as its own tmux `/goal` session, in its own git worktree, on its
own branch `lane/<item id>`, started by an external launcher. **`delegate()` and
in-session agent fan-out never execute lane work** — a wave that cannot reach a
launcher fails loud rather than falling back to agents.

The one sanctioned in-loop `delegate()` is the integrator's watcher/monitor: it
has to stay in the main agent loop to report back, and it executes no lane work.

What that means for the brief you write:

- **The brief is standalone.** The lane sees the goal file and its worktree, not
  your conversation. Everything it needs is in the file or it does not exist.
- **The terminal marker lives OUTSIDE the worktree** (the launcher names its
  absolute path in the goal file), so a lane's own `git add -A` can never stage
  the marker and collide at merge.
- **A commit is the only thing the wave can read back.** A lane whose branch tip
  still equals its base committed nothing and is credited as *blocked*, whatever
  its marker claims.

## What every lane brief carries

- **An honesty gate:** name what "not proven" looks like *before* work starts.
  The enemy is the successful-looking run that did nothing (pillar 5).
- **A file-ownership split:** two lanes in one repo require an explicit split
  of which files each owns.
- **Clause-quoting acceptance criteria:** the ledger row / contract clause the
  lane closes, quoted — so "done" is checkable against the spec, not vibes.

## How completion is known (not from liveness)

- **Completion is knowable only from git artifacts** (`DONE.md`, commits) —
  **never** from pane or session liveness.
- **Inherited-from-fork artifacts are the #1 false signal.** Check provenance
  (commit, mtime) before crediting any artifact as this lane's work.
- **Health endpoints are not a working system.** Numbers reported are real or
  absent.

## A self-report is never proof (pillar 2)

An agent's or monitor's verdict is a *raw observation*. Promotion to **proven**
requires an artifact check the orchestrator runs itself. Fabricated PASS
verdicts were measured in two independent sessions — do not trust a verdict you
did not verify.

## A missing artifact is a real result (pillar 5)

Honest stopping — `N/A` with a reason, `BLOCKED.md` with a cause — always beats
fabricated compliance. A lane that stops honestly and says why has done better
than one that reports a green result it cannot back with an artifact.
