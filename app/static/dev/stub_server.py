#!/usr/bin/env python3
"""Front-end dev stub: serves app/templates + app/static against JSON fixtures
shaped exactly per the app contract. NOT the backend — the backend lane owns
app/serve.py, PAM auth, and the real API. This exists so the front-end lane can
prove the app boots, navigates, and posts, with nothing invented at runtime.

    python3 app/static/dev/stub_server.py --port 8799

Every POST is appended to app/static/dev/requests.log so a decision can be shown.
"""
import argparse
import json
import pathlib
import datetime

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from jinja2 import Environment, FileSystemLoader, select_autoescape

DEV = pathlib.Path(__file__).resolve().parent
ROOT = DEV.parents[2]
STATIC = ROOT / "app" / "static"
TEMPLATES = ROOT / "app" / "templates"
BRANDING = ROOT / "assets" / "branding"
FIXTURES = DEV / "fixtures"
LOG = DEV / "requests.log"

env = Environment(loader=FileSystemLoader(str(TEMPLATES)), autoescape=select_autoescape(["html"]))
app = FastAPI()


def fixture(name: str):
    path = FIXTURES / f"{name}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text())


def log(line: str) -> None:
    stamp = datetime.datetime.now().isoformat(timespec="seconds")
    with LOG.open("a") as fh:
        fh.write(f"[{stamp}] {line}\n")
    print(f"[{stamp}] {line}", flush=True)


@app.get("/", response_class=HTMLResponse)
def shell():
    return env.get_template("shell.html").render(user="bkrabach")


@app.get("/login", response_class=HTMLResponse)
def login(next: str = "/"):
    return env.get_template("login.html").render(next=next)


@app.post("/login")
async def do_login(request: Request):
    form = await request.form()
    log(f"POST /login user={form.get('username')!r} (stub accepts everyone)")
    return RedirectResponse(form.get("next") or "/", status_code=302)


@app.get("/manifest.webmanifest")
def manifest():
    return FileResponse(STATIC / "manifest.webmanifest", media_type="application/manifest+json")


@app.get("/sw.js")
def service_worker():
    return FileResponse(STATIC / "sw.js", media_type="text/javascript")


@app.get("/api/boot")
def boot():
    return fixture("boot")


@app.get("/api/managers/{mid}")
def manager(mid: str):
    return fixture(f"manager.{mid}") or JSONResponse({"error": "no such manager"}, status_code=404)


@app.get("/api/managers/{mid}/operation")
def operation(mid: str):
    return fixture(f"operation.{mid}") or JSONResponse({"error": "no operation"}, status_code=404)


@app.get("/api/managers/{mid}/docs/{repo_id}/{doc_id}")
def doc(mid: str, repo_id: str, doc_id: str):
    return fixture(f"doc.{mid}.{repo_id}.{doc_id}") or JSONResponse({"error": "no such document"}, status_code=404)


@app.get("/api/needs/{mid}")
def needs(mid: str):
    return fixture(f"needs.{mid}") or []


@app.post("/api/managers/{mid}/decision")
async def decision(mid: str, request: Request):
    body = await request.json()
    log(f"POST /api/managers/{mid}/decision {json.dumps(body)}")
    day = datetime.date.today().isoformat()
    return {"ok": True, "recorded": f"docs/workflow/owner-ratifications-{day}.md#{body.get('proposalId', '')}"}


@app.post("/api/managers/{mid}/feedback")
async def feedback(mid: str, request: Request):
    body = await request.json()
    trimmed = {k: (v[:60] + "…" if isinstance(v, str) and len(v) > 60 else v) for k, v in body.items()}
    log(f"POST /api/managers/{mid}/feedback {json.dumps(trimmed)}")
    return {"ok": True, "path": f".converge/feedback/{datetime.datetime.now().isoformat(timespec='seconds')}.md"}


@app.post("/api/managers/{mid}/steer")
async def steer(mid: str, request: Request):
    body = await request.json()
    log(f"POST /api/managers/{mid}/steer {json.dumps(body)}")
    return {"ok": True}


app.mount("/static", StaticFiles(directory=str(STATIC)), name="static")
app.mount("/branding", StaticFiles(directory=str(BRANDING)), name="branding")


if __name__ == "__main__":
    import uvicorn

    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8799)
    args = parser.parse_args()
    uvicorn.run(app, host=args.host, port=args.port, log_level="warning")
