"""Locking a document — the server half of the gate, against a real repository.

`experience-direction.v1` §11 gates the lock control on four conditions and
says nothing locks on its own. The browser half of that gate exists already;
what is checked here is the half that changes a file, because a gate whose
control reaches nothing is a gate over an empty doorway.

Everything below runs on a real git repository in a temporary directory: the
H1 is read back off disk, the commit is read back out of `git log`, and the
downstream consequence of locking — that an edit now writes a proposal beside
the document instead of touching it — is exercised through `writes.apply_change`
itself rather than asserted about. Nothing here is faked.
"""

from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app import auth, serve, writes  # noqa: E402

GOOD_USER = "tester"
GOOD_PASSWORD = "hunter2"

FOUR = [
    "It says what it means — your word",
    "It carries a real example of right and wrong — your word",
    "It can be checked against reality — Kept — every clause has a row",
    "You have read it and agreed — your word",
]

VISION = """# Demo Vision (DRAFT)

## Where this is going

One place for direction and one place for operation.

## Changelog

- **2026-09-05 — v1 (DRAFT).** First written.
"""

#: The plain shape: one word in the parenthetical, and nothing else in it.
DRAFT = """# Demo Contract — v1 (DRAFT)

## Core

**Core 1.** The app shows only what it can read.
"""

#: The shape this repository's own contracts actually carry.
AMENDED = """# Amended Contract — v1 (DRAFT — amended 2026-09-03, owner-ratified twice)

## Core

**Core 1.** The prose beside the status is not the status.
"""

#: A parenthetical that is not a status word, so there is nowhere obvious to
#: put one — and `documents.v1` §6 says there must be exactly one place.
PROSE = """# Prose Contract — v1 (content owner-ratified 2026-09-03)

## Core

**Core 1.** A heading may say more than its status.
"""

#: No parenthetical at all.
BARE = """# Bare Contract — v1

## Core

**Core 1.** A heading may say only its name.
"""

#: No heading at all: nowhere for a status to live.
HEADLESS = """Just a paragraph, with no heading above it.
"""

LOCKED = """# Locked Contract — v1 (FROZEN 2026-09-01)

## Core

**Core 1.** Nothing here changes in place.
"""

HIGHWAY = """# HIGHWAY — Demo batch

## Outcome
Have the lock gate reach a write.
"""


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "user.name=Test", "-c", "user.email=test@example.invalid", *args],
        cwd=repo,
        check=True,
        capture_output=True,
    )


def _read(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=repo, check=True, capture_output=True, text=True
    ).stdout.strip()


def _porcelain(repo: Path, rel: str) -> str:
    return _read(repo, "status", "--porcelain", "--", rel)


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _today() -> str:
    return writes._now().strftime("%Y-%m-%d")


@pytest.fixture
def project(tmp_path: Path) -> dict:
    """A repository with one document of every heading shape in it."""
    repo = tmp_path / "demo-repo"
    (repo / "docs").mkdir(parents=True)
    (repo / "contracts").mkdir()
    (repo / "docs" / "VISION.md").write_text(VISION, encoding="utf-8")
    (repo / "contracts" / "demo.v1.md").write_text(DRAFT, encoding="utf-8")
    (repo / "contracts" / "amended.v1.md").write_text(AMENDED, encoding="utf-8")
    (repo / "contracts" / "prose.v1.md").write_text(PROSE, encoding="utf-8")
    (repo / "contracts" / "bare.v1.md").write_text(BARE, encoding="utf-8")
    (repo / "contracts" / "headless.v1.md").write_text(HEADLESS, encoding="utf-8")
    (repo / "contracts" / "locked.v1.md").write_text(LOCKED, encoding="utf-8")

    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "seed: a vision and six contracts")

    batch = tmp_path / "hw-demo"
    batch.mkdir()
    (batch / "HIGHWAY.md").write_text(HIGHWAY, encoding="utf-8")

    conf = tmp_path / "converge-app.toml"
    conf.write_text(
        "[[managers]]\n"
        'id = "demo"\n'
        'name = "Demo manager"\n'
        f'batch_dir = "{batch}"\n'
        f'repos = ["{repo}"]\n'
        'tracker_project = ""\n'
        'tmux_socket = "test-socket-that-does-not-exist"\n',
        encoding="utf-8",
    )
    return {
        "repo": repo,
        "batch": batch,
        "config": conf,
        "secret": tmp_path / "secret",
        "state": tmp_path / "state.json",
    }


