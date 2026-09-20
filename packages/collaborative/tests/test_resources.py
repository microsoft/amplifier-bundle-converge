from importlib.resources import files
import hashlib
from pathlib import Path


EXPECTED = {
    "instructions/manager.md": "0a91a4810b3cfc136dbff1cc81a109a6e19ba827b10a947cdd7a6b937f79fa1d",
    "bundle/bundle.md": "f2ae9914433938df6962d21bb520ab7a9b0598ff2dbe8e6cc6041cb6e46209d7",
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
