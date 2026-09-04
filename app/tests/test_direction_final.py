"""Rendered-browser tests for the Direction surface's last two gaps.

Two work items, one screen, and both of them the kind of defect an API-level
check cannot see:

**converge-jdm** — `experience-direction.v1` §3 and §11.

* §3 names five reader abilities and the app offered three. Worse than the
  count: the one copy control was called ``copyRendered`` and handed over
  ``doc.raw`` — the SOURCE. A test that asserted "a copy control exists" would
  have passed against that, which is why the assertions below read what each
  control actually put on the clipboard.
* §11 asks that the lock control be gated on the four Freeze Bar conditions and
  that they be shown. The conformance kit can prove the four sentences and the
  control are *served* — it says so itself: "that the control's live/inert state
  tracks the conditions at runtime is beyond a static read". That sentence is
  this file's job.

**converge-2ib** — the workspace header grew with the objective. Measured in
Chromium against a 293-character objective before the fix: 215px of an 800px
viewport at 1280 with the console open, 261px at 1000, 206px at 390. The header
is a summary and the document below it is the work.

  The height chosen, deliberately: **at most a quarter of a laptop viewport —
  200px of 800 — at every width, console open or closed**, bought by clamping
  the objective to two lines with the whole sentence one gesture away.

Measured after the fix, same objective, in this file's own fixture and in the
real repository:

    1280 open 179px (was 215)   1280 closed 104px (was 140)
    1000 open 179px (was 261)   1000 closed 179px (was 215)
    1440 open 179px (was 215)   1440 closed 104px (was 117)
     390       100px (was 206)

Right and wrong, told apart
---------------------------
Every assertion here was checked against a wrong as well as a right, because a
test that has only ever seen the fixed code proves nothing about what it would
catch:

* ``renderedTextForDoc`` first returned ``doc.title`` followed by the sections —
  and the sections already carry the H1, so the title arrived twice. The
  clipboard assertion caught it before the commit; the title line was removed.
* The "Show all" toggle first took a line of its own in the header, which cost
  19px of the very header it exists to shrink: 192px instead of 179px. The
  toggle now shares the eyebrow's line, and ``test_the_header_keeps_to_its_
  stated_height`` is what made that visible.
* The lock control is asserted inert in three separate ways — nothing ticked,
  three of four ticked, and *every* box ticked on a document nothing watches —
  because "the button is disabled at first" is not the promise. The promise is
  that it tracks.
* And it is asserted that FORCING the control still locks nothing, because §5's
  standard for a guard is that it is the guard, never a hidden control.

If Playwright or its Chromium build is unavailable the browser tests skip with
the reason printed, and ``MANUAL_PROCEDURE`` below is the documented manual
check that stands in for it.
"""

from __future__ import annotations

import datetime
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

from app import auth, serve  # noqa: E402

USER = "tester"

#: Sub-pixel slack. Layout numbers are fractional.
TOL = 0.5

#: converge-2ib's stated budget, in pixels: a quarter of an 800px viewport.
HEADER_BUDGET = 200

#: §11's four conditions, in the contract's order, as the gate words them.
FOUR_CONDITIONS = (
    "It says what it means",
    "It carries a real example of right and wrong",
    "It can be checked against reality",
    "You have read it and agreed",
)

MANUAL_PROCEDURE = """
MANUAL PROCEDURE — run this by hand if Playwright is unavailable.
Each step says what you must SEE; seeing anything else is a failure.

Setup
  uv run --extra app python -m app.serve --host 127.0.0.1 --port 8788
  Open http://127.0.0.1:8788/ on the Direction view, in a browser sized with the
  devtools device toolbar ("Responsive"), at 1280 x 800, console open.

Check — five abilities, five controls (§3)
  a. SEE in the document toolbar: Wide · Raw · Copy rendered · Copy source ·
     Download · A− 100% A+ · Ask…
  b. Click "Copy source", paste into an editor. SEE the Markdown file: a line
     beginning "# ", "## " headings, "**bold**" markers.
  c. Click "Copy rendered", paste. SEE the same document as prose: no "#", no
     "**", the title appearing ONCE.
  FAILS IF: the two paste the same thing, or "Copy rendered" pastes Markdown.

Check — zoom (§3)
  d. Click A+ four times. SEE the document text grow at each click and the
     readout go 115% · 130% · 150% · 175%; SEE no horizontal scrollbar along the
     bottom of the window at any step.
  e. Click A+ again. SEE nothing change and the button greyed at 175%.
  FAILS IF: the toolbar or the change cards grow with the text, or the page
     scrolls sideways.

Check — the lock gate (§11)
  f. Open the fold marked "Locking this document". SEE all four conditions:
     It says what it means · It carries a real example of right and wrong ·
     It can be checked against reality · You have read it and agreed.
  g. On a contract (one the ledger watches) SEE the third already answered, with
     the ledger's own words beside it, and no checkbox to tick it with.
  h. Tick the other three. SEE the count reach "4 of 4 met" and "Lock this
     document" become usable. Untick one. SEE it go inert again.
  i. Open docs/VISION.md, which no ledger row watches. Tick all three boxes.
     SEE "3 of 4 met", the control still inert, and the line naming what is
     missing: "Not yet: it can be checked against reality."
  j. Go back to the contract. SEE the boxes empty — an answer about one document
     is not an answer about another.
  FAILS IF: any tick survives moving between documents, or the control is ever
     usable below 4 of 4.

Check — the header keeps to its height (converge-2ib)
  k. With a long objective (~270 characters or more), SEE the objective on TWO
     lines, ending in an ellipsis, and the workspace header no taller than a
     quarter of the window.
  l. Hover the objective. SEE the whole sentence in the tooltip.
  m. Click "Show all". SEE the whole sentence in place; click "Show less". SEE
     it clamped again and the header back to its earlier height.
  n. Repeat at 390 x 844.
  FAILS IF: the header is a third of the screen, or the full sentence cannot be
     reached without leaving the page.
"""


