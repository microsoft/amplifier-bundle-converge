"""The server — a loopback web page beside your project.

Every POST that changes the project goes through `/do/<write>`, and there are
exactly four of those because there are exactly four writes. One further POST
exists, `mark-read`, and it changes nothing about the project at all: it moves
the page's own last-read marker, which lives outside the repository. It is
named here so that "exactly four" stays a claim anyone can check rather than a
claim you have to take on trust.
"""

from __future__ import annotations

from pathlib import Path
from urllib.parse import quote

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse

from ..reading import Reading
from ..reading import brief as brief_reader
from ..reading import snapshot as snapshot_reader
from ..reading import strip as strip_reader
from ..reading.documents import find_document
from ..reading.proposals import find_proposal
from ..reading.queue import read_managers
from ..reading.whatchanged import mark_read, what_changed
from ..writing import WRITES, by_name
from . import pages

#: POST routes that deliberately change nothing about the project.
NON_WRITE_POSTS = ("/direction/{slug}/mark-read",)

#: Every write is reachable at exactly this path, and nowhere else.
WRITE_ROUTE_PREFIX = "/do/"


def _flash(request: Request) -> tuple[str, bool] | None:
    message = request.query_params.get("said")
    if not message:
        return None
    return message, request.query_params.get("ok", "1") != "0"


def _back(target: str, result_message: str, ok: bool) -> RedirectResponse:
    joiner = "&" if "?" in target else "?"
    url = f"{target}{joiner}said={quote(result_message)}&ok={'1' if ok else '0'}"
    return RedirectResponse(url, status_code=303)


