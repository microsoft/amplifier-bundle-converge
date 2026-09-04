// Everything that leaves the browser.
import { api } from './api.js';

export function wire() {
  qsa('[data-decision]').forEach((b) => b.addEventListener('click', () => api.decision(b.dataset.decision)));
}

export function openFeedback() { api.feedback({ text: read('feedbackText') }); }
export function publish() { api.publish({ everything: true }); }
