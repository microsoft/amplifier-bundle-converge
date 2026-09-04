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

`recipes/seed-reconcile.yaml` carries `schema_version: 2` and a `dependencies:`
block, so its two `agent:` references resolve from the declared closure and
**not** from the calling session's agent map. Measured on this tree,
2026-09-04:

```
$ recipe-runner validate recipes/seed-reconcile.yaml
status: ok
schema_version: 2

$ recipe-runner plan recipes/seed-reconcile.yaml
dependencies (1):
  - git+https://github.com/microsoft/amplifier-bundle-converge@main [bundle]
      -> 4507e462d1e801a2b0080c58417ec9647b313880
agents (12): … anchors:explorer … converge:reconciler …   (both from that one entry)
steps: load-contracts, derive-rows, run-conformance, file-drift
```

Four facts about it that are **not** what you would assume:

1. **One dependency, not two, and that is deliberate.** Declaring the lean base
   alongside this bundle is a preflight *error*, because this bundle already
   composes the lean base. Reproduced on a scratch copy, 2026-09-04:

   ```
   error: Agent name 'context-intelligence:session-navigator' is supplied by
   more than one dependency: …bundles/anchors, …amplifier-bundle-converge@main.
   remedy: … agent name collisions are never resolved by precedence.
   ```

2. **The self-reference is required, not redundant.** The runner never infers a
   dependency from an agent name's namespace prefix.
3. **`@main`, not a SHA, on purpose.** A ref is fetched with `git clone
   --branch`, which takes a branch or a tag but not a commit SHA. Reproduced on
   a scratch copy pinned to the very revision `plan` had just resolved:

   ```
   warning: Could not find remote branch 4507e462… to clone.
   fatal: Remote branch 4507e462… not found in upstream origin
   ```

   This repository publishes no tags, so `@main` is the most precise pin that
   resolves today, and `plan` still pins the run itself to an immutable
   revision. Re-pin the moment a tag exists.
4. **The Amplifier recipes tool runs it `runner-isolated`,** measured here — not
   the in-session `v2-closed-world-legacy-engine` mode named in older notes.
   Either way the closed world is the point: the helpers come from the manifest.

Still stated in the old terms, and therefore wrong until their owner fixes
them: `README.md`'s Host requirement sentence and its "`seed-reconcile` recipe
runnable — only if the host is on the `anchors` base" table row. This lane may
not edit `README.md`.

## Work tracking

- Work-tracker project: `converge`.
- Every work item names the contract it serves.

## Handoffs to other lanes

- **Composition lane (owns `README.md`)** — README needs one line under setup:
  "Enable the locked-contract guard once per clone: `git config core.hooksPath
  .githooks`." This lane may not edit `README.md`.
