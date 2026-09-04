"""Write out the pages the companion app serves, so the kit can be pointed at them.

This one is NOT a standalone script: it needs the app itself, so it runs inside
the project's environment (`uv run --extra web --with httpx …`). `run.py`, the
kit proper, stays stdlib-only and standalone — it never imports the app.

`run.py` takes either a running app (a URL) or a directory of its pages. This
writes that directory: every place, every document, every proposal, plus a
`pages.json` naming the route each file came from. Nothing here renders HTML of
its own — every byte is what `amplifier_converge.web` served.

Two things it is careful about:

* **The project is only read.** The app's last-read markers live outside the
  repository (`AMPLIFIER_CONVERGE_HOME`), and this points them at a throwaway
  directory, so rendering never moves a steward's own markers.
* **`--exercise-what-changed` works on a copy.** "What changed since you last
  read this" only has something to show once a document has been read *and*
  then changed. With that flag, this copies `docs/`, `contracts/` and
  `conformance/` to a temporary project, marks one document read through the
  app's own route, removes a sentence from the copy, and renders that document
  page again. The change is real and the page's answer to it is the app's own —
  it just happens to a copy rather than to your project.

Usage
-----
    uv run --extra web --with httpx conformance/surface/render.py \\
        --repo . --out /tmp/converge-pages --exercise-what-changed
    uv run conformance/surface/run.py /tmp/converge-pages
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlsplit

MISSING_WEB = """The web extra is not installed, so the app cannot be rendered.

    uv run --extra web --with httpx conformance/surface/render.py --repo . --out <dir>
"""

PLACES = (("/", "landing"), ("/direction", "direction"), ("/operation", "operation"))


def _slugify(route: str) -> str:
    name = re.sub(r"[^\w.-]+", "-", route.strip("/")) or "landing"
    return name[:60]


def _client(repo: Path, project: str):
    from fastapi.testclient import TestClient

    from amplifier_converge.web.app import create_app

    return TestClient(create_app(repo, project, include_remote_proposals=False))


def _links(html: str, prefix: str) -> list[str]:
    out = []
    for href in re.findall(r'href="([^"]+)"', html):
        if not href.startswith(prefix) or href.endswith("/ask") or "/ask?" in href:
            continue
        out.append(href.split("#", 1)[0])
    return list(dict.fromkeys(out))


def _write(out: Path, name: str, route: str, html: str, pages: list) -> None:
    filename = f"{name}.html"
    (out / filename).write_text(html, encoding="utf-8")
    pages.append({"route": urlsplit(route).path or "/", "file": filename})


def _non_write_post_globs() -> list[str]:
    """The app's own list of POSTs that change nothing, as globs the kit can match."""
    from amplifier_converge.web.app import NON_WRITE_POSTS

    return [re.sub(r"\{[^}]+\}", "*", route) for route in NON_WRITE_POSTS]


def _exercise_what_changed(repo: Path, project: str, out: Path, pages: list) -> str | None:
    """Render a document page that has something to show under "what changed".

    Returns a note for the manifest, or None when it could not be done.
    """
    with tempfile.TemporaryDirectory(prefix="surface-kit-copy-") as tmp:
        copy = Path(tmp) / "project"
        copy.mkdir(parents=True)
        for folder in ("docs", "contracts", "conformance"):
            source = repo / folder
            if source.is_dir():
                shutil.copytree(source, copy / folder)
        client = _client(copy, project)
        index = client.get("/direction").text
        slugs = [href.rsplit("/", 1)[-1] for href in _links(index, "/direction/")
                 if not href.startswith("/direction/proposal")]
        if not slugs:
            return None
        slug = slugs[0]
        # 1. read it, through the app's own route — the marker lands in the
        #    throwaway app home, never in the project.
        client.post(f"/direction/{slug}/mark-read", follow_redirects=False)
        # 2. change it, in the copy: take a sentence away.
        path = next((p for p in (copy / "docs").rglob(f"{slug}.md")), None)
        if path is None:
            path = next((p for p in copy.rglob(f"{slug}.md")), None)
        if path is None:
            return None
        text = path.read_text(encoding="utf-8")
        lines = text.splitlines()
        dropped = None
        for i, line in enumerate(lines):
            stripped = line.strip()
            if len(stripped) > 60 and not stripped.startswith(("#", "-", "*", "|", ">")):
                dropped = lines.pop(i)
                break
        if dropped is None:
            return None
        lines.append("")
        lines.append("A sentence added by the kit's renderer, so a reader can see an addition too.")
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        # 3. render the document page, which now has a change to state.
        html = client.get(f"/direction/{slug}").text
        _write(out, f"what-changed-{_slugify(slug)}", f"/direction/{slug}", html, pages)
        return (f"/direction/{slug} was rendered a second time against a throwaway copy of the "
                f"project in which one sentence was removed and one added after the document was "
                f"marked read, so the page has a change to state")


def render(repo: Path, project: str, out: Path, exercise: bool) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    for stale in out.glob("*.html"):
        stale.unlink()

    client = _client(repo, project)
    pages: list[dict] = []

    served: dict[str, str] = {}
    for route, name in PLACES:
        response = client.get(route)
        served[route] = response.text
        _write(out, name, route, response.text, pages)

    for href in _links(served["/direction"], "/direction/"):
        response = client.get(href)
        if response.status_code >= 400:
            continue
        kind = "proposal" if href.startswith("/direction/proposal") else "document"
        _write(out, f"{kind}-{_slugify(href[len('/direction/'):])}", href, response.text, pages)

    note = _exercise_what_changed(repo, project, out, pages) if exercise else None

    manifest = {
        "rendered_by": "conformance/surface/render.py",
        "app": "amplifier_converge.web",
        "project": str(repo.resolve()),
        "changes_nothing": _non_write_post_globs(),
        "note": note,
        "pages": pages,
    }
    (out / "pages.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="surface-render",
        description="Write out the pages the companion app serves, for conformance/surface/run.py.",
    )
    parser.add_argument("--repo", default=".", help="the project to read (default: here)")
    parser.add_argument("--out", required=True, help="the directory to write the pages into")
    parser.add_argument("--project", default=None,
                        help="the work-queue project name (default: from the folder name)")
    parser.add_argument("--exercise-what-changed", action="store_true",
                        help="also render a document page that has a change to state, by marking a "
                             "document read and then changing it IN A THROWAWAY COPY")
    args = parser.parse_args(argv)

    repo = Path(args.repo).expanduser().resolve()
    if not repo.is_dir():
        sys.stderr.write(f"There is no folder at {repo}.\n")
        return 2
    project = args.project or repo.name.replace("amplifier-bundle-", "")

    home = Path(tempfile.mkdtemp(prefix="surface-kit-home-"))
    os.environ["AMPLIFIER_CONVERGE_HOME"] = str(home)
    try:
        try:
            manifest = render(repo, project, Path(args.out).expanduser().resolve(),
                              args.exercise_what_changed)
        except ImportError:
            sys.stderr.write(MISSING_WEB)
            return 3
    finally:
        shutil.rmtree(home, ignore_errors=True)

    sys.stderr.write(f"rendered {len(manifest['pages'])} page(s) from {manifest['project']} "
                     f"into {args.out}\n")
    for page in manifest["pages"]:
        sys.stderr.write(f"  {page['route']:34} {page['file']}\n")
    if manifest["note"]:
        sys.stderr.write(f"  note: {manifest['note']}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
