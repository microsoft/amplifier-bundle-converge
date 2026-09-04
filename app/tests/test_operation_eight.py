"""The whole operation, in view — read off a rendered page at 1280 and 390.

`surface.v1` Core 9 named eight things that must be on one page:

| # | surface.v1 Core 9's words                                | now judged by            |
|---|----------------------------------------------------------|--------------------------|
| 1 | lanes running against lanes intended, with the fill control | experience-operation Core 6 |
| 2 | truly ready against waiting on you                        | Core 7                   |
| 3 | the plan in order, with reasons                           | Core 2                   |
| 4 | each lane's state and evidence, with drill-in             | Core 8 (and Core 9)      |
| 5 | your limits                                              | Core 1 and Core 11       |
| 6 | the feedback drop                                        | Core 10                  |
| 7 | every manager session you run, with "tell all"           | Core 13                  |
| 8 | stopping something is never a board button               | Core 12                  |

`surface.v1` is superseded by the experience family, and its kit judges the
retired server-rendered app in `src/amplifier_converge/web/`, not this one. So
the eight are asserted here against the clauses that now own them, on the body
that now carries them — the companion app.

Why a browser, and not a kit
---------------------------
`conformance/experience-operation/run.py` says so itself: "It cannot judge a
rendered layout." It reads the served shell, the operation payload and the
client source. Every one of the defects this file pins was invisible to that
reading and visible on a screen:

* the lanes gauge read "N of M **working**" — Core 8's word for ONE lane's
  state, used for Core 6's count of lanes RUNNING. A Quiet lane is running
  just the same, so the heading said something the reading does not support;
* the fill control was offered whether or not any lane was short, so it
  offered to fill lanes that were all carrying work;
* a lane's evidence was the single line "3 commits" — a claim, and Core 8 asks
  for the opposite: "Underneath sits what the lane actually produced, so a
  claim can be inspected rather than believed." A number cannot be inspected.
  Measured before this file: **zero** `details` folds in the whole view;
* the feedback control lives in the shell's top bar, and the shell's phone
  rules do not draw it: measured at 390, `#feedbackButton` computed to
  `display:none`. On a phone the Operation page offered no way to say what
  you saw at all;
* the manager sessions were listed in the shell's rail but not on this page.

Falsity conditions are stated beside each assertion. Where one needs the world
to be different — a board with nothing short — the world is changed through
the app's own reading (`.width` on disk) and the page re-read, rather than the
assertion being softened.

If Playwright or its Chromium build is unavailable the browser tests skip with
the reason printed, and MANUAL_PROCEDURE below is the documented manual check
that stands in for it.
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

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app import auth, data, serve  # noqa: E402

USER = "tester"

#: experience.v1 Core 6, quoted by experience-operation.v1 Core 8 — the only
#: words a LANE at work may be shown in.
LANE_WORDS = {"Working", "Quiet", "Silent — may have died"}

#: Core 12 — "Stopping something is never a board button."
STOP_WORDS = re.compile(r"\b(stop|kill|abort|terminate|halt)\b", re.IGNORECASE)

MANUAL_PROCEDURE = """
MANUAL PROCEDURE — run this by hand if Playwright is unavailable.
Each step says what you must SEE; seeing anything else is a failure.

Setup
  uv run --extra app python -m app.serve --host 127.0.0.1 --port 8788
  Open http://127.0.0.1:8788/ sized to exactly 1280 CSS px wide, click
  "Operation", and repeat every step at 390 x 844.

1. Lanes running against lanes intended (Core 6)
   SEE: a heading reading "<n> of <m> lanes running".
   FAILS IF: it reads "<n> of <m> working" — that is Core 8's word for one
   lane's state, not Core 6's count of lanes running.
   SEE: a "Fill lanes" control, and a line saying how many lanes are not
   carrying work — only while n < m.
   FAILS IF: the control is offered when n == m.

2. Truly ready against waiting on you (Core 7)
   SEE: both phrases, each with a number under it, above the lanes.

3. The plan in order, with reasons (Core 2)
   SEE: the waves, in order, each with a sentence saying what it is for or
   the words "Not recorded"; and, below them, why the plan was redrawn.
   FAILS IF: a wave is headed by its own lane names.

