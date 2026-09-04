#!/usr/bin/env python3
"""Write the six good/bad fixtures the three experience kits are proved against.

    uv run conformance/experience-fixtures/make_fixtures.py

A fixture is a **captured app snapshot** — the same shape `run.py --capture`
writes: a `manifest.json` naming the route each file came from, plus the files.
So a fixture is judged by exactly the code path a live app is, and a kit that
only worked against a hand-shaped page would be caught here.

`sample-good` is a body that keeps every promise its kit asserts; `sample-bad`
breaks every one of them at once, so a single run surfaces all of them. Both are
committed, and this script rewrites them in place — it is how they are kept in
step when a rule is added, not a build step anyone has to run first.
"""

from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent          # conformance/
MANAGER = "m1"


# --------------------------------------------------------------------------- #
# writing                                                                      #
# --------------------------------------------------------------------------- #
def write(kit: str, name: str, note: str, files: dict) -> pathlib.Path:
    out = ROOT / kit / "fixtures" / name
    if out.exists():
        for old in sorted(out.iterdir()):
            old.unlink()
    out.mkdir(parents=True, exist_ok=True)
    routes = []
    for route, (filename, body) in files.items():
        (out / filename).write_text(body, encoding="utf-8")
        kind = ("js" if filename.endswith(".js") else
                "css" if filename.endswith(".css") else
                "openapi" if route == "/openapi.json" else
                "json" if filename.endswith(".json") else "html")
        routes.append({"route": route, "file": filename, "kind": kind})
    (out / "manifest.json").write_text(json.dumps(
        {"base": str(out), "captured": "fixture", "manager": MANAGER,
         "note": note, "routes": routes}, indent=2) + "\n", encoding="utf-8")
    return out


def api(routes: dict) -> str:
    return json.dumps({"openapi": "3.1.0", "paths": {
        p: {m.lower(): {"summary": p} for m in ms} for p, ms in routes.items()}}, indent=1)


GOOD_ROUTES = {
    "/": ["GET"],
    "/api/boot": ["GET"],
    f"/api/managers/{{mid}}": ["GET"],
    f"/api/managers/{{mid}}/operation": ["GET"],
    f"/api/managers/{{mid}}/docs/{{repo}}/{{doc}}": ["GET"],
    f"/api/managers/{{mid}}/docs/{{repo}}/{{doc}}/save": ["POST"],
    f"/api/managers/{{mid}}/decision": ["POST"],
    f"/api/managers/{{mid}}/priority": ["POST"],
    f"/api/managers/{{mid}}/feedback": ["POST"],
    f"/api/managers/{{mid}}/steer": ["POST"],
    f"/api/managers/{{mid}}/ask": ["POST"],
    "/api/needs/{mid}": ["GET"],
    "/api/tmux/{socket}/{session}": ["GET"],
    "/api/tmux/{socket}/{session}/keys": ["POST"],
    "/login": ["GET", "POST"],
}

BAD_ROUTES = {
    "/": ["GET"],
    "/api/boot": ["GET"],
    f"/api/managers/{{mid}}": ["GET"],
    f"/api/managers/{{mid}}/operation": ["GET"],
    f"/api/managers/{{mid}}/docs/{{repo}}/{{doc}}": ["GET"],
    f"/api/managers/{{mid}}/decision": ["POST"],
    f"/api/managers/{{mid}}/feedback": ["POST"],
    f"/api/managers/{{mid}}/steer": ["POST"],
    "/api/tmux/sessions": ["GET"],
    "/api/tmux/{socket}/{session}": ["GET"],
    "/login": ["GET", "POST"],
}


# --------------------------------------------------------------------------- #
# the payloads                                                                 #
# --------------------------------------------------------------------------- #
GOOD_DOC = {
    "path": "docs/VISION.md",
    "title": "Vision",
    "state": "draft",
    "standing": "Not yet",
    "sections": [["Where this is going",
                  "<p>The agreement is <strong>one body of work</strong>.</p>"
                  "<table><tr><th>Promise</th><th>State</th></tr>"
                  "<tr><td>one place</td><td>Not yet</td></tr></table>"
                  "<p><a href=\"contracts/experience.v1.md\">the umbrella</a></p>"]],
    "raw": ("# Vision\n\nThe agreement is **one body of work**.\n\n"
            "| Promise | State |\n|---|---|\n| one place | Not yet |\n\n"
            "See [the umbrella](contracts/experience.v1.md).\n"),
    "changes": [{"id": 1, "section": "Where this is going", "source": "proposal 4",
                 "before": "People align in documents.",
                 "now": "People align in documents, and Git is the protocol."}],
    "proposals": [{"id": "P4", "source": "a pull request", "title": "name the protocol",
                   "why": "a teammate asked", "unchanged": "every other clause",
                   "evidence": ["the teammate's comment"]}],
    "history": [{"id": "now", "label": "Current", "date": "Sep 3", "note": "ratified"}],
}

