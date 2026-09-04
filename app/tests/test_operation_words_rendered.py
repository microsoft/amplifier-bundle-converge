"""Rendered-browser check: Operation is READ in the words the contract fixes.

`app/tests/test_operation_words.py` proves the payload and the client source.
Neither proves what a steward's eye actually lands on, and that is where the
defect in converge-q66 lived: the payload had `statusLabel` all along, and the
surface rendered the raw `status` beside it, so 42 lanes on the running app
read `done` — a WORK word — where `experience-operation.v1` Core 8 fixes three
LANE words.

So this drives a real Chromium against the real app and reads the pills, the
headings and the numbers off the page, at 1280 and at 390:

* every pill in the lanes-at-work grid says Working, Quiet, or
  Silent — may have died, and nothing else;
* the lanes that reported back sit under their own heading, in the work words;
* both of Core 7's numbers are on the page;
* the fifth flow measure (stuck) is on the page;
* Core 11's fifth limit and Core 13's one-message-to-all are real controls —
  clicking them through writes the ask where the manager session reads it;
* and none of it widens the page at either width.

If Playwright or its Chromium build is unavailable the browser tests skip with
the reason printed, and MANUAL_PROCEDURE below is the documented manual check
that stands in for it.
"""

from __future__ import annotations

import json
import shutil
import socket as socketlib
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app import auth, data, serve  # noqa: E402

USER = "tester"

LANE_WORDS = {"Working", "Quiet", "Silent — may have died"}
WORK_WORDS = {"Done", "Stuck"}

MANUAL_PROCEDURE = """
MANUAL PROCEDURE — run this by hand if Playwright is unavailable.
Each step says what you must SEE; seeing anything else is a failure.

Setup
  uv run --extra app python -m app.serve --host 127.0.0.1 --port 8788
  Open http://127.0.0.1:8788/ sized to exactly 1280 CSS px wide, and click
  the "Operation" tab.

Check — every lane at work is read in a lane word
  a. SEE: under "Live lanes", every pill reads one of exactly three things:
     "Working", "Quiet", or "Silent — may have died".
  FAILS IF: any pill in that grid reads "Done", "Stuck", "done" or "stuck",
     or any other word.

Check — the lanes that reported back are shown apart, in the work words
  b. SEE: below the live lanes, a heading "Reported back" reading
     "<n> finished · <m> stopped", and under it cards whose pills read
     "Done" or "Stuck".
  FAILS IF: finished lanes are missing from the page altogether, or their
     word appears on a card in the live-lanes grid above.

Check — Core 7's two numbers
  c. SEE: above the lanes, "Truly ready" and "Waiting on you", each with a
     number under it.
  FAILS IF: either is absent.

Check — the fifth flow measure
  d. SEE: in the "Flow today" card, a "Stuck" figure beside Derived,
     Resolved, Verified and Reopened.
  FAILS IF: only four measures are shown.

Check — the two asks are real
  e. Click "Have the manager session review this", type a sentence, click
     "Ask for a review".
  f. SEE: the batch's HIGHWAY.md gains a "## Weave-in log" line containing
     "review this: <your sentence>".
  g. Click "Tell all manager sessions", type a sentence, click "Tell them all".
  h. SEE: a dated file under <repo>/.converge/feedback/ containing it.
  FAILS IF: either control does nothing, or nothing lands on disk.

Check — nothing widens the page
  i. In the devtools console run:
       document.documentElement.scrollWidth + ' vs ' + document.documentElement.clientWidth
  j. SEE: the two numbers are equal, at 1280 x 800 and again at 390 x 844.
  FAILS IF: scrollWidth is larger, or the page scrolls sideways.
"""


# --------------------------------------------------------------------------
# availability
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
    reason=f"{PLAYWRIGHT_SKIP}; use MANUAL_PROCEDURE in this file instead",
)


# --------------------------------------------------------------------------
# a project to serve, and the real app serving it
# --------------------------------------------------------------------------

VISION = """# Demo Vision (DRAFT)

## Where this is going

One place for direction and one place for operation.
"""

HIGHWAY = """# Highway — demo

Width 4.
"""

MANIFEST_HEAD = "lane\tworktree\tbranch\tbase\ttmux\tgoal\tlog\tstarted\n"

LANES = ("w1-alpha", "w1-bravo", "w1-charlie", "w1-delta")

#: The counts a work queue would answer with. The queue itself is a live
#: service on the machine, not a fixture of this repository — what is under
#: test here is the reading of the numbers, so the reading is given numbers.
COUNTS = {"TOTAL": 76, "READY": 8, "BLOCKED": 3, "RESOLVED": 57}


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "user.name=Test", "-c", "user.email=test@example.invalid", *args],
        cwd=repo,
        check=True,
        capture_output=True,
    )


