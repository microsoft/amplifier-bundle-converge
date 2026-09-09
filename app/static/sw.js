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
//      something later, so this worker does not pretend it will. And that
//      sentence is never more certain than the browser actually is: when the
//      interface itself is down nothing could have left this machine, but
//      when it is up and one request still died in flight, this worker does
//      not know whether a manager session already received it — so it says
//      that, rather than claiming "nothing happened" when it might have.
//
// Two things are deliberately never served from a stored copy: /api/tmux/*,
// because §12 says the Manager Console is live or plainly disconnected and
// never in between; and the sign-in page.
//
// A fourth rule, not one of the original three: the SYNCED/SHELL caches are
// scoped to whoever this device last confirmed. `window.ConvergePWA.setPrincipal`
// (in offline.js) tells this worker who Shell just validated against the
// authenticated /api/boot response; a genuinely different person clears both
// caches before anything of theirs is read. A 401/403 on any /api request does
// the same, because a rejected cookie is exactly the "no longer this person's
// session" signal — and /logout still empties them outright, as before.
//
// Everything else (static assets, branding, the app shell) is cache-first or
// network-first-with-fallback so the app opens at all with the network off.

const STATIC = 'converge-static-v4';
const SHELL = 'converge-shell-v1';
const SYNCED = 'converge-synced-v1';
// converge-moe4 (platform-web.v1 Core 9): the ONE thing that changes between
// server generations of an otherwise-identical worker file. `app/serve.py`
// substitutes this one literal (`app/assets.py`'s `render_service_worker`)
// with `/static/<this generation's revision>` before ever sending these bytes
// to a browser -- so the PRECACHE list below, built from it, always names
// the SAME versioned URLs the HTML this worker was registered from just
// asked for. Unsubstituted (a source-level read of this file on disk, the
// shape every fence test here reads), it is exactly the unversioned,
// legacy `/static` prefix every server has always answered on.
const STATIC_PREFIX = '/static';
// Who this device last confirmed is behind the browser -- a durable record
// (Cache Storage, not memory) so it survives this worker being stopped and
// restarted, which happens freely and would otherwise forget the fact between
// one request and the next.
const PRINCIPAL = 'converge-principal-v1';
const PRINCIPAL_KEY = '/__converge_principal__';
// A counter, bumped every time SYNCED/SHELL are cleared for an identity
// reason (a confirmed change, a logout, a 401/403). It survives its own
// PRINCIPAL cache being deleted -- logout forgets *who*, never *how many
// times this device has changed hands* -- precisely so an answer already in
// flight when a clear happens can tell it was overtaken and refuse to write
// itself into the cache the clear just emptied. See readApi()'s use below.
const EPOCH = 'converge-epoch-v1';
const EPOCH_KEY = '/__epoch';
const KEEP = [STATIC, SHELL, SYNCED, PRINCIPAL, EPOCH];

// The app shell is one document for every route: it holds no data, so one
// stored copy answers any navigation.
const SHELL_KEY = '/';

const SYNCED_AT = 'X-Converge-Synced-At';
const FROM_CACHE = 'X-Converge-Offline';
// The server's own authenticated claim of who this response was for (the
// HTTPS lane supplies it in production; test fixtures stand in for it until
// that lands). Read only -- this worker never sets it on an outgoing request.
const SERVER_USER_HEADER = 'X-Converge-User';
// What this worker itself recorded a cached entry as belonging to, written
// alongside SYNCED_AT so a later read can refuse to hand it to anyone else.
const OWNER_HEADER = 'X-Converge-Cache-Owner';

