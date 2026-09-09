// Shared client state + tiny DOM helpers. No data lives here: every datum comes
// from the JSON API (see api.js) and is parked on `data` for the renderers.

export const state = {
  user: '',
  managerId: null,
  screen: 'workspace',
  workspace: 'direction',
  docMode: 'read',
  repoFilter: 'all',
  repoId: null,
  docId: null,
  raw: false,
  wide: false,
  // `experience-console.v1` Core 1/7: the console is a pane beside the work,
  // never something forced on a steward before they have chosen a manager
  // session at all. Home's own working area carries no console (Core 1), so
  // the pane starts closed and only the steward's own tap (or `watchLane`)
  // opens it. Converge-t30q: it used to default open, which put a live tmux
  // pane in front of Home before a session was even picked.
  consoleOpen: false,
  consoleTab: 'terminal',
  consoleContext: 'manager',
  consoleTarget: null, // {socket, session} for the tmux viewer
  historyId: 'now',
  proposalDecision: null,
  bookmarked: false,
};

export const data = {
  managerList: [],
  manager: null,
  repoList: [],
  doc: null,
  operation: null,
  needList: [],
  // `/api/boot`'s own `config` block: which workspace roots were scanned,
  // where the config came from, and any note the server attached. Home's
  // empty-setup state (converge-t30q, acceptance 1) reads this so a steward
  // with zero manager sessions sees where the app actually looked rather than
  // an unexplained empty grid.
  config: null,
  // Set only when window.ConvergePWA.setPrincipal(user) rejects after boot
  // (converge-t30q, manager correction 3). A rejection there means identity
  // could not be verified against the authenticated boot response -- a
  // setup/identity failure, not a benign hiccup elsewhere -- so this is a
  // fail-CLOSED signal: home.js reads it to show a recovery state instead of
  // the ordinary manager grid, and boot() never lets manager/document data
  // land in `data` while it is set.
  identityError: null,
};

export const $ = (id) => document.getElementById(id);
export const qsa = (sel, root = document) => Array.from(root.querySelectorAll(sel));

export function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>'"]/g, (c) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;',
  }[c]));
}

export function currentManager() {
  return data.manager || data.managerList.find((m) => m.id === state.managerId) || data.managerList[0] || null;
}

export function currentRepo() {
  return data.repoList.find((r) => r.id === state.repoId) || data.repoList[0] || null;
}

export function currentDoc() {
  const repo = currentRepo();
  if (!repo) return null;
  return repo.docs.find((d) => d.id === state.docId) || repo.docs[0] || null;
}

export function toast(message) {
  const el = $('toast');
  if (!el) return;
  el.textContent = message;
  el.classList.remove('hidden');
  clearTimeout(toast._timer);
  toast._timer = setTimeout(() => el.classList.add('hidden'), 2800);
}

const BOOKMARK_PREFIX = 'converge:bookmark:';

export function bookmarkKey() {
  return `${BOOKMARK_PREFIX}${state.managerId}:${state.repoId}:${state.docId}`;
}

export function readBookmark() {
  try { return localStorage.getItem(bookmarkKey()) === '1'; } catch { return false; }
}

export function writeBookmark(on) {
  try { on ? localStorage.setItem(bookmarkKey(), '1') : localStorage.removeItem(bookmarkKey()); } catch { /* storage blocked */ }
}

// tmux target may arrive as {socket, session}, as the registration's combined
// "socket:session" string (a manager whose own console runs on a DIFFERENT
// socket than its worker lanes), or as a bare session name (the ordinary
// case, one socket for both) -- `defaultSocket` is what a bare name is paired
// with, and MUST be the caller's own explicit `tmuxSocket`, never an ambient
// ``$TMUX`` (there is none in a browser) or a guess. Split on the FIRST colon
// only, matching `app/config.py`'s `ManagerConfig.console_target` byte for
// byte, so a registration and this reading of it can never disagree about
// what one `manager_tmux` value names (converge-c6cv).
export function normalizeTmux(value, defaultSocket) {
  if (!value) return null;
  if (typeof value === 'string') {
    const at = value.indexOf(':');
    if (at === -1) {
      return defaultSocket ? { socket: defaultSocket, session: value } : null;
    }
    const socket = value.slice(0, at);
    const session = value.slice(at + 1);
    return socket && session ? { socket, session } : null;
  }
  return value.socket && value.session ? { socket: value.socket, session: value.session } : null;
}
