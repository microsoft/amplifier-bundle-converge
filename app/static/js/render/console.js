// Manager Console. The Terminal tab is a viewport onto a real tmux session and is
// owned by the tmux lane (window.ConvergeTmux, app/static/js/tmux.js). This module
// decides WHICH session is on screen, hands over the element, and owns the pane's
// own two behaviours: what you type reaches that session, and how wide the pane is.
//
// experience-console.v1 Core 3 — "one console, one manager session, and it IS that
// session". The manager's own session takes the keyboard; a watched lane does not,
// because the contract promises the console carries the manager conversation and
// says nothing about typing into somebody else's worker.
//
// experience-console.v1 Core 4 — "wide screen: a resizable pane". The pane is a
// grid column, so the drag handle moves the column, not the element inside it; a
// native corner grip would grow the pane off the right-hand edge instead.
import { $, qsa, state, data, escapeHtml, toast, currentManager, normalizeTmux } from '../state.js';

let attachedKey = null;

// Below this width the pane is a tray (app/static/css/console.css), and a tray
// is not dragged — the same breakpoint, named once.
const TRAY_MAX_WIDTH = 980;
const MIN_PANE = 280;
const KEY_STEP = 24;

// null means "whatever the stylesheet says"; a number is the steward's own choice.
let paneWidth = null;
let furnitureWired = false;

function managerTarget() {
  const m = data.manager || currentManager();
  if (!m) return null;
  return normalizeTmux(m.tmux || m.managerTmux || m.manager_tmux);
}

function activeTarget() {
  return state.consoleContext === 'manager' ? managerTarget() : state.consoleTarget;
}

function notice(title, body) {
  return `<div class="console-notice"><strong>${escapeHtml(title)}</strong><span>${escapeHtml(body)}</span></div>`;
}

function detach() {
  if (attachedKey && window.ConvergeTmux && typeof window.ConvergeTmux.detach === 'function') {
    window.ConvergeTmux.detach();
  }
  attachedKey = null;
}

// --------------------------------------------------------------------------
// typing: the line goes to the session, or the steward is told it did not
// --------------------------------------------------------------------------

// The form's own controls, found through the form rather than by id, so this
// module never needs to know what the markup called them.
function controls() {
  const form = document.getElementById('consoleForm');
  if (!form) return null;
  return {
    form,
    field: form.querySelector('input, textarea'),
    send: form.querySelector('button[type="submit"]'),
    note: document.querySelector('.console-readonly-note'),
  };
}

// Nothing is echoed into the pane here. The line goes to tmux; the next capture
// of the pane is what appears, so the screen can only ever show what the session
// itself did with it.
async function sendLine() {
  const c = controls();
  if (!c || !c.field) return null;
  const line = c.field.value;
  if (!line.trim()) return null;
  const tmux = window.ConvergeTmux;
  if (!tmux || typeof tmux.send !== 'function') {
    toast('The terminal viewer is not available in this build, so the line was not sent.');
    return null;
  }
  const answer = await tmux.send(line, true);
  if (answer && answer.sent) {
    c.field.value = '';
  } else {
    const why = (answer && (answer.detail || answer.state)) || 'no session is attached';
    toast(`Not delivered to ${answer && answer.session ? answer.session : 'the session'}: ${why}`);
  }
  return answer;
}

// Whether the controls are live, and what the pane says about itself. Both
// follow the same fact: is there a manager session on the other end.
function setTyping(live) {
  const c = controls();
  if (!c) return;
  if (c.field) {
    c.field.disabled = !live;
    c.field.placeholder = live ? 'Type into the manager session…' : 'Message the manager…';
  }
  if (c.send) c.send.disabled = !live;
  if (c.note) {
    c.note.textContent = live
      ? 'not a chat — this pane is the manager session itself'
      : 'read-only in this version';
  }
}

// --------------------------------------------------------------------------
// width: the pane is a grid column, so the handle moves the column
// --------------------------------------------------------------------------

function isTray() {
  return window.matchMedia(`(max-width: ${TRAY_MAX_WIDTH}px)`).matches;
}

function gridEl() {
  const pane = $('managerConsole');
  return pane ? pane.parentElement : null;
}

// The stylesheet owns the rail and the workspace; only the last track is the
// steward's to move, so the first is copied from whatever is in force right now
// (it differs by breakpoint) rather than duplicated here.
function applyWidth() {
  const grid = gridEl();
  if (!grid) return;
  if (paneWidth === null || isTray() || !state.consoleOpen) {
    grid.style.removeProperty('grid-template-columns');
    return;
  }
  const tracks = window.getComputedStyle(grid).gridTemplateColumns.split(' ');
  if (tracks.length < 3) return;
  grid.style.gridTemplateColumns = `${tracks[0]} minmax(0,1fr) ${Math.round(paneWidth)}px`;
}

function setWidth(px) {
  const max = Math.max(MIN_PANE, Math.round(window.innerWidth * 0.6));
  paneWidth = Math.min(max, Math.max(MIN_PANE, px));
  applyWidth();
}

