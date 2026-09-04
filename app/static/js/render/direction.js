// Direction: the living agreement — read, what changed, one worked-out decision, history.
//
// Nothing in the Changes view is staged, mocked, or acknowledged with a message
// and then forgotten. Keep, Edit, Restore and Mark all as read each call the
// server and each re-read the document afterwards, so what is on the screen is
// what is on disk. That is why no handler in this file reports an outcome of
// its own: every one of them hands off to actions.js, which makes the request
// and then says what the server actually did.
//
// The Reading view holds to the same rule. Editing a draft in place goes to
// the same document-saving write the Changes view uses, and it is offered on a
// paragraph only where that write can still land — the lock itself is read by
// the server, never guessed here. Ask is the one control on this screen whose
// route the app does not answer yet: it fails out loud and names the work
// (converge-ddt) rather than looking like it did something.
import { $, qsa, state, data, escapeHtml, currentRepo, currentDoc, readBookmark } from '../state.js';
import { hooks } from '../refresh.js';
import { handleDecision, keepChange, saveChangeEdit, restoreChange, restoreScope, markAllRead, editDoc, reconcile, openAsk, copyText, confirmLock } from '../actions.js';
import { startPresence, holdSection, paintPresence, presenceLineHtml, presenceStanding } from '../presence.js';

const DECISION_BUTTONS = [
  ['ratified', 'Ratify', 'primary-button'],
  ['ratified-with-edits', 'Ratify with edits', 'outline-button'],
  ['declined', 'Decline', 'outline-button'],
  ['later', 'Later', 'outline-button'],
];

// The three choices experience-direction.v1 §10 names when two writes collide.
// They are offered together or not at all: a steward who is only allowed to
// keep their own wording has not been offered a choice.
const RECONCILE_CHOICES = [
  ['use-combined', 'Use combined', 'primary-button'],
  ['keep-mine', 'Keep mine', 'outline-button'],
  ['review-both', 'Review both', 'outline-button'],
];

const STATE_LABEL = { kept: 'Kept', gap: 'Not yet', draft: 'Draft' };

function plural(n, word) { return `${n} ${word}${n === 1 ? '' : 's'}`; }

export function rawTextForDoc() {
  return data.doc && data.doc.raw ? data.doc.raw : '';
}

// --------------------------------------------------------------------------
// §3 — copy as rendered, copy as source, zoom, width
// --------------------------------------------------------------------------
//
// The clause names five reader abilities and two of them are copies: what the
// page shows, and the file behind it. Until now one control called
// `copyRendered` handed over `doc.raw` — the SOURCE, under a name that said
// otherwise (converge-jdm). So there are two controls, and each copies what
// its label promises.

//: Tags that end a line when the render is read as text. Everything else is
//: inline and joins the line it sits on.
const BLOCK_TAGS = new Set([
  'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'tr', 'pre', 'blockquote',
  'div', 'section', 'article', 'ul', 'ol', 'dl', 'dt', 'dd', 'hr', 'table',
]);

function textInto(node, out) {
  node.childNodes.forEach((child) => {
    if (child.nodeType === 3) { out.push(child.nodeValue); return; }
    if (child.nodeType !== 1) return;
    const tag = child.tagName.toLowerCase();
    if (tag === 'br') { out.push('\n'); return; }
    const block = BLOCK_TAGS.has(tag);
    if (block) out.push('\n');
    textInto(child, out);
    if (block) out.push('\n');
  });
}

//: The document as the Reading view shows it, in plain text: headings and
//: prose, no Markdown punctuation. Read from the same rendered sections the
//: screen draws, so what is copied is what was seen.
export function renderedTextForDoc() {
  const doc = data.doc;
  if (!doc) return '';
  const holder = document.createElement('div');
  holder.innerHTML = (doc.sections || [])
    .map(([title, html]) => `<h2>${escapeHtml(title)}</h2>${html}`).join('');
  const out = [];
  textInto(holder, out);
  const body = out.join('').replace(/[ \t]+\n/g, '\n').replace(/\n{3,}/g, '\n\n').trim();
  // The screen shows the title above the sections, so the copy carries it too —
  // but `sections_of` in app/data.py gives the first section the H1's own words
  // whenever anything sits under it, and a document written that way would
  // otherwise hand the steward its title twice. Measured on both shapes.
  const first = ((doc.sections || [])[0] || [])[0] || '';
  const title = String(doc.title || '').trim();
  return title && first.trim() !== title ? `${title}\n\n${body}` : body;
}

//: Zoom is the reading column's own text size and nothing else's, so the
//: controls never grow out of the toolbar they sit in. Kept on the device
//: rather than the server: it is how one person's eyes read today, not a fact
//: about the document.
const ZOOM_STEPS = [0.8, 0.9, 1, 1.15, 1.3, 1.5, 1.75];
const ZOOM_KEY = 'converge:zoom';
let zoomAt = ZOOM_STEPS.indexOf(1);

function readZoom() {
  try {
    const at = ZOOM_STEPS.indexOf(Number(localStorage.getItem(ZOOM_KEY)));
    if (at >= 0) zoomAt = at;
  } catch { /* storage blocked: this device reads at 100% */ }
}

