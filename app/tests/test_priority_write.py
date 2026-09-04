"""The fifth write, and the door the host knocks on.

Two work items, one file, because they touch the same two lines of
`app/serve.py` and would otherwise be asserted twice.

* **`converge-a5g`** - `experience.v1` Core 4 names five writes and the app
  offered four. There was no `priority` route in its own `/openapi.json`, no
  control on any surface, and nothing in `app/writes.py` that would order the
  queue; rule 4a of `conformance/experience/run.py` FAILed on exactly that.
* **`converge-7cs`** - `experience-collaboration.v1` Core 6 asks for webhooks
  where the host offers them. `POST /api/collab/webhooks/host` existed and
  worked, but every `/api/` path sat behind the sign-in gate and a repository
  host carries no `cv_session` cookie, so the host could never reach its own
  webhook and polling was what actually kept the surface fresh.

What is real here, and what stands in
-------------------------------------
Everything on the Converge side is real: a real app built by `app/serve.py`, a
real cookie gate, a real batch directory, and `app/writes.py` appending to a
real `HIGHWAY.md` on disk. The assertions read the file back rather than
trusting the response.

Two things stand in, both facts about this machine rather than about what the
app says: PAM (a sign-in must not need a real account) and the work queue's own
command line (a test must not depend on a live tracker, nor on what happens to
be in it today). `test_the_queue_reading_is_the_queues_own_answer` exercises the
real `data.queue_items` against a stubbed command, so the parsing is proved
rather than assumed.

**No test here writes to a real batch.** Every `HIGHWAY.md` is under `tmp_path`.
A priority call against `~/dev/hw-converge` would append to the highway a live
run is reading.

MANUAL PROCEDURE (when playwright is not installed)
---------------------------------------------------
Check - the control is where the queue is read
  a. Open the app, sign in, go to Operation.
  b. SEE a card "Work queue - Raise or lower a priority", above the
     "Truly ready / Waiting on you" numbers.
  c. SEE one row per queued item, or a sentence saying why the queue could not
     be read. Never an empty list with no sentence.
  d. Press Raise on a row, write a note, confirm. SEE a toast quoting the line
     that was written.
  e. Reload. SEE the call under "Priority calls on the record".
  f. Open the card's Details. SEE the same write said as a sentence for the
     Manager Console.
  FAILS IF: the card is missing, a press writes nothing, or the recorded call
     does not come back after a reload.

Check - nothing widens the page
  g. At 1280x800 and again at 390x844, with the fold open, in the console run:
       document.documentElement.scrollWidth + ' vs ' + document.documentElement.clientWidth
  h. SEE the two numbers are equal.
  FAILS IF: scrollWidth is larger, or the page scrolls sideways.
"""

from __future__ import annotations

import json
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

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from app import auth, collab, data, serve, writes  # noqa: E402

#: `data.queue_items` as it really is, held before the autouse fixture below
#: replaces it. Without this the one test that exercises the real reading would
#: silently exercise the stub instead and assert nothing.
REAL_QUEUE_ITEMS = data.queue_items

GOOD_USER = "tester"
GOOD_PASSWORD = "correct-horse"
MANAGER = "demo"
SECRET = "a-shared-secret-only-the-host-has"

#: Core 4's five, and the word each one would be in the app's own route table.
#: The same table `conformance/experience/run.py` reads, written out here so a
#: route quietly renamed fails in this file too.
FIVE_WRITES = (
    ("answer with a word", "decision"),
    ("raise or lower a priority", "priority"),
    ("drop feedback", "feedback"),
    ("steer", "steer"),
    ("ask for a proposal", "ask"),
)

HIGHWAY = """# Highway - demo

Width 4.

## Weave-in log
- 2026-09-04T06:00:00Z launched wave 8
"""

#: What the stand-in work queue answers. Two rows and a total larger than
#: either, so "the front of the queue" is provably a slice and not the whole.
QUEUE_ANSWER = {
    "project": "demo-project",
    "items": [
        {"id": "demo-aaa", "title": "The first thing in the queue"},
        {"id": "demo-bbb", "title": "The second thing in the queue"},
    ],
    "returned_count": 2,
    "total_count": 17,
}


