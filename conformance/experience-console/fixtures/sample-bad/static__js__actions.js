// controls that show a message and forget
export function wireEditing() {
  document.querySelectorAll('[data-restore]').forEach((btn) => btn.addEventListener('click', () => {
    toast('Restoring opens a proposal for your word.');
  }));
  document.querySelectorAll('[data-change-action]').forEach((btn) => btn.addEventListener('click', () => {
    toast('Change marked to keep, pending the next proposal decision.');
  }));
}

export function openSteer() {
  api.steer(state.managerId, { objective: read('steerObjective') });
}
