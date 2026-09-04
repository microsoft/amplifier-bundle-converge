// every control that leaves the browser reaches a declared write
import { api } from './api.js';

export function wireEditing() {
  document.querySelectorAll('[data-edit]').forEach((btn) => btn.addEventListener('click', () => {
    api.save(state.managerId, { repoId: state.repoId, docId: state.docId, body: editorText() });
  }));
  document.querySelectorAll('[data-restore]').forEach((btn) => btn.addEventListener('click', () => {
    api.ask(state.managerId, { scope: btn.dataset.restore, intent: 'restore this wording' });
  }));
  document.querySelectorAll('[data-change-action]').forEach((btn) => btn.addEventListener('click', () => {
    api.decision(state.managerId, { proposalId: openProposalId(), staged: btn.dataset.changeAction });
  }));
  document.querySelectorAll('[data-ask]').forEach((btn) => btn.addEventListener('click', () => {
    api.ask(state.managerId, { scope: btn.getAttribute('scope') });
  }));
}

export function openFeedback() {
  const forms = { text: true, image: 'image/*', voice: 'audio/*' };
  api.feedback(state.managerId, { text: read('feedbackText'), forms });
}

export function fillLanes() {
  api.steer(state.managerId, { fill: true });
}

export function openSteer() {
  // objective, budget, lane count, fill the lanes, review this
  api.steer(state.managerId, {
    objective: read('steerObjective'), budget: read('steerBudget'),
    lanes: read('steerLanes'), fill: read('fillLanes'), review: read('managerReview'),
  });
}
