// Manager Console: one pane, one manager session.
export function watchLane(laneId) {
  const lane = data.operation.lanes.find((l) => String(l.id) === String(laneId));
  state.consoleTarget = lane.tmux;
  state.consoleContext = `lane-${lane.id}`;
  renderConsole();
}

export function showManagerConsole() {
  state.consoleContext = 'manager';
  state.consoleTarget = null;
  renderConsole();
}

export function renderConsole() {
  const target = activeTarget();
  window.ConvergeTmux.attach(document.getElementById('terminalHost'),
                             target.socket, target.session);
}

export function sendLine(line) {
  fetch(`/api/tmux/${target.socket}/${target.session}/keys`, {
    method: 'POST', body: JSON.stringify({ keys: line }),
  });
}
