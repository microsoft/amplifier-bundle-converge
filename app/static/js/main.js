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

export function renderAll() {
  renderTop();
  renderSessions();
  renderHome();
  renderDirection();
  renderOperation();
  renderConsole();
  renderManagerMenu();
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
  $('needsYouButton').addEventListener('click', () => { state.screen = 'workspace'; state.workspace = 'direction'; state.docMode = 'review'; renderAll(); });
  $('feedbackButton').addEventListener('click', openFeedback);
  $('consoleToggle').addEventListener('click', () => { state.consoleOpen = !state.consoleOpen; renderConsole(); });
  $('consoleClose').addEventListener('click', () => { state.consoleOpen = false; renderConsole(); });
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
  $('consoleForm').addEventListener('submit', (e) => { e.preventDefault(); toast('The console is read-only in this version.'); });
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
