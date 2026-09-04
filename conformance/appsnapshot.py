"""One target model for the three experience kits: **what the app served**.

`experience-direction`, `experience-operation` and `experience-console` all
judge the same body — the companion app in `app/` — so they share one reader
rather than three that drift apart. Each kit is still its own runnable script
and its own rule table; only *how a target is read* lives here.

Why this is not the surface kit's page-set reader
-------------------------------------------------
`conformance/_superseded/surface/` fetched a set of server-rendered HTML pages
and judged their markup. The app that shipped is not that shape: `/` serves one
shell, and everything a steward reads arrives as JSON from `/api/…` and is
rendered by the scripts under `/static/js/`. A reader that only looked at `/`
would see an empty shell and report a body with no content — the same
false-FAIL that made converge-e59 necessary.

So a snapshot of this app is four kinds of thing, and every rule says which
kind it read:

===========  =========================================================
`html`       the served shell — the DOM every view is rendered into
`json`       the API payloads — the real project data, no fixtures
`js` / `css` the client the app serves — what it does with that data
`openapi`    the app's own route table, from `/openapi.json`
===========  =========================================================

`openapi` matters more than it looks: it is the app's **own** machine-readable
statement of every route it answers, so "which writes exist" is settled from
the app rather than guessed from markup.

No browser is launched. A promise that genuinely needs a rendered viewport
(a layout at two widths, a live console round trip) is reported SKIP with its
reason — never a fabricated PASS.

Reading a live app
------------------
Every route except `/login`, `/static`, `/branding` and `/healthz` is behind the
app's cookie gate, and **there is no loopback exemption** (`app/auth.py`). So a
live target needs a signed cookie:

    export CONVERGE_APP_COOKIE="$(python3 - <<'PY'
    import pathlib
    from itsdangerous import URLSafeTimedSerializer
    secret = (pathlib.Path.home()/".amplifier"/"converge-app.secret").read_text().strip()
    print(URLSafeTimedSerializer(secret, salt="converge-app-session").dumps({"u": "<you>"}))
    PY
    )"
    uv run conformance/experience-direction/run.py http://127.0.0.1:8788

which is the same signer the app itself uses. Without one the kit fails loudly
with that instruction rather than reporting an empty app.

Reading a captured snapshot
---------------------------
`--capture <dir>` writes every route it read to a directory with a
`manifest.json` naming the route each file came from. That directory is then a
target in its own right, which is what the good/bad fixtures are.
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import quote, urlsplit

__all__ = [
    "AppSnapshot",
    "Node",
    "TargetError",
    "parse_html",
    "resolve_target",
]


class TargetError(RuntimeError):
    """The target could not be read at all — never reported as a rule FAIL."""


# --------------------------------------------------------------------------- #
# a small HTML tree — stdlib only                                              #
# (structure carried over from the superseded surface kit, which proved it)    #
# --------------------------------------------------------------------------- #
VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input",
             "link", "meta", "param", "source", "track", "wbr"}


class Node:
    __slots__ = ("tag", "attrs", "classes", "id", "parent", "children", "own_text")

    def __init__(self, tag="", attrs=None, parent=None):
        self.tag = tag
        self.attrs = attrs or {}
        self.classes = self.attrs.get("class", "").split()
        self.id = self.attrs.get("id", "")
        self.parent = parent
        self.children = []
        self.own_text = []

    def walk(self):
        for child in self.children:
            yield child
            yield from child.walk()

    def find(self, tag=None, cls=None, node_id=None, attr=None):
        out = []
        for node in self.walk():
            if tag and node.tag != tag:
                continue
            if cls and cls not in node.classes:
                continue
            if node_id and node.id != node_id:
                continue
            if attr and attr not in node.attrs:
                continue
            out.append(node)
        return out

    def first(self, **kw):
        found = self.find(**kw)
        return found[0] if found else None

    def ancestors(self):
        node = self.parent
        while node is not None:
            yield node
            node = node.parent

    def inside(self, tag=None, cls=None, node_id=None):
        for node in self.ancestors():
            if tag and node.tag == tag:
                return True
            if cls and cls in node.classes:
                return True
            if node_id and node.id == node_id:
                return True
        return False

    def text(self):
        parts = list(self.own_text)
        for child in self.children:
            if child.tag in ("script", "style"):
                continue
            parts.append(child.text())
        return re.sub(r"\s+", " ", "".join(parts)).strip()

    def describe(self):
        bits = [self.tag]
        if self.id:
            bits.append(f"#{self.id}")
        if self.classes:
            bits.append("." + ".".join(self.classes[:3]))
        return "".join(bits)


class _TreeParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node("#document")
        self._cur = self.root

    def handle_starttag(self, tag, attrs):
        a = {k: (v if v is not None else "") for k, v in attrs}
        node = Node(tag, a, self._cur)
        self._cur.children.append(node)
        if tag not in VOID_TAGS:
            self._cur = node

    def handle_startendtag(self, tag, attrs):
        a = {k: (v if v is not None else "") for k, v in attrs}
        self._cur.children.append(Node(tag, a, self._cur))

    def handle_endtag(self, tag):
        node = self._cur
        while node is not None and node.tag != tag:
            node = node.parent
        if node is not None and node.parent is not None:
            self._cur = node.parent

    def handle_data(self, data):
        self._cur.own_text.append(data)


def parse_html(text: str) -> Node:
    parser = _TreeParser()
    parser.feed(text or "")
    parser.close()
    return parser.root


# --------------------------------------------------------------------------- #
# the snapshot                                                                 #
# --------------------------------------------------------------------------- #
COOKIE_ENV = "CONVERGE_APP_COOKIE"

COOKIE_HELP = (
    "the app gates every route behind its signed cookie and has NO loopback "
    "exemption (app/auth.py), so a live target needs one. Mint it with the app's "
    "own signer and pass --cookie, or set $" + COOKIE_ENV + ":\n"
    "    python3 -c \"import pathlib;from itsdangerous import URLSafeTimedSerializer as S;"
    "print(S(pathlib.Path.home().joinpath('.amplifier','converge-app.secret')"
    ".read_text().strip(), salt='converge-app-session').dumps({'u':'<you>'}))\""
)

#: Client assets worth reading. The app serves more; these are the ones that
#: carry behaviour a rule reads.
CLIENT_ASSETS = (
    "/static/js/main.js",
    "/static/js/api.js",
    "/static/js/state.js",
    "/static/js/actions.js",
    "/static/js/refresh.js",
    "/static/js/render/top.js",
    "/static/js/render/home.js",
    "/static/js/render/direction.js",
    "/static/js/render/operation.js",
    "/static/js/render/console.js",
    "/static/js/tmux.js",
    "/static/css/shell.css",
    "/static/css/console.css",
    "/static/css/direction.css",
    "/static/css/operation.css",
)

#: How many document payloads to pull. A repo with 15 documents is normal; a
#: cap keeps a live run quick and is reported in the snapshot so a reader knows
#: the set was bounded rather than empty.
DOC_LIMIT = 12


def _kind_of(route: str) -> str:
    if route.endswith(".js"):
        return "js"
    if route.endswith(".css"):
        return "css"
    if route == "/openapi.json":
        return "openapi"
    if route.startswith("/api/") or route.endswith(".json"):
        return "json"
    return "html"


def _safe_name(route: str) -> str:
    name = route.strip("/").replace("/", "__") or "index"
    name = re.sub(r"[^A-Za-z0-9_.-]", "-", name)
    kind = _kind_of(route)
    if kind in ("json", "openapi") and not name.endswith(".json"):
        name += ".json"
    if kind == "html" and not name.endswith(".html"):
        name += ".html"
    return name


class AppSnapshot:
    """Everything one target served, addressed by route."""

    def __init__(self, base: str, kind: str, bodies: dict, order=None, notes=None):
        self.base = base
        self.kind = kind                       # "live" | "snapshot"
        self.bodies = dict(bodies)
        self.order = list(order or bodies.keys())
        self.notes = dict(notes or {})
        self._html_cache = {}

    # -- addressing ------------------------------------------------------
    def has(self, route: str) -> bool:
        return route in self.bodies

    def text(self, route: str) -> str:
        return self.bodies.get(route, "")

    def json(self, route: str):
        raw = self.bodies.get(route)
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return None

    def html(self, route: str = "/") -> Node:
        if route not in self._html_cache:
            self._html_cache[route] = parse_html(self.bodies.get(route, ""))
        return self._html_cache[route]

    def routes_of_kind(self, kind: str):
        return [r for r in self.order if _kind_of(r) == kind]

    def script_text(self) -> str:
        return "\n".join(self.bodies.get(r, "") for r in self.routes_of_kind("js"))

    def style_text(self) -> str:
        return "\n".join(self.bodies.get(r, "") for r in self.routes_of_kind("css"))

    def script_named(self, tail: str) -> str:
        for r in self.routes_of_kind("js"):
            if r.endswith(tail):
                return self.bodies.get(r, "")
        return ""

    # -- the app's own route table --------------------------------------
    def api_routes(self) -> dict:
        """{path: [METHOD, …]} from the app's own /openapi.json, or {}."""
        doc = self.json("/openapi.json") or {}
        paths = doc.get("paths") or {}
        return {p: sorted(m.upper() for m in ops) for p, ops in paths.items()}

    def write_routes(self) -> list:
        """Every POST route the app answers, its own words for 'a write'."""
        return sorted(p for p, m in self.api_routes().items() if "POST" in m)

    # -- convenience over the payloads ----------------------------------
    def manager_id(self):
        return self.notes.get("manager")

    def manager(self):
        mid = self.manager_id()
        return self.json(f"/api/managers/{mid}") if mid else None

    def operation(self):
        mid = self.manager_id()
        return self.json(f"/api/managers/{mid}/operation") if mid else None

    def needs(self):
        mid = self.manager_id()
        return self.json(f"/api/needs/{mid}") if mid else None

    def boot(self):
        return self.json("/api/boot")

    def doc_routes(self):
        return [r for r in self.order if "/docs/" in r]

    def documents(self):
        return [(r, self.json(r)) for r in self.doc_routes() if self.json(r)]

    # -- writing it out --------------------------------------------------
    def capture(self, out_dir) -> Path:
        out = Path(out_dir)
        out.mkdir(parents=True, exist_ok=True)
        entries = []
        for route in self.order:
            name = _safe_name(route)
            (out / name).write_text(self.bodies.get(route, ""), encoding="utf-8")
            entries.append({"route": route, "file": name, "kind": _kind_of(route)})
        manifest = {
            "base": self.base,
            "captured": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "manager": self.notes.get("manager"),
            "note": self.notes.get("note", ""),
            "routes": entries,
        }
        (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n",
                                           encoding="utf-8")
        return out