@pytest.fixture(scope="module")
def project(tmp_path_factory) -> dict:
    tmp_path = tmp_path_factory.mktemp("operation-words")
    repo = tmp_path / "demo-repo"
    (repo / "docs").mkdir(parents=True)
    (repo / "docs" / "VISION.md").write_text(VISION, encoding="utf-8")
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "seed: the vision")

    batch = tmp_path / "hw-demo"
    (batch / "goals").mkdir(parents=True)
    (batch / "HIGHWAY.md").write_text(HIGHWAY, encoding="utf-8")
    (batch / ".width").write_text("4\n", encoding="utf-8")
    for name in LANES:
        (batch / "lanes" / name).mkdir(parents=True)
        (batch / "lanes" / name / "lane.log").write_text("working\n", encoding="utf-8")
        (batch / "goals" / f"{name}.md").write_text(f"# Lane {name} — the {name} thing\n", encoding="utf-8")
    (batch / "lanes" / "w1-charlie" / "DONE.json").write_text(
        json.dumps({"status": "success", "summary": "Charlie landed."}), encoding="utf-8"
    )
    (batch / "lanes" / "w1-delta" / "BLOCKED.md").write_text(
        "# Lane w1-delta — BLOCKED\n\n**Outcome:** B) BLOCKED. The signing key is not on this host.\n",
        encoding="utf-8",
    )
    (batch / "manifest.tsv").write_text(
        MANIFEST_HEAD
        + "".join(
            f"{name}\t{batch}/lanes/{name}/demo-repo\tlane/{name}\tdeadbee\thw__hw-demo__{name}\t"
            f"{batch}/goals/{name}.md\t{batch}/lanes/{name}/lane.log\t2026-09-01T10:00:00Z\n"
            for name in LANES
        ),
        encoding="utf-8",
    )

    conf = tmp_path / "converge-app.toml"
    conf.write_text(
        "[[managers]]\n"
        'id = "demo"\n'
        'name = "Demo manager"\n'
        f'batch_dir = "{batch}"\n'
        f'repos = ["{repo}"]\n'
        'tracker_project = "demo-project"\n'
        'tmux_socket = "test-socket-that-does-not-exist"\n',
        encoding="utf-8",
    )
    # Never the real ~/.amplifier: a test must not move a steward's read point.
    return {"config": conf, "secret": tmp_path / "secret", "state": tmp_path / "state.json",
            "batch": batch, "repo": repo}


def _free_port() -> int:
    s = socketlib.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


@pytest.fixture(scope="module")
def server(project):
    import uvicorn

    patch = pytest.MonkeyPatch()
    # Two seams, both facts about this machine rather than about the words:
    # which tmux sessions are alive, and what the work queue would answer.
    patch.setattr(data, "tmux_sessions", lambda socket: {"hw__hw-demo__w1-alpha"})
    patch.setattr(data, "tracker_counts", lambda mc: dict(COUNTS))

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
    print(f"\napp server: http://127.0.0.1:{port} (in-process, torn down with this test module)")
    yield f"http://127.0.0.1:{port}"
    uv_server.should_exit = True
    thread.join(timeout=10)
    patch.undo()


@pytest.fixture(scope="module")
def browser():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        b = p.chromium.launch(args=["--no-sandbox"])
        yield b
        b.close()


MEASURE = """
() => {
  const de = document.documentElement;
  const rows = [];
  document.querySelectorAll('body, body *').forEach(el => {
    const s = getComputedStyle(el);
    if (s.display === 'none' || s.visibility === 'hidden') return;
    const r = el.getBoundingClientRect();
    if (r.right > de.clientWidth + 0.01) {
      rows.push(((el.id ? '#' + el.id : '') + '.' + String(el.className || el.tagName)).slice(0, 50)
                + ' right=' + Math.round(r.right));
    }
  });
  return {scrollWidth: de.scrollWidth, clientWidth: de.clientWidth, past: rows.slice(0, 8)};
}
"""


def _open_operation(browser, server, project, width: int, height: int, errors: list[str]):
    sessions = auth.Sessions(auth.read_or_make_secret(project["secret"]))
    ctx = browser.new_context(viewport={"width": width, "height": height})
    ctx.add_cookies([{"name": auth.COOKIE, "value": sessions.issue(USER),
                      "domain": "127.0.0.1", "path": "/"}])
    page = ctx.new_page()
    page.on("console", lambda m: errors.append(f"console.{m.type}: {m.text}") if m.type == "error" else None)
    page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
    page.goto(server, wait_until="networkidle")
    page.wait_for_selector("#operationTab", timeout=15000)
    page.click("#operationTab")
    page.wait_for_selector("#lanesGrid .lane-status", timeout=15000)
    return ctx, page


def _texts(page, selector: str) -> list[str]:
    return page.eval_on_selector_all(selector, "els => els.map(e => e.textContent.trim())")


# --------------------------------------------------------------------------
# 1. the words, read off the page
# --------------------------------------------------------------------------


