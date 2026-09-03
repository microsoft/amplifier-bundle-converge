# The shape of the app, running

    uv run poc/serve.py --repo . --port 8098

Open <http://127.0.0.1:8098/>. It installs as an app from the browser's own
install button, and nothing is ever fetched from anywhere else.

Two places — **Direction** and **Operation** — and a **Manager Console** pane that
is not a third place: it stays open as you move between them. On a phone it rises
from the bottom; on a desktop it docks to the right.

## What is real, and what is not

Real, read from this project every time you ask: the manager session cards; the
return brief; the work queue counts; the lanes and their state words, read from
the run directory beside this project; the vision and the contracts; what changed
between a document's last two saved versions, sentence by sentence; the proposals
waiting for your word.

Made up for this proof of concept, and labelled as such on screen: today's
strategy, the plan in waves, and how sure the manager session has been over time.
Diagrams inside a document are shown as their source, not drawn.

The four things you can do — answer with a word, ask for a proposal, drop
feedback, steer — are real, and append one line each to `ratifications.jsonl`,
`asks.jsonl`, `feedback.jsonl` and `steer.jsonl` beside this file. Those are made
on first use and are not kept in the code record.

## The seam, and checking it

`console_connector.py` is the join between the console pane and a live session.
It ships one connector, which replays `fixtures/console-transcript.txt` so the
pane can be seen and sized. The real one attaches to the session the manager
session already runs in; its interface — `attach`, `send`, `sessions` — and the
two things it must get right are written out in that file.

    python3 poc/verify.py --url http://127.0.0.1:8098

drives a real browser at 390 and 1280, writes `screenshots/`, and fails on
sideways overflow, on a browser error, or if the console pane does not survive
the switch between places. `vendor/` holds xterm.js (MIT), unmodified.

**This implementation may be thrown away. The contracts are the keeper.**
