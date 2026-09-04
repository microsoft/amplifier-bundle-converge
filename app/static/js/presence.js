// Courtesy presence (§10): who else has an editor open on this section.
//
// Until this file, "shown softly" meant the steward's own open editor, in the
// steward's own browser. A second person on a second machine was invisible,
// which is company only in the way a mirror is. `app/presence.py` is the
// channel; this is the half that beats into it and paints what comes back.
//
// Two rules shape everything below.
//
// **It never blocks.** A mark makes a section look occupied and says so in
// words; nothing here disables a control, and there is no route it could call
// that would. What actually stops two writes from overwriting each other is
// the collision path that already exists — `app/writes.py` refuses a sentence
// that moved, and actions.js offers Use combined · Keep mine · Review both.
//
// **It never re-renders the document.** A beat arriving every few seconds that
// called renderDirection() would rebuild `#documentModeContent` — and throw
// away whatever the steward was in the middle of typing. So the beat patches
// the sections it needs to and touches nothing else. That is why the marks are
// written here rather than only in render/direction.js.
import { $, state, data, escapeHtml } from './state.js';
import { api } from './api.js';

//: Every four seconds while a document is open. Slow enough to be nothing on
//: a LAN, fast enough that "within a few seconds" is true — the mark itself
//: stands for a full minute (app/presence.py's TTL_SECONDS), so a missed beat
//: is not a person disappearing.
const BEAT_MS = 4000;

export const presence = {
  others: [],     // live marks that are not yours
  queued: [],     // writers waiting on a section rather than writing it
  ttlSeconds: 60,
  trouble: '',    // the last refusal, in the server's own words
  beats: 0,
};

let holding = '';   // the section THIS browser has an editor open on
let timer = null;
let inFlight = false;

//: What the document surface is keyed on. A card's `section` is a path
//: ("Principles › 8"); the rendered section is its head, and the head is what
//: is shown softly, so the head is what a mark names.
export function holdSection(title) {
  const wanted = String(title || '');
  if (wanted === holding) return;
  holding = wanted;
  beatNow();
}

function where() {
  if (!state.managerId || !state.repoId || !state.docId) return null;
  return { mid: state.managerId, repoId: state.repoId, docId: state.docId };
}

//: Why a beat should not be sent, or '' to send it.
//:
//: With the network gone there is nobody to tell and nobody to see, and
//: beating anyway is actively worse than silence: the request reaches the
//: app's own service worker, which refuses a write while the network is down,
//: puts a line in the browser's log, and tells the page that a write failed —
//: a message about a signal the steward never asked for, on the one screen
//: already saying the app is offline.
//:
//: Two witnesses, because one is not enough. `navigator.onLine` is the
//: obvious one and it lies in a real window: after a reload with the network
//: already gone, a fresh document reports itself ONLINE again while nothing
//: it asks for arrives (measured 2026-09-04, and `app/tests/test_offline.py`'s
//: own harness says the same in its own words). The second is the service
//: worker's own news: it tells the page every time it served an answer from
//: the store, missed one, or refused a write, and it is the thing that
//: actually knows whether a request reached the network.
//:
//: That second witness is read with a clock rather than as a flag, on purpose.
//: The app's offline banner would have been the easy thing to read, and it is
//: sticky: `offline.js` clears its refusals when the network returns but keeps
//: believing the worker is offline until something asks the worker again, so a
//: beat gated on the banner could stay stood down long after the network came
//: back. "The worker said something did not arrive, recently" expires by
//: itself and cannot get stuck.
const HUSH_MS = 12000;
let lastMiss = 0;

if (typeof navigator !== 'undefined' && 'serviceWorker' in navigator) {
  navigator.serviceWorker.addEventListener('message', (event) => {
    const kind = (event && event.data && event.data.type) || '';
    if (kind === 'converge-offline-read' || kind === 'converge-offline-write' || kind === 'converge-offline-miss') {
      lastMiss = Date.now();
    }
  });
}

function unreachable() {
  if (typeof navigator !== 'undefined' && navigator.onLine === false) return 'this device is offline';
  if (lastMiss && Date.now() - lastMiss < HUSH_MS) return 'Converge cannot be reached from this device';
  return '';
}

function take(answer, at) {
  presence.others = (answer && answer.others) || [];
  presence.queued = (answer && answer.queued) || [];
  presence.ttlSeconds = (answer && answer.ttlSeconds) || presence.ttlSeconds;
  presence.trouble = '';
  presence.beats += 1;
  // The document may have been switched while the request was in the air.
  // Painting the answer to a different document would be a lie about this one.
  const now = where();
  if (!now || now.repoId !== at.repoId || now.docId !== at.docId) return;
  paintPresence();
}

