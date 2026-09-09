"""The SAME open tab adopts a NEW server generation's code -- converge-moe4,
contract `platform-web.v1` Core 9 ("it installs, and installing changes only
the frame"), read together with Core 13's own-origin promise (a static asset
must keep resolving to the SAME bytes an installed client already trusts) and
Core 14 ("renders ... with nothing cut off and no errors in the browser's own
log").

**Why the earlier attempt at this test did not reproduce the real bug.** An
independent review (`GOAL.md`) found that a prior version of this test closed
each `Page` and opened a new one for its "after upgrade" half. That is not
what an already-open tab on a real Mac does, and it is not what this test
does either: ONE `BrowserContext`, ONE `Page`, the SAME origin/port, across
BOTH server generations, from the first navigation to the last. Nothing here
ever calls `ctx.new_page()`, replaces `ctx`, deletes Cache Storage/`localStorage`,
unregisters the worker, forces a hard reload, or cache-busts a URL by hand --
any of those would prove a different, easier claim than the one converge-moe4
is actually about.

**What is proved, directly:**

1. Two REAL server generations (`app.serve.create_app()`, twice, over two
   genuinely different `app/static/` trees -- see `_build_generation` below)
   answer on the exact SAME `127.0.0.1:<port>`, with the SAME signed session
   cookie valid across both (`secret_path`/`sessions_path`/`state_path` are
   shared, never regenerated) -- a same-origin swap, not a different app.
2. An ORDINARY `page.goto(base)` -- never a reload, never a cache-buster --
   to generation B, on the SAME `Page` that was already open on generation A,
   causes generation B's OWN `collab.js` (the entry `collab.html` gives it)
   AND the `state.js` it transitively imports (`import { state } from
   '../state.js'`) to both actually EXECUTE -- proved by a marker literal
   each generation's own copy of those two files carries (see
   `_build_generation`), never inferred from a URL alone.
3. Nothing adopts generation B on its own: the SAME page, left idle after the
   backend swaps generations underneath it, still reports generation A's own
   markers and makes no new `/static/` request at all, until this test makes
   the one deliberate navigation in step 2.
4. Every `/static/` request this test observes for `collab.js`/`state.js`
   after the swap carries generation B's OWN revision, and NONE still carries
   generation A's -- the coherent, single asset identity Core 9 asks for,
   not a partial upgrade where the entry moved but an import stayed stale.
5. No console or page error is logged across the deliberate upgrade itself
   (errors are examined only from the point network connectivity resumes --
   see the comment at that reset for why the artificial gap this test's own
   orchestration creates while swapping which process is listening is not
   itself evidence of anything the real app does).

**What is a documentary control, and degrades honestly rather than faking a
pass:** `test_the_old_stable_url_scheme_is_the_reason_this_lane_moved_off_it`
reproduces, with the SAME `Page`/origin discipline, the failure mode
`app/static/sw.js`'s own `2fca3d8` comment and this lane's evidence describe:
a browser's own HTTP cache (a layer neither the app nor a service worker
controls) can go on answering a STABLE, unversioned URL with OLD bytes long
after the server that answers it moved on. Chromium's own caching heuristics
for a resource whose Last-Modified is "just now" are not guaranteed to
reproduce that in every build/profile (the same class of environment
dependence `test_web_polish.py` already documents for offline emulation) --
where it does not, that test reports so and skips, rather than asserting a
premise it could not actually stage.

**What is NOT proved here, on purpose (residual, not silently dropped):** the
real collaboration panel's own unsent-draft preservation
(`collab.js`'s `#collabQuestion`/`#collabNote`) needs a live pull-request
fixture (a real or faked `gh`) this lane does not own; what IS proved instead
(item 3 above) is the narrower, load-bearing half of the same claim -- nothing
reloads or replaces the page's own running code merely because the backend
changed underneath it while nobody navigated, which is the actual mechanism
that would have discarded a draft. Native install UI, and anything about a
real macOS Safari/PWA container specifically, remain PENDING-HUMAN exactly as
the rest of this app's PWA suite already says.

Focused, non-browser controls for `app/assets.py` itself (revision
determinism, per-app isolation, the `dev/` denial from both static routes,
unknown/malformed-revision refusal, and installed-wheel-style operation with
no `.git` anywhere) are grouped in their own section below, and never skip.
"""

