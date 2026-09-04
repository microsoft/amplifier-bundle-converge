// Every write, and the manager-session operation that does the same thing.
import { api } from './api.js';

// experience.v1 clause 8 — whatever you can do here, the manager session can do
// too, and the surface says which operation that is.
export const MANAGER_OPERATIONS = {
  decision: 'manager-session operation: record the steward word in the dated record',
  priority: 'manager-session operation: raise or lower a priority in the queue',
  feedback: 'manager-session operation: drop feedback into the return log',
  steer: 'manager-session operation: steer the objective, the budget, the lanes',
  ask: 'manager-session operation: ask for a proposal at a named scope',
};

export function wire() {
  qsa('[data-decision]').forEach((b) => b.addEventListener('click', () => api.decision(b.dataset.decision)));
  qsa('[data-priority]').forEach((b) => b.addEventListener('click', () => api.priority(b.dataset.priority)));
  qsa('[data-ask]').forEach((b) => b.addEventListener('click', () => api.ask()));
}

export function openFeedback() { api.feedback({ text: read('feedbackText') }); }
export function openSteer() { api.steer({ objective: read('steerObjective') }); }
