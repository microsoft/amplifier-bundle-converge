// "Which manager needs you?" — every manager on this machine, most needful first.
import { $, qsa, data, escapeHtml } from '../state.js';
import { hooks } from '../refresh.js';

export function renderHome() {
  const sorted = [...data.managerList].sort((a, b) => b.needs - a.needs || (a.status === 'running' ? -1 : 1));
  $('homeAttentionTotal').textContent = data.managerList.reduce((sum, m) => sum + (m.needs || 0), 0);
  $('homeSessionGrid').innerHTML = sorted.map((m) => `
      <button class="home-manager-card" data-home-manager="${escapeHtml(m.id)}" type="button">
        <div class="home-card-top">
          <div><span class="eyebrow">${escapeHtml(m.statusLabel)}</span><h2>${escapeHtml(m.name)}</h2></div>
          <span class="status-dot ${escapeHtml(m.status)}"></span>
        </div>
        <p>${escapeHtml(m.summary)}</p>
        <div class="home-card-meta">
          <div><strong>${m.needs}</strong><span>need your word</span></div>
          <div><strong>${m.lanesActive}/${m.lanesMax}</strong><span>lanes</span></div>
          <div><strong>${m.repos}</strong><span>repos</span></div>
          <div><strong>${m.projects}</strong><span>projects</span></div>
        </div>
      </button>`).join('');
  qsa('[data-home-manager]').forEach((btn) =>
    btn.addEventListener('click', () => hooks.selectManager(btn.dataset.homeManager)));
}
