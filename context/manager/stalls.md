# The stall stamp - counting to three, then saying so

Clause 9 says a stall is a decision, not a loop. The decision needs a number, or
it is a mood: "no progress across iterations" without a count is satisfied by a
session that polls forever and always intends to stop soon. This file carries the
number, what it counts, and the one line the count is written into.

**The number is three.** Three iterations against the same target with no
progress, and you stop attempting and declare.

## What one iteration is

An iteration is **one attempt at the same target**: one tool call at the file that
refused you, one relaunch of the lane that died, one poll of the lane you are
waiting on, one re-run of the command that failed. Attempts at different targets
are different counts - a refused edit and a hung lane are two stalls, each with
its own three.

Trying a different move on the same target is still an iteration on that target.
Grepping for another way around a guard that refused you is attempt two, not a
fresh start; that is precisely the move that produced the twenty minutes below.

## What progress is

Progress is **a new fact you did not have before the attempt**:

- a file changed, or a command that had been failing succeeded;
- a lane's branch moved, or its terminal session ended;
- an error message that is **different** from the last one - a new refusal is a
  new fact and resets the count for that target;
- an answer arrived from the queue, the steward, or a check.

Progress is **not**: time passing; a poll returning what the last poll returned;
the same refusal in different words; a plan to try again. A watcher that reports
"still running, no change" three times is three iterations with no progress, and
the third one is the declaration.

## The stamp - one line, in the plan record

Write it in the same plan record as every other cycle entry, at the moment you
stop attempting:

    - 2026-09-06T04:12:07Z STUCK w4-changelog - the locked-document guard
      refuses the changelog edit and there is no candidate file to write instead.
      Iterations without progress: 3. Routed: plan.

Read it left to right:

- **STUCK `<target>`** - the lane, the file, the command. Whatever the three
  attempts were against, named so somebody else can go and look at it.
- **The cause, in plain words.** What stopped you, not what you were doing. "The
  guard refuses the edit" is a cause; "I was unable to complete the change" is
  not.
- **Iterations without progress:** the count you actually reached. Three is the
  bar; a stall you declared at two is honest and says two.
- **Routed:** `plan` when the next move is work - file it as an item, requeue it,
  brief a lane for it. `steward` when it is one of clause 11's four calls, in
  which case stamp the CALL line beside it as clause 11 asks.

A stall routed nowhere is not declared. The route is the half that turns the stop
into a decision somebody else can act on.

## Why the number exists at all

Measured on 2026-09-06, in the adopter harness run of 03:50Z, scenario 2: a
manager session's own locked-document guard refused an edit it needed to make. It
recognised the problem, tried to get around it by grepping and delegating, and
then polled for **more than twenty minutes** without declaring anything. The
person watching received no cause, no route, and no call - and the scenario's
remaining steps were never reached. One sentence - "stuck: the lock guard refuses
the changelog edit; here is the file, half-frozen" - would have handed them
something to act on.

The rule that was in place at the time already said stalls are decisions. What it
did not carry was a number, so no iteration was ever the last one.

## What the stamp can prove, and what it cannot

It is countable by somebody who was not in the session: the stamps can be found,
the targets named in them can be checked, and a declared count can be compared
against what the wave actually shows. The turnkey harness reads exactly that -
`evaluations/turnkey/run.py`'s clause 9 reading finds the record that says a lane
stopped, and now also reports the iteration count when the record carries one.

It cannot prove that the count is true. A session that attempted six times and
wrote three has written a number nobody can check against the attempts, because
attempts leave no trace of their own. What the stamp settles is that a stop was
declared, with a cause, a count and a route - not that the count is accurate.
Treat it as this session's own honest report, in the same way the return log is.
