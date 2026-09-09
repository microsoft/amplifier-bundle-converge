"""converge-j6vi: the two host-writing routes no longer block the app.

`contracts/experience-collaboration.v1.md` Core 4 -- the bridge -- says a
question asked in Converge, and the steward's answer, reach the pull request
through the host's own command line (``gh``). Both routes that do that,
``POST /api/collab/{mid}/pulls/{number}/comments`` (``ask_on_the_host``) and
``POST /api/collab/{mid}/pulls/{number}/answer`` (``answer_a_pull``), are
``async def`` but used to call ``_run``'s blocking ``subprocess.run`` directly
on Uvicorn's single asyncio event loop, with no thread offload. A slow ``gh``
call -- real GitHub latency, or the test-only hold this file uses to
reproduce it deterministically -- froze that one event loop for its whole
duration, which stalled every other request the server was handling, for
every manager and repository, not only the one that was actually slow.

The fix, in ``app/collab.py``, wraps each of the two blocking calls in
``await asyncio.to_thread(...)`` -- the same effect ``one_pull`` already gets
for free by being a plain ``def`` route Starlette itself dispatches to a
threadpool. Nothing about authentication, authority checks, parsing, response
shapes or status codes, timeout/error normalization, or the
record-then-post-to-host ordering in ``answer_a_pull`` changes.

What is real here, and what stands in
-------------------------------------
Everything on the Converge side is real: a real FastAPI app served by a real
Uvicorn server in a background thread (never ``TestClient``'s in-process
ASGI transport, which would not prove the fix helps a SECOND, CONCURRENT
network request), a real signed-in session cookie issued the same way
``app/auth.py`` issues one, and the real ``app/writes.py`` appending to the
real dated ratification record on a real git repository in a temp folder.

The one stand-in is the repository host itself. ``gh`` is replaced on
``$PATH`` by a script that answers per-repository fixtures and, for exactly
one repository at a time, HOLDS its ``pr comment`` call open: it writes an
"entered" marker file the instant it starts holding (so a test can prove the
host call genuinely began, rather than guess a sleep duration is "long
enough"), then waits for a "release" marker file the test writes when it is
done observing. This never contacts real GitHub.

The independent failsafe
-------------------------
Two SEPARATE timeouts protect this file from ever hanging on a regression,
and they are not the same guard:

1. The stand-in host's own wait loop gives up after
   ``FAKE_GH_HOLD_FAILSAFE_SECONDS`` (8s here) and finishes the call anyway,
   recording that it timed out -- a backstop against a test that forgot to
   release, not the thing that actually catches a regression.
2. The concurrent "other repository" request in each test below uses a
   SHORT client-side timeout (2s) -- far shorter than the hold's failsafe.
   Against the prior, event-loop-blocking code, that other request queues
   behind the held one on the same event loop and this short timeout fires,
   failing the test with a clear ``httpx`` timeout exception. Against the
   fix, the other request is served promptly because the held call is off
   the loop entirely.

This was run against the prior code (the two lines this fix changes reverted
to their inline blocking form) to confirm it actually fails this way, not by
hanging -- see the terminal transcript in ``.afk-evidence/terminal.json``.
"""

from __future__ import annotations

import json
import os
import socket as socketlib
import subprocess
import sys
import threading
import time
from pathlib import Path

import httpx
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from app import auth, collab, serve  # noqa: E402

MANAGER = "demo"

#: The manager's registered steward -- the only identity `answer_a_pull`
#: accepts (`app/serve.py`'s `_steward_denied`, exactly as `/decision` uses).
STEWARD = "tester"


