# The return brief - what the steward reads when they come back

Every time the intent steward returns, they get one brief. It is written in
plain sentences, not a status table, and it is short enough to read standing up.
`contracts/operation.v1.md` clause 10 requires one on every return.

## Where it lives

Append each brief to **`docs/workflow/OWNER-RETURN-LOG.md`**, newest entry last,
under a dated heading. That file is the durable memory: it survives a manager
session's context resetting, and a fresh session reads its tail first to learn
where things stand.

Write the log entry **before** sending the message. If your context resets
between the two, the record still exists. Stamp, then the five parts, then reply.

## The stamp - the heading, written the moment they come back

**Stamp the return before you answer it.** The moment the steward's message
arrives - before you read the queue, before you reply, before anything else -
append the entry heading with the clock time of their return:

    ## 2026-09-04 04:01 - they came back to a green gate

That heading is the record that a return happened, and nothing else in this
project keeps one. The stamp goes in at the moment of the return and the five
parts under it at the end of the turn, so the two are countable against each
other: a return that never got briefed stands in the file as a stamp with the
parts missing under it, in plain sight on the page the steward already reads.

A brief you send unprompted - a wave landed while the steward is still away - is
welcome and keeps a **date-only heading**, with no clock time on it. Every
return has a brief; not every brief has a return.

## The five parts, in this order

**Each part is one sentence, opening with its own bold label** - the label
written into the entry exactly as it appears below, never paraphrased - so the
shape is visible without reading the prose:

1. **Time away.** How long they were gone, and how many waves ran in it.
2. **Finished.** What is done and proven - each with the check you re-ran, not
   the lane's word for it.
3. **Stuck.** What stopped, and the cause. An honest stop with a reason is a
   real result and belongs here plainly.
4. **Needs you.** The calls only they can make, each stated so it is answerable
   in a word. Nothing here that is not one of the four calls in clause 11.
5. **Anything quietly broken.** What went wrong that they did not ask about, and
   what it cost - including anything the manager session broke itself.

**No part is ever folded into another** - a manager session once folded *time
away* into *finished* and the check caught it. "Nothing stopped" is a Stuck
sentence and "nothing needs you" is a Needs you sentence: an absent part and an
empty one are not the same thing, and only the empty one is honest.

## How it reads

- **Sentences, not fragments.** A colleague who has never opened a code editor
  can read it and know what happened.
- **The verdict first.** The stamp's headline says the state of the project in a
  few words, before any detail; the five parts under it fill in how.
- **Nothing claimed that was not re-checked.** If a check could not be run, say
  *can't check* and why. A gap named honestly is worth more than a green line
  nobody can back up.
- **Technical detail folded** into a marked section at the end, never carried in
  the deciding sentence.
- **No status vocabulary of its own.** Contracts read *Kept - Not yet - Broken -
  Pinned open - Can't check*; work reads *Truly ready - Waiting on you - Working
  - Stuck - Done*; lanes read *Working - Quiet - Silent, may have died*.

## When the manager session is stopping

A brief written at hand-off (clause 13) carries one more thing: what a fresh
session needs to resume without re-deriving anything - what is already verified,
what is honestly still open, and where the plan and the queue are.
