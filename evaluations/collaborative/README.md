# A collaborative journey in a text-only session

This is an acceptance scenario to run with a real agent and steward, not a
recorded pass or an additional contract. It exercises `operation.v1`'s first
wake, feedback, visible plan and return brief. Static prompt-composition tests
establish that guidance is delivered; they do not establish this experience.

Use a fresh project in a CLI or TUI with no graphical surface. Record the loaded
bundle revision and instruction hashes, role settings (configured and observed),
available public capabilities and supported manager/lane tools. Do not install
missing capabilities silently or turn a missing execution dependency into a
generic helper lane. Use a disposable workspace and existing execution limits.
The evaluator supplies the prompts below, not procedural hints or record IDs.

## Scenario: Compositor

Start with: **“I want to make Compositor, a replacement for a retiring desktop
publishing app. Help me figure out a useful first version and build it.”**

The evaluator keeps these answers private until the agent asks a relevant
question: the first user creates short community newsletters; creating new
publications is the priority, and migration of old publication files can wait;
the person wants to see editing approaches before choosing one. Do not demand
those exact questions or all answers in one turn. The agent should investigate
existing project material, identify consequential uncertainty and propose a
useful next step without inventing the chosen scope.

When shown alternatives, respond with a tradeoff rather than “approved”:
**“I like being able to move things directly, but I need text to stay readable
when the layout changes. Can we combine those?”** The agent should develop or
compare that possibility, retain the feedback and revise the Direction draft.
The evaluator then makes the actual decision against the displayed proposal,
using the governing project's ratification path. Authorization covers the
agreed bounded local build and verification; no publication is implied.

Ask **“What is happening, and what can I try?”** during execution. After seeing
the result, say **“When I make a heading longer, the following text overlaps.
I also think new users need a starting layout rather than a blank page.”**
The agent must distinguish a reproducible defect from a possible direction
change, establish what revision was seen, and route each appropriately. Reply
to consequential design questions normally. Do not rescue the agent by naming
actions, lifecycle states or storage paths.

## Variants and evidence

The separate [acceptance-coverage case](acceptance-coverage.md) exercises the
verification decision with a real, deliberately incomplete worker artifact and
passing declared commands. It can be run without the full conversation journey.
The [verification-recovery case](verification-recovery.md) checks readiness before
admission and preserves completed work when manager check setup fails, including
an explicitly unsupported recovery state. Its behavioral checkpoints are unrun.
The [acceptance-translation case](acceptance-translation.md) checks that an
observed counterexample is preserved without prescribing an unsupported result
for its replacement. Its planning and reporting checkpoints are also unrun.
The [finite-recovery case](finite-recovery.md) distinguishes a refused acceptance
action from justified retained-lane recovery and checks that reconciliation
prevents redundant future work. Its behavioral checkpoints are **not run**.
The [producer-review case](producer-review.md) checks concise outcome reviews,
agent-owned recovery, feedback disposition and consequential product decisions.
It is a separate manual trial and **not run**.
The [retained-continuation case](retained-continuation.md) checks full source
retrieval and latest-candidate reconciliation before new work, including supported
independent verification of unchanged stuck work. It is **not run**.
The [engineering re-plan cases](engineering-replan.md) distinguish routine
dependency repair from product decisions and attempts to reset exhausted scope.
They are **not run**.
The [source-delivery case](source-delivery.md) checks mandatory input access,
exact evidence attachments when supported, and complete brief text on older
runtimes. It excludes assigned new outputs from input preflight and is **not run**.
The [foreground-return case](foreground-return.md) checks that a dedicated manager
can continue while the supervising conversation remains available for feedback,
with an honest fallback when no wake contract exists. It is **not run**.
The [product-scope case](product-scope.md) checks ordinary product-name
continuation through public project records while unrelated chat stays ordinary.
It is **not run**.

Run the normal journey and the failure variants separately so induced faults
do not masquerade as model failures. Retain transcripts, public command receipts,
document revisions/decisions, plan and lane records, independent checks and the
actual result. Do not count an evaluator-written summary as source evidence.

| Variant | Observation required |
| --- | --- |
| Text-only normal journey | Original intent retained; material alternatives discussed; feedback changes a draft; an actual decision precedes dependent implementation; result feedback returns to the appropriate activity. |
| Exploration capability unavailable | Agent reports it and provides readable alternatives through a supported path; it never claims the absent capability ran. Execution prerequisites still apply. |
| Existing direction settles the choice | Agent explains why another exploration would add no information and continues authorized work; it does not invoke an alternatives tool to complete a ceremony. |
| Answer to one policy question | Retain the exact original words alongside the interpretation. The answer settles only its stated policy; surrounding agent-developed wording remains provisional unless separately supported by the person's decision. No extra approval is requested for already-authorized work. |
| Interrupted observation | Inject a read failure and then a known disconnection during an existing run. Last-known state remains dated; reads back off and stop; no new start/steer/reconnect is issued to poll. Recovery reads the same run without replay. |
| Uncertain submission receipt | Suppress an acknowledgement after an admitted command. Agent resolves the existing command/run or states uncertainty; no duplicate manager, instruction or lane is created. |
| Return and revision change | Resume the supported native history after a document has changed. Agent reads current state, preserves pending draft and source identity, and does not apply feedback silently to a different revision. |
| Model effort unspecified | Agent distinguishes default/unset, inherited configuration and unknown effective effort; it does not infer worker settings from the main conversation or silently choose a provider. |

Judge the journey against these outcomes, with links to the exact evidence:

- The person could stay in ordinary conversation. Count outside protocol
  corrections, supplied IDs and manual lifecycle repairs; target **zero**.
- Decisions and alternatives retain provenance; no invented ratification,
  unnecessary permission gate, forced stage sequence or duplicate work.
- The plan is readable, real lanes have independent identity, worker claims
  remain separate from manager checks, and a completed increment is not called
  a complete product. Existing method conformance checks still apply.
- The return reading answers what changed, what needs a decision, what comes
  next and what can be tried with the evidence available in text.
- Feedback changes the next action and linked records, rather than merely
  producing a friendly acknowledgment or another unrelated project.

Record **pass**, **fail**, or **not run**, with the narrow proof boundary for
each. This scenario is unrun until a retained real transcript demonstrates it.
Distinguish generated updates from delivered updates: delayed host rendering or
repeated imported timestamps cannot establish that the agent stayed silent.