# --------------------------------------------------------------------------
# availability
# --------------------------------------------------------------------------


def _playwright_reason() -> str:
    if shutil.which("git") is None:
        return "git is not installed"
    try:
        from playwright.sync_api import sync_playwright  # noqa: F401
    except Exception as exc:  # pragma: no cover - environment dependent
        return f"playwright is not importable: {exc}"
    try:
        from playwright.sync_api import sync_playwright

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

#: Long on purpose. The header only grows when the objective is long enough to
#: make it grow, so a short fixture objective would pass against the unfixed CSS.
OBJECTIVE = (
    "Every steward opens one page and sees the whole batch — the direction that "
    "governs it, the lanes running against that direction right now, and the small "
    "number of decisions that only a person can make — without reading a log file "
    "or a manifest by hand to find any of it"
)

HIGHWAY = f"""# Highway — demo

Deadline: Fri 12 Sep

## Outcome

{OBJECTIVE}. Nothing else counts as done.
"""

#: No ledger row watches this one, so it reads `draft`: "it can be checked
#: against reality" is NOT met, however many boxes a steward ticks.
VISION = """# Demo Vision (DRAFT)

## Where this is going

One place for direction and one place for operation. **Bold** here so the
rendered copy has Markdown punctuation to lose.

## What that costs

The header is the one surface every steward sees first.
"""

#: One CONFORMS row watches this one, so it reads `kept`: the third condition is
#: answered by the app, from the ledger, with its own words as the evidence.
DEMO_CONTRACT = """# Demo Contract — v1 (DRAFT)

## Core

1. **The demo keeps one promise.** It is watched by the ledger below.

## What v1 does not freeze

Anything else.
"""

#: Already locked: its H1 carries a locking word, which `app/writes.py` reads.
FROZEN_CONTRACT = """# Frozen Contract — v1 (FROZEN 2026-09-04)

## Core

1. **This one is already law.** Nothing here may be edited in place.
"""

LEDGER = """# Demo conformance ledger.
- id: DEMO-001
  title: the demo contract keeps its one promise
  contract:
    file: contracts/demo.v1.md
    clause: "Core 1"
  disposition: CONFORMS
- id: DEMO-002
  title: the frozen contract keeps its one promise
  contract:
    file: contracts/frozen.v1.md
    clause: "Core 1"
  disposition: CONFORMS
"""

MANIFEST_HEAD = "lane\tworktree\tbranch\tbase\ttmux\tgoal\tlog\tstarted\n"


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "user.name=Test", "-c", "user.email=test@example.invalid", *args],
        cwd=repo,
        check=True,
        capture_output=True,
    )


