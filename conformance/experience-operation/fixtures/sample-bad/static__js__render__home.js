export function renderHome() {
  document.getElementById('homeSessionGrid').innerHTML =
    data.managerList.map((m) => `<button>${m.name}</button>`).join('');
}
