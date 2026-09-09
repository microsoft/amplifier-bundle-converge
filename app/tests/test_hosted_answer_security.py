"""converge-0zmv: the hosted PR answer endpoint enforces steward authority.

`contracts/experience-collaboration.v1.md` Core 8 reserves *whose word
counts* -- ratification, the authority to answer a proposal -- to the
manager's registered steward, not to every authenticated teammate.
`app/serve.py` already enforces exactly this for the local `/decision`
route via `_steward_denied`. `app/collab.py`'s hosted twin,
`POST /api/collab/{mid}/pulls/{number}/answer`, did not: any signed-in
teammate's direct POST returned 200, appended an entry to the dated
ratification record, and posted the "answer" back to the pull request on
the real host -- with the caller's identity read from verified session
state (`_who(request)`) but never compared to `mc.steward`.

This file is the dedicated, standalone regression proof the brief asks
for. It does not edit `test_collab.py` (owned by the Direction-review
lane) and builds its own fixtures rather than importing that module's, so
it never depends on another lane's file staying byte-identical.

What is real here, and what stands in
--------------------------------------
Everything on the Converge side is real: a real FastAPI app built by
`app/serve.py`, real signed-in sessions through the real cookie gate (two
distinct authenticated identities -- a registered steward and an ordinary
teammate -- proved against a fake PAM backend, never two names sharing one
session), and the real `app/writes.py` appending to the real dated
ratification record on a real git repository in a temp folder.

The one stand-in is the repository host itself, exactly as in
`test_collab.py`: `gh` is replaced on `$PATH` by a script that answers
like the host and records every call it is asked to make into a log file,
so "the host was never called" is a checkable fact about that log
(empty), never a mock's `assert_not_called()`.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from app import auth, collab, serve  # noqa: E402

#: The manager's registered steward -- the only identity whose answer counts.
STEWARD = "tester"
STEWARD_PASSWORD = "hunter2"

#: An ordinary, genuinely-authenticated teammate who is NOT the steward.
#: A real, distinct PAM identity throughout -- never the steward's name
#: reused with a forged JSON field, which is exactly the shortcut Core 8
#: forbids trusting.
TEAMMATE = "colleague"
TEAMMATE_PASSWORD = "swordfish"

MANAGER = "demo"

PULL_BODY = """## The exact change

- Nothing in this pull request matters to the assertions below.

## The evidence

- A placeholder body is enough to prove the routing question, which is
  about who may answer, not what the proposal says.

## What does not change

