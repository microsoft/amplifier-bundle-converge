// "Which manager needs you?" — every manager, most needful first.
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