function applyZoom() {
  const factor = ZOOM_STEPS[zoomAt];
  $('documentSurface').style.setProperty('--doc-zoom', String(factor));
  $('zoomLevel').textContent = `${Math.round(factor * 100)}%`;
  $('zoomOut').disabled = zoomAt === 0;
  $('zoomIn').disabled = zoomAt === ZOOM_STEPS.length - 1;
}

function stepZoom(direction) {
  const next = Math.min(ZOOM_STEPS.length - 1, Math.max(0, zoomAt + direction));
  if (next === zoomAt) return;
  zoomAt = next;
  try { localStorage.setItem(ZOOM_KEY, String(ZOOM_STEPS[zoomAt])); } catch { /* storage blocked */ }
  applyZoom();
}

// --------------------------------------------------------------------------
// converge-2ib — the objective, clamped, with the whole sentence one gesture away
// --------------------------------------------------------------------------
//
// `#objectiveText` is filled by render/top.js with the first sentence of the
// batch's Outcome — ~300 characters in a real batch. The clamp is CSS; this
// only says whether there is anything hidden to show, and offers the gesture
// when there is.
function syncObjective() {
  const text = $('objectiveText');
  const more = $('objectiveMore');
  if (!text || !more) return;
  const block = text.closest('.objective-block');
  const whole = (text.textContent || '').trim();
  text.title = whole;
  const open = block.classList.contains('objective-open');
  const clipped = text.scrollHeight - text.clientHeight > 1;
  more.classList.toggle('hidden', !open && !clipped);
  more.textContent = open ? 'Show less' : 'Show all';
  more.setAttribute('aria-expanded', open ? 'true' : 'false');
}

function toggleObjective() {
  const block = $('objectiveText').closest('.objective-block');
  block.classList.toggle('objective-open');
  syncObjective();
}

// --------------------------------------------------------------------------
// platform-web.v1 §10 — this document's own sync moment, on this document
// --------------------------------------------------------------------------
//
// §10 asks that what is shown while the network is down is "marked with the
// moment it came from". The offline banner says that for the device as a whole,
// in the corner of the screen; this says it for the document the steward is
// actually reading, beside its own title, at every width (converge-baz).
//
// The moment is the one `app/static/sw.js` stored with THIS document's payload,
// carried out of that response by api.js as `doc.storedCopy`. A document read
// from the server just now carries no mark at all, because there is nothing
// stale to say about it.
//
// The words are formatted exactly as offline.js formats the banner's: two
// surfaces naming one payload must name one time. They are not shared through
// an import because offline.js is a plain script that has to be running before
// any module loads, and so exports nothing.
function syncedWord(iso) {
  if (!iso) return 'an unrecorded moment';
  const at = new Date(iso);
  if (isNaN(at.getTime())) return 'an unrecorded moment';
  const clock = at.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  const sameDay = at.toDateString() === new Date().toDateString();
  return sameDay ? clock : `${at.toLocaleDateString([], { month: 'short', day: 'numeric' })} ${clock}`;
}

export function renderStoredMark(doc) {
  const mark = $('docSyncedAt');
  if (!mark) return;
  const stored = doc && doc.storedCopy;
  if (!stored) {
    mark.hidden = true;
    mark.textContent = '';
    mark.removeAttribute('title');
    return;
  }
  const when = syncedWord(stored.syncedAt);
  mark.textContent = `Stored copy · as of ${when}`;
  mark.title = `This document was not read from the server just now. What is on screen is the copy stored on this device, as of ${when}.`;
  mark.hidden = false;
}

// --------------------------------------------------------------------------
// §11 — the lock gate: four conditions, shown, and a control that tracks them
// --------------------------------------------------------------------------
//
// The Freeze Bar's four conditions, in the contract's own order. Three are a
// judgement only a reader can make and the steward answers them here; the
// third the app can answer from the document's own ledger standing, so it
// does, with the evidence beside it — asking a steward to attest to something
// the project already measures is how an attestation becomes a formality.
//
// Nothing is ticked for the steward, and no answer survives moving to another
// document: an answer about the vision is not an answer about a contract.
// And nothing locks on its own — the control is the last step, never the
// first.
const LOCK_CONDITIONS = [
  ['means', 'It says what it means'],
  ['example', 'It carries a real example of right and wrong'],
  ['reality', 'It can be checked against reality'],
  ['steward', 'You have read it and agreed'],
];

//: The steward's own answers, for ONE document.
let stewardAnswers = { key: '', means: false, example: false, steward: false };

function lockKey() { return `${state.repoId}\u001f${state.docId}`; }

function answersHere() {
  if (stewardAnswers.key !== lockKey()) {
    stewardAnswers = { key: lockKey(), means: false, example: false, steward: false };
  }
  return stewardAnswers;
}