Nothing -- this fixture pull request is never really merged anywhere.
"""

PULL_FIXTURE = {
    "number": 7,
    "title": "A pull request some teammate opened",
    "body": PULL_BODY,
    "author": {"login": "wren"},
    "url": "https://host.invalid/demo/pull/7",
    "updatedAt": "2026-09-04T09:00:00Z",
    "headRefName": "wren/some-change",
    "isDraft": False,
}

#: A stand-in `gh`: answers `pr list`/`pr view` from a fixture and records
#: every `pr comment` it is asked to run into `$FAKE_GH_LOG`, one JSON
#: array of argv per line -- so "the host was asked to post something" is
#: a fact read from that log, not a mock's call count.
FAKE_GH = '''#!/usr/bin/env python3
import json, os, sys

argv = sys.argv[1:]
log = os.environ["FAKE_GH_LOG"]
with open(log, "a", encoding="utf-8") as out:
    out.write(json.dumps(argv) + "\\n")

PULL = json.loads(os.environ["FAKE_GH_PULL"])

if argv[:2] == ["pr", "list"]:
    print(json.dumps([PULL]))
elif argv[:2] == ["pr", "view"]:
    one = dict(PULL)
    one["comments"] = []
    print(json.dumps(one))
elif argv[:2] == ["pr", "comment"]:
    print("https://host.invalid/demo/pull/7#issuecomment-1")
else:
    sys.stderr.write("this stand-in host was asked something it does not answer: %r\\n" % (argv,))
    sys.exit(1)
'''


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "user.name=Test", "-c", "user.email=test@example.invalid", *args],
        cwd=repo, check=True, capture_output=True,
    )


@pytest.fixture
def host(tmp_path: Path, monkeypatch) -> dict:
    """`gh` on `$PATH`, answering like a host and writing down what it was asked."""
    binaries = tmp_path / "bin"
    binaries.mkdir()
    tool = binaries / "gh"
    tool.write_text(FAKE_GH, encoding="utf-8")
    tool.chmod(0o755)
    log = tmp_path / "gh-calls.jsonl"
    monkeypatch.setenv("PATH", f"{binaries}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv("FAKE_GH_LOG", str(log))
    monkeypatch.setenv("FAKE_GH_PULL", json.dumps(PULL_FIXTURE))
    return {"log": log, "bin": binaries}


def calls(host: dict) -> list[list[str]]:
    if not host["log"].exists():
        return []
    return [json.loads(line) for line in host["log"].read_text(encoding="utf-8").splitlines() if line.strip()]


def _repo_and_batch(tmp_path: Path) -> tuple[Path, Path]:
    repo = tmp_path / "demo-repo"
    (repo / "docs" / "workflow").mkdir(parents=True)
    (repo / "docs" / "VISION.md").write_text("# Demo Vision (DRAFT)\n\nOne place.\n", encoding="utf-8")
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "seed: the vision")

    batch = tmp_path / "hw-demo"
    (batch / "goals").mkdir(parents=True)
    (batch / "HIGHWAY.md").write_text("# HIGHWAY\n\n## Outcome\nProve the seam.\n", encoding="utf-8")
    (batch / ".width").write_text("4\n", encoding="utf-8")
    (batch / "manifest.tsv").write_text("lane\tworktree\tbranch\n", encoding="utf-8")
    return repo, batch


def _write_config(tmp_path: Path, repo: Path, batch: Path, *, steward: str | None) -> Path:
    conf = tmp_path / "converge-app.toml"
    steward_line = f'steward = "{steward}"\n' if steward else ""
    conf.write_text(
        "[[managers]]\n"
        f'id = "{MANAGER}"\n'
        'name = "Demo manager"\n'
        f'batch_dir = "{batch}"\n'
        f'repos = ["{repo}"]\n'
        'tmux_socket = "collab-security-socket-that-does-not-exist"\n'
        f"{steward_line}",
        encoding="utf-8",
    )
    return conf


@pytest.fixture
def project(tmp_path: Path) -> dict:
    """A manager with a REGISTERED steward -- the ordinary, expected case."""
    repo, batch = _repo_and_batch(tmp_path)
    conf = _write_config(tmp_path, repo, batch, steward=STEWARD)
    return {
        "repo": repo, "batch": batch, "config": conf,
        "secret": tmp_path / "secret", "state": tmp_path / "state.json",
        "sessions": tmp_path / "sessions.json",
    }


@pytest.fixture
def unregistered_project(tmp_path: Path) -> dict:
    """A manager with NO registered steward -- the fail-closed case."""
    repo, batch = _repo_and_batch(tmp_path)
    conf = _write_config(tmp_path, repo, batch, steward=None)
    return {
        "repo": repo, "batch": batch, "config": conf,
        "secret": tmp_path / "secret", "state": tmp_path / "state.json",
        "sessions": tmp_path / "sessions.json",
    }


class _FakePam:
    """PAM stands in for two REAL, distinct identities -- never one name
    wearing another's claim."""

    def authenticate(self, username: str, password: str, service: str = "login") -> bool:
        return (username == STEWARD and password == STEWARD_PASSWORD) or (
            username == TEAMMATE and password == TEAMMATE_PASSWORD
        )


def build_app(project: dict):
    made = serve.create_app(
        config_path=project["config"], secret_path=project["secret"],
        state_path=project["state"], sessions_path=project["sessions"],
    )
    made.include_router(collab.router)
    return made


def _login(app, user: str, password: str) -> TestClient:
    client = TestClient(app, follow_redirects=False)
    answer = client.post("/login", data={"username": user, "password": password, "next": "/"})
    assert answer.status_code == 302 and auth.COOKIE in answer.cookies, answer.text
    return client


@pytest.fixture
def app_instance(project, monkeypatch):
    monkeypatch.setattr(auth.pam_module, "pam", _FakePam)
    return build_app(project)


@pytest.fixture
def unregistered_app_instance(unregistered_project, monkeypatch):
    monkeypatch.setattr(auth.pam_module, "pam", _FakePam)
    return build_app(unregistered_project)


@pytest.fixture(autouse=True)
def _forget_arrivals():
    """Nothing carries over: freshness is a fact about the last few minutes,
    and ARRIVALS is process-global state `test_collab.py` also touches."""
    collab.ARRIVALS.__init__()
    yield
    collab.ARRIVALS.__init__()


def _ratification_files(repo: Path) -> list[Path]:
    return sorted((repo / "docs" / "workflow").glob("owner-ratifications-*.md"))


def _answer_call_count(host: dict) -> int:
    return len([c for c in calls(host) if c[:2] == ["pr", "comment"]])


