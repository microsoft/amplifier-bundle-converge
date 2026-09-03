// Operation: the manager session at work — strategy, brief, flow, confidence, waves, lanes.
import { $, qsa, data, escapeHtml, currentManager } from '../state.js';
import { watchLane } from './console.js';

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

  const laneRows = op.lanes || [];
  $('lanesGrid').innerHTML = laneRows.map((l) => `<article class="lane-card ${escapeHtml(l.status)}"><div class="lane-main"><div class="lane-topline"><span class="lane-status ${escapeHtml(l.status)}">${escapeHtml(l.status)}</span><span class="lane-title">${escapeHtml(l.title)}</span></div><div class="lane-meta"><span>${escapeHtml(l.worker)}</span><span>${escapeHtml(l.wave)}</span><span>${escapeHtml(l.age)}</span></div></div><div class="lane-evidence"><strong>${escapeHtml(l.evidence)}</strong><button class="watch-button" data-watch-lane="${escapeHtml(l.id)}" type="button">Watch session →</button></div></article>`).join('')
    || '<p class="muted">No lanes are running right now.</p>';
  qsa('[data-watch-lane]').forEach((btn) => btn.addEventListener('click', () => watchLane(btn.dataset.watchLane)));

  const timelineRows = op.timeline || [];
  $('timelineList').innerHTML = timelineRows.map(([time, title, text]) => `<div class="timeline-entry"><div class="timeline-time">${escapeHtml(time)}</div><div class="timeline-axis"><span></span></div><div class="timeline-content"><strong>${escapeHtml(title)}</strong><p>${escapeHtml(text)}</p></div></div>`).join('')
    || '<p class="muted">No meaningful changes recorded yet.</p>';
}