from __future__ import annotations

import shutil
import socket as socketlib
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app import assets, auth, serve  # noqa: E402

APP = Path(__file__).resolve().parents[1]
STATIC = APP / "static"

USER = "tester"
MANAGER = "demo"


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
    reason=f"{PLAYWRIGHT_SKIP}; this lane's proof needs a real Chromium, not a substitute",
)


# --------------------------------------------------------------------------
# focused controls for app/assets.py -- no browser, never skip
# --------------------------------------------------------------------------


def test_compute_revision_is_content_and_name_sensitive_never_git_or_mtime(tmp_path) -> None:
    """The module docstring's own promise, proved directly: sorted relative
    names AND bytes move it; nothing else does.

    WHAT WOULD FALSIFY THIS: two directories with identical names+bytes
    computing different revisions, or a rename/content edit alone failing to
    move it.
    """
    a = tmp_path / "a"
    a.mkdir()
    (a / "x.js").write_text("one", encoding="utf-8")
    b = tmp_path / "b"
    b.mkdir()
    (b / "x.js").write_text("one", encoding="utf-8")
    assert assets.compute_revision(a) == assets.compute_revision(b), (
        "identical names and bytes computed different revisions"
    )
    # git never enters the computation at all -- no .git anywhere near either.
    assert not (a / ".git").exists() and not (b / ".git").exists()

    renamed = tmp_path / "renamed"
    renamed.mkdir()
    (renamed / "y.js").write_text("one", encoding="utf-8")
    assert assets.compute_revision(a) != assets.compute_revision(renamed), (
        "a rename alone did not move the revision"
    )

    edited = tmp_path / "edited"
    edited.mkdir()
    (edited / "x.js").write_text("two", encoding="utf-8")
    assert assets.compute_revision(a) != assets.compute_revision(edited), (
        "a content edit alone did not move the revision"
    )


def test_compute_revision_excludes_dev_so_running_the_stub_locally_never_bumps_it(tmp_path) -> None:
    """converge-moe4 finding #1, half one -- the fingerprint side.

    `EXCLUDED_TOP_LEVEL` keeps a dev-only file (the front-end stub's own
    request log, its fixtures) from moving the revision every real client
    sees. Proved directly against the pure function; the OTHER half -- that
    `dev/` is also never actually SERVED -- is proved below, against the
    real mount, since excluding a directory from a fingerprint never by
    itself stops it from answering a request for it.

    WHAT WOULD FALSIFY THIS: two trees whose only difference is under `dev/`
    computing different revisions.
    """
    one = tmp_path / "one"
    (one / "dev").mkdir(parents=True)
    (one / "js").mkdir()
    (one / "js" / "main.js").write_text("real client code", encoding="utf-8")
    (one / "dev" / "requests.log").write_text("a", encoding="utf-8")

    two = tmp_path / "two"
    (two / "dev").mkdir(parents=True)
    (two / "js").mkdir()
    (two / "js" / "main.js").write_text("real client code", encoding="utf-8")
    (two / "dev" / "requests.log").write_text("a whole lot more, from a local run", encoding="utf-8")

    assert assets.compute_revision(one) == assets.compute_revision(two), (
        "a dev-only file moved the revision -- running the front-end stub locally would make "
        "every real client's asset look new"
    )


