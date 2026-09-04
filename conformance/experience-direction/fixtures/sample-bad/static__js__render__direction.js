export function renderReview() {
  const p = openProposal();
  return `<article class="review-sheet">
    <div class="review-section"><h3>Evidence</h3><ul>${p.evidence}</ul></div>
    <div class="review-section"><h3>What changes</h3><p>${p.title}</p></div>
  </article>`;
}
