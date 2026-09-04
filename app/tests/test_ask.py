"""Asking for a proposal — the fifth write, against a real repository.

`experience-direction.v1` clause 9 makes one promise with two halves: an ask is
scoped (a paragraph, a document, every document), and its output is *always* a
proposal — never a silent edit, never a chat. Both halves are checked here on a
real git repository rather than on a canned payload, because the half that
matters most is the one about a file on disk.

The drafting session is the one thing faked, and it is faked at
`subprocess.run` rather than at the app's own drafter, so the code path under
test is the real one: the app really builds an `amplifier run` command line and
really believes the answer it gets back.
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
GOOD_PASSWORD = "let-me-in"


VISION = """# Demo Vision (DRAFT)

## Where this is going

One place for direction and one place for operation.

## Principles

The app has two places.
Evidence beats claims.
"""

CONTRACT = """# Demo Contract — v1 (DRAFT)

## Core

**Core 1.** The app shows only what it can read.
"""

LOCKED = """# Locked Contract — v1 (FROZEN 2026-09-01)

## Core

**Core 1.** Nothing here changes in place.
"""

HIGHWAY = """# HIGHWAY — Demo batch

## Outcome
Have the fifth write answer.
"""


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "user.name=Test", "-c", "user.email=test@example.invalid", *args],
        cwd=repo,
        check=True,
        capture_output=True,
    )


def _porcelain(repo: Path, rel: str) -> str:
    return subprocess.run(
        ["git", "status", "--porcelain", "--", rel],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture
def project(tmp_path: Path) -> dict:
    """A repository a steward could actually be reading, and a batch beside it."""
    repo = tmp_path / "demo-repo"
    (repo / "docs").mkdir(parents=True)
    (repo / "contracts").mkdir()
    (repo / "docs" / "VISION.md").write_text(VISION, encoding="utf-8")
    (repo / "contracts" / "demo.v1.md").write_text(CONTRACT, encoding="utf-8")
    (repo / "contracts" / "locked.v1.md").write_text(LOCKED, encoding="utf-8")

    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "seed: a vision and two contracts")

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


def ask(client: TestClient, **body) -> "tuple[int, dict]":
    payload = {"repoId": "demo-repo", "docId": "demo", "scope": "document", "text": "", "section": ""}
    payload.update(body)
    answer = client.post("/api/managers/demo/ask", json=payload)
    return answer.status_code, answer.json()


# --------------------------------------------------------------------------
# the gate, and the route existing at all
# --------------------------------------------------------------------------


def test_ask_refuses_anyone_without_a_cookie(client: TestClient) -> None:
    assert client.post("/api/managers/demo/ask", json={"scope": "document", "text": "hi"}).status_code == 401


def test_the_app_declares_a_write_that_produces_a_proposal(client: TestClient) -> None:
    """Rule 9 of the direction kit reads the app's own route table, not its code."""
    sign_in(client)
    paths = client.get("/openapi.json").json()["paths"]
    writes_declared = [p for p, methods in paths.items() if "post" in methods]
    assert [p for p in writes_declared if "ask" in p.lower()] == ["/api/managers/{mid}/ask"]


# --------------------------------------------------------------------------
# all three scopes, and what each one leaves on disk
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "scope,section",
    [("paragraph", "Principles"), ("document", ""), ("all", "")],
)
def test_every_scope_comes_back_as_a_proposal(client, project, scope, section) -> None:
    sign_in(client)
    doc = project["repo"] / "docs" / "VISION.md"
    before, dirt = _digest(doc), _porcelain(project["repo"], "docs/VISION.md")

    code, body = ask(
        client,
        docId="vision",
        scope=scope,
        section=section,
        text="Say plainly that evidence beats claims everywhere.",
    )
    assert code == 200, body
    assert body["ok"] is True
    assert body["scope"] == scope
    assert body["proposal"], "the answer must name the proposal it made"

    made = Path(body["path"])
    assert made.exists(), f"{made} is not on disk"
    assert made.parent == doc.parent, "a proposal belongs beside the document it is about"
    assert made.name == "VISION.v1-candidate.md"

    # The half of clause 9 that is about the document itself.
    assert _digest(doc) == before, "the ask edited the document"
    assert _porcelain(project["repo"], "docs/VISION.md") == dirt
    assert body["documentUntouched"] is True


@pytest.mark.parametrize("scope", ["paragraph", "document", "all"])
def test_every_scope_appears_in_the_documents_review_view(client, scope) -> None:
    sign_in(client)
    code, body = ask(client, docId="vision", scope=scope, section="Principles", text="Make it plainer.")
    assert code == 200, body

    seen = client.get("/api/managers/demo/docs/demo-repo/vision").json()["proposals"]
    assert [one for one in seen if one["id"] == body["proposal"]], f"{body['proposal']} is not in Review: {seen}"


