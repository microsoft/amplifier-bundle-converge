"""A shipped recipe must say what it needs, not borrow it from whoever calls it.

Under recipe schema v1 a step's ``agent:`` reference resolves out of the
*calling session's* agent map. A recipe that works when run from this bundle
then fails from any other bundle with::

    Agent 'converge:reconciler' not found in configuration

Schema v2 fixes that by making the recipe declare its own closure
(``schema_version: 2`` plus a ``dependencies:`` block), so its agents resolve
from that closure and never from the caller.

This test is the ratchet for that: any recipe in this repository that names an
``agent:`` must carry the v2 header. A new recipe added without one fails here
rather than in someone else's session six weeks later.

Run it:

    python3 -m pytest tests/test_every_recipe_says_what_it_needs.py -q
"""

from __future__ import annotations

from pathlib import Path

import pytest

yaml = pytest.importorskip("yaml", reason="PyYAML is needed to read the recipes")

REPO_ROOT = Path(__file__).resolve().parents[1]

# Files that legitimately do NOT carry the v2 header. Every entry needs a
# reason, in the file, in words -- an exemption nobody can explain is a hole,
# not an exemption.
#
# Two kinds of exemption are expected to appear here over time:
#   * fixtures -- a deliberately-shaped input to a conformance kit, not a
#     recipe anyone runs;
#   * `agent: self` -- a self-referential step cannot be made v2-safe, because
#     there is no bundle a `self` reference could be declared against
#     (bundle-recipes tracker item recipes-80q). Such a file stays legacy and
#     says so at the top of the file.
EXEMPT: dict[str, str] = {
    # path relative to the repository root -> reason
    "conformance/composition/fixtures/sample-good/recipes/seed-reconcile.yaml": (
        "Fixture, not a recipe anyone runs. It is the composition kit's example "
        "of a compliant automated step; adding a manifest would change what the "
        "kit is looking at."
    ),
    "conformance/composition/fixtures/sample-bad/recipes/seed-reconcile.yaml": (
        "Fixture, deliberately shaped to VIOLATE composition rule 1b by naming "
        "heavy-package helpers. Fixing it would delete the thing the kit tests."
    ),
    "conformance/composition/fixtures/sample-bad/recipes/stray-step.yaml": (
        "Fixture, deliberately shaped to VIOLATE composition rule 1e by being a "
        "step file bundle.md names nowhere."
    ),
}


def _recipe_files() -> list[Path]:
    """Every YAML file living in a `recipes/` directory in this repository."""
    return sorted(
        path
        for path in REPO_ROOT.rglob("*.yaml")
        if "recipes" in path.relative_to(REPO_ROOT).parts and ".git" not in path.parts
    )


def _names_an_agent(node: object) -> bool:
    """True if any mapping anywhere under `node` carries an `agent:` key."""
    if isinstance(node, dict):
        if "agent" in node:
            return True
        return any(_names_an_agent(value) for value in node.values())
    if isinstance(node, list):
        return any(_names_an_agent(item) for item in node)
    return False


def test_every_recipe_that_names_an_agent_declares_schema_v2() -> None:
    borrowers: list[str] = []
    checked: list[str] = []

    for path in _recipe_files():
        rel = path.relative_to(REPO_ROOT).as_posix()
        if rel in EXEMPT:
            continue

        try:
            document = yaml.safe_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:  # a recipe that will not parse is a real result
            borrowers.append(f"{rel}: does not parse as YAML ({exc.__class__.__name__})")
            continue

        if not isinstance(document, dict) or not _names_an_agent(document):
            continue

        checked.append(rel)
        if document.get("schema_version") != 2:
            borrowers.append(
                f"{rel}: names an `agent:` but declares "
                f"schema_version={document.get('schema_version')!r} -- its agents "
                f"would resolve from the calling session, not from the recipe"
            )
        elif not document.get("dependencies"):
            borrowers.append(
                f"{rel}: declares schema_version 2 but has no `dependencies:` "
                f"block -- there is no closure for its agents to resolve from"
            )

    assert checked, (
        "No recipe naming an `agent:` was found at all. Either the recipes moved "
        "or this test stopped looking where they live -- both are failures."
    )
    assert not borrowers, "Recipes that borrow their agents from the caller:\n  " + "\n  ".join(borrowers)


def test_exemptions_still_exist() -> None:
    """An exemption for a file that is gone is stale, and hides the next one."""
    missing = [rel for rel in EXEMPT if not (REPO_ROOT / rel).exists()]
    assert not missing, f"EXEMPT names files that no longer exist: {missing}"
