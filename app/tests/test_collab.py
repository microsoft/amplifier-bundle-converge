"""The host half of collaboration, proved against a stand-in host.

`contracts/experience-collaboration.v1.md` is a contract about a **seam**: git
is the protocol, the repository host carries the conversation, Converge renders
it. Before `app/collab.py` the Converge side of that seam did not exist -- no
route addressed a pull request, nothing posted a comment, and freshness was the
steward's own job.

What is real in these tests, and what stands in
----------------------------------------------
Everything on the Converge side is real: a real FastAPI app built by
`app/serve.py`, a real signed-in session through the real cookie gate, a real
git repository in a temp folder, and the real `app/writes.py` appending to the
real dated ratification record.

The one thing that stands in is **the repository host itself**. A live host
would need a second person and a network, which no file in this tree can be --
the conformance kit says the same thing when it SKIPs rule 4b. So `gh` is
replaced on `$PATH` by a script that answers like the host and *records what it
was asked to do*. That is what makes "the question reached the host" a checkable
claim rather than a hopeful one: the assertion reads the argv the bridge
actually ran, not a mock's `called_once_with`.

The last two tests run the contract's **own conformance kit** in-process, over a
snapshot of this app, so the verdict here and the verdict a steward gets from
`uv run conformance/experience-collaboration/run.py <app>` come from one piece
of code rather than two that can drift.
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

GOOD_USER = "tester"
GOOD_PASSWORD = "correct horse"
MANAGER = "demo"

#: The three-part shape this repository's own proposals use, written into a
#: pull request body by a teammate who has never opened Converge.
PULL_BODY = """## The exact change

- Core 4 gains a sentence about comments arriving both ways.
- The word "bridge" is defined once, in Core 4.

## The evidence

- A steward copied an answer between two tools four times in one week.
- One of those four answers reached the wrong pull request.

## What does not change

Git stays the protocol, and nothing about the write path moves.
"""


# --------------------------------------------------------------------------
# a stand-in host
# --------------------------------------------------------------------------
FAKE_GH = '''#!/usr/bin/env python3
"""A stand-in for the repository host command line.

