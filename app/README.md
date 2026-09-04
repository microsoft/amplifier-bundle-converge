# The Converge companion app

    uv run --extra app python -m app.serve --host 0.0.0.0 --port 8788

On the LAN: <http://spark-1:8788> (192.168.1.5). As a service: `cp
app/converge-app.service ~/.config/systemd/user/ && systemctl --user enable
--now converge-app`. Tests: `uv run --extra app --with pytest --with httpx pytest -q app/tests`.

**Sign-in is your machine account, checked by PAM** — the same check `login`
makes; the app keeps no passwords. What it keeps is a signed cookie naming
you, good for twelve hours, signed with `~/.amplifier/converge-app.secret`
(created `0600` on first run). **There is no loopback exemption:** a request
from 127.0.0.1 is gated like any other, because when the server is bound to
the LAN, "it came from localhost" says nothing about who is asking. Only
`/login`, `/static`, `/branding` and `/healthz` answer without a cookie.

**What it watches** is `~/.amplifier/converge-app.toml` — one `[[managers]]`
block per manager session naming its `batch_dir`, `repos`, `tracker_project`,
and the explicit `tmux_socket` its lanes run on. With no file, every
`~/dev/hw-*/HIGHWAY.md` is discovered as a manager instead.

One more key on that block says **whose word counts**: `steward = "<name>"`.
`experience-collaboration.v1` Core 8 asks for that to be settled when the
session is registered, so it is read from the block and from nowhere else — a
block that names no steward answers with an empty one rather than with the name
of whoever is signed in. Everyone else is a teammate: their proposals get the
same reading and none of the authority. A discovered manager names no steward,
because it was never registered.

## What is real

Everything on the screens. No fixtures, no placeholders:

| On the page | Read from |
|---|---|
| lanes active / max | live `tmux -L <socket> list-sessions` · `.width` |
| lane state word | tmux liveness + `lane.log` mtime + `DONE.json`/`BLOCKED.md` (field guide §5) |
| lane title, evidence | the lane's goal file · `git rev-list --count main..<branch>` |
| waves, progress | `HIGHWAY.md`'s `## Lane board` when it keeps one; otherwise `manifest.tsv` lane-name prefixes, with `DONE.json` and merge commits for progress |
| objective, deadline, steers | `HIGHWAY.md` |
| return brief, timeline | `docs/workflow/OWNER-RETURN-LOG.md` |
| sections, history | the file itself · `git log --follow` |
| what changed | `git diff <your read point> <last commit> -U0`, hunk by hunk |
| a card's section | the heading path above the line, plus its numbered item |
| a card's source | `git blame` on the line: subject · short sha · date |
| your read point, your kept marks | `~/.amplifier/converge-app.state.json`, per steward |
| proposals | `*-candidate.md` beside the document — including the ones an ask makes |
| kept / gap / draft, confidence | `ledger/rows.yaml` (`draft` = nothing watches it yet) |
| throughput | `amplifier-work-tracker status`, merged lanes, `REOPENED` entries |

## Changes: since you last read

The Changes view answers "what moved since **you** last read this", not "what
moved in the last two commits". Your read point is a commit, kept per steward
in `~/.amplifier/converge-app.state.json` (`--state` overrides the path), and
**Mark all as read** moves it to the document's latest commit — after which the
list is empty until the document changes again. A steward who has never opened
a document starts at the commit before its last one, so a first visit shows the
most recent change rather than a blank page.

