"""The app against a project built for the occasion.

Every test here runs on a real git repository and a real batch directory made
in a temp folder — not on fixtures of the API's own answers. That is
deliberate: the thing worth proving is that the readers read, and a test that
feeds them a canned payload proves nothing about that.

PAM is the one thing mocked, and it is mocked at `pam.pam` rather than at the
app's own `authenticate`, so the code path under test is the real one: the app
really calls `pam.pam().authenticate(...)` and really believes the answer.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app import auth, serve  # noqa: E402

GOOD_USER = "tester"
GOOD_PASSWORD = "correct horse"


# --------------------------------------------------------------------------
# a project to read
# --------------------------------------------------------------------------


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "user.name=Test", "-c", "user.email=test@example.invalid", *args],
        cwd=repo,
        check=True,
        capture_output=True,
    )


VISION_FIRST = """# Demo Vision (DRAFT)

## Where this is going

One place for direction and one place for operation.

## Principles

The app has two places.
Evidence beats claims.
"""

VISION_SECOND = """# Demo Vision (DRAFT)

## Where this is going

One place for direction, one place for operation, and one console.

## Principles

The app has two places, one console, and one anchor.
Evidence beats claims.
"""

CONTRACT = """# Demo Contract — v1 (DRAFT)

## Core

**Core 1.** The app shows only what it can read.
"""

CANDIDATE = """# Widen Core 1

## The exact change

Core 1 gains a sentence about silence.

## The evidence

- A steward read a placeholder as real data once.
- The cost was one wrong decision.

## What does not change

The two places, and the write paths, do not change.
"""

ROWS = """- id: DEMO-001
  disposition: CONFORMS
  contract:
    file: contracts/demo.v1.md
    clause: "Core 1"
- id: DEMO-002
  disposition: GAP
  contract:
    file: contracts/demo.v1.md
    clause: "Core 1"
"""

OWNER_LOG = """# Owner return log

Plain-sentence briefs for the intent steward.

## 2026-09-01 — the run began

Four lanes started against the objective. Nothing needed you.

## 2026-09-02 — the run closed

Every item landed or was honestly disposed. One call is yours to make. Nothing else needs you.
"""

HIGHWAY = """# HIGHWAY — Demo batch

## Outcome
Have a convincing demo ready. Two waves, then polish.

Deadline: Today, 12:00 PM

## Priority rationale
First make the path work. Then make it dependable.

