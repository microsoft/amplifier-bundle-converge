"""Rendered-browser regression test: the steward's three constraint chips.

The defect this pins (converge-6qk, fixed in 7113de7) was invisible to every
API-level check, because the chips were *rendered* — the DOM had all three, the
API served all three — and then thrown away by the layout:

``.constraint-strip`` needs 348px for HARD LIMIT / STRATEGY / LANES and was
allotted 52–216px.  It is ``overflow: hidden``, so rather than pushing the page
sideways it swallowed its own content.  STRATEGY and LANES never rendered at any
width, console open or closed; at 1280 with the console open HARD LIMIT went too.
Nothing in the repository would have noticed, which is why it lived for weeks.

Three declarations in ``app/static/css/shell.css`` fix it, and this file asserts
each of them where it is actually applied, so a regression names its own cause:

1. ``.constraint-strip { flex: 0 0 auto }`` — the strip keeps its content width.
2. ``.direction-view .objective-block { flex: 1 1 420px }`` — the objective yields,
   but has a floor.
3. ``.direction-view .workspace-header { flex-wrap: wrap }`` — the row wraps and
   the strip takes a line of its own before the objective is squeezed to nothing.

(1) alone is not enough and this file will not accept it: measured, it passes at
1280/1440/1920 and at 1000 with the console open squeezes the objective into a
40px column, 46 lines tall — a 1127px header.  That is why the wrap-or-floor rule
below is an assertion and not a comment.

Each declaration was removed on its own and the file re-run, so what catches what
is measured rather than assumed:

* all three removed (the CSS as it stood before 7113de7) — 8 of 12 tests fail;
  at 1280 with the console open all three chips are cut (HARD LIMIT by 19px,
  STRATEGY by 135px, LANES by 251px), and with it closed STRATEGY and LANES are.
* ``flex-wrap: wrap`` removed (the naive one-declaration fix) — 6 fail; at 1000
  with the console open the objective is a 40px column and the header is 1197px
  tall.
* ``flex: 0 0 auto`` removed, the other two kept — the *geometry* still holds,
  and only the declaration test below fails.  That is not a gap in the geometry:
  with the header wrapping and the objective floored at 420px, the line wraps
  before the strip is ever asked to shrink, so nothing is clipped at any width
  the strip is shown.  It is exactly why this file asserts the rules as well as
  the pixels — the strip would be one CSS change away from clipping again with
  no rendered evidence of it.

What is measured, per width and per console state: each chip's box against the
strip's **padding** box — that, not the border box, is where ``overflow: hidden``
clips — each chip's own text overflow, the strip against the viewport edge,
whether the objective spills out of its own box, and whether the objective and
the strip overlap on both axes.  The fixture carries a realistic ~265-character
objective, because the defect only appears when the objective is long enough to
win the flex fight.

At 390 and 768 the strip is ``display: none`` — deliberately, by a rule that
predates the fix (``@media (max-width: 980px)``, shell.css line 199 before
7113de7).  Those widths are checked too, but for what is actually true there:
the strip is hidden by intent, and nothing is clipped or overlapping.  A test
asserting three visible chips at 390 would be asserting a fiction.

If Playwright or its Chromium build is unavailable the browser tests skip with
the reason printed, and ``MANUAL_PROCEDURE`` below is the documented manual check
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

from app import auth, serve  # noqa: E402

USER = "tester"

#: Sub-pixel slack. Layout numbers are fractional; a chip one hundredth of a
#: pixel past its clip edge is not the defect this pins.
TOL = 0.5

MANUAL_PROCEDURE = """
MANUAL PROCEDURE — run this by hand if Playwright is unavailable.
Each step says what you must SEE; seeing anything else is a failure.

Setup
  uv run --extra app python -m app.serve --host 127.0.0.1 --port 8788
  Open http://127.0.0.1:8788/ on the Direction view, in a browser sized with the
  devtools device toolbar ("Responsive").

Check — all three chips are there and whole, at 1280
  a. Size the viewport to exactly 1280 x 800.
  b. SEE, at the right of the workspace header, three chips side by side:
       HARD LIMIT · STRATEGY · LANES
     each with a value under its label, none cut off mid-character, none with a
     sliver of a fourth box showing at the strip's right edge.
  c. Click "Manager Console" in the top bar to CLOSE it. SEE: still three whole
     chips. Re-open it. SEE: still three whole chips.
  FAILS IF: any chip is missing, or any chip is cut off by the strip's rounded
     right edge. Before the fix, STRATEGY and LANES were absent at every width
     and HARD LIMIT was cut at 1280 with the console open.