export async function beatNow() {
  const at = where();
  if (!at || inFlight) return;
  const away = unreachable();
  if (away) {
    presence.trouble = `${away}, so nobody can be told you are here and nobody else can be seen`;
    presence.others = [];
    presence.queued = [];
    paintPresence();
    return;
  }
  inFlight = true;
  try {
    take(await api.presenceBeat(at.mid, { repoId: at.repoId, docId: at.docId, section: holding }), at);
  } catch (err) {
    // Never a toast and never console.error: presence is a courtesy, and a
    // courtesy that interrupts the reading is worse than one that is quietly
    // absent. The reason is kept and shown in the Details fold instead.
    presence.trouble = (err && err.message) || 'the presence channel did not answer';
    presence.others = [];
    presence.queued = [];
    paintPresence();
  } finally {
    inFlight = false;
  }
}

export function startPresence() {
  if (timer) return;
  // Deliberately no beat right here. `startPresence` runs inside boot, and
  // right after a reload the page has not yet been told whether anything it
  // asked for actually arrived — `unreachable()` has nothing to go on yet, so
  // a beat sent into that gap is the one request that would put a line in the
  // browser's log on a screen that is simply offline. The first beat is the
  // first tick instead, and opening an editor forces one immediately anyway
  // (holdSection), which is the moment that actually has to be prompt.
  timer = setInterval(beatNow, BEAT_MS);
}

export function stopPresence() {
  if (!timer) return;
  clearInterval(timer);
  timer = null;
}

// --------------------------------------------------------------------------
// what a mark says
// --------------------------------------------------------------------------

function names(rows) {
  const unique = [...new Set(rows.map((r) => String(r.user || 'someone')))];
  if (unique.length === 1) return unique[0];
  if (unique.length === 2) return `${unique[0]} and ${unique[1]}`;
  return `${unique.slice(0, -1).join(', ')} and ${unique[unique.length - 1]}`;
}

function ago(rows) {
  const seconds = Math.min(...rows.map((r) => Number(r.ago) || 0));
  return seconds < 10 ? 'just now' : `${seconds}s ago`;
}

//: Everything live about one section, as one sentence. Returns '' when the
//: section is yours alone — the absence of a mark is the normal case and it
//: should cost nothing to draw.
export function presenceLine(title) {
  const key = String(title || '');
  const editing = presence.others.filter((one) => String(one.section) === key);
  const waiting = presence.queued.filter((one) => String(one.section) === key);
  const parts = [];
  if (editing.length) {
    parts.push(`${names(editing)} ${editing.length > 1 ? 'are' : 'is'} editing this section `
      + `(${ago(editing)}). Nothing is locked — if you both write, you are offered a choice.`);
  }
  if (waiting.length) {
    parts.push(`${names(waiting)} has a write queued on this section rather than making it.`);
  }
  return parts.join(' ');
}

export function presenceLineHtml(title) {
  const said = presenceLine(title);
  if (!said) return '';
  return `<p class="presence-line" data-presence-for="${escapeHtml(String(title || ''))}">${escapeHtml(said)}</p>`;
}

// --------------------------------------------------------------------------
// painting, without disturbing the reading
// --------------------------------------------------------------------------

export function paintPresence() {
  const surface = $('documentModeContent');
  if (!surface) return;
  // The Details fold under an open editor is written at render time and the
  // editor outlives many beats, so it is repainted here too — otherwise it
  // would still be claiming the channel is fine a minute after it stopped
  // answering, which is the exact kind of stale confidence this fold exists
  // to prevent.
  const standing = surface.querySelector('[data-presence-standing]');
  if (standing) {
    const said = presenceStanding();
    if (standing.textContent !== said) standing.textContent = said;
  }
  surface.querySelectorAll('section[data-section]').forEach((el) => {
    const title = el.dataset.section || '';
    const said = presenceLine(title);
    let line = el.querySelector('[data-presence-for]');
    el.classList.toggle('is-editing-elsewhere', !!said);
    if (!said) {
      if (line) line.remove();
      return;
    }
    if (!line) {
      line = document.createElement('p');
      line.className = 'presence-line';
      line.setAttribute('data-presence-for', title);
      const heading = el.querySelector('h2');
      if (heading && heading.nextSibling) el.insertBefore(line, heading.nextSibling);
      else el.appendChild(line);
    }
    if (line.textContent !== said) line.textContent = said;
  });
}

//: What the Details fold under an open editor says about the channel itself,
//: so the honesty is on the screen rather than in a comment. It reports what
//: is actually true this second, including when the channel is not answering.
export function presenceStanding() {
  if (presence.trouble) {
    return `The presence channel is not answering: ${presence.trouble}. `
      + 'Your own editing still works, and a collision is still met with a choice.';
  }
  const others = presence.others.length;
  const doc = data.doc ? ` of ${data.doc.title}` : '';
  const held = others
    ? `${names(presence.others)} ${others > 1 ? 'have editors' : 'has an editor'} open on `
      + `${[...new Set(presence.others.map((o) => o.section))].join(', ')}${doc}.`
    : `Nobody else has an editor open on this document.`;
  return `${held} Marks are kept in the app's memory, never in the repository, and one stops `
    + `standing after ${presence.ttlSeconds}s without a refresh. Presence is courtesy: it never `
    + `blocks a write, and a collision is met with a choice rather than a lock.`;
}