def test_two_app_instances_never_poison_each_others_revision(tmp_path) -> None:
    """`app/assets.py`'s own module docstring: `compute_revision` is a pure
    function of a directory, so two servers over two different static trees
    (routine in this project's own test suite, which builds several
    `create_app()`s in one process) must never see each other's answer,
    computed in any order.

    WHAT WOULD FALSIFY THIS: computing one directory's revision after the
    other's changes it.
    """
    a = tmp_path / "a"
    a.mkdir()
    (a / "one.txt").write_text("A", encoding="utf-8")
    b = tmp_path / "b"
    b.mkdir()
    (b / "one.txt").write_text("B", encoding="utf-8")

    rev_a = assets.compute_revision(a)
    rev_b = assets.compute_revision(b)
    assert rev_a != rev_b
    assert assets.compute_revision(b) == rev_b, "computing a's revision moved b's own answer"
    assert assets.compute_revision(a) == rev_a, "computing b's revision moved a's own answer"


def test_compute_revision_needs_no_checkout_installed_wheel_shaped(tmp_path) -> None:
    """converge-moe4's own claim: \"an installed wheel with no `.git` at all
    gets exactly the answer a source checkout does\". `tmp_path` is
    guaranteed to sit outside any repository's own `.git` ancestry, which is
    exactly the installed-wheel shape -- no build toolchain, no external
    service, nothing but the bytes on disk right now.

    WHAT WOULD FALSIFY THIS: raising at all with no `.git` present, or two
    calls over the same unmodified tree disagreeing with each other.
    """
    wheel_shaped = tmp_path / "site-packages" / "app" / "static"
    shutil.copytree(STATIC, wheel_shaped)
    assert not (wheel_shaped / ".git").exists()
    assert not list(wheel_shaped.rglob(".git"))

    first = assets.compute_revision(wheel_shaped)
    second = assets.compute_revision(wheel_shaped)
    assert first == second, "the same unmodified tree computed two different revisions"
    assert len(first) == 16 and all(c in "0123456789abcdef" for c in first), (
        f"not the short hex fingerprint the rest of the app expects: {first!r}"
    )


def _mini_static_app(directory: Path, revision: str):
    """A bare Starlette app mounting ONLY `VersionedStaticFiles` -- enough to
    prove the mount's own request-handling contract without booting the real
    (auth-gated) app at all."""
    from starlette.applications import Starlette
    from starlette.routing import Mount

    return Starlette(routes=[Mount("/static", app=assets.VersionedStaticFiles(
        directory=str(directory), revision=revision,
    ))])


def test_dev_is_refused_through_both_the_legacy_and_versioned_static_routes(tmp_path) -> None:
    """converge-moe4 finding #1, half two -- the SERVED side.

    `app/static/dev/` is the front-end dev stub: its own source
    (`stub_server.py`), its fixtures, and `requests.log` -- every POST it has
    ever recorded. `app/serve.py` mounts `VersionedStaticFiles` directly over
    the real `app/static/`, `dev/` included, so excluding `dev/` from the
    FINGERPRINT (proved above) never by itself stopped it being SERVED:
    `StaticFiles.lookup_path` answers for anything that exists under
    `directory`, unconditionally. This is the denial control the finding
    asks for, proved against BOTH the legacy, unversioned route and the
    current, versioned one -- a browser or an old Cache Storage entry could
    ask through either.

    The development stub's own NORMAL behaviour (serving `app/templates` and
    `app/static` to build its own UI) is untouched: this denies the
    production STATIC MOUNT answering for `dev/`, never the stub process
    itself, which never reads its own fixtures back out over HTTP in the
    first place.

    WHAT WOULD FALSIFY THIS: any 200 for anything under `dev/`, through
    either route, or a real (non-`dev`) file starting to 404 because of an
    over-broad denial.
    """
    from starlette.testclient import TestClient

    static_dir = tmp_path / "static"
    (static_dir / "dev").mkdir(parents=True)
    (static_dir / "js").mkdir()
    (static_dir / "js" / "main.js").write_text("real client code", encoding="utf-8")
    (static_dir / "dev" / "stub_server.py").write_text("# not for a browser\n", encoding="utf-8")
    (static_dir / "dev" / "requests.log").write_text("[stamp] POST /login user='someone'\n", encoding="utf-8")

    revision = assets.compute_revision(static_dir)
    client = TestClient(_mini_static_app(static_dir, revision))

    denied = {
        "legacy dev file": "/static/dev/requests.log",
        "legacy dev source": "/static/dev/stub_server.py",
        "versioned dev file": f"/static/{revision}/dev/requests.log",
        "versioned dev source": f"/static/{revision}/dev/stub_server.py",
    }
    for label, path in denied.items():
        code = client.get(path).status_code
        print(f"  {code} {label}: {path}")
        assert code == 404, f"{label} answered {code}, not refused: {path}"

    allowed = {
        "legacy real file": "/static/js/main.js",
        "versioned real file": f"/static/{revision}/js/main.js",
    }
    for label, path in allowed.items():
        code = client.get(path).status_code
        print(f"  {code} {label}: {path}")
        assert code == 200, f"{label} answered {code} -- the denial is too broad: {path}"


