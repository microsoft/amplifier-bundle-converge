"""Shared content-fingerprint / URL / static-mount helper (converge-moe4,
contract `platform-web.v1` Core 9: "renders ... with nothing cut off", read
together with Core 13's own-origin promise -- a static asset must keep
resolving to the SAME bytes an installed client already trusts).

ONE thing lives here, in one place, so no two callers can compute it two
different ways and quietly disagree:

* `compute_revision` -- a short, stable fingerprint of every file
  `app/static/` actually serves: sorted relative names AND their bytes. No
  Git, no mtimes, no build toolchain, no external service -- an installed
  wheel with no `.git` at all gets exactly the answer a source checkout
  does, and two servers whose static trees are byte-identical always agree;
  two that differ, even by one byte, never do.
* `static_url` -- the URL a template renders for one file under
  `app/static/`, always carrying the CURRENT revision.
* `VersionedStaticFiles` -- mounts `/static/<revision>/<relpath>` (current)
  AND legacy, unversioned `/static/<relpath>` from the SAME real directory,
  on Starlette's own safe path-lookup -- never a second, reimplemented
  traversal guard.
* `render_service_worker` -- the exact bytes `/sw.js` answers with for one
  server generation: `app/static/sw.js`'s own `STATIC_PREFIX` token,
  substituted for this generation's revision, so its PRECACHE list's
  entries resolve to the SAME versioned URLs the rendered HTML just asked
  for -- including on the very first install.
* `precache_entries` -- read-only, source-level: every PRECACHE URL in a
  `sw.js` source, normalized back to its LOGICAL (unversioned) form, so a
  test can compare what the app loads against what the worker precaches
  without caring whether either happens to be printed as a plain literal
  or a `${STATIC_PREFIX}` template literal.

Why the revision lives in the URL at all, rather than only in an HTTP
response header: `2fca3d8` (this lane's own base commit) already fixed
`sw.js`'s runtime-cache branch so a background refresh actually reaches
Cache Storage -- but nothing about that fix forces a PAGE to re-execute new
code. Only a fresh navigation does that, and an ordinary reload still asks
for the same URL it always has, which the browser's own HTTP cache (a layer
`sw.js` does not control) can go on answering from long after the server
moved on. A new server generation rendering a DIFFERENT `<script src>` for
the very first time is what makes the very next navigation ask for a URL
nothing -- old HTTP cache, old Cache Storage, none of it -- has ever seen.

Two app instances (routine in this project's own test suite, which spins up
several `create_app()`s in one process) must never poison each other's
rendered URLs, so nothing here is a mutable module global: `compute_revision`
is a pure function of a directory, and every caller stores what it returns
on its OWN instance (`app.state.static_revision` in `app/serve.py`, a plain
local in `app/static/dev/stub_server.py`).
"""

from __future__ import annotations

import hashlib
import os
import re
from pathlib import Path

from starlette._utils import get_route_path
from starlette.exceptions import HTTPException
from starlette.responses import Response as _Response
from starlette.staticfiles import StaticFiles
from starlette.types import Scope

#: Top-level directories under `app/static/` that are never part of what a
#: browser is served, and must never move the revision. `dev/` is the
#: front-end dev stub, its JSON fixtures, and its own request log
#: (`app/static/dev/`) -- content that changes for reasons that have
#: nothing to do with what a real client loads, and would otherwise bump
#: the revision -- forcing every real asset to look "new" -- every time
#: someone ran the stub locally.
EXCLUDED_TOP_LEVEL = frozenset({"dev"})


def _served_relative_paths(static_dir: Path) -> list[str]:
    out: list[str] = []
    for path in static_dir.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(static_dir)
        if rel.parts and rel.parts[0] in EXCLUDED_TOP_LEVEL:
            continue
        out.append(rel.as_posix())
    return out


