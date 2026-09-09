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

import { state, escapeHtml } from '../state.js';

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
  // converge-xet9: bumped every time a detail fetch starts (manual open or a
  // background poll of the open thread). A response is only drawn if it is
  // still the newest one in flight when it lands -- a late answer to a
  // question that no longer applies (the steward moved on, or another poll
  // already started) is silently dropped rather than drawn over whatever is
  // on screen now. That is what keeps a draft from ever becoming a comment
  // on the wrong PR.
  seq: 0,
  // converge-8crs (repaired -- see refresh() below): whose word counts
  // here. Read fresh every `refresh()` tick (mount, poll, and after each
  // answer/post) and committed only once the manager it was read FOR is
  // confirmed still the one selected -- never cached across a manager
  // switch or a principal refresh, so a stale steward's permission can
  // never stay lit on screen. `known: false` (before the first successful
  // read) is treated as NOT authorized -- missing identity is uncertainty,
  // never permission, the same rule `render/direction.js` applies to
  // Review and Changes. Guidance only: `app/collab.py`'s `answer_a_pull`
  // route is not owned by this lane, so this disables and explains the
  // control but is never the security boundary by itself.
  authority: { known: false, steward: '', isSteward: false },
  // converge-8crs (reopened -- authority-refresh): bumped at the very
  // start of every `refresh()` call, before anything else -- including
  // which manager it targets is even resolved. A call is superseded the
  // instant a newer one starts, never merely when an older one happens to
  // still be in flight. This replaces a plain `busy` boolean, which
  // guarded a NEW call on an OLD one's own progress: checked before the
  // manager was even resolved, it could suppress a refresh meant for the
  // manager the steward just switched to, and a stale call's own cleanup
  // could clear state a newer call was still relying on. `refresh()`
  // commits nothing -- authority, proposals, freshness/trouble, or a DOM
  // redraw -- unless `refreshSeq` still names it the newest call AND the
  // manager it read for is confirmed still selected, checked again after
  // EVERY awaited read, not just once at the top.
  refreshSeq: 0,
};

// Pure: reads authority for `mid` and returns it. Never touches `here`
// itself -- a helper that published straight into shared state could not
// be gated by its caller on whether the read is still wanted, which is
// exactly how a switch mid-read used to overwrite a manager the steward
// had already moved on from (converge-8crs, reopened).
async function loadAuthorityFor(mid) {
  try {
    const boot = await ask('/api/boot');
    const manager = (boot.managers || []).find((m) => m.id === mid) || null;
    const steward = (manager && manager.steward) || '';
    const user = boot.user || '';
    return { known: true, steward, isSteward: Boolean(steward) && Boolean(user) && user === steward };
  } catch {
    return { known: false, steward: '', isSteward: false };
  }
}

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
  // converge-xet9: `repoId` is an opaque identity key (unique even when two
  // repositories share a basename); `repoLabel` is what a steward actually
  // recognizes. Prefer the label, but never show nothing if an older/other
  // caller only sent the id.
  const said = (rows || []).map((r) => `${r.repoLabel || r.repoId}: ${r.reason}`).join(' · ');
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
//
// converge-ibxt: a PR's own headings may not be the three Converge asks a
// proposal to use, and that is not the same fact as the PR having nothing to
// say. `*Recognized` (set by `app/collab.py`'s `proposal_from_pull`) says
// which of those the parser actually found. When it found none, the full
// body -- server-rendered, safe Markdown -- IS the reading, shown open and
// first; a set of quick-view bullets in that case would either be empty
// (read as "nothing here", which is false) or, worse, guessed from
// paragraphs that were never labelled that way at all. When it found at
// least one, the quick view stays the glanceable summary and the full body
// sits one native disclosure away for verification -- present, but not
// repeated inline as a second copy of what the bullets already said.
function fullBodyHtml(one) {
  if (!one.bodyHtml) return '<p class="muted">This pull request has no description.</p>';
  return `<div class="collab-body-render">${one.bodyHtml}</div>`;
}

