"""Shared ground for the tests.

Every test runs against a throwaway project and a throwaway app home, so
nothing here can touch a real project or a real steward's last-read markers.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE = REPO_ROOT / "conformance" / "surface" / "fixtures" / "app"


@pytest.fixture
def app_home(tmp_path, monkeypatch):
    home = tmp_path / "app-home"
    monkeypatch.setenv("AMPLIFIER_CONVERGE_HOME", str(home))
    return home


@pytest.fixture
def project(tmp_path, app_home) -> Path:
    """A copy of the example project, safe to write to."""
    target = tmp_path / "project"
    shutil.copytree(FIXTURE, target)
    return target


@pytest.fixture
def client(project):
    from fastapi.testclient import TestClient

    from amplifier_converge.web.app import create_app

    app = create_app(project, "kettle", include_remote_proposals=False)
    return TestClient(app)
