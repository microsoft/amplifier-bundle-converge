# Adopting Converge — your first day

This page is for someone who heard of Converge this morning. It asks you to
understand nothing about how it is built. Follow it top to bottom and you end
the day with a **manager session** running against your own project: one
long-running AI session that plans the work, launches the sessions that do it,
checks their results itself, and writes you a brief when you come back.

Six steps. Two of them are one command each. The rest is you saying what you
want.

> If you want to know how any of it works, every explanation is linked at the
> bottom, after you have it running. None of it is needed to get there.

## Before you start

| You need | How you know you have it |
|---|---|
| Amplifier, installed and answering | `amplifier --version` prints a version |
| `uv` | `uv --version` prints a version |
| `git` 2.5 or newer | `git --version` prints 2.5 or above |
| A project you want moved toward something | It is a git repository on this machine |

The project can be one you started this morning with nothing in it, or one with
years of code in it. Both work, and step 5 says what differs.

## 1. Install it — one command

```
amplifier bundle add git+https://github.com/microsoft/amplifier-bundle-converge@main#subdirectory=behaviors/converge.yaml --app
```

It does not matter which directory you run this in. It adds Converge to your
Amplifier, not to one project.

> There is a second install path, for running Converge's one recipe end to end
> against a target repository. You do not need it today. `README.md` compares
> the two if you ever do.

## 2. Check it took — one command

An install can look fine and leave you with nothing: a second bundle registered
under the name `converge` makes the manager session disappear with no error
anywhere. This command is how you find that out in one line rather than by
typing a mode name and guessing why nothing happened.

```
uv run https://raw.githubusercontent.com/microsoft/amplifier-bundle-converge/main/scripts/adopt-check.py
```

No clone needed. When the install took, the last two lines read:

```
  The install took. The manager session is available here — start it with `amplifier`, then `/mode converge-manager`.
  (leaving 0)
```

When it did not, the same command says so and names what to do about it:

```
  [absent  ] Manager session mode                      (needed)
      `converge-manager` is not in this Amplifier's mode list. Typing `/mode converge-manager` will not start a manager session.
      Fix: Two known causes, in the order worth checking. One: the bundle is not installed here — run the install command from the README. Two: a second bundle is registered under the name `converge`, which makes the mode vanish with no error (converge-348) — run `amplifier bundle list --all`, and remove the duplicate with `amplifier bundle remove <name>`.
--------------------------------------------------------------------------
  The install did not take. `converge-manager` is not in this Amplifier's mode list, so there is no manager session to start. Read the remedy on that line.
  (leaving 1)
```

It leaves 0 when everything a manager session needs is there and 1 when
something it needs is missing, so it is safe to put in a script. It changes
nothing — it only looks. Run it again any time the manager session is not where
you expect it.

## 3. Stand in the right place

```
cd ~/dev/my-workspace     # or: cd ~/dev/my-project
```

Go to the **workspace root**: the directory holding `WORKSPACE-MANIFEST.json`,
the folder your repositories sit inside. If your project has no workspace around
it, the workspace root is the project repository's own root. There is no third
case.

This is the step people skip and the one that cannot be fixed afterwards. The
manager session builds a whole operation — one working copy per parallel worker
session, its plan, its logs, its record of anything it started — under wherever
you were standing when you typed the next command.

## 4. Start the manager session

```
amplifier
/mode converge-manager
```

**If the first attempt comes back refused rather than switching, type it again.**
The confirmation gate refuses once by design; the second call takes. A second
refusal is a different problem — go back to step 2 and read what the check says.

You know it took when the prompt itself changes:

```
[converge-manager]>
```

An ordinary session is not a manager session. If the prompt never shows
`[converge-manager]`, nothing below will happen, however the session answers.

## 5. Say what you want to be true

In your own words, in sentences. Three things:

1. **The outcome** — what must be true of this project when it is right.
2. **How wide to run** — how many worker sessions at once. Start at two or
   three; you can change it any time.
3. **Where the work comes from** — a queue you already keep, a list you paste
   in, or the gap between what you just said and what the code actually does.

From there the manager session plans the order, briefs and launches the worker
sessions, checks their results by re-running the check itself rather than
trusting an account of it, and writes you a brief every time you come back.

### The first wake, on either kind of project

A project with no contracts has nothing to derive work from, so the first thing
that happens is not work — it is reading and drafting. Which of the two shapes
you get depends on whether there is already code.

**A repository that already has code — adopting.** Say so in your first message,
and say what the project is for. In this order:

1. **The work in flight pauses.** Nothing new is launched against a repository
   whose direction is not written down yet.
2. **It reads what is there** — the code, the history, whatever documents exist
   — before proposing anything.
3. **It proposes a vision and first contracts, as drafts,** and stops. This is
   the moment it comes back to you. Nothing in your repository is law until you
   answer, in one word: *ratified* · *ratified with edits* · *declined* ·
   *later*.
4. **On your word, the ledger is seeded** — one row per checkable promise, each
   saying whether that promise is kept today.
5. **The queue is derived from the gap** between what you just agreed to and
   what the code actually does. Every item names the contract it serves.

Until step 3 has your answer, no worker session is launched. That is the design,
not a delay: lanes against an unagreed direction are work you will throw away.

**A blank repository — starting.** The same five steps with nothing to read
first. It begins at the vision: what this will be when it is right, written as
though already true. Everything after that is identical.