function sectionOrNote(recognized, rows, whatWord) {
  if (!recognized) {
    return `<p class="muted">This pull request's body did not use a heading this reader recognizes for ${whatWord} \u2014 unrecognized, not absent. Read the full PR body below.</p>`;
  }
  if (!rows || !rows.length) return '<p class="muted">This section was written, and left empty.</p>';
  return `<ul>${rows.map((x) => `<li>${escapeHtml(x)}</li>`).join('')}</ul>`;
}

// converge-8crs: same guidance `render/direction.js` gives Review and
// Changes -- disabled and explained before any attempt, never the only
// guard. Real security is `app/serve.py`'s `_steward_denied` pattern; this
// route (`app/collab.py`'s `answer_a_pull`) does not yet call it, which is
// a separate, out-of-ownership finding filed alongside this lane.
function collabDecisionButtonHtml(value, label) {
  const disabled = !here.authority.isSteward;
  return `<button type="button" class="collab-button"${disabled ? ' disabled aria-disabled="true"' : ''} data-collab-decision="${value}">${escapeHtml(label)}</button>`;
}

function collabStewardGateNote() {
  const said = here.authority.known && here.authority.steward
    ? `Only the registered steward (${here.authority.steward}) may decide.`
    : 'No steward is registered for this manager session yet, so nobody may decide.';
  return `<p class="muted">${escapeHtml(said)} You can still ask questions on the host.</p>`;
}

