// Fetch wrappers for every endpoint in the app contract. A 401 sends the browser
// to /login: the cookie gate is the backend's, this only obeys it.

async function request(url, options = {}) {
  const res = await fetch(url, {
    credentials: 'same-origin',
    headers: options.body ? { 'Content-Type': 'application/json' } : undefined,
    ...options,
  });
  if (res.status === 401) {
    location.href = `/login?next=${encodeURIComponent(location.pathname + location.search)}`;
    throw new Error('unauthenticated');
  }
  if (!res.ok) {
    // The writers in app/writes.py refuse in plain words — "that sentence is no
    // longer in the file as it was written" — and those words are the whole
    // reason a caller can tell a collision from a typo. Throwing only the
    // status threw that away, so the sentence is carried out with the error.
    let said = '';
    try {
      const body = await res.json();
      said = (body && (body.error || body.detail)) || '';
    } catch { /* the refusal was not JSON: the status is all there is */ }
    const refusal = new Error(said || `${options.method || 'GET'} ${url} → ${res.status}`);
    refusal.status = res.status;
    refusal.said = said;
    throw refusal;
  }
  return marked(await res.json(), res);
}

// platform-web.v1 §10: what is shown while the network is down is "marked with
// the moment it came from". `app/static/sw.js` already puts that moment on
// every stored payload (`X-Converge-Synced-At`) and re-serves it with
// `X-Converge-Offline: 1`; both headers are readable here because the response
// is same-origin. Reading them off the very response a screen was drawn from is
// what lets a document carry its own mark beside its own title, rather than the
// steward having to look at the banner in the corner (converge-baz).
//
// Nothing is attached to a payload that came from the server just now, so a
// screen on a live network is unchanged.
const FROM_STORE = 'X-Converge-Offline';
const SYNCED_AT = 'X-Converge-Synced-At';

function marked(payload, res) {
  if (!res.headers.get(FROM_STORE)) return payload;
  if (!payload || typeof payload !== 'object' || Array.isArray(payload)) return payload;
  payload.storedCopy = { syncedAt: res.headers.get(SYNCED_AT) || '' };
  return payload;
}

const post = (url, payload) => request(url, { method: 'POST', body: JSON.stringify(payload) });

const docBase = (mid, repoId, docId) =>
  `/api/managers/${encodeURIComponent(mid)}/docs/${encodeURIComponent(repoId)}/${encodeURIComponent(docId)}`;

export const api = {
  boot: () => request('/api/boot'),
  manager: (mid) => request(`/api/managers/${encodeURIComponent(mid)}`),
  doc: (mid, repoId, docId) =>
    request(`/api/managers/${encodeURIComponent(mid)}/docs/${encodeURIComponent(repoId)}/${encodeURIComponent(docId)}`),
  operation: (mid) => request(`/api/managers/${encodeURIComponent(mid)}/operation`),
  needs: (mid) => request(`/api/needs/${encodeURIComponent(mid)}`),
  decision: (mid, payload) => post(`/api/managers/${encodeURIComponent(mid)}/decision`, payload),
  feedback: (mid, payload) => post(`/api/managers/${encodeURIComponent(mid)}/feedback`, payload),
  steer: (mid, payload) => post(`/api/managers/${encodeURIComponent(mid)}/steer`, payload),
  markRead: (mid, repoId, docId) => post(`${docBase(mid, repoId, docId)}/read`, {}),
  keepChange: (mid, repoId, docId, changeId, kept) =>
    post(`${docBase(mid, repoId, docId)}/changes/${encodeURIComponent(changeId)}/keep`, { kept }),
  editChange: (mid, repoId, docId, changeId, text) =>
    post(`${docBase(mid, repoId, docId)}/changes/${encodeURIComponent(changeId)}/edit`, { text }),
  restoreChange: (mid, repoId, docId, changeId) =>
    post(`${docBase(mid, repoId, docId)}/changes/${encodeURIComponent(changeId)}/restore`, {}),
  // Presence (§10) — who has an editor open on which section, right now.
  // Courtesy only: none of these three refuses anything, and there is no route
  // here that could. The beat both refreshes and releases (an empty section is
  // goodbye), so a browser cannot forget to say it is done.
  presenceBeat: (mid, payload) => post(`/api/managers/${encodeURIComponent(mid)}/presence`, payload),
  presenceHere: (mid, repoId, docId) =>
    request(`/api/managers/${encodeURIComponent(mid)}/presence`
      + `?repoId=${encodeURIComponent(repoId)}&docId=${encodeURIComponent(docId)}`),
  // The manager session's half: ask before writing, and be told to wait.
  presenceQueue: (mid, payload) => post(`/api/managers/${encodeURIComponent(mid)}/presence/queue`, payload),
  // Ask — the fifth write the umbrella names. One route for all three scopes,
  // because the scope is a fact about the request rather than a different
  // request. What comes back is a proposal to review.
  //
  // The app answers this route: converge-ddt landed in `app/serve.py` and
  // `app/writes.py` (48cdc90). So a failure here is no longer evidence of a
  // missing route, and `sendAsk` no longer says it is (converge-3al) — it
  // reports whatever refused, in that refuser's own words.
  ask: (mid, payload) => post(`/api/managers/${encodeURIComponent(mid)}/ask`, payload),
  // Lock — stamping a document's H1 so it becomes law (§11). The gate in the
  // browser decides whether the control is live; the write itself is the
  // server's, because the H1 is a file and `app/writes.py` is the only place
  // that touches one.
  //
  // The app does not answer this route yet: `app/serve.py` and `app/writes.py`
  // are another lane's files, and the server half is filed as converge-eci.
  // Same choice as `ask` above — the call points at the real route so it fails
  // out loud and the screen says so, rather than a control that ticks four
  // boxes and quietly changes nothing.
  lock: (mid, repoId, docId, payload) => post(`${docBase(mid, repoId, docId)}/lock`, payload),
};
