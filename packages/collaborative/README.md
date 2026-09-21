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

## Version 0.4.0: collaboration before and after execution

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
transition of the full per-session instruction hash. The role-specific file remains unchanged
in this version; its composed instruction will change. Direct supervisor readers
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

- `instructions/manager.md`: `0a91a4810b3cfc136dbff1cc81a109a6e19ba827b10a947cdd7a6b937f79fa1d`
- `instructions/supervisor.md`: `4be7a8a358d975b3ebf754289f7172bf8dbbad24292a082f1d6c12e6f6d1b65f`
- `instructions/collaboration.md`: `919e5c7ac05306097fb004416c9643bcd971b0c76b1d75ae1177ac253bd2df33`

The package retains the repository's MIT license.
