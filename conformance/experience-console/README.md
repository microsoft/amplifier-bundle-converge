# experience-console.v1 conformance kit

The runnable definition of **"the Manager Console keeps its promises."** Point it
at the companion app — the running server, or a snapshot captured from it — and
it mechanically asserts
[`contracts/experience-console.v1.md`](../../contracts/experience-console.v1.md)
against what the app actually serves.

Stdlib only, and **no browser is launched**.

## The target is the app, and the app is not a page

Same target model as the other two experience kits — the served `html`, the
`json` payloads, the `js`/`css` client, and the app's own `openapi` route table.
See [`../appsnapshot.py`](../appsnapshot.py).

Most of this contract is **structural**, which is the happy case for a static
read: whether the console is a pane beside the two places or a third place,
whether anything needing a steward's word is reachable only from it, whether the
console's own form can reach the ratification write, what the stylesheet does to
it at a small width.

## Run it

```sh
uv run --extra app python -m app.serve --port 8788
export CONVERGE_APP_COOKIE="…"     # the app's own signer; no loopback exemption
uv run conformance/experience-console/run.py http://127.0.0.1:8788
```

A JSON report on **stdout**, a human summary on **stderr**, exit **0** unless a
rule FAILs. `--json-only` suppresses the summary; `--capture <dir>` writes a
snapshot that is a target in its own right.

## What it checks

Rows are numbered to the contract's **Core clause** numbers — rule 7 judges
Core 7. **Every one of the ten Core clauses has a row**, and
`test_every_core_clause_has_a_row` fails if one does not.

| # | Clause | The promise this operationalizes | How the kit checks it, against the app |
|---|---|---|---|
| 1 | Core 1 | "The console is a pane, not a place" | The place switch must offer exactly the two places and never the console; the console must not be nested inside either view; and the place-switch renderer must not touch the console's open state or empty its body — switching leaves it as it was. |
| 2 | Core 2 | "V1 carries the manager session exactly as it already runs" | The manager session must name a live terminal session, the app must answer a connector route, and the console must attach to it. |
| 3 | Core 3 | "One console, one manager session, and it *is* that session" | The console must take input, its send control must be live, and a route must exist that carries a keystroke to the session. Whether a typed line **arrives** is a live round trip this kit does not attempt, and the detail says so. |
| 4 | Core 4 | "Wide screen: a resizable pane. Small screen: a sliding tray" *(IDIOM)* | Read from the **stylesheet's own rules**: a small-width rule that makes the console a tray, a control that dismisses it, and a rule or handle that makes the pane resizable when wide. A rendered layout at two widths is not judged here. A target that served no stylesheet **SKIPs** with that reason — never a FAIL against a body that may be fine. |
| 5 | Core 5 | "Watch session reuses this pane" | Watching a lane must open in this pane rather than change place, and leaving it must put the manager conversation back where it stood. |
| 6 | Core 6 | "The console is never the dashboard" | Nothing in Operation may send the reader to the console to make sense of it, and Operation must carry its own reading — the plan, the lanes, the brief, the flow, confidence. |
| 7 | Core 7 | "Nothing that needs your word arrives only here" | A short list and a route that lists what needs your word, and **no decision offered inside the console** — a steward who never opens it must miss nothing. |
| 8 | Core 8 | "The console never ratifies" | The console's own submit must reach no ratification write, and the console must not offer the answer words themselves. |
| 9 | Core 9 | "It is not a native chat in V1, and nothing may be built to depend on it being one" | The app must say so in its own words, and nothing outside the console may depend on it being a conversation. |
| 10 | Core 10 | "It shows one manager session's own work and reaches nothing else" | The console's targets must trace to this manager session, and **no served route may enumerate terminal sessions beyond it** — the machine's other sessions, checkouts and queues must not be reachable merely because they exist. |

## What a static read buys, and what it does not

Two things it deliberately does not do, and says so rather than pretending:

- **Rule 3 never claims a round trip.** It judges whether a path exists for a
  typed line at all, not that the line arrives. `test_a_live_round_trip_is_never_claimed`
  asserts the detail says so.
- **Rule 4 reads the stylesheet, not a viewport.** It asserts the rules that
  make a tray and a resizable pane exist. Where a target served no stylesheet it
  SKIPs with the reason, which `test_rule_4_skips_rather_than_fails_when_no_stylesheet_was_served`
  pins.

Handlers are read the same way as in the other two kits: string literals are
blanked first, because **a write is a call, not a word in a message.**

## Fixtures (the kit's own proof)

Both are **captured app snapshots**, the shape `--capture` writes.

- `fixtures/sample-good/` — a console that is a pane beside two places, carrying
  the manager's own session through the connector, with a live input and a route
  that carries a keystroke; a stylesheet with a tray rule and a resizable pane; a
  watch that reuses the pane and returns the conversation; an Operation that reads
  on its own terms; a short list and a needs route with no decision in the console;
  a submit that reaches no ratification write; the app saying in its own words that
  this is the session and not a chat; and no route enumerating anything else.
  **PASS on all ten rules.**
- `fixtures/sample-bad/` — a **Console** tab in the place switch, no session named
  and no attach, a disabled input and send control, a stylesheet with no tray or
  resize rule, no watch at all, an Operation telling the reader to open the
  console, no short list and a **Ratified/Declined** pair inside the console, a
  submit reaching the decision write, nothing saying it is not a chat, and an
  `/api/tmux/sessions` route enumerating every session on a socket. **FAIL on all
  ten.**

Both are rewritten by
[`../experience-fixtures/make_fixtures.py`](../experience-fixtures/make_fixtures.py).

## Self-test

```sh
uv run --with pytest pytest conformance/experience-console/tests/ -q
python3 conformance/experience-console/tests/test_conformance.py   # no deps
```

`test_every_rule_has_a_negative_fixture` is load-bearing. Rule 4's conditional
SKIP is exercised directly against a stylesheet-less snapshot rather than being
pinned in `EXPECTED_SKIPS`, so a rule cannot drift into SKIP against a real
target without `test_skip_set_is_pinned` going red.

## Measured against the running app

2026-09-03, against `http://127.0.0.1:8788`: **PASS 7 · FAIL 3 · SKIP 0**. The
three are true findings — the console shows the session but is not it (input and
send are disabled, and no route carries a keystroke); the pane is a tray at a
small width but is not resizable when wide; and `/api/tmux/sessions` enumerates
every terminal session on the socket, so the console's *reach* is not bounded to
this manager session even though its *display* is.

A FAIL here is a **true finding, not a bug in the kit to be tuned away.**
