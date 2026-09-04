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
      <button id="tellAllButton" class="primary-subtle-button" type="button">Tell all manager sessions</button>
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

// --------------------------------------------------------------------------
// lanes
// --------------------------------------------------------------------------

// `statusLabel` names the payload field an at-work lane's word comes from, and
// it is this parameter's name too: what the card shows IS the lane's state
// word, and a reader of this file — or a conformance kit reading it — should be
// able to see that without following the call.
function laneCard(lane, statusLabel, cls, watchAttr) {
  const watch = watchAttr
    ? `<button class="watch-button" ${watchAttr}="${escapeHtml(lane.id)}" type="button">Watch session →</button>`
    : '';
  return `<article class="lane-card ${escapeHtml(cls)}"><div class="lane-main"><div class="lane-topline"><span class="lane-status ${escapeHtml(cls)}">${escapeHtml(statusLabel)}</span><span class="lane-title">${escapeHtml(lane.title)}</span></div><div class="lane-meta"><span>${escapeHtml(lane.worker)}</span><span>${escapeHtml(lane.wave)}</span><span>${escapeHtml(lane.age)}</span></div></div><div class="lane-evidence"><strong>${escapeHtml(lane.evidence)}</strong>${watch}</div></article>`;
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

  const waveRows = op.waves || [];
  $('wavesHeadline').textContent = waveRows.length === 1 ? 'One wave' : `${waveRows.length} waves`;
  $('wavesGrid').innerHTML = waveRows.map((w) => `<article class="wave-card ${escapeHtml(w.cls)}"><div class="wave-kicker"><span>${escapeHtml(w.label)}</span><span>${escapeHtml(w.phase)}</span></div><h3>${escapeHtml(w.title)}</h3><div class="wave-items">${(w.items || []).map(([name, done]) => `<div class="wave-item ${done ? 'done' : ''}"><span class="check">${done ? '✓' : ''}</span><span>${escapeHtml(name)}</span></div>`).join('')}</div><div class="progress-bar"><span style="width:${Number(w.progress) || 0}%"></span></div></article>`).join('')
    || '<p class="muted">No wave plan has been published yet.</p>';

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
  $('timelineList').innerHTML = timelineRows.map(([time, title, text]) => `<div class="timeline-entry"><div class="timeline-time">${escapeHtml(time)}</div><div class="timeline-axis"><span></span></div><div class="timeline-content"><strong>${escapeHtml(title)}</strong><p>${escapeHtml(text)}</p></div></div>`).join('')
    || '<p class="muted">No meaningful changes recorded yet.</p>';
}