function drawProposal(one) {
  if (!reviewEl) return;
  if (!one) {
    reviewEl.innerHTML = '<p class="muted">Choose a pull request to read what it proposes.</p>';
    return;
  }
  const origin = one.origin || {};
  const anyRecognized = one.changesRecognized || one.evidenceRecognized || one.unchangedRecognized;
  const quickView = anyRecognized ? `
    <div class="collab-section"><h4>What changes</h4>${sectionOrNote(one.changesRecognized, one.changes, 'what changes')}</div>
    ${one.whyRecognized ? `<div class="collab-section"><h4>Why now</h4><p>${escapeHtml(one.why)}</p></div>` : ''}
    <div class="collab-section"><h4>Evidence the author cites <span class="muted">(not independently verified)</span></h4>${sectionOrNote(one.evidenceRecognized, one.evidence, 'evidence')}</div>
    ${one.unchangedRecognized ? `<div class="collab-section"><h4>What does not change</h4><p>${escapeHtml(one.unchanged)}</p></div>` : ''}
    <details class="collab-fullbody"><summary class="muted">Full PR body, unedited</summary>${fullBodyHtml(one)}</details>` : `
    <div class="collab-section"><h4>Full PR body</h4>${fullBodyHtml(one)}</div>
    <p class="muted">This pull request does not use headings this reader recognizes as a structured proposal (what changes \u00b7 evidence \u00b7 what does not change). Its complete, unedited body is shown above \u2014 that is not the same as having no evidence attached.</p>`;
  reviewEl.innerHTML = `
    <div class="collab-hero">
      <span class="eyebrow">${escapeHtml(one.source)}</span>
      <h3>${escapeHtml(one.title)}</h3>
      ${origin.url ? `<a class="collab-link" href="${escapeHtml(origin.url)}" target="_blank" rel="noreferrer">Open on the host</a>` : ''}
    </div>
    ${quickView}
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
        ${DECISIONS.map(([value, label]) => collabDecisionButtonHtml(value, label)).join('')}
      </div>
      ${here.authority.isSteward ? '' : collabStewardGateNote()}
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

// converge-xet9: what a background refresh must never throw away -- the
// question and decision-note drafts, which field had focus and where the
// caret sat in it, and how far the steward had scrolled into the review.
// Captured immediately before a redraw and restored immediately after, so a
// poll landing mid-sentence never costs the sentence.
function captureDraft() {
  const q = document.getElementById('collabQuestion');
  const note = document.getElementById('collabNote');
  const active = document.activeElement;
  const focusedId = active && (active.id === 'collabQuestion' || active.id === 'collabNote') ? active.id : '';
  const caret = focusedId && typeof active.selectionStart === 'number' ? active.selectionStart : null;
  return {
    question: q ? q.value : '',
    note: note ? note.value : '',
    focusedId,
    caret,
    scrollTop: reviewEl ? reviewEl.scrollTop : 0,
  };
}

function restoreDraft(draft) {
  if (!draft) return;
  const q = document.getElementById('collabQuestion');
  const note = document.getElementById('collabNote');
  if (q && draft.question) q.value = draft.question;
  if (note && draft.note) note.value = draft.note;
  if (reviewEl) reviewEl.scrollTop = draft.scrollTop || 0;
  if (draft.focusedId) {
    const el = document.getElementById(draft.focusedId);
    if (el) {
      el.focus();
      if (draft.caret !== null && typeof el.setSelectionRange === 'function') {
        try { el.setSelectionRange(draft.caret, draft.caret); } catch { /* not a text field */ }
      }
    }
  }
}

// converge-xet9 (reopened): the GET-side race guard above (`mySeq` /
// `here.openId` inside `openOne`) only ever covered a *poll* landing after
// the steward moved on. A POST completion -- posting a question, or
// answering -- awaits its own round trip, and the steward is free to switch
// to a different manager/repository/PR while that await is pending. Both
// `postQuestion` and `answer` capture what they were submitted for BEFORE
// the await, and re-check it fresh AFTER, so a completion for a thread that
// is no longer selected touches nothing already on screen: not the outcome
// sentence, not a draft, not the current selection. A completion for the
// thread that is STILL selected behaves exactly as before.
async function submissionTarget(one) {
  return { mid: await managerId(), id: one.id };
}

function sameTarget(a, b) {
  return a.mid === b.mid && a.id === b.id;
}

async function targetStillSelected(target) {
  return sameTarget(target, { mid: await managerId(), id: here.openId });
}

async function postQuestion(one) {
  const box = document.getElementById('collabQuestion');
  const original = box ? box.value : '';
  const said = original.trim();
  if (!said) { outcome('A question with nothing in it is not sent.'); return; }
  const origin = one.origin || {};
  const target = await submissionTarget(one);
  try {
    const done = await send(`/api/collab/${encodeURIComponent(target.mid)}/pulls/${origin.number}/comments`,
      { repoId: origin.repoId || '', text: said });
    if (!(await targetStillSelected(target))) return;
    // Clear the CURRENTLY LIVE textarea, looked up fresh here -- not the
    // `box` reference captured at the top of this function. A same-target
    // background poll (`refresh()` -> `openOne(id, true)`, quiet) can run
    // its own captureDraft/drawProposal/restoreDraft cycle while this POST
    // is still in flight, which replaces `#collabQuestion` with a brand-new
    // node. Clearing the OLD reference would then be a silent no-op on a
    // detached element: the node the steward is actually looking at would
    // keep showing the text they already submitted, looking exactly like an
    // unsent draft. Comparing the LIVE node's value against what was
    // submitted (not against whatever a redraw's own restoreDraft put there)
    // still leaves anything genuinely new the steward typed since untouched
    // (converge-xet9, reopened).
    const liveBox = document.getElementById('collabQuestion');
    if (done.ok && liveBox && liveBox.value === original) liveBox.value = '';
    // Reading the conversation back redraws this review, which throws away the
    // element the outcome was written into. So the redraw happens first and the
    // sentence is written after it -- otherwise a steward who posted
    // successfully saw nothing at all, which reads exactly like a failure.
    if (done.ok) await openOne(one.id, true);
    // The read-back above is its own awaited round trip -- the steward is
    // free to switch manager/repository/PR while it alone is pending, even
    // though the POST itself already passed its own check above. Recheck
    // AFTER the read-back lands, not just before it started, or a switch
    // during the read-back alone still paints this outcome sentence over
    // whatever the steward has moved on to (converge-xet9, reopened).
    if (!(await targetStillSelected(target))) return;
    outcome(done.ok ? `Posted on pull request #${origin.number}.` : `Not posted: ${done.reason}`);
  } catch (err) {
    if (!(await targetStillSelected(target))) return;
    outcome(`Not posted: ${err.message}`);
  }
}