# --------------------------------------------------------------------------
# a stand-in host that can HOLD one repository's `pr comment` call open
# --------------------------------------------------------------------------
FAKE_GH = '''#!/usr/bin/env python3
"""Stand-in host: answers per-repository fixtures from $FAKE_GH_BY_CWD, and
can hold ONE repository's `pr comment` call open until released -- turning
"the host is slow" into something a test synchronizes on exactly, never a
guessed sleep duration.
"""
import json, os, sys, time

argv = sys.argv[1:]
cwd = os.path.realpath(os.getcwd())
log = os.environ.get("FAKE_GH_LOG")
if log:
    with open(log, "a", encoding="utf-8") as out:
        out.write(json.dumps({"argv": argv, "cwd": cwd}) + "\\n")

by_cwd = json.loads(os.environ.get("FAKE_GH_BY_CWD", "{}"))
here = by_cwd.get(cwd, {"pulls": [], "comments": []})

hold_cwd = os.environ.get("FAKE_GH_HOLD_CWD", "")
entered_file = os.environ.get("FAKE_GH_ENTERED_FILE", "")
release_file = os.environ.get("FAKE_GH_RELEASE_FILE", "")
failsafe = float(os.environ.get("FAKE_GH_HOLD_FAILSAFE_SECONDS", "8") or 8)


def hold_if_asked() -> None:
    if not (hold_cwd and entered_file and cwd == os.path.realpath(hold_cwd)):
        return
    # exists() is the reader's readiness signal. Publish complete JSON, never
    # an empty file visible between creation and the first write.
    pending = entered_file + ".tmp"
    with open(pending, "w", encoding="utf-8") as fh:
        fh.write(json.dumps({"cwd": cwd, "pid": os.getpid(), "at": time.time()}))
    os.replace(pending, entered_file)
    deadline = time.time() + failsafe
    while not os.path.exists(release_file):
        if time.time() > deadline:
            with open(entered_file + ".timedout", "w", encoding="utf-8") as fh:
                fh.write("failsafe elapsed without a release file")
            break
        time.sleep(0.02)


if argv[:2] == ["pr", "list"]:
    print(json.dumps(here.get("pulls", [])))
elif argv[:2] == ["pr", "view"]:
    number = argv[2]
    pulls = here.get("pulls", [])
    match = next((p for p in pulls if str(p["number"]) == str(number)), None)
    if match is None:
        sys.stderr.write("no such pull request: %s in %s\\n" % (number, cwd))
        sys.exit(1)
    one = dict(match)
    one["comments"] = here.get("comments", [])
    print(json.dumps(one))
elif argv[:2] == ["pr", "comment"]:
    hold_if_asked()
    if os.environ.get("FAKE_GH_FAIL_COMMENT") == "1":
        sys.stderr.write("the stand-in host refuses this comment on purpose\\n")
        sys.exit(1)
    print("https://host.invalid/%s/pull/%s#issuecomment-1" % (os.path.basename(cwd), argv[2]))
else:
    sys.stderr.write("stand-in host asked something it does not answer: %r\\n" % (argv,))
    sys.exit(1)
'''


def _pull(number: int, title: str) -> dict:
    return {
        "number": number,
        "title": title,
        "body": (
            "## The exact change\n\n- n/a\n\n## The evidence\n\n- n/a\n\n"
            "## What does not change\n\nn/a\n"
        ),
        "author": {"login": "wren"},
        "url": f"https://host.invalid/demo/pull/{number}",
        "updatedAt": "2026-09-04T09:00:00Z",
        "headRefName": f"wren/lane-{number}",
        "isDraft": False,
    }


@pytest.fixture
def host(tmp_path: Path, monkeypatch):
    """`gh` on `$PATH`, answering from `$FAKE_GH_BY_CWD` and able to hold one
    repository's `pr comment` call open, or make it fail, on request."""
    binaries = tmp_path / "bin"
    binaries.mkdir()
    tool = binaries / "gh"
    tool.write_text(FAKE_GH, encoding="utf-8")
    tool.chmod(0o755)
    log = tmp_path / "gh-calls.jsonl"
    entered = tmp_path / "entered.json"
    release = tmp_path / "release.flag"
    monkeypatch.setenv("PATH", f"{binaries}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv("FAKE_GH_LOG", str(log))
    monkeypatch.setenv("FAKE_GH_BY_CWD", "{}")
    monkeypatch.setenv("FAKE_GH_ENTERED_FILE", str(entered))
    monkeypatch.setenv("FAKE_GH_RELEASE_FILE", str(release))
    monkeypatch.setenv("FAKE_GH_HOLD_FAILSAFE_SECONDS", "8")
    monkeypatch.delenv("FAKE_GH_HOLD_CWD", raising=False)
    monkeypatch.delenv("FAKE_GH_FAIL_COMMENT", raising=False)

    def set_by_cwd(mapping: dict) -> None:
        keyed = {str(Path(k).resolve()): v for k, v in mapping.items()}
        monkeypatch.setenv("FAKE_GH_BY_CWD", json.dumps(keyed))

    def hold(repo_path) -> None:
        for stale in (entered, release, Path(str(entered) + ".timedout")):
            if stale.exists():
                stale.unlink()
        monkeypatch.setenv("FAKE_GH_HOLD_CWD", str(Path(repo_path).resolve()))

    def wait_for_entry(timeout: float = 5.0) -> dict:
        deadline = time.time() + timeout
        while time.time() < deadline:
            if entered.exists():
                return json.loads(entered.read_text(encoding="utf-8"))
            time.sleep(0.02)
        raise AssertionError(f"the held host call never actually started within {timeout}s")

    def release_now() -> None:
        release.write_text("go", encoding="utf-8")

    def timed_out() -> bool:
        return Path(str(entered) + ".timedout").exists()

    def fail_comment() -> None:
        monkeypatch.setenv("FAKE_GH_FAIL_COMMENT", "1")

    def calls() -> list[dict]:
        if not log.exists():
            return []
        return [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines() if line.strip()]

    return {
        "set_by_cwd": set_by_cwd, "hold": hold, "wait_for_entry": wait_for_entry,
        "release": release_now, "timed_out": timed_out, "fail_comment": fail_comment,
        "calls": calls,
    }


# --------------------------------------------------------------------------
# a real server, two real repositories, one manager -- module scope so every
# test in this file shares one boot rather than paying for it per test
# --------------------------------------------------------------------------
def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "user.name=Test", "-c", "user.email=test@example.invalid", *args],
        cwd=repo, check=True, capture_output=True,
    )


