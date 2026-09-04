// Everything that leaves the browser: decisions, feedback, steering — plus the
// dialog primitives and the local-only conveniences (copy, download, bookmark).
import { $, state, data, escapeHtml, toast, currentDoc, writeBookmark } from './state.js';
import { api } from './api.js';
import { hooks } from './refresh.js';

export function openDialog(title, eyebrow, content, actions) {
  $('dialogTitle').textContent = title;
  $('dialogEyebrow').textContent = eyebrow;
  $('dialogContent').innerHTML = content;
  $('dialogActions').innerHTML = '';
  actions.forEach((a) => {
    const b = document.createElement('button');
    b.type = 'button';
    b.className = a.kind === 'primary' ? 'primary-button' : 'outline-button';
    b.textContent = a.label;
    b.addEventListener('click', a.action);
    $('dialogActions').appendChild(b);
  });
  $('modalBackdrop').classList.remove('hidden');
  if (typeof $('appDialog').showModal === 'function') $('appDialog').showModal();
  else $('appDialog').setAttribute('open', '');
}

export function closeDialog() {
  const dlg = $('appDialog');
  if (dlg.open && typeof dlg.close === 'function') dlg.close();
  else dlg.removeAttribute('open');
  $('modalBackdrop').classList.add('hidden');
}

function activeProposalId() {
  const p = (data.doc && (data.doc.proposals || [])[0]) || null;
  return p ? p.id : null;
}

// --------------------------------------------------------------------------
// §8 — the granular choices, and the one answer they build
// --------------------------------------------------------------------------
//
// A steward keeps six changes, drops one, fixes three words, and answers once.
// The keeping is already a write of its own (`changes/{id}/keep`, remembered
// per steward on the server), and the dropping is a restore that has already
// put the earlier wording back. What was missing is the last step: those
// choices reaching the ONE answer. So the ratify-with-edits dialog reads the
// reading as it stands — kept, not kept — shows the steward exactly what their
// choices are, and carries them, verbatim, into the note the decision write
// records. They are not a new kind of ratification; they build the word that
// is already in the vocabulary.

function plural(n, word) { return `${n} ${word}${n === 1 ? '' : 's'}`; }

function shortOf(text, limit = 88) {
  const one = String(text || '').replace(/\s+/g, ' ').trim();
  return one.length > limit ? `${one.slice(0, limit - 1)}…` : one;
}

//: A card's section is a path — "Principles › 8" — and its head is the
//: section that path sits in. Kept local rather than imported from
//: render/direction.js, which imports this file.
function headOf(section) {
  return String(section || '').split(' › ')[0];
}

export function choicesNow() {
  const rows = cardsNow();
  return { rows, kept: rows.filter((c) => c.kept), open: rows.filter((c) => !c.kept) };
}

//: The choices as the ratification record will carry them. Plain lines, the
//: steward's own sections and sentences, nothing summarised away.
export function choiceLedger() {
  const { rows, kept, open } = choicesNow();
  if (!rows.length) return '';
  const lines = [`Granular choices carried into this answer — ${kept.length} of ${rows.length} changes kept.`];
  if (kept.length) {
    lines.push('Kept:');
    kept.forEach((c) => lines.push(`- ${c.section || 'this document'}: ${shortOf(c.now || c.before)}`));
  }
  if (open.length) {
    lines.push('Not kept:');
    open.forEach((c) => lines.push(`- ${c.section || 'this document'}: ${shortOf(c.now || c.before)}`));
  }
  return lines.join('\n');
}

function choiceSummaryHtml() {
  const { rows, kept, open } = choicesNow();
  if (!rows.length) {
    return '<p class="muted">Nothing has moved in this document since your read point, so there are no granular choices to carry.</p>';
  }
  const list = (cards) => `<ul>${cards.map((c) => `<li><strong>${escapeHtml(c.section || 'This document')}</strong> — ${escapeHtml(shortOf(c.now || c.before, 64))}</li>`).join('')}</ul>`;
  return `<p><strong>${kept.length} of ${rows.length}</strong> changes are kept. These go into the record with your word, verbatim.</p>
      ${kept.length ? `<p class="muted">Kept</p>${list(kept)}` : ''}
      ${open.length ? `<p class="muted">Not kept</p>${list(open)}` : ''}`;
}

export function handleDecision(decision, label) {
  if (decision === 'ratified-with-edits') {
    openDialog('Ratify with edits', 'Direction decision', `
        ${choiceSummaryHtml()}
        <div class="dialog-field"><label for="ratifyEdit">The wording change you want before accepting</label><textarea id="ratifyEdit" placeholder="Say what you want changed…"></textarea></div>
        <p class="muted">One answer, in your ratification log, carrying the choices above and your words.</p>`, [
      { label: 'Cancel', kind: 'outline', action: closeDialog },
      {
        label: 'Ratify with edits',
        kind: 'primary',
        action: () => {
          const words = $('ratifyEdit')?.value.trim() || '';
          const ledger = choiceLedger();
          finalizeDecision(decision, label, [words, ledger].filter(Boolean).join('\n\n'));
        },
      },
    ]);
    return;
  }
  finalizeDecision(decision, label, '');
}

