// Boot, wiring, and the full re-render. Same shape as the mock: state changes,
// then everything renders again. No framework, no partial diffing.
import { $, qsa, state, data, toast, currentDoc } from './state.js';
import { api } from './api.js';
import { hooks } from './refresh.js';
import { renderTop, renderSessions, renderManagerMenu } from './render/top.js';
import { renderHome } from './render/home.js';
import { renderDirection } from './render/direction.js';
import { renderOperation } from './render/operation.js';
import { renderConsole, showManagerConsole } from './render/console.js';
import {
  openFeedback, openSteer, fillLanes, closeDialog, downloadCurrentDoc, copyText, toggleBookmark,
} from './actions.js';

// Which screen the shell is on, said once on the shell's own root so a
// stylesheet can read it.
//
// `platform-web.v1` Core 1: the Manager Console is "a pane beside either
// [Direction or Operation], never a third place". Home is neither of those two
// places. Where the console is a PANE that costs nothing (the laptop) drawing
// it beside Home is harmless; where it is an OVERLAY (a phone, below 980px,
// `app/static/css/console.css`) it lies over Home -- and Home IS the list of
// manager sessions, so the list was drawn and not touchable (converge-nxf,
// measured 2026-09-04 at 390x844: a click on Home's tell-all control at
// [16,418,211,457] was intercepted by `#consoleBody`).
//
// So the class below is the fact, and console.css draws the consequence at the
// overlay width only. The console's own open state is untouched: the pane is
// exactly as the steward left it the moment they open a manager session.
function reflectScreen() {
  const shell = $('app');
  if (shell) shell.classList.toggle('screen-home', state.screen === 'home');
}

// Is the console pane inert where the steward is standing? Read off the pane
// itself rather than re-deriving the breakpoint here: `console.css` owns the
// rule, and a second copy of a rule is a second thing to keep in step.
export function consoleIsStowedHere() {
  const pane = $('managerConsole');
  if (!pane || typeof getComputedStyle !== 'function') return false;
  return getComputedStyle(pane).pointerEvents === 'none';
}

const CONSOLE_IS_ELSEWHERE =
  'The Manager Console is a pane beside Direction and Operation. Open a manager '
  + 'session to read it.';

// The control must not say "on" over a screen with no pane on it (converge-30aw).
//
// `render/console.js` sets `aria-pressed` and `active` from `state.consoleOpen`,
// which is the console's own open state and is deliberately NOT changed by Home
// -- converge-nxf stows the SHEET on Home and leaves the state alone, so the
// pane is exactly as the steward left it the moment they open a manager
// session. Both halves are right on their own and wrong together: measured
// 2026-09-04 at 390x844 on Home, `{pointerEvents: 'none', gridClosed: false,
// togglePressed: 'true'}` -- the control read "on" while nothing was drawn, and
// a steward tapping it saw nothing change on that screen.
//
// So the STATE stays untouched and the CONTROL tells the truth about the screen
// it is on: not pressed, and a title naming where the pane actually is. This
// runs after `renderConsole()` rather than inside it, because `console.js` is
// another lane's file.
function reflectConsoleControl() {
  const btn = $('consoleToggle');
  if (!btn) return;
  const elsewhere = state.screen === 'home' && consoleIsStowedHere();
  btn.classList.toggle('console-elsewhere', elsewhere);
  if (elsewhere) {
    btn.setAttribute('aria-pressed', 'false');
    btn.classList.remove('active');
    btn.setAttribute('title', CONSOLE_IS_ELSEWHERE);
  } else {
    btn.removeAttribute('title');
  }
}

export function renderAll() {
  renderTop();
  renderSessions();
  renderHome();
  renderDirection();
  renderOperation();
  renderConsole();
  renderManagerMenu();
  reflectScreen();
  reflectConsoleControl();
}