4. Each lane's state and evidence, with drill-in (Core 8, Core 9)
   SEE: on every live lane card, a pill reading Working, Quiet, or
   "Silent — may have died"; a "Watch session" control; and a fold reading
   "What this lane produced".
   Open the fold on a lane with commits.
   SEE: the commit subjects themselves, each naming where it was read from.
   FAILS IF: the fold repeats the count, or is absent.

5. Your limits (Core 1, Core 11)
   SEE: above any list of work — the objective, "Hard limit", "Lane budget",
   "Lanes active", and a "Steer" control.

6. The feedback drop (Core 10)
   SEE: on the page itself, a "Drop feedback" box with a text area and a send
   control — at 1280 AND at 390.
   Type a sentence and send it.
   SEE: a dated file under <repo>/.converge/feedback/ containing it.

7. Every manager session you run, with tell-all (Core 13)
   SEE: every configured manager session listed on this page, the one needing
   you most first, and one "Tell all manager sessions" control.

8. Stopping is never a board button (Core 12)
   SEE: no control anywhere on the page reading Stop, Kill, Abort, Terminate
   or Halt.

9. Nothing widens the page
   In the console run:
     document.documentElement.scrollWidth + ' vs ' + document.documentElement.clientWidth
   SEE: the two numbers equal, at 1280 x 800 and again at 390 x 844.
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

Deadline: when the eight are in view

## Outcome

Put the whole operation on one page. Nothing on the board stops anything.

## Weave-in log

- 2026-09-01T10:00:00Z W1 launched on owner word "go": prove the sign-in path
  before anything is built on top of it.
- 2026-09-02T09:00:00Z REOPENED on owner word: the contract changed under us,
  so wave 1 is redrawn.
"""

RETURN_LOG = """# Owner return log

## 2026-09-03 — where things stand

