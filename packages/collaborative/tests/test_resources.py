from importlib.resources import files
import hashlib
from pathlib import Path
import pytest

from converge_instructions import instruction


EXPECTED = {
    "instructions/manager.md": "76fdc229efe748e4cfdf1785eb313293ba3f6a293bb7f2c9f88d2d0e19574119",
    "instructions/supervisor.md": "cc2e6c31b58772e266d3208d8a289403aecde136cf4844a69edc1175ae430e17",
    "instructions/collaboration.md": "ac4a6e135f95b2f7345a6978c65eb4bbd02ace19e285e79895665f439ff88f0f",
}


def test_instruction_resources_match_reviewed_version():
    root = files("converge_instructions")
    for name, expected in EXPECTED.items():
        assert hashlib.sha256(root.joinpath(name).read_bytes()).hexdigest() == expected


def test_namespace_exposes_no_runtime_implementation():
    root = files("converge_instructions")
    assert {p.name for p in root.iterdir() if p.name.endswith(".py")} == {"__init__.py"}


@pytest.mark.parametrize("role", ("manager", "supervisor"))
def test_direct_consumer_composes_shared_guidance_once(role):
    root = files("converge_instructions").joinpath("instructions")
    shared = root.joinpath("collaboration.md").read_text().rstrip()
    specific = root.joinpath(f"{role}.md").read_text().rstrip()
    text = instruction(role)
    assert text == shared + "\n\n" + specific + "\n"
    assert text.count(shared) == 1


@pytest.mark.parametrize("role", ("worker", "../supervisor", "", "collaboration"))
def test_direct_consumer_rejects_unsupported_roles(role):
    with pytest.raises(ValueError, match="role must be"):
        instruction(role)


def test_community_profile_composes_the_behavior_and_preserves_anchors():
    repository = Path(__file__).resolve().parents[3]
    profile = (repository / "bundles/collaborative/bundle.md").read_text()
    assert "converge:behaviors/collaborative.yaml" in profile
    assert "@anchors:context/system.md" in profile
    behavior = (repository / "behaviors/collaborative.yaml").read_text()
    assert "converge:packages/collaborative/src/converge_instructions/instructions/supervisor.md" in behavior


def test_portable_resources_have_no_host_api_or_private_integration_dependency():
    root = files("converge_instructions")
    for name in EXPECTED:
        text = root.joinpath(name).read_text().lower()
        for host_reference in ("app_control", "smarttools.", "/smarttools", "unified", "canvas.mcp"):
            assert host_reference not in text


def test_behavior_does_not_select_a_host_or_replace_its_instruction():
    text = (Path(__file__).resolve().parents[3] / "behaviors/collaborative.yaml").read_text()
    for forbidden in ("includes:", "providers:", "session:", "spawn:", "instruction:", "---"):
        assert forbidden not in text