Between those two commits the reading is **git's own**: `git diff <since>
<head> -U0`, one hunk at a time. A hunk with no removed lines is **New** and
has no Before; one with no added lines is **Removed**; a hunk with both is
paired by how alike the sentences actually are, in order, so a sentence
inserted in the middle stays unpaired instead of shifting every Before/Now
couple after it. Each card says two different things and does not confuse
them: **section** is the heading path plus the numbered item it sits in
(`Principles › 8`), and **source** is the commit `git blame` names for that
line — subject · short sha · date.

Four things a steward can do to a card, and each one writes:

| On the card | What happens |
|---|---|
| Keep this change | remembered for you, server-side — it survives a reload and a different browser |
| Edit wording… | your words replace the sentence |
| Restore | the previous wording goes back — an addition is taken back out, a removal is put back |
| Mark all as read | your read point advances to the current commit |

Restore is also offered **at three wider scopes** from History — a paragraph, a
section, the whole document. Same write, more sentences; see *History* below.

Edit and Restore take one of two paths, and **the document decides which**. If
its H1 carries no locking word the file is rewritten and committed, authored
`<you> via Converge`, with a subject naming the document and the section. If
the H1 says `FROZEN` or `RATIFIED`, the document is not touched at all: the
wording is written to `<doc-stem>.vN-candidate.md` beside it, in the three-part
shape `documents.v1` §8 requires. The check is made in `app/writes.py`, on the
file, so forcing the control in the browser changes nothing.

### Answer with these choices

Keeping and dropping are already writes of their own — **Keep this change** is
`changes/{change_id}/keep`, remembered per steward on the server, and dropping
one is a Restore that has already put the earlier wording back. What was
missing was those choices reaching the **one** answer. So Changes offers
**Answer with these choices**, which opens the ratify-with-edits dialog on the
reading as it stands: *N of M changes are kept*, then the **Kept** list and the
**Not kept** list, each row its own section path and its own sentence. A list
with no rows is not drawn — keep everything and there is no *Not kept* heading,
keep nothing and there is no *Kept* one — but the count above them is always
both numbers, so neither list is silently missing.

The control appears **only while a proposal is open on that document**, because
an answer with nothing to answer would refuse. With none open the line says so
instead — *"Your keeping is remembered for you, and goes into the record with
your word when a proposal is open"* — rather than offering a button that would
fail when pressed.

Answering carries both lists into the record, **verbatim** — the steward's own
words first, then the choice ledger:

```
Granular choices carried into this answer — 6 of 7 changes kept.
Kept:
- Principles › 8: <the sentence>
…
Not kept:
- Principles › 3: <the sentence>
```

That whole block travels as the decision's note, and `app/writes.py` appends it
under **Note, verbatim:** in `docs/workflow/owner-ratifications-<date>.md`
beneath the decision, document, proposal and steward. It is **not a new kind of
ratification**: the word recorded is *ratified with edits*, already in the
vocabulary. The choices build that word; they do not add one.

## History: restoring, at four scopes

History carries a restore panel, and it offers all four scopes
`experience-direction.v1` §6 names — **a wording · a paragraph · a section ·
the whole document**. A paragraph is a change card's own section path
(`Principles › 8`); a section is the head of that path (`Principles`). Every
one of them is the same per-card `changes/{change_id}/restore` write, applied
one sentence at a time — no scope has a write of its own, and none of them
stages anything.

**Which snapshot a restore reaches, and which it cannot.** It reaches exactly
one: the wording as it stood at **your own read point**, because that is the
only earlier wording the server can still find. Restoring to any other row in
the history list is **not offered**. The app answers no route that reads a
document at an arbitrary commit, so a control for it would look like time
travel and not be one; the panel says so in its own Details, and the gap is
filed as `converge-4pq`. Only the sentences in this reading can be put back.

Before anything is written, the confirmation names the sentences (the first
eight, then *…and N more*) and which of the two paths this document takes.
Afterwards the outcome sentence separates commits from proposals using the
server's own `mode` for each write, never guessed from the payload's shape —
both modes carry a `file`, and reading that would have called a commit a
proposal.

Which of the two paths a restore takes is the same rule as an edit's, above:
a draft is committed in your name, a locked document gets
`<doc-stem>.vN-candidate.md` beside it and is not touched.

## The other writes

They are real too. A decision appends to
`docs/workflow/owner-ratifications-<date>.md`, carrying the kept and not-kept
lists verbatim when the answer came from *Answer with these choices*; feedback
creates `.converge/feedback/<ts>.md`; a steer rewrites `.width` and appends to
`HIGHWAY.md`. Nothing here has a demo mode.

## Ask: a scoped question, answered as a proposal

`POST /api/managers/{mid}/ask` with `{scope, repoId, docId, section, text}`,
where scope is `paragraph` · `document` · `all`. It answers with the proposal
it made — `{ok, scope, proposal, file, path, document, documentUntouched,
merged, drafted, draftedBy, said}` — so the client can send the steward to
Review to answer it.

`experience-direction.v1` clause 9 says the output of an ask is *always* a
proposal: never a silent edit, never a chat. So at every scope, locked document
or draft, this writes one file and only one file — the same
`<doc-stem>.vN-candidate.md` beside the document that a locked-document edit
produces, in the three-part shape `documents.v1` §8 requires. The document is
never opened for writing, and the answer says so (`documentUntouched`). A
second ask about the same document joins the open proposal, carrying its own
change *and* its own evidence, so the record never names one ask while the body
carries three.

Where the wording comes from is a choice, and the proposal always says which:

| `CONVERGE_ASK_DRAFTER` | What the replacement fence carries |
|---|---|
| unset (default) | the steward's own words, marked as not yet drafted |
| `agent` | wording from a headless `amplifier run` in the repository |

The drafting session reads `--output-format json` and takes only its `response`
— measured on 2026-09-04, reading all of stdout put the CLI's banner, its
token-usage table and its colour codes into a proposal as if a session had
proposed them. A session that fails, times out, is missing, or reports anything
but success does not lose the ask: the proposal is still written from the
steward's own words and names what went wrong.

## From the host: pull requests, read as proposals

The sixth surface (`app/collab.py`, plus the `collab.html` partial) is the host
half of collaboration. Git is the protocol and the repository host carries the
conversation; this panel is the lens on it. Open pull requests in each of the
manager session's `repos` are read with the host's own command line — `gh pr
list` for the panel, `gh pr view` for one — and laid out in **the same proposal
shape a `*-candidate.md` file produces**, so the review anatomy is identical
whatever the origin. Where a proposal came from is a value on it (`source`),
never a second layout.

| Route | What it does |
|---|---|
| `GET /api/collab/{mid}/pulls` | every open pull request across this session's repositories, as proposals (capped at 20, and the answer says the cap) |
| `GET /api/collab/{mid}/pulls/{number}` | one pull request and the conversation on it |
| `POST /api/collab/{mid}/pulls/{number}/comments` | a question asked here, arriving on the host as a comment |
| `POST /api/collab/{mid}/pulls/{number}/answer` | the steward's word, recorded and returned |
| `POST /api/collab/webhooks/host` | the door the host knocks on when something changed |
| `GET /api/collab/{mid}/freshness` | which mechanism is keeping this panel current |

**Answering writes twice, and reports both halves separately.** `app/writes.py`
appends the word to `docs/workflow/owner-ratifications-<date>.md` — the same
dated record every other decision lands in — and the same word is posted back to
the pull request it came from as a comment, in the steward's own words. The
response carries `recorded` and `returnedToOrigin` as two values, so a host that
refuses the comment never makes the record look unwritten. The four words are
`app/writes.py`'s four; this surface adds none.

**Freshness is not the steward's job**, and the panel says which mechanism is
carrying it rather than leaving anyone to guess: a **webhook** when the host can
call one, **polling every 60 seconds** otherwise. Today it is polling. The
webhook route exists and checks a shared secret from
`~/.amplifier/converge-app.webhook-secret` (`CONVERGE_COLLAB_SECRET_FILE`
overrides it, and with no secret file the route refuses rather than trusting the
caller), but every `/api/` path is behind the sign-in gate in `app/serve.py`, so
a call from the host answers 401 until that route is listed as public. A webhook
call counts as *being told* for fifteen minutes; after that the panel says
polling again rather than claiming a webhook it has not heard from.

**Nothing about the conversation is kept here.** No pull request, comment or
answer is stored by the app — every row is the host's own, read fresh. The only
state is *when the host last called*, held in memory per repository, so a restart
goes back to saying polling rather than claiming a webhook nobody has heard from.
This is also not a channel between two manager sessions: every destination is a
pull request on the shared host, so two stewards both running Converge still meet
as Converge → host → Converge.

**`gh` is required for this surface and this surface only.** Without it the panel
says so in plain words — *the host command line `gh` is not installed on this
machine, so no pull request can be read and no comment can be posted* — rather
than showing an empty list that looks like "no open pull requests". The rest of
the app runs unchanged.

## The console: the manager session, not a chat about it

The terminal pane **is the manager's own session** — what you type there is
what that session receives, sent as code points to
`POST /api/tmux/{socket}/{session}/keys`, never a summary the app relays. So
the word `Enter` typed into it is five letters, not the Return key. Nothing is
echoed into the pane by the app: the next capture of the pane is what appears,
so the screen can only ever show what the session itself did with the line.

The keyboard belongs to the manager's own session and to nothing else. Watching
a lane reuses the same pane, and that pane takes no keystrokes — the contract
promises the console carries the manager conversation and says nothing about
typing into somebody else's worker. When there is no session on the other end
the controls go quiet and the footer says why. Either way the footer says the
same thing about what this is: **not a chat**. It is not a conversation built
into the app, in this version or any planned one.

Its router (`app/tmux_view.py`) is optional: when it is absent, the rest of the
app runs unchanged — and with it absent there is no path for a keystroke, which
`app/tests/test_console_input.py` asserts rather than assumes.
