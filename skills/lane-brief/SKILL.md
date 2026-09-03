---
name: lane-brief
description: >
  Write a lane brief a worker session can run alone, and judge honestly whether
  a lane is done. Carries the proven charter: an honesty gate, acceptance whose
  evidence a reader can still see afterwards — a file on disk or printed command
  output, never a tool call's arguments — an explicit file-ownership split, two
  exits and no third, the terminal marker outside the worktree, and completion
  credited from commits rather than from liveness or self-report. Use when
  briefing a worker session, when deciding whether a lane is actually done, or
  when a run looks successful but may have produced nothing. Applies
  operation.v1 §5 (lanes are real sessions) and §7 (done means the manager
  session re-ran the check).
version: 0.3.0
---

# Lane briefs and honest completion

A **lane** is one bounded piece of work carried out by a **worker session** —
a short-lived AI session working alone in its own copy of the code. The
**manager session** writes the brief, launches the lane, and judges the result.
The **intent steward** — the person the work is for — is not in this loop.

The brief is the whole of what a worker session gets. It sees the goal file and
its working copy, never the manager session's conversation. Everything the lane
needs is in the file, or it does not exist.

Governing text: `contracts/operation.v1.md` §5, §7 and `docs/PROTOCOL.md` §4.

## Runtime: a lane is a tmux `/goal` session in its own worktree and branch, started externally — `delegate()` and in-session agent fan-out never execute lane work

Every lane runs as its own tmux `/goal` session, in its own git worktree, on its
own branch `lane/<item id>`, started by an external launcher. A wave that cannot
reach a launcher **fails loud** and says so; it never quietly falls back to
spawning agents inside the manager session.

### The four sanctioned in-session sub-agent roles

A manager session may spawn a sub-agent for exactly four things, and **none of
them executes lane work**:

1. **Read-only investigation under half an hour** — look, report, change nothing.
2. **Protocol ruling** — ask the authority what the rules require, and relay it.
3. **Janitorial queue recording** — file or update items in the shared queue.
4. **The watcher** — absorb waiting. It must stay in the main agent loop so it
   can report back, and it observes only.

Anything beyond these four is a lane, and a lane is a session.

## What every lane brief carries

The brief template is `docs/workspace-template/GOAL-FILE.md.template`. Whatever
shape it takes, a brief carries these four things:

- **The honesty gate: name the exact outcome that means "not proven" before the
  work starts.** Write the sentence the lane must be able to say — *"no macOS
  host here, so verification is unit-level only, and the resolution must say
  so."* Then name where that sentence will be visible: the file it goes in, or
  the command whose output shows it. The enemy is the successful-looking run
  that produced nothing. A lane that knows in advance what failure looks like
  will report it, and a gate written this way can be checked by someone who was
  not there.
- **An explicit file-ownership split.** When two lanes share one repository,
  each brief names the exact paths that lane owns and states that everything
  else is off-limits. Where one file must be shared, name that one file and no
  others. Width is a collision decision, not a speed decision: items touching
  adjacent code run as one lane claiming them in order.
- **Acceptance that quotes the contract and that a reader can check alone.**
  Quote the clause the lane closes, so "done" is checkable against the promise
  rather than against a feeling — and write every item so its evidence lands in
  a file or in printed output. The next section is the rule for that.
- **The boundaries it must not cross.** Live services, shared tooling, other
  people's files — named, not implied.

## Evidence the evaluator can see

Whoever judges the lane — the manager session, or an automatic evaluator reading
the goal file — sees exactly two things: the files in the lane's branch, and the
text the lane printed while it worked. It cannot see inside a tool call. A
reason handed to a queue command as an argument is invisible to it.

So an acceptance item whose only evidence is a tool-call argument can never be
marked met, however well the lane did the work. That is measured, not
hypothetical: in one run three lanes finished and committed everything asked of
them and all three were ruled not done, because their acceptance asked for
evidence that lived only in tool-call arguments. One of those lanes wrote a
blocked marker over work that was complete.

Three rules follow, and they apply to every brief:

- **Every acceptance item names a file path, or a command whose output the lane
  prints.** An item that names neither is not an acceptance item yet. Rewrite it
  until it does.
- **A resolved queue item is evidenced by the read-back, not by the resolve.**
  Write it as: resolve the item, then **read it back** with the queue's read
  command (`work_list`, given the item's id) and print the stored reason. The
  printed read-back is the evidence. The resolve call is not, because its reason
  lives only in a tool-call argument.
- **Show output where it happens.** "The check passes" proves nothing on its
  own. Run the command, print what it said, and let the printed text be the
  claim.

Well-formed acceptance items look like these:

- `skills/lane-brief/SKILL.md` frontmatter reads `version: 0.3.0`.
- `docs/workspace-template/GOAL-FILE.md.template` exists and carries the
  evidence rule.
- `grep -n 'read it back' skills/lane-brief/SKILL.md` prints at least one line,
  and that output is shown.
- `python conformance/<contract>/run.py` is run and its output is printed.
- The queue item is resolved, then read back with `work_list` and the stored
  reason printed.

Every one of them names a file a reader can open, or a command a reader can see
the output of. That is the whole test.

## Two exits and no third

A lane ends one of exactly two ways, and the brief says so in these words:

- **A) SUCCESS** — every acceptance item met, with each item's evidence visible
  in a committed file or in printed output; the work committed; the queue item
  resolved with a reason written for the person who asked, then read back and
  printed.
- **B) BLOCKED** — a named blocker the lane cannot clear; whatever is sound is
  committed; the cause is written down; the lane stops.

There is no third outcome, and no improving after A or B. An honest stop with a
cause always beats a green report nobody can back up. A single item that proves
impossible does not strand the rest: release it with the blocker named and
continue to the next.

If every deliverable is committed and its evidence is on disk or in printed
output, the outcome is A. A lane that writes BLOCKED over finished work has
reported a result that did not happen.

## The terminal marker lives OUTSIDE the worktree

The brief names the marker's absolute path, and that path is outside the
repository on purpose. A lane's own `git add -A` can then never stage the marker,
and two lanes' markers can never collide when their branches merge. A brief that
puts the marker inside the working copy is a brief that will cause a merge
conflict later.

## A commit is the only durable evidence

Completion is read back from git, never from anything else:

- **A branch whose tip still equals its base committed nothing.** It is recorded
  *stuck*, whatever its marker claims. An artifact inherited from the base is the
  most common false signal there is — check what commit produced it before
  crediting it.
- **A lane still running at the deadline is stuck, not done.** Never write down
  an outcome that has not happened yet.
- **A self-report is never proof.** A worker session's verdict, a monitor's
  verdict, a marker file's text and a live terminal pane are all raw
  observations. They become *proven* only when the manager session re-runs the
  check itself and sees the result.
- **What only a tool call saw did not happen, as far as the judge is
  concerned.** If the work left no file and printed no output, there is nothing
  to re-run and nothing to credit.
- **Health endpoints are not a working system.** Numbers reported are real or
  they are absent; there is no third state.

## A missing artifact is a real result

Stopping honestly — recording *can't check* with a reason, writing down a
blocker with its cause — is a genuine outcome and is recorded as one. A lane
that stops and says why has done better than a lane that reports green and
cannot show the artifact behind it.
