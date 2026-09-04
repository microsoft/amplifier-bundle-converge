#!/usr/bin/env python3
"""Write the two fixtures the experience.v1 kit is proved against.

    uv run conformance/experience/make_fixtures.py

A fixture here is a **pair**, because the umbrella makes two kinds of promise:

* a captured app snapshot — a `manifest.json` naming the route each file came
  from, plus the files, exactly the shape `run.py --capture` writes;
* a `repo/` half — the contracts, the ratification record and the app source
  the umbrella's own clauses are about.

`conformance/experience-fixtures/make_fixtures.py` writes the six fixtures of
the three section kits and knows nothing about a repository half, so this kit's
maker lives beside the kit instead: both halves of one fixture are written by
one file, and neither can drift from the other.

`sample-good` keeps every promise the kit asserts; `sample-bad` breaks every one
of them at once, so a single run surfaces all of them. Both are committed, and
this script rewrites them in place — it is how they are kept in step when a rule
is added, not a build step anyone has to run first.
"""

from __future__ import annotations

import json
import pathlib
import shutil

KIT = pathlib.Path(__file__).resolve().parent
MANAGER = "m1"


# --------------------------------------------------------------------------- #
# writing                                                                      #
# --------------------------------------------------------------------------- #
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
    "/api/managers/{mid}/operation": ["GET"],
    "/api/managers/{mid}/docs/{repo}/{doc}": ["GET"],
    "/api/needs/{mid}": ["GET"],
    # the five writes, and only the five
    "/api/managers/{mid}/decision": ["POST"],
    "/api/managers/{mid}/priority": ["POST"],
    "/api/managers/{mid}/feedback": ["POST"],
    "/api/managers/{mid}/steer": ["POST"],
    "/api/managers/{mid}/ask": ["POST"],
    # exempt: the sign-in gate, and the console's message path
    "/login": ["GET", "POST"],
    "/logout": ["POST"],
    "/api/tmux/{socket}/{session}": ["GET"],
    "/api/tmux/{socket}/{session}/keys": ["POST"],
}

BAD_ROUTES = {
    "/": ["GET"],
    "/api/boot": ["GET"],
    "/api/managers/{mid}": ["GET"],
    "/api/managers/{mid}/operation": ["GET"],
    "/api/managers/{mid}/docs/{repo}/{doc}": ["GET"],
    "/api/needs/{mid}": ["GET"],
    # two of the five are missing, and one write no contract names is added
    "/api/managers/{mid}/decision": ["POST"],
    "/api/managers/{mid}/feedback": ["POST"],
    "/api/managers/{mid}/steer": ["POST"],
    "/api/managers/{mid}/publish": ["POST"],
    "/login": ["GET", "POST"],
}


# --------------------------------------------------------------------------- #
# the payloads                                                                 #
# --------------------------------------------------------------------------- #
GOOD_BOOT = {
    "user": "a-steward",
    "managers": [{
        "id": MANAGER, "name": "Example", "status": "working", "statusLabel": "Working",
        "summary": "Two lanes landed; one is waiting on your word.",
        "needs": 2, "lanesActive": 3, "lanesMax": 4, "repos": 1, "projects": 1,
    }],
}

BAD_BOOT = {
    "user": "a-steward",
    "managers": [{
        "id": MANAGER, "name": "Example", "status": "running", "statusLabel": "RUNNING",
        "summary": "", "needs": 7, "lanesActive": 3, "lanesMax": 4,
        "repos": 1, "projects": 1,
    }],
}

GOOD_MANAGER = {
    "id": MANAGER, "name": "Example", "status": "working", "statusLabel": "Working",
    "summary": "Two lanes landed; one is waiting on your word.",
    "repositories": [{"id": "r1", "name": "Repo one", "path": "/tmp/r1", "docs": [
        {"id": "vision", "title": "Vision", "state": "draft", "standing": "Not yet",
         "path": "docs/VISION.md"},
        {"id": "experience", "title": "Experience", "state": "draft", "standing": "Kept",
         "path": "contracts/experience.v1.md"}]}],
}

