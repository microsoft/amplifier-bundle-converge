# Onboarding audit — 2026-09-04

What an early adopter actually meets today, on both paths, read from the files
themselves. Every finding names the file and the line a reader reaches it at.

**How this was done.** The repository was read twice. First as a naive reader:
`README.md`, then only what the README points to, in the order it points there,
with no prior knowledge. Then, and only then, as an insider: `AGENTS.md`,
`PINS.md`, `modes/converge-manager.md`, `context/**`, `recipes/**`, `skills/**`,
`behaviors/converge.yaml`, `contracts/**`. The split matters — several things
that look present from the inside are unreachable from the outside, and that gap
*is* the finding.

**The bar**, as the steward set it. Ready for early adopters means:

- **(a)** one install command;
- **(b)** one documented way to start a manager session from inside the
  Amplifier CLI, in a project directory;
- **(c)** it works on a **new** project (blank repo → investigate → vision →
  contracts → seed → queue) and on an **existing** one (adopt: pause the work in
  flight, investigate, propose vision and contracts, wait for the steward's
  word, seed the ledger, file the items that bring the repo into alignment);
- **(d)** an adopter needs to know nothing about how it works.

## Verdict

| | The bar | Today | The one sentence |
|---|---|---|---|
| **(a)** | One install command | **Not met** | Two commands, a table to choose between them, and the README calls one "THE install path" then recommends the other. |
| **(b)** | One documented way to start a manager session | **Not met** | Zero. No document a reader reaches names a command. The mode file documents how to *leave* the mode and never how to enter it. |
| **(c)** | New project and existing project | **Not met** | Neither path is written down. The only adoption procedure anywhere is "copy the five files by hand". |
| **(d)** | Needs to know nothing about how it works | **Not met** | The install section explains the composition; the reading order opens with the rulebook; there is no page whose subject is the adopter's first day. |

Two of these cannot be *judged* against the contracts as they stand, because the
contracts do not say what the bar says. That is the most important finding here
and it is separated out below, under "Two things no contract covers".

---

## (a) One install command — **not met**

### a-1 · Two paths, and the reader must choose

`README.md:51–100` is one section with two commands in it.

- `README.md:53` — "**THE install path — the behavior (`--app`)**", then the
  `amplifier bundle add … --app` command at `:56`.
- `README.md:67` — "**Full-workspace path — Converge as the primary bundle:**",
  then two more commands at `:70–71`.
- `README.md:83` — a heading, "What differs between the two paths (honestly)",
  and a five-row comparison table at `:85–91`.

A reader who wants one command is given two and a table. The table is honest and
well made; that is not the problem. The problem is that reading it is a task,
and it arrives at the exact moment the reader is trying to type one line.

### a-2 · The README recommends against its own "THE" path

`README.md:53` names the `--app` behavior **THE** install path. `README.md:93–96`
then says:

> "The root path additionally supplies the base — so for end-to-end recipe runs
> against a target repo, prefer `bundle use converge`."

An adopter's first real act on a project is a run against a target repo. So the
document tells the same reader, forty lines apart, that path one is *the* path
and that path two is preferred for what they are about to do. Whichever they
pick, the README told them the other.

### a-3 · Neither command says where to run it

Neither `README.md:56` nor `README.md:70–71` is preceded by a `cd`. Nothing says
whether the install is global to the CLI or scoped to a project directory. For
`(b)` — "in a project directory" — this is the first place the trail goes cold.

### a-4 · Already owned elsewhere, not re-filed

`PINS.md:140–142` records a handoff: the README needs one line under setup,
`git config core.hooksPath .githooks`, and the lane that found it may not edit
`README.md`. `converge-x40` is open on the adjacent host-requirement sentence.
Noted so the next reader does not file it a third time.

---

## (b) One documented way to start a manager session — **not met (zero)**

This is the sharpest gap in the audit. The manager session is the product —
`README.md:16–20` describes it as the thing that runs a project on your behalf —
and no document a reader can reach tells them how to start one.

### b-1 · No command, anywhere a reader goes

Searched across `README.md`, `AGENTS.md`, `PINS.md`, and `docs/*.md` for `/mode`
and for `mode(operation=`: **no match in any of them.** The three `amplifier`
commands in the entire reader-facing surface are the three install commands
(`README.md:56`, `:70`, `:71`).

### b-2 · The mode file says how to leave, never how to enter

`modes/converge-manager.md` is 322 lines and is named in `README.md:131` as "the
manager-session mode". Its final line, `:320–321`:

> "Use `/mode off` when the project is handed off (clause 13) or the engagement
> is closed."

That is the only mode syntax in the file. A reader is told how to exit a mode
they were never told how to enter.

### b-3 · The one sentence that names it is not addressed to a person

`context/converge-awareness.md:34–35` says:

> "To act as the manager session, use the **`converge-manager` mode**
> (`@converge:modes/converge-manager.md`)."

This is context injected into a session — the model reads it, the human never
does. And it names no command either.

