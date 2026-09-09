"""End-to-end journey tests for the hosted PR review (converge-vtkw / -ibxt / -xet9).

Three defects, one steward's browser, one focused file -- the FILES section of
this lane's brief asks for this in preference to growing `test_collab.py`
further, and the three defects genuinely share one journey: open Direction,
reach the PR panel, read a PR, answer or ask.

converge-vtkw -- the entry point.  `direction.css` hides `.context-rail`
outright at 1320 CSS px and narrower, so a panel that lived only there had no
entry point at all at 1280 or 390 (measured on the steward's own Mac PWA,
2026-09-09). The panel now lives inside `.document-surface`, which carries no
such rule at any width. Proved here by measuring the real DOM at 1440, 1280
and 390, console open and closed, and by reaching an empty composer with
ordinary clicks -- never a forced state or a hidden-node read.

converge-ibxt -- the reading. A PR's own headings are not required to be
Converge's three-part shape, and a heading this reader does not recognize is
not the same fact as the PR having nothing to say. Proved here against a real
PR body with headings of its own, a table, a code block, a link, and a raw
`<script>` tag and a `javascript:` link a hostile or careless author could
paste in -- the complete original text must be reachable and safe, and the
honest "unrecognized" wording must replace the old, false "no evidence" claim.

converge-xet9 -- staying current without losing anything. A background poll
must reach the open thread as well as the list, without erasing an unsent
question or decision note, without moving a reading position, and without
ever drawing a reply onto the wrong PR because the steward switched away
mid-fetch. Proved here with a controlled stand-in host (never a real GitHub
call) whose answers this test changes between two poll ticks, and with two
repositories that both happen to have a pull request numbered 7.

If Playwright or its Chromium build is unavailable every browser test skips
with the reason printed, and MANUAL_PROCEDURE below is the check that stands
in for it. The API-level tests need no browser and always run.
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

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from app import auth, collab, serve  # noqa: E402

USER = "tester"

MANUAL_PROCEDURE = """
MANUAL PROCEDURE -- run this by hand if Playwright is unavailable.
Each step says what you must SEE; seeing anything else is a failure.

Setup
  uv run --extra app python -m app.serve --host 127.0.0.1 --port 8788
  Open http://127.0.0.1:8788/, sign in, open a manager, open Direction.
  A real `gh` and a real GitHub repository with at least one open PR are
  needed for the live parts of this procedure; without them, check only the
  layout steps (a, b, c).

Check -- the PR panel is reachable, not just present (converge-vtkw)
  a. At 1440x900, console open (the default), SEE "Pull requests, read as
     proposals" appear near the top of the document, above the Read/Changes/
     Review/History tabs -- not inside the right-hand context rail.
  b. Resize to 1280x800. SEE the same panel still visible and clickable.
     Before the fix, the right-hand rail vanished below 1320px and took the
     only entry point with it.
  c. Resize to 390x844 (or open dev tools' device toolbar). Close the Manager
     Console if it covers the page (tap its icon). SEE the panel, open it,
     pick a pull request, and SEE an empty, focusable composer textarea.
  FAILS IF: the panel is missing at 1280 or 390, or reaching it needs a
     resize, a forced CSS state, or a click on something invisible.

Check -- the full PR body is the reading, not a guess about it (converge-ibxt)
  d. Open a real pull request whose body does NOT use Converge's own
     "## The exact change / ## The evidence / ## What does not change"
     headings -- almost any ordinary PR qualifies.
  e. SEE the complete original body, rendered (tables and code blocks
     readable, links clickable), and SEE it say plainly that this reader did
     not recognize a change/evidence/unchanged heading -- never "No evidence
     was attached to this pull request."
  FAILS IF: any paragraph is missing, a table renders as raw pipe characters,
     or the panel claims no evidence exists rather than admitting it did not
     recognize the heading.

Check -- a background refresh never costs a draft (converge-xet9)
  f. Open a pull request. Start typing a question, and separately a decision
     note, but send neither.
  g. Ask a teammate to leave a new comment on that same PR (or wait for the
     next poll tick if one already has). Wait up to 60 seconds.
  h. SEE the new comment appear in the conversation, and SEE your unsent
     question and note exactly as you left them -- not cleared, not
     overwritten.
  FAILS IF: either draft is gone, or the conversation does not pick up the
     new comment without you re-clicking the row.
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
# a stand-in host -- never a real GitHub call
# --------------------------------------------------------------------------
#: Reads its answers from env vars EVERY call, so a test can change what the
#: "host" says between two poll ticks without restarting anything -- that is
#: what makes the xet9 draft-preservation check possible at all.
FAKE_GH = '''#!/usr/bin/env python3
import json, os, sys

argv = sys.argv[1:]
log = os.environ.get("FAKE_GH_LOG")
if log:
    with open(log, "a", encoding="utf-8") as out:
        out.write(json.dumps(argv) + "\\n")

if argv[:2] == ["pr", "list"]:
    print(json.dumps(json.loads(os.environ.get("FAKE_GH_PULLS", "[]"))))
elif argv[:2] == ["pr", "view"]:
    number = argv[2]
    # A test can break just THIS one call -- a transient read failure on the
    # open thread's own detail -- while `pr list` above keeps answering, which
    # is what a real momentary read failure looks like (unlike the host being
    # entirely missing, which fails every call the same way).
    if os.environ.get("FAKE_GH_BREAK_VIEW") == "1":
        sys.stderr.write("stand-in host: pr view deliberately made to fail for this test\\n")
        sys.exit(1)
    pulls = json.loads(os.environ.get("FAKE_GH_PULLS", "[]"))
    match = next((p for p in pulls if str(p["number"]) == str(number)), None)
    if match is None:
        sys.stderr.write("no such pull request: %s\\n" % number)
        sys.exit(1)
    one = dict(match)
    one["comments"] = json.loads(os.environ.get("FAKE_GH_COMMENTS", "[]"))
    print(json.dumps(one))
elif argv[:2] == ["pr", "comment"]:
    print("https://host.invalid/demo/pull/%s#issuecomment-1" % argv[2])
else:
    sys.stderr.write("stand-in host asked something it does not answer: %r\\n" % (argv,))
    sys.exit(1)
'''

CONVERGE_SHAPED_BODY = """## The exact change

- Core 4 gains a sentence about comments arriving both ways.
- The word "bridge" is defined once, in Core 4.

## The evidence

- A steward copied an answer between two tools four times in one week.
- One of those four answers reached the wrong pull request.

## What does not change

Git stays the protocol, and nothing about the write path moves.
"""

#: An ORDINARY pull request: real headings of its own, none of them the
#: three-part Converge shape, a table, a fenced code block, a link, four-plus
#: paragraphs, and -- pasted by a careless or hostile author -- a raw
#: `<script>` tag and a `javascript:` link. converge-ibxt is about exactly
#: this shape: nothing here is "the change" or "the evidence" to a reader that
#: only knows Converge's own headings, and none of it may be lost or executed.
ORDINARY_BODY = """# Doc-only follow-up to #62 -- the lane note now matches what main does

This paragraph is the first of four, and it must survive completely: it
explains why the earlier note went stale the moment main moved, and why
nobody caught it for two weeks.

## What this PR corrects

The lane note claimed a check that main no longer runs. This paragraph is the
second of four, and names the exact sentence that was wrong and why.

## The gate this PR runs under

| check | result |
|---|---|
| lint | pass |
| tests | pass |

```
uv run pytest -q
6 passed in 1.02s
```

This paragraph is the third of four, sitting after the table and the code
block, and must still be reachable -- see https://example.com/evidence for
the terminal transcript this refers to.

This is the fourth and final paragraph, deliberately placed last so a reader
who only sees the first four can be told the truth: there is no artificial
cutoff, so a fifth would matter here too if there were one.

<script>window.__xss__ = true;</script>
[click me](javascript:window.__xss__ = true)
"""

EMPTY_BODY = ""


def _pull_fixture(number: int, title: str, body: str, author: str = "wren") -> dict:
    return {
        "number": number,
        "title": title,
        "body": body,
        "author": {"login": author},
        "url": f"https://host.invalid/demo/pull/{number}",
        "updatedAt": "2026-09-04T09:00:00Z",
        "headRefName": f"{author}/lane-{number}",
        "isDraft": False,
    }


# --------------------------------------------------------------------------
# a repository and an app around it
# --------------------------------------------------------------------------
def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "user.name=Test", "-c", "user.email=test@example.invalid", *args],
        cwd=repo, check=True, capture_output=True,
    )


def _make_project(tmp_path: Path, repos: list[Path]) -> dict:
    for repo in repos:
        (repo / "docs" / "workflow").mkdir(parents=True)
        (repo / "docs" / "VISION.md").write_text("# Demo Vision (DRAFT)\n\nOne place.\n", encoding="utf-8")
        _git(repo, "init", "-q", "-b", "main")
        _git(repo, "add", "-A")
        _git(repo, "commit", "-q", "-m", "seed: the vision")

    batch = tmp_path / "hw-demo"
    (batch / "goals").mkdir(parents=True)
    (batch / "HIGHWAY.md").write_text("# HIGHWAY\n\n## Outcome\nProve the PR journey.\n", encoding="utf-8")
    (batch / ".width").write_text("4\n", encoding="utf-8")
    (batch / "manifest.tsv").write_text("lane\tworktree\tbranch\n", encoding="utf-8")

    conf = tmp_path / "converge-app.toml"
    repo_list = ", ".join(f'"{r}"' for r in repos)
    conf.write_text(
        "[[managers]]\n"
        'id = "demo"\n'
        'name = "Demo manager"\n'
        f'batch_dir = "{batch}"\n'
        f'repos = [{repo_list}]\n'
        'tmux_socket = "collab-journey-socket-that-does-not-exist"\n'
        f'steward = "{USER}"\n',
        encoding="utf-8",
    )
    return {
        "config": conf, "secret": tmp_path / "secret", "state": tmp_path / "state.json",
        "sessions": tmp_path / "sessions.json", "repos": repos,
    }


@pytest.fixture(scope="module")
def project(tmp_path_factory) -> dict:
    """One repository. Every test except the cross-repo id-collision one uses
    this -- a second repository would give every single-PR fixture below TWO
    identical-looking rows (the stand-in host answers the same list for any
    repo that asks it), which is not what those tests are about."""
    tmp_path = tmp_path_factory.mktemp("collab-journey")
    return _make_project(tmp_path, [tmp_path / "repo-a"])


