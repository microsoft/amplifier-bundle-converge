// The PWA's own script — the page's half of `platform-web.v1` §9, §10 and §11.
// Three sections, each an independent IIFE so a failure in one cannot take
// down another:
//
//   1. The offline banner (§10, §11): `sw.js` decides what happens to a
//      request when the network is down; this section only says so on the
//      screen — a visible "as of <time>" for what was last synced, and a
//      write's refusal shown whole and unprefixed.
//   2. `window.ConvergePWA.setPrincipal(user)` — the seam composition.v1's
//      shared-interfaces section names: Shell awaits this after /api/boot and
//      before its first manager/doc read, passing the user the AUTHENTICATED
//      boot response named. This is a REQUEST to check, never a claim of
//      identity by itself: `sw.js` never trusts `user` -- it independently
//      re-fetches /api/boot with its own credentialed request and acts only
//      on what the real server says, so a forged or stale `user` argument
//      here can, at worst, ask for a check that was always going to happen.
//      Always SETTLES within a bounded time (never hangs). It resolves when
//      no active worker exists to ask (a network-only capability gap, not a
//      failure) or when identity is confirmed and matches; it REJECTS when
//      an active worker fails to confirm at all, or confirms someone other
//      than expected -- Shell's own `await`/`catch` is the fail-closed gate
//      that keeps stale boot data from reaching a manager/doc read.
//   3. The install affordance (§9): offers installing only where the browser
//      actually supports it (`beforeinstallprompt`), gives iOS Safari — which
//      never fires that event — its own honest manual steps instead of a dead
//      button, and never claims installed/worker-ready without the real
//      capability behind it. Never prompts on its own; only a steward's own
//      click on this app's button ever calls `.prompt()`.
//
// It is a plain script rather than a module on purpose: it must be running
// before `main.js` makes its first request, so that no message from the worker
// is missed. It touches nothing else on the page.

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
    // Standing information, never a control: everything inside this element is
    // built right here and not one of it is interactive (two paragraphs and a
    // list of chips). It is `position: fixed` at the bottom-left and, at 390px,
    // full width -- so at that width it sits directly over the bottom of Home,
    // which is the list of manager sessions. Measured 2026-09-08 at 390x844
    // with the network down: a tap on `.home-manager-card` was swallowed by
    // `.offline-headline`, so the one navigation §10 depends on -- open a
    // manager, read what was last synced -- could not be made at all on a
    // phone. Said here, on the element this file owns and fills, rather than in
    // another lane's stylesheet.
    el.style.pointerEvents = 'none';
    // The one exception, and the reason this is not simply a stylesheet rule:
    // the banner is `max-height: 40vh; overflow: auto`, and the chips are the
    // only part of it that can outgrow that. Left touchable, they still scroll
    // their own container, so nothing here trades a swallowed tap for a list
    // that cannot be read to the end.
    marks.style.pointerEvents = 'auto';
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

// ============================================================================
// 2. window.ConvergePWA.setPrincipal(user) — identity-safe caching
// ============================================================================