Check — the objective is not squeezed to nothing, at 1000
  d. Size the viewport to exactly 1000 x 900 and OPEN the console.
  e. SEE: either the objective still occupies a readable column (roughly 420px
     or wider), or the strip has dropped onto a line of its own beneath it.
  f. SEE: the workspace header is a normal header — two or three lines tall, not
     a tower.
  FAILS IF: the objective is a narrow vertical ribbon of one or two words per
     line, or the header is hundreds of pixels tall (it read 1127px with
     flex:0 0 auto applied to the strip alone).

Check — the strip is deliberately absent on a phone
  g. Size the viewport to 390 x 844.
  h. SEE: no constraint strip at all (it is display:none below 980px, by design),
     and NO horizontal scrollbar along the bottom of the window.
  i. Repeat at 768 x 1024.
  FAILS IF: a partial strip or a clipped chip appears, or the page scrolls
     sideways.
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

VISION = """# Demo Vision (DRAFT)

## Where this is going

One place for direction and one place for operation.
"""

#: The objective is deliberately long. The strip only loses the flex fight when
#: the objective is long enough to win it, so a short fixture objective would
#: make this whole file pass against the unfixed CSS.
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

## Priority rationale

The header is the one surface every steward sees first.
"""

MANIFEST_HEAD = "lane\tworktree\tbranch\tbase\ttmux\tgoal\tlog\tstarted\n"

#: Two waves, so STRATEGY reads "2 waves" rather than the "Continuous" fallback —
#: a chip whose value is a fallback is a weaker thing to measure.
LANES = ["w1-alpha", "w1-beta", "w2-gamma"]


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
    tmp_path = tmp_path_factory.mktemp("constraint-strip")
    repo = tmp_path / "demo-repo"
    (repo / "docs").mkdir(parents=True)
    (repo / "docs" / "VISION.md").write_text(VISION, encoding="utf-8")
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "seed: the vision")

    batch = tmp_path / "hw-demo"
    (batch / "goals").mkdir(parents=True)
    (batch / "HIGHWAY.md").write_text(HIGHWAY, encoding="utf-8")
    (batch / ".width").write_text("10\n", encoding="utf-8")

    rows = [MANIFEST_HEAD]
    for name in LANES:
        (batch / "lanes" / name).mkdir(parents=True)
        (batch / "goals" / f"{name}.md").write_text(f"# Lane {name}\n", encoding="utf-8")
        (batch / "lanes" / name / "lane.log").write_text("working\n", encoding="utf-8")
        (batch / "lanes" / name / "DONE.json").write_text(
            json.dumps({"status": "success", "summary": f"{name} landed."}), encoding="utf-8"
        )
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
# the measurement
# --------------------------------------------------------------------------

#: One evaluation returns everything the assertions need, so a failure prints the
#: whole geometry rather than the one number that tripped.
#:
#: ``clip`` is the strip's PADDING box, not its border box: ``overflow: hidden``
#: clips at the padding edge, so a chip inside the border box but outside the
#: padding box is still cut off. Measuring the border box would let the defect
#: back in by a border's width.
MEASURE = """
() => {
  const de = document.documentElement;
  const header = document.querySelector('.direction-view .workspace-header');
  const objective = document.querySelector('.direction-view .objective-block');
  const strip = document.querySelector('.direction-view .constraint-strip');
  if (!header || !objective || !strip) {
    return {missing: {header: !header, objective: !objective, strip: !strip}};
  }
  const hs = getComputedStyle(header), os = getComputedStyle(objective);
  const ss = getComputedStyle(strip);
  const hr = header.getBoundingClientRect(), or = objective.getBoundingClientRect();
  const out = {
    clientWidth: de.clientWidth,
    scrollWidth: de.scrollWidth,
    rules: {
      headerFlexWrap: hs.flexWrap,
      objectiveFlexBasis: os.flexBasis,
      objectiveFlexGrow: os.flexGrow,
      objectiveFlexShrink: os.flexShrink,
      stripFlexGrow: ss.flexGrow,
      stripFlexShrink: ss.flexShrink,
      stripFlexBasis: ss.flexBasis,
      stripOverflow: ss.overflowX,
      stripDisplay: ss.display
    },
    header: {height: hr.height, width: hr.width, top: hr.top, bottom: hr.bottom},
    objective: {left: or.left, right: or.right, top: or.top, bottom: or.bottom,
                width: or.width, height: or.height,
                scrollWidth: objective.scrollWidth, clientWidth: objective.clientWidth,
                scrollHeight: objective.scrollHeight, clientHeight: objective.clientHeight,
                text: (objective.querySelector('strong') || {}).textContent || ''},
    chips: []
  };
  if (ss.display === 'none') { out.stripVisible = false; return out; }
  out.stripVisible = true;
  const sr = strip.getBoundingClientRect();
  const bl = parseFloat(ss.borderLeftWidth) || 0, br = parseFloat(ss.borderRightWidth) || 0;
  const bt = parseFloat(ss.borderTopWidth) || 0, bb = parseFloat(ss.borderBottomWidth) || 0;
  out.strip = {left: sr.left, right: sr.right, top: sr.top, bottom: sr.bottom,
               width: sr.width, height: sr.height,
               scrollWidth: strip.scrollWidth, clientWidth: strip.clientWidth};
  out.clip = {left: sr.left + bl, right: sr.right - br,
              top: sr.top + bt, bottom: sr.bottom - bb};
  strip.querySelectorAll(':scope > div').forEach(chip => {
    const cr = chip.getBoundingClientRect();
    const label = chip.querySelector('span'), value = chip.querySelector('strong');
    out.chips.push({
      label: (label ? label.textContent : '').trim(),
      value: (value ? value.textContent : '').trim(),
      left: cr.left, right: cr.right, top: cr.top, bottom: cr.bottom,
      width: cr.width, height: cr.height,
      textOverflowX: chip.scrollWidth - chip.clientWidth
    });
  });
  // Overlap is only real when both axes overlap; two boxes on different lines
  // share an x-range and overlap nowhere.
  out.overlap = {x: Math.min(or.right, sr.right) - Math.max(or.left, sr.left),
                 y: Math.min(or.bottom, sr.bottom) - Math.max(or.top, sr.top)};
  out.wrapped = sr.top >= or.bottom - 0.5;
  return out;
}
"""


def _is_closed(page) -> bool:
    return page.evaluate("() => document.querySelector('.body-grid').classList.contains('console-closed')")


def _set_console(page, want_open: bool) -> None:
    if _is_closed(page) != want_open:
        return
    page.click("#consoleToggle")
    page.wait_for_timeout(500)  # the grid column animates for .22s


def _boot(browser, server, project, width: int, height: int, errors: list[str]):
    sessions = auth.Sessions(auth.read_or_make_secret(project["secret"]))
    ctx = browser.new_context(viewport={"width": width, "height": height})
    ctx.add_cookies([{"name": auth.COOKIE, "value": sessions.issue(USER),
                      "domain": "127.0.0.1", "path": "/"}])
    page = ctx.new_page()
    page.on("console", lambda m: errors.append(f"console.{m.type}: {m.text}") if m.type == "error" else None)
    page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
    page.goto(server, wait_until="networkidle")
    page.wait_for_selector("#directionView .constraint-strip", state="attached", timeout=15000)
    # The chips are filled by render/top.js from /api; measuring before that lands
    # would measure an empty strip and pass for the wrong reason.
    page.wait_for_function(
        "() => (document.getElementById('objectiveText').textContent || '').trim().length > 40",
        timeout=15000,
    )
    return ctx, page


def _chip_report(state: dict) -> str:
    return " | ".join(
        f"{c['label']}='{c['value']}' [{c['left']:.1f}→{c['right']:.1f}] w={c['width']:.1f}"
        for c in state["chips"]
    ) or "(no chips)"


def _problems(state: dict, width: int, label: str) -> list[str]:
    """Every way the strip can be wrong at one width and console state."""
    found: list[str] = []
    tag = f"[{width} {label}]"

    if state["chips"] and len(state["chips"]) != 3:
        found.append(f"{tag} the strip has {len(state['chips'])} chips, not 3")

    for chip in state["chips"]:
        name = chip["label"] or "(unlabelled)"
        if not chip["value"] or chip["value"] == "—":
            found.append(f"{tag} chip {name} has no value ('{chip['value']}')")
        if chip["width"] <= 0 or chip["height"] <= 0:
            found.append(f"{tag} chip {name} has no box: {chip['width']}x{chip['height']}")
        clip = state["clip"]
        if chip["left"] < clip["left"] - TOL:
            found.append(
                f"{tag} chip {name} is cut off on the left: {chip['left']:.1f} < clip {clip['left']:.1f}"
            )
        if chip["right"] > clip["right"] + TOL:
            found.append(
                f"{tag} chip {name} is cut off on the right: {chip['right']:.1f} > clip "
                f"{clip['right']:.1f} (over by {chip['right'] - clip['right']:.1f}px)"
            )
        if chip["top"] < clip["top"] - TOL or chip["bottom"] > clip["bottom"] + TOL:
            found.append(
                f"{tag} chip {name} is cut off vertically: {chip['top']:.1f}→{chip['bottom']:.1f} "
                f"vs clip {clip['top']:.1f}→{clip['bottom']:.1f}"
            )
        if chip["textOverflowX"] > 1:
            found.append(f"{tag} chip {name} clips its own text by {chip['textOverflowX']}px")

    strip = state["strip"]
    if strip["right"] > state["clientWidth"] + TOL:
        found.append(
            f"{tag} the strip runs past the viewport: right={strip['right']:.1f} > "
            f"{state['clientWidth']}"
        )
    if strip["left"] < -TOL:
        found.append(f"{tag} the strip starts off-screen: left={strip['left']:.1f}")

    over = state["overlap"]
    if over["x"] > TOL and over["y"] > TOL:
        found.append(
            f"{tag} the objective and the strip overlap by {over['x']:.1f}x{over['y']:.1f}px"
        )

    obj = state["objective"]
    if obj["scrollWidth"] - obj["clientWidth"] > 1:
        found.append(
            f"{tag} the objective spills out of its own box by "
            f"{obj['scrollWidth'] - obj['clientWidth']}px"
        )

    # Rule 2+3, the one the naive single-declaration fix breaks: the objective
    # keeps its basis floor, OR the strip drops to a line of its own. Never
    # neither -- that is the 40px column, 46 lines tall.
    basis = state["rules"]["objectiveFlexBasis"]
    try:
        floor = float(basis.removesuffix("px"))
    except ValueError:
        found.append(
            f"{tag} the objective has no flex-basis floor (flex-basis: {basis}); "
            "nothing stops it being squeezed to nothing"
        )
    else:
        if obj["width"] < floor - TOL and not state["wrapped"]:
            found.append(
                f"{tag} the objective is squeezed to {obj['width']:.1f}px, below its "
                f"{floor:.0f}px floor, and the strip did NOT wrap to its own line "
                f"(header is {state['header']['height']:.0f}px tall)"
            )
    return found


# --------------------------------------------------------------------------
# 1. the defect itself, where the strip is shown
# --------------------------------------------------------------------------


@needs_browser
@pytest.mark.parametrize("width", [1000, 1100, 1200, 1280, 1440, 1600, 1920])
def test_all_three_chips_are_whole_at_every_width_the_strip_is_shown(
    server, project, browser, width
):
    """Every chip fully inside the strip's clip box, console open and closed."""
    errors: list[str] = []
    ctx, page = _boot(browser, server, project, width, 900, errors)
    found: list[str] = []

    for label, want_open in (("OPEN", True), ("CLOSED", False)):
        _set_console(page, want_open=want_open)
        assert _is_closed(page) is (not want_open), f"the console must actually be {label}"
        state = page.evaluate(MEASURE)
        assert "missing" not in state, f"the header did not render: {state.get('missing')}"

        print(
            f"\n[{width} {label:6}] strip visible={state['stripVisible']} "
            f"header={state['header']['height']:.0f}px "
            f"objective={state['objective']['width']:.0f}px "
            f"wrapped={state.get('wrapped')} "
            f"page={state['scrollWidth']}/{state['clientWidth']}"
        )
        print(f"[{width} {label:6}] chips: {_chip_report(state)}")
        if state["stripVisible"]:
            print(
                f"[{width} {label:6}] clip box: "
                f"{state['clip']['left']:.1f}→{state['clip']['right']:.1f} "
                f"(strip {state['strip']['left']:.1f}→{state['strip']['right']:.1f})"
            )

        if not state["stripVisible"]:
            found.append(f"[{width} {label}] the strip is display:none above 980px")
            continue
        found.extend(_problems(state, width, label))

    print(f"[{width}] console errors: {errors or 'none'}")
    ctx.close()

    assert not found, "\n  ".join(["the constraint strip is broken:", *found])
    assert not errors, "; ".join(errors[:3])