def compute_revision(static_dir: Path) -> str:
    """A short, stable fingerprint of every file `static_dir` actually
    serves. Sorted relative names AND their bytes both move it, so a rename
    and a content edit are both caught, and two directory trees that agree
    on both compute the same revision every time -- no Git, no mtimes, no
    network, nothing but the bytes on disk right now.
    """
    hasher = hashlib.sha256()
    for rel in sorted(_served_relative_paths(static_dir)):
        hasher.update(rel.encode("utf-8"))
        hasher.update(b"\0")
        hasher.update((static_dir / rel).read_bytes())
        hasher.update(b"\0")
    return hasher.hexdigest()[:16]


def static_url(revision: str, relpath: str) -> str:
    """The URL a template renders for one file under `app/static/` --
    ALWAYS this server generation's own revision, so the very first
    navigation against it asks for a URL nothing has cached yet, old or
    new. `relpath` is relative to `app/static/`, e.g. `'js/main.js'` or
    `'vendor/xterm/css/xterm.css'`.
    """
    return f"/static/{revision}/{relpath.lstrip('/')}"


def strip_revision(path: str, revision: str) -> str:
    """The LOGICAL (unversioned) form of a `/static/...` path: `path`
    unchanged unless it carries EXACTLY this revision as its first segment
    after `/static/`. Used only by tests comparing a rendered or served URL
    against the on-disk, revision-agnostic module graph -- never by
    anything that serves a request.
    """
    prefix = f"/static/{revision}/"
    if path.startswith(prefix):
        return "/static/" + path[len(prefix):]
    return path


class VersionedStaticFiles(StaticFiles):
    """Serves `/static/<revision>/<relpath>` (current) AND legacy,
    unversioned `/static/<relpath>` from the SAME real directory -- a tab
    still open from before this instance existed, or a service worker's
    Cache Storage entry written under the old scheme, must not go dark.

    Only the path segment immediately after the mount that EXACTLY equals
    THIS instance's own `revision` is treated specially, and "treated
    specially" means exactly one thing: it is removed before the remaining
    path ever reaches `StaticFiles.get_path`'s own normalisation -- the
    identical `lookup_path` traversal guard (absolute-path rejection,
    `os.path.realpath` + `os.path.commonpath` containment) that already
    governs the legacy, unversioned form runs completely unchanged either
    way. This class never re-implements that guard and never bypasses it.

    A segment that is NOT an exact match for the current revision -- an
    unknown one, a stale one from a previous server generation, or a
    malformed one -- is never stripped. It is looked up LITERALLY as an
    ordinary path component under `static_dir`; since no such directory
    exists there, `lookup_path` simply reports "not found" through the
    normal path, precisely like any other bad request. Nothing here can
    select a file outside `static_dir`, and nothing here silently answers
    with a DIFFERENT file than the one actually asked for.
    """

    def __init__(self, *, directory: str | os.PathLike[str], revision: str, **kwargs) -> None:
        super().__init__(directory=directory, **kwargs)
        self.revision = revision

    def get_path(self, scope: Scope) -> str:
        route_path = get_route_path(scope)
        parts = route_path.split("/")
        # parts[0] is '' (route_path always starts with '/'); a match needs
        # a real revision segment AND at least one segment after it -- a
        # bare "/<revision>" with nothing following is left untouched, the
        # same as anything else that isn't a genuine versioned reference.
        if len(parts) >= 3 and parts[1] == self.revision:
            route_path = "/" + "/".join(parts[2:])
        return os.path.normpath(os.path.join(*route_path.split("/")))

    async def get_response(self, path: str, scope: Scope) -> _Response:
        """The one gate every request -- legacy `/static/<relpath>` AND
        versioned `/static/<revision>/<relpath>` alike, since both funnel
        through here after `get_path` above has already stripped a matching
        revision segment -- passes through before a byte of `static_dir`
        is ever touched.

        `compute_revision` already excludes `EXCLUDED_TOP_LEVEL` (`dev/`)
        from what it fingerprints, on the theory that a browser never loads
        it -- but excluding a directory from the FINGERPRINT never made it
        stop being SERVED: `directory=static_dir` here is the same real
        `app/static/`, `dev/` and all, and `StaticFiles.lookup_path` will
        happily answer for anything under it that exists on disk, including
        `app/static/dev/stub_server.py` (this project's own front-end dev
        stub, source and all) and `app/static/dev/requests.log` (every POST
        that stub has ever logged). Production (`app/serve.py`) mounts this
        very class over the very same directory a running dev stub writes
        into, so without this check either one 404s a browser's real asset
        request or leaks the other's private files -- there is no third
        option that serves `app/static/` at all and reaches only what a
        browser is meant to load.

        A 404 here (`raise HTTPException`, exactly what `StaticFiles` itself
        raises for an ordinary miss -- never a distinguishable status or
        body) is indistinguishable from `dev/` never having existed, which
        is the whole point: this is a NEW gate in front of the same safe,
        unmodified `lookup_path` traversal guard every other path already
        goes through, never a second reimplementation of it and never a
        different answer for a request that would otherwise 404 anyway.
        """
        first = path.split(os.sep, 1)[0] if path else ""
        if first in EXCLUDED_TOP_LEVEL:
            raise HTTPException(status_code=404)
        return await super().get_response(path, scope)


