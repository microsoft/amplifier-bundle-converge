# Collaborative instruction resources

This text-only package owns portable Converge collaboration, manager and supervisor instructions.
It has no runtime, tool, host dependency, process, store or command entrypoint.

```python
from converge_instructions import instruction

manager = instruction("manager")
supervisor = instruction("supervisor")
```

The collaborative bundle entry point is [`behaviors/collaborative.yaml`](../../behaviors/collaborative.yaml).
It composes the shared collaboration and supervisor resources into an existing host without selecting
a provider, root instruction, skills list or session orchestrator. The optional
[`bundles/collaborative`](../../bundles/collaborative/README.md) root composes
Anchors and that behavior. The ordinary CLI root and app-install behavior load
the same shared collaboration resource through `behaviors/converge.yaml`.
The existing mode, guard and installation paths are unchanged.

## Version 0.4.14: recognize an existing product before choosing a work path

The supervisor reconciles an ordinary product progress, result or feedback
request against current public project records without requiring the person to
name Converge. It reuses a grounded binding or matches available workspace and
intent through bounded public reads; a same-name project, latest row or folder
alone is insufficient. Unrelated conversation stays ordinary, and recognition
does not create a project, grant execution authority or ratify intent.

This serves `composition.v1` clause 6 and `operation.v1` clauses 4, 10–11.
Only the supervisor instruction resource and its composed hash change; shared
collaboration, manager resources, CLI/root behavior and native-manager method
bytes are unchanged. The collaborative behavior's metadata version tracks this
package release without changing its composition. Publication updates no live
session. The [product-scope case](../../evaluations/collaborative/product-scope.md)
is **NOT RUN**. Source and wheel checks establish delivery, not activation
enforcement, model compliance or the cause of a prior routing failure.

## Version 0.4.13: give the person something useful to judge

The shared collaboration guidance keeps the person working with product examples
and meaningful choices. When an executable result is not ready, a provisional
example may resolve an actual uncertainty without pretending to be a working
build. Otherwise the return names the product consequence and next observable
checkpoint. Questions must earn attention, and a saved recommendation or question
must not be reported as the person's decision.

This serves `operation.v1` clauses 3, 4 and 10–11. It applies to text-only and
graphical consumers without changing capability APIs, authority, verification or
the boundary between a supervisor and product implementation. Only the shared
resource changes; both composed roles therefore change. Existing manager sessions
need the supported instruction-migration path before consuming it. The
[producer-review cases](../../evaluations/collaborative/producer-review.md) remain
manual behavior trials, **NOT RUN** with this revision. Packaging checks prove
delivery, not usability or model compliance.

## Version 0.4.12: keep the supervising conversation available

The supervisor yields after bounded observations while independently admitted
manager work continues. Long synchronous sleeps and unchanged polling do not
keep the foreground conversation useful. Supported interruptible waits or
background returns retain their actual host contract; without a wake facility,
the next real conversation turn reconciles the retained records. Yielding is not
completion, a stop, or a new permission gate, and promises no automatic notice.

Only the supervisor resource and composed supervisor hash change. Shared and
manager instruction bytes remain unchanged. The
[foreground-return scenario](../../evaluations/collaborative/foreground-return.md)
is a manual behavior trial and **NOT RUN**. Source/composition and installed-wheel
checks prove delivery, not responsiveness, interruption or model compliance.

## Version 0.4.11: deliver required sources before a lane starts

Manager examples include exact-revision Operations evidence attachments when
the installed runtime advertises them, preserving verification meaning and scoped
worker reads. Older runtimes receive complete needed evidence text/provenance in
the brief rather than an unavailable selector. Mandatory reading is checked
against the admitted source and access scope; outputs assigned for creation are
not missing prerequisite inputs. The supervisor's source wording is generalized.
This serves `operation.v1` clauses 4, 5 and 7 without changing contracts, authority,
attempt limits, runtime capabilities or the shared collaboration resource.

Manager/supervisor resources and both composed hashes change; publication updates
no retained session. The [source-delivery scenario](../../evaluations/collaborative/source-delivery.md)
is **NOT RUN**. Composition and wheel checks verify delivery, not model compliance.

### Version 0.4.10: repair engineering plans within existing authority

Shared guidance distinguishes an out-of-brief implementation dependency from a
product decision. A constrained manager routes the needed repair to its supervisor,
which may revise the bounded instruction within existing user authority without
asking the person to ratify file ownership or routine engineering work. Immutable
briefs, history and consumed budgets remain intact; a renamed exhausted target
cannot acquire a fresh budget. Changed promises or authority still need the
appropriate decision. This serves `operation.v1` clauses 1–4 and 9–11 without
amending contracts or adding capabilities, permissions or dependencies.

All three resources and both composed hashes change; ordinary CLI/TUI behavior
loads the same shared guidance. Publication adopts nothing in retained sessions.
The [engineering re-plan scenarios](../../evaluations/collaborative/engineering-replan.md)
are **NOT RUN**; source/wheel checks establish delivery, not agent compliance.

