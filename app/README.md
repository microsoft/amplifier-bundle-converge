# The Converge companion app

    scripts/run-app.sh

That is the one command, and it is the one `README.md` names: it serves HTTPS
on <https://127.0.0.1:8788>, prints that URL, says how you sign in and how to
trust its certificate, and prints every workspace root it scanned for manager
sessions. Every interface is bound by default, and the banner prints the
address another device can open (for example, <https://your-hostname:8788>);
`--host 127.0.0.1` binds loopback only, for the SSH-tunnel case; `--port N`
moves it off 8788; anything else is handed to `app.serve` unchanged. Ctrl-C
stops it.

**HTTPS is always on** — there is no plain-HTTP mode. On first run the app
creates a small local certificate authority and a leaf certificate it signs
(`app/tls.py`), under `~/.amplifier/converge-app-tls` by default
(`--tls-dir`/`$CONVERGE_TLS_DIR` overrides it; `0600` on every private key,
`0700` on the directory, atomic writes, and the CA is never rotated once
made). `GET /setup` on the running app — public, no sign-in required, no
private key ever exposed — carries the CA's download link, its SHA-256
fingerprint, and how to trust it in your browser or OS; `GET /ca.crt` is the
one file it downloads. Trusting the CA once covers every future certificate
renewal; clicking through the one-time browser warning instead works too, for
browsing, but most browsers refuse to install this app as a PWA until the CA
is trusted.

**`amplifier-converge start` is the same command, resolved from this
package's own installed location** rather than a checkout you `cd` into —
`uv run --project <this bundle's resolved path> --extra app python -m
amplifier_converge.cli start` works from any workspace. `amplifier-converge
doctor` is the read-only twin: every dependency, PAM, tmux, the certificate's
expiry and SAN coverage, and every workspace/registration this app would
discover — never a side effect, never a generated certificate, never a
request for a secret. `amplifier-converge register` is a thin call into
`scripts/register-manager.py`'s own `main()` (same flags, see below).

Underneath it is one line, and running that line yourself is the same thing:

    uv run --extra app python -m app.serve --host 0.0.0.0 --port 8788

**As a Linux user service**, copy the included unit with `cp
app/converge-app.service ~/.config/systemd/user/ && systemctl --user enable
--now converge-app`. The unit runs the module line above directly rather than
the wrapper: a unit file already carries the working directory, the arguments
and the restart policy, so the wrapper's whole job — remembering `--extra app`,
choosing a bind, printing where to go — is already done by systemd and would
only be a second place for the port to drift. Change the port in one of them and
you have changed it in one of them. Tests: `uv run --extra app --with pytest
--with httpx --with playwright pytest -q app/tests`.

Browser automation is a test dependency, not an app runtime dependency; install
Chromium once with `uv run --with playwright playwright install chromium`.
Authority-bearing test fixtures name their steward explicitly, and rendered
tests navigate Home, choose a manager, then choose a view. A skipped browser
check is not proof. In particular, an offline-window flag alone may not cut off
a service worker's own network requests: offline boot needs a real controlled
transport outage, not a longer arbitrary sleep.

**Sign-in is your machine account, checked by PAM** — the same check `login`
makes; the app keeps no passwords. What it keeps is a signed cookie naming
you, good for twelve hours, signed with `~/.amplifier/converge-app.secret`
(created `0600` on first run). **There is no loopback exemption:** a request
from 127.0.0.1 is gated like any other, because when the server is bound to
the LAN, "it came from localhost" says nothing about who is asking. Only
`/login`, `/static`, `/branding`, `/healthz`, `/setup` and `/ca.crt` answer
without a cookie — the last two are read-only trust instructions and the
CA's own public certificate, never a private key.

**Every unsafe request is checked for same-origin and, once a `cv_csrf`
cookie exists, a matching CSRF token** — login and logout included, and every
`/api/` route (the console's keystrokes and the voice note among them). A
present-and-wrong `Origin`/`Referer` or CSRF token is always refused; neither
being present at all is not, because a same-origin browser page always sends
one or both once it has opened this app once, and the double-submit token
is what actually catches a forged cross-site request from a browser that
already holds this app's cookies. See `app/auth.py`'s module docstring for
the full reasoning. Repeated wrong passwords are throttled per caller
(`auth.LoginThrottle`), in memory, cleared by a restart.

**What it watches** is every manager session that has registered itself, plus
`~/.amplifier/converge-app.toml` — one `[[managers]]` block per manager session
naming its `batch_dir`, `repos`, `tracker_project`, and the explicit
`tmux_socket` its lanes run on. With no file at all, every
`~/dev/hw-*/HIGHWAY.md` is discovered as a manager beside the registered ones.
The next section says how registration works.

One more key on that block says **whose word counts**: `steward = "<name>"`.
`experience-collaboration.v1` Core 8 asks for that to be settled when the
session is registered, so it is read from the block and from nowhere else — a
block that names no steward answers with an empty one rather than with the name
of whoever is signed in. Everyone else is a teammate: their proposals get the
same reading and none of the authority. A discovered manager names no steward,
because it was never registered.

## How managers appear here

Nobody edits a file to put a manager session on Home. **On every wake, a manager
session writes its own registration** — `<workspace>/.converge/<manager-id>/registration.toml`,
by `scripts/register-manager.py` — naming itself, its steward, its workspace
root, the repositories it steers with their default branches, its plan record,
its tmux socket and session, its work queue, and the moment of that wake. This
app scans for those files on every request and shows what it finds.
`experience.v1` Core 2 asks that Home be the list of manager sessions you run,
and a list that only grows when somebody edits a config file is not that list.

**Where it looks**, in this order:

1. every path in `workspaces` in `~/.amplifier/converge-app.toml`, or — when it
   names none — **the parent of this app's own repository**, which is the
   workspace root whenever the app is checked out beside the workspace's other
   repositories, and is the ordinary case;
2. plus any path in `CONVERGE_WORKSPACES`, `:`-separated, for a host whose
   workspaces do not all sit in one place.

Both are printed at boot, one line per root, because a manager session missing
from Home is nearly always a root nobody scanned.

**A hand-written block still wins.** Name a manager in `[[managers]]` and that
block is what is shown, once, even if a registration of the same id exists — a
person's answer outranks a process's. What it takes from the registration is
`last_seen`, and the workspace root and plan record where the block named
neither: when a session was last awake is a fact only the session has, and
filling a hole is not overruling an answer.

**Last seen, and going silent.** The stamp *is* the heartbeat — the mode writes
the file unconditionally each wake, so how old it is, is how long since the
session woke. Under fifteen minutes a card reads *Last heard 3m ago*; past
fifteen it reads **Silent — may have died**, the same word `experience.v1` Core
6 fixes for a lane that has stopped answering, because it is the same reading. A
manager named only by hand has no stamp at all and reads neither: never having
registered is a different silence from having gone quiet, and this app does not
show one as the other. **Details — where these manager sessions came from**,
under the list on Home, says for each one whether it registered itself, was
named by hand, or was discovered from a batch directory — and where.

An **existing** manager session needs nothing done to it. It registers on its
next wake, because the mode writes the file whether or not one is already there.

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

**Which snapshot a restore reaches, and the one bound left.** It reaches **any
snapshot in this document's own history** — every row the History list shows.
Picking a row reads the document back at that commit: the read carries
`?since=<commit>` and so does each restore, so the wording that goes back is
the wording that stood there, not the nearest one this browser happened to be
holding.

Three things about that are easy to assume wrongly:

- **The `now` row is the steward's own reading, not a snapshot.** Between HEAD
  and HEAD there is nothing to put back, so the panel on first open is
  unchanged.
- **Reading a snapshot never moves the read point.** Looking at history is not
  reading, and the panel says so where a steward would otherwise assume it.
- **The bound reads deeper than the eight rows the view shows.** A
  whole-document restore commits once per sentence, and a shallower bound would
  push its own snapshot out of range partway through its own run.

The one thing a restore cannot reach is a commit that never touched this
document, and the server refuses it in plain words rather than by a code:
`<sha> is not a commit in this document's history. The snapshots this document
offers are: …`. That refusal is the whole of the bound, and the panel's own
Details says so.

Measured against this repository's own `docs/VISION.md` on a live server,
2026-09-04:

```
read at afd83c8b -> 200,  1 sentence(s) restorable
read at c2420ce3 -> 200, 17 sentence(s) restorable
read at e1747ba5 -> 200, 40 sentence(s) restorable
read at deadbeefcafe -> 400, "…is not a commit in this document's history…"
read point afterwards: afd83c8 (was afd83c8) — UNMOVED
```

This paragraph said the opposite until 2026-09-04 — that a restore reaches your
read point and nothing else, and that the gap was filed as `converge-4pq`. That
work landed; the screen's words moved with it and this file was the half that
could not, because it was outside that lane's ownership (`converge-gkx9`).

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
