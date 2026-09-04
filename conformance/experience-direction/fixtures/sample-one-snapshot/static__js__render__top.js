// Topbar chrome and the place switch. It never touches the console.
export function renderTop() {
  document.getElementById('directionView').classList.toggle(
    'hidden', state.workspace !== 'direction');
  document.getElementById('operationView').classList.toggle(
    'hidden', state.workspace !== 'operation');
}