BAD_DOC = dict(GOOD_DOC,
               sections=[["Where this is going", "<p>plain words only</p>"]],
               raw=GOOD_DOC["raw"],
               changes=[{"id": 1, "section": "Where this is going", "text": "something moved"}],
               proposals=[{"id": "P4", "source": "a pull request", "title": "name it"}])

GOOD_MANAGER = {
    "id": MANAGER, "name": "Example", "status": "running", "statusLabel": "Running",
    "age": "20m", "summary": "Working.", "objective": "Keep the promises.",
    "deadline": "Friday", "strategy": "3 waves", "strategyNarrative": "Contracts first.",
    "lanesMax": 4, "lanesActive": 3, "needs": 2, "repos": 1, "projects": 1,
    "managerTmux": "hw:example",
    "repositories": [{"id": "r1", "name": "Repo one", "path": "/tmp/r1", "docs": [
        {"id": "vision", "title": "Vision", "fullTitle": "Vision (DRAFT)",
         "state": "draft", "standing": "Not yet", "path": "docs/VISION.md"}]}],
}

BAD_MANAGER = dict(GOOD_MANAGER, objective="", strategy="", strategyNarrative="",
                   deadline="", lanesMax=None, lanesActive=None, managerTmux="",
                   repositories=[{"id": "r1", "name": "Repo one", "path": "/tmp/r1",
                                  "docs": []}])

GOOD_OPERATION = {
    "waves": [{"id": "w1", "label": "Wave 1", "title": "Prove the contracts are checkable",
               "reason": "Nothing else can be trusted until a kit can judge it.",
               "phase": "RUNNING", "cls": "run", "progress": 40,
               "items": [["w1-kit", False], ["w1-ledger", True]]}],
    "lanes": [
        {"id": "w1-kit", "status": "working", "statusLabel": "Working", "wave": "Wave 1",
         "title": "build the kit", "worker": "w1-kit", "age": "20m",
         "evidence": "3 commits", "tmux": {"socket": "hw", "session": "w1-kit"}},
        {"id": "w1-ledger", "status": "quiet", "statusLabel": "Quiet", "wave": "Wave 1",
         "title": "seed the ledger", "worker": "w1-ledger", "age": "40m",
         "evidence": "1 commit", "tmux": {"socket": "hw", "session": "w1-ledger"}}],
    "timeline": [{"date": "2026-09-03", "title": "the kit judged the app",
                  "text": "Confidence rose: the promises are now checkable.",
                  "evidence": "/api/managers/m1/operation#w1-kit"}],
    "returnBrief": [
        "You were away 20m.",
        "Finished: the ledger seed landed and was verified.",
        "Stuck: the turnkey lane is blocked on a host package.",
        "Needs your word: two proposals are waiting on you.",
        "Quietly changed: the plan was redrawn after the app shipped."],
    "throughput": {"derived": 8, "resolved": 6, "verified": 5, "reopened": 1, "stuck": 1,
                   "spark": [1, 2, 3], "available": True},
    "confidence": {"pct": 60, "kept": 6, "notyet": 4, "broken": 0, "pinnedOpen": 0,
                   "cantCheck": 1, "available": True},
}

BAD_OPERATION = {
    "waves": [{"id": "w1", "label": "Wave 1", "title": "w1-kit, w1-ledger",
               "phase": "RUNNING", "cls": "run", "progress": 40,
               "items": [["w1-kit", False], ["w1-ledger", True]]},
              {"id": "w2", "label": "Wave 2", "title": "", "phase": "NEXT", "cls": "next",
               "progress": 0, "items": []}],
    "lanes": [{"id": "w1-kit", "status": "done", "statusLabel": "Done", "wave": "",
               "title": "build the kit", "worker": "w1-kit", "age": "20m",
               "evidence": ""}],
    "timeline": [["2026-09-03", "something moved", "no way to look at it"]],
    "returnBrief": [],
    "throughput": {"derived": 8, "resolved": 6, "available": True},
    "confidence": {"available": False},
}


