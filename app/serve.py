"""The server: one gate, one set of routes, one place they are mounted.

The gate is a middleware rather than a per-route dependency on purpose. A
route added later — by this lane or another — is protected because it exists,
not because someone remembered to decorate it. Only a short, explicit list is
public: the sign-in page itself, the static files, and the branding.

Run it:

    uv run --extra app python -m app.serve --host 0.0.0.0 --port 8788
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from urllib.parse import quote, unquote

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from jinja2 import Environment, FileSystemLoader, TemplateNotFound, select_autoescape

from . import assets, auth, changes, config, data, presence, state_store, tls, writes

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent


def _branding_dir() -> Path:
    """Where `assets/branding` (favicons, the PWA icon set `/setup`/`/login`
    reference) actually lives -- a source checkout's own `<repo>/assets/branding`,
    or, installed from a wheel, the top-level sibling `pyproject.toml`'s
    `force-include` gives it (`amplifier_converge_branding`, beside the
    installed `app`/`amplifier_converge` packages, the same trick
    `amplifier_converge.appctl._wheel_scripts_dir` uses for `scripts/*`).

    Without this, `REPO_ROOT / "assets" / "branding"` resolves inside
    `site-packages` for a wheel install -- a real directory that simply never
    contains the branding assets, since a wheel's `packages` list never
    named `assets/` at all. That silently skipped the `/branding` mount
    entirely: every `<link>`/`<img>` in `login.html`/`setup.html` pointing at
    `/branding/...` rendered fine as HTML and then 404'd for real.
    """
    source = REPO_ROOT / "assets" / "branding"
    if source.is_dir():
        return source
    wheel = HERE.parent / "amplifier_converge_branding"
    return wheel if wheel.is_dir() else source

#: Paths that answer without a sign-in. Everything else needs the cookie.
#: `/setup` and `/ca.crt` are read-only and carry no private material -- the
#: CA's own PUBLIC certificate and trust instructions, nothing that needs a
#: session to look at (converge-b2ak, acceptance #3).
PUBLIC_PREFIXES = (
    "/login",
    "/static/",
    "/branding/",
    "/favicon",
    "/manifest.webmanifest",
    "/sw.js",
    "/healthz",
    "/setup",
    "/ca.crt",
)

#: Methods a CSRF/same-origin check applies to. GET/HEAD/OPTIONS never
#: change state, so they carry nothing to forge.
UNSAFE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})

#: The one path that answers without a cookie and is still a write, listed
#: apart from the prefixes above because it is matched WHOLE.
#:
#: `experience-collaboration.v1` Core 6 asks for webhooks where the host offers
#: them, and polling as the honest fallback. The route exists and works
#: (`app/collab.py`), but a repository host carries no `cv_session` cookie, so
#: the gate answered 401 and the host could never reach its own webhook --
#: measured 2026-09-04 on 127.0.0.1:8846, and the reason the freshness sentence
#: on the surface has always said polling. That is `converge-7cs`.
#:
#: What stands in for the cookie here is the route's own shared-secret check,
#: which is why this list must never grow a second entry casually and why the
#: check inside `collab.host_called` must never be relaxed at the same time.
#: Relax both and the app has gained an unauthenticated write.
#:
#: Matched whole rather than as a prefix on purpose: a prefix would also open
#: `/api/collab/webhooks/host/anything-at-all`, which is not what Core 6 asks
#: for and not what the secret check was written to cover.
#:
#: The string is taken from `collab.WEBHOOK_PATH` rather than written out again,
#: so the door and the route it opens cannot drift apart. The collab module is
#: optional here -- the mount below already treats it as optional -- and with it
#: absent there is no webhook route to open and nothing is public.
try:  # pragma: no cover - exercised by which modules are installed
    from . import collab as _collab

    PUBLIC_PATHS: tuple[str, ...] = (_collab.WEBHOOK_PATH,)
except ImportError:  # pragma: no cover - the collab surface is another lane's file
    PUBLIC_PATHS = ()

#: Who drafts the wording an ask proposes. `agent` runs a headless Amplifier
#: session per ask; anything else writes the proposal from the steward's own
#: words with no session at all, which is what the tests run and what an ask
#: falls back to when a session fails. Off by default: a route that shells out
#: to a minutes-long session on every call should be asked for, not assumed.
ASK_DRAFTER = os.environ.get("CONVERGE_ASK_DRAFTER", "fixture").strip().lower()


def _is_public(path: str) -> bool:
    if path in PUBLIC_PATHS:
        return True
    return path == "/login" or any(path.startswith(prefix) for prefix in PUBLIC_PREFIXES)


def _tmux_keys_target(path: str) -> tuple[str, str] | None:
    """(socket, session) if `path` is exactly `/api/tmux/{socket}/{session}/keys`,
    else None -- this is the one write in `app/tmux_view.py`'s router (converge-e2c3):
    every keystroke this app can ever send to a running session goes through it,
    so it is the one place steward authority has to be checked for tmux at all.

    `tmux_view.py` itself carries no manager/steward concept (see its own
    module docstring's scope) and one of its tests wires the router into a
    bare `FastAPI()` with no `app.state.settings` at all -- so the check
    belongs here, in the one gate that already knows both `who(request)` and
    every manager's registered steward, rather than inside that module.
    """
    parts = path.split("/")
    if len(parts) == 6 and parts[1] == "api" and parts[2] == "tmux" and parts[5] == "keys":
        return unquote(parts[3]), unquote(parts[4])
    return None


def _placeholder(name: str, why: str) -> HTMLResponse:
    """What a missing template says. Never a 500, never a fake screen."""
    return HTMLResponse(
        "<!doctype html><meta charset=utf-8>"
        f"<title>{name} is not here yet</title>"
        "<style>body{font:16px/1.6 system-ui;margin:4rem auto;max-width:38rem;color:#1c1d21}"
        "code{background:#f1f2f5;padding:.1em .35em;border-radius:4px}</style>"
        f"<h1>{name} is not here yet</h1><p>{why}</p>"
        "<p>The JSON API is live and answering — this page is the only thing missing.</p>",
        status_code=200,
    )


# --------------------------------------------------------------------------
# the steward-authority gate -- module level so any router (this file's own
# routes, or `collab.py`'s hosted-answer route) can reuse the SAME narrow
# policy rather than each growing its own copy that can drift out of sync.
# --------------------------------------------------------------------------
def who(request: Request) -> str:
    return getattr(request.state, "user", "") or ""


def _steward_denied(mc, request: Request) -> JSONResponse | None:
    """None when `who(request)` is this manager's own registered
    steward; otherwise a 403 that fails closed and says exactly why.

    `experience-collaboration.v1` Core 8, `direction.v1` Core 11
    (locking/ratification), and `operation.v1`'s steering/priority
    clauses reserve these actions to the registered steward, not to
    "any PAM login" -- being signed in proves who is asking, not that
    they are the one whose word counts here. Identity comes from the
    manager's own registration (`app/config.py`'s `steward` field,
    settled at registration time), never inferred from whoever happens
    to be signed in right now. An unregistered manager (`steward == ""`)
    has nobody authorized yet, so it is refused the same as a mismatch --
    never treated as "anyone may act" (converge-b2ak https-repair
    item 3).

    Deliberately narrow: feedback, proposal requests (`/ask`), personal
    read-points and kept marks, and every read-only route stay open to
    any signed-in user, per `preview-common.md`'s shared-interface note.

    converge-0zmv: also the guard `collab.answer_a_pull` calls (via a
    function-scoped import, to avoid any module-load-order coupling
    between the two files) before it records a ratification or posts
    back to the host -- see that function's own docstring.
    """
    steward = getattr(mc, "steward", "") or ""
    user = who(request)
    if not steward:
        return JSONResponse(
            {"error": "this manager session has no registered steward, so nobody may take this action"},
            status_code=403,
        )
    if user != steward:
        return JSONResponse(
            {
                "error": (
                    f"only the registered steward ({steward}) may take this action, "
                    f"not {user or '(signed out)'}"
                )
            },
            status_code=403,
        )
    return None


def create_app(
    config_path: Path | None = None,
    secret_path: Path | None = None,
    state_path: Path | None = None,
    tls_dir: Path | None = None,
    instance_dir: Path | None = None,
    sessions_path: Path | None = None,
    static_dir: Path | None = None,
) -> FastAPI:
    app = FastAPI(title="Amplifier Converge", docs_url=None, redoc_url=None)
    app.state.config_path = Path(config_path) if config_path else None
    app.state.settings = config.load(app.state.config_path)
    # A preview started with its own `--instance-dir` gets its own cookie
    # names, its own secret, and its own logout-revocation store -- never
    # another instance's, and never the machine-wide default unless no
    # instance directory was given at all. Ports do not scope cookies, so
    # two previews on the same host with no namespace WOULD otherwise read
    # and overwrite each other's session/CSRF cookies (converge-b2ak
    # https-repair item 1).
    instance_dir = Path(instance_dir) if instance_dir else None
    namespace = auth.instance_namespace(instance_dir)
    app.state.session_cookie, app.state.csrf_cookie = auth.cookie_names(namespace)
    resolved_secret_path = (
        Path(secret_path) if secret_path else (instance_dir / "secret" if instance_dir else None)
    )
    app.state.sessions = auth.Sessions(auth.read_or_make_secret(resolved_secret_path))
    # A logout ends THIS session, not merely this browser's copy of the
    # cookie (converge-b2ak https-repair item 2) -- see auth.SessionRegistry.
    # An explicit `sessions_path` (tests, mainly) always wins -- mirroring
    # `secret_path` above -- so a caller that names its own secret/state
    # files but never names a sessions path does not fall through to the
    # single machine-wide default and silently share/mutate it.
    resolved_sessions_path = (
        Path(sessions_path)
        if sessions_path
        else (instance_dir / "sessions.json" if instance_dir else auth.DEFAULT_SESSIONS_PATH)
    )
    app.state.session_registry = auth.SessionRegistry(path=resolved_sessions_path)
    # Where each steward's read point and kept marks live, so leaving the
    # page and coming back does not throw their answers away.
    app.state.store = state_store.Store(state_path)
    # Who has an editor open on which section, right now. In memory on
    # purpose: a mark is true for the next minute and a restart should forget
    # it (app/presence.py says why at length).
    app.state.presence = presence.Presence()
    # Where the local CA and leaf certificate live -- used by /ca.crt and
    # /setup to read what is already on disk. `main()` is what calls
    # `tls.ensure()`; this module never generates a certificate on a request.
    app.state.tls_dir = Path(tls_dir) if tls_dir else None
    # A burst of wrong passwords slows down rather than being ignored --
    # per-process, in memory, cleared by a restart (see auth.LoginThrottle).
    app.state.login_throttle = auth.LoginThrottle()

    # One revision for this server generation (converge-moe4, platform-web.v1
    # Core 9) -- computed once, here, and stored on THIS app's own state
    # rather than a module global, so two `create_app()` instances in one
    # process (routine in this project's own test suite) never poison each
    # other's rendered URLs. `static_dir` is created here (moved up from the
    # mounts section below, which now only reuses it) because the templates
    # Environment's own `static_url` global needs the revision before a
    # single template is ever rendered. `static_dir` itself is an optional
    # override (converge-moe4) -- ONLY the test suite ever passes one, to
    # stand up two server GENERATIONS with genuinely different bytes on the
    # SAME port (`test_pwa_same_tab_upgrade.py`): `create_app()` has no other
    # way to make two of its own instances compute two different revisions,
    # since the real `app/static/` on disk is a single, shared tree. Every
    # real caller (`main()` below, every other test) omits it and gets
    # exactly the unparameterized behaviour this had before -- this app's own
    # real static tree, unconditionally.
    static_dir = Path(static_dir) if static_dir else (HERE / "static")
    static_dir.mkdir(parents=True, exist_ok=True)
    static_revision = assets.compute_revision(static_dir)
    app.state.static_revision = static_revision

    templates = Environment(
        loader=FileSystemLoader(str(HERE / "templates")),
        autoescape=select_autoescape(["html", "xml"]),
    )
    # base.html/shell.html/collab.html render every first-party static
    # reference through this rather than a literal `/static/...` href/src --
    # see app/assets.py's own module docstring for why the revision belongs
    # in the URL. A relative ES-module import or CSS url() inside a file
    # this already versions inherits the same prefix for free: the browser
    # resolves it against the versioned document/module URL, not the
    # unversioned source path on disk.
    templates.globals["static_url"] = lambda relpath: assets.static_url(static_revision, relpath)

    def settings() -> config.AppConfig:
        # Re-read on demand: the file is the source of truth, not a snapshot
        # taken at boot. A manager added while the app runs shows up.
        app.state.settings = config.load(app.state.config_path)
        return app.state.settings

    def manager_or_none(mid: str):
        return settings().manager(mid)

    def render(name: str, **values) -> Response:
        try:
            template = templates.get_template(name)
        except TemplateNotFound:
            return _placeholder(name, f"The template <code>app/templates/{name}</code> has not been written yet.")
        return HTMLResponse(template.render(**values))

    # ----------------------------------------------------------------- gate
    #: `/login` is checked for CSRF inside its own route (below), against the
    #: form field FastAPI already parses -- not here. Reading `request.form()`
    #: in a middleware consumes the ASGI body stream; a route's OWN `Form(...)`
    #: parameters are the only safe reader for a form-encoded POST, because
    #: nothing else touches the stream first.
    FORM_CSRF_PATHS = frozenset({"/login"})

    def _client_key(request: Request) -> str:
        remote = request.client.host if request.client else "unknown"
        return remote

    def _with_csrf_cookie(request: Request, response: Response) -> Response:
        # Named on every response -- public or authenticated -- so a
        # browser-side script (api.js/tmux.js) never has to guess or
        # hardcode a cookie name that might belong to a different preview
        # instance sharing this host (converge-b2ak https-repair items 1
        # and 5).
        response.headers[auth.CSRF_COOKIE_NAME_HEADER] = app.state.csrf_cookie
        authed_user = getattr(request.state, "user", "") or ""
        if authed_user:
            # Derived only from verified auth state, never an untrusted
            # client claim -- the PWA lane's principal check (item 5).
            response.headers[auth.USER_HEADER] = authed_user
        # Only issued when the request did not already carry one -- a repeat
        # visitor keeps the same token rather than getting a new one on
        # every response, which would make the double-submit check useless.
        if not request.cookies.get(app.state.csrf_cookie):
            token = getattr(request.state, "csrf_token", None) or auth.new_csrf_token()
            response.set_cookie(
                app.state.csrf_cookie,
                token,
                max_age=auth.MAX_AGE,
                httponly=False,  # JS must read this to echo it back as a header
                samesite="lax",
                secure=request.url.scheme == "https",
                path="/",
            )
        return response

    @app.middleware("http")
    async def gate(request: Request, call_next):
        """Same-origin + CSRF on every unsafe method, then the sign-in cookie.

        There is deliberately no exemption for a loopback peer on the
        sign-in check below. When this process is bound to a LAN address,
        "the connection came from 127.0.0.1" says nothing about who is
        asking — and an exemption there would hand the whole app to
        anything that can reach the loopback.

        The CSRF/same-origin check runs first and applies to EVERY unsafe
        method on EVERY route except `PUBLIC_PATHS` (the collab webhook,
        which carries its own shared-secret proof instead of a cookie) —
        including `/login` and `/logout`, which the sign-in check below
        would otherwise treat as exempt. See `auth.py`'s module docstring
        for what each half actually catches and why an absent Origin/Referer
        or an absent `cv_csrf` cookie is not, by itself, treated as an attack.
        """
        path = request.url.path
        request.state.csrf_token = request.cookies.get(app.state.csrf_cookie) or auth.new_csrf_token()

        if request.method in UNSAFE_METHODS and path not in PUBLIC_PATHS:
            if not auth.same_origin(request.url.scheme, request.url.netloc,
                                     request.headers.get("origin"), request.headers.get("referer")):
                return JSONResponse({"error": "cross-origin request refused"}, status_code=403)
            if path not in FORM_CSRF_PATHS:
                supplied = request.headers.get(auth.CSRF_HEADER) or ""
                if not auth.csrf_ok(request.cookies.get(app.state.csrf_cookie), supplied):
                    return JSONResponse({"error": "missing or invalid CSRF token"}, status_code=403)

        if _is_public(path):
            response = await call_next(request)
            return _with_csrf_cookie(request, response)
        # A cookie that decodes cleanly still names a session that may have
        # been explicitly logged out -- `identity_of` proves only that this
        # app once issued it. `is_revoked` is what makes logout real
        # (converge-b2ak https-repair item 2), and it is checked here, on
        # every request, not only inside `/logout` itself.
        identity = app.state.sessions.identity_of(request.cookies.get(app.state.session_cookie))
        user = None
        if identity is not None:
            candidate, sid = identity
            if not app.state.session_registry.is_revoked(sid):
                user = candidate
        if not user:
            if path.startswith("/api/"):
                return JSONResponse({"error": "sign-in required"}, status_code=401)
            dest = quote(auth.safe_next(request.url.path))
            response = RedirectResponse(f"/login?next={dest}", status_code=302)
            return _with_csrf_cookie(request, response)
        request.state.user = user
        # A terminal keystroke is a write like decision/priority/steer, and
        # was missed here between lane ownerships (converge-e2c3): being
        # signed in proved who is asking, never that they may type into
        # this manager's own console -- only its registered steward may.
        if request.method == "POST":
            tmux_target = _tmux_keys_target(path)
            if tmux_target is not None:
                tmux_socket, tmux_session = tmux_target
                mc = settings().manager_for_tmux(tmux_socket, tmux_session)
                denied = (
                    JSONResponse(
                        {
                            "error": (
                                "no registered manager owns this tmux session, "
                                "so nobody may send keystrokes to it"
                            )
                        },
                        status_code=403,
                    )
                    if mc is None
                    else _steward_denied(mc, request)
                )
                if denied is not None:
                    return _with_csrf_cookie(request, denied)
        response = await call_next(request)
        return _with_csrf_cookie(request, response)

    # ------------------------------------------------------------- sign-in
    @app.get("/login")
    def login_form(request: Request, next: str = "/", error: str = "") -> Response:
        safe = auth.safe_next(next)
        # Same identity+revocation check the gate itself makes below --
        # `user_of` alone proves only that this app once signed the cookie,
        # never that the session it names is still good. Using `user_of`
        # here on its own (converge-iizz, caught by a real two-instance
        # browser test replaying a cookie saved before logout) sent a
        # revoked-but-signature-valid cookie straight back to "/", which the
        # gate then correctly bounced back to "/login" -- an infinite
        # redirect loop between the two, never surfaced by any single-page
        # TestClient check because none of them ever loaded "/login" itself
        # with a revoked cookie still attached.
        identity = app.state.sessions.identity_of(request.cookies.get(app.state.session_cookie))
        if identity is not None:
            _, sid = identity
            if not app.state.session_registry.is_revoked(sid):
                return RedirectResponse(safe, status_code=302)
        csrf_token = getattr(request.state, "csrf_token", "")
        try:
            template = templates.get_template("login.html")
        except TemplateNotFound:
            return HTMLResponse(
                "<!doctype html><meta charset=utf-8><title>Sign in — Converge</title>"
                "<style>body{font:16px/1.6 system-ui;margin:4rem auto;max-width:22rem}"
                "input,button{font:inherit;display:block;width:100%;margin:.4rem 0;padding:.5rem}</style>"
                "<h1>Sign in</h1>"
                + (f"<p style='color:#b3261e'>{error}</p>" if error else "")
                + f"<form method=post action=/login><input name=username placeholder=user autofocus>"
                f"<input name=password type=password placeholder=password>"
                f"<input type=hidden name=csrf_token value='{csrf_token}'>"
                f"<input type=hidden name=next value='{safe}'><button>Sign in</button></form>"
            )
        return HTMLResponse(template.render(next=safe, error=error, csrf_token=csrf_token))

    @app.post("/login")
    def login(
        request: Request,
        username: str = Form(""),
        password: str = Form(""),
        next: str = Form("/"),
        csrf_token: str = Form(""),
    ) -> Response:
        safe = auth.safe_next(next)
        if not auth.csrf_ok(request.cookies.get(app.state.csrf_cookie), csrf_token):
            return JSONResponse({"error": "missing or invalid CSRF token"}, status_code=403)
        key = _client_key(request)
        throttle: auth.LoginThrottle = app.state.login_throttle
        if not throttle.allowed(key):
            wait = int(throttle.retry_after(key)) + 1
            return RedirectResponse(
                f"/login?next={quote(safe)}&error=Too+many+attempts.+Try+again+in+{wait}s.",
                status_code=302,
            )
        if not auth.authenticate(username.strip(), password):
            throttle.record_failure(key)
            return RedirectResponse(f"/login?next={quote(safe)}&error=That+did+not+match.", status_code=302)
        throttle.record_success(key)
        answer = RedirectResponse(safe, status_code=302)
        answer.set_cookie(
            app.state.session_cookie,
            app.state.sessions.issue(username.strip()),
            max_age=auth.MAX_AGE,
            httponly=True,
            samesite="lax",
            secure=request.url.scheme == "https",
            path="/",
        )
        return answer

    @app.post("/logout")
    def logout(request: Request) -> Response:
        """Ends the session server-side, not only in this browser.

        Deleting the cookie alone would leave a copied or previously-saved
        token still valid until it expired on its own -- `identity_of` reads
        the session id the cookie names, and `session_registry.revoke`
        is what makes that id actually stop working on every future request,
        from any browser that still holds a copy of it (converge-b2ak
        https-repair item 2).
        """
        identity = app.state.sessions.identity_of(request.cookies.get(app.state.session_cookie))
        answer = RedirectResponse("/login", status_code=302)
        answer.delete_cookie(app.state.session_cookie, path="/")
        if identity is not None:
            _, sid = identity
            try:
                app.state.session_registry.revoke(sid)
            except auth.SessionRegistryCorrupt:
                # The registry itself cannot be trusted right now -- never
                # silently overwrite it with a fresh table that only holds
                # this one revocation (that would erase whatever history it
                # already held). The browser is still signed out below, and
                # the gate's own fail-closed `is_revoked` check already
                # refuses every session while the file is in this state, so
                # nothing stays reachable on a stolen/replayed cookie -- but
                # an operator needs to know the store itself needs repair,
                # not just this one cookie, so this is surfaced rather than
                # swallowed.
                error = JSONResponse(
                    {
                        "error": "session store unreadable; you have been signed out, "
                        "but the server operator must repair the session registry"
                    },
                    status_code=503,
                )
                error.delete_cookie(app.state.session_cookie, path="/")
                return error
        return answer

    @app.get("/healthz")
    def healthz() -> dict:
        return {"ok": True}

    # ------------------------------------------------------------ setup/CA
    @app.get("/ca.crt")
    def ca_cert() -> Response:
        """The local CA's PUBLIC certificate, and nothing else.

        Never the leaf certificate, never either private key -- see
        `app/tls.py`'s module docstring for why a person only ever needs to
        trust this one file. Deliberately public: trusting the CA is the
        step that happens BEFORE a sign-in is possible at all.
        """
        tls_dir = app.state.tls_dir
        p = tls.paths(tls_dir)
        if not p.ca_cert.is_file():
            return JSONResponse(
                {"error": "no CA certificate has been generated on this server yet"}, status_code=404
            )
        return Response(
            content=p.ca_cert.read_bytes(),
            media_type="application/x-x509-ca-cert",
            headers={"Content-Disposition": "attachment; filename=converge-preview-ca.crt"},
        )

    @app.get("/setup")
    def setup_page(request: Request) -> Response:
        """Trust instructions, read-only. Never a key, never a form over HTTP."""
        tls_dir = app.state.tls_dir
        insp = tls.inspect(tls_dir)
        fingerprint = ""
        if insp.ca_present:
            try:
                fingerprint = tls.fingerprint_sha256(tls.paths(tls_dir).ca_cert)
            except Exception:  # noqa: BLE001 - the page still renders without it
                fingerprint = ""
        return render(
            "setup.html",
            scheme=request.url.scheme,
            host=request.url.hostname or "",
            ca_present=insp.ca_present,
            leaf_present=insp.leaf_present,
            leaf_expires=insp.leaf_expires,
            leaf_sans=insp.leaf_sans,
            fingerprint=fingerprint,
            problems=insp.problems,
        )

    # ----------------------------------------------------------------- page
    @app.get("/")
    def shell(request: Request) -> Response:
        return render("shell.html", user=who(request))

    # ------------------------------------------------------------------ api
    @app.get("/api/boot")
    def boot(request: Request) -> JSONResponse:
        found = settings()
        return JSONResponse(
            {
                "user": who(request),
                "managers": [data.manager_payload(one) for one in found.managers],
                "config": {
                    "source": found.source,
                    "note": found.note,
                    "discovered": found.discovered,
                    # Every workspace root scanned for a manager session's own
                    # `.converge/<id>/registration.toml`. Carried so a steward
                    # whose session is missing from Home can see WHERE this app
                    # looked, rather than guessing at it.
                    "workspaces": [str(one) for one in found.workspaces],
                },
            }
        )

    @app.get("/api/managers/{mid}")
    def manager(mid: str) -> JSONResponse:
        mc = manager_or_none(mid)
        if mc is None:
            return JSONResponse({"error": f"no manager named {mid}"}, status_code=404)
        payload = data.manager_payload(mc)
        payload["repositories"] = data.repositories_payload(mc)
        return JSONResponse(payload)

    @app.get("/api/managers/{mid}/operation")
    def operation(mid: str) -> JSONResponse:
        mc = manager_or_none(mid)
        if mc is None:
            return JSONResponse({"error": f"no manager named {mid}"}, status_code=404)
        return JSONResponse(data.operation_payload(mc))

    def doc_or_none(mid: str, repo_ident: str, doc_ident: str):
        mc = manager_or_none(mid)
        if mc is None:
            return None, JSONResponse({"error": f"no manager named {mid}"}, status_code=404)
        found = data.find_doc(mc, repo_ident, doc_ident)
        if found is None:
            return None, JSONResponse({"error": f"no document {doc_ident} in {repo_ident}"}, status_code=404)
        return found, None

    #: The shortest prefix that may name a snapshot. `history_for` hands the
    #: browser eight characters; anything shorter than seven is as likely to
    #: name two commits as one, and resolving it to whichever matched first
    #: would restore wording from a commit nobody chose.
    SHA_FLOOR = 7

    #: How deep the bound reads this document's history. The History view
    #: shows eight rows; the bound reads far deeper on purpose, because a
    #: whole-document restore is one commit per sentence. Bounded at eight, a
    #: restore of eight sentences would push its own snapshot out of range
    #: partway through and be refused with half the work already written —
    #: the loop's own commits would have made its starting point unreachable.
    #: Every sha here is still a commit that touched THIS document and
    #: nothing else, which is the whole of what the bound promises.
    SNAPSHOT_DEPTH = 500

    def snapshot_or_refusal(repo: Path, path: Path, wanted: str):
        """One commit from THIS document's own history, or a refusal in words.

        `changes.changes_for` will diff any revision it is handed, so the
        bound has to be made here: a route that reads a document at any
        revision the caller names is a larger promise than
        `experience-direction.v1` §6 makes. What §6 asks for is the snapshots
        the History view shows, which is what `data.history_for` returns — so
        a commit that never touched this document is refused by name rather
        than resolved quietly.

        The refusal names the nearest few rather than every commit it read,
        because a refusal a steward cannot finish reading tells them nothing.
        """
        rows = data.history_for(Path(repo), Path(path), limit=SNAPSHOT_DEPTH)
        offered = [str(row.get("sha") or "") for row in rows if row.get("sha")]
        if len(wanted) >= SHA_FLOOR:
            for sha in offered:
                if sha.startswith(wanted) or wanted.startswith(sha):
                    return sha, None
        nearest = ", ".join(offered[:8]) or "none"
        rest = f", and {len(offered) - 8} older" if len(offered) > 8 else ""
        return "", JSONResponse(
            {
                "error": (
                    f"{wanted or '(no commit named)'} is not a commit in this document's history. "
                    f"The snapshots this document offers are: {nearest}{rest}."
                )
            },
            status_code=400,
        )

    @app.get("/api/managers/{mid}/docs/{repo_ident}/{doc_ident}")
    def document(mid: str, repo_ident: str, doc_ident: str, request: Request, since: str = "") -> JSONResponse:
        """This document, read from the steward's own point — or from one snapshot.

        `?since=<sha>` reads the document as it stood at one commit in its own
        history, for that one response only. It deliberately does **not** move
        the read point: the read point belongs to the steward, and looking at
        history is not reading. So a steward can open a snapshot, restore from
        it, and still come back to exactly the changes they had not answered.
        """
        found, refusal = doc_or_none(mid, repo_ident, doc_ident)
        if refusal is not None:
            return refusal
        repo, path = found
        user = who(request)
        store = app.state.store
        point = store.read_point(user, repo_ident, doc_ident)
        wanted = (since or "").strip()
        if wanted:
            point, refusal = snapshot_or_refusal(repo, path, wanted)
            if refusal is not None:
                return refusal
        return JSONResponse(
            data.doc_payload(repo, path, since=point, kept=store.kept(user, repo_ident, doc_ident))
        )

    # --------------------------------------------------- since you last read
    @app.post("/api/managers/{mid}/docs/{repo_ident}/{doc_ident}/read")
    def mark_read(mid: str, repo_ident: str, doc_ident: str, request: Request) -> JSONResponse:
        """Move this steward's read point to where the document stands now.

        The point is the document's own last commit rather than the branch
        tip, so "empty until it changes again" is exactly true: the next card
        appears when the next commit touches this file and not before.
        """
        found, refusal = doc_or_none(mid, repo_ident, doc_ident)
        if refusal is not None:
            return refusal
        repo, path = found
        head = changes.head_of(repo, Path(path).relative_to(repo).as_posix())
        if not head:
            return JSONResponse({"error": "this document has never been committed"}, status_code=400)
        app.state.store.set_read_point(who(request), repo_ident, doc_ident, head)
        return JSONResponse({"ok": True, "sha": head, "short": head[:7]})

    @app.post("/api/managers/{mid}/docs/{repo_ident}/{doc_ident}/changes/{change_id}/keep")
    async def keep_change(mid: str, repo_ident: str, doc_ident: str, change_id: str, request: Request) -> JSONResponse:
        found, refusal = doc_or_none(mid, repo_ident, doc_ident)
        if refusal is not None:
            return refusal
        try:
            body = await request.json()
        except Exception:
            body = {}
        on = bool(body.get("kept", True)) if isinstance(body, dict) else True
        here = app.state.store.keep(who(request), repo_ident, doc_ident, change_id, on)
        return JSONResponse({"ok": True, "kept": on, "keptIds": sorted(here)})

    async def _reword(mid, repo_ident, doc_ident, change_id, request, action) -> JSONResponse:
        """Edit or restore one sentence, from one reading of this document.

        Which reading is the caller's to name. With no `since` in the body it
        is the steward's own read point, as it always was; with one, it is
        that snapshot from this document's history — which is what lets a
        restore reach a wording older than anything the steward has read
        (`experience-direction.v1` §6). Nothing below this line changes:
        `writes.apply_change` is handed the card either way, and it is that
        function, reading the document's own H1, that decides whether this
        commits or becomes a proposal beside a locked document.

        **There is deliberately no `_steward_denied` call here, and its
        absence is the point** (converge-bk6o). One was added in `50d3c48`
        alongside the decision/lock/priority/steer gates, and it was too
        broad: `experience-collaboration.v1` Core 8 reserves whose *word
        counts* -- ratification, the authority to answer a proposal -- to the
        registered steward, and `Core 5`/`Core 9` are about that answer
        returning to its origin. None of them makes a teammate's ordinary
        draft edit the steward's business. `experience-direction.v1` Core 10
        promises the opposite outright: concurrent editing met with courtesy
        presence and reconciliation (Use combined / Keep mine / Review both),
        which cannot happen if only one signed-in person may ever write. A
        403 here turned that promise into a lock and lost a capability the
        app already had.

        What still protects the document is unchanged and sits below this
        line rather than in front of it: the gate middleware (signed in,
        same-origin, CSRF) has already run; `writes.apply_change` reads the
        document's own H1 and turns a write to a LOCKED document into a
        proposal beside it rather than mutating the source; and the
        collision path in `writes.py` is what keeps two writes from
        overwriting each other. Ratification (`/decision`), locking
        (`/lock`), `/priority`, `/steer` and terminal keystrokes keep their
        `_steward_denied` gates -- see `_steward_denied`'s own docstring.
        """
        found, refusal = doc_or_none(mid, repo_ident, doc_ident)
        if refusal is not None:
            return refusal
        repo, path = found
        user = who(request)
        try:
            body = await request.json()
        except Exception:
            body = {}
        body = body if isinstance(body, dict) else {}
        since = app.state.store.read_point(user, repo_ident, doc_ident)
        wanted_snapshot = str(body.get("since") or "").strip()
        if wanted_snapshot:
            since, refusal = snapshot_or_refusal(repo, path, wanted_snapshot)
            if refusal is not None:
                return refusal
        card = changes.find_change(repo, path, change_id, since=since)
        if card is None:
            return JSONResponse({"error": "that change is not in this reading any more"}, status_code=404)
        wanted = str(body.get("text") or "") if action == "edit" else card["before"]
        result = writes.apply_change(Path(repo), Path(path), change=card, text=wanted, action=action, user=user)
        return JSONResponse(result, status_code=200 if result.get("ok") else 400)

    @app.post("/api/managers/{mid}/docs/{repo_ident}/{doc_ident}/changes/{change_id}/edit")
    async def edit_change(mid: str, repo_ident: str, doc_ident: str, change_id: str, request: Request) -> JSONResponse:
        """The steward's own wording, in place of what the change proposed."""
        return await _reword(mid, repo_ident, doc_ident, change_id, request, "edit")

    @app.post("/api/managers/{mid}/docs/{repo_ident}/{doc_ident}/changes/{change_id}/restore")
    async def restore_change(mid: str, repo_ident: str, doc_ident: str, change_id: str, request: Request) -> JSONResponse:
        """The wording that was there before, back where it was.

        An optional `since` in the body names which "before" — any snapshot in
        this document's own history, not only the steward's read point.
        """
        return await _reword(mid, repo_ident, doc_ident, change_id, request, "restore")

    @app.post("/api/managers/{mid}/docs/{repo_ident}/{doc_ident}/lock")
    async def lock_document(mid: str, repo_ident: str, doc_ident: str, request: Request) -> JSONResponse:
        """Stamp this document's H1 so it becomes law — `experience-direction.v1` §11.

        The gate that decides whether the control is live is the browser's;
        the gate that decides whether a file changes is this one. It counts
        the four conditions again here rather than trusting the ones the
        browser ticked, so forcing the control reaches the same refusal — the
        same shape as the edit guard above, and for the same reason.
        """
        found, refusal = doc_or_none(mid, repo_ident, doc_ident)
        if refusal is not None:
            return refusal
        denied = _steward_denied(manager_or_none(mid), request)
        if denied is not None:
            return denied
        repo, path = found
        try:
            body = await request.json()
        except Exception:
            body = {}
        body = body if isinstance(body, dict) else {}
        raw = body.get("conditions")
        conditions = [str(one) for one in raw] if isinstance(raw, (list, tuple)) else []
        result = writes.lock_document(
            Path(repo),
            Path(path),
            conditions=conditions,
            repo_id=repo_ident,
            doc_id=doc_ident,
            user=who(request),
        )
        return JSONResponse(result, status_code=200 if result.get("ok") else 400)

    # ------------------------------------------- who is editing what, right now
    #
    # `experience-direction.v1` clause 10. The three routes below are the whole
    # channel: a browser says what it has open, anyone may read what is open,
    # and a writer that is not a browser asks whether to write or to wait.
    #
    # None of them is a lock. Nothing here refuses a write, and there is no
    # route that could -- what keeps two writes from overwriting each other is
    # the collision path in `app/writes.py`, which is untouched by this lane.

    @app.post("/api/managers/{mid}/presence")
    async def presence_beat(mid: str, request: Request) -> JSONResponse:
        """A browser saying what it has open. An empty section is goodbye.

        The same call refreshes and releases, so a browser cannot forget to
        say goodbye -- and one that is closed mid-sentence stops beating,
        which the expiry covers.
        """
        mc = manager_or_none(mid)
        if mc is None:
            return JSONResponse({"error": f"no manager named {mid}"}, status_code=404)
        try:
            body = await request.json()
        except Exception:
            body = {}
        body = body if isinstance(body, dict) else {}
        repo_ident = str(body.get("repoId") or "")
        doc_ident = str(body.get("docId") or "")
        if not repo_ident or not doc_ident:
            return JSONResponse({"error": "a presence mark names a repository and a document"}, status_code=400)
        user = who(request)
        app.state.presence.editing(
            user=user, repo=repo_ident, doc=doc_ident, section=str(body.get("section") or "")
        )
        here = app.state.presence.here(repo=repo_ident, doc=doc_ident)
        return JSONResponse({"ok": True, "you": user, **here,
                             "others": [one for one in here["editing"] if one["user"] != user]})

    @app.get("/api/managers/{mid}/presence")
    def presence_here(mid: str, request: Request, repoId: str = "", docId: str = "") -> JSONResponse:
        """Who has an editor open on this document, and who is waiting on it."""
        mc = manager_or_none(mid)
        if mc is None:
            return JSONResponse({"error": f"no manager named {mid}"}, status_code=404)
        if not repoId or not docId:
            return JSONResponse({"error": "name a repository and a document to read presence for"}, status_code=400)
        user = who(request)
        here = app.state.presence.here(repo=repoId, doc=docId)
        return JSONResponse({"ok": True, "you": user, **here,
                             "others": [one for one in here["editing"] if one["user"] != user]})

    @app.post("/api/managers/{mid}/presence/queue")
    async def presence_queue(mid: str, request: Request) -> JSONResponse:
        """The manager session's half: ask before writing, and wait if told to.

        This is the app holding up its end of clause 10. It answers whether a
        section is held and by whom, and records the wait so the steward can
        see that something is queued behind them. It does not write, defer, or
        replay the caller's work -- the caller keeps its own write and asks
        again. A session that asks and writes anyway is beyond what a server
        can honestly promise; being told plainly is what makes backing off
        cheap enough to actually do.
        """
        mc = manager_or_none(mid)
        if mc is None:
            return JSONResponse({"error": f"no manager named {mid}"}, status_code=404)
        try:
            body = await request.json()
        except Exception:
            body = {}
        body = body if isinstance(body, dict) else {}
        repo_ident = str(body.get("repoId") or "")
        doc_ident = str(body.get("docId") or "")
        section = str(body.get("section") or "")
        if not repo_ident or not doc_ident or not section:
            return JSONResponse(
                {"error": "a queued write names a repository, a document and a section"}, status_code=400
            )
        user = who(request)
        if body.get("release"):
            app.state.presence.unqueue(user=user, repo=repo_ident, doc=doc_ident, section=section)
            return JSONResponse({"ok": True, "queued": False, "released": True, "section": section})
        answer = app.state.presence.queue(
            user=user, repo=repo_ident, doc=doc_ident, section=section, note=str(body.get("note") or "")
        )
        return JSONResponse({"ok": True, "you": user, **answer})

    @app.get("/api/needs/{mid}")
    def needs(mid: str) -> JSONResponse:
        mc = manager_or_none(mid)
        if mc is None:
            return JSONResponse({"error": f"no manager named {mid}"}, status_code=404)
        return JSONResponse(data._needs_items(mc)[:5])

    # --------------------------------------------------------------- writes
    @app.post("/api/managers/{mid}/decision")
    async def decision(mid: str, request: Request) -> JSONResponse:
        mc = manager_or_none(mid)
        if mc is None:
            return JSONResponse({"error": f"no manager named {mid}"}, status_code=404)
        denied = _steward_denied(mc, request)
        if denied is not None:
            return denied
        body = await request.json()
        repo_ident = str(body.get("repoId") or "")
        target = next((r for r in mc.repos if data.repo_id(r) == repo_ident), mc.repo)
        if target is None:
            return JSONResponse({"error": "this manager has no repository to record against"}, status_code=400)
        result = writes.record_decision(
            Path(target),
            repo_id=repo_ident or data.repo_id(target),
            doc_id=str(body.get("docId") or ""),
            proposal_id=str(body.get("proposalId") or ""),
            decision=str(body.get("decision") or ""),
            note=str(body.get("note") or ""),
            user=who(request),
        )
        return JSONResponse(result)

    @app.post("/api/managers/{mid}/feedback")
    async def feedback(mid: str, request: Request) -> JSONResponse:
        mc = manager_or_none(mid)
        if mc is None:
            return JSONResponse({"error": f"no manager named {mid}"}, status_code=404)
        body = await request.json()
        target = mc.repo
        if target is None:
            return JSONResponse({"error": "this manager has no repository to write into"}, status_code=400)
        result = writes.record_feedback(
            Path(target),
            text=str(body.get("text") or ""),
            context=str(body.get("context") or ""),
            user=who(request),
            image_data_url=str(body.get("imageDataUrl") or ""),
        )
        return JSONResponse(result)

    @app.post("/api/managers/{mid}/priority")
    async def priority(mid: str, request: Request) -> JSONResponse:
        """Raise or lower one item's priority — `experience.v1` Core 4's second write.

        It lands in the batch's weave-in log, which is where the manager
        session reads what to do next; `writes.record_priority` says at length
        why that is the honest destination and what it deliberately does not
        claim to have changed. The refusals are the writer's own words, so
        forcing the control in the browser reaches the same sentence a bad
        payload does.
        """
        mc = manager_or_none(mid)
        if mc is None:
            return JSONResponse({"error": f"no manager named {mid}"}, status_code=404)
        denied = _steward_denied(mc, request)
        if denied is not None:
            return denied
        if not mc.batch_dir:
            return JSONResponse(
                {"error": "this manager has no batch directory to record a priority in"},
                status_code=400,
            )
        try:
            body = await request.json()
        except Exception:
            body = {}
        body = body if isinstance(body, dict) else {}
        result = writes.record_priority(
            Path(mc.batch_dir),
            item=str(body.get("item") or ""),
            direction=str(body.get("direction") or ""),
            note=str(body.get("note") or ""),
            title=str(body.get("title") or ""),
            user=who(request),
        )
        return JSONResponse(result, status_code=200 if result.get("ok") else 400)

    @app.post("/api/managers/{mid}/ask")
    async def ask(mid: str, request: Request) -> JSONResponse:
        """A scoped ask, answered with a proposal and nothing else.

        The fifth write `experience.v1` §4 names. It takes the scope the
        steward chose — a paragraph, this document, or every document in the
        repository — and returns the proposal it made, by name, so the client
        can send them to Review to answer it. It never edits the document: the
        writer does not open it for writing at any scope.
        """
        mc = manager_or_none(mid)
        if mc is None:
            return JSONResponse({"error": f"no manager named {mid}"}, status_code=404)
        try:
            body = await request.json()
        except Exception:
            body = {}
        body = body if isinstance(body, dict) else {}
        repo_ident = str(body.get("repoId") or "")
        doc_ident = str(body.get("docId") or "")
        found = data.find_doc(mc, repo_ident, doc_ident)
        if found is None:
            return JSONResponse(
                {"error": f"no document {doc_ident or '(none named)'} in {repo_ident or '(no repository named)'} to ask about"},
                status_code=404,
            )
        repo, path = found
        scope = str(body.get("scope") or "")
        result = writes.record_ask(
            Path(repo),
            Path(path),
            scope=scope,
            text=str(body.get("text") or ""),
            section=str(body.get("section") or ""),
            documents=data.repo_docs(Path(repo)) if scope == "all" else (),
            user=who(request),
            drafter=ASK_DRAFTER,
        )
        return JSONResponse(result, status_code=200 if result.get("ok") else 400)

    @app.post("/api/managers/{mid}/steer")
    async def steer(mid: str, request: Request) -> JSONResponse:
        mc = manager_or_none(mid)
        if mc is None:
            return JSONResponse({"error": f"no manager named {mid}"}, status_code=404)
        denied = _steward_denied(mc, request)
        if denied is not None:
            return denied
        if not mc.batch_dir:
            return JSONResponse({"error": "this manager has no batch directory to steer"}, status_code=400)
        body = await request.json()
        lanes = body.get("lanes")
        result = writes.steer(
            Path(mc.batch_dir),
            objective=str(body.get("objective") or ""),
            lanes=int(lanes) if isinstance(lanes, (int, str)) and str(lanes).strip().isdigit() else None,
            fill=bool(body.get("fill")),
            note=str(body.get("note") or ""),
            user=who(request),
        )
        return JSONResponse(result, status_code=200 if result.get("ok") else 400)

    # --------------------------------------------------------------- mounts
    # `static_dir`/`static_revision` were computed above, before the
    # templates Environment was built -- reused here rather than recomputed.
    app.mount(
        "/static",
        assets.VersionedStaticFiles(directory=str(static_dir), revision=static_revision),
        name="static",
    )

    from fastapi.responses import FileResponse

    @app.get("/manifest.webmanifest", include_in_schema=False)
    def manifest():
        return FileResponse(static_dir / "manifest.webmanifest", media_type="application/manifest+json")

    @app.get("/sw.js", include_in_schema=False)
    def service_worker():
        # Rendered fresh per request (a small text substitution over a small
        # file) rather than cached at app-creation time -- this server
        # generation's revision never changes while it runs, so there is
        # nothing to invalidate. The existing `Cache-Control: no-cache`
        # below is what actually governs the BROWSER's copy of this response.
        source = (static_dir / "sw.js").read_text(encoding="utf-8")
        rendered = assets.render_service_worker(source, static_revision)
        return Response(rendered, media_type="application/javascript",
                         headers={"Service-Worker-Allowed": "/", "Cache-Control": "no-cache"})


    branding_dir = _branding_dir()
    if branding_dir.is_dir():
        app.mount("/branding", StaticFiles(directory=str(branding_dir)), name="branding")

    # The terminal viewer is another lane's file. Its absence is normal here.
    try:
        from . import tmux_view  # type: ignore

        app.include_router(tmux_view.router)

        try:

            from app import collab as _collab

            app.include_router(_collab.router)

        except ImportError:

            pass

        try:

            from app import feedback_voice as _fv

            app.include_router(_fv.router)

        except ImportError:

            pass

    except ImportError:
        pass

    return app


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="app.serve", description="Serve the Converge companion app.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8788)
    parser.add_argument("--config", default=None, help="Path to converge-app.toml")
    parser.add_argument(
        "--state",
        default=None,
        help="Path to the read-point and kept-mark store (default ~/.amplifier/converge-app.state.json)",
    )
    parser.add_argument(
        "--tls-dir",
        default=None,
        help=f"Path to the local CA and leaf certificate (default {tls.DEFAULT_TLS_DIR})",
    )
    parser.add_argument(
        "--instance-dir",
        default=None,
        help=(
            "One directory naming THIS preview instance, isolating its signing secret, "
            "cookie names and logout-revocation store from any other instance on this "
            "host (default: the machine-wide ~/.amplifier files everyone shares -- fine "
            "for a single instance, wrong for two run side by side, since cookies are "
            "never scoped by port)."
        ),
    )
    args = parser.parse_args(argv)

    import uvicorn

    tls_dir = Path(args.tls_dir) if args.tls_dir else None
    instance_dir = Path(args.instance_dir) if args.instance_dir else None
    # HTTPS is mandatory -- there is no flag to fall back to plain HTTP.
    # `--host 127.0.0.1` (the SSH-tunnel case) still gets a certificate,
    # because "loopback" is a fact about the socket, not a promise that
    # nothing else on this machine can reach it.
    cert_paths = tls.ensure(tls_dir=tls_dir, extra_host=args.host)
    made = create_app(
        Path(args.config) if args.config else None,
        state_path=Path(args.state) if args.state else None,
        tls_dir=cert_paths.tls_dir,
        instance_dir=instance_dir,
    )
    found = made.state.settings
    print(f"config: {found.source}", flush=True)
    # Where registrations were looked for, said out loud at boot: a manager
    # session missing from Home is nearly always a workspace root nobody
    # scanned, and this is the one line that shows which ones were.
    for root in found.workspaces:
        print(f"  workspace root scanned: {root}/{config.CONVERGE_DIR}/*/{config.REGISTRATION_NAME}", flush=True)
    for one in found.managers:
        print(f"  manager {one.id}: batch={one.batch_dir} repos={[str(r) for r in one.repos]} socket={one.tmux_socket}", flush=True)
        print(f"    {one.origin or 'origin not recorded'}; last seen {one.last_seen or 'never'}", flush=True)
    fingerprint = tls.fingerprint_sha256(cert_paths.ca_cert)
    print(f"serving on https://{args.host}:{args.port} — every route behind a PAM sign-in", flush=True)
    print(f"  tls: {cert_paths.tls_dir}", flush=True)
    print(f"  ca fingerprint (sha256): {fingerprint}", flush=True)
    print(f"  trust it, or accept the browser warning once: https://{args.host}:{args.port}/setup", flush=True)
    uvicorn.run(
        made,
        host=args.host,
        port=args.port,
        log_level="info",
        ssl_keyfile=str(cert_paths.leaf_key),
        ssl_certfile=str(cert_paths.leaf_cert),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
