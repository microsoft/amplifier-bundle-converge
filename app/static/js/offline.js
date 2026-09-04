// The offline banner — the page's half of `platform-web.v1` §10 and §11.
//
// `sw.js` decides what happens to a request when the network is down. This
// file only says so on the screen, in the two ways the contract asks for:
//
//   §10  what is on screen was last synced, and when that was — a visible
//        "as of <time>", plus the moment each stored payload came from, so
//        nothing that is not current is shown as current.
//   §11  a write while the network is down is refused in one plain sentence,
//        shown here whole and unprefixed.
//
// It is a plain script rather than a module on purpose: it must be running
// before `main.js` makes its first request, so that no message from the worker
// is missed. It touches nothing else on the page and holds no data of its own.

(function () {
  'use strict';

  var BANNER = 'offlineBanner';

  // What was actually served from the store this visit — the payloads the
  // screen is drawn from. Keyed by path so a re-read replaces its predecessor.
  var served = Object.create(null);
  // Everything this device is holding, read back out of the worker's cache.
  var stored = Object.create(null);
  // The last write the worker refused, in its own words.
  var refusal = '';
  // What the WORKER believes about the network. It is the thing whose requests
  // actually failed, and a page can believe it is online while every request
  // out of it dies; when the two disagree the worker is the one to believe.
  var workerOnline = null;

  // ------------------------------------------------------------------ words

  var LABELS = [
    [/^\/api\/boot$/, 'manager sessions'],
    [/^\/api\/needs\//, 'what needs you'],
    [/^\/api\/managers\/[^/]+\/operation$/, 'operation'],
    [/^\/api\/managers\/[^/]+\/docs\/[^/]+\/(.+)$/, null],
    [/^\/api\/managers\/[^/]+$/, 'direction'],
  ];

  function label(path) {
    for (var i = 0; i < LABELS.length; i += 1) {
      var found = LABELS[i][0].exec(path);
      if (!found) continue;
      if (LABELS[i][1]) return LABELS[i][1];
      return decodeURIComponent(found[1]);
    }
    return path;
  }

  function when(iso) {
    if (!iso) return 'an unrecorded moment';
    var at = new Date(iso);
    if (isNaN(at.getTime())) return 'an unrecorded moment';
    var clock = at.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    var sameDay = at.toDateString() === new Date().toDateString();
    return sameDay ? clock : at.toLocaleDateString([], { month: 'short', day: 'numeric' }) + ' ' + clock;
  }

  function capitalise(sentence) {
    return sentence ? sentence.charAt(0).toUpperCase() + sentence.slice(1) : sentence;
  }

  // ------------------------------------------------------------------ state

  function shownEntries() {
    var merged = Object.create(null);
    var path;
    for (path in stored) merged[path] = stored[path];
    for (path in served) merged[path] = served[path];
    return Object.keys(merged).sort().map(function (p) {
      return { path: p, syncedAt: merged[p] };
    });
  }

  // The oldest of them, never the newest: saying "as of" the newest moment
  // would claim an older payload beside it is fresher than it is.
  function oldest(entries) {
    return entries.reduce(function (so_far, entry) {
      if (!entry.syncedAt) return so_far;
      if (!so_far || entry.syncedAt < so_far) return entry.syncedAt;
      return so_far;
    }, '');
  }

  function offline() {
    if (workerOnline === false) return true;
    return typeof navigator !== 'undefined' && navigator.onLine === false;
  }

  function anythingRefusedOrStale() {
    return Boolean(refusal) || Object.keys(served).length > 0;
  }

  // ------------------------------------------------------------------ paint

  function paint() {
    var el = document.getElementById(BANNER);
    if (!el) return;

    var show = offline() || anythingRefusedOrStale();
    if (!show) {
      el.textContent = '';
      el.hidden = true;
      el.classList.remove('is-visible');
      return;
    }

    var entries = shownEntries();
    var lead = offline() ? 'Offline' : 'Converge could not be reached';

    var headline = document.createElement('p');
    headline.className = 'offline-headline';
    headline.textContent = entries.length
      ? lead + ' — showing what was last synced, as of ' + when(oldest(entries)) + '.'
      : lead + ' — nothing has been synced to this device yet, so there is nothing to read.';

    var second = document.createElement('p');
    second.className = 'offline-refusal';
    second.textContent = refusal
      ? capitalise(refusal)
      : 'No write is sent while the network is down.';

    var marks = document.createElement('ul');
    marks.className = 'offline-marks';
    entries.forEach(function (entry) {
      var li = document.createElement('li');
      li.className = 'offline-mark';
      li.dataset.path = entry.path;
      li.textContent = label(entry.path) + ' as of ' + when(entry.syncedAt);
      marks.appendChild(li);
    });

    el.textContent = '';
    el.appendChild(headline);
    el.appendChild(second);
    if (entries.length) el.appendChild(marks);
    el.hidden = false;
    el.classList.add('is-visible');
  }

  // ------------------------------------------------------- the worker's news

  function ask() {
    if (!('serviceWorker' in navigator) || !navigator.serviceWorker.controller) return;
    var channel = new MessageChannel();
    channel.port1.onmessage = function (event) {
      var data = event.data || {};
      if (data.type !== 'converge-synced') return;
      stored = Object.create(null);
      (data.entries || []).forEach(function (entry) { stored[entry.path] = entry.syncedAt; });
      if (typeof data.onLine === 'boolean') workerOnline = data.onLine;
      paint();
    };
    try {
      navigator.serviceWorker.controller.postMessage({ type: 'converge-what-is-synced' }, [channel.port2]);
    } catch { /* no worker to ask: the banner falls back to what it was told */ }
  }

  function heard(event) {
    var data = event.data || {};
    if (data.type === 'converge-offline-read') {
      served[data.path] = data.syncedAt || '';
      paint();
      return;
    }
    if (data.type === 'converge-offline-write') {
      refusal = data.sentence || '';
      paint();
      return;
    }
    if (data.type === 'converge-offline-miss') {
      paint();
    }
  }

  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.addEventListener('message', heard);
    navigator.serviceWorker.ready.then(ask).catch(function () { /* no worker: banner still reports offline */ });
    navigator.serviceWorker.addEventListener('controllerchange', ask);
  }

  window.addEventListener('offline', function () { ask(); paint(); });
  window.addEventListener('online', function () {
    // Back on the network: the refusal is spent and what is on screen is about
    // to be re-read, so the banner stops claiming either.
    refusal = '';
    served = Object.create(null);
    paint();
  });

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', paint);
  else paint();

  ask();
}());
