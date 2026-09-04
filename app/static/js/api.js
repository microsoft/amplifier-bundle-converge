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
  return res.json();
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
  // Ask — the fifth write the umbrella names. One route for all three scopes,
  // because the scope is a fact about the request rather than a different
  // request. What should come back is a proposal to review.
  //
  // The app does not answer this route yet: `app/serve.py` and `app/writes.py`
  // are another lane's files and the server half is filed as converge-ddt. The
  // call is left pointing at the real route on purpose — it fails loudly and
  // the screen says so, rather than a control that quietly does nothing.
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
