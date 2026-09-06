# Manager Console Contract — v1 (FROZEN 2026-09-06)

**Who builds against this:** the intent steward, who talks to the manager
session while looking at either place; whoever builds the console pane in any
body; the manager session, whose own live session is what the pane carries; and
the authors of `experience.v1`, the umbrella this contract hangs off. It
inherits that umbrella's platform mechanism: every clause below carries one of
its four words — `REQUIRED` (present and behaving as written), `IDIOM`
(required; its shape follows the platform), or `EXCLUDED` (a body must not
carry it, and its presence is the defect) — and is placed against its three
surface classes. The
tag is the clause's **full app** placement; **quick-access** and
**notification** are `EXCLUDED` throughout, because a console is one live session
beside the work, and clause 7 already keeps anything needing your word from
arriving only here.

## Purpose

The conversation with the manager session is the one thing a steward must not
lose when switching places. The console keeps it beside the work without
becoming a third place, and without building a second conversation before we
know what the first one is missing.

## Core (the teeth)

1. **The console is a pane, not a place.** `(REQUIRED)` It opens beside
   Direction or Operation, and switching between them does not close it,
   restart it, or lose a line of what was said.
2. **V1 carries the manager session exactly as it already runs.** `(REQUIRED)`
   The pane embeds the live command-line session through the tmux connector —
   tmux being the tool that lets a long-running terminal session be attached to
   from somewhere else. Nothing about the manager has to be redesigned to ship.
3. **One console, one manager session, and it *is* that session.** `(REQUIRED)`
   What you type there is what the manager session receives, not a summary the
   app relays — so there is no second conversation to keep in step with the
   first.
4. **Wide screen: a resizable pane. Small screen: a sliding tray.** `(IDIOM)`
   The umbrella governs it — the shape follows the platform; the behaviors
   (stays open, keeps its conversation, gets out of the way on demand) do not
   change.
5. **Watch session reuses this pane.** `(REQUIRED)` Watching a lane's live
   worker session from Operation opens here rather than in a new place, and
   leaving it returns the manager conversation where it stood.
6. **The console is never the dashboard.** `(EXCLUDED)` Raw agent and tool
   activity is not how the operation is understood; Operation is. Nothing there
   may require reading the console to make sense.
7. **Nothing that needs your word arrives only here.** `(REQUIRED)` Every
   decision reaches you through the short list and its ratification sheet, so a
   steward who never opens the console misses nothing and can answer everything.
8. **The console never ratifies.** `(EXCLUDED)` A word typed here is a message
   to the manager session; any decision it produces comes back through the
   ordinary path and lands in the dated ratification record.
9. **It is not a native chat in V1.** `(EXCLUDED)` Nothing may be built to
   depend on it being one; a native conversation later replaces the connector
   underneath without changing one behavior above.
10. **It shows one manager session's own work and reaches nothing else.**
    `(REQUIRED)` The machine may hold other terminal sessions, checkouts, and
    queues; none of them appear merely because they exist.

## What v1 deliberately does NOT freeze

- The connector's own contract — how the terminal session is located, reached,
  framed, kept safe, and resized. Promoted when the steward's proof-of-concept
  notes land; until then this contract names the mechanism and nothing more.
- A native in-app manager conversation — promoted when the two places prove
  themselves in daily use and the connector's limits have been measured.
- Whether the console can be torn off into a window of its own — promoted when
  someone working across two screens asks for it.

## Conformance kit asserts

- Switching Direction ↔ Operation leaves the console open with its conversation
  intact, and does not restart the session behind it.
- A line typed in the console reaches the manager session itself; a line the
  manager session writes appears in the console.
- The pane resizes at 1280 pixels and behaves as a dismissible tray at 390, with
  nothing cut off and no console errors.
- Watch session opens a lane's live view in this pane, and leaving it restores
  the manager conversation.
- A steward who never opens the console can still perform all five writes and
  answer every decision waiting on them.
- No decision is reachable only through the console.
- Every recorded answer traces to the ordinary decision path, never to a console
  message read as a ratification.

## Reserved / open questions

- What the console shows when a manager session hands off to a fresh one, and
  whether the earlier conversation stays readable beside the new one.
- Whether a second person may watch the same console without being able to type.

## Changelog

| Date | Change | Evidence |
|---|---|---|
| 2026-09-06 | Every clause carries one of the four words as a code span, and each is placed across full app · quick-access · notification | `docs/workflow/experience-console.v1-candidate.ratified.md`; owner words 2026-09-05T20:01:47-07:00 and 2026-09-06 round 2 |
| 2026-09-06 | Locked on the steward's word "1) lock" (tidy card, round 3) — kits PASS, rows Kept, no proposal open; changes from here go through a `<name>.vN-candidate.md` proposal | docs/workflow/owner-ratifications-2026-09-06.md round 3 |