# --------------------------------------------------------------------------
# 2. the widths where the strip is deliberately absent
# --------------------------------------------------------------------------


@needs_browser
@pytest.mark.parametrize("width,height", [(390, 844), (768, 1024)])
def test_the_strip_is_absent_by_design_below_980_and_nothing_is_clipped(
    server, project, browser, width, height
):
    """A partial strip on a phone would be worse than none; there must be none."""
    errors: list[str] = []
    ctx, page = _boot(browser, server, project, width, height, errors)

    for label, want_open in (("OPEN", True), ("CLOSED", False)):
        _set_console(page, want_open=want_open)
        state = page.evaluate(MEASURE)
        assert "missing" not in state, f"the header did not render: {state.get('missing')}"
        print(
            f"\n[{width} {label:6}] strip display={state['rules']['stripDisplay']} "
            f"header={state['header']['height']:.0f}px "
            f"objective={state['objective']['width']:.0f}px "
            f"page={state['scrollWidth']}/{state['clientWidth']}"
        )

        assert state["rules"]["stripDisplay"] == "none", (
            f"below 980px the strip must be hidden outright, not shown clipped; "
            f"it is display:{state['rules']['stripDisplay']} with chips "
            f"{_chip_report(state)}"
        )
        assert state["scrollWidth"] <= state["clientWidth"], (
            f"the header widened the page at {width}: "
            f"scrollWidth={state['scrollWidth']} > clientWidth={state['clientWidth']}"
        )
        obj = state["objective"]
        assert obj["scrollWidth"] - obj["clientWidth"] <= 1, (
            f"the objective spills out of its own box at {width}: "
            f"{obj['scrollWidth']} vs {obj['clientWidth']}"
        )

    print(f"[{width}] console errors: {errors or 'none'}")
    ctx.close()
    assert not errors, "; ".join(errors[:3])


