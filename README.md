# Converge

**Vision-first, contract-driven development.**

The owner and the orchestrator negotiate at the **contract** level. Work is
**derived from the gap** between repo reality and the ratified contracts —
never invented. A standing conformance ledger (the **ratchet**) prevents
silent backsliding: drift in either direction files a row. The owner's
attention is spent only at the contract layer; everything below it that
reaches the owner is a protocol defect.

## Install

**THE install path — the behavior (`--app`):**

```
amplifier bundle add git+https://github.com/microsoft/amplifier-bundle-converge@main#subdirectory=behaviors/converge.yaml --app
```

This composes converge's **capability layer** onto whatever bundle is already
active: the four agents (`protocol-authority`, `reconciler`, `negotiator`,
`amendment-drafter`), the five procedure skills, the `hooks-candidate-guard`
hook (structural PROTOCOL.md §5 enforcement, on by default), the thin awareness
context, and — via a behavior-includes-behavior include — the `amplifier-work-tracker`
behavior that gives `reconciler` its `work_*` filing tools. Use this to add
converge to an existing workspace/session (which must already provide foundation).

**Full-workspace path — converge as the primary bundle:**

```
amplifier bundle add git+https://github.com/microsoft/amplifier-bundle-converge@main
amplifier bundle use converge
```

This composes the **root** `bundle.md`, which pulls in `amplifier-foundation`
**and** `amplifier-work-tracker` **and** the same behavior. Use this to run the
phase-loop recipes (`seed-reconcile`, `encode`, `full-wave`) end-to-end against
a target repo.

### What differs between the two paths (honestly)

| | `--app` behavior | `bundle use converge` (root) |
|---|---|---|
| 4 agents · 5 skills · guard hook · awareness | ✅ | ✅ |
| `foundation` present | assumes the active bundle already provides it (agents use `@foundation:` refs) | ✅ pulled in by `bundle.md` |
| `work-tracker` present (reconciler's `work_*` filing) | ✅ the behavior includes the work-tracker **behavior** (behavior-includes-behavior), so `reconciler` gets `work_*` filing on this path too | ✅ pulled in by `bundle.md` |
| Agents' "no delegate / no skills / no shell" rules | behavioral — agent body instructions + explicit `tools:` blocks (per-agent structural spawn policy is an upstream feature request) | behavioral (same) |

Both paths give the four agents, five skills, guard hook, awareness context, and
work-tracker filing. The root path additionally pulls `foundation` itself — so
for end-to-end recipe runs against a target repo, prefer `bundle use converge`.
For lightweight composition of the knowledge/enforcement layer onto a session
that already provides foundation, the `--app` behavior is the quick path.
Neither path imposes any session-wide `spawn:` policy: a live probe
(2026-09-02) showed a composed `spawn.exclude_tools` strips tools from **every**
spawned sub-agent in every session — unacceptable collateral for a composable
bundle, so it is deliberately absent everywhere.

## Status

**Increment 4 build (final) — the agent roster is complete.** This bundle
ships:

- `context/converge-awareness.md` — a thin pointer wired into the root session
- `agents/protocol-authority.md` — THE carrier of the ratified protocol
- `agents/reconciler.md` — the ratchet: SEED + standing RECONCILE
- `agents/negotiator.md` — Phase 1 NEGOTIATE: turns investigation evidence into
  decision-level minutes for the owner (options + recommendation + the one
  decision to make); returns needs rather than re-routing; read-only.
- `agents/amendment-drafter.md` — authors `CANDIDATE-<topic>.md` proposals
  (exact diff · real-evidence bar · "what does NOT change" · ratification ask ·
  the `target:` field the guard escape hatch consumes) and **stops**; never
  edits the frozen file, never self-ratifies, returns needs.
- `skills/` — five procedure skills (seam test, CANDIDATE amendment authoring,
  Freeze Bar checklist, ledger dispositions, lane-brief discipline)
- `modules/hooks-candidate-guard/` — the ratchet's teeth: a `tool:pre` hook,
  wired on by default via `behaviors/converge.yaml`'s `hooks:` block, that
  structurally enforces PROTOCOL.md §5 (no direct write to a FROZEN
  contract/`VISION.md`; amendments land only via a ratified
  `CANDIDATE-<topic>.md`). See that module's own README for the full contract
  and documented non-coverage.

- `recipes/` — the phase loop, shipped and live-verified:
  `@converge:recipes/seed-reconcile.yaml` (SEED + standing RECONCILE),
  `@converge:recipes/encode.yaml` (Phase 2 ENCODE, owner-gated), and
  `@converge:recipes/full-wave.yaml` (the owner-gated wave with the four §6
  attention gates). Spec of record: `docs/design/mechanism-spec.md` §4
  (`encode` §4.1, `seed-reconcile` §4.2, `full-wave` §4.3).

The orchestration mode is deferred by decision (pure delegation + recipe gates +
hook instead).

## The authoritative spec

- **`docs/PROTOCOL.md`** — the ratified protocol (v2). The source of truth.
- **`docs/LEDGER-FORMAT.md`** — the starter conformance-ledger format (a DRAFT
  convention with a named promotion trigger; not a contract).

Everything in this bundle quotes or points to those docs rather than
restating them. Read `docs/PROTOCOL.md` first.

## What it does not do

This bundle is stateless know-how. It does **not** own the tracker, does
**not** ratify anything (only the owner does, in literal words), and does
**not** store any repo's VISION.md, contracts, or ledger — those live in each
target repo.

## Contributing

> [!NOTE]
> This project is not currently accepting external contributions, but we're actively working toward opening this up. We value community input and look forward to collaborating in the future. For now, feel free to fork and experiment!

Most contributions require you to agree to a
Contributor License Agreement (CLA) declaring that you have the right to, and actually do, grant us
the rights to use your contribution. For details, visit [Contributor License Agreements](https://cla.opensource.microsoft.com).

When you submit a pull request, a CLA bot will automatically determine whether you need to provide
a CLA and decorate the PR appropriately (e.g., status check, comment). Simply follow the instructions
provided by the bot. You will only need to do this once across all repos using our CLA.

This project has adopted the [Microsoft Open Source Code of Conduct](https://opensource.microsoft.com/codeofconduct/).
For more information see the [Code of Conduct FAQ](https://opensource.microsoft.com/codeofconduct/faq/) or
contact [opencode@microsoft.com](mailto:opencode@microsoft.com) with any additional questions or comments.

## Trademarks

This project may contain trademarks or logos for projects, products, or services. Authorized use of Microsoft
trademarks or logos is subject to and must follow
[Microsoft's Trademark & Brand Guidelines](https://www.microsoft.com/legal/intellectualproperty/trademarks/usage/general).
Use of Microsoft trademarks or logos in modified versions of this project must not cause confusion or imply Microsoft sponsorship.
Any use of third-party trademarks or logos are subject to those third-party's policies.
