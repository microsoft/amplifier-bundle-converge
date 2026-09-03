# Surface Contract — v1 (DRAFT)
**Superseded 2026-09-03 by the experience family** — `experience.v1` and its section and platform contracts. Kept for the record; build against the family.  
**Who builds against this:** intent stewards and their teammates, who open the
app; the manager session, which must be able to do anything the app can; and
whoever builds the app itself. The companion web page shipped inside Converge
is the reference implementation; the verified mockup interactions are its kit.

## Purpose

One place to see the direction and one place to see the operation, so the
steward's word is asked for rarely, answered in seconds, and never hunted for
across sessions, files, and repositories.

## Core (the teeth)

1. **Two places and a short list.** *Direction* — the vision and contracts as
   one experience. *Operation* — the manager session at work as one experience.
   You land on at most five things that need your word, re-ranked each refresh,
   each opening into its place. Nothing needing you is said aloud, as good news.
2. **Decisions arrive worked out.** What · why now · the recommendation · at most
   two trade-offs · the word to answer with. Several small calls may arrive as
   one ratification sheet, answered in a pass; every answer is written to a
   dated ratification record.
3. **Exactly four writes.** Answer with a word (ratified · ratified with edits ·
   declined · later, which re-ranks and never dismisses) · raise or lower a
   priority, with a note · drop feedback (text, screenshot, voice) for the
   manager session to interpret · steer (objective, budget, lane count, fill the
   lanes, have the manager session review this). Each is an operation the
   manager session can perform the same way.
4. **No data of its own.** It shows the project's documents, code record, work
   queue, lanes, return log, and pending decisions. No second copy of the truth.
5. **Proposals look the same whoever proposed.** A manager session's draft and
   a teammate's pull request: what changes, sentence by sentence · the evidence
   · what does not change · your questions pinned to paragraphs. Ratified makes
   the change with the word recorded; a teammate's proposal gets your questions
   and answer back where it came from.
6. **What changed since you last read this,** on every document, sentence by
   sentence — so a rewrite is checkable without rereading.
7. **Locking is gated.** The four conditions are shown; the control is live only
   when all four are met. The app never locks on its own.
8. **Evidence over claims, in plain words.** Done is shown as the evidence
   itself. *Kept · Not yet · Broken · Pinned open · Can't check* for contracts;
   *Working · Quiet · Silent — may have died* for lanes. Technical detail waits
   behind a Details fold. The app surfaces; it does not interrupt.
9. **The whole operation in view.** Lanes running against lanes intended, with
   the fill control · running against waiting-on-you · truly ready against
   waiting on you · the plan in order with reasons · each lane's state and
   evidence with drill-in · your limits · the feedback drop · every manager
   session you run, with "tell all." Stopping something is never a board button.
10. **Phone first, companion first.** Large targets, one-handed answers. The
    first release ships inside the bundle as a simple web page; the manager
    conversation stays in the CLI session and moves between the places freely.

## What v1 deliberately does NOT freeze

- The manager conversation inside the app — promoted when the two places prove
  themselves in daily use.
- Adding work directly — promoted by a real case where feedback is the wrong path.
- Budget choices beyond until done · a time · a spend — when someone asks for a fourth.
- A shared look with sister apps — when a second app exists.
- The app as its own installable product — when used daily by more than its author.

## Conformance kit asserts

- Places switch; answering marks the card and shortens the list; fill updates the
  gauge and the board; the lock control stays off until all four are green;
  what-changed shows removed sentences.
- Renders at 390 and 1280 pixels with nothing cut off and no console errors.
- Exactly four write paths, each mapped to a named manager-session operation.
- Every answer lands in the dated ratification record.
- No internal vocabulary outside Details folds.

## Reserved / open questions (NOT frozen)

- The manager-conversation surface.