class _FakePam:
    def authenticate(self, username: str, password: str, service: str = "login") -> bool:
        assert service == "login"
        return username == GOOD_USER and password == GOOD_PASSWORD


@pytest.fixture
def client(project, monkeypatch) -> TestClient:
    monkeypatch.setattr(auth.pam_module, "pam", _FakePam)
    made = serve.create_app(
        config_path=project["config"], secret_path=project["secret"], state_path=project["state"]
    )
    return TestClient(made, follow_redirects=False)


def sign_in(client: TestClient) -> None:
    answer = client.post("/login", data={"username": GOOD_USER, "password": GOOD_PASSWORD, "next": "/"})
    assert answer.status_code == 302


def lock(client: TestClient, doc_id: str = "demo", conditions=None) -> "tuple[int, dict]":
    answer = client.post(
        f"/api/managers/demo/docs/demo-repo/{doc_id}/lock",
        json={"conditions": FOUR if conditions is None else conditions},
    )
    return answer.status_code, answer.json()


def read_doc(client: TestClient, doc_id: str = "demo") -> dict:
    return client.get(f"/api/managers/demo/docs/demo-repo/{doc_id}").json()


# --------------------------------------------------------------------------
# the gate, and the route existing at all
# --------------------------------------------------------------------------


def test_lock_refuses_anyone_without_a_cookie(client: TestClient) -> None:
    answer = client.post("/api/managers/demo/docs/demo-repo/demo/lock", json={"conditions": FOUR})
    assert answer.status_code == 401


def test_the_app_declares_a_write_that_locks(client: TestClient) -> None:
    """The measurement that filed this item read the app's own route table."""
    sign_in(client)
    paths = client.get("/openapi.json").json()["paths"]
    declared = [p for p, methods in paths.items() if "post" in methods]
    assert [p for p in declared if p.endswith("/lock")] == [
        "/api/managers/{mid}/docs/{repo_ident}/{doc_ident}/lock"
    ]


# --------------------------------------------------------------------------
# the acceptance, end to end
# --------------------------------------------------------------------------


def test_locking_stamps_the_h1_commits_it_and_the_document_reads_locked(client, project) -> None:
    """GIVEN a draft whose four conditions are met, WHEN the steward locks it."""
    sign_in(client)
    doc = project["repo"] / "contracts" / "demo.v1.md"
    assert read_doc(client)["locked"] == "", "the document was not a draft to begin with"

    code, body = lock(client)
    assert code == 200, body
    assert body["ok"] is True
    assert body["locked"] == "FROZEN"

    # ... the H1 carries (FROZEN <date>) in the file on disk.
    day = _today()
    first = doc.read_text(encoding="utf-8").splitlines()[0]
    assert first == f"# Demo Contract — v1 (FROZEN {day})"
    assert body["heading"] == first

    # ... the change is committed, in the steward's name, and nothing is left
    # uncommitted behind it.
    assert _porcelain(project["repo"], "contracts/demo.v1.md") == ""
    assert _read(project["repo"], "log", "-1", "--format=%an") == f"{GOOD_USER} via Converge"
    assert _read(project["repo"], "log", "-1", "--format=%H").startswith(body["sha"])
    subject = _read(project["repo"], "log", "-1", "--format=%s")
    assert subject == f"demo.v1: locked FROZEN {day} by {GOOD_USER} in Converge"

    # ... and re-opening the document shows it locked.
    again = read_doc(client)
    assert again["locked"] == "FROZEN"
    assert again["editable"] is False


