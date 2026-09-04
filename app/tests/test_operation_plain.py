"""A wave's phase, in plain words — in the payload and on the screen.

`experience.v1` Core 6 fixes three vocabularies a steward may be shown. Work
states are *Truly ready · Waiting on you · Working · Stuck · Done*. A wave is a
batch of work, so its phase is said in those words.

Measured on 2026-09-04 against the app at 127.0.0.1:8823, by
`conformance/experience/run.py` rule 6a (work item converge-d83):
`/api/managers/converge/operation` served twelve waves, **eleven carrying the
machine's `DONE` and one carrying `NOW`**, and `render/operation.js` wrote the
field straight into the wave kicker, so both reached the screen exactly as
written. `DONE` is not `Done`: the plain word is title case, the screaming form
is the machine's, and that difference is the whole of the clause. The machine's
word for the wave at work was not in any of the three vocabularies at all.

Two failures, not one, and this file pins both
----------------------------------------------
The payload was only half of it. `.wave-kicker` in `app/static/css/operation.css`
is styled `text-transform:uppercase`, so a payload repaired to say `Done` would
still have put the screaming form in front of a steward's eyes — a rule 6a PASS
sitting above an unrepaired screen. So:

* `test_the_payload_says_the_plain_word_*` read the payload, which is what rule
  6a judges;
* `test_the_screen_shows_the_plain_word_*` read `innerText`, which is the text
  as **rendered** — `text-transform` applied — which is what a person reads.
  `textContent` would pass either way and prove nothing, which is exactly how
  this defect survived a green suite.

Falsity conditions are stated beside each assertion. If Playwright or its
Chromium build is unavailable the rendered tests skip with the reason printed,
and MANUAL_PROCEDURE below is the documented manual check that stands in.

Run:
    uv run --extra app --with pytest --with httpx pytest -q app/tests/test_operation_plain.py
    uv run --extra app --with pytest --with httpx --with playwright \\
        pytest -q app/tests/test_operation_plain.py     # including the screen
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

#: `experience.v1` Core 6 — the WORK words. A wave is a batch of work, so these
#: are the only words its phase may be said in. Written out here rather than
#: imported from `app.data`, so a change to the app's own table cannot quietly
#: redefine what this file is asserting.
WORK_WORDS = {"Truly ready", "Waiting on you", "Working", "Stuck", "Done"}

#: What the four branches of the phase reading must produce, given the project
#: stood up below. The keys are wave labels; `wave_label` derives them.
EXPECTED_PHASE = {
    "Wave 1": "Stuck",        # passed by, and it never finished
    "Wave 2": "Working",      # a lane in it is at work right now
    "Wave 3": "Truly ready",  # the next one
    "Wave 4": "Truly ready",  # further out
    "Wave 5": "Done",         # every lane in it landed
}

MANUAL_PROCEDURE = """
MANUAL PROCEDURE — run this by hand if Playwright is unavailable.

Setup
  uv run --extra app python -m app.serve --host 127.0.0.1 --port 8788
  Open http://127.0.0.1:8788/ sized to exactly 1280 CSS px wide, click
  "Operation", and repeat every step at 390 x 844.

1. The wave phase is a plain word (experience.v1 Core 6)
   LOOK AT: the small word on the right of each wave card's top line.
   SEE: one of Truly ready / Waiting on you / Working / Stuck / Done, in
   title case, exactly as written.
   FAILS IF: it reads DONE, NOW, NEXT or STRETCH — the first is the machine's
   form of a plain word, and the other three are in no vocabulary at all.
   FAILS IF: it reads WORKING or STUCK — the word is right and the screen is
   not, which is what the kicker's text-transform did to it.

2. The wave label beside it is untouched
   SEE: the label on the left of the same line still reads in capitals
   (WAVE 8) — the phase opted out of the transform, not the whole kicker.
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
# a project whose waves land in all four readings
# --------------------------------------------------------------------------

VISION = """# Demo Vision (DRAFT)

## Where this is going

One place for direction and one place for operation.
"""

HIGHWAY = """# Highway — demo

Deadline: when the waves read in plain words

## Outcome

Every wave says where it stands in a word a person uses.

## Lane board

| Lane | What it is for |
|---|---|
| w1-alpha | prove the sign-in path |
| w2-bravo | put the plan on the page |
| w3-charlie | read the ledger |
| w4-delta | write the brief |
| w5-echo | seed the kit |

## Weave-in log

- 2026-09-01T10:00:00Z W1 launched on owner word "go".
- 2026-09-02T09:00:00Z REOPENED on owner word: the contract changed, so the
  plan is redrawn.
"""

RETURN_LOG = """# Owner return log

## 2026-09-03 — where things stand

The sign-in path is real and was re-checked on the merged result. One lane is
blocked because the signing key is not on this host. Nothing else waits on your
word. The plan was redrawn once and the reason is on record.
"""

MANIFEST_HEAD = "lane\tworktree\tbranch\tbase\ttmux\tgoal\tlog\tstarted\n"