@needs_browser
@pytest.mark.parametrize("width,height", [(1280, 800), (390, 844)])
def test_the_page_reads_lanes_in_lane_words_and_reports_the_rest_apart(
    server, project, browser, width, height
) -> None:
    errors: list[str] = []
    ctx, page = _open_operation(browser, server, project, width, height, errors)

    at_work = _texts(page, "#lanesGrid .lane-status")
    reported = _texts(page, "#reportedGrid .lane-status")
    heading = page.inner_text("#reportedHeading").strip()
    print(f"\n[{width}] lanes at work: {at_work}")
    print(f"[{width}] reported back: {reported} under {heading!r}")

    assert at_work, "no lane is shown at all"
    assert set(at_work) <= LANE_WORDS, (
        f"a lane at work is shown in a word the contract does not fix: {sorted(set(at_work) - LANE_WORDS)}"
    )
    assert "Working" in at_work and "Silent — may have died" in at_work
    assert set(reported) == WORK_WORDS, f"the reported lanes read {sorted(set(reported))}"
    assert "1 finished" in heading and "1 stopped" in heading

    measured = page.evaluate(MEASURE)
    print(f"[{width}] scrollWidth={measured['scrollWidth']} clientWidth={measured['clientWidth']}")
    if measured["past"]:
        print(f"[{width}] boxes past the right edge (diagnostic only): {measured['past']}")
    assert measured["scrollWidth"] <= measured["clientWidth"], (
        f"the operation page widened the document: {measured}"
    )
    assert not errors, "; ".join(errors[:3])
    ctx.close()


@needs_browser
@pytest.mark.parametrize("width,height", [(1280, 800), (390, 844)])
def test_the_page_shows_both_queue_numbers_and_all_five_flow_measures(
    server, project, browser, width, height
) -> None:
    errors: list[str] = []
    ctx, page = _open_operation(browser, server, project, width, height, errors)

    strip = page.inner_text("#queueStrip")
    flow = page.inner_text(".throughput-stats")
    print(f"\n[{width}] queue strip: {strip!r}")
    print(f"[{width}] flow card: {flow!r}")

    assert "Truly ready" in strip and "Waiting on you" in strip
    assert page.inner_text("#trulyReadyCount").strip() == "8"
    for measure in ("Derived", "Resolved", "Verified", "Reopened", "Stuck"):
        assert measure in flow, f"the flow card never says {measure}"
    assert page.inner_text("#throughputStuck").strip() == "3"
    assert not errors, "; ".join(errors[:3])
    ctx.close()


# --------------------------------------------------------------------------
# 2. the two asks, clicked through to what they write
# --------------------------------------------------------------------------


@needs_browser
def test_asking_for_a_review_writes_the_ask_where_the_manager_reads_it(server, project, browser) -> None:
    errors: list[str] = []
    ctx, page = _open_operation(browser, server, project, 1280, 800, errors)

    page.click("#reviewThisButton")
    page.wait_for_selector("#reviewNote", timeout=5000)
    page.fill("#reviewNote", "the lane words on this page")
    page.click("#dialogActions button:has-text('Ask for a review')")
    page.wait_for_timeout(800)

    weave = (project["batch"] / "HIGHWAY.md").read_text(encoding="utf-8")
    print(f"\nHIGHWAY.md after the ask:\n{weave}")
    assert "## Weave-in log" in weave
    assert "review this: the lane words on this page" in weave
    assert not errors, "; ".join(errors[:3])
    ctx.close()


@needs_browser
def test_telling_all_sessions_reaches_every_manager_session(server, project, browser) -> None:
    errors: list[str] = []
    ctx, page = _open_operation(browser, server, project, 1280, 800, errors)

    page.click("#tellAllButton")
    page.wait_for_selector("#tellAllText", timeout=5000)
    page.fill("#tellAllText", "hold new work until the release lands")
    page.click("#dialogActions button:has-text('Tell them all')")
    page.wait_for_timeout(1200)

    folder = project["repo"] / ".converge" / "feedback"
    files = sorted(folder.glob("*.md")) if folder.is_dir() else []
    print(f"\nfeedback files written: {[f.name for f in files]}")
    assert files, "telling every manager session wrote nothing at all"
    said = files[-1].read_text(encoding="utf-8")
    print(said)
    assert "hold new work until the release lands" in said
    assert "told with every manager session" in said
    assert not errors, "; ".join(errors[:3])
    ctx.close()


# --------------------------------------------------------------------------
# what runs when the browser cannot
# --------------------------------------------------------------------------


def test_manual_procedure_is_documented() -> None:
    assert "FAILS IF" in MANUAL_PROCEDURE
    assert "1280" in MANUAL_PROCEDURE and "390" in MANUAL_PROCEDURE
    assert "Silent — may have died" in MANUAL_PROCEDURE
    if PLAYWRIGHT_SKIP:
        print(f"\nPlaywright unavailable ({PLAYWRIGHT_SKIP}). Manual procedure:\n{MANUAL_PROCEDURE}")


if __name__ == "__main__":  # pragma: no cover
    print(MANUAL_PROCEDURE)
