#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["fastapi>=0.110", "uvicorn>=0.27"]
# ///
"""Amplifier Converge — the shape of the app, running.

    uv run poc/serve.py --repo . --port 8098

One page, two places, one console pane. Everything it shows is read from the
project at the moment you ask for it; the four things you can do are appended
to plain files beside this script so you can see exactly what a write is.

This implementation may be thrown away. The promises are the keeper.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent
# The project's own readers are used read-only; nothing here writes into src/.
for extra in (str(HERE), str(REPO_ROOT / "src")):
    if extra not in sys.path:
        sys.path.insert(0, extra)

from fastapi import FastAPI, Request  # noqa: E402
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402

import data  # noqa: E402
from console_connector import load_canned  # noqa: E402

TEMPLATES = HERE / "templates"
STATIC = HERE / "static"
VENDOR = HERE / "vendor"

#: The four things you can do, each appended to its own file. One line per
#: write, in the order you made them, readable without a tool.
WRITE_FILES = {
    "answer": HERE / "ratifications.jsonl",
    "feedback": HERE / "feedback.jsonl",
    "steer": HERE / "steer.jsonl",
    "ask": HERE / "asks.jsonl",
}

ANSWER_WORDS = ("ratified", "ratified with edits", "declined", "later")


def append(kind: str, record: dict) -> dict:
    record = {"at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), **record}
    path = WRITE_FILES[kind]
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    return record


def read_writes(kind: str) -> list[dict]:
    path = WRITE_FILES[kind]
    if not path.is_file():
        return []
    out: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def build(repo: Path) -> FastAPI:
    app = FastAPI(title="Amplifier Converge — proof of concept", docs_url=None, redoc_url=None)
    console = load_canned("your manager session")

    app.mount("/static", StaticFiles(directory=STATIC), name="static")
    app.mount("/vendor", StaticFiles(directory=VENDOR), name="vendor")

    # -- what the page shows ---------------------------------------------

    def boot() -> dict:
        asks = read_writes("ask")
        return {
            "project": repo.name,
            "managers": data.manager_sessions(repo),
            "brief": data.return_brief(repo),
            "queue": data.queue(repo),
            "lanes": data.lanes(repo),
            "documents": data.documents(repo),
            "proposals": data.proposals(repo, asks),
            "strategy": data.strategy(),
            "waves": data.waves(),
            "confidence": data.confidence(),
            "answers": read_writes("answer"),
            "feedback": read_writes("feedback"),
            "steers": read_writes("steer"),
        }

    @app.get("/", response_class=HTMLResponse)
    def home() -> HTMLResponse:
        shell = (TEMPLATES / "index.html").read_text(encoding="utf-8")
        payload = json.dumps(boot(), ensure_ascii=False).replace("</", "<\\/")
        return HTMLResponse(shell.replace("__BOOT__", payload))

    @app.get("/api/boot")
    def api_boot() -> JSONResponse:
        return JSONResponse(boot())

    @app.get("/api/document/{slug}")
    def api_document(slug: str) -> JSONResponse:
        return JSONResponse(data.document(repo, slug))

    @app.get("/api/changes/{slug}")
    def api_changes(slug: str) -> JSONResponse:
        return JSONResponse(data.changes(repo, slug))

    # -- the console ------------------------------------------------------

    @app.get("/api/console/{session}")
    def api_console(session: str) -> JSONResponse:
        chunks = [piece.decode("utf-8", "replace") for piece in console.attach(session)]
        return JSONResponse({"session": session, "chunks": chunks, "real": False,
                             "note": "A recorded session. The live connector is named and empty at poc/console_connector.py."})

    @app.post("/api/console/{session}/keys")
    async def api_console_keys(session: str, request: Request) -> JSONResponse:
        body = await request.json()
        console.send(session, str(body.get("keys", "")).encode("utf-8"))
        chunks = [piece.decode("utf-8", "replace") for piece in console.attach(session)]
        return JSONResponse({"session": session, "chunks": chunks[-2:]})

    # -- the things you can do -------------------------------------------

    @app.post("/api/answer")
    async def api_answer(request: Request) -> JSONResponse:
        body = await request.json()
        word = str(body.get("word", "")).strip().lower()
        if word not in ANSWER_WORDS:
            return JSONResponse({"ok": False, "note": "That is not one of the four words."}, status_code=400)
        record = append("answer", {
            "proposal": body.get("proposal", ""),
            "title": body.get("title", ""),
            "word": word,
            "note": body.get("note", ""),
        })
        return JSONResponse({"ok": True, "record": record, "file": "poc/ratifications.jsonl"})

    @app.post("/api/feedback")
    async def api_feedback(request: Request) -> JSONResponse:
        body = await request.json()
        text = str(body.get("text", "")).strip()
        if not text:
            return JSONResponse({"ok": False, "note": "Say something first."}, status_code=400)
        record = append("feedback", {"text": text, "about": body.get("about", "")})
        return JSONResponse({"ok": True, "record": record, "file": "poc/feedback.jsonl"})

    @app.post("/api/steer")
    async def api_steer(request: Request) -> JSONResponse:
        body = await request.json()
        record = append("steer", {
            "what": str(body.get("what", "")).strip(),
            "value": str(body.get("value", "")).strip(),
        })
        return JSONResponse({"ok": True, "record": record, "file": "poc/steer.jsonl"})

    @app.post("/api/ask")
    async def api_ask(request: Request) -> JSONResponse:
        body = await request.json()
        question = str(body.get("question", "")).strip()
        paragraph = str(body.get("paragraph", "")).strip()
        n = len(read_writes("ask")) + 1
        record = append("ask", {
            "key": f"asked-{n:03d}",
            "title": f"A proposal you asked for on {body.get('document', 'a document')}",
            "document": body.get("document", ""),
            "target": body.get("target", ""),
            "anchor": body.get("anchor", ""),
            "paragraph": paragraph,
            "question": question,
        })
        return JSONResponse({"ok": True, "record": record, "file": "poc/asks.jsonl"})

    # -- installable web app ----------------------------------------------

    @app.get("/manifest.webmanifest")
    def manifest() -> FileResponse:
        return FileResponse(STATIC / "manifest.webmanifest", media_type="application/manifest+json")

    @app.get("/sw.js")
    def service_worker() -> FileResponse:
        return FileResponse(STATIC / "sw.js", media_type="text/javascript")

    return app


def main() -> int:
    parser = argparse.ArgumentParser(description="Amplifier Converge — the shape of the app, running.")
    parser.add_argument("--repo", default=".", help="the project to read")
    parser.add_argument("--port", type=int, default=8098)
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args()

    repo = Path(args.repo).resolve()
    if not repo.is_dir():
        print(f"There is no project at {repo}.", file=sys.stderr)
        return 2

    import uvicorn

    print(f"Reading {repo}")
    print(f"Open http://{args.host}:{args.port}/")
    uvicorn.run(build(repo), host=args.host, port=args.port, log_level="warning")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
