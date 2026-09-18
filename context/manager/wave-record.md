# The wave record - boundaries, checks, and transfers a wave leaves behind

A manager session's promises are about what it DOES across a wave, not about what
any file contains. Six months later, the only thing left of a wave is what
somebody wrote down while it ran. Two of those writings are conventions rather
than habits, because a check reads them: the **call stamp** in the plan record,
and the **check record** in the repository.

Both are small. Neither is bookkeeping for its own sake: each is the durable
trace of a promise `contracts/operation.v1.md` makes.

## Boundary facts - in the existing plan record

For each produced boundary, retain one compact line naming the **producer,
consumers, interface decision owner within agreed direction, version or fixture,
incoming dependency, consumer acceptance owner and check, and residual
destination**. This makes local success, consumer acceptance, and product
acceptance separate facts without adding a tracker or supervisor.

    - BOUNDARY api-v2: producer w3; consumers web, cli; decision owner platform;
      fixture api-v2.1; incoming auth-v4; consumer check web journey (web owner);
      residual destination: cli queue item C-18.

## The call stamp - one line, in the plan record

Clause 11 says exactly four things reach the steward. Clause 3 says what needs
their word is parked and **everything else keeps moving**. Both are about the
same moment, so one line records both:

    - 2026-09-04T09:35:48Z CALL ratify - the clause 15 candidate needs your word.
      Parked: w8-clause15. Continued: console, direction-writes, ledger-refs.

Read it left to right:

- **CALL `<one of the four>`** - `ratify` · `irreversible` · `human check` ·
  `priority`. Those four words and no others; a call that is none of them is a
  defect in how the work is set up, and clause 11 says to file it as one rather
  than send it.
- **What is asked**, in a form they can answer in a word.
- **Parked:** what is now waiting on their word. `none` when the call parks
  nothing - a priority question usually parks nothing at all.
- **Continued:** what kept moving beside it. This is the half that makes clause 3
  checkable: "never the bottleneck" is a comparison, and a park with nothing
  written beside it cannot be told apart from a wave that stopped.

When nothing could continue, say so **and say why** in the same entry - *no ready
item that does not collide*, *everything else is blocked on this same word*. A
park with nothing continuing and no reason reads as a wave that went idle waiting
on a person, which is the one thing clause 3 forbids.

Write the stamp at the moment of the call, in the same plan record as every other
cycle entry. A call recorded a cycle later has already lost the thing being
recorded: what was running at the time.

## The check record - one entry, in the repository

Clause 7 says done means **the manager session** re-ran the check. Clause 8 says
the verification is yours, never the worker session's. After you integrate a wave
and re-run the check yourself, append an entry to
**`docs/workflow/CHECK-RECORD.md`** and commit it **in your own commit on the
integration branch**.

That file carries its own shape. Every entry names what it covers, the command
you ran, what it printed, the revisions, and environment. It also says whether
an installed consumer journey was run, or `N/A — no installed consumer applies`;
that is the manager's product-acceptance evidence, not a lane's local green.

Two things about it are worth knowing before you decide it is ceremony:

- **A lane may never write an entry.** The record's whole value is that the
  commit adding it sits outside every lane merge, so a reader can tell your hand
  from a lane's. An entry that arrives through a lane merge is a worker session's
  own green wearing the manager session's clothes, which is exactly what clause 8
  forbids.
- **The ledger is not this record.** `ledger/rows.yaml` says what the contracts
  currently read; lanes edit it, so the newest commit touching it is usually a
  lane's. Measured on this repository on 2026-09-04, that is precisely why the
  turnkey run could not say who had verified the newest wave.

## Optional external execution transfer - still the existing record

When work moves to an external executor, append its state: **offered;
accepted, declined, or unaccepted; returned; reintegrated.** For every state,
name the exact scope and revision, evidence or gaps, execution owner, interface
decision rights, expected receipt, next checkpoint, and reintegration owner.

    - TRANSFER offered: scope cli consumer at a14c9; execution owner partner;
      interface decisions: platform within direction; receipt: command output by
      04:40Z; reintegration: manager. Status: unaccepted.

Exporting a packet is not acceptance; acceptance is not product acceptance. Do
not maintain a duplicate local claim for transferred scope. An explicit steward
stop applies even without recipient acknowledgement, and a missing receipt is
never permission to continue the old work. The steward retains ratification and
priority; this convention does not promise direct manager-to-manager messaging.

## What these two can prove, and what they cannot

They are records a session keeps about itself, so they are honest about the same
limit the return log names: a call you never stamped and a check you never wrote
down leave no trace either way. What they do give is countability - a stamped
call can be classified, and a check record can be attributed to the hand that
wrote it, by anyone who was not in the session.
