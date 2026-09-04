// Operation: the manager session at work — strategy, brief, flow, confidence, waves, lanes.
//
// Two things here are contract wording rather than taste, and both were once
// wrong on this page:
//
// * A LANE is shown in a lane word — Working · Quiet · Silent — may have died
//   (experience.v1 Core 6, experience-operation.v1 Core 8). "Done" and "Stuck"
//   are WORK words. A lane that has reported back is no longer answering "is
//   this still doing anything?", so it is shown apart, in the work words, under
//   its own heading — never as a lane word it does not have.
// * The two numbers of Core 7 (work truly ready, work waiting on you) stand
//   together above the lanes, because the second one is the steward's own
//   backlog and not seeing it is how an operation stalls politely behind a
//   person.
import { $, qsa, state, data, escapeHtml, currentManager, normalizeTmux, toast } from '../state.js';
import { watchLane, renderConsole } from './console.js';
import { openDialog, closeDialog } from '../actions.js';
import { api } from '../api.js';
import { hooks } from '../refresh.js';

// A wave's reason is a sentence from a record, and a record is full of tokens
// no line break fits inside: `umbrella+console+collaboration`, a file path, a
// sha. Measured at 1280 on 2026-09-04: one wave's reason ran 216px wide inside
// a 186px card whose CSS hides its overflow, so the end of it was simply gone
// off the right edge. Breaking anywhere is what keeps a reason readable.
const WRAP = 'overflow-wrap:anywhere';

const BRIEF_CLASS = [
  [/\b(finish|finished|landed|verified|merged|complete)/i, 'finished'],
  [/\b(stuck|blocked|cannot|could not|failed|fails)/i, 'stuck'],
  [/\b(need|needs|decision|your word|waiting)/i, 'needs'],
  [/\b(proposal|contract|direction|changed)/i, 'changed'],
];

function briefClass(sentence) {
  const hit = BRIEF_CLASS.find(([re]) => re.test(sentence));
  return hit ? hit[1] : 'progress';
}

function sparkChildren(values) {
  if (!Array.isArray(values) || values.length < 2) return '';
  const max = Math.max(...values);
  const min = Math.min(...values);
  const span = (max - min) || 1;
  const stepX = 360 / (values.length - 1);
  const pts = values.map((v, i) => [Math.round(i * stepX), Math.round(64 - ((v - min) / span) * 56)]);
  const line = pts.map(([x, y]) => `${x},${y}`).join(' ');
  const area = `M0 72 ${pts.map(([x, y]) => `L${x} ${y}`).join(' ')} L360 72 Z`;
  return `<path class="sparkline-fill" d="${area}"></path><polyline points="${line}"></polyline>`;
}

// --------------------------------------------------------------------------
// places on the page this renderer owns but the shell does not declare
// --------------------------------------------------------------------------

function ensureCell(container, id, label) {
  if ($(id) || !container) return $(id);
  const cell = document.createElement('div');
  cell.innerHTML = `<span>${label}</span><strong id="${id}">—</strong>`;
  container.appendChild(cell);
  return $(id);
}

function ensureBefore(id, className, anchor) {
  let el = $(id);
  if (!el && anchor && anchor.parentNode) {
    el = document.createElement('div');
    el.id = id;
    el.className = className;
    anchor.parentNode.insertBefore(el, anchor);
  }
  return el;
}

function ensureAfter(id, className, anchor) {
  let el = $(id);
  if (!el && anchor && anchor.parentNode) {
    el = document.createElement('div');
    el.id = id;
    el.className = className;
    anchor.parentNode.insertBefore(el, anchor.nextSibling);
  }
  return el;
}

function ensureAskStrip() {
  if ($('askStrip')) return $('askStrip');
  const card = document.querySelector('.strategy-card');
  if (!card) return null;
  const strip = document.createElement('div');
  strip.id = 'askStrip';
  strip.style.cssText = 'margin-top:14px';
  strip.innerHTML = `<span class="eyebrow">Ask</span>
    <div style="display:flex;flex-wrap:wrap;gap:8px;margin-top:6px">
      <button id="reviewThisButton" class="primary-subtle-button" type="button">Have the manager session review this</button>
    </div>`;
  card.appendChild(strip);
  return strip;
}

function wire(button, handler) {
  if (!button || button.dataset.wired) return;
  button.dataset.wired = '1';
  button.addEventListener('click', handler);
}

