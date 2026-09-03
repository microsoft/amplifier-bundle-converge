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
from pathlib import Path
from urllib.parse import quote

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from jinja2 import Environment, FileSystemLoader, TemplateNotFound, select_autoescape

from . import auth, config, data, writes

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent

#: Paths that answer without a sign-in. Everything else needs the cookie.
PUBLIC_PREFIXES = ("/login", "/static/", "/branding/", "/favicon", "/manifest.webmanifest", "/sw.js", "/healthz")


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


def create_app(config_path: Path | None = None, secret_path: Path | None = None) -> FastAPI:
    app = FastAPI(title="Amplifier Converge", docs_url=None, redoc_url=None)
    app.state.config_path = Path(config_path) if config_path else None
    app.state.settings = config.load(app.state.config_path)
    app.state.sessions = auth.Sessions(auth.read_or_make_secret(secret_path))

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

    @app.get("/api/managers/{mid}/docs/{repo_ident}/{doc_ident}")
    def document(mid: str, repo_ident: str, doc_ident: str) -> JSONResponse:
        mc = manager_or_none(mid)
        if mc is None:
            return JSONResponse({"error": f"no manager named {mid}"}, status_code=404)
        found = data.find_doc(mc, repo_ident, doc_ident)
        if found is None:
            return JSONResponse({"error": f"no document {doc_ident} in {repo_ident}"}, status_code=404)
        return JSONResponse(data.doc_payload(*found))

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
    except ImportError:
        pass

    return app


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="app.serve", description="Serve the Converge companion app.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8788)
    parser.add_argument("--config", default=None, help="Path to converge-app.toml")
    args = parser.parse_args(argv)

    import uvicorn

    made = create_app(Path(args.config) if args.config else None)
    found = made.state.settings
    print(f"config: {found.source}", flush=True)
    for one in found.managers:
        print(f"  manager {one.id}: batch={one.batch_dir} repos={[str(r) for r in one.repos]} socket={one.tmux_socket}", flush=True)
    print(f"serving on http://{args.host}:{args.port} — every route behind a PAM sign-in", flush=True)
    uvicorn.run(made, host=args.host, port=args.port, log_level="info")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