# --------------------------------------------------------------------------
# a batch, a repository, and an app around them
# --------------------------------------------------------------------------
def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "user.name=Test", "-c", "user.email=test@example.invalid", *args],
        cwd=repo,
        check=True,
        capture_output=True,
    )


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
    (batch / "HIGHWAY.md").write_text(HIGHWAY, encoding="utf-8")
    (batch / ".width").write_text("4\n", encoding="utf-8")
    (batch / "manifest.tsv").write_text("lane\tworktree\tbranch\n", encoding="utf-8")

    conf = tmp_path / "converge-app.toml"
    conf.write_text(
        "[[managers]]\n"
        f'id = "{MANAGER}"\n'
        'name = "Demo manager"\n'
        f'batch_dir = "{batch}"\n'
        f'repos = ["{repo}"]\n'
        'tracker_project = "demo-project"\n'
        'tmux_socket = "priority-socket-that-does-not-exist"\n',
        encoding="utf-8",
    )
    # Never the real ~/.amplifier: a test must not move a steward's read point,
    # and never a real batch: a priority call would land in a live highway.
    return {
        "repo": repo,
        "batch": batch,
        "highway": batch / "HIGHWAY.md",
        "config": conf,
        "secret": tmp_path / "secret",
        "state": tmp_path / "state.json",
        "webhook_secret": tmp_path / "webhook-secret",
    }


class _FakePam:
    def authenticate(self, username: str, password: str, service: str = "login") -> bool:
        return username == GOOD_USER and password == GOOD_PASSWORD


@pytest.fixture(autouse=True)
def _quiet_machine(monkeypatch, project):
    """The two seams that are facts about this machine, not about the app."""
    monkeypatch.setattr(data, "tmux_sessions", lambda socket: set())
    monkeypatch.setattr(data, "tracker_counts", lambda mc: {"TOTAL": 17, "READY": 4})
    monkeypatch.setattr(data, "queue_items", lambda mc, limit=data.QUEUE_SHOWN: {
        "available": True,
        "items": list(QUEUE_ANSWER["items"]),
        "total": QUEUE_ANSWER["total_count"],
        "project": "demo-project",
        "why": "",
    })
    monkeypatch.setattr(collab, "SECRET_PATH", project["webhook_secret"])
    collab.ARRIVALS.__init__()
    yield
    collab.ARRIVALS.__init__()


def build_app(project: dict):
    return serve.create_app(
        config_path=project["config"], secret_path=project["secret"], state_path=project["state"]
    )


@pytest.fixture
def client(project, monkeypatch) -> TestClient:
    """Signed in, the way a steward is."""
    monkeypatch.setattr(auth.pam_module, "pam", _FakePam)
    made = TestClient(build_app(project), follow_redirects=False)
    answer = made.post("/login", data={"username": GOOD_USER, "password": GOOD_PASSWORD, "next": "/"})
    assert answer.status_code == 302 and auth.COOKIE in answer.cookies
    return made


@pytest.fixture
def guest(project) -> TestClient:
    """Carrying no cookie at all - what a repository host looks like."""
    return TestClient(build_app(project), follow_redirects=False)


def write_routes(client: TestClient) -> list[str]:
    paths = client.get("/openapi.json").json().get("paths") or {}
    return sorted(p for p, ops in paths.items() if any(m.upper() == "POST" for m in ops))


def tail(path: str) -> str:
    """`/api/managers/{mid}/priority` -> `priority`, as the kit reads it."""
    parts = [p for p in path.strip("/").split("/") if not p.startswith("{")]
    return parts[-1] if parts else ""


def calls_on_record(project: dict) -> list[str]:
    return [
        line for line in project["highway"].read_text(encoding="utf-8").splitlines()
        if "priority (" in line
    ]


# --------------------------------------------------------------------------
# converge-a5g - the fifth write exists
# --------------------------------------------------------------------------
def test_the_app_declares_a_route_for_each_of_the_five_writes(client) -> None:
    """Rule 4a's own question, asked of the app's own route table."""
    routes = write_routes(client)
    tails = {tail(r) for r in routes}
    print("\nPOST routes the app declares:")
    for route in routes:
        print(f"  {route}")

    missing = [f"{name} (`{token}`)" for name, token in FIVE_WRITES if token not in tails]
    assert not missing, f"the app declares no route for {missing}"
    assert "/api/managers/{mid}/priority" in routes, (
        "the priority write is not at the path the surface and the kit both expect"
    )