@pytest.fixture(scope="module")
def two_repo_project(tmp_path_factory) -> dict:
    """Two repositories, one manager -- exactly the shape converge-xet9's
    "second repo sharing a PR number" case needs, and only that case."""
    tmp_path = tmp_path_factory.mktemp("collab-journey-two-repo")
    return _make_project(tmp_path, [tmp_path / "repo-a", tmp_path / "repo-b"])


@pytest.fixture(scope="module")
def same_basename_project(tmp_path_factory) -> dict:
    """Two DIFFERENT repositories that happen to share ONE basename -- the
    CONFIRMED FAILURE this lane's brief names: `/a/repo` and `/b/repo` both
    answered to the identifier "repo" under `data.repo_id` (`Path(repo).name`),
    so both listed the same PR under one colliding id and a request naming
    that id could not say which repository it meant. `two_repo_project`
    above (`repo-a`/`repo-b`) has DIFFERENT basenames and never exercised
    this -- it proves id-uniqueness only by construction, not the actual
    reported shape. This fixture is the one that does."""
    tmp_path = tmp_path_factory.mktemp("collab-journey-same-basename")
    repo_a = tmp_path / "loc-a" / "repo"
    repo_b = tmp_path / "loc-b" / "repo"
    return _make_project(tmp_path, [repo_a, repo_b])


@pytest.fixture(scope="module")
def same_basename_server(same_basename_project):
    uv_server, thread, url = _start_server(same_basename_project)
    yield url
    uv_server.should_exit = True
    thread.join(timeout=10)