export async function finalizeDecision(decision, label, note) {
  const proposalId = activeProposalId();
  if (!proposalId) { toast('There is no open proposal to decide.'); return; }
  closeDialog();
  try {
    const res = await api.decision(state.managerId, {
      repoId: state.repoId,
      docId: state.docId,
      proposalId,
      decision,
      note: note || '',
    });
    state.proposalDecision = label;
    toast(res && res.recorded ? `Recorded in ${res.recorded}` : `Proposal ${proposalId}: ${label}`);
    await hooks.reloadManager();
  } catch (err) {
    toast(`Could not record the decision: ${err.message}`);
  }
}

// --------------------------------------------------------------------------
// the Changes view: four writes, no staging
// --------------------------------------------------------------------------
//
// Each of these makes a request and then re-reads the document, so what the
// steward sees afterwards is what the server actually did. Keep used to be a
// message and nothing else — the steward marked every change, left the page,
// came back, and found them all reset. That is why the reload is not optional
// here: it is the proof.

async function afterChange(said) {
  await hooks.reloadDoc();
  if (said) toast(said);
}

export async function keepChange(changeId, on) {
  try {
    await api.keepChange(state.managerId, state.repoId, state.docId, changeId, on);
    await afterChange(on ? 'Kept — and remembered for you, not for this browser.' : 'No longer kept.');
  } catch (err) {
    toast(`Could not save that: ${err.message}`);
  }
}

export async function saveChangeEdit(changeId, text) {
  if (!text || !text.trim()) { toast('Write the wording you want first.'); return; }
  try {
    const res = await api.editChange(state.managerId, state.repoId, state.docId, changeId, text.trim());
    await afterChange(res && res.said ? res.said : 'Your wording is in.');
  } catch (err) {
    toast(`Could not write that edit: ${err.message}`);
  }
}

export async function restoreChange(changeId) {
  try {
    const res = await api.restoreChange(state.managerId, state.repoId, state.docId, changeId);
    await afterChange(res && res.said ? res.said : 'The previous wording is back.');
  } catch (err) {
    toast(`Could not restore that: ${err.message}`);
  }
}

// --------------------------------------------------------------------------
// §6 — restoring from history, at four scopes, as a real action
// --------------------------------------------------------------------------
//
// The contract asks that a steward be able to restore a wording, a paragraph,
// a section, or the whole document, and that on a locked document the same
// gesture produce a proposal to answer.
//
// This app answers ONE restore write — `changes/{id}/restore` — and it puts
// back the wording that stood before one sentence moved. A wider scope is
// therefore not a different write: it is that write over every sentence the
// scope covers, one at a time, and the screen says how many landed and where.
// The lock is never consulted here. `app/writes.py` reads the document's own
// H1 and either commits or writes `<doc-stem>.vN-candidate.md` beside it; this
// file only reports afterwards what the server did, so forcing a control in
// the browser changes nothing.
//
// Two things this deliberately does not pretend:
//
// - **The snapshot it restores to is the one the steward picked in History.**
//   Any row in that list, not only their own read point: the app answers a
//   read at any commit in a document's own history now (converge-4pq —
//   `?since=<sha>` on the read, `since` in the write's body), and the sha
//   travels with every write below. Which commits are reachable is the
//   server's bound, not this file's: it refuses a commit that never touched
//   this document, in its own words.
// - **Every restore commits**, which moves HEAD and renumbers every hunk after
//   it — so the change ids this loop starts with go stale as it runs. Each
//   sentence is found again by what it SAYS in the reading as it stands, never
//   by an id that was true one write ago. With a snapshot open that reading is
//   re-read at the same sha after each write, for the same reason.

const SCOPE_WORD = {
  wording: 'this wording',
  paragraph: 'this paragraph',
  section: 'this section',
  document: 'the whole document',
};

// --------------------------------------------------------------------------
// the snapshot a restore reads from
// --------------------------------------------------------------------------
//
// Kept BESIDE `data.doc` rather than replacing it. `data.doc` is the steward's
// own reading — their read point, their kept marks, the changes they have not
// answered — and opening a snapshot must not disturb any of it. The server
// keeps the same rule at its end: a read with `?since=` never moves a read
// point.
//
// The History list's `now` row is the steward's own reading and is not a
// snapshot at all: there is nothing between HEAD and HEAD to put back, so that
// row means "what has moved since you last read", which is what `data.doc`
// already holds.

const snapshot = { key: '', rowId: '', sha: '', label: '', loading: false, doc: null, error: '' };

//: Which document a snapshot belongs to. A snapshot of the vision is not a
//: snapshot of a contract, and moving between documents must not carry one
//: across.
function docKey() { return `${state.repoId}\u001f${state.docId}`; }

