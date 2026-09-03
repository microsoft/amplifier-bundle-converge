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