BAD_MANAGER = {
    "id": MANAGER, "name": "Example", "status": "running", "statusLabel": "RUNNING",
    "summary": "",
    "repositories": [{"id": "r1", "name": "Repo one", "path": "/tmp/r1", "docs": [
        {"id": "vision", "title": "Vision", "state": "draft", "standing": "RESOLVED",
         "path": "docs/VISION.md"}]}],
}

GOOD_OPERATION = {
    "waves": [{"id": "w1", "label": "Wave 1", "title": "Prove the umbrella is checkable",
               "phase": "Working", "cls": "run", "progress": 40, "items": []},
              {"id": "w2", "label": "Wave 2", "title": "Place every behavior",
               "phase": "Done", "cls": "done", "progress": 100, "items": []}],
    "lanes": [{"id": "w1-kit", "status": "working", "statusLabel": "Working",
               "wave": "Wave 1", "title": "build the kit", "worker": "w1-kit",
               "age": "20m", "evidence": "3 commits"}],
    "timeline": [], "returnBrief": ["You were away 20m."],
}

BAD_OPERATION = {
    "waves": [{"id": "w1", "label": "Wave 1", "title": "", "phase": "DONE",
               "cls": "done", "progress": 100, "items": []}],
    "lanes": [{"id": "w1-kit", "status": "running", "statusLabel": "RUNNING",
               "wave": "", "title": "build the kit", "worker": "w1-kit",
               "age": "20m", "evidence": ""}],
    "timeline": [], "returnBrief": [],
}

GOOD_NEEDS = [{"kind": "proposal", "title": f"Proposal {n}",
               "where": {"repoId": "r1", "docId": "vision"},
               "since": "2026-09-04T09:00:00+00:00"} for n in range(1, 4)]

#: Seven things asking for a word at once — the clause fixes the limit at five.
BAD_NEEDS = [{"kind": "proposal", "title": f"Proposal {n}",
              "where": {"repoId": "r1", "docId": "vision"},
              "since": "2026-09-04T09:00:00+00:00"} for n in range(1, 8)]

GOOD_DOC = {
    "path": "docs/VISION.md", "title": "Vision", "state": "draft", "standing": "Not yet",
    "sections": [["Where this is going", "<p>One experience, many bodies.</p>"]],
    "raw": "# Vision\n\nOne experience, many bodies.\n",
    "changes": [], "proposals": [], "history": [],
}


# --------------------------------------------------------------------------- #
# the shells                                                                   #
# --------------------------------------------------------------------------- #
GOOD_SHELL = """<!doctype html><html><head><title>Converge</title>
<link rel="stylesheet" href="/static/css/shell.css"></head><body>
<div id="app" class="app-shell">
<header class="topbar">
  <div id="workspaceSwitch" class="workspace-switch" role="tablist" aria-label="Workspace view">
    <button class="workspace-tab active" id="directionTab" role="tab" type="button">Direction</button>
    <button class="workspace-tab" id="operationTab" role="tab" type="button">Operation</button>
  </div>
  <button id="needsYouButton" type="button"><strong id="needsYouCount">3</strong> need your word</button>
  <button id="consoleToggle" type="button">Manager Console</button>
</header>
<div class="body-grid"><main class="workspace">
  <section id="homeView" class="view home-view hidden" aria-label="All manager sessions">
    <strong id="homeAttentionTotal">3</strong><div id="homeSessionGrid"></div>
  </section>
  <section id="directionView" class="view direction-view" aria-label="Direction">
    <div class="review-actions">
      <button data-decision="ratified" type="button" title="manager-session operation: record the word">Ratified</button>
      <button data-ask type="button" title="manager-session operation: ask for a proposal">Ask</button>
    </div>
    <div class="limits">
      <details><summary class="muted">Details</summary><p class="muted">A lane whose worker stopped reporting is RESOLVED in the queue and Quiet here.</p></details>
    </div>
  </section>
  <section id="operationView" class="view operation-view hidden" aria-label="Operation">
    <button id="steerButton" type="button" title="manager-session operation: steer the objective">Steer</button>
    <button data-priority="up" type="button" title="manager-session operation: raise a priority">Raise this</button>
    <button id="feedbackButton" type="button">Feedback</button>
    <div class="dialog-field"><label for="feedbackText">Feedback</label><textarea id="feedbackText"></textarea></div>
    <div class="dialog-field"><label for="feedbackImage">Optional screenshot</label><input id="feedbackImage" type="file" accept="image/*" /></div>
    <div class="dialog-field"><label for="feedbackVoice">Or a voice note</label><input id="feedbackVoice" type="file" accept="audio/*" /></div>
  </section>
</main>
  <aside class="manager-console" id="managerConsole" aria-label="Manager Console">
    <div id="consoleBody" class="console-body"></div>
    <form id="consoleForm"><input id="consoleInput" autocomplete="off" /><button type="submit">Send</button></form>
  </aside>
</div></div>
<script src="/static/js/main.js"></script></body></html>
"""

