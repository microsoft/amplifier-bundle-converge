# Introducing Amplifier Converge

> **Status: DRAFT — publish when every claim below is true.** Written ahead of the release on purpose: it is the plain statement of what Converge is *for*, and each claim maps to a contract in `contracts/`.

**You define what must be true. It builds toward it — with you, over time.**

## Why now

AI does more of the work every month, and an **amplified** person — one human, well-leveraged — now builds what recently took a team. Capturing that value means working above the level of tasks and code. Collaboration faces the same shift: teams move too fast, on efforts too large, for yesterday's coordination to keep pace. Converge is a way of working at that altitude.

## The idea

Converge introduces two AI roles most people have not met. A **manager session** is a long-running AI session that runs a project's work on your behalf, for days or weeks. **Worker sessions** are many short-lived AI sessions, each taking one bounded piece of work in isolation and returning with proof. You are neither. You are the **intent steward**: you set the direction and make the decisions only a person can.

You define that direction in a **vision** — the project as it will be when it is right — and in **contracts**: the specific promises it must keep, each short enough to read in a minute and precise enough to check. You work them out at the altitude of what you actually care about, in conversation with the system and, when you choose, with other people. The details are worked out and managed for you. The work unfolds over time and you are present throughout: long stretches run unattended, real decisions surface exactly when they need you, nothing is called done until it has been seen working. The vision and contracts mature as the work does. The direction is grown, not declared.

## One text, two audiences

The vision and contracts are also where people align — at the altitude of promises, not code review. A teammate's proposal and the manager session's proposal look and behave the same: what changes, the evidence, what does *not* change, your questions pinned to the paragraph. Review it yourself or have the manager session review it first. Your word ratifies it, and on a teammate's pull request your questions and answer post back to the request. The words you ratify are the words every session then obeys — an unbroken **through-line** from human agreement to AI guardrail.

## What you do

Your attention is the scarce resource, spent only where it is irreplaceable: **defining the direction** · **confirming the major decisions** as they arise — the system proposes, you decide · **taste and judgment** — deciding what *not* to build is its clearest form · the **critical thinking** that turns a proposal into a decision worth standing behind · and four kinds of call only you can make — ratify a change to the direction, make an irreversible choice, check what only a person or device can check, set priority or stop. Everything else is the system's job, visibly.

## What ships

**The method.** Ratified rules for writing a vision, deciding which commitments deserve a contract, locking them, changing locked contracts only by evidenced proposal, and deriving work from the gap between contract and reality.

**The manager session — the whole operation.** One `--app` install onto your existing Amplifier CLI. The manager session owns the queue: it derives work from the gap and from your feedback — never filing a raw note as a ticket, always reading it against the contracts and the work in flight first — plans what to build next and in what order, and shows you that plan. Its governing strategy is to **maximize the useful work that proceeds without you**: within your objective, budget, and lane count, it accounts for dependencies and collisions, fills spare capacity, and parks whatever needs your word while everything else continues. Waiting on you is never the bottleneck. It launches worker sessions as separate, independent sessions in isolated lanes, keeps the lanes full, notices silence, judges completion by **evidence rather than account**, integrates and verifies, re-checks the contracts, and writes you a brief in plain sentences for your return. Each worker session's piece ends one of three ways: done with proof, stuck with the cause, or needs your judgment. A guard makes locked contracts physically un-editable, by people and AI alike.

**The app — two places.** Amplifier Converge runs beside your project, on laptop or phone. **Direction** — the vision and contracts as one experience: what changed since you last read, whether each contract is kept, ask for a proposal on any paragraph, every proposal awaiting you. **Operation** — the manager session at work: your return brief, the plan, what runs against what waits on you, lanes running against lanes intended, evidence you can inspect, your limits, a place to drop feedback, every manager session you run. At most five things ever ask for your word. Five writes in total, and nothing else writes: answer with a word — ratified · ratified with edits · declined · later — raise or lower a priority, drop feedback, steer, ask for a proposal. The app keeps no data of its own. Whatever you can do in it, the manager session can do too. It begins as a companion web page shipped inside the bundle, your manager-session conversation still in your usual place; in time the whole experience, that conversation included, lives in the app.

## What it depends on

Proven pieces, composed rather than rebuilt: the shared work queue with custody, the parallel-lanes practice, worktrees and a terminal multiplexer, the lean base bundle. From a clean machine, one install brings them up, verified — or says plainly what is missing.

## What this is not

Not another issue tracker. Not a terminal dashboard. Not notifications. Not a code-review tool. Not one-shot magic. Not autonomy for its own sake — the point is that your attention, when spent, is high-leverage.

## Getting started

```
amplifier bundle add git+https://github.com/microsoft/amplifier-bundle-converge@main#subdirectory=behaviors/converge.yaml --app
```

Settle the vision first, then the contracts. Let the work derive itself.
