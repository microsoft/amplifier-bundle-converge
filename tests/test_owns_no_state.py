"""Surface.v1 clause 4: no data of its own.

Nothing in the package imports a database or an object-relational mapper — a
store cannot be kept without something to keep it in — and the one place it may
write, the app home, holds exactly two things and sits outside any repository.

The three assertions that proved this by walking every page of the retired
server-rendered page were deleted with it on 2026-09-06. What they proved that
these do not — that a last-read marker written during a real read lands outside
the project — now has no check at this level; that is filed, not forgotten.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from amplifier_converge.home import OWNED_SUBDIRS, app_home

PACKAGE = Path(__file__).resolve().parents[1] / "src" / "amplifier_converge"

#: If any of these are imported, the package has grown a store of its own.
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
    assert not offenders, f"the package has grown a store of its own: {offenders}"


def test_app_home_is_not_inside_any_project(monkeypatch):
    monkeypatch.delenv("AMPLIFIER_CONVERGE_HOME", raising=False)
    home = app_home()
    assert home.parts[-2:] == (".amplifier", "converge")


@pytest.mark.parametrize("subdir", OWNED_SUBDIRS)
def test_the_owned_list_is_exactly_two_things(subdir):
    assert len(OWNED_SUBDIRS) == 2
    assert subdir in ("last-read", "cache")