def test_raising_a_priority_writes_one_attributed_line_where_the_run_is_ordered(
    client, project
) -> None:
    """The write is real: the assertion reads the file, not the response."""
    before = project["highway"].read_text(encoding="utf-8")
    answer = client.post(
        f"/api/managers/{MANAGER}/priority",
        json={
            "item": "converge-a5g",
            "direction": "raise",
            "title": "The fifth write is absent",
            "note": "rule 4a is the last thing failing",
        },
    )
    assert answer.status_code == 200, answer.text
    body = answer.json()
    after = project["highway"].read_text(encoding="utf-8")
    print(f"\nthe line written: {body['line']}")

    assert body["ok"] is True
    assert body["direction"] == "raise" and body["item"] == "converge-a5g"
    assert after != before, "the response said ok and the file did not change"
    assert body["line"] in after, "the line the answer quoted is not the line on disk"

    # Attributed, and carrying the note `surface.v1` clause 3 asks travel with
    # the call - not a second message about it.
    written = calls_on_record(project)
    assert len(written) == 1, written
    assert GOOD_USER in written[0], "the call does not say who made it"
    assert "raise converge-a5g" in written[0]
    assert "rule 4a is the last thing failing" in written[0], "the note did not travel"

    # And it does not claim to have moved a number it never touched.
    assert body["queueNumberUntouched"] is True
    assert "no verb that sets one" in body["queueNote"]


def test_lowering_is_the_same_write_in_the_other_direction(client, project) -> None:
    answer = client.post(
        f"/api/managers/{MANAGER}/priority",
        json={"item": "converge-9zz", "direction": "lower", "note": "can wait a wave"},
    )
    assert answer.status_code == 200, answer.text
    assert answer.json()["direction"] == "lower"
    written = calls_on_record(project)
    print(f"\nthe line written: {written[0]}")
    assert "lower converge-9zz" in written[0]


def test_nothing_is_appended_when_the_call_is_refused(client, project) -> None:
    """A refusal is in words, and leaves the record exactly as it was."""
    before = project["highway"].read_text(encoding="utf-8")
    refused = [
        ({"item": "converge-a5g", "direction": "sideways"}, "raised or lowered"),
        ({"item": "converge-a5g", "direction": ""}, "raised or lowered"),
        ({"item": "converge-a5g"}, "raised or lowered"),
        ({"direction": "raise"}, "name the item"),
        ({"item": "   ", "direction": "raise"}, "name the item"),
    ]
    print()
    for payload, expected in refused:
        answer = client.post(f"/api/managers/{MANAGER}/priority", json=payload)
        said = answer.json().get("error", "")
        print(f"  {payload} -> {answer.status_code} {said}")
        assert answer.status_code == 400, f"{payload} was not refused"
        assert expected in said, f"{payload} was refused without saying why: {said!r}"

    assert project["highway"].read_text(encoding="utf-8") == before, (
        "a refused call still changed the record"
    )

    # Two directions and no more. A third word would be a third ordering, and
    # the refusals above are only honest while this stays two.
    assert writes.PRIORITY_DIRECTIONS == ("raise", "lower"), writes.PRIORITY_DIRECTIONS


def test_an_unknown_manager_session_is_refused_by_name(client) -> None:
    answer = client.post("/api/managers/nobody/priority", json={"item": "x", "direction": "raise"})
    assert answer.status_code == 404
    assert "nobody" in answer.json()["error"]


def test_a_priority_call_needs_the_sign_in_like_every_other_write(guest) -> None:
    """The webhook is the ONE public write. This is not it."""
    answer = guest.post(f"/api/managers/{MANAGER}/priority", json={"item": "x", "direction": "raise"})
    assert answer.status_code == 401, answer.text


# --------------------------------------------------------------------------
# converge-a5g - and it lands where a steward can see it
# --------------------------------------------------------------------------
def test_the_call_comes_back_on_the_surface_that_made_it(client, project) -> None:
    """Read back out of the same log it was written into - no second store."""
    client.post(
        f"/api/managers/{MANAGER}/priority",
        json={"item": "converge-a5g", "direction": "raise", "note": "blocks the kit"},
    )
    client.post(
        f"/api/managers/{MANAGER}/priority",
        json={"item": "converge-9zz", "direction": "lower"},
    )
    payload = client.get(f"/api/managers/{MANAGER}/operation").json()
    recorded = payload["priorityCalls"]
    print(f"\ncalls read back: {recorded}")

    assert len(recorded) == 2
    # Newest first, so the most recent call is the one a steward sees.
    assert recorded[0]["item"] == "converge-9zz" and recorded[0]["direction"] == "lower"
    assert recorded[1]["item"] == "converge-a5g" and recorded[1]["direction"] == "raise"
    assert recorded[1]["who"] == GOOD_USER
    assert "blocks the kit" in recorded[1]["said"]

    # A call with no title and no note reads back with a clean id, not with the
    # separator stuck to it.
    assert recorded[0]["item"] == "converge-9zz", "the id carries punctuation from the line"