The sign-in path is real and was re-checked on the merged result. One lane is
blocked because the signing key is not on this host. Nothing else waits on your
word. The plan was redrawn once and the reason is on record.
"""

MANIFEST_HEAD = "lane\tworktree\tbranch\tbase\ttmux\tgoal\tlog\tstarted\n"

LANES = ("w1-alpha", "w1-bravo", "w1-charlie", "w1-delta")

#: The two commits the alpha lane really makes. Core 8's fold must show these
#: sentences themselves, not the number two.
ALPHA_COMMITS = (
    "alpha: the first thing this lane actually produced",
    "alpha: the second thing this lane actually produced",
)

#: What a work queue would answer with. The queue is a live service on the
#: machine, not a fixture of this repository; what is under test is the
#: reading, so the reading is given numbers.
COUNTS = {"TOTAL": 76, "READY": 8, "BLOCKED": 3, "RESOLVED": 57}

#: What needs a person, per manager session. Core 13 sorts on this, so the two
#: sessions are given different answers and the order is asserted.
NEEDS = {"demo": 1, "other": 4}


def _git(repo: Path, *args: str) -> str:
    done = subprocess.run(
        ["git", "-c", "user.name=Test", "-c", "user.email=test@example.invalid", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    return done.stdout


@pytest.fixture(scope="module")
def project(tmp_path_factory) -> dict:
    tmp_path = tmp_path_factory.mktemp("operation-eight")
    repo = tmp_path / "demo-repo"
    (repo / "docs" / "workflow").mkdir(parents=True)
    (repo / "docs" / "VISION.md").write_text(VISION, encoding="utf-8")
    (repo / "docs" / "workflow" / "OWNER-RETURN-LOG.md").write_text(RETURN_LOG, encoding="utf-8")
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "seed: the vision and the return log")

    # A real branch with real commits, so Core 8's fold has real things to
    # open onto rather than a fixture list.
    _git(repo, "checkout", "-q", "-b", "lane/w1-alpha")
    for index, subject in enumerate(ALPHA_COMMITS):
        (repo / f"alpha-{index}.md").write_text(f"{subject}\n", encoding="utf-8")
        _git(repo, "add", "-A")
        _git(repo, "commit", "-q", "-m", subject)
    _git(repo, "checkout", "-q", "main")

    other = tmp_path / "other-repo"
    other.mkdir()
    (other / "README.md").write_text("# Other\n", encoding="utf-8")
    _git(other, "init", "-q", "-b", "main")
    _git(other, "add", "-A")
    _git(other, "commit", "-q", "-m", "seed")

    batch = tmp_path / "hw-demo"
    (batch / "goals").mkdir(parents=True)
    (batch / "HIGHWAY.md").write_text(HIGHWAY, encoding="utf-8")
    (batch / ".width").write_text("4\n", encoding="utf-8")
    for name in LANES:
        (batch / "lanes" / name).mkdir(parents=True)
        (batch / "lanes" / name / "lane.log").write_text("working\n", encoding="utf-8")
        (batch / "goals" / f"{name}.md").write_text(f"# Lane {name} — the {name} thing\n", encoding="utf-8")
    (batch / "lanes" / "w1-charlie" / "DONE.json").write_text(
        json.dumps({"status": "success", "summary": "Charlie landed the thing it went for."}),
        encoding="utf-8",
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

    other_batch = tmp_path / "hw-other"
    other_batch.mkdir()
    (other_batch / "HIGHWAY.md").write_text("# Highway — other\n\nWidth 1.\n", encoding="utf-8")
    (other_batch / ".width").write_text("1\n", encoding="utf-8")

    conf = tmp_path / "converge-app.toml"
    conf.write_text(
        "[[managers]]\n"
        'id = "demo"\n'
        'name = "Demo manager"\n'
        f'batch_dir = "{batch}"\n'
        f'repos = ["{repo}"]\n'
        'tracker_project = "demo-project"\n'
        'tmux_socket = "test-socket-that-does-not-exist"\n'
        "\n"
        "[[managers]]\n"
        'id = "other"\n'
        'name = "Other manager"\n'
        f'batch_dir = "{other_batch}"\n'
        f'repos = ["{other}"]\n'
        'tracker_project = "other-project"\n'
        'tmux_socket = "test-socket-that-does-not-exist"\n',
        encoding="utf-8",
    )
    # Never the real ~/.amplifier: a test must not move a steward's read point.
    return {
        "config": conf,
        "secret": tmp_path / "secret",
        "state": tmp_path / "state.json",
        "batch": batch,
        "repo": repo,
    }


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
    # Three seams, every one of them a fact about this MACHINE rather than
    # about the page: which terminal sessions are alive, what the work queue
    # would answer, and what is waiting on a person. Everything the page shows
    # below is read from the files and the git history stood up above.
    patch.setattr(data, "tmux_sessions", lambda socket: {"hw__hw-demo__w1-alpha", "hw__hw-demo__w1-bravo"})
    patch.setattr(data, "tracker_counts", lambda mc: dict(COUNTS))
    patch.setattr(
        data,
        "_needs_items",
        lambda mc: [{"kind": "work", "title": f"{mc.id} item {n}", "where": {}, "since": ""}
                    for n in range(NEEDS.get(mc.id, 0))],
    )

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
  return {scrollWidth: de.scrollWidth, clientWidth: de.clientWidth};
}
"""