# --------------------------------------------------------------------------- #
# the shells                                                                   #
# --------------------------------------------------------------------------- #
SHELL_HEAD = """<!doctype html><html><head><title>Converge</title>
<link rel="stylesheet" href="/static/css/shell.css"></head><body>
<div id="app" class="app-shell">
<header class="topbar">
"""

GOOD_DIRECTION_VIEW = """
  <section id="directionView" class="view direction-view" aria-label="Direction">
    <select id="repoFilter" aria-label="Repository filter">
      <option value="all">All repos</option><option value="r1">Repo one</option></select>
    <div id="repoTree"></div>
    <div class="doc-tools">
      <button id="rawToggle" type="button">Raw</button>
      <button id="copyRendered" type="button">Copy rendered</button>
      <button id="copySource" type="button">Copy source</button>
      <button id="downloadDoc" type="button">Download</button>
      <button id="zoomIn" type="button">Zoom</button>
      <button id="wideToggle" type="button">Wide</button>
    </div>
    <div class="mode-tabs">
      <button data-doc-mode="read" type="button">Read</button>
      <button data-doc-mode="changes" type="button">Changes</button>
      <button data-doc-mode="review" type="button">Review</button>
      <button data-doc-mode="history" type="button">History</button>
    </div>
    <div class="editing">
      <button data-edit="document" type="button">Edit this draft</button>
      <p class="presence">Someone is editing this section right now.</p>
      <div class="collision">
        <button type="button">Use combined</button>
        <button type="button">Keep mine</button>
        <button type="button">Review both</button>
      </div>
    </div>
    <div class="change-card">
      <button data-change-action="keep" type="button">Keep this change</button>
      <button data-change-action="revert" type="button">Revert this change</button>
    </div>
    <div class="history-actions">
      <button data-restore="paragraph" type="button">Restore a paragraph</button>
      <button data-restore="document" type="button">Restore this document</button>
    </div>
    <div class="ask">
      <button data-ask scope="paragraph" type="button">Ask about this paragraph</button>
      <button data-ask scope="document" type="button">Ask about this document</button>
      <button data-ask scope="all" type="button">Ask across every document</button>
    </div>
    <div class="lock-gate">
      <p>It says what it means &mdash; Green</p>
      <p>It carries a real example of right and wrong &mdash; Green</p>
      <p>It can be checked against reality &mdash; Not yet</p>
      <p>The steward has read it and agreed &mdash; Not yet</p>
      <button id="lockButton" type="button" disabled>Lock this contract</button>
    </div>
  </section>
"""

GOOD_OPERATION_VIEW = """
  <section id="operationView" class="view operation-view" aria-label="Operation">
    <strong id="opObjectiveText">Keep the promises.</strong>
    <h2 id="strategyHeadline">3 waves</h2>
    <div class="strategy-facts"><span>Hard limit</span><strong id="strategyDeadline">Friday</strong>
      <span>Lane budget</span><strong id="strategyLaneBudget">4 max</strong></div>
    <section class="return-card"><h2 id="awayDuration">20m</h2>
      <div id="returnBrief" class="brief-list"></div></section>
    <section class="throughput-card"><h2>Flow today</h2>
      <div><span>Derived</span><strong id="throughputDerived">8</strong></div>
      <div><span>Resolved</span><strong id="throughputResolved">6</strong></div>
      <div><span>Verified</span><strong id="throughputVerified">5</strong></div>
      <div><span>Reopened</span><strong id="throughputReopened">1</strong></div>
      <div><span>Stuck</span><strong id="throughputStuck">1</strong></div></section>
    <section class="confidence-card"><h2>Reality vs direction</h2>
      <div><span>Kept</span><strong id="confidenceKept">6</strong></div></section>
    <div class="queue"><span>Truly ready</span><strong id="trulyReadyCount">3</strong>
      <span>Waiting on you</span><strong id="waitingOnYouCount">2</strong></div>
    <section class="waves-card"><div id="wavesGrid" class="waves-grid"></div></section>
    <section class="lanes-card">
      <h2><span id="activeLaneCount">3</span> of <span id="laneBudgetCount">4</span> working</h2>
      <button id="fillLanesButton" type="button">Fill lanes</button>
      <div id="lanesGrid" class="lanes-grid"></div></section>
    <section class="timeline-card"><div id="timelineList"></div></section>
    <button id="steerButton" type="button">Steer</button>
    <p class="muted">A redrawn plan says why it was redrawn.</p>
  </section>
"""

