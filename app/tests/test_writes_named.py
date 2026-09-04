"""Rendered-browser check: every write NAMES its manager-session operation, and
the two things this body cannot do SAY SO.

The two defects this file fences, both measured against the running app on
127.0.0.1:8843 on 2026-09-04, before the fix, by
`uv run conformance/experience/run.py`:

* **`experience.v1` Core 8 - "Whatever you can do here, the manager session can
  do too."** Every write is meant to name the manager-session operation that
  does the same thing, so nothing the project needs is reachable only by a
  person at a screen. Measured:

      [FAIL] 8  this body offers 4 of the five writes (answer with a word, drop
                feedback, steer, ask for a proposal) and publishes no
                manager-session operation for any of them. A reader cannot
                check that what they can do here the manager session can do too

* **`experience.v1` Core 14 - "Where a body genuinely cannot do a thing, it says
  so in the app."** Measured:

      [FAIL] 14 this body cannot do ['raise or lower a priority (`priority`)',
                'feedback as voice'], and says nothing anywhere about them -
                not what the limit is, and not what to do instead. Silence is
                the only wrong answer this clause names.

So this drives a real Chromium against the real app, at 1280 and at 390, and

* opens the shell's own fold and reads, for every write the app's own
  `/openapi.json` says it offers, the operation named beside it;
* reads the two limits - no priority write here, no voice note here - each with
  what to do instead and the item that would change it;
* checks the machine's route words sit INSIDE a `<details>` element, because
  Core 6 keeps the machine's words behind a fold and this is where they are;
* checks the folds beside the controls they are about, on Operation and on
  Home, at both widths;
* and checks nothing widens the page with every fold open, and nothing lands in
  the browser's log.

**Why one of these assertions cannot be delegated to the kit.** The kit decides
which feedback forms a body offers with `\\bvoice\\b|audio/\\*|MediaRecorder`
against everything the app serves, so the very sentence stating that voice is
NOT taken makes the kit read this body as offering voice - rule 14 then passes
without ever looking at the sentence. Measured on this tree today: before the
fix rule 14 reported `cannot_do: [priority, feedback as voice]`; after it
reports `cannot_do: [priority]`. Filed as converge-gl6. The voice sentence is
therefore fenced HERE, by reading the rendered page, and does not depend on
that detector.

If Playwright or its Chromium build is unavailable the browser tests skip with
the reason printed, and MANUAL_PROCEDURE below is the documented manual check
that stands in for it. The served-surface fences at the top need no browser and
never skip.
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
import urllib.request
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app import auth, data, serve  # noqa: E402

USER = "tester"

#: `experience.v1` Core 4's five writes, and the word the app's own route table
#: uses for each - the same pairing `conformance/experience/run.py` reads. The
#: app offers four of them today; which four is asked of `/openapi.json` at run
#: time rather than pinned here, so the day the fifth lands this file asks for
#: its operation too instead of quietly passing.
FIVE_WRITES = (
    ("answer with a word", "decision"),
    ("raise or lower a priority", "priority"),
    ("drop feedback", "feedback"),
    ("steer", "steer"),
    ("ask for a proposal", "ask"),
)

#: How this body publishes the operation behind a write. One marker, on the
#: element that carries the write's own route word.
OPERATION_ATTR = "data-manager-operation"

MANUAL_PROCEDURE = """
MANUAL PROCEDURE - run this by hand if Playwright is unavailable.
Each step says what you must SEE; seeing anything else is a failure.

Setup
  uv run --extra app python -m app.serve --host 127.0.0.1 --port 8788
  Open http://127.0.0.1:8788/.