function forgetSnapshot() {
  snapshot.key = '';
  snapshot.rowId = '';
  snapshot.sha = '';
  snapshot.label = '';
  snapshot.loading = false;
  snapshot.doc = null;
  snapshot.error = '';
}

//: The open snapshot, or null when the steward is reading from their own
//: point. It answers null for a snapshot that no longer matches what is
//: selected — another document, or a return to the `now` row — so a stale
//: reading can never be the one a restore is built from. `state.historyId`
//: is reset to `now` whenever a document is opened (`main.js`), and that is
//: exactly the case this catches.
export function openSnapshot() {
  if (snapshot.key !== docKey() || !snapshot.sha) return null;
  return String(state.historyId) === String(snapshot.rowId) ? snapshot : null;
}

//: The reading a restore works from: which cards, and which sha its writes
//: carry. With no snapshot open both are what they have always been — the
//: steward's own reading, and no sha at all.
export function restoreReading() {
  const open = openSnapshot();
  if (!open || !open.sha) return { doc: data.doc, since: '', cards: cardsNow() };
  return { doc: open.doc, since: open.sha, cards: (open.doc && open.doc.changes) || [] };
}

//: Pick one History row to restore from. The `now` row is the steward's own
//: reading rather than a snapshot — there is nothing between HEAD and HEAD to
//: put back — so it closes any open snapshot instead of asking the server for
//: one.
export function selectSnapshot(row) {
  if (!row || String(row.id) === 'now' || !row.sha) { forgetSnapshot(); return Promise.resolve(); }
  return readSnapshot(String(row.sha), String(row.label || ''), String(row.id));
}

//: Read this document as it stood at one commit. The fields are set before
//: the first await, so a caller can draw "reading…" straight after; the view
//: is drawn again when the answer lands.
async function readSnapshot(wanted, label, rowId = snapshot.rowId) {
  snapshot.key = docKey();
  snapshot.rowId = String(rowId || '');
  snapshot.sha = wanted;
  snapshot.label = String(label || '');
  snapshot.loading = true;
  snapshot.doc = null;
  snapshot.error = '';
  const mine = () => snapshot.key === docKey() && snapshot.sha === wanted;
  try {
    const read = await api.doc(state.managerId, state.repoId, state.docId, wanted);
    if (!mine()) return;
    snapshot.doc = read;
  } catch (err) {
    if (!mine()) return;
    // The server's own sentence, whole. It is the one that says WHY — a
    // commit outside this document's history is refused by name there, and
    // repeating that here in different words would be this file inventing a
    // cause it did not observe.
    snapshot.error = err.message || 'that snapshot could not be read';
  }
  snapshot.loading = false;
  hooks.renderDirection();
}

function signatureOf(card) {
  return [String(card.section || ''), String(card.before || ''), String(card.now || '')].join('\u001f');
}

export function cardsInScope(scope, key, rows = cardsNow()) {
  if (scope === 'wording') return rows.filter((c) => String(c.id) === String(key));
  if (scope === 'paragraph') return rows.filter((c) => String(c.section) === String(key));
  if (scope === 'section') return rows.filter((c) => headOf(c.section) === String(key));
  return rows.slice();
}

export function restoreScope(scope, key) {
  const reading = restoreReading();
  const wanted = cardsInScope(scope, key, reading.cards);
  if (!wanted.length) {
    toast('Nothing in this reading moved at that scope, so there is no earlier wording to put back.');
    return;
  }
  // The lock is read from the steward's own reading of the document, because
  // that is what the document says NOW — a snapshot's copy would be this
  // document's H1 as it stood then, and a lock added since would be missed.
  // It changes nothing that matters either way: `app/writes.py` decides, and
  // this is only what the confirmation says it will decide.
  const doc = data.doc || {};
  const lock = doc.locked || '';
  const point = (reading.doc && reading.doc.reading) || {};
  const where = lock
    ? `${doc.path || 'This document'} is ${lock}, so it is not touched at all: each wording is written to a proposal beside it, for you to answer.`
    : 'Each wording goes back into the document and is committed in your name.';
  openDialog(`Restore ${SCOPE_WORD[scope] || 'these changes'}`, 'Restore from history', `
      <p>${plural(wanted.length, 'sentence')} ${wanted.length === 1 ? 'goes' : 'go'} back to the wording that stood at <strong>${escapeHtml(point.sinceShort || 'your read point')}</strong>${point.sinceSource ? ` — ${escapeHtml(point.sinceSource)}` : ''}.</p>
      <ul>${wanted.slice(0, 8).map((c) => `<li><strong>${escapeHtml(c.section || 'This document')}</strong> — ${escapeHtml(shortOf(c.before || c.now, 64))}</li>`).join('')}</ul>
      ${wanted.length > 8 ? `<p class="muted">…and ${wanted.length - 8} more.</p>` : ''}
      <p class="muted">${escapeHtml(where)}</p>`, [
    { label: 'Cancel', kind: 'outline', action: closeDialog },
    { label: `Restore ${plural(wanted.length, 'sentence')}`, kind: 'primary', action: () => runRestore(wanted, reading.since) },
  ]);
}

