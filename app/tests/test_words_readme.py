"""Two checks that a green suite kept missing, for two different reasons.

**1. The lane's state word, as RENDERED** (`converge-6my`).

`app/data.py` has served each lane a plain word all along -- `Working`,
`Quiet`, `Silent -- may have died` for a lane at work, `Done` or `Stuck` for one
that reported back -- and every existing check agreed it did. The screen did
not: `.lane-status` is styled `text-transform:uppercase`, so a steward read the
machine's screaming form of the word instead. `experience.v1` Core 6 fixes the
title-case word, and that difference is the whole of the clause.

Nothing caught it, and *how* nothing caught it is the point of this file:

* the payload rules read the payload, which was already plain;
* the served-markup rule skips `.css` routes, and the token is never written
  down in the markup anyway -- the browser makes it at render time;
* `app/tests/test_operation_words_rendered.py` drives a real browser but reads
  `textContent`, which is the text **as written**. A CSS transform is invisible
  to it.

So every assertion below reads `innerText` -- the text **as rendered**, with the
transform applied. That is the only reading that can tell `Done` from the
machine's form of it, and swapping it back to `textContent` makes this file
green against the very defect it exists to catch.

**2. The host panel, documented** (`converge-u2y`).

`app/README.md` gives every surface a section saying what is read from where and
what is deliberately not claimed. The sixth surface (`app/collab.py` plus the
`collab.html` partial) arrived without one, because the lane that built it could
not edit `app/README.md`. The second half of this file asserts that section is
there and carries the five things a reader should not have to read the code to
find out.

If Playwright or its Chromium build is unavailable the browser tests skip with
the reason printed, and MANUAL_PROCEDURE below is the documented manual check
that stands in for it. The README checks never need a browser and always run.
"""

from __future__ import annotations

import json
import os
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

REPO_ROOT = Path(__file__).resolve().parents[2]
APP_README = REPO_ROOT / "app" / "README.md"

#: The three words a LANE may be read in, exactly as `experience.v1` Core 6
#: fixes them -- and as `app/data.py`'s `LANE_WORD` serves them.
LANE_WORDS = {"Working", "Quiet", "Silent — may have died"}

#: The two WORK words a lane that has reported back is read in.
WORK_WORDS = {"Done", "Stuck"}

#: Every word either vocabulary allows, which is the whole of what a state pill
#: on this page is permitted to say once the browser has finished with it.
STATE_WORDS = LANE_WORDS | WORK_WORDS

MANUAL_PROCEDURE = """
MANUAL PROCEDURE -- run this by hand if Playwright is unavailable.
Each step says what you must SEE; seeing anything else is a failure.

Setup
  uv run --extra app python -m app.serve --host 127.0.0.1 --port 8788
  Open http://127.0.0.1:8788/ sized to exactly 1280 CSS px wide, and click
  the "Operation" tab. Repeat every step at 390 CSS px wide.

Check -- a lane's state word reaches the eye in its plain form
  a. SEE: every pill on every lane card -- both the live grid and the
     "Reported back" grid below it -- reads one of exactly five things, in
     these letters: "Working", "Quiet", "Silent — may have died", "Done",
     "Stuck".
  FAILS IF: any pill is upper-cased, i.e. reads the same word in capitals.
     Reading it with the eye is the check; the pill is small, so if in doubt
     open devtools and run:

       [...document.querySelectorAll('.lane-status')].map(e => e.innerText)

     innerText, never textContent: textContent is the text as WRITTEN and
     cannot see a CSS transform at all, which is exactly how this defect
     survived a green suite.

Check -- the pill's own style says so
  b. In devtools, select any lane pill and read its computed style.
  c. SEE: text-transform is "none".
  FAILS IF: it is "uppercase".
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

HIGHWAY = """# Highway -- demo

