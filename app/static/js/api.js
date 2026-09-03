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
  if (!res.ok) throw new Error(`${options.method || 'GET'} ${url} → ${res.status}`);
  return res.json();
}

const post = (url, payload) => request(url, { method: 'POST', body: JSON.stringify(payload) });

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
};