//: Which conditions are met right now, and what says so. `reality` is the
//: ledger's word about this document (`draft` means no row watches it, which
//: is exactly "cannot be checked against reality yet").
function lockState(doc) {
  const answers = answersHere();
  const watched = !!(doc && doc.state && doc.state !== 'draft');
  const standing = (doc && doc.standingSentence)
    || 'This project keeps no record yet of whether this is being kept.';
  return {
    met: { means: answers.means, example: answers.example, reality: watched, steward: answers.steward },
    evidence: {
      means: 'Your word — only a reader can say whether the wording means one thing.',
      example: 'Your word — the document has to carry the example, not the promise of one.',
      reality: `${(doc && doc.standing) || "Can't check"} — ${standing}`,
      steward: 'Your word, and it is the last one. Nothing locks on its own.',
    },
  };
}

export function renderLockGate() {
  const gate = $('lockGate');
  if (!gate) return;
  const doc = data.doc;
  const lock = (doc && doc.locked) || '';
  const { met, evidence } = lockState(doc);
  const count = LOCK_CONDITIONS.filter(([key]) => met[key]).length;

  LOCK_CONDITIONS.forEach(([key]) => {
    const row = gate.querySelector(`[data-lock-row="${key}"]`);
    if (!row) return;
    row.classList.toggle('met', !!met[key]);
    const box = row.querySelector('[data-lock-check]');
    if (box) {
      box.checked = !!met[key] && !lock;
      box.disabled = !!lock || !doc;
    }
    const mark = row.querySelector('[data-lock-mark]');
    if (mark) mark.textContent = met[key] ? '✓' : '•';
    const said = row.querySelector('[data-lock-evidence]');
    if (said) said.textContent = evidence[key];
  });

  const chip = $('lockGateCount');
  chip.className = `lock-gate-count${lock ? ' locked' : count === 4 ? ' met' : ''}`;
  if (lock) {
    $('lockGateHead').textContent = 'This document is locked';
    chip.textContent = lock;
    $('lockGateWhy').textContent = `Its first line carries ${lock}, so app/writes.py will not edit it in place: every change to it, yours included, is written as a proposal beside it for you to answer.`;
    $('lockGateNote').textContent = 'Unlocking is not a control here — a locked document changes by the same proposal it took to lock it.';
  } else {
    $('lockGateHead').textContent = 'Locking this document';
    chip.textContent = `${count} of 4 met`;
    $('lockGateWhy').textContent = 'A document is locked only when all four of the Freeze Bar\u2019s conditions are met. Three are yours to answer; the third is read from this project\u2019s own ledger, so it is not yours to tick past.';
    const short = LOCK_CONDITIONS.filter(([key]) => !met[key]).map(([, label]) => label.toLowerCase());
    $('lockGateNote').textContent = count === 4
      ? 'Locking is irreversible in the way that matters: from then on this document changes by proposal.'
      : `Not yet: ${short.join('; ')}.`;
  }
  $('lockButton').disabled = !!lock || count < 4 || !doc;
}

//: The control's last step. It is inert unless all four are met, but the
//: check is made again here rather than trusted: what actually keeps a
//: document from being locked is the server's write, so forcing the control
//: in the browser reaches the same refusal.
function requestLock() {
  const doc = data.doc;
  if (!doc || doc.locked) return;
  const { met, evidence } = lockState(doc);
  const answered = LOCK_CONDITIONS
    .filter(([key]) => met[key])
    .map(([key, label]) => (key === 'reality' ? `${label} — ${evidence.reality}` : `${label} — your word`));
  if (answered.length < 4) return;
  confirmLock(doc, answered);
}

//: The Direction toolbar and the header outlive a re-render, so their controls
//: are wired once. `#copyRendered` is REPLACED rather than added to: main.js
//: binds it to `copyText(data.doc.raw)` — the source — and main.js is not this
//: lane's file. Replacing the node drops that listener, and the button then
//: does what its label says. Safe to do here because main.js's `wire()` is
//: synchronous at boot, before any render, so nothing binds it again after.
let toolsWired = false;

function wireDocTools() {
  if (toolsWired) return;
  toolsWired = true;
  const stale = $('copyRendered');
  const fresh = stale.cloneNode(true);
  stale.replaceWith(fresh);
  fresh.addEventListener('click', () => copyText(renderedTextForDoc()));
  $('copySource').addEventListener('click', () => copyText(rawTextForDoc()));
  $('zoomIn').addEventListener('click', () => stepZoom(1));
  $('zoomOut').addEventListener('click', () => stepZoom(-1));
  $('objectiveMore').addEventListener('click', toggleObjective);
  qsa('[data-lock-check]').forEach((box) => box.addEventListener('change', () => {
    answersHere()[box.dataset.lockCheck] = box.checked;
    renderLockGate();
  }));
  $('lockButton').addEventListener('click', requestLock);
  readZoom();
  applyZoom();
  // §10: start beating into the presence channel. Once, here, rather than in
  // main.js — main.js is not this lane's file, and the Direction surface is
  // the only place an editor is opened.
  startPresence();
}

