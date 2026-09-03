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
  consoleOpen: true,
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

// tmux target may arrive as {socket, session} or as the config's "socket:session".
export function normalizeTmux(value) {
  if (!value) return null;
  if (typeof value === 'string') {
    const [socket, session] = value.split(':');
    return socket && session ? { socket, session } : null;
  }
  return value.socket && value.session ? { socket: value.socket, session: value.session } : null;
}