def test_the_surface_offers_the_front_of_the_queue_to_reorder(client) -> None:
    payload = client.get(f"/api/managers/{MANAGER}/operation").json()
    queue = payload["queueItems"]
    print(f"\nqueue offered: {queue}")
    assert queue["available"] is True
    assert [row["id"] for row in queue["items"]] == ["demo-aaa", "demo-bbb"]
    assert queue["total"] == 17, "the surface cannot say 2 of 17 without the 17"


def test_the_queue_reading_is_the_queues_own_answer(monkeypatch, project) -> None:
    """`data.queue_items` for real, against a stand-in command line.

    The autouse fixture replaces this function everywhere else, so without this
    test the parsing would never run at all.
    """
    from app.config import ManagerConfig

    seen: list[list[str]] = []

    def fake_run(args, cwd=None, timeout=8.0):
        seen.append(list(args))
        return json.dumps(QUEUE_ANSWER)

    monkeypatch.setattr(data, "run", fake_run)
    mc = ManagerConfig(id=MANAGER, name="Demo", batch_dir=project["batch"], tracker_project="demo-project")
    read = REAL_QUEUE_ITEMS(mc, limit=2)
    print(f"\nasked: {seen[0]}")
    print(f"read:  {read}")

    assert seen[0][:2] == ["amplifier-work-tracker", "list"], "the queue was asked with something else"
    assert "--json" in seen[0], "the answer was parsed out of prose rather than asked for as JSON"
    assert read["available"] is True
    assert [row["id"] for row in read["items"]] == ["demo-aaa", "demo-bbb"]
    assert read["total"] == 17

    # A queue that does not answer says so. It never returns an empty list,
    # which would read as "the queue is empty".
    monkeypatch.setattr(data, "run", lambda *a, **k: "")
    silent = REAL_QUEUE_ITEMS(mc)
    assert silent["available"] is False and silent["items"] == []
    assert "did not answer" in silent["why"]

    # Nor does a manager with no queue at all.
    none = REAL_QUEUE_ITEMS(ManagerConfig(id="x", name="x"))
    assert none["available"] is False and "no work queue" in none["why"]


def test_the_control_names_the_manager_session_operation_it_stands_for(client) -> None:
    """`experience.v1` Core 8, read off the shell the app actually serves."""
    shell = client.get("/").text
    element = re.search(r"<details[^>]*data-write=\"priority\"[^>]*>", shell)
    print(f"\nthe element: {element.group(0) if element else None}")

    assert element, "no control on any surface names itself as the priority write"
    assert "data-manager-operation=" in element.group(0), (
        "the priority control names no manager-session operation, so a reader cannot "
        "check that what they can do here the manager session can do too"
    )
    # The shell rail already publishes this wording for the same write; the two
    # must not drift (converge-a5g's own scope note).
    assert "raise or lower a priority in the work queue" in element.group(0)


# --------------------------------------------------------------------------
# converge-7cs - the host can reach its own webhook
# --------------------------------------------------------------------------
def test_the_host_reaches_the_webhook_with_the_secret_and_no_cookie(guest, project) -> None:
    project["webhook_secret"].write_text(SECRET + "\n", encoding="utf-8")
    answer = guest.post(
        collab.WEBHOOK_PATH,
        headers={"X-Converge-Secret": SECRET, "X-GitHub-Event": "pull_request"},
        json={"repoId": "demo-repo", "note": "a pull request was opened"},
    )
    print(f"\nno cookie, right secret -> {answer.status_code}")
    assert answer.status_code == 200, answer.text
    body = answer.json()
    assert body["ok"] is True

    # And the surface's freshness sentence names the webhook, which is the whole
    # point of the door being reachable.
    said = body["freshness"]
    print(f"freshness now: {said['words']}")
    assert said["mechanism"] == "webhook"
    assert "webhook" in said["words"].lower()


