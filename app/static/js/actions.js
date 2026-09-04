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

export function handleDecision(decision, label) {
  if (decision === 'ratified-with-edits') {
    openDialog('Ratify with edits', 'Direction decision', `
        <div class="dialog-field"><label for="ratifyEdit">The wording change you want before accepting</label><textarea id="ratifyEdit" placeholder="Say what you want changed…"></textarea></div>
        <p class="muted">This is recorded as one proposal decision with your edits, in your ratification log.</p>`, [
      { label: 'Cancel', kind: 'outline', action: closeDialog },
      { label: 'Ratify with edits', kind: 'primary', action: () => finalizeDecision(decision, label, $('ratifyEdit')?.value.trim() || '') },
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
