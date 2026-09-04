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
from urllib.parse import quote

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from jinja2 import Environment, FileSystemLoader, TemplateNotFound, select_autoescape

from . import auth, changes, config, data, presence, state_store, writes

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent

#: Paths that answer without a sign-in. Everything else needs the cookie.
PUBLIC_PREFIXES = ("/login", "/static/", "/branding/", "/favicon", "/manifest.webmanifest", "/sw.js", "/healthz")

#: Who drafts the wording an ask proposes. `agent` runs a headless Amplifier
#: session per ask; anything else writes the proposal from the steward's own
#: words with no session at all, which is what the tests run and what an ask
#: falls back to when a session fails. Off by default: a route that shells out
#: to a minutes-long session on every call should be asked for, not assumed.
ASK_DRAFTER = os.environ.get("CONVERGE_ASK_DRAFTER", "fixture").strip().lower()


def _is_public(path: str) -> bool:
    return path == "/login" or any(path.startswith(prefix) for prefix in PUBLIC_PREFIXES)


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


def create_app(
    config_path: Path | None = None,
    secret_path: Path | None = None,
    state_path: Path | None = None,
) -> FastAPI:
    app = FastAPI(title="Amplifier Converge", docs_url=None, redoc_url=None)
    app.state.config_path = Path(config_path) if config_path else None
    app.state.settings = config.load(app.state.config_path)
    app.state.sessions = auth.Sessions(auth.read_or_make_secret(secret_path))
    # Where each steward's read point and kept marks live, so leaving the
    # page and coming back does not throw their answers away.
    app.state.store = state_store.Store(state_path)
    # Who has an editor open on which section, right now. In memory on
    # purpose: a mark is true for the next minute and a restart should forget
    # it (app/presence.py says why at length).
    app.state.presence = presence.Presence()

    templates = Environment(
        loader=FileSystemLoader(str(HERE / "templates")),
        autoescape=select_autoescape(["html", "xml"]),
    )

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
    @app.middleware("http")
    async def gate(request: Request, call_next):
        """One check, by cookie only.

        There is deliberately no exemption for a loopback peer. When this
        process is bound to a LAN address, "the connection came from
        127.0.0.1" says nothing about who is asking — and an exemption there
        would hand the whole app to anything that can reach the loopback.
        """
        path = request.url.path
        if _is_public(path):
            return await call_next(request)
        user = app.state.sessions.user_of(request.cookies.get(auth.COOKIE))
        if not user:
            if path.startswith("/api/"):
                return JSONResponse({"error": "sign-in required"}, status_code=401)
            return RedirectResponse(f"/login?next={quote(request.url.path)}", status_code=302)
        request.state.user = user
        return await call_next(request)

    def who(request: Request) -> str:
        return getattr(request.state, "user", "") or ""

    # ------------------------------------------------------------- sign-in
    @app.get("/login")
    def login_form(request: Request, next: str = "/", error: str = "") -> Response:
        if app.state.sessions.user_of(request.cookies.get(auth.COOKIE)):
            return RedirectResponse(next or "/", status_code=302)
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
                f"<input type=hidden name=next value='{next}'><button>Sign in</button></form>"
            )
        return HTMLResponse(template.render(next=next, error=error))

    @app.post("/login")
    def login(username: str = Form(""), password: str = Form(""), next: str = Form("/")) -> Response:
        if not auth.authenticate(username.strip(), password):
            return RedirectResponse(f"/login?next={quote(next or '/')}&error=That+did+not+match.", status_code=302)
        target = next if next.startswith("/") else "/"
        answer = RedirectResponse(target, status_code=302)
        answer.set_cookie(
            auth.COOKIE,
            app.state.sessions.issue(username.strip()),
            max_age=auth.MAX_AGE,
            httponly=True,
            samesite="lax",
            path="/",
        )
        return answer

    @app.post("/logout")
    def logout() -> Response:
        answer = RedirectResponse("/login", status_code=302)
        answer.delete_cookie(auth.COOKIE, path="/")
        return answer

    @app.get("/healthz")
    def healthz() -> dict:
        return {"ok": True}

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
                "config": {"source": found.source, "note": found.note, "discovered": found.discovered},
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

    @app.get("/api/managers/{mid}/docs/{repo_ident}/{doc_ident}")
    def document(mid: str, repo_ident: str, doc_ident: str, request: Request) -> JSONResponse:
        found, refusal = doc_or_none(mid, repo_ident, doc_ident)
        if refusal is not None:
            return refusal
        user = who(request)
        store = app.state.store
        return JSONResponse(
            data.doc_payload(
                *found,
                since=store.read_point(user, repo_ident, doc_ident),
                kept=store.kept(user, repo_ident, doc_ident),
            )
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
        found, refusal = doc_or_none(mid, repo_ident, doc_ident)
        if refusal is not None:
            return refusal
        repo, path = found
        user = who(request)
        since = app.state.store.read_point(user, repo_ident, doc_ident)
        card = changes.find_change(repo, path, change_id, since=since)
        if card is None:
            return JSONResponse({"error": "that change is not in this reading any more"}, status_code=404)
        if action == "edit":
            try:
                body = await request.json()
            except Exception:
                body = {}
            wanted = str((body or {}).get("text") or "")
        else:
            wanted = card["before"]
        result = writes.apply_change(Path(repo), Path(path), change=card, text=wanted, action=action, user=user)
        return JSONResponse(result, status_code=200 if result.get("ok") else 400)

    @app.post("/api/managers/{mid}/docs/{repo_ident}/{doc_ident}/changes/{change_id}/edit")
    async def edit_change(mid: str, repo_ident: str, doc_ident: str, change_id: str, request: Request) -> JSONResponse:
        """The steward's own wording, in place of what the change proposed."""
        return await _reword(mid, repo_ident, doc_ident, change_id, request, "edit")

    @app.post("/api/managers/{mid}/docs/{repo_ident}/{doc_ident}/changes/{change_id}/restore")
    async def restore_change(mid: str, repo_ident: str, doc_ident: str, change_id: str, request: Request) -> JSONResponse:
        """The wording that was there before, back where it was."""
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
    static_dir = HERE / "static"
    static_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    from fastapi.responses import FileResponse

    @app.get("/manifest.webmanifest", include_in_schema=False)
    def manifest():
        return FileResponse(static_dir / "manifest.webmanifest", media_type="application/manifest+json")

    @app.get("/sw.js", include_in_schema=False)
    def service_worker():
        return FileResponse(static_dir / "sw.js", media_type="application/javascript",
                            headers={"Service-Worker-Allowed": "/", "Cache-Control": "no-cache"})


    branding_dir = REPO_ROOT / "assets" / "branding"
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
    args = parser.parse_args(argv)

    import uvicorn

    made = create_app(
        Path(args.config) if args.config else None,
        state_path=Path(args.state) if args.state else None,
    )
    found = made.state.settings
    print(f"config: {found.source}", flush=True)
    for one in found.managers:
        print(f"  manager {one.id}: batch={one.batch_dir} repos={[str(r) for r in one.repos]} socket={one.tmux_socket}", flush=True)
    print(f"serving on http://{args.host}:{args.port} — every route behind a PAM sign-in", flush=True)
    uvicorn.run(made, host=args.host, port=args.port, log_level="info")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