@pytest.fixture(scope="module")
def project(tmp_path_factory) -> dict:
    """A small real repository and a real batch — never fixtures of the answers."""
    tmp_path = tmp_path_factory.mktemp("direction-final")
    repo = tmp_path / "demo-repo"
    (repo / "docs").mkdir(parents=True)
    (repo / "contracts").mkdir(parents=True)
    (repo / "ledger").mkdir(parents=True)
    (repo / "docs" / "VISION.md").write_text(VISION, encoding="utf-8")
    (repo / "contracts" / "demo.v1.md").write_text(DEMO_CONTRACT, encoding="utf-8")
    (repo / "contracts" / "frozen.v1.md").write_text(FROZEN_CONTRACT, encoding="utf-8")
    (repo / "ledger" / "rows.yaml").write_text(LEDGER, encoding="utf-8")
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "seed: the vision and two contracts")
    # A second commit, so the reading has a "since you last read" boundary that
    # is a real commit rather than an empty one.
    (repo / "docs" / "VISION.md").write_text(
        VISION.replace("One place for direction", "One single place for direction"), encoding="utf-8"
    )
    _git(repo, "commit", "-qam", "vision: one single place")

    batch = tmp_path / "hw-demo"
    (batch / "goals").mkdir(parents=True)
    (batch / "HIGHWAY.md").write_text(HIGHWAY, encoding="utf-8")
    (batch / ".width").write_text("10\n", encoding="utf-8")
    rows = [MANIFEST_HEAD]
    for name in ("w1-alpha", "w2-beta"):
        (batch / "lanes" / name).mkdir(parents=True)
        (batch / "goals" / f"{name}.md").write_text(f"# Lane {name}\n", encoding="utf-8")
        (batch / "lanes" / name / "lane.log").write_text("working\n", encoding="utf-8")
        rows.append(
            f"{name}\t{batch}/lanes/{name}/demo-repo\tlane/{name}\tdeadbee\t"
            f"hw__hw-demo__{name}\t{batch}/goals/{name}.md\t{batch}/lanes/{name}/lane.log\t"
            "2026-09-01T10:00:00Z\n"
        )
    (batch / "manifest.tsv").write_text("".join(rows), encoding="utf-8")

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
    # Never the real ~/.amplifier: a test must not move a steward's read point.
    return {
        "config": conf,
        "secret": tmp_path / "secret",
        "state": tmp_path / "state.json",
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


@pytest.fixture(scope="module")
def browser():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        b = p.chromium.launch(args=["--no-sandbox"])
        yield b
        b.close()


# --------------------------------------------------------------------------
# driving the page
# --------------------------------------------------------------------------


def _boot(browser, server, project, width: int, height: int, errors: list[str]):
    """A signed-in browser on the Direction view, with the document loaded."""
    sessions = auth.Sessions(auth.read_or_make_secret(project["secret"]))
    ctx = browser.new_context(
        viewport={"width": width, "height": height},
        permissions=["clipboard-read", "clipboard-write"],
    )
    ctx.add_cookies(
        [{"name": auth.COOKIE, "value": sessions.issue(USER), "domain": "127.0.0.1", "path": "/"}]
    )
    page = ctx.new_page()
    page.on(
        "console",
        lambda m: errors.append(f"console.{m.type}: {m.text}") if m.type == "error" else None,
    )
    page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
    page.goto(server, wait_until="networkidle")
    # Below 980px the Manager Console is a fixed tray over the bottom 68vh of
    # the screen (console.css), so a phone reads with it closed — that is the
    # app's own design and the steward's own gesture, not something to force
    # past. The header tests re-open it deliberately.
    if width <= 980:
        page.wait_for_selector("#consoleToggle", timeout=15000)
        page.click("#consoleToggle")
        page.wait_for_timeout(500)
    page.wait_for_selector("#directionView .lock-gate", state="attached", timeout=15000)
    # The header is filled by render/top.js from /api; measuring before that
    # lands would measure an empty header and pass for the wrong reason.
    page.wait_for_function(
        "() => (document.getElementById('objectiveText').textContent || '').trim().length > 40",
        timeout=15000,
    )
    page.wait_for_function(
        "() => (document.getElementById('docPath').textContent || '').includes('.md')",
        timeout=15000,
    )
    return ctx, page


def _is_closed(page) -> bool:
    return page.evaluate(
        "() => document.querySelector('.body-grid').classList.contains('console-closed')"
    )


def _set_console(page, want_open: bool) -> None:
    if _is_closed(page) != want_open:
        return
    page.click("#consoleToggle")
    page.wait_for_timeout(500)  # the grid column animates for .22s


def _open_doc(page, title: str) -> None:
    """Open a document from the nav by its title, and wait for it to arrive."""
    page.click(f'.repo-doc:has-text("{title}")')
    page.wait_for_function(
        "() => (document.getElementById('docTitle').textContent || '').trim().length > 0",
        timeout=10000,
    )
    page.wait_for_timeout(300)


def _open_gate(page) -> None:
    if not page.evaluate("() => document.getElementById('lockGate').open"):
        page.click("#lockGate summary")
        page.wait_for_timeout(150)


def _gate(page) -> dict:
    return page.evaluate(
        """() => ({
      path: document.getElementById('docPath').textContent,
      head: document.getElementById('lockGateHead').textContent,
      count: document.getElementById('lockGateCount').textContent,
      note: document.getElementById('lockGateNote').textContent,
      why: document.getElementById('lockGateWhy').textContent,
      disabled: document.getElementById('lockButton').disabled,
      conditions: Array.from(document.querySelectorAll('.lock-conditions li'))
        .map(li => (li.textContent || '').replace(/\\s+/g, ' ').trim()),
      boxes: Array.from(document.querySelectorAll('[data-lock-check]'))
        .map(b => ({key: b.dataset.lockCheck, checked: b.checked, disabled: b.disabled})),
      reality: (document.querySelector('[data-lock-evidence="reality"]') || {}).textContent || '',
      visible: Array.from(document.querySelectorAll('.lock-conditions li'))
        .every(li => li.getBoundingClientRect().height > 0),
    })"""
    )


HEADER_MEASURE = """
() => {
  const de = document.documentElement;
  const header = document.querySelector('.direction-view .workspace-header');
  const text = document.getElementById('objectiveText');
  const strip = document.querySelector('.direction-view .constraint-strip');
  const hr = header.getBoundingClientRect();
  const ss = getComputedStyle(strip);
  const out = {
    clientWidth: de.clientWidth,
    scrollWidth: de.scrollWidth,
    headerHeight: hr.height,
    headerBottom: hr.bottom,
    objectiveChars: (text.textContent || '').trim().length,
    titleChars: (text.title || '').length,
    clipped: text.scrollHeight - text.clientHeight > 1,
    lines: Math.round(text.clientHeight / parseFloat(getComputedStyle(text).lineHeight)),
    stripDisplay: ss.display,
    chips: [],
  };
  if (ss.display !== 'none') {
    const sr = strip.getBoundingClientRect();
    const bl = parseFloat(ss.borderLeftWidth) || 0, br = parseFloat(ss.borderRightWidth) || 0;
    const bt = parseFloat(ss.borderTopWidth) || 0, bb = parseFloat(ss.borderBottomWidth) || 0;
    out.clip = {left: sr.left + bl, right: sr.right - br, top: sr.top + bt, bottom: sr.bottom - bb};
    strip.querySelectorAll(':scope > div').forEach(chip => {
      const cr = chip.getBoundingClientRect();
      out.chips.push({
        label: (chip.querySelector('span') || {}).textContent || '',
        value: (chip.querySelector('strong') || {}).textContent || '',
        left: cr.left, right: cr.right, top: cr.top, bottom: cr.bottom,
        textOverflowX: chip.scrollWidth - chip.clientWidth,
      });
    });
  }
  return out;
}
"""


# --------------------------------------------------------------------------
# converge-jdm §3 — the five reader abilities
# --------------------------------------------------------------------------


@needs_browser
def test_the_two_copy_controls_carry_different_text(server, project, browser):
    """Copy as rendered and copy as source, each carrying what its label says.

    The defect this pins is not a missing button: it is a button called
    ``copyRendered`` that copied ``doc.raw``. So the clipboard is read.
    """
    errors: list[str] = []
    ctx, page = _boot(browser, server, project, 1280, 800, errors)
    _open_doc(page, "Vision")

    page.click("#copySource")
    page.wait_for_timeout(400)
    source = page.evaluate("() => navigator.clipboard.readText()")
    page.click("#copyRendered")
    page.wait_for_timeout(400)
    rendered = page.evaluate("() => navigator.clipboard.readText()")

    print(f"\n[copy] source   {len(source):5d} chars: {source[:70]!r}")
    print(f"[copy] rendered {len(rendered):5d} chars: {rendered[:70]!r}")

    on_disk = (project["repo"] / "docs" / "VISION.md").read_text(encoding="utf-8")
    assert source.strip() == on_disk.strip(), "Copy source must hand over the file, byte for byte"
    assert source != rendered, "the two copy controls handed over the same text"
    assert "**" in source and "## " in source, "the source copy lost its Markdown"
    assert "**" not in rendered and "## " not in rendered, (
        f"the rendered copy still carries Markdown punctuation: {rendered[:200]!r}"
    )
    for phrase in ("Where this is going", "One single place for direction"):
        assert phrase in rendered, f"the rendered copy dropped {phrase!r}"
    title = "Demo Vision (DRAFT)"
    assert rendered.count(title) == 1, (
        f"the rendered copy repeats the title {rendered.count(title)} times"
    )
    assert not errors, f"the page logged errors: {errors}"
    ctx.close()


@needs_browser
@pytest.mark.parametrize("width,height", [(1280, 800), (390, 844)])
def test_all_five_abilities_have_a_visible_control(server, project, browser, width, height):
    """§3's five abilities, each with a control a reader can actually reach."""
    errors: list[str] = []
    ctx, page = _boot(browser, server, project, width, height, errors)
    controls = {
        "copy as rendered": "#copyRendered",
        "copy as source": "#copySource",
        "download the source": "#downloadDoc",
        "zoom": "#zoomIn",
        "page width or full screen": "#wideToggle",
    }
    seen = {}
    for ability, selector in controls.items():
        box = page.evaluate(
            "(sel) => { const el = document.querySelector(sel);"
            " if (!el) return null; const r = el.getBoundingClientRect();"
            " return {w: r.width, h: r.height, right: r.right, text: el.textContent.trim()}; }",
            selector,
        )
        seen[ability] = box
    print(f"\n[{width}] controls: " + " | ".join(
        f"{a}={'MISSING' if b is None else b['text']}" for a, b in seen.items()))
    for ability, box in seen.items():
        assert box is not None, f"[{width}] no control for {ability}"
        assert box["w"] > 0 and box["h"] > 0, f"[{width}] the control for {ability} has no box"
        assert box["right"] <= width + TOL, (
            f"[{width}] the control for {ability} runs off the screen at {box['right']}"
        )
    assert not errors, f"the page logged errors: {errors}"
    ctx.close()


@needs_browser
@pytest.mark.parametrize("width,height", [(1280, 800), (390, 844)])
def test_zoom_scales_the_reading_text_and_never_widens_the_page(
    server, project, browser, width, height
):
    """Zoom moves the document's own text, stops at its ends, and does not
    push the page sideways — platform-web.v1 §14 holds at every step."""
    errors: list[str] = []
    ctx, page = _boot(browser, server, project, width, height, errors)
    _open_doc(page, "Vision")

    def reading() -> dict:
        return page.evaluate(
            """() => {
              const p = document.querySelector('#documentModeContent p');
              const de = document.documentElement;
              return {
                label: document.getElementById('zoomLevel').textContent,
                font: p ? parseFloat(getComputedStyle(p).fontSize) : 0,
                toolbar: parseFloat(getComputedStyle(document.getElementById('rawToggle')).fontSize),
                overflow: de.scrollWidth - de.clientWidth,
                outAt: document.getElementById('zoomOut').disabled,
                inAt: document.getElementById('zoomIn').disabled,
              };
            }"""
        )

    start = reading()
    print(f"\n[{width}] zoom {start['label']} text={start['font']}px toolbar={start['toolbar']}px")
    assert start["label"] == "100%", f"the reading did not start at 100%: {start['label']}"

    seen = [start]
    for _ in range(10):
        if reading()["inAt"]:
            break
        page.click("#zoomIn")
        page.wait_for_timeout(120)
        now = reading()
        print(f"[{width}] zoom {now['label']} text={now['font']}px "
              f"toolbar={now['toolbar']}px overflow={now['overflow']}")
        assert now["overflow"] <= 0, (
            f"[{width}] at {now['label']} the page is {now['overflow']}px wider than the viewport"
        )
        assert now["toolbar"] == start["toolbar"], (
            "the toolbar grew with the document text; zoom is the reading column's, not the chrome's"
        )
        assert now["font"] > seen[-1]["font"], (
            f"[{width}] {seen[-1]['label']} → {now['label']} did not move the text"
        )
        seen.append(now)
    top = seen[-1]
    assert top["label"] == "175%", f"zoom did not stop at its top step: {top['label']}"
    assert top["inAt"] is True, "the zoom-in control is still live at the top of the scale"
    assert top["font"] > start["font"], (
        f"the reading text did not grow: {start['font']}px → {top['font']}px"
    )
    # Used again at the top of the scale, from the page's own side of the
    # glass: a disabled control fires no handler, so nothing moves.
    page.evaluate("() => document.getElementById('zoomIn').click()")
    page.wait_for_timeout(120)
    assert reading()["label"] == "175%", "the scale went past its top step"

    for _ in range(10):
        if reading()["outAt"]:
            break
        page.click("#zoomOut")
        page.wait_for_timeout(120)
    bottom = reading()
    print(f"[{width}] zoom {bottom['label']} text={bottom['font']}px (bottom of the scale)")
    assert bottom["label"] == "80%", f"zoom did not stop at its bottom step: {bottom['label']}"
    assert bottom["outAt"] is True, "the zoom-out control is still live at the bottom of the scale"
    assert bottom["font"] < start["font"], "the reading text did not shrink"
    assert not errors, f"the page logged errors: {errors}"
    ctx.close()


# --------------------------------------------------------------------------
# converge-jdm §11 — the lock gate, and what it is gated on
# --------------------------------------------------------------------------


@needs_browser
@pytest.mark.parametrize("width,height", [(1280, 800), (390, 844)])
def test_the_four_conditions_are_shown_at_both_widths(server, project, browser, width, height):
    """All four, on the screen, at the phone and the laptop the contract names.

    The width matters: the context rail is ``display:none`` below 1320px, so a
    gate living there would be invisible at exactly the width §14 cares about.
    """
    errors: list[str] = []
    ctx, page = _boot(browser, server, project, width, height, errors)
    _open_gate(page)
    state = _gate(page)
    print(f"\n[{width}] gate: {state['head']} — {state['count']}")
    for line in state["conditions"]:
        print(f"[{width}]   {line}")
    assert state["visible"], f"[{width}] the conditions are in the DOM but have no box on screen"
    shown = " \n".join(state["conditions"])
    for condition in FOUR_CONDITIONS:
        assert condition in shown, f"[{width}] the gate does not state: {condition}"
    assert not errors, f"the page logged errors: {errors}"
    ctx.close()


@needs_browser
def test_the_control_tracks_the_conditions_in_both_directions(server, project, browser):
    """Inert at 1 of 4, live at 4 of 4, and inert again the moment one is undone."""
    errors: list[str] = []
    ctx, page = _boot(browser, server, project, 1280, 800, errors)
    _open_doc(page, "Demo")
    _open_gate(page)

    first = _gate(page)
    print(f"\n[gate] {first['path']}: {first['count']} · control disabled={first['disabled']}")
    print(f"[gate] reality: {first['reality']}")
    assert first["count"] == "1 of 4 met", (
        f"a ledger-watched contract should start with the app's own condition met: {first['count']}"
    )
    assert first["disabled"] is True, "the control is live with three conditions unanswered"
    assert "Kept" in first["reality"], (
        f"the app's condition is not evidenced by the ledger: {first['reality']!r}"
    )
    reality_box = [b for b in first["boxes"] if b["key"] == "reality"]
    assert not reality_box, "the ledger's condition is offered as a tick box a steward could fake"

    for key in ("means", "example", "steward"):
        page.check(f'[data-lock-check="{key}"]')
        page.wait_for_timeout(80)
        step = _gate(page)
        print(f"[gate] ticked {key}: {step['count']} · disabled={step['disabled']}")
    live = _gate(page)
    assert live["count"] == "4 of 4 met", f"the count did not reach four: {live['count']}"
    assert live["disabled"] is False, "the control is still inert with all four conditions met"
    assert "irreversible" in live["note"], f"nothing warns what locking costs: {live['note']!r}"

    page.uncheck('[data-lock-check="example"]')
    page.wait_for_timeout(120)
    back = _gate(page)
    print(f"[gate] unticked example: {back['count']} · disabled={back['disabled']}")
    print(f"[gate] note: {back['note']}")
    assert back["disabled"] is True, "the control stayed live after a condition was withdrawn"
    assert "real example of right and wrong" in back["note"], (
        f"the gate does not say which condition is missing: {back['note']!r}"
    )
    assert not errors, f"the page logged errors: {errors}"
    ctx.close()


@needs_browser
def test_a_document_nothing_watches_cannot_be_locked_however_many_ticks(server, project, browser):
    """The third condition is the ledger's answer, and no tick gets past it."""
    errors: list[str] = []
    ctx, page = _boot(browser, server, project, 1280, 800, errors)
    _open_doc(page, "Vision")
    _open_gate(page)

    for key in ("means", "example", "steward"):
        page.check(f'[data-lock-check="{key}"]')
        page.wait_for_timeout(80)
    state = _gate(page)
    print(f"\n[gate] {state['path']}: {state['count']} · disabled={state['disabled']}")
    print(f"[gate] reality: {state['reality']}")
    print(f"[gate] note: {state['note']}")
    assert state["count"] == "3 of 4 met", (
        f"a document no row watches reached {state['count']} with every tick given"
    )
    assert state["disabled"] is True, "a document nothing watches was lockable"
    assert "checked against reality" in state["note"], (
        f"the gate does not name what is missing: {state['note']!r}"
    )
    assert "No part of this one is being watched yet" in state["reality"], (
        f"the gate does not say WHY it cannot be checked: {state['reality']!r}"
    )
    assert not errors, f"the page logged errors: {errors}"
    ctx.close()


@needs_browser
def test_an_answer_about_one_document_is_not_an_answer_about_another(server, project, browser):
    """Steward answers do not travel. Nothing is ticked for them, ever."""
    errors: list[str] = []
    ctx, page = _boot(browser, server, project, 1280, 800, errors)
    _open_doc(page, "Demo")
    _open_gate(page)
    for key in ("means", "example", "steward"):
        page.check(f'[data-lock-check="{key}"]')
        page.wait_for_timeout(80)
    answered = _gate(page)
    print(f"\n[gate] {answered['path']}: {answered['count']}")

    _open_doc(page, "Vision")
    _open_gate(page)
    moved = _gate(page)
    print(f"[gate] {moved['path']}: {moved['count']} boxes={[b['checked'] for b in moved['boxes']]}")
    assert all(not b["checked"] for b in moved["boxes"]), (
        "answers given about one document arrived pre-ticked on another"
    )

    _open_doc(page, "Demo")
    _open_gate(page)
    returned = _gate(page)
    print(f"[gate] {returned['path']}: {returned['count']} "
          f"boxes={[b['checked'] for b in returned['boxes']]}")
    assert all(not b["checked"] for b in returned["boxes"]), (
        "answers were remembered across a move away and back; they are given, not stored"
    )
    assert returned["disabled"] is True
    assert not errors, f"the page logged errors: {errors}"
    ctx.close()


@needs_browser
def test_a_locked_document_offers_no_lock(server, project, browser):
    """The document that is already law says so, and offers nothing to answer."""
    errors: list[str] = []
    ctx, page = _boot(browser, server, project, 1280, 800, errors)
    _open_doc(page, "Frozen")
    _open_gate(page)
    state = _gate(page)
    print(f"\n[gate] {state['path']}: {state['head']} · {state['count']} "
          f"· disabled={state['disabled']}")
    print(f"[gate] why: {state['why']}")
    assert state["head"] == "This document is locked"
    assert state["count"] == "FROZEN", f"the gate does not name the locking word: {state['count']!r}"
    assert state["disabled"] is True, "a locked document offered its lock control again"
    assert all(b["disabled"] for b in state["boxes"]), (
        "a locked document still offers conditions to answer"
    )
    assert "proposal" in state["why"], (
        f"the gate does not say what changing a locked document means: {state['why']!r}"
    )
    assert not errors, f"the page logged errors: {errors}"
    ctx.close()


@needs_browser
def test_forcing_the_control_locks_nothing(server, project, browser):
    """§5's standard: the refusal is the guard's, never a hidden control.

    The control is stripped of its `disabled` attribute in the browser and used
    with zero conditions met. What must NOT happen is a locked document.
    """
    errors: list[str] = []
    ctx, page = _boot(browser, server, project, 1280, 800, errors)
    _open_doc(page, "Vision")
    _open_gate(page)
    before = (project["repo"] / "docs" / "VISION.md").read_text(encoding="utf-8")
    state = _gate(page)
    assert state["disabled"] is True and state["count"] == "0 of 4 met"

    page.evaluate("() => document.getElementById('lockButton').removeAttribute('disabled')")
    page.click("#lockButton")
    page.wait_for_timeout(400)
    dialog = page.evaluate(
        "() => { const d = document.getElementById('appDialog');"
        " return d.open ? document.getElementById('dialogTitle').textContent : ''; }"
    )
    print(f"\n[forced] the forced control opened: {dialog!r}")
    assert dialog == "", (
        "forcing the control walked straight into the confirmation; the check is not made again"
    )
    after = (project["repo"] / "docs" / "VISION.md").read_text(encoding="utf-8")
    assert after == before, "the document changed on disk when the control was forced"
    assert "FROZEN" not in after.splitlines()[0], "the document's H1 was stamped"
    assert not errors, f"the page logged errors: {errors}"
    ctx.close()


@needs_browser
def test_locking_stamps_the_document_and_says_so(server, project, browser):
    """With all four met the control is live — and the lock actually lands.

    Until converge-eci the app answered no lock route, and this test asserted
    the refusal while carrying its own tripwire: "when converge-eci lands, the
    tripwire below fails and this test is the one to rewrite: it should then
    assert the document's H1 is stamped."

    The route landed and the tripwire fired. Measured 2026-09-04 before this
    rewrite (converge-drh):

        AssertionError: the refusal was swallowed: 'Locked: FROZEN'
        assert 'Nothing was locked' in 'Locked: FROZEN'

    So this is that rewrite. `contracts/documents.v1.md` clause 6 puts a
    document's status in its H1 and nowhere else, so the H1 on disk is what is
    read here — not the toast, which is only the app's report of it.
    """
    errors: list[str] = []
    ctx, page = _boot(browser, server, project, 1280, 800, errors)
    _open_doc(page, "Demo")
    _open_gate(page)
    before = (project["repo"] / "contracts" / "demo.v1.md").read_text(encoding="utf-8")
    for key in ("means", "example", "steward"):
        page.check(f'[data-lock-check="{key}"]')
        page.wait_for_timeout(80)
    assert _gate(page)["disabled"] is False

    page.click("#lockButton")
    page.wait_for_timeout(400)
    said = page.evaluate(
        """() => ({
          title: document.getElementById('dialogTitle').textContent,
          items: Array.from(document.querySelectorAll('#dialogContent li')).map(l => l.textContent),
        })"""
    )
    print(f"\n[lock] dialog: {said['title']}")
    for item in said["items"]:
        print(f"[lock]   {item}")
    assert said["title"] == "Lock this document"
    assert len(said["items"]) == 4, "the confirmation does not carry all four answers"

    page.click("#dialogActions button:has-text('Lock it')")
    # Wait for THIS answer, not for whatever the last toast happened to say —
    # the one from booting ("Opened Demo manager") is still on screen and read
    # as a pass once already.
    page.wait_for_function(
        "() => /lock/i.test(document.getElementById('toast').textContent || '')", timeout=10000
    )
    toast = page.evaluate("() => document.getElementById('toast').textContent")
    after = (project["repo"] / "contracts" / "demo.v1.md").read_text(encoding="utf-8")
    day = datetime.date.today().isoformat()
    head, body = before.splitlines()[0], before.splitlines()[1:]
    stamped, kept = after.splitlines()[0], after.splitlines()[1:]

    print(f"[lock] toast: {toast}")
    print(f"[lock] H1 before: {head}")
    print(f"[lock] H1 after:  {stamped}")
    print(f"[lock] everything below the H1 is unchanged: {kept == body}")
    print(f"[lock] console errors: {errors or 'none'}")

    assert "Locked" in toast, f"the app did not say the lock landed: {toast!r}"
    assert "FROZEN" in toast, f"the report does not name the locking word: {toast!r}"
    # The H1, on disk, is the claim — clause 6 says the status lives there and
    # nowhere else, so a screen that says "Locked" over an unstamped file is
    # exactly the defect this test exists to catch.
    assert f"(FROZEN {day})" in stamped, (
        f"the document's H1 was not stamped although the app said it locked: {stamped!r}"
    )
    assert "(DRAFT)" not in stamped, f"the H1 still carries its draft status: {stamped!r}"
    assert kept == body, "locking rewrote something below the H1; it stamps the H1 and nothing else"
    assert not errors, f"the page logged errors: {errors}"
    ctx.close()


# --------------------------------------------------------------------------
# converge-2ib — the header's stated height, and the whole sentence
# --------------------------------------------------------------------------


@needs_browser
@pytest.mark.parametrize("width,height", [(1000, 900), (1280, 800), (1440, 900), (1920, 1080), (390, 844)])
def test_the_header_keeps_to_its_stated_height(server, project, browser, width, height):
    """At most a quarter of a laptop viewport, console open and closed.

    Before the clamp, with this fixture's 269-character objective: 215px at
    1280 with the console open, 261px at 1000, 206px at 390.
    """
    errors: list[str] = []
    ctx, page = _boot(browser, server, project, width, height, errors)
    for label, want_open in (("OPEN", True), ("CLOSED", False)):
        _set_console(page, want_open=want_open)
        state = page.evaluate(HEADER_MEASURE)
        print(
            f"\n[{width} {label:6}] header={state['headerHeight']:.0f}px "
            f"(budget {HEADER_BUDGET}px) objective={state['objectiveChars']} chars on "
            f"{state['lines']} line(s), clipped={state['clipped']} "
            f"page={state['scrollWidth']}/{state['clientWidth']}"
        )
        assert state["objectiveChars"] > 260, (
            "the fixture objective is too short to make the header grow; this test would pass "
            "against the unfixed CSS"
        )
        assert state["headerHeight"] <= HEADER_BUDGET + TOL, (
            f"[{width} {label}] the header takes {state['headerHeight']:.0f}px, over the stated "
            f"{HEADER_BUDGET}px budget"
        )
        assert state["lines"] <= 2, (
            f"[{width} {label}] the objective is on {state['lines']} lines, not clamped to two"
        )
        assert state["scrollWidth"] <= state["clientWidth"] + TOL, (
            f"[{width} {label}] the page scrolls sideways: "
            f"{state['scrollWidth']} > {state['clientWidth']}"
        )
    assert not errors, f"the page logged errors: {errors}"
    ctx.close()


@needs_browser
@pytest.mark.parametrize("width,height", [(1280, 800), (390, 844)])
def test_the_whole_objective_is_reachable_without_leaving_the_view(
    server, project, browser, width, height
):
    """Hover carries it, "Show all" shows it, "Show less" puts it back."""
    errors: list[str] = []
    ctx, page = _boot(browser, server, project, width, height, errors)
    clamped = page.evaluate(HEADER_MEASURE)
    toggle = page.evaluate(
        """() => {
          const b = document.getElementById('objectiveMore');
          return {shown: !b.classList.contains('hidden'), label: b.textContent.trim(),
                  expanded: b.getAttribute('aria-expanded')};
        }"""
    )
    print(f"\n[{width}] clamped: header={clamped['headerHeight']:.0f}px "
          f"lines={clamped['lines']} clipped={clamped['clipped']} "
          f"title={clamped['titleChars']} chars · toggle={toggle}")
    assert clamped["clipped"] is True, "nothing is hidden, so this fixture proves nothing"
    assert clamped["titleChars"] == clamped["objectiveChars"], (
        "hovering does not carry the whole sentence: "
        f"{clamped['titleChars']} of {clamped['objectiveChars']} characters"
    )
    assert toggle["shown"] is True, "there is no gesture to see the rest"
    assert toggle["label"] == "Show all" and toggle["expanded"] == "false"

    page.click("#objectiveMore")
    page.wait_for_timeout(250)
    opened = page.evaluate(HEADER_MEASURE)
    label = page.evaluate("() => document.getElementById('objectiveMore').textContent.trim()")
    print(f"[{width}] opened: header={opened['headerHeight']:.0f}px "
          f"lines={opened['lines']} clipped={opened['clipped']} · toggle={label!r}")
    assert opened["clipped"] is False, "the whole sentence is still cut off after Show all"
    assert opened["lines"] > clamped["lines"], "Show all did not open anything"
    assert label == "Show less", f"the toggle does not offer the way back: {label!r}"

    page.click("#objectiveMore")
    page.wait_for_timeout(250)
    shut = page.evaluate(HEADER_MEASURE)
    print(f"[{width}] closed again: header={shut['headerHeight']:.0f}px lines={shut['lines']}")
    assert abs(shut["headerHeight"] - clamped["headerHeight"]) <= TOL, (
        f"the header did not come back to {clamped['headerHeight']:.0f}px: "
        f"{shut['headerHeight']:.0f}px"
    )
    assert not errors, f"the page logged errors: {errors}"
    ctx.close()


@needs_browser
def test_the_three_constraint_chips_are_still_whole(server, project, browser):
    """converge-6qk's fix survives this one: the chips are not clipped at 1280.

    The header shrank by taking lines away from the objective, never from the
    strip; this is what would notice if that stopped being true.
    """
    errors: list[str] = []
    ctx, page = _boot(browser, server, project, 1280, 800, errors)
    for label, want_open in (("OPEN", True), ("CLOSED", False)):
        _set_console(page, want_open=want_open)
        state = page.evaluate(HEADER_MEASURE)
        assert state["stripDisplay"] != "none", f"[1280 {label}] the strip is hidden above 980px"
        print(f"\n[1280 {label:6}] chips: " + " | ".join(
            f"{c['label'].strip()}='{c['value'].strip()}' [{c['left']:.0f}→{c['right']:.0f}]"
            for c in state["chips"]))
        assert len(state["chips"]) == 3, f"[1280 {label}] {len(state['chips'])} chips, not 3"
        for chip in state["chips"]:
            name = chip["label"].strip() or "(unlabelled)"
            assert chip["right"] <= state["clip"]["right"] + TOL, (
                f"[1280 {label}] chip {name} is cut off on the right by "
                f"{chip['right'] - state['clip']['right']:.1f}px"
            )
            assert chip["left"] >= state["clip"]["left"] - TOL, (
                f"[1280 {label}] chip {name} is cut off on the left"
            )
            assert chip["textOverflowX"] <= 1, (
                f"[1280 {label}] chip {name} clips its own text by {chip['textOverflowX']}px"
            )
    assert not errors, f"the page logged errors: {errors}"
    ctx.close()


# --------------------------------------------------------------------------
# the stand-in, when there is no browser
# --------------------------------------------------------------------------


def test_manual_procedure_is_documented():
    """A skip is only honest if a person can still run the check by hand."""
    for wanted in ("Copy source", "Copy rendered", "4 of 4", "Show all", "FAILS IF"):
        assert wanted in MANUAL_PROCEDURE, f"the manual procedure does not cover {wanted!r}"
    assert len(re.findall(r"FAILS IF", MANUAL_PROCEDURE)) >= 4, (
        "every check in the manual procedure needs its own failure condition"
    )
    if PLAYWRIGHT_SKIP:  # pragma: no cover - environment dependent
        print(f"\nbrowser tests skipped: {PLAYWRIGHT_SKIP}\n{MANUAL_PROCEDURE}")