It answers `pr list` and `pr view` from a fixture, and records every `pr
comment` it is asked to make into $FAKE_GH_LOG as one JSON line, so a test can
read exactly what the bridge sent.
"""
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
    one["comments"] = json.loads(os.environ.get("FAKE_GH_COMMENTS", "[]"))
    print(json.dumps(one))
elif argv[:2] == ["pr", "comment"]:
    print("https://host.invalid/demo/pull/7#issuecomment-1")
else:
    sys.stderr.write("this stand-in host was asked something it does not answer: %r\\n" % (argv,))
    sys.exit(1)
'''

PULL_FIXTURE = {
    "number": 7,
    "title": "Say that comments travel both ways",
    "body": PULL_BODY,
    "author": {"login": "wren"},
    "url": "https://host.invalid/demo/pull/7",
    "updatedAt": "2026-09-04T09:00:00Z",
    "headRefName": "wren/two-way-comments",
    "isDraft": False,
}


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


# --------------------------------------------------------------------------
# a repository and an app around it
# --------------------------------------------------------------------------
@pytest.fixture
def project(tmp_path: Path) -> dict:
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

    conf = tmp_path / "converge-app.toml"
    conf.write_text(
        "[[managers]]\n"
        f'id = "{MANAGER}"\n'
        'name = "Demo manager"\n'
        f'batch_dir = "{batch}"\n'
        f'repos = ["{repo}"]\n'
        'tmux_socket = "collab-socket-that-does-not-exist"\n',
        encoding="utf-8",
    )
    return {"repo": repo, "batch": batch, "config": conf,
            "secret": tmp_path / "secret", "state": tmp_path / "state.json"}


class _FakePam:
    def authenticate(self, username: str, password: str, service: str = "login") -> bool:
        return username == GOOD_USER and password == GOOD_PASSWORD


def build_app(project: dict):
    """The app, plus the one line `app/serve.py` gains at integration."""
    made = serve.create_app(
        config_path=project["config"], secret_path=project["secret"], state_path=project["state"]
    )
    made.include_router(collab.router)
    return made


@pytest.fixture
def client(project, monkeypatch) -> TestClient:
    monkeypatch.setattr(auth.pam_module, "pam", _FakePam)
    made = build_app(project)
    client = TestClient(made, follow_redirects=False)
    answer = client.post("/login", data={"username": GOOD_USER, "password": GOOD_PASSWORD, "next": "/"})
    assert answer.status_code == 302 and auth.COOKIE in answer.cookies
    return client


@pytest.fixture(autouse=True)
def _forget_arrivals():
    """Nothing carries over: freshness is a fact about the last few minutes."""
    collab.ARRIVALS.__init__()
    yield
    collab.ARRIVALS.__init__()


# --------------------------------------------------------------------------
# clause 3 -- three origins, one review
# --------------------------------------------------------------------------
def test_a_pull_request_arrives_in_the_shape_a_proposal_is_laid_out_in(client, host) -> None:
    answer = client.get(f"/api/collab/{MANAGER}/pulls")
    assert answer.status_code == 200, answer.text
    body = answer.json()
    assert body["unreadable"] == [], body["unreadable"]
    one = body["proposals"][0]

    # The keys `app/data.py`'s `proposals_for` produces, so the review that
    # already exists lays this out without knowing where it came from.
    for key in ("id", "title", "source", "why", "evidence", "unchanged", "recommendation", "tradeoffs"):
        assert key in one, key
    assert one["changes"] == [
        'Core 4 gains a sentence about comments arriving both ways.',
        'The word "bridge" is defined once, in Core 4.',
    ]
    assert one["evidence"] == [
        "A steward copied an answer between two tools four times in one week.",
        "One of those four answers reached the wrong pull request.",
    ]
    assert one["unchanged"].startswith("Git stays the protocol")

    # Where it came from is a value on the proposal, never a second experience.
    assert one["source"] == "Pull request #7 - wren"
    assert one["origin"]["kind"] == "pull request"
    assert one["origin"]["number"] == 7
    assert one["origin"]["url"] == "https://host.invalid/demo/pull/7"


def test_the_reading_really_ran_the_hosts_own_command_line(client, host) -> None:
    client.get(f"/api/collab/{MANAGER}/pulls")
    assert calls(host)[0][:2] == ["pr", "list"], calls(host)


# --------------------------------------------------------------------------
# clause 4 -- a question asked here arrives on the host
# --------------------------------------------------------------------------
def test_a_question_asked_in_converge_is_posted_as_a_comment(client, host) -> None:
    answer = client.post(
        f"/api/collab/{MANAGER}/pulls/7/comments",
        json={"repoId": "demo-repo", "text": "Which sentence in Core 4 does this replace?"},
    )
    assert answer.status_code == 200, answer.text
    assert answer.json()["ok"] is True

    posted = [c for c in calls(host) if c[:2] == ["pr", "comment"]]
    assert len(posted) == 1, calls(host)
    assert posted[0][2] == "7"
    assert posted[0][3] == "--body"
    assert "Which sentence in Core 4 does this replace?" in posted[0][4]
    # Attributed, so the teammate knows who is asking without leaving the host.
    assert f"Asked by {GOOD_USER}" in posted[0][4]


def test_an_empty_question_is_not_sent_anywhere(client, host) -> None:
    answer = client.post(f"/api/collab/{MANAGER}/pulls/7/comments", json={"text": "   "})
    assert answer.status_code == 400
    assert [c for c in calls(host) if c[:2] == ["pr", "comment"]] == []


def test_the_conversation_on_the_host_is_read_back_into_the_review(client, host, monkeypatch) -> None:
    monkeypatch.setenv("FAKE_GH_COMMENTS", json.dumps([
        {"author": {"login": "wren"}, "createdAt": "2026-09-04T10:00:00Z", "body": "The second one."},
    ]))
    answer = client.get(f"/api/collab/{MANAGER}/pulls/7?repoId=demo-repo")
    assert answer.status_code == 200, answer.text
    said = answer.json()["proposal"]["comments"]
    assert said == [{"author": "wren", "when": "2026-09-04T10:00:00Z", "body": "The second one."}]


# --------------------------------------------------------------------------
# clause 5 -- the answer lands in the record AND goes back to its origin
# --------------------------------------------------------------------------
def test_an_answer_is_recorded_and_posted_back_where_it_came_from(client, host, project) -> None:
    answer = client.post(
        f"/api/collab/{MANAGER}/pulls/7/answer",
        json={"repoId": "demo-repo", "decision": "ratified-with-edits",
              "note": "Keep the first sentence, drop the second."},
    )
    assert answer.status_code == 200, answer.text
    body = answer.json()
    assert body["ok"] is True
    assert body["decision"] == "Ratified with edits"

    # Half one: the dated ratification record, written by app/writes.py.
    records = sorted((project["repo"] / "docs" / "workflow").glob("owner-ratifications-*.md"))
    assert records, "no dated ratification record was written"
    written = records[0].read_text(encoding="utf-8")
    assert "Ratified with edits" in written
    assert "pull-7" in written
    assert "Keep the first sentence, drop the second." in written

    # Half two: the same word, on the pull request it came from.
    assert body["returnedToOrigin"]["ok"] is True
    posted = [c for c in calls(host) if c[:2] == ["pr", "comment"]]
    assert len(posted) == 1, calls(host)
    assert "**Ratified with edits**" in posted[0][4]
    assert "Keep the first sentence, drop the second." in posted[0][4]
    assert GOOD_USER in posted[0][4]


def test_a_word_outside_the_four_is_refused_and_nothing_is_written(client, host, project) -> None:
    answer = client.post(
        f"/api/collab/{MANAGER}/pulls/7/answer", json={"repoId": "demo-repo", "decision": "approved"}
    )
    assert answer.status_code == 400
    assert list((project["repo"] / "docs" / "workflow").glob("owner-ratifications-*.md")) == []
    assert [c for c in calls(host) if c[:2] == ["pr", "comment"]] == []


def test_a_host_that_refuses_the_comment_does_not_hide_that_the_record_was_written(
    client, project, tmp_path, monkeypatch
) -> None:
    """The two halves are reported separately, on purpose.

    A single `ok` would have to choose which half it means, and either choice
    lies: a steward told "not answered" would answer twice, and one told
    "answered" would never learn the teammate was not told.
    """
    binaries = tmp_path / "refusing-bin"
    binaries.mkdir()
    (binaries / "gh").write_text("#!/bin/sh\necho 'the host said no' >&2\nexit 1\n", encoding="utf-8")
    (binaries / "gh").chmod(0o755)
    monkeypatch.setenv("PATH", f"{binaries}{os.pathsep}{os.environ['PATH']}")

    answer = client.post(
        f"/api/collab/{MANAGER}/pulls/7/answer", json={"repoId": "demo-repo", "decision": "declined"}
    )
    body = answer.json()
    assert body["ok"] is True, "the record was written, and the answer says so"
    assert body["returnedToOrigin"]["ok"] is False
    assert "the host said no" in body["returnedToOrigin"]["reason"]
    assert list((project["repo"] / "docs" / "workflow").glob("owner-ratifications-*.md"))


def test_with_no_host_command_line_the_refusal_says_so_in_plain_words(client, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("PATH", str(tmp_path / "empty-bin"))
    answer = client.get(f"/api/collab/{MANAGER}/pulls")
    said = answer.json()["unreadable"]
    assert said and "gh` is not installed" in said[0]["reason"], said


# --------------------------------------------------------------------------
# clause 6 -- inbound changes arrive without the steward asking
# --------------------------------------------------------------------------
def test_without_a_shared_secret_the_webhook_refuses_rather_than_trusting_the_caller(client) -> None:
    answer = client.post(collab.WEBHOOK_PATH, json={"event": "pull_request"})
    assert answer.status_code == 503
    assert "shared secret" in answer.json()["reason"]


def test_a_call_that_does_not_carry_the_secret_is_refused(client, tmp_path, monkeypatch) -> None:
    secret = tmp_path / "webhook-secret"
    secret.write_text("open-sesame\n", encoding="utf-8")
    monkeypatch.setattr(collab, "SECRET_PATH", secret)
    answer = client.post(collab.WEBHOOK_PATH, json={}, headers={"x-converge-secret": "guess"})
    assert answer.status_code == 403


def test_a_call_from_the_host_flips_the_surface_from_polling_to_webhook(client, tmp_path, monkeypatch) -> None:
    secret = tmp_path / "webhook-secret"
    secret.write_text("open-sesame\n", encoding="utf-8")
    monkeypatch.setattr(collab, "SECRET_PATH", secret)

    before = client.get(f"/api/collab/{MANAGER}/freshness").json()
    assert before["mechanism"] == "polling"
    assert "checked every 60 seconds" in before["words"]

    answer = client.post(
        collab.WEBHOOK_PATH,
        json={"repoId": "demo-repo", "note": "one pull request opened"},
        headers={"x-converge-secret": "open-sesame", "x-github-event": "pull_request"},
    )
    assert answer.status_code == 200, answer.text

    after = client.get(f"/api/collab/{MANAGER}/freshness").json()
    assert after["mechanism"] == "webhook"
    assert "Webhook" in after["words"] and "Polling still runs" in after["words"]
    assert after["lastArrival"]


def test_the_freshness_sentence_names_the_mechanism_rather_than_assuming_it(client) -> None:
    said = client.get(f"/api/collab/{MANAGER}/freshness").json()["words"]
    assert "Polling" in said
    assert "checked every" in said
    assert "webhook" in said.lower()
    assert "you are not the one keeping this fresh" in said


def test_the_partial_says_how_it_stays_fresh_without_waiting_for_a_script() -> None:
    """Clause 6b is about a reader, not about a payload.

    The sentence is in the markup because a sentence that only exists after
    JavaScript has run is not named to a steward whose script failed.
    """
    said = (REPO_ROOT / "app" / "templates" / "collab.html").read_text(encoding="utf-8")
    assert "checked every 60 seconds" in said
    assert "webhook" in said
    assert "polling" in said.lower()


# --------------------------------------------------------------------------
# clause 2 / clause 10 -- what this bridge must never grow into
# --------------------------------------------------------------------------
def test_no_route_here_addresses_a_second_manager_session(client) -> None:
    paths = list(client.app.openapi()["paths"])
    ours = [p for p in paths if p.startswith("/api/collab")]
    assert ours, "the router is not mounted"
    for path in ours:
        assert "/manager" not in path.replace("/{mid}", ""), path
    source = (REPO_ROOT / "app" / "collab.py").read_text(encoding="utf-8")
    for word in ("federat", "\npeer", " peer", "_peer"):
        assert word not in source, f"{word!r} names a channel this clause forbids"


def test_the_bridge_keeps_no_surface_of_its_own(client) -> None:
    """Every destination is the host. Nothing is stored here."""
    ours = [p for p in client.app.openapi()["paths"] if p.startswith("/api/collab")]
    for word in ("/issues", "/tickets", "/threads", "/boards", "/wikis"):
        assert not any(word in p for p in ours), word
    # The only state this module keeps is when the host last called: no pull
    # request, no comment, and no answer is held here.
    assert set(vars(collab.ARRIVALS)) == {"_lock", "_last", "_events"}


def test_the_gate_covers_the_new_routes_because_they_exist(project, monkeypatch) -> None:
    """`app/serve.py` gates by middleware, not by decoration -- so this is free."""
    monkeypatch.setattr(auth.pam_module, "pam", _FakePam)
    stranger = TestClient(build_app(project), follow_redirects=False)
    assert stranger.get(f"/api/collab/{MANAGER}/pulls").status_code == 401
    assert stranger.post(f"/api/collab/{MANAGER}/pulls/7/comments", json={"text": "hi"}).status_code == 401
    assert stranger.post(f"/api/collab/{MANAGER}/pulls/7/answer", json={"decision": "ratified"}).status_code == 401


# --------------------------------------------------------------------------
# clause 8 -- whose word counts, settled at registration
# --------------------------------------------------------------------------
def test_the_steward_is_read_from_the_registration_and_never_from_the_reader() -> None:
    """`steward_of` reads a registered fact, or says nothing.

    The field itself belongs to `app/config.py` and `app/data.py`, which this
    lane does not own; what is proved here is that when it is there this module
    reads it, and when it is not this module answers with an empty string
    rather than falling back to whoever is signed in.
    """
    class Registered:
        steward = "wren"

    class NotRegistered:
        pass

    assert collab.steward_of(Registered()) == "wren"
    assert collab.steward_of(NotRegistered()) == ""


# --------------------------------------------------------------------------
# the contract's own kit, run over this app
# --------------------------------------------------------------------------
def _kit():
    """The kit script itself, loaded the way its own command line loads it."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "collab_kit", REPO_ROOT / "conformance" / "experience-collaboration" / "run.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)          # this puts conformance/ on sys.path
    return module