def test_the_four_conditions_are_on_the_record_and_in_the_commit(client, project) -> None:
    """A lock is the steward's word, so it is written where their words go."""
    sign_in(client)
    code, body = lock(client)
    assert code == 200, body

    record = Path(body["recorded"])
    assert record.name == f"owner-ratifications-{_today()}.md"
    assert record.parent == project["repo"] / "docs" / "workflow"
    written = record.read_text(encoding="utf-8")
    for condition in FOUR:
        assert condition in written, f"the record does not carry: {condition}"
    assert GOOD_USER in written
    assert body["sha"] in written, "the record does not name the commit it is about"

    # The same four in the commit message body, so `git log` alone answers why.
    message = _read(project["repo"], "log", "-1", "--format=%b")
    for condition in FOUR:
        assert condition in message


def test_a_locked_document_now_takes_the_proposal_path_instead(client, project) -> None:
    """What locking is *for*: the writer stops touching the file.

    Exercised through `writes.apply_change`, the same function the edit and
    restore routes call, so this is the real downstream behaviour rather than
    a claim about it.
    """
    sign_in(client)
    assert lock(client)[0] == 200
    doc = project["repo"] / "contracts" / "demo.v1.md"
    before = _digest(doc)

    result = writes.apply_change(
        project["repo"],
        doc,
        change={"section": "Core", "now": "The app shows only what it can read.", "anchor": 5},
        text="The app shows only what it has read.",
        user=GOOD_USER,
    )
    assert result["ok"] is True
    assert result["mode"] == "candidate"
    assert result["locked"] == "FROZEN"
    assert Path(result["path"]).name == "demo.v1-candidate.md"
    assert _digest(doc) == before, "locking did not stop the writer touching the document"


# --------------------------------------------------------------------------
# every heading shape, and the one with nowhere to put a status
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "doc_id,expected",
    [
        ("demo", "# Demo Contract — v1 (FROZEN {day})"),
        ("amended", "# Amended Contract — v1 (FROZEN {day} — amended 2026-09-03, owner-ratified twice)"),
        ("prose", "# Prose Contract — v1 (FROZEN {day} — content owner-ratified 2026-09-03)"),
        ("bare", "# Bare Contract — v1 (FROZEN {day})"),
    ],
)
def test_the_status_lands_in_the_h1_parenthetical_and_keeps_the_rest(client, project, doc_id, expected) -> None:
    """`documents.v1` §6: status in the H1 parenthetical, and nowhere else."""
    sign_in(client)
    code, body = lock(client, doc_id)
    assert code == 200, body

    path = project["repo"] / "contracts" / f"{doc_id}.v1.md"
    text = path.read_text(encoding="utf-8")
    assert text.splitlines()[0] == expected.format(day=_today())
    assert text.count("(") == text.count(")"), "the heading was left with an unbalanced parenthesis"
    assert len([line for line in text.splitlines() if line.startswith("# ")]) == 1
    # Nothing below the heading moved.
    assert "**Core 1.**" in text


def test_a_document_with_no_heading_is_refused_and_left_alone(client, project) -> None:
    sign_in(client)
    doc = project["repo"] / "contracts" / "headless.v1.md"
    before = _digest(doc)

    code, body = lock(client, "headless")
    assert code == 400
    assert body["ok"] is False
    assert "no first heading" in body["error"]
    assert "documents.v1" in body["error"]
    assert _digest(doc) == before


# --------------------------------------------------------------------------
# what it refuses, and how loudly
# --------------------------------------------------------------------------


def test_locking_a_document_that_is_already_locked_is_refused_by_name(client, project) -> None:
    """The second half of the acceptance: it refuses, and it names the word."""
    sign_in(client)
    doc = project["repo"] / "contracts" / "locked.v1.md"
    before, head = _digest(doc), _read(project["repo"], "rev-parse", "HEAD")

    code, body = lock(client, "locked")
    assert code == 400
    assert body["ok"] is False
    assert "FROZEN" in body["error"], "the refusal does not name the locking word it found"
    assert "locked.v1.md" in body["error"]
    assert body["locked"] == "FROZEN"
    assert _digest(doc) == before, "the refusal still wrote to the document"
    assert _read(project["repo"], "rev-parse", "HEAD") == head, "the refusal still made a commit"