#: The exact token `app/static/sw.js` defines for its own unversioned
#: default. Matched literally rather than assumed, so a rename of the
#: constant fails loud (`render_service_worker` raises) instead of quietly
#: shipping a worker whose PRECACHE list still points at last generation's
#: URLs.
_STATIC_PREFIX_TOKEN = "const STATIC_PREFIX = '/static';"


def render_service_worker(sw_source: str, revision: str) -> str:
    """The exact bytes `/sw.js` answers with for THIS server generation:
    `sw_source` (whatever this app instance's `app/static/sw.js` reads),
    with its one `STATIC_PREFIX` token substituted so the `${STATIC_PREFIX}`
    template-literal PRECACHE entries it builds from that constant resolve
    to THIS generation's versioned URLs -- the same ones the rendered HTML
    just asked for, on the very first install. Everything else in the file
    is untouched, byte-for-byte: this is one exact literal substitution,
    never a template engine and never a second copy of the source to keep
    in sync.
    """
    if _STATIC_PREFIX_TOKEN not in sw_source:
        raise RuntimeError(
            "app/static/sw.js no longer defines the exact STATIC_PREFIX token "
            f"app/assets.py substitutes ({_STATIC_PREFIX_TOKEN!r}) -- the two have drifted"
        )
    replacement = f"const STATIC_PREFIX = '/static/{revision}';"
    return sw_source.replace(_STATIC_PREFIX_TOKEN, replacement, 1)


#: Matches either a plain single-quoted PRECACHE literal (`'/manifest...'`)
#: or a `${STATIC_PREFIX}`-prefixed template literal (`` `${STATIC_PREFIX}/js/main.js` ``).
_PRECACHE_ENTRY_RE = re.compile(r"`\$\{STATIC_PREFIX\}([^`]*)`|'([^']*)'")


def precache_entries(sw_source: str) -> list[str]:
    """Every PRECACHE URL in `sw_source`, in its LOGICAL (unversioned)
    form -- a `` `${STATIC_PREFIX}/js/main.js` `` template-literal entry and
    a plain `'/manifest.webmanifest'` literal both come back as the URL an
    unversioned request would use. Source-only: reads text, renders and
    serves nothing, and never needs a running app.
    """
    block = re.search(r"const PRECACHE = \[(.*?)\];", sw_source, re.S)
    if not block:
        raise ValueError("no `const PRECACHE = [...]` array found in this source")
    entries: list[str] = []
    for template_tail, literal in _PRECACHE_ENTRY_RE.findall(block.group(1)):
        if template_tail:
            entries.append("/static" + template_tail)
        else:
            entries.append(literal)
    return entries
