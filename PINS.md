# Pins — hard facts for this repository

Read this before your first command. Every line is a fact you may rely on. If a
line here is wrong, sessions act on it anyway — fix it the moment it drifts.

## Where things are

| Thing | Exact location |
|---|---|
| Vision | `docs/VISION.md` |
| The full protocol (rules behind the vision) | `docs/PROTOCOL.md` |
| Contracts | `contracts/*.v1.md` — fourteen today (`ls contracts/`) |
| Contracts README | `docs/CONTRACTS-README.md` |
| Standing rules for sessions | `AGENTS.md` |
| Participant kit for other repositories | `docs/workspace-template/` |
| Ledger format | `docs/LEDGER-FORMAT.md` |
| Conformance ledger | `ledger/rows.yaml` — seeded; self-check with `uv run --with pyyaml ledger/checks/verify.py` |
| Conformance kits | `conformance/<contract>/run.py` — `conformance/README.md` names each one and how to run it |
| Integration branch | `main` |

Measured on this tree, 2026-09-04:

```
$ uv run --with pyyaml ledger/checks/verify.py
ALL LEDGER SELF-CHECKS PASS                    (175 rows, 14 contracts, exit 0)
$ uv run conformance/documents/run.py .
VERDICT: PASS  (pass=18 fail=0 skip=9)
```

## Naming

- A proposal to change a contract is `<contract>.vN-candidate.md`, in the same
  folder as the contract it changes — for example
  `contracts/documents.v2-candidate.md`.
  **That example does not match what this repository actually does, and the
  disagreement is an open decision, not a typo to fix in passing.** All seven
  candidates in `contracts/` today read `<contract>.v1-candidate.md` — `vN` is
  the version being *amended*, not the version being *proposed*. Both readings
  satisfy `.githooks/pre-push`, so nothing catches the difference; settling it
  takes one sentence in `documents.v1` clause 8, which is a contract and not a
  file to edit in passing. Filed as `converge-t18`. Until it is answered, follow
  the folder (`<contract>.v1-candidate.md`), not this example.
- A locked contract carries `(FROZEN <date>)` in its first heading line; a draft
  carries `(DRAFT)`. Status appears nowhere else in the file.
- Every contract in `contracts/` is `(DRAFT)` today. None is locked.

## The pre-push guard

- The hook is `.githooks/pre-push`. Enable it once per clone:

  ```
  git config core.hooksPath .githooks
  ```

- It refuses any push whose diff touches a file whose first heading contains
  `(FROZEN`, unless the same push also contains a sibling `*-candidate.md` (the
  legacy `CANDIDATE-*.md` name is also accepted).
- Run it by hand against a base: `./.githooks/pre-push origin/main`.
- The escape hatch is not a bypass. Adding a candidate lets the push through so
  the proposal can be written and read. Only the intent steward's word changes
  the original.

## The in-session guard (`hooks-candidate-guard`)

A second, different guard runs inside Amplifier sessions and denies write-shaped
tool calls. Its shipped configuration is in `behaviors/converge.yaml`:

- Guards `contracts/*.md`, `contracts/**/*.md`, `docs/VISION.md`, `VISION.md`.
- Only guards a file whose **on-disk content** already carries the frozen
  marker, so a `(DRAFT)` contract is writable during authoring.
- Also scans `bash` for write-laundering (`>`, `tee`, `sed -i`, `cp`, `mv`,
  `truncate`, `dd of=`).
- `fail_closed_on_error: true` — an error in the guard denies the write.

Two facts about it that are **not** what you would assume:

1. Its `frozen_marker_regex` matches `**Status:** RATIFIED|FROZEN` or
   `status: FROZEN` — **not** the `(FROZEN <date>)` H1 parenthetical that
   `contracts/documents.v1.md` clause 6 mandates and that `.githooks/pre-push`
   checks. The two guards read different markers.
2. Its `always_allow_globs` / `candidate_glob` are `**/CANDIDATE-*.md` only —
   it does **not** yet recognise `<contract>.vN-candidate.md`, though
   `contracts/composition.v1.md` clause 7 says it must.

Both are recorded as work, not worked around. Do not "fix" a document to match
the guard; the contract is the law and the guard is the thing that must move.

## Composition

- Converge's lean base is the *anchors* bundle:
  `git+https://github.com/microsoft/amplifier-foundation@main#subdirectory=bundles/anchors`
- **Never reintroduce a session-wide `spawn:` block.** Measured in isolation on
  2026-09-02: a behavior's top-level `spawn.exclude_tools` strips the listed
  tools from every spawned sub-agent in *every* session, not just Converge's —
  `foundation:explorer` in a plain foundation session lost `bash`, `delegate`,
  and `load_skill`. Confirmed with a removal control. Per-agent spawn policy is
  an upstream request; until it lands, agent tool limits are behavioural and the
  candidate guard is the structural enforcement.

## The recipe declares its own helpers

