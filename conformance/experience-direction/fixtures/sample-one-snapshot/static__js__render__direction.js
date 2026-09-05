// Direction: read, what changed, the worked-out decision, history.
const DECISION_BUTTONS = [
  ['ratified', 'Ratify'],
  ['ratified-with-edits', 'Ratify with edits'],
  ['declined', 'Decline'],
  ['later', 'Later'],
];

export function renderReview() {
  const p = openProposal();
  return `<article class="review-sheet">
    <div class="review-section"><h3>What changes</h3><p>${p.title}</p></div>
    <div class="review-section"><h3>Why now</h3><p>${p.why}</p></div>
    <div class="review-section"><h3>Evidence</h3><ul>${p.evidence}</ul></div>
    <div class="review-section"><h3>What does not change</h3><p>${p.unchanged}</p></div>
    <div class="decision-stack">${DECISION_BUTTONS.map(([v, l]) =>
      `<button data-decision="${v}">${l}</button>`).join('')}</div>
  </article>`;
}
