// Converge service worker.
//
// Two rules that matter:
//   1. /login and /logout are NEVER cached — an auth surface must not be replayed.
//   2. /api is network-first and is never written to the cache at all, so a stale
//      decision or lane state can never be shown as if it were live.
// Everything else (static assets, branding) is cache-first with a background refresh.

const CACHE = 'converge-static-v3';

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
    caches.open(CACHE)
      .then((cache) => cache.addAll(PRECACHE).catch(() => undefined))
      .then(() => self.skipWaiting()),
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim()),
  );
});

function isNeverCached(url) {
  return url.pathname === '/login' || url.pathname === '/logout';
}

function isApi(url) {
  return url.pathname === '/api' || url.pathname.startsWith('/api/');
}

function isCacheable(url) {
  return url.pathname.startsWith('/static/')
    || url.pathname.startsWith('/branding/')
    || url.pathname === '/manifest.webmanifest';
}

self.addEventListener('fetch', (event) => {
  const req = event.request;
  if (req.method !== 'GET') return;

  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;

  // Auth surface: straight to the network, never stored.
  if (isNeverCached(url)) return;

  // Live data: network-first, and never written to the cache.
  if (isApi(url)) {
    event.respondWith(
      fetch(req).catch(() => new Response(
        JSON.stringify({ error: 'offline' }),
        { status: 503, headers: { 'Content-Type': 'application/json' } },
      )),
    );
    return;
  }

  if (!isCacheable(url)) return;

  event.respondWith(
    caches.match(req).then((hit) => {
      const network = fetch(req).then((res) => {
        if (res && res.ok) {
          const copy = res.clone();
          caches.open(CACHE).then((cache) => cache.put(req, copy));
        }
        return res;
      }).catch(() => hit);
      return hit || network;
    }),
  );
});