def _make_repo(repo: Path) -> None:
    (repo / "docs" / "workflow").mkdir(parents=True)
    (repo / "docs" / "VISION.md").write_text("# Demo Vision (DRAFT)\n\nOne place.\n", encoding="utf-8")
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "seed: the vision")


def _make_project(tmp_path: Path, repos: list[Path]) -> dict:
    for repo in repos:
        _make_repo(repo)
    batch = tmp_path / "hw-demo"
    (batch / "goals").mkdir(parents=True)
    (batch / "HIGHWAY.md").write_text("# HIGHWAY\n\n## Outcome\nProve gh responsiveness.\n", encoding="utf-8")
    (batch / ".width").write_text("4\n", encoding="utf-8")
    (batch / "manifest.tsv").write_text("lane\tworktree\tbranch\n", encoding="utf-8")
    conf = tmp_path / "converge-app.toml"
    repo_list = ", ".join(f'"{r}"' for r in repos)
    conf.write_text(
        "[[managers]]\n"
        f'id = "{MANAGER}"\n'
        'name = "Demo manager"\n'
        f'batch_dir = "{batch}"\n'
        f'repos = [{repo_list}]\n'
        'tmux_socket = "collab-gh-responsiveness-socket-that-does-not-exist"\n'
        f'steward = "{STEWARD}"\n',
        encoding="utf-8",
    )
    return {
        "config": conf, "secret": tmp_path / "secret", "state": tmp_path / "state.json",
        "sessions": tmp_path / "sessions.json", "repos": repos,
    }


@pytest.fixture(scope="module")
def two_repo_project(tmp_path_factory) -> dict:
    tmp_path = tmp_path_factory.mktemp("collab-gh-responsiveness")
    return _make_project(tmp_path, [tmp_path / "repo-a", tmp_path / "repo-b"])


def _free_port() -> int:
    s = socketlib.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def _start_server(project: dict):
    import uvicorn

    made = serve.create_app(
        config_path=project["config"], secret_path=project["secret"],
        state_path=project["state"], sessions_path=project["sessions"],
    )
    made.include_router(collab.router)
    port = _free_port()
    config = uvicorn.Config(made, host="127.0.0.1", port=port, log_level="warning")
    uv_server = uvicorn.Server(config)
    thread = threading.Thread(target=uv_server.run, daemon=True)
    thread.start()
    deadline = time.time() + 20
    while not uv_server.started and time.time() < deadline:
        time.sleep(0.05)
    assert uv_server.started, "app server did not start"
    return uv_server, thread, f"http://127.0.0.1:{port}"


@pytest.fixture(scope="module")
def server(two_repo_project):
    uv_server, thread, url = _start_server(two_repo_project)
    yield url
    uv_server.should_exit = True
    thread.join(timeout=10)


@pytest.fixture(autouse=True)
def _forget_arrivals():
    collab.ARRIVALS.__init__()
    yield
    collab.ARRIVALS.__init__()


def _ratification_files(repo: Path) -> list[Path]:
    return sorted((repo / "docs" / "workflow").glob("owner-ratifications-*.md"))