(function () {
  'use strict';

  window.ConvergePWA = window.ConvergePWA || {};

  // --------------------------------------------------- is there a worker at all
  //
  // Telling "this browser will never give us a worker" from "a worker is on its
  // way, or exists and is not answering" CANNOT be done from
  // `navigator.serviceWorker.controller` alone. A perfectly ordinary FIRST page
  // load also has no controller while registration and activation are still in
  // flight, and reading that as a capability gap would wave the identity check
  // through at exactly the moment `clients.claim()` is about to hand this page a
  // worker with someone else's caches already behind it. So the bare
  // `!controller` shortcut is not taken here; the outcome is OBSERVED.
  //
  // Three pieces of evidence, all required, none assumed:
  //   1. registration has SETTLED with no registration at all -- blocked by
  //      policy (`service_workers: block`), no secure context, or the call
  //      threw. `main.js` publishes that outcome as
  //      `window.ConvergePWA.registration`. When it is absent -- `offline.js`
  //      loaded on its own, which several tests do -- there is NO evidence, and
  //      the bounded fail-closed path below stands exactly as it did.
  //   2. no controller for this page, and
  //   3. no registration on this scope holding an active, installing or waiting
  //      worker.
  // Anything pending, ambiguous, slow, or unreadable yields '' -- no gap
  // claimed, and the 4s no-response rejection stays in force.
  var PROBE_MS = 1500;

  function bounded(promise, fallback) {
    return new Promise(function (resolve) {
      var done = false;
      function settle(value) {
        if (done) return;
        done = true;
        clearTimeout(timer);
        resolve(value);
      }
      var timer = setTimeout(function () { settle(fallback); }, PROBE_MS);
      Promise.resolve(promise).then(settle, function () { settle(fallback); });
    });
  }

  // true / false / null, where null means "could not look" -- never a gap.
  function anyLiveRegistration() {
    var sw = navigator.serviceWorker;
    var query;
    if (typeof sw.getRegistrations === 'function') {
      query = sw.getRegistrations().then(function (regs) { return regs || []; });
    } else if (typeof sw.getRegistration === 'function') {
      query = sw.getRegistration().then(function (reg) { return reg ? [reg] : []; });
    } else {
      return Promise.resolve(null);
    }
    return bounded(query, null).then(function (regs) {
      if (regs === null) return null;
      return regs.some(function (reg) {
        return !!(reg && (reg.active || reg.installing || reg.waiting));
      });
    });
  }

  // Resolves to a reason string ONLY when all three pieces of evidence agree
  // that there is nothing to ask; '' in every other case.
  function noWorkerAtAll() {
    var sw = navigator.serviceWorker;
    var published = window.ConvergePWA && window.ConvergePWA.registration;
    if (!published || typeof published.then !== 'function') return Promise.resolve('');
    return bounded(published, 'still-registering').then(function (reg) {
      if (reg === 'still-registering') return '';   // no settled outcome yet
      if (reg) return '';                            // a registration exists: ask it
      if (sw.controller) return '';                  // controlled: a worker is right there
      return anyLiveRegistration().then(function (live) {
        if (live === null || live) return '';
        return sw.controller ? '' : 'no-worker-registration';
      });
    }).catch(function () { return ''; });
  }

  // Asks the active worker to CHECK who this is against the real server --
  // `user` travels along only as a hint a worker may use for its own
  // diagnostics; the worker's own /api/boot fetch is what actually decides,
  // never this argument. Always SETTLES, never rejects, never hangs
  // indefinitely. That is the fail-closed
  // shape #3 asks for across every race named there: no service-worker
  // support, a worker that has not become active yet, one that restarted and
  // is slow to come back, or a controller that changes mid-flight all resolve
  // to a plain {ok, reason} rather than leaving Shell's `await` stuck or
  // throwing where Shell may not have a `catch`.
  function askWorkerToSetPrincipal(user) {
    return new Promise(function (resolve) {
      if (!('serviceWorker' in navigator)) { resolve({ ok: false, reason: 'no-service-worker' }); return; }
      var settled = false;
      function finish(value) {
        if (settled) return;
        settled = true;
        clearTimeout(timer);
        resolve(value);
      }
      // 4s is generous for a worker already installed and merely slow to
      // activate; a bound exists at all so a worker that never answers cannot
      // leave the caller waiting forever.
      var timer = setTimeout(function () { finish({ ok: false, reason: 'no-response' }); }, 4000);
      // Runs BESIDE `ready`, never instead of it: where workers are explicitly
      // unavailable `navigator.serviceWorker.ready` never settles at all, so the
      // only other thing that ever answers there is the 4s no-response timeout,
      // which is a rejection. This resolves first ONLY on the three-part
      // evidence above; where a worker exists or may yet appear it resolves to
      // '' and changes nothing.
      noWorkerAtAll().then(function (gap) {
        if (gap) finish({ ok: false, reason: gap });
      });
      navigator.serviceWorker.ready.then(function (reg) {
        var worker = reg && reg.active;
        if (!worker) { clearTimeout(timer); finish({ ok: false, reason: 'no-active-worker' }); return; }
        var channel = new MessageChannel();
        channel.port1.onmessage = function (event) {
          clearTimeout(timer);
          var data = event.data || {};
          // `offlineConfirmed` is retained rather than dropped: it is how a
          // caller can tell an identity confirmed against a live server from
          // one the worker stood behind on its own cached-boot receipt while
          // the network was down (converge-ex30). Both are confirmations the
          // worker made; only one of them reached a server just now, and a
          // caller that cares must be able to see which.
          finish({
            ok: !!data.ok,
            cleared: !!data.cleared,
            reason: data.reason || '',
            user: data.user || '',
            offlineConfirmed: !!data.offlineConfirmed,
          });
        };
        try {
          worker.postMessage({ type: 'converge-set-principal', user: user }, [channel.port2]);
        } catch {
          clearTimeout(timer);
          finish({ ok: false, reason: 'post-failed' });
        }
      }).catch(function () {
        clearTimeout(timer);
        finish({ ok: false, reason: 'worker-never-ready' });
      });
    });
  }

  // `user` is whatever Shell read off the authenticated /api/boot response.
  // An empty or missing one is a failed/offline boot, not a confirmed change
  // of who is here — resolved rather than acted on, so it can never be used to
  // wipe good offline reads on the one path meant to preserve them.
  // Reasons that mean "there is no active worker/controller to ask at all" --
  // a distinct, non-failing capability gap. A browser-bypass session after a
  // certificate warning, or a worker that has not finished installing yet,
  // must still let ordinary authenticated network-only browsing proceed; it
  // just cannot claim offline/PWA capability it does not have. These resolve.
  var NO_WORKER_REASONS = ['no-service-worker', 'no-active-worker', 'worker-never-ready'];
  // `no-worker-registration` joins those three on exactly the evidence
  // `noWorkerAtAll` demands: registration settled with nothing, no controller,
  // and no active/installing/waiting registration anywhere. It is a capability
  // gap -- this browser has no PWA to offer -- and never a worker's silence.
  // Appended on its own line rather than folded into the literal above so the
  // exact allow-list `test_preview_pwa.py` reads out of this source, and the
  // invariant it guards -- that path RESOLVES, never rejects -- both stay
  // legible unchanged.
  NO_WORKER_REASONS = NO_WORKER_REASONS.concat(['no-worker-registration']);

  function unresolved(reason, result) {
    var err = new Error('setPrincipal did not confirm: ' + reason);
    err.ok = false;
    err.reason = reason;
    err.user = (result && result.user) || '';
    err.cleared = !!(result && result.cleared);
    return err;
  }

  // This seam now settles three ways, not two:
  //   - no worker/controller present at all (NO_WORKER_REASONS): resolves --
  //     a capability gap, not a failure, and never Shell's problem to catch.
  //   - an ACTIVE worker exists but did not confirm (timeout, a postMessage
  //     that threw, its own /api/boot re-check failing, storage refusing):
  //     rejects. A worker that can serve sensitive caches failing to confirm
  //     who is behind them must fail closed, not let a caller carry on with
  //     data it can no longer stand behind.
  //   - the worker DID confirm someone, but not who the caller expected (its
  //     own independent check raced Shell's boot fetch, or disagreed for any
  //     other reason): rejects. Stale boot data must never go on speaking for
  //     whoever the worker just confirmed instead. This is also what refuses a
  //     page that asks offline under a name the worker does not hold: the
  //     worker answers with ITS durable principal, never the asked-for one, so
  //     a mismatch is caught here rather than waved through.
  //
  // A confirmation carrying `offlineConfirmed: true` is the third of these --
  // a real confirmation the worker made, from its own receipt for a cached
  // /api/boot it had already validated for this exact client at this epoch
  // (converge-ex30), reached only after a live check genuinely failed. It is
  // checked against `name` exactly like any other, so nothing about being
  // offline relaxes the comparison.
  window.ConvergePWA.setPrincipal = function setPrincipal(user) {
    var name = (user == null ? '' : String(user)).trim();
    if (!name) return Promise.resolve({ ok: false, reason: 'no-user' });
    return askWorkerToSetPrincipal(name).then(function (result) {
      if (!result.ok && NO_WORKER_REASONS.indexOf(result.reason) !== -1) return result;
      if (!result.ok) return Promise.reject(unresolved(result.reason || 'unresolved', result));
      if (result.user !== name) return Promise.reject(unresolved('mismatch', result));
      return result;
    });
  };
}());