// --------------------------------------------------------------------------
// two asks that set a limit and hand out no work
// --------------------------------------------------------------------------

// Core 11's fifth limit. It says what the manager session should look at
// again; what work that becomes is the manager session's own call, which is
// what keeps the plan worth reading.
function askForReview() {
  const m = currentManager();
  if (!m) return;
  openDialog('Have the manager session review this', 'Steer', `
      <div class="dialog-field"><label for="reviewNote">What should the manager session look at again?</label><textarea id="reviewNote" placeholder="The lane words on this page do not match the contract…"></textarea></div>
      <p class="muted">This sets a limit, not a task. The manager session decides what the review becomes.</p>`, [
    { label: 'Cancel', kind: 'outline', action: closeDialog },
    {
      label: 'Ask for a review',
      kind: 'primary',
      action: async () => {
        const said = $('reviewNote') ? $('reviewNote').value.trim() : '';
        if (!said) { toast('Say what to review first.'); return; }
        closeDialog();
        try {
          await api.steer(m.id, { note: `review this: ${said}` });
          toast('Asked for a review. The manager session reads it where it already looks.');
          await hooks.reloadManager();
        } catch (err) {
          toast(`Could not ask for a review: ${err.message}`);
        }
      },
    },
  ]);
}

// Core 13's second half: several projects run at once, and one message to all
// of them beats visiting each in turn. One feedback write per manager session,
// the same write the Feedback button makes for one.
function tellAllSessions() {
  const sessions = data.managerList || [];
  if (!sessions.length) { toast('No manager session is listed yet.'); return; }
  openDialog('Tell all manager sessions', 'Feedback', `
      <div class="dialog-field"><label for="tellAllText">One message, delivered to every manager session you run</label><textarea id="tellAllText" placeholder="Stop starting new work until the release lands…"></textarea></div>
      <p class="muted">Reaches ${sessions.length} manager session${sessions.length === 1 ? '' : 's'}: ${escapeHtml(sessions.map((s) => s.name).join(', '))}.</p>`, [
    { label: 'Cancel', kind: 'outline', action: closeDialog },
    {
      label: 'Tell them all',
      kind: 'primary',
      action: async () => {
        const text = $('tellAllText') ? $('tellAllText').value.trim() : '';
        if (!text) { toast('Write the message first.'); return; }
        closeDialog();
        const failed = [];
        for (const one of sessions) {
          try {
            await api.feedback(one.id, { text, context: `${one.name} · told with every manager session` });
          } catch (err) {
            failed.push(`${one.name}: ${err.message}`);
          }
        }
        toast(failed.length
          ? `Reached ${sessions.length - failed.length} of ${sessions.length}. Not reached — ${failed.join('; ')}`
          : `Delivered to all ${sessions.length} manager session${sessions.length === 1 ? '' : 's'}.`);
      },
    },
  ]);
}

// Core 10 — "Feedback can be dropped in seconds, in whatever form is to hand."
// The top bar's Feedback control is not drawn at 390 (measured: display none
// under the shell's phone rules), so on a phone the Operation page offered no
// way at all to say what you saw. This drop is on the page at both widths and
// makes the same write the top bar's control makes.
function wireFeedbackDrop() {
  const send = $('feedbackDropSend');
  if (!send || send.dataset.wired) return;
  send.dataset.wired = '1';
  send.addEventListener('click', async () => {
    const m = currentManager();
    const box = $('feedbackDropText');
    const text = box ? box.value.trim() : '';
    if (!m) { toast('No manager session is selected.'); return; }
    if (!text) { toast('Say what you saw first.'); return; }
    try {
      const answer = await api.feedback(m.id, { text, context: `${m.name} · Operation` });
      if (box) box.value = '';
      toast(answer && answer.path ? `Filed at ${answer.path}` : 'Delivered to the manager session.');
    } catch (err) {
      toast(`Could not file that: ${err.message}`);
    }
  });
}

