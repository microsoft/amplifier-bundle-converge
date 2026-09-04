// "Which manager needs you?" — every manager on this machine, most needful first.
import { $, qsa, data, escapeHtml, toast } from '../state.js';
import { hooks } from '../refresh.js';
import { openDialog, closeDialog } from '../actions.js';
import { api } from '../api.js';

// --------------------------------------------------------------------------
// Core 13's second half, on the surface that draws the list
// --------------------------------------------------------------------------
//
// `experience.v1` Core 1 puts the list of manager sessions on Home;
// `experience-operation.v1` Core 13 asks that one message can reach every
// session in it. converge-q66 supplied the control on the Operation surface,
// which left a steward standing in front of the list itself with no control on
// it (converge-are).
//
// This is deliberately the SAME control, not a second kind of one: the same
// title, the same words, and one feedback write per manager session — the same
// write the Feedback button makes for one. `experience.v1` §11's transfer test
// is the reason: a steward who learned "Tell all manager sessions" on Operation
// must find it here doing the same thing, or the two surfaces have diverged.
// It is written out here rather than imported because the Operation renderer is
// another lane's file; if the two ever have to move together, one of them
// should be lifted into a shared module rather than quietly drift.
function tellAllSessions() {
  const sessions = data.managerList || [];
  if (!sessions.length) { toast('No manager session is listed yet.'); return; }
  openDialog('Tell all manager sessions', 'Feedback', `
      <div class="dialog-field"><label for="homeTellAllText">One message, delivered to every manager session you run</label><textarea id="homeTellAllText" placeholder="Stop starting new work until the release lands…"></textarea></div>
      <p class="muted">Reaches ${sessions.length} manager session${sessions.length === 1 ? '' : 's'}: ${escapeHtml(sessions.map((s) => s.name).join(', '))}.</p>`, [
    { label: 'Cancel', kind: 'outline', action: closeDialog },
    {
      label: 'Tell them all',
      kind: 'primary',
      action: async () => {
        const text = $('homeTellAllText') ? $('homeTellAllText').value.trim() : '';
        if (!text) { toast('Write the message first.'); return; }
        closeDialog();
        const failed = [];
        for (const one of sessions) {
          try {
            await api.feedback(one.id, { text, context: `${one.name} · told with every manager session` });
          } catch (err) {
            failed.push(`${one.name}: ${err.message}`);
          }
        }
        // What landed and what did not, by name. A message that reached three
        // of four sessions is not "delivered", and saying so is the only way a
        // steward knows to say it again to the one that missed it.
        toast(failed.length
          ? `Reached ${sessions.length - failed.length} of ${sessions.length}. Not reached — ${failed.join('; ')}`
          : `Delivered to all ${sessions.length} manager session${sessions.length === 1 ? '' : 's'}.`);
      },
    },
  ]);
}

//: renderHome runs on every re-render, so the listener is attached once and
//: marked, the way the Operation surface wires its own drop.
function wireTellAll() {
  const button = $('homeTellAllButton');
  if (!button || button.dataset.wired) return;
  button.dataset.wired = '1';
  button.addEventListener('click', tellAllSessions);
}

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
  wireTellAll();
}
