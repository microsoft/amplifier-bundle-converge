# Operation Contract — v1 (DRAFT — content owner-ratified 2026-09-02)

**Who builds against this:** the intent steward who relies on a manager session;
peer manager sessions; the shared work queue; the parallel-lane tooling that
worker sessions run on. Converge's manager mode is the reference implementation,
and the turnkey run in `evaluations/` is this contract's conformance kit.

## Purpose

The manager session carries a project from contract gap to verified result so
that the steward's attention is spent only where a person is irreplaceable.
Waiting on the steward is never the bottleneck.

## Core (the teeth)

1. **Work is derived, never invented.** Every item traces to a contract gap or to
   steward feedback, names its contract, and states what done looks like.
2. **The plan is visible.** Order, dependencies, collisions, and opportunistic
   picks are shown with reasons. The steward may reorder; nothing is hidden.
3. **Never the bottleneck.** Within the steward's objective, budget, and lane
   count, the manager session maximizes work that proceeds without them. What
   needs their word is parked; everything else continues.
4. **Feedback is signal, not a ticket.** Before filing: read and quote the
   evidence; confirm which version was seen; merge reports sharing a cause and
   split one hiding several; supply cause, reproduction, contract, and the
   meaning of fixed; update existing work rather than duplicate it; surface
   failures nobody reported. Feedback about direction returns a decision, not a
   ticket. "Still broken" reopens verification, never the tracker.
5. **Lanes are real sessions.** A lane is a worker session's own working copy,
   branch, and terminal session, launched through the parallel-lane tooling. No
   launcher → fail loud, never agents. In-session sub-agents serve exactly four
   roles — read-only investigation under half an hour, protocol ruling,
   janitorial queue recording, the watcher — none of which executes lane work.
6. **Width is a collision decision.** Lanes fill to the steward's count only with
   items that provably touch different files; adjacent items run as one lane. A
   shortfall past a bounded interval becomes a repair the steward answers with a
   word: fill from these disjoint items, or confirm the lower width. Never silent.
7. **Done means the manager session re-ran the check.** A marker is a claim.
   Done requires commits beyond base (a marker on an unchanged branch is stuck),
   evidence on disk, and — where the item lives in an installed system — the
   installed thing showing the change. Running at deadline is stuck; stuck
   outranks done. Each piece ends done · stuck with cause · needs judgment.
8. **Integrate, verify, re-check.** The manager session's own verification, never
   the worker session's; a post-merge gate when two or more lanes landed in one
   repository; then the contract check, before the next brief.
9. **Stalls are decisions, not loops.** No progress across iterations → stuck with
   cause, routed to the plan or the steward. Honest refusal is a designed exit.
10. **A brief on every return.** Time away · finished · stuck · needs you ·
    anything quietly broken — in sentences, appended to a log the steward can read.
11. **Four calls reach the steward.** Ratify a direction change · an irreversible
    action · a check only a person or device can perform · priority or stop.
    Anything else is a defect to file.
12. **The queue is the shared one, with custody.** Atomic claim, heartbeat while
    held, resolution written for whoever asked.
13. **Hand off when done.** A manager session that has lost its footing says so,
    writes a hand-off a fresh session can resume from, and stops.

## Declared dependencies (checked at install)

The shared work queue **and its service** (without it: no queue, stop before
planning) · the parallel-lane tooling and its goal helpers (without them: one lane
at a time, said aloud) · worktrees and a terminal multiplexer (without them: no
lanes) · the lean base and Converge's guard · optionally the session-history
service for provenance. One install verifies each and names what is missing.

## What v1 deliberately does NOT freeze

- Lanes on a remote service — promoted when a service offers brief-in, evidence-out.
- Manager sessions coordinating directly — promoted the second time one message
  must reach several.
- Enforced per-role tool limits — promoted when upstream #388 lands.

## Conformance kit asserts

- **Turnkey:** fresh environment → one install → start a project, derive from a
  sample gap, run two lanes, tend, judge, integrate, re-check, brief → green.
  **First green 2026-09-04** — nine of nine steps, twice, in fresh containers, with a manager session that was not the integrator (`evaluations/turnkey/RESULT.md`); it re-runs on every merge.
- Every lane has a terminal session and working copy on disk; in-session
  sub-agents never hold work items.
- Lanes are filled only with disjoint items; adjacent items appear as one lane.
- A marker on an unchanged branch is recorded stuck; a post-merge gate runs for
  multi-lane merges; every done has evidence the manager session re-ran.
- No raw feedback becomes work without a quoted source and enrichment.
- A stall is declared stuck; a brief exists for every return; a hand-off exists
  for every manager session that ended by choice.

## Reserved / open questions (NOT frozen)

- The remote-lane interface shape.
- A namespace for Converge's own worker helpers, should the standard ones prove
  insufficient.

## Changelog

| Date | Change | Evidence |
|---|---|---|
| 2026-09-04 | Turnkey sentence: red → first green recorded (owner word "ratified") | evaluations/turnkey/RESULT.md GREEN 9·0·0 ×2; docs/workflow/owner-ratifications-2026-09-03.md round 4 |