@pytest.fixture
def host(tmp_path: Path, monkeypatch):
    """`gh` on `$PATH`, answering from env vars this test can change mid-run."""
    binaries = tmp_path / "bin"
    binaries.mkdir()
    tool = binaries / "gh"
    tool.write_text(FAKE_GH, encoding="utf-8")
    tool.chmod(0o755)
    log = tmp_path / "gh-calls.jsonl"
    monkeypatch.setenv("PATH", f"{binaries}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv("FAKE_GH_LOG", str(log))
    monkeypatch.setenv("FAKE_GH_PULLS", "[]")
    monkeypatch.setenv("FAKE_GH_COMMENTS", "[]")
    monkeypatch.delenv("FAKE_GH_COMMENTS", raising=False)

    def set_pulls(pulls: list[dict]) -> None:
        monkeypatch.setenv("FAKE_GH_PULLS", json.dumps(pulls))

    def set_comments(comments: list[dict]) -> None:
        monkeypatch.setenv("FAKE_GH_COMMENTS", json.dumps(comments))

    def break_host() -> None:
        """Simulate a host that cannot be reached: `gh` refuses on $PATH."""
        monkeypatch.setenv("PATH", str(tmp_path / "no-gh-here"))

    def break_view() -> None:
        """Simulate a transient read failure on ONE request (`pr view`) only
        -- `pr list` keeps answering. `page.route` cannot stand in for this:
        this app's service worker owns fetches before Playwright's page-level
        routing ever sees them (AGENTS.md's own app-verification lesson), so
        the fault has to be injected on the server side, not the network."""
        monkeypatch.setenv("FAKE_GH_BREAK_VIEW", "1")

    return {
        "set_pulls": set_pulls, "set_comments": set_comments,
        "break_host": break_host, "break_view": break_view,
    }


# --------------------------------------------------------------------------
# a stand-in host that answers PER REPOSITORY -- what the same-basename /
# cross-repo write / race proof needs and the single-fixture `host` above
# cannot give it (that one answers ONE fixed list no matter which repository
# asked, which is fine for tests about the client only, but this lane's
# brief explicitly asks for "different bodies/conversations per cwd" and
# "log actual cwd/PR for list/view/comment/answer" -- a same-ID list
# assertion alone is not a cross-repository post-destination check).
# --------------------------------------------------------------------------
FAKE_GH_MULTI = '''#!/usr/bin/env python3
import json, os, sys, time

argv = sys.argv[1:]
cwd = os.path.realpath(os.getcwd())
log = os.environ.get("FAKE_GH_LOG")
if log:
    with open(log, "a", encoding="utf-8") as out:
        out.write(json.dumps({"argv": argv, "cwd": cwd}) + "\\n")

by_cwd = json.loads(os.environ.get("FAKE_GH_BY_CWD", "{}"))
here = by_cwd.get(cwd, {"pulls": [], "comments": []})

delay_secs = float(os.environ.get("FAKE_GH_DELAY_SECONDS", "0") or 0)
delay_cwd = os.environ.get("FAKE_GH_DELAY_CWD", "")
# "view" (default, back-compat) delays `pr view` -- the open thread's own
# detail read, i.e. the GET/quiet-refresh race. "comment" delays `pr comment`
# -- what BOTH `postQuestion`'s comment route and `answer`'s post-back-to-
# origin route actually call, i.e. the POST-completion race.
delay_kind = os.environ.get("FAKE_GH_DELAY_KIND", "view")

def maybe_delay(kind: str) -> None:
    # Delay applies ONLY to the one call kind under test, and ONLY for the
    # one repository under test -- every other call, and every call to a
    # repository not being delayed, answers immediately, which is what a
    # genuinely slow single request looks like.
    if delay_secs > 0 and delay_cwd and cwd == delay_cwd and kind == delay_kind:
        time.sleep(delay_secs)

if argv[:2] == ["pr", "list"]:
    print(json.dumps(here.get("pulls", [])))
elif argv[:2] == ["pr", "view"]:
    maybe_delay("view")
    number = argv[2]
    pulls = here.get("pulls", [])
    match = next((p for p in pulls if str(p["number"]) == str(number)), None)
    if match is None:
        sys.stderr.write("no such pull request: %s in %s\\n" % (number, cwd))
        sys.exit(1)
    one = dict(match)
    one["comments"] = here.get("comments", [])
    print(json.dumps(one))
elif argv[:2] == ["pr", "comment"]:
    maybe_delay("comment")
    print("https://host.invalid/%s/pull/%s#issuecomment-1" % (os.path.basename(cwd), argv[2]))
else:
    sys.stderr.write("stand-in host asked something it does not answer: %r\\n" % (argv,))
    sys.exit(1)
'''


@pytest.fixture
def multi_repo_host(tmp_path: Path, monkeypatch):
    """`gh` on `$PATH`, answering differently depending on which real
    repository directory it was run in -- and logging that real directory
    (never just the argv) for every call, so a test can assert WHERE a
    comment landed, not only that one landed somewhere."""
    binaries = tmp_path / "bin-multi"
    binaries.mkdir()
    tool = binaries / "gh"
    tool.write_text(FAKE_GH_MULTI, encoding="utf-8")
    tool.chmod(0o755)
    log = tmp_path / "gh-calls-multi.jsonl"
    monkeypatch.setenv("PATH", f"{binaries}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv("FAKE_GH_LOG", str(log))
    monkeypatch.setenv("FAKE_GH_BY_CWD", "{}")
    monkeypatch.delenv("FAKE_GH_DELAY_SECONDS", raising=False)
    monkeypatch.delenv("FAKE_GH_DELAY_CWD", raising=False)
    monkeypatch.delenv("FAKE_GH_DELAY_KIND", raising=False)

    def set_by_cwd(mapping: dict) -> None:
        """`{str(repo path): {"pulls": [...], "comments": [...]}}`, keyed by
        each repository's own CANONICAL path -- the same normalization
        `app/collab.py`'s `_repo_key` uses, so the stand-in and the app never
        disagree about which directory a repository actually is."""
        keyed = {str(Path(k).resolve()): v for k, v in mapping.items()}
        monkeypatch.setenv("FAKE_GH_BY_CWD", json.dumps(keyed))

    def set_delay(repo_path, seconds: float, kind: str = "view") -> None:
        """`kind="view"` (default) delays the GET detail read; `kind="comment"`
        delays `pr comment` -- the call both the ask-a-question route and the
        answer route's post-back-to-origin actually make, i.e. the POST-
        completion race."""
        monkeypatch.setenv("FAKE_GH_DELAY_CWD", str(Path(repo_path).resolve()))
        monkeypatch.setenv("FAKE_GH_DELAY_SECONDS", str(seconds))
        monkeypatch.setenv("FAKE_GH_DELAY_KIND", kind)

    def calls() -> list[dict]:
        if not log.exists():
            return []
        return [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines() if line.strip()]

    return {"set_by_cwd": set_by_cwd, "set_delay": set_delay, "calls": calls}


def _free_port() -> int:
    s = socketlib.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def _start_server(project: dict):
    import uvicorn

    made = serve.create_app(
        config_path=project["config"], secret_path=project["secret"],
        state_path=project["state"], sessions_path=project["sessions"],
    )
    made.include_router(collab.router)
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
    return uv_server, thread, f"http://127.0.0.1:{port}"


@pytest.fixture(scope="module")
def server(project):
    uv_server, thread, url = _start_server(project)
    yield url
    uv_server.should_exit = True
    thread.join(timeout=10)


@pytest.fixture(scope="module")
def two_repo_server(two_repo_project):
    uv_server, thread, url = _start_server(two_repo_project)
    yield url
    uv_server.should_exit = True
    thread.join(timeout=10)


@pytest.fixture(scope="module")
def browser():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        b = p.chromium.launch(args=["--no-sandbox"])
        yield b
        b.close()


@pytest.fixture(autouse=True)
def _forget_arrivals():
    collab.ARRIVALS.__init__()
    yield
    collab.ARRIVALS.__init__()


# --------------------------------------------------------------------------
# driving
# --------------------------------------------------------------------------
def _installed(browser, server, project, width=1280, height=800):
    sessions = auth.Sessions(auth.read_or_make_secret(project["secret"]))
    ctx = browser.new_context(viewport={"width": width, "height": height})
    ctx.add_cookies([{"name": auth.COOKIE, "value": sessions.issue(USER),
                      "domain": "127.0.0.1", "path": "/"}])
    page = ctx.new_page()
    errors: list[str] = []
    page.on("console", lambda m: errors.append(f"console.{m.type}: {m.text}") if m.type == "error" else None)
    page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
    page.on("dialog", lambda d: (errors.append(f"a JS dialog fired: {d.message}"), d.dismiss()))

    page.goto(server, wait_until="networkidle")
    page.wait_for_selector(".home-manager-card", timeout=15000)
    page.click(".home-manager-card")
    page.wait_for_selector("#directionTab", timeout=15000)
    page.click("#directionTab")
    page.wait_for_selector("#documentModeContent", timeout=15000)
    return ctx, page, errors


def _close_console_if_covering(page, width: int) -> None:
    """Below 980px the console is a fixed sheet over the whole page (shell's
    own, intentional behaviour -- see AGENTS.md's app-verification lessons).
    Closing it is one ordinary, visible click, not a workaround."""
    if width < 980:
        page.click("#consoleToggle")
        page.wait_for_timeout(400)
        if page.eval_on_selector("#consoleToggle", "el => el.getAttribute('aria-pressed')") == "true":
            # One click did not close it (a slow first render can still be
            # animating in) -- try once more rather than fail on timing.
            page.click("#consoleToggle")
            page.wait_for_timeout(400)


def _open_panel(page) -> None:
    is_open = page.eval_on_selector("#collabPanel", "el => el.open")
    if not is_open:
        page.click("#collabPanel > summary")
    page.wait_for_selector(".collab-row", timeout=8000)


PANEL_GEOMETRY = """
() => {
  const el = document.getElementById('collabPanel');
  if (!el) return null;
  const box = el.getBoundingClientRect();
  return {
    inSurface: !!el.closest('#documentSurface'),
    inRail: !!el.closest('#contextRail'),
    visible: box.width > 0 && box.height > 0,
  };
}
"""


# --------------------------------------------------------------------------
# converge-vtkw -- reachable, at every width this app supports
# --------------------------------------------------------------------------
@needs_browser
@pytest.mark.parametrize("width,height", [(1440, 900), (1280, 800), (390, 844)])
def test_the_pr_panel_is_reachable_by_ordinary_clicks_at_every_width(server, project, browser, host, width, height):
    host["set_pulls"]([_pull_fixture(1, "A small PR", CONVERGE_SHAPED_BODY)])
    ctx, page, errors = _installed(browser, server, project, width, height)
    _close_console_if_covering(page, width)

    geometry = page.evaluate(PANEL_GEOMETRY)
    print(f"\n[{width}] collabPanel geometry: {geometry}")
    assert geometry is not None, "the collab panel is not on the page at all"
    assert geometry["inSurface"] and not geometry["inRail"], (
        f"the collab panel is not inside .document-surface (or is still inside "
        f".context-rail, which direction.css hides at <=1320px): {geometry}"
    )
    assert geometry["visible"], f"the collab panel has no visible box at {width}px: {geometry}"

    _open_panel(page)
    page.click(".collab-row")
    page.wait_for_selector("#collabQuestion", timeout=8000)
    composer = page.eval_on_selector(
        "#collabQuestion",
        "el => { const r = el.getBoundingClientRect(); return {w: r.width, h: r.height, value: el.value}; }",
    )
    print(f"[{width}] composer: {composer}")
    assert composer["w"] > 0 and composer["h"] > 0, f"the composer has no visible box at {width}px: {composer}"
    assert composer["value"] == "", "the composer was not empty on first reaching it"
    assert not errors, f"the browser reported errors: {errors}"
    ctx.close()


@needs_browser
@pytest.mark.parametrize("width,height", [(1440, 900), (1280, 800)])
def test_the_pr_panel_is_reachable_with_the_console_explicitly_closed(server, project, browser, host, width, height):
    host["set_pulls"]([_pull_fixture(1, "A small PR", CONVERGE_SHAPED_BODY)])
    ctx, page, errors = _installed(browser, server, project, width, height)
    page.click("#consoleToggle")
    page.wait_for_timeout(300)

    geometry = page.evaluate(PANEL_GEOMETRY)
    assert geometry is not None and geometry["visible"], (
        f"closing the console at {width}px hid the collab panel: {geometry}"
    )
    _open_panel(page)
    assert not errors, f"the browser reported errors: {errors}"
    ctx.close()


#: `sel => hit-test result` -- present in the DOM and a non-empty box are
#: NOT the same fact as reachable by a real tap: `document.elementFromPoint`
#: at the element's own center is what a finger actually lands on, so this
#: catches the console's fixed overlay sitting on top of something that is
#: otherwise perfectly attached and perfectly sized (AGENTS.md's own lesson:
#: "Hidden DOM nodes ... are not rendered UI").
HIT_TEST = """
(sel) => {
  const target = document.querySelector(sel);
  if (!target) return { present: false };
  const r = target.getBoundingClientRect();
  if (r.width <= 0 || r.height <= 0) return { present: true, visibleBox: false };
  const cx = r.left + r.width / 2, cy = r.top + r.height / 2;
  const hit = document.elementFromPoint(cx, cy);
  const reachable = !!(hit && (hit === target || target.contains(hit) || (hit.closest && hit.closest(sel) === target)));
  return { present: true, visibleBox: true, reachable, rect: { x: r.x, y: r.y, w: r.width, h: r.height } };
}
"""


@needs_browser
def test_the_mobile_console_state_is_explicit_and_closing_it_reaches_the_pr_review(
    server, project, browser, host, tmp_path
):
    """converge-xet9 MOBILE EVIDENCE.

    `test_the_pr_panel_is_reachable_by_ordinary_clicks_at_every_width`'s 390px
    case calls `_close_console_if_covering` BEFORE looking at the page at
    all, so its "reachable at 390" claim never actually observed the
    console's OWN state on arrival -- it silently closed the console first,
    whatever that state was.

    This test does not. It measures first, rather than assuming: `state.js`
    ships `consoleOpen: false` (converge-t30q) and nothing in the ordinary
    Home-to-Direction path this lane's helper drives (`_installed`) flips it
    -- so the ACTUAL default at 390px, observed rather than presumed, is
    CLOSED, and the PR panel is reachable immediately with no gesture at all.
    That is itself evidence worth recording plainly rather than silently
    assuming the opposite (as the older helper's name -- "close ... if it
    covers" -- did). The second, genuinely covering state this lane's brief
    asks about is reached by explicitly opening the console (the same
    ordinary tap a steward who taps "Manager Console" makes) -- proving that
    is ALSO real, that it DOES cover the panel at this width (`console.css`'s
    own `position:fixed` rule, not a redesign target), and that the same
    ordinary close gesture restores reachability, a real focused composer,
    and the ability to draft -- never a forced CSS state, a hidden-node
    read, or a click on something still covered.
    """
    host["set_pulls"]([_pull_fixture(11, "Mobile-reachable PR", CONVERGE_SHAPED_BODY)])
    ctx, page, errors = _installed(browser, server, project, width=390, height=844)

    evidence_dir = Path(os.environ.get("COLLAB_MOBILE_EVIDENCE_DIR") or tmp_path)
    evidence_dir.mkdir(parents=True, exist_ok=True)

    # 1. State ON ARRIVAL -- measured, not assumed. Observed: closed.
    initial_pressed = page.eval_on_selector("#consoleToggle", "el => el.getAttribute('aria-pressed')")
    print(f"\n[390] console aria-pressed on arrival: {initial_pressed!r}")
    arrival_hit = page.evaluate(HIT_TEST, "#collabPanel > summary")
    print(f"[390] collabPanel summary hit-test on arrival: {arrival_hit}")
    arrival_shot = evidence_dir / "mobile-390-console-arrival.png"
    page.screenshot(path=str(arrival_shot))
    print(f"[390] screenshot (arrival state, console {initial_pressed}): {arrival_shot}")

    if initial_pressed == "false":
        # The console's OWN default does not cover the panel at this width --
        # reachable with no gesture at all. Recorded as a fact, not skipped.
        assert arrival_hit["present"] and arrival_hit["visibleBox"] and arrival_hit["reachable"], (
            f"the console reports closed (aria-pressed=false) but the PR panel is still not "
            f"reachable by a real hit-test: {arrival_hit}"
        )

    # 2. Explicitly OPEN the console -- the same ordinary tap a steward who
    # taps "Manager Console" makes -- and confirm this app's own, intentional
    # mobile behaviour: it becomes a position:fixed overlay (console.css)
    # that DOES cover the panel. This is not asserted as a defect; it is the
    # documented, unredesigned starting point for the close-gesture proof.
    page.click("#consoleToggle")
    page.wait_for_function(
        "() => document.getElementById('consoleToggle').getAttribute('aria-pressed') === 'true'",
        timeout=4000,
    )
    opened_hit = page.evaluate(HIT_TEST, "#collabPanel > summary")
    print(f"[390] collabPanel summary hit-test with console explicitly OPENED: {opened_hit}")
    opened_shot = evidence_dir / "mobile-390-console-open.png"
    page.screenshot(path=str(opened_shot))
    print(f"[390] screenshot (console explicitly open): {opened_shot}")
    if not opened_hit["reachable"]:
        print("[390] confirmed: the open console overlays the PR panel at this width -- "
              "reported as this app's existing, intentional mobile behaviour, not redesigned here.")

    # 3. The visible, ordinary close gesture.
    page.click("#consoleToggle")
    page.wait_for_function(
        "() => document.getElementById('consoleToggle').getAttribute('aria-pressed') === 'false'",
        timeout=4000,
    )
    closed_pressed = page.eval_on_selector("#consoleToggle", "el => el.getAttribute('aria-pressed')")
    assert closed_pressed == "false", f"the ordinary close gesture did not close the console: {closed_pressed!r}"

    closed_hit = page.evaluate(HIT_TEST, "#collabPanel > summary")
    print(f"[390] collabPanel summary hit-test with console CLOSED again: {closed_hit}")
    assert closed_hit["present"] and closed_hit["visibleBox"] and closed_hit["reachable"], (
        f"closing the console did not make the PR panel reachable by a real hit-test, "
        f"not just DOM attachment: {closed_hit}"
    )

    # 4. Reach an empty, focused composer with ordinary clicks -- review is
    # not merely present, it is usable, and gains real keyboard focus, and a
    # draft can actually be typed -- proving reachability restores real work,
    # not just an empty box.
    _open_panel(page)
    page.click(".collab-row")
    page.wait_for_selector("#collabQuestion", timeout=8000)
    # The composer sits well down a narrow page (ordinary scrollable content,
    # not a console-covering defect) -- scroll it into view exactly as a
    # steward's own finger-scroll would, THEN hit-test, so this proves real
    # reachability rather than failing on an off-screen coordinate that no
    # scrolled tap would ever land on either.
    page.eval_on_selector("#collabQuestion", "el => el.scrollIntoView({block: 'center'})")
    composer_hit = page.evaluate(HIT_TEST, "#collabQuestion")
    print(f"[390] composer hit-test (after scrolling into view): {composer_hit}")
    assert composer_hit["present"] and composer_hit["visibleBox"] and composer_hit["reachable"], (
        f"the composer is present but not actually reachable by a real tap, even scrolled into view: {composer_hit}"
    )

    page.click("#collabQuestion")
    page.fill("#collabQuestion", "Drafted after closing the console.")
    focused_id = page.evaluate("() => document.activeElement && document.activeElement.id")
    draft_value = page.eval_on_selector("#collabQuestion", "el => el.value")
    print(f"[390] focused element after reaching the composer: {focused_id!r}, draft: {draft_value!r}")
    assert focused_id == "collabQuestion", f"focus did not land in the composer: {focused_id!r}"
    assert draft_value == "Drafted after closing the console.", draft_value

    closed_shot = evidence_dir / "mobile-390-console-closed-composer.png"
    page.screenshot(path=str(closed_shot))
    print(f"[390] screenshot (console closed, composer focused): {closed_shot}")

    assert not errors, f"the browser reported errors: {errors}"
    ctx.close()


@needs_browser
def test_a_host_with_no_gh_available_says_so_rather_than_leaving_a_blank_panel(server, project, browser, host):
    host["break_host"]()
    ctx, page, errors = _installed(browser, server, project)
    page.wait_for_timeout(1200)
    _open_panel_summary_only = page.click("#collabPanel > summary")
    page.wait_for_timeout(300)
    trouble = page.eval_on_selector("#collabTrouble", "el => ({hidden: el.hidden, text: el.textContent})")
    print(f"\ntrouble line: {trouble}")
    assert trouble["hidden"] is False, "no host means the panel must say so, not sit blank"
    assert "gh" in trouble["text"] and "not installed" in trouble["text"]
    ctx.close()


# --------------------------------------------------------------------------
# converge-ibxt -- the complete, original, safe reading
# --------------------------------------------------------------------------
@needs_browser
def test_an_ordinary_pr_body_is_shown_whole_safe_and_honestly_labelled(server, project, browser, host):
    host["set_pulls"]([_pull_fixture(2, "Doc-only follow-up to #62", ORDINARY_BODY)])
    ctx, page, errors = _installed(browser, server, project)
    _open_panel(page)
    page.click(".collab-row")
    page.wait_for_selector(".collab-body-render", timeout=8000)

    text = page.eval_on_selector("#collabReview", "el => el.innerText")
    print("\nrendered review text (first 300 chars):", text[:300])

    # All four paragraphs, not just the first four sentences -- and not
    # truncated anywhere, per this lane's brief.
    for said in (
        "This paragraph is the first of four",
        "This paragraph is the second of four",
        "This paragraph is the third of four",
        "This is the fourth and final paragraph",
    ):
        assert said in text, f"the full PR body lost a paragraph: {said!r} is missing"

    # The honest label, replacing the old false claim.
    assert "does not use headings this reader recognizes" in text
    assert "No evidence was attached to this pull request" not in text

    # The table and the code block rendered as real elements, not raw pipes
    # or literal backticks.
    table = page.eval_on_selector_all(".collab-body-render table td", "els => els.map(e => e.textContent.trim())")
    assert "pass" in table, f"the table did not render as a real <table>: {table}"
    code = page.eval_on_selector(".collab-body-render pre", "el => !!el")
    assert code, "the fenced code block did not render as a real <pre>"

    # Safety: the raw <script> must never execute, and the javascript: link
    # must never become clickable.
    xss = page.evaluate("() => window.__xss__ === true")
    assert xss is not True, "a script embedded in the PR body executed"
    js_link = page.eval_on_selector_all(
        ".collab-body-render a", "els => els.map(e => e.getAttribute('href'))"
    )
    assert not any((h or "").startswith("javascript:") for h in js_link), (
        f"a javascript: link was rendered as a real, clickable link: {js_link}"
    )
    assert not errors, f"the browser reported errors: {errors}"
    ctx.close()


@needs_browser
def test_a_converge_shaped_pr_shows_the_quick_view_with_the_full_body_one_click_away(server, project, browser, host):
    host["set_pulls"]([_pull_fixture(3, "Say comments travel both ways", CONVERGE_SHAPED_BODY)])
    ctx, page, errors = _installed(browser, server, project)
    _open_panel(page)
    page.click(".collab-row")
    # `#collabReview` is the ALWAYS-present container (it holds the "Choose a
    # pull request..." placeholder too), so waiting for it proves nothing --
    # `.collab-hero` is drawn only once `drawProposal` has a real proposal in
    # hand, after the detail fetch actually resolves.
    page.wait_for_selector(".collab-hero", timeout=8000)

    text = page.eval_on_selector("#collabReview", "el => el.innerText")
    assert "Core 4 gains a sentence about comments arriving both ways." in text
    assert "did not use a heading this reader recognizes" not in text

    # The full body sits behind a native disclosure, collapsed by default --
    # present for verification, not duplicated inline beside the bullets that
    # already say the same thing.
    disclosure = page.eval_on_selector(".collab-fullbody", "el => ({open: el.open, present: true})")
    assert disclosure["present"] and disclosure["open"] is False, (
        f"the full body disclosure should exist, collapsed by default: {disclosure}"
    )
    page.click(".collab-fullbody > summary")
    full_text = page.eval_on_selector(".collab-fullbody", "el => el.innerText")
    assert "Git stays the protocol" in full_text
    assert not errors, f"the browser reported errors: {errors}"
    ctx.close()


@needs_browser
def test_an_empty_pr_body_says_so_rather_than_rendering_nothing(server, project, browser, host):
    host["set_pulls"]([_pull_fixture(4, "No description written", EMPTY_BODY)])
    ctx, page, errors = _installed(browser, server, project)
    _open_panel(page)
    page.click(".collab-row")
    page.wait_for_selector(".collab-hero", timeout=8000)
    text = page.eval_on_selector("#collabReview", "el => el.innerText")
    assert "no description" in text.lower(), f"an empty PR body rendered no honest statement: {text!r}"
    assert not errors, f"the browser reported errors: {errors}"
    ctx.close()


# --------------------------------------------------------------------------
# converge-xet9 -- keying, and a background refresh that loses nothing
# --------------------------------------------------------------------------
@needs_browser
def test_two_repositories_sharing_a_pr_number_are_never_collapsed_into_one_row(
    two_repo_server, two_repo_project, browser, host
):
    host["set_pulls"]([
        _pull_fixture(7, "Repo A's own #7", "Body for repo A.", author="alice"),
    ])
    # The stand-in host answers ONE fixed list regardless of which repo asked,
    # which is a limitation of this test double, not of the app: the real
    # defect under test is client-side (whether two rows with the same
    # server-shaped id collapse into one), so the id-uniqueness fix is what
    # this test actually exercises. See app/collab.py's `proposal_from_pull`.
    # `two_repo_project`/`two_repo_server` register BOTH repositories under
    # one manager, which is exactly the shape that used to collide.
    ctx, page, errors = _installed(browser, two_repo_server, two_repo_project)
    _open_panel(page)
    rows = page.eval_on_selector_all(".collab-row", "els => els.map(e => e.dataset.pull)")
    print(f"\nrow ids: {rows}")
    assert len(rows) == len(set(rows)), f"two rows share one id, which means they cannot both be selected: {rows}"
    for row_id in rows:
        assert "::pull-" in row_id, f"a row id is not repo-qualified, so a same-numbered PR in another repo would collide: {row_id!r}"
    ctx.close()


@needs_browser
def test_same_basename_repositories_post_to_the_right_directory_not_just_a_distinct_id(
    same_basename_server, same_basename_project, browser, multi_repo_host
):
    """The CONFIRMED FAILURE, reproduced exactly: two repositories at
    different locations, both named ``repo`` (``loc-a/repo`` and
    ``loc-b/repo``), both carrying their own pull request #7. `data.repo_id`
    (`Path(repo).name`) answered "repo" for both, so both listed under one
    colliding `repo::pull-7`. `_repo_key` (a canonical-path-derived key) is
    what this test actually exercises.

    A same-ID list assertion alone is not a cross-repository post-destination
    check (this lane's brief, verbatim) -- so beyond the row ids being
    distinct, this test selects the SECOND row and posts a real question, then
    reads back the stand-in host's own log to prove the comment reached the
    SECOND repository's real, on-disk directory -- never the first, and never
    both.
    """
    repo_a, repo_b = same_basename_project["repos"]
    key_a, key_b = str(Path(repo_a).resolve()), str(Path(repo_b).resolve())
    multi_repo_host["set_by_cwd"]({
        repo_a: {"pulls": [_pull_fixture(7, "Repo A's own #7", "Body for repo A.", author="alice")]},
        repo_b: {"pulls": [_pull_fixture(7, "Repo B's own #7", "Body for repo B.", author="bob")]},
    })
    ctx, page, errors = _installed(browser, same_basename_server, same_basename_project)
    _open_panel(page)

    titles = page.eval_on_selector_all(".collab-row strong", "els => els.map(e => e.textContent)")
    rows = page.eval_on_selector_all(".collab-row", "els => els.map(e => e.dataset.pull)")
    print(f"\ntitles: {titles}\nrow ids: {rows}")
    assert titles == ["Repo A's own #7", "Repo B's own #7"], titles
    assert len(rows) == len(set(rows)), f"same-basename repositories collapsed into one row id: {rows}"
    for row_id in rows:
        assert "::pull-" in row_id, row_id

    # Select the SECOND row and prove the review shown is really repo B's.
    page.click(".collab-row >> nth=1")
    page.wait_for_selector(".collab-hero", timeout=8000)
    text = page.eval_on_selector("#collabReview", "el => el.innerText")
    assert "Body for repo B" in text, text

    page.fill("#collabQuestion", "Which real directory does this reach?")
    page.click("[data-collab-ask]")
    page.wait_for_function(
        "() => (document.getElementById('collabOutcome') || {}).textContent && "
        "document.getElementById('collabOutcome').textContent.includes('Posted')",
        timeout=8000,
    )

    posted = [c for c in multi_repo_host["calls"]() if c["argv"][:2] == ["pr", "comment"]]
    assert len(posted) == 1, posted
    assert posted[0]["cwd"] == key_b, (
        f"the comment from the SECOND row reached the wrong repository -- "
        f"expected {key_b!r}, got {posted[0]['cwd']!r} (repo A is {key_a!r})"
    )
    assert not errors, f"the browser reported errors: {errors}"
    ctx.close()


@needs_browser
def test_a_delayed_stale_response_cannot_render_or_post_into_a_repo_the_steward_switched_away_from(
    same_basename_server, same_basename_project, browser, multi_repo_host
):
    """The race this lane's brief asks for, in full: select the second row,
    type both drafts, inject an ACTUALLY delayed response (a real server-side
    sleep in the stand-in host, never `page.route` -- this app's own service
    worker owns fetches before Playwright's page-level routing ever sees them,
    AGENTS.md's own app-verification lesson), switch to a DIFFERENT
    repository entirely while that response is still in flight, release it by
    waiting past its delay, and prove the stale response neither rendered
    over the new selection nor could redirect a live post to the wrong
    repository.
    """
    repo_a, repo_b = same_basename_project["repos"]
    key_a, key_b = str(Path(repo_a).resolve()), str(Path(repo_b).resolve())
    multi_repo_host["set_by_cwd"]({
        repo_a: {"pulls": [_pull_fixture(9, "Repo A's own #9", "Body for repo A, PR nine.", author="alice")]},
        repo_b: {"pulls": [_pull_fixture(9, "Repo B's own #9", "Body for repo B, PR nine.", author="bob")]},
    })
    ctx, page, errors = _installed(browser, same_basename_server, same_basename_project)
    _open_panel(page)

    # Select the SECOND row (repo B) and start both drafts.
    page.click(".collab-row >> nth=1")
    page.wait_for_selector("#collabQuestion", timeout=8000)
    opened_text = page.eval_on_selector("#collabReview", "el => el.innerText")
    assert "Body for repo B" in opened_text, opened_text
    page.fill("#collabQuestion", "A question meant for repo B only.")
    page.fill("#collabNote", "A decision note meant for repo B only.")

    # Make repo B's OWN detail read genuinely slow, then trigger one poll
    # tick WITHOUT waiting for it -- `window.__collabRefresh()` returns a
    # promise; calling it without awaiting/returning that promise from the
    # evaluated function lets this Python call return immediately, exactly
    # like Playwright never blocking on a real background timer.
    multi_repo_host["set_delay"](repo_b, 3.0)
    page.evaluate("() => { window.__collabRefresh(); return true; }")
    page.wait_for_timeout(300)  # let the delayed request actually start

    # Switch away WHILE that response is still pending -- a different
    # REPOSITORY entirely, not just a different PR in the same one.
    page.click(".collab-row >> nth=0")
    page.wait_for_function(
        "() => (document.getElementById('collabReview') || {}).innerText && "
        "document.getElementById('collabReview').innerText.includes('Body for repo A')",
        timeout=8000,
    )

    # Release: wait past repo B's delay so its stale response actually lands
    # at the client, late, in the background.
    page.wait_for_timeout(3500)

    # It must not have rendered over the new (repo A) selection.
    text_after = page.eval_on_selector("#collabReview", "el => el.innerText")
    assert "Body for repo A" in text_after, text_after
    assert "Body for repo B" not in text_after, (
        "a stale response from the repository the steward switched away from "
        f"rendered over the new selection: {text_after!r}"
    )

    # Prove the delayed round trip to repo B genuinely completed late --
    # this is not "it never got there", it is "it got there after, and was
    # still correctly ignored".
    view_calls_b = [
        c for c in multi_repo_host["calls"]()
        if c["argv"][:2] == ["pr", "view"] and c["cwd"] == key_b
    ]
    assert view_calls_b, "the delayed repo-B detail request never actually reached the host"

    # Post from the CURRENTLY open thread (repo A) and prove it reaches repo
    # A's own directory -- a stale in-flight response must not be able to
    # redirect a live write either.
    page.fill("#collabQuestion", "Meant for repo A, after switching away from repo B.")
    page.click("[data-collab-ask]")
    page.wait_for_function(
        "() => (document.getElementById('collabOutcome') || {}).textContent && "
        "document.getElementById('collabOutcome').textContent.includes('Posted')",
        timeout=8000,
    )
    posted = [c for c in multi_repo_host["calls"]() if c["argv"][:2] == ["pr", "comment"]]
    assert posted, "no comment was posted at all"
    assert posted[-1]["cwd"] == key_a, (
        f"the post after switching away from repo B reached the wrong repository: {posted[-1]} "
        f"(expected repo A, {key_a!r})"
    )
    assert not errors, f"the browser reported errors: {errors}"
    ctx.close()


# --------------------------------------------------------------------------
# converge-xet9 REOPENED -- the POST-completion race the GET-side guard
# above never covered: `postQuestion`/`answer` awaited their own round trip
# and, on return, unconditionally repainted whatever PR they were called
# for -- even if the steward had switched to a different one while the
# request was in flight. Proven here exactly like the GET race above: a
# genuinely delayed (server-side sleep, never page.route) `gh pr comment`
# call for the repository being posted/answered to, released only after the
# steward has switched away and started a fresh draft elsewhere.
# --------------------------------------------------------------------------
@needs_browser
def test_a_delayed_comment_post_completion_cannot_paint_or_clear_a_repo_the_steward_switched_away_from(
    same_basename_server, same_basename_project, browser, multi_repo_host
):
    """`postQuestion`'s completion used to call `openOne(one.id, true)` and
    write to `#collabOutcome` unconditionally once its POST resolved -- with
    no check that the steward was still looking at that PR. If the steward
    switched to a different repository while the post was in flight and
    started typing there, the late completion would reopen the original PR
    (changing the visible selection out from under the steward), and the
    quiet-reopen's own draft capture/restore would capture the NEW repo's
    in-progress draft and paste it into the reopened (old) one."""
    repo_a, repo_b = same_basename_project["repos"]
    key_a, key_b = str(Path(repo_a).resolve()), str(Path(repo_b).resolve())
    multi_repo_host["set_by_cwd"]({
        repo_a: {"pulls": [_pull_fixture(11, "Repo A's own #11", "Body for repo A, PR eleven.", author="alice")]},
        repo_b: {"pulls": [_pull_fixture(11, "Repo B's own #11", "Body for repo B, PR eleven.", author="bob")]},
    })
    ctx, page, errors = _installed(browser, same_basename_server, same_basename_project)
    _open_panel(page)

    # Select repo B and start posting a question there.
    page.click(".collab-row >> nth=1")
    page.wait_for_selector("#collabQuestion", timeout=8000)
    opened_text = page.eval_on_selector("#collabReview", "el => el.innerText")
    assert "Body for repo B" in opened_text, opened_text
    page.fill("#collabQuestion", "A question meant for repo B only.")

    # Make repo B's `pr comment` genuinely slow, then click Post without
    # waiting for it.
    multi_repo_host["set_delay"](repo_b, 3.0, kind="comment")
    page.click("[data-collab-ask]")
    page.wait_for_timeout(300)  # let the delayed POST actually start

    # Switch away WHILE that POST is still pending -- a different repository.
    page.click(".collab-row >> nth=0")
    page.wait_for_function(
        "() => (document.getElementById('collabReview') || {}).innerText && "
        "document.getElementById('collabReview').innerText.includes('Body for repo A')",
        timeout=8000,
    )
    # A fresh, distinct draft, typed only after switching, on the NEW selection.
    fresh_draft = "A draft for repo A, typed while repo B's post was still in flight."
    page.fill("#collabQuestion", fresh_draft)
    outcome_before = page.eval_on_selector("#collabOutcome", "el => el ? el.textContent : ''")

    # Release: wait past repo B's delay so its POST completes late.
    page.wait_for_timeout(3500)

    text_after = page.eval_on_selector("#collabReview", "el => el.innerText")
    assert "Body for repo A" in text_after, text_after
    assert "Body for repo B" not in text_after, (
        f"repo B's late comment-post completion repainted repo B over the steward's new selection: {text_after!r}"
    )
    question_after = page.eval_on_selector("#collabQuestion", "el => el.value")
    assert question_after == fresh_draft, (
        f"repo B's late post completion clobbered repo A's own in-progress draft: {question_after!r}"
    )
    outcome_after = page.eval_on_selector("#collabOutcome", "el => el ? el.textContent : ''")
    assert outcome_after == outcome_before, (
        f"repo B's late post completion painted its own outcome sentence over repo A's screen: {outcome_after!r}"
    )

    # Prove the delayed comment POST to repo B genuinely completed late --
    # this is "it got there after, and was still correctly ignored", not
    # "it never got there".
    posted_b = [c for c in multi_repo_host["calls"]() if c["argv"][:2] == ["pr", "comment"] and c["cwd"] == key_b]
    assert posted_b, "the delayed repo-B comment POST never actually reached the host"

    # Same-target posting still works exactly as before: posting from the
    # CURRENTLY selected repo (A) lands in the right place.
    page.click("[data-collab-ask]")
    page.wait_for_function(
        "() => (document.getElementById('collabOutcome') || {}).textContent && "
        "document.getElementById('collabOutcome').textContent.includes('Posted')",
        timeout=8000,
    )
    posted = [c for c in multi_repo_host["calls"]() if c["argv"][:2] == ["pr", "comment"]]
    assert posted[-1]["cwd"] == key_a, (
        f"the post from the currently-selected repo A reached the wrong repository: {posted[-1]} (expected {key_a!r})"
    )
    assert not errors, f"the browser reported errors: {errors}"
    ctx.close()


@needs_browser
def test_a_delayed_answer_post_completion_cannot_paint_or_clear_a_repo_the_steward_switched_away_from(
    same_basename_server, same_basename_project, browser, multi_repo_host
):
    """Same race, the `answer` code path: a decision's post-back-to-origin
    (`gh pr comment`, same command `postQuestion` uses) held open while the
    steward switches to a different repository and starts a fresh note
    there must not repaint the old repo, clobber the new draft, or paint a
    stale outcome sentence."""
    repo_a, repo_b = same_basename_project["repos"]
    key_a, key_b = str(Path(repo_a).resolve()), str(Path(repo_b).resolve())
    multi_repo_host["set_by_cwd"]({
        repo_a: {"pulls": [_pull_fixture(12, "Repo A's own #12", "Body for repo A, PR twelve.", author="alice")]},
        repo_b: {"pulls": [_pull_fixture(12, "Repo B's own #12", "Body for repo B, PR twelve.", author="bob")]},
    })
    ctx, page, errors = _installed(browser, same_basename_server, same_basename_project)
    _open_panel(page)

    # Select repo B and start answering there.
    page.click(".collab-row >> nth=1")
    page.wait_for_selector("#collabNote", timeout=8000)
    opened_text = page.eval_on_selector("#collabReview", "el => el.innerText")
    assert "Body for repo B" in opened_text, opened_text
    page.fill("#collabNote", "A decision note meant for repo B only.")

    # Make repo B's post-back-to-origin genuinely slow, then click a decision
    # without waiting for it.
    multi_repo_host["set_delay"](repo_b, 3.0, kind="comment")
    page.click('[data-collab-decision="ratified"]')
    page.wait_for_timeout(300)  # let the delayed POST actually start

    # Switch away WHILE that POST is still pending -- a different repository.
    page.click(".collab-row >> nth=0")
    page.wait_for_function(
        "() => (document.getElementById('collabReview') || {}).innerText && "
        "document.getElementById('collabReview').innerText.includes('Body for repo A')",
        timeout=8000,
    )
    fresh_note = "A note for repo A, typed while repo B's answer was still in flight."
    page.fill("#collabNote", fresh_note)
    outcome_before = page.eval_on_selector("#collabOutcome", "el => el ? el.textContent : ''")

    # Release: wait past repo B's delay so its POST completes late.
    page.wait_for_timeout(3500)

    text_after = page.eval_on_selector("#collabReview", "el => el.innerText")
    assert "Body for repo A" in text_after, text_after
    assert "Body for repo B" not in text_after, (
        f"repo B's late answer-post completion repainted repo B over the steward's new selection: {text_after!r}"
    )
    note_after = page.eval_on_selector("#collabNote", "el => el.value")
    assert note_after == fresh_note, (
        f"repo B's late answer completion clobbered repo A's own in-progress note: {note_after!r}"
    )
    outcome_after = page.eval_on_selector("#collabOutcome", "el => el ? el.textContent : ''")
    assert outcome_after == outcome_before, (
        f"repo B's late answer completion painted its own outcome sentence over repo A's screen: {outcome_after!r}"
    )

    # Prove the delayed post-back-to-origin for repo B genuinely completed late.
    posted_b = [c for c in multi_repo_host["calls"]() if c["argv"][:2] == ["pr", "comment"] and c["cwd"] == key_b]
    assert posted_b, "the delayed repo-B answer post-back never actually reached the host"

    # Same-target answering still works exactly as before.
    page.click('[data-collab-decision="ratified"]')
    page.wait_for_function(
        "() => (document.getElementById('collabOutcome') || {}).textContent && "
        "document.getElementById('collabOutcome').textContent.includes('written to the dated ratification record')",
        timeout=8000,
    )
    posted = [c for c in multi_repo_host["calls"]() if c["argv"][:2] == ["pr", "comment"]]
    assert posted[-1]["cwd"] == key_a, (
        f"the answer from the currently-selected repo A reached the wrong repository: {posted[-1]} (expected {key_a!r})"
    )
    assert not errors, f"the browser reported errors: {errors}"
    ctx.close()


# --------------------------------------------------------------------------
# converge-xet9 (reopened) -- de48762 rechecked the submission target once,
# right after the POST itself resolved, then unconditionally awaited
# `openOne`'s own read-back and wrote the outcome sentence. The read-back is
# its own awaited round trip; the two tests below delay ONLY it (`kind`
# "view", the GET) while the POST itself (`kind` "comment") answers
# immediately, reproducing the gap that a switch during the read-back alone
# left unguarded, on both the question and the decision path.
# --------------------------------------------------------------------------
@needs_browser
def test_a_delayed_read_back_after_posting_a_question_cannot_paint_a_stale_outcome_over_a_switched_repo(
    same_basename_server, same_basename_project, browser, multi_repo_host
):
    """The comment POST itself succeeds immediately; only the follow-up
    detail read (`openOne`'s own `pr view`, used to redraw the conversation)
    is slow. Switching to a different repository while that read-back alone
    is still pending must not paint the old repo's success sentence over the
    new selection, even though the POST's own earlier check already passed."""
    repo_a, repo_b = same_basename_project["repos"]
    key_a, key_b = [str(Path(r).resolve()) for r in (repo_a, repo_b)]
    multi_repo_host["set_by_cwd"]({
        repo_a: {"pulls": [_pull_fixture(31, "Repo A's own #31", "Body for repo A, PR thirty-one.", author="alice")]},
        repo_b: {"pulls": [_pull_fixture(31, "Repo B's own #31", "Body for repo B, PR thirty-one.", author="bob")]},
    })
    ctx, page, errors = _installed(browser, same_basename_server, same_basename_project)
    _open_panel(page)

    # Select repo B and start a question there.
    page.click(".collab-row >> nth=1")
    page.wait_for_selector("#collabQuestion", timeout=8000)
    opened_text = page.eval_on_selector("#collabReview", "el => el.innerText")
    assert "Body for repo B" in opened_text, opened_text
    page.fill("#collabQuestion", "A question meant for repo B only.")

    # Delay ONLY repo B's read-back detail GET; the comment POST itself
    # (a different `gh` call kind) answers immediately.
    multi_repo_host["set_delay"](repo_b, 3.0, kind="view")
    page.click("[data-collab-ask]")
    page.wait_for_timeout(300)  # let the (fast) POST resolve and the slow read-back actually start

    # Switch away WHILE the read-back alone is still pending.
    page.click(".collab-row >> nth=0")
    page.wait_for_function(
        "() => (document.getElementById('collabReview') || {}).innerText && "
        "document.getElementById('collabReview').innerText.includes('Body for repo A')",
        timeout=8000,
    )
    fresh_draft = "A draft for repo A, typed while repo B's read-back was still in flight."
    page.fill("#collabQuestion", fresh_draft)
    outcome_before = page.eval_on_selector("#collabOutcome", "el => el ? el.textContent : ''")

    # Release: wait past repo B's read-back delay so it completes late.
    page.wait_for_timeout(3500)

    text_after = page.eval_on_selector("#collabReview", "el => el.innerText")
    assert "Body for repo A" in text_after, text_after
    assert "Body for repo B" not in text_after, (
        f"repo B's late read-back repainted repo B over the steward's new selection: {text_after!r}"
    )
    question_after = page.eval_on_selector("#collabQuestion", "el => el.value")
    assert question_after == fresh_draft, (
        f"repo B's late read-back clobbered repo A's own in-progress draft: {question_after!r}"
    )
    outcome_after = page.eval_on_selector("#collabOutcome", "el => el ? el.textContent : ''")
    assert outcome_after == outcome_before, (
        f"repo B's late read-back painted its own 'Posted' outcome sentence over repo A's screen: {outcome_after!r}"
    )

    # Prove the delayed read-back genuinely completed late, and the comment
    # itself genuinely reached repo B -- this is "it got there after, and was
    # still correctly ignored", not "it never got there".
    posted_b = [c for c in multi_repo_host["calls"]() if c["argv"][:2] == ["pr", "comment"] and c["cwd"] == key_b]
    assert posted_b, "the repo-B comment never actually reached the host"
    view_calls_b = [c for c in multi_repo_host["calls"]() if c["argv"][:2] == ["pr", "view"] and c["cwd"] == key_b]
    assert view_calls_b, "the delayed repo-B read-back never actually reached the host"

    assert not errors, f"the browser reported errors: {errors}"
    ctx.close()


@needs_browser
def test_a_delayed_read_back_after_answering_cannot_paint_a_stale_outcome_over_a_switched_repo(
    same_basename_server, same_basename_project, browser, multi_repo_host
):
    """Same race, the `answer` code path: the post-back-to-origin succeeds
    immediately, only the follow-up detail read is slow. Switching away while
    it alone is pending must not paint the old repo's ratification sentence
    over the new selection."""
    repo_a, repo_b = same_basename_project["repos"]
    key_a, key_b = [str(Path(r).resolve()) for r in (repo_a, repo_b)]
    multi_repo_host["set_by_cwd"]({
        repo_a: {"pulls": [_pull_fixture(32, "Repo A's own #32", "Body for repo A, PR thirty-two.", author="alice")]},
        repo_b: {"pulls": [_pull_fixture(32, "Repo B's own #32", "Body for repo B, PR thirty-two.", author="bob")]},
    })
    ctx, page, errors = _installed(browser, same_basename_server, same_basename_project)
    _open_panel(page)

    page.click(".collab-row >> nth=1")
    page.wait_for_selector("#collabNote", timeout=8000)
    opened_text = page.eval_on_selector("#collabReview", "el => el.innerText")
    assert "Body for repo B" in opened_text, opened_text
    page.fill("#collabNote", "A decision note meant for repo B only.")

    multi_repo_host["set_delay"](repo_b, 3.0, kind="view")
    page.click('[data-collab-decision="ratified"]')
    page.wait_for_timeout(300)  # let the (fast) post-back resolve and the slow read-back actually start

    page.click(".collab-row >> nth=0")
    page.wait_for_function(
        "() => (document.getElementById('collabReview') || {}).innerText && "
        "document.getElementById('collabReview').innerText.includes('Body for repo A')",
        timeout=8000,
    )
    fresh_note = "A note for repo A, typed while repo B's read-back was still in flight."
    page.fill("#collabNote", fresh_note)
    outcome_before = page.eval_on_selector("#collabOutcome", "el => el ? el.textContent : ''")

    page.wait_for_timeout(3500)

    text_after = page.eval_on_selector("#collabReview", "el => el.innerText")
    assert "Body for repo A" in text_after, text_after
    assert "Body for repo B" not in text_after, (
        f"repo B's late read-back repainted repo B over the steward's new selection: {text_after!r}"
    )
    note_after = page.eval_on_selector("#collabNote", "el => el.value")
    assert note_after == fresh_note, (
        f"repo B's late read-back clobbered repo A's own in-progress note: {note_after!r}"
    )
    outcome_after = page.eval_on_selector("#collabOutcome", "el => el ? el.textContent : ''")
    assert outcome_after == outcome_before, (
        f"repo B's late read-back painted its own ratification sentence over repo A's screen: {outcome_after!r}"
    )

    posted_b = [c for c in multi_repo_host["calls"]() if c["argv"][:2] == ["pr", "comment"] and c["cwd"] == key_b]
    assert posted_b, "the repo-B post-back-to-origin never actually reached the host"
    view_calls_b = [c for c in multi_repo_host["calls"]() if c["argv"][:2] == ["pr", "view"] and c["cwd"] == key_b]
    assert view_calls_b, "the delayed repo-B read-back never actually reached the host"

    assert not errors, f"the browser reported errors: {errors}"
    ctx.close()


@needs_browser
def test_a_same_target_background_poll_during_a_post_clears_the_live_textarea_not_a_detached_one(
    same_basename_server, same_basename_project, browser, multi_repo_host
):
    """`postQuestion` used to clear `#collabQuestion` through the DOM
    reference it captured at the TOP of the function, before its own POST's
    own await. A SAME-target background poll (`openOne(id, true)`, quiet --
    driven here through the test-only `window.__collabReopen` hook so this
    race is between exactly two calls, not muddied by `refresh()`'s own
    unrelated authority/list round trips) can run its own
    captureDraft/drawProposal/restoreDraft cycle while that POST is still in
    flight, replacing `#collabQuestion` with a brand-new node carrying the
    same (restored) text. Clearing the OLD, by-then-detached node would be a
    silent no-op: the LIVE node the steward is actually looking at would keep
    showing the text they already submitted, looking exactly like an unsent
    draft."""
    repo_a, repo_b = same_basename_project["repos"]
    multi_repo_host["set_by_cwd"]({
        repo_a: {"pulls": []},
        repo_b: {"pulls": [_pull_fixture(33, "Repo B's own #33", "Body for repo B, PR thirty-three.", author="bob")]},
    })
    ctx, page, errors = _installed(browser, same_basename_server, same_basename_project)
    _open_panel(page)

    page.click(".collab-row >> nth=0")
    page.wait_for_selector("#collabQuestion", timeout=8000)
    submitted = "A question that must be cleared once it actually posts."
    page.fill("#collabQuestion", submitted)

    # Make repo B's comment POST genuinely slow.
    multi_repo_host["set_delay"](repo_b, 3.0, kind="comment")
    page.click("[data-collab-ask]")
    page.wait_for_timeout(300)  # let the delayed POST actually start, box not yet cleared

    # Force a SAME-target background redraw while that POST is still in
    # flight -- a single, direct `openOne(id, true)`, not a full `refresh()`.
    # Its own detail read (kind "view") is not the delayed call kind, so it
    # completes and redraws well before the comment POST above does.
    page.evaluate("() => { window.__collabReopen(); return true; }")
    page.wait_for_function(
        "(expected) => { const el = document.getElementById('collabQuestion'); "
        "return el && el.value === expected; }",
        arg=submitted,
        timeout=8000,
    )
    # The redraw happened -- the review is still open on the same PR and the
    # draft survived it (restored by the redraw's own restoreDraft), proving
    # the node was genuinely replaced underneath the still-pending POST.
    still_open = page.eval_on_selector("#collabReview", "el => el.innerText")
    assert "Body for repo B" in still_open, still_open

    # Release: wait past the comment POST's delay so it completes late, and
    # settles. Poll the LIVE textarea directly rather than the outcome
    # sentence -- an unrelated later redraw (this same reopen mechanism could
    # in principle run again) always resets the outcome paragraph, so the
    # textarea's own value is the one honest, stable signal for what this
    # test is actually about.
    page.wait_for_function(
        "() => { const el = document.getElementById('collabQuestion'); return el && el.value === ''; }",
        timeout=8000,
    )
    question_after = page.eval_on_selector("#collabQuestion", "el => el.value")
    assert question_after == "", (
        "the submitted question is still sitting in the LIVE textarea -- clearing must have touched "
        f"a stale, detached reference instead of the current node: {question_after!r}"
    )

    # Prove the comment genuinely reached the host late, rather than never
    # having been sent at all.
    posted = [c for c in multi_repo_host["calls"]() if c["argv"][:2] == ["pr", "comment"]]
    assert posted, "the comment POST never actually reached the host"

    assert not errors, f"the browser reported errors: {errors}"
    ctx.close()


@needs_browser
def test_a_background_poll_updates_the_open_thread_without_losing_the_draft(server, project, browser, host):
    host["set_pulls"]([_pull_fixture(5, "Long-running thread", CONVERGE_SHAPED_BODY)])
    ctx, page, errors = _installed(browser, server, project)
    _open_panel(page)
    page.click(".collab-row")
    page.wait_for_selector("#collabQuestion", timeout=8000)

    question_draft = "Which sentence in Core 4 does this replace?"
    note_draft = "Keep the first sentence, drop the second."
    page.fill("#collabQuestion", question_draft)
    page.fill("#collabNote", note_draft)
    scroll_before = page.eval_on_selector("#collabReview", "el => el.scrollTop")

    # A new comment "arrives" on the host between two poll ticks -- exactly
    # what clause 6 asks the app to notice without the steward asking again.
    host["set_comments"]([
        {"author": {"login": "wren"}, "createdAt": "2026-09-04T10:00:00Z", "body": "The second one."},
    ])
    # Trigger one tick deterministically rather than waiting the real 60s
    # POLL_MS -- this calls the same exported function the real timer calls.
    page.evaluate("() => window.__collabRefresh ? window.__collabRefresh() : null")
    page.wait_for_function(
        "() => (document.getElementById('collabReview') || {}).innerText && "
        "document.getElementById('collabReview').innerText.includes('The second one.')",
        timeout=8000,
    )

    question_after = page.eval_on_selector("#collabQuestion", "el => el.value")
    note_after = page.eval_on_selector("#collabNote", "el => el.value")
    scroll_after = page.eval_on_selector("#collabReview", "el => el.scrollTop")
    print(f"\nquestion draft: before={question_draft!r} after={question_after!r}")
    print(f"note draft:     before={note_draft!r} after={note_after!r}")

    assert question_after == question_draft, "the background poll erased the unsent question"
    assert note_after == note_draft, "the background poll erased the unsent decision note"
    assert scroll_after == scroll_before, "the background poll moved the reading position"
    assert not errors, f"the browser reported errors: {errors}"
    ctx.close()


@needs_browser
def test_a_failed_poll_of_the_open_thread_keeps_the_draft_and_reports_the_failure(server, project, browser, host):
    """A failed READ OF THE OPEN THREAD -- not a host that has gone entirely
    missing (that is `test_a_host_with_no_gh_available...` above, and the
    LIST route legitimately empties and closes the thread when a repository's
    `gh` truly cannot be read at all -- correct behaviour, not this defect).
    Here the list still answers (the PR is still there); only the one
    request that would refresh the OPEN thread's own detail is made to fail,
    via `page.route`, which is what a transient read failure on that one
    request actually looks like.
    """
    host["set_pulls"]([_pull_fixture(6, "Thread that goes quiet", CONVERGE_SHAPED_BODY)])
    ctx, page, errors = _installed(browser, server, project)
    _open_panel(page)
    page.click(".collab-row")
    page.wait_for_selector("#collabQuestion", timeout=8000)

    draft = "Still drafting this one."
    page.fill("#collabQuestion", draft)

    host["break_view"]()
    page.evaluate("() => window.__collabRefresh ? window.__collabRefresh() : null")
    page.wait_for_timeout(1500)

    question_after = page.eval_on_selector("#collabQuestion", "el => el.value")
    outcome_text = page.eval_on_selector("#collabOutcome", "el => el ? el.textContent : ''")
    print(f"\ndraft after a failed poll of the open thread: {question_after!r}")
    print(f"outcome line: {outcome_text!r}")
    assert question_after == draft, "a failed poll of the open thread erased the unsent draft"
    assert outcome_text and "did not answer" in outcome_text, (
        f"a failed poll of the open thread said nothing went wrong: {outcome_text!r}"
    )
    ctx.close()


# --------------------------------------------------------------------------
# converge-8crs (reopened) -- a manager switch during refresh()'s OWN
# authority/list reads, not just a repo switch during the open thread's own
# detail read (that race is converge-xet9's, above, and is unchanged).
# --------------------------------------------------------------------------
def _make_two_manager_project(tmp_path: Path, steward_a: str, steward_b: str) -> dict:
    """TWO manager sessions, each with its own repository and its own
    registered steward -- `steward_a` the signed-in tester, `steward_b`
    deliberately someone else, so manager A's decisions are enabled and
    manager B's are disabled by the SAME real authority check, not a fixture
    assumption. `_make_project`'s single-`[[managers]]` shape does not cover
    two managers at once, so this is its own project builder rather than a
    parametrization of it."""
    repo_a = tmp_path / "repo-a"
    repo_b = tmp_path / "repo-b"
    for repo in (repo_a, repo_b):
        (repo / "docs" / "workflow").mkdir(parents=True)
        (repo / "docs" / "VISION.md").write_text("# Demo Vision (DRAFT)\n\nOne place.\n", encoding="utf-8")
        _git(repo, "init", "-q", "-b", "main")
        _git(repo, "add", "-A")
        _git(repo, "commit", "-q", "-m", "seed: the vision")

    batch_a = tmp_path / "hw-demo-a"
    batch_b = tmp_path / "hw-demo-b"
    for batch in (batch_a, batch_b):
        (batch / "goals").mkdir(parents=True)
        (batch / "HIGHWAY.md").write_text("# HIGHWAY\n\n## Outcome\nProve the authority switch.\n", encoding="utf-8")
        (batch / ".width").write_text("4\n", encoding="utf-8")
        (batch / "manifest.tsv").write_text("lane\tworktree\tbranch\n", encoding="utf-8")

    conf = tmp_path / "converge-app.toml"
    conf.write_text(
        "[[managers]]\n"
        'id = "mgr-a"\n'
        'name = "Manager A"\n'
        f'batch_dir = "{batch_a}"\n'
        f'repos = ["{repo_a}"]\n'
        'tmux_socket = "collab-journey-socket-that-does-not-exist"\n'
        f'steward = "{steward_a}"\n'
        "\n"
        "[[managers]]\n"
        'id = "mgr-b"\n'
        'name = "Manager B"\n'
        f'batch_dir = "{batch_b}"\n'
        f'repos = ["{repo_b}"]\n'
        'tmux_socket = "collab-journey-socket-that-does-not-exist"\n'
        f'steward = "{steward_b}"\n',
        encoding="utf-8",
    )
    return {
        "config": conf, "secret": tmp_path / "secret", "state": tmp_path / "state.json",
        "sessions": tmp_path / "sessions.json", "repos": (repo_a, repo_b),
        "managers": ("mgr-a", "mgr-b"),
    }


@pytest.fixture(scope="module")
def two_manager_project(tmp_path_factory) -> dict:
    """Manager A's steward IS the signed-in tester; manager B's is someone
    else entirely -- so A permits deciding and B does not, by the real
    server-derived `manager.steward` field, the same fact `loadAuthorityFor`
    reads from `/api/boot`."""
    tmp_path = tmp_path_factory.mktemp("collab-journey-two-manager")
    return _make_two_manager_project(tmp_path, steward_a=USER, steward_b="someone-else-entirely")


@pytest.fixture(scope="module")
def two_manager_server(two_manager_project):
    uv_server, thread, url = _start_server(two_manager_project)
    yield url
    uv_server.should_exit = True
    thread.join(timeout=10)


@needs_browser
def test_selecting_a_nonfirst_manager_refreshes_its_hosted_pull_requests_without_a_manual_refresh(
    two_manager_server, two_manager_project, browser, multi_repo_host
):
    """The normal Home -> second manager -> Direction journey reads manager B.

    The initial collab mount may have completed manager A's empty list before
    this visible navigation.  No test global, manual refresh, or forced click
    is used below: selecting B must itself cause the real B host request.
    """
    mgr_a, mgr_b = two_manager_project["managers"]
    repo_a, repo_b = two_manager_project["repos"]
    key_b = str(Path(repo_b).resolve())
    multi_repo_host["set_by_cwd"]({
        repo_a: {"pulls": []},
        repo_b: {"pulls": [_pull_fixture(22, "B arrives through normal navigation", CONVERGE_SHAPED_BODY)]},
    })

    sessions = auth.Sessions(auth.read_or_make_secret(two_manager_project["secret"]))
    ctx = browser.new_context(viewport={"width": 1280, "height": 800}, service_workers="block")
    ctx.add_cookies([{"name": auth.COOKIE, "value": sessions.issue(USER),
                      "domain": "127.0.0.1", "path": "/"}])
    page = ctx.new_page()
    errors: list[str] = []
    page.on("console", lambda m: errors.append(f"console.{m.type}: {m.text}") if m.type == "error" else None)
    page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))

    page.goto(two_manager_server, wait_until="networkidle")
    page.wait_for_selector(".home-manager-card", timeout=15000)
    page.click(f'[data-home-manager="{mgr_b}"]')
    page.wait_for_selector("#directionTab", timeout=15000)
    page.click("#directionTab")
    page.wait_for_selector("#documentModeContent", timeout=15000)
    # The panel is a native disclosure. Open it with the same visible click a
    # steward uses before inspecting its rendered list; hidden content's
    # `innerText` is intentionally empty even when the list has landed.
    panel_open = page.eval_on_selector("#collabPanel", "el => el.open")
    if not panel_open:
        page.click("#collabPanel > summary")
    try:
        page.wait_for_function(
            "() => (document.getElementById('collabList') || {}).innerText"
            " && document.getElementById('collabList').innerText.includes('B arrives through normal navigation')",
            timeout=8000,
        )
    except Exception:
        print(
            "\nnormal second-manager refresh diagnostic:",
            page.eval_on_selector("#collabList", "el => el.innerText"),
            multi_repo_host["calls"](),
        )
        raise

    b_lists = [
        call for call in multi_repo_host["calls"]()
        if call["cwd"] == key_b and call["argv"][:2] == ["pr", "list"]
    ]
    assert b_lists, f"normal selection never requested manager B's host: {multi_repo_host['calls']()}"
    assert not errors, f"the browser reported errors: {errors}"
    ctx.close()