async function runRestore(targets, since) {
  closeDialog();
  const wanted = targets.map(signatureOf);
  const landed = [];
  const refused = [];
  // Which of the two paths the server took is the server's own word for it
  // (`mode`), never guessed from the payload's shape: both modes carry a
  // `file`, so reading that would have called a commit a proposal.
  let proposal = '';
  let commits = 0;
  for (const signature of wanted) {
    const card = restoreReading().cards.find((c) => signatureOf(c) === signature);
    if (!card) {
      refused.push('one sentence had left this reading by the time its turn came');
      continue;
    }
    try {
      const res = await api.restoreChange(state.managerId, state.repoId, state.docId, card.id, since);
      if (res && res.mode === 'candidate') proposal = res.file || proposal;
      if (res && res.mode === 'commit') commits += 1;
      landed.push(card.section || card.id);
    } catch (err) {
      refused.push(`${card.section || card.id}: ${err.message}`);
    }
    await hooks.reloadDoc();
    // Read the snapshot again at the same commit. A restore that committed
    // moved HEAD, so the reading this loop works from is one write out of
    // date — including the ids the next write needs.
    if (since) await readSnapshot(since, snapshot.label);
  }
  let said = 'Nothing was put back.';
  if (proposal && commits) {
    said = `${plural(landed.length, 'wording')} put back: ${plural(commits, 'commit')}, and the rest waiting in ${proposal}.`;
  } else if (proposal) {
    said = `${plural(landed.length, 'wording')} written into ${proposal} for you to answer. The document itself was not touched.`;
  } else if (commits) {
    said = `${plural(commits, 'sentence')} put back, each committed in your name.`;
  }
  toast(refused.length ? `${said} ${plural(refused.length, 'refusal')}: ${refused[0]}` : said);
}

export async function markAllRead() {
  try {
    const res = await api.markRead(state.managerId, state.repoId, state.docId);
    await afterChange(`Marked read at ${res && res.short ? res.short : 'the current version'}. The next change will be the next thing you see.`);
  } catch (err) {
    toast(`Could not move your read point: ${err.message}`);
  }
}

// --------------------------------------------------------------------------
// the Reading view: editing a draft in place, and meeting a collision
// --------------------------------------------------------------------------
//
// The document-saving write is `changes/{id}/edit`, and it is the same write
// whether the steward reaches it from a change card or from the document they
// are reading. Which sentences it can carry is therefore not a choice this
// file makes: it is the sentences the server can still find, which is why the
// Reading view offers editing on those and nowhere else.
//
// The lock is not consulted here at all. `app/writes.py` reads the document's
// own H1 and either commits or writes a proposal beside it; the browser only
// says afterwards what the server did. A refusal that came from this file
// would be an instruction someone could follow, not a guard.

//: A refusal that means the document moved under this reading rather than
//: that the steward wrote something wrong. Each phrase is `app/writes.py`'s
//: or `app/serve.py`'s own wording.
const COLLISION = /no longer in the file|uncommitted changes|not in this reading/i;

function cardsNow() {
  return (data.doc && data.doc.changes) || [];
}

export async function editDoc(changeId, text) {
  if (!text || !text.trim()) { toast('Write the wording you want first.'); return; }
  const card = cardsNow().find((c) => String(c.id) === String(changeId)) || null;
  try {
    const res = await api.editChange(state.managerId, state.repoId, state.docId, changeId, text.trim());
    state.editingChangeId = null;
    state.collision = null;
    await afterChange(res && res.said ? res.said : 'Saved to the document.');
  } catch (err) {
    if (!COLLISION.test(err.message || '')) {
      toast(`Could not write that edit: ${err.message}`);
      return;
    }
    // Someone else's write landed between this reading and this save. Nothing
    // has been written, so the steward is shown both wordings and chooses.
    state.collision = { section: card ? card.section : '', mine: text.trim(), theirs: '', why: err.message };
    await hooks.reloadDoc();
    const fresh = cardsNow().find((c) => String(c.section) === String(state.collision.section));
    state.collision.theirs = fresh ? String(fresh.now || fresh.before || '') : '';
    state.editingChangeId = fresh ? fresh.id : null;
    hooks.renderDirection();
    toast('That sentence moved while you were writing. Nothing was written.');
  }
}

export async function reconcile(choice) {
  const clash = state.collision;
  if (!clash) return;
  if (choice === 'review-both') {
    state.collision = null;
    state.editingChangeId = null;
    state.docMode = 'changes';
    hooks.renderDirection();
    toast('Nothing was written. Both wordings are side by side in Changes.');
    return;
  }
  const card = cardsNow().find((c) => String(c.section) === String(clash.section)) || null;
  if (!card) {
    toast('That sentence is gone from this reading, so there is nothing left to combine. Review both instead.');
    return;
  }
  const theirs = String(card.now || card.before || '').trim();
  const wanted = choice === 'use-combined' && theirs ? `${theirs} ${clash.mine}` : clash.mine;
  state.collision = null;
  await editDoc(card.id, wanted);
}