// ============================================================================
// 3. Install affordance — platform-web.v1 §9
// ============================================================================

(function () {
  'use strict';

  var BANNER_ID = 'pwaInstallBanner';
  var TEXT_CLASS = 'pwa-install-text';
  var INSTALL_BTN_ID = 'pwaInstallAction';
  var DISMISS_BTN_ID = 'pwaInstallDismiss';
  var DISMISS_KEY = 'converge-pwa-install-dismissed';

  var deferredPrompt = null;

  function el(id) { return document.getElementById(id); }

  // iOS Safari never fires `beforeinstallprompt` — Apple ships no such event —
  // so "wait for the event, offer nothing otherwise" would silently drop the
  // one browser where installing is most likely to matter. Detected instead
  // of assumed, and only ever used to offer honest MANUAL steps, never a
  // button that would do nothing when pressed.
  function isIOSSafari() {
    var ua = (navigator.userAgent || '');
    var iOS = /iPad|iPhone|iPod/.test(ua)
      || (/Macintosh/.test(ua) && typeof document !== 'undefined' && 'ontouchend' in document);
    var webkit = /AppleWebKit/.test(ua) && !/CriOS|FxiOS|EdgiOS|OPiOS/.test(ua);
    return iOS && webkit;
  }

  // Already running installed, on any platform: #9 says installing changes
  // only the frame, so there is nothing left for this section to offer.
  function isStandalone() {
    if (typeof navigator !== 'undefined' && navigator.standalone === true) return true; // iOS's own flag
    return typeof window.matchMedia === 'function' && window.matchMedia('(display-mode: standalone)').matches;
  }

  function dismissedBefore() {
    try { return window.localStorage.getItem(DISMISS_KEY) === '1'; } catch { return false; }
  }
  function rememberDismissed() {
    try { window.localStorage.setItem(DISMISS_KEY, '1'); } catch { /* no storage: may return next visit, honestly */ }
  }

  function hide() {
    var banner = el(BANNER_ID);
    if (banner) banner.hidden = true;
  }

  function show(message, offerInstallButton) {
    if (isStandalone() || dismissedBefore()) return;
    var banner = el(BANNER_ID);
    if (!banner) return;
    var textEl = banner.querySelector('.' + TEXT_CLASS);
    if (textEl) {
      textEl.textContent = '';
      textEl.appendChild(document.createTextNode(message + ' '));
      var link = document.createElement('a');
      link.href = '/setup';
      // What #9 actually promises: no store, no second build, and here is
      // where the same-origin fingerprint that makes that trustworthy lives.
      link.textContent = 'See what installing changes, and how to check the certificate.';
      textEl.appendChild(link);
    }
    var installBtn = el(INSTALL_BTN_ID);
    if (installBtn) installBtn.hidden = !offerInstallButton;
    banner.hidden = false;
  }

  // Suppressing the browser's own mini-infobar here is not "a forced install
  // popup" — it is the opposite: it means THIS banner, worded the same
  // everywhere and dismissible, is the only thing that ever asks. Nothing
  // calls `.prompt()` except a steward's own click on the button below.
  window.addEventListener('beforeinstallprompt', function (event) {
    event.preventDefault();
    deferredPrompt = event;
    show('Converge can be installed to a home screen or dock — no app store, no review queue.', true);
  });

  window.addEventListener('appinstalled', function () {
    deferredPrompt = null;
    hide();
  });

  function wire() {
    var installBtn = el(INSTALL_BTN_ID);
    if (installBtn) {
      installBtn.addEventListener('click', function () {
        if (!deferredPrompt) return; // capability withdrawn since shown: nothing to claim
        var chosen = deferredPrompt;
        deferredPrompt = null;
        chosen.prompt();
        chosen.userChoice.finally(hide);
      });
    }
    var dismissBtn = el(DISMISS_BTN_ID);
    if (dismissBtn) dismissBtn.addEventListener('click', function () { rememberDismissed(); hide(); });

    // Offered once, on arrival, only when no real install event is possible
    // here and none has already fired. A browser that DOES support
    // `beforeinstallprompt` gets that path instead, even on a platform that
    // also matches the iOS check below (there is none today, but the ordering
    // itself is the honesty rule: never show manual steps where the real
    // mechanism just worked).
    if (!isStandalone() && !deferredPrompt && isIOSSafari()) {
      show('Add Converge to your Home Screen: tap Share, then "Add to Home Screen".', false);
    }
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', wire);
  else wire();
}());
