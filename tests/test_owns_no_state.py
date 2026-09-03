"""Surface.v1 clause 4: no data of its own.

Two ways to be sure. First, nothing in the package imports a database or an
object-relational mapper — a store cannot be kept without something to keep it
in. Second, after a full walk of every page, the only thing the app has written
outside the project is its last-read marker and its cache, and both live under
the app home, outside the repository.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from amplifier_converge.home import OWNED_SUBDIRS, app_home

PACKAGE = Path(__file__).resolve().parents[1] / "src" / "amplifier_converge"

#: If any of these are imported, the page has grown a store of its own.
FORBIDDEN = {
    "sqlite3",
    "sqlalchemy",
    "psycopg",
    "psycopg2",
    "pymongo",
    "redis",
    "tinydb",
    "shelve",
    "dbm",
    "duckdb",
    "peewee",
    "sqlmodel",
}


def _imported_modules() -> set[str]:
    found: set[str] = set()
    for path in PACKAGE.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                found.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                found.add(node.module.split(".")[0])
    return found


def test_no_database_is_imported_anywhere():
    offenders = sorted(_imported_modules() & FORBIDDEN)
    assert not offenders, f"the page has grown a store of its own: {offenders}"


def test_the_app_home_holds_only_the_two_permitted_things(client, project, app_home):
    for page in ("/", "/direction", "/direction/VISION", "/direction/gate.v1", "/operation"):
        assert client.get(page).status_code == 200
    client.post("/direction/VISION/mark-read", follow_redirects=False)

    if not app_home.exists():
        return
    top = {p.name for p in app_home.iterdir()}
    assert top <= set(OWNED_SUBDIRS), f"the page kept something it should not: {sorted(top)}"


def test_reading_a_document_never_writes_into_the_project(client, project):
    before = _fingerprint(project)
    for page in ("/", "/direction", "/direction/VISION", "/direction/gate.v1", "/operation"):
        client.get(page)
    client.post("/direction/VISION/mark-read", follow_redirects=False)
    assert _fingerprint(project) == before


def test_the_last_read_marker_lives_outside_the_project(client, project, app_home):
    client.post("/direction/VISION/mark-read", follow_redirects=False)
    markers = list(app_home.rglob("VISION.json"))
    assert markers, "the last-read marker was not written to the app home at all"
    for marker in markers:
        assert project not in marker.parents


def test_app_home_is_not_inside_any_project(monkeypatch):
    monkeypatch.delenv("AMPLIFIER_CONVERGE_HOME", raising=False)
    home = app_home()
    assert home.parts[-2:] == (".amplifier", "converge")


@pytest.mark.parametrize("subdir", OWNED_SUBDIRS)
def test_the_owned_list_is_exactly_two_things(subdir):
    assert len(OWNED_SUBDIRS) == 2
    assert subdir in ("last-read", "cache")


def _fingerprint(root: Path) -> set[tuple[str, int]]:
    return {
        (str(p.relative_to(root)), p.stat().st_size)
        for p in sorted(root.rglob("*"))
        if p.is_file()
    }