### Version 0.4.9: reconcile current sources before continuing

Supervisor guidance retrieves full relevant Direction/decision bodies when reads
are abbreviated, and reconciles existing candidate evidence before directing new
implementation. Routine engineering hypotheses remain revisable within actual
authority. Supervisor inspection of source/setup is distinguished from product
verification owned by the manager and tracked lanes.

Shared and manager guidance distinguish a historical stuck worker outcome from
separately authorized independent qualification of its exact unchanged candidate,
where the installed runtime supports that guarded path. They use the latest
trusted returned source, preserve budgets/history, and require fresh checks through
integration and closure. Unsupported recovery remains explicit; no new action,
permission, contract or dependency is introduced. This serves `operation.v1`
clauses 1, 3, 4 and 7–10.

All three resources and both composed hashes change; ordinary CLI/TUI behavior
loads the same shared text. Publication updates no retained session. The
[retained-continuation scenario](../../evaluations/collaborative/retained-continuation.md)
is **NOT RUN**; source/wheel checks establish delivery, not agent compliance.

### Version 0.4.8: make outcomes and decisions easy to review

Shared guidance separates accepted intent from revisable engineering hypotheses,
and routine agent-owned work from quiet status, meaningful updates and genuine
steward calls. Reviews lead with an actual artifact/version, realistic task and
limits. Concise summaries preserve received/applied/verified feedback distinctions,
real stops and inspectable evidence; they confer no execution authority. Role
instructions retain detailed durable reports without requiring their identifiers
to dominate the person's return summary. This serves `operation.v1` clauses 3,
4 and 9–11 without changing contracts, permissions, capabilities or dependencies.

Shared and both role resources change, including both composed hashes. Ordinary
CLI/TUI behavior loads the same shared guidance. Publication changes no live or
saved session; retained consumers need their explicit instruction adoption path.
The [producer-review trial](../../evaluations/collaborative/producer-review.md)
is **NOT RUN**. Source and wheel checks prove delivery, not the user experience.

### Version 0.4.7: finite recovery within retained work

Shared guidance preserves stuck returns while allowing finite investigation and
justified same-lane continuation within actual authority and the remaining bound.
A placeholder owner is not an accepted handoff. Supervisor and manager bindings
distinguish a new run-owned wave (`require_wave:true`) from a finite assessment
or continuation of already planned work (`false`, not read-only). Reconciliation
precedes scheduling more work; no extra wave is invented to satisfy accounting.
This serves `operation.v1` clauses 3, 7–10 and 13 without changing contracts,
runtime guards, capabilities, scope or permissions.

Shared and both role resources change, including both composed hashes. The same
shared recovery guidance reaches ordinary CLI/TUI behavior. Retained sessions
still require explicit adoption; publication updates no live manager. The
[finite-recovery scenario](../../evaluations/collaborative/finite-recovery.md)
is manual and **not run**; source checks do not prove model compliance.

### Version 0.4.6: preserve acceptance through handoffs

Shared guidance compares derived acceptance with its exact source before manager
handoff or worker admission. It preserves counterexample inputs and constraints
without converting a past symptom into a mandatory verdict for a corrected
implementation. Conflicting shorthand is reconciled against Direction rather
than silently strengthening it. Status reports distinguish admitted manager runs,
recorded plans and started lanes. This serves `operation.v1` clauses 1–4 and 7–10;
no contract, runtime schema, permission or host dependency changes.

The shared resource reaches ordinary CLI/TUI behaviors and both
`instruction(role)` consumers. Role files remain unchanged; both composed hashes
change, so retained sessions still require explicit adoption. No live session is
updated by publication. The [acceptance-translation scenario](../../evaluations/collaborative/acceptance-translation.md)
is a manual evaluation, not a claimed model result.

### Version 0.4.5: distinguish reconnect from new work

Supervisor bindings name the exact `instruction` argument for reconnect and
require evidence that the intended run was admitted before waiting on it.
Instruction-free reconnect still restores lifecycle without manufacturing work;
uncertain delivery is reconciled before retry. This serves `operation.v1`
clauses 3 and 9 without adding an action, permission or host dependency.

Only the supervisor resource and its composed hash change. Shared collaboration,
manager instructions, ordinary CLI/TUI behavior and the manager's composed hash
remain unchanged. Publication does not update a live session; source and wheel
checks do not prove an agent follows these instructions.

### Version 0.4.4: verification readiness and bounded recovery

Shared guidance checks the manager's verification environment before admitting
implementation and routes setup failures without spending worker launches just
to reconfirm them. It preserves completed returns, recorded checks and attempt
caps, and names unsupported recovery instead of bypassing guards. Manager
guidance distinguishes a fresh supported check from replay of an old receipt.
Environment readiness does not establish product acceptance or resolve separate
counterevidence. This serves `operation.v1` clauses 7–9; no contract, runtime
action or recovery mechanism changes.

