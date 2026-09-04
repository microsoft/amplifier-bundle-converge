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
// - **The snapshot it restores to is the steward's own read point**, not any
//   row in the History list. The sentences the server can still find are the
//   ones in this reading, so that is the only earlier wording that is actually
//   reachable. Restoring to an arbitrary commit needs a route the app does not
//   answer; it is filed as converge-4pq and the panel says so on the screen.
// - **Every restore commits**, which moves HEAD and renumbers every hunk after
//   it — so the change ids this loop starts with go stale as it runs. Each
//   sentence is found again by what it SAYS in the reading as it stands, never
//   by an id that was true one write ago.

const SCOPE_WORD = {
  wording: 'this wording',
  paragraph: 'this paragraph',
  section: 'this section',
  document: 'the whole document',
};

function signatureOf(card) {
  return [String(card.section || ''), String(card.before || ''), String(card.now || '')].join('\u001f');
}

export function cardsInScope(scope, key) {
  const rows = cardsNow();
  if (scope === 'wording') return rows.filter((c) => String(c.id) === String(key));
  if (scope === 'paragraph') return rows.filter((c) => String(c.section) === String(key));
  if (scope === 'section') return rows.filter((c) => headOf(c.section) === String(key));
  return rows.slice();
}

export function restoreScope(scope, key) {
  const wanted = cardsInScope(scope, key);
  if (!wanted.length) {
    toast('Nothing in this reading moved at that scope, so there is no earlier wording to put back.');
    return;
  }
  const doc = data.doc || {};
  const lock = doc.locked || '';
  const point = doc.reading || {};
  const where = lock
    ? `${doc.path || 'This document'} is ${lock}, so it is not touched at all: each wording is written to a proposal beside it, for you to answer.`
    : 'Each wording goes back into the document and is committed in your name.';
  openDialog(`Restore ${SCOPE_WORD[scope] || 'these changes'}`, 'Restore from history', `
      <p>${plural(wanted.length, 'sentence')} ${wanted.length === 1 ? 'goes' : 'go'} back to the wording that stood at <strong>${escapeHtml(point.sinceShort || 'your read point')}</strong>${point.sinceSource ? ` — ${escapeHtml(point.sinceSource)}` : ''}.</p>
      <ul>${wanted.slice(0, 8).map((c) => `<li><strong>${escapeHtml(c.section || 'This document')}</strong> — ${escapeHtml(shortOf(c.before || c.now, 64))}</li>`).join('')}</ul>
      ${wanted.length > 8 ? `<p class="muted">…and ${wanted.length - 8} more.</p>` : ''}
      <p class="muted">${escapeHtml(where)}</p>`, [
    { label: 'Cancel', kind: 'outline', action: closeDialog },
    { label: `Restore ${plural(wanted.length, 'sentence')}`, kind: 'primary', action: () => runRestore(wanted) },
  ]);
}

async function runRestore(targets) {
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
    const card = cardsNow().find((c) => signatureOf(c) === signature);
    if (!card) {
      refused.push('one sentence had left this reading by the time its turn came');
      continue;
    }
    try {
      const res = await api.restoreChange(state.managerId, state.repoId, state.docId, card.id);
      if (res && res.mode === 'candidate') proposal = res.file || proposal;
      if (res && res.mode === 'commit') commits += 1;
      landed.push(card.section || card.id);
    } catch (err) {
      refused.push(`${card.section || card.id}: ${err.message}`);
    }
    await hooks.reloadDoc();
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
    // Said out loud rather than swallowed: this app answers no route that
    // makes a proposal, so nothing was asked and nothing was recorded. The
    // server half is converge-ddt.
    toast(`Nothing was asked — this app answers no proposal route yet (${err.message}). Filed as converge-ddt.`);
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

export function openFeedback() {
  const doc = currentDoc();
  const m = data.manager;
  const context = `${m ? m.name : 'Converge'} · ${state.workspace === 'direction' && doc ? doc.fullTitle : 'Operation'}`;
  openDialog('Tell the manager what you noticed', 'Feedback', `
      <div class="dialog-field"><label for="feedbackText">Feedback</label><textarea id="feedbackText" placeholder="Still not working on Android…"></textarea></div>
      <div class="dialog-field"><label for="feedbackContext">Context the app will attach</label><input id="feedbackContext" value="${escapeHtml(context)}" readonly /></div>
      <div class="dialog-field"><label for="feedbackImage">Optional screenshot or image</label><input id="feedbackImage" type="file" accept="image/*" /></div>
      <p class="muted">The manager decides whether this reopens verification, updates existing work, or belongs back in Direction.</p>`, [
    { label: 'Cancel', kind: 'outline', action: closeDialog },
    {
      label: 'Send feedback',
      kind: 'primary',
      action: async () => {
        const text = $('feedbackText')?.value.trim();
        if (!text) { toast('Add a little feedback first.'); return; }
        const image = await readImage($('feedbackImage'));
        closeDialog();
        try {
          const res = await api.feedback(state.managerId, { text, context, imageDataUrl: image || undefined });
          toast(res && res.path ? `Feedback filed at ${res.path}` : 'Feedback delivered to the manager.');
        } catch (err) {
          toast(`Could not file the feedback: ${err.message}`);
        }
      },
    },
  ]);
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
