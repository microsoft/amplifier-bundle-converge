"""A teammate may draft; only the steward decides. Both halves, proven.

`experience-direction.v1` Core 10 promises concurrent editing met with
courtesy presence and reconciliation -- which needs two people who can both
write. `experience-collaboration.v1` Core 8 reserves whose *word counts* to
the manager session's registered steward: ratification, and with it locking,
priority, steering and the steward's own terminal.

Between those two sits the regression this file guards (converge-bk6o).
`50d3c48` put a `_steward_denied` check in `serve._reword`, which serves
`changes/{id}/edit` and `changes/{id}/restore`, and that turned Core 10 into
a single-writer lock: a signed-in teammate could no longer save a draft at
all. The gate was removed from that one function. Everything below asserts
BOTH directions of the resulting line, against the real handlers and the real
write path -- no mocked core write, no test-only auth bypass:

* a teammate who is NOT the steward may edit and restore a DRAFT document,
* the same teammate's write to a LOCKED document becomes a proposal beside it
  and leaves the source byte-identical,
* decision, lock, priority, steer and terminal keystrokes each still refuse
  that teammate 403 and mutate nothing,
* unauthenticated and wrong-origin writes are still refused, and a CSRF
  cookie/header pair that disagrees is still refused.

ANA is the registered steward. BROOK is a different signed-in person. They
are never the same user -- a test that quietly makes them one would assert
nothing at all about collaboration.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app import auth, serve  # noqa: E402

ANA = "ana"
BROOK = "brook"

VISION_FIRST = """# Demo vision (DRAFT)

## Where this is going

One place for direction and one place for operation.
The console is a tab you visit.
"""

VISION_SECOND = """# Demo vision (DRAFT)

## Where this is going

One place for direction and one place for operation.
The console is a place you work, not a tab you visit.
"""

LOCKED_FIRST = """# Sample Contract -- v1 (FROZEN 2026-09-06)

## Core

1. A promise this project keeps.
2. A second promise, worded once.
"""

LOCKED_SECOND = """# Sample Contract -- v1 (FROZEN 2026-09-06)

## Core