# --------------------------------------------------------------------------- #
# loading                                                                      #
# --------------------------------------------------------------------------- #
def _fetch(base: str, route: str, cookie: str, timeout: float = 20.0):
    url = base.rstrip("/") + route
    req = urllib.request.Request(url, headers={
        "Cookie": f"cv_session={cookie}" if cookie else "",
        "Accept": "*/*",
        "User-Agent": "converge-conformance/1",
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as res:
            body = res.read().decode("utf-8", "replace")
            return res.status, str(res.url), body
    except urllib.error.HTTPError as exc:
        return exc.code, url, exc.read().decode("utf-8", "replace")
    except urllib.error.URLError as exc:
        raise TargetError(f"cannot reach {url}: {exc.reason}") from exc


def from_url(base: str, cookie: str = "", doc_limit: int = DOC_LIMIT) -> AppSnapshot:
    cookie = cookie or os.environ.get(COOKIE_ENV, "")
    bodies, order = {}, []

    def take(route, body):
        bodies[route] = body
        order.append(route)

    status, final, body = _fetch(base, "/", cookie)
    if status in (401, 403) or "/login" in urlsplit(final).path:
        raise TargetError(
            f"{base} answered the sign-in gate for `/` — {COOKIE_HELP}"
        )
    if status != 200:
        raise TargetError(f"{base}/ answered {status}, not 200")
    take("/", body)

    for route in ("/openapi.json", "/api/boot"):
        status, _, body = _fetch(base, route, cookie)
        if status == 200:
            take(route, body)

    boot = json.loads(bodies["/api/boot"]) if "/api/boot" in bodies else {}
    managers = boot.get("managers") or []
    if not managers:
        raise TargetError(
            f"{base} lists no manager session, so there is nothing to judge. "
            "Point the kit at an app whose ~/.amplifier/converge-app.toml names one."
        )
    mid = managers[0]["id"]

    for route in (f"/api/managers/{quote(mid)}",
                  f"/api/managers/{quote(mid)}/operation",
                  f"/api/needs/{quote(mid)}"):
        status, _, body = _fetch(base, route, cookie)
        if status == 200:
            take(route, body)

    manager = json.loads(bodies.get(f"/api/managers/{quote(mid)}", "{}"))
    pulled = 0
    for repo in manager.get("repositories") or []:
        for doc in repo.get("docs") or []:
            if pulled >= doc_limit:
                break
            route = (f"/api/managers/{quote(mid)}/docs/"
                     f"{quote(str(repo['id']))}/{quote(str(doc['id']))}")
            status, _, body = _fetch(base, route, cookie)
            if status == 200:
                take(route, body)
                pulled += 1

    for asset in CLIENT_ASSETS:
        status, _, body = _fetch(base, asset, cookie)
        if status == 200:
            take(asset, body)

    return AppSnapshot(base, "live", bodies, order, {
        "manager": mid,
        "doc_limit": doc_limit,
        "documents_read": pulled,
    })


def from_dir(path) -> AppSnapshot:
    root = Path(path)
    manifest_path = root / "manifest.json"
    if not manifest_path.is_file():
        raise TargetError(
            f"{root} carries no manifest.json, so no file can be traced to the route "
            "it came from. Write one with `run.py <live app> --capture <dir>`."
        )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    bodies, order = {}, []
    for entry in manifest.get("routes") or []:
        f = root / entry["file"]
        if not f.is_file():
            raise TargetError(f"{manifest_path} names {entry['file']}, which is missing")
        bodies[entry["route"]] = f.read_text(encoding="utf-8")
        order.append(entry["route"])
    return AppSnapshot(str(root), "snapshot", bodies, order, {
        "manager": manifest.get("manager"),
        "note": manifest.get("note", ""),
        "captured": manifest.get("captured", ""),
    })


def resolve_target(target: str, cookie: str = "") -> AppSnapshot:
    """A URL of the running app, or a directory written by --capture."""
    if str(target).startswith(("http://", "https://")):
        return from_url(str(target), cookie)
    path = Path(target)
    if path.is_dir():
        return from_dir(path)
    raise TargetError(
        f"{target} is neither a URL of the running app nor a captured snapshot "
        "directory. Point the kit at http://127.0.0.1:8788 or at a --capture dir."
    )
