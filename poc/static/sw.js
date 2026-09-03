/* Enough of a service worker to install as an app and open without a network.
   The shell is cached; everything the page reads from the project is asked for
   fresh every time, because a stale answer is worse than no answer. */

const SHELL = "converge-shell-v1";
const FILES = [
  "/",
  "/static/app.css",
  "/static/app.js",
  "/static/icon-192.png",
  "/static/icon-512.png",
  "/vendor/xterm/xterm.js",
  "/vendor/xterm/xterm.css",
  "/manifest.webmanifest",
];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(SHELL).then((cache) => cache.addAll(FILES)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys()
      .then((names) => Promise.all(names.filter((n) => n !== SHELL).map((n) => caches.delete(n))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);
  if (event.request.method !== "GET" || url.origin !== self.location.origin) return;
  if (url.pathname.startsWith("/api/")) return;
  event.respondWith(
    fetch(event.request)
      .then((res) => {
        const copy = res.clone();
        caches.open(SHELL).then((cache) => cache.put(event.request, copy)).catch(() => {});
        return res;
      })
      .catch(() => caches.match(event.request).then((hit) => hit || caches.match("/")))
  );
});