# --------------------------------------------------------------------------
# 3. the three declarations, asserted where they are applied
# --------------------------------------------------------------------------


@needs_browser
def test_the_three_declarations_that_make_the_chips_survive(server, project, browser):
    """The mechanism, not just the symptom — so a regression names its own cause."""
    errors: list[str] = []
    ctx, page = _boot(browser, server, project, 1280, 900, errors)
    _set_console(page, want_open=True)
    rules = page.evaluate(MEASURE)["rules"]
    print(f"\ncomputed rules at 1280: {rules}")
    ctx.close()

    assert rules["stripOverflow"] == "hidden", (
        "this whole test exists because the strip clips rather than widening the "
        "page; if it no longer clips, the assertions above measure nothing"
    )
    assert (rules["stripFlexGrow"], rules["stripFlexShrink"], rules["stripFlexBasis"]) == (
        "0",
        "0",
        "auto",
    ), (
        f"the strip must be flex:0 0 auto so it keeps its content width; it is "
        f"{rules['stripFlexGrow']} {rules['stripFlexShrink']} {rules['stripFlexBasis']}"
    )
    assert rules["headerFlexWrap"] == "wrap", (
        "the header must wrap, so the strip takes a line of its own before the "
        "objective is squeezed into a 40px column; it is "
        f"flex-wrap:{rules['headerFlexWrap']}"
    )
    assert rules["objectiveFlexBasis"].endswith("px"), (
        "the objective needs a flex-basis floor to yield down to; it is "
        f"flex-basis:{rules['objectiveFlexBasis']}"
    )
    assert rules["objectiveFlexShrink"] != "0", (
        "the objective must be the one that yields, not the strip"
    )
    assert not errors, "; ".join(errors[:3])


# --------------------------------------------------------------------------
# what runs when the browser cannot
# --------------------------------------------------------------------------


def test_manual_procedure_is_documented():
    """The stand-in when Playwright is unavailable is a real, checkable procedure."""
    assert "FAILS IF" in MANUAL_PROCEDURE
    assert "HARD LIMIT" in MANUAL_PROCEDURE
    for width in ("1280", "1000", "390", "768"):
        assert width in MANUAL_PROCEDURE, f"the manual check must cover {width}"
    if PLAYWRIGHT_SKIP:
        print(f"\nPlaywright unavailable ({PLAYWRIGHT_SKIP}). Manual procedure:\n{MANUAL_PROCEDURE}")


def test_the_fixture_objective_is_long_enough_to_provoke_the_defect():
    """A short objective would let the unfixed CSS pass; that must not drift."""
    assert len(OBJECTIVE) > 200, (
        f"the fixture objective is only {len(OBJECTIVE)} characters; the strip only "
        "loses the flex fight against a long one, so a short fixture makes the "
        "rendered tests above pass for the wrong reason"
    )


if __name__ == "__main__":  # pragma: no cover
    print(MANUAL_PROCEDURE)