## Weave-in log
- 2026-09-01T10:00:00Z REOPENED on owner word.
"""

MANIFEST_HEAD = "lane\tworktree\tbranch\tbase_sha\ttmux\tgoal\tlog\tlaunched_at\n"


@pytest.fixture
def project(tmp_path: Path) -> dict:
    """A repository with history, a ledger, a proposal — and a batch running it."""
    repo = tmp_path / "demo-repo"
    (repo / "docs" / "workflow").mkdir(parents=True)
    (repo / "contracts").mkdir()
    (repo / "ledger").mkdir()

    (repo / "docs" / "VISION.md").write_text(VISION_FIRST, encoding="utf-8")
    (repo / "contracts" / "demo.v1.md").write_text(CONTRACT, encoding="utf-8")
    (repo / "ledger" / "rows.yaml").write_text(ROWS, encoding="utf-8")
    (repo / "docs" / "workflow" / "OWNER-RETURN-LOG.md").write_text(OWNER_LOG, encoding="utf-8")

    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "seed: the vision and one contract")

    # A second commit so there is a real sentence-level change to find.
    (repo / "docs" / "VISION.md").write_text(VISION_SECOND, encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "vision: the console becomes a place")

    # A proposal sitting beside the contract, unratified.
    (repo / "contracts" / "demo.v1-candidate.md").write_text(CANDIDATE, encoding="utf-8")

    batch = tmp_path / "hw-demo"
    (batch / "lanes" / "w1-alpha").mkdir(parents=True)
    (batch / "lanes" / "w2-beta").mkdir(parents=True)
    (batch / "lanes" / "w1-gamma").mkdir(parents=True)
    (batch / "goals").mkdir()
    (batch / ".width").write_text("4\n", encoding="utf-8")
    (batch / "HIGHWAY.md").write_text(HIGHWAY, encoding="utf-8")
    (batch / "goals" / "w1-alpha.md").write_text("# Lane alpha — make the path work\n", encoding="utf-8")
    (batch / "manifest.tsv").write_text(
        MANIFEST_HEAD
        + f"w1-alpha\t{batch}/lanes/w1-alpha/demo-repo\tlane/w1-alpha\tdeadbee\thw__hw-demo__w1-alpha\t{batch}/goals/w1-alpha.md\t{batch}/lanes/w1-alpha/lane.log\t2026-09-01T10:00:00Z\n"
        + f"w2-beta\t{batch}/lanes/w2-beta/demo-repo\tlane/w2-beta\tdeadbee\thw__hw-demo__w2-beta\t{batch}/goals/w2-beta.md\t{batch}/lanes/w2-beta/lane.log\t2026-09-01T11:00:00Z\n"
        + f"w1-gamma\t{batch}/lanes/w1-gamma/demo-repo\tlane/w1-gamma\tdeadbee\thw__hw-demo__w1-gamma\t{batch}/goals/w1-gamma.md\t{batch}/lanes/w1-gamma/lane.log\t2026-09-01T12:00:00Z\n",
        encoding="utf-8",
    )
    (batch / "lanes" / "w1-alpha" / "lane.log").write_text("working\n", encoding="utf-8")
    (batch / "lanes" / "w2-beta" / "lane.log").write_text("working\n", encoding="utf-8")
    (batch / "lanes" / "w1-gamma" / "lane.log").write_text("stopped\n", encoding="utf-8")
    (batch / "lanes" / "w1-gamma" / "BLOCKED.md").write_text(
        "# Lane w1-gamma — BLOCKED\n\n"
        "**Date:** 2026-09-01\n"
        "**Branch:** `lane/w1-gamma` (2 commits, nothing merged)\n"
        "**Outcome:** B) BLOCKED. Not A. The device cannot be reached from this host, so the\n"
        "one acceptance item that needs it cannot be proved.\n",
        encoding="utf-8",
    )
    (batch / "lanes" / "w2-beta" / "DONE.json").write_text(
        json.dumps({"status": "success", "summary": "Beta landed. Nothing residual."}), encoding="utf-8"
    )

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
        # Never the real ~/.amplifier: a test must not move a steward's own
        # read point or drop their kept marks.
        "state": tmp_path / "state.json",
    }


class _FakePam:
    """Stands in for `pam.pam()`. Answers only for the one right password."""

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
    assert auth.COOKIE in answer.cookies


# --------------------------------------------------------------------------
# the gate
# --------------------------------------------------------------------------


def test_api_refuses_anyone_without_a_cookie(client: TestClient) -> None:
    # The test client connects over loopback. If a loopback exemption existed
    # anywhere, this would be a 200 — which is exactly the bug it guards.
    assert client.get("/api/boot").status_code == 401
    assert client.get("/api/managers/demo").status_code == 401
    assert client.get("/api/managers/demo/operation").status_code == 401
    assert client.post("/api/managers/demo/steer", json={"lanes": 9}).status_code == 401


def test_html_sends_a_stranger_to_sign_in(client: TestClient) -> None:
    answer = client.get("/")
    assert answer.status_code == 302
    assert answer.headers["location"].startswith("/login")


def test_a_wrong_password_sets_no_cookie(client: TestClient) -> None:
    answer = client.post("/login", data={"username": GOOD_USER, "password": "wrong", "next": "/"})
    assert answer.status_code == 302
    assert auth.COOKIE not in answer.cookies
    assert "/login" in answer.headers["location"]
    assert client.get("/api/boot").status_code == 401


def test_the_right_password_opens_the_api(client: TestClient) -> None:
    sign_in(client)
    assert client.get("/api/boot").status_code == 200


def test_a_tampered_cookie_proves_nothing(client: TestClient) -> None:
    client.cookies.set(auth.COOKIE, "not-a-real-token")
    assert client.get("/api/boot").status_code == 401


def test_an_empty_password_never_passes(monkeypatch) -> None:
    monkeypatch.setattr(auth.pam_module, "pam", _FakePam)
    assert auth.authenticate(GOOD_USER, "") is False
    assert auth.authenticate("", GOOD_PASSWORD) is False
    assert auth.authenticate(GOOD_USER, GOOD_PASSWORD) is True


# --------------------------------------------------------------------------
# what the screens are fed
# --------------------------------------------------------------------------


def test_boot_lists_the_configured_manager(client: TestClient) -> None:
    sign_in(client)
    payload = client.get("/api/boot").json()
    assert payload["user"] == GOOD_USER
    assert [m["id"] for m in payload["managers"]] == ["demo"]
    manager = payload["managers"][0]
    assert manager["lanesMax"] == 4  # .width
    assert manager["lanesActive"] == 0  # no session on that socket
    assert manager["objective"].startswith("Have a convincing demo ready")
    assert manager["deadline"] == "Today, 12:00 PM"
    assert manager["summary"] == "Nothing else needs you."  # last sentence of the newest brief
    assert manager["needs"] == 1  # the candidate beside the contract
    assert manager["status"] == "waiting"


def test_manager_lists_the_docs_with_a_state_from_the_ledger(client: TestClient) -> None:
    sign_in(client)
    payload = client.get("/api/managers/demo").json()
    docs = {d["id"]: d for d in payload["repositories"][0]["docs"]}
    assert set(docs) == {"vision", "demo"}
    # One CONFORMS row and one GAP row: the worst honest word wins, so not kept.
    assert docs["demo"]["state"] == "gap"
    assert docs["demo"]["clauses"] == 2
    # Nothing in the ledger watches the vision, which is a different silence.
    assert docs["vision"]["state"] == "draft"
    assert docs["vision"]["clauses"] == 0


def test_a_document_carries_its_real_sections_changes_and_history(client: TestClient) -> None:
    sign_in(client)
    payload = client.get("/api/managers/demo/docs/demo-repo/vision").json()
    titles = [title for title, _html in payload["sections"]]
    assert "Where this is going" in titles and "Principles" in titles
    assert any("<p>" in html for _title, html in payload["sections"])
    assert payload["changes"], "two commits touch the vision; a change must be found"
    change = payload["changes"][0]
    # Where it lives and which commit changed it are two different labels, and
    # the card carries both: the heading path, and subject + sha + date.
    assert change["section"] in {"Where this is going", "Principles"}
    assert change["source"].startswith("vision: the console becomes a place \u00b7 ")
    assert change["sourceSubject"] == "vision: the console becomes a place"
    assert change["kind"] in {"new", "changed", "removed"}
    assert change["before"] != change["now"]
    assert payload["reading"]["headSha"]
    assert payload["history"][0]["id"] == "now"
    assert len(payload["history"]) == 2
    assert payload["proposals"] == []


def test_a_contract_carries_its_proposal(client: TestClient) -> None:
    sign_in(client)
    payload = client.get("/api/managers/demo/docs/demo-repo/demo").json()
    assert len(payload["proposals"]) == 1
    one = payload["proposals"][0]
    assert one["title"] == "Widen Core 1"
    assert len(one["evidence"]) == 2
    assert "two places" in one["unchanged"]


def test_a_missing_document_says_so(client: TestClient) -> None:
    sign_in(client)
    assert client.get("/api/managers/demo/docs/demo-repo/nope").status_code == 404
    assert client.get("/api/managers/nope/operation").status_code == 404


def test_operation_reads_waves_lanes_and_the_return_brief(client: TestClient) -> None:
    sign_in(client)
    payload = client.get("/api/managers/demo/operation").json()
    waves = {w["id"]: w for w in payload["waves"]}
    assert set(waves) == {"w1", "w2"}
    assert waves["w1"]["label"] == "Wave 1"
    assert waves["w1"]["progress"] == 0
    assert waves["w2"]["progress"] == 100  # beta wrote DONE.json

    # Lanes at work and lanes that have reported back are two lists, because
    # they are read in two vocabularies — see test_operation_words.py.
    lanes = {lane["id"]: lane for lane in payload["lanes"]}
    reported = {lane["id"]: lane for lane in payload["reported"]}
    # No tmux session exists on that socket, so nothing may claim to be working.
    assert lanes["w1-alpha"]["status"] == "silent"
    assert lanes["w1-alpha"]["statusLabel"] == "Silent — may have died"
    assert lanes["w1-alpha"]["title"] == "make the path work"
    assert lanes["w1-alpha"]["tmux"] == {"socket": "test-socket-that-does-not-exist", "session": "hw__hw-demo__w1-alpha"}
    assert lanes["w1-alpha"]["live"] is False
    assert "w2-beta" not in lanes and "w1-gamma" not in lanes
    assert reported["w2-beta"]["outcome"] == "done"
    assert reported["w2-beta"]["outcomeLabel"] == "Done"
    assert reported["w2-beta"]["evidence"] == "Beta landed."
    # A stopped lane says why, from its own marker — never from the date or
    # the branch line above the reason.
    assert reported["w1-gamma"]["outcome"] == "stuck"
    assert reported["w1-gamma"]["outcomeLabel"] == "Stuck"
    assert reported["w1-gamma"]["evidence"].startswith("The device cannot be reached from this host")

    assert payload["timeline"][0][0] == "2026-09-02"  # newest first
    assert payload["returnBrief"][0].startswith("Every item landed")
    assert payload["confidence"] == {
        "pct": 50,
        "kept": 1,
        "notyet": 1,
        "broken": 0,
        "pinnedOpen": 0,
        "cantCheck": 0,
        "available": True,
    }
    assert payload["throughput"]["reopened"] == 1


def test_needs_names_the_open_proposal(client: TestClient) -> None:
    sign_in(client)
    payload = client.get("/api/needs/demo").json()
    assert len(payload) == 1
    assert payload[0]["kind"] == "proposal"
    assert payload[0]["where"] == {"repoId": "demo-repo", "docId": "demo"}


# --------------------------------------------------------------------------
# the writes — each one lands on disk
# --------------------------------------------------------------------------


def test_a_decision_is_appended_to_todays_record(client: TestClient, project) -> None:
    sign_in(client)
    answer = client.post(
        "/api/managers/demo/decision",
        json={
            "repoId": "demo-repo",
            "docId": "demo",
            "proposalId": "demo.v1-candidate",
            "decision": "ratified-with-edits",
            "note": "Yes, with the silence sentence tightened.",
        },
    )
    assert answer.status_code == 200 and answer.json()["ok"] is True
    written = Path(answer.json()["path"])
    assert written.parent == project["repo"] / "docs" / "workflow"
    text = written.read_text(encoding="utf-8")
    assert "Ratified with edits" in text
    assert "demo.v1-candidate" in text
    assert "Yes, with the silence sentence tightened." in text
    assert GOOD_USER in text

    # A second decision appends rather than replacing the first.
    client.post(
        "/api/managers/demo/decision",
        json={"repoId": "demo-repo", "docId": "demo", "proposalId": "p2", "decision": "declined"},
    )
    text = written.read_text(encoding="utf-8")
    assert text.count("## ") == 2
    assert "Declined" in text


def test_feedback_becomes_its_own_dated_file(client: TestClient, project) -> None:
    sign_in(client)
    answer = client.post(
        "/api/managers/demo/feedback",
        json={"text": "The lane ages read wrong on mobile.", "context": "operation"},
    )
    assert answer.status_code == 200 and answer.json()["ok"] is True
    written = Path(answer.json()["path"])
    assert written.parent == project["repo"] / ".converge" / "feedback"
    text = written.read_text(encoding="utf-8")
    assert "context: operation" in text
    assert f"user: {GOOD_USER}" in text
    assert "The lane ages read wrong on mobile." in text


def test_a_steer_rewrites_the_width_and_says_so_in_the_log(client: TestClient, project) -> None:
    sign_in(client)
    answer = client.post("/api/managers/demo/steer", json={"lanes": 6, "note": "more lanes for the demo"})
    assert answer.status_code == 200 and answer.json()["ok"] is True

    assert (project["batch"] / ".width").read_text(encoding="utf-8").strip() == "6"
    highway = (project["batch"] / "HIGHWAY.md").read_text(encoding="utf-8")
    assert "lanes 6" in highway
    assert "more lanes for the demo" in highway
    assert f"steer ({GOOD_USER})" in highway
    # The rest of the file is untouched.
    assert "## Outcome" in highway and "Deadline: Today, 12:00 PM" in highway

    # And the new width is what boot reports.
    assert client.get("/api/boot").json()["managers"][0]["lanesMax"] == 6


def test_a_steer_with_no_number_still_records_the_ask(client: TestClient, project) -> None:
    sign_in(client)
    before = (project["batch"] / ".width").read_text(encoding="utf-8")
    answer = client.post("/api/managers/demo/steer", json={"note": "hold the width, change the aim", "fill": True})
    assert answer.json()["ok"] is True
    assert (project["batch"] / ".width").read_text(encoding="utf-8") == before
    assert "fill now" in (project["batch"] / "HIGHWAY.md").read_text(encoding="utf-8")


def test_writes_refuse_an_unknown_manager(client: TestClient) -> None:
    sign_in(client)
    assert client.post("/api/managers/nope/decision", json={}).status_code == 404
    assert client.post("/api/managers/nope/feedback", json={"text": "x"}).status_code == 404
    assert client.post("/api/managers/nope/steer", json={"lanes": 2}).status_code == 404
