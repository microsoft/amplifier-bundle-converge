// Indirection so a renderer or an action can ask for a re-render (or a reload)
// without importing main.js and creating a module cycle. main.js fills these in.

export const hooks = {
  renderAll() {},
  renderDirection() {},
  renderOperation() {},
  renderConsole() {},
  selectManager() {},
  selectDoc() {},
  reloadManager() {},
  reloadDoc() {},
};