def test_an_unknown_or_malformed_revision_segment_404s_never_escapes_the_directory(tmp_path) -> None:
    """`VersionedStaticFiles.get_path`'s own docstring: a segment that is NOT
    an exact match for the CURRENT revision is never stripped -- it is looked
    up literally, on Starlette's own unmodified traversal guard, and 404s
    exactly like any other bad request. Proved here for a stale revision (a
    previous server generation's own, once-valid prefix), a segment that
    merely LOOKS like one, and a `..` escape attempt.

    WHAT WOULD FALSIFY THIS: any of these answering with a file, or with a
    different file than the one actually asked for.
    """
    from starlette.testclient import TestClient

    static_dir = tmp_path / "static"
    static_dir.mkdir()
    (static_dir / "main.js").write_text("real client code", encoding="utf-8")
    outside = tmp_path / "secret.txt"
    outside.write_text("never this app's to serve", encoding="utf-8")

    revision = assets.compute_revision(static_dir)
    client = TestClient(_mini_static_app(static_dir, revision))

    assert client.get(f"/static/{revision}/main.js").status_code == 200, "the current revision itself must still work"

    for label, path in {
        "a stale, no-longer-current revision": "/static/deadbeefdeadbeef/main.js",
        "a segment that merely looks like a revision": f"/static/{revision}x/main.js",
        "traversal past the mount": "/static/../secret.txt",
        "traversal past a revision segment": f"/static/{revision}/../../secret.txt",
    }.items():
        code = client.get(path).status_code
        print(f"  {code} {label}: {path}")
        assert code == 404, f"{label} did not refuse: {path} -> {code}"


def _real_app(secret_path: Path, state_path: Path, sessions_path: Path, config_path: Path):
    return serve.create_app(
        config_path=config_path, secret_path=secret_path, state_path=state_path, sessions_path=sessions_path,
    )


@pytest.fixture(scope="module")
def real_static_server(tmp_path_factory):
    """The REAL, unmodified `app/serve.py` + `app/static/` -- no override --
    for the two checks below that must be true of the actual shipped app, not
    a synthetic mount."""
    import uvicorn

    tmp_path = tmp_path_factory.mktemp("real-static")
    conf = tmp_path / "converge-app.toml"
    conf.write_text("", encoding="utf-8")
    made = _real_app(tmp_path / "secret", tmp_path / "state.json", tmp_path / "sessions.json", conf)
    port = _free_port()
    config = uvicorn.Config(made, host="127.0.0.1", port=port, log_level="warning")
    uv_server = uvicorn.Server(config)
    thread = threading.Thread(target=uv_server.run, daemon=True)
    thread.start()
    deadline = time.time() + 20
    while not uv_server.started and time.time() < deadline:
        time.sleep(0.05)
    assert uv_server.started, "app server did not start"
    yield f"http://127.0.0.1:{port}", made.state.static_revision
    uv_server.should_exit = True
    thread.join(timeout=10)


