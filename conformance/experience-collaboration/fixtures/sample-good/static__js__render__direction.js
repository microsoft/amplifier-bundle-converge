// One review, whoever proposed it.
import { escapeHtml } from '../state.js';
import { api } from '../api.js';

function renderReview(proposal) {
  return `<article class="review">
      <span class="eyebrow">Proposal ${escapeHtml(proposal.id)} · ${escapeHtml(proposal.source)}</span>
      <section><h3>What changes</h3>${sentences(proposal)}</section>
      <section><h3>The evidence</h3>${evidence(proposal)}</section>
      <section><h3>What does not change</h3><p>${escapeHtml(proposal.unchanged)}</p></section>
    </article>`;
}

export function askOnTheHost(proposal, question) {
  return api.postComment(proposal.pullNumber, question);
}

export function answer(proposal, word) {
  return api.decision(proposal.id, word).then(() => api.postBackToOrigin(proposal, word));
}