@needs_browser
def test_a_stale_authority_and_list_read_cannot_paint_over_a_manager_the_steward_switched_away_from(
    two_manager_server, two_manager_project, browser, multi_repo_host
):
    """The race this lane's brief describes in full, reproduced against a real
    mounted browser: `refresh()` captures its target manager (A), awaits
    `/api/boot` for A's authority, then awaits A's own PR list, and used to
    commit both unconditionally. Switching to a SECOND manager (B, whose
    registered steward is deliberately NOT the signed-in tester -- A permits
    deciding, B must not) while A's authority read is still genuinely held
    open must not let A's authority or A's list paint over B's screen once
    it lands late; and B's own refresh, fired while A's is still pending,
    must not be suppressed by A's stale in-flight state.

    The delay is injected server-side on `/api/boot` itself via a real
    `page.route` hold in an explicitly worker-free context (`service_workers
    ="block"`) -- boot is this app's own endpoint, not a `gh` call the stand-
    in host can delay, and this app's service worker would otherwise own the
    fetch before Playwright's route ever saw it (AGENTS.md's own app-
    verification lesson), so a worker-free context is what makes the hold
    real rather than silently bypassed.
    """
    mgr_a, mgr_b = two_manager_project["managers"]
    repo_a, repo_b = two_manager_project["repos"]
    key_a, key_b = str(Path(repo_a).resolve()), str(Path(repo_b).resolve())
    multi_repo_host["set_by_cwd"]({
        repo_a: {"pulls": [_pull_fixture(1, "A's own open pull request", "Body belonging to manager A.")]},
        repo_b: {"pulls": [_pull_fixture(2, "B's own open pull request", "Body belonging to manager B.")]},
    })

    sessions = auth.Sessions(auth.read_or_make_secret(two_manager_project["secret"]))
    ctx = browser.new_context(viewport={"width": 1280, "height": 800}, service_workers="block")
    ctx.add_cookies([{"name": auth.COOKIE, "value": sessions.issue(USER),
                      "domain": "127.0.0.1", "path": "/"}])
    page = ctx.new_page()
    errors: list[str] = []
    page.on("console", lambda m: errors.append(f"console.{m.type}: {m.text}") if m.type == "error" else None)
    page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))

    page.goto(two_manager_server, wait_until="networkidle")
    page.wait_for_selector(".home-manager-card", timeout=15000)
    page.click(f'[data-home-manager="{mgr_a}"]')
    page.wait_for_selector("#directionTab", timeout=15000)
    page.click("#directionTab")
    page.wait_for_selector("#documentModeContent", timeout=15000)
    _open_panel(page)
    page.click(".collab-row >> nth=0")
    page.wait_for_selector("#collabQuestion", timeout=8000)

    review_a = page.eval_on_selector("#collabReview", "el => el.innerText")
    assert "Body belonging to manager A" in review_a, review_a
    disabled_on_a = page.eval_on_selector_all(
        "[data-collab-decision]", "els => els.map(e => e.disabled)"
    )
    assert disabled_on_a and all(d is False for d in disabled_on_a), (
        f"manager A's own registered steward should see enabled decisions: {disabled_on_a}"
    )

    # Hold A's NEXT authority read open. After the initial page load this is
    # unambiguous: nothing else calls /api/boot again until collab.js's own
    # refresh() does (selectManager() below reaches the manager/operation
    # routes, never boot).
    HOLD_S = 2.5

    def _hold_boot(route):
        time.sleep(HOLD_S)
        route.continue_()

    page.route("**/api/boot", _hold_boot)
    page.evaluate("() => { window.__collabRefresh(); return true; }")
    page.wait_for_timeout(300)  # let the held /api/boot request actually start

    # Switch to a DIFFERENT manager -- B, whose steward is not this tester --
    # while A's authority read is still genuinely pending. Unroute first so
    # B's own upcoming refresh below is not itself held by the same hook.
    page.unroute("**/api/boot")
    page.click("#managerSelectButton")
    page.wait_for_selector('[data-menu-manager]', timeout=8000)
    page.click(f'[data-menu-manager="{mgr_b}"]')
    page.wait_for_selector("#directionTab", timeout=8000)
    # selectManager() (main.js) always lands on Operation, not Direction
    # (experience.v1 Core 1/2) -- switch back to Direction so the panel is
    # actually visible; `.innerText` reads empty on a hidden view even
    # though collab.js keeps updating its DOM underneath.
    page.click("#directionTab")
    page.wait_for_selector("#documentModeContent", timeout=8000)

    # Fire B's own refresh now, while A's held read is still in flight, and
    # wait for its LIST to land -- proving the old busy/in-flight state from
    # A never suppressed it. A's previously-open PR id belongs to a manager
    # B does not share, so refresh() correctly clears the selection rather
    # than auto-opening anything; select B's own row explicitly, exactly as
    # a steward would.
    page.evaluate("() => { window.__collabRefresh(); return true; }")
    page.wait_for_function(
        "() => (document.getElementById('collabList') || {}).innerText && "
        "document.getElementById('collabList').innerText.includes(\"B's own open pull request\")",
        timeout=8000,
    )
    page.click(".collab-row >> nth=0")
    page.wait_for_selector("#collabQuestion", timeout=8000)
    review_b = page.eval_on_selector("#collabReview", "el => el.innerText")
    assert "Body belonging to manager B" in review_b, review_b
    disabled_on_b = page.eval_on_selector_all(
        "[data-collab-decision]", "els => els.map(e => e.disabled)"
    )
    assert disabled_on_b and all(d is True for d in disabled_on_b), (
        f"manager B's own registered steward is someone else -- decisions must be disabled: {disabled_on_b}"
    )
    gate_note = page.eval_on_selector("#collabReview", "el => el.innerText")
    assert "Only the registered steward" in gate_note, gate_note

    # Release: wait past A's hold so its stale authority (and list) response
    # actually lands late, in the background, while B is what is on screen.
    page.wait_for_timeout(int(HOLD_S * 1000) + 500)

    review_after = page.eval_on_selector("#collabReview", "el => el.innerText")
    assert "Body belonging to manager B" in review_after, review_after
    assert "Body belonging to manager A" not in review_after, (
        f"manager A's stale, late-arriving read painted over manager B's screen: {review_after!r}"
    )
    disabled_after = page.eval_on_selector_all(
        "[data-collab-decision]", "els => els.map(e => e.disabled)"
    )
    assert disabled_after and all(d is True for d in disabled_after), (
        f"manager A's late authority re-enabled decisions on manager B's screen: {disabled_after}"
    )

    # B must still be a genuinely usable panel, not merely un-clobbered --
    # ask a question from here and prove it reaches repo B, never repo A.
    page.fill("#collabQuestion", "Meant for manager B, after A's stale read landed late.")
    page.click("[data-collab-ask]")
    page.wait_for_function(
        "() => (document.getElementById('collabOutcome') || {}).textContent && "
        "document.getElementById('collabOutcome').textContent.includes('Posted')",
        timeout=8000,
    )
    posted = [c for c in multi_repo_host["calls"]() if c["argv"][:2] == ["pr", "comment"]]
    assert posted, "no comment was posted at all after switching to manager B"
    assert posted[-1]["cwd"] == key_b, (
        f"the post from manager B's panel reached the wrong repository: {posted[-1]} (B is {key_b!r})"
    )
    assert not errors, f"the browser reported errors: {errors}"
    ctx.close()


# --------------------------------------------------------------------------
# wording -- no browser needed, always runs
# --------------------------------------------------------------------------
def test_collab_js_exposes_the_refresh_tick_this_file_drives_deterministically():
    """This file never waits the real 60s POLL_MS -- it calls the same
    function the timer calls, exposed on `window` for exactly this purpose."""
    js = (REPO_ROOT / "app" / "static" / "js" / "render" / "collab.js").read_text(encoding="utf-8")
    assert "refreshCollab" in js, "collab.js no longer exports a refresh function this test can call"