export function renderRepoTree() {
  const filter = $('repoFilter');
  const wanted = ['all', ...data.repoList.map((r) => r.id)].join('|');
  if (filter.dataset.built !== wanted) {
    filter.innerHTML = '<option value="all">All repos</option>';
    data.repoList.forEach((r) => {
      const opt = document.createElement('option');
      opt.value = r.id;
      opt.textContent = r.name;
      filter.appendChild(opt);
    });
    filter.dataset.built = wanted;
  }
  filter.value = state.repoFilter;
  const visible = state.repoFilter === 'all' ? data.repoList : data.repoList.filter((r) => r.id === state.repoFilter);
  $('repoTree').innerHTML = visible.map((repo) => `
      <div class="repo-group">
        <div class="repo-name"><span>${escapeHtml(repo.name)}</span><span>⌄</span></div>
        ${repo.docs.map((doc) => `<button class="repo-doc ${doc.id === state.docId && repo.id === state.repoId ? 'active' : ''}" type="button" data-repo="${escapeHtml(repo.id)}" data-doc="${escapeHtml(doc.id)}"><span>${escapeHtml(doc.title)}</span><span class="doc-state-mini ${doc.state === 'kept' ? '' : 'gap'}"></span></button>`).join('')}
      </div>`).join('');
  qsa('[data-doc]', $('repoTree')).forEach((btn) => btn.addEventListener('click', () => {
    hooks.selectDoc(btn.dataset.repo, btn.dataset.doc);
  }));
}

// A card's section is a path — "Principles › 8" — and a rendered section is
// its own heading, so the top of the path is what marks the section changed.
function sectionHead(card) {
  return String(card.section || '').split(' › ')[0];
}

function shorten(text, limit = 64) {
  const one = String(text || '').replace(/\s+/g, ' ').trim();
  return one.length > limit ? `${one.slice(0, limit - 1)}…` : one;
}

// experience-direction.v1 §10: while a person is editing, the section is shown
// softly and a collision is met with a choice rather than a lost sentence.
// The soft marking now carries a second person: `app/presence.py` keeps a mark
// per section per steward, this browser beats into it while its editor is open
// (presence.js), and a mark that stops being refreshed stops standing after a
// minute. The marking is courtesy and nothing else — no control here is
// disabled by someone else's mark, and the collision path is what actually
// keeps two writes from overwriting each other.
function editPanel(doc, card) {
  const lock = doc.locked || '';
  const clash = state.collision && String(state.collision.section) === String(card.section) ? state.collision : null;
  return `<div class="change-edit" data-editing="${escapeHtml(card.id)}">
      <p class="muted lock-note">You are editing this section. Anyone else reading this document sees it shown softly, with your name on it, while you write — that is the presence, so a change landing underneath you is offered as a choice rather than applied over you.${lock ? ` This document is ${escapeHtml(lock)}, so saving writes a proposal beside it and the document itself is not touched.` : ''}</p>
      <label for="read-edit-${escapeHtml(card.id)}">The wording you want instead</label>
      <textarea id="read-edit-${escapeHtml(card.id)}" rows="3">${escapeHtml(card.now || card.before)}</textarea>
      ${clash ? collisionPanel(clash) : ''}
      <div class="change-edit-actions">
        <button class="outline-button" data-edit="cancel" type="button">Cancel</button>
        <button class="primary-button" data-edit="save" data-change-id="${escapeHtml(card.id)}" type="button">${lock ? 'Propose this wording' : 'Save'}</button>
      </div>
      <details><summary class="muted">Details</summary><p class="muted" data-presence-standing>${escapeHtml(presenceStanding())}</p></details>
    </div>`;
}

function collisionPanel(clash) {
  return `<div class="changes-banner">
      <div><strong>This moved while you were writing.</strong>
        <span class="muted">The document now says “${escapeHtml(shorten(clash.theirs) || 'something this reading no longer shows')}”. You wrote “${escapeHtml(shorten(clash.mine))}”. Nothing has been written yet.</span></div>
      <div class="changes-banner-actions">
        ${RECONCILE_CHOICES.map(([value, label, cls]) => `<button class="${cls}" data-reconcile="${value}" type="button">${label}</button>`).join('')}
      </div>
    </div>`;
}

// §5: editing is offered exactly where it is legal. What is legal is decided
// by the server — `app/writes.py` reads the document's own H1 — and what is
// possible is the sentences the document-saving write can still find, which
// is exactly this reading's own change cards. A section with none of those
// gets no edit control rather than one that would refuse.
function sectionFooter(doc, title, mine) {
  const open = mine.find((c) => String(c.id) === String(state.editingChangeId)) || null;
  if (open) return editPanel(doc, open);
  const lock = doc.locked || '';
  const edits = mine.map((c) => `<button class="outline-button" data-edit="open" data-change-id="${escapeHtml(c.id)}" type="button" title="${escapeHtml(c.now || c.before)}">${lock ? 'Propose wording for' : 'Edit'} “${escapeHtml(shorten(c.now || c.before, 40))}”</button>`).join('');
  return `<div class="change-actions">
      <button class="outline-button" data-ask data-ask-scope="paragraph" data-ask-section="${escapeHtml(title)}" type="button">Ask about this paragraph</button>
      ${edits}
    </div>`;
}