def _steward_cookie(project: dict) -> str:
    sessions = auth.Sessions(auth.read_or_make_secret(project["secret"]))
    return sessions.issue(STEWARD)


# --------------------------------------------------------------------------
# the fix: a slow `pr comment` (ask_on_the_host) no longer blocks a
# concurrent request for a DIFFERENT repository
# --------------------------------------------------------------------------
def test_ask_on_the_host_does_not_block_a_different_repository_while_the_host_is_slow(
    server, host, two_repo_project,
) -> None:
    repo_a, repo_b = two_repo_project["repos"]
    repo_a_id = collab._repo_key(repo_a)
    repo_b_id = collab._repo_key(repo_b)
    host["set_by_cwd"]({
        repo_a: {"pulls": [_pull(7, "Repo A's own PR")], "comments": []},
        repo_b: {"pulls": [_pull(9, "Repo B's own PR")], "comments": []},
    })
    host["hold"](repo_a)
    cookie = _steward_cookie(two_repo_project)

    held: dict = {}

    def post_held_comment() -> None:
        with httpx.Client(base_url=server, cookies={auth.COOKIE: cookie}, timeout=15.0) as client:
            response = client.post(
                f"/api/collab/{MANAGER}/pulls/7/comments",
                json={"text": "Does this look right?", "repoId": repo_a_id},
            )
            held["status"] = response.status_code
            held["body"] = response.json()

    holder = threading.Thread(target=post_held_comment, daemon=True)
    holder.start()

    # Prove entry: the held call genuinely started before we test anything.
    entry = host["wait_for_entry"](timeout=5.0)
    assert Path(entry["cwd"]) == repo_a.resolve(), entry

    # Prove the OTHER repository's request completes BEFORE the held one is
    # released -- a short client-side timeout is the independent failsafe:
    # against the prior code this would raise a timeout, not hang.
    with httpx.Client(base_url=server, cookies={auth.COOKIE: cookie}, timeout=2.0) as client:
        started = time.time()
        other = client.get(f"/api/collab/{MANAGER}/pulls/9", params={"repoId": repo_b_id})
        elapsed = time.time() - started

    assert other.status_code == 200, other.text
    assert other.json()["proposal"]["origin"]["number"] == 9
    assert elapsed < 1.5, (
        f"repo B's request took {elapsed:.2f}s while repo A's comment was held open "
        "-- the event loop was blocked"
    )
    assert holder.is_alive(), "the held request finished on its own -- it was never actually held"

    host["release"]()
    holder.join(timeout=15)
    assert not holder.is_alive(), "the held comment request never returned after release"
    assert not host["timed_out"](), "the stand-in host's own failsafe fired -- release arrived too late"

    assert held["status"] == 200, held
    assert held["body"]["ok"] is True, held["body"]
    posted = [c for c in host["calls"]() if c["argv"][:2] == ["pr", "comment"]]
    assert len(posted) == 1 and posted[0]["argv"][2] == "7", host["calls"]()