GOOD_CONSOLE = """
  <aside class="manager-console" id="managerConsole" aria-label="Manager Console">
    <div class="console-header"><strong id="consoleContextTitle">manager-m1</strong>
      <button id="consoleClose" type="button" title="Close console">&times;</button></div>
    <div id="consoleBody" class="console-body"></div>
    <form id="consoleForm" class="console-form">
      <input id="consoleInput" autocomplete="off" placeholder="Message the manager" />
      <button type="submit">Send</button>
    </form>
    <div class="console-footer"><span>This pane is the manager session itself,
      not a chat built into the app.</span></div>
  </aside>
"""

GOOD_TOPBAR = """
  <div id="workspaceSwitch" class="workspace-switch" role="tablist">
    <button class="workspace-tab" id="directionTab" role="tab" type="button">Direction</button>
    <button class="workspace-tab" id="operationTab" role="tab" type="button">Operation</button>
  </div>
  <button id="needsYouButton" type="button"><strong id="needsYouCount">2</strong> need your word</button>
  <button id="tellAllButton" type="button">Tell all manager sessions</button>
  <button id="feedbackButton" type="button">Feedback</button>
  <button id="consoleToggle" type="button">Manager Console</button>
</header>
<div class="body-grid"><main class="workspace">
"""


def good_shell() -> str:
    return (SHELL_HEAD + GOOD_TOPBAR + GOOD_DIRECTION_VIEW + GOOD_OPERATION_VIEW
            + "</main>" + GOOD_CONSOLE + "</div></div>"
            + '<script src="/static/js/main.js"></script></body></html>\n')


BAD_TOPBAR = """
  <div id="workspaceSwitch" class="workspace-switch" role="tablist">
    <button class="workspace-tab" id="directionTab" role="tab" type="button">Direction</button>
    <button class="workspace-tab" id="operationTab" role="tab" type="button">Operation</button>
    <button class="workspace-tab" id="consoleTab" role="tab" type="button">Console</button>
  </div>
</header>
<div class="body-grid"><main class="workspace">
"""

BAD_DIRECTION_VIEW = """
  <section id="directionView" class="view direction-view" aria-label="Direction">
    <select id="repoFilter"><option value="r1">Repo one</option></select>
    <div class="doc-tools"><button id="copyRendered" type="button">Copy</button></div>
    <div class="mode-tabs">
      <button data-doc-mode="read" type="button">Read</button>
      <button data-doc-mode="changes" type="button">Changes</button>
    </div>
    <div class="change-card">
      <button data-change-action="keep" type="button">Keep this change</button></div>
    <div class="history-actions">
      <button data-restore="document" type="button">Restore this document</button></div>
  </section>
"""

BAD_OPERATION_VIEW = """
  <section id="operationView" class="view operation-view" aria-label="Operation">
    <strong id="opObjectiveText"></strong>
    <h2 id="strategyHeadline">&mdash;</h2>
    <div id="returnBrief" class="brief-list"></div>
    <section class="throughput-card"><h2>Flow today</h2>
      <div><span>Derived</span><strong id="throughputDerived">8</strong></div></section>
    <section class="waves-card"><div id="wavesGrid" class="waves-grid"></div></section>
    <section class="lanes-card"><div id="lanesGrid" class="lanes-grid"></div>
      <button id="stopLaneButton" type="button">Stop this lane</button></section>
    <p class="muted">Open the console to see what is happening.</p>
  </section>
"""

BAD_CONSOLE = """
  <aside class="manager-console" id="managerConsole" aria-label="Manager Console">
    <div id="consoleBody" class="console-body"></div>
    <form id="consoleForm" class="console-form">
      <input id="consoleInput" disabled />
      <button type="submit" disabled>Send</button>
    </form>
    <div class="console-decisions">
      <button data-decision="ratified" type="button">Ratified</button>
      <button data-decision="declined" type="button">Declined</button>
    </div>
  </aside>
"""