export function renderRead() {
  const doc = data.doc;
  if (!doc) return '<p class="muted">Loading document…</p>';
  if (state.raw) return `<pre class="raw-view">${escapeHtml(doc.raw || '')}</pre>`;
  const cards = doc.changes || [];
  const changedSections = new Set(cards.map(sectionHead));
  const sectionHtml = (doc.sections || []).map(([title, content]) => {
    const mine = cards.filter((c) => sectionHead(c) === title);
    const editing = mine.some((c) => String(c.id) === String(state.editingChangeId));
    // §10 presence. `is-editing` is this browser's own open editor;
    // `is-editing-elsewhere` is somebody else's, carried by the channel in
    // app/presence.py. Both are soft marks and neither disables anything.
    // `data-section` is what presence.js repaints against between renders —
    // it never rebuilds this HTML, because doing so while a steward is typing
    // would throw their sentence away.
    const elsewhere = presenceLineHtml(title);
    return `
      <section data-section="${escapeHtml(title)}" class="${changedSections.has(title) ? 'marked-change' : ''}${editing ? ' is-editing' : ''}${elsewhere ? ' is-editing-elsewhere' : ''}">
        <h2>${escapeHtml(title)}</h2>
        ${elsewhere}
        ${content}
        ${sectionFooter(doc, title, mine)}
      </section>`;
  }).join('');
  const changeCount = cards.length;
  const proposalCount = (doc.proposals || []).length;
  const lock = doc.locked || '';
  const editable = lock
    ? `This document is ${escapeHtml(lock)}, so a wording you write here becomes a proposal beside it.`
    : `${plural(changeCount, 'sentence')} can be edited here; saving commits it in your name.`;
  const banner = `<div class="since-banner"><div><strong>Since the last ratified version:</strong> ${plural(changeCount, 'sentence')} changed · ${plural(proposalCount, 'proposal')} open<br><span class="muted">${editable}</span></div><button type="button" data-inline-mode="changes">Show highlights</button></div>`;
  return banner + (sectionHtml || '<p class="muted">This document has no sections yet.</p>');
}

const KIND_WORD = { new: 'New', changed: 'Changed', removed: 'Removed' };
const RESTORE_WORD = {
  new: 'Take this addition back out',
  changed: 'Restore previous wording',
  removed: 'Put this sentence back',
};

function changeSides(c) {
  if (c.kind === 'new') {
    return `<div class="change-comparison one-sided"><div class="change-side added"><span>New — nothing stood here before</span><p>${escapeHtml(c.now)}</p></div></div>`;
  }
  if (c.kind === 'removed') {
    return `<div class="change-comparison one-sided"><div class="change-side"><span>Removed</span><p>${escapeHtml(c.before)}</p></div></div>`;
  }
  return `<div class="change-comparison"><div class="change-side"><span>Before</span><p>${escapeHtml(c.before)}</p></div><div class="change-side added"><span>Now</span><p>${escapeHtml(c.now)}</p></div></div>`;
}

// §8: the granular choices are not a new kind of ratification — they build the
// one word already in the vocabulary. So the answer is offered where the
// choices are made, and it is the same `[data-decision]` control the Review
// sheet carries, reaching the same decision write. When no proposal is open
// there is nothing to answer, and the line says that rather than offering a
// button that would refuse.
function answerFromChoices(doc) {
  const open = (doc && doc.proposals) || [];
  if (!open.length) {
    return '<span class="muted">Your keeping is remembered for you, and goes into the record with your word when a proposal is open.</span>';
  }
  return `<button class="outline-button" data-decision="ratified-with-edits" data-decision-label="Ratify with edits" type="button">Answer with these choices</button>`;
}