def _snapshot(client, tmp_path: Path, extra_boot: dict | None = None):
    """This app, captured the way the kit's own reader captures one.

    The `/` body is the shell with the partial included, which is the second of
    the two integration lines. Rendering it here rather than asserting against
    the un-included shell is deliberate: the kit judges *what a steward is
    served*, and until `app/templates/shell.html` carries the include line this
    is the only place that page exists.
    """
    from jinja2 import Environment, FileSystemLoader, select_autoescape

    _kit()                                    # sys.path, once
    import appsnapshot                        # the kit's own reader

    templates = Environment(
        loader=FileSystemLoader(str(REPO_ROOT / "app" / "templates")),
        autoescape=select_autoescape(["html", "xml"]),
    )
    shell = templates.get_template("shell.html").render(user=GOOD_USER)
    partial = templates.get_template("collab.html").render()
    # Where the include line goes: below `.body-grid`, beside the dialogs -- not
    # inside `<main class="workspace">`, which is `overflow:hidden` and draws the
    # foot of this panel underneath the console pane. Measured 2026-09-04.
    anchor = '<div id="managerMenu"'
    assert anchor in shell, "the shell no longer includes dialogs.html where this expects"
    served = shell.replace(anchor, partial + "\n" + anchor, 1)
    assert partial.strip() and partial in served, "the partial was not included in the shell"

    boot = client.get("/api/boot").json()
    if extra_boot:
        boot["managers"] = [{**one, **extra_boot} for one in boot["managers"]]

    bodies = {
        "/": served,
        "/openapi.json": json.dumps(client.app.openapi()),
        "/api/boot": json.dumps(boot),
        f"/api/managers/{MANAGER}": client.get(f"/api/managers/{MANAGER}").text,
    }
    order = list(bodies)
    for asset in appsnapshot.CLIENT_ASSETS:
        on_disk = REPO_ROOT / "app" / asset.removeprefix("/")
        if on_disk.is_file():
            bodies[asset] = on_disk.read_text(encoding="utf-8")
            order.append(asset)

    base = tmp_path / "snapshot"
    base.mkdir(exist_ok=True)
    beside = base / "repo"
    if not beside.exists():
        beside.symlink_to(REPO_ROOT, target_is_directory=True)

    return appsnapshot.AppSnapshot(str(base), "snapshot", bodies, order, {"manager": MANAGER})


