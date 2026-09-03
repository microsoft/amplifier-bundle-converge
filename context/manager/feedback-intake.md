# Feedback intake - where the steward's notes land

The intent steward will react to work in progress at any moment - a screenshot,
a voice note, "still not working", a paragraph about where the project should be
going. That is welcome, and it must never cost them a form to fill in.

## The convention

Raw feedback lands in **`.converge/feedback/`** in the project repository, one
file per drop, in whatever format it arrived. No naming scheme is required; a
timestamp and a few words is enough (`2026-09-02-login-screenshot.md`). The
steward writes; the manager session reads. Nothing else is asked of them.

A drop may be a sentence, a transcript, a pasted log, a path to an image, or a
mix. The folder is an inbox, not a tracker: entries stay as written and are
never edited to look tidier.

## The manager session's obligation

**Raw feedback is never filed as work.** A drop is read against the contracts,
the current queue, and what is running, and then it becomes one of three things:
an enriched work item, a decision put to the steward, or a verification the
manager re-runs itself.

Apply `contracts/operation.v1.md` clause 4 before anything reaches the queue:

1. **Quote the evidence** - the steward's own words, verbatim, in the item.
2. **Date it against the build** - confirm which version they were looking at.
3. **Merge by cause; split what hides several.**
4. **Enrich to lane-ready** - cause, reproduction, the contract it serves, and
   what "fixed" will mean.
5. **Update, don't duplicate** - add to the open item that already covers it.
6. **Mine the failures nobody reported** - what the note implies but omits.
7. **Direction returns a decision, not a ticket** - a call answerable in a word.
8. **"Still broken" reopens verification, never the tracker** - re-run the check
   yourself first.

## Closing the loop

Record what happened to each drop where the plan lives, next to the reason:
became item X - answered by decision Y - already covered by Z - re-verified and
genuinely fixed. A drop that produced nothing still gets a line saying so.

A drop is never deleted. The folder is the record of what the steward actually
said, and an item's quoted evidence must be traceable back to it.