def test_the_real_running_app_also_refuses_its_own_dev_directory(real_static_server) -> None:
    """The synthetic mount above proves the CLASS's contract; this proves the
    REAL app actually wires it that way -- `app/static/dev/requests.log`
    exists for real in this checkout (the front-end stub writes it), so this
    is not a hypothetical file.

    WHAT WOULD FALSIFY THIS: either URL answering 200.
    """
    import httpx

    base, revision = real_static_server
    with httpx.Client(base_url=base, timeout=10.0) as client:
        for path in (f"/static/{revision}/dev/requests.log", "/static/dev/requests.log"):
            code = client.get(path).status_code
            print(f"  {code} {path}")
            assert code == 404, f"the real app answers for its own dev/ directory: {path} -> {code}"


def test_a_legacy_unversioned_static_url_still_answers_after_this_lanes_own_fix(real_static_server) -> None:
    """The old-unversioned migration story, proved against the real app: a
    tab or Cache Storage entry that recorded a PRE-converge-moe4,
    unversioned `/static/...` key must keep being answered -- `sw.js`'s
    `STATIC` cache (`converge-static-v4`) is unchanged and un-migrated, so
    what makes an old entry still viable is exactly this: the legacy route
    the app answered on before this lane still answers, unconditionally,
    after it.

    WHAT WOULD FALSIFY THIS: a real, currently-shipped static asset 404ing
    at its own old, unversioned URL.
    """
    import httpx

    base, revision = real_static_server
    with httpx.Client(base_url=base, timeout=10.0) as client:
        legacy = client.get("/static/js/main.js")
        versioned = client.get(f"/static/{revision}/js/main.js")
        print(f"\n  legacy   /static/js/main.js -> {legacy.status_code}")
        print(f"  versioned /static/{revision}/js/main.js -> {versioned.status_code}")
        assert legacy.status_code == 200, "the pre-existing, unversioned URL no longer answers"
        assert versioned.status_code == 200
        assert legacy.content == versioned.content, (
            "the legacy and versioned routes answered with DIFFERENT bytes for the same file -- "
            "an old tab and a new one would silently disagree about what main.js even is"
        )


# --------------------------------------------------------------------------
# two real server generations, one browser tab
# --------------------------------------------------------------------------


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "user.name=Test", "-c", "user.email=test@example.invalid", *args],
        cwd=repo, check=True, capture_output=True,
    )


def _free_port() -> int:
    s = socketlib.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


#: The exact, plain-text marker appended to each generation's own temp copy
#: of `collab.js`/`state.js` below. Never executed as anything but a plain
#: global assignment -- this proves WHICH generation's file actually ran,
#: never inferred from a URL alone (a server could, in principle, render the
#: right URL and still answer with the wrong bytes; this checks the bytes
#: that actually executed).
_MARKED = (
    ("js/render/collab.js", "__CONVERGE_COLLAB_GEN__"),
    ("js/state.js", "__CONVERGE_STATE_GEN__"),
)


def _build_generation(tmp_path: Path, name: str, marker: str) -> Path:
    """A full, real copy of this checkout's OWN `app/static/` -- every
    template reference, every worker precache entry, every real module
    import resolves exactly as it does in production -- with ONE marker
    line appended to `collab.js` and to the `state.js` it transitively
    imports. That is the only difference between generation A and
    generation B: enough for `compute_revision` to genuinely disagree, and
    enough to prove, by direct observation rather than inference, which
    generation's bytes actually executed in the browser.

    A plain trailing assignment is syntactically safe at the end of an ES
    module: `import`/`export` declarations are hoisted regardless of where
    they appear in the file, so appending a statement after them changes
    nothing about how the rest of the module already behaves.
    """
    dest = tmp_path / f"static_{name}"
    shutil.copytree(STATIC, dest)
    for rel, varname in _MARKED:
        path = dest / rel
        with path.open("a", encoding="utf-8") as fh:
            fh.write(f"\nif (typeof window !== 'undefined') window.{varname} = '{marker}';\n")
    return dest