// --------------------------------------------------------------------------
// Ask: a scoped request whose output is a proposal
// --------------------------------------------------------------------------

const ASK_SCOPES = [
  ['paragraph', 'Ask about this paragraph'],
  ['document', 'Ask about this document'],
  ['all', 'Ask across every document in this repository'],
];

export function openAsk(scope, section) {
  const wanted = ASK_SCOPES.some(([value]) => value === scope) ? scope : 'document';
  const doc = data.doc;
  const about = section || (doc ? doc.title : '');
  openDialog('Ask for a proposal', 'Ask', `
      <div class="dialog-field"><label for="askScope">What this ask covers</label>
        <select id="askScope">${ASK_SCOPES.map(([value, label]) =>
    `<option value="${value}" ${value === wanted ? 'selected' : ''}>${escapeHtml(label)}</option>`).join('')}</select></div>
      <div class="dialog-field"><label for="askWhat">What you want</label><textarea id="askWhat" placeholder="Say plainly what should be different…"></textarea></div>
      ${section ? `<div class="dialog-field"><label for="askSection">The paragraph this is about</label><input id="askSection" value="${escapeHtml(section)}" readonly /></div>` : ''}
      <p class="muted">What comes back is a proposal to review — never a silent edit, and never a chat. Nothing in any document changes until you answer it.</p>`, [
    { label: 'Cancel', kind: 'outline', action: closeDialog },
    {
      label: 'Ask',
      kind: 'primary',
      action: () => sendAsk($('askScope')?.value || wanted, $('askWhat')?.value.trim() || '', about),
    },
  ]);
}

export async function sendAsk(scope, text, section) {
  if (!text) { toast('Say what you want first.'); return; }
  closeDialog();
  try {
    const res = await api.ask(state.managerId, {
      scope, text, section: section || '', repoId: state.repoId, docId: state.docId,
    });
    toast(res && res.proposal ? `Proposal ${res.proposal} is waiting in Review.` : 'Your ask came back as a proposal, waiting in Review.');
    await hooks.reloadDoc();
  } catch (err) {
    // What refused, in its own words, and no cause of our own on top of it
    // (converge-3al). This used to say "this app answers no proposal route
    // yet", which is now false twice over: the route landed with converge-ddt,
    // and offline the refusal is the service worker's — "you are offline, so
    // nothing was asked — reconnect and ask again, or tell the manager session
    // directly" — carried here whole by api.js. Framing that sentence as a
    // missing route contradicted the banner beside it. Every other write in
    // this file already reports the refusal and stops; so does this one.
    toast(`Could not ask: ${err.message}`);
  }
}

// --------------------------------------------------------------------------
// §11 — locking a document, once the four conditions are met
// --------------------------------------------------------------------------
//
// The gate lives in render/direction.js: it is what decides whether the
// control is live at all, and it never ticks a condition on the steward's
// behalf. This is only the last step — the confirmation, and the write.
//
// Locking is irreversible in the way that matters: from the moment a document
// carries a locking word in its H1, `app/writes.py` refuses to touch it and
// every later change becomes a proposal to answer. So the dialog says that in
// those words before anything leaves the browser, and the conditions the
// steward answered are carried into the write rather than summarised away.

export function confirmLock(doc, answered) {
  if (!doc) return;
  openDialog('Lock this document', 'Direction decision', `
      <p><strong>${escapeHtml(doc.path || doc.title || 'This document')}</strong> becomes law when you lock it.</p>
      <p class="muted">From then on it is not edited in place: every change to it, including your own, is written as a proposal beside it for you to answer. That is the guard in <code>app/writes.py</code> reading the document's own first line, not a setting.</p>
      <p class="muted">The four conditions you are answering for:</p>
      <ul>${answered.map((line) => `<li>${escapeHtml(line)}</li>`).join('')}</ul>`, [
    { label: 'Cancel', kind: 'outline', action: closeDialog },
    { label: 'Lock it', kind: 'primary', action: () => sendLock(answered) },
  ]);
}

export async function sendLock(answered) {
  closeDialog();
  try {
    const res = await api.lock(state.managerId, state.repoId, state.docId, { conditions: answered });
    toast(res && res.locked ? `Locked: ${res.locked}` : 'This document is locked.');
    await hooks.reloadDoc();
  } catch (err) {
    // What refused, in its own words, and no cause of our own on top of it
    // (converge-8r5). This used to say "this app answers no lock route yet",
    // which was true while converge-eci was open and false the moment it
    // landed: `app/serve.py` answers this route and `writes.lock_document`
    // refuses it for four real reasons — the document already carries a
    // locking word, fewer than four conditions arrived, the file has
    // uncommitted changes that a lock commit would carry along, or there is
    // no H1 to put a status in. Each of those arrives here as `err.message`,
    // already a whole sentence a steward can act on, and each was reaching
    // them under a cause nobody had observed. AGENTS.md §5 cuts both ways: a
    // screen may not claim a cause it did not observe either.
    //
    // "Nothing was locked" stays, because it is this file's own true
    // observation: the write threw, so no stamp was made.
    toast(`Nothing was locked — ${err.message}`);
  }
}