def bad_shell() -> str:
    return (SHELL_HEAD + BAD_TOPBAR + BAD_DIRECTION_VIEW + BAD_OPERATION_VIEW
            + "</main>" + BAD_CONSOLE + "</div></div>"
            + '<script src="/static/js/main.js"></script></body></html>\n')


# --------------------------------------------------------------------------- #
# the client                                                                   #
# --------------------------------------------------------------------------- #
GOOD_ACTIONS = """// every control that leaves the browser reaches a declared write
import { api } from './api.js';

export function wireEditing() {
  document.querySelectorAll('[data-edit]').forEach((btn) => btn.addEventListener('click', () => {
    api.save(state.managerId, { repoId: state.repoId, docId: state.docId, body: editorText() });
  }));
  document.querySelectorAll('[data-restore]').forEach((btn) => btn.addEventListener('click', () => {
    api.ask(state.managerId, { scope: btn.dataset.restore, intent: 'restore this wording' });
  }));
  document.querySelectorAll('[data-change-action]').forEach((btn) => btn.addEventListener('click', () => {
    api.decision(state.managerId, { proposalId: openProposalId(), staged: btn.dataset.changeAction });
  }));
  document.querySelectorAll('[data-ask]').forEach((btn) => btn.addEventListener('click', () => {
    api.ask(state.managerId, { scope: btn.getAttribute('scope') });
  }));
}

export function openFeedback() {
  const forms = { text: true, image: 'image/*', voice: 'audio/*' };
  api.feedback(state.managerId, { text: read('feedbackText'), forms });
}

export function fillLanes() {
  api.steer(state.managerId, { fill: true });
}

export function openSteer() {
  // objective, budget, lane count, fill the lanes, review this
  api.steer(state.managerId, {
    objective: read('steerObjective'), budget: read('steerBudget'),
    lanes: read('steerLanes'), fill: read('fillLanes'), review: read('managerReview'),
  });
}
"""

GOOD_DIRECTION_JS = """// Direction: read, what changed, the worked-out decision, history.
const DECISION_BUTTONS = [
  ['ratified', 'Ratify'],
  ['ratified-with-edits', 'Ratify with edits'],
  ['declined', 'Decline'],
  ['later', 'Later'],
];

export function renderReview() {
  const p = openProposal();
  return `<article class="review-sheet">
    <div class="review-section"><h3>What changes</h3><p>${p.title}</p></div>
    <div class="review-section"><h3>Why now</h3><p>${p.why}</p></div>
    <div class="review-section"><h3>Evidence</h3><ul>${p.evidence}</ul></div>
    <div class="review-section"><h3>What does not change</h3><p>${p.unchanged}</p></div>
    <div class="decision-stack">${DECISION_BUTTONS.map(([v, l]) =>
      `<button data-decision="${v}">${l}</button>`).join('')}</div>
  </article>`;
}
"""

GOOD_OPERATION_JS = """// Operation: strategy, brief, flow, confidence, waves, lanes.
export function renderOperation(op) {
  document.getElementById('lanesGrid').innerHTML = op.lanes.map((l) =>
    `<article class="lane-card"><span class="lane-status">${l.status}</span>
     <span class="lane-title">${l.title}</span>
     <details><summary>Evidence</summary><p>${l.evidence}</p></details>
     <button data-watch-lane="${l.id}">Watch session</button></article>`).join('');
  document.getElementById('wavesGrid').innerHTML = op.waves.map((w) =>
    `<article class="wave-card"><h3>${w.title}</h3><p class="wave-reason">${w.reason}</p>
     </article>`).join('');
}
"""

GOOD_CONSOLE_JS = """// Manager Console: one pane, one manager session.
export function watchLane(laneId) {
  const lane = data.operation.lanes.find((l) => String(l.id) === String(laneId));
  state.consoleTarget = lane.tmux;
  state.consoleContext = `lane-${lane.id}`;
  renderConsole();
}

export function showManagerConsole() {
  state.consoleContext = 'manager';
  state.consoleTarget = null;
  renderConsole();
}

export function renderConsole() {
  const target = activeTarget();
  window.ConvergeTmux.attach(document.getElementById('terminalHost'),
                             target.socket, target.session);
}

export function sendLine(line) {
  fetch(`/api/tmux/${target.socket}/${target.session}/keys`, {
    method: 'POST', body: JSON.stringify({ keys: line }),
  });
}
"""

