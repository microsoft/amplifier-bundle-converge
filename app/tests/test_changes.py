"""The Changes view, against a repository built to break the old one.

The steward's report was specific: "Many of the Before/Now are currently off by
one, where one of the Now items was new and so then the next Now was lined up
w/ the previous Before and so on." So the fixture here makes exactly that
shape on purpose — one sentence inserted in the middle of a paragraph and the
sentence right after it reworded, close enough together that git emits them as
a single hunk with one removal and two additions. Pairing by position gets that
wrong every time; pairing by likeness gets it right, and the first test is the
difference.

Everything else in this file is the same discipline as `test_api.py`: a real
git repository in a temp folder, real commits, real writes. Nothing is mocked
except PAM.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app import auth, changes, serve, writes  # noqa: E402

GOOD_USER = "tester"
OTHER_USER = "colleague"
GOOD_PASSWORD = "correct horse"

SOURCE_SHAPE = re.compile(r"^.+ \u00b7 [0-9a-f]{7} \u00b7 \d{4}-\d{2}-\d{2}$")


def _git(repo: Path, *args: str) -> str:
    done = subprocess.run(
        ["git", "-c", "user.name=Test", "-c", "user.email=test@example.invalid", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    return done.stdout


# --------------------------------------------------------------------------
# the document, in three states
# --------------------------------------------------------------------------

FIRST = """# Fixture Vision (DRAFT)

## Where this is going

The app has one place for direction.
Evidence beats claims.
The steward reads what changed.

## Principles

1. **Attention is scarce.** It is spent only where a person is irreplaceable.
2. **Grown, not declared.** A contract begins as a draft and becomes locked.
3. **Work is derived.** Every item traces to a gap between promise and reality.
"""

#: One sentence inserted in the middle, one later sentence reworded. Nothing
#: else moves — so anything else appearing as a card is the reader inventing.
SECOND = """# Fixture Vision (DRAFT)

## Where this is going

The app has one place for direction.
Evidence beats claims.
A second place shows the operation.
The steward reads exactly what changed since they last looked.

## Principles

1. **Attention is scarce.** It is spent only where a person is irreplaceable.
2. **Grown, not declared.** A contract begins as a draft and becomes locked.
3. **Work is derived.** Every item traces to a gap between promise and reality.
"""

#: A third state, used where a test needs the document to move again after the
#: steward has already marked it read.
THIRD = SECOND.replace(
    "2. **Grown, not declared.** A contract begins as a draft and becomes locked.",
    "2. **Grown, not declared.** A contract begins as a draft and becomes locked once four conditions are met.",
)

LOCKED_CONTRACT_FIRST = """# Locked Contract — v1 (FROZEN 2026-09-02)

**Who builds against this:** everyone downstream of this promise.

## Core (the teeth)

1. **The app shows only what it can read.** Silence is said, never filled in.
"""

LOCKED_CONTRACT_SECOND = """# Locked Contract — v1 (FROZEN 2026-09-02)

**Who builds against this:** everyone downstream of this promise.

## Core (the teeth)