The shared resource reaches both ordinary CLI/TUI behavior paths and both
`instruction(role)` consumers; the manager role resource also changes. The
supervisor role file and manager mode are unchanged. Composed instruction hashes
change, so retained sessions require their existing explicit adoption process.
Publication does not update a running or saved session. The
[verification-recovery scenario](../../evaluations/collaborative/verification-recovery.md)
is a manual behavioral evaluation, not a claimed model result.

### Version 0.4.3: finite feedback before implementation

Feedback acknowledgment, acceptance reassessment and a replacement-plan discussion
can finish without launching another wave. Supervisor guidance chooses the installed
`require_wave` mode explicitly; shared and manager guidance preserve the separate
plan, lane and verification requirements for actual implementation. New feedback
is handled before another observation loop. This serves `operation.v1` clauses
4 and 9: feedback is signal, and stalls are decisions. It changes no contract,
runtime API or permission boundary, and adds no host dependency.

Shared, supervisor and manager resources changed; retained sessions require explicit
adoption of the new composed hashes. This publication does not update a live session.
Static guidance checks do not prove that an agent will follow the guidance.

### Version 0.4.2: check acceptance coverage

Shared guidance asks whether declared checks can pass while an acceptance
promise remains false, and retains missing or failed acceptance in existing
check/return records. It adds no required test medium, schema or approval gate.
The ordinary manager-mode and collaborative consumers already load this same
resource; the role files and mode remain unchanged. Composed instruction hashes
change, so retained sessions require their existing explicit adoption process.
The [acceptance-coverage evaluation](../../evaluations/collaborative/acceptance-coverage.md)
supplies a reproducible case with passing declared checks and missing behavior;
fixture validation is separate from observing an agent handle it.

### Version 0.4.1: preserve intent and decision scope

Shared guidance now preserves exact source wording alongside interpretation,
limits approval to the decision actually made, and asks for meaningful product
alternatives or an explanation that existing direction already settles the
choice. It adds no approval gate or mandatory tool invocation. The role-specific
resources remain unchanged; composed instruction hashes change. Publication
does not alter a running or saved session.

### Version 0.4.0: collaboration before and after execution

The shared `instructions/collaboration.md` leads idea intake, consequential
questions, exploration, revision and feedback in a text-only experience. It
adds no tool dependency, authority or mandatory stage sequence. It also makes
observation/retry boundaries and per-role configuration claims explicit. The
[acceptance journey](../../evaluations/collaborative/README.md) requires a real
conversation and records evidence; it is not a completed live evaluation.

Both behavior entry points use the same context URI, so composing them includes
the shared text once. The CLI behavior does not acquire the collaborative
supervisor's tool bindings. The pure-text `instruction(role)` helper composes
that same shared text and one role resource for consumers outside the bundle
loader. It starts no runtime and selects no provider.

Legacy direct `importlib.resources` reads still return only the named file.
They **do not** acquire the shared text by upgrading the package alone. Consumers
that read `instructions/manager.md` directly need a separate change to
`instruction("manager")`, a reviewed package source update, and an explicit
transition of the full per-session instruction hash. Role-specific and shared files have independent hashes; inspect the selected
version before adopting its composed instruction. Direct supervisor readers
likewise need the helper or explicit inclusion of the shared resource. Do not
pass a composed helper result alongside the same loaded behavior, duplicating
the common text. No installed or saved session is updated by this source change.

Version 0.3.0 removes host-specific command/canvas instructions and moves the
supervisor resource from `bundle/bundle.md` to `instructions/supervisor.md`.
Consumers reading the old supervisor resource must use the new path. The manager
resource and its import path are byte-unchanged; existing pinned runtimes remain
compatible. A portable package must never depend on a private host integration.
All three instructions ship as actual files in the wheel and source archive.

The [protocol map](METHOD-PROTOCOL.md) describes canonical Method promises and
execution proof still required. Instructions are not enforcement. The collaborative
behavior does not mount the legacy manager mode or filesystem candidate guard.
API-backed writes need their capability owner's enforcement. Inspect actual
role/tool/hook manifests; package installation proves none of these are mounted.

Saved sessions stay on their reviewed pins until a separately authorized idle
adoption. Preserve native identity/history, use exact old/new instruction hashes,
and inspect runtime readiness. No silent restart or replay is part of this change.
The manager's known refusal-wording and read-only guidance reconciliation remains
runtime-owner work; this resource split does not claim to fix or validate it.

## Checks

```sh
uv run --extra test python -m pytest
uv build
```

The root CI includes source and installed-wheel resource checks. These are static
and packaging checks, not proof a live manager follows Method or product acceptance.
Reviewed SHA-256 values:

- `instructions/manager.md`: `7b9661fd2240ea35ff1fa5f574749a1b080638982cc0de2b907793267279516f`
- `instructions/supervisor.md`: `1fa9a2139a48eca349de189a7f7fc04a649f931218c5cf02526fa98583f013ff`
- `instructions/collaboration.md`: `8ee4a97809be502d795d6c864a5dc6ba0c09aa9f32ec013cd1a87de31e9f6bb7`

The package retains the repository's MIT license.