Check - every write names the manager-session operation that does the same
        thing (experience.v1 Core 8)
  a. Size the window to exactly 1280 x 800.
  b. In the left rail, below the manager sessions, SEE a fold reading
     "Say it to the manager session instead". Click it open.
  c. SEE one entry for each of: Answer with a word, Drop feedback, Steer,
     Ask for a proposal - each with a sentence you could type into the Manager
     Console, in quotation marks, and a line saying what the manager session
     does with it.
  d. Repeat at 390 x 844. SEE the same fold, the same entries, the same words.
  FAILS IF: the fold is absent at either width, or any write the app offers has
     no sentence beside it.

Check - the two things this body cannot do say so (experience.v1 Core 14)
  e. In the same fold, SEE "Raise or lower a priority - not here", saying this
     app answers no route that would write one, what to say in the console
     instead, and the item filed for it (converge-a5g).
  f. SEE "Feedback as a voice note - not here", saying feedback is taken as
     text and as a screenshot, that a voice note is not recorded here, and what
     to do instead - say it in the console, or drop the audio file into the
     project's .converge/feedback/ folder (converge-rj1).
  FAILS IF: either limit is missing, or states the limit without saying what to
     do instead.

Check - the same naming stands beside the controls it is about
  g. Open Operation. Under "Manager strategy", open Details: SEE the steer
     sentence for the Manager Console.
  h. Under "Drop feedback", open Details: SEE the feedback sentence and the
     voice limit.
  i. Click the Converge logo for Home. Beside "Tell all manager sessions", open
     Details: SEE the tell-them-all sentence.
  FAILS IF: any of those three folds is missing.

Check - nothing widens the page
  j. With every fold open, in the devtools console run:
       document.documentElement.scrollWidth + ' vs ' + document.documentElement.clientWidth
  k. SEE the two numbers are equal, at 1280 x 800 and again at 390 x 844.
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
# two manager sessions, each with its own repository, and the real app
# --------------------------------------------------------------------------
#
# Two, because Home's "tell all" is a claim about more than one of them, and
# this file reads the fold that names that write.

VISION = """# Demo Vision (DRAFT)

## Where this is going

One place for direction and one place for operation.
"""

HIGHWAY = """# Highway - demo

Width 4.
"""

MANIFEST_HEAD = "lane\tworktree\tbranch\tbase\ttmux\tgoal\tlog\tstarted\n"

MANAGERS = ("alpha", "bravo")

COUNTS = {"TOTAL": 21, "READY": 4, "BLOCKED": 1, "RESOLVED": 16}


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "user.name=Test", "-c", "user.email=test@example.invalid", *args],
        cwd=repo,
        check=True,
        capture_output=True,
    )


@pytest.fixture(scope="module")
def project(tmp_path_factory) -> dict:
    tmp_path = tmp_path_factory.mktemp("writes-named")
    blocks = []
    for mid in MANAGERS:
        repo = tmp_path / f"repo-{mid}"
        (repo / "docs").mkdir(parents=True)
        (repo / "docs" / "VISION.md").write_text(VISION, encoding="utf-8")
        _git(repo, "init", "-q", "-b", "main")
        _git(repo, "add", "-A")
        _git(repo, "commit", "-q", "-m", "seed: the vision")

        batch = tmp_path / f"hw-{mid}"
        (batch / "goals").mkdir(parents=True)
        (batch / "HIGHWAY.md").write_text(HIGHWAY, encoding="utf-8")
        (batch / ".width").write_text("4\n", encoding="utf-8")
        (batch / "manifest.tsv").write_text(MANIFEST_HEAD, encoding="utf-8")

        blocks.append(
            "[[managers]]\n"
            f'id = "{mid}"\n'
            f'name = "Manager {mid}"\n'
            f'batch_dir = "{batch}"\n'
            f'repos = ["{repo}"]\n'
            'tracker_project = "demo-project"\n'
            'tmux_socket = "test-socket-that-does-not-exist"\n'
        )

    conf = tmp_path / "converge-app.toml"
    conf.write_text("".join(blocks), encoding="utf-8")
    # Never the real ~/.amplifier: a test must not move a steward's read point.
    return {"config": conf, "secret": tmp_path / "secret", "state": tmp_path / "state.json"}


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
    # Two seams, both facts about this machine rather than about what the app
    # says: which tmux sessions are alive, and what the work queue would answer.
    patch.setattr(data, "tmux_sessions", lambda socket: set())
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