def create_app(
    repo: Path,
    project: str,
    batch_dir: Path | None = None,
    include_remote_proposals: bool = True,
) -> FastAPI:
    repo = Path(repo).resolve()
    app = FastAPI(title="Amplifier Converge", docs_url=None, redoc_url=None)
    app.state.repo = repo
    app.state.project = project
    app.state.batch_dir = batch_dir

    def look():
        return snapshot_reader.take(
            repo, project, batch_dir, include_remote_proposals=include_remote_proposals
        )

    def page(title: str, place: str, body: str, request: Request, snap) -> HTMLResponse:
        return HTMLResponse(
            pages.shell(
                title=title,
                place=place,
                snapshot=snap,
                waiting=len(strip_reader.build(snap)),
                body=body,
                flash=_flash(request),
            )
        )

    # ---------------------------------------------------------------- read

    @app.get("/", response_class=HTMLResponse)
    def landing(request: Request) -> HTMLResponse:
        snap = look()
        decisions = strip_reader.build(snap)
        return page("Needs your word", "landing", pages.landing(snap, decisions), request, snap)

    @app.get("/direction", response_class=HTMLResponse)
    def direction(request: Request) -> HTMLResponse:
        snap = look()
        return page("Direction", "direction", pages.direction_index(snap), request, snap)

    @app.get("/direction/proposal", response_class=HTMLResponse)
    def proposal(request: Request, key: str = "") -> HTMLResponse:
        snap = look()
        found = find_proposal(repo, key, include_remote=include_remote_proposals)
        if found is None:
            body = (
                '<article class="card"><p>That proposal is no longer here. '
                'It may have been ratified, declined, or withdrawn. '
                '<a href="/direction#proposals">Back to Direction</a>.</p></article>'
            )
            return page("Proposal", "direction", body, request, snap)
        return page(found.title, "direction", pages.proposal_page(snap, found), request, snap)

    @app.get("/direction/{slug}", response_class=HTMLResponse)
    def document(request: Request, slug: str) -> HTMLResponse:
        snap = look()
        doc = find_document(repo, slug)
        if doc is None:
            body = (
                '<article class="card"><p>There is no document by that name in this project. '
                '<a href="/direction">Back to Direction</a>.</p></article>'
            )
            return page("Not here", "direction", body, request, snap)
        changed = what_changed(repo, doc.slug, doc.text)
        return page(doc.title, "direction", pages.direction_document(snap, doc, changed), request, snap)

    @app.get("/direction/{slug}/ask", response_class=HTMLResponse)
    def ask(request: Request, slug: str, anchor: str = "") -> HTMLResponse:
        snap = look()
        doc = find_document(repo, slug)
        if doc is None:
            return RedirectResponse("/direction", status_code=303)
        paragraph = next(
            (p.text for p in doc.paragraphs if p.anchor == anchor),
            "",
        )
        return page(
            "Ask about this", "direction", pages.ask_a_question(doc, anchor, paragraph), request, snap
        )

    @app.get("/operation", response_class=HTMLResponse)
    def operation(request: Request) -> HTMLResponse:
        snap = look()
        managers: Reading = read_managers(repo)
        body = pages.operation(
            snap, brief_reader.return_brief(snap), brief_reader.plan(snap), managers
        )
        return page("Operation", "operation", body, request, snap)

    # ------------------------------------------------- the one non-write

    @app.post("/direction/{slug}/mark-read")
    def mark_document_read(slug: str) -> RedirectResponse:
        """Not one of the four. Nothing about the project changes here."""
        doc = find_document(repo, slug)
        if doc is not None:
            mark_read(repo, doc.slug, doc.text)
        return _back(f"/direction/{slug}", "Marked as read. Changes from here will be shown against it.", True)

    # ------------------------------------------------------ the four writes

    @app.post("/do/answer-with-a-word")
    def do_answer(
        subject: str = Form(""),
        word: str = Form(""),
        note: str = Form(""),
        back: str = Form("/"),
    ) -> RedirectResponse:
        write = by_name("answer-with-a-word")
        assert write is not None
        result = write.handler(repo=repo, subject=subject, word=word, note=note)
        return _back(back, result.message, result.ok)

    @app.post("/do/signal-priority")
    def do_priority(
        item_id: str = Form(""),
        direction: str = Form(""),
        note: str = Form(""),
        back: str = Form("/operation"),
    ) -> RedirectResponse:
        write = by_name("signal-priority")
        assert write is not None
        result = write.handler(
            repo=repo, project=project, item_id=item_id, direction=direction, note=note
        )
        return _back(back, result.message, result.ok)

    @app.post("/do/drop-feedback")
    async def do_feedback(
        text: str = Form(""),
        looking_at: str = Form(""),
        picture: UploadFile | None = File(None),
        back: str = Form("/operation"),
    ) -> RedirectResponse:
        write = by_name("drop-feedback")
        assert write is not None
        payload = None
        content_type = ""
        if picture is not None and picture.filename:
            payload = await picture.read()
            content_type = picture.content_type or ""
        result = write.handler(
            repo=repo,
            text=text,
            looking_at=looking_at,
            attachment=payload,
            attachment_type=content_type,
        )
        return _back(back, result.message, result.ok)

    @app.post("/do/steer")
    def do_steer(
        objective: str | None = Form(None),
        budget: str | None = Form(None),
        lane_width: str | None = Form(None),
        ask: str = Form(""),
        about: str = Form(""),
        back: str = Form("/operation"),
    ) -> RedirectResponse:
        write = by_name("steer")
        assert write is not None
        result = write.handler(
            repo=repo,
            objective=objective,
            budget=budget,
            lane_width=lane_width,
            ask=ask,
            about=about,
        )
        return _back(back, result.message, result.ok)

    return app


def write_routes(app: FastAPI) -> set[str]:
    """Every POST path on the app that is meant to change the project."""
    out: set[str] = set()
    for route in app.routes:
        methods = getattr(route, "methods", set()) or set()
        path = getattr(route, "path", "")
        if "POST" in methods and path.startswith(WRITE_ROUTE_PREFIX):
            out.add(path)
    return out


def non_write_post_routes(app: FastAPI) -> set[str]:
    out: set[str] = set()
    for route in app.routes:
        methods = getattr(route, "methods", set()) or set()
        path = getattr(route, "path", "")
        if "POST" in methods and not path.startswith(WRITE_ROUTE_PREFIX):
            out.add(path)
    return out


def declared_write_names() -> set[str]:
    return {write.name for write in WRITES}