function readImage(input) {
  const file = input && input.files && input.files[0];
  if (!file) return Promise.resolve(null);
  return new Promise((resolve) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = () => resolve(null);
    reader.readAsDataURL(file);
  });
}

// --------------------------------------------------------------------------
// Feedback as a voice note -- the third form, beside text and a screenshot
// --------------------------------------------------------------------------
//
// `experience-operation.v1` clause 10: "Feedback can be dropped in seconds, in
// whatever form is to hand. (IDIOM) Text, a screenshot, or voice." IDIOM means
// the behaviour is required and its shape is not, so this body may choose the
// gesture but not drop the form. It dropped it until now (converge-rj1).
//
// ## Why this lives here and not in a module of its own
//
// It was written as `app/static/js/feedback_voice.js` and folded back in here,
// measured on this tree 2026-09-04. `app/static/sw.js` precaches every client
// module by hand, and `app/tests/test_web_polish.py` derives what the app
// actually loads by walking `main.js`'s import graph, so a new module is a new
// PRECACHE entry or it is a module a steward loses the moment they go offline:
//
//     MISSING /static/js/feedback_voice.js
//     FAILED app/tests/test_web_polish.py::
//         test_the_precache_list_carries_every_module_the_app_loads
//
// `app/static/sw.js` is another lane's file today, so the entry cannot be added
// in this change -- and shipping the module without it would have traded a
// working voice note for an app that stops opening offline. Splitting it out
// once that one line can move with it is filed as work, not left implied.

// Feedback as a voice note — the browser half of `experience-operation.v1`
// clause 10 ("Text, a screenshot, or voice"), landing beside the text in the
// project's `.converge/feedback/` folder (converge-rj1).
//
// One gesture, three forms. This file owns only the third: the field the
// feedback dialog grows, the recording it makes when the browser can record,
// and the one POST that carries it. `actions.js` still sends the text and the
// screenshot exactly as it did; the recording follows on the same press of
// "Send feedback", named after the note the server just wrote, so the two land
// as one piece of feedback rather than two.
//
// ## Recording is not always available, and the sentence says which
//
// `MediaRecorder` and `navigator.mediaDevices` are two different absences and
// they are said differently. `mediaDevices` is undefined outside a secure
// context, which on this app is the ordinary LAN case — served over plain
// http from `spark-1:8788`, no browser will hand over a microphone. That is
// not a defect to hide behind a dead button: the field says so in a plain
// sentence and offers the file input, which works everywhere and always has.
// `experience.v1` Core 14 asks a body to say what it cannot do; this says it
// at the exact control it is about.
//
// The file input is therefore never conditional. Recording is the convenience;
// attaching is the floor.

const RECORD_MIME_CANDIDATES = [
  'audio/webm;codecs=opus',
  'audio/webm',
  'audio/ogg;codecs=opus',
  'audio/ogg',
  'audio/mp4',
];

//: Why this browser will not record, in words a steward can act on — or '' when
//: it will. Read once when the field is drawn, never guessed at afterwards.
function whyNoRecording() {
  if (typeof window === 'undefined') return 'there is no browser here to record with';
  if (typeof window.MediaRecorder === 'undefined') {
    return 'this browser cannot record audio';
  }
  if (!navigator.mediaDevices || typeof navigator.mediaDevices.getUserMedia !== 'function') {
    return 'recording needs a secure connection (https, or the app opened on this machine)';
  }
  return '';
}

function pickMime() {
  if (typeof window.MediaRecorder?.isTypeSupported !== 'function') return '';
  return RECORD_MIME_CANDIDATES.find((m) => window.MediaRecorder.isTypeSupported(m)) || '';
}

function asDataUrl(blob) {
  return new Promise((resolve) => {
    const reader = new FileReader();
    reader.onload = () => resolve(typeof reader.result === 'string' ? reader.result : null);
    reader.onerror = () => resolve(null);
    reader.readAsDataURL(blob);
  });
}

// --------------------------------------------------------------------------
// the field
// --------------------------------------------------------------------------

//: The markup the feedback dialog grows. `accept="audio/*"` is the offer the
//: conformance kit reads (`conformance/experience/run.py` FEEDBACK_FORMS), and
//: it is here rather than in a template because the image offer it sits beside
//: is here too — the feedback dialog is built in `actions.js`, not in
//: `app/templates/dialogs.html`.
function voiceField() {
  const why = whyNoRecording();
  const control = why
    ? `<p class="voice-unavailable">Recording is not available here — ${why}. Attach an audio file instead.</p>`
    : '<div class="voice-row"><button type="button" id="feedbackVoiceRecord" class="outline-button voice-record">Record</button>'
      + '<span id="feedbackVoiceState" class="voice-state" role="status" aria-live="polite">Nothing recorded yet.</span></div>';
  return `
      <div class="dialog-field voice-field">
        <label for="feedbackVoice">Or a voice note</label>
        ${control}
        <input id="feedbackVoice" type="file" accept="audio/*" />
      </div>`;
}