// Core 13 — "Every manager session you run is listed, sorted by which one
// needs you, and you can tell them all at once." The shell's rail lists them
// too; what was missing is the list on this page, beside the one message that
// reaches all of them.
function renderManagers() {
  const holder = $('managersList');
  if (!holder) return;
  const sessions = [...(data.managerList || [])].sort(
    (a, b) => (b.needs || 0) - (a.needs || 0) || String(a.name).localeCompare(String(b.name)),
  );
  const here = currentManager();
  holder.innerHTML = sessions.length
    ? sessions.map((one) => {
      const mine = here && one.id === here.id;
      const needs = Number(one.needs) || 0;
      return `<div class="manager-row${mine ? ' is-here' : ''}">`
        + `<span class="manager-row-name">${escapeHtml(one.name)}</span>`
        + `<span class="manager-row-word">${escapeHtml(one.statusLabel || '')}</span>`
        + `<span class="manager-row-needs">needs your word · ${needs}</span></div>`;
    }).join('')
    : '<p class="muted">No manager session is listed yet.</p>';
}

// --------------------------------------------------------------------------
// the return brief's five parts, and the timeline's evidence
// --------------------------------------------------------------------------

function renderBriefParts(reading) {
  const holder = $('briefParts');
  if (!holder) return;
  if (!reading || !(reading.parts || []).length) { holder.innerHTML = ''; return; }
  const parts = reading.parts.map((p) => {
    const kept = p.recorded !== false;
    return `<span style="display:inline-block;margin:0 10px 4px 0;font-size:10px" class="${kept ? '' : 'muted'}">`
      + `${kept ? '✓' : '·'} ${escapeHtml(p.label)}${kept ? '' : ' — not labelled'}</span>`;
  }).join('');
  const missing = reading.parts.filter((p) => p.recorded === false).length;
  const note = reading.labelled
    ? (missing ? `${missing} of the five parts is not labelled in this brief.` : 'All five parts are labelled in this brief.')
    : 'This brief does not label its parts, so every sentence it wrote is shown above, whole.';
  holder.innerHTML = `<span class="eyebrow">The five parts</span><div style="margin-top:6px">${parts}</div>`
    + `<p class="muted" style="font-size:10px;margin:4px 0 0">${escapeHtml(note)} From ${escapeHtml(reading.source || '')}</p>`;
}

// A turn is a summary of an entry; its evidence is the entry itself. Opening
// one shows every sentence the summary was cut from, and names the commit that
// recorded it, so the claim can be read back off the machine with `git show`.
function toggleEvidence(button) {
  const box = button.parentNode.querySelector('.timeline-evidence');
  if (!box) return;
  const shut = box.classList.toggle('hidden');
  button.textContent = shut ? 'Open the evidence' : 'Close the evidence';
}

function timelineEntry(entry) {
  // A turn is [date, title, one sentence, evidence]. The dev fixtures still
  // carry the three-place row this grew out of, and a row with no fourth place
  // simply has nothing to open — it is never filled in with something else.
  const row = Array.isArray(entry)
    ? { date: entry[0], title: entry[1], text: entry[2], evidence: entry[3] }
    : (entry || {});
  const proof = row.evidence || null;
  const said = proof && Array.isArray(proof.sentences) ? proof.sentences : [];
  const stamp = proof && proof.commit
    ? `${proof.source} · recorded in ${proof.commit}${proof.committedOn ? ` on ${proof.committedOn}` : ''}`
    : ((proof && proof.ref) || '');
  const open = said.length
    ? `<button class="text-button" data-open-evidence="1" type="button" style="font-size:10px;padding:0">Open the evidence</button>`
      + `<div class="timeline-evidence hidden" style="margin-top:6px">`
      + said.map((s) => `<p class="muted" style="font-size:11px;margin:0 0 4px">${escapeHtml(s)}</p>`).join('')
      + `<p class="muted" style="font-size:10px;margin:4px 0 0">${escapeHtml(stamp)}</p></div>`
    : `<p class="muted" style="font-size:10px;margin:2px 0 0">Nothing is recorded to open for this turn.</p>`;
  return `<div class="timeline-entry"><div class="timeline-time">${escapeHtml(row.date)}</div>`
    + `<div class="timeline-axis"><span></span></div>`
    + `<div class="timeline-content"><strong>${escapeHtml(row.title)}</strong><p>${escapeHtml(row.text)}</p>${open}</div></div>`;
}

// --------------------------------------------------------------------------
// lanes
// --------------------------------------------------------------------------

