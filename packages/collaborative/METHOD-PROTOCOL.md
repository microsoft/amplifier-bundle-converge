# Collaborative Method protocol mapping

This is the operating profile's implementation map, not a new contract or a
ratification. It serves the steward's request to make the canonical Converge
method operative through the installed collaborative tools. Method remains
owned by its document repository; this package supplies executable instructions,
not runtime code. The existing root bundle, manager mode, guards, contract files
and installation path are unchanged.

The audit reads Method at `4a33a39ca465f867bfdf2d9bd80680c36273a097`:

- [operation.v1](https://github.com/bkrabach/amplifier-converge-method/blob/4a33a39ca465f867bfdf2d9bd80680c36273a097/contracts/operation.v1.md), ratified 2026-09-07;
- [lanes.v1](https://github.com/bkrabach/amplifier-converge-method/blob/4a33a39ca465f867bfdf2d9bd80680c36273a097/contracts/lanes.v1.md), ratified 2026-09-07;
- [wake.v1](https://github.com/bkrabach/amplifier-converge-method/blob/4a33a39ca465f867bfdf2d9bd80680c36273a097/contracts/wake.v1.md), including the ratified 2026-09-08 transport clarification;
- [MANAGER-MODE](https://github.com/bkrabach/amplifier-converge-method/blob/4a33a39ca465f867bfdf2d9bd80680c36273a097/docs/MANAGER-MODE.md), a **draft worked reading**, not law;
- the named [lane brief](https://github.com/bkrabach/amplifier-converge-method/blob/4a33a39ca465f867bfdf2d9bd80680c36273a097/docs/templates/LANE-BRIEF.md.template), plus the documents, settling and ledger seams that those contracts name.

## Independent gap audit

The previous `manager.md` was six lines, with SHA-256
`03d1421e550a24ed75597f352604f120e4bf0a65f069d7e55bdedd19558266a1`.
It required current Direction reads, preserved provenance and native history,
and distinguished a file observation from correctness. Those were useful
boundaries. However, “delegate when useful” supplied no lane isolation rule,
and `record_evidence` supplied no manager check or guarded closure. There was no
item source, durable wave, fixed failure bound, terminal return protocol or
steward-call filter. Installing those bytes alone could not establish Method
conformance even when a manager performed useful product work.

The table accounts for every live promise in the operation and lanes contracts.
Operation numbers 4–9 are retired and must not be counted twice. “Instruction”
names the manager section; the last column is evidence still required from an
actual execution, not a claim earned by this prose.

| Canonical promise | Previous gap | Instruction | Required execution evidence |
|---|---|---|---|
| operation.v1:1 | Direction context without item derivation | 1 | Stored item cites a promise/gap or the steward's exact words and source. |
| operation.v1:2 | No durable plan before delegation | 1–2 | Plan receipt predates launch; item, capacity and runtime lane identities remain readable. |
| operation.v1:3 | No parked/continued call record | 1, 6 | Open call parks dependent items while independent authorized work continues. |
| operation.v1:10 | Artifact reports without required rerun | 4 | Manager commands rerun after each landed change; new breaks and newly kept promises are both reconciled. |
| operation.v1:11 | Ownership seams implicit | 4 | Documents, settling and ledger use their owning interfaces; no invented ratification or verdict. |
| lanes.v1:1 | Generic helper could be called a lane | 2 | Distinct branch, working copy and native session observed for every product lane. |
| lanes.v1:2 | Worker report could substitute for proof | 4 | Manager-owned check executes against the returned revision; worker cannot write that check or close. |
| lanes.v1:3 | No finite domain outcome vocabulary | 5 | Every returned lane has exactly one of the three outcomes, distinct from lifecycle labels. |
| lanes.v1:4 | No fixed per-target attempt budget | 3 | Numeric bound stored before launch; attempts name target/result; bound terminates and routes the cause. |
| lanes.v1:5 | General uncertainty report only | 5 | Return names what landed, what did not, evidence for each and a next action/residual owner. |
| lanes.v1:6 | Unbounded “ask when unclear” | 6 | Decision calls are ratify, allow, check or priority/stop; other setup defects are handled or filed. |

Wake is part of a usable lane protocol even though the original six lines did
not mention a brief. The template's nine parts are preserved in reading order.

| Canonical promise | Instruction | Required execution evidence |
|---|---|---|
| wake.v1:1 | 2 | Worker gets its self-contained brief and own working copy, without inherited manager conversation. |
| wake.v1:2 | 1–2 | Every acceptance item names a file or printed command and a falsifier; evidence is retained for a reader. |
| wake.v1:3 | 2 | Exact ownership is enforced; out-of-scope criteria return as routed residuals. |
| wake.v1:4 | 5 | SUCCESS maps to worker done-with-proof; BLOCKED preserves stuck or steward-wait; manager still verifies. |
| wake.v1:5 | 3 | Positive numeric failure limit appears in the brief before the worker starts. |
| wake.v1:6 | 2 | Unique absolute marker is outside the working copy and permitted by the worker's actual access policy. |
| wake.v1:7 | 1–2 | Wave orchestration remains with the operation seam; the brief does not invent another lifecycle. |

## Operating choices, kept distinct from law

The default of three failed attempts is this profile's recorded operating
choice; the contract requires a number fixed in advance, not that particular
number. Capacity is also a recorded choice within the authorized cap. A healthy
wait is not a failed attempt: it needs observed health, a checkpoint, deadline
and next route. A changed result advances reconciliation. The runtime also imposes a separate
conservative cap on total admitted lane launches, using the same item limit.
That cap is not canonical failed-attempt accounting. `record_attempt` records
per-target observations and whether they produced a new fact; healthy polling
does not call it. A return names which bound caused the stop. No retrospective
failure reconstruction or recursively spawned auditor is required to return an
honest result with missing evidence explicitly named.

The worked reading asks for manager checks in the lane before integration and
again on the target afterwards. The profile applies that sequence within the
steward's actual authority. It does not grant permission to merge or publish.
A restricted review-only assignment may leave a ready result awaiting its
already identified integration boundary; that is not a claim that it landed.

The three lane outcomes and the five ledger verdicts are different domains.
`active`, `idle`, `reported` and `stopped` are runtime observations. `SUCCESS`
and `BLOCKED` are file-marker transport exits. None creates a fourth lane ending.
A worker's done-with-proof report remains a claim until the manager reruns the
check and the guarded closure succeeds.

A request for an actual progress reading is not a fifth decision call. The
supervisor shows existing records and their evidence without inventing a choice
or demanding unsolicited attention. If a substantive decision is needed it is
one of ratify, allow, check or priority/stop. Unselected alternatives and draft
Direction remain unsettled; direct steward instructions retain their own source
without silently ratifying another document.

## Implementation seams and authority

The supervisor calls installed `converge_operations`; the manager calls its
project-bound `converge_project` wrapper. Both use public records, stable exact
retry receipts and current revisions. The manager cannot change its own
lifecycle. Product implementation uses the lane workflow, while bounded
in-session helpers are limited to investigation, protocol, queue reading or
watching; they are not canonical lanes.

For convergence, the supervisor uses `require_wave:true` on start, steer or
reconnect. A durable plan, lane execution, worker return, manager checks,
closure and the derived final wave picture make completion inspectable. A finite informational
turn need not invent a wave. Feedback acknowledgment, acceptance reassessment and
a plan-only discussion use `require_wave:false`; implementation uses
`require_wave:true`. The action name `steer` does not decide the mode. An
incorrectly queued mode can be replaced only through supported guarded
cancellation while still unstarted, with both receipts retained; never by editing
a run or replaying started work. If the provider ends early, continuation reads the
same stored wave under a bounded runtime policy; it does not replay an uncertain
launch. Missing actions are visible setup defects, never permission for direct
database writes or a generic delegate fallback.

Runtime owns lane isolation and process/session identity; Queue owns work and
custody; the operating workflow coordinates them; Operations exposes the state.
The instruction package owns none of those implementations. The current tool
schema is the executable authority for argument names and refusals. The protocol table below is checked against the coordinated implementation;
installed readiness still must expose these actions before activation.

| Action on the Operations capability | Arguments beyond project_id | Authority/effect |
|---|---|---|
| initialize_workspace | optional ignore_patterns:[string] | Manager-only safe repository/baseline preparation within existing authority. |
| file_item | title, source:{kind,reference,text}, acceptance, attempt_limit, checks; optional gap, discovered_from | Queue preserves immutable source and bounded acceptance/check requirements. |
| plan_wave | title, item_ids, width | Plan and lane records precede execution. |
| run_lane | lane_id, agent_name, instruction, brief:{read_first,owned_paths,acceptance,boundaries,sources?,read_only?} | Resolves required revision-bound sources before admission; persists the nine-part brief before isolated native launch; exact retry observes the original attempt. |
| return_lane | lane_id, outcome, brief:{landed,not_landed,evidence}; cause/routed_to or steward_call when applicable | Worker claim; never independent verification or closure. |
| record_attempt | lane_id, target, observation, new_fact | Per-target no-new-fact accounting; distinct from total launch cap and healthy waiting. |
| verify_lane | lane_id | Manager executes declared checks, recording actual result and revision. |
| integrate_lane | lane_id, expected_target_head | Checks and integrates only the expected target under existing authorization. |
| close_item | item_id, lane_id, check_id, resolution:{what_is_live,what_changed,caveat,check} | Guard requires actual successful manager check after integration. |
| answer_call | lane_id, answer | Conveys the steward's actual answer; no invented approval. |
| finish_wave | wave_id, brief:{landed,not_landed,evidence?} | Optional final brief; refuses until every lane is closed or explicitly stuck/waiting. |
| read | project_id | Returns workflow items, waves, lanes, attempts and checks; wave state is derived. |

The outcome wire values are `done-with-proof`, `stuck-with-cause` and
`waiting-on-steward`; these encode the three canonical prose outcomes. The call
wire values are `ratify`, `allow_irreversible`, `human_check` and
`priority_or_stop`. `attempt_limit` accepts 1–20; `checks` is a list of argv
arrays. `source.kind` is `promise` or `steward`; item `acceptance` is text.
The lane brief's `read_first` and `owned_paths` are lists of strings; its
`acceptance` is a list of `{evidence,falsifier}` objects and `boundaries` is
text. The runtime persists the assembled brief before launch and supplies an
absolute marker path outside the working copy; the controlled return tool
writes that marker. The marker carries SUCCESS/BLOCKED and the exact domain
outcome. Target no-new-fact counts are based on worker-reported observations;
the runtime enforces the limit, not the semantic truth of a reported new fact.
No public action accepts a
caller-supplied verification boolean. The optional `finish_wave` records a guarded final brief;
completion is also derived from records, and the final brief cites their IDs.
Neither sets a model-supplied project-complete flag.

`brief.sources` is a list of `{capability:"direction",document_id,revision}`.
For required Direction material the revision must be explicit and current;
resolution uses the project-scoped public Service getter. The captured body,
title, state, project, revision and hash become an immutable attachment in the
attempt, lane and external brief. The worker's scoped read exposes that snapshot,
not general document browsing. Missing, stale, cross-project and bare unresolved
document references fail before custody, worktree preparation or an admitted
attempt. An exact retry keeps the original captured bytes, including their
draft status; later source changes do not rewrite old briefs.

`brief.read_only:true` accepts `owned_paths:[]` and grants no product-write
ownership. Manager verification, integration and closure must reject a changed
review worktree or a HEAD different from its admitted base. Generated ignored
check outputs do not create product-edit authority. A worker's report of being
read-only is not sufficient integrity evidence.

The brief also carries exact examples for the only worker actions: scoped read,
return with all three outcome shapes, and target-attempt reporting. The worker
returns a named setup defect if needed context is absent. Filesystem access does
not grant permission to inspect host caches, installed source, private stores or
manager history. This is an application reading policy, not OS sandboxing.

This correction follows an observed trial failure: an independent reviewer was
given a draft document ID without its body; its scoped read returned only its
item and lane, and Direction access was refused. It then used host filesystem
tools to find the private store and implementation to reconstruct missing
source and return schemas. Passing product checks did not make that lane comply
with wake.v1:1. The original brief, attempts and evidence remain preserved;
source tests of this correction do not retroactively prove that trial compliant.

The original operating root's `.converge` layout is not silently adopted by this
collaborative profile. The selected runtime and domain libraries own their
configured state locations. Native transcripts stay in the existing native
history. A repository-less workspace first needs the runtime's explicit safe
initialization/baseline path within authorization; a second folder alone is not
a branch. Instruction text cannot manufacture isolation or custody.

## Instruction transition and proof boundary

The old and new package versions are immutable source pins. A live manager must
be observed idle, then upgraded through an explicit migration from its exact
saved instruction digest to the new digest, retaining its native session ID.
The digest covers the full runtime instruction, including project suffixes; a
hash of this resource alone is not the per-session migration key. Runtime
configuration checks remain in force. Readiness must report the actual new
instruction digest and tools. Do not delete history, manufacture a checkpoint,
allow arbitrary configuration changes or replay old input to force adoption.

Static guidance tests can catch a missing clause, inconsistent outcome or
broken resource distribution. Runtime tests can show that the particular
isolation/verification paths reject bad inputs. Neither proves that a real model
has followed this protocol. Live evidence must still include a planned isolated
lane, a worker return, manager-executed checks and a settled wave under the
preserved manager session. A successful repair under the earlier six-line
instruction proves useful execution and continuity, not this protocol's adoption.

## Checks for this change

- Version 0.2.2 passes all 15 package guidance/resource tests against the source
  and an isolated installation of its source-built wheel. With the 187 required
  manager-guidance/turnkey regressions, the combined source run reports 202
  passed. The wheel contains only the initializer, two reviewed text resources
  and distribution metadata. Root bundle/mode and locked contracts remain
  unchanged. These checks establish shipped guidance, not live recovery from
  the observed reading-policy failure.
- The initial package's 13 guidance/resource tests passed against the source and against
  its source-built wheel installed in an isolated environment. The wheel has
  only the namespace initializer, two instruction resources and distribution
  metadata; both resource hashes match the reviewed source.
- The repository-required manager-guidance and turnkey fixture regressions pass:
  187 tests. These exercise guidance/fixtures, not a live model.
- The documents kit reports 17 pass, 1 fail, 9 skip. Its existing rule 12b
  failure concerns `docs/workspace-template/MANAGER-BRIEF.md.template` and the
  kit's destination accounting; those files are outside this change. Rule 9a
  cannot be trusted as current: refreshing its export failed because
  `amplifier-work-tracker` is unavailable.
- Ledger verification is not green. It cannot read the live queue, its fallback
  export is stale, existing executable references fail, and it finally stops on
  an unavailable historical `/home/bkrabach/.../index.html` artifact. No ledger
  row or failing rule was weakened to hide these missing checks.
- The unchanged root bundle/manager mode and the pre-push frozen-document guard
  were checked. No live session or product files were changed by this package
  work. A migrated live manager obeying the full protocol remains unproven here.


## Portable behavior composition (0.3.0)

The supervisor text is now `instructions/supervisor.md`; `behaviors/collaborative.yaml`
consumes that exact resource. The optional complete profile composes Anchors and
this behavior while preserving the Anchors root instruction. The manager resource
is unchanged. Host presentation, installation and session/canvas bindings belong
to a separate consuming integration. This split changes no Method promise and
establishes no additional runtime or product acceptance.

## Collaborative guidance delivery (0.4.0)

`instructions/collaboration.md` carries the shared conversation guidance for
first wake, feedback, a visible plan and an actionable return. Both the ordinary
`behaviors/converge.yaml` and optional `behaviors/collaborative.yaml` load that
exact context URI, once when composed together. The ordinary CLI path gains no
collaborative tool bindings. Existing mode, guard and contract bytes are unchanged.

The package's `instruction(role)` helper supplies common plus role text to a
direct consumer. It does not start a runtime or resolve arbitrary includes.
Legacy reads of `manager.md` remain compatible but omit the common guidance;
the consuming runtime must separately adopt the helper and reviewed package revision,
preserving the existing exact-hash migration and native history checks. The raw
manager file is unchanged, while the composed manager instruction gains text.

The [text-only journey](../../evaluations/collaborative/README.md) tests the
experience the execution-only trial did not establish: incomplete intent,
alternatives, negotiated revision, a bounded build and feedback returning to
direction or verification. Its fault variants check that observation cannot
create duplicate execution, and that unset effort is not misreported. It remains
unrun; source composition and wheel checks prove delivery only.