def _verdicts(report) -> dict:
    return {row["rule"]: row["status"] for row in report["results"]}


def test_the_four_rules_this_bridge_answers_all_pass(client, host, tmp_path, capsys) -> None:
    """4a, 5b, 6a and 6b, judged by the contract's own kit over this app."""
    kit = _kit()
    snapshot = _snapshot(client, tmp_path)
    report = kit.run_conformance(snapshot)
    seen = _verdicts(report)
    with capsys.disabled():
        print("\n  experience-collaboration.v1, over this app:")
        for row in report["results"]:
            print(f"    {row['rule']:<3} {row['status']:<4} {row['detail'][:92]}")
        s = report["summary"]
        print(f"    VERDICT: {report['verdict']}  (pass={s['pass']} fail={s['fail']} skip={s['skip']})")
    for rule in ("4a", "5b", "6a", "6b"):
        assert seen[rule] == "PASS", f"{rule}: {seen[rule]} -- {report['results']}"


def test_nothing_this_bridge_added_broke_a_rule_that_already_held(client, host, tmp_path) -> None:
    """The seven rules that passed before must still pass.

    A bridge to the host is exactly the change that could grow a second
    collaboration surface (clause 10) or a channel between two manager sessions
    (clause 2), so those are asserted rather than assumed.
    """
    kit = _kit()
    seen = _verdicts(kit.run_conformance(_snapshot(client, tmp_path)))
    for rule in ("1", "2", "3", "5a", "7", "9", "10"):
        assert seen[rule] == "PASS", f"{rule}: {seen[rule]}"


def test_one_steward_per_session_needs_one_field_on_the_registration(client, host, tmp_path) -> None:
    """Rule 8a, and exactly what is missing.

    `app/config.py` and `app/data.py` are not this lane's files, so the manager
    payload does not carry a steward yet. What is proved here is that the field
    is the whole of it: with `steward` on the registration the contract's own
    kit passes rule 8a, and `app/collab.py` already reads it.
    """
    kit = _kit()
    with_field = _verdicts(kit.run_conformance(_snapshot(client, tmp_path, {"steward": "wren"})))
    assert with_field["8a"] == "PASS", with_field["8a"]
