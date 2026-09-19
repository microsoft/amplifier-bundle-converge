from importlib.resources import files
import hashlib
from pathlib import Path


EXPECTED = {
    "instructions/manager.md": "03d1421e550a24ed75597f352604f120e4bf0a65f069d7e55bdedd19558266a1",
    "bundle/bundle.md": "43092048d79f1eee7b76000d1e1c59e60f0345a65186b1742c6bec63f8e4f5c3",
}


def test_instruction_resources_preserve_adopted_bytes():
    root = files("converge_instructions")
    for name, expected in EXPECTED.items():
        assert hashlib.sha256(root.joinpath(name).read_bytes()).hexdigest() == expected


def test_namespace_exposes_no_runtime_implementation():
    root = files("converge_instructions")
    assert {p.name for p in root.iterdir() if p.name.endswith(".py")} == {"__init__.py"}


def test_community_profile_uses_the_owned_bundle():
    repository = Path(__file__).resolve().parents[3]
    profile = repository / "bundles/collaborative/bundle.md"
    source = repository / "packages/collaborative/src/converge_instructions/bundle/bundle.md"
    assert profile.is_symlink()
    assert profile.resolve() == source.resolve()
    assert profile.read_bytes() == files("converge_instructions").joinpath("bundle/bundle.md").read_bytes()
