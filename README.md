# Amplifier Converge

**You define what must be true. It builds toward it — with you, over time.**

Converge is a way of working above the level of tasks and code. You write down
where a project is going and what must be true of it; the work of getting there
is planned, run, and checked for you, and comes back to you only where a person
is irreplaceable.

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

## The two halves

**Direction** — the vision and the contracts as one experience: what changed
since you last read, whether each contract is kept, your questions on any
paragraph, every proposal awaiting your word.

**Operation** — the manager session at work: your return brief, the plan, what
is running against what waits on you, lanes running against lanes intended,
evidence you can inspect, your limits, a place to drop feedback.

Both halves are the project's own truth, read from the repository. The app holds
no data of its own.

## Install

**THE install path — the behavior (`--app`):**

```
amplifier bundle add git+https://github.com/microsoft/amplifier-bundle-converge@main#subdirectory=behaviors/converge.yaml --app
```

This composes Converge's **capability layer** onto whatever bundle is already
active: the four agents (`protocol-authority`, `reconciler`, `negotiator`,
`proposal-drafter`), the five procedure skills, the `hooks-candidate-guard` hook
(the guard that refuses edits to locked documents, on by default), the thin
awareness context, and — via a behavior-includes-behavior include — the
`amplifier-work-tracker` behavior that gives `reconciler` its `work_*` filing
tools. Use this to add Converge to an existing workspace or session.

**Full-workspace path — Converge as the primary bundle:**

```
amplifier bundle add git+https://github.com/microsoft/amplifier-bundle-converge@main
amplifier bundle use converge
```

This composes the root `bundle.md`, which assembles on the lean **anchors** base
and pulls in `amplifier-work-tracker` **and** the same behavior. Use this to run
the `seed-reconcile` recipe end-to-end against a target repo.

> **Host requirement.** The `seed-reconcile` recipe declares its own helpers
> (`schema_version: 2`) and resolves them only from that declared closure, never
> from the session it runs in, so it needs no particular host, not even the lean
> `anchors` base the rest of Converge assembles on.

### What differs between the two paths (honestly)

| | `--app` behavior | `bundle use converge` (root) |
|---|---|---|
| 4 agents · 5 skills · guard hook · awareness | ✅ | ✅ |
| Session base + everyday tools | supplied by whatever bundle is already active | ✅ the lean `anchors` base, pulled in by `bundle.md` |
| `seed-reconcile` recipe runnable | ✅ the recipe declares its own helpers (`schema_version: 2`) and resolves them from that closure, so this path no longer has to supply them | ✅ |
| `work-tracker` present (reconciler's `work_*` filing) | ✅ the behavior includes the work-tracker **behavior**, so `reconciler` gets `work_*` filing on this path too | ✅ pulled in by `bundle.md` |
| Agents' "no delegate / no skills / no shell" rules | behavioral — agent body instructions + explicit `tools:` blocks (per-role structural spawn policy is an upstream feature request) | behavioral (same) |

Both paths give the four agents, five skills, guard hook, awareness context, and
work-tracker filing. The root path additionally supplies the base — so for
end-to-end recipe runs against a target repo, prefer `bundle use converge`. For
lightweight composition onto a session that already has its own base, the
`--app` behavior is the quick path. Neither path imposes any session-wide
`spawn:` policy: a live probe (2026-09-02) showed a composed `spawn.exclude_tools`
strips tools from **every** spawned sub-agent in every session — unacceptable
collateral for a composable bundle, so it is deliberately absent everywhere.

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
- `src/amplifier_converge/` — the companion web page (the two halves). Run it
  beside a project with `amplifier-converge web --repo .`; it listens on
  loopback by default, on purpose.

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
[`docs/workspace-template/`](docs/workspace-template/).

## Where everything lives

| | Where |
|---|---|
| The ratified rules (source of truth) | [`docs/PROTOCOL.md`](docs/PROTOCOL.md) |
| The vision | [`docs/VISION.md`](docs/VISION.md) |
| The four contracts | [`contracts/`](contracts/) — indexed in [`docs/CONTRACTS-README.md`](docs/CONTRACTS-README.md) |
| The announcement — what Converge is for | [`docs/ANNOUNCEMENT.md`](docs/ANNOUNCEMENT.md) |
| Worked examples, one per contract | [`docs/examples/`](docs/examples/) |
| This repository's own contract check | [`ledger/rows.yaml`](ledger/rows.yaml), with runnable checks in [`ledger/checks/`](ledger/checks/) |
| The conformance kits the ledger runs | [`conformance/`](conformance/) |
| The deck — a six-minute walk-through | [`docs/presentation/amplifier-converge.html`](docs/presentation/amplifier-converge.html) |
| The explainer — the sit-down companion, about twelve minutes | [`docs/presentation/explainer/index.html`](docs/presentation/explainer/index.html) |
| The app (the two halves) | [`src/amplifier_converge/`](src/amplifier_converge/) |
| Design records — dated snapshots, not current law | [`docs/design/`](docs/design/) |
| The starter ledger format (a draft convention, not a contract) | [`docs/LEDGER-FORMAT.md`](docs/LEDGER-FORMAT.md) |

The deck and the explainer are self-contained HTML — no server, no build. Open
either file directly.

## Reading order

[`docs/PROTOCOL.md`](docs/PROTOCOL.md) → this README →
[`docs/ANNOUNCEMENT.md`](docs/ANNOUNCEMENT.md) →
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
