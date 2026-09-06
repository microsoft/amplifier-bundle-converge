# Amplifier Converge

**You define what must be true. It builds toward it — with you, over time.**

Converge is a way of working above the level of tasks and code. You write down
where a project is going and what must be true of it; the work of getting there
is planned, run, and checked for you, and comes back to you only where a person
is irreplaceable.

**New here? Start with [`docs/ADOPTING.md`](docs/ADOPTING.md) — your first day,
start to finish.** One command to install, one command to check it took, and the
exact words that start a manager session on your own project. It asks you to
understand nothing about how any of this works. Everything below is here for
after it is running.

## The three roles

- **You — the intent steward.** You set the direction and make the decisions
  only a person can make: ratify a change to the direction, make an irreversible
  choice, check what only a person or a device can check, set priority or stop.
  Anything else that reaches you is a defect.
- **The manager session** — one long-running AI session that runs a project's
  work on your behalf, for days or weeks. It owns the queue, plans the order,
  briefs and launches worker sessions, notices silence, verifies by its own
  re-run check rather than by a worker's account, and writes you a brief in
  plain sentences for your return.
- **Worker sessions** — many short-lived AI sessions, each taking one bounded
  piece of work in its own copy of the code and returning with proof. Each piece
  ends one of three ways: done with proof; stuck, with the cause; needs your
  judgment.

You write the direction in two documents. A **vision** — the project as it will
be when it is right, written as though already true. And **contracts** — the
specific promises the project must keep, each short enough to read in a minute
and precise enough to check against reality. Both are written for people.

A document begins as a draft and becomes **locked** when it says what it means,
carries a real example of right and wrong, can be checked against reality, and
you have read it and agreed. A locked document changes only by written
**proposal** backed by evidence — a cost actually paid or a failure actually
caught. Preference is not evidence. Nobody edits a locked document in place; the
guard refuses.

## The two places

**Direction** — the vision and the contracts as one experience: what changed
since you last read, whether each contract is kept, your questions on any
paragraph, every proposal awaiting your word.

**Operation** — the manager session at work: your return brief, the plan, what
is running against what waits on you, lanes running against lanes intended,
evidence you can inspect, your limits, a place to drop feedback.

Both halves are the project's own truth, read from the repository. The app holds
no data of its own.

## Install

One command. It composes Converge onto the Amplifier session you already have:

```
amplifier bundle add git+https://github.com/microsoft/amplifier-bundle-converge@main#subdirectory=behaviors/converge.yaml --app
```

That is the install. It brings Converge's **capability layer**: the four agents
(`protocol-authority`, `reconciler`, `negotiator`, `proposal-drafter`), the five
procedure skills, the `hooks-candidate-guard` hook (the guard that refuses edits
to locked documents, on by default), the thin awareness context, and — via a
behavior-includes-behavior include — the `amplifier-work-tracker` behavior that
gives `reconciler` its `work_*` filing tools.

### Advanced: Converge as the primary bundle

Two commands, for one case: a host that supplies neither the session base nor
the mode machinery.

```
amplifier bundle add git+https://github.com/microsoft/amplifier-bundle-converge@main
amplifier bundle use converge
```

This composes the root `bundle.md`, which assembles on the lean **anchors** base
itself and pulls in `amplifier-work-tracker` **and** the same behavior, so
nothing about the host can take the manager session away. Everything else is the
same either way — the four agents, the five skills, the guard hook, the
awareness context — and the shared work queue rides on both, so the contract
checker files and reads work whichever command you took.

> **Host requirement.** The `seed-reconcile` recipe declares its own helpers
> (`schema_version: 2`) and resolves them only from that declared closure, never
> from the session it runs in, so it needs no particular host, not even the lean
> `anchors` base the rest of Converge assembles on.

Neither command imposes any session-wide `spawn:` policy: a live probe
(2026-09-02) showed a composed `spawn.exclude_tools` strips tools from **every**
spawned sub-agent in every session — unacceptable collateral for a composable
bundle, so it is deliberately absent everywhere. The agents' "no delegate / no
skills / no shell" limits are therefore behavioral — agent body instructions
plus explicit `tools:` blocks; per-role structural spawn policy is an upstream
feature request.

### Did the install take?

An install can look fine and leave you with nothing: a second bundle registered
under the name `converge` makes the manager session mode vanish with no error
anywhere (`converge-348`). One command says which you have, and needs no clone:

```
uv run https://raw.githubusercontent.com/microsoft/amplifier-bundle-converge/main/scripts/adopt-check.py
```

It leaves 0 and says *the install took* when `converge-manager` is in this
Amplifier's mode list; it leaves 1 and names the two known causes and their
fixes when it is not. It also reports whether the work queue answers, whether
the locked-contract guard is installed in the repository you are standing in,
and whether a manager session has ever run here. It changes nothing — it only
looks. From a checkout of this repository, `uv run scripts/adopt-check.py` is
the same command.

If you cloned this repository, enable the locked-contract guard once per clone:

```
git config core.hooksPath .githooks
```

Installed is not started. **Where** you start a manager session decides where
everything it stands up lives, so start it as below rather than wherever your
terminal happens to be.

## Start your first manager session

Three steps. You need the bundle installed (above) and a project you want moved
toward something.

**1. Go to the workspace root.**

That is the directory holding `WORKSPACE-MANIFEST.json` — the folder your
repositories sit inside. If your project has no workspace around it, the
workspace root is the project repository's own root. There is no third case.

```
cd ~/dev/my-workspace     # or: cd ~/dev/my-project
```

This is the step people skip, and it is the one that cannot be fixed afterwards:
the manager session builds a whole operation — one working copy per parallel
worker session, its plan, its logs, its record of anything it started — under
wherever you were standing when you typed the next command.

**2. Start a session and put it in manager mode.**

```
amplifier
/mode converge-manager
```