def test_a_call_without_the_secret_is_refused_though_the_path_is_public(guest, project) -> None:
    """Public is not open. The secret is what stands in for the cookie."""
    project["webhook_secret"].write_text(SECRET + "\n", encoding="utf-8")
    for headers, why in (
        ({"X-Converge-Secret": "not-the-secret"}, "a wrong secret"),
        ({}, "no secret at all"),
    ):
        answer = guest.post(collab.WEBHOOK_PATH, headers=headers, json={})
        print(f"\n{why} -> {answer.status_code} {answer.json().get('reason')}")
        assert answer.status_code == 403, f"{why} was accepted"
        assert "shared secret" in answer.json()["reason"]


def test_with_no_secret_file_the_route_refuses_rather_than_trusting_the_caller(guest, project) -> None:
    assert not project["webhook_secret"].exists()
    answer = guest.post(collab.WEBHOOK_PATH, headers={"X-Converge-Secret": SECRET}, json={})
    print(f"\nno secret file -> {answer.status_code} {answer.json().get('reason')}")
    assert answer.status_code == 503, answer.text
    assert "no shared secret is set" in answer.json()["reason"]


def test_no_other_route_became_reachable_without_a_cookie(guest, client) -> None:
    """The blast radius of opening one path, measured rather than argued.

    Every route the app declares is called with no cookie. Exactly three may
    answer: the sign-in page, the health check, and the webhook - and the
    webhook only reaches its own refusal, which is the secret check doing the
    job the cookie was doing.
    """
    paths = client.get("/openapi.json").json()["paths"]
    answered, gated = [], []
    for path, ops in sorted(paths.items()):
        concrete = re.sub(r"\{[^}]+\}", "demo", path)
        for method in ops:
            verb = method.upper()
            if verb not in ("GET", "POST"):
                continue
            call = guest.get if verb == "GET" else guest.post
            answer = call(concrete) if verb == "GET" else call(concrete, json={})
            row = f"{verb} {path} -> {answer.status_code}"
            (gated if answer.status_code in (401, 302) else answered).append(row)

    print("\nanswered without a cookie:")
    for row in answered:
        print(f"  {row}")
    print(f"gated: {len(gated)}")

    assert sorted(answered) == sorted([
        "POST /api/collab/webhooks/host -> 503",
        "GET /healthz -> 200",
        "GET /login -> 200",
    ]), f"the public surface is not the three it should be: {answered}"


def test_the_public_path_is_matched_whole_and_never_as_a_prefix(guest) -> None:
    """A prefix would have opened everything under the webhook's path."""
    print(f"\nPUBLIC_PATHS = {serve.PUBLIC_PATHS}")
    assert serve.PUBLIC_PATHS == (collab.WEBHOOK_PATH,), (
        "the public-path list is not exactly the one webhook path"
    )
    assert serve._is_public(collab.WEBHOOK_PATH)
    assert not serve._is_public(collab.WEBHOOK_PATH + "/anything")
    assert not serve._is_public("/api/collab/demo/pulls")
    answer = guest.post(collab.WEBHOOK_PATH + "/anything", json={})
    assert answer.status_code == 401, answer.text


def test_the_door_and_the_route_cannot_drift_apart(client) -> None:
    """`app/serve.py` takes the path from `app/collab.py` rather than retyping it."""
    assert collab.WEBHOOK_PATH in write_routes(client), (
        "the path the gate opens is not a route the app answers"
    )


# --------------------------------------------------------------------------
# rendered - the control is on the screen at both widths
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
            browser = p.chromium.launch(args=["--no-sandbox"])
            browser.close()
    except Exception as exc:  # pragma: no cover - environment dependent
        return f"chromium is not launchable: {str(exc).splitlines()[0]}"
    return ""


PLAYWRIGHT_SKIP = _playwright_reason()

needs_browser = pytest.mark.skipif(
    bool(PLAYWRIGHT_SKIP),
    reason=f"{PLAYWRIGHT_SKIP}; use the MANUAL PROCEDURE in this file instead",
)


def _free_port() -> int:
    s = socketlib.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