// --------------------------------------------------------------------------
// recording
// --------------------------------------------------------------------------

//: Wire the record button and hand back the one thing the caller needs: what
//: the steward left behind, whichever way they left it. Safe to call when the
//: field drew no button — `take()` then reads the file input alone.
function wireVoiceField(root = document) {
  const button = root.getElementById
    ? root.getElementById('feedbackVoiceRecord')
    : root.querySelector('#feedbackVoiceRecord');
  const state = root.getElementById
    ? root.getElementById('feedbackVoiceState')
    : root.querySelector('#feedbackVoiceState');
  const input = root.getElementById
    ? root.getElementById('feedbackVoice')
    : root.querySelector('#feedbackVoice');

  let recorder = null;
  let chunks = [];
  let recorded = null;
  let stream = null;
  let startedAt = 0;

  const say = (words) => { if (state) state.textContent = words; };

  function releaseTheMicrophone() {
    if (stream) stream.getTracks().forEach((track) => track.stop());
    stream = null;
  }

  async function start() {
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch (err) {
      say(`The microphone was not allowed, so nothing was recorded (${err.name || err.message}). Attach an audio file instead.`);
      return;
    }
    const mime = pickMime();
    try {
      recorder = new window.MediaRecorder(stream, mime ? { mimeType: mime } : undefined);
    } catch (err) {
      releaseTheMicrophone();
      say(`This browser refused to start a recording (${err.message}). Attach an audio file instead.`);
      return;
    }
    chunks = [];
    recorded = null;
    startedAt = Date.now();
    recorder.addEventListener('dataavailable', (e) => { if (e.data && e.data.size) chunks.push(e.data); });
    recorder.addEventListener('stop', () => {
      releaseTheMicrophone();
      const seconds = Math.max(1, Math.round((Date.now() - startedAt) / 1000));
      recorded = chunks.length ? new Blob(chunks, { type: recorder.mimeType || mime || 'audio/webm' }) : null;
      if (button) button.textContent = 'Record';
      say(recorded
        ? `Recorded ${seconds}s — it will be sent with your feedback.`
        : 'Nothing was captured, so there is no recording to send.');
    });
    recorder.start();
    if (button) button.textContent = 'Stop';
    say('Recording… press Stop when you are done.');
  }

  function stop() {
    if (recorder && recorder.state !== 'inactive') recorder.stop();
    else releaseTheMicrophone();
    recorder = null;
  }

  if (button) {
    button.addEventListener('click', () => {
      if (recorder && recorder.state !== 'inactive') stop();
      else start();
    });
  }

  return {
    //: What the steward left, as the server takes it — or null when they left
    //: nothing. A recording wins over an attached file only because it is the
    //: thing they just made; the file is still read when there is no recording.
    async take() {
      if (recorder && recorder.state !== 'inactive') stop();
      if (recorded) {
        const dataUrl = await asDataUrl(recorded);
        return dataUrl ? { dataUrl, how: 'recorded' } : null;
      }
      const file = input && input.files && input.files[0];
      if (!file) return null;
      const dataUrl = await asDataUrl(file);
      return dataUrl ? { dataUrl, how: 'attached', filename: file.name } : null;
    },
    stop,
    whyNoRecording: whyNoRecording(),
  };
}

// --------------------------------------------------------------------------
// the write
// --------------------------------------------------------------------------

