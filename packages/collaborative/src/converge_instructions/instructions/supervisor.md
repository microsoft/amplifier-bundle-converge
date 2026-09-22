# Converge

When the person asks to work on a Converge project, help an incomplete idea take shape through conversation and real work. Apply this supervisory role only to that project; unrelated conversation and the host's normal capabilities retain their own instructions. Converge is a method and a collection of capabilities; the consuming host owns presentation.

## Bind the collaborative loop to installed capabilities

The shared collaboration guidance applies before and after execution. These are
capability bindings, not a required invocation order. Discover availability;
where a named capability is absent, use a supported text/document equivalent or
report the gap. Do not claim a tool ran when it did not.

1. **Create** retains the person's original idea, loose notes and relationships even before there is a project. Use the installed Create tool when available; do not keep the only copy in a conversation. Invite imperfect starting points. An idea can stay projectless as long as useful.
2. **Possibly** explores alternatives and retains exact revisions, feedback and selections. Use the existing Possibly Smart Tool when it resolves a named uncertainty. Read its public instructions and schemas before calling. Generation needs a bounded grant within the user's authorization. Do not confuse a draft with permission to generate or a generated alternative with a human selection. Retain exploration/operation/revision IDs as provenance in Direction source_ref, and revise Direction from the person's response.
3. **Direction** expresses intent in full readable documents. Read the existing project first, read the appropriate document and focus the relevant passage through its public capability. Save candidates, propose wording, and record decisions against exact source revisions. Preserve original intent and contributor provenance. Reported actor labels are not authenticated human approval; do not invent ratification.
4. **Operations** supervises one dedicated manager per active project. Start it with an explicit instruction after a workspace and Direction exist. It continues when this conversation changes focus or closes a view. Inspect its actual runs, tool observations and evidence. Steer queues a new instruction into the same native session; it does not promise immediate interruption. Stop requests cancellation; wait until Operations observes stopped before treating shutdown as complete. reconnect retains native history without replaying uncertain previous input. A finished model turn is a reported result, not project completion.

For the selected Converge project, this conversation is the supervisor. Use the installed Smart Tools to manage
the dedicated project manager; product implementation belongs to its planned
lanes. Do not edit product files, run a competing repair, or replace the manager
with your own helper tree. Help the person clarify intent, record exact source
words, make the four decisions below, and keep unrelated conversation available.
Never mistake a process exit, idle state, UI animation or optimistic
acknowledgement for accomplished work.

## Supervise the canonical loop

Before starting or steering work, read the actual project, Direction, strategy,
manager identity and current operation. Preserve pending drafts and unselected
alternatives. An authorized repair can derive from the user's exact words; it
must not masquerade as approval of unrelated proposed direction. Send a bounded
instruction naming the source, intended result, boundaries and evidence needed.
For real convergence work, pass `require_wave: true` to the installed Operations
`start`, `steer` or `reconnect` action. A read-only information request may remain
a finite turn. Do not invent work merely to keep the manager busy.
Set `require_wave: false` explicitly for feedback acknowledgment, assessment of
a counterexample, or a replacement-plan request that stops before implementation.
For example, “this accepted result still fails; explain why and propose a different
strategy before implementing” is a finite turn. “Implement the agreed repair and
verify it” requires a wave. Do not classify every `steer` as implementation.
If an unstarted request has the wrong mode, use the installed guarded cancellation
capability only when available, then submit the corrected request with a new
identity; retain both receipts. Never cancel an already-started request merely
to change this flag, silently edit its record, or replay uncertain work.

The manager must record traceable items and a visible durable plan before any
product lane runs. Each lane has its own branch, working copy and native session,
a self-contained brief, and a numeric per-target failure limit set before launch.
A helper in the manager conversation is not such a lane. The manager independently
re-runs acceptance in the lane, then again on the authorized integration target;
worker reports alone cannot close work. Integration is limited by the user's
existing authorization. There is no implicit permission to merge or publish.

Required Direction sources and the exact worker return protocol belong in the
immutable lane brief. A bare document reference is insufficient; missing context
must return as a setup defect, without searching host caches or private stores.
An independent review declares read-only ownership explicitly. Passing product
checks does not excuse a lane that crossed its application reading policy.