BAD_SHELL = """<!doctype html><html><head><title>Converge</title>
<link rel="stylesheet" href="/static/css/shell.css"></head><body>
<div id="app" class="app-shell">
<header class="topbar">
  <div id="workspaceSwitch" class="workspace-switch" role="tablist" aria-label="Workspace view">
    <button class="workspace-tab active" id="directionTab" role="tab" type="button">Direction</button>
    <button class="workspace-tab" id="operationTab" role="tab" type="button">Operation</button>
    <button class="workspace-tab" id="consoleTab" role="tab" type="button">Console</button>
  </div>
</header>
<div class="body-grid"><main class="workspace">
  <section id="homeView" class="view home-view hidden" aria-label="All manager sessions">
    <div id="homeSessionGrid"></div>
  </section>
  <section id="directionView" class="view direction-view" aria-label="Direction">
    <p class="lane-note">This lane is STALE and its last worker is DEAD.</p>
    <div class="review-actions">
      <button data-decision="ratified" type="button">Ratified</button>
    </div>
    <aside class="manager-console" id="managerConsole" aria-label="Manager Console">
      <div id="consoleBody" class="console-body"></div>
    </aside>
  </section>
  <section id="operationView" class="view operation-view hidden" aria-label="Operation">
    <button id="feedbackButton" type="button">Feedback</button>
    <div class="dialog-field"><label for="feedbackText">Feedback</label><textarea id="feedbackText"></textarea></div>
  </section>
</main></div></div>
<script src="/static/js/main.js"></script></body></html>
"""


# --------------------------------------------------------------------------- #
# the client                                                                   #
# --------------------------------------------------------------------------- #
GOOD_HOME_JS = """// "Which manager needs you?" — every manager, most needful first.
import { $, qsa, data, escapeHtml } from '../state.js';

export function renderHome() {
  const sorted = [...data.managerList].sort((a, b) => b.needs - a.needs || (a.status === 'working' ? -1 : 1));
  $('homeSessionGrid').innerHTML = sorted.map((m) => `
      <button class="home-manager-card" data-home-manager="${escapeHtml(m.id)}" type="button">
        <span class="eyebrow">${escapeHtml(m.statusLabel)}</span>
        <span class="status-dot ${escapeHtml(m.status)}"></span>
        <p>${escapeHtml(m.summary)}</p>
        <div><strong>${m.needs}</strong><span>need your word</span></div>
        <div><strong>${m.lanesActive}/${m.lanesMax}</strong><span>lanes</span></div>
      </button>`).join('');
}
"""

BAD_HOME_JS = """// the manager list, in whatever order it arrived
import { $, data, escapeHtml } from '../state.js';

export function renderHome() {
  $('homeSessionGrid').innerHTML = data.managerList.map((m) => `
      <button class="home-manager-card" type="button"><h2>${escapeHtml(m.name)}</h2></button>`).join('');
}
"""