//: `POST /api/managers/{mid}/feedback/voice` — the *drop feedback* write, told
//: which form arrived. It is not a sixth write: `app/feedback_voice.py` says
//: at length why the form is a path parameter and what would have gone wrong
//: had it been a route of its own.
//
// The fetch is here rather than in `api.js` because `api.js` is another lane's
// file today. It obeys the same two rules that file does: send the cookie, and
// carry the server's own refusal out with the error rather than a status code.
async function sendVoiceNote(mid, payload) {
  const res = await fetch(`/api/managers/${encodeURIComponent(mid)}/feedback/voice`, {
    method: 'POST',
    credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    let said = '';
    try {
      const body = await res.json();
      said = (body && (body.error || body.detail)) || '';
    } catch { /* the refusal was not JSON: the status is all there is */ }
    const refusal = new Error(said || `the voice note was refused (${res.status})`);
    refusal.status = res.status;
    throw refusal;
  }
  return res.json();
}

// Three forms, one gesture (`experience-operation.v1` clause 10). Text and a
// screenshot go on the feedback route as they always have; the voice note
// follows on the same press, named after the note the server just wrote, so it
// lands beside it rather than as a second piece of feedback (converge-rj1).
// The field itself, the recording, and that write are `feedback_voice.js`.
export function openFeedback() {
  const doc = currentDoc();
  const m = data.manager;
  // Assigned once the dialog's markup is in the DOM, a few lines below: the
  // field has to exist before anything can be wired to it.
  let voice = null;
  const context = `${m ? m.name : 'Converge'} · ${state.workspace === 'direction' && doc ? doc.fullTitle : 'Operation'}`;
  openDialog('Tell the manager what you noticed', 'Feedback', `
      <div class="dialog-field"><label for="feedbackText">Feedback</label><textarea id="feedbackText" placeholder="Still not working on Android…"></textarea></div>
      <div class="dialog-field"><label for="feedbackContext">Context the app will attach</label><input id="feedbackContext" value="${escapeHtml(context)}" readonly /></div>
      <div class="dialog-field"><label for="feedbackImage">Optional screenshot or image</label><input id="feedbackImage" type="file" accept="image/*" /></div>
      ${voiceField()}
      <p class="muted">The manager decides whether this reopens verification, updates existing work, or belongs back in Direction.</p>`, [
    { label: 'Cancel', kind: 'outline', action: () => { if (voice) voice.stop(); closeDialog(); } },
    {
      label: 'Send feedback',
      kind: 'primary',
      action: async () => {
        const text = $('feedbackText')?.value.trim();
        if (!text) { toast('Add a little feedback first.'); return; }
        const image = await readImage($('feedbackImage'));
        const spoken = voice ? await voice.take() : null;
        closeDialog();
        let said;
        let note = '';
        try {
          const res = await api.feedback(state.managerId, { text, context, imageDataUrl: image || undefined });
          note = res && res.path ? String(res.path).split('/').pop() : '';
          said = res && res.path ? `Feedback filed at ${res.path}` : 'Feedback delivered to the manager.';
        } catch (err) {
          toast(`Could not file the feedback: ${err.message}`);
          return;
        }
        // The text landed. Whatever happens to the recording, that stays true
        // — so the voice half reports itself beside it and never overwrites it.
        if (spoken) {
          try {
            const kept = await sendVoiceNote(state.managerId, {
              dataUrl: spoken.dataUrl, note, context, text,
            });
            said += `, with your voice note beside it as ${kept.voice}`;
          } catch (err) {
            said += `. The voice note was not filed: ${err.message}`;
          }
        }
        toast(said);
      },
    },
  ]);
  voice = wireVoiceField(document);
}

export function openSteer() {
  const m = data.manager;
  if (!m) return;
  const options = [...new Set([2, 4, 6, 8, 10, m.lanesMax])].sort((a, b) => a - b);
  openDialog('Steer this operating epoch', 'Steer', `
      <div class="dialog-field"><label for="steerObjective">Objective</label><textarea id="steerObjective">${escapeHtml(m.objective)}</textarea></div>
      <div class="dialog-field"><label for="steerLanes">Maximum lanes</label><select id="steerLanes">${options.map((n) => `<option ${n === m.lanesMax ? 'selected' : ''}>${n}</option>`).join('')}</select></div>
      <div class="dialog-field"><label for="steerNote">Note for the manager</label><input id="steerNote" placeholder="Why you are steering" /></div>`, [
    { label: 'Cancel', kind: 'outline', action: closeDialog },
    {
      label: 'Update steering',
      kind: 'primary',
      action: async () => {
        const objective = $('steerObjective').value.trim() || m.objective;
        const laneWidth = Number($('steerLanes').value) || m.lanesMax;
        const note = $('steerNote').value.trim();
        closeDialog();
        try {
          await api.steer(state.managerId, { objective, lanes: laneWidth, note });
          toast('Steering updated.');
          await hooks.reloadManager();
        } catch (err) {
          toast(`Could not steer: ${err.message}`);
        }
      },
    },
  ]);
}

export async function fillLanes() {
  try {
    await api.steer(state.managerId, { fill: true });
    toast('Manager is evaluating safe lane width.');
    await hooks.reloadManager();
  } catch (err) {
    toast(`Could not ask for a fill: ${err.message}`);
  }
}

export function toggleBookmark() {
  state.bookmarked = !state.bookmarked;
  writeBookmark(state.bookmarked);
  hooks.renderDirection();
  toast(state.bookmarked ? 'Bookmarked on this device.' : 'Bookmark removed.');
}

export function downloadCurrentDoc() {
  const doc = data.doc;
  if (!doc) return;
  const blob = new Blob([doc.raw || ''], { type: 'text/markdown;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `${String(doc.title).replace(/\s+/g, '-').toLowerCase()}.md`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 500);
  toast('Downloaded the current Markdown source.');
}

export async function copyText(text) {
  try {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(text);
    } else {
      const ta = document.createElement('textarea');
      ta.value = text;
      ta.style.position = 'fixed';
      ta.style.opacity = '0';
      document.body.appendChild(ta);
      ta.select();
      document.execCommand('copy');
      ta.remove();
    }
    toast('Copied to clipboard.');
  } catch {
    toast('Clipboard was blocked by the browser.');
  }
}
