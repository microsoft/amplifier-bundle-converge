# The first wake - a project that has no contracts yet

Every other part of this mode assumes a contract to derive from. The operating
loop's first three steps - heartbeat, status, refill to width - each quietly
assume one, and so does the rule that work is derived rather than invented. On a
project's first wake none of that is there. There is a repository, a person who
wants something to be true of it, and nothing written down between the two.

So the first wake is its own shape, and it is a shape that runs exactly once per
project:

**Investigate first, propose second, and launch nothing until the steward's word
lands.**

The clause behind it is `contracts/operation.v1.md` Core 14: "A project with no
contracts has no gap to derive from, so the first work is drafting — clause 1's
one exception."

## Which path you are on

One question, asked before anything else: **does this repository already hold
code?**

- **It does** - you are *adopting*, and the work in flight pauses before you
  read a line. Say the pause in the plan record; a pause nobody wrote down is
  indistinguishable from a session that wandered off.
- **It does not** - you are *starting*, so there is nothing to read and you
  begin at the vision.

Everything after the reading is the same on both paths.

## The investigation - what to come back with

Read. Change nothing: not a fix in passing, not a rename, not a filed item.
Nothing is derivable yet, so anything you would file is an opinion, and clause 1
already says what to do with those.

Come back with four answers, each a sentence a colleague who has never opened a
code editor could read back to you:

1. **What is this?** What the repository does today, said once, plainly.
2. **Who is it for?** Who would be surprised by a silent change - the people and
   the systems that build against it.
3. **What does it promise today?** What already behaves like a promise although
   nobody wrote it as one: a public interface, a documented command, a test that
   guards a behaviour, a file everything else reads.
4. **What is in flight?** Open branches, running work, anything half-done. This
   is what the pause is protecting, and it is the part only this moment can see.

One thing belongs in that first brief besides the four answers: **where the
steward can watch this** - the app's URL when it answers on
`https://127.0.0.1:8788`, and the one command that starts it
(`scripts/run-app.sh`) when it does not - because the registration written in
step 0 puts this session on a page nobody has been told how to open.

On a blank repository all four have the same answer - *nothing yet* - and saying
so is the honest move. Inventing findings to fill the shape is how a first wake
goes wrong. There the steward's own sentences are the whole of the input.

## The drafts - what each one is

Both are written from the shipped templates in `docs/workspace-template/`, so
what reaches the steward is a draft to react to rather than a blank to fill in.

**The vision** - `VISION.md.template`, to `docs/VISION.md`. Where the project is
going, written as though already true: present tense, no roadmap, no dates in
the body, two screens. A sentence that needs "will" belongs in a contract or in
a work item, not here.

**Each contract** - `CONTRACT.md.template`, to `contracts/<name>.v1.md`. One
promise the project must keep: who builds against it on line 3, the purpose, the
numbered teeth, what this version deliberately does not freeze, and what a check
would observe. Fifty to a hundred lines; longer than that is two contracts.
Propose few - one or two, covering what the repository already promises - because
a promise nobody has tested against reality is a guess with a number on it.

Every one of them carries `(DRAFT)` in its first heading and stays that way.
Drafting is not deciding: the file is a proposal until the steward answers, in
one word - *ratified* - *ratified with edits* - *declined* - *later*. Only the
first two let you seed.

## After the word

If the word locks a document, **the freeze is one edit, never two.** A document
is locked by editing its own H1, and the record of that lock is more text in the
same file - so the H1 stamped `(FROZEN <date>)` and the `## Changelog` entry
recording the ratification go in a single write and a single commit. Written as
two edits, the second is always refused: the file already reads locked by then,
and a locked document takes no edit in place, including the one that would say
why it was locked. What is left is a half-frozen file - the status word landed,
the record of why it landed did not - and no later edit repairs it. That is
measured, not a caution: it stopped a first wake dead on 2026-09-06
(`converge-p17d`). The `freeze-bar` skill carries the exact shape.

Then seed the ledger: one row per checkable clause, each row starting at the verdict
the repository actually earns today, which on a first day is mostly *Not yet*. A
row seeded at *Kept* because the clause sounds obviously true is the drift this
whole method exists to catch. Then derive the queue from the gap between what
was just agreed and what the code does, every item naming the contract it
serves - and from there the operating loop is the whole of the job, and this
file never applies again.

## What this can prove, and what it cannot

The artifacts are checkable by anybody: a vision file, contracts carrying
`(DRAFT)`, a seeded ledger, and a queue whose items name contracts. What no file
can show is whether the investigation happened *before* the drafting - a vision
written without reading the code looks exactly like one written after. The only
evidence for that is the four answers themselves, written down where the steward
can hold them against what they already know is there. That is why they come
back as sentences rather than as a summary, and it is the honest limit of a
record the investigating session keeps itself.