1. A promise this project keeps.
2. A second promise, worded twice.
"""


def _git(repo: Path, *args: str) -> str:
    done = subprocess.run(
        ["git", "-c", "user.name=Test", "-c", "user.email=test@example.invalid", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    return done.stdout


@pytest.fixture
def project(tmp_path: Path) -> dict:
    """One repository with a DRAFT document and a LOCKED one, two commits each.

    Two commits is what gives `changes.changes_for` something to offer with
    no read point at all, which is exactly the state a teammate opening the
    document for the first time is in.
    """
    repo = tmp_path / "demo-repo"
    (repo / "docs").mkdir(parents=True)
    (repo / "contracts").mkdir(parents=True)
    (repo / "docs" / "VISION.md").write_text(VISION_FIRST, encoding="utf-8")
    (repo / "contracts" / "sample.v1.md").write_text(LOCKED_FIRST, encoding="utf-8")
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "seed: a draft and a locked contract")

    (repo / "docs" / "VISION.md").write_text(VISION_SECOND, encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "the console becomes a place")
    (repo / "contracts" / "sample.v1.md").write_text(LOCKED_SECOND, encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "the second promise is reworded")

    conf = tmp_path / "converge-app.toml"
    conf.write_text(
        "[[managers]]\n"
        'id = "demo"\n'
        'name = "Demo manager"\n'
        f'repos = ["{repo}"]\n'
        'tracker_project = ""\n'
        'tmux_socket = "test-socket-that-does-not-exist"\n'
        'manager_tmux = "manager-session"\n'
        f'steward = "{ANA}"\n',
        encoding="utf-8",
    )
    return {
        "config": conf,
        "secret": tmp_path / "secret",
        "state": tmp_path / "state.json",
        "sessions": tmp_path / "sessions.json",
        "repo": repo,
        "vision": repo / "docs" / "VISION.md",
        "locked": repo / "contracts" / "sample.v1.md",
        "root": tmp_path,
    }


def _client(project: dict, user: str) -> TestClient:
    """A real signed-in client: a cookie this app's own `Sessions` issued.

    Nothing is monkeypatched into the gate -- the cookie goes through the
    same middleware every browser request does.
    """
    made = serve.create_app(
        config_path=project["config"],
        secret_path=project["secret"],
        state_path=project["state"],
        sessions_path=project["sessions"],
    )
    client = TestClient(made)
    sessions = auth.Sessions(auth.read_or_make_secret(project["secret"]))
    client.cookies.set(auth.COOKIE, sessions.issue(user))
    return client


def _first_change(client: TestClient, doc: str) -> dict:
    answer = client.get(f"/api/managers/demo/docs/demo-repo/{doc}")
    assert answer.status_code == 200, answer.text
    moved = answer.json()["changes"]
    assert moved, f"no change card to act on for {doc}"
    return moved[0]


# --------------------------------------------------------------------------
# the half that regressed: a teammate may draft
# --------------------------------------------------------------------------


def test_a_teammate_who_is_not_the_steward_may_edit_a_draft(project) -> None:
    brook = _client(project, BROOK)
    card = _first_change(brook, "vision")
    print(f"\nthe registered steward is {ANA!r}; the person writing is {BROOK!r}")
    print(f"brook edits: {card['id']} in section {card['section']!r}")

    answer = brook.post(
        f"/api/managers/demo/docs/demo-repo/vision/changes/{card['id']}/edit",
        json={"text": "The console is a place brook works in every day."},
    )
    said = answer.json()
    after = project["vision"].read_text(encoding="utf-8")
    log = _git(project["repo"], "log", "-1", "--format=%s%n%an")
    print(f"the app answered {answer.status_code}: {said.get('said') or said}")
    print(f"brook's wording is in the file: {'brook works in every day' in after}")
    print("last commit:\n  " + "\n  ".join(log.strip().splitlines()))

    assert answer.status_code == 200, answer.text
    assert said["ok"] and said["mode"] == "commit"
    assert "brook works in every day" in after
    assert BROOK in log, "the commit did not record who actually wrote it"


def test_a_teammate_who_is_not_the_steward_may_restore_a_draft_wording(project) -> None:
    brook = _client(project, BROOK)
    card = _first_change(brook, "vision")
    before_words = card["before"]
    print(f"\nbrook restores the earlier wording: {before_words!r}")

    answer = brook.post(
        f"/api/managers/demo/docs/demo-repo/vision/changes/{card['id']}/restore",
        json={},
    )
    said = answer.json()
    after = project["vision"].read_text(encoding="utf-8")
    print(f"the app answered {answer.status_code}: {said.get('said') or said}")
    print(f"the earlier wording is back: {'The console is a tab you visit.' in after}")

    assert answer.status_code == 200, answer.text
    assert said["ok"] and said["mode"] == "commit"
    assert "The console is a tab you visit." in after


def test_the_steward_can_still_edit_a_draft_too(project) -> None:
    """The gate did not move for the steward either -- the point is that the
    door is open to both, not that it swapped which one it excludes."""
    ana = _client(project, ANA)
    card = _first_change(ana, "vision")
    answer = ana.post(
        f"/api/managers/demo/docs/demo-repo/vision/changes/{card['id']}/edit",
        json={"text": "The console is a place ana works in every day."},
    )
    print(f"\nana (the steward) edits: {answer.status_code} {answer.json().get('said')}")
    assert answer.status_code == 200, answer.text
    assert "ana works in every day" in project["vision"].read_text(encoding="utf-8")


# --------------------------------------------------------------------------
# the half that must NOT move: locked documents, and steward-only powers
# --------------------------------------------------------------------------


def test_a_teammates_edit_of_a_locked_document_becomes_a_proposal(project) -> None:
    """Forced past any browser gate, straight at the handler: the locked
    source is byte-identical afterwards and the wording waits in a candidate."""
    brook = _client(project, BROOK)
    card = _first_change(brook, "sample")
    before_bytes = project["locked"].read_bytes()

    answer = brook.post(
        f"/api/managers/demo/docs/demo-repo/sample/changes/{card['id']}/edit",
        json={"text": "2. A second promise, reworded by a teammate."},
    )
    said = answer.json()
    candidate = project["repo"] / "contracts" / "sample.v1-candidate.md"
    after_bytes = project["locked"].read_bytes()
    print(f"\nbrook edits a FROZEN contract: {answer.status_code} {said.get('said')}")
    print(f"mode: {said.get('mode')}  locked word: {said.get('locked')}")
    print(f"the source changed: {after_bytes != before_bytes}")
    print(f"the candidate exists: {candidate.is_file()}")

    assert answer.status_code == 200, answer.text
    assert said["ok"] and said["mode"] == "candidate"
    assert said["locked"] == "FROZEN"
    assert after_bytes == before_bytes, "a write to a locked document mutated the source"
    assert candidate.is_file(), "no proposal was written beside the locked document"
    assert "reworded by a teammate" in candidate.read_text(encoding="utf-8")


STEWARD_ONLY = [
    ("/api/managers/demo/decision",
     {"repoId": "demo-repo", "docId": "vision", "proposalId": "p", "decision": "ratified"}),
    ("/api/managers/demo/priority", {"item": "x", "direction": "raise"}),
    ("/api/managers/demo/steer", {"lanes": 3}),
    ("/api/tmux/test-socket-that-does-not-exist/manager-session/keys", {"keys": "echo hi"}),
]


@pytest.mark.parametrize("path,payload", STEWARD_ONLY)
def test_a_teammate_is_still_refused_every_steward_only_power(project, path, payload) -> None:
    brook = _client(project, BROOK)
    before = _git(project["repo"], "log", "--format=%H").strip()
    dirty_before = _git(project["repo"], "status", "--porcelain").strip()

    answer = brook.post(path, json=payload)
    said = answer.json().get("error", "")
    after = _git(project["repo"], "log", "--format=%H").strip()
    dirty_after = _git(project["repo"], "status", "--porcelain").strip()
    print(f"\n{path} as {BROOK}: {answer.status_code} {said}")
    print(f"commits before/after: {len(before.splitlines())}/{len(after.splitlines())}; "
          f"working tree dirty: {bool(dirty_after)}")

    assert answer.status_code == 403, answer.text
    assert ANA in said or "no registered steward" in said or "nobody may" in said, said
    assert after == before, "a refused steward-only write still made a commit"
    assert dirty_after == dirty_before, "a refused steward-only write still touched the tree"


def test_locking_a_document_is_still_the_stewards_alone(project) -> None:
    """The lock route keeps its gate -- `experience-direction.v1` Core 11 --
    and the document's own H1 is asserted afterwards, not just the status."""
    brook = _client(project, BROOK)
    before = project["vision"].read_text(encoding="utf-8")
    answer = brook.post(
        "/api/managers/demo/docs/demo-repo/vision/lock",
        json={"conditions": ["a", "b", "c", "d"]},
    )
    after = project["vision"].read_text(encoding="utf-8")
    print(f"\nbrook tries to lock the vision: {answer.status_code} {answer.json().get('error')}")
    print(f"the H1 still reads: {after.splitlines()[0]!r}")
    assert answer.status_code == 403, answer.text
    assert ANA in answer.json()["error"]
    assert after == before, "a refused lock still changed the document"
    assert "(DRAFT)" in after.splitlines()[0]