# --------------------------------------------------------------------------
# the fix: a slow `pr comment` from answering (answer_a_pull) no longer
# blocks a concurrent request for a DIFFERENT repository, and the
# ratification record is written before the host call even begins
# --------------------------------------------------------------------------
def test_answer_a_pull_does_not_block_a_different_repository_while_the_host_is_slow(
    server, host, two_repo_project,
) -> None:
    repo_a, repo_b = two_repo_project["repos"]
    repo_a_id = collab._repo_key(repo_a)
    repo_b_id = collab._repo_key(repo_b)
    host["set_by_cwd"]({
        repo_a: {"pulls": [_pull(7, "Repo A's own PR")], "comments": []},
        repo_b: {"pulls": [_pull(9, "Repo B's own PR")], "comments": []},
    })
    host["hold"](repo_a)
    cookie = _steward_cookie(two_repo_project)

    held: dict = {}

    def post_held_answer() -> None:
        with httpx.Client(base_url=server, cookies={auth.COOKIE: cookie}, timeout=15.0) as client:
            response = client.post(
                f"/api/collab/{MANAGER}/pulls/7/answer",
                json={"decision": "ratified", "note": "Looks right.", "repoId": repo_a_id},
            )
            held["status"] = response.status_code
            held["body"] = response.json()

    holder = threading.Thread(target=post_held_answer, daemon=True)
    holder.start()

    entry = host["wait_for_entry"](timeout=5.0)
    assert Path(entry["cwd"]) == repo_a.resolve(), entry

    # Record-before-host ordering: `writes.record_decision` runs
    # synchronously, before the `await asyncio.to_thread(post_answer_back,
    # ...)`. By the time the host call has demonstrably started (the assert
    # above), the record must already be on disk -- proving the fix moved
    # only the blocking HOST call off the loop, not the write that precedes it.
    files = _ratification_files(repo_a)
    assert len(files) == 1, "the ratification record was not written before the host call began"
    text = files[0].read_text(encoding="utf-8")
    assert "Ratified" in text and STEWARD in text, text

    with httpx.Client(base_url=server, cookies={auth.COOKIE: cookie}, timeout=2.0) as client:
        started = time.time()
        other = client.get(f"/api/collab/{MANAGER}/pulls/9", params={"repoId": repo_b_id})
        elapsed = time.time() - started

    assert other.status_code == 200, other.text
    assert other.json()["proposal"]["origin"]["number"] == 9
    assert elapsed < 1.5, (
        f"repo B's request took {elapsed:.2f}s while repo A's answer was held open "
        "-- the event loop was blocked"
    )
    assert holder.is_alive(), "the held request finished on its own -- it was never actually held"

    host["release"]()
    holder.join(timeout=15)
    assert not holder.is_alive(), "the held answer request never returned after release"
    assert not host["timed_out"](), "the stand-in host's own failsafe fired -- release arrived too late"

    assert held["status"] == 200, held
    body = held["body"]
    assert body["ok"] is True, body
    assert body["recorded"]["ok"] is True, body
    assert body["returnedToOrigin"]["ok"] is True, body


# --------------------------------------------------------------------------
# host-failure control: the thread offload changes nothing about how a
# genuine host failure is reported -- still a structured, fast 502/ok:false,
# never a hang and never a swallowed exception
# --------------------------------------------------------------------------
def test_ask_on_the_host_reports_a_host_failure_promptly(server, host, two_repo_project) -> None:
    repo_a, repo_b = two_repo_project["repos"]
    repo_a_id = collab._repo_key(repo_a)
    host["set_by_cwd"]({
        repo_a: {"pulls": [_pull(7, "Repo A's own PR")], "comments": []},
        repo_b: {"pulls": [], "comments": []},
    })
    host["fail_comment"]()
    cookie = _steward_cookie(two_repo_project)

    with httpx.Client(base_url=server, cookies={auth.COOKIE: cookie}, timeout=5.0) as client:
        started = time.time()
        response = client.post(
            f"/api/collab/{MANAGER}/pulls/7/comments",
            json={"text": "Hello", "repoId": repo_a_id},
        )
        elapsed = time.time() - started

    assert elapsed < 3.0, f"a host failure took {elapsed:.2f}s to report -- it should fail fast, not hang"
    assert response.status_code == 502, response.text
    body = response.json()
    assert body["ok"] is False
    assert body.get("reason"), body


def test_answer_a_pull_reports_a_host_failure_but_keeps_the_record(server, host, two_repo_project) -> None:
    """The record is written before the host call; a host failure must not
    make it look unwritten (`app/collab.py`'s own docstring for this route)."""
    repo_a, repo_b = two_repo_project["repos"]
    repo_a_id = collab._repo_key(repo_a)
    host["set_by_cwd"]({
        repo_a: {"pulls": [_pull(11, "Repo A's second PR")], "comments": []},
        repo_b: {"pulls": [], "comments": []},
    })
    host["fail_comment"]()
    cookie = _steward_cookie(two_repo_project)

    with httpx.Client(base_url=server, cookies={auth.COOKIE: cookie}, timeout=5.0) as client:
        started = time.time()
        response = client.post(
            f"/api/collab/{MANAGER}/pulls/11/answer",
            json={"decision": "declined", "note": "Not yet.", "repoId": repo_a_id},
        )
        elapsed = time.time() - started

    assert elapsed < 3.0, f"a host failure took {elapsed:.2f}s to report -- it should fail fast, not hang"
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["ok"] is True, body  # the record succeeded even though the host call did not
    assert body["recorded"]["ok"] is True, body
    assert body["returnedToOrigin"]["ok"] is False, body
    assert body["returnedToOrigin"].get("reason"), body

    files = _ratification_files(repo_a)
    assert len(files) == 1
    assert "Declined" in files[0].read_text(encoding="utf-8")
