# qtwo — skills catalog reduction: five skills contributed by the mode, not always-on

**Work item:** `model_performance-qtwo`
**Date:** 2026-09-07
**Landing stage:** DRAFT PR. This lane may not merge; the merge is the manager's next stage.

## What changed

Converge's five procedure skills — `freeze-bar`, `lane-brief`, `ledger-disposition`,
`proposing-a-change`, `seam-test` — were registered **always-on** in
`behaviors/converge.yaml` via a `tools: - module: tool-skills` block with
`config.skills: ["@converge:skills"]`. Every session this behavior composed onto
therefore rendered all five into the always-on `hooks-skills-visibility` catalog,
whether or not that session was running a Converge operation.

All five are mid-operation **manager** procedures. They now arrive through
`modes/converge-manager.md`'s `contributes.skills` block, so they mount only while
that mode is active.

| file | change |
|---|---|
| `behaviors/converge.yaml` | the `tools:` block deleted; replaced by a comment saying what moved, why, and what not to re-add |
| `modes/converge-manager.md` | `contributes.skills` added, listing all five as `@converge:skills/<name>` |
| `context/converge-awareness.md` | the always-on routing line now says the five arrive with the mode |
| `README.md`, `bundle.md` | the skills sections say the same |
| `tests/test_the_skills_ride_with_the_mode.py` | new — the standing guard (fail-before evidence below) |

Nothing was deleted: all five `skills/*/SKILL.md` files are untouched and still ship.

## The measurement

`render_catalog.py` in this directory stands up a **real session** on this
repository's `bundle.md` and renders the block with the **shipped** renderer
(`SkillsVisibilityHook._format_skills_list`), then activates `converge-manager`
through the real path — `mode:activated` on the session's own hook bus, which is
what `tool-mode` emits — so hooks-mode applies `contributes` via `RuntimeOverlay`
and tool-skills picks it up through the `runtime_skill_overlay` capability.
Nothing in it re-implements the renderer or hand-builds the overlay.

It never runs the `amplifier` CLI and never sets `AMPLIFIER_HOME`. Bundles load
through a private `BundleRegistry(home=…)` — a throwaway directory with a copy of
the real `registry.json` and a symlink to the real cache — with
`install_deps=False`, so no package manager runs and no editable `.pth` file is
rewritten. Verified after the run: `grep -l /tmp/ …/site-packages/*.pth` matched
nothing across 75 `.pth` files, and the real `registry.json` gained no `file://`
converge entry.

Reproduce:

```sh
python3 docs/lanes/qtwo-converge-catalog-reduction/render_catalog.py
```

### Result

| phase | skills in the always-on catalog | the five present? | `load_skill` on each |
|---|---:|---|---|
| **before**, mode inactive | **50** | all five | 5/5 load |
| **after**, mode inactive | **45** | **none** | **0/5 load** |
| **after**, mode active | **50** | all five | **5/5 load** |

**50 → 45: smaller by exactly 5**, and the five come back — loadable by name — the
moment the mode is on. Raw JSON and the rendered blocks for every phase are in
`evidence/` (`before.json`, `after.json`, `*-block-*.txt`).

The before-run also shows the honest baseline for the mode path: with the
contribution absent, activating the mode moved the count not at all (50 → 50).

## Checks run

| check | result |
|---|---|
| `uv run --with pytest pytest -q` (tests/) | **140 passed, 1 skipped** (was 137 + 1; the 3 new ones are this lane's) |
| `uv run --with pytest --with pyyaml pytest -q -c conformance/pytest.ini conformance` | **128 passed** |
| `uv run conformance/composition/run.py .` | **PASS 14/14, fail=0 skip=0** — including 3b (a real session reaches its helpers) and 6b/6c (an unrelated session's helper still keeps `tool-skills`, supplied by the host) |
| `uv run conformance/documents/run.py .` | exit 0 |
| `uv run --with pyyaml ledger/checks/verify.py` | 7 tripwire rows fail — **byte-identical to the same 7 at HEAD**, measured in a clean `git worktree` of HEAD side by side. Pre-existing, not touched by this change. |

The new test could have failed: with the `contributes.skills` block removed from
the mode, `test_every_shipped_skill_is_contributed_by_the_mode` fails with
`assert set() == {'freeze-bar', …, 'seam-test'}`; with it present, 3 passed.

## Honest limits

- **The five now depend on the host supplying `tool-skills` at all.** This behavior
  no longer mounts that module. On the root path the lean anchors base ships it; on
  the `--app` path the host session does — the same dependency the mode machinery
  and the delegation tool already have. A host with no skills tool would reach none
  of its *own* skills either, so this is not a converge-specific gap. Deliberately
  not papered over with a `config.skills: []` entry: module configs deep-merge, and
  a list written here would replace the host's skills dirs rather than add to them.
- **The count 45 is this host's composition**, not a universal number: the catalog
  is the whole composed session's (anchors + work-tracker + the rest). The *delta*
  is what this change owns, and it is exactly the five.
- **The new test is a file-shape check, not a live render.** It proves the wiring
  still says what it says; `render_catalog.py` is what proves the session behaves.
  Drifting back would have to be deliberate and visible in a diff.
- **`render_catalog.py` applies `expand_env_vars`** to the mount plan, which the
  CLI does and a direct `load_and_prepare_bundle` call does not. Without it the
  lean base's context-intelligence hook keeps a literal
  `${AMPLIFIER_CONTEXT_INTELLIGENCE_LOG_LEVEL:INFO}` and refuses to mount. That is
  a gap between the probe and a real session, closed — not a change to the bundle.
