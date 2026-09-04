// Converge service worker — the small helper `platform-web.v1` §10 names.
//
// Three rules that matter:
//
//   1. /login and /logout are NEVER cached — an auth surface must not be
//      replayed. Signing out empties everything this worker kept, so the next
//      person at this browser reads nothing of the last person's.
//
//   2. A GET under /api is network-first, and the network's answer always
//      wins. A stored copy is served ONLY when the request actually failed,
//      and when it is served it carries the moment it was fetched, which the
//      page shows as "as of <time>". §10 asks for what was last synced,
//      *labelled with when* — which is a different thing from a stale value
//      shown as if it were live. The old rule here ("never write /api to the
//      cache at all") kept the second promise by giving up the first: offline
//      the shell loaded and every panel in it was empty (converge-719).
//
//   3. A write while the network is down is refused in one plain sentence
//      naming what to do instead — never a status code and never "Failed to
//      fetch" (§11). Nothing is queued: a browser cannot promise to send
//      something later, so this worker does not pretend it will.
//
// Two things are deliberately never served from a stored copy: /api/tmux/*,
// because §12 says the Manager Console is live or plainly disconnected and
// never in between; and the sign-in page.
//
// Everything else (static assets, branding, the app shell) is cache-first or
// network-first-with-fallback so the app opens at all with the network off.

const STATIC = 'converge-static-v4';
const SHELL = 'converge-shell-v1';
const SYNCED = 'converge-synced-v1';
const KEEP = [STATIC, SHELL, SYNCED];

// The app shell is one document for every route: it holds no data, so one
// stored copy answers any navigation.
const SHELL_KEY = '/';

const SYNCED_AT = 'X-Converge-Synced-At';
const FROM_CACHE = 'X-Converge-Offline';

const PRECACHE = [
  '/static/css/tokens.css',
  '/static/css/shell.css',
  '/static/css/direction.css',
  '/static/css/operation.css',
  '/static/css/console.css',
  '/static/css/dialogs.css',
  '/static/js/main.js',
  '/static/js/state.js',
  '/static/js/api.js',
  '/static/js/refresh.js',
  '/static/js/actions.js',
  '/static/js/offline.js',
  '/static/js/render/top.js',
  '/static/js/render/home.js',
  '/static/js/render/direction.js',
  '/static/js/render/operation.js',
  '/static/js/render/console.js',
  '/manifest.webmanifest',
  '/branding/icons/converge-icon-64.png',
  '/branding/favicons/favicon-32.png',
  '/branding/pwa/pwa-192.png',
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(STATIC)
      .then((cache) => cache.addAll(PRECACHE).catch(() => undefined))
      .then(() => self.skipWaiting()),
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => !KEEP.includes(k)).map((k) => caches.delete(k))))
      .then(() => self.clients.claim()),
  );
});

// --------------------------------------------------------------------------
// what is being asked for
// --------------------------------------------------------------------------

function isNeverCached(url) {
  return url.pathname === '/login' || url.pathname === '/logout';
}

function isApi(url) {
  return url.pathname === '/api' || url.pathname.startsWith('/api/');
}

// §12: the console is a view of a running session. A stored frame of it would
// be an old screen sitting there looking live, which is the one thing §12
// forbids, so it is never stored and never replayed.
function isConsole(url) {
  return url.pathname.startsWith('/api/tmux');
}

function isCacheable(url) {
  return url.pathname.startsWith('/static/')
    || url.pathname.startsWith('/branding/')
    || url.pathname === '/manifest.webmanifest';
}

// --------------------------------------------------------------------------
// the sentences
// --------------------------------------------------------------------------
//
// Each is one sentence, in plain words, and each names what to do instead.
// The opening clause is lower-case because the app's own handlers put it after
// their own words ("Could not record the decision: you are offline, so …");
// `offline.js` capitalises it when it shows one on its own.

// True in both of the two ways a request can fail, and it never claims the
// wrong one: the browser knows whether the machine is off the network.
function lead() {
  const off = self.navigator && self.navigator.onLine === false;
  return off ? 'you are offline' : 'Converge could not be reached';
}

const ENDINGS = [
  [/\/decision$/, 'so nothing was recorded — reconnect and answer it again, or tell the manager session directly'],
  [/\/feedback$/, 'so nothing was filed — reconnect and send it again, or tell the manager session directly'],
  [/\/steer$/, 'so nothing was sent — reconnect and steer again, or tell the manager session directly'],
  [/\/ask$/, 'so nothing was asked — reconnect and ask again, or tell the manager session directly'],
  [/\/read$/, 'so your read point did not move — reconnect and mark it read again'],
  [/\/keep$/, 'so nothing was kept — reconnect and keep it again'],
  [/\/edit$/, 'so nothing was written — reconnect and save it again, or edit the document directly'],
  [/\/restore$/, 'so nothing was restored — reconnect and restore it again, or edit the document directly'],
];

const FALLBACK_ENDING = 'so nothing was sent — reconnect and try again, or tell the manager session directly';

function refusal(pathname) {
  const found = ENDINGS.find(([pattern]) => pattern.test(pathname));
  return `${lead()}, ${found ? found[1] : FALLBACK_ENDING}.`;
}

const NOTHING_SYNCED = 'this has not been synced to this device yet, so there is nothing to read offline';
const CONSOLE_DOWN = 'the Manager Console is a live view, so it is disconnected while the network is down';

