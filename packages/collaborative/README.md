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

This is an opt-in instruction profile serving `operation.v1` Core 1, 7 and 10
and `composition.v1` Core 1 and 6. It preserves the existing root bundle, manager
mode, guards and installation path. Publishing the instructions does not prove
that a runtime obeys them; consumers must verify their own execution behavior.

## Checks

From this package directory:

```sh
uv run --extra test python -m pytest
uv build
```

The resource checks lock the adopted instruction bytes and verify that the
package contains no runtime implementation. The approved source hashes are:

- `instructions/manager.md`: `03d1421e550a24ed75597f352604f120e4bf0a65f069d7e55bdedd19558266a1`
- `bundle/bundle.md`: `43092048d79f1eee7b76000d1e1c59e60f0345a65186b1742c6bec63f8e4f5c3`

The package retains this repository's MIT license. The profile references only
public bundle dependencies and discovers configured capabilities at runtime.