export function renderChanges() {
  const doc = data.doc;
  const changeRows = (doc && doc.changes) || [];
  const reading = (doc && doc.reading) || {};
  const lock = doc && doc.locked ? doc.locked : '';
  if (!changeRows.length) {
    return `<div class="changes-banner"><div><strong>You are up to date.</strong>
        <span class="muted">Nothing has changed in this document since you last read it${reading.sinceSource ? ` — ${escapeHtml(reading.sinceSource)}` : ''}.</span></div></div>`;
  }
  const keptCount = changeRows.filter((c) => c.kept).length;
  const allKept = keptCount === changeRows.length;
  const banner = `<div class="changes-banner ${allKept ? 'all-kept' : ''}" data-all-kept="${allKept ? 'true' : 'false'}">
      <div><strong>Since you last read${reading.sinceShort ? ` · ${escapeHtml(reading.sinceShort)}` : ''}</strong>
        <span class="muted">${escapeHtml(reading.sinceSource || 'the previous version of this document')}</span></div>
      <div class="changes-banner-actions">
        <span class="kept-count">${keptCount} of ${changeRows.length} kept</span>
        ${answerFromChoices(doc)}
        <button class="${allKept ? 'primary-button' : 'outline-button'}" data-change-all="read" type="button">Mark all as read</button>
      </div>
    </div>`;
  const lockNote = lock
    ? `<p class="muted lock-note">This document is ${escapeHtml(lock)}. Editing or restoring here writes a proposal beside it — the document itself is not touched.</p>`
    : '';
  return banner + lockNote + `<div class="change-list">${changeRows.map((c) => `
      <article class="change-card ${c.kept ? 'kept' : ''}" data-change-id="${escapeHtml(c.id)}">
        <div class="change-card-header">
          <strong>${escapeHtml(c.section || 'This document')}</strong>
          <span class="change-kind ${escapeHtml(c.kind)}">${KIND_WORD[c.kind] || 'Changed'}</span>
          <span class="change-stamp" title="${escapeHtml(c.source)}">${escapeHtml(c.sourceSha)} · ${escapeHtml(c.sourceDate)}</span>
          <span class="muted change-source" title="${escapeHtml(c.source)}">${escapeHtml(c.sourceSubject)}</span>
        </div>
        ${changeSides(c)}
        <div class="change-edit hidden">
          <label for="edit-${escapeHtml(c.id)}">The wording you want instead</label>
          <textarea id="edit-${escapeHtml(c.id)}" rows="4">${escapeHtml(c.now || c.before)}</textarea>
          <div class="change-edit-actions">
            <button class="outline-button" data-change-action="cancel-edit" type="button">Cancel</button>
            <button class="primary-button" data-change-action="save-edit" type="button">${lock ? 'Propose this wording' : 'Save and commit'}</button>
          </div>
        </div>
        <div class="change-actions">
          <button class="outline-button" data-change-action="edit" type="button">Edit wording…</button>
          <button class="outline-button" data-change-action="restore" type="button">${RESTORE_WORD[c.kind] || 'Restore previous wording'}</button>
          <button class="${c.kept ? 'kept-button' : 'primary-button'}" data-change-action="keep" type="button">${c.kept ? '✓ Kept' : 'Keep this change'}</button>
        </div>
      </article>`).join('')}</div>`;
}

export function renderReview() {
  const activeProposal = (data.doc && (data.doc.proposals || [])[0]) || null;
  if (!activeProposal) return '<p class="muted">No proposal is waiting on your word for this document.</p>';
  const decided = state.proposalDecision;
  return `<article class="review-sheet">
      <div class="review-hero"><span class="eyebrow">Proposal ${escapeHtml(activeProposal.id)} · ${escapeHtml(activeProposal.source)}</span><h2>${escapeHtml(activeProposal.title)}</h2><p>One worked-out decision instead of a raw diff.</p></div>
      <div class="review-grid">
        <div class="review-main">
          <div class="review-section"><h3>What changes</h3><p>${escapeHtml(activeProposal.title)}</p></div>
          ${activeProposal.why ? `<div class="review-section"><h3>Why now</h3><p>${escapeHtml(activeProposal.why)}</p></div>` : ''}
          ${activeProposal.unchanged ? `<div class="review-section"><h3>What does not change</h3><p>${escapeHtml(activeProposal.unchanged)}</p></div>` : ''}
          <div class="review-section"><h3>Evidence</h3><div class="evidence-list">${(activeProposal.evidence || []).map((x) => `<div class="evidence-item">✓ <span>${escapeHtml(x)}</span></div>`).join('') || '<p class="muted">No evidence was attached to this proposal.</p>'}</div></div>
          ${activeProposal.file ? `<details><summary class="muted">Details</summary><p><code>${escapeHtml(activeProposal.file)}</code></p></details>` : ''}
        </div>
        <div class="review-side">
          ${activeProposal.recommendation ? `<div class="review-section"><h3>Recommendation</h3><p><strong>${escapeHtml(activeProposal.recommendation)}</strong></p></div>` : ''}
          ${(activeProposal.tradeoffs || []).length ? `<div class="review-section"><h3>Trade-offs</h3><ul>${activeProposal.tradeoffs.map((x) => `<li>${escapeHtml(x)}</li>`).join('')}</ul></div>` : ''}
          <div class="decision-stack">
            ${DECISION_BUTTONS.map(([value, label, cls]) => `<button class="${cls}" data-decision="${value}" data-decision-label="${label}" type="button">${label}</button>`).join('')}
          </div>
          ${decided ? `<div class="decision-status">Recorded: ${escapeHtml(decided)}</div>` : ''}
        </div>
      </div>
    </article>`;
}

