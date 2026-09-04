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
import { handleDecision, keepChange, saveChangeEdit, restoreChange, markAllRead, editDoc, reconcile, openAsk } from '../actions.js';

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
// What is honest here today: the soft marking and the three choices are real,
// and the presence is this browser's own. There is no channel that carries a
// second person's editing, which is why the fold below says so instead of
// implying a company that is not there. The channel is converge-wmh.
function editPanel(doc, card) {
  const lock = doc.locked || '';
  const clash = state.collision && String(state.collision.section) === String(card.section) ? state.collision : null;
  return `<div class="change-edit" data-editing="${escapeHtml(card.id)}">
      <p class="muted lock-note">You are editing this section. It is shown softly while you write — that is the presence, so a change landing underneath you is offered as a choice rather than applied over you.${lock ? ` This document is ${escapeHtml(lock)}, so saving writes a proposal beside it and the document itself is not touched.` : ''}</p>
      <label for="read-edit-${escapeHtml(card.id)}">The wording you want instead</label>
      <textarea id="read-edit-${escapeHtml(card.id)}" rows="3">${escapeHtml(card.now || card.before)}</textarea>
      ${clash ? collisionPanel(clash) : ''}
      <div class="change-edit-actions">
        <button class="outline-button" data-edit="cancel" type="button">Cancel</button>
        <button class="primary-button" data-edit="save" data-change-id="${escapeHtml(card.id)}" type="button">${lock ? 'Propose this wording' : 'Save'}</button>
      </div>
      <details><summary class="muted">Details</summary><p class="muted">Presence is this browser only: the app carries no signal for someone else editing the same section, and the manager session is not told to queue. Filed as converge-wmh.</p></details>
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
    return `
      <section class="${changedSections.has(title) ? 'marked-change' : ''}${editing ? ' is-editing' : ''}">
        <h2>${escapeHtml(title)}</h2>
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

export function renderHistory() {
  const historyRows = (data.doc && data.doc.history) || [];
  if (!historyRows.length) return '<p class="muted">No recorded history for this document yet.</p>';
  const snap = historyRows.find((h) => h.id === state.historyId) || historyRows[0];
  // Restoring is done sentence by sentence in Changes, where it is a real
  // write. The three buttons that used to sit here only ever showed a message,
  // so they are a pointer now rather than a promise nothing keeps.
  return `<div class="history-layout"><div class="history-list">${historyRows.map((h) => `<button class="history-item ${h.id === snap.id ? 'active' : ''}" data-history="${escapeHtml(h.id)}" type="button"><strong>${escapeHtml(h.label)}</strong><br><span>${escapeHtml(h.date)}</span></button>`).join('')}</div>
      <div class="history-snapshot"><span class="eyebrow">${escapeHtml(snap.date)}</span><h3>${escapeHtml(snap.label)}</h3><p>${escapeHtml(snap.note)}</p>${snap.sha ? `<details><summary class="muted">Details</summary><p><code>${escapeHtml(snap.sha)}</code></p></details>` : ''}<div class="history-actions"><p class="muted">Restoring earlier wording is done change by change in <strong>Changes</strong>, where each restore is a real write.</p><button class="outline-button" data-inline-mode="changes" type="button">Open Changes</button></div></div></div>`;
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
  renderRepoTree();
  const repo = currentRepo();
  const navDoc = currentDoc();
  const doc = data.doc;
  const changeCount = (doc && doc.changes ? doc.changes.length : 0);
  const proposalCount = (doc && doc.proposals ? doc.proposals.length : 0);

  $('docPath').textContent = doc ? doc.path : (repo && navDoc ? `${repo.name} / ${navDoc.title}` : '—');
  $('docTitle').textContent = doc ? doc.title : (navDoc ? navDoc.fullTitle : '');
  $('docUpdated').textContent = doc ? doc.updated : '';
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

  let html = '';
  if (state.docMode === 'read') html = renderRead();
  if (state.docMode === 'changes') html = renderChanges();
  if (state.docMode === 'review') html = renderReview();
  if (state.docMode === 'history') html = renderHistory();
  $('documentModeContent').innerHTML = html;
  attachDocumentModeHandlers();
  renderProposalMini();

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
