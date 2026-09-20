from importlib.resources import files
import hashlib
from pathlib import Path


EXPECTED = {
    "instructions/manager.md": "f76a3b1506f850939fd30c7053cba32ec1a30a3d5d139578ed368b89744f3f43",
    "bundle/bundle.md": "858bc1bda1eb5c83ba5e1aa4d06aa8307c23055a6e7b3a14450498384668ee7e",
}


def test_instruction_resources_match_reviewed_version():
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
