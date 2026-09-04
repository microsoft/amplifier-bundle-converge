// The host half of collaboration, drawn.
//
// `contracts/experience-collaboration.v1.md`:
//
//  * clause 3 -- a pull request is laid out with the same anatomy every other
//    proposal gets: what changes, why, the evidence, what does not change, and
//    the same four words to answer with. Where it came from is printed as a
//    fact about the proposal (`source`), never a different screen. The server
//    hands these over already in `app/data.py`'s proposal shape, so nothing
//    here has to know a proposal came from the host.
//  * clause 4 -- the question box below writes a comment on the pull request
//    itself. The teammate reads it where they already are.
//  * clause 5 -- answering records the word AND posts it back to the pull
//    request. The two outcomes are reported separately, because a host that
//    refuses the comment must not make the record look unwritten.
//  * clause 6 -- this file polls. Every POLL_MS it asks the host again, so a
//    change that arrived while the steward was reading turns up without them
//    doing anything. When the host can call the app's webhook instead, the
//    server says so and the sentence at the top of the panel changes to match.
//
// It is deliberately self-contained: the partial brings this script and its
// stylesheet with it, so `{% include "collab.html" %}` is the whole wiring. If
// the panel is not on the page, everything below is a no-op.

import { state, escapeHtml } from '/static/js/state.js';

const POLL_MS = 60000;

const panel = document.getElementById('collabPanel');
const listEl = document.getElementById('collabList');
const reviewEl = document.getElementById('collabReview');
const countEl = document.getElementById('collabCount');
const freshEl = document.getElementById('collabFreshness');
const troubleEl = document.getElementById('collabTrouble');

const here = {
  managerId: null,
  proposals: [],
  openId: null,
  busy: false,
};

const DECISIONS = [
  ['ratified', 'Ratify'],
  ['ratified-with-edits', 'Ratify with edits'],
  ['declined', 'Decline'],
  ['later', 'Answer later'],
];

async function ask(url, options) {
  const res = await fetch(url, { credentials: 'same-origin', ...options });
  if (!res.ok) {
    let said = '';
    try { said = (await res.json()).reason || ''; } catch { /* not JSON */ }
    const refusal = new Error(said || `${url} answered ${res.status}`);
    refusal.status = res.status;
    throw refusal;
  }
  return res.json();
}

const send = (url, payload) => ask(url, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(payload),
});

async function managerId() {
  if (state.managerId) return state.managerId;
  if (here.managerId) return here.managerId;
  const boot = await ask('/api/boot');
  here.managerId = (boot.managers || [])[0] ? boot.managers[0].id : null;
  return here.managerId;
}

function sayFreshness(said) {
  if (freshEl && said && said.words) freshEl.textContent = said.words;
}

function sayTrouble(rows) {
  if (!troubleEl) return;
  const said = (rows || []).map((r) => `${r.repoId}: ${r.reason}`).join(' · ');
  troubleEl.textContent = said;
  troubleEl.hidden = !said;
}

function drawList() {
  if (!listEl) return;
  if (countEl) countEl.textContent = String(here.proposals.length);
  if (!here.proposals.length) {
    listEl.innerHTML = '<li class="collab-empty">No pull request is open on this session\u2019s repositories.</li>';
    return;
  }
  listEl.innerHTML = here.proposals.map((one) => `
    <li>
      <button type="button" class="collab-row${one.id === here.openId ? ' active' : ''}" data-pull="${escapeHtml(one.id)}">
        <strong>${escapeHtml(one.title)}</strong>
        <span>${escapeHtml(one.source)}</span>
      </button>
    </li>`).join('');
  listEl.querySelectorAll('[data-pull]').forEach((btn) => {
    btn.addEventListener('click', () => openOne(btn.dataset.pull));
  });
}

