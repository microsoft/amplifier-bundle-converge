// Manager Console. The Terminal tab is a viewport onto a real tmux session and is
// owned by the tmux lane (window.ConvergeTmux, app/static/js/tmux.js). This module
// only decides WHICH session is on screen and hands over the element.
// Read-only in this version: there is no send-keys path.
import { $, qsa, state, data, escapeHtml, toast, currentManager, normalizeTmux } from '../state.js';

let attachedKey = null;

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

export function renderConsole() {
  const grid = $('managerConsole').parentElement;
  grid.classList.toggle('console-closed', !state.consoleOpen);
  $('consoleToggle').setAttribute('aria-pressed', state.consoleOpen ? 'true' : 'false');
  $('consoleToggle').classList.toggle('active', state.consoleOpen);

  const isManager = state.consoleContext === 'manager';
  const label = isManager ? `manager-${state.managerId}` : state.consoleContext;
  const target = activeTarget();
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

  const key = `tmux:${target.socket}:${target.session}`;
  if (key === attachedKey) return;
  detach();
  body.innerHTML = '<div id="terminalHost" class="terminal-host"></div>';
  window.ConvergeTmux?.attach($('terminalHost'), target.socket, target.session);
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
