"""Restoring from any snapshot, and a lock refusal that names its own cause.

Two work items, one lane, and both are about a screen telling the truth about
what the server actually did.

**converge-4pq — `experience-direction.v1` §6.** Restore was a real action at
four scopes already, but it could only ever reach ONE snapshot: the steward's
own read point. Every other row in the History list was out of reach, because
the app answered no route that read a document at another commit. It does now:
`GET .../docs/{repo}/{doc}?since=<sha>` reads the document as it stood at any
commit in its OWN history, and `POST .../changes/{id}/restore` takes the same
`since` in its body, so the wording that goes back is the wording that stood
there. Reading a snapshot never moves the read point — looking at history is
not reading.

**converge-8r5 — `experience-direction.v1` §11, and AGENTS.md §5.** The lock
control's failure toast said *"this app answers no lock route yet … Filed as
converge-eci"*. That was true while converge-eci was open. Since it landed,
`app/serve.py` answers the route and `writes.lock_document` refuses it for four
real reasons — already locked · fewer than four conditions · uncommitted
changes · no H1 — and every one of them reached the steward under a cause
nobody had observed. "Never claim a result you did not observe" cuts both ways:
a screen may not claim a cause it did not observe either.

Everything below runs against a real git repository in a temporary directory.
The wording is read back off disk, the commits out of `git log`, the proposal
out of the file beside the document. Nothing here is faked.

MANUAL_PROCEDURE (no browser on this host — do these by hand instead)

Setup
  a. Serve a repository with a document that has three or more commits:
       uv run --extra app python -m app.serve --port <your own port>
  b. Sign in and open that document, then Mark all as read, so the steward's
     read point IS the current version and the ONLY thing an older snapshot can
     be reached by is the new route.

Check — an older snapshot is reachable (converge-4pq)
  c. Open History. SEE the list of snapshots, "Current" selected.
  d. Click the OLDEST row. SEE the restore panel redraw and say it puts wording
     back as it stood at that commit's short sha — not at your read point.
  e. Open Details under the panel. SEE that it no longer says an older snapshot
     is out of reach, and no longer names converge-4pq.
     FAILS IF: the panel still shows the read point's sentences under an older
     row's heading — that is the old behaviour wearing the new label.
  f. Restore one wording. SEE a toast naming a commit, and:
       git log -1 --format=%s -- <the document>
       git show HEAD:<the document> | grep '<the old sentence>'
     SEE the sentence as it read at that OLD snapshot, not the one before it.
     FAILS IF: the sentence that came back is the one from your read point.
  g. Switch to Changes. SEE your read point where you left it: reading history
     did not mark anything read.

Check — the bound is real
  h. In the devtools console:
       await (await fetch(location.origin + '/api/managers/<mid>/docs/<repo>/'
              + '<doc>?since=deadbeefcafe')).json()
     SEE `{error: "deadbeefcafe is not a commit in this document's history…"}`
     and a 400.
     FAILS IF: it answers 200 with a reading — the route would then read any
     revision a caller names, which is a larger promise than §6 makes.

Check — a locked document proposes instead (§6's second half)
  i. Open a document whose H1 carries (FROZEN <date>). Pick an older snapshot,
     restore a wording. SEE the toast name a proposal file, and:
       git status --porcelain
     SEE the document itself unchanged and `<doc-stem>.vN-candidate.md` beside
     it carrying the wording.

Check — a lock refusal names its own cause (converge-8r5)
  j. Open a DRAFT contract the ledger watches; tick the three steward
     conditions so the control goes live. Before clicking, lock the file from a
     shell:
       sed -i '1s/(DRAFT)/(FROZEN 2026-09-04)/' <the contract>
       git commit -qam 'locked out of band'
  k. Click Lock, then Lock it. SEE a toast reading
     "Nothing was locked — <contract> already carries FROZEN in its first line,
     so it is already law…".
     FAILS IF: the toast says the app answers no lock route, or names
     converge-eci. Both are causes the screen did not observe.
  l. On a DRAFT contract the ledger watches, tick the three and lock it for
     real. SEE "Locked: FROZEN", and the H1 stamped on disk.

Check — it holds at both widths
  m. Repeat (c)-(f) at 1280x800 and at 390x844. At each, with History open, run
     in the console:
       document.documentElement.scrollWidth + ' vs ' + document.documentElement.clientWidth
     SEE the two numbers equal, and no console errors.
"""

from __future__ import annotations

import re
import shutil
import socket as socketlib
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app import auth, serve  # noqa: E402

USER = "tester"
PASSWORD = "hunter2"

HERE = Path(__file__).resolve().parents[1]
ACTIONS_JS = HERE / "static" / "js" / "actions.js"
DIRECTION_JS = HERE / "static" / "js" / "render" / "direction.js"
API_JS = HERE / "static" / "js" / "api.js"

#: The four the Freeze Bar asks for, in the words the browser sends.
FOUR = [
    "It says what it means — your word",
    "It carries a real example of right and wrong — your word",
    "It can be checked against reality — Kept — every clause has a row",
    "You have read it and agreed — your word",
]


# --------------------------------------------------------------------------
# a repository with real history
# --------------------------------------------------------------------------
#
# Three commits on the vision on purpose. Two would be enough to prove a
# restore works; three are what proves it reaches the RIGHT one, because the
# wording at the oldest commit and the wording at the steward's read point are
# then different sentences, and a restore that quietly fell back to the read
# point would put back the wrong one and still look like a success.

VISION_ONE = """# Demo Vision (DRAFT)

## Where this is going

The console is a tab you visit when something breaks.

## Core

1. A decision is recorded where the manager session already reads.
2. Nothing is ever overwritten.

## How we work

A lane returns with proof or it returns blocked.
"""

VISION_TWO = """# Demo Vision (DRAFT)

## Where this is going

The console is a place you work.

## Core

1. A decision is recorded where the manager session already reads, and nowhere else.
2. Nothing is ever overwritten.

## How we work

A lane returns with proof or it returns blocked.
"""