`recipes/seed-reconcile.yaml` (v1.6.0) carries `schema_version: 2` and a
`dependencies:` block, so its two `agent:` references resolve from the declared
closure and **not** from the calling session's agent map. Measured 2026-09-05:

```
$ recipe-runner validate recipes/seed-reconcile.yaml
status: ok   schema_version: 2

$ recipe-runner plan recipes/seed-reconcile.yaml
dependencies (2):
  - git+https://github.com/microsoft/amplifier-foundation@main#subdirectory=bundles/anchors/bundle.md [bundle]
      -> 7ca50a8adb7e1d7b60318b97259e860625a6aded      supplies anchors:explorer
  - git+https://github.com/microsoft/amplifier-bundle-converge@v0.1.0#subdirectory=behaviors/converge.yaml [behavior]
      -> 4507e462d1e801a2b0080c58417ec9647b313880      supplies converge:reconciler
agents (12) · no collision
steps: preflight-tracker, load-contracts, derive-rows, run-conformance, file-drift
```

(The anchors SHA moves because that entry is still pinned to a branch — fact 4
below. The converge behavior partial is pinned to a tag and does not move.)

Six facts about it that are **not** what you would assume:

1. **The converge entry is the BEHAVIOR PARTIAL at a TAG, not the root bundle at
   `@main`.** The root bundle composes the lean base, so declaring the lean base
   beside it is a preflight collision (`context-intelligence:session-navigator`
   supplied twice — measured 2026-09-04). The partial does not compose the lean
   base, so each helper has exactly one supplier.
2. **The self-reference is required, not redundant.** The runner never infers a
   dependency from an agent name's namespace prefix.
3. **A SHA cannot be pinned.** A ref is fetched with `git clone --branch`, which
   takes a branch or a tag but not a commit SHA (`fatal: Remote branch <sha> not
   found`). Tags on this repo: `v0.1.0` = `4507e46` (cut 2026-09-04). When the
   agents change, cut a new tag and bump the pin.
4. **The lean base is still pinned to a branch (`@main`).** No foundation tag
   ships `bundles/anchors` (`v2.1.2` is the newest and predates it). Re-pin at the
   first tag that does; composition.v1's "does NOT freeze" list carries the trigger.
5. **Two labels, both correct.** The Amplifier `recipes` tool reports
   `execution_mode: runner-isolated` on `validate` and
   `execution_mode: v2-closed-world-legacy-engine` on `execute` (measured on a
   same-shape v2 probe run in a non-anchors session). Either way the helpers come
   from the manifest, never from the caller.
6. **The first step is not an agent, and it can stop the whole run.**
   `preflight-tracker` is a `type: bash` step (v1.6.0). It refuses the run —
   before any agent is spawned, so at no token cost — when `tracker_project` is
   empty, names a project that does not exist, or names a project the target
   ledger's own `work:` refs disagree with. **It never redirects.** Measured
   2026-09-04 (converge-myu8): told a project that did not exist, an earlier
   version reached step 4 with items to file and filed them into the live
   `converge` project instead.

**`README.md` now agrees with all five.** This section carried a closing
paragraph saying README's Host requirement sentence and its "`seed-reconcile`
recipe runnable" table row were "still stated in the old terms, and therefore
wrong until their owner fixes them". They were restated on 2026-09-04 under
converge-yj3: the Host requirement now says the recipe needs no particular host,
not even the lean `anchors` base, and the table row no longer makes the `--app`
path conditional on one. `uv run conformance/composition/run.py .` reports rule 4
PASS on the new sentence. The paragraph was removed rather than corrected in
place, because a fact that has stopped being a fact is not one (converge-x40).

## Work tracking

- Work-tracker project: `converge`.
- Every work item names the contract it serves.
- **The ledger cites ONE project.** Every `work:` ref in `ledger/rows.yaml` is a
  `converge-*` id, `scripts/export-work-items.py` exports `--project converge`,
  and `ledger/checks/verify.py` resolves refs against the LIVE queue of the
  project each ref itself names — through `amplifier-work-tracker`, never
  through that export (converge-j0u5). Anything that
  runs `seed-reconcile` against this repo — including an e2e harness — passes
  `tracker_project: converge`. A different project is refused at preflight, not
  silently redirected; and an isolated queue would require the export script, the
  app config and the ledger's existing refs to move together.

## Standing gaps

Facts about this repository that are true until someone closes them. They are
not addressed to any one lane — a line here that names "this lane" has outlived
whichever lane it was written for, and is a defect in this file (converge-x40).

- **`README.md` does not tell a reader to enable the pre-push guard.** The line
  it needs, under setup: "Enable the locked-contract guard once per clone:
  `git config core.hooksPath .githooks`." Measured 2026-09-04:
  `grep -n hooksPath README.md` returns nothing, while
  `docs/CONTRACTS-README.md:156` carries it. Until then a fresh clone pushes
  with no guard and the first person to learn that is whoever edits a locked
  contract.
