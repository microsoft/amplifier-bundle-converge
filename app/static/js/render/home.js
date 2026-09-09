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

// --------------------------------------------------------------------------
// whose word counts, and whether anybody is still listening
// --------------------------------------------------------------------------
//
// `experience.v1` Core 1 says Home shows, for each manager session, how many
// things want your word, lanes running against lanes intended, the last brief
// line, and "quiet or silent". The last of those is the registration's own
// heartbeat, read by `app/data.py`'s `manager_presence`, and it is a different
// reading from the card's status: status says whether the WORK needs a person,
// presence says whether the SESSION is still waking up at all.
//
// A manager with no registration carries an empty `presence`, and then nothing
// is drawn. Never having registered is not the same as having gone quiet, and
// a card that showed silence for it would be claiming something nothing here
// knows.
//
// Both facts share ONE line, because `shell.css` gives every `<p>` inside a
// card a 16px foot and three stacked paragraphs push the meta tiles off a
// phone. That file belongs to another lane, so the markup bends instead.
function registrationLine(m) {
  // `experience-collaboration.v1` Core 8 - whose word counts on this session,
  // settled at registration. Empty when the registration named nobody, and
  // then the card says exactly that rather than the reader's own name.
  const steward = m.steward
    ? `Steward: ${escapeHtml(m.steward)}`
    : 'No steward named in this session&rsquo;s registration';
  const presence = m.presenceLabel
    ? ` &middot; <span class="home-card-presence ${escapeHtml(m.presence)}">${escapeHtml(m.presenceLabel)}</span>`
    : '';
  return `<p class="muted home-card-registration">${steward}${presence}</p>`;
}

//: One row per manager, saying where it came from and when it was last awake.
//: `origin` is written by `app/config.py`, which is the only place that knows.
function renderOriginFold(sessions) {
  const body = $('homeOriginBody');
  if (!body) return;
  if (!sessions.length) {
    body.innerHTML = '<p class="muted">No manager session is listed yet, so there is nothing to say where anything came from.</p>';
    return;
  }
  body.innerHTML = sessions.map((m) => `
      <p><strong>${escapeHtml(m.name)}</strong> &mdash; ${escapeHtml(m.origin || 'origin not recorded')}.
      ${m.lastSeen ? `Last awake ${escapeHtml(m.lastSeen)}.` : 'Never registered, so nothing here says when it was last awake.'}
      ${m.workspace ? `Workspace root <code>${escapeHtml(m.workspace)}</code>.` : ''}</p>`).join('');
}

// --------------------------------------------------------------------------
// zero managers: a usable next action, not a silently empty grid
// --------------------------------------------------------------------------
//
// `experience.v1` acceptance 1 (converge-t30q): with no manager session
// registered, Home must say a usable next action and name the actual
// workspace roots `/api/boot` scanned (`data.config.workspaces`), including
// an explicit remedy when one is missing -- never an unexplained blank grid.
function emptySetupHtml(cfg) {
  const roots = (cfg && cfg.workspaces) || [];
  const note = (cfg && cfg.note) || '';
  return `
    <div class="home-empty-setup">
      <span class="eyebrow">Setup</span>
      <h2>No manager session found yet</h2>
      <p>This app looked for a session&rsquo;s own registration in
        ${roots.length} workspace root${roots.length === 1 ? '' : 's'} and found none.</p>
      ${roots.length
    ? `<ul>${roots.map((r) => `<li><code>${escapeHtml(r)}</code></li>`).join('')}</ul>`
    : '<p class="muted">No workspace roots are configured to scan at all &mdash; that is the remedy: add one to converge-app.toml.</p>'}
      <p class="muted">${escapeHtml(note) || 'Start a manager session in one of the roots above (or a root you add), then reload this page.'}</p>
    </div>`;
}

// --------------------------------------------------------------------------
// identity check failed: fail closed, never a silent continue (correction 3)
// --------------------------------------------------------------------------
//
// `data.identityError` is set only when `window.ConvergePWA.setPrincipal`
// rejected after boot (main.js). That is a setup/identity failure, not an
// empty manager list, so it gets its own honest card rather than being read
// as "no manager session found yet" -- and a real recovery action, since
// reloading is the one thing that re-runs the identity check from scratch.
function identityFailureHtml(message) {
  return `
    <div class="home-empty-setup home-identity-failure">
      <span class="eyebrow">Identity check failed</span>
      <h2>Your session could not be verified</h2>
      <p>${escapeHtml(message || 'The identity check after boot did not complete.')}</p>
      <p class="muted">Nothing cached was shown, and no manager or document data was read.
        Reload to try the check again.</p>
      <button type="button" class="primary-button" id="identityRetryButton">Reload and try again</button>
    </div>`;
}

function wireIdentityRetry() {
  const btn = $('identityRetryButton');
  if (!btn || btn.dataset.wired) return;
  btn.dataset.wired = '1';
  btn.addEventListener('click', () => window.location.reload());
}

export function renderHome() {
  if (data.identityError) {
    $('homeAttentionTotal').textContent = '0';
    $('homeSessionGrid').innerHTML = identityFailureHtml(data.identityError);
    renderOriginFold([]);
    wireTellAll();
    wireIdentityRetry();
    return;
  }
  const sorted = [...data.managerList].sort((a, b) => b.needs - a.needs || (a.status === 'running' ? -1 : 1));
  $('homeAttentionTotal').textContent = data.managerList.reduce((sum, m) => sum + (m.needs || 0), 0);
  if (!sorted.length) {
    $('homeSessionGrid').innerHTML = emptySetupHtml(data.config);
    renderOriginFold(sorted);
    wireTellAll(); // safe with zero sessions: tellAllSessions() itself toasts and stops
    return;
  }
  $('homeSessionGrid').innerHTML = sorted.map((m) => `
      <button class="home-manager-card" data-home-manager="${escapeHtml(m.id)}" type="button">
        <div class="home-card-top">
          <div><span class="eyebrow">${escapeHtml(m.statusLabel)}</span><h2>${escapeHtml(m.name)}</h2></div>
          <span class="status-dot ${escapeHtml(m.status)}"></span>
        </div>
        <p>${escapeHtml(m.summary)}</p>
        ${registrationLine(m)}
        <div class="home-card-meta">
          <div><strong>${m.needs}</strong><span>need your word</span></div>
          <div><strong>${m.lanesActive}/${m.lanesMax}</strong><span>lanes</span></div>
          <div><strong>${m.repos}</strong><span>repos</span></div>
          <div><strong>${m.projects}</strong><span>projects</span></div>
        </div>
      </button>`).join('');
  qsa('[data-home-manager]').forEach((btn) =>
    btn.addEventListener('click', () => hooks.selectManager(btn.dataset.homeManager)));
  renderOriginFold(sorted);
  wireTellAll();
}
