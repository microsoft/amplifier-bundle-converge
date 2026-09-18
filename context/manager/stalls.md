# The stall stamp - a named exit, not a poll count

Clause 9 says a stall is a decision, not a loop. This file distinguishes a
failed attempt from a healthy wait, and gives both a named boundary and route.

## Refusals and failed attempts

A guard or tool refusal is an **immediate STOP**. Record the target, cause,
evidence, and route. Do not try a different tool around the refusal. For a
failed command or terminal lane, bound the attempted recovery in advance; after
the declared limit, record the named route instead of repeating it.

    - 2026-09-06T04:12:07Z STUCK w4-changelog - locked-document guard refused
      the changelog edit. Attempts: 1. Evidence: guard refusal. Routed: plan.

`Routed: plan` means file, requeue, or brief the next work. `Routed: steward`
means one of clause 11's four calls, stamped beside it. A route is part of the
declaration, not an optional afterthought.

## Healthy passive waits

Before a passive wait, write the **health signal, checkpoint, deadline, and
route if it is missed**. Poll or wait actively and boundedly unless a supported
resumer has been proven in this environment. Three identical healthy polls are
not a stall; they are expected observations until the declared boundary.

    - 2026-09-06T04:12:07Z WAIT w4-tests - health: branch and terminal observed.
      Checkpoint: 04:25Z. Deadline: 04:40Z. Miss route: investigate then plan.

A missed checkpoint or deadline, terminal failure, or changed result triggers
the route. The highway watchdog is **advisory only**: `LIVE` is observation, not
automatic resume. It does not make a paused manager session continue, and its
absence or a missing receipt never authorizes one.

## What the record can prove

The record proves that this session declared a boundary, observed an outcome, and
selected a route. It does not prove a watchdog resumed it, that an unrecorded
attempt never happened, or that a recipient accepted a transfer. State those
limits rather than upgrading observation into completion.
