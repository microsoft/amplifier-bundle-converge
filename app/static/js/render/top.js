// Topbar chrome, the manager session rail, and the manager picker menu.
import { $, qsa, state, data, escapeHtml, currentManager } from '../state.js';
import { hooks } from '../refresh.js';

export function renderTop() {
  const m = currentManager();
  $('managerNameTop').textContent = m ? m.name : '—';
  $('managerStatusTop').textContent = m ? m.statusLabel : '';
  const dot = $('managerSelectButton').querySelector('.status-dot');
  dot.className = `status-dot ${m ? m.status : ''}`;
  $('needsYouCount').textContent = m ? m.needs : 0;
  $('needsYouButton').classList.toggle('hidden', state.screen === 'home' || !m || !m.needs);
  $('objectiveText').textContent = m ? m.objective : '';
  $('opObjectiveText').textContent = m ? m.objective : '';
  $('deadlineText').textContent = m && m.deadline ? m.deadline : 'No hard deadline';
  $('strategyShort').textContent = m ? m.strategy : '—';
  $('lanesShort').textContent = m ? `${m.lanesMax} max` : '—';

  $('homeView').classList.toggle('hidden', state.screen !== 'home');
  $('directionView').classList.toggle('hidden', !(state.screen === 'workspace' && state.workspace === 'direction'));
  $('operationView').classList.toggle('hidden', !(state.screen === 'workspace' && state.workspace === 'operation'));
  $('workspaceSwitch').classList.toggle('hidden', state.screen === 'home');
  $('managerCrumb').classList.toggle('hidden', state.screen === 'home');

  $('directionTab').classList.toggle('active', state.workspace === 'direction');
  $('directionTab').setAttribute('aria-selected', state.workspace === 'direction' ? 'true' : 'false');
  $('operationTab').classList.toggle('active', state.workspace === 'operation');
  $('operationTab').setAttribute('aria-selected', state.workspace === 'operation' ? 'true' : 'false');
}

// --------------------------------------------------------------------------
// the workspace rail: narrow rows, not a second set of Home's cards
// --------------------------------------------------------------------------
//
// Manager correction 1 (converge-t30q): this used to redraw Home's own rich
// card -- name, age, summary paragraph, a 2-up metrics grid, a resources
// line -- once per manager, on every screen, all the time. That is a
// required compact rail duplicating a required full card, not a choice
// between them (shell-inbox.md acceptance 2: "do not duplicate expanded
// cards in every place"). So the row here carries only what a narrow rail
// needs to answer "which one, and does it need me": the manager's own name,
// a status dot with its word, and a needs badge when something is waiting.
// Everything Home's card already shows in full -- summary, lanes, repos,
// projects -- stays reachable through a native <details> so it is still
// there, accessibly, on demand rather than gone.
export function renderSessions() {
  $('sessionList').innerHTML = data.managerList.map((m) => {
    const active = m.id === state.managerId && state.screen === 'workspace';
    const needs = Number(m.needs) || 0;
    return `
      <div class="session-row ${active ? 'active' : ''}">
        <button class="session-row-main" data-manager-id="${escapeHtml(m.id)}" type="button" title="${escapeHtml(m.name)} \u2014 ${escapeHtml(m.statusLabel)}">
          <span class="session-row-name">${escapeHtml(m.name)}</span>
          <span class="session-row-badges">
            <span class="status-dot ${escapeHtml(m.status)}" aria-hidden="true"></span>
            <span class="session-row-status">${escapeHtml(m.statusLabel)}</span>
            ${needs > 0 ? `<span class="needs-badge" title="${needs} need your word">${needs}</span>` : ''}
          </span>
        </button>
        <details class="session-row-detail">
          <summary>Details</summary>
          <p class="session-row-summary">${escapeHtml(m.summary)}</p>
          <div class="session-row-metrics">
            <span>${m.lanesActive} / ${m.lanesMax} lanes</span>
            <span>${m.repos} repos</span>
            <span>${m.projects} projects</span>
          </div>
        </details>
      </div>`;
  }).join('');
  qsa('[data-manager-id]', $('sessionList')).forEach((btn) =>
    btn.addEventListener('click', () => hooks.selectManager(btn.dataset.managerId)));
}

export function renderManagerMenu() {
  $('managerMenu').innerHTML = data.managerList.map((m) => `
      <button type="button" role="option" data-menu-manager="${escapeHtml(m.id)}"><span><strong>${escapeHtml(m.name)}</strong><br><span class="muted">${escapeHtml(m.summary)}</span></span><span class="status-dot ${escapeHtml(m.status)}"></span></button>`).join('');
  qsa('[data-menu-manager]').forEach((btn) => btn.addEventListener('click', () => {
    $('managerMenu').classList.add('hidden');
    hooks.selectManager(btn.dataset.menuManager);
  }));
}