async function answer(one, decision) {
  const origin = one.origin || {};
  const note = document.getElementById('collabNote');
  const target = await submissionTarget(one);
  try {
    const done = await send(`/api/collab/${encodeURIComponent(target.mid)}/pulls/${origin.number}/answer`,
      { repoId: origin.repoId || '', decision, note: note ? note.value : '' });
    if (!(await targetStillSelected(target))) return;
    const back = done.returnedToOrigin || {};
    const said = `${done.decision}: written to the dated ratification record. `
      + (back.ok
        ? `Posted back to pull request #${origin.number}.`
        : `NOT posted back to the host — ${back.reason || 'the host refused'}.`);
    // Same order as the question above: redraw, then say what happened, so the
    // word the steward just gave is visible beside the comment it became.
    if (back.ok) await openOne(one.id, true);
    // Same reasoning as `postQuestion` above: the read-back is its own
    // awaited round trip, and a switch during it alone -- after the POST
    // itself already passed its own check -- must not paint this outcome
    // over a manager/repository/PR the steward has since moved on to
    // (converge-xet9, reopened).
    if (!(await targetStillSelected(target))) return;
    outcome(said);
  } catch (err) {
    if (!(await targetStillSelected(target))) return;
    outcome(`Not answered: ${err.message}`);
  }
}

// converge-xet9: `quiet` means "reload the thread I already have open" --
// after posting a comment/answer, or on a background poll tick (see
// `refresh` below) -- as opposed to a steward's own click on a different row.
// Both paths share one race guard: `mySeq` is this call's own ticket, and a
// response is drawn only if nothing newer has started by the time it lands
// (`here.seq` unchanged), the steward is still looking at this same PR
// (`here.openId` unchanged), AND the manager selected when this read started
// is still the one selected now -- a switch away and back to a DIFFERENT
// manager that happens to reuse the same proposal id is not "the same PR"
// (converge-8crs, reopened; the third check is new, the first two are
// converge-xet9's, unchanged). Any one of the three moving on is reason
// enough to drop the answer silently -- drawing it would mean showing a
// reply to a question nobody is asking anymore, or worse, letting a stray
// keystroke land as a comment on the wrong PR or the wrong manager's PR.
async function openOne(id, quiet) {
  here.openId = id;
  const known = here.proposals.find((p) => p.id === id);
  drawList();
  if (!known) return;
  const origin = known.origin || {};
  const mySeq = ++here.seq;
  const draft = quiet ? captureDraft() : null;
  const mid = await managerId();
  try {
    const got = await ask(`/api/collab/${encodeURIComponent(mid)}/pulls/${origin.number}`
      + `?repoId=${encodeURIComponent(origin.repoId || '')}`);
    if (mySeq !== here.seq || here.openId !== id || (await managerId()) !== mid) return;
    drawProposal(got.proposal);
    sayFreshness(got.freshness);
    if (draft) restoreDraft(draft);
  } catch (err) {
    if (mySeq !== here.seq || here.openId !== id || (await managerId()) !== mid) return;
    // A failed read of the open thread keeps whatever is already on screen
    // (including an unsent draft) rather than replacing it with a blank or a
    // stale fallback; the sentence below is the only thing that changes.
    if (!quiet) drawProposal(known);
    if (draft) restoreDraft(draft);
    outcome(`The host did not answer: ${err.message}`);
  }
}