VISION_THREE = """# Demo Vision (DRAFT)

## Where this is going

The console is where the work happens, all day long.

## Core

1. A decision is recorded where the manager session already reads, and in no other place.
2. Nothing is ever overwritten.

## How we work

A lane returns with proof, or it returns blocked and says why.
"""

LOCKED_ONE = """# Locked Contract — v1 (FROZEN 2026-09-01)

## Core

1. A decision is recorded where the manager session already reads.
"""

LOCKED_TWO = """# Locked Contract — v1 (FROZEN 2026-09-01)

## Core

1. A decision is recorded wherever the manager session happens to look.
"""

#: Watched by the ledger, so "it can be checked against reality" is met and the
#: lock control can go live. One to lock for real, one to lose a race with.
DEMO_ONE = """# Demo Contract — v1 (DRAFT)

## Core

1. **The demo keeps one promise.** It is watched by the ledger.
"""

RACE_ONE = """# Race Contract — v1 (DRAFT)

## Core

1. **This one gets locked underneath the browser.** It is watched by the ledger.
"""

LEDGER = """# Demo conformance ledger.
- id: DEMO-001
  title: the demo contract keeps its one promise
  contract:
    file: contracts/demo.v1.md
    clause: "Core 1"
  disposition: CONFORMS
- id: RACE-001
  title: the race contract keeps its one promise
  contract:
    file: contracts/race.v1.md
    clause: "Core 1"
  disposition: CONFORMS
"""

#: Twelve sentences that all move in one commit. A whole-document restore is
#: one commit per sentence, so restoring this from its first commit makes the
#: loop commit twelve times — which is what proves the snapshot stays
#: reachable while the loop's own writes pile up on top of it.
MANY = 12


def _many(word: str) -> str:
    lines = ["# Many Contract — v1 (DRAFT)", "", "## Core", ""]
    lines += [f"{n}. Rule {n} says the {word} thing about rule {n}." for n in range(1, MANY + 1)]
    return "\n".join(lines) + "\n"


#: `data.repo_docs` shows a steward the vision and the contracts and nothing
#: else, so every document this file needs the app to open lives in
#: `contracts/*.v1.md`. A fixture document the app cannot see is a fixture
#: that tests nothing.
OTHER_ONE = "# Other Contract — v1 (DRAFT)\n\n## Core\n\n1. This document is not the vision.\n"
OTHER_TWO = "# Other Contract — v1 (DRAFT)\n\n## Core\n\n1. This document is still not the vision.\n"

