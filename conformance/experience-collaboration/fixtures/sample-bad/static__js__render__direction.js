// A review per origin, and nothing leaves this machine.
import { escapeHtml } from '../state.js';

function renderReview(proposal) {
  if (proposal.origin === 'a teammate') { return renderTeammateReview(proposal); }
  return `<article class="review"><h3>${escapeHtml(proposal.title)}</h3></article>`;
}

function renderReviewFromHost(proposal) {
  return `<article class="review host"><h3>${escapeHtml(proposal.title)}</h3></article>`;
}

export function answer(proposal, word) {
  return api.decision(proposal.id, word);
}
