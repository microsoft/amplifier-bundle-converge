"""Actual Foundation loading; no provider, tool module, or model activation."""
import asyncio
from importlib.resources import files
from pathlib import Path
from types import SimpleNamespace

from amplifier_foundation import Bundle, BundleRegistry
from amplifier_foundation.bundle import PreparedBundle
from amplifier_foundation.validator import validate_bundle


REPO = Path(__file__).resolve().parents[3]


def test_behavior_materializes_once_and_preserves_the_host(tmp_path):
    async def check():
        registry = BundleRegistry(home=tmp_path / 'registry', strict=True)
        behavior = await registry.load(REPO.as_uri() + '#subdirectory=behaviors/collaborative.yaml')
        assert validate_bundle(behavior).valid
        assert behavior.instruction is None
        assert not behavior.providers and not behavior.tools and not behavior.hooks
        assert not behavior.session and not behavior.spawn
        host = Bundle.from_dict({
            'bundle': {'name': 'existing-host'},
            'session': {'orchestrator': {'module': 'existing-loop'}},
            'providers': [{'module': 'provider-existing', 'config': {'model': 'unchanged'}}],
            'tools': [{'module': 'tool-skills', 'config': {'skills': ['host-skills']}}],
        })
        host.instruction = 'Existing host instruction stays first.'
        composed = host.compose(behavior)
        composed.resolve_pending_context()
        assert composed.instruction == host.instruction
        assert composed.session == host.session
        assert composed.providers == host.providers
        assert composed.tools == host.tools
        assert not composed._pending_context
        assert all(path.is_file() for path in composed.context.values())
        events = []

        async def emit(event, payload):
            events.append((event, payload))

        session = SimpleNamespace(coordinator=SimpleNamespace(hooks=SimpleNamespace(emit=emit)))
        prepared = PreparedBundle(mount_plan=composed.to_mount_plan(), resolver=None, bundle=composed)
        prompt = await prepared.create_system_prompt_factory(session, session_cwd=tmp_path)()
        source = files('converge_instructions').joinpath('instructions/supervisor.md').read_text()
        shared = files('converge_instructions').joinpath('instructions/collaboration.md').read_text()
        assert prompt.startswith(host.instruction)
        assert prompt.count(source) == 1
        assert prompt.count(shared) == 1
        assert all(not payload['failed'] for _, payload in events)

    asyncio.run(check())


def test_complete_profile_resolves_same_behavior_without_body_replacement(tmp_path):
    async def check():
        # Isolate this root wrapper from Anchors' many unrelated network dependencies.
        anchor = tmp_path / 'anchor'
        (anchor / 'context').mkdir(parents=True)
        (anchor / 'context/system.md').write_text('ANCHORS INSTRUCTION')
        (anchor / 'bundle.md').write_text('---\nbundle:\n  name: anchors\n---\n@anchors:context/system.md\n')
        registry = BundleRegistry(home=tmp_path / 'registry', strict=True,
            include_source_resolver=lambda source: anchor.as_uri() if 'amplifier-foundation@' in source else None)
        root = await registry.load(REPO.as_uri() + '#subdirectory=bundles/collaborative')
        root.resolve_pending_context()
        assert root.instruction.strip() == '@anchors:context/system.md'
        assert {path.read_text() for path in root.context.values()} == {
            files('converge_instructions').joinpath(f'instructions/{name}.md').read_text()
            for name in ('collaboration', 'supervisor')
        }

    asyncio.run(check())


def test_cli_root_and_app_behavior_share_one_collaboration_resource(tmp_path):
    async def check():
        # Only external dependencies are stubbed; real local roots, behaviors,
        # namespace resolution and prompt materialization are exercised.
        sources = {}
        for name in ('amplifier-foundation', 'amplifier-work-tracker'):
            path = tmp_path / name
            path.mkdir()
            (path / 'bundle.md').write_text(
                f'---\nbundle:\n  name: {name}\n---\n')
            sources[name] = path.as_uri()

        def resolve(source):
            return next((uri for name, uri in sources.items() if name + '@' in source), None)

        registry = BundleRegistry(home=tmp_path / 'registry', strict=True,
                                  include_source_resolver=resolve)
        root = await registry.load(REPO.as_uri())
        behavior = await registry.load(REPO.as_uri() + '#subdirectory=behaviors/converge.yaml')
        collaborative = await registry.load(REPO.as_uri() + '#subdirectory=behaviors/collaborative.yaml')
        shared = files('converge_instructions').joinpath('instructions/collaboration.md').read_text()
        for loaded in (root, behavior, root.compose(collaborative), behavior.compose(collaborative)):
            loaded.resolve_pending_context()
            assert sum(path.read_text() == shared for path in loaded.context.values()) == 1
            assert any(path.name == 'converge-awareness.md' for path in loaded.context.values())
            events = []

            async def emit(event, payload):
                events.append((event, payload))

            session = SimpleNamespace(coordinator=SimpleNamespace(hooks=SimpleNamespace(emit=emit)))
            prepared = PreparedBundle(mount_plan=loaded.to_mount_plan(), resolver=None, bundle=loaded)
            prompt = await prepared.create_system_prompt_factory(session, session_cwd=tmp_path)()
            assert prompt.count(shared) == 1
            assert all(not payload['failed'] for _, payload in events)

    asyncio.run(check())