Width 4.
"""

MANIFEST_HEAD = "lane\tworktree\tbranch\tbase\ttmux\tgoal\tlog\tstarted\n"

#: Five lanes chosen to put all five state words on the page at once, because a
#: run that only rendered four of them would not be proving what this file
#: claims to prove. `app/data.py`'s `lane_state` decides each one:
#:
#:   alpha    live session, log touched just now      -> working -> Working
#:   echo     live session, log touched 10 min ago    -> quiet   -> Quiet
#:   bravo    no live session                         -> silent  -> Silent — …
#:   charlie  DONE.json beside it                     -> done    -> Done
#:   delta    BLOCKED.md beside it                    -> stuck   -> Stuck
#:
#: The two live ones are the two the `tmux_sessions` seam is told about below;
#: the boundaries they sit either side of are `WORKING_SECONDS` (5 min) and
#: `QUIET_SECONDS` (25 min).
LANES = ("w1-alpha", "w1-bravo", "w1-charlie", "w1-delta", "w1-echo")

#: Which lanes have a session alive, as far as this run is concerned.
LIVE = {"hw__hw-demo__w1-alpha", "hw__hw-demo__w1-echo"}

#: How old `w1-echo`'s log is made: past `WORKING_SECONDS`, well short of
#: `QUIET_SECONDS`, so its one reachable state is `quiet`.
QUIET_AGE_SECONDS = 10 * 60

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
    tmp_path = tmp_path_factory.mktemp("words-readme")
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
        (batch / "goals" / f"{name}.md").write_text(f"# Lane {name} -- the {name} thing\n", encoding="utf-8")
    (batch / "lanes" / "w1-charlie" / "DONE.json").write_text(
        json.dumps({"status": "success", "summary": "Charlie landed."}), encoding="utf-8"
    )
    (batch / "lanes" / "w1-delta" / "BLOCKED.md").write_text(
        "# Lane w1-delta -- BLOCKED\n\n**Outcome:** B) BLOCKED. The signing key is not on this host.\n",
        encoding="utf-8",
    )
    # `w1-echo` is alive but has not written for ten minutes, which is the one
    # way a lane reaches `quiet`. Age is read off the log's mtime, so the mtime
    # is what is moved -- nothing about the state is stubbed.
    echo_log = batch / "lanes" / "w1-echo" / "lane.log"
    old = time.time() - QUIET_AGE_SECONDS
    os.utime(echo_log, (old, old))
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
    patch.setattr(data, "tmux_sessions", lambda socket: set(LIVE))
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


#: The one reading this file is about. `innerText` is the text as RENDERED --
#: a CSS `text-transform` has already been applied to it. `textContent` is the
#: text as WRITTEN and would report the plain word no matter what the screen
#: says, which is exactly how this defect survived a green suite.
AS_RENDERED = "els => els.map(e => e.innerText.trim())"

#: Both grids at once: a state pill is a state pill wherever it sits, and the
#: reported-back cards use the very same renderer.
EVERY_PILL = "#lanesGrid .lane-status, #reportedGrid .lane-status"


# --------------------------------------------------------------------------
# converge-6my -- the word, as a steward's eye actually receives it
# --------------------------------------------------------------------------


@needs_browser
@pytest.mark.parametrize("width,height", [(1280, 800), (390, 844)])
def test_every_lane_state_pill_is_read_in_its_plain_word(server, project, browser, width, height) -> None:
    errors: list[str] = []
    ctx, page = _open_operation(browser, server, project, width, height, errors)

    rendered = page.eval_on_selector_all(EVERY_PILL, AS_RENDERED)
    written = page.eval_on_selector_all(EVERY_PILL, "els => els.map(e => e.textContent.trim())")
    print(f"\n[{width}] pills as RENDERED (innerText): {rendered}")
    print(f"[{width}] pills as WRITTEN  (textContent): {written}")

    assert rendered, "no lane state pill is on the page at all"

    # The whole of the defect: the two readings disagreed, and only one of them
    # is what a person receives.
    assert rendered == written, (
        "the screen shows something other than what the payload wrote: "
        f"rendered={rendered} written={written}"
    )

    unexpected = sorted(set(rendered) - STATE_WORDS)
    assert not unexpected, (
        "a lane's state reaches the screen in a form the contract does not fix: "
        f"{unexpected} (allowed: {sorted(STATE_WORDS)})"
    )

    # Named explicitly, because "not upper-cased" is the clause and a set
    # comparison alone would pass a page that had somehow gone lower-case.
    screaming = sorted(one for one in rendered if one == one.upper() and one != one.title())
    assert not screaming, f"a state word reaches the screen in the machine's form: {screaming}"

    # All five words, so this run is proving the whole vocabulary rather than
    # whichever subset happened to render.
    assert set(rendered) == STATE_WORDS, (
        f"this run did not put all five state words on the page: saw {sorted(set(rendered))}"
    )
    assert not errors, "; ".join(errors[:3])
    ctx.close()


@needs_browser
@pytest.mark.parametrize("width,height", [(1280, 800), (390, 844)])
def test_no_state_pill_is_left_under_an_uppercasing_style(server, project, browser, width, height) -> None:
    """The style itself, not just this run's words.

    `Quiet` upper-cases to `QUIET` and is caught by the reading above, but a
    single-word state that happened to survive the transform unchanged would
    not be. So the computed style is asserted directly: no pill may still be
    under `text-transform:uppercase`, whatever it currently says.
    """
    errors: list[str] = []
    ctx, page = _open_operation(browser, server, project, width, height, errors)

    styles = page.eval_on_selector_all(
        EVERY_PILL,
        "els => els.map(e => [e.innerText.trim(), getComputedStyle(e).textTransform])",
    )
    print(f"\n[{width}] computed text-transform per pill: {styles}")

    offenders = [pair for pair in styles if pair[1] != "none"]
    assert not offenders, f"a state pill is still being transformed by CSS: {offenders}"
    assert not errors, "; ".join(errors[:3])
    ctx.close()


# --------------------------------------------------------------------------
# converge-u2y -- the host panel, documented like every other surface
# --------------------------------------------------------------------------


@pytest.fixture(scope="module")
def readme() -> str:
    assert APP_README.is_file(), f"{APP_README} does not exist"
    return APP_README.read_text(encoding="utf-8")


def _host_section(text: str) -> str:
    """The host panel's own section, from its `##` heading to the next one."""
    lines = text.splitlines()
    start = next(
        (i for i, line in enumerate(lines) if line.startswith("## ") and "host" in line.lower()),
        -1,
    )
    assert start >= 0, "app/README.md has no `##` section for the host panel"
    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("## ")), len(lines))
    return "\n".join(lines[start:end])