function pickDoc() {
  const repo = data.repoList.find((r) => r.id === state.repoId) || data.repoList[0];
  if (!repo) { state.repoId = null; state.docId = null; return; }
  state.repoId = repo.id;
  const doc = repo.docs.find((d) => d.id === state.docId) || repo.docs[0];
  state.docId = doc ? doc.id : null;
}

async function loadDoc() {
  if (!state.repoId || !state.docId) { data.doc = null; return; }
  try {
    data.doc = await api.doc(state.managerId, state.repoId, state.docId);
  } catch (err) {
    data.doc = null;
    toast(`Could not open the document: ${err.message}`);
  }
}

export async function selectManager(id) {
  state.managerId = id;
  state.screen = 'workspace';
  state.consoleContext = 'manager';
  state.consoleTarget = null;
  state.proposalDecision = null;
  state.historyId = 'now';
  try {
    const [manager, operation] = await Promise.all([api.manager(id), api.operation(id)]);
    data.manager = manager;
    data.repoList = manager.repositories || [];
    data.operation = operation;
  } catch (err) {
    toast(`Could not open that manager: ${err.message}`);
    return;
  }
  pickDoc();
  await loadDoc();
  renderAll();
  toast(`Opened ${data.manager.name}`);
}

export async function selectDoc(repoId, docId) {
  state.repoId = repoId;
  state.docId = docId;
  state.docMode = 'read';
  state.raw = false;
  state.historyId = 'now';
  state.proposalDecision = null;
  await loadDoc();
  renderDirection();
}

export async function reloadDoc() {
  await loadDoc();
  renderDirection();
}

export async function reloadManager() {
  if (!state.managerId) return;
  try {
    const [boot, manager, operation] = await Promise.all([
      api.boot(), api.manager(state.managerId), api.operation(state.managerId),
    ]);
    data.managerList = boot.managers || [];
    data.manager = manager;
    data.repoList = manager.repositories || [];
    data.operation = operation;
  } catch (err) {
    toast(`Could not refresh: ${err.message}`);
    return;
  }
  pickDoc();
  await loadDoc();
  renderAll();
}

function showHome() {
  state.screen = 'home';
  renderAll();
}