// The same anatomy `render/direction.js` gives a proposal from any other
// origin: what changes, why, the evidence, what does not change, one decision.
function drawProposal(one) {
  if (!reviewEl) return;
  if (!one) {
    reviewEl.innerHTML = '<p class="muted">Choose a pull request to read what it proposes.</p>';
    return;
  }
  const origin = one.origin || {};
  const list = (rows) => (rows || []).map((x) => `<li>${escapeHtml(x)}</li>`).join('');
  reviewEl.innerHTML = `
    <div class="collab-hero">
      <span class="eyebrow">${escapeHtml(one.source)}</span>
      <h3>${escapeHtml(one.title)}</h3>
      ${origin.url ? `<a class="collab-link" href="${escapeHtml(origin.url)}" target="_blank" rel="noreferrer">Open on the host</a>` : ''}
    </div>
    <div class="collab-section"><h4>What changes</h4><ul>${list(one.changes) || '<li class="muted">The pull request body says nothing under a heading this reader understands.</li>'}</ul></div>
    ${one.why ? `<div class="collab-section"><h4>Why now</h4><p>${escapeHtml(one.why)}</p></div>` : ''}
    <div class="collab-section"><h4>Evidence</h4><ul>${list(one.evidence) || '<li class="muted">No evidence was attached to this pull request.</li>'}</ul></div>
    ${one.unchanged ? `<div class="collab-section"><h4>What does not change</h4><p>${escapeHtml(one.unchanged)}</p></div>` : ''}
    <div class="collab-section">
      <h4>Conversation on the host</h4>
      ${(one.comments || []).length
        ? `<ol class="collab-comments">${one.comments.map((c) => `<li><b>${escapeHtml(c.author)}</b> <span class="muted">${escapeHtml(c.when)}</span><p>${escapeHtml(c.body)}</p></li>`).join('')}</ol>`
        : '<p class="muted">Nobody has said anything on this pull request yet.</p>'}
      <label class="collab-askbox">
        <span>Ask on the host</span>
        <textarea id="collabQuestion" rows="2" placeholder="Your question, posted as a comment on this pull request"></textarea>
      </label>
      <button type="button" class="collab-button" data-collab-ask>Post this question</button>
    </div>
    <div class="collab-section collab-decide">
      <h4>Your word</h4>
      <label class="collab-askbox">
        <span>In your own words (carried into the record and to the host, verbatim)</span>
        <textarea id="collabNote" rows="2"></textarea>
      </label>
      <div class="collab-decisions">
        ${DECISIONS.map(([value, label]) => `<button type="button" class="collab-button" data-collab-decision="${value}">${label}</button>`).join('')}
      </div>
    </div>
    <p class="collab-outcome" id="collabOutcome"></p>`;

  const q = reviewEl.querySelector('[data-collab-ask]');
  if (q) q.addEventListener('click', () => postQuestion(one));
  reviewEl.querySelectorAll('[data-collab-decision]').forEach((btn) => {
    btn.addEventListener('click', () => answer(one, btn.dataset.collabDecision));
  });
}

function outcome(said) {
  const el = document.getElementById('collabOutcome');
  if (el) el.textContent = said;
}

async function postQuestion(one) {
  const box = document.getElementById('collabQuestion');
  const said = box ? box.value.trim() : '';
  if (!said) { outcome('A question with nothing in it is not sent.'); return; }
  const origin = one.origin || {};
  try {
    const mid = await managerId();
    const done = await send(`/api/collab/${encodeURIComponent(mid)}/pulls/${origin.number}/comments`,
      { repoId: origin.repoId || '', text: said });
    outcome(done.ok ? `Posted on pull request #${origin.number}.` : `Not posted: ${done.reason}`);
    if (done.ok && box) box.value = '';
    if (done.ok) await openOne(one.id, true);
  } catch (err) {
    outcome(`Not posted: ${err.message}`);
  }
}

async function answer(one, decision) {
  const origin = one.origin || {};
  const note = document.getElementById('collabNote');
  try {
    const mid = await managerId();
    const done = await send(`/api/collab/${encodeURIComponent(mid)}/pulls/${origin.number}/answer`,
      { repoId: origin.repoId || '', decision, note: note ? note.value : '' });
    const back = done.returnedToOrigin || {};
    outcome(`${done.decision}: written to the dated ratification record. `
      + (back.ok
        ? `Posted back to pull request #${origin.number}.`
        : `NOT posted back to the host — ${back.reason || 'the host refused'}.`));
  } catch (err) {
    outcome(`Not answered: ${err.message}`);
  }
}

async function openOne(id, quiet) {
  here.openId = id;
  const known = here.proposals.find((p) => p.id === id);
  drawList();
  if (!known) return;
  const origin = known.origin || {};
  try {
    const mid = await managerId();
    const got = await ask(`/api/collab/${encodeURIComponent(mid)}/pulls/${origin.number}`
      + `?repoId=${encodeURIComponent(origin.repoId || '')}`);
    drawProposal(got.proposal);
    sayFreshness(got.freshness);
  } catch (err) {
    if (!quiet) drawProposal(known);
    outcome(`The host did not answer: ${err.message}`);
  }
}

// Clause 6: this is the polling half. It runs whether or not anyone is looking
// at the panel, so a change on the host is already here when it is opened.
async function refresh() {
  if (!panel || here.busy) return;
  here.busy = true;
  try {
    const mid = await managerId();
    if (!mid) return;
    const got = await ask(`/api/collab/${encodeURIComponent(mid)}/pulls`);
    here.proposals = got.proposals || [];
    sayFreshness(got.freshness);
    sayTrouble(got.unreadable);
    drawList();
    if (here.openId && !here.proposals.some((p) => p.id === here.openId)) {
      here.openId = null;
      drawProposal(null);
    }
  } catch (err) {
    sayTrouble([{ repoId: 'this app', reason: err.message }]);
  } finally {
    here.busy = false;
  }
}

export function mountCollab() {
  if (!panel) return null;
  refresh();
  return setInterval(refresh, POLL_MS); // poll: freshness is never the steward's job
}

const ticker = mountCollab();

export { refresh as refreshCollab, ticker as collabTicker };
