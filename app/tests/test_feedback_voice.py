"""Feedback dropped as a voice note (converge-rj1).

`experience-operation.v1` clause 10 asks that feedback can be dropped "in
whatever form is to hand -- text, a screenshot, or voice", and marks it
`(IDIOM)`: the behaviour is required and its shape is not. The app took the
first two and said out loud that it did not take the third (converge-9mq).
Saying a limit is not closing it. These tests hold the closing of it.

Every one runs against a real repository in a temp folder and reads what
actually landed on disk -- never a mock of the writer, because the thing worth
proving is that a recording becomes a file beside the note, in the form it
arrived.

## The one structural claim, and why it is asserted here

`experience.v1` Core 4 fixes the app at five writes. A voice note is not a
sixth: it is the *drop feedback* write with the form named in the path
(`/api/managers/{mid}/feedback/{form}`), so the kit's own `write_tail` reads
this route's write as `feedback`. `test_the_route_table_still_reads_five_writes`
imports the kit's own reader rather than restating it, so the day either side
moves, this fails instead of the two quietly disagreeing.

## What is NOT asserted here, and where it lives instead

The one line that mounts the router --

    app.include_router(feedback_voice.router)

-- belongs in `app/serve.py`, which is another lane's file today. Every test
below mounts it exactly as that line does, and `test_the_sign_in_gate_covers_the
_voice_route` proves the gate reaches it once mounted. Whether `app/serve.py`
carries the line yet is reported by `test_report_whether_serve_mounts_the_router`
rather than asserted, so this file neither fails before the line lands nor goes
quiet after it.
"""

from __future__ import annotations

import base64
import importlib.util
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

from app import auth, feedback_voice, serve  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]
ACTIONS_JS = REPO_ROOT / "app" / "static" / "js" / "actions.js"
DIALOGS_CSS = REPO_ROOT / "app" / "static" / "css" / "dialogs.css"

GOOD_USER = "tester"
GOOD_PASSWORD = "hunter2"

#: Bytes that are not audio and never pretend to be. What matters in every
#: assertion below is that exactly these bytes come back off the disk -- the
#: route stores what arrived and does not re-encode it, so a made-up payload
#: proves the round trip as well as a real recording would, and proves it
#: byte for byte.
SPOKEN = b"\x1aE\xdf\xa3not-really-opus-but-exactly-these-bytes\x00\x01\x02"


def data_url(media: str, payload: bytes = SPOKEN) -> str:
    return f"data:{media};base64," + base64.b64encode(payload).decode("ascii")


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "user.name=Test", "-c", "user.email=test@example.invalid", *args],
        cwd=repo, check=True, capture_output=True,
    )


VISION = """# Demo Vision (DRAFT)

## Where this is going

One place for direction and one place for operation.
"""

HIGHWAY = """# Highway — demo

Width 2.
"""

MANIFEST_HEAD = "lane\tworktree\tbranch\tbase\ttmux\tgoal\tlog\tstarted\n"


