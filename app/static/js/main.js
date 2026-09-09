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
import { refreshCollab } from './render/collab.js';
import {
  openFeedback, openSteer, fillLanes, closeDialog, downloadCurrentDoc, copyText, toggleBookmark, openNeeds,
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
  // A failed fetch below must never leave the screen showing manager B's
  // chrome (the new `id` is already in the title) over manager A's content
  // (the old `data.manager`/`data.doc`) -- acceptance 1's "failed fetch never
  // mixes old content with new title" (converge-t30q). So the previous
  // screen is kept until the reads actually land, and restored, unchanged, on
  // failure -- nothing above this line is committed to `state` yet.
  let manager;
  let operation;
  try {
    [manager, operation] = await Promise.all([api.manager(id), api.operation(id)]);
  } catch (err) {
    toast(`Could not open that manager: ${err.message}`);
    return;
  }
  state.managerId = id;
  state.screen = 'workspace';
  // `experience.v1` Core 1/2: opening a manager session is opening its
  // Operation -- the manager at work -- with Direction an obvious peer tab
  // away, never the other way around (converge-t30q, acceptance 1).
  state.workspace = 'operation';
  state.consoleContext = 'manager';
  state.consoleTarget = null;
  state.proposalDecision = null;
  state.historyId = 'now';
  data.manager = manager;
  data.repoList = manager.repositories || [];
  data.operation = operation;
  pickDoc();
  await loadDoc(); // toasts and leaves data.doc null on its own failure; never throws
  renderAll();
  // `collab.js`'s singleton mount starts while no manager is selected, so its
  // first read can belong to a different manager. Refresh the committed
  // selection without awaiting the host: navigation remains responsive while
  // the existing module's own guarded refresh updates its panel.
  void refreshCollab();
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

// A listener wired against an element another lane's markup may remove.
// `experience.v1` acceptance 5 (converge-t30q) asks that a reader-owned
// element's removal not throw here: `$(id)` already answers `null` for a
// missing element, so this is the one place that has to check before calling
// `addEventListener` on it. A removed element used to be a boot-time
// TypeError that took every other listener in `wire()` down with it.
function on(id, event, handler) {
  const el = $(id);
  if (el) el.addEventListener(event, handler);
}

function wire() {
  on('brandHome', 'click', showHome);
  on('allSessionsButton', 'click', showHome);
  on('directionTab', 'click', () => { state.screen = 'workspace'; state.workspace = 'direction'; renderAll(); });
  on('operationTab', 'click', () => { state.screen = 'workspace'; state.workspace = 'operation'; renderAll(); });
  // The needs pill opens the decision inbox dialog -- up to five named
  // choices, each with where it applies and what answering it does -- rather
  // than jumping straight to the first document and guessing the rest
  // (`experience.v1` Core 5, converge-t30q acceptance 4). `openNeeds` is
  // shell's own dialog code, in `actions.js`, beside every other write and
  // dialog this file owns.
  on('needsYouButton', 'click', openNeeds);
  on('feedbackButton', 'click', openFeedback);
  on('consoleToggle', 'click', () => {
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
  on('consoleClose', 'click', () => { state.consoleOpen = false; renderConsole(); reflectConsoleControl(); });
  on('managerSelectButton', 'click', () => { const menu = $('managerMenu'); if (menu) menu.classList.toggle('hidden'); });
  document.addEventListener('click', (e) => {
    const menu = $('managerMenu');
    if (menu && !e.target.closest('#managerMenu') && !e.target.closest('#managerSelectButton')) menu.classList.add('hidden');
  });
  on('repoFilter', 'change', (e) => { state.repoFilter = e.target.value; renderDirection(); });
  qsa('[data-doc-mode]').forEach((btn) => btn.addEventListener('click', () => { state.docMode = btn.dataset.docMode; renderDirection(); }));
  on('showChangesShortcut', 'click', () => { state.docMode = 'changes'; renderDirection(); });
  on('wideToggle', 'click', () => { state.wide = !state.wide; renderDirection(); });
  on('rawToggle', 'click', () => { state.raw = !state.raw; state.docMode = 'read'; renderDirection(); });
  on('copyRendered', 'click', () => copyText(data.doc ? data.doc.raw || '' : ''));
  on('downloadDoc', 'click', downloadCurrentDoc);
  on('bookmarkButton', 'click', toggleBookmark);
  qsa('[data-nav-special]').forEach((btn) => btn.addEventListener('click', () => {
    const kind = btn.dataset.navSpecial;
    if (kind === 'changes') state.docMode = 'changes';
    if (kind === 'proposals') state.docMode = 'review';
    if (kind === 'decisions') state.docMode = 'history';
    renderDirection();
  }));
  on('steerButton', 'click', openSteer);
  on('timelineButton', 'click', () => { const card = $('timelineCard'); if (card) card.classList.remove('hidden'); });
  on('closeTimelineButton', 'click', () => { const card = $('timelineCard'); if (card) card.classList.add('hidden'); });
  on('fillLanesButton', 'click', fillLanes);
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
  on('modalBackdrop', 'click', closeDialog);
  on('appDialog', 'close', () => { const b = $('modalBackdrop'); if (b) b.classList.add('hidden'); });
  on('consoleContextTitle', 'click', showManagerConsole);
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
  // preview-common.md, Shared interfaces section: PWA owns
  // `window.ConvergePWA.setPrincipal(user)` and shell awaits it, when
  // present, after `/api/boot` and before any manager or document read --
  // PWA validates identity against this authenticated boot response, not an
  // untrusted claim, so it has to run before this session reads anything
  // that principal might gate. Absent in a build without the PWA lane's
  // code, which is a normal shape, not a defect.
  if (window.ConvergePWA && typeof window.ConvergePWA.setPrincipal === 'function') {
    try {
      await window.ConvergePWA.setPrincipal(state.user);
    } catch (err) {
      // Manager correction 3 (converge-t30q): a rejection here means the
      // identity check itself failed, not some unrelated lane's hiccup --
      // continuing past it used to read manager/document data with an
      // unverified principal, a fail-OPEN path into sensitive cached reads.
      // Fail closed instead: clear anything already loaded, stay on Home
      // (never a screen that assumes a verified identity), and give a real
      // recovery action rather than a dead-end toast that vanishes in 2.8s.
      data.managerList = [];
      data.manager = null;
      data.repoList = [];
      data.doc = null;
      data.operation = null;
      data.config = null;
      data.identityError = err && err.message ? err.message : 'Identity check failed.';
      state.managerId = null;
      state.screen = 'home';
      renderAll();
      return;
    }
  }
  data.identityError = null;
  data.managerList = bootData.managers || [];
  data.config = bootData.config || null;
  // `experience.v1` Core 1 (converge-t30q, acceptance 1): boot lands on
  // Home, the list of manager sessions sorted by which needs you -- never an
  // arbitrarily first-picked manager. Zero, one, or many managers all draw
  // the same screen; `render/home.js` is what tells them apart, with an
  // honest setup state when the list is empty.
  state.screen = 'home';
  renderAll();
}

if ('serviceWorker' in navigator) {
  // Publish the registration's OUTCOME, not merely fire it. `offline.js` cannot
  // otherwise tell "this browser will never give us a worker" (blocked by
  // policy, no secure context) from "a worker is on its way, or exists and is
  // not answering" -- and the difference decides whether an ordinary online
  // boot may proceed or must fail closed. Resolving to `null` on failure keeps
  // this a SETTLED observation rather than an unhandled rejection; the promise
  // is deliberately not awaited, so boot() is never delayed by it.
  window.ConvergePWA = window.ConvergePWA || {};
  window.ConvergePWA.registration = navigator.serviceWorker
    .register('/sw.js')
    .then((reg) => reg || null)
    .catch(() => null); // http LAN: no secure context, fine
}

boot();

// Named exports keep the module testable; the app itself boots on load.
export { currentDoc };