**If the first attempt comes back refused rather than switching, type it again.**
The confirmation gate refuses once by design; the second call takes. You know it
took when the prompt itself changes to `[converge-manager]>` — an ordinary
session is not a manager session, however it answers. A second refusal, or a
mode that is not offered at all, is a different problem: run the check under
[Did the install take?](#did-the-install-take) above, which names the cause.

**3. Say what you want to be true, and where the work comes from.**

In sentences, in your own words — the outcome, how wide to run (how many worker
sessions at once), and whether work comes from a queue, a list, or from the gap
between your contracts and the code. The manager session plans the order, briefs
and launches the worker sessions, checks their results by re-running the check
itself, and writes you a brief every time you come back.

### Run the app

The manager session works whether or not you watch it. The app is where you
watch it — the two places above, read from your own repository. From a checkout
of this repository, one command:

```
scripts/run-app.sh
```

It prints where to open it — **<http://127.0.0.1:8788>** — and stops with
Ctrl-C. You sign in with your account on that machine, the same username and
password as `login`; the app keeps no passwords of its own. It stays on
loopback unless you say `--lan`, and takes `--port N` when 8788 is busy.

**What you see** is Home: the list of manager sessions you run, each with what
wants your word, lanes running against lanes intended, and its last brief line.
Open one and you are in Direction and Operation, with the Manager Console as a
pane beside either.

**How a manager session gets there** — nobody adds it. On every wake a manager
session writes its own registration to
`<workspace>/.converge/<manager-id>/registration.toml`, and the app scans for
those files on every request. So a session you started before you first ran the
app appears the next time it wakes, and the stamp it writes each wake is how the
page knows whether it is still there. Under the list, **Details — where these
manager sessions came from** says for each one whether it registered itself, was
named by hand, or was discovered — and where the app looked. A session missing
from Home is nearly always a workspace root nobody scanned, and the command
prints every root it scanned as it starts.

To keep it running across logout and reboot, run it as a service —
[`app/README.md`](app/README.md) carries the unit file and the rest of the
app's operation.

### What appears where

| Where | What |
|---|---|
| `<workspace>/.converge/<project>/` | Everything the operation stands up. One directory per project; nothing lands outside it, and nothing lands in your home directory. |
| `<workspace>/.converge/<project>/lanes/` | One working copy per worker session, each on its own branch. |
| `<workspace>/.converge/<project>/HIGHWAY.md` | The plan, rewritten every cycle: what is running, what waits on you, what was declined and why. |
| `<workspace>/.converge/<project>/infra.tsv` | Anything the run started that outlives a command, each line carrying its own teardown. |
| Your project repository | The work itself — commits, on branches, merged by the manager session after its own check. |

`.converge/` is a running operation's state, not your project's content, so the
workspace git-ignores it. Templates for the directory's own README and the
`.gitignore` line are in
[`docs/workspace-template/`](docs/workspace-template/).

To close an operation: sweep its infra ledger first — it is the only record of
anything the run started outside that directory — then delete the project's
`.converge/<project>/` folder. The project is untouched.

## What ships

- `agents/protocol-authority.md` — the carrier of the ratified rules. Ask it any
  interpretive question ("does this conform? am I allowed?").
- `agents/reconciler.md` — the **ratchet**: it derives the conformance ledger
  from a repo's locked contracts, re-checks it after every change, catches drift
  in both directions, and files what it finds. The one agent that writes; it
  never interrupts you synchronously.
- `agents/negotiator.md` — turns investigation evidence into decision-level
  minutes: options, a recommendation, and the one decision you must make.
  Read-only; returns needs rather than re-routing.
- `agents/proposal-drafter.md` — authors a proposal beside a locked document
  (the target line · the exact change · real evidence · what does **not** change ·
  the place for your word) and **stops**. Never edits the locked file, never
  ratifies.
- `skills/` — five procedures: `seam-test` (does this warrant a contract?),
  `proposing-a-change` (how to write a proposal), `freeze-bar` (the four
  conditions for locking a document — PROTOCOL.md §5 calls this the Freeze Bar),
  `ledger-disposition` (the contract-check vocabulary and row shape),
  `lane-brief` (briefing a worker session honestly).
- `modules/hooks-candidate-guard/` — the guard. A `tool:pre` hook, on by default,
  that structurally denies a direct write, edit, patch, or shell-laundered write
  to a locked contract or `VISION.md`. Changes land only via a ratified proposal
  sibling. See that module's README for the proposal filenames it recognizes and
  its documented non-coverage.
- `recipes/seed-reconcile.yaml` — the one recipe: derive and refresh the ledger
  from a target repo's contracts, detect drift in both directions, file what it
  finds. Its steps use only the lean base's helpers plus Converge's own
  `reconciler` for every write.
- `modes/converge-manager.md` — the manager-session mode: the operating loop,
  keyed clause by clause to `contracts/operation.v1.md`. Where the mode and a
  clause disagree, the clause wins.
- `app/` — **the app you open beside a project**: Home, the two places, and the
  Manager Console as a pane beside either. One command from a checkout of this
  repository, `scripts/run-app.sh`, which serves it on
  <http://127.0.0.1:8788>. This is the body the experience family is written
  against and the five experience kits read. [Run the app](#run-the-app) above
  starts it; [`app/README.md`](app/README.md) carries the rest of its operation.
- `src/amplifier_converge/` — the Python package the app reads through, and
  **it is not the app above**. Its *readers and writers* turn a repository into
  the words on a page — documents, ledger, work queue, lanes, proposals, and the
  four writes `surface.v1` named before the experience family superseded it on
  2026-09-03 (the app itself carries `experience.v1`'s five) — and `app/` uses
  one of them (`app/data.py`
  says whether a promise is kept through `amplifier_converge.reading.kept`).
  [`src/amplifier_converge/README.md`](src/amplifier_converge/README.md) says
  what is used by what.

**Retired:** the earlier server-rendered page in `src/amplifier_converge/web/`,
and the `amplifier-converge web` subcommand that served it, were removed on
2026-09-06 on the intent steward's word, in commit `eea3166`.

## The participant kit

The through-line has to reach a colleague who never installs this bundle, and a
coding agent that is not an Amplifier session. Every converged repository
therefore carries four files, and this repository carries its own:

| File | What it is for |
|---|---|
| [`docs/CONTRACTS-README.md`](docs/CONTRACTS-README.md) | The contract anatomy, the index of contracts, when a document locks, and how to propose a change. Start a colleague here. |
| [`AGENTS.md`](AGENTS.md) | The addendum every coding agent reads: converge toward the vision, never edit a locked contract, propose instead, where the ledger is, how to run the conformance kit. |
| [`PINS.md`](PINS.md) | Hard facts every worker session reads first. |
| [`.githooks/pre-push`](.githooks/pre-push) | A pre-push scan that refuses edits to locked contracts, so the rule holds even without the bundle. |

Templates for a project adopting the method live in
[`docs/workspace-template/`](docs/workspace-template/) — eight files, each one
listed in [that directory's own README](docs/workspace-template/README.md) with
where it goes and whether you need it on day one. The one whose name changes on
the way in is the pre-push scan: git runs it only at `.githooks/pre-push`, so it
is copied under that name and made executable, not copied as it stands.
[`docs/ADOPTING.md`](docs/ADOPTING.md) walks the whole of it.

## Where everything lives

| | Where |
|---|---|
| The adopter's first day — install, check, start | [`docs/ADOPTING.md`](docs/ADOPTING.md) |
| The check that says whether the install took | [`scripts/adopt-check.py`](scripts/adopt-check.py) |
| The ratified rules (source of truth) | [`docs/PROTOCOL.md`](docs/PROTOCOL.md) |
| The vision | [`docs/VISION.md`](docs/VISION.md) |
| The contracts — three govern the method, a family governs the app | [`contracts/`](contracts/) — indexed in [`docs/CONTRACTS-README.md`](docs/CONTRACTS-README.md) |
| The announcement — what Converge is for | [`docs/ANNOUNCEMENT.md`](docs/ANNOUNCEMENT.md) |
| Worked examples, one per contract | [`docs/examples/`](docs/examples/) |
| This repository's own contract check | [`ledger/rows.yaml`](ledger/rows.yaml), with runnable checks in [`ledger/checks/`](ledger/checks/) |
| The conformance kits the ledger runs | [`conformance/`](conformance/) |
| The deck — a six-minute walk-through | [`docs/presentation/amplifier-converge.html`](docs/presentation/amplifier-converge.html) |
| The explainer — the sit-down companion, about twelve minutes | [`docs/presentation/explainer/index.html`](docs/presentation/explainer/index.html) |
| The app you open beside a project (the two places) | [`app/`](app/), started by [`scripts/run-app.sh`](scripts/run-app.sh) and documented in [`app/README.md`](app/README.md) |
| Design records — dated snapshots, not current law | [`docs/design/`](docs/design/) |
| The starter ledger format (a draft convention, not a contract) | [`docs/LEDGER-FORMAT.md`](docs/LEDGER-FORMAT.md) |

The deck and the explainer are self-contained HTML — no server, no build. Open
either file directly.

## Reading order

**Using it:** [`docs/ADOPTING.md`](docs/ADOPTING.md) — and that is the whole of
it. The first day needs no other document.

**Understanding it, afterwards:** this README →
[`docs/ANNOUNCEMENT.md`](docs/ANNOUNCEMENT.md) →
[`docs/PROTOCOL.md`](docs/PROTOCOL.md) →
[`docs/design/mechanism-spec.md`](docs/design/mechanism-spec.md) → the
presentation.

The rules and the contracts stay always-true. Design records carry a dated
snapshot banner and are read as history, not as current law.

## What it does not do

This bundle is stateless know-how. It does **not** own any project's vision,
contracts, work, or results; it does **not** ratify anything — that word is
yours, in so many words; and it does **not** store any repo's documents or
ledger. Those live in each target repo. It does not become another issue
tracker, monitoring console, notification stream, or code-review tool, and it
does not alter the tools of other work in your session.

## Contributing

> [!NOTE]
> This project is not currently accepting external contributions, but we're actively working toward opening this up. We value community input and look forward to collaborating in the future. For now, feel free to fork and experiment!

Most contributions require you to agree to a
Contributor License Agreement (CLA) declaring that you have the right to, and actually do, grant us
the rights to use your contribution. For details, visit [Contributor License Agreements](https://cla.opensource.microsoft.com).

When you submit a pull request, a CLA bot will automatically determine whether you need to provide
a CLA and decorate the PR appropriately (e.g., status check, comment). Simply follow the instructions
provided by the bot. You will only need to do this once across all repos using our CLA.

This project has adopted the [Microsoft Open Source Code of Conduct](https://opensource.microsoft.com/codeofconduct/).
For more information see the [Code of Conduct FAQ](https://opensource.microsoft.com/codeofconduct/faq/) or
contact [opencode@microsoft.com](mailto:opencode@microsoft.com) with any additional questions or comments.

## Trademarks

This project may contain trademarks or logos for projects, products, or services. Authorized use of Microsoft
trademarks or logos is subject to and must follow
[Microsoft's Trademark & Brand Guidelines](https://www.microsoft.com/legal/intellectualproperty/trademarks/usage/general).
Use of Microsoft trademarks or logos in modified versions of this project must not cause confusion or imply Microsoft sponsorship.
Any use of third-party trademarks or logos are subject to those third-party's policies.
