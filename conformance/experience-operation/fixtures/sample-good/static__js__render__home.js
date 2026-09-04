// Which manager session needs you?
export function renderHome() {
  const sorted = [...data.managerList].sort((a, b) => b.needs - a.needs);
  document.getElementById('homeSessionGrid').innerHTML = sorted.map((m) =>
    `<button data-home-manager="${m.id}">${m.name}</button>`).join('');
}