GOOD_ACTIONS_JS = """// Every write, and the manager-session operation that does the same thing.
import { api } from './api.js';

// experience.v1 clause 8 — whatever you can do here, the manager session can do
// too, and the surface says which operation that is.
export const MANAGER_OPERATIONS = {
  decision: 'manager-session operation: record the steward word in the dated record',
  priority: 'manager-session operation: raise or lower a priority in the queue',
  feedback: 'manager-session operation: drop feedback into the return log',
  steer: 'manager-session operation: steer the objective, the budget, the lanes',
  ask: 'manager-session operation: ask for a proposal at a named scope',
};

export function wire() {
  qsa('[data-decision]').forEach((b) => b.addEventListener('click', () => api.decision(b.dataset.decision)));
  qsa('[data-priority]').forEach((b) => b.addEventListener('click', () => api.priority(b.dataset.priority)));
  qsa('[data-ask]').forEach((b) => b.addEventListener('click', () => api.ask()));
}

export function openFeedback() { api.feedback({ text: read('feedbackText') }); }
export function openSteer() { api.steer({ objective: read('steerObjective') }); }
"""

BAD_ACTIONS_JS = """// Everything that leaves the browser.
import { api } from './api.js';

export function wire() {
  qsa('[data-decision]').forEach((b) => b.addEventListener('click', () => api.decision(b.dataset.decision)));
}

export function openFeedback() { api.feedback({ text: read('feedbackText') }); }
export function publish() { api.publish({ everything: true }); }
"""

MAIN_JS = "import { renderHome } from './render/home.js';\nrenderHome();\n"
SHELL_CSS = ".app-shell { display: grid; }\n"


# --------------------------------------------------------------------------- #
# the repository half                                                          #
# --------------------------------------------------------------------------- #
def umbrella(named_contracts, reserved: str) -> str:
    lines = "\n".join(f"   `{n}` ·" for n in named_contracts)
    return f"""# Experience Contract — v1 (DRAFT)

## Core (the teeth)

1. **The anchor is a manager session, not a repository.** Home is the list of
   manager sessions you run, sorted by which one needs you.
2. **Two places, and only two.** Direction and Operation.
3. **The Manager Console is a pane, never a third place.**
4. **Exactly five writes.** Answer with a word · raise or lower a priority ·
   drop feedback · steer · ask for a proposal.
5. **At most five things ask for your word at once,** and every answer lands in
   a dated ratification record.
6. **Plain state words everywhere.**
7. **The app holds no data of its own.**
8. **Whatever you can do here, the manager session can do too.**
9. **Every behavior carries one of four words.**
10. **`IDIOM` means the behavior is required and its shape is not.**
11. **Idioms satisfy behaviors; they never subtract them.**
12. **A body may exceed this umbrella in idiom, never in features.**
13. **Three surface classes, named once:** full app · quick-access · notification.
14. **Where a body genuinely cannot do a thing, it says so in the app.**
15. **This umbrella governs a family.** The places are held by
{lines}
   and the idioms of one body by one platform contract.

## Reserved / open questions

{reserved}
"""


def section(title: str, tagged: bool, placed: bool) -> str:
    word = " *(REQUIRED)*" if tagged else ""
    placement = ("\n\n*Placement:* full app · quick-access · notification."
                 if placed else "")
    clauses = "\n".join(
        f"{n}. **Clause {n} of {title}.**{word} It says what it means.{placement}"
        for n in range(1, 4))
    return f"# {title} — v1 (DRAFT)\n\n## Core (the teeth)\n\n{clauses}\n"


GOOD_FAMILY = ("experience-direction.v1", "experience-operation.v1",
               "experience-console.v1", "experience-collaboration.v1")