def test_locking_the_same_document_twice_is_refused_the_second_time(client) -> None:
    sign_in(client)
    assert lock(client)[0] == 200
    code, body = lock(client)
    assert code == 400
    assert "FROZEN" in body["error"]


@pytest.mark.parametrize("answered", [[], FOUR[:1], FOUR[:3], ["", "  ", "", ""]])
def test_fewer_than_four_conditions_locks_nothing(client, project, answered) -> None:
    """§11: the control is live only when all four are met, and the server counts them too."""
    sign_in(client)
    doc = project["repo"] / "contracts" / "demo.v1.md"
    before, head = _digest(doc), _read(project["repo"], "rev-parse", "HEAD")

    code, body = lock(client, "demo", answered)
    assert code == 400
    assert body["ok"] is False
    assert "four" in body["error"]
    assert _digest(doc) == before
    assert _read(project["repo"], "rev-parse", "HEAD") == head
    assert read_doc(client)["locked"] == ""


def test_a_document_with_uncommitted_changes_is_refused(client, project) -> None:
    """The commit names one path, so it would carry someone else's edit too."""
    sign_in(client)
    doc = project["repo"] / "contracts" / "demo.v1.md"
    doc.write_text(DRAFT + "\n**Core 2.** Someone was mid-sentence.\n", encoding="utf-8")

    code, body = lock(client)
    assert code == 400
    assert "uncommitted" in body["error"]
    assert "**Core 2.** Someone was mid-sentence." in doc.read_text(encoding="utf-8")
    assert doc.read_text(encoding="utf-8").splitlines()[0] == "# Demo Contract — v1 (DRAFT)"


def test_locking_a_document_that_is_not_there(client) -> None:
    sign_in(client)
    code, body = lock(client, "no-such-doc")
    assert code == 404
    assert "no-such-doc" in body["error"]


def test_locking_through_a_manager_that_is_not_there(client) -> None:
    sign_in(client)
    answer = client.post("/api/managers/nobody/docs/demo-repo/demo/lock", json={"conditions": FOUR})
    assert answer.status_code == 404
    assert "nobody" in answer.json()["error"]


def test_a_lock_with_no_body_at_all_is_refused_rather_than_crashing(client) -> None:
    sign_in(client)
    answer = client.post("/api/managers/demo/docs/demo-repo/demo/lock")
    assert answer.status_code == 400
    assert "four" in answer.json()["error"]


# --------------------------------------------------------------------------
# the freeze is one write: the stamp and the record of it land together
#
#   converge-p17d  A document is locked by editing its own H1, and the record
#                  of that lock is more text in the SAME file. Split across
#                  two writes, the second is refused by the locked-document
#                  guard that the first one just switched on, and the file is
#                  left half-frozen. Measured 2026-09-06 in the adopter
#                  harness (evaluations/adopter/RESULT.md, scenario 2).
# --------------------------------------------------------------------------


def _changelog_entries(text: str) -> list[str]:
    return [line for line in text.splitlines() if line.startswith("- **")]


def test_the_lock_writes_the_changelog_entry_in_the_same_commit(client, project) -> None:
    """GIVEN a drafted vision and the steward's word, WHEN it is locked, THEN
    the H1 status AND the entry recording that ratification are both in the
    file, and both are in the one commit."""
    sign_in(client)
    doc = project["repo"] / "docs" / "VISION.md"

    code, body = lock(client, "vision")
    assert code == 200, body

    day = _today()
    text = doc.read_text(encoding="utf-8")
    assert text.splitlines()[0] == f"# Demo Vision (FROZEN {day})"

    entries = _changelog_entries(text)
    assert entries[0].startswith(f"- **{day} \u2014 locked (FROZEN {day}).**"), entries
    assert "- **2026-09-05 \u2014 v1 (DRAFT).** First written." in entries, (
        "the older changelog entries were not kept"
    )

    # One commit, carrying both halves, and nothing of the document left over.
    assert _porcelain(project["repo"], "docs/VISION.md") == ""
    shown = _read(project["repo"], "show", "--format=", "--", "docs/VISION.md")
    assert f"+# Demo Vision (FROZEN {day})" in shown
    assert f"+- **{day} \u2014 locked (FROZEN {day}).**" in shown