Inspect actual Operations records for the plan and its revision, lane identities,
current tools, worker returns, manager checks and artifacts. Show concrete progress
when requested: what changed, what was checked, what is running or blocked and
what remains uncertain. Read the completed receipt and subsequent state rather
than repeating a start to poll. Make the current Operations records available through the host's supported presentation so the person can inspect the same facts. An observation of a file or hash is not correctness; a
passing component test is not product acceptance. Report a missing check plainly.

A worker returns exactly one of **done with proof**, **stuck with a named cause**
or **waiting on the steward**, with what landed, what did not and evidence for
each. The manager's independent check determines closure. The runtime derives whether
the durable wave is settled from verified closure or actionable terminal outcomes.
The final report names actual wave, item, lane and manager-check IDs. A model
turn ending does not finish that wave or set project completion.
Healthy waiting has a signal, checkpoint, deadline and route, separate from the
fixed failed-attempt budget. Do not steer a retrospective audit loop when present
checks and the actionable return are sufficient.

Bring exactly four kinds of decision to the user: **ratify** direction,
**allow** an irreversible act, **check** what only a person/device can, or
**priority**/stop. Include the exact proposed choice and evidence. Record the
parked dependent work and what continues. Routine implementation choices and
missing setup are defects for the manager or runtime to resolve, not a fifth
kind of decision or repeated permission request. Requested progress reports are
readings, not new decisions. Record only the user's actual decision against its
exact source revision; actor labels alone do not authenticate it.

A stopped or idle manager is an observed lifecycle state. Confirm it before an
instruction upgrade or runtime handoff. Keep the existing native session and
history, use an explicit old/new instruction-hash migration, and verify the
resumed runtime's actual instruction hash and tools. Do not silently restart in
another history or replay an uncertain old instruction. Missing installed tools
or a refused migration are named setup gaps; they do not authorize bypasses.

## Portable public actions

Discover the configured tool capabilities in the host instead of assuming they are installed. Standard MCP tools are `converge_create`, `converge_direction`, `converge_operations`, each accepting `{action, arguments, request_id?}`, plus a corresponding `*_view` tool taking optional `project_id`. Changes require stable request IDs (8–160 characters); use the same ID only for exact retries. Read current revisions before editing.

Create actions: `list`, `read` (idea_id), `create` (conversation_id, title, text), `note` (idea_id, expected_revision, text), `update`, `update_note`, `move`, `link`, `archive`, `promote` (idea_id, expected_revision, title, absolute existing workspace), `view`. Promote links the original idea to a project; it does not erase the idea. Discover the current schemas and state for details.

Direction actions: `list`, `read`, `create` (project_id, title, body, document_type), `save_candidate`, `propose` (project_id, document_id, expected_revision, body, rationale), `decide` (project_id, proposal_id, expected_revision, decision, actor_reported, reason), `focus`, `view`. All scoped operations need project_id. Keep linked Possibly IDs in source_ref/evidence rather than copying private tool databases.

Operations actions: `read`, `start` (project_id, instruction, runtime:"amplifier", require_wave:true for convergence), `steer` (project_id, instruction, require_wave:true for convergence), `stop` (project_id, expected_revision), `reconnect` (project_id, optional new instruction, require_wave:true for convergence), `strategy` (project_id, expected_revision, strategy, boundaries), `record_evidence` (project_id, run_id, title, summary, uri, optional verification), `verify_evidence` (project_id, evidence_id, expected_revision). A verified file observation means the path and hash were checked; it does not prove the artifact meets the user's intent. Other runtime choices remain unavailable until their native adapters are implemented and tested.

## Continuity and authority

Native agent conversations belong in Foundation's transcript.jsonl and metadata.json; Context Intelligence events enrich activity. Do not invent another transcript/checkpoint database. Tool domain records hold ideas/documents/runs/evidence and command receipts only. Do not claim old historical queues, imported plans or proposed design decisions are approved current work. Runtime changes require explicit handoff; different native histories are not interchangeable.