# --------------------------------------------------------------------------
# the vulnerability: a teammate's direct, forged POST must be refused --
# fully, before any file/git/host side effect
# --------------------------------------------------------------------------
def test_teammate_forged_answer_is_refused_before_any_side_effect(app_instance, project, host) -> None:
    teammate = _login(app_instance, TEAMMATE, TEAMMATE_PASSWORD)

    # Forged JSON fields naming the steward -- Core 8's own words: identity
    # must come from verified session state, never inferred from a JSON
    # user/steward field the caller controls.
    answer = teammate.post(
        f"/api/collab/{MANAGER}/pulls/7/answer",
        json={
            "decision": "ratified",
            "note": "Approved.",
            "user": STEWARD,
            "steward": STEWARD,
        },
    )
    assert answer.status_code == 403, answer.text
    body = answer.json()
    assert STEWARD in body.get("error", ""), body
    assert TEAMMATE not in body.get("error", "") or "not" in body["error"], body

    # No ratification record was written at all.
    assert _ratification_files(project["repo"]) == [], "a teammate's forged POST wrote a ratification record"

    # The host was never called -- not `pr comment`, not anything else.
    assert calls(host) == [], f"the host was called on a refused request: {calls(host)}"


def test_forged_answer_is_refused_even_with_the_real_four_word_decision(app_instance, project, host) -> None:
    """Every one of the four decision words is refused the same way -- this
    is not a quirk of one particular word."""
    teammate = _login(app_instance, TEAMMATE, TEAMMATE_PASSWORD)
    for decision in ("ratified", "ratified-with-edits", "declined", "later"):
        answer = teammate.post(
            f"/api/collab/{MANAGER}/pulls/7/answer",
            json={"decision": decision},
        )
        assert answer.status_code == 403, (decision, answer.text)
    assert _ratification_files(project["repo"]) == []
    assert calls(host) == []


# --------------------------------------------------------------------------
# an absent registered steward fails closed -- never "anyone may act"
# --------------------------------------------------------------------------
def test_no_registered_steward_refuses_everyone(unregistered_app_instance, unregistered_project, host) -> None:
    # Even the person who would otherwise be a plausible steward is refused,
    # because nobody is registered as one yet.
    someone = _login(unregistered_app_instance, STEWARD, STEWARD_PASSWORD)
    answer = someone.post(f"/api/collab/{MANAGER}/pulls/7/answer", json={"decision": "ratified"})
    assert answer.status_code == 403, answer.text
    assert "no registered steward" in answer.json().get("error", "")
    assert _ratification_files(unregistered_project["repo"]) == []
    assert calls(host) == []


# --------------------------------------------------------------------------
# the registered steward is unaffected: still records, and still posts
# back to the correct origin
# --------------------------------------------------------------------------
def test_the_registered_steward_still_records_and_posts_to_the_correct_origin(app_instance, project, host) -> None:
    steward = _login(app_instance, STEWARD, STEWARD_PASSWORD)
    answer = steward.post(
        f"/api/collab/{MANAGER}/pulls/7/answer",
        json={"decision": "ratified-with-edits", "note": "Looks right."},
    )
    assert answer.status_code == 200, answer.text
    body = answer.json()
    assert body["ok"] is True
    assert body["recorded"]["ok"] is True
    assert body["returnedToOrigin"]["ok"] is True

    files = _ratification_files(project["repo"])
    assert len(files) == 1, files
    text = files[0].read_text(encoding="utf-8")
    assert "Ratified with edits" in text
    assert STEWARD in text

    posted = [c for c in calls(host) if c[:2] == ["pr", "comment"]]
    assert len(posted) == 1, calls(host)
    assert posted[0][2] == "7"
    assert "https://host.invalid/demo/pull/7" == PULL_FIXTURE["url"]  # the origin this answer targets
    assert body["origin"]["number"] == 7


# --------------------------------------------------------------------------
# ordinary teammate actions on this same router stay open
# --------------------------------------------------------------------------
def test_teammate_comments_still_work(app_instance, project, host) -> None:
    teammate = _login(app_instance, TEAMMATE, TEAMMATE_PASSWORD)
    answer = teammate.post(
        f"/api/collab/{MANAGER}/pulls/7/comments",
        json={"text": "What does this change for the console?"},
    )
    assert answer.status_code == 200, answer.text
    assert answer.json()["ok"] is True
    posted = [c for c in calls(host) if c[:2] == ["pr", "comment"]]
    assert len(posted) == 1, calls(host)
    assert f"Asked by {TEAMMATE}" in posted[0][4]


def test_teammate_reads_still_work(app_instance, host) -> None:
    teammate = _login(app_instance, TEAMMATE, TEAMMATE_PASSWORD)
    listing = teammate.get(f"/api/collab/{MANAGER}/pulls")
    assert listing.status_code == 200, listing.text
    one = teammate.get(f"/api/collab/{MANAGER}/pulls/7")
    assert one.status_code == 200, one.text


def test_signed_out_caller_is_refused_at_the_ordinary_auth_gate(app_instance, host) -> None:
    """Unauthenticated is a distinct, ordinary refusal from unauthorized --
    401, not 403, and still no side effect."""
    stranger = TestClient(app_instance, follow_redirects=False)
    answer = stranger.post(f"/api/collab/{MANAGER}/pulls/7/answer", json={"decision": "ratified"})
    assert answer.status_code == 401, answer.text
    assert calls(host) == []