def _cookie(project) -> str:
    return auth.Sessions(auth.read_or_make_secret(project["secret"])).issue(USER)


def _fetch(server: str, project: dict, route: str) -> str:
    """One route, read the way the conformance kit reads it: signed cookie, no
    browser. The app gates every route and has no loopback exemption."""
    request = urllib.request.Request(
        server + route, headers={"Cookie": f"{auth.COOKIE}={_cookie(project)}"}
    )
    with urllib.request.urlopen(request, timeout=20) as response:  # noqa: S310 - our own server
        return response.read().decode("utf-8")


def _offered_writes(server: str, project: dict) -> list[tuple[str, str]]:
    """The writes this app actually offers, from its own route table."""
    paths = (json.loads(_fetch(server, project, "/openapi.json")).get("paths") or {})
    tails = set()
    for path, ops in paths.items():
        if not any(method.upper() == "POST" for method in ops):
            continue
        parts = [p for p in path.strip("/").split("/") if not p.startswith("{")]
        if parts:
            tails.add(parts[-1])
    return [(name, token) for name, token in FIVE_WRITES if token in tails]


#: Every element that carries the operation marker, as it was written.
ELEMENT_RE = re.compile(r"<[a-z]+\b[^>]*" + re.escape(OPERATION_ATTR) + r"[^>]*>", re.I)


# --------------------------------------------------------------------------
# 1. the served surface - no browser, never skips
# --------------------------------------------------------------------------


def test_every_write_this_app_offers_names_a_manager_session_operation(server, project) -> None:
    """Core 8, read off the surface the app serves."""
    offered = _offered_writes(server, project)
    shell = _fetch(server, project, "/")
    elements = ELEMENT_RE.findall(shell)
    print(f"\nwrites offered: {[n for n, _ in offered]}")
    print(f"elements carrying {OPERATION_ATTR}: {len(elements)}")

    assert offered, "the app declares none of the five writes, so this file is asserting nothing"
    assert elements, (
        f"nothing the app serves carries {OPERATION_ATTR} - a reader cannot check that what "
        "they can do here the manager session can do too"
    )

    unnamed = []
    for name, token in offered:
        named_by = [el for el in elements if f'data-write="{token}"' in el]
        print(f"  {name} (`{token}`) -> {len(named_by)} element(s)")
        if not named_by:
            unnamed.append(f"{name} (`{token}`)")
        else:
            for el in named_by:
                operation = re.search(re.escape(OPERATION_ATTR) + r'="([^"]*)"', el)
                assert operation and operation.group(1).strip(), (
                    f"{name} is marked with {OPERATION_ATTR} but the operation is empty: {el}"
                )
                print(f"      operation: {operation.group(1)}")
    assert not unnamed, (
        f"the app offers {unnamed} and names no manager-session operation for them"
    )


def test_the_two_things_this_body_cannot_do_say_so_and_say_what_to_do_instead(
    server, project
) -> None:
    """Core 14, read off the surface - independent of the kit's own detector."""
    shell = _fetch(server, project, "/")

    # The priority write: absent from the route table, and said out loud.
    offered = {token for _, token in _offered_writes(server, project)}
    assert "priority" not in offered, (
        "the app now answers a priority route - this assertion has fired: replace it with one "
        "about the write working, and delete the limit sentence from shell.html (converge-a5g)"
    )
    for phrase in (
        "Raise or lower a priority",
        "no control that raises or lowers a priority",
        "converge-a5g",
    ):
        assert phrase in shell, f"the app never says {phrase!r} - the priority limit is silent"

    # Voice feedback: not taken here, and said out loud. Checked here rather
    # than left to the kit, whose detector reads this very sentence as an offer.
    assert "audio/*" not in shell and "MediaRecorder" not in shell, (
        "the app now takes audio - this assertion has fired: replace it with one about the "
        "voice write working, and delete the limit sentences (converge-rj1)"
    )
    for phrase in (
        "voice note is not recorded here",
        ".converge/feedback/",
        "converge-rj1",
    ):
        assert phrase in shell, f"the app never says {phrase!r} - the voice limit is silent"

    print("\nboth limits are stated on the served surface, each with what to do instead")