GOOD_WRITES_PY = '''"""The things a steward can actually do."""


def record_decision(repo, *, word, proposal_id):
    """Append the steward's word to today's ratification record."""
    path = repo / "docs" / "workflow" / f"owner-ratifications-{day}.md"
    path.write_text(entry)
'''

BAD_WRITES_PY = '''"""The things a steward can actually do."""

import sqlite3


def record_decision(repo, *, word, proposal_id):
    """Keep the steward's word in the app's own database."""
    sqlite3.connect("decisions.db").execute("insert into decisions values (?)", (word,))
'''

RATIFICATIONS = """# Owner ratifications — 2026-09-03

Each entry below is the steward's own word on one proposal, recorded when it was
given.

## 2026-09-03T10:00:00+01:00 — Ratified: experience (P4)

- **Proposal:** `P4`
"""


def good_repo() -> dict:
    repo = {
        "contracts/experience.v1.md": umbrella(
            GOOD_FAMILY,
            "- Where the reading cursor behind \"what changed since you last read\" is\n"
            "  kept, given the app holds no data of its own.\n"),
        "docs/workflow/owner-ratifications-2026-09-03.md": RATIFICATIONS,
        "app/writes.py": GOOD_WRITES_PY,
    }
    for name in GOOD_FAMILY:
        repo[f"contracts/{name}.md"] = section(name, tagged=True, placed=True)
    return repo


def bad_repo() -> dict:
    repo = {
        # names a contract that does not exist, and leaves nothing open
        "contracts/experience.v1.md": umbrella(
            GOOD_FAMILY + ("experience-nowhere.v1",),
            "- Nothing is left open.\n"),
        "app/writes.py": BAD_WRITES_PY,
    }
    for name in GOOD_FAMILY:
        repo[f"contracts/{name}.md"] = section(name, tagged=False, placed=False)
    return repo


# --------------------------------------------------------------------------- #
# the two fixtures                                                             #
# --------------------------------------------------------------------------- #
def routes_for(shell, boot, manager, operation, needs, home_js, actions_js, table):
    return {
        "/": ("index.html", shell),
        "/openapi.json": ("openapi.json", api(table)),
        "/api/boot": ("api__boot.json", json.dumps(boot, indent=1)),
        f"/api/managers/{MANAGER}": ("api__managers__m1.json", json.dumps(manager, indent=1)),
        f"/api/managers/{MANAGER}/operation":
            ("api__managers__m1__operation.json", json.dumps(operation, indent=1)),
        f"/api/needs/{MANAGER}": ("api__needs__m1.json", json.dumps(needs, indent=1)),
        f"/api/managers/{MANAGER}/docs/r1/vision":
            ("api__managers__m1__docs__r1__vision.json", json.dumps(GOOD_DOC, indent=1)),
        "/static/js/main.js": ("static__js__main.js", MAIN_JS),
        "/static/js/actions.js": ("static__js__actions.js", actions_js),
        "/static/js/render/home.js": ("static__js__render__home.js", home_js),
        "/static/css/shell.css": ("static__css__shell.css", SHELL_CSS),
    }


def main() -> int:
    good = write(
        "sample-good",
        "a body that keeps every promise experience.v1 makes of it, beside a "
        "repository whose family is fully written",
        routes_for(GOOD_SHELL, GOOD_BOOT, GOOD_MANAGER, GOOD_OPERATION, GOOD_NEEDS,
                   GOOD_HOME_JS, GOOD_ACTIONS_JS, GOOD_ROUTES),
        good_repo())
    bad = write(
        "sample-bad",
        "the same promises with nothing behind them: a third place, two writes "
        "missing and one no contract names, seven things asking at once, the "
        "machine's own words on the surface, and a family half unwritten",
        routes_for(BAD_SHELL, BAD_BOOT, BAD_MANAGER, BAD_OPERATION, BAD_NEEDS,
                   BAD_HOME_JS, BAD_ACTIONS_JS, BAD_ROUTES),
        bad_repo())
    for path in (good, bad):
        print(f"wrote {path.relative_to(KIT.parent.parent)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