#: One lane per wave, in the order the waves must appear. `wave_key` groups on
#: the lane name's first token, so the prefix IS the wave.
LANES = ("w1-alpha", "w2-bravo", "w3-charlie", "w4-delta", "w5-echo")

#: The one lane with a live terminal session. It fixes `now_index`, which is
#: what puts Wave 1 behind the current wave and Wave 3 in front of it.
LIVE_LANE = "w2-bravo"

#: The one lane that has landed. Its wave is at 100%, which is the Done branch.
LANDED_LANE = "w5-echo"

COUNTS = {"TOTAL": 12, "READY": 3, "BLOCKED": 1, "RESOLVED": 8}


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
    tmp_path = tmp_path_factory.mktemp("operation-plain")
    repo = tmp_path / "demo-repo"
    (repo / "docs" / "workflow").mkdir(parents=True)
    (repo / "docs" / "VISION.md").write_text(VISION, encoding="utf-8")
    (repo / "docs" / "workflow" / "OWNER-RETURN-LOG.md").write_text(RETURN_LOG, encoding="utf-8")
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "seed: the vision and the return log")

    batch = tmp_path / "hw-demo"
    (batch / "goals").mkdir(parents=True)
    (batch / "HIGHWAY.md").write_text(HIGHWAY, encoding="utf-8")
    (batch / ".width").write_text("5\n", encoding="utf-8")
    for name in LANES:
        (batch / "lanes" / name).mkdir(parents=True)
        (batch / "lanes" / name / "lane.log").write_text("working\n", encoding="utf-8")
        (batch / "goals" / f"{name}.md").write_text(
            f"# Lane {name} — the {name} thing\n", encoding="utf-8")
    (batch / "lanes" / LANDED_LANE / "DONE.json").write_text(
        json.dumps({"status": "success", "summary": "Echo landed the thing it went for."}),
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
    return {
        "config": conf,
        "secret": tmp_path / "secret",
        "state": tmp_path / "state.json",
        "batch": batch,
        "repo": repo,
    }


@pytest.fixture(scope="module")
def patched(project):
    """The two seams that are facts about this MACHINE, not about the words."""
    patch = pytest.MonkeyPatch()
    patch.setattr(data, "tmux_sessions", lambda socket: {f"hw__hw-demo__{LIVE_LANE}"})
    patch.setattr(data, "tracker_counts", lambda mc: dict(COUNTS))
    yield patch
    patch.undo()


@pytest.fixture(scope="module")
def waves(project, patched) -> list[dict]:
    from app import config as app_config

    mc = app_config.load(project["config"]).manager("demo")
    assert mc is not None, "the fixture config did not produce the demo manager"
    payload = data.operation_payload(mc)
    made = payload["waves"]
    assert made, "the fixture project produced no waves at all, so nothing below is a test"
    return made


# --------------------------------------------------------------------------
# the payload — what rule 6a judges
# --------------------------------------------------------------------------


def test_the_payload_says_the_plain_word_for_every_wave(waves):
    """Every phase served is in the work vocabulary `experience.v1` Core 6 fixes.

    FAILS IF: any wave carries a word outside it — which is the state the app
    was measured in on 2026-09-04, when eleven waves carried `DONE`.
    """
    foreign = {w["label"]: w["phase"] for w in waves if w["phase"] not in WORK_WORDS}
    assert not foreign, (
        f"waves carrying a word outside the work vocabulary {sorted(WORK_WORDS)}: {foreign}")
    print("\nphases served: " + ", ".join(f"{w['label']}={w['phase']!r}" for w in waves))


def test_the_payload_never_says_the_machines_screaming_form(waves):
    """`DONE` is not `Done`. The difference is the whole of the clause.

    FAILS IF: a phase is all-caps — even when upper-casing it would land on a
    word that IS in the vocabulary, because that is precisely the machine's
    form of it.
    """
    screaming = {w["label"]: w["phase"] for w in waves
                 if w["phase"].isupper() and w["phase"].isalpha()}
    assert not screaming, f"waves served in the machine's own form: {screaming}"


def test_each_of_the_four_readings_lands_on_its_own_plain_word(waves):
    """All four branches are exercised, and each says something different.

    The fixture puts one wave behind the wave at work and one in front of it, so
    *Stuck* and *Truly ready* are told apart rather than collapsed.

    FAILS IF: a branch answers with another branch's word, or the four
    branches produce fewer than four distinct readings between them.
    """
    said = {w["label"]: w["phase"] for w in waves}
    assert said == EXPECTED_PHASE, f"expected {EXPECTED_PHASE}, read {said}"
    assert len(set(EXPECTED_PHASE.values())) == 4, "the fixture stopped covering four readings"


def test_where_a_wave_sits_in_the_plan_is_carried_apart_from_where_it_stands(waves):
    """`cls` keeps the position; the phase keeps the state.

    Two waves that stand in the same place may sit in different parts of the
    plan, and the style hook is what keeps that distinction after the phase
    stopped carrying two meanings at once.

    FAILS IF: `cls` disappears, or the near and far ready waves become
    indistinguishable in the payload.
    """
    cls = {w["label"]: w["cls"] for w in waves}
    assert cls["Wave 3"] == "next" and cls["Wave 4"] == "stretch", (
        f"the next wave and the far one are no longer told apart: {cls}")
    assert cls["Wave 2"] == "now" and cls["Wave 5"] == "done", cls


# --------------------------------------------------------------------------
# the screen — what a person reads
# --------------------------------------------------------------------------


def _free_port() -> int:
    s = socketlib.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


@pytest.fixture(scope="module")
def server(project, patched):
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


def _open_operation(browser, server, project, width: int, height: int, errors: list[str]):
    sessions = auth.Sessions(auth.read_or_make_secret(project["secret"]))
    ctx = browser.new_context(viewport={"width": width, "height": height})
    ctx.add_cookies([{"name": auth.COOKIE, "value": sessions.issue(USER),
                      "domain": "127.0.0.1", "path": "/"}])
    page = ctx.new_page()
    page.on("console",
            lambda m: errors.append(f"console.{m.type}: {m.text}") if m.type == "error" else None)
    page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
    page.goto(server, wait_until="networkidle")
    page.wait_for_selector("#operationTab", timeout=20000)
    page.click("#operationTab")
    page.wait_for_selector("#operationView:not(.hidden)", timeout=20000)
    page.wait_for_selector("#wavesGrid .wave-phase", timeout=20000)
    return ctx, page


#: `innerText` is the text as RENDERED — `text-transform` applied. `textContent`
#: is the text as written, and would report `Done` off a screen showing the
#: screaming form, which is how this defect survived a green suite.
RENDERED_PHASES = """
() => Array.from(document.querySelectorAll('#wavesGrid .wave-phase'))
        .map(el => el.innerText.trim())
"""

RENDERED_LABELS = """
() => Array.from(document.querySelectorAll('#wavesGrid .wave-kicker > span:first-child'))
        .map(el => el.innerText.trim())
"""

TRANSFORMS = """
() => {
  const card = document.querySelector('#wavesGrid .wave-card');
  return {
    phase: getComputedStyle(card.querySelector('.wave-phase')).textTransform,
    label: getComputedStyle(card.querySelector('.wave-kicker > span:first-child')).textTransform,
  };
}
"""

WIDTHS = [(1280, 900), (390, 844)]


@needs_browser
@pytest.mark.parametrize("width,height", WIDTHS)
def test_the_screen_shows_the_plain_word_for_every_wave(
    server, project, browser, width, height
):
    """Read as a person reads it, at both widths.

    FAILS IF: any wave's phase renders outside the work vocabulary — including
    the case where the payload is already plain and the kicker's
    `text-transform:uppercase` puts the machine's form back on the screen.
    """
    errors: list[str] = []
    ctx, page = _open_operation(browser, server, project, width, height, errors)
    try:
        rendered = page.evaluate(RENDERED_PHASES)
        print(f"\n{width}x{height} rendered phases: {rendered}")
        assert rendered, "no wave phase is drawn on the page at all"
        foreign = [word for word in rendered if word not in WORK_WORDS]
        assert not foreign, (
            f"at {width}px a steward reads {foreign}, which is outside the work vocabulary "
            f"{sorted(WORK_WORDS)}")
        assert sorted(set(rendered)) == sorted(set(EXPECTED_PHASE.values())), (
            f"at {width}px the screen shows {sorted(set(rendered))}, "
            f"expected {sorted(set(EXPECTED_PHASE.values()))}")
        assert not errors, f"the page reported errors: {errors}"
    finally:
        ctx.close()


@needs_browser
@pytest.mark.parametrize("width,height", WIDTHS)
def test_only_the_phase_opts_out_of_the_kickers_capitals(
    server, project, browser, width, height
):
    """The repair is aimed at the state word, not at the kicker's styling.

    FAILS IF: the phase is still being upper-cased (the defect), or the wave's
    LABEL stopped being upper-cased (a blunt fix that changed more than the
    clause asked for).
    """
    errors: list[str] = []
    ctx, page = _open_operation(browser, server, project, width, height, errors)
    try:
        transforms = page.evaluate(TRANSFORMS)
        print(f"\n{width}x{height} text-transform: {transforms}")
        assert transforms["phase"] == "none", (
            "the wave phase is still being upper-cased, so the machine's form of the word "
            f"reaches the screen: {transforms}")
        assert transforms["label"] == "uppercase", (
            f"the wave label stopped reading in capitals — more changed than the clause "
            f"asked for: {transforms}")
        labels = page.evaluate(RENDERED_LABELS)
        assert labels and all(word == word.upper() for word in labels), (
            f"the wave labels no longer read in capitals: {labels}")
        assert not errors, f"the page reported errors: {errors}"
    finally:
        ctx.close()