@pytest.fixture(scope="module")
def project(tmp_path_factory) -> dict:
    """One manager over one real repository -- just enough for Home to list
    a card and Direction to render `collab.html` -- plus the two static
    generations this whole file is about."""
    tmp_path = tmp_path_factory.mktemp("pwa-same-tab-upgrade")
    repo = tmp_path / "repo"
    (repo / "docs").mkdir(parents=True)
    (repo / "docs" / "VISION.md").write_text("# Demo Vision (DRAFT)\n\nOne place.\n", encoding="utf-8")
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "seed: the vision")

    batch = tmp_path / "hw-demo"
    (batch / "goals").mkdir(parents=True)
    (batch / "HIGHWAY.md").write_text("# HIGHWAY\n\n## Outcome\nProve the seam.\n", encoding="utf-8")
    (batch / ".width").write_text("2\n", encoding="utf-8")
    (batch / "manifest.tsv").write_text("lane\tworktree\tbranch\tbase\ttmux\tgoal\tlog\tstarted\n", encoding="utf-8")

    conf = tmp_path / "converge-app.toml"
    conf.write_text(
        "[[managers]]\n"
        f'id = "{MANAGER}"\n'
        'name = "Demo manager"\n'
        f'batch_dir = "{batch}"\n'
        f'repos = ["{repo}"]\n'
        'tracker_project = ""\n'
        'tmux_socket = "pwa-upgrade-socket-that-does-not-exist"\n',
        encoding="utf-8",
    )
    return {
        "config": conf,
        # Shared, and NEVER regenerated between generations -- the same
        # signed session cookie must keep authenticating across the swap,
        # exactly as "preserve fixture auth/instance state" asks for.
        "secret": tmp_path / "secret",
        "state": tmp_path / "state.json",
        "sessions": tmp_path / "sessions.json",
        "static_a": _build_generation(tmp_path, "a", "A"),
        "static_b": _build_generation(tmp_path, "b", "B"),
        "port": _free_port(),
    }


def _app_for(project: dict, static_dir: Path):
    return serve.create_app(
        config_path=project["config"],
        secret_path=project["secret"],
        state_path=project["state"],
        sessions_path=project["sessions"],
        static_dir=static_dir,
    )


def _start(app, port: int):
    import uvicorn

    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    uv_server = uvicorn.Server(config)
    thread = threading.Thread(target=uv_server.run, daemon=True)
    thread.start()
    deadline = time.time() + 20
    while not uv_server.started and time.time() < deadline:
        time.sleep(0.05)
    assert uv_server.started, "app server did not start"
    return uv_server, thread


def _stop(uv_server, thread) -> None:
    uv_server.should_exit = True
    thread.join(timeout=10)


@pytest.fixture(scope="module")
def browser():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        b = p.chromium.launch(args=["--no-sandbox"])
        yield b
        b.close()