def test_the_machine_route_words_sit_behind_a_fold(server, project) -> None:
    """Core 6: the machine's words - here, the route word behind each write -
    are kept behind a Details fold, not spelled out on the open page."""
    shell = _fetch(server, project, "/")
    folded = re.sub(r"<details\b.*?</details>", " ", shell, flags=re.S | re.I)
    leaked = re.findall(r'data-write="[^"]*"', folded)
    print(f"\nroute words outside a fold: {leaked}")
    assert not leaked, f"the machine's route words are outside a Details fold: {leaked}"


# --------------------------------------------------------------------------
# what the browser is asked
# --------------------------------------------------------------------------

#: Everything drawn that reaches past the viewport's right edge, named. An
#: empty list is the only passing answer.
MEASURE = """
() => {
  const de = document.documentElement;
  const past = [];
  document.querySelectorAll('body, body *').forEach(el => {
    const s = getComputedStyle(el);
    if (s.display === 'none' || s.visibility === 'hidden') return;
    const r = el.getBoundingClientRect();
    if (r.right > de.clientWidth + 0.01) {
      past.push(((el.id ? '#' + el.id : '') + '.' + String(el.className || el.tagName)).slice(0, 50)
                + ' right=' + Math.round(r.right));
    }
  });
  return {scrollWidth: de.scrollWidth, clientWidth: de.clientWidth, past: past.slice(0, 8)};
}
"""

#: One fold as the eye meets it: is it drawn, is it a fold at all, is it inside
#: the page's width, and what does it say once open.
FOLD = """
(selector) => {
  const el = document.querySelector(selector);
  if (!el) return null;
  const de = document.documentElement;
  const r = el.getBoundingClientRect();
  return {
    tag: el.tagName.toLowerCase(),
    open: el.hasAttribute('open'),
    drawn: r.width > 0 && r.height > 0,
    withinWidth: r.left >= -0.01 && r.right <= de.clientWidth + 0.01,
    summary: (el.querySelector('summary') || {}).innerText || '',
    text: (el.innerText || '').replace(/\\s+/g, ' ').trim(),
    // The marker sits on the fold itself where the fold IS the naming (one
    // control, one operation), and on each row where the fold lists several.
    operations: [el, ...el.querySelectorAll('[data-manager-operation]')]
      .filter(n => n.hasAttribute('data-manager-operation')).map(n => ({
      write: n.getAttribute('data-write') || '',
      operation: n.getAttribute('data-manager-operation'),
      text: (n.innerText || '').replace(/\\s+/g, ' ').trim(),
    })),
  };
}
"""


def _open(browser, server, project, width: int, height: int, errors: list[str]):
    ctx = browser.new_context(viewport={"width": width, "height": height})
    ctx.add_cookies([{"name": auth.COOKIE, "value": _cookie(project),
                      "domain": "127.0.0.1", "path": "/"}])
    page = ctx.new_page()
    page.on("console", lambda m: errors.append(f"console.{m.type}: {m.text}") if m.type == "error" else None)
    page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
    page.goto(server, wait_until="networkidle")
    page.wait_for_selector("#brandHome", timeout=15000)
    page.wait_for_selector("#managerParity", timeout=15000)
    return ctx, page