// Every first-party stylesheet and script the app loads, so a browser that
// installs this worker and goes offline BEFORE it has fetched them still opens.
// Runtime caching alone is not enough for that cold case: it fills as things are
// fetched, and a module never fetched online is not there when the network is.
//
// This list is hand-kept and it has drifted twice: `presence.js` (converge-9ke)
// and, found with it, `tmux.js`, `render/collab.js` and `css/collab.css`.
// Missing `presence.js` did not cost only presence -- `render/direction.js`
// imports it, and a module whose import fails does not run, so the whole
// Direction surface would have gone down offline.
//
// `app/tests/test_web_polish.py` now derives the list the app actually loads --
// every `/static/` reference in the templates, plus every module reachable from
// `main.js`'s imports -- and fails if this array is missing one, so the third
// drift is caught by a check rather than by a steward offline. It also checks
// every entry below resolves to a real file: `cache.addAll` is all-or-nothing
// and its rejection is swallowed here, so ONE bad path would silently precache
// NOTHING.
//
// `/static/vendor/xterm/*` is deliberately absent: it is 488K, and it is only
// needed by the terminal viewer, which by rule 2 above is disconnected while the
// network is down anyway (§12). It stays runtime-cached.
const PRECACHE = [
  `${STATIC_PREFIX}/css/tokens.css`,
  `${STATIC_PREFIX}/css/shell.css`,
  `${STATIC_PREFIX}/css/direction.css`,
  `${STATIC_PREFIX}/css/operation.css`,
  `${STATIC_PREFIX}/css/console.css`,
  `${STATIC_PREFIX}/css/dialogs.css`,
  `${STATIC_PREFIX}/css/collab.css`,
  `${STATIC_PREFIX}/css/pwa.css`,
  `${STATIC_PREFIX}/js/main.js`,
  `${STATIC_PREFIX}/js/state.js`,
  `${STATIC_PREFIX}/js/api.js`,
  `${STATIC_PREFIX}/js/refresh.js`,
  `${STATIC_PREFIX}/js/actions.js`,
  `${STATIC_PREFIX}/js/feedback_voice.js`,
  `${STATIC_PREFIX}/js/offline.js`,
  `${STATIC_PREFIX}/js/presence.js`,
  `${STATIC_PREFIX}/js/tmux.js`,
  `${STATIC_PREFIX}/js/render/top.js`,
  `${STATIC_PREFIX}/js/render/home.js`,
  `${STATIC_PREFIX}/js/render/direction.js`,
  `${STATIC_PREFIX}/js/render/operation.js`,
  `${STATIC_PREFIX}/js/render/console.js`,
  `${STATIC_PREFIX}/js/render/collab.js`,
  // Never versioned below this line: assets.py computes a revision only over
  // app/static, and these two are served from their own separate mounts
  // (manifest, branding), which are not part of it.
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
function isOffline() {
  return Boolean(self.navigator && self.navigator.onLine === false);
}

function lead() {
  return isOffline() ? 'you are offline' : 'Converge could not be reached';
}

// Used only when the browser interface itself is down: the request could
// never have left this machine at all, so "nothing was X" is a fact, not a
// guess.
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

// Used when the interface is UP but the request still failed — a timeout, a
// dropped connection mid-flight, a manager session that vanished between the
// request landing and its answer coming back. The browser cannot tell "never
// arrived" from "arrived, and the answer was lost", so this never asserts
// nothing happened; it says so honestly and asks for a check, not a guess.
const UNKNOWN_ENDINGS = [
  [/\/decision$/, 'so it is not known whether this was recorded — reconnect, then check the decision before answering again'],
  [/\/feedback$/, 'so it is not known whether this was filed — reconnect and check before sending it again'],
  [/\/steer$/, 'so it is not known whether this was sent — reconnect and check the steering before sending it again'],
  [/\/ask$/, 'so it is not known whether this was asked — reconnect and check before asking again'],
  [/\/read$/, 'so it is not known whether your read point moved — reconnect and check before marking it read again'],
  [/\/keep$/, 'so it is not known whether this was kept — reconnect and check before keeping it again'],
  [/\/edit$/, 'so it is not known whether this was written — reconnect and check the document before saving again'],
  [/\/restore$/, 'so it is not known whether this was restored — reconnect and check the document before restoring again'],
];

const UNKNOWN_FALLBACK_ENDING = 'so it is not known whether this was sent — reconnect and check before trying again';

function refusal(pathname) {
  const table = isOffline() ? ENDINGS : UNKNOWN_ENDINGS;
  const fallback = isOffline() ? FALLBACK_ENDING : UNKNOWN_FALLBACK_ENDING;
  const found = table.find(([pattern]) => pattern.test(pathname));
  return `${lead()}, ${found ? found[1] : fallback}.`;
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

// --------------------------------------------------------------------------
// who this device last confirmed -- platform-web.v1's own-body promise that
// "whatever you can do here, the manager session can do too" only holds if
// what is shown here actually belongs to whoever is sitting at it now.
// --------------------------------------------------------------------------

async function storedPrincipal() {
  try {
    const cache = await caches.open(PRINCIPAL);
    const hit = await cache.match(PRINCIPAL_KEY);
    if (!hit) return '';
    const body = await hit.json();
    return (body && body.user) || '';
  } catch { return ''; } // storage refused: an unknown principal is the honest answer
}

async function rememberPrincipal(user) {
  try {
    const cache = await caches.open(PRINCIPAL);
    await cache.put(PRINCIPAL_KEY, new Response(
      JSON.stringify({ user, at: new Date().toISOString() }),
      { headers: { 'Content-Type': 'application/json' } },
    ));
  } catch { /* storage refused: nothing durable to remember this visit */ }
}

async function forgetPrincipal() {
  forgetBootProofs();
  try { await caches.delete(PRINCIPAL); } catch { /* nothing to forget */ }
}

// --------------------------------------------------------------------------
// the offline boot proof -- ephemeral, per-client, never a second identity
// --------------------------------------------------------------------------
//
// The gap this closes (converge-ex30): with the network down, a controlled
// page's own GET /api/boot is answered from SYNCED -- and only ever after the
// owner check below has already matched the stored entry's recorded owner
// against this device's durable, independently confirmed principal. Shell then
// asks this worker to confirm identity, and that confirmation is a NETWORK-ONLY
// fetch of /api/boot, which offline cannot succeed. Shell correctly fails
// closed on the unresolved answer and clears everything -- so the very read
// §10 exists to preserve was thrown away at the last step.
//
// What is remembered here is NOT identity and never stands in for one. It is a
// receipt for something this worker itself just did: "the cached /api/boot I
// served to THIS client a moment ago was already validated against the durable
// principal, at THIS epoch". It is consulted in exactly one place -- after a
// network confirmation has genuinely failed -- and only to answer "may this
// one client go on reading what it was already, verifiably, allowed to read".
//
// Four things make it safe to consult at all, and every one of them is checked
// again at the moment of use rather than trusted from when it was written:
//
//   1. It is keyed by the browser-supplied fetch-event clientId and matched
//      against the message's own `event.source.id`. Neither is a value a page
//      can choose -- the user agent stamps both -- so a page cannot present
//      another client's receipt, and the page's own `event.data.user` claim is
//      still never read for anything.
//   2. Its principal must still equal the NONEMPTY durable principal this
//      device confirmed for itself via a real server answer. A forged owner
//      matches nothing, and an unconfirmed device (no principal at all) has
//      nothing for it to match.
//   3. Its epoch must still be current: any identity-reason clear -- a
//      confirmed change of person, a logout, a 401/403 -- bumps the epoch and
//      clears every proof outright, so one written a moment before a clear is
//      dead the instant that clear commits.
//   4. It lives in memory only, never in Cache Storage, and expires. A
//      restarted worker, or a client that comes back later, simply has no
//      proof and is refused exactly as before -- the safe direction.
//
// So this is never an "offline authentication fallback": with no cached boot
// already validated for this exact client, nothing is remembered and nothing
// changes. Every path that used to refuse still refuses.

// Long enough to bridge Shell's own cached /api/boot read and the
// setPrincipal call that immediately follows it (milliseconds), short enough
// that nothing here outlives the page load that earned it.
const PROOF_TTL_MS = 60000;

const bootProofs = new Map();

function rememberBootProof(clientId, principal, epoch) {
  if (!clientId || !principal) return;
  bootProofs.set(clientId, { principal, epoch, at: Date.now() });
}

function forgetBootProofs() {
  bootProofs.clear();
}

// The principal this client's proof still stands for, or '' -- which every
// caller must read as "refuse", never as "nothing to compare against".
async function provenPrincipalFor(clientId) {
  if (!clientId) return '';
  const proof = bootProofs.get(clientId);
  if (!proof) return '';
  if (Date.now() - proof.at > PROOF_TTL_MS) { bootProofs.delete(clientId); return ''; }
  const principal = await storedPrincipal();
  if (!principal || !proof.principal || proof.principal !== principal) return '';
  if ((await currentEpoch()) !== proof.epoch) { bootProofs.delete(clientId); return ''; }
  return principal;
}

// Never STATIC: that cache is this origin's own code, safe for anyone to run,
// and wiping it on a principal change would be exactly the "unrelated cache"
// the PWA brief forbids deleting indiscriminately.
async function forgetWhatWasSynced() {
  await Promise.all([caches.delete(SHELL), caches.delete(SYNCED)]).catch(() => undefined);
}

async function currentEpoch() {
  try {
    const cache = await caches.open(EPOCH);
    const hit = await cache.match(EPOCH_KEY);
    if (!hit) return 0;
    const body = await hit.json();
    return (body && typeof body.epoch === 'number') ? body.epoch : 0;
  } catch { return 0; } // storage refused: treat as epoch 0, same as a fresh worker
}

async function bumpEpoch() {
  const next = (await currentEpoch()) + 1;
  try {
    const cache = await caches.open(EPOCH);
    await cache.put(EPOCH_KEY, new Response(
      JSON.stringify({ epoch: next }),
      { headers: { 'Content-Type': 'application/json' } },
    ));
  } catch {
    // storage refused: the epoch check below degrades to "always current",
    // which only risks one extra cache write -- the clear this pairs with
    // already happened, so no identity can leak from this failing alone.
  }
  return next;
}

// A single chain every identity-transition write, and every readApi() cache
// write, runs through -- so one can never land in the middle of the other.
// Cache Storage gives no ordering guarantee across concurrent awaits on its
// own; this is the one thing this worker owns to provide it.
let transitionChain = Promise.resolve();
function serialized(fn) {
  const run = transitionChain.then(fn, fn);
  transitionChain = run.then(() => undefined, () => undefined);
  return run;
}

// Every identity-reason clear -- a confirmed principal change, a logout, a
// 401/403 -- goes through here, never through forgetWhatWasSynced() alone.
//
// Epoch bumps FIRST, cache clears SECOND -- reversed from the original
// shape, and that order is load-bearing. readApi() captures the epoch
// before its own fetch and only writes to the cache if that epoch is still
// current afterwards. With clear-then-bump, a response already past that
// recheck could still land in the window between the clear finishing and
// the bump committing, repopulating the cache this call was meant to empty.
// Bumping first closes that window: the recheck fails the instant the bump
// commits, before the clear has even started, so nothing already in flight
// can land in cleared-but-not-yet-bumped (or bumped-but-not-yet-cleared)
// space. Wrapped in the same `serialized()` chain readApi() uses, so a
// concurrent transition and a concurrent cache write can never interleave.
async function clearSyncedForNewEpoch() {
  return serialized(async () => {
    // Proofs go FIRST, synchronously, before anything awaits: a proof is a
    // receipt for a cached read, and the cache backing it is about to be
    // emptied for an identity reason. The epoch recheck in
    // provenPrincipalFor() would already refuse them a moment later, but
    // clearing them outright means there is no window at all in which one
    // could be consulted.
    forgetBootProofs();
    await bumpEpoch();
    await forgetWhatWasSynced();
  });
}

// The worker's OWN confirmation of who is authenticated right now: a fresh,
// same-origin, credentialed fetch of /api/boot, issued directly from this
// script -- never dispatched through the 'fetch' listener below. A service
// worker's own fetch() calls are not intercepted by its own 'fetch' event
// (only requests a controlled PAGE makes are), so this cannot recurse
// through readApi()/writeApi() no matter how those change later. This is the
// only source of truth for identity anywhere in this file; a page message
// can ask it to run, but nothing a page says can stand in for it.
async function fetchBootIdentity() {
  try {
    const res = await fetch('/api/boot', { credentials: 'same-origin', cache: 'no-store' });
    if (!res || !res.ok) return { ok: false };
    const body = await res.json().catch(() => null);
    const user = (body && typeof body.user === 'string') ? body.user.trim() : '';
    return { ok: true, user };
  } catch {
    return { ok: false };
  }
}

self.addEventListener('message', (event) => {
  const kind = event.data && event.data.type;

  if (kind === 'converge-set-principal') {
    const reply = (payload) => {
      if (event.ports && event.ports[0]) event.ports[0].postMessage(payload);
    };
    // Read synchronously, off the event itself: the user agent's own stamp of
    // WHICH client sent this message. Not `event.data` -- nothing a page can
    // author reaches this variable.
    const sourceId = (event.source && event.source.id) || '';
    // The page's own claim -- event.data.user, if present at all -- is NEVER
    // treated as identity. It is only a request to check now; who this
    // device trusts is decided solely by fetchBootIdentity()'s own answer
    // from the real server. A forged or stale page message can, at worst,
    // ask for a check that was always going to happen anyway -- it can never
    // select, keep, or clear a cache on its own say-so.
    event.waitUntil(
      fetchBootIdentity().then(async ({ ok, user }) => {
        if (!ok) {
          // The server could not be reached, or the request itself failed.
          // Neither is proof that whoever this device already trusts has
          // gone away -- acting on it would throw away good offline reads on
          // the one path meant to preserve them, so nothing here changes.
          //
          // One narrow thing may still be answered: whether THIS client was
          // itself just served a cached /api/boot that this worker had
          // already validated against the durable principal, at the current
          // epoch. That is a receipt for a read this worker performed, not a
          // second way to authenticate -- provenPrincipalFor() re-checks the
          // client, the durable owner and the epoch at this moment, and the
          // principal reported back is the one THIS WORKER holds, never the
          // `user` the page asked with. With no such proof this is exactly
          // the refusal it always was.
          const proven = await provenPrincipalFor(sourceId);
          if (proven) {
            reply({
              type: 'converge-principal-set',
              ok: true,
              cleared: false,
              offlineConfirmed: true,
              user: proven,
            });
            return;
          }
          reply({ type: 'converge-principal-set', ok: false, reason: 'boot-unreachable' });
          return;
        }
        if (!user) {
          // The server answered, plainly: no one is authenticated here right
          // now. That IS a confirmed fact, and it is a logout in every way
          // that matters to this cache -- nothing of the last confirmed
          // person may linger for whoever the next request turns out to be.
          await clearSyncedForNewEpoch();
          await forgetPrincipal();
          reply({ type: 'converge-principal-set', ok: true, cleared: true, user: '' });
          return;
        }
        const known = await storedPrincipal();
        // Multi-tab, same confirmed person: idempotent, nothing to clear. A
        // genuinely different confirmed person -- a second login racing this
        // one, a worker that restarted mid-session, or exactly the attack
        // this exists to catch: a page claiming to still be whoever was here
        // while the server says someone else now holds this cookie -- is the
        // one case that must clear first.
        const changed = Boolean(known) && known !== user;
        if (changed) await clearSyncedForNewEpoch();
        await rememberPrincipal(user);
        reply({ type: 'converge-principal-set', ok: true, cleared: changed, user });
      }).catch(() => reply({ type: 'converge-principal-set', ok: false, reason: 'storage-error' })),
    );
    return;
  }

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

async function withHeaders(res, pairs) {
  const body = await res.arrayBuffer();
  const headers = new Headers(res.headers);
  for (const [name, value] of pairs) headers.set(name, value);
  return new Response(body, { status: res.status, statusText: res.statusText, headers });
}

// The server's own authenticated claim, when present. Never trusted from
// anywhere else -- this is the one place this file reads SERVER_USER_HEADER.
function serverClaimedOwner(res) {
  const header = res && res.headers && res.headers.get(SERVER_USER_HEADER);
  return header ? header.trim() : '';
}

// 401/403 mean this cookie no longer speaks for anyone trusted -- a session
// that expired, or (on a shared browser) simply is not the person it was a
// moment ago. Either way, whatever this device had synced under it must not
// go on answering the next request that arrives without a good one.
function isAuthLoss(res) {
  return Boolean(res) && (res.status === 401 || res.status === 403);
}

// `clientId` is the user agent's own stamp on the fetch event -- which window
// client made this request. It is never a value a page chooses, and it is used
// for exactly one thing: keying the cached-boot proof described above.
async function readApi(req, url, clientId) {
  // Captured before the request leaves, so a clear that happens WHILE it is
  // in flight -- a confirmed principal change, a logout, a 401 answered by a
  // different in-flight request -- can be told apart from the ordinary case
  // where nothing changed underneath it.
  const epoch = await currentEpoch();
  try {
    const res = await fetch(req);
    if (res && res.ok) {
      // Admit to the offline cache ONLY when the server's own authenticated
      // claim for THIS response (X-Converge-User, serve.py's USER_HEADER) is
      // a NONEMPTY match for the NONEMPTY, durable principal this device has
      // already verified via its own /api/boot confirmation (converge-e2c3).
      //
      // The old `serverClaimedOwner(res) || (await storedPrincipal())` fell
      // back to "whoever we last remembered" the moment the header was
      // missing or empty -- an unverified pre-boot write, not a confirmed
      // one. There is no fallback here: a missing/empty claim, an
      // unconfirmed device (no principal recorded yet), or a claim that does
      // not match the confirmed principal all mean this response is simply
      // never written to SYNCED. The live network answer is still returned
      // either way -- only the offline copy is refused.
      //
      // This still preserves the normal path: `converge-set-principal`
      // (fetchBootIdentity) is confirmed once, first, before Shell's own
      // /api/... reads run, so by the time those responses arrive their
      // X-Converge-User already equals the just-confirmed principal, and
      // first-online-load-then-offline-reload keeps working exactly as
      // before.
      const claimed = serverClaimedOwner(res);
      const principal = await storedPrincipal();
      const owner = (claimed && principal && claimed === principal) ? claimed : '';
      if (owner) {
        // The TIMING check below is a separate concern from the identity
        // check above: only keep it if nothing cleared the cache while it
        // was still in flight. Without this, an answer fetched under
        // whoever's cookie was live when the request STARTED could
        // repopulate a cache a clear just emptied for whoever is confirmed
        // here now, right after the clear emptied it for exactly that
        // reason. Wrapped in the same `serialized()` chain a concurrent
        // identity transition uses, so the recheck and the write can never
        // straddle one.
        const keep = await withHeaders(res.clone(), [
          [SYNCED_AT, new Date().toISOString()],
          [OWNER_HEADER, owner],
        ]);
        await serialized(async () => {
          if ((await currentEpoch()) === epoch) {
            const cache = await caches.open(SYNCED);
            await cache.put(req, keep);
          }
        });
      }
    } else if (isAuthLoss(res)) {
      await clearSyncedForNewEpoch();
      await forgetPrincipal();
    }
    return res;
  } catch {
    const cache = await caches.open(SYNCED);
    const hit = await cache.match(req);
    if (!hit) {
      tell({ type: 'converge-offline-miss', path: url.pathname });
      return said(NOTHING_SYNCED);
    }
    // Replay only a NONEMPTY recorded owner that matches a NONEMPTY current
    // principal (converge-e2c3) -- never an unowned/legacy entry (one
    // written before this bound anything, or by an earlier version of this
    // file that admitted a fallback owner), and never against an
    // unconfirmed device (no current principal recorded at all). Either
    // side being empty is refused, not treated as "nothing to compare
    // against, so let it through" -- that fallback is exactly the gap that
    // let a cache entry answer for someone it was never confirmed to be.
    const owner = hit.headers.get(OWNER_HEADER) || '';
    const current = await storedPrincipal();
    if (!owner || !current || owner !== current) {
      tell({ type: 'converge-offline-miss', path: url.pathname });
      return said(NOTHING_SYNCED);
    }
    // This cached /api/boot was just served to this client, and only because
    // its recorded owner matched the durable principal this device confirmed
    // for itself. Remember that -- for this client, at this epoch, briefly --
    // so the identity confirmation that immediately follows can tell "this
    // page already read a validated boot" from "some page is asking to be
    // trusted offline". See the proof section above for why this is not an
    // identity, and for the four checks made again at the moment of use.
    if (url.pathname === '/api/boot') {
      rememberBootProof(clientId, current, await currentEpoch());
    }
    const at = hit.headers.get(SYNCED_AT) || '';
    tell({ type: 'converge-offline-read', path: url.pathname, syncedAt: at });
    return withHeader(hit, FROM_CACHE, '1');
  }
}

async function writeApi(req, url) {
  try {
    const res = await fetch(req);
    if (isAuthLoss(res)) {
      await clearSyncedForNewEpoch();
      await forgetPrincipal();
    }
    return res;
  } catch {
    // `refusal()` itself tells "definitely never left this machine" (offline)
    // from "the interface is up but this one request still died" (unknown
    // outcome) -- see the ENDINGS/UNKNOWN_ENDINGS split above. Neither case is
    // asserted here; the sentence already says the honest one.
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
      // The PRINCIPAL record goes too: whoever signs in next at this browser
      // starts with no known predecessor, rather than being silently compared
      // against the person who just signed out. The epoch bumps along with
      // it, so a response for a request this person made just before signing
      // out cannot repopulate the cache this just emptied.
      event.waitUntil(
        clearSyncedForNewEpoch().then(forgetPrincipal).catch(() => undefined),
      );
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
    event.respondWith(req.method === 'GET' ? readApi(req, url, event.clientId) : writeApi(req, url));
    return;
  }

  if (req.method !== 'GET') return;
  if (!isCacheable(url)) return;

  // \u00a79: installing changes only the frame, and nothing here may freeze the
  // code inside it. A cached hit answers THIS request immediately -- slow
  // networking must stay slow networking, never slow cached startup -- but
  // the refresh behind it has two bugs a fixed URL and a changed server can
  // both expose at once:
  //
  //   1. `fetch(req)` runs in the SAME cache mode the original request used
  //      (ordinarily 'default'), so it can be answered straight out of the
  //      browser's OWN HTTP cache -- a layer this worker does not control --
  //      without ever reaching the network the server just changed. Measured
  //      fact this fixes: a same-URL asset served with an ETag/Last-Modified
  //      but no explicit Cache-Control is exactly the shape the browser's own
  //      heuristic freshness keeps "fresh" for a while, so an ordinary
  //      same-URL reload can keep reusing it long after the server moved on
  //      (converge-moe4). `cache: 'reload'` forces this one request past that
  //      layer every time -- the same thing a person pressing reload does --
  //      while still writing the fresh answer back into it.
  //   2. The old `.then(...)` chain below was never kept alive: a service
  //      worker may be stopped the instant `respondWith`'s promise settles,
  //      and stopping it mid-chain drops the `cache.put` on the floor. The
  //      refresh keeps happening on the wire but the new bytes never reach
  //      Cache Storage, so the next navigation reads the same stale entry
  //      again. `event.waitUntil` below extends the worker's own life until
  //      the put actually lands -- it never delays the response itself,
  //      which is already served from `hit` the moment one exists.
  event.respondWith(
    caches.match(req).then((hit) => {
      const refresh = fetch(new Request(req, { cache: 'reload' })).then((res) => {
        if (res && res.ok) {
          const copy = res.clone();
          return caches.open(STATIC).then((cache) => cache.put(req, copy)).then(() => res);
        }
        return res;
      }).catch(() => hit);
      event.waitUntil(refresh.catch(() => undefined));
      return hit || refresh;
    }),
  );
});
