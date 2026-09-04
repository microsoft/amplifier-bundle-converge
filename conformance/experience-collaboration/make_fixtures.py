#!/usr/bin/env python3
"""Write the two fixtures the experience-collaboration.v1 kit is proved against.

    uv run conformance/experience-collaboration/make_fixtures.py

A fixture here is a **pair**, the same shape the umbrella kit's fixtures take: a
captured app snapshot (a `manifest.json` naming the route each file came from,
plus the files) and a `repo/` half carrying the write path, the ratification
record and the proposals this contract is about. Both halves are written here so
neither can drift from the other.

`sample-good` keeps every promise the kit asserts; `sample-bad` breaks every one
of them at once, so a single run surfaces all of them.
"""

from __future__ import annotations

import json
import pathlib
import shutil

KIT = pathlib.Path(__file__).resolve().parent
MANAGER = "m1"


def write(name: str, note: str, routes: dict, repo: dict) -> pathlib.Path:
    out = KIT / "fixtures" / name
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    entries = []
    for route, (filename, body) in routes.items():
        (out / filename).write_text(body, encoding="utf-8")
        kind = ("js" if filename.endswith(".js") else
                "css" if filename.endswith(".css") else
                "openapi" if route == "/openapi.json" else
                "json" if filename.endswith(".json") else "html")
        entries.append({"route": route, "file": filename, "kind": kind})
    (out / "manifest.json").write_text(json.dumps(
        {"base": str(out), "captured": "fixture", "manager": MANAGER,
         "note": note, "routes": entries}, indent=2) + "\n", encoding="utf-8")
    for rel, body in repo.items():
        target = out / "repo" / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding="utf-8")
    return out


def api(routes: dict) -> str:
    return json.dumps({"openapi": "3.1.0", "paths": {
        p: {m.lower(): {"summary": p} for m in ms} for p, ms in routes.items()}}, indent=1)


# --------------------------------------------------------------------------- #
# the app's own route table                                                    #
# --------------------------------------------------------------------------- #
GOOD_ROUTES = {
    "/": ["GET"],
    "/api/boot": ["GET"],
    "/api/managers/{mid}": ["GET"],
    "/api/managers/{mid}/decision": ["POST"],
    # the two-way bridge to the host's own pull-request comments
    "/api/managers/{mid}/pulls/{number}/comments": ["GET", "POST"],
    # inbound, without the steward asking
    "/webhooks/host": ["POST"],
    "/login": ["GET", "POST"],
}

BAD_ROUTES = {
    "/": ["GET"],
    "/api/boot": ["GET"],
    "/api/managers/{mid}": ["GET"],
    "/api/managers/{mid}/decision": ["POST"],
    # one manager session reaching another, and a tracker of Converge's own
    "/api/managers/{mid}/peers/{other}": ["POST"],
    "/api/issues": ["GET", "POST"],
    "/login": ["GET", "POST"],
}


# --------------------------------------------------------------------------- #
# the payloads                                                                 #
# --------------------------------------------------------------------------- #
GOOD_BOOT = {
    "user": "a-reader",
    "managers": [{"id": MANAGER, "name": "Example", "status": "working",
                  "statusLabel": "Working", "steward": "a-steward", "needs": 1}],
}

BAD_BOOT = {
    "user": "a-reader",
    "managers": [{"id": MANAGER, "name": "Example", "status": "working",
                  "statusLabel": "Working", "needs": 1}],
}

GOOD_MANAGER = {
    "id": MANAGER, "name": "Example", "steward": "a-steward",
    "repositories": [{"id": "r1", "name": "Repo one", "path": "/tmp/r1", "docs": []}],
}

BAD_MANAGER = {
    "id": MANAGER, "name": "Example",
    "repositories": [{"id": "r1", "name": "Repo one", "path": "/tmp/r1", "docs": []}],
}


# --------------------------------------------------------------------------- #
# the shells                                                                   #
# --------------------------------------------------------------------------- #
GOOD_SHELL = """<!doctype html><html><head><title>Converge</title></head><body>
<div id="app" class="app-shell">
<header class="topbar">
  <div id="workspaceSwitch" class="workspace-switch" role="tablist">
    <button class="workspace-tab active" id="directionTab" role="tab" type="button">Direction</button>
    <button class="workspace-tab" id="operationTab" role="tab" type="button">Operation</button>
  </div>
  <p class="freshness muted">Changes from the host arrive on their own. Where the host
  offers no webhook, this is checked every 2 minutes and the last check is shown here.</p>
</header>
<div class="body-grid"><main class="workspace">
  <section id="directionView" class="view direction-view" aria-label="Direction">
    <div id="reviewPane"></div>
    <form id="hostCommentForm"><textarea id="hostCommentText"></textarea>
      <button type="submit">Ask on the pull request</button></form>
  </section>
</main></div></div>
<script src="/static/js/main.js"></script></body></html>
"""

BAD_SHELL = """<!doctype html><html><head><title>Converge</title></head><body>
<div id="app" class="app-shell">
<header class="topbar">
  <div id="workspaceSwitch" class="workspace-switch" role="tablist">
    <button class="workspace-tab active" id="directionTab" role="tab" type="button">Direction</button>
  </div>
</header>
<div class="body-grid"><main class="workspace">
  <section id="directionView" class="view direction-view" aria-label="Direction">
    <div id="reviewPane"></div>
    <button id="reloadButton" type="button">Reload to see what changed</button>
  </section>
</main></div></div>
<script src="/static/js/main.js"></script></body></html>
"""


