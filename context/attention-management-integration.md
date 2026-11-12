# Attention-management integration — recovered brainstorm context

This is a working context note for discussion, not a Converge vision, contract,
proposal, or implementation brief. It reconstructs a design explored in an
Amplifier session during September 2–8, 2026. Treat the architecture below as
input to a new discussion, not as ratified direction.

## Source

The primary source is Amplifier session
`82831e30-cfd7-4ec0-a59e-fd75a848354f`, run from:

```text
/home/ramparte/dev/ANext/concern-os
```

The session can be resumed with:

```bash
cd /home/ramparte/dev/ANext/concern-os
amplifier session resume 82831e30-cfd7-4ec0-a59e-fd75a848354f
```

Its local records are under:

```text
~/.amplifier/projects/-home-ramparte-dev-ANext-concern-os/sessions/82831e30-cfd7-4ec0-a59e-fd75a848354f/
```

Supporting implementation sessions included:

- `1767bdb3-d5e9-4fac-b328-0c4dd9c68711` — Butler supervisor and handler pool
- `9019923b-f92f-4961-903a-98cddff4405a` — notification queue, triggers, and deduplication
- `647082f5-175b-4d18-be20-9fc80f2b329f` — Ansible attention board

## The recovered idea in one sentence

Concern OS owns durable lifecycle and evidence; Butler performs bounded triage
and orchestration; Ansible presents an attention-first workbench; a narrow
notification and exact-session-steering seam brings a person or an idle session
back only when needed.

## System shape

```text
Incoming signal or work
        │
        ▼
Concern OS
  canonical concern lifecycle
  evidence, claims, disposition, projections
        │
        ├──────────────► Butler
        │                 classify and route
        │                 supervise bounded handlers
        │                 report inability, never invent authority
        │
        ├──────────────► Ansible attention workbench
        │                 group by project
        │                 show what needs attention
        │                 drill into the exact concern/session
        │
        └──────────────► Notification seam
                          only needs_you / overdue / inability
                          bounded payload + deep link
                          durable deduplication
                                   │
                                   ▼
                          exact session note/wake/resume
```

## Responsibilities and boundaries

### Concern OS — lifecycle and evidence authority

- Owns the canonical state of each concern.
- Owns evidence, claims, state transitions, projections, returns, and final
  disposition.
- Exposes a versioned state API to other surfaces.
- Is the sole authority: Butler and Ansible must not grow competing lifecycle
  stores.
- Produces attention-worthy conditions such as `needs_you`, overdue assessment,
  and handler inability.

### Butler — bounded triage and orchestration

- Performs seven-way triage rather than treating every incoming item alike.
- Supervises a small handler pool with atomic claims and separate process groups.
- Distinguishes worker work, builder work, and an “optimal workflow”
  meta-concern.
- Automated handlers run with deliberately constrained capabilities.
- The earlier design moved bounded automation toward a repository-owned,
  provider-only runner with no tools or app behavior. Explicitly named
  interactive Amplifier sessions retain their normal tooling.
- Butler can classify, claim, dispatch, and report inability; it does not become
  the lifecycle or evidence authority.

### Ansible — attention-first workbench

- Acts as the human-facing dashboard and proxy, not another source of truth.
- Groups attention by project and supports exact drill-down to the relevant
  concern and session.
- Reads Concern OS state through a controlled API/adapter seam.
- Earlier deployment was staged behind a `WORKBENCH_INPUT` feature flag while
  the raw-text ingress adapter was being verified.

### Notification seam

Only three conditions were allowed to create a notification:

1. `needs_you`
2. an overdue assessment
3. handler inability

The proposed delivery rules were:

- one human-readable line plus a card/deep link;
- never include code, filesystem paths, or secrets;
- at most one push per `(concern_id, reason)` until disposition;
- persist sent state so restarts do not re-notify;
- keep the channel adapter replaceable. The recovered design did not establish
  WhatsApp as the channel.

### Exact note, wake, and resume

A substantive payload is queued first through `amplifier-note`. Activation is a
separate operation.

- An active session receives the note but no forced activation.
- Only a verified-idle session receives a minimal wake marker and Enter.
- The payload itself is never injected with `tmux send-keys`.
- Exact steering must prove:

  ```text
  canonical session UUID
      → fresh beacon/process identity
      → exactly one live tmux pane
  ```

- If the pane is gone but identity remains valid, resume the same session UUID
  with `amplifier session resume <uuid> --no-history`, rebind it, and then send
  the marker.
- Missing, stale, duplicate, or ambiguous identity becomes `target_lost`; the
  system does not guess by display name or directory.
- A crash after dispatch becomes `unknown`; it does not replay the note, marker,
  or resume action blindly.

## Contract seams named in the earlier work

The prior session organized the design around six contracts:

- `core-state-api`
- `dash-proxy`
- `butler-runtime`
- `session-identity`
- `evidence-lifecycle`
- `notifier`

These names describe the earlier decomposition. They are not contracts of the
Converge repository and are not ratified here.

## Attention-management principles implicit in the design

- Preserve one authority for truth while allowing several specialized surfaces.
- Spend human attention only on bounded conditions that actually require it.
- Separate recording a message from interrupting or activating its recipient.
- Prefer exact identity and proof over convenient inference.
- Make uncertainty explicit (`target_lost`, `unknown`) instead of hiding it with
  retries or guesses.
- Bound automated execution more tightly than interactive collaboration.
- Keep notification content small, safe, deduplicated, and linked back to richer
  context.
- Put consequential changes behind short, explicit steward decisions rather
  than continuous supervision.

## Questions for Brian and the steward

These are prompts for exploration, not decisions already made:

1. Is Concern OS still the right name and boundary for the canonical lifecycle,
   or should Converge itself own some of that state?
2. Is Ansible the durable attention surface, one client of a shared attention
   API, or an implementation that should be absorbed into the Converge app?
3. Where does Butler sit relative to a Converge manager session: intake clerk,
   triage service, manager capability, or a separate peer?
4. Which events genuinely deserve interruption, and is the earlier set of three
   sufficient?
5. Should the notification seam remain channel-neutral, with WhatsApp and other
   destinations as adapters?
6. What is the smallest useful concern schema shared by Butler, Ansible, and
   Converge without creating a second work tracker?
7. Which identity proofs are required before waking or resuming a session, and
   which component owns those proofs?
8. How should `unknown` and `target_lost` appear to a person so uncertainty is
   visible without becoming noise?
9. Which parts are enduring direction, which need explicit contracts, and which
   are merely implementation choices that should remain unfrozen?
10. What is the first end-to-end slice that can demonstrate reduced attention
    cost without committing to the whole architecture?

## A useful first brainstorm frame

Start with one concrete journey rather than the component map:

> A signal arrives while Sam is away. The system decides whether it matters,
> records why, lets bounded automation handle what it can, and asks Sam exactly
> once only if his judgment is required. When he opens the notification, he
> lands on the exact concern with its evidence, current handler, and session.
> Nothing guessed his identity, duplicated the work, or created a second source
> of truth.

For that journey, identify:

1. the source event;
2. the canonical record and state transitions;
3. Butler’s bounded decision;
4. what Ansible/Converge renders;
5. whether and how notification occurs;
6. the exact wake/resume behavior;
7. the evidence that the journey reduced rather than increased attention cost.