function wire() {
  $('brandHome').addEventListener('click', showHome);
  $('allSessionsButton').addEventListener('click', showHome);
  $('directionTab').addEventListener('click', () => { state.screen = 'workspace'; state.workspace = 'direction'; renderAll(); });
  $('operationTab').addEventListener('click', () => { state.screen = 'workspace'; state.workspace = 'operation'; renderAll(); });
  $('needsYouButton').addEventListener('click', async () => {
    // Take the steward to the thing that actually needs their word, not just to a tab.
    state.screen = 'workspace';
    state.workspace = 'direction';
    try {
      data.needList = (await api.needs(state.managerId)) || [];
      const first = data.needList.find((n) => n.where && n.where.repoId && n.where.docId);
      if (first) await selectDoc(first.where.repoId, first.where.docId);
    } catch { /* no needs endpoint answer: fall back to the open document */ }
    state.docMode = 'review';
    renderAll();
  });
  $('feedbackButton').addEventListener('click', openFeedback);
  $('consoleToggle').addEventListener('click', () => {
    // The gesture `platform-web.v1` §6 names -- pull it up, push it down -- is
    // untouched: the state flips wherever the steward taps, so the pane is as
    // they left it when they next open a manager session.
    const wasStowedHere = state.screen === 'home' && consoleIsStowedHere();
    state.consoleOpen = !state.consoleOpen;
    renderConsole();
    reflectConsoleControl();
    // On Home below the overlay width nothing is drawn to change, so the tap
    // would otherwise be silent (converge-30aw). Say where the pane is and what
    // just happened to it, rather than leaving the steward tapping a control
    // that appears dead.
    if (wasStowedHere) {
      toast(`${CONSOLE_IS_ELSEWHERE} It is now ${state.consoleOpen ? 'open' : 'closed'} there.`);
    }
  });
  $('consoleClose').addEventListener('click', () => { state.consoleOpen = false; renderConsole(); reflectConsoleControl(); });
  $('managerSelectButton').addEventListener('click', () => $('managerMenu').classList.toggle('hidden'));
  document.addEventListener('click', (e) => {
    if (!e.target.closest('#managerMenu') && !e.target.closest('#managerSelectButton')) $('managerMenu').classList.add('hidden');
  });
  $('repoFilter').addEventListener('change', (e) => { state.repoFilter = e.target.value; renderDirection(); });
  qsa('[data-doc-mode]').forEach((btn) => btn.addEventListener('click', () => { state.docMode = btn.dataset.docMode; renderDirection(); }));
  $('showChangesShortcut').addEventListener('click', () => { state.docMode = 'changes'; renderDirection(); });
  $('wideToggle').addEventListener('click', () => { state.wide = !state.wide; renderDirection(); });
  $('rawToggle').addEventListener('click', () => { state.raw = !state.raw; state.docMode = 'read'; renderDirection(); });
  $('copyRendered').addEventListener('click', () => copyText(data.doc ? data.doc.raw || '' : ''));
  $('downloadDoc').addEventListener('click', downloadCurrentDoc);
  $('bookmarkButton').addEventListener('click', toggleBookmark);
  qsa('[data-nav-special]').forEach((btn) => btn.addEventListener('click', () => {
    const kind = btn.dataset.navSpecial;
    if (kind === 'changes') state.docMode = 'changes';
    if (kind === 'proposals') state.docMode = 'review';
    if (kind === 'decisions') state.docMode = 'history';
    renderDirection();
  }));
  $('steerButton').addEventListener('click', openSteer);
  $('timelineButton').addEventListener('click', () => $('timelineCard').classList.remove('hidden'));
  $('closeTimelineButton').addEventListener('click', () => $('timelineCard').classList.add('hidden'));
  $('fillLanesButton').addEventListener('click', fillLanes);
  qsa('[data-console-tab]').forEach((btn) => btn.addEventListener('click', () => { state.consoleTab = btn.dataset.consoleTab; renderConsole(); }));
  // No submit handler for #consoleForm here, on purpose (converge-gf0). The one
  // that used to sit on this line toasted that the console could not be typed
  // into. That sentence has been false since converge-tfu -- the app takes
  // keystrokes, `POST /api/tmux/{socket}/{session}/keys` answers them, and
  // `render/console.js` owns BOTH ways a line is sent: Enter in the field and
  // the send button, each calling `preventDefault()` before its own `sendLine()`.
  // The toast was unreachable only by that accident of event ordering; a second,
  // differently-behaved submit path is exactly what would have made it misfire,
  // so the fix is to have no second path rather than a truer one.
  $('modalBackdrop').addEventListener('click', closeDialog);
  $('appDialog').addEventListener('close', () => $('modalBackdrop').classList.add('hidden'));
  $('consoleContextTitle').addEventListener('click', showManagerConsole);
}

async function boot() {
  hooks.renderAll = renderAll;
  hooks.renderDirection = renderDirection;
  hooks.renderOperation = renderOperation;
  hooks.renderConsole = renderConsole;
  hooks.selectManager = selectManager;
  hooks.selectDoc = selectDoc;
  hooks.reloadManager = reloadManager;
  hooks.reloadDoc = reloadDoc;
  wire();

  let bootData;
  try {
    bootData = await api.boot();
  } catch (err) {
    state.screen = 'home';
    renderAll();
    toast(`Could not reach the Converge service: ${err.message}`);
    return;
  }
  state.user = bootData.user || '';
  data.managerList = bootData.managers || [];
  if (!data.managerList.length) {
    state.screen = 'home';
    renderAll();
    return;
  }
  await selectManager(data.managerList[0].id);
}

if ('serviceWorker' in navigator) {
  navigator.serviceWorker.register('/sw.js').catch(() => { /* http LAN: no secure context, fine */ });
}

boot();

// Named exports keep the module testable; the app itself boots on load.
export { currentDoc };
