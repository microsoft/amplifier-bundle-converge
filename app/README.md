# The Converge companion app

    uv run --extra app python -m app.serve --host 0.0.0.0 --port 8788

On the LAN: <http://spark-1:8788> (192.168.1.5). As a service: `cp
app/converge-app.service ~/.config/systemd/user/ && systemctl --user enable
--now converge-app`. Tests: `uv run --extra app pytest app/tests/test_api.py`.

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
| what changed | sentence diff of the file's last two commits |
| proposals | `*-candidate.md` beside the document |
| kept / gap / draft, confidence | `ledger/rows.yaml` (`draft` = nothing watches it yet) |
| throughput | `amplifier-work-tracker status`, merged lanes, `REOPENED` entries |

The four writes are real too: a decision appends to
`docs/workflow/owner-ratifications-<date>.md`, feedback creates
`.converge/feedback/<ts>.md`, a steer rewrites `.width` and appends to
`HIGHWAY.md`. Nothing here has a demo mode.

The terminal pane is **read-only in this version** — it shows a lane's tmux
session and takes no keystrokes. Its router (`app/tmux_view.py`) is optional:
when it is absent, the rest of the app runs unchanged.