### b-4 · Entering the mode is gated, and the gate is documented nowhere

`evaluations/turnkey/manager-objective.md:15–17` tells its own agent that
`mode(operation="set", name="converge-manager")` "is gated" and must be called
again. A person who finds the mode name by luck, types it once, sees a refusal,
and concludes it does not work has done nothing wrong — nothing they can read
says the first refusal is the design.

### b-5 · There is a known way for the mode to be silently absent, with no check offered

`behaviors/converge.yaml:124–141` records, measured, that the `modes:` block is a
declaration rather than the mechanism, that modes arrive by auto-discovery, and
that a duplicate `converge` namespace makes the mode vanish "with or without this
block" (filed `converge-348`). So "is the manager session even available here?"
has a real, silent failure mode — and `README.md`'s install section ends without
one command to confirm the install did anything. The adopter has no way to tell
a working install from a broken one.

---

## (c) New project and existing project — **not met**

### c-1 · The only adoption procedure in the repository is manual

`docs/CONTRACTS-README.md:151–156`, "Taking this to your own project", in full:

> "`docs/workspace-template/` holds the participant kit … Copy the five files,
> fill in the placeholders, and enable the hook with
> `git config core.hooksPath .githooks`."

That is the whole of it. Copy, fill in, enable. It starts no manager session,
investigates no repository, drafts no vision, derives no contract, seeds no
ledger, and files no work. Set beside `README.md:5–8` —

> "You write down where a project is going and what must be true of it; the work
> of getting there is planned, run, and checked for you"

— the promise and the procedure describe two different products. The adopter is
asked to do by hand precisely the work the manager session exists to do.

This is also the only place the word "adopt" leads to anything: it appears once
in the reader-facing surface, at `README.md:151`, pointing at the template
directory.

### c-2 · "Copy the five files" — the directory holds six

`docs/CONTRACTS-README.md:154` names five: a vision template, a contract
template, an `AGENTS.md` addendum, a pins template, and the pre-push scan.
`docs/workspace-template/` contains six files; the unnamed sixth is
`GOAL-FILE.md.template`. A reader who follows the instruction leaves one behind
and is not told which. The directory has no index of its own, so nothing else
corrects the count.

Related, smaller: the instruction says "enable the hook", but the file is
`docs/workspace-template/pre-push-scan.sh` and the hook path is
`.githooks/pre-push`. The rename step is documented only inside the script's own
comments (`docs/workspace-template/pre-push-scan.sh:18–20`), which is a place the
reader has not been sent.

### c-3 · The manager mode has no first day

`modes/converge-manager.md:293` heads the operating loop "**on every wake**", and
its steps run: heartbeat → status → refill to width → verify and merge ended
lanes → weave in feedback → rewrite the picture → clear the wake signal
(`:299–319`). Every one of those presupposes contracts, a ledger, a queue with
ready items, and a lane width already in existence.

There is no branch for wake one. Worse, clause 1 (`:42–50`) forbids improvising
one:

> "If you cannot name the contract, you do not have a work item — you have an
> opinion."

On a blank repository there are no contracts, so there is no derivable work, so a
conforming manager session correctly does nothing. The mode is complete for the
project it is already running and silent on the project it is not yet running.

### c-4 · The chain's first two links are missing and only the third is documented

`README.md:127–130` describes `recipes/seed-reconcile.yaml` as the one recipe —
it derives and refreshes the ledger **from a target repo's contracts**. So of
`blank repo → vision → contracts → seed → queue`, the *seed* step has a
documented mechanism and the two steps that must precede it have none. The recipe
cannot run until something has produced contracts, and nothing written down
produces contracts.

### c-5 · The existing-project path exists only as undocumented practice

The item behind this audit records that the steward has already driven the adopt
path by hand, twice, in `cortex-core` and `drumbeat`. Neither run left a
procedure in this repository: there is no adopt recipe, no adopt skill (the five
in `skills/` are `seam-test`, `proposing-a-change`, `freeze-bar`,
`ledger-disposition`, `lane-brief` — all mid-project procedures), and no section
in the mode. The most valuable path Converge has is the one held entirely in one
person's head.

---

## (d) An adopter needs to know nothing about how it works — **not met**

### d-1 · The reading order opens with the rulebook

`README.md:174–179`:

> `docs/PROTOCOL.md` → this README → `docs/ANNOUNCEMENT.md` →
> `docs/design/mechanism-spec.md` → the presentation.

The first thing an adopter is told to read is the ratified rules, and the fourth
is the mechanism specification. Three of the five entries are documents about how
Converge works. None is about using it.

### d-2 · The install section is a design note

Within `README.md:59–100` the reader meets: "capability layer", a
"behavior-includes-behavior include", `schema_version: 2` and helper closures,
`spawn.exclude_tools`, "per-role structural spawn policy is an upstream feature
request", and a dated live probe with its collateral finding. Every one is true
and every one is internals, placed at the moment the reader is trying to install.

