# Worked example — Platform: Web v1

Contract: [`../../contracts/platform-web.v1.md`](../../contracts/platform-web.v1.md)
Kit: none — a platform contract is shape, and shape needs a browser. This
example runs the browser.

The browser body is the only body that exists, so this is the one platform
contract that can be worked end to end today. Every block below is output from a
command run on 2026-09-04 against this repository at `f718a20`.

> Every behavior the umbrella requires has to survive a 390-pixel phone screen
> and a 1280-pixel laptop. Those two numbers are in the contract, and they are
> the two numbers the check uses — not a range, not "mobile", not "desktop".

## Start with one promise

Clause 14, in full:

> **It renders at 390 and 1280 pixels with nothing cut off and no errors in the
> browser's own log.** Those two widths are the phone and the laptop this
> contract is written for; a body that fails either is not shipped.

This is the hardest clause in the family to check honestly, and the ledger says
so: its row is Can't check, because no conformance kit here launches a browser.
What follows is the part that *can* be measured today, and an exact statement of
what it does not cover.

## The rendered check, at the two widths the contract names

`app/tests/test_console_overflow_rendered.py` drives a real Chromium against the
real app and asserts, at each width, that the page does not scroll sideways:
`document.documentElement.scrollWidth <= clientWidth`.

```
$ uv run --extra app --with pytest --with httpx --with playwright \
    pytest app/tests/test_console_overflow_rendered.py app/tests/test_tmux_rendered.py -v

test_closed_console_does_not_widen_the_page[1280-800]              PASSED
test_closed_console_does_not_widen_the_page[390-844]               PASSED
test_the_pane_clips_its_own_content_and_drops_its_divider_when_closed  PASSED
test_manual_procedure_is_documented                                PASSED
test_killed_session_renders_ended_and_never_another_session        PASSED
test_full_height_tui_keeps_its_top_row                             PASSED
test_manual_procedure_is_documented                                PASSED

7 passed in 10.01s
```

Both widths, both console states.

## Right and wrong, told apart — and the wrong one really happened

The right is above. The wrong is written into the same file, because the test
exists to pin a defect that was measured, not imagined:

> With the console **closed** the desktop grid gives the pane a 0px column — and
> the page was still 11px wider than the viewport:
>
>     scrollWidth 1291 vs clientWidth 1280 at a 1280x800 viewport

Two causes, both invisible to every API-level check: an absolutely positioned
descendant escaping the pane's `overflow: hidden` (10 of the 11 pixels), and a
1px left border sitting at x=1280 when the column is 0. That is the discriminating
pair this contract needs — a real failure with a number, and the run above that
no longer reproduces it.

There is a second, live wrong at the same widths, and it is fair to name it here
rather than let the green run above stand for the whole clause:

```
converge-6qk — the workspace header's constraint strip needs 348px for its three
chips and is allotted 92–219px. Because the strip is overflow:hidden it swallows
its own content instead of widening the page:

  1280 console open   ->  92px   all three chips clipped
  1280 console closed -> 138px   STRATEGY + LANES clipped
  1920 console closed -> 219px   STRATEGY + LANES clipped
```

So: "the page does not scroll sideways" is Kept and measured. "Nothing is cut
off" is Broken, measured by hand, and filed. Clause 14 is one sentence carrying
two promises, and this example refuses to let the easier one stand in for the
harder one.

## The structural half, which needs no browser

```
$ uv run --with pytest pytest tests/test_renders_at_both_widths.py -q
14 passed in 12.53s
```

Fourteen assertions read the stylesheet's own rules — that the layout has a
declaration for each width, that the console is a pane at one and a tray at the
other. It cannot see a render. It is named here as what it is, so nobody counts
it twice.

## Clause 13, which one command settles

> **Everything it needs comes from its own origin.** No script, font, style, or
> image is fetched from anywhere else […]

```
$ curl -s -b "cv_session=$COOKIE" http://127.0.0.1:8811/ \
    | grep -oE '(src|href)="[^"]+"' | sed 's/.*="//;s/"$//' | sort -u

/branding/favicons/apple-touch-icon.png
/branding/favicons/favicon-32.png
/branding/favicons/favicon.ico
/branding/icons/converge-icon-64.png
/manifest.webmanifest
/static/css/console.css
/static/css/dialogs.css
/static/css/direction.css
/static/css/operation.css
/static/css/shell.css
/static/css/tokens.css
/static/js/main.js
/static/js/tmux.js
/static/vendor/xterm/css/xterm.css
/static/vendor/xterm/lib/xterm.js

$ ... | grep -cE '(src|href)="https?://'
0
```

Fifteen references, every one root-relative, none off-origin. The terminal
viewer that would normally arrive from a content network is vendored at
`app/static/vendor/xterm/`. The ledger records this as an *absence* assertion —
the first off-origin reference flips it. Kept.

## Clause 9, installability

```
$ [ -f app/static/manifest.webmanifest ] && [ -f app/static/sw.js ] \
    && grep -q 'manifest.webmanifest' app/templates/base.html \
    && echo INSTALLABLE-FROM-ITS-OWN-ORIGIN

INSTALLABLE-FROM-ITS-OWN-ORIGIN
```

A manifest, a service worker, and the link between them: it installs to a home
screen with no store and no second build. What is *not* proved is that
installing changes only the frame — nothing compares the two windows — and the
ledger says so in those words.

## What offline still owes

Clauses 10 and 11 are Not yet, and the reason is a good rule doing its job:

```
$ grep -n "never written to the cache" app/static/sw.js
5://   2. /api is network-first and is never written to the cache at all, so a stale
74:  // Live data: network-first, and never written to the cache.
```

Static assets are precached, so with the network off the shell loads — and
every payload behind it comes from `/api`, which is never cached, so the shell
renders empty. There is nothing that "was last synced" to read, nothing saying
when, and no plain sentence refusing a write. The two clauses and the service
worker's rule are not actually in conflict: the clause asks for what was last
synced *labelled with when*, which is a different thing from a stale value shown
as if it were live. Closing it is a design call about which payloads may be
cached with a visible timestamp. Carried by `converge-719`.

## Clause traceability

| Clause | How it is checked | State today |
|---|---|---|
| 1 — everything the umbrella requires, in the browser's shape | the three experience kits | Not yet |
| 2 — what the umbrella asks of every body, this body keeps | the three experience kits | Not yet |
| 3 — idioms satisfy behaviors, never subtract | needs a second body | Can't check |
| 4 — one architecture, two layouts | needs a browser at two widths | Can't check |
| 5 — the phone switches places from the bottom | needs a browser at two widths | Can't check |
| 6 — console: right pane wide, sheet on the phone | Console kit rule 4 + the rendered run above | Not yet |
| 7 — a proposal full-screen on the phone | needs a browser at two widths | Can't check |
| 8 — evidence arrives in a sheet | needs a browser at two widths | Can't check |
| 9 — it installs, and installing changes only the frame | probe, above | Kept |
| 10 — offline it reads what it last synced | the offline run | Not yet |
| 11 — offline it refuses the five writes plainly | the offline run | Not yet |
| 12 — the console is live or plainly disconnected | probe over the app | Kept |
| 13 — everything from its own origin | the request scan above | Kept |
| 14 — renders at 390 and 1280, nothing cut off | rendered run above, plus one hand-measured failure | Can't check as a whole; one half Kept, one half Broken |

No claim here the contract does not make, and no verdict here that was not run.