def test_the_readme_has_a_section_for_the_host_panel(readme) -> None:
    section = _host_section(readme)
    print(f"\napp/README.md host section ({len(section.splitlines())} lines):\n{section}")
    assert len(section.splitlines()) > 10, "the host panel gets a heading but no substance"


def test_that_section_names_every_route_the_surface_answers(readme) -> None:
    section = _host_section(readme)
    for route in (
        "GET /api/collab/{mid}/pulls",
        "GET /api/collab/{mid}/pulls/{number}",
        "POST /api/collab/{mid}/pulls/{number}/comments",
        "POST /api/collab/{mid}/pulls/{number}/answer",
        "POST /api/collab/webhooks/host",
        "GET /api/collab/{mid}/freshness",
    ):
        method, path = route.split(" ", 1)
        assert path in section, f"the host section never names the route {route}"
        assert method in section, f"the host section never says {method}"


def test_that_section_says_answering_writes_both_halves_and_reports_each(readme) -> None:
    section = _host_section(readme)
    assert "owner-ratifications-" in section, "it never says where the word is recorded"
    assert "app/writes.py" in section, "it never says which module does the recording"
    assert "comment" in section, "it never says the word is posted back to the pull request"
    assert "recorded" in section and "returnedToOrigin" in section, (
        "it never names the two values that keep a refused comment from making "
        "the record look unwritten"
    )


def test_that_section_names_the_freshness_mechanism_in_use_and_why(readme) -> None:
    section = _host_section(readme)
    assert "webhook" in section.lower(), "it never mentions the webhook"
    assert "polling" in section.lower(), "it never mentions polling"
    assert "60 seconds" in section, "it never says how often polling asks"
    # Which of the two is carrying it TODAY, and the reason -- clause 6 asks
    # for the mechanism to be named rather than assumed.
    assert "Today it is polling" in section, "it never says which mechanism is in use today"
    assert "401" in section or "sign-in gate" in section, "it never says why the webhook is not in use"


def test_that_section_says_nothing_about_the_conversation_is_stored(readme) -> None:
    section = _host_section(readme)
    lowered = section.lower()
    assert "nothing about the conversation is kept" in lowered or "no pull request, comment or answer is stored" in lowered, (
        "it never says the app stores nothing of the conversation"
    )
    assert "in memory" in lowered, "it never says the one piece of state is in memory only"


def test_that_section_says_gh_is_required_and_what_happens_without_it(readme) -> None:
    section = _host_section(readme)
    assert "`gh`" in section, "it never says `gh` is required"
    assert "not installed" in section, "it never says what the panel does when `gh` is absent"
    assert "empty list" in section, (
        "it never distinguishes 'gh is missing' from 'there are no open pull requests'"
    )


def test_the_host_section_is_as_deep_as_the_other_surface_sections(readme) -> None:
    """The clause asks for *the same depth every other surface's section has*."""
    lines = readme.splitlines()
    heads = [i for i, line in enumerate(lines) if line.startswith("## ")]
    sizes = {}
    for n, i in enumerate(heads):
        end = heads[n + 1] if n + 1 < len(heads) else len(lines)
        sizes[lines[i][3:].strip()] = end - i
    print(f"\nsection lengths in app/README.md: {json.dumps(sizes, indent=2)}")
    host = next(name for name in sizes if "host" in name.lower())
    others = [size for name, size in sizes.items() if name != host]
    floor = min(others)
    assert sizes[host] >= floor, (
        f"the host section ({sizes[host]} lines) is thinner than the thinnest other "
        f"surface section ({floor} lines)"
    )


# --------------------------------------------------------------------------
# what runs when the browser cannot
# --------------------------------------------------------------------------


def test_manual_procedure_is_documented() -> None:
    assert "FAILS IF" in MANUAL_PROCEDURE
    assert "1280" in MANUAL_PROCEDURE and "390" in MANUAL_PROCEDURE
    assert "innerText, never textContent" in MANUAL_PROCEDURE
    if PLAYWRIGHT_SKIP:
        print(f"\nPlaywright unavailable ({PLAYWRIGHT_SKIP}). Manual procedure:\n{MANUAL_PROCEDURE}")


if __name__ == "__main__":  # pragma: no cover
    print(MANUAL_PROCEDURE)