> **What is settled here and what is not.** The five steps above are quoted from
> a **proposed** clause — `contracts/operation.v1-candidate.md`, Core 14, "The
> first wake is investigate, then propose" — which is waiting for the steward's
> word and is **not ratified**. Until it is, this page describes the path the
> proposal names; it is not yet law, and the manager session's own rules carry
> no first-wake section, because a section keyed to an unratified clause is
> exactly what this method refuses to ship. Two things follow for you. The
> conversation in this step is a conversation — hold it deliberately rather than
> assuming the session will run it for you. And if you want to know where it
> stands, the item to read is `converge-njaj`, with `converge-jyg0` behind it.

## 6. Take the participant kit into your repository

Converge's promise has to hold for a colleague who never installs the bundle and
for a coding agent that is not an Amplifier session. That is what
[`docs/workspace-template/`](workspace-template/) is for.

The vision and contracts step 5 proposes are written from these same templates,
so on that path you are reading drafts rather than filling in blanks. Copy them
by hand when you would rather start something yourself, or when you want a file
step 5 does not produce — the guard, chiefly, which is yours to install.

The kit is **eight**
files — the directory also holds an index of them, which is not copied
anywhere — and here is every one, including the ones you do not need.

| File | Where it goes | Needed on day one |
|---|---|---|
| `VISION.md.template` | `docs/VISION.md` | Yes — where the project is going |
| `CONTRACT.md.template` | `contracts/<name>.v1.md`, once per contract | Yes — copy it again for each promise |
| `AGENTS-addendum.md.template` | appended to `AGENTS.md`, or pasted whole if there is none | Yes — the rules every coding agent reads |
| `PINS.md.template` | `PINS.md` at the repository root | Yes — the hard facts every session reads first |
| `pre-push-scan.sh` | `.githooks/pre-push` — **renamed**, see below | Yes — the guard that works without the bundle |
| `converge-dir-README.md.template` | `<workspace>/.converge/README.md` | No — for the operation's own directory, when it first appears |
| `gitignore-addendum.txt` | appended to the workspace root's `.gitignore` | No — same directory, so the operation's state is not committed |
| `GOAL-FILE.md.template` | one worker session's brief | No — the manager session writes these; it is here so the shape is on record |

[`docs/workspace-template/README.md`](workspace-template/README.md) is the same
list, kept beside the files themselves.

### Installing the guard, which is not a copy

The file ships as `pre-push-scan.sh` and git will only run it at
`.githooks/pre-push`. Copying without renaming leaves you with a hook directory
git looks in and finds nothing, and a guard that silently never runs:

```
mkdir -p .githooks
cp docs/workspace-template/pre-push-scan.sh .githooks/pre-push
chmod +x .githooks/pre-push
git config core.hooksPath .githooks
```

Do not skip `chmod +x`. A hook that is not executable is a hook git ignores.

### Proving the guard is really installed

Run the scan by hand against your integration branch. It leaves 0 when the push
is clean and 1 when it refuses, naming each locked file:

```
./.githooks/pre-push origin/main
```

For the real thing: on a throwaway branch, edit a locked contract — one whose
first heading carries `(FROZEN <date>)` — with no `<contract>.vN-candidate.md`
beside it, and push. The push is refused. That refusal is the guard working, and
it is the only way to know it is there. Delete the branch afterwards.

`uv run scripts/adopt-check.py` also reports this: it says whether the hook is
at `.githooks/pre-push`, whether it is executable, and whether `core.hooksPath`
actually points at it.

## What you have now

| Where | What |
|---|---|
| `<workspace>/.converge/<project>/` | Everything the operation stands up. One directory per project; nothing lands outside it, and nothing lands in your home directory. |
| `<workspace>/.converge/<project>/lanes/` | One working copy per worker session, each on its own branch. |
| `<workspace>/.converge/<project>/HIGHWAY.md` | The plan, rewritten every cycle: what is running, what waits on you, what was declined and why. |
| `<workspace>/.converge/<project>/infra.tsv` | Anything the run started that outlives a command, each line carrying its own teardown. |
| Your project repository | The work itself — commits, on branches, merged by the manager session after its own check. |

`.converge/` is a running operation's state, not your project's content, so the
workspace ignores it in git.

**What reaches you, and nothing else:** ratify a change to the direction; make
an irreversible choice; check what only a person or a device can check; set
priority or stop. Anything else that reaches you is a defect — say so, and it
gets filed as one.

**To close an operation:** sweep its infra ledger first — it is the only record
of anything the run started outside that directory — then delete the project's
`.converge/<project>/` folder. Your project is untouched.

## When it does not work

| What you see | What it is |
|---|---|
| `/mode converge-manager` refused once | The confirmation gate. Type it again. |
| Refused twice, or the mode is not offered | Run step 2's check. It names the cause and the fix. |
| The session answers but the prompt never shows `[converge-manager]` | An ordinary session. Nothing above applies to it. Start again at step 4. |
| A push refused, naming a locked contract | The guard working. Write a proposal beside the contract instead of editing it. |

## Where to read more — after it is running

- [`README.md`](../README.md) — what ships, and the two install paths compared.
- [`docs/CONTRACTS-README.md`](CONTRACTS-README.md) — what a contract is, how to
  write one, and how to propose a change to one. Start a colleague here.
- [`docs/VISION.md`](VISION.md) — where Converge itself is going.
- [`docs/PROTOCOL.md`](PROTOCOL.md) — the ratified rules in full.
- [`docs/design/mechanism-spec.md`](design/mechanism-spec.md) — how the
  machinery is built.
