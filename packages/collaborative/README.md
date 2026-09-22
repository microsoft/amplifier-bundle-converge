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

## Version 0.4.4: verification readiness and bounded recovery

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

- `instructions/manager.md`: `b605f53d80c116458424940effbe2da11701c07c0ff200b0e29b04871910fa02`
- `instructions/supervisor.md`: `2f38a211f295b877c5ab9a360ddad0f1efb68384195fd825c6d33b3962428557`
- `instructions/collaboration.md`: `37faeb74b7741e9d19d9a1057cfc12f83a678db32ac2d6c5c8f171ea680898e8`

The package retains the repository's MIT license.
