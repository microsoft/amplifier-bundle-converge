// Operation: strategy, brief, flow, confidence, waves, lanes.
export function renderOperation(op) {
  document.getElementById('lanesGrid').innerHTML = op.lanes.map((l) =>
    `<article class="lane-card"><span class="lane-status">${l.status}</span>
     <span class="lane-title">${l.title}</span>
     <details><summary>Evidence</summary><p>${l.evidence}</p></details>
     <button data-watch-lane="${l.id}">Watch session</button></article>`).join('');
  document.getElementById('wavesGrid').innerHTML = op.waves.map((w) =>
    `<article class="wave-card"><h3>${w.title}</h3><p class="wave-reason">${w.reason}</p>
     </article>`).join('');
}
