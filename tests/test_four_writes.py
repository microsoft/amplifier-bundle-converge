"""Surface.v1 clause 3: exactly four writes, each a manager-session operation.

The number is the promise, so it is asserted three ways: the registry has four
entries, the app exposes four write routes and no more, and every form on every
page posts to one of them.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from amplifier_converge.web.app import (
    NON_WRITE_POSTS,
    create_app,
    declared_write_names,
    non_write_post_routes,
    write_routes,
)
from amplifier_converge.writing import EXPECTED_WRITE_COUNT, WRITES

EXPECTED = {
    "answer-with-a-word",
    "signal-priority",
    "drop-feedback",
    "steer",
}


def test_registry_holds_exactly_four():
    assert len(WRITES) == EXPECTED_WRITE_COUNT == 4
    assert declared_write_names() == EXPECTED


def test_every_write_names_a_manager_operation():
    for write in WRITES:
        assert write.manager_operation.strip(), f"{write.name} names no manager operation"
        assert write.lands_in.strip(), f"{write.name} does not say where it lands"


def test_the_app_exposes_exactly_those_four_write_routes(project):
    app = create_app(project, "kettle", include_remote_proposals=False)
    assert write_routes(app) == {f"/do/{name}" for name in EXPECTED}


def test_the_only_other_post_route_is_the_declared_non_write(project):
    app = create_app(project, "kettle", include_remote_proposals=False)
    assert non_write_post_routes(app) == set(NON_WRITE_POSTS)


def test_the_non_write_changes_nothing_in_the_project(client, project):
    before = _fingerprint(project)
    response = client.post("/direction/VISION/mark-read", follow_redirects=False)
    assert response.status_code == 303
    assert _fingerprint(project) == before


@pytest.mark.parametrize("page", ["/", "/direction", "/direction/gate.v1", "/operation"])
def test_every_form_posts_to_one_of_the_four(client, page):
    html = client.get(page).text
    actions = set(re.findall(r'<form[^>]*action="([^"]+)"', html))
    for action in actions:
        assert action.startswith("/do/") or action in {
            "/direction/VISION/mark-read",
            "/direction/gate.v1/mark-read",
            "/direction/half.v1/mark-read",
        }, f"{page} posts to {action}, which is not one of the four writes"
        if action.startswith("/do/"):
            assert action.removeprefix("/do/") in EXPECTED


def _fingerprint(root: Path) -> set[tuple[str, int]]:
    return {
        (str(p.relative_to(root)), p.stat().st_size)
        for p in sorted(root.rglob("*"))
        if p.is_file()
    }