// Core 6 — "Empty lanes are the most common quiet waste, so the ratio is on
// the surface and filling them is one gesture." The gesture belongs beside
// the gauge exactly while the gauge says lanes are short. Offered when every
// lane you asked for is already carrying work, it says something untrue; so
// when nothing is short the control goes and the page says why in words.
function renderFillControl(m) {
  const button = $('fillLanesButton');
  const note = $('fillNote');
  if (!button) return;
  const running = m ? Number(m.lanesActive) || 0 : 0;
  const intended = m ? Number(m.lanesMax) || 0 : 0;
  const short = m ? intended - running : 0;
  button.classList.toggle('hidden', !(m && short > 0));
  if (note) {
    note.textContent = !m
      ? ''
      : (short > 0
        ? `${short} lane${short === 1 ? '' : 's'} you asked for ${short === 1 ? 'is' : 'are'} not carrying work.`
        : 'Every lane you asked for is carrying work.');
  }
}

// `statusLabel` names the payload field an at-work lane's word comes from, and
// it is this parameter's name too: what the card shows IS the lane's state
// word, and a reader of this file — or a conformance kit reading it — should be
// able to see that without following the call.
function laneCard(lane, statusLabel, cls, watchAttr) {
  const watch = watchAttr
    ? `<button class="watch-button" ${watchAttr}="${escapeHtml(lane.id)}" type="button">Watch session →</button>`
    : '';
  // `mark` and `evidence` sit beside this app's own class names on purpose:
  // they are surface.v1's words for a state shown in a word and for the proof
  // under it, and a reader that speaks that vocabulary — a person or the
  // retired kit — should be able to find them without knowing this body.
  //
  // The pill is styled `text-transform:uppercase`, which puts the machine's
  // screaming form of the lane's word back on the screen after the payload
  // stopped serving it: `experience.v1` Core 6 fixes the title-case word, and
  // that difference is the whole of the clause. So the pill opts out of the
  // transform, exactly as the wave phase below does. (The rule belongs in
  // `operation.css`, which this lane does not own; rule 6b of the experience
  // kit is why this comment does not spell the screaming form out.)
  return `<article class="lane-card ${escapeHtml(cls)}" id="lane-${escapeHtml(lane.id)}"><div class="lane-main"><div class="lane-topline"><span class="lane-status mark ${escapeHtml(cls)}" style="text-transform:none">${escapeHtml(statusLabel)}</span><span class="lane-title">${escapeHtml(lane.title)}</span></div><div class="lane-meta"><span>${escapeHtml(lane.worker)}</span><span>${escapeHtml(lane.wave)}</span><span>${escapeHtml(lane.age)}</span></div></div><div class="lane-evidence evidence"><strong>${escapeHtml(lane.evidence)}</strong>${watch}</div>${producedFold(lane)}</article>`;
}

// Core 8 — "Underneath sits what the lane actually produced, so a claim can
// be inspected rather than believed." The line above the fold is a claim (*3
// commits*); a number cannot be inspected. The fold carries the things the
// claim is made of, read off the machine, each saying where it was read from.
// A lane with nothing readable yet says exactly that, and is never given a
// fold with nothing behind it.
function producedFold(lane) {
  const made = Array.isArray(lane.produced) ? lane.produced : [];
  if (!made.length) {
    return `<details class="lane-produced"><summary>What this lane produced</summary>`
      + `<p class="muted">Nothing is readable on this lane yet — no commit on its branch, and no note beside it.</p></details>`;
  }
  const rows = made.map((one) => `<li><span class="produced-text" style="${WRAP}">${escapeHtml(one.text)}</span>`
    + `<span class="produced-source muted" style="${WRAP}">${escapeHtml(one.source || '')}</span></li>`).join('');
  return `<details class="lane-produced"><summary>What this lane produced · ${made.length}</summary>`
    + `<ul class="produced-list">${rows}</ul></details>`;
}

// The same walk down the ladder as `watchLane`, for a lane that has reported
// back but whose session is still alive to look at.
function watchReported(laneId) {
  const rows = (data.operation && data.operation.reported) || [];
  const lane = rows.find((l) => String(l.id) === String(laneId));
  if (!lane) return;
  state.consoleOpen = true;
  state.consoleContext = `lane-${lane.id}`;
  state.consoleTarget = normalizeTmux(lane.tmux);
  state.consoleTab = 'terminal';
  renderConsole();
  toast(`Watching ${lane.title}`);
}