@pytest.fixture
def project(tmp_path: Path) -> dict:
    repo = tmp_path / "demo-repo"
    (repo / "docs").mkdir(parents=True)
    (repo / "docs" / "VISION.md").write_text(VISION, encoding="utf-8")
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "seed: the vision")

    batch = tmp_path / "hw-demo"
    (batch / "lanes" / "w1-alpha").mkdir(parents=True)
    (batch / "goals").mkdir()
    (batch / "HIGHWAY.md").write_text(HIGHWAY, encoding="utf-8")
    (batch / "goals" / "w1-alpha.md").write_text("# Lane alpha\n", encoding="utf-8")
    (batch / "lanes" / "w1-alpha" / "lane.log").write_text("working\n", encoding="utf-8")
    (batch / "manifest.tsv").write_text(
        MANIFEST_HEAD
        + f"w1-alpha\t{batch}/lanes/w1-alpha/demo-repo\tlane/w1-alpha\tdeadbee\t"
        f"hw__hw-demo__w1-alpha\t{batch}/goals/w1-alpha.md\t"
        f"{batch}/lanes/w1-alpha/lane.log\t2026-09-01T10:00:00Z\n",
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
    return {
        "repo": repo,
        "batch": batch,
        "config": conf,
        # Never the real ~/.amplifier: a test must not touch a steward's own
        # secret or move their read point.
        "secret": tmp_path / "secret",
        "state": tmp_path / "state.json",
        "feedback": repo / ".converge" / "feedback",
    }


class _FakePam:
    """Stands in for `pam.pam()`. Answers only for the one right password."""

    def authenticate(self, username: str, password: str, service: str = "login") -> bool:
        assert service == "login"
        return username == GOOD_USER and password == GOOD_PASSWORD


def build_app(project: dict):
    """The app, plus the one line `app/serve.py` will carry.

    Written out rather than hidden in a helper's helper, because it is the
    whole of what another lane has to add and this file is where a reader
    comes to find out what that is.
    """
    made = serve.create_app(
        config_path=project["config"], secret_path=project["secret"], state_path=project["state"]
    )
    made.include_router(feedback_voice.router)
    return made


@pytest.fixture
def client(project, monkeypatch) -> TestClient:
    monkeypatch.setattr(auth.pam_module, "pam", _FakePam)
    made = build_app(project)
    with TestClient(made) as c:
        signed = c.post(
            "/login",
            data={"username": GOOD_USER, "password": GOOD_PASSWORD, "next": "/"},
            follow_redirects=False,
        )
        assert signed.status_code == 302, signed.text
        yield c


def drop_feedback(client: TestClient, text: str = "The Android build still will not open.") -> str:
    """The text half, through the app's own route. Returns the note's name."""
    answer = client.post(
        "/api/managers/demo/feedback", json={"text": text, "context": "Demo manager · Operation"}
    )
    assert answer.status_code == 200, answer.text
    return Path(answer.json()["path"]).name


# --------------------------------------------------------------------------
# 1. the recording lands, beside the text, in the form it arrived
# --------------------------------------------------------------------------


def test_a_voice_note_lands_beside_the_text_and_the_note_names_it(client, project) -> None:
    """The whole of clause 10's third form, end to end.

    WHAT WOULD FALSIFY THIS: the recording landing somewhere other than the
    project's own feedback folder, landing under a different moment from the
    text it was dropped with, arriving changed, or the note not naming it.
    """
    note = drop_feedback(client)
    answer = client.post(
        "/api/managers/demo/feedback/voice",
        json={"dataUrl": data_url("audio/webm;codecs=opus"), "note": note},
    )
    assert answer.status_code == 200, answer.text
    said = answer.json()
    print(f"\nthe app answered: {said}")

    landed = project["feedback"] / said["voice"]
    assert landed.is_file(), f"the recording was not written: {landed}"
    assert landed.read_bytes() == SPOKEN, "the recording was changed on the way in"
    assert landed.name == note.replace(".md", ".webm"), (
        f"the recording did not land under the same moment as its note: {landed.name} vs {note}"
    )

    written = (project["feedback"] / note).read_text(encoding="utf-8")
    print(f"the note now reads:\n{written}")
    assert f"voice: {landed.name}" in written, f"the note does not name the recording:\n{written}"
    assert said["namedInTheNote"] is True and said["whyNot"] == "", said
    assert sorted(p.name for p in project["feedback"].iterdir()) == sorted([note, landed.name])


@pytest.mark.parametrize(
    "media,extension",
    [
        ("audio/webm;codecs=opus", "webm"),
        ("audio/ogg", "ogg"),
        ("audio/mpeg", "mp3"),
        ("audio/mp4", "m4a"),
        ("audio/wav", "wav"),
        ("audio/x-flac", "flac"),
        # Not in the table, and deliberately not an error: the clause asks for
        # the form it arrived in, and a subtype is that form's own name.
        ("audio/basic", "basic"),
    ],
)
def test_the_form_it_arrived_in_is_the_form_it_lands_in(client, project, media, extension) -> None:
    """WHAT WOULD FALSIFY THIS: any audio type renamed or re-encoded into another."""
    note = drop_feedback(client)
    answer = client.post(
        "/api/managers/demo/feedback/voice", json={"dataUrl": data_url(media), "note": note}
    )
    assert answer.status_code == 200, answer.text
    landed = Path(answer.json()["path"])
    print(f"\n{media} -> {landed.name}")
    assert landed.suffix == f".{extension}", f"{media} landed as {landed.name}"
    assert landed.read_bytes() == SPOKEN


def test_with_no_note_to_sit_beside_the_recording_still_lands(client, project) -> None:
    """A recording is the steward's whatever happened to the note beside it.

    WHAT WOULD FALSIFY THIS: a recording dropped on the floor because the note
    it named was gone, or a note written that does not name the recording.
    """
    answer = client.post(
        "/api/managers/demo/feedback/voice",
        json={"dataUrl": data_url("audio/webm"), "note": "", "text": "Said out loud, not typed."},
    )
    assert answer.status_code == 200, answer.text
    said = answer.json()
    print(f"\nthe app answered: {said}")
    assert Path(said["path"]).read_bytes() == SPOKEN
    note = Path(said["note"]).read_text(encoding="utf-8")
    print(f"the note it wrote:\n{note}")
    assert f"voice: {said['voice']}" in note
    assert "Said out loud, not typed." in note


# --------------------------------------------------------------------------
# 2. what it refuses -- and that a refusal writes nothing
# --------------------------------------------------------------------------


def _wrote_nothing(project) -> bool:
    folder = project["feedback"]
    return not folder.exists() or not any(folder.iterdir())


@pytest.mark.parametrize(
    "payload,expect",
    [
        ({"dataUrl": data_url("image/png")}, "arrived as image/png"),
        ({"dataUrl": data_url("text/plain")}, "arrived as text/plain"),
        ({"dataUrl": "data:audio/webm,not-base64-at-all"}, "did not arrive as an audio recording"),
        ({"dataUrl": data_url("audio/webm", b"")}, "arrived empty"),
        ({"dataUrl": ""}, "no voice note arrived"),
        ({"dataUrl": data_url("audio/webm"), "note": "../../escape.md"}, "not the name of a feedback note"),
        ({"dataUrl": data_url("audio/webm"), "note": "somewhere/else.md"}, "not the name of a feedback note"),
    ],
)
def test_a_refusal_says_why_in_plain_words_and_writes_nothing(
    client, project, payload, expect
) -> None:
    """WHAT WOULD FALSIFY THIS: a file written on a path the app refused, a
    refusal that names a status code instead of a reason, or a note name that
    reaches outside the feedback folder."""
    answer = client.post("/api/managers/demo/feedback/voice", json=payload)
    said = answer.json().get("error", "")
    print(f"\n{payload.get('note') or payload['dataUrl'][:40]!r} -> {answer.status_code}: {said}")
    assert answer.status_code == 400, answer.text
    assert expect in said, f"the refusal did not say why: {said!r}"
    assert "nothing was written" in said, f"the refusal did not say nothing was written: {said!r}"
    assert _wrote_nothing(project), (
        f"a refusal wrote into the feedback folder: {[p.name for p in project['feedback'].iterdir()]}"
    )


def test_a_form_this_does_not_take_is_refused_and_names_the_forms_it_does(client, project) -> None:
    """WHAT WOULD FALSIFY THIS: an unknown form accepted, or refused without
    saying which forms feedback can be dropped in."""
    answer = client.post("/api/managers/demo/feedback/interpretive-dance",
                         json={"dataUrl": data_url("audio/webm")})
    said = answer.json().get("error", "")
    print(f"\nthe app answered: {answer.status_code}: {said}")
    assert answer.status_code == 400
    assert "voice" in said and "text and a screenshot" in said, said
    assert _wrote_nothing(project)


def test_a_note_that_is_gone_does_not_take_the_recording_with_it(client, project) -> None:
    """WHAT WOULD FALSIFY THIS: a recording lost because its note was deleted
    between the two halves of one gesture."""
    note = drop_feedback(client)
    (project["feedback"] / note).unlink()
    answer = client.post(
        "/api/managers/demo/feedback/voice",
        json={"dataUrl": data_url("audio/webm"), "note": note},
    )
    assert answer.status_code == 200, answer.text
    said = answer.json()
    print(f"\nthe app answered: {said}")
    assert Path(said["path"]).read_bytes() == SPOKEN


def test_a_note_with_no_front_matter_is_left_exactly_as_it_was(client, project) -> None:
    """Half-writing somebody else's file is worse than saying the line could
    not be added.

    WHAT WOULD FALSIFY THIS: a note rewritten when its front matter could not
    be found, or the app claiming it named the recording when it did not.
    """
    note = drop_feedback(client)
    plain = "no front matter here, just a sentence\n"
    (project["feedback"] / note).write_text(plain, encoding="utf-8")
    answer = client.post(
        "/api/managers/demo/feedback/voice",
        json={"dataUrl": data_url("audio/webm"), "note": note},
    )
    said = answer.json()
    print(f"\nthe app answered: {said}")
    assert answer.status_code == 200
    assert Path(said["path"]).read_bytes() == SPOKEN, "the recording was lost with the note"
    assert (project["feedback"] / note).read_text(encoding="utf-8") == plain, "the note was rewritten"
    assert said["namedInTheNote"] is False and "front matter" in said["whyNot"], said


def test_a_recording_larger_than_the_bound_is_refused_by_name(client, project) -> None:
    """WHAT WOULD FALSIFY THIS: an unbounded body read into memory and written."""
    answer = client.post(
        "/api/managers/demo/feedback/voice",
        json={"dataUrl": data_url("audio/webm", b"x" * (feedback_voice.MAX_BYTES + 1))},
    )
    said = answer.json().get("error", "")
    print(f"\nthe app answered: {answer.status_code}: {said}")
    assert answer.status_code == 400
    assert "at most" in said and "nothing was written" in said, said
    assert _wrote_nothing(project)


def test_a_manager_this_app_does_not_watch_is_refused(client, project) -> None:
    answer = client.post("/api/managers/nobody/feedback/voice",
                         json={"dataUrl": data_url("audio/webm")})
    print(f"\nthe app answered: {answer.status_code}: {answer.json()}")
    assert answer.status_code == 404
    assert "no manager named nobody" in answer.json()["error"]


# --------------------------------------------------------------------------
# 3. the structural claims: five writes, and one gate
# --------------------------------------------------------------------------


def _kit():
    """`conformance/experience/run.py`, imported rather than restated.

    The point of reading the kit's own `write_tail` here is that the two
    cannot drift apart quietly: if the kit changes how it decides which write
    a route is, this test changes with it.
    """
    path = REPO_ROOT / "conformance" / "experience" / "run.py"
    spec = importlib.util.spec_from_file_location("experience_kit_for_this_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_route_table_still_reads_five_writes(client) -> None:
    """`experience.v1` Core 4, read the way the kit reads it.

    The voice note is the *drop feedback* write told which form arrived, not a
    sixth write, and this is where that claim is checked rather than assumed.

    WHAT WOULD FALSIFY THIS: a route ending `/voice` -- the kit would read a
    write called `voice`, which no contract in the family names, and rules 4b
    and 12 would be right to call it debt.
    """
    kit = _kit()
    spec = client.get("/openapi.json").json()
    posts = [p for p, methods in spec["paths"].items() if "post" in methods]
    five = {token for _, token in kit.FIVE_WRITES}
    beyond = [p for p in posts
              if kit.write_tail(p) not in five and not kit.exempt_write(p)]
    feedback = sorted(p for p in posts if kit.write_tail(p) == "feedback")
    print("\nthe writes this app declares, as the kit reads them:")
    for path in sorted(posts):
        print(f"  {kit.write_tail(path):<10} {path}")
    print(f"beyond the five, as the kit counts them: {beyond}")

    assert kit.write_tail("/api/managers/{mid}/feedback/{form}") == "feedback", (
        "the kit no longer reads this route as the feedback write"
    )
    assert feedback == ["/api/managers/{mid}/feedback", "/api/managers/{mid}/feedback/{form}"], (
        f"the two halves of one write are not both declared as feedback: {feedback}"
    )
    # This lane's claim is about its own route, and only that. The app already
    # declares writes this rule counts beyond the five -- editing, restoring,
    # per-change choices and the reading cursor, which the section contracts
    # name and `experience.v1`'s Reserved section leaves open; that standing
    # disagreement is the steward's, not this test's. What must stay true is
    # that the voice note added nothing to that list.
    assert not [p for p in beyond if "feedback" in p], (
        f"the voice note was counted as a write of its own: {beyond}"
    )


def test_the_sign_in_gate_covers_the_voice_route(project, monkeypatch) -> None:
    """The gate in `app/serve.py` is middleware, not a per-route dependency, so
    a route added by another file is behind it because it exists.

    WHAT WOULD FALSIFY THIS: the voice route answering without a cookie.
    """
    monkeypatch.setattr(auth.pam_module, "pam", _FakePam)
    with TestClient(build_app(project)) as anonymous:
        answer = anonymous.post("/api/managers/demo/feedback/voice",
                                json={"dataUrl": data_url("audio/webm")})
    print(f"\nwithout a cookie: {answer.status_code} {answer.json()}")
    assert answer.status_code == 401, "the voice route answered a caller who had not signed in"
    assert _wrote_nothing(project)


def test_report_whether_serve_mounts_the_router(project, monkeypatch) -> None:
    """Reported, never asserted -- `app/serve.py` is another lane's file.

    This file mounts the router itself in every other test, so nothing here
    depends on the line existing. What this does is say out loud whether it
    does, so neither "it is not wired yet" nor "it has been wired since" is
    ever a silent fact.
    """
    monkeypatch.setattr(auth.pam_module, "pam", _FakePam)
    stock = serve.create_app(
        config_path=project["config"], secret_path=project["secret"], state_path=project["state"]
    )
    posts = [p for p, m in stock.openapi()["paths"].items() if "post" in m]
    mounted = any("feedback/{form}" in p for p in posts)
    print(f"\napp/serve.py mounts feedback_voice.router: {mounted}")
    if not mounted:
        print("  the line it still needs, exactly as every test here writes it:")
        print("      from . import feedback_voice")
        print("      app.include_router(feedback_voice.router)")


# --------------------------------------------------------------------------
# 4. the surface: one gesture, three forms
# --------------------------------------------------------------------------


def test_the_feedback_dialog_offers_voice_beside_text_and_a_screenshot() -> None:
    """The offer the conformance kit reads, and the sentence Core 14 asks for.

    WHAT WOULD FALSIFY THIS: the voice field drawn only where the browser can
    record -- served over plain http on the LAN no browser will, so that would
    be no offer at all on the machine this app actually runs on.
    """
    js = ACTIONS_JS.read_text(encoding="utf-8")
    head, _, dialog = js.partition("export function openFeedback")
    assert dialog, "openFeedback is no longer in actions.js"
    body = dialog.split("\nexport ")[0]

    for offer in ('id="feedbackText"', 'accept="image/*"', "${voiceField()}"):
        assert offer in body, f"the feedback dialog no longer offers {offer}"
    for mark in ('id="feedbackVoice"', 'accept="audio/*"', "MediaRecorder", "getUserMedia"):
        assert mark in js, f"actions.js carries no {mark}"

    field = js.partition("function voiceField()")[2].split("\nfunction ")[0]
    assert 'type="file" accept="audio/*"' in field, (
        "the file input is no longer drawn unconditionally, so a browser that cannot "
        "record is offered nothing at all"
    )
    assert "Recording is not available here" in field, (
        "the field states no limit where the browser cannot record (experience.v1 Core 14)"
    )
    print("\nthe feedback dialog offers, in one gesture:")
    for line in field.splitlines():
        if "label" in line or "input" in line or "Recording is not" in line:
            print(f"  {line.strip()[:120]}")


def test_the_voice_write_is_reported_beside_the_text_never_instead_of_it() -> None:
    """The text landing is true whatever happens to the recording.

    WHAT WOULD FALSIFY THIS: a failed voice write reported as a failed
    feedback write, when the feedback itself is on disk.
    """
    js = ACTIONS_JS.read_text(encoding="utf-8")
    body = js.partition("export function openFeedback")[2].split("\nexport ")[0]
    assert "said += `. The voice note was not filed:" in body, (
        "a refused voice note no longer reports itself beside the feedback that landed"
    )
    assert "said += `, with your voice note beside it as" in body, (
        "a filed voice note is no longer named in what the steward is told"
    )
    print("\nwhat the steward is told, both ways:")
    for line in body.splitlines():
        if "said +=" in line or "said =" in line:
            print(f"  {line.strip()}")


def test_the_field_is_styled_where_the_dialog_is_styled() -> None:
    css = DIALOGS_CSS.read_text(encoding="utf-8")
    for rule in (".voice-row", ".voice-state", ".voice-unavailable"):
        assert rule in css, f"{rule} has no style, so the field is unstyled at every width"


# --------------------------------------------------------------------------
# 5. the same gesture, in a real browser
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
            b = p.chromium.launch(args=["--no-sandbox"])
            b.close()
    except Exception as exc:  # pragma: no cover - environment dependent
        return f"chromium is not launchable: {str(exc).splitlines()[0]}"
    return ""


PLAYWRIGHT_SKIP = _playwright_reason()

needs_browser = pytest.mark.skipif(
    bool(PLAYWRIGHT_SKIP),
    reason=f"{PLAYWRIGHT_SKIP}; MANUAL_PROCEDURE below covers the same ground",
)

MANUAL_PROCEDURE = """
Feedback as a voice note, by hand (converge-rj1)

  a. Sign in, open Operation, press "Drop feedback".
  b. SEE three fields: Feedback, a screenshot, and "Or a voice note" carrying a
     file input that accepts audio.
  c. Over plain http (the LAN case) SEE the sentence "Recording is not available
     here - recording needs a secure connection ... Attach an audio file
     instead." Over https or on localhost SEE a Record button instead.
  d. Type some feedback, attach any audio file, press "Send feedback".
  e. SEE one toast naming both: "Feedback filed at <...>.md, with your voice
     note beside it as <...>.wav".
  f. SEE both files in the project's `.converge/feedback/`, and the note's front
     matter carrying `voice: <name>`.
  g. Repeat at 1280x800 and at 390x844: the field does not widen the page.
  FAILS IF: the voice field is missing, the page scrolls sideways at 390, the
     recording lands under a different moment from its note, or the toast claims
     a voice note that is not on disk.
"""


def _free_port() -> int:
    s = socketlib.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


@pytest.fixture
def server(project, monkeypatch):
    import uvicorn

    monkeypatch.setattr(auth.pam_module, "pam", _FakePam)
    port = _free_port()
    config = uvicorn.Config(build_app(project), host="127.0.0.1", port=port, log_level="warning")
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


@needs_browser
@pytest.mark.parametrize("width,height", [(1280, 800), (390, 844)])
def test_one_gesture_drops_the_text_and_the_voice_note(server, project, width, height) -> None:
    """Driven as a steward drives it, at both widths.

    WHAT WOULD FALSIFY THIS: the field absent from the dialog, the page
    scrolling sideways at 390, a console error, or a toast that names a
    recording no file backs.
    """
    from playwright.sync_api import sync_playwright

    audio = project["repo"].parent / f"note-{width}.wav"
    audio.write_bytes(SPOKEN)
    errors: list[str] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--no-sandbox"])
        ctx = browser.new_context(viewport={"width": width, "height": height})
        page = ctx.new_page()
        page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
        page.on("console", lambda m: errors.append(f"console.{m.type}: {m.text}")
                if m.type == "error" else None)

        page.goto(f"{server}/login")
        page.fill("input[name=username]", GOOD_USER)
        page.fill("input[name=password]", GOOD_PASSWORD)
        page.click("button")
        page.wait_for_selector("#app", timeout=20000)
        page.wait_for_timeout(1500)

        page.click("#feedbackButton")
        page.wait_for_selector("#feedbackVoice", timeout=10000)

        shown = page.evaluate("""() => {
          const input = document.getElementById('feedbackVoice');
          const said = document.querySelector('.voice-unavailable, .voice-state');
          const box = input.getBoundingClientRect();
          const de = document.documentElement;
          return {
            accept: input.getAttribute('accept'),
            said: said ? said.textContent.trim() : '',
            withinWidth: box.right <= de.clientWidth + 1,
            sideways: de.scrollWidth > de.clientWidth,
          };
        }""")
        print(f"\n[{width}] the voice field: {shown}")
        assert shown["accept"] == "audio/*", shown
        assert shown["said"], "the field says nothing about recording, either way"
        assert shown["withinWidth"], f"[{width}] the voice field is cut off: {shown}"
        assert not shown["sideways"], f"[{width}] the dialog widened the page: {shown}"

        page.fill("#feedbackText", f"Said at {width} wide.")
        page.set_input_files("#feedbackVoice", str(audio))
        page.click('#dialogActions button:text-is("Send feedback")')
        page.wait_for_timeout(2500)
        said = page.eval_on_selector("#toast", "el => el.textContent.trim()")
        print(f"[{width}] the app said: {said!r}")

        ctx.close()
        browser.close()

    assert "with your voice note beside it as" in said, said
    landed = sorted(p.name for p in project["feedback"].iterdir())
    print(f"[{width}] the feedback folder holds: {landed}")
    recording = [p for p in project["feedback"].iterdir() if p.suffix == ".wav"]
    assert recording, f"the toast named a voice note and none is on disk: {landed}"
    assert recording[0].read_bytes() == SPOKEN, "the recording arrived changed"
    note = recording[0].with_suffix(".md")
    assert note.is_file() and f"voice: {recording[0].name}" in note.read_text(encoding="utf-8")
    assert f"Said at {width} wide." in note.read_text(encoding="utf-8")
    assert not errors, f"the browser reported: {errors}"