def test_the_proposal_has_the_three_parts_in_order(client, project) -> None:
    """`documents.v1` §8: the exact change, the evidence, what does not change."""
    sign_in(client)
    code, body = ask(client, docId="vision", scope="paragraph", section="Principles", text="Say it once, not twice.")
    assert code == 200, body
    text = Path(body["path"]).read_text(encoding="utf-8")

    change = text.index("## The exact change")
    evidence = text.index("## The evidence")
    unchanged = text.index("## What does not change")
    assert change < evidence < unchanged

    # "Each change shows the current text in a fenced block, then the
    # replacement in a second fence."
    assert text[change:evidence].count("```text") == 2
    assert "The app has two places." in text[change:evidence], "the paragraph asked about is not quoted back"
    assert "Say it once, not twice." in text, "the steward's own words are not in the proposal"


def test_an_ask_across_every_document_names_them(client) -> None:
    sign_in(client)
    code, body = ask(client, docId="vision", scope="all", text="Use the same words for state everywhere.")
    assert code == 200, body
    text = Path(body["path"]).read_text(encoding="utf-8")
    assert "docs/VISION.md" in text
    assert "contracts/demo.v1.md" in text
    assert "contracts/locked.v1.md" in text
    assert "every document in this repository" in text


def test_a_second_ask_joins_the_open_proposal_in_order(client) -> None:
    sign_in(client)
    first = ask(client, docId="vision", scope="document", text="First ask.")[1]
    second = ask(client, docId="vision", scope="paragraph", section="Principles", text="Second ask.")[1]
    assert second["proposal"] == first["proposal"]
    assert second["merged"] is True

    text = Path(second["path"]).read_text(encoding="utf-8")
    assert "First ask." in text and "Second ask." in text
    assert text.index("## The exact change") < text.index("Second ask.") < text.index("## The evidence")


def test_a_joined_ask_puts_its_own_evidence_on_the_record(client) -> None:
    """A proposal whose evidence names one ask and whose body carries two is a half-truth."""
    sign_in(client)
    ask(client, docId="vision", scope="document", text="First ask.")
    second = ask(client, docId="vision", scope="all", text="Second ask.")[1]

    text = Path(second["path"]).read_text(encoding="utf-8")
    evidence = text[text.index("## The evidence"):text.index("## What does not change")]
    assert 'verbatim: "First ask."' in evidence
    assert 'verbatim: "Second ask."' in evidence
    assert "The ask covers every document in this repository." in evidence
    assert text.index("## The evidence") < text.index("## What does not change")


def test_an_ask_about_a_locked_document_still_only_writes_beside_it(client, project) -> None:
    sign_in(client)
    doc = project["repo"] / "contracts" / "locked.v1.md"
    before = _digest(doc)
    code, body = ask(client, docId="locked", scope="document", text="Loosen Core 1.")
    assert code == 200, body
    assert body["locked"] == "FROZEN"
    assert Path(body["path"]).name == "locked.v1-candidate.md"
    assert _digest(doc) == before


# --------------------------------------------------------------------------
# what it refuses, and how loudly
# --------------------------------------------------------------------------


def test_an_unnamed_scope_is_refused_by_name(client) -> None:
    sign_in(client)
    code, body = ask(client, docId="vision", scope="everything", text="Anything.")
    assert code == 400
    assert body["ok"] is False
    for named in ("paragraph", "document", "all"):
        assert named in body["error"]


def test_an_ask_with_no_question_is_refused(client) -> None:
    sign_in(client)
    code, body = ask(client, docId="vision", scope="document", text="   ")
    assert code == 400
    assert "question" in body["error"]


def test_an_ask_about_a_document_that_is_not_there(client) -> None:
    sign_in(client)
    code, body = ask(client, docId="no-such-doc", scope="document", text="Anything.")
    assert code == 404
    assert "no-such-doc" in body["error"]


def test_an_ask_to_a_manager_that_is_not_there(client) -> None:
    sign_in(client)
    answer = client.post("/api/managers/nobody/ask", json={"scope": "document", "text": "Anything."})
    assert answer.status_code == 404
    assert "nobody" in answer.json()["error"]


# --------------------------------------------------------------------------
# the drafting session: used when asked for, survived when it fails
# --------------------------------------------------------------------------


class _Ran:
    def __init__(self, returncode: int = 0, stdout: str = "", stderr: str = "") -> None:
        self.returncode, self.stdout, self.stderr = returncode, stdout, stderr


#: What `amplifier run --output-format json` actually printed on 2026-09-04:
#: a line of the CLI's own before the object it was asked for.
def _session_output(response: str, status: str = "success") -> str:
    import json as _json

    return "Bundle 'anchors' prepared successfully\n" + _json.dumps(
        {"status": status, "response": response, "session_id": "c40ac936", "model": "a-model"}
    )