def _push_the_console_sheet_down(page, width: int) -> bool:
    """On a phone the Manager Console is a sheet lying over the lower screen
    (`console.css`, `state.js` opens it by default), so it intercepts clicks on
    anything below about y=197 at 390x844. `platform-web.v1` §6 names exactly
    this gesture - "on the phone you pull it up when you want it and push it
    down when you do not" - so pushing it down is what a steward does, not a
    workaround. That it is UP on arrival is another lane's defect, filed as
    converge-nxf.
    """
    if width > 520:
        return False
    page.click("#consoleToggle", timeout=5000)
    page.wait_for_function(
        "() => getComputedStyle(document.getElementById('managerConsole')).pointerEvents === 'none'",
        timeout=5000,
    )
    return True


def _unfold(page, selector: str) -> None:
    """Open one fold the way a steward does - by clicking its summary."""
    page.eval_on_selector(selector, "el => el.scrollIntoView({block: 'center'})")
    page.click(f"{selector} > summary", timeout=8000)
    page.wait_for_function(
        "(s) => document.querySelector(s).hasAttribute('open')", arg=selector, timeout=5000
    )


# --------------------------------------------------------------------------
# 2. Core 8 in a rendered browser, at both widths
# --------------------------------------------------------------------------


@needs_browser
@pytest.mark.parametrize("width,height", [(1280, 800), (390, 844)])
def test_the_shell_fold_names_an_operation_for_every_write_offered(
    server, project, browser, width, height
) -> None:
    errors: list[str] = []
    ctx, page = _open(browser, server, project, width, height, errors)
    _push_the_console_sheet_down(page, width)

    before = page.evaluate(FOLD, "#managerParity")
    assert before and before["tag"] == "details", (
        f"the shell's naming is not a fold: {before}"
    )
    assert not before["open"], "the fold is open on arrival; the machine's words are not folded"
    assert before["drawn"], f"the fold is not drawn at {width}px: {before}"
    assert before["withinWidth"], f"the fold is cut off at {width}px: {before}"

    _unfold(page, "#managerParity")
    fold = page.evaluate(FOLD, "#managerParity")
    print(f"\n[{width}] summary: {fold['summary']!r}")
    for row in fold["operations"]:
        print(f"[{width}]   {row['write'] or '(no route)'}: {row['operation']}")

    named = {row["write"]: row for row in fold["operations"] if row["write"]}
    for name, token in _offered_writes(server, project):
        assert token in named, (
            f"[{width}] the app offers {name} (`{token}`) and the fold names no operation for it"
        )
        row = named[token]
        assert row["operation"].strip(), f"[{width}] {name} carries an empty operation"
        # A steward reads the sentence, not the attribute: the row must say
        # something out loud as well as carry the marker.
        assert len(row["text"]) > 40, (
            f"[{width}] {name}'s entry says almost nothing: {row['text']!r}"
        )
        assert "\u201c" in row["text"], (
            f"[{width}] {name}'s entry has no sentence to say in the console: {row['text']!r}"
        )

    assert not errors, f"the browser logged: {errors}"
    ctx.close()


# --------------------------------------------------------------------------
# 3. Core 14 in a rendered browser, at both widths
# --------------------------------------------------------------------------


@needs_browser
@pytest.mark.parametrize("width,height", [(1280, 800), (390, 844)])
def test_the_two_limits_are_readable_on_the_page(
    server, project, browser, width, height
) -> None:
    errors: list[str] = []
    ctx, page = _open(browser, server, project, width, height, errors)
    _push_the_console_sheet_down(page, width)
    _unfold(page, "#managerParity")

    said = page.eval_on_selector("#managerParity", "el => el.innerText.replace(/\\s+/g, ' ')")
    print(f"\n[{width}] the fold reads: {said}")

    # The limit, and what to do instead, for each of the two.
    for limit, instead, item in (
        ("Raise or lower a priority", "Manager session can", "converge-a5g"),
        ("voice note", "Manager Console", "converge-rj1"),
    ):
        assert limit.lower() in said.lower(), f"[{width}] the fold never mentions {limit!r}"
        assert re.search(r"\bnot\b|\bno\b|cannot", said, re.I), (
            f"[{width}] the fold mentions {limit!r} without saying it is not offered"
        )
        assert instead.lower() in said.lower(), (
            f"[{width}] {limit!r} states a limit and never says what to do instead"
        )
        assert item in said, f"[{width}] {limit!r} names no item that would change it"

    assert not errors, f"the browser logged: {errors}"
    ctx.close()


