# Collaborative instruction resources

This text-only package owns portable Converge manager and supervisor instructions.
It has no runtime, tool, host dependency, process, store or command entrypoint.

```python
from importlib.resources import files

manager = files("converge_instructions").joinpath("instructions/manager.md").read_text()
supervisor = files("converge_instructions").joinpath("instructions/supervisor.md").read_text()
```

The primary bundle entry point is [`behaviors/collaborative.yaml`](../../behaviors/collaborative.yaml).
It composes the same supervisor resource into an existing host without selecting
a provider, root instruction, skills list or session orchestrator. The optional
[`bundles/collaborative`](../../bundles/collaborative/README.md) root composes
Anchors and that behavior. The original CLI root/mode/guard paths are unchanged.

Version 0.3.0 removes host-specific command/canvas instructions and moves the
supervisor resource from `bundle/bundle.md` to `instructions/supervisor.md`.
Consumers reading the old supervisor resource must use the new path. The manager
resource and its import path are byte-unchanged; existing pinned runtimes remain
compatible. A portable package must never depend on a private host integration.
Both instructions ship as actual files in the wheel and source archive.

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
- `instructions/supervisor.md`: `c75ea0d41389fbc5ef66630a233e25bf3bcda6bc702f8616f8946a43f620312c`

The package retains the repository's MIT license.