function addHandle() {
  const pane = $('managerConsole');
  if (!pane || pane.querySelector('.console-resize')) return;
  const handle = document.createElement('div');
  handle.className = 'console-resize';
  handle.setAttribute('role', 'separator');
  handle.setAttribute('aria-orientation', 'vertical');
  handle.setAttribute('aria-label', 'Drag to resize the console');
  handle.tabIndex = 0;

  let dragging = false;
  handle.addEventListener('pointerdown', (e) => {
    if (isTray()) return;
    dragging = true;
    handle.setPointerCapture(e.pointerId);
    document.body.classList.add('console-resizing');
    e.preventDefault();
  });
  handle.addEventListener('pointermove', (e) => {
    if (!dragging) return;
    // The pane is docked right: its width is the distance from the pointer to
    // the window's right edge.
    setWidth(window.innerWidth - e.clientX);
  });
  const stop = (e) => {
    if (!dragging) return;
    dragging = false;
    try { handle.releasePointerCapture(e.pointerId); } catch { /* already released */ }
    document.body.classList.remove('console-resizing');
  };
  handle.addEventListener('pointerup', stop);
  handle.addEventListener('pointercancel', stop);
  // Draggable is not the same as reachable: the same move from the keyboard.
  handle.addEventListener('keydown', (e) => {
    if (isTray()) return;
    if (e.key !== 'ArrowLeft' && e.key !== 'ArrowRight') return;
    const pane2 = $('managerConsole');
    const now = paneWidth === null ? pane2.getBoundingClientRect().width : paneWidth;
    setWidth(now + (e.key === 'ArrowLeft' ? KEY_STEP : -KEY_STEP));
    e.preventDefault();
  });

  pane.insertBefore(handle, pane.firstChild);
}

// Once, on first render: the pane's own furniture and its own listeners.
function wireFurniture() {
  if (furnitureWired) return;
  furnitureWired = true;
  addHandle();
  const c = controls();
  if (c && c.field) {
    c.field.addEventListener('keydown', (e) => {
      if (e.key !== 'Enter' || e.shiftKey) return;
      e.preventDefault();   // never a form submit: the send is ours
      sendLine();
    });
  }
  if (c && c.send) {
    c.send.addEventListener('click', (e) => {
      e.preventDefault();
      sendLine();
    });
  }
  // A tray is not dragged, and a dragged width must not survive into one.
  window.matchMedia(`(max-width: ${TRAY_MAX_WIDTH}px)`).addEventListener('change', applyWidth);
}

export function renderConsole() {
  const grid = $('managerConsole').parentElement;
  grid.classList.toggle('console-closed', !state.consoleOpen);
  $('consoleToggle').setAttribute('aria-pressed', state.consoleOpen ? 'true' : 'false');
  $('consoleToggle').classList.toggle('active', state.consoleOpen);
  wireFurniture();
  applyWidth();

  const isManager = state.consoleContext === 'manager';
  const label = isManager ? `manager-${state.managerId}` : state.consoleContext;
  const target = activeTarget();
  // The keyboard belongs to the manager's own session, and only while its
  // terminal is the thing on screen.
  const typing = isManager && !!target && state.consoleTab === 'terminal' && !!window.ConvergeTmux;
  setTyping(typing);
  $('consoleContextTitle').textContent = label;
  $('consoleFooterText').textContent = target
    ? `Attached to tmux: ${target.socket}:${target.session}`
    : (isManager ? 'manager session is not in tmux' : 'this lane is not in tmux');
  $('consoleConnected').textContent = target && window.ConvergeTmux ? '● Connected' : '● Detached';
  $('consoleConnected').classList.toggle('detached', !(target && window.ConvergeTmux));
  qsa('[data-console-tab]').forEach((btn) => btn.classList.toggle('active', btn.dataset.consoleTab === state.consoleTab));

  const body = $('consoleBody');

  if (state.consoleTab === 'notes') {
    detach();
    const m = currentManager();
    body.innerHTML = m
      ? `<div class="context-note"><strong>Objective</strong><p>${escapeHtml(m.objective)}</p></div>
         <div class="context-note"><strong>Where it stands</strong><p>${escapeHtml(m.summary)}</p></div>
         <div class="context-note"><strong>Registered scope</strong><p>${m.repos} repositories · ${m.projects} tracker projects · ${m.lanesActive} active lanes.</p></div>
         <div class="context-note"><strong>Strategy</strong><p>${escapeHtml(m.strategyNarrative)}</p></div>`
      : '<div class="context-note"><strong>No manager selected</strong><p>Choose a manager session to see its context.</p></div>';
    attachedKey = 'notes';
    return;
  }

  if (!target) {
    detach();
    body.innerHTML = notice(
      isManager ? 'manager session is not in tmux' : 'this lane is not in tmux',
      'There is no live session to watch from here.',
    );
    attachedKey = 'no-target';
    return;
  }

  if (!window.ConvergeTmux) {
    detach();
    body.innerHTML = notice('terminal viewer not loaded', `Session ${target.socket}:${target.session} is running; the terminal viewer is not available in this build.`);
    attachedKey = 'no-viewer';
    return;
  }

  const key = `tmux:${target.socket}:${target.session}:${typing ? 'rw' : 'ro'}`;
  if (key === attachedKey) return;
  detach();
  body.innerHTML = '<div id="terminalHost" class="terminal-host"></div>';
  window.ConvergeTmux?.attach($('terminalHost'), target.socket, target.session, { writable: typing });
  attachedKey = key;
}

export function watchLane(laneId) {
  const laneRows = (data.operation && data.operation.lanes) || [];
  const lane = laneRows.find((l) => String(l.id) === String(laneId));
  if (!lane) return;
  state.consoleOpen = true;
  state.consoleContext = `lane-${lane.id}`;
  state.consoleTarget = normalizeTmux(lane.tmux);
  state.consoleTab = 'terminal';
  renderConsole();
  toast(`Watching ${lane.title}`);
}

export function showManagerConsole() {
  state.consoleContext = 'manager';
  state.consoleTarget = null;
  renderConsole();
}