MANIFEST_HEAD = "lane\tworktree\tbranch\tbase\ttmux\tgoal\tlog\tstarted\n"


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
def project(tmp_path_factory) -> dict:
    """A real repository, real history, and nothing pre-answered.

    Function-scoped: every test here writes to the document it opens, so a
    shared repository would make each test's evidence depend on the order the
    tests happened to run in.
    """
    tmp_path = tmp_path_factory.mktemp("direction-restore")
    repo = tmp_path / "demo-repo"
    (repo / "docs").mkdir(parents=True)
    (repo / "contracts").mkdir(parents=True)
    (repo / "ledger").mkdir(parents=True)

    (repo / "docs" / "VISION.md").write_text(VISION_ONE, encoding="utf-8")
    (repo / "contracts" / "many.v1.md").write_text(_many("first"), encoding="utf-8")
    (repo / "contracts" / "other.v1.md").write_text(OTHER_ONE, encoding="utf-8")
    (repo / "contracts" / "locked.v1.md").write_text(LOCKED_ONE, encoding="utf-8")
    (repo / "contracts" / "demo.v1.md").write_text(DEMO_ONE, encoding="utf-8")
    (repo / "contracts" / "race.v1.md").write_text(RACE_ONE, encoding="utf-8")
    (repo / "ledger" / "rows.yaml").write_text(LEDGER, encoding="utf-8")
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "seed: a vision, three contracts and two more documents")

    (repo / "docs" / "VISION.md").write_text(VISION_TWO, encoding="utf-8")
    (repo / "contracts" / "many.v1.md").write_text(_many("second"), encoding="utf-8")
    (repo / "contracts" / "locked.v1.md").write_text(LOCKED_TWO, encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "the console becomes a place")

    (repo / "docs" / "VISION.md").write_text(VISION_THREE, encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "the console is where the work happens")

    # A commit that touches no document but the other contract. It is a real
    # commit in this repository and NOT in the vision's own history, which is
    # exactly what the bound has to be able to tell apart.
    (repo / "contracts" / "other.v1.md").write_text(OTHER_TWO, encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "other: still not the vision")

    batch = tmp_path / "hw-demo"
    (batch / "lanes" / "w1-alpha").mkdir(parents=True)
    (batch / "goals").mkdir()
    (batch / "HIGHWAY.md").write_text("# Highway — demo\n\n## Outcome\n\nOne page.\n", encoding="utf-8")
    (batch / "goals" / "w1-alpha.md").write_text("# Lane alpha\n", encoding="utf-8")
    (batch / "lanes" / "w1-alpha" / "lane.log").write_text("working\n", encoding="utf-8")
    (batch / "manifest.tsv").write_text(
        MANIFEST_HEAD
        + f"w1-alpha\t{batch}/lanes/w1-alpha/demo-repo\tlane/w1-alpha\tdeadbee\t"
        f"hw__hw-demo__w1-alpha\t{batch}/goals/w1-alpha.md\t{batch}/lanes/w1-alpha/lane.log\t"
        "2026-09-01T10:00:00Z\n",
        encoding="utf-8",
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
    # Never the real ~/.amplifier: a test must not move a steward's read point
    # or answer a change on their behalf.
    return {
        "config": conf,
        "secret": tmp_path / "secret",
        "state": tmp_path / "state.json",
        "repo": repo,
        "vision": repo / "docs" / "VISION.md",
        "many": repo / "contracts" / "many.v1.md",
        "locked": repo / "contracts" / "locked.v1.md",
        "demo": repo / "contracts" / "demo.v1.md",
        "race": repo / "contracts" / "race.v1.md",
    }


@pytest.fixture
def client(project, monkeypatch) -> TestClient:
    monkeypatch.setattr(auth, "authenticate", lambda user, secret: user == USER and secret == PASSWORD)
    made = serve.create_app(
        config_path=project["config"], secret_path=project["secret"], state_path=project["state"]
    )
    one = TestClient(made, follow_redirects=False)
    answer = one.post("/login", data={"username": USER, "password": PASSWORD, "next": "/"})
    assert auth.COOKIE in answer.cookies, "the test could not sign in"
    return one


BASE = "/api/managers/demo/docs/demo-repo"


def read(client: TestClient, doc_id: str = "vision", since: str = ""):
    answer = client.get(f"{BASE}/{doc_id}", params={"since": since} if since else None)
    return answer.status_code, answer.json()


def restore(client: TestClient, change_id: str, doc_id: str = "vision", since: str = ""):
    answer = client.post(
        f"{BASE}/{doc_id}/changes/{change_id}/restore", json={"since": since} if since else {}
    )
    return answer.status_code, answer.json()


def sentences(payload: dict) -> list[str]:
    return [f"{c['kind']}: {c['before']!r} -> {c['now']!r}" for c in payload.get("changes", [])]


def _uncommented(source: str) -> str:
    """The lines of some JavaScript that a steward could actually be shown.

    Line comments are dropped. This is deliberately crude — it would not
    survive a `//` inside a string literal, and there is none in the files it
    reads — because the alternative is a source scan that cannot tell a
    sentence on a screen from a comment recording what that sentence used to
    be. The whole point of these two work items is that the two are different.
    """
    kept = []
    for line in source.splitlines():
        stripped = line.strip()
        if stripped.startswith("//") or stripped.startswith("*") or stripped.startswith("/*"):
            continue
        kept.append(line)
    return "\n".join(kept)


# --------------------------------------------------------------------------
# converge-4pq — a reading at any snapshot the History view shows
# --------------------------------------------------------------------------


def test_every_snapshot_the_history_shows_can_be_read(client: TestClient) -> None:
    """§6's premise: a row in the list is a snapshot you can go back to.

    Every row, not one. The reading each answers names that commit as where it
    starts from, which is the whole of what "restore from here" needs.
    """
    _, whole = read(client)
    rows = whole["history"]
    print(f"\nthe vision's History shows {len(rows)} rows:")
    for row in rows:
        print(f"  · {row['id']:<10} {row['sha']}  {row['note']}")
    assert len(rows) >= 3, f"the fixture did not make enough history: {rows}"

    for row in rows:
        code, payload = read(client, since=row["sha"])
        assert code == 200, f"snapshot {row['sha']} was refused: {payload}"
        assert payload["reading"]["sinceSha"].startswith(row["sha"]), (
            f"a reading at {row['sha']} says it starts at {payload['reading']['sinceSha']}"
        )
        print(f"  read at {row['sha']}: since={payload['reading']['sinceShort']} "
              f"· {len(payload['changes'])} sentence(s) moved")


def test_an_older_snapshot_reaches_wording_the_read_point_cannot(client: TestClient) -> None:
    """The failure this item is about, stated as a difference.

    The steward marks everything read, so their own read point IS the current
    version and the reading from it is empty — there is nothing left to put
    back. The oldest snapshot still has three sentences behind it, and the
    wording it offers is the ORIGINAL, not the one commit before HEAD.
    """
    marked = client.post(f"{BASE}/vision/read").json()
    print(f"\nread point moved to {marked['short']}")
    _, mine = read(client)
    print(f"from the read point: {len(mine['changes'])} sentence(s) moved")
    assert mine["changes"] == [], "the fixture left changes behind the read point"

    oldest = mine["history"][-1]["sha"]
    _, back = read(client, since=oldest)
    print(f"from the oldest snapshot {oldest}: {len(back['changes'])} sentence(s) moved")
    for line in sentences(back):
        print(f"  · {line}")
    assert back["changes"], "the oldest snapshot reached no earlier wording at all"

    befores = " ".join(c["before"] for c in back["changes"])
    assert "The console is a tab you visit when something breaks." in befores, (
        "the wording offered is not the one that stood at the OLDEST snapshot"
    )
    assert "The console is a place you work." not in befores, (
        "the reading fell back to the middle commit — that is the read point's answer, not this one's"
    )


def test_reading_a_snapshot_does_not_move_the_read_point(client: TestClient) -> None:
    """The read point belongs to the steward. Looking at history is not reading."""
    client.post(f"{BASE}/vision/read")
    _, before = read(client)
    start = before["reading"]["sinceSha"]
    oldest = before["history"][-1]["sha"]
    print(f"\nread point before: {before['reading']['sinceShort']}")

    for _ in range(3):
        read(client, since=oldest)
    _, after = read(client)
    print(f"read point after three snapshot reads: {after['reading']['sinceShort']}")
    assert after["reading"]["sinceSha"] == start, (
        "reading history moved the steward's read point, so changes they never read were marked read"
    )


# --------------------------------------------------------------------------
# converge-4pq — the bound: this document's own history and nothing else
# --------------------------------------------------------------------------


def test_a_commit_outside_this_documents_history_is_refused_by_name(client: TestClient) -> None:
    """A route that reads any revision a caller names is a larger promise.

    Three refusals, and the third is the one that matters: a real commit, in
    this repository, that touched a DIFFERENT document. It is not a typo and
    not a forgery — it is exactly the case a bound that only checked "is this
    a commit?" would wave through.
    """
    _, whole = read(client)
    print(f"\nthe vision's own history: {[r['sha'] for r in whole['history']]}")

    code, said = read(client, since="deadbeefcafe")
    print(f"  invented sha    -> {code} {said['error']}")
    assert code == 400 and "not a commit in this document's history" in said["error"]

    code, said = read(client, since="dead")
    print(f"  four characters -> {code} {said['error']}")
    assert code == 400, "a prefix too short to name one commit was accepted"

    _, other = read(client, doc_id="other")
    stranger = other["history"][0]["sha"]
    mine = {row["sha"] for row in whole["history"]}
    assert stranger not in mine, "the fixture's other-document commit also touched the vision"
    code, said = read(client, since=stranger)
    print(f"  another document's commit {stranger} -> {code} {said['error']}")
    assert code == 400, (
        f"a commit that never touched this document was accepted as one of its snapshots: {said}"
    )
    assert stranger in said["error"], "the refusal does not name what was asked for"


def test_a_restore_refuses_the_same_commits_the_read_does(client: TestClient) -> None:
    """The bound is on the write too, and it refuses rather than falling back.

    Falling back would be the dangerous shape: a restore that quietly used the
    read point when it could not resolve the snapshot would put back a wording
    the steward never chose, and report success.
    """
    _, whole = read(client)
    oldest = whole["history"][-1]["sha"]
    _, back = read(client, since=oldest)
    card = back["changes"][0]
    before_disk = project_text(client)
    code, said = restore(client, card["id"], since="0123456789ab")
    print(f"\nrestore with an invented snapshot -> {code} {said['error']}")
    assert code == 400 and "not a commit in this document's history" in said["error"]
    assert project_text(client) == before_disk, "the document changed although the snapshot was refused"


def project_text(client: TestClient) -> str:
    """The vision as it stands on disk, read through the app's own payload."""
    return read(client)[1]["raw"]


# --------------------------------------------------------------------------
# converge-4pq — the acceptance: the wording as of that snapshot comes back
# --------------------------------------------------------------------------


def test_restoring_at_a_snapshot_puts_back_the_wording_that_stood_there(
    client: TestClient, project
) -> None:
    """The acceptance, on a DRAFT: it commits, and it commits the RIGHT words.

    The read point is moved to the current version first, so nothing but the
    snapshot could have supplied the sentence that comes back.
    """
    client.post(f"{BASE}/vision/read")
    _, whole = read(client)
    oldest = whole["history"][-1]["sha"]
    _, back = read(client, since=oldest)
    card = next(c for c in back["changes"] if "console" in (c["before"] or ""))
    print(f"\nrestoring at {oldest}: {card['now']!r} -> {card['before']!r}")

    code, said = restore(client, card["id"], since=oldest)
    print(f"  {code} {said.get('said')}")
    assert code == 200 and said["ok"] and said["mode"] == "commit", said

    on_disk = project["vision"].read_text(encoding="utf-8")
    print("  the document now reads:")
    for line in on_disk.splitlines():
        if "console" in line:
            print(f"    {line}")
    assert "The console is a tab you visit when something breaks." in on_disk, (
        "the sentence that came back is not the one that stood at that snapshot"
    )
    assert "The console is where the work happens" not in on_disk, "nothing was replaced"
    subject = _git(project["repo"], "log", "-1", "--format=%s").strip()
    print(f"  last commit: {subject}")
    assert "restored" in subject, f"the restore did not commit in the steward's name: {subject}"


def test_restoring_a_locked_document_at_a_snapshot_proposes_beside_it(
    client: TestClient, project
) -> None:
    """§6's second half, reached from a snapshot rather than the read point.

    The lock is not consulted anywhere in the new path: `writes.apply_change`
    reads the document's own H1, exactly as it did before a snapshot could be
    named. What this proves is that naming one did not route around it.
    """
    _, whole = read(client, doc_id="locked")
    oldest = whole["history"][-1]["sha"]
    print(f"\n{whole['path']} is {whole['locked']!r}; restoring at {oldest}")
    _, back = read(client, doc_id="locked", since=oldest)
    card = back["changes"][0]
    before = project["locked"].read_text(encoding="utf-8")

    code, said = restore(client, card["id"], doc_id="locked", since=oldest)
    print(f"  {code} mode={said.get('mode')} · {said.get('said')}")
    assert code == 200 and said["ok"], said
    assert said["mode"] == "candidate", f"a locked document was written in place: {said}"

    assert project["locked"].read_text(encoding="utf-8") == before, (
        "the locked document itself was touched"
    )
    beside = project["repo"] / "contracts" / Path(said["file"]).name
    text = beside.read_text(encoding="utf-8")
    print(f"  proposal at {said['file']}:")
    for line in text.splitlines()[:6]:
        print(f"    {line}")
    assert card["before"] in text, "the proposal does not carry the wording that stood at the snapshot"


def test_a_whole_document_restore_outlives_its_own_commits(client: TestClient, project) -> None:
    """A restore of many sentences must not make its own snapshot unreachable.

    Every restore on a draft commits, so restoring a whole document commits
    once per sentence. The History VIEW shows eight rows; if the bound read
    only those eight, this loop would push its own starting point out of range
    partway through and be refused with half the work already written. Twelve
    sentences is four more than eight, so this fails loudly if that bound is
    ever narrowed to what the view happens to show.
    """
    client.post(f"{BASE}/many/read")
    _, whole = read(client, doc_id="many")
    oldest = whole["history"][-1]["sha"]
    _, back = read(client, doc_id="many", since=oldest)
    print(f"\nrestoring the whole of {whole['path']} at {oldest}: "
          f"{len(back['changes'])} sentence(s)")
    assert len(back["changes"]) == MANY, f"the fixture moved {len(back['changes'])} sentences, not {MANY}"

    landed, refused = 0, []
    for _ in range(MANY):
        _, reading = read(client, doc_id="many", since=oldest)
        rows = reading["changes"]
        if not rows:
            break
        code, said = restore(client, rows[0]["id"], doc_id="many", since=oldest)
        if code == 200 and said.get("ok"):
            landed += 1
        else:
            refused.append(said.get("error"))
    print(f"  {landed} landed · {len(refused)} refused")
    for one in refused[:3]:
        print(f"    refused: {one}")
    assert landed == MANY, f"only {landed} of {MANY} landed; refusals: {refused[:3]}"

    on_disk = project["many"].read_text(encoding="utf-8")
    print(f"  the document now says 'first' {on_disk.count('first')} time(s)")
    assert on_disk.count("second") == 0, "some sentences kept the later wording"
    assert on_disk.count("first") == MANY, "not every sentence came back"


def test_the_edit_write_takes_the_same_snapshot(client: TestClient, project) -> None:
    """`/edit` takes `since` for the same reason `/restore` does.

    A change card only exists inside one reading. An edit against a card the
    steward is looking at in a snapshot has to name that snapshot, or the
    server looks for it in a reading it was never in and refuses.
    """
    client.post(f"{BASE}/vision/read")
    _, whole = read(client)
    oldest = whole["history"][-1]["sha"]
    _, back = read(client, since=oldest)
    card = next(c for c in back["changes"] if "console" in (c["now"] or ""))

    blind = client.post(f"{BASE}/vision/changes/{card['id']}/edit", json={"text": "Whatever."})
    print(f"\nedit with no snapshot named -> {blind.status_code} {blind.json().get('error')}")
    assert blind.status_code == 404, "a card from a snapshot was found in a reading it is not in"

    named = client.post(
        f"{BASE}/vision/changes/{card['id']}/edit",
        json={"text": "The console is the place the work happens.", "since": oldest},
    )
    print(f"edit naming the snapshot   -> {named.status_code} {named.json().get('said')}")
    assert named.status_code == 200 and named.json()["ok"], named.json()
    assert "The console is the place the work happens." in project["vision"].read_text(encoding="utf-8")


# --------------------------------------------------------------------------
# converge-8r5 — a lock refusal reaches the steward under its own cause
# --------------------------------------------------------------------------


def test_the_lock_route_refuses_by_name_for_every_real_reason(client: TestClient, project) -> None:
    """The four sentences the toast now carries, read from the server itself.

    This is the half `sendLock` reports rather than invents. Each refusal is a
    whole sentence naming what is actually wrong — which is why passing it
    through untouched is worth more than any wording this app could put on top
    of it.
    """
    said = {}

    answer = client.post(f"{BASE}/locked/lock", json={"conditions": FOUR})
    said["already locked"] = answer.json()["error"]
    assert answer.status_code == 400

    answer = client.post(f"{BASE}/demo/lock", json={"conditions": FOUR[:2]})
    said["fewer than four conditions"] = answer.json()["error"]
    assert answer.status_code == 400

    project["demo"].write_text(
        project["demo"].read_text(encoding="utf-8") + "\n2. An uncommitted line.\n", encoding="utf-8"
    )
    answer = client.post(f"{BASE}/demo/lock", json={"conditions": FOUR})
    said["uncommitted changes"] = answer.json()["error"]
    assert answer.status_code == 400
    _git(project["repo"], "checkout", "--", "contracts/demo.v1.md")

    headless = project["repo"] / "contracts" / "nohead.v1.md"
    headless.write_text("No heading at all, just this line.\n", encoding="utf-8")
    _git(project["repo"], "add", "-A")
    _git(project["repo"], "commit", "-q", "-m", "a document with no H1")
    answer = client.post(f"{BASE}/nohead/lock", json={"conditions": FOUR})
    said["no H1"] = answer.json()["error"]
    assert answer.status_code == 400

    print("\nwhat the lock route refuses, in its own words:")
    for why, sentence in said.items():
        print(f"  · {why}:\n      {sentence}")
    assert "FROZEN" in said["already locked"], (
        f"the refusal does not name the locking word: {said['already locked']!r}"
    )
    for why, sentence in said.items():
        assert len(sentence.split()) >= 6, f"{why} refused in too few words to act on: {sentence!r}"


def test_the_lock_toast_carries_the_servers_sentence_and_no_cause_of_its_own() -> None:
    """converge-8r5, at the one line that was wrong.

    `sendLock`'s catch used to assert a cause — "this app answers no lock route
    yet … Filed as converge-eci" — that was false the moment converge-eci
    landed, and it reached the steward instead of the real reason sitting in
    `err.message`. The catch reports; it no longer diagnoses.
    """
    text = ACTIONS_JS.read_text(encoding="utf-8")
    head, _, tail = text.partition("export async function sendLock(")
    body = tail.split("\nfunction readImage(")[0]
    assert body, "sendLock is no longer in actions.js"
    said = [line.strip() for line in body.splitlines() if "toast(" in line]
    print("\nwhat sendLock tells a steward:")
    for line in said:
        print(f"  {line}")

    # Comments are stripped first. A comment explaining what the sentence used
    # to be is not a sentence anybody reads on a screen, and a test that could
    # not tell those apart would forbid recording why the change was made.
    catch = _uncommented(body.partition("} catch (err) {")[2])
    assert "${err.message}" in catch, (
        "the catch no longer carries the server's own refusal to the steward"
    )
    assert "no lock route" not in catch, (
        "the catch still claims the app answers no lock route; it has answered one since converge-eci"
    )
    assert "converge-eci" not in catch, (
        "the catch still names converge-eci as the reason nothing was locked"
    )
    # The success path is untouched and still reports the document locked.
    assert "res && res.locked ? `Locked: ${res.locked}`" in body, (
        "a successful lock no longer reports the document locked"
    )


def test_no_surface_in_this_app_still_says_the_lock_route_is_missing() -> None:
    """The sentence is gone from every screen, not just from one catch."""
    offenders = []
    for one in sorted((HERE / "static" / "js").rglob("*.js")) + sorted((HERE / "templates").glob("*.html")):
        for number, line in enumerate(_uncommented(one.read_text(encoding="utf-8")).splitlines(), start=1):
            if "no lock route" in line:
                offenders.append(f"{one.relative_to(HERE)}: {line.strip()}")
    print(f"\nsurfaces still claiming the lock route is missing: {offenders or 'none'}")
    assert not offenders, offenders


# --------------------------------------------------------------------------
# converge-4pq — what the screen says, now that the limit is gone
# --------------------------------------------------------------------------


def test_the_history_panel_no_longer_says_an_older_snapshot_is_out_of_reach() -> None:
    """The honest sentence has to go the moment it stops being true.

    `app/tests/test_direction_polish.py::test_the_history_panel_still_says_what_a_restore_cannot_reach`
    pinned that sentence while converge-4pq was open, and said in its own
    docstring that it is the test to rewrite when the route lands. It is not
    this lane's file — the brief names the files this lane may edit and that is
    not one of them — so it is handed to its owner rather than edited here, and
    this test is the replacement standing in the meantime.
    """
    render = DIRECTION_JS.read_text(encoding="utf-8")
    head, _, tail = render.partition("function reachSaid(")
    body = _uncommented(tail.split("\nexport function renderHistory")[0])
    assert "function restorePanel(" in body, "the restore panel is no longer in render/direction.js"
    assert "older than your read point is not offered" not in body, (
        "the panel still says an older snapshot is out of reach; the route reaches one now"
    )
    assert "converge-4pq" not in body, "the panel still names converge-4pq as an open gap"

    #: What replaced it has to be true of the code, not just cheerful.
    assert "restoreReading()" in body, "the panel is not built from the snapshot's own reading"
    assert "openSnapshot()" in body, "the panel does not know whether a snapshot is open"
    said = [line.strip() for line in body.splitlines() if "since=" in line]
    print("\nwhat the History panel tells a steward today:")
    for line in said:
        print(f"  {line[:240]}")
    assert said, "the panel does not say how an older snapshot is reached"


def test_the_browser_carries_the_snapshot_into_every_write_that_needs_it() -> None:
    """A control with no route behind it is the failure this pair exists to avoid.

    So the wiring is checked at both ends: `api.js` puts the sha on the wire,
    and `actions.js` takes it from the reading the steward is looking at rather
    than from anywhere else.
    """
    api = API_JS.read_text(encoding="utf-8")
    actions = ACTIONS_JS.read_text(encoding="utf-8")
    render = DIRECTION_JS.read_text(encoding="utf-8")

    assert "?since=${encodeURIComponent(since)}" in api, "the document read cannot name a snapshot"
    assert re.search(r"restoreChange: \(mid, repoId, docId, changeId, since", api), (
        "the restore write cannot name a snapshot"
    )
    assert re.search(r"editChange: \(mid, repoId, docId, changeId, text, since", api), (
        "the edit write cannot name a snapshot"
    )
    assert "api.restoreChange(state.managerId, state.repoId, state.docId, card.id, since)" in actions, (
        "the restore loop does not carry the snapshot into its writes"
    )
    assert "data-history-sha" in render, "a History row does not carry the commit it stands for"
    assert "selectSnapshot(" in render, "picking a History row reads nothing back"
    print("\nsnapshot wiring: api.js ?since= · restoreChange(since) · editChange(since) "
          "· data-history-sha · selectSnapshot()")


# --------------------------------------------------------------------------
# availability of a real browser
# --------------------------------------------------------------------------


def _playwright_reason() -> str:
    if shutil.which("git") is None:
        return "git is not installed"
    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:  # pragma: no cover - environment dependent
        return f"playwright is not importable: {exc}"
    try:
        with sync_playwright() as p:
            one = p.chromium.launch(args=["--no-sandbox"])
            one.close()
    except Exception as exc:  # pragma: no cover - environment dependent
        return f"chromium is not launchable: {str(exc).splitlines()[0]}"
    return ""


PLAYWRIGHT_SKIP = _playwright_reason()

needs_browser = pytest.mark.skipif(
    bool(PLAYWRIGHT_SKIP),
    reason=f"{PLAYWRIGHT_SKIP}; use MANUAL_PROCEDURE in this file instead",
)


def _free_port() -> int:
    s = socketlib.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


@pytest.fixture
def server(project):
    import uvicorn

    made = serve.create_app(
        config_path=project["config"], secret_path=project["secret"], state_path=project["state"]
    )
    port = _free_port()
    config = uvicorn.Config(made, host="127.0.0.1", port=port, log_level="warning")
    uv_server = uvicorn.Server(config)
    thread = threading.Thread(target=uv_server.run, daemon=True)
    thread.start()
    deadline = time.time() + 20
    while not uv_server.started and time.time() < deadline:
        time.sleep(0.05)
    assert uv_server.started, "app server did not start"
    print(f"\napp server: http://127.0.0.1:{port} (in-process, torn down with this test)")
    yield f"http://127.0.0.1:{port}"
    uv_server.should_exit = True
    thread.join(timeout=10)


@pytest.fixture(scope="module")
def browser():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        b = p.chromium.launch(args=["--no-sandbox"])
        yield b
        b.close()


def _boot(browser, server, project, width=1280, height=800):
    sessions = auth.Sessions(auth.read_or_make_secret(project["secret"]))
    ctx = browser.new_context(viewport={"width": width, "height": height})
    ctx.add_cookies([{"name": auth.COOKIE, "value": sessions.issue(USER),
                      "domain": "127.0.0.1", "path": "/"}])
    page = ctx.new_page()
    errors: list[str] = []
    page.on("console", lambda m: errors.append(f"console.{m.type}: {m.text}") if m.type == "error" else None)
    page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
    page.goto(server, wait_until="networkidle")
    page.wait_for_selector("#documentModeContent", timeout=15000)
    if width < 980:
        # Below the breakpoint the Manager Console is a sheet over the page, so
        # it sits on top of the document tree. Closing it is what a steward
        # reading on a phone does.
        page.click("#consoleToggle")
        page.wait_for_timeout(500)
    return ctx, page, errors


def _open_doc(page, title: str) -> None:
    page.click(f'.repo-doc:has-text("{title}")')
    page.wait_for_selector("#documentModeContent .since-banner, #documentModeContent section", timeout=10000)
    page.wait_for_timeout(400)


def _mode(page, name: str) -> None:
    page.click(f'[data-doc-mode="{name}"]')
    page.wait_for_timeout(400)


def _toast(page) -> str:
    return page.eval_on_selector("#toast", "el => el.textContent || ''")


def _panel(page) -> str:
    return page.eval_on_selector(".history-snapshot .history-actions", "el => el.innerText || ''")


# --------------------------------------------------------------------------
# converge-4pq — in a real browser
# --------------------------------------------------------------------------


@needs_browser
def test_picking_an_older_row_restores_the_wording_that_stood_there(server, project, browser):
    """The acceptance, driven the way a steward drives it.

    Mark all as read first, so the read point is the current version: from
    there the old path could reach nothing at all, and anything that comes back
    came back through the snapshot.
    """
    ctx, page, errors = _boot(browser, server, project)
    _open_doc(page, "Vision")
    _mode(page, "changes")
    page.click('[data-change-all="read"]')
    page.wait_for_timeout(700)
    _mode(page, "history")

    rows = page.eval_on_selector_all(
        "[data-history]",
        "els => els.map(e => ({id: e.dataset.history, sha: e.dataset.historySha, text: e.innerText.trim()}))",
    )
    print("\nHistory rows offered:")
    for row in rows:
        print(f"  · {row['id']:<10} {row['sha']}  {row['text'][:40].replace(chr(10), ' / ')}")
    assert len(rows) >= 3, f"the fixture did not make enough history: {rows}"

    at_read_point = _panel(page)
    print(f"\nwith 'Current' selected the panel says:\n{at_read_point.strip()[:300]}")

    page.click(f'[data-history="{rows[-1]["id"]}"]')
    page.wait_for_timeout(900)
    at_snapshot = _panel(page)
    print(f"\nwith the oldest row selected it says:\n{at_snapshot.strip()[:400]}")
    assert rows[-1]["sha"][:7] in at_snapshot, (
        "the panel does not say it is putting wording back as it stood at that commit"
    )
    assert "converge-4pq" not in at_snapshot, "the panel still names the gap as open"

    scopes = page.eval_on_selector_all("[data-restore]", "els => els.map(e => e.dataset.restore)")
    print(f"scopes offered against that snapshot: {sorted(set(scopes))}")
    for wanted in ("wording", "paragraph", "section", "document"):
        assert wanted in scopes, f"§6's `{wanted}` scope is not offered against a snapshot: {scopes}"

    labels = page.eval_on_selector_all(
        '[data-restore="wording"]', "els => els.map(e => e.innerText.trim())")
    print(f"wordings restorable from here: {labels}")
    console = next((i for i, one in enumerate(labels) if "console" in one), None)
    assert console is not None, f"the console sentence is not restorable from this snapshot: {labels}"

    page.eval_on_selector_all(
        '[data-restore="wording"]', f"els => els[{console}].click()")
    page.wait_for_selector("#dialogActions button.primary-button", timeout=5000)
    dialog = page.eval_on_selector("#dialogContent", "el => el.innerText || ''")
    print(f"\nthe confirmation says:\n{dialog.strip()[:300]}")
    page.click("#dialogActions button.primary-button")
    page.wait_for_function(
        "() => /put back|refus/i.test(document.getElementById('toast').textContent || '')",
        timeout=15000,
    )
    print(f"toast: {_toast(page)}")

    on_disk = project["vision"].read_text(encoding="utf-8")
    print("the document on disk now says:")
    for line in on_disk.splitlines():
        if "console" in line:
            print(f"  {line}")
    assert "The console is a tab you visit when something breaks." in on_disk, (
        "the wording that came back is not the one that stood at the snapshot the steward picked"
    )
    assert not errors, f"the page reported errors: {errors}"
    ctx.close()


@needs_browser
def test_a_snapshot_the_server_refuses_is_reported_in_the_servers_words(server, project, browser):
    """A control that reaches nothing must say what refused, not guess.

    The row's sha is rewritten in the DOM to a commit this document never had —
    the browser's own idea of what is reachable is bypassed entirely — and what
    the steward reads is the server's sentence, unedited.
    """
    ctx, page, errors = _boot(browser, server, project)
    _open_doc(page, "Vision")
    _mode(page, "history")
    rows = page.eval_on_selector_all("[data-history]", "els => els.map(e => e.dataset.history)")
    page.eval_on_selector(
        f'[data-history="{rows[-1]}"]', "el => { el.dataset.historySha = 'deadbeefcafe'; }")
    page.click(f'[data-history="{rows[-1]}"]')
    page.wait_for_timeout(1200)
    said = _panel(page)
    print(f"\nthe panel says:\n{said.strip()[:400]}")
    assert "not a commit in this document's history" in said, (
        "the panel invented a cause instead of carrying the server's refusal"
    )
    assert "Nothing has been written" in said, "the panel does not say the document is untouched"
    # The 400 IS the finding here, so it is the one console error this expects.
    unexpected = [e for e in errors if "400" not in e]
    assert not unexpected, f"the page logged errors beyond the expected 400: {unexpected}"
    ctx.close()


#: What is measured, and what is deliberately not.
#:
#: The page itself must not scroll sideways, and nothing in the restore panel
#: may sit past the panel's own right edge. The snapshot LIST is excluded from
#: the second measure on purpose: below 980 `app/static/css/direction.css`
#: turns `.history-list` into `display:flex; overflow:auto` with 150px items,
#: so a row extending past the viewport inside its own scroller is the design
#: rather than a defect — and a check that could not tell those apart would
#: report the strip as broken every time a document gained a fourth commit.
PANEL_FIT = """
() => {
  const de = document.documentElement;
  const panel = document.querySelector('.history-snapshot');
  if (!panel) return {scrollWidth: de.scrollWidth, clientWidth: de.clientWidth, past: ['no panel']};
  const edge = panel.getBoundingClientRect().right;
  const past = [];
  panel.querySelectorAll('*').forEach(el => {
    const s = getComputedStyle(el);
    if (s.display === 'none' || s.visibility === 'hidden') return;
    const r = el.getBoundingClientRect();
    if (r.width && r.right > edge + 0.5) {
      past.push(((el.id ? '#' + el.id : '') + '.' + String(el.className || el.tagName)).slice(0, 50)
                + ' right=' + Math.round(r.right) + ' panel=' + Math.round(edge));
    }
  });
  return {scrollWidth: de.scrollWidth, clientWidth: de.clientWidth, past: past.slice(0, 6)};
}
"""


@needs_browser
@pytest.mark.parametrize("width,height", [(1280, 800), (390, 844)])
def test_the_snapshot_panel_holds_at_both_widths(server, project, browser, width, height):
    """§6 at 1280 and at 390 — the same four scopes, and nothing past the edge."""
    ctx, page, errors = _boot(browser, server, project, width=width, height=height)
    _open_doc(page, "Vision")
    _mode(page, "history")
    rows = page.eval_on_selector_all("[data-history]", "els => els.map(e => e.dataset.history)")
    page.click(f'[data-history="{rows[-1]}"]')
    page.wait_for_timeout(900)

    scopes = page.eval_on_selector_all("[data-restore]", "els => els.map(e => e.dataset.restore)")
    said = _panel(page)
    print(f"\nat {width} the snapshot offers: {sorted(set(scopes))}")
    print(f"at {width} the panel says: {said.strip()[:220]}")
    for wanted in ("wording", "paragraph", "section", "document"):
        assert wanted in scopes, f"`{wanted}` is missing at {width}: {scopes}"

    measured = page.evaluate(PANEL_FIT)
    print(f"{width}: scrollWidth={measured['scrollWidth']} clientWidth={measured['clientWidth']} "
          f"· past the panel's edge: {measured['past'] or 'nothing'}")
    assert measured["scrollWidth"] <= measured["clientWidth"], (
        f"History pushes the page sideways at {width}: {measured}"
    )
    assert not measured["past"], (
        f"the restore panel spills past its own right edge at {width}: {measured['past']}"
    )
    assert not errors, f"the page reported errors: {errors}"
    ctx.close()


# --------------------------------------------------------------------------
# converge-8r5 — in a real browser
# --------------------------------------------------------------------------


def _open_gate(page) -> None:
    """`#lockGate` is a `<details>`; its boxes have no box on screen until it is
    open, and a checkbox that is not visible cannot be ticked."""
    if not page.evaluate("() => document.getElementById('lockGate').open"):
        page.click("#lockGate summary")
        page.wait_for_timeout(150)


@needs_browser
def test_a_forced_lock_on_an_already_locked_document_names_the_locking_word(
    server, project, browser
):
    """converge-8r5's acceptance, driven as the race it actually is.

    The steward opens a DRAFT the ledger watches and answers the three
    conditions only a reader can answer, so the control goes live. Between that
    and their click, the document is locked out of band — which is precisely
    the case §11's server-side count exists for, and precisely the case whose
    refusal was reaching them as "this app answers no lock route yet".
    """
    ctx, page, errors = _boot(browser, server, project)
    _open_doc(page, "Race")
    _open_gate(page)
    for key in ("means", "example", "steward"):
        page.check(f'[data-lock-check="{key}"]')
        page.wait_for_timeout(80)
    live = page.evaluate(
        """() => ({count: document.getElementById('lockGateCount').textContent,
                   disabled: document.getElementById('lockButton').disabled})"""
    )
    print(f"\n[gate] {live['count']} · control disabled={live['disabled']}")
    assert live["disabled"] is False, f"the control never went live: {live}"

    # Locked underneath the browser, which still believes it is a draft.
    text = project["race"].read_text(encoding="utf-8").replace("(DRAFT)", "(FROZEN 2026-09-04)", 1)
    project["race"].write_text(text, encoding="utf-8")
    _git(project["repo"], "commit", "-qam", "race: locked out of band")
    print(f"[race] the document's H1 is now: {text.splitlines()[0]}")
    before = project["race"].read_text(encoding="utf-8")

    page.click("#lockButton")
    page.wait_for_selector("#dialogActions button:has-text('Lock it')", timeout=5000)
    page.click("#dialogActions button:has-text('Lock it')")
    page.wait_for_function(
        "() => /lock/i.test(document.getElementById('toast').textContent || '')", timeout=15000
    )
    toast = _toast(page)
    print(f"[lock] toast: {toast}")

    assert "Nothing was locked" in toast, f"the refusal was swallowed: {toast!r}"
    assert "FROZEN" in toast, f"the toast does not carry the locking word the server named: {toast!r}"
    assert "already law" in toast, (
        f"the toast does not carry the server's own sentence: {toast!r}"
    )
    assert "no lock route" not in toast, (
        f"the toast still claims the app answers no lock route: {toast!r}"
    )
    assert "converge-eci" not in toast, f"the toast still names converge-eci: {toast!r}"
    assert project["race"].read_text(encoding="utf-8") == before, "the document changed on disk"
    unexpected = [e for e in errors if "400" not in e]
    assert not unexpected, f"the page logged errors beyond the expected 400: {unexpected}"
    ctx.close()


@needs_browser
def test_a_lock_that_succeeds_still_reports_the_document_locked(server, project, browser):
    """The other half of the acceptance: the success path is untouched."""
    ctx, page, errors = _boot(browser, server, project)
    _open_doc(page, "Demo")
    _open_gate(page)
    for key in ("means", "example", "steward"):
        page.check(f'[data-lock-check="{key}"]')
        page.wait_for_timeout(80)
    page.click("#lockButton")
    page.wait_for_selector("#dialogActions button:has-text('Lock it')", timeout=5000)
    page.click("#dialogActions button:has-text('Lock it')")
    page.wait_for_function(
        "() => /lock/i.test(document.getElementById('toast').textContent || '')", timeout=15000
    )
    toast = _toast(page)
    print(f"\n[lock] toast: {toast}")
    assert "Locked" in toast and "Nothing was locked" not in toast, (
        f"a successful lock did not report the document locked: {toast!r}"
    )
    heading = project["demo"].read_text(encoding="utf-8").splitlines()[0]
    subject = _git(project["repo"], "log", "-1", "--format=%s").strip()
    print(f"[lock] the H1 now reads: {heading}")
    print(f"[lock] committed as: {subject}")
    assert "FROZEN" in heading, f"the document was not stamped: {heading!r}"
    assert not errors, f"the page reported errors: {errors}"
    ctx.close()
