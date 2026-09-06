# Registration - how a manager session becomes visible

A manager session is only useful to a steward if the steward can find it. This
is the one line that makes that true:

**On every wake, write `<workspace>/.converge/<manager-id>/registration.toml`.**

    uv run scripts/register-manager.py --steward <name> --print

That is the whole convention. What follows is why it is shaped that way.

## What the file says

Ten fields and a repository list, all of them facts the session already has:

| Field | What it is |
|---|---|
| `id` | the project's own name - the one its work queue carries |
| `name` | what a steward reads on Home |
| `steward` | whose word counts on this session |
| `workspace` | the workspace root the session runs from |
| `batch_dir` | `<workspace>/.converge/<id>` - clause 5's directory |
| `plan_record` | the operating picture, rewritten each cycle |
| `tracker_project` | the work queue this session files against |
| `tmux_socket` | the socket the lanes run on |
| `manager_tmux` | this session's own terminal session |
| `last_seen` | the moment of this wake |
| `[[repos]]` | each repository steered, with its default branch |

## Why on every wake, and not once

`last_seen` **is** the heartbeat. The app reads it to answer `experience.v1`
Core 1's last reading - "quiet or silent" - and marks a session
*Silent - may have died* when the stamp is more than fifteen minutes old. A
stamp written once at first wake would report a dead session as alive forever,
which is worse than reporting nothing.

The second reason is the one that decided the shape. A manager session that
already exists - started before any of this, running right now - has no
registration and no reason to notice it is missing. Writing the file
**unconditionally** means every such session appears on Home the next time it
wakes, with nobody editing anything on its behalf. A "write it if it is not
there" version would leave every existing session invisible, which is the exact
defect this closes.

The cost is a few hundred bytes and a rename, once per wake. That is not a
number worth optimising against a session nobody can see.

## What is never guessed

Two fields are deliberately harder to fill than they look, and both are refused
rather than inferred:

- **`steward`** is not `$USER`. `experience-collaboration.v1` Core 8 says whose
  word counts is settled at registration, not read off whoever happens to be
  signed in - and the account the session runs as is exactly that inference.
  With nothing given, the field is written empty and the script says so.
- **`manager_tmux`** is not the ambient `$TMUX`. That names the socket and pane
  this process happens to sit in, which is a different fact from the session a
  steward would attach to. `app/config.py` refuses the same inference from the
  other side, and the two refusals are the same refusal.

Everything else is read from the surroundings - the working directory, git, a
few `CONVERGE_*` variables - and every one of them takes a flag.

One of those defaults is worth naming, because it is a guess about scope rather
than a fact: with no `--repo`, the script records **every git checkout directly
under the workspace root**. In a workspace holding one project that is right; in
a workspace holding eight it lists eight, and a manager session that steers one
of them should say so - `--repo <path>`, repeatable. The default is the
workspace's own contents, which is honest, but it is not a claim about what this
session steers.

## How the app finds it

`app/config.py` scans, on every request:

- every workspace root named in `workspaces` in the app's own
  `converge-app.toml`, or, when it names none, **the parent of the app's own
  repository** - which is the workspace root when the app is checked out
  beside the other repositories, and is the ordinary case;
- plus any path in `CONVERGE_WORKSPACES`, `:`-separated.

A hand-written `[[managers]]` block still wins over a registration of the same
id - a person's answer outranks a process's - and appears once, taking the
registration's `last_seen`, because when a session was last awake is a fact only
the session has.

## What this can prove, and what it cannot

It can prove a session is registered: the file is there and `last_seen` is
fresh. It cannot prove the session is *working* - a wake that writes the file
and then fails still writes the file. Freshness answers "did this session wake",
and nothing more; what it did with the wake is the plan record's answer, not
this one's.
