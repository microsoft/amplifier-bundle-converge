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

export function renderSessions() {
  $('sessionList').innerHTML = data.managerList.map((m) => `
      <button class="session-card ${m.id === state.managerId && state.screen === 'workspace' ? 'active' : ''}" data-manager-id="${escapeHtml(m.id)}" type="button">
        <div class="session-topline"><span class="session-name">${escapeHtml(m.name)}</span><span class="session-age">${escapeHtml(m.age)}</span></div>
        <div class="session-summary">${escapeHtml(m.summary)}</div>
        <div class="session-status-line"><span class="status-dot ${escapeHtml(m.status)}"></span><strong class="${escapeHtml(m.status)}">${escapeHtml(m.statusLabel)}</strong></div>
        <div class="session-metrics">
          <div class="session-metric"><strong>${m.needs}</strong><span>Need your word</span></div>
          <div class="session-metric"><strong>${m.lanesActive} / ${m.lanesMax}</strong><span>Lanes active</span></div>
        </div>
        <div class="session-resources"><span>${m.repos} repos</span><span>${m.projects} projects</span></div>
      </button>`).join('');
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