def test_the_locked_document_never_reads_frozen_without_its_record(client, project) -> None:
    """The state the item forbids, asserted directly on the committed file:
    a FROZEN heading with no changelog line naming the word that froze it.

    Falsified the day this passes against a working tree where the entry was
    added by a SECOND write \u2014 hence the porcelain check: the assertion is
    about the committed state, not about what happens to be on disk.
    """
    sign_in(client)
    for doc_id, rel in [
        ("vision", "docs/VISION.md"),
        ("demo", "contracts/demo.v1.md"),
        ("bare", "contracts/bare.v1.md"),
    ]:
        code, body = lock(client, doc_id)
        assert code == 200, (doc_id, body)
        assert _porcelain(project["repo"], rel) == "", rel

        text = (project["repo"] / rel).read_text(encoding="utf-8")
        assert "FROZEN" in text.splitlines()[0], rel
        recorded = [
            line
            for line in text.splitlines()[1:]
            if not line.startswith("#") and "FROZEN" in line
        ]
        assert recorded, f"{rel} is frozen in its heading and nowhere records it"


def test_a_document_with_no_changelog_gets_one_at_the_end(client, project) -> None:
    """`documents.v1` Core 4 puts the changelog last, and both shipped
    templates produce one \u2014 but a document that has none must still come out
    of a lock carrying the record of it."""
    sign_in(client)
    assert lock(client, "demo")[0] == 200

    text = (project["repo"] / "contracts" / "demo.v1.md").read_text(encoding="utf-8")
    headings = [line for line in text.splitlines() if line.startswith("## ")]
    assert headings[-1] == "## Changelog", headings
    assert _changelog_entries(text)[0].startswith(f"- **{_today()} \u2014 locked")
    assert "**Core 1.** The app shows only what it can read." in text


def test_the_entry_names_where_the_four_conditions_are_kept(client, project) -> None:
    """Core 7 asks a changelog entry to carry its evidence. The evidence for a
    lock is the steward's four answers, and they are kept in the ratification
    record \u2014 so the entry names that file rather than asserting the lock."""
    sign_in(client)
    code, body = lock(client, "vision")
    assert code == 200, body

    day = _today()
    text = (project["repo"] / "docs" / "VISION.md").read_text(encoding="utf-8")
    entry = _changelog_entries(text)[0]
    assert f"owner-ratifications-{day}.md" in entry
    assert GOOD_USER in entry
    assert Path(body["recorded"]).name == f"owner-ratifications-{day}.md"


def test_the_record_is_not_a_second_heading_or_an_unbalanced_one(client, project) -> None:
    """The entry is history, not a second status: it must not add an H1, and
    it must not leave the file's parentheses unbalanced."""
    sign_in(client)
    for doc_id, rel in [
        ("vision", "docs/VISION.md"),
        ("amended", "contracts/amended.v1.md"),
        ("prose", "contracts/prose.v1.md"),
    ]:
        assert lock(client, doc_id)[0] == 200, doc_id
        text = (project["repo"] / rel).read_text(encoding="utf-8")
        assert len([ln for ln in text.splitlines() if ln.startswith("# ")]) == 1, rel
        assert text.count("(") == text.count(")"), rel
        assert text.endswith("\n"), rel


def test_a_refused_lock_writes_no_changelog_entry_either(client, project) -> None:
    """The two halves are one write, so a refusal leaves neither of them."""
    sign_in(client)
    doc = project["repo"] / "docs" / "VISION.md"
    before = _digest(doc)

    code, body = lock(client, "vision", FOUR[:2])
    assert code == 400
    assert _digest(doc) == before
    assert "locked (FROZEN" not in doc.read_text(encoding="utf-8")