# --------------------------------------------------------------------------
# 4. the same naming beside the controls it is about
# --------------------------------------------------------------------------


@needs_browser
@pytest.mark.parametrize("width,height", [(1280, 800), (390, 844)])
def test_the_controls_this_surface_owns_carry_the_naming_beside_them(
    server, project, browser, width, height
) -> None:
    errors: list[str] = []
    ctx, page = _open(browser, server, project, width, height, errors)
    _push_the_console_sheet_down(page, width)

    page.click("#operationTab")
    page.wait_for_selector("#operationView:not(.hidden)", timeout=15000)

    for selector, must_say in (
        (".strategy-card .op-parity", "Steer"),
        ("#feedback .op-parity", "voice note is not recorded here"),
        ("#managers .op-parity", "every manager session"),
    ):
        _unfold(page, selector)
        fold = page.evaluate(FOLD, selector)
        print(f"\n[{width}] {selector}: {fold['text'][:150]}")
        assert fold["tag"] == "details", f"[{width}] {selector} is not a fold"
        assert fold["withinWidth"], f"[{width}] {selector} is cut off: {fold}"
        assert must_say.lower() in fold["text"].lower(), (
            f"[{width}] {selector} never says {must_say!r}: {fold['text']!r}"
        )
        assert fold["operations"] and fold["operations"][0]["operation"].strip(), (
            f"[{width}] {selector} names no manager-session operation"
        )

    page.click("#brandHome")
    page.wait_for_selector(".home-manager-card", timeout=15000)
    _unfold(page, "#homeView .op-parity")
    home = page.evaluate(FOLD, "#homeView .op-parity")
    print(f"[{width}] home fold: {home['text'][:150]}")
    assert "manager session" in home["text"].lower(), (
        f"[{width}] Home's write names no operation: {home['text']!r}"
    )
    assert home["operations"] and home["operations"][0]["operation"].strip()

    assert not errors, f"the browser logged: {errors}"
    ctx.close()


# --------------------------------------------------------------------------
# 5. nothing the fold adds widens the page, at either width
# --------------------------------------------------------------------------


@needs_browser
@pytest.mark.parametrize("width,height", [(1280, 800), (390, 844)])
def test_nothing_widens_the_page_with_every_fold_open(
    server, project, browser, width, height
) -> None:
    errors: list[str] = []
    ctx, page = _open(browser, server, project, width, height, errors)
    _push_the_console_sheet_down(page, width)

    page.click("#operationTab")
    page.wait_for_selector("#operationView:not(.hidden)", timeout=15000)
    # Every fold this lane added, open at once - the widest the page can be.
    page.evaluate(
        "() => document.querySelectorAll('#managerParity, .op-parity')"
        ".forEach(d => d.setAttribute('open', ''))"
    )
    page.wait_for_timeout(150)

    measured = page.evaluate(MEASURE)
    print(f"\n[{width}] with every fold open: {measured}")
    assert measured["scrollWidth"] <= measured["clientWidth"] + 1, (
        f"[{width}] the page scrolls sideways with the folds open: {measured}"
    )
    assert not measured["past"], (
        f"[{width}] something reaches past the right edge with the folds open: {measured['past']}"
    )

    assert not errors, f"the browser logged: {errors}"
    ctx.close()