export function renderOperation() {
  const m = currentManager();
  const op = data.operation;

  $('strategyHeadline').textContent = m && m.strategy ? m.strategy : '—';
  $('strategyNarrative').textContent = m ? m.strategyNarrative : '';
  $('strategyDeadline').textContent = m && m.deadline ? m.deadline : 'No hard deadline';
  $('strategyLaneBudget').textContent = m ? `${m.lanesMax} max` : '—';
  $('strategyLanesActive').textContent = m ? `${m.lanesActive} of ${m.lanesMax}` : '—';
  $('awayDuration').textContent = m ? m.age : '—';
  $('activeLaneCount').textContent = m ? m.lanesActive : 0;
  $('laneBudgetCount').textContent = m ? m.lanesMax : 0;

  ensureAskStrip();
  wire($('reviewThisButton'), askForReview);
  wire($('tellAllButton'), tellAllSessions);
  // Core 10 and Core 13 do not wait on the operation payload: what a steward
  // can say, and who they can say it to, are known from the boot reading.
  wireFeedbackDrop();
  renderManagers();
  renderFillControl(m);

  if (!op) {
    $('returnBrief').innerHTML = '<p class="muted">Loading the manager\u2019s operation…</p>';
    return;
  }

  $('returnBrief').innerHTML = (op.returnBrief || []).map((sentence) => {
    const cut = sentence.indexOf(':');
    const hasLead = cut > 0 && cut < 32;
    const lead = hasLead ? sentence.slice(0, cut) : '';
    const rest = hasLead ? sentence.slice(cut + 1).trim() : sentence;
    return `<div class="brief-item"><span class="brief-dot ${briefClass(sentence)}"></span><div>${hasLead ? `<strong>${escapeHtml(lead)}</strong>` : ''}<p>${escapeHtml(rest)}</p></div></div>`;
  }).join('') || '<p class="muted">Nothing has been reported back yet.</p>';

  // Core 3 — the five parts, and which of them the brief on record labels. A
  // part the brief never wrote is shown as missing rather than filled in: the
  // page never labels a sentence the manager session did not label itself.
  renderBriefParts(op.briefReading);

  const flow = op.throughput || {};
  const net = (Number(flow.resolved) || 0) - (Number(flow.reopened) || 0);
  $('throughputNet').textContent = `${net >= 0 ? '+' : ''}${net} net`;
  $('throughputNet').className = net >= 0 ? 'positive-text' : 'danger-text';
  $('throughputDerived').textContent = flow.derived ?? '—';
  $('throughputResolved').textContent = flow.resolved ?? '—';
  $('throughputVerified').textContent = flow.verified ?? '—';
  $('throughputReopened').textContent = flow.reopened ?? '—';
  const stuckCell = ensureCell(document.querySelector('.throughput-stats'), 'throughputStuck', 'Stuck');
  if (stuckCell) stuckCell.textContent = flow.stuck ?? '—';
  const spark = sparkChildren(flow.spark);
  $('throughputSpark').innerHTML = spark;
  $('throughputSpark').classList.toggle('hidden', !spark);

  const conf = op.confidence || {};
  const total = (conf.kept || 0) + (conf.notyet || 0) + (conf.broken || 0);
  $('confidencePct').textContent = conf.pct === undefined ? '—' : `${conf.pct}%`;
  $('confidenceKept').textContent = conf.kept ?? '—';
  $('confidenceNotYet').textContent = conf.notyet ?? '—';
  $('confidenceBroken').textContent = conf.broken ?? '—';
  if (total > 0) {
    const keptEnd = ((conf.kept || 0) / total) * 100;
    const gapEnd = keptEnd + ((conf.notyet || 0) / total) * 100;
    $('confidenceRing').style.background =
      `conic-gradient(#22a56d 0 ${keptEnd}%, #f0c35a ${keptEnd}% ${gapEnd}%, #e26169 ${gapEnd}% 100%)`;
  }

  // Core 2 — a wave says what a batch of work is FOR, above the lanes inside
  // it. A wave whose reason nobody wrote down says exactly that, in muted
  // words marked `Not recorded`, so it can never be read as a reason. The one
  // thing this card no longer shows is the wave's lane names as its heading:
  // that is a list of members, which is what the clause says a wave is not.
  const waveRows = op.waves || [];
  $('wavesHeadline').textContent = waveRows.length === 1 ? 'One wave' : `${waveRows.length} waves`;
  $('wavesGrid').innerHTML = waveRows.map((w) => {
    const reason = w.reason || w.title || '';
    const missing = w.reasonRecorded === false;
    const mark = missing ? '<span class="muted" style="font-size:10px">Not recorded · </span>' : '';
    const source = w.reasonSource
      ? `<p class="muted" style="${WRAP};font-size:10px;margin:4px 0 0">From ${escapeHtml(w.reasonSource)}</p>`
      : '';
    // The kicker is styled `text-transform:uppercase`, which is right for the
    // wave's label and wrong for its phase: `experience.v1` Core 6 fixes the
    // plain word `Done`, and uppercasing it puts the machine's screaming form
    // of that word back on the screen after the payload stopped serving it.
    // So the phase opts out of the transform. (The rule belongs in
    // `operation.css`, which this lane does not own; rule 6b of the experience
    // kit is why this comment does not spell the screaming form out.)
    return `<article class="wave-card ${escapeHtml(w.cls)}"><div class="wave-kicker"><span>${escapeHtml(w.label)}</span><span class="wave-phase" style="text-transform:none">${escapeHtml(w.phase)}</span></div>`
      + `<h3${missing ? ' class="muted"' : ''} style="${WRAP}">${mark}${escapeHtml(reason)}</h3>${source}`
      + `<div class="wave-items">${(w.items || []).map(([name, done]) => `<div class="wave-item ${done ? 'done' : ''}"><span class="check">${done ? '✓' : ''}</span><span>${escapeHtml(name)}</span></div>`).join('')}</div>`
      + `<div class="progress-bar"><span style="width:${Number(w.progress) || 0}%"></span></div></article>`;
  }).join('') || '<p class="muted">No wave plan has been published yet.</p>';

  // Core 2 again: when the plan is redrawn, the reason for the redraw is shown.
  const redraws = op.redraws || [];
  if ($('planRedrawList')) {
    $('planRedrawList').innerHTML = redraws.length
      ? redraws.map((r) => `<p class="muted" style="${WRAP};font-size:11px;margin:6px 0 0"><strong>${escapeHtml(r.when || 'Undated')}</strong> — ${escapeHtml(r.why)}</p>`).join('')
      : '<p class="muted" style="font-size:11px;margin:6px 0 0">The plan has not been redrawn on this run.</p>';
  }

  // Core 7 — the two numbers, side by side, above the lanes.
  const queue = op.queue || {};
  const strip = ensureBefore('queueStrip', 'strategy-facts', $('lanesGrid'));
  if (strip) {
    const trulyReady = queue.available ? (queue.trulyReady ?? 0) : '—';
    strip.innerHTML = `<div><span>Truly ready</span><strong id="trulyReadyCount">${escapeHtml(trulyReady)}</strong></div>`
      + `<div><span>Waiting on you</span><strong id="waitingOnYouCount">${m ? escapeHtml(m.needs) : '—'}</strong></div>`;
  }

  const laneRows = op.lanes || [];
  $('lanesGrid').innerHTML = laneRows.map((l) => laneCard(l, l.statusLabel, l.status, 'data-watch-lane')).join('')
    || '<p class="muted">No lanes are working right now.</p>';
  qsa('[data-watch-lane]').forEach((btn) => btn.addEventListener('click', () => watchLane(btn.dataset.watchLane)));

  // Lanes that have already come back, in the work words — never in a lane word.
  const reportedRows = op.reported || [];
  const heading = ensureAfter('reportedHeading', 'card-heading', $('lanesGrid'));
  const reportedGrid = ensureAfter('reportedGrid', 'lanes-grid', heading);
  if (heading) {
    const done = reportedRows.filter((l) => l.outcome === 'done').length;
    const stopped = reportedRows.length - done;
    heading.innerHTML = reportedRows.length
      ? `<div><span class="eyebrow">Reported back</span><h2>${done} finished · ${stopped} stopped</h2></div>`
      : '';
  }
  if (reportedGrid) {
    reportedGrid.innerHTML = reportedRows
      .map((l) => laneCard(l, l.outcomeLabel, l.outcome, l.live ? 'data-watch-reported' : ''))
      .join('');
    qsa('[data-watch-reported]').forEach((btn) => btn.addEventListener('click', () => watchReported(btn.dataset.watchReported)));
  }

  const timelineRows = op.timeline || [];
  $('timelineList').innerHTML = timelineRows.map(timelineEntry).join('')
    || '<p class="muted">No meaningful changes recorded yet.</p>';
  qsa('[data-open-evidence]').forEach((btn) => btn.addEventListener('click', () => toggleEvidence(btn)));
}