1. **The app shows only what it can read.** Silence is said plainly, never filled in with a placeholder.
"""

INSERTED = "A second place shows the operation."
REWORDED_BEFORE = "The steward reads what changed."
REWORDED_NOW = "The steward reads exactly what changed since they last looked."


@pytest.fixture
def project(tmp_path: Path) -> dict:
    repo = tmp_path / "fixture-repo"
    (repo / "docs").mkdir(parents=True)
    (repo / "contracts").mkdir()
    (repo / "docs" / "VISION.md").write_text(FIRST, encoding="utf-8")
    (repo / "contracts" / "locked.v1.md").write_text(LOCKED_CONTRACT_FIRST, encoding="utf-8")
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "seed: the vision and one locked contract")

    (repo / "docs" / "VISION.md").write_text(SECOND, encoding="utf-8")
    (repo / "contracts" / "locked.v1.md").write_text(LOCKED_CONTRACT_SECOND, encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "vision: the operation becomes a place")

    conf = tmp_path / "converge-app.toml"
    conf.write_text(
        "[[managers]]\n"
        'id = "demo"\n'
        'name = "Demo manager"\n'
        f'repos = ["{repo}"]\n'
        'tmux_socket = "test-socket-that-does-not-exist"\n',
        encoding="utf-8",
    )
    return {
        "repo": repo,
        "config": conf,
        "secret": tmp_path / "secret",
        "state": tmp_path / "state.json",
    }


class _FakePam:
    def authenticate(self, username: str, password: str, service: str = "login") -> bool:
        return password == GOOD_PASSWORD and username in {GOOD_USER, OTHER_USER}


def _app(project, monkeypatch):
    monkeypatch.setattr(auth.pam_module, "pam", _FakePam)
    return serve.create_app(
        config_path=project["config"], secret_path=project["secret"], state_path=project["state"]
    )


def _client(project, monkeypatch, user: str = GOOD_USER) -> TestClient:
    made = TestClient(_app(project, monkeypatch), follow_redirects=False)
    answer = made.post("/login", data={"username": user, "password": GOOD_PASSWORD, "next": "/"})
    assert answer.status_code == 302 and auth.COOKIE in answer.cookies
    return made


@pytest.fixture
def client(project, monkeypatch) -> TestClient:
    return _client(project, monkeypatch)


DOC = "/api/managers/demo/docs/fixture-repo/vision"
LOCKED = "/api/managers/demo/docs/fixture-repo/locked"


def _changes(client: TestClient, url: str = DOC) -> list[dict]:
    answer = client.get(url)
    assert answer.status_code == 200, answer.text
    return answer.json()["changes"]


# --------------------------------------------------------------------------
# 1. alignment — the bug the steward actually reported
# --------------------------------------------------------------------------


def test_an_insertion_does_not_shift_the_pairs_after_it(client: TestClient, project) -> None:
    # The two edits are adjacent, so git puts them in one hunk: one removed
    # line and two added ones. Pairing by position would marry the removal to
    # the *inserted* sentence and leave the reworded one orphaned.
    raw = _git(project["repo"], "diff", "HEAD~1", "HEAD", "-U0", "--", "docs/VISION.md")
    hunks = [line for line in raw.splitlines() if line.startswith("@@")]
    assert len(hunks) == 1, f"the fixture must produce one hunk, not:\n{raw}"
    body = raw.split(hunks[0], 1)[1].splitlines()
    assert len([one for one in body if one.startswith("-")]) == 1, raw
    assert len([one for one in body if one.startswith("+")]) == 2, raw

    rows = _changes(client)
    assert len(rows) == 2, [(r["kind"], r["before"], r["now"]) for r in rows]

    added = [r for r in rows if r["kind"] == "new"]
    changed = [r for r in rows if r["kind"] == "changed"]
    assert len(added) == 1 and len(changed) == 1

    assert added[0]["before"] == ""
    assert added[0]["now"] == INSERTED

    assert changed[0]["before"] == REWORDED_BEFORE
    assert changed[0]["now"] == REWORDED_NOW


def test_a_deletion_is_shown_as_removed_with_nothing_pretending_to_replace_it(
    client: TestClient, project
) -> None:
    text = (project["repo"] / "docs" / "VISION.md").read_text(encoding="utf-8")
    (project["repo"] / "docs" / "VISION.md").write_text(text.replace("Evidence beats claims.\n", ""), encoding="utf-8")
    _git(project["repo"], "commit", "-q", "-m", "vision: drop a line", "--", "docs/VISION.md")

    rows = [r for r in _changes(client) if r["kind"] == "removed"]
    assert [r["before"] for r in rows] == ["Evidence beats claims."]
    assert rows[0]["now"] == ""


def test_alignment_leaves_a_sentence_unpaired_rather_than_pairing_it_wrongly() -> None:
    steps = changes.align(["The steward reads what changed."], ["Something else entirely.", REWORDED_NOW])
    assert steps == [(None, 0), (0, 1)]


# --------------------------------------------------------------------------
# 2. the labels — where it lives, and which commit changed it
# --------------------------------------------------------------------------


def test_a_card_says_where_it_lives_and_which_commit_changed_it(client: TestClient) -> None:
    rows = _changes(client)
    for one in rows:
        assert one["section"] == "Where this is going", one
        assert SOURCE_SHAPE.match(one["source"]), one["source"]
        assert one["sourceSubject"] == "vision: the operation becomes a place"
        assert len(one["sourceSha"]) == 7


def test_a_numbered_item_carries_its_number_in_the_section_path(client: TestClient, project) -> None:
    (project["repo"] / "docs" / "VISION.md").write_text(THIRD, encoding="utf-8")
    _git(project["repo"], "commit", "-q", "-m", "vision: name the four conditions", "--", "docs/VISION.md")
    rows = _changes(client)
    named = [r for r in rows if "Grown, not declared" in (r["now"] or r["before"])]
    assert named and named[0]["section"] == "Principles \u203a 2", [r["section"] for r in rows]


def test_heading_paths_read_the_document_not_the_commit() -> None:
    found = changes.heading_paths(SECOND)
    lines = SECOND.splitlines()
    where = {index: found[index] for index, line in enumerate(lines, start=1)}
    assert where[lines.index("Evidence beats claims.") + 1] == "Where this is going"
    assert where[lines.index("2. **Grown, not declared.** A contract begins as a draft and becomes locked.") + 1] == "Principles \u203a 2"
    # The blank line after an item closes it: the next heading is not "3".
    assert "\u203a" not in where[lines.index("## Principles") + 1]


# --------------------------------------------------------------------------
# 3. since you last read — server-side, per steward
# --------------------------------------------------------------------------


def test_marking_read_empties_the_list_until_the_document_moves_again(
    client: TestClient, project
) -> None:
    assert len(_changes(client)) == 2

    answer = client.post(f"{DOC}/read")
    assert answer.status_code == 200 and answer.json()["ok"] is True
    head = _git(project["repo"], "log", "-1", "--format=%H", "--", "docs/VISION.md").strip()
    assert answer.json()["sha"] == head

    assert _changes(client) == []

    (project["repo"] / "docs" / "VISION.md").write_text(THIRD, encoding="utf-8")
    _git(project["repo"], "commit", "-q", "-m", "vision: name the four conditions", "--", "docs/VISION.md")
    rows = _changes(client)
    assert len(rows) == 1 and "four conditions" in rows[0]["now"]


def test_the_read_point_lives_in_a_file_on_this_machine(client: TestClient, project) -> None:
    client.post(f"{DOC}/read")
    whole = json.loads(project["state"].read_text(encoding="utf-8"))
    read = whole["stewards"][GOOD_USER]["read"]["fixture-repo/vision"]
    assert read["sha"] == _git(project["repo"], "log", "-1", "--format=%H", "--", "docs/VISION.md").strip()


def test_one_stewards_reading_is_not_another_stewards(project, monkeypatch) -> None:
    mine = _client(project, monkeypatch, GOOD_USER)
    theirs = _client(project, monkeypatch, OTHER_USER)
    mine.post(f"{DOC}/read")
    assert _changes(mine) == []
    assert len(_changes(theirs)) == 2


def test_a_first_visit_shows_the_latest_change_rather_than_an_empty_page(client: TestClient) -> None:
    # No read point has ever been set for this steward, and the list is not
    # empty: the default is the commit before the last one for this file.
    assert len(_changes(client)) == 2


# --------------------------------------------------------------------------
# 4. Keep — remembered for the person, not for the browser
# --------------------------------------------------------------------------


def test_keep_survives_a_reload_and_a_new_browser(client: TestClient, project, monkeypatch) -> None:
    rows = _changes(client)
    assert [r["kept"] for r in rows] == [False, False]

    for one in rows:
        answer = client.post(f"{DOC}/changes/{one['id']}/keep", json={"kept": True})
        assert answer.status_code == 200 and answer.json()["kept"] is True

    # Same client, fresh request — the mark is not in the page's memory.
    assert all(r["kept"] for r in _changes(client))

    # A different browser entirely, same person: still kept.
    again = _client(project, monkeypatch, GOOD_USER)
    reloaded = _changes(again)
    assert all(r["kept"] for r in reloaded)
    assert {r["id"] for r in reloaded} == {r["id"] for r in rows}


def test_a_kept_mark_can_be_taken_back(client: TestClient) -> None:
    one = _changes(client)[0]
    client.post(f"{DOC}/changes/{one['id']}/keep", json={"kept": True})
    client.post(f"{DOC}/changes/{one['id']}/keep", json={"kept": False})
    found = next(r for r in _changes(client) if r["id"] == one["id"])
    assert found["kept"] is False


def test_a_change_keeps_its_name_across_requests(client: TestClient) -> None:
    assert [r["id"] for r in _changes(client)] == [r["id"] for r in _changes(client)]


def test_marking_read_puts_the_answered_marks_away(client: TestClient, project) -> None:
    for one in _changes(client):
        client.post(f"{DOC}/changes/{one['id']}/keep", json={"kept": True})
    client.post(f"{DOC}/read")
    whole = json.loads(project["state"].read_text(encoding="utf-8"))
    assert whole["stewards"][GOOD_USER]["kept"] == {}


# --------------------------------------------------------------------------
# 5. Edit — a commit on a draft, a proposal on a locked document
# --------------------------------------------------------------------------


def test_an_edit_to_a_draft_is_committed_in_the_stewards_name(client: TestClient, project) -> None:
    card = next(r for r in _changes(client) if r["kind"] == "changed")
    wanted = "The steward reads exactly what moved since they last looked."
    answer = client.post(f"{DOC}/changes/{card['id']}/edit", json={"text": wanted})
    assert answer.status_code == 200, answer.text
    result = answer.json()
    assert result["ok"] is True and result["mode"] == "commit"

    text = (project["repo"] / "docs" / "VISION.md").read_text(encoding="utf-8")
    assert wanted in text
    assert REWORDED_NOW not in text

    log = _git(project["repo"], "log", "-1", "--format=%an%x1f%s").strip().split("\x1f")
    assert log[0] == f"{GOOD_USER} via Converge"
    assert "VISION" in log[1] and "Where this is going" in log[1]
    assert _git(project["repo"], "status", "--porcelain").strip() == ""


def test_an_empty_edit_is_refused(client: TestClient) -> None:
    card = _changes(client)[0]
    answer = client.post(f"{DOC}/changes/{card['id']}/edit", json={"text": "   "})
    assert answer.status_code == 400 and answer.json()["ok"] is False


def test_an_edit_to_a_locked_document_never_touches_the_document(client: TestClient, project) -> None:
    contract = project["repo"] / "contracts" / "locked.v1.md"
    before_text = contract.read_text(encoding="utf-8")
    before_head = _git(project["repo"], "log", "-1", "--format=%H").strip()

    card = _changes(client, LOCKED)[0]
    wanted = "Silence is said in a sentence, never filled in with a placeholder."
    answer = client.post(f"{LOCKED}/changes/{card['id']}/edit", json={"text": wanted})
    assert answer.status_code == 200, answer.text
    result = answer.json()
    assert result["ok"] is True and result["mode"] == "candidate" and result["locked"] == "FROZEN"

    assert contract.read_text(encoding="utf-8") == before_text
    assert _git(project["repo"], "log", "-1", "--format=%H").strip() == before_head

    proposal = project["repo"] / "contracts" / "locked.v1-candidate.md"
    assert proposal.is_file()
    written = proposal.read_text(encoding="utf-8")
    # documents.v1 §8: three parts, in order, each change shown as the current
    # text in a fence and the replacement in a second fence.
    assert written.index("## The exact change") < written.index("## The evidence") < written.index("## What does not change")
    assert card["now"] in written
    assert wanted in written
    assert written.count("```text") == 2


def test_the_lock_is_read_from_the_document_not_from_the_request(project) -> None:
    assert writes.document_lock(project["repo"] / "contracts" / "locked.v1.md") == "FROZEN"
    assert writes.document_lock(project["repo"] / "docs" / "VISION.md") == ""


def test_a_draft_that_merely_mentions_being_ratified_is_still_a_draft(tmp_path: Path) -> None:
    # The real contract's H1 reads "(DRAFT — amended 2026-09-03, owner-ratified)".
    # Reading that as locked would put every draft out of the steward's reach.
    path = tmp_path / "documents.v1.md"
    path.write_text("# Documents Contract — v1 (DRAFT — amended 2026-09-03, owner-ratified)\n", encoding="utf-8")
    assert writes.document_lock(path) == ""


# --------------------------------------------------------------------------
# 6. Restore — the same two ways
# --------------------------------------------------------------------------


def test_restoring_a_reworded_sentence_puts_the_old_wording_back(client: TestClient, project) -> None:
    card = next(r for r in _changes(client) if r["kind"] == "changed")
    answer = client.post(f"{DOC}/changes/{card['id']}/restore")
    assert answer.status_code == 200, answer.text
    assert answer.json()["mode"] == "commit"

    text = (project["repo"] / "docs" / "VISION.md").read_text(encoding="utf-8")
    assert REWORDED_BEFORE in text
    assert REWORDED_NOW not in text
    assert "restored by" in _git(project["repo"], "log", "-1", "--format=%s")


def test_restoring_an_addition_takes_the_sentence_back_out(client: TestClient, project) -> None:
    card = next(r for r in _changes(client) if r["kind"] == "new")
    answer = client.post(f"{DOC}/changes/{card['id']}/restore")
    assert answer.status_code == 200, answer.text
    text = (project["repo"] / "docs" / "VISION.md").read_text(encoding="utf-8")
    assert INSERTED not in text
    assert REWORDED_NOW in text, "only the addition goes; the rewording stays"


def test_restoring_a_removed_sentence_puts_it_back_where_it_was(client: TestClient, project) -> None:
    doc = project["repo"] / "docs" / "VISION.md"
    doc.write_text(doc.read_text(encoding="utf-8").replace("Evidence beats claims.\n", ""), encoding="utf-8")
    _git(project["repo"], "commit", "-q", "-m", "vision: drop a line", "--", "docs/VISION.md")
    client.post(f"{DOC}/read")
    # Read point moved to the deleting commit, so re-read from the one before.
    client.post(f"{DOC}/changes/x/keep", json={"kept": False})  # a no-op write, proving keep needs no card
    whole = json.loads(project["state"].read_text(encoding="utf-8"))
    del whole["stewards"][GOOD_USER]["read"]["fixture-repo/vision"]
    project["state"].write_text(json.dumps(whole), encoding="utf-8")

    card = next(r for r in _changes(client) if r["kind"] == "removed")
    answer = client.post(f"{DOC}/changes/{card['id']}/restore")
    assert answer.status_code == 200, answer.text
    assert "Evidence beats claims." in doc.read_text(encoding="utf-8")


def test_restoring_on_a_locked_document_writes_a_proposal_and_changes_no_file(
    client: TestClient, project
) -> None:
    contract = project["repo"] / "contracts" / "locked.v1.md"
    before_text = contract.read_text(encoding="utf-8")
    card = _changes(client, LOCKED)[0]
    answer = client.post(f"{LOCKED}/changes/{card['id']}/restore")
    assert answer.status_code == 200 and answer.json()["mode"] == "candidate"
    assert contract.read_text(encoding="utf-8") == before_text
    written = (project["repo"] / "contracts" / "locked.v1-candidate.md").read_text(encoding="utf-8")
    assert card["before"] in written


def test_a_change_that_is_no_longer_in_the_reading_is_said_so(client: TestClient) -> None:
    answer = client.post(f"{DOC}/changes/deadbeef1234/edit", json={"text": "anything"})
    assert answer.status_code == 404


def test_the_change_routes_refuse_a_stranger(project, monkeypatch) -> None:
    stranger = TestClient(_app(project, monkeypatch), follow_redirects=False)
    assert stranger.post(f"{DOC}/read").status_code == 401
    assert stranger.post(f"{DOC}/changes/abc/keep", json={"kept": True}).status_code == 401
    assert stranger.post(f"{DOC}/changes/abc/edit", json={"text": "x"}).status_code == 401
    assert stranger.post(f"{DOC}/changes/abc/restore").status_code == 401


# --------------------------------------------------------------------------
# 7. the edges that fail quietly if nobody looks
# --------------------------------------------------------------------------


def test_a_hash_inside_a_code_fence_is_code_and_not_a_heading() -> None:
    text = "# Title\n\n## Real Section\n\n```bash\n# not a heading\n```\n\nA sentence.\n"
    found = changes.heading_paths(text)
    lines = text.splitlines()
    assert found[lines.index("A sentence.") + 1] == "Real Section"


def test_the_sentence_is_reworded_where_the_steward_was_looking(client: TestClient, project) -> None:
    # The same sentence twice in one document: the card's own line must win,
    # not whichever copy comes first in the file.
    doc = project["repo"] / "docs" / "VISION.md"
    doc.write_text(doc.read_text(encoding="utf-8").replace("## Principles", f"{INSERTED}\n\n## Principles"), encoding="utf-8")
    _git(project["repo"], "commit", "-q", "-m", "vision: say it twice", "--", "docs/VISION.md")
    client.post(f"{DOC}/read")
    whole = json.loads(project["state"].read_text(encoding="utf-8"))
    del whole["stewards"][GOOD_USER]["read"]["fixture-repo/vision"]
    project["state"].write_text(json.dumps(whole), encoding="utf-8")

    card = next(r for r in _changes(client) if r["now"] == INSERTED)
    answer = client.post(f"{DOC}/changes/{card['id']}/edit", json={"text": "The second copy is the one that moved."})
    assert answer.status_code == 200, answer.text
    lines = doc.read_text(encoding="utf-8").splitlines()
    assert lines.count(INSERTED) == 1, "the untouched copy is still there"
    assert "The second copy is the one that moved." in lines


def test_an_edit_refuses_to_sweep_up_an_uncommitted_change(client: TestClient, project) -> None:
    doc = project["repo"] / "docs" / "VISION.md"
    card = next(r for r in _changes(client) if r["kind"] == "changed")
    doc.write_text(doc.read_text(encoding="utf-8") + "\nSomething nobody asked for.\n", encoding="utf-8")

    answer = client.post(f"{DOC}/changes/{card['id']}/edit", json={"text": "Anything at all."})
    assert answer.status_code == 400
    assert "uncommitted" in answer.json()["error"]
    assert "Something nobody asked for." in doc.read_text(encoding="utf-8"), "the file is left exactly as it was"
    assert "Anything at all." not in doc.read_text(encoding="utf-8")
