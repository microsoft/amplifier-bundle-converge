# Collaborative instruction resources

This package carries the supervisor bundle and project-manager instructions for
Converge's collaborative profile. It publishes text only: no process, tools,
store, command entrypoint or runtime dependency. The only Python module is the
resource namespace initializer.

```python
from importlib.resources import files

manager = files("converge_instructions").joinpath("instructions/manager.md").read_text()
supervisor = files("converge_instructions").joinpath("bundle/bundle.md").read_text()
```

The source owns one copy of each instruction under `src/converge_instructions`.
The community profile at `bundles/collaborative/bundle.md` points to that owned
bundle text through a repository-relative symlink. Source archives and wheels
carry the actual text files, independent of the checkout. Consumers pin a
reviewed full commit and `#subdirectory=packages/collaborative`.

This is an opt-in instruction profile implementing the canonical Method loop:
traceable work, durable plans, isolated lanes, bounded failures, independent
manager checks, actionable returns and exactly four steward calls. The
[protocol map and gap audit](METHOD-PROTOCOL.md) accounts for every live promise
of Method's operation, lanes and wake contracts and identifies the execution
proof still required. It preserves the existing root bundle, manager
mode, guards and installation path. Publishing the instructions does not prove
that a runtime obeys them; consumers must verify their own execution behavior.

## Checks

From this package directory:

```sh
uv run --extra test python -m pytest
uv build
```

The guidance checks protect protocol and authority boundaries; resource checks
pin this version's instruction bytes and verify that the package contains no
runtime implementation. These are static and packaging checks, not proof that
a live manager follows the Method. The reviewed resource hashes are:

- `instructions/manager.md`: `0a91a4810b3cfc136dbff1cc81a109a6e19ba827b10a947cdd7a6b937f79fa1d`
- `bundle/bundle.md`: `f2ae9914433938df6962d21bb520ab7a9b0598ff2dbe8e6cc6041cb6e46209d7`

The package retains this repository's MIT license. The profile references only
public bundle dependencies and discovers configured capabilities at runtime.

Version 0.2.2 requires immutable, revision-bound Direction attachments and exact
worker return shapes in every brief that needs them. Missing context routes a
named setup defect, without host/cache/private-store discovery. Independent
review lanes declare `read_only:true` with empty writable ownership. This follows
an observed reading-policy failure; product checks did not establish that lane's
Method compliance. The policy does not claim OS sandbox enforcement.

Upgrade a
live manager only at an observed idle boundary using the runtime's explicit
old/new instruction-digest transition. Preserve its native session and inspect
readiness for the actual new digest and tools. The runtime's digest includes
project-specific text; the resource digest above is not that migration key.