# --------------------------------------------------------------------------- #
# the client                                                                   #
# --------------------------------------------------------------------------- #
GOOD_DIRECTION_JS = """// One review, whoever proposed it.
import { escapeHtml } from '../state.js';
import { api } from '../api.js';

function renderReview(proposal) {
  return `<article class="review">
      <span class="eyebrow">Proposal ${escapeHtml(proposal.id)} · ${escapeHtml(proposal.source)}</span>
      <section><h3>What changes</h3>${sentences(proposal)}</section>
      <section><h3>The evidence</h3>${evidence(proposal)}</section>
      <section><h3>What does not change</h3><p>${escapeHtml(proposal.unchanged)}</p></section>
    </article>`;
}

export function askOnTheHost(proposal, question) {
  return api.postComment(proposal.pullNumber, question);
}

export function answer(proposal, word) {
  return api.decision(proposal.id, word).then(() => api.postBackToOrigin(proposal, word));
}
"""

BAD_DIRECTION_JS = """// A review per origin, and nothing leaves this machine.
import { escapeHtml } from '../state.js';

function renderReview(proposal) {
  if (proposal.origin === 'a teammate') { return renderTeammateReview(proposal); }
  return `<article class="review"><h3>${escapeHtml(proposal.title)}</h3></article>`;
}

function renderReviewFromHost(proposal) {
  return `<article class="review host"><h3>${escapeHtml(proposal.title)}</h3></article>`;
}

export function answer(proposal, word) {
  return api.decision(proposal.id, word);
}
"""

MAIN_JS = "import './render/direction.js';\n"


# --------------------------------------------------------------------------- #
# the repository half                                                          #
# --------------------------------------------------------------------------- #
GOOD_WRITES_PY = '''"""The things a steward can actually do, written where they belong."""

import subprocess


def _git(repo, *args):
    return subprocess.run(["git", *args], cwd=str(repo), capture_output=True, text=True)


def record_decision(repo, *, word, proposal_id, day):
    """Append the steward word to today ratification record, and commit it."""
    path = repo / "docs" / "workflow" / f"owner-ratifications-{day}.md"
    path.write_text(entry(word, proposal_id))
    _git(repo, "add", str(path))
    _git(repo, "commit", "-m", f"ratification: {proposal_id}")
    return path


def candidate_path(path):
    """The proposal beside the document it proposes against."""
    return path.with_name(f"{path.stem}.v2-candidate.md")


def post_back_to_origin(repo, *, proposal, word):
    """Send the steward own word to the origin, as a comment on the host."""
    return _git(repo, "push", "origin", "HEAD")
'''

BAD_WRITES_PY = '''"""Everything a steward does, relayed through the session that is watching."""

import subprocess


def record_decision(repo, *, word, proposal_id, day):
    """Tell the manager session; it will work out what to do."""
    subprocess.run(["tmux", "send-keys", "-t", "manager", f"decision {word}", "Enter"])


PEER_ENDPOINT = "the other manager session"


def tell_the_other_manager(word):
    peer_channel(PEER_ENDPOINT).send(word)
'''

RATIFICATIONS = """# Owner ratifications — 2026-09-03

Each entry below is the steward's own word on one proposal, recorded when it was
given.

## 2026-09-03T10:00:00+01:00 — Ratified: experience (P4)

- **Proposal:** `P4`
"""

CANDIDATE = """# Experience Contract — v2 candidate (proposal)

## The exact change

One sentence, replaced.

## The evidence

A cost actually paid.

## What does not change

Every other clause.
"""


def good_repo() -> dict:
    return {
        "app/writes.py": GOOD_WRITES_PY,
        "docs/workflow/owner-ratifications-2026-09-03.md": RATIFICATIONS,
        "contracts/experience.v2-candidate.md": CANDIDATE,
    }


def bad_repo() -> dict:
    return {"app/writes.py": BAD_WRITES_PY}


# --------------------------------------------------------------------------- #
# the two fixtures                                                             #
# --------------------------------------------------------------------------- #
def routes_for(shell, boot, manager, direction_js, table):
    return {
        "/": ("index.html", shell),
        "/openapi.json": ("openapi.json", api(table)),
        "/api/boot": ("api__boot.json", json.dumps(boot, indent=1)),
        f"/api/managers/{MANAGER}": ("api__managers__m1.json", json.dumps(manager, indent=1)),
        "/static/js/main.js": ("static__js__main.js", MAIN_JS),
        "/static/js/render/direction.js": ("static__js__render__direction.js", direction_js),
    }


def main() -> int:
    good = write(
        "sample-good",
        "a body that keeps the seam: git as the protocol, one review whoever proposed, "
        "a two-way bridge to the host, an answer that lands in the record and returns "
        "to its origin, freshness that is not the steward's job, and one steward",
        routes_for(GOOD_SHELL, GOOD_BOOT, GOOD_MANAGER, GOOD_DIRECTION_JS, GOOD_ROUTES),
        good_repo())
    bad = write(
        "sample-bad",
        "the seam broken every way at once: a channel between manager sessions, a review "
        "per origin, no bridge to the host, an answer that goes nowhere, freshness left to "
        "the steward, writes relayed through a terminal session, no steward, and a tracker "
        "of Converge's own",
        routes_for(BAD_SHELL, BAD_BOOT, BAD_MANAGER, BAD_DIRECTION_JS, BAD_ROUTES),
        bad_repo())
    for path in (good, bad):
        print(f"wrote {path.relative_to(KIT.parent.parent)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
