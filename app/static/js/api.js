// Fetch wrappers for every endpoint in the app contract. A 401 sends the browser
// to /login: the cookie gate is the backend's, this only obeys it.

// The double-submit CSRF cookie (`app/auth.py`'s CSRF_COOKIE) is deliberately
// readable by JS, unlike the session cookie -- this is the one place that
// reads it back out, so every unsafe request echoes it as a header. A
// cross-site page can make the browser SEND the cookie but cannot READ its
// value to forge this header, which is the whole of what the check proves.
//
// The cookie's NAME is not always `cv_csrf`: a preview started with its own
// `--instance-dir` gets a namespaced name instead, so that two preview
// instances on one host (cookies are never scoped by port) never read or
// clobber each other's CSRF cookie (converge-b2ak https-repair item 1).
// `app/serve.py` names its own actual cookie on every single response, in
// the `X-Converge-Csrf-Cookie` header -- read and cached here, on the same
// `window` global `tmux.js` also reads, so both files learn the same name
// without one importing the other. `cv_csrf` remains the correct fallback
// for the default/no-namespace case (unchanged for every existing
// deployment and test that never passes `--instance-dir`), and for the
// very first request of a page load, before any response has been seen.
function csrfCookieName() {
  return (typeof window !== 'undefined' && window.__convergeCsrfCookieName) || 'cv_csrf';
}

function csrfToken() {
  const name = csrfCookieName();
  const match = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : '';
}

async function request(url, options = {}) {
  const method = (options.method || 'GET').toUpperCase();
  const headers = options.body ? { 'Content-Type': 'application/json' } : {};
  if (method !== 'GET' && method !== 'HEAD') {
    const token = csrfToken();
    if (token) headers['X-CSRF-Token'] = token;
  }
  const res = await fetch(url, {
    credentials: 'same-origin',
    ...options,
    headers: { ...headers, ...(options.headers || {}) },
  });
  const namedCookie = res.headers.get('X-Converge-Csrf-Cookie');
  if (namedCookie && typeof window !== 'undefined') window.__convergeCsrfCookieName = namedCookie;
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
  // `since` reads this document as it stood at one commit in its own history
  // (converge-4pq). Left out, the read is the steward's own — their read
  // point, their kept marks — exactly as before. It is a separate URL, so the
  // service worker stores a snapshot apart from the steward's own reading and
  // one can never be served in place of the other.
  //
  // Reading a snapshot deliberately does NOT move the read point: the read
  // point belongs to the steward, and looking at history is not reading. The
  // server holds that rule, not this file.
  doc: (mid, repoId, docId, since = '') =>
    request(`${docBase(mid, repoId, docId)}${since ? `?since=${encodeURIComponent(since)}` : ''}`),
  operation: (mid) => request(`/api/managers/${encodeURIComponent(mid)}/operation`),
  needs: (mid) => request(`/api/needs/${encodeURIComponent(mid)}`),
  decision: (mid, payload) => post(`/api/managers/${encodeURIComponent(mid)}/decision`, payload),
  feedback: (mid, payload) => post(`/api/managers/${encodeURIComponent(mid)}/feedback`, payload),
  steer: (mid, payload) => post(`/api/managers/${encodeURIComponent(mid)}/steer`, payload),
  // Priority — the second of the five writes the umbrella names, and the last
  // one to exist (converge-a5g). `{item, direction, note, title}`, where the
  // direction is `raise` or `lower` and nothing else: the server refuses any
  // other word by name rather than guessing at it, so this end does not need
  // to police the vocabulary. `surface.v1` clause 3 says "with a note", which
  // is why the note travels in the same call rather than after it.
  priority: (mid, payload) => post(`/api/managers/${encodeURIComponent(mid)}/priority`, payload),
  markRead: (mid, repoId, docId) => post(`${docBase(mid, repoId, docId)}/read`, {}),
  keepChange: (mid, repoId, docId, changeId, kept) =>
    post(`${docBase(mid, repoId, docId)}/changes/${encodeURIComponent(changeId)}/keep`, { kept }),
  // Both writes take the same optional `since` the read above does, and for
  // the same reason: a change card only exists inside one reading, so a write
  // against a card from a snapshot has to name the snapshot it came from. The
  // server refuses a commit that is not in this document's own history, in
  // those words — the bound is its, not this file's.
  editChange: (mid, repoId, docId, changeId, text, since = '') =>
    post(`${docBase(mid, repoId, docId)}/changes/${encodeURIComponent(changeId)}/edit`,
      since ? { text, since } : { text }),
  restoreChange: (mid, repoId, docId, changeId, since = '') =>
    post(`${docBase(mid, repoId, docId)}/changes/${encodeURIComponent(changeId)}/restore`,
      since ? { since } : {}),
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
  // The app answers this route now (converge-eci): it stamps `(FROZEN <date>)`
  // into the document's own first heading, commits it as `<you> via Converge`,
  // and writes the four conditions into today's ratification record. The
  // payload carries them — `{conditions: [four sentences]}` — because the
  // server counts them again rather than trusting the boxes this end ticked,
  // and refuses by name when the document already carries a locking word.
  lock: (mid, repoId, docId, payload) => post(`${docBase(mid, repoId, docId)}/lock`, payload),
};