@needs_browser
def test_the_same_open_tab_adopts_a_new_server_generations_code_after_an_ordinary_navigation(
    project, browser
) -> None:
    """The core claim this file exists to prove. See this file's own module
    docstring for the full account of what each assertion below measures and
    what is deliberately left as a residual.
    """
    rev_a = assets.compute_revision(project["static_a"])
    rev_b = assets.compute_revision(project["static_b"])
    assert rev_a != rev_b, "the two generations' static trees must genuinely differ, or this proves nothing"
    print(f"\ngeneration A revision: {rev_a}\ngeneration B revision: {rev_b}")

    port = project["port"]
    base = f"http://127.0.0.1:{port}"

    uv_current, th_current = _start(_app_for(project, project["static_a"]), port)

    sessions = auth.Sessions(auth.read_or_make_secret(project["secret"]))
    ctx = browser.new_context(viewport={"width": 1280, "height": 800})
    ctx.add_cookies([{"name": auth.COOKIE, "value": sessions.issue(USER), "domain": "127.0.0.1", "path": "/"}])
    page = ctx.new_page()

    errors: list[str] = []
    page.on("console", lambda m: errors.append(f"console.{m.type}: {m.text}") if m.type == "error" else None)
    page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
    requests_seen: list[str] = []
    page.on("request", lambda r: requests_seen.append(r.url) if "/static/" in r.url else None)

    def _open_direction() -> None:
        page.goto(base, wait_until="networkidle")
        page.wait_for_selector(".home-manager-card", timeout=15000)
        page.click(".home-manager-card")
        page.wait_for_selector("#directionTab", timeout=15000)
        page.click("#directionTab")
        page.wait_for_selector("#documentModeContent", timeout=15000)

    try:
        # ---- generation A: the first, ordinary open --------------------
        _open_direction()
        page.wait_for_function("() => window.__CONVERGE_COLLAB_GEN__ === 'A'", timeout=15000)
        gen_a_collab = page.evaluate("() => window.__CONVERGE_COLLAB_GEN__")
        gen_a_state = page.evaluate("() => window.__CONVERGE_STATE_GEN__")
        print(f"generation A executed: collab={gen_a_collab!r} state={gen_a_state!r}")
        assert gen_a_collab == "A" and gen_a_state == "A", (
            f"generation A did not even execute its own code: collab={gen_a_collab!r} state={gen_a_state!r}"
        )
        gen_a_urls = sorted({u for u in requests_seen if "render/collab.js" in u or u.endswith("/state.js")})
        print(f"generation A asset URLs: {gen_a_urls}")
        assert any(rev_a in u for u in gen_a_urls), (
            f"generation A's own rendered HTML never asked for its own revision: {gen_a_urls}"
        )
        page.evaluate("async () => { await navigator.serviceWorker.ready; }")

        # ---- swap the live backend, on the SAME port, SAME page open ---
        requests_seen.clear()
        _stop(uv_current, th_current)
        uv_current, th_current = _start(_app_for(project, project["static_b"]), port)

        # ---- idle: nothing may adopt B on its own ----------------------
        # No navigation, no reload, nothing this test does, for a short
        # window -- this is the narrowest available proof that an unsent
        # draft would never be discarded merely because the backend changed
        # underneath an open tab (the full collab-panel-draft claim needs a
        # live pull-request fixture this lane does not own -- see this
        # file's module docstring).
        page.wait_for_timeout(1500)
        idle_collab = page.evaluate("() => window.__CONVERGE_COLLAB_GEN__")
        idle_state = page.evaluate("() => window.__CONVERGE_STATE_GEN__")
        print(f"idle after the backend swapped (no navigation): collab={idle_collab!r} state={idle_state!r}, "
              f"static requests made on its own: {requests_seen}")
        assert idle_collab == "A" and idle_state == "A", (
            "the page changed which generation's code is running on its own, with no navigation "
            f"this test made: collab={idle_collab!r} state={idle_state!r}"
        )
        assert not requests_seen, f"the idle page made static requests on its own: {requests_seen}"

        # Errors are examined starting HERE, not across the swap above: this
        # test's own orchestration (stopping one process, starting another)
        # creates a real, artificial gap in network connectivity that a
        # production deploy would also have in some form -- a fetch that
        # fails during THAT gap is a fact about this test's harness, not
        # about the app, and asserting zero errors across it would be
        # measuring the harness rather than the regression.
        errors.clear()

        # ---- the one deliberate act: an ORDINARY same-URL navigation ---
        _open_direction()
        page.wait_for_function("() => window.__CONVERGE_COLLAB_GEN__ === 'B'", timeout=15000)
        gen_b_collab = page.evaluate("() => window.__CONVERGE_COLLAB_GEN__")
        gen_b_state = page.evaluate("() => window.__CONVERGE_STATE_GEN__")
        print(f"after the ordinary same-URL navigation: collab={gen_b_collab!r} state={gen_b_state!r}")
        assert gen_b_collab == "B", (
            "an ordinary same-page navigation to generation B did not execute B's own collab.js -- "
            f"the page is still running stale code: {gen_b_collab!r}"
        )
        assert gen_b_state == "B", (
            "collab.js's own entry updated but the state module it transitively imports did not -- "
            f"module identity is incoherent on the same page: {gen_b_state!r}"
        )

        gen_b_urls = sorted({u for u in requests_seen if "render/collab.js" in u or u.endswith("/state.js")})
        print(f"generation B asset URLs: {gen_b_urls}")
        assert any(rev_b in u for u in gen_b_urls), (
            f"generation B's own rendered HTML never asked for its own revision: {gen_b_urls}"
        )
        assert not any(rev_a in u for u in gen_b_urls), (
            f"the page kept asking for generation A's own (now stale) revision after upgrading: {gen_b_urls}"
        )
        print(f"console/page errors across the upgrade: {errors or 'none'}")
        assert not errors, f"the browser logged errors across the upgrade itself: {errors}"
    finally:
        ctx.close()
        _stop(uv_current, th_current)


