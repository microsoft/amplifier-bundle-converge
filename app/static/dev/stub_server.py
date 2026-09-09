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
import sys

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, FileResponse, Response
from fastapi.staticfiles import StaticFiles
from jinja2 import Environment, FileSystemLoader, select_autoescape

DEV = pathlib.Path(__file__).resolve().parent
ROOT = DEV.parents[2]
STATIC = ROOT / "app" / "static"
TEMPLATES = ROOT / "app" / "templates"
BRANDING = ROOT / "assets" / "branding"
FIXTURES = DEV / "fixtures"
LOG = DEV / "requests.log"

sys.path.insert(0, str(ROOT))
from app import assets  # noqa: E402  -- the same helper app/serve.py uses; see its module docstring

# One revision for this stub process's own lifetime. A plain module global is
# fine here (unlike app/serve.py's create_app, which the real test suite
# instantiates several times in one process) -- this script starts exactly
# one long-running FastAPI app, never a second one to poison.
STATIC_REVISION = assets.compute_revision(STATIC)

env = Environment(loader=FileSystemLoader(str(TEMPLATES)), autoescape=select_autoescape(["html"]))
env.globals["static_url"] = lambda relpath: assets.static_url(STATIC_REVISION, relpath)
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
    return env.get_template("shell.html").render(user="project-steward")


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
    source = (STATIC / "sw.js").read_text(encoding="utf-8")
    rendered = assets.render_service_worker(source, STATIC_REVISION)
    return Response(rendered, media_type="text/javascript")


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


# --------------------------------------------------------------------------
# the console's own two routes
#
# The front end asks for these on every load, whether or not anyone opens the
# tab: the terminal view polls, and the collaboration panel polls (clause 6 --
# a change on the host is already here when the panel is opened). A stub that
# does not answer them is not a quiet gap; it is four console errors on every
# run, and a terminal tab that reads "observation failed -- HTTP 404" against a
# stub that is otherwise complete.
#
# Both answer in the shape the real app answers in -- `app/tmux_view.py`'s
# Frame.as_dict() and `app/collab.py`'s list_pulls() -- so what the front end
# is proved against here is the payload it will meet in production.
# --------------------------------------------------------------------------


@app.get("/api/tmux/{socket}/{session}")
def tmux_frame(socket: str, session: str, lines: int = 200):
    """One frame of one pane, shaped as app/tmux_view.py's Frame.as_dict().

    The identity echo is taken from the REQUEST, never from the fixture, for
    the same reason the real route echoes it: the client binds its viewer to
    `socket`/`session` and can prove the frame it is painting belongs to the
    session it asked for. A fixture that answered with its own baked-in
    identity would let a mistargeted request look answered.

    A session with no fixture gets `ended`, not `ok` with empty text -- the
    four states are never conflated (field guide: an empty pane and a failed
    observation both yield empty text, and presenting either as healthy is the
    failure the design guards against).
    """
    lines = max(1, min(int(lines), 2000))
    captured = fixture(f"tmux.{socket}.{session}")
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    if captured is None:
        return {
            "state": "ended",
            "text": "",
            "geometry": None,
            "captured_at": now,
            "socket": socket,
            "session": session,
            "lines": lines,
            "detail": f"can't find session: {session}",
        }
    return {
        "state": captured.get("state", "ok"),
        "text": captured.get("text", ""),
        "geometry": captured.get("geometry"),
        "captured_at": now,
        "socket": socket,
        "session": session,
        "lines": lines,
        "detail": captured.get("detail", ""),
    }


@app.post("/api/tmux/{socket}/{session}/keys")
async def tmux_keys(socket: str, session: str, request: Request):
    """Carry a keystroke to the pane, and say what happened.

    The stub cannot echo the line back into the fixture's pane text, so what it
    proves is narrower than the real route: that the client's write reaches a
    server, is bounded, and is answered in the shape the client reads. It says
    so in `detail` rather than letting `ok` be read as "the pane received it".
    """
    body = await request.json()
    keys = str(body.get("keys") or "")
    enter = bool(body.get("enter"))
    log(f"POST /api/tmux/{socket}/{session}/keys keys={keys[:60]!r} enter={enter}")
    truncated = len(keys) > 4096
    return {
        "sent": True,
        "state": "ok",
        "socket": socket,
        "session": session,
        "keys": len(keys[:4096]),
        "enter": enter,
        "truncated": truncated,
        "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "detail": "the dev stub recorded this send; no live pane echoed it back",
        "ambient_tmux_ignored": None,
    }


@app.get("/api/collab/{mid}/pulls")
def collab_pulls(mid: str):
    """Open pull requests as proposals, shaped as app/collab.py's list_pulls().

    A manager with no fixture answers 404 exactly as the real route does for an
    unknown manager -- the stub does not invent a session that was never
    registered.
    """
    found = fixture(f"pulls.{mid}")
    if found is None:
        return JSONResponse({"error": f"no manager named {mid}"}, status_code=404)
    return found


app.mount("/static", assets.VersionedStaticFiles(directory=str(STATIC), revision=STATIC_REVISION), name="static")
app.mount("/branding", StaticFiles(directory=str(BRANDING)), name="branding")


if __name__ == "__main__":
    import uvicorn

    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8799)
    args = parser.parse_args()
    uvicorn.run(app, host=args.host, port=args.port, log_level="warning")