### d-3 · "What ships" is an inventory of parts

`README.md:102–136` lists the four agents, the five skills, the hook module, the
recipe, the mode file, and the `src/` package — by path. It answers "what is this
made of", which is a maintainer's question. Nowhere does the README answer "what
do I do on Monday".

### d-4 · There is no page whose subject is the adopter's first day

There is no getting-started or quickstart at the repository root. The single
"Quickstart" heading, `docs/CONTRACTS-README.md:122`, is a quickstart *by
audience for reading contracts* — steward, teammate, coding agent, implementer —
and its steward entry (`:123–126`) is "read the vision, then the four contracts,
then `PINS.md`". Reading, again, not starting.

---

## Two things no contract covers

Named plainly, because `AGENTS.md:32–33` says a missing contract is a decision
for the steward and not a thing a lane invents.

**1. The bar says one install; the contract sanctions two.** The readiness
definition reads "one install; nothing else to know", keyed to `composition.v1`
§1–2. Those clauses say something else: §1 is "a lean base, never a heavy one"
and §2 is "automated steps use only the lean base's helpers". Neither mentions
the number of install commands. And `composition.v1` §5 says, in as many words,
"The shared work queue rides on **both install paths**" — the contract *assumes*
two. So finding (a) above cannot be a broken clause: nothing is broken. Either
the contract should say one path, or the bar should stop asking for one. That is
a proposal, and a steward's word.

**2. `operation.v1` has thirteen clauses and none of them is about starting.**
Every clause governs a project already under way: derive from a gap (§1), show
the plan (§2), fill lanes (§6), re-run the check (§7), brief on return (§10).
There is no clause for the first wake — no vision-drafting, no
contract-deriving, no ledger-seeding, no adopt. This is *why* `modes/converge-manager.md`
has no first day: the mode is keyed clause by clause to a contract that has no
first-day clause. Finding (c) is therefore not a mode defect either; it is a hole
in the contract that the mode faithfully reproduces. Writing the day-one path
into the mode without a clause to key it to would break the mode's own rule
(`modes/converge-manager.md:35–37`: every section is keyed to one clause and adds
nothing the clause does not say).

Both are recorded below as items that route to the steward rather than to a lane.

---

## What was filed

One item per gap, each naming its contract on line one and stating done in plain
words. Nothing here was fixed by this lane — the item that produced this audit
owns the audit and the harness, and no other file.

| Item | The gap | Findings |
|---|---|---|
| `converge-jyg0` | `operation.v1` has no clause for the first wake, so no path from a blank repository can be keyed to anything. Steward's call. | c-3, c-4, and "Two things", 2 |
| `converge-279a` | `composition.v1` §5 sanctions two install paths while the readiness bar asks for one. Steward's call. | a-1, a-2, and "Two things", 1 |
| `converge-eqds` | No document tells an adopter how to start a manager session, or how to tell whether it took. | b-1 … b-5 |
| `converge-njaj` | The only adoption procedure is "copy the five files"; the existing-project path the steward has driven twice is written down nowhere. | c-1, c-5 |
| `converge-ph6o` | `docs/CONTRACTS-README.md:154` says five templates; the directory holds six, and the hook's rename step is documented only inside the script. | c-2 |
| `converge-76vp` | Nothing a reader reaches is addressed to the adopter's first day; the reading order opens with the rulebook. | d-1 … d-4 |

## What this audit is not — and what the run added

It is a reading of files, not a run. Whether an adopter who holds only
`README.md` can actually get from a fresh machine to a running manager session is
a different question, and a document cannot answer it. That question is what
`evaluations/adopter/` exists to ask, against a fresh environment, twice — once
on a blank repository and once on a real one.

It ran on 2026-09-04 against `be59331`, and the answer is in
`evaluations/adopter/RESULT.md`: **RED, 12 pass · 3 fail**. Three things it
established that this reading could not:

- **Nothing is structurally broken about the manager mode.** In the
  existing-project scenario the AI user got there, and the captured pane shows a
  real `[converge-manager]>` prompt. Finding (b) is therefore a documentation
  gap and only that — the door works, and no document names it. In the
  new-project scenario the probe caught a blank pane and so proved nothing
  either way; that is recorded as a limit of the run, not as a finding.
- **Both scenarios reached a vision, a contract and a seeded ledger — by
  improvising, and differently each time.** Scenario 1 hand-built the participant
  kit file by file; scenario 2 ran a seed reconcile and filed work. With no
  written day-one path (finding c-1), two adopters got two different first days.
  That is what `converge-njaj` is for.
- **The cost is about an hour** of wall time and two long provider sessions to
  adopt one small project — and scenario 1 hit a thirty-minute budget without
  reaching a stopping point at all.

The run also found three defects in its own judging, which are recorded in
`RESULT.md` under "Limits of this run" and filed as `converge-f0bj`. Two of the
three reds name a cause the evidence does not support; the twelve passes were
each read off a file or a live pane and stand.