GOOD_HOME_JS = """// Which manager session needs you?
export function renderHome() {
  const sorted = [...data.managerList].sort((a, b) => b.needs - a.needs);
  document.getElementById('homeSessionGrid').innerHTML = sorted.map((m) =>
    `<button data-home-manager="${m.id}">${m.name}</button>`).join('');
}
"""

GOOD_TOP_JS = """// Topbar chrome and the place switch. It never touches the console.
export function renderTop() {
  document.getElementById('directionView').classList.toggle(
    'hidden', state.workspace !== 'direction');
  document.getElementById('operationView').classList.toggle(
    'hidden', state.workspace !== 'operation');
}
"""

GOOD_MAIN_JS = """import { renderTop } from './render/top.js';
import { renderOperation } from './render/operation.js';
import { renderConsole, watchLane } from './render/console.js';
import { wireEditing, openFeedback, openSteer, fillLanes } from './actions.js';
export function renderAll() { renderTop(); renderOperation(data.operation); renderConsole(); }
"""

GOOD_CSS = """.manager-console { display:flex; flex-direction:column; resize:horizontal; overflow:auto; }
.body-grid.console-closed .manager-console { opacity:0; }
@media (max-width: 980px) {
  .manager-console { position:fixed; left:10px; right:10px; bottom:10px; }
  .body-grid.console-closed .manager-console { transform:translateY(calc(100% + 20px)); }
}
"""

BAD_ACTIONS = """// controls that show a message and forget
export function wireEditing() {
  document.querySelectorAll('[data-restore]').forEach((btn) => btn.addEventListener('click', () => {
    toast('Restoring opens a proposal for your word.');
  }));
  document.querySelectorAll('[data-change-action]').forEach((btn) => btn.addEventListener('click', () => {
    toast('Change marked to keep, pending the next proposal decision.');
  }));
}

export function openSteer() {
  api.steer(state.managerId, { objective: read('steerObjective') });
}
"""

BAD_DIRECTION_JS = """export function renderReview() {
  const p = openProposal();
  return `<article class="review-sheet">
    <div class="review-section"><h3>Evidence</h3><ul>${p.evidence}</ul></div>
    <div class="review-section"><h3>What changes</h3><p>${p.title}</p></div>
  </article>`;
}
"""

BAD_OPERATION_JS = """export function renderOperation(op) {
  document.getElementById('lanesGrid').innerHTML = op.lanes.map((l) =>
    `<article class="lane-card"><span class="lane-status">${l.status}</span></article>`).join('');
}
"""

BAD_CONSOLE_JS = """export function renderConsole() {
  document.getElementById('consoleBody').innerHTML = '<p>no session</p>';
}

export function submitConsole(line) {
  api.decision(state.managerId, { decision: line });
}
"""

BAD_HOME_JS = """export function renderHome() {
  document.getElementById('homeSessionGrid').innerHTML =
    data.managerList.map((m) => `<button>${m.name}</button>`).join('');
}
"""

BAD_TOP_JS = """export function renderTop() {
  state.consoleOpen = false;
  document.getElementById('consoleBody').innerHTML = '';
}
"""

BAD_MAIN_JS = """import { renderTop } from './render/top.js';
export function renderAll() { renderTop(); }
"""

BAD_CSS = """.manager-console { display:flex; flex-direction:column; }
@media (max-width: 980px) { .topbar { grid-template-columns:1fr; } }
"""


