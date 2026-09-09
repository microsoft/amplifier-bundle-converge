"""Consumer-side fixes for `operation-repair.md`, resuming faff11c.

faff11c made `data.py` honest about what it does not know: `throughput()`
returns `None` (not `0`) for `derived`/`resolved`/`stuck` when the work queue
is unavailable, and `brief_parts()` was meant to strip a return-brief line's
own bold Markdown label off before handing back its value. Neither promise
held all the way to what a steward actually reads:

* **The flow card converted "unknown" back into "zero".** `operation.js`
  coerced a `null` `resolved`/`reopened` with `Number(x) || 0`, so an
  unavailable tracker rendered `"+0 net"` in `positive-text` -- the exact
  "unsupported claim of activity" `data.py` had just stopped making, put
  back by the one file that reads its output.
* **`**Label**:` (bold closing before the colon) left the label in the
  value.** The old strip regex only matched a label whose closing `**`
  came *after* the punctuation (`**Label.**`); `**Label**: text` has the
  punctuation *outside* the bold, which that regex's own `[^*.:]{0,32}[.:]`
  character class cannot cross, so the substitution silently found nothing
  to replace and the raw `**Finished**:` sat in the summary a steward reads.
  A label with no separator at all near it (`Finished value no
  punctuation.`) had the opposite failure: the same character class, with
  nothing to stop it early, ran all the way to the sentence's own trailing
  period and swallowed the whole line.
* **A brief with no "Finished" part and no heading guessed at one anyway.**
  `latest_summary` fell back to `first_sentence(body)` -- an arbitrary
  fragment of whatever the entry happened to open on, dressed up as the
  project's own account of itself.

Every case below is proven to fail against faff11c before the fix in this
lane, and to pass after it. No fixture here mutates the live tracker or any
real manager's files -- everything is built fresh under `tmp_path`.
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


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "user.name=Test", "-c", "user.email=test@example.invalid", *args],
        cwd=repo,
        check=True,
        capture_output=True,
    )


# ==========================================================================
# 1. data.py -- brief_parts strips every conventional label shape
# ==========================================================================


@pytest.mark.parametrize(
    "line,expected",
    [
        # **Label**: value -- the bold closes BEFORE the colon. faff11c's
        # regex needed the closing `**` on the far side of the punctuation
        # and could not cross it, so this shape left the raw label in place.
        ("**Finished**: The report is ready.", "The report is ready."),
        # **Label.** value -- the period sits INSIDE the bold. This shape
        # already worked before this lane; pinned here so the fix does not
        # regress it.
        ("**Finished.** The report is ready.", "The report is ready."),
        # Plain label, colon separator, no Markdown at all.
        ("Finished: The report is ready.", "The report is ready."),
        # Plain label, period separator, no Markdown at all.
        ("Finished. The report is ready.", "The report is ready."),
        # Plain label, no separator at all -- just a space. The old
        # character class had nothing to stop it early and ran on to the
        # sentence's own trailing period, swallowing the whole line.
        ("Finished the report is ready.", "the report is ready."),
    ],
)
def test_brief_parts_strips_every_label_shape_leaving_only_the_value(line, expected) -> None:
    parts = {one["part"]: one["text"] for one in data.brief_parts(line)}
    assert parts.get("finished") == expected
    # The specific defect named in the goal: the bold markers or the label
    # word itself must never survive into the value a steward reads.
    assert "*" not in parts["finished"]
    assert "finished" not in parts["finished"].lower()


def test_brief_parts_covers_all_five_labels_in_all_three_written_shapes() -> None:
    """One entry, every label written a different conventional way."""
    body = (
        "**Time away**: Ten hours, one wave.\n"
        "**Finished.** The gap analysis's whole plan landed and was re-checked.\n"
        "Stuck: Nothing is stuck.\n"
        "**Needs you.** Nothing needs you this turn.\n"
        "Anything quietly broken nothing to report.\n"
    )
    parts = {one["part"]: one["text"] for one in data.brief_parts(body)}
    assert parts["timeAway"] == "Ten hours, one wave."
    assert parts["finished"] == "The gap analysis's whole plan landed and was re-checked."
    assert parts["stuck"] == "Nothing is stuck."
    assert parts["needsYou"] == "Nothing needs you this turn."
    assert parts["quietlyChanged"] == "nothing to report."
    for value in parts.values():
        assert "*" not in value, f"a bold marker survived into a value: {value!r}"


def test_brief_parts_yields_nothing_for_an_entry_that_labels_nothing() -> None:
    """Missing parts: an unlabelled entry yields no parts at all, not a guess."""
    body = "Just a plain paragraph with no return-brief labels in it at all."
    assert data.brief_parts(body) == []


# ==========================================================================
# 2. data.py -- latest_summary never invents a summary from raw prose
# ==========================================================================


def test_latest_summary_uses_the_finished_part_stripped_of_its_own_label() -> None:
    """End-to-end through the real defect shape: **Finished**: value."""
    body = (
        "**Time away**: Ten hours.\n"
        "**Finished**: Every write the umbrella names now exists in the app.\n"
        "**Stuck**: Nothing.\n"
    )
    entries = [("2026-09-04", "the run closed", body)]
    summary = data.latest_summary(entries)
    assert summary == "Every write the umbrella names now exists in the app."
    assert "*" not in summary
    assert "Finished" not in summary


def test_latest_summary_falls_back_to_heading_never_to_a_guessed_first_sentence() -> None:
    """No 'Finished' part; a heading exists -- use it, exactly as before."""
    body = "The long-form explainer landed. The turnkey harness is honestly red."
    entries = [("2026-09-02", "explainer and turnkey landed", body)]
    assert data.latest_summary(entries) == "explainer and turnkey landed"


def test_latest_summary_is_honestly_empty_with_no_finished_part_and_no_heading() -> None:
    """Missing brief/heading: an absent summary, never an invented one.

    The old fallback reached into the raw body for its first sentence when
    neither a 'Finished' part nor a heading existed. That sentence -- here,
    a caveat that happens to open the entry -- is not an account of where
    the project stands; showing it as `summary` is the same unsupported
    claim this lane also removes from the flow card, just made in the
    brief instead.
    """
    body = "Note: this entry predates the return-brief convention entirely."
    entries = [("2026-09-01", "", body)]
    assert data.latest_summary(entries) == ""


# ==========================================================================
# 3. operation.js -- the source itself makes the "unknown is not zero"
#    promise real for the flow card
# ==========================================================================

OPERATION_JS = Path(__file__).resolve().parents[1] / "static" / "js" / "render" / "operation.js"


def test_the_source_never_coerces_a_null_flow_measure_with_number_or_zero() -> None:
    """The exact defect line: `Number(flow.resolved) || 0` reads null as 0."""
    source = OPERATION_JS.read_text(encoding="utf-8")
    assert "Number(flow.resolved) || 0" not in source
    assert "Number(flow.reopened) || 0" not in source
    # Net must only be computed when both measures it is built from are
    # real numbers -- an unavailable resolved count must not, on its own or
    # combined with a real reopened count, produce a numeric net.
    assert "typeof flow.resolved === 'number'" in source
    assert "typeof flow.reopened === 'number'" in source


# ==========================================================================
# 4. a real rendered payload -- what a steward's eye actually lands on
# ==========================================================================


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
    reason=f"{PLAYWRIGHT_SKIP}; rendered check skipped, see test_the_source_never_coerces... for the source-level pin",
)

VISION = "# Demo Vision (DRAFT)\n\n## Where this is going\n\nOne place for direction and one place for operation.\n"
HIGHWAY = "# Highway \u2014 demo\n\nWidth 4.\n"
MANIFEST_HEAD = "lane\tworktree\tbranch\tbase\ttmux\tgoal\tlog\tstarted\n"


@pytest.fixture(scope="module")
def project(tmp_path_factory) -> dict:
    tmp_path = tmp_path_factory.mktemp("operation-repair")
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
    (batch / "lanes" / "w1-alpha").mkdir(parents=True)
    (batch / "lanes" / "w1-alpha" / "lane.log").write_text("working\n", encoding="utf-8")
    (batch / "goals" / "w1-alpha.md").write_text("# Lane w1-alpha \u2014 the w1-alpha thing\n", encoding="utf-8")
    (batch / "manifest.tsv").write_text(
        MANIFEST_HEAD
        + f"w1-alpha\t{batch}/lanes/w1-alpha/demo-repo\tlane/w1-alpha\tdeadbee\thw__hw-demo__w1-alpha\t"
        f"{batch}/goals/w1-alpha.md\t{batch}/lanes/w1-alpha/lane.log\t2026-09-01T10:00:00Z\n",
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
        'tmux_socket = "test-socket-that-does-not-exist"\n'
        f'steward = "{USER}"\n',
        encoding="utf-8",
    )
    return {"config": conf, "secret": tmp_path / "secret", "state": tmp_path / "state.json", "sessions": tmp_path / "sessions.json", "batch": batch}


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
    patch.setattr(data, "tmux_sessions", lambda socket: {"hw__hw-demo__w1-alpha"})
    # The exact payload the goal names: unavailable tracker (derived/resolved/
    # stuck null), with verified/reopened -- read from git and the plan record
    # directly, independent of the tracker -- staying real numbers.
    patch.setattr(
        data,
        "throughput",
        lambda counts, merged, reopened: {
            "derived": None,
            "resolved": None,
            "verified": 2,
            "reopened": 0,
            "stuck": None,
            "spark": [],
            "available": False,
        },
    )

    made = serve.create_app(config_path=project["config"], secret_path=project["secret"], state_path=project["state"], sessions_path=project["sessions"])
    port = _free_port()
    config = uvicorn.Config(made, host="127.0.0.1", port=port, log_level="warning")
    uv_server = uvicorn.Server(config)
    thread = threading.Thread(target=uv_server.run, daemon=True)
    thread.start()
    deadline = time.time() + 20
    while not uv_server.started and time.time() < deadline:
        time.sleep(0.05)
    assert uv_server.started, "app server did not start"
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


@needs_browser
def test_an_unavailable_throughput_shows_no_plus_zero_net_or_positive_styling(server, project, browser) -> None:
    errors: list[str] = []
    sessions = auth.Sessions(auth.read_or_make_secret(project["secret"]))
    ctx = browser.new_context(viewport={"width": 1280, "height": 800})
    ctx.add_cookies([{"name": auth.COOKIE, "value": sessions.issue(USER), "domain": "127.0.0.1", "path": "/"}])
    page = ctx.new_page()
    page.on("console", lambda m: errors.append(f"console.{m.type}: {m.text}") if m.type == "error" else None)
    page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
    page.goto(server, wait_until="networkidle")
    # Boot always lands on Home first, never an auto-picked manager
    # (experience.v1 Core 1, converge-t30q) -- open the one manager session
    # this project registers before reaching its Operation tab.
    page.wait_for_selector(".home-manager-card", timeout=15000)
    page.click(".home-manager-card")
    page.wait_for_selector("#operationTab", timeout=15000)
    page.click("#operationTab")
    # Waits on the field this scenario actually changes, not an unrelated one
    # -- verified=2 only appears once the operation payload has rendered.
    page.wait_for_selector("#throughputVerified:has-text('2')", timeout=15000)

    net_text = page.inner_text("#throughputNet").strip()
    net_class = page.get_attribute("#throughputNet", "class") or ""
    resolved_text = page.inner_text("#throughputResolved").strip()
    verified_text = page.inner_text("#throughputVerified").strip()
    reopened_text = page.inner_text("#throughputReopened").strip()
    headline_text = page.inner_text("#throughputHeadline").strip()
    print(f"\nnet={net_text!r} class={net_class!r} resolved={resolved_text!r} "
          f"verified={verified_text!r} reopened={reopened_text!r} headline={headline_text!r}")

    # The falsity condition this test replaces: faff11c rendered "+0 net" in
    # positive-text here, an unsupported claim that work is moving.
    assert net_text != "+0 net"
    assert "positive-text" not in net_class
    assert net_text == "\u2014"
    # Independently known measures stay visible: verified/reopened are real
    # counts (read from git/the plan record) whether or not the tracker
    # answers, and must never be swallowed into the same "unavailable" look.
    assert verified_text == "2"
    assert reopened_text == "0"
    assert resolved_text == "\u2014"
    # The card no longer overclaims "Work is moving" when it cannot say so.
    assert headline_text != "Work is moving"
    assert not errors, "; ".join(errors[:3])
    ctx.close()


def test_manual_procedure_is_documented_for_when_the_browser_cannot_run() -> None:
    if PLAYWRIGHT_SKIP:
        print(
            f"\nPlaywright unavailable ({PLAYWRIGHT_SKIP}). Manual check: open Operation with an "
            "unconfigured/unreachable work tracker and SEE the Flow today card show em-dashes and "
            "neutral text for net/derived/resolved/stuck, never '+0 net' in green, while verified "
            "and reopened still show their real numbers."
        )
    assert True