@needs_browser
def test_the_old_stable_url_scheme_is_the_reason_this_lane_moved_off_it(project, browser) -> None:
    """A documentary control, not a requirement of the CURRENT app -- which
    no longer renders any stable, unversioned static URL into its own HTML
    at all, so this failure mode is not reachable through the real app any
    more. What it reproduces, directly, is the mechanism `app/static/sw.js`'s
    own `2fca3d8` comment names: a browser's HTTP cache, a layer neither the
    app nor a service worker controls, can go on answering a STABLE URL with
    OLD bytes long after the server behind it changed -- proved here with
    the SAME `Page` and the SAME literal URL, across the SAME two real
    server generations the main test above uses.

    Whether a given Chromium build/profile reproduces this specific caching
    heuristic is itself environment-dependent (the same class of dependence
    `test_web_polish.py` already documents for offline emulation): where it
    does not, this reports that plainly and skips, rather than asserting a
    premise it could not actually stage.
    """
    port = project["port"]
    base = f"http://127.0.0.1:{port}"
    legacy_url = f"{base}/static/js/render/collab.js"

    uv_current, th_current = _start(_app_for(project, project["static_a"]), port)
    # `/static/` is a PUBLIC prefix (app/serve.py's PUBLIC_PREFIXES) on
    # purpose -- an asset a page already loaded must keep answering even
    # after a session ends -- so this control needs no auth cookie at all.
    ctx = browser.new_context(viewport={"width": 1280, "height": 800})
    page = ctx.new_page()

    try:
        page.goto(legacy_url, wait_until="load")
        first = page.evaluate("() => document.body.innerText")
        assert "'A'" in first, (
            f"generation A's own legacy URL did not even serve generation A's own bytes: {first[-200:]!r}"
        )

        _stop(uv_current, th_current)
        uv_current, th_current = _start(_app_for(project, project["static_b"]), port)

        page.goto(legacy_url, wait_until="load")
        second = page.evaluate("() => document.body.innerText")
        marker = "A" if "'A'" in second else ("B" if "'B'" in second else "?")
        print(f"\nsame legacy URL, same Page, after the backend swapped generations: marker={marker}")

        if marker == "B":
            pytest.skip(
                "this browser build revalidated the legacy, unversioned static URL on its own after "
                "the backend swapped generations, so the historical staleness this control documents "
                "was not reproducible here -- MANUAL_PROCEDURE-style verification on a real browser "
                "profile is what converge-moe4's own evidence was built on"
            )
        assert marker == "A", f"the legacy URL answered with neither generation's marker: {second[-200:]!r}"
        print("reproduced: the browser's own HTTP cache kept answering the OLD generation's bytes for "
              "the SAME stable URL after the backend moved on -- exactly the failure converge-moe4 fixes "
              "by never rendering a stable static URL into the real app's own HTML any more")
    finally:
        ctx.close()
        _stop(uv_current, th_current)