// §6: restoring from history is a real action at four scopes — a wording, a
// paragraph, a section, the whole document. Each control below is the app's own
// restore write over the sentences that scope covers; none of them stages
// anything or reports an outcome of its own. What the scopes are made of is
// this reading's change cards: `section` is the heading path ("Principles › 8"),
// so its head is the section and the whole path is the paragraph.
//
// The panel names the one snapshot a restore can actually reach — the
// steward's own read point — because that is the only earlier wording the
// server can still find. Restoring to any other row in the list needs a route
// the app does not answer; it is converge-4pq, and saying so is the honest
// alternative to a control that would look like time travel and not be.
function restorePanel(doc) {
  const cards = (doc && doc.changes) || [];
  const point = (doc && doc.reading) || {};
  const lock = (doc && doc.locked) || '';
  const at = point.sinceShort ? `${escapeHtml(point.sinceShort)}` : 'your read point';
  if (!cards.length) {
    return `<div class="history-actions"><p class="muted">Nothing has moved in this document since ${at}, so there is no earlier wording to put back. When something moves, restoring it at any of the four scopes appears here.</p></div>`;
  }
  const paragraphs = [...new Set(cards.map((c) => String(c.section || 'This document')))];
  const sections = [...new Set(cards.map(sectionHead))].filter(Boolean);
  const button = (scope, key, label) =>
    `<button class="outline-button" data-restore="${escapeHtml(scope)}" data-restore-key="${escapeHtml(key)}" type="button">${label}</button>`;
  return `<div class="history-actions">
      <p class="muted">Restore puts wording back as it stood at <strong>${at}</strong> — ${escapeHtml(point.sinceSource || 'the version you last read')}. ${lock ? `This document is ${escapeHtml(lock)}, so each restore writes a proposal beside it and the document itself is not touched.` : 'Each restore goes into the document and is committed in your name.'}</p>
      ${button('document', '', `Restore the whole document (${plural(cards.length, 'sentence')})`)}
      ${sections.map((s) => button('section', s, `Restore section “${escapeHtml(shorten(s, 28))}”`)).join('')}
      ${paragraphs.map((p) => button('paragraph', p, `Restore paragraph “${escapeHtml(shorten(p, 28))}”`)).join('')}
      ${cards.map((c) => button('wording', c.id, `Restore wording “${escapeHtml(shorten(c.before || c.now, 28))}”`)).join('')}
      <details><summary class="muted">Details</summary><p class="muted">Restoring to a snapshot older than your read point is not offered, because the app answers no route that reads a document at an arbitrary commit — only the sentences in this reading can be put back. Filed as converge-4pq.</p></details>
    </div>`;
}

export function renderHistory() {
  const doc = data.doc;
  const historyRows = (doc && doc.history) || [];
  if (!historyRows.length) return '<p class="muted">No recorded history for this document yet.</p>';
  const snap = historyRows.find((h) => h.id === state.historyId) || historyRows[0];
  return `<div class="history-layout"><div class="history-list">${historyRows.map((h) => `<button class="history-item ${h.id === snap.id ? 'active' : ''}" data-history="${escapeHtml(h.id)}" type="button"><strong>${escapeHtml(h.label)}</strong><br><span>${escapeHtml(h.date)}</span></button>`).join('')}</div>
      <div class="history-snapshot"><span class="eyebrow">${escapeHtml(snap.date)}</span><h3>${escapeHtml(snap.label)}</h3><p>${escapeHtml(snap.note)}</p>${snap.sha ? `<details><summary class="muted">Details</summary><p><code>${escapeHtml(snap.sha)}</code></p></details>` : ''}${restorePanel(doc)}</div></div>`;
}

export function renderProposalMini() {
  const activeProposal = (data.doc && (data.doc.proposals || [])[0]) || null;
  if (!activeProposal) {
    $('proposalCard').innerHTML = '<div class="proposal-mini"><span class="eyebrow">Proposals</span><h3>Nothing waiting on you</h3><span class="proposal-source">This document has no open proposal.</span></div>';
    return;
  }
  $('proposalCard').innerHTML = `<div class="proposal-mini"><span class="eyebrow">Active proposal ${escapeHtml(activeProposal.id)}</span><h3>${escapeHtml(activeProposal.title)}</h3><span class="proposal-source">${escapeHtml(activeProposal.source)}</span><dl>${activeProposal.why ? `<dt>Why now</dt><dd>${escapeHtml(activeProposal.why)}</dd>` : ''}${activeProposal.recommendation ? `<dt>Recommendation</dt><dd><strong>${escapeHtml(activeProposal.recommendation)}</strong></dd>` : ''}</dl><button id="reviewProposalMini" class="primary-button" type="button">Review proposal</button></div>`;
  $('reviewProposalMini').addEventListener('click', () => { state.docMode = 'review'; renderDirection(); });
}