// Clause 6: this is the polling half. It runs whether or not anyone is looking
// at the panel, so a change on the host is already here when it is opened.
//
// converge-8crs (reopened -- authority-refresh): a review of 2924f40 found
// that this function captured its target manager (call it A) once at the
// top, then awaited `loadAuthority(A)` -- which used to mutate shared
// `here.authority` directly, inside the helper, where this caller could not
// gate the write on anything -- and then awaited A's own PR list and
// unconditionally rendered both. A steward who switched to manager B during
// EITHER await got A's authority and A's proposal list painted over B's
// screen: B's decision buttons could show A's steward's permission, and B's
// list/DOM could show A's pull requests. Separately, the old `busy` flag was
// checked before the manager was even resolved, so an old, still-running
// call for A could suppress a call that was actually meant for B, and its
// own cleanup could clear busy state a newer call needed.
//
// The fix: `refreshSeq` (see `here` above) is bumped before anything else,
// so a newer call always supersedes an older one on sight rather than being
// blocked by it. `loadAuthorityFor` (above) is pure -- it returns a reading,
// it does not publish one -- so this function decides whether a reading is
// still wanted before committing it. Every awaited read (the authority read,
// then the PR-list read) is followed by the same two checks: is this call
// still the newest (`mySeq === here.refreshSeq`), and is the manager it read
// for still the one selected (`(await managerId()) === mid`, the same
// freshly-read check `postQuestion`/`answer` already use via
// `targetStillSelected`)? Only if both hold does anything get written --
// `here.authority`, `here.proposals`, freshness/trouble text, or a DOM
// redraw. A late completion for a manager the steward has moved on from
// touches nothing; it is not merely ignored by a stale flag, it was never
// able to publish in the first place.
async function refresh() {
  if (!panel) return;
  const mySeq = ++here.refreshSeq;
  const mid = await managerId();
  if (mySeq !== here.refreshSeq || !mid) return;
  try {
    const authority = await loadAuthorityFor(mid);
    if (mySeq !== here.refreshSeq || (await managerId()) !== mid) return;
    here.authority = authority;

    const got = await ask(`/api/collab/${encodeURIComponent(mid)}/pulls`);
    if (mySeq !== here.refreshSeq || (await managerId()) !== mid) return;
    here.proposals = got.proposals || [];
    sayFreshness(got.freshness);
    sayTrouble(got.unreadable);
    drawList();
    if (here.openId && !here.proposals.some((p) => p.id === here.openId)) {
      here.openId = null;
      drawProposal(null);
    } else if (here.openId) {
      // converge-xet9: the list alone used to be all a poll refreshed -- an
      // already-open thread's own conversation, and any comment that landed
      // on it while the steward was reading, never updated until the row was
      // clicked again. Reusing openOne's "quiet" path means one implementation
      // answers both "what is open" and "what is in it", with the same race
      // guard and the same draft preservation.
      await openOne(here.openId, true);
    }
  } catch (err) {
    if (mySeq !== here.refreshSeq || (await managerId()) !== mid) return;
    // converge-xet9: a failed poll must not erase what is already on screen,
    // nor a draft the steward has begun typing -- only the freshness line
    // (sayTrouble, below) admits the read failed; nothing else moves.
    sayTrouble([{ repoId: 'this app', reason: err.message }]);
  }
}

export function mountCollab() {
  if (!panel) return null;
  refresh();
  return setInterval(refresh, POLL_MS); // poll: freshness is never the steward's job
}

const ticker = mountCollab();

// converge-xet9: a test drives one poll tick deterministically rather than
// waiting the real POLL_MS -- a module's own exports are not reachable from
// `page.evaluate`, so the same function the timer calls is also attached
// here. Nothing else reads or writes this global; it exists for tests only.
if (typeof window !== 'undefined') window.__collabRefresh = refresh;

// converge-xet9 (reopened): a test drives a SINGLE same-target quiet reopen
// deterministically -- the direct `openOne(id, true)` a background poll
// tick performs on an already-open thread, without also going through
// `refresh()`'s own authority/list round trips (whose own timing this test
// does not care about and which only add unrelated scheduling noise to a
// race that is otherwise between exactly two calls: this one and a
// submission's own read-back). Nothing else reads or writes this global; it
// exists for tests only.
if (typeof window !== 'undefined') window.__collabReopen = () => (here.openId ? openOne(here.openId, true) : null);

export { refresh as refreshCollab, ticker as collabTicker };
