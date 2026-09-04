export function renderOperation(op) {
  document.getElementById('lanesGrid').innerHTML = op.lanes.map((l) =>
    `<article class="lane-card"><span class="lane-status">${l.status}</span></article>`).join('');
}