#: Every control a steward can press inside the Operation view, by its label.
CONTROL_LABELS = """
() => Array.from(document.querySelectorAll('#operationView button, #operationView input[type=submit]'))
        .map(el => (el.textContent || el.value || '').trim()).filter(Boolean)
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
    page.wait_for_selector("#operationTab", timeout=20000)
    page.click("#operationTab")
    page.wait_for_selector("#operationView:not(.hidden)", timeout=20000)
    page.wait_for_selector("#lanesGrid .lane-status", timeout=20000)
    return ctx, page


def _shown(page, selector: str) -> bool:
    """Visible to an eye: drawn, and with a box bigger than nothing."""
    return page.eval_on_selector(
        selector,
        """el => {
             const s = getComputedStyle(el);
             const r = el.getBoundingClientRect();
             return s.display !== 'none' && s.visibility !== 'hidden' && r.width > 0 && r.height > 0;
           }""",
    ) if page.query_selector(selector) else False


WIDTHS = [(1280, 900), (390, 844)]


# --------------------------------------------------------------------------
# 1 of 8 — lanes running against lanes intended, with the fill control (Core 6)
# --------------------------------------------------------------------------


@needs_browser
@pytest.mark.parametrize("width,height", WIDTHS)
def test_the_gauge_counts_lanes_running_and_never_says_working(
    server, project, browser, width, height
) -> None:
    """Falsity condition — the heading this replaces read "2 of 4 working".

    "Working" is one lane's state (Core 8); a Quiet lane is running just the
    same. If the heading says `working` again, this fails.
    """
    errors: list[str] = []
    ctx, page = _open_operation(browser, server, project, width, height, errors)

    heading = page.inner_text(".lanes-card h2").strip()
    print(f"\n[{width}] lanes gauge: {heading!r}")
    assert re.fullmatch(r"\d+ of \d+ lanes running", heading), heading
    assert "working" not in heading.lower(), (
        "the gauge counts lanes RUNNING (Core 6); Working is Core 8's word for one lane's state"
    )
    assert heading.startswith("2 of 4"), f"two sessions are alive and four lanes were asked for: {heading}"
    assert not errors, "; ".join(errors[:3])
    ctx.close()


@needs_browser
def test_the_fill_control_is_offered_exactly_when_a_lane_is_short(server, project, browser) -> None:
    """Both halves of Core 6's promise, driven through the app's own reading.

    Falsity condition — before this, the control was drawn whether or not any
    lane was short. The second half below sets `.width` on disk to the number
    of lanes actually running and re-reads the page; if the control is still
    offered there, the board is offering to fill lanes that are all carrying
    work, and this fails.
    """
    errors: list[str] = []
    ctx, page = _open_operation(browser, project and server, project, 1280, 900, errors)

    assert _shown(page, "#fillLanesButton"), "two of four lanes are short and no fill is offered"
    note = page.inner_text("#fillNote").strip()
    print(f"\n[short] fill note: {note!r}")
    assert "2 lanes" in note and "not carrying work" in note, note

    width_file = Path(project["batch"]) / ".width"
    before = width_file.read_text(encoding="utf-8")
    try:
        width_file.write_text("2\n", encoding="utf-8")
        page.reload(wait_until="networkidle")
        page.wait_for_selector("#operationTab", timeout=20000)
        page.click("#operationTab")
        page.wait_for_selector("#operationView:not(.hidden)", timeout=20000)
        page.wait_for_selector("#lanesGrid .lane-status", timeout=20000)
        heading = page.inner_text(".lanes-card h2").strip()
        note = page.inner_text("#fillNote").strip()
        print(f"[full ] gauge: {heading!r}  fill note: {note!r}")
        assert heading.startswith("2 of 2"), heading
        assert not _shown(page, "#fillLanesButton"), (
            "every lane asked for is carrying work, and the board still offers to fill them"
        )
        assert note == "Every lane you asked for is carrying work.", note
    finally:
        width_file.write_text(before, encoding="utf-8")
    assert not errors, "; ".join(errors[:3])
    ctx.close()


# --------------------------------------------------------------------------
# 2 of 8 — truly ready against waiting on you (Core 7)
# --------------------------------------------------------------------------


@needs_browser
@pytest.mark.parametrize("width,height", WIDTHS)
def test_both_queue_numbers_stand_together_above_the_lanes(
    server, project, browser, width, height
) -> None:
    """Falsity condition — either phrase missing, or either number not read."""
    errors: list[str] = []
    ctx, page = _open_operation(browser, server, project, width, height, errors)

    strip = page.inner_text("#queueStrip")
    print(f"\n[{width}] queue strip: {strip!r}")
    assert "Truly ready" in strip and "Waiting on you" in strip
    assert page.inner_text("#trulyReadyCount").strip() == "8", "the queue answered READY 8"
    assert page.inner_text("#waitingOnYouCount").strip() == "1", "one thing waits on this steward"
    assert not errors, "; ".join(errors[:3])
    ctx.close()


# --------------------------------------------------------------------------
# 3 of 8 — the plan in order, with reasons (Core 2)
# --------------------------------------------------------------------------


@needs_browser
@pytest.mark.parametrize("width,height", WIDTHS)
def test_the_plan_is_shown_in_order_and_every_grouping_carries_a_reason(
    server, project, browser, width, height
) -> None:
    """Falsity condition — a wave headed by its own lane names carries no reason.

    The one wave here is named in the weave-in log, so its heading must be
    that sentence; and the redraw the log records must be shown with its why.
    """
    errors: list[str] = []
    ctx, page = _open_operation(browser, server, project, width, height, errors)

    headings = page.eval_on_selector_all("#wavesGrid .wave-card h3", "els => els.map(e => e.textContent.trim())")
    redraws = page.inner_text("#planRedrawList").strip()
    print(f"\n[{width}] wave headings: {headings}")
    print(f"[{width}] redraw: {redraws!r}")
    assert headings, "no wave is on the page at all"
    for one in headings:
        assert one, "a wave carries no reason at all"
        assert "w1-alpha" not in one, "a wave is headed by its own lane names, which is not a reason"
    assert 'prove the sign-in path' in " ".join(headings), headings
    assert "the contract changed under us" in redraws, redraws
    assert not errors, "; ".join(errors[:3])
    ctx.close()


# --------------------------------------------------------------------------
# 4 of 8 — each lane's state and evidence, with drill-in (Core 8, Core 9)
# --------------------------------------------------------------------------


@needs_browser
@pytest.mark.parametrize("width,height", WIDTHS)
def test_every_lane_shows_a_plain_word_and_a_fold_that_opens_onto_what_it_produced(
    server, project, browser, width, height
) -> None:
    """The measured defect: zero folds in the whole view.

    Falsity conditions — (a) if a live lane's pill reads anything but the
    three lane words this fails; (b) if a lane card carries no fold this
    fails; (c) if the fold merely repeats the claim above it — the count —
    rather than the commits themselves, the assertion on ALPHA_COMMITS fails.
    """
    errors: list[str] = []
    ctx, page = _open_operation(browser, server, project, width, height, errors)

    pills = page.eval_on_selector_all("#lanesGrid .lane-status", "els => els.map(e => e.textContent.trim())")
    cards = page.eval_on_selector_all("#lanesGrid .lane-card", "els => els.length")
    folds = page.eval_on_selector_all("#lanesGrid .lane-card details.lane-produced", "els => els.length")
    watch = page.eval_on_selector_all("#lanesGrid .watch-button", "els => els.length")
    print(f"\n[{width}] {cards} live lane(s), pills {pills}, folds {folds}, watch controls {watch}")
    assert cards == 2, "two sessions are alive"
    assert set(pills) <= LANE_WORDS, f"a lane is shown in a word the contract does not fix: {pills}"
    assert folds == cards, "Core 8 asks for evidence you can open, on every lane"
    assert watch == cards, "Core 9 — Watch session opens that worker session's live view"

    page.eval_on_selector_all("#lanesGrid details.lane-produced", "els => els.forEach(e => (e.open = true))")
    opened = page.inner_text("#lane-w1-alpha .lane-produced")
    print(f"[{width}] alpha's fold: {opened!r}")
    for subject in ALPHA_COMMITS:
        assert subject in opened, (
            "the fold must carry what the lane actually produced, not the number of things it produced"
        )
    assert "main..lane/w1-alpha" in opened, "every line says where it was read from"

    # A lane with nothing readable says so, and is never given an empty fold.
    bravo = page.inner_text("#lane-w1-bravo .lane-produced")
    print(f"[{width}] bravo's fold: {bravo!r}")
    assert "Nothing is readable on this lane yet" in bravo, bravo
    assert not errors, "; ".join(errors[:3])
    ctx.close()


@needs_browser
def test_a_lane_that_reported_back_opens_onto_what_it_wrote(server, project, browser) -> None:
    """Charlie finished and Delta stopped; each said why, and each fold shows it."""
    errors: list[str] = []
    ctx, page = _open_operation(browser, server, project, 1280, 900, errors)

    page.eval_on_selector_all("#reportedGrid details.lane-produced", "els => els.forEach(e => (e.open = true))")
    charlie = page.inner_text("#lane-w1-charlie .lane-produced")
    delta = page.inner_text("#lane-w1-delta .lane-produced")
    print(f"\ncharlie's fold: {charlie!r}\ndelta's fold: {delta!r}")
    assert "Charlie landed the thing it went for." in charlie, charlie
    assert "The signing key is not on this host" in delta, delta
    assert not errors, "; ".join(errors[:3])
    ctx.close()


# --------------------------------------------------------------------------
# 5 of 8 — your limits (Core 1, Core 11)
# --------------------------------------------------------------------------


@needs_browser
@pytest.mark.parametrize("width,height", WIDTHS)
def test_the_objective_and_the_limits_stand_above_any_list_of_work(
    server, project, browser, width, height
) -> None:
    """Falsity condition — a limit below the first lane card is not "at the top"."""
    errors: list[str] = []
    ctx, page = _open_operation(browser, server, project, width, height, errors)

    objective = page.inner_text("#opObjectiveText").strip()
    facts = page.inner_text(".strategy-facts")
    print(f"\n[{width}] objective: {objective!r}")
    print(f"[{width}] limits: {facts!r}")
    assert "whole operation on one page" in objective, objective
    for limit in ("Hard limit", "Lane budget", "Lanes active"):
        assert limit in facts, f"the limits do not say {limit}"
    assert page.inner_text("#strategyDeadline").strip() == "when the eight are in view"
    assert _shown(page, "#steerButton"), "Core 11 — steering sets the limits"

    tops = page.evaluate(
        """() => {
             const box = (sel) => {
               const el = document.querySelector(sel);
               return el ? el.getBoundingClientRect().top + window.scrollY : null;
             };
             return {limits: box('.strategy-facts'), work: box('#lanesGrid'), waves: box('#wavesGrid')};
           }"""
    )
    print(f"[{width}] tops: {tops}")
    assert tops["limits"] < tops["waves"] < tops["work"], (
        f"the limits must stand above any list of work: {tops}"
    )
    assert not errors, "; ".join(errors[:3])
    ctx.close()


# --------------------------------------------------------------------------
# 6 of 8 — the feedback drop (Core 10)
# --------------------------------------------------------------------------


@needs_browser
@pytest.mark.parametrize("width,height", WIDTHS)
def test_the_feedback_drop_is_on_the_page_at_both_widths(
    server, project, browser, width, height
) -> None:
    """The measured defect: at 390 the shell's own Feedback control is not drawn.

    Falsity condition — if `#feedback` is absent or computes to display:none
    at either width, a steward on that width has no way to say what they saw.
    """
    errors: list[str] = []
    ctx, page = _open_operation(browser, server, project, width, height, errors)

    assert _shown(page, "#feedback"), "no feedback drop on the Operation page"
    assert _shown(page, "#feedbackDropText"), "the drop has nothing to type into"
    assert _shown(page, "#feedbackDropSend"), "the drop has nothing to press"
    shell_control = _shown(page, "#feedbackButton")
    print(f"\n[{width}] drop on the page: True; the shell's own control: {shell_control}")
    assert not errors, "; ".join(errors[:3])
    ctx.close()


@needs_browser
def test_dropping_feedback_writes_it_where_the_manager_session_reads_it(
    server, project, browser
) -> None:
    """Falsity condition — nothing lands on disk, and the drop is decoration."""
    errors: list[str] = []
    ctx, page = _open_operation(browser, server, project, 1280, 900, errors)

    said = "The lanes gauge and the lane words are two different readings."
    page.fill("#feedbackDropText", said)
    page.click("#feedbackDropSend")
    page.wait_for_timeout(1200)

    folder = Path(project["repo"]) / ".converge" / "feedback"
    written = sorted(folder.glob("*.md")) if folder.is_dir() else []
    print(f"\nfeedback files: {[str(p) for p in written]}")
    assert written, f"nothing was written under {folder}"
    body = written[-1].read_text(encoding="utf-8")
    assert said in body, body
    assert "Operation" in body, "the drop says where the steward was standing"
    assert page.input_value("#feedbackDropText") == "", "the box is cleared once it has been sent"
    assert not errors, "; ".join(errors[:3])
    ctx.close()


# --------------------------------------------------------------------------
# 7 of 8 — every manager session you run, with tell-all (Core 13)
# --------------------------------------------------------------------------


@needs_browser
@pytest.mark.parametrize("width,height", WIDTHS)
def test_every_manager_session_is_listed_on_the_page_sorted_by_which_needs_you(
    server, project, browser, width, height
) -> None:
    """Falsity condition — two sessions are configured and one needs the steward
    four times as much as the other. If the list is missing, short, or in the
    other order, this fails.
    """
    errors: list[str] = []
    ctx, page = _open_operation(browser, server, project, width, height, errors)

    rows = page.eval_on_selector_all(
        "#managersList .manager-row .manager-row-name", "els => els.map(e => e.textContent.trim())"
    )
    counts = page.eval_on_selector_all(
        "#managersList .manager-row .manager-row-needs", "els => els.map(e => e.textContent.trim())"
    )
    print(f"\n[{width}] manager sessions: {rows} · {counts}")
    assert rows == ["Other manager", "Demo manager"], (
        f"every session listed, the one needing you most first: {rows}"
    )
    assert counts == ["needs your word · 4", "needs your word · 1"], counts
    assert _shown(page, "#tellAllButton"), "Core 13 — one message reaches all of them"
    assert not errors, "; ".join(errors[:3])
    ctx.close()


# --------------------------------------------------------------------------
# 8 of 8 — stopping is never a board button (Core 12)
# --------------------------------------------------------------------------


@needs_browser
@pytest.mark.parametrize("width,height", WIDTHS)
def test_no_control_on_the_operation_page_stops_anything(
    server, project, browser, width, height
) -> None:
    """Falsity condition — one control reading Stop / Kill / Abort / Terminate /
    Halt anywhere in the view fails this, whatever it does.
    """
    errors: list[str] = []
    ctx, page = _open_operation(browser, server, project, width, height, errors)

    labels = page.evaluate(CONTROL_LABELS)
    stops = [one for one in labels if STOP_WORDS.search(one)]
    print(f"\n[{width}] {len(labels)} control(s) on the page; stop-shaped: {stops}")
    assert not stops, f"work stops because the objective changed or the steward said so — not here: {stops}"
    assert not errors, "; ".join(errors[:3])
    ctx.close()


# --------------------------------------------------------------------------
# all eight at once, and nothing widened
# --------------------------------------------------------------------------


@needs_browser
@pytest.mark.parametrize("width,height", WIDTHS)
def test_all_eight_are_in_view_on_one_page_and_none_of_it_widens_the_document(
    server, project, browser, width, height
) -> None:
    """One roll-up, in surface.v1 Core 9's own order, on the clauses that own it.

    Falsity condition — any one of the eight absent from the rendered view, or
    a document wider than its own viewport at either width.
    """
    errors: list[str] = []
    ctx, page = _open_operation(browser, server, project, width, height, errors)

    # Read as the eye reads it: `inner_text` returns the RENDERED text, and the
    # small headings on this page are upper-cased by the stylesheet.
    text = page.inner_text("#operationView")
    said = text.lower()
    eight = [
        ("lanes running against lanes intended, with the fill control (Core 6)",
         bool(re.search(r"\d+ of \d+ lanes running", said)) and _shown(page, "#fillLanesButton")),
        ("truly ready against waiting on you (Core 7)",
         "truly ready" in said and "waiting on you" in said),
        ("the plan in order, with reasons (Core 2)",
         page.eval_on_selector_all("#wavesGrid .wave-card h3", "els => els.length") > 0
         and "why the plan was redrawn" in said),
        ("each lane's state and evidence, with drill-in (Core 8, Core 9)",
         page.eval_on_selector_all("#lanesGrid .lane-card details.lane-produced", "els => els.length") > 0
         and page.eval_on_selector_all("#lanesGrid .watch-button", "els => els.length") > 0),
        ("your limits (Core 1, Core 11)",
         "hard limit" in said and "lane budget" in said and _shown(page, "#steerButton")),
        ("the feedback drop (Core 10)", _shown(page, "#feedbackDropText")),
        ("every manager session you run, with tell all (Core 13)",
         page.eval_on_selector_all("#managersList .manager-row", "els => els.length") == 2
         and _shown(page, "#tellAllButton")),
        ("stopping something is never a board button (Core 12)",
         not [one for one in page.evaluate(CONTROL_LABELS) if STOP_WORDS.search(one)]),
    ]
    print(f"\n[{width}] the whole operation in view:")
    for name, ok in eight:
        print(f"   {'PASS' if ok else 'FAIL'}  {name}")
    missing = [name for name, ok in eight if not ok]
    assert not missing, f"{len(missing)} of 8 not in view: {missing}"

    measured = page.evaluate(MEASURE)
    print(f"[{width}] scrollWidth={measured['scrollWidth']} clientWidth={measured['clientWidth']}")
    assert measured["scrollWidth"] <= measured["clientWidth"], (
        f"the operation page widened the document: {measured}"
    )
    assert not errors, "; ".join(errors[:3])
    ctx.close()