function said(sentence, status) {
  return new Response(
    JSON.stringify({ error: sentence, offline: true }),
    { status: status || 503, headers: { 'Content-Type': 'application/json' } },
  );
}

// --------------------------------------------------------------------------
// telling the page
// --------------------------------------------------------------------------

function tell(message) {
  self.clients.matchAll({ type: 'window', includeUncontrolled: true })
    .then((all) => all.forEach((client) => client.postMessage(message)))
    .catch(() => undefined);
}

// What this worker is holding, read back out of the cache itself rather than
// out of memory — a worker is stopped and restarted freely, and an answer that
// died with it would leave the page unable to say when anything was synced.
async function whatIsSynced() {
  const entries = [];
  try {
    const cache = await caches.open(SYNCED);
    const keys = await cache.keys();
    for (const key of keys) {
      const hit = await cache.match(key);
      if (!hit) continue;
      entries.push({ path: new URL(key.url).pathname, syncedAt: hit.headers.get(SYNCED_AT) || '' });
    }
  } catch { /* storage refused: an empty list is the honest answer */ }
  return entries;
}

self.addEventListener('message', (event) => {
  const kind = event.data && event.data.type;
  if (kind !== 'converge-what-is-synced') return;
  const reply = (payload) => {
    if (event.ports && event.ports[0]) event.ports[0].postMessage(payload);
    else tell(payload);
  };
  // `onLine` travels with the answer because this worker, not the page, is the
  // thing whose requests failed — and the two can disagree. The banner and the
  // refusals must read the same fact, or the screen contradicts itself.
  event.waitUntil(
    whatIsSynced().then((entries) => reply({
      type: 'converge-synced',
      entries,
      onLine: !(self.navigator && self.navigator.onLine === false),
    })),
  );
});

// --------------------------------------------------------------------------
// storing and re-serving
// --------------------------------------------------------------------------

async function withHeader(res, name, value) {
  const body = await res.arrayBuffer();
  const headers = new Headers(res.headers);
  headers.set(name, value);
  return new Response(body, { status: res.status, statusText: res.statusText, headers });
}

async function readApi(req, url) {
  try {
    const res = await fetch(req);
    if (res && res.ok) {
      const keep = await withHeader(res.clone(), SYNCED_AT, new Date().toISOString());
      const cache = await caches.open(SYNCED);
      await cache.put(req, keep);
    }
    return res;
  } catch {
    const cache = await caches.open(SYNCED);
    const hit = await cache.match(req);
    if (!hit) {
      tell({ type: 'converge-offline-miss', path: url.pathname });
      return said(NOTHING_SYNCED);
    }
    const at = hit.headers.get(SYNCED_AT) || '';
    tell({ type: 'converge-offline-read', path: url.pathname, syncedAt: at });
    return withHeader(hit, FROM_CACHE, '1');
  }
}

async function writeApi(req, url) {
  try {
    return await fetch(req);
  } catch {
    // The request never left this machine, so nothing was written anywhere.
    const sentence = refusal(url.pathname);
    tell({ type: 'converge-offline-write', path: url.pathname, sentence });
    return said(sentence);
  }
}

async function shellRoute(req) {
  try {
    const res = await fetch(req);
    // A redirect means the gate sent this to /login. That page is never stored,
    // and it is certainly not the app shell.
    if (res && res.ok && !res.redirected) {
      const cache = await caches.open(SHELL);
      await cache.put(SHELL_KEY, res.clone());
    }
    return res;
  } catch {
    const cache = await caches.open(SHELL);
    const hit = await cache.match(SHELL_KEY);
    if (hit) return hit;
    return new Response(
      '<!doctype html><meta charset="utf-8"><title>Converge — offline</title>'
      + '<body style="font:16px/1.5 system-ui;margin:3rem auto;max-width:34rem;padding:0 1rem">'
      + '<h1>Converge is offline</h1><p>Converge has not finished opening on this device yet, '
      + 'so there is nothing stored here to read. Reconnect and open it once, and what you '
      + 'read will be here the next time the network is down.</p>',
      { status: 503, headers: { 'Content-Type': 'text/html; charset=utf-8' } },
    );
  }
}

// --------------------------------------------------------------------------
// routing
// --------------------------------------------------------------------------

self.addEventListener('fetch', (event) => {
  const req = event.request;
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;

  // Rule 1. Signing out empties everything kept for the person signing out,
  // so nothing of theirs is left for whoever opens this browser next.
  if (isNeverCached(url)) {
    if (url.pathname === '/logout') {
      event.waitUntil(Promise.all([caches.delete(SHELL), caches.delete(SYNCED)]).catch(() => undefined));
    }
    return;
  }

  // The app shell, so the app opens at all with the network off.
  if (req.mode === 'navigate') {
    event.respondWith(shellRoute(req));
    return;
  }

  if (isApi(url)) {
    if (isConsole(url)) {
      event.respondWith(fetch(req).catch(() => said(CONSOLE_DOWN)));
      return;
    }
    event.respondWith(req.method === 'GET' ? readApi(req, url) : writeApi(req, url));
    return;
  }

  if (req.method !== 'GET') return;
  if (!isCacheable(url)) return;

  event.respondWith(
    caches.match(req).then((hit) => {
      const network = fetch(req).then((res) => {
        if (res && res.ok) {
          const copy = res.clone();
          caches.open(STATIC).then((cache) => cache.put(req, copy));
        }
        return res;
      }).catch(() => hit);
      return hit || network;
    }),
  );
});
