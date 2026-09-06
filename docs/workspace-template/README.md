# The participant kit — what is in this directory

Everything a repository needs to take part in Converge without anyone installing
the bundle: a colleague reading a contract, a coding agent from another tool, a
push that must be refused. Copy from here into your own repository.

**Eight files.** Every one is listed below, including the three you do not need
on day one — so that "I have them all" is something you can check rather than
assume.

| File | Copy it to | Needed on day one |
|---|---|---|
| `VISION.md.template` | `docs/VISION.md` | Yes — where the project is going, written as though already true |
| `CONTRACT.md.template` | `contracts/<name>.v1.md` | Yes — once per promise the project must keep |
| `AGENTS-addendum.md.template` | appended to `AGENTS.md`, or pasted whole if there is none | Yes — the standing rules every coding agent reads |
| `PINS.md.template` | `PINS.md` at the repository root | Yes — hard facts every session reads first |
| `pre-push-scan.sh` | `.githooks/pre-push` — **renamed**, see below | Yes — the guard that holds without the bundle |
| `converge-dir-README.md.template` | `<workspace>/.converge/README.md` | No — for the operation's own directory, when it first appears |
| `gitignore-addendum.txt` | appended to the workspace root's `.gitignore` | No — same directory, so a running operation's state is not committed |
| `GOAL-FILE.md.template` | one worker session's brief | No — the manager session writes these; it is here so the shape is on record |

Each template opens with an HTML comment telling you what to replace and to
delete the comment. Delete it — a template judged as a document is judged
without that block.

## The one that is not a copy

`pre-push-scan.sh` is the only file here whose name changes on the way in. Git
runs a pre-push hook at `.githooks/pre-push` and nowhere else, so copying it
under its own name leaves you with a hook directory git looks in and finds
nothing — and a guard that silently never runs. Four commands, once per
repository:

```
mkdir -p .githooks
cp docs/workspace-template/pre-push-scan.sh .githooks/pre-push
chmod +x .githooks/pre-push
git config core.hooksPath .githooks
```

`chmod +x` is not optional. A hook that is not executable is a hook git ignores,
and it reports nothing when it does.

**Prove it is really installed.** Run the scan by hand — it leaves 0 when the
push is clean and 1 when it refuses, naming each locked file:

```
./.githooks/pre-push origin/main
```

For the real thing: on a throwaway branch, edit a locked contract — one whose
first heading carries `(FROZEN <date>)` — with no `<contract>.vN-candidate.md`
beside it, and push. The push is refused. That refusal is how you learn the hook
is there. Delete the branch afterwards.

`uv run scripts/adopt-check.py` reports the same three facts in one line: hook
present, hook executable, `core.hooksPath` actually pointing at it.

## Where the rest of the day is written down

[`docs/ADOPTING.md`](../ADOPTING.md) — installing Converge, starting a manager
session, and checking that it took.