@pytest.fixture
def served(project):
    """The real app on a real port, for a real browser."""
    import uvicorn

    port = _free_port()
    config = uvicorn.Config(build_app(project), host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.time() + 20
    while not server.started and time.time() < deadline:
        time.sleep(0.05)
    assert server.started, "app server did not start"
    print(f"\napp server: http://127.0.0.1:{port} (torn down with this test)")
    yield f"http://127.0.0.1:{port}"
    server.should_exit = True
    thread.join(timeout=10)


@needs_browser
@pytest.mark.parametrize("width,height", [(1280, 800), (390, 844)])
def test_the_card_is_on_the_screen_at_both_widths(served, project, width, height) -> None:
    from playwright.sync_api import sync_playwright

    cookie = auth.Sessions(auth.read_or_make_secret(project["secret"])).issue(GOOD_USER)
    errors: list[str] = []
    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--no-sandbox"])
        ctx = browser.new_context(viewport={"width": width, "height": height})
        ctx.add_cookies([{
            "name": auth.COOKIE, "value": cookie, "domain": "127.0.0.1",
            "path": "/", "httpOnly": True, "sameSite": "Lax",
        }])
        page = ctx.new_page()
        page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(served, wait_until="networkidle")
        page.wait_for_selector("#operationTab", timeout=15000)
        page.click("#operationTab")
        page.wait_for_selector("#priorityQueue", state="visible", timeout=15000)

        said = page.eval_on_selector("#priorityNote", "el => el.innerText")
        rows = page.eval_on_selector_all("#priorityList [data-raise]", "els => els.length")
        heading = page.eval_on_selector("#priorityQueue h2", "el => el.innerText")
        print(f"\n[{width}] heading: {heading!r}")
        print(f"[{width}] note: {said!r}")
        print(f"[{width}] rows offering a raise: {rows}")

        assert "Raise or lower a priority" in heading
        assert said.strip(), "the card says nothing at all about the queue"
        assert rows >= 1, "the card offers no row to raise or lower"

        # The fold beside the control, which is Core 8 read on the screen.
        page.eval_on_selector("#priorityQueue .op-parity", "el => el.open = true")
        fold = page.eval_on_selector("#priorityQueue .op-parity", "el => el.innerText.replace(/\\s+/g, ' ')")
        print(f"[{width}] the fold reads: {fold}")
        assert "manager console" in fold.lower(), "the fold never names where else this can be said"

        widths = page.evaluate(
            "() => [document.documentElement.scrollWidth, document.documentElement.clientWidth]"
        )
        print(f"[{width}] scrollWidth vs clientWidth: {widths[0]} vs {widths[1]}")
        assert widths[0] <= widths[1], f"[{width}] the page scrolls sideways"
        assert not errors, f"[{width}] the browser logged: {errors}"
        ctx.close()
        browser.close()


@needs_browser
def test_pressing_raise_writes_the_call_and_shows_it_back(served, project) -> None:
    """The whole loop, in a browser: press, write, reload, see it."""
    from playwright.sync_api import sync_playwright

    cookie = auth.Sessions(auth.read_or_make_secret(project["secret"])).issue(GOOD_USER)
    before = calls_on_record(project)
    assert before == []

    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--no-sandbox"])
        ctx = browser.new_context(viewport={"width": 1280, "height": 800})
        ctx.add_cookies([{
            "name": auth.COOKIE, "value": cookie, "domain": "127.0.0.1",
            "path": "/", "httpOnly": True, "sameSite": "Lax",
        }])
        page = ctx.new_page()
        page.goto(served, wait_until="networkidle")
        page.wait_for_selector("#operationTab", timeout=15000)
        page.click("#operationTab")
        page.wait_for_selector("#priorityList [data-raise]", state="visible", timeout=15000)

        page.click("[data-raise='demo-aaa']")
        page.wait_for_selector("#priorityNoteText", state="visible", timeout=10000)
        page.fill("#priorityNoteText", "this one first, it blocks the rest")
        page.click("text=Raise it")
        page.wait_for_timeout(1500)

        written = calls_on_record(project)
        print(f"\nwritten by the browser: {written}")
        assert len(written) == 1, "pressing Raise wrote nothing"
        assert "raise demo-aaa" in written[0]
        assert "this one first, it blocks the rest" in written[0]

        page.reload(wait_until="networkidle")
        page.wait_for_selector("#operationTab", timeout=15000)
        page.click("#operationTab")
        page.wait_for_selector("#priorityCallList", state="visible", timeout=15000)
        page.wait_for_timeout(1000)
        shown = page.eval_on_selector("#priorityCallList", "el => el.innerText.replace(/\\s+/g, ' ')")
        print(f"shown after a reload: {shown}")
        assert "demo-aaa" in shown, "the call was written and never came back on the screen"
        assert "Raised" in shown

        ctx.close()
        browser.close()