# --------------------------------------------------------------------------
# the global gates, unchanged
# --------------------------------------------------------------------------


def test_an_unsigned_in_write_is_still_refused(project) -> None:
    app = serve.create_app(
        config_path=project["config"], secret_path=project["secret"],
        state_path=project["state"], sessions_path=project["sessions"],
    )
    stranger = TestClient(app)
    answer = stranger.post(
        "/api/managers/demo/docs/demo-repo/vision/changes/anything/edit", json={"text": "no"}
    )
    print(f"\nno cookie at all: {answer.status_code} {answer.json()}")
    assert answer.status_code == 401
    assert "The console is a place you work" in project["vision"].read_text(encoding="utf-8")


def test_a_cross_origin_write_is_still_refused(project) -> None:
    brook = _client(project, BROOK)
    card = _first_change(brook, "vision")
    answer = brook.post(
        f"/api/managers/demo/docs/demo-repo/vision/changes/{card['id']}/edit",
        json={"text": "written from somewhere else"},
        headers={"Origin": "https://evil.example"},
    )
    print(f"\nsigned in, wrong Origin: {answer.status_code} {answer.json()}")
    assert answer.status_code == 403
    assert "cross-origin" in answer.json()["error"]
    assert "written from somewhere else" not in project["vision"].read_text(encoding="utf-8")


def test_a_csrf_pair_that_disagrees_is_still_refused(project) -> None:
    """The double-submit check, exactly as `auth.csrf_ok` defines it.

    A *disagreeing* pair is the signal a forged or stale request produces and
    it is refused here. A pair that is wholly ABSENT is deliberately not
    treated as an attack (see `auth.csrf_ok`'s own docstring): same-origin
    carries that case, and every test client in this repository -- and every
    legitimate non-browser caller -- would otherwise be refused. This test
    asserts the behaviour the app actually promises rather than a stricter
    one it does not.
    """
    brook = _client(project, BROOK)
    card = _first_change(brook, "vision")
    brook.cookies.set(auth.CSRF_COOKIE, "the-real-token")
    answer = brook.post(
        f"/api/managers/demo/docs/demo-repo/vision/changes/{card['id']}/edit",
        json={"text": "written with a stale token"},
        headers={auth.CSRF_HEADER: "a-stale-token"},
    )
    print(f"\ncookie and header disagree: {answer.status_code} {answer.json()}")
    assert answer.status_code == 403
    assert "CSRF" in answer.json()["error"]
    assert "stale token" not in project["vision"].read_text(encoding="utf-8")