export function renderDirection() {
  wireDocTools();
  renderRepoTree();
  const repo = currentRepo();
  const navDoc = currentDoc();
  const doc = data.doc;
  const changeCount = (doc && doc.changes ? doc.changes.length : 0);
  const proposalCount = (doc && doc.proposals ? doc.proposals.length : 0);

  $('docPath').textContent = doc ? doc.path : (repo && navDoc ? `${repo.name} / ${navDoc.title}` : '—');
  $('docTitle').textContent = doc ? doc.title : (navDoc ? navDoc.fullTitle : '');
  $('docUpdated').textContent = doc ? doc.updated : '';
  renderStoredMark(doc);
  const docState = doc ? doc.state : (navDoc ? navDoc.state : 'draft');
  $('docStateBadge').textContent = STATE_LABEL[docState] || 'Draft';
  $('docStateBadge').className = `state-badge ${docState}`;
  $('changesCountChip').textContent = changeCount;
  $('reviewCountChip').textContent = proposalCount;
  $('allChangesCount').textContent = changeCount;
  $('proposalCountNav').textContent = proposalCount;
  $('sinceSummary').textContent = `${plural(changeCount, 'sentence')} changed`;
  $('sinceDetail').textContent = `${plural(proposalCount, 'proposal')} open`;
  $('rawToggle').setAttribute('aria-pressed', state.raw ? 'true' : 'false');
  $('wideToggle').setAttribute('aria-pressed', state.wide ? 'true' : 'false');
  $('documentSurface').classList.toggle('wide', state.wide);
  state.bookmarked = readBookmark();
  $('bookmarkButton').setAttribute('aria-pressed', state.bookmarked ? 'true' : 'false');
  $('bookmarkButton').textContent = state.bookmarked ? '★' : '☆';
  qsa('[data-doc-mode]').forEach((btn) => {
    const active = btn.dataset.docMode === state.docMode;
    btn.classList.toggle('active', active);
    btn.setAttribute('aria-selected', active ? 'true' : 'false');
  });

  // §10: say what this browser has open before drawing, so the mark this
  // steward sets and the marks they are shown come from the same moment.
  // Scoped to the Reading view's editor, which is the one the clause is about.
  const openCard = ((doc && doc.changes) || []).find((c) => String(c.id) === String(state.editingChangeId));
  holdSection(state.docMode === 'read' && openCard ? sectionHead(openCard) : '');

  let html = '';
  if (state.docMode === 'read') html = renderRead();
  if (state.docMode === 'changes') html = renderChanges();
  if (state.docMode === 'review') html = renderReview();
  if (state.docMode === 'history') html = renderHistory();
  $('documentModeContent').innerHTML = html;
  attachDocumentModeHandlers();
  paintPresence();
  renderProposalMini();
  renderLockGate();
  syncObjective();

  const confidence = data.operation && data.operation.confidence;
  $('realityKept').textContent = confidence ? confidence.kept : '—';
  $('realityNotYet').textContent = confidence ? confidence.notyet : '—';
  $('realityBroken').textContent = confidence ? confidence.broken : '—';
}

export function attachDocumentModeHandlers() {
  qsa('[data-inline-mode]').forEach((btn) => btn.addEventListener('click', () => {
    state.docMode = btn.dataset.inlineMode;
    renderDirection();
  }));
  qsa('[data-change-all]').forEach((btn) => btn.addEventListener('click', markAllRead));
  // §6: one wiring for all four restore scopes. Nothing is staged and nothing
  // is decided here — the scope names which sentences, and actions.js makes
  // the app's own restore write for each of them.
  qsa('[data-restore]').forEach((btn) => btn.addEventListener('click', () => {
    restoreScope(btn.dataset.restore, btn.dataset.restoreKey || '');
  }));
  qsa('[data-change-action]').forEach((btn) => btn.addEventListener('click', () => {
    const card = btn.closest('.change-card');
    if (!card) return;
    const id = card.dataset.changeId;
    const row = ((data.doc && data.doc.changes) || []).find((c) => String(c.id) === String(id));
    const panel = card.querySelector('.change-edit');
    switch (btn.dataset.changeAction) {
      case 'edit':
        panel.classList.remove('hidden');
        card.querySelector('.change-actions').classList.add('hidden');
        panel.querySelector('textarea').focus();
        break;
      case 'cancel-edit':
        panel.classList.add('hidden');
        card.querySelector('.change-actions').classList.remove('hidden');
        break;
      case 'save-edit':
        saveChangeEdit(id, panel.querySelector('textarea').value);
        break;
      case 'restore':
        restoreChange(id);
        break;
      case 'keep':
        keepChange(id, !(row && row.kept));
        break;
      default:
        break;
    }
  }));
  // Editing a draft in place: open, cancel, or save. Save is the only one of
  // the three that leaves the browser, and it goes straight to the document
  // write — there is no staging step between the button and the file.
  qsa('[data-edit]').forEach((btn) => btn.addEventListener('click', () => {
    const what = btn.dataset.edit;
    if (what === 'open') {
      state.editingChangeId = btn.dataset.changeId;
      state.collision = null;
      renderDirection();
      return;
    }
    if (what === 'cancel') {
      state.editingChangeId = null;
      state.collision = null;
      renderDirection();
      return;
    }
    const box = btn.closest('.change-edit');
    const wording = box ? box.querySelector('textarea').value : '';
    editDoc(btn.dataset.changeId, wording);
  }));
  qsa('[data-reconcile]').forEach((btn) => btn.addEventListener('click', () => reconcile(btn.dataset.reconcile)));
  // Ask sits in the toolbar as well as beside each paragraph, and the toolbar
  // outlives a re-render — hence the mark, so one button does not collect a
  // listener every time the document is drawn again.
  qsa('[data-ask]').forEach((btn) => {
    if (btn.dataset.askWired === '1') return;
    btn.dataset.askWired = '1';
    btn.addEventListener('click', () => openAsk(btn.dataset.askScope || 'document', btn.dataset.askSection || ''));
  });
  qsa('[data-decision]').forEach((btn) => btn.addEventListener('click', () =>
    handleDecision(btn.dataset.decision, btn.dataset.decisionLabel)));
  qsa('[data-history]').forEach((btn) => btn.addEventListener('click', () => {
    state.historyId = btn.dataset.history;
    renderDirection();
  }));
}