def test_a_drafting_session_is_asked_for_the_wording(client, monkeypatch) -> None:
    seen: dict = {}

    def fake_run(argv, **kwargs):
        seen["argv"] = argv
        seen["cwd"] = kwargs.get("cwd")
        return _Ran(0, _session_output("Evidence beats claims, in every document and every screen."))

    monkeypatch.setattr(writes.subprocess, "run", fake_run)
    monkeypatch.setattr(serve, "ASK_DRAFTER", "agent")
    sign_in(client)
    code, body = ask(client, docId="vision", scope="paragraph", section="Principles", text="Say it once.")

    assert code == 200, body
    assert seen["argv"][:2] == ["amplifier", "run"]
    assert "Say it once." in seen["argv"][-1], "the question is not in the prompt"
    assert "The app has two places." in seen["argv"][-1], "the paragraph is not in the prompt"
    assert body["drafted"] is True
    assert "Evidence beats claims, in every document and every screen." in Path(body["path"]).read_text(encoding="utf-8")


def test_the_proposal_carries_the_answer_and_not_the_clis_furniture(client, monkeypatch) -> None:
    """Caught live: the session's banner and token table were quoted as wording.

    Reading the whole of stdout put "Bundle 'anchors' prepared successfully",
    a token-usage table and colour codes into a steward's proposal as if the
    session had proposed them. The answer is the JSON object's `response`.
    """
    noisy = (
        "Bundle 'anchors' prepared successfully\n"
        "\x1b[2m│  Token Usage (anthropic/claude-opus-5) [2.2s]\x1b[0m\n"
        "\x1b[2m└─ Input: 121,713 | Output: 80 | Cost: $0.28\x1b[0m\n"
        '{"status": "success", "response": "\\u001b[2mCore 2.\\u001b[0m A check that cannot run says so."}'
    )
    monkeypatch.setattr(writes.subprocess, "run", lambda argv, **kw: _Ran(0, noisy))
    monkeypatch.setattr(serve, "ASK_DRAFTER", "agent")
    sign_in(client)
    code, body = ask(client, docId="demo", scope="document", text="Say what an unrunnable check reports.")

    assert code == 200, body
    assert body["drafted"] is True
    text = Path(body["path"]).read_text(encoding="utf-8")
    assert "Core 2. A check that cannot run says so." in text
    assert "Token Usage" not in text
    assert "prepared successfully" not in text
    assert "\x1b" not in text, "colour codes reached the proposal"


def test_a_session_that_reports_a_failure_is_not_read_as_wording(client, monkeypatch) -> None:
    monkeypatch.setattr(
        writes.subprocess, "run", lambda argv, **kw: _Ran(0, _session_output("half an answer", status="error"))
    )
    monkeypatch.setattr(serve, "ASK_DRAFTER", "agent")
    sign_in(client)
    code, body = ask(client, docId="demo", scope="document", text="Anything.")
    assert code == 200, body
    assert body["drafted"] is False
    assert "reported error" in body["draftedBy"]
    assert "half an answer" not in Path(body["path"]).read_text(encoding="utf-8")


def test_an_ask_about_a_paragraph_that_is_not_there_says_so(client) -> None:
    sign_in(client)
    code, body = ask(client, docId="demo", scope="paragraph", section="Where this is going", text="Add a sentence.")
    assert code == 200, body
    text = Path(body["path"]).read_text(encoding="utf-8")
    assert "no section by that name is in the document" in text
    assert "**Core 1.** The app shows only what it can read." in text


@pytest.mark.parametrize(
    "outcome",
    [
        _Ran(1, "", "the session fell over"),
        _Ran(0, "   \n"),
        _Ran(0, _session_output("   ")),
        OSError("amplifier is not installed"),
        subprocess.TimeoutExpired(cmd="amplifier", timeout=1.0),
    ],
)
def test_a_drafting_session_that_fails_still_leaves_a_proposal(client, monkeypatch, outcome) -> None:
    """The failure clause 9 forbids is silence, not an undrafted proposal."""

    def fake_run(argv, **kwargs):
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome

    monkeypatch.setattr(writes.subprocess, "run", fake_run)
    monkeypatch.setattr(serve, "ASK_DRAFTER", "agent")
    sign_in(client)
    code, body = ask(client, docId="vision", scope="document", text="Make the second place plainer.")

    assert code == 200, body
    assert body["drafted"] is False
    assert body["draftedBy"].startswith("no wording was drafted")
    text = Path(body["path"]).read_text(encoding="utf-8")
    assert "Make the second place plainer." in text, "the steward's ask was lost"
    assert "No wording was drafted" in text, "the proposal does not say the wording is missing"


def test_no_session_is_run_unless_one_is_asked_for(client, monkeypatch) -> None:
    def refuse(*args, **kwargs):
        raise AssertionError("the default ask must not shell out to a drafting session")

    monkeypatch.setattr(writes.subprocess, "run", refuse)
    sign_in(client)
    assert serve.ASK_DRAFTER != "agent"
    code, body = ask(client, docId="vision", scope="document", text="No session, please.")
    assert code == 200, body
    assert body["drafted"] is False
