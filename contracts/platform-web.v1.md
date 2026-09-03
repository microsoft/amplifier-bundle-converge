# Platform Contract — Web — v1 (DRAFT)

**Who builds against this:** whoever builds the browser body of Amplifier
Converge — the first body and, for most people, the only one — and the intent
steward who opens it on a phone or a laptop. It holds only what the browser
adds to `experience.v1`, the umbrella every body keeps. An umbrella-plus-platform
pair is the work of one sub-project, with its own repository and its own steward.

## Purpose

Every behavior the umbrella requires has to survive a 390-pixel phone screen
and a 1280-pixel laptop, install to a home screen without an app store, and be
honest about the one thing a web page cannot do — keep working while it is not
running. This contract says what the browser adds, and what it must not claim.

## Core (the teeth)

1. **Everything the umbrella requires is present here, in the browser's shape.**
   The anchor is a manager session; the home is the list of them sorted by which
   needs you; Direction and Operation are the two places; the Manager Console is
   a pane beside either, never a third place; at most five things ask for your
   word at once; all five writes work — answer with a word, raise or lower a
   priority, drop feedback, steer, ask.
2. **What the umbrella asks of every body, this body keeps.** It holds no data
   of its own; whatever you can do here, the manager session can do too; state
   words stay plain; evidence is shown rather than claimed, with technical
   detail folded; a proposal looks the same whoever wrote it; what changed since
   you last read is shown sentence by sentence; locking is gated, and the app
   never locks on its own.
3. **Idioms satisfy behaviors; they never subtract them.** Everything below this
   clause is shape. A difference is an idiom when you can do the same thing,
   learn the same fact, and be refused for the same reason; it is a divergence
   the moment it takes one of those away.
4. **One information architecture, two layouts — IDIOM.** The phone and the
   laptop show the same places, the same list, and the same words, and differ
   in arrangement only: one thing at a time, or two side by side.
5. **The phone switches places from the bottom — IDIOM.** Direction and
   Operation sit within thumb reach, and the things needing your word are a
   full-width stack of cards. On the laptop the switch is always visible and
   that same list becomes a narrow rail beside the reading surface.
6. **The Manager Console is a right pane on the laptop and a sheet that slides
   up on the phone — IDIOM.** It stays live while you move between Direction and
   Operation. On the laptop you drag it wider; on the phone you pull it up when
   you want it and push it down when you do not.
7. **A proposal opens full-screen on the phone and beside its evidence on the
   laptop — IDIOM.** The phone gives the review the whole screen so the reading
   is undivided; the laptop puts what changed next to the evidence for it.
8. **Evidence and technical detail arrive in a sheet — IDIOM.** On the phone it
   rises from the bottom over what you were reading; on the laptop it opens in
   the inspector beside it. Either way the deciding sentence stays in view.
9. **It installs, and installing changes only the frame — IDIOM.** Added to a
   home screen or a dock, it runs in its own window without browser furniture.
   Nothing gains a behavior by being installed and nothing loses one; there is
   no store, no review queue, and no second build.
10. **Offline it reads what it last synced, and says when that was.** A small
    helper the browser keeps beside the app serves the documents already
    fetched, each marked with the moment it came from. Nothing that is not
    current is shown as current.
11. **Offline it refuses the five writes in a plain sentence.** A browser cannot
    promise to send something later — the helper may never be woken, and on some
    browsers never is — so the app says the write is unavailable and names what
    to do instead. Silence is the only wrong answer.
12. **The Manager Console is live or plainly disconnected, never in between.**
    It is a view of a running session; when the connection drops it says so on
    its own face, and never leaves an old screen sitting there looking live.
13. **Everything it needs comes from its own origin.** No script, font, style,
    or image is fetched from anywhere else, so it works on a restricted network
    and on a laptop with no internet at all.
14. **It renders at 390 and 1280 pixels with nothing cut off and no errors in
    the browser's own log.** Those two widths are the phone and the laptop this
    contract is written for; a body that fails either is not shipped.

## What v1 deliberately does NOT freeze

- Notifications from the browser — promoted when a steward asks to be told
  without the app open, and each browser's honest limits are written down.
- A quick-access surface in this body — promoted when a home-screen shortcut
  proves too coarse for "which manager needs me?".
- Widths beyond 390 and 1280 — promoted when a tablet or a wide monitor is in
  daily use.
- Holding a write until the connection returns — promoted when refusing one
  costs a steward a decision they meant to make.

## Conformance kit asserts

- Renders at 390 and 1280 pixels with nothing cut off and no errors in the log.
- Every behavior the umbrella requires is reachable at both widths.
- The places switch and the Manager Console stays open across the switch, at
  both widths.
- Installed and opened with the network off: the last-synced documents read,
  each showing when it synced, and each write refuses in a plain sentence.
- No request leaves the app's own origin, measured with the network recorded.
- Five write paths, no more, each mapped to a named manager-session operation.

## Reserved / open questions

- Whether an installed body may ask the system to wake it.
- Which browsers are supported by name, and what is said where one falls short.