# --------------------------------------------------------------------------- #
# assembling                                                                   #
# --------------------------------------------------------------------------- #
def good_files(include: set) -> dict:
    files = {
        "/": ("index.html", good_shell()),
        "/openapi.json": ("openapi.json", api(GOOD_ROUTES)),
        "/api/boot": ("api__boot.json", json.dumps(
            {"user": "you", "managers": [dict(GOOD_MANAGER, repositories=None)]}, indent=1)),
        f"/api/managers/{MANAGER}": (f"api__managers__{MANAGER}.json",
                                     json.dumps(GOOD_MANAGER, indent=1)),
        f"/api/managers/{MANAGER}/operation": (f"api__managers__{MANAGER}__operation.json",
                                               json.dumps(GOOD_OPERATION, indent=1)),
        f"/api/needs/{MANAGER}": (f"api__needs__{MANAGER}.json", json.dumps(
            [{"id": "P4", "where": {"repoId": "r1", "docId": "vision"}}], indent=1)),
        f"/api/managers/{MANAGER}/docs/r1/vision":
            (f"api__managers__{MANAGER}__docs__r1__vision.json", json.dumps(GOOD_DOC, indent=1)),
        "/static/js/main.js": ("static__js__main.js", GOOD_MAIN_JS),
        "/static/js/actions.js": ("static__js__actions.js", GOOD_ACTIONS),
        "/static/js/render/direction.js": ("static__js__render__direction.js", GOOD_DIRECTION_JS),
        "/static/js/render/operation.js": ("static__js__render__operation.js", GOOD_OPERATION_JS),
        "/static/js/render/console.js": ("static__js__render__console.js", GOOD_CONSOLE_JS),
        "/static/js/render/home.js": ("static__js__render__home.js", GOOD_HOME_JS),
        "/static/js/render/top.js": ("static__js__render__top.js", GOOD_TOP_JS),
        "/static/css/shell.css": ("static__css__shell.css", GOOD_CSS),
    }
    return {k: v for k, v in files.items() if k in include}


def bad_files(include: set) -> dict:
    files = {
        "/": ("index.html", bad_shell()),
        "/openapi.json": ("openapi.json", api(BAD_ROUTES)),
        "/api/boot": ("api__boot.json", json.dumps(
            {"user": "you", "managers": [dict(BAD_MANAGER, repositories=None)]}, indent=1)),
        f"/api/managers/{MANAGER}": (f"api__managers__{MANAGER}.json",
                                     json.dumps(BAD_MANAGER, indent=1)),
        f"/api/managers/{MANAGER}/operation": (f"api__managers__{MANAGER}__operation.json",
                                               json.dumps(BAD_OPERATION, indent=1)),
        f"/api/needs/{MANAGER}": (f"api__needs__{MANAGER}.json", json.dumps([], indent=1)),
        f"/api/managers/{MANAGER}/docs/r1/vision":
            (f"api__managers__{MANAGER}__docs__r1__vision.json", json.dumps(BAD_DOC, indent=1)),
        "/static/js/main.js": ("static__js__main.js", BAD_MAIN_JS),
        "/static/js/actions.js": ("static__js__actions.js", BAD_ACTIONS),
        "/static/js/render/direction.js": ("static__js__render__direction.js", BAD_DIRECTION_JS),
        "/static/js/render/operation.js": ("static__js__render__operation.js", BAD_OPERATION_JS),
        "/static/js/render/console.js": ("static__js__render__console.js", BAD_CONSOLE_JS),
        "/static/js/render/home.js": ("static__js__render__home.js", BAD_HOME_JS),
        "/static/js/render/top.js": ("static__js__render__top.js", BAD_TOP_JS),
        "/static/css/shell.css": ("static__css__shell.css", BAD_CSS),
    }
    return {k: v for k, v in files.items() if k in include}


COMMON = {"/", "/openapi.json", "/api/boot", f"/api/managers/{MANAGER}",
          "/static/js/main.js", "/static/js/actions.js", "/static/js/render/top.js",
          "/static/css/shell.css"}

READS = {
    "experience-direction": COMMON | {f"/api/managers/{MANAGER}/docs/r1/vision",
                                      "/static/js/render/direction.js"},
    "experience-operation": COMMON | {f"/api/managers/{MANAGER}/operation",
                                      f"/api/needs/{MANAGER}",
                                      "/static/js/render/operation.js",
                                      "/static/js/render/console.js",
                                      "/static/js/render/home.js"},
    "experience-console": COMMON | {f"/api/managers/{MANAGER}/operation",
                                    f"/api/needs/{MANAGER}",
                                    "/static/js/render/console.js",
                                    "/static/js/render/operation.js"},
}

NOTES = {
    "sample-good": "a body that keeps every promise this kit asserts — the kit reports PASS",
    "sample-bad": "the same promises with nothing behind them — every checkable rule FAILs",
}


def main() -> int:
    for kit, reads in READS.items():
        write(kit, "sample-good", NOTES["sample-good"], good_files(reads))
        write(kit, "sample-bad", NOTES["sample-bad"], bad_files(reads))
        print(f"wrote {kit}/fixtures/sample-good and sample-bad "
              f"({len(reads)} routes each)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
