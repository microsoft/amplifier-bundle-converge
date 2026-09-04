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

Edit and Restore take one of two paths, and **the document decides which**. If
its H1 carries no locking word the file is rewritten and committed, authored
`<you> via Converge`, with a subject naming the document and the section. If
the H1 says `FROZEN` or `RATIFIED`, the document is not touched at all: the
wording is written to `<doc-stem>.vN-candidate.md` beside it, in the three-part
shape `documents.v1` §8 requires. The check is made in `app/writes.py`, on the
file, so forcing the control in the browser changes nothing.

The other writes are real too: a decision appends to
`docs/workflow/owner-ratifications-<date>.md`, feedback creates
`.converge/feedback/<ts>.md`, a steer rewrites `.width` and appends to
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
