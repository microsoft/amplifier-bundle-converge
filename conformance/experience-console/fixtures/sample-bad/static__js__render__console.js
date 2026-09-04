export function renderConsole() {
  document.getElementById('consoleBody').innerHTML = '<p>no session</p>';
}

export function submitConsole(line) {
  api.decision(state.managerId, { decision: line });
}
