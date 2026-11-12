# Deriving contracts from an existing repository

This is authoring guidance, not a new contract format or a change to Converge's
governing rules.

Use this when asked to establish behavioral contracts for code that already
exists, including a repository that has specifications but no explicit contract
set. The goal is to identify the promises consumers depend on, not to turn the
implementation into a specification of itself.

## Establish the scope and authority

Read the repository's instructions and existing agreements first. Identify whether
the task is to describe an implementation baseline, propose new requirements, or
both. Keep those outputs distinct. Reuse decisions already made; ask only when an
unresolved choice would change the promised behavior or authorized scope.

Record which contract guidance and revision applies. Use the project's applicable
format and review process. If guidance conflicts, name the conflicting passages
and the affected decision separately. Do not silently combine formats, claim an
adaptation is prescribed, or repair the guidance as part of deriving contracts.
Continue investigation and drafting that does not depend on that decision.

Derivation does not authorize implementation, ratification, publication or a
broader adoption operation. Preserve unrelated work and remain within the scope
the person requested.

## Investigate from the consumer's side

Start with who uses the repository and what crosses its boundaries: public
operations, observable outcomes, consumed data, and interactions with other
components. Follow those paths through the implementation, including failure
paths and configuration-dependent behavior. Do not organize contracts around the
repository's classes or directory tree merely because those are easy to enumerate.

Treat descriptive documentation, designs, comments and test names as leads to
check, not proof of implementation. Read the relevant executable paths and what
tests actually assert. Where authorized and practical, use a focused probe to
resolve uncertainty. Source inspection establishes less than observing the
behavior in the environment where a consumer relies on it.

Keep existing accepted obligations distinct from descriptive claims. Code may
contradict a promise without invalidating it. Record that discrepancy; do not
weaken an accepted contract to make the implementation conform. Conversely, a
planned capability in a design document does not establish present behavior.

Retain the source revision, relevant paths, consumer evidence, contrary findings
and verification limits in the existing investigation record. This is the basis
for challenging a draft, not content to paste into its promises.
Keep that evidence within its authorized sharing boundary. An upstream
contribution must not expose private source excerpts, paths or session references
merely because they are placed in supporting notes rather than contracts.

## Classify findings before drafting promises

Distinguish these cases in the investigation record:

- **Accepted obligation:** a promise already established by the project's
  governing documents or explicit decisions. An implementation mismatch is a gap,
  not permission to redefine the promise.
- **Inferred reliance:** observed behavior that a consumer depends on, but which
  has not yet been agreed as a contract. Propose it with its evidence and limits.
- **Proposed requirement:** behavior someone wants but which the inspected
  implementation does not establish. Keep it separate from the baseline.
- **Incidental mechanism or defect:** something the implementation does, without
  establishing that it should be preserved. Record any consumer impact and
  compatibility risk; visibility alone does not make it a desirable guarantee.
- **Unresolved or unspecified behavior:** insufficient evidence or no settled
  decision. Preserve that uncertainty rather than completing the story by guess.

One finding can involve several of these: a defect can violate an accepted
obligation while a consumer also depends on its current behavior. Retain both
facts and bring the actual choice to review.

Do not promise that a defect has been repaired, or require it to remain forever.
State material limitations precisely where they affect what a consumer can rely
on. A missing guarantee is not the same as a guarantee of failure. Keep proposed
remedies and current implementation status outside the contract's promise prose.

## Write the reliance, not the mechanism

For each candidate promise, ask:

- Who relies on this behavior?
- What must remain true for them?
- What would they observe if it were violated?
- Could the owned internals change without affecting that reliance?

Write the observable rule in plain language, with the conditions and limitations
needed to make it accurate. Remove internal placement, helper names, storage
choices and execution sequences unless a consumer genuinely relies on them.
Do not replace precise behavior with vague assurances to make the text shorter.

Exact public names, values and formats can be essential to a contract. Keep or
reference them when compatibility depends on them; do not remove them merely
because they are technical. Reference an existing authoritative schema or surface
specification instead of copying its entire inventory into the contract.

Avoid adding guarantees that the task did not request and the evidence does not
support. Reliability mechanisms, compatibility schemes and future extensibility
are design choices, not automatic consequences of documenting existing code.

Keep working notes, source maps, test-run output, investigation history and repair
plans in the appropriate supporting records. Observable conformance assertions
are different from test reports: follow the applicable contract format without
turning its check section into an investigation log. Document agreement state is
also different from implementation status; this guidance changes neither policy.

## Check ownership across components

Assign each promise to the component responsible for keeping it. A producer's
contract describes what it provides; a consumer's contract describes its use and
policy. Keep shared interfaces in their established owning documents and refer
to them rather than repeating their rules in every repository.

Review the set for obligations assigned to the wrong owner, incompatible meanings
and vocabulary borrowed from one implementation into a general interface.
Generalize only as far as the actual audience and agreed scope justify.

If multiple authors work in parallel, use the same scope, evidence distinctions
and review questions. Check a representative draft for the right level of detail
before expanding the set. This is a drafting quality check, not another mandatory
human approval gate. Finish with a cross-component review; consistent formatting
alone does not establish consistent promises.

## Make examples accurate where the format calls for them

A small public input, output or artifact can clarify a promise without becoming a
source walkthrough. Check examples of existing behavior against the implementation;
label omissions, placeholders and relevant conditions. Do not imply universal
ordering or success from a single successful path.

For a proposed interface whose details are not settled, use a clearly conceptual
illustration rather than inventing endpoints, fields or enum values. An example
must not quietly add an obligation or contradict the deciding text. This does not
require a separate worked-example document or a synthetic project.

## Review the result and hand it back honestly

Before presenting the drafts, check that:

- Every promise has a named consumer and an observable meaning.
- Baseline behavior and proposed changes are distinguishable without reading
  the investigation history.
- Existing obligations have not been weakened to match broken code, and defects
  have not been promoted into permanent requirements.
- Material limitations remain explicit without freezing incidental mechanisms.
- Each component owns its promises, and shared rules are referenced consistently.
- Examples and referenced specifications agree with the proposed promises.
- Supporting evidence is retrievable without crowding the contract itself.

For each promise, identify what a check at the consumer boundary would need to
observe. Could the proposed check pass while the promise is false? If so, refine
the check. Record separately what was inspected, what was executed, what passed
or failed, and what remains unchecked. A test reference is not a passing test;
source review and structural validation are not runtime conformance.

Present explicit repository and file paths. Keep baseline review separate from
new requirements, and distinguish unsettled decisions from verification gaps.
In the handoff, identify accepted obligations that the implementation does not
meet or that remain unverified; keep that current status out of the promise prose.
If the implementation changes during review, refresh the affected evidence and
wording before claiming the baseline is current. Report drafts as drafts under
the applicable process, not as ratified contracts or verified implementation.
