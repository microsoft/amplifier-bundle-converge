// the manager list, in whatever order it arrived
import { $, data, escapeHtml } from '../state.js';

export function renderHome() {
  $('homeSessionGrid').innerHTML = data.managerList.map((m) => `
      <button class="home-manager-card" type="button"><h2>${escapeHtml(m.name)}</h2></button>`).join('');
}
