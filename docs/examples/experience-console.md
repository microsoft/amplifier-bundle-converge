# Worked example — Manager Console v1

Contract: [`../../contracts/experience-console.v1.md`](../../contracts/experience-console.v1.md)
Kit: [`../../conformance/experience-console/`](../../conformance/experience-console/)

The pane that must not become a place, and the check that keeps it honest.
Every block below is output from a command run on 2026-09-04 against this
repository at `f718a20`, with the app served from this worktree on port 8811.

> The conversation with the manager session is the one thing a steward must not
> lose when switching places. Everything this contract refuses — a second
> conversation, a third place, a ratification typed into a terminal — is a way
> of losing it while appearing to keep it.

## Start with one promise

Clause 3, in full:

> **One console, one manager session, and it *is* that session.** What you type
> there is what the manager session receives, not a summary the app relays — so
> there is no second conversation to keep in step with the first.

The failure this clause guards against does not look like a failure. A pane
that shows the session, faithfully, live, and cannot carry a keystroke back is
indistinguishable from a working console until the moment someone types.

## Right and wrong, told apart

```
$ uv run conformance/experience-console/run.py conformance/experience-console/fixtures/sample-good --json-only
exit=0  {"pass": 10, "fail": 0, "skip": 0}  PASS

$ uv run conformance/experience-console/run.py conformance/experience-console/fixtures/sample-bad --json-only
exit=1  {"pass": 0, "fail": 10, "skip": 0}  FAIL
```

Ten rules, ten separations. The fixtures are captured app snapshots — the same
shape `--capture` writes — so a fixture is judged through exactly the code path
a live app is, and a passing fixture is not a different kind of evidence from a
passing body.

## The same check against the real body

```
$ uv run conformance/experience-console/run.py http://127.0.0.1:8811

experience-console.v1 conformance — http://127.0.0.1:8811 (live, 33 route(s))
asserts: contracts/experience-console.v1.md — static — read from what the app
served (shell, API payloads, client assets, its own route table); no browser is
launched
------------------------------------------------------------------------------
  [PASS] 1   the console is a pane beside the two places (['direction',
             'operation']) and the place switch neither lists it nor disturbs it
  [PASS] 2   the pane embeds the manager session as it already runs (hw:cvdemo)
             through the connector
  [FAIL] 3   the console's input is disabled; its send control is disabled; the
             app answers no route that carries a keystroke to the session, so
             there is no path for a typed line to arrive — the pane shows the
             session but is not it
  [FAIL] 4   no rule or control makes the pane resizable on a wide screen
  [PASS] 5   watching a lane opens in this pane, and leaving it puts the manager
             conversation back where it stood
  [PASS] 6   Operation is understood on its own terms, and nothing sends the
             reader to the console
  [PASS] 7   what needs your word arrives through the short list, never only
             through the console
  [PASS] 8   the console's submit reaches no ratification write and offers none
             of the answer words — a word typed here is a message
  [PASS] 9   the app says so in its own words ('read-only in this version')
  [FAIL] 10  the app answers ['/api/tmux/sessions'], which enumerates every
             terminal session on a socket
------------------------------------------------------------------------------
  VERDICT: FAIL  (pass=7 fail=3 skip=0)
```

Seven of ten clauses are kept in this body today.

## What the check refuses to claim

Rule 3's detail ends with a sentence that is the whole discipline of this
directory:

```
Whether a line ARRIVES is a live round trip this kit does not attempt;
it judges only whether a path exists at all
```

The kit found something real — there is no route at all — and then said exactly
where its own evidence stops. Rule 4 does the same:

```
Read from the stylesheet's rules; a rendered layout at two widths is not
judged here
```

A kit that quietly widened its claim to "the pane resizes" would be reporting a
judgment it never made. The rendered half of that question is answered by a
different check, in a different contract's example:
[`platform-web.md`](platform-web.md), where the pane is measured at 1280 and 390.

## The failure that is about reach, not display

Rule 10, in full:

```
the app answers ['/api/tmux/sessions'], which enumerates every terminal session
on a socket — the machine's other sessions, checkouts and queues are reachable
merely because they exist. The client itself calls it: False. The console pane
shows only this manager's own targets (61 of them), so the defect is the reach,
not the display
```

Nothing wrong is on the screen. The pane shows one manager session, as clause 10
asks. What the clause refuses is the *reachability*, and the kit is careful to
say which of the two it caught — the client does not call that route, so no
steward has ever seen another session's work. The fix is to remove the reach,
not to hide the list. Carried by `converge-tfu`.

## Clause traceability

| Clause | Rule | Where it appears above |
|---|---|---|
| 1 — a pane, not a place | 1 | live run, Kept |
| 2 — carries the session exactly as it already runs | 2 | live run, Kept |
| 3 — one console, one session, and it *is* that session | 3 | "Start with one promise"; "What the check refuses to claim" |
| 4 — resizable pane wide, sliding tray small | 4 | live run, Not yet — and the rendered half is elsewhere |
| 5 — Watch session reuses this pane | 5 | live run, Kept |
| 6 — the console is never the dashboard | 6 | live run, Kept |
| 7 — nothing needing your word arrives only here | 7 | live run, Kept |
| 8 — the console never ratifies | 8 | live run, Kept |
| 9 — not a native chat in v1, and nothing depends on it being one | 9 | live run, Kept |
| 10 — one manager's own work, reaching nothing else | 10 | "The failure that is about reach, not display" |

No claim here the contract does not make, and no verdict here that was not run.
