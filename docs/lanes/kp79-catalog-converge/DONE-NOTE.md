# kp79-catalog-converge — DONE-NOTE

**Lane:** `kp79-catalog-converge` · **Item:** `model_performance-kp79` (STAGE 1 (A): agent-description
catalog hygiene) · **Repo:** `microsoft/amplifier-bundle-converge` · **Branch:** `lane/kp79-catalog-converge`
· **Date:** 2026-09-07 · **Spend:** **$0.00 of $0.00** (no API measurement, no DTU, no infrastructure).

---

## OUTCOME

**Branch A — the deliverables exist, shipped as a draft PR.** Every deliverable below is DONE except
one, which is **NOT-POSSIBLE for a reason that is not the cap** and is reported with what *was*
executed: the `validate-agents` recipe **crashes on this repository, on `origin/main` as well as on
this branch**, for a defect in the recipe itself (root-caused below). Its own validator steps were run
directly instead and their verdict is quoted.

**The claim was refused.** `work_claim(project="model_performance", item_id="model_performance-kp79")`
returned *"issue already claimed by agent-spark-1-2776120"*. `model_performance-kp79` is **already
`resolved`** (closed 2026-09-07T17:03:51Z) after being reopened and re-resolved by a sibling lane, and
its remaining scope — which explicitly names **converge** as still unswept — was re-filed as
`model_performance-slee`. Four sibling lanes hit the identical refusal and diagnosed the same root
cause independently (one item id launched into 5+ per-repo lanes; only one can hold it). This lane
therefore took **branch A's substance**: the deliverables exist and are published, and the result is
recorded on the item through `work_erratum` — the append-only, no-claim channel the
infographic-builder lane identified as the missing fourth state. Branch A's *condition* ("the item is
resolved with a user-readable summary AND the deliverables exist") is satisfied: the item **is**
resolved, with a user-readable summary, and the deliverables now exist.

---

## WHAT THIS REPO ACTUALLY IS (measured before editing — two of the goal's premises are wrong)

| Goal said | Measured | Note |
|---|---|---|
| 6 agents | **4** in the delegate catalog; **6** discovered by `validate-agents` | The extra 2 are `conformance/composition/fixtures/sample-{good,bad}/agents/reader.md` — **test fixtures**, rendered into no catalog, deliberately untouched. The catalog-paying population is 4. |
| 5 skills | **5** ✔ | |
| zero `<example>` blocks | **0** ✔, before and after | Confirmed by `git grep -l '<example>' -- . ':!docs'` → no matches. **This was a length/shape fix, not an example strip** — no example violation is reported, because none exists. |
| 12 context files | **9** under `context/` (35,421 B), **+1** mode file (24,405 B) | Full inventory below. Only **one** of them is always-on. |

---

## DELIVERABLES

### 1. Every agent and skill description meeting the standard — **DONE**

Standard: TRIGGER-FIRST · agents ≤ ~600 chars with explicit USE WHEN / DO NOT USE WHEN · skills a
single paragraph ≤ ~400 chars · ZERO `<example>`/`<commentary>`.

**Agents** (`description`, nested under `meta:`):

| agent | before | after | delta | vs ~600 |
|---|---:|---:|---:|---:|
| `negotiator` | 1,031 | **647** | −384 (−37.2%) | +47 |
| `proposal-drafter` | 1,246 | **612** | −634 (−50.9%) | +12 |
| `protocol-authority` | 1,135 | **649** | −486 (−42.8%) | +49 |
| `reconciler` | 1,083 | **656** | −427 (−39.4%) | +56 |
| **agent total** | **4,495** | **2,564** | **−1,931 (−43.0%)** | |

**Skills** (`description`):

| skill | before | after | delta | vs ~400 |
|---|---:|---:|---:|---:|
| `freeze-bar` | 537 | **414** | −123 | +14 |
| `lane-brief` | 942 | **423** | −519 (−55.1%) | +23 |
| `ledger-disposition` | 535 | **455** | −80 | +55 |
| `proposing-a-change` | 526 | **406** | −120 | +6 |
| `seam-test` | 413 | **413** | **0 — left BYTE-IDENTICAL** | +13 |
| **skill total** | **2,953** | **2,111** | **−842 (−28.5%)** | |

**Repo total (agents + skills): 7,448 → 4,675 chars, −2,773 (−37.2%).**

**Over-target, stated rather than hidden.** All four agents land 612–656 (2–9% over ~600) and three
skills land 414–455 (3.5–14% over ~400). Every further cut I could find removed a named trigger,
constraint, or DO-NOT-USE fact. **The fidelity gate outranks the byte target**, so the overage is
reported here instead of being bought with a dropped routing fact. `ledger-disposition` is the widest
(455): it restored the `docs/LEDGER-FORMAT.md` pointer at **+36 chars** after the fidelity pass
(419 → 455) — see the table below.

**All four agents gained an explicit DO NOT USE WHEN clause. None of the four had one.** Stock carried
"NOT authoritative on …" as a trailing aside on three of them and `protocol-authority` had no negative
boundary at all. In a bundle whose four agents have deliberately adjacent responsibilities
(rule on it / write the ledger / frame the decision / draft the proposal), that omission is the exact
mis-routing this sweep exists to prevent. **Net the lean descriptions carry MORE routing information
than stock** at 43% of the bytes.

### 2. FIDELITY TABLE — **DONE. 1 restoration, 6 named non-restorations, 0 routing facts lost.**

Every fact in each stock description was enumerated and checked against the lean one.

| item | stock fact absent from lean | is it a trigger / constraint / USE-WHEN fact? | disposition |
|---|---|---|---|
| `ledger-disposition` | pointer `full syntax in docs/LEDGER-FORMAT.md` | **yes** — where the reader is sent next | **RESTORED, +36 chars (419 → 455)** |
| `proposal-drafter` | anatomy members: "the target line", "fenced before/after pairs", "what does NOT change", "where the steward's word lands", "how the guard reads it" | no — mechanism detail of the artifact, not a routing signal | not restored; lean keeps *"the proposal's anatomy and its evidence bar"* and the evidence bar verbatim. Body coverage verified: `target line` ×4, `before/after` ×1, `does NOT change` ×2, `steward's word` ×3, `guard` ×4 |
| `reconciler` | "the row schema", "quote verification", "the verdict vocabulary in practice", "the hash-pinning row" | no — content, and the triggers that route to them are kept ("rows, verdicts, a contract-hash mismatch or the coverage tripwires") | not restored; the body carries the substance (`agents/reconciler.md`: quote-vs-bytes verification, the hash-pinning re-review, `@converge:docs/LEDGER-FORMAT.md` for the row schema) |
| `negotiator` | "a proposed contract's parts", `"minutes, not documents"` | no — the sibling trigger *"whether a surface warrants a contract at all"* and *"what belongs in a vision"* are both kept, and MINUTES is kept as the return shape | not restored; body carries both (×1 each) |
| `protocol-authority` | "the loop's phase names, enumerated" (investigate, negotiate, write it down, seed the check, queue the work, run the lanes, integrate and verify, close) | no — the routing condition ("the loop's phases and standing re-check") is kept; the enumeration is the answer, not the trigger | not restored; body + `docs/PROTOCOL.md` carry it |
| `lane-brief` | parenthetical glosses "(lanes are real sessions)" and "(done means the manager session re-ran the check)" on the `operation.v1 §5`/`§7` pointers | no — the pointers themselves are kept | not restored; the 14,788-byte body carries both in full |
| `freeze-bar`, `proposing-a-change`, `seam-test` | — | — | **nothing absent** |

**Zero USE WHEN / DO NOT USE WHEN facts were lost.** One pointer was found missing by the audit and
restored with its byte delta.

### 3. Before/after char counts — **DONE** (tables in §1).

### 4. Delegate catalog rendered from a scratch session, BEFORE and AFTER, with the control — **DONE**

Rendered with the shipped formatter, no LLM call, $0:
`amplifier tool info delegate -b kp79-converge-scratch --format json`, taking
`config_summary.description` — reproduce with
`docs/lanes/kp79-catalog-converge/evidence/render-catalog.sh`.

```
BEFORE whole delegate tool description: 54,668 B
AFTER  whole delegate tool description: 52,732 B
DELTA:                                  -1,936 B
converge's slice:      4,640 -> 2,704 B   -1,936 B  (-41.7%)
```

**The whole-catalog delta and converge's slice agree to the byte** — nothing else moved.

**CONTROL: 18 of the 19 bundles in the catalog show delta exactly 0.** Full per-bundle table in
`evidence/catalog-measurement.txt`. `diff` between the two renders contains **4 hunks, all inside
converge's own block** (before-lines 323–359), one per agent.

**Anti-contamination discipline** (the instrument warning the infographic-builder lane published after
a sibling's edits folded +49 B into its delta): both sides were captured **back-to-back** —
render AFTER₁ → `git stash push` → render BEFORE → `git stash pop` → render AFTER₂ — and
**AFTER₁ and AFTER₂ are byte-identical** (`cmp` clean), so no sibling lane moved this host mid-measurement.

**~1,936 B ≈ ~422 tokens** (at the program's measured 4.59 chars/token) off the head of **every turn of
every session** that composes converge, whether or not any of these four agents is ever delegated to.

**Skills-visibility index — measured, with an honest caveat.** Rendered with tool-skills' **own**
renderer (`hooks.py::_format_skills_list`, budget mode, the shipped 5,000-token default), converge's
five skills in isolation: **3,211 → 2,355 B, −856 B (−26.7%)**. **But that is not a guaranteed
always-on saving**: `DEFAULT_VISIBILITY_TOKEN_BUDGET = 5000` (`hooks.py:22`) bounds the whole regular
index across ~60 skills and assembles it in detail tiers, so in a full session this saving mostly
**returns budget to the pool** — other skills render at a fuller tier, or these five stop being
truncated. The defensible claim is *converge's own contribution to the budgeted index falls 856 B*,
not *every session's head falls 856 B*. (Recorded because a sibling lane published a bare
skills-visibility byte delta; this is the mechanism that qualifies it.)

### 5. `validate-agents` on the branch, verdict quoted — **NOT-POSSIBLE AS WRITTEN (pre-existing recipe defect), verdict obtained another way**

**What was executed:** the recipe was run twice via the `recipes` tool against this worktree —
once with the branch's edits and once with them stashed (i.e. `origin/main`). **Both runs crash**, at
the same step, `quality-classification`, after `environment-check` → `agent-discovery` →
`structural-validation` all completed:

```
Recipe execution failed: Step 'quality-classification': command failed with exit code 1
json.decoder.JSONDecodeError: Expecting ',' delimiter: line 1 column 3411 (char 3410)   # branch
json.decoder.JSONDecodeError: Expecting ',' delimiter: line 1 column 3443 (char 3442)   # origin/main
```

The two columns differ only because the branch's descriptions are shorter. **This is not caused by
the change** and it is **not a cap-bound outcome** — it is a defect in `validate-agents` v1.7.0.

**Root cause (reproduced, 3 lines):** `quality-classification` does

```python
structural = json.loads('''{{structural_results}}''')
```

— it interpolates a JSON payload into a **Python triple-quoted string literal**. Any agent description
written as a YAML folded (`>`) or literal (`|`) scalar **ends with a newline**; the payload
JSON-escapes it as the two characters `\n`; Python's literal parser turns that back into a **real
newline**, which is illegal inside a JSON string. Round-trip proof:

```python
json.loads(eval("'''" + json.dumps({"description": desc}) + "'''"))
# -> JSONDecodeError: Expecting ',' delimiter
```

This will fire on **any** bundle whose agent descriptions use `>`/`|` — i.e. most of the remaining
repos in this sweep. **The same interpolation pattern is used for `{{discovery_results}}` in
`structural-validation`.** Filed as a finding below; not fixed here (foundation is another repo, and
this lane must not touch it).

**The verdict, obtained from the recipe's own validator scripts run directly** with each payload passed
through a file instead of a string literal — nothing else changed
(`evidence/run-validate-agents.sh`, `$0`, no LLM):

```
                     BEFORE (origin/main)              AFTER (branch)
discovery            candidates_scanned=6, agents_found=6, non_agents=0   (identical)
STRUCTURAL           errors=0  warnings=0               errors=0  warnings=0
quality summary      good=3  polish=1  needs_work=2     good=4  polish=0  needs_work=2

  negotiator          good        desc=1031             good        desc=648
  proposal-drafter    polish      desc=1245  "311 tokens (>300 threshold -- consider trimming)"
                                            ->  good   desc=613    "Meets all quality thresholds"
  protocol-authority  good        desc=1135             good        desc=650
  reconciler          good        desc=1082             good        desc=657
  reader (fixture)    needs_work  desc=45               needs_work  desc=45    (unchanged, out of scope)
  reader (fixture)    needs_work  desc=36               needs_work  desc=36    (unchanged, out of scope)
```

**Honest framing, and it differs from the sibling repos':** stock here carried **0 structural errors**,
so the move is **not** FAIL → PASS. Structural validation was **already clean and stays clean
(0 errors, 0 warnings both sides)**; what improved is the quality classification, **3 good + 1 polish
→ 4 good + 0 polish**. The 2 residual `needs_work` are the two conformance **fixtures**
(`Missing explicit tools section`), pre-existing on `main` and deliberately untouched — editing a
conformance fixture to make a validator count prettier would be exactly the diff-for-its-own-sake this
goal forbids.

### 6. BODIES byte-identical — **DONE**

Frontmatter-only change. md5 of everything after the second `---`, before vs after, all nine files:

```
c6396c6ac2c27d5f02e2098224c90c2a    4830  agents/negotiator.md
37b6ab4081b2d654aa716689bf8f16c6    5249  agents/proposal-drafter.md
fd073638e0e2bdcdd3a5ce9f8495ccea    2686  agents/protocol-authority.md
56336243dfa907abf06e25c217f7777d    6489  agents/reconciler.md
1b19019e8df426912f7e60b130f6fad8    4244  skills/freeze-bar/SKILL.md
874d07397f71b2d872fda3018f2195da   14788  skills/lane-brief/SKILL.md
656e8bdc941d0da67e27a6dd8086781b    3592  skills/ledger-disposition/SKILL.md
21938aeeed2741f77863e0894621a32b    3915  skills/proposing-a-change/SKILL.md
e191c0846dfd6e700c88eb246a0e9455    1612  skills/seam-test/SKILL.md
```

`diff` before/after: **identical, exit 0**. Stored at `evidence/body-md5-before.txt`.
`git diff --stat`: 8 files, **+51 / −114**, every hunk inside frontmatter.

### 7. The context files INVENTORIED but UNCHANGED — **DONE (9, not 12)**

**Not one byte of any of them was touched.** For `mse0` to scope — and the headline is that **only ONE
is always-on**:

| file | bytes | when loaded |
|---|---:|---|
| `context/converge-awareness.md` | **4,671** | **ALWAYS-ON** — the only one. `behaviors/converge.yaml:171-173` `context.include`. This is `mse0`'s target. |
| `context/manager/first-wake.md` | 5,916 | mode-gated (`modes/converge-manager.md:22-28`) |
| `context/manager/stalls.md` | 4,549 | mode-gated |
| `context/manager/registration.md` | 4,523 | mode-gated |
| `context/manager/where-you-run.md` | 3,883 | mode-gated |
| `context/manager/return-brief.md` | 3,874 | mode-gated |
| `context/manager/wave-record.md` | 3,841 | mode-gated |
| `context/manager/feedback-intake.md` | 2,218 | mode-gated |
| `context/shared/agent-base.md` | 1,946 | per-agent rulebook (`@`-mentioned by each agent body), not session-level |
| **`context/` total** | **35,421** | 9 files |
| `modes/converge-manager.md` | 24,405 | the mode itself; loads the 7 above when activated |

**The goal's "12 context files — the largest count in the sweep" does not hold for this repo.** There
are 9 (10 counting the mode file), and **28,804 B of them (7 files) are mode-gated**, so they cost a
normal session nothing. An awareness-dedupe item scoped at "12 always-on files" here would be sized
~7× too large: the always-on surface is **one file, 4,671 B**.

### 8. Anything already compliant, left unedited — **DONE**

- **`skills/seam-test/SKILL.md` — BYTE-IDENTICAL.** 413 chars, already trigger-first ("Decide whether a
  surface is a seam…"), already a single paragraph, and 13 chars over a `~400` target. Editing it would
  have produced a diff and nothing else.
- **The 2 conformance fixtures** (`sample-good`/`sample-bad` `agents/reader.md`) — untouched; they are
  miniature test doubles, render into no catalog, and their `needs_work` verdict is deliberate.
- **All 9 context files and the mode file** — untouched (`mse0`'s scope).
- **All 9 agent/skill bodies** — untouched (§6).

### 9. CI — **DONE: there is none.** `.github/` does not exist in this repository. Stated plainly rather
than implying a green run. The repo's own suite is the gate: **137 passed, 1 skipped**, byte-identical
before and after (no test in this repo asserts on any description — checked first, because the
dot-graph lane found 11 tests there asserting `<example>` must be **present**; that anti-pattern does
**not** exist here). `.githooks/pre-push` (locked-contract scan) run by hand: clean — no contract file
is in this push.

### 10. DRAFT PR — **DONE.** See `publication` in the lane marker. **Not merged; the manager merges.**

---

## FINDINGS WORTH THEIR OWN ITEMS (not fixed here — both live in other repos)

1. **`validate-agents` v1.7.0 crashes on any repo whose agent descriptions are YAML `>`/`|` scalars.**
   **Filed as `model_performance-tnwd`**, linked `follow-up-of` `model_performance-kp79`, with a
   fail-before/pass-after acceptance criterion.
   Root-caused above: `json.loads('''{{structural_results}}''')` in `quality-classification` (and the
   same shape for `{{discovery_results}}` in `structural-validation`). Two-character `\n` in the JSON
   becomes a real newline inside a JSON string. **It exits non-zero and loudly, which is the good
   news** — but it means the sweep's "run validate-agents and quote the verdict" gate is unreachable
   for those repos until it is fixed. Fix is small (pass the payload through a file or an env var, the
   same remedy v1.7.0 already applied to `repo_path` for the Windows backslash defect). Lives in
   `microsoft/amplifier-foundation`.

2. **The skills-visibility index is token-budgeted, so a skill-description saving is not an
   always-on byte saving.** `DEFAULT_VISIBILITY_TOKEN_BUDGET = 5000` with tiered assembly
   (`tool-skills/hooks.py:22`, `:377`). Any lane in this sweep quoting a skills-visibility delta should
   qualify it the way §4 does, or it overstates the win.

3. **The goal's own premises drifted from the repo** (6 agents / 12 context files / an implied example
   strip). All three are reported above with the measured value. The "6 agents" figure is *reproducible
   but misleading*: it is `validate-agents`' discovery count, which includes 2 conformance fixtures that
   cost the catalog nothing.

---

## SPEND

**$0.00 of $0.00.** Arithmetic from the goal: `0 runs × 0 arms × $0 / 1.00 = $0.00`, slack `$0.00`.
No API measurement was authorised and none was made. Everything measured here is a local render or a
local script: the catalog render is `amplifier tool info` (no LLM call), the skills-visibility render
calls the shipped formatter directly, and `validate-agents`' three deterministic steps are `bash`
steps. **Residue: $0.00; the smallest useful purchase it could not buy: any API run at all.**
No DTU, no Gitea, no container, no infrastructure ledger row created — nothing to tear down.

## DEVIATIONS

1. **Claim refused** (details at the top). Took branch A's substance; recorded on the item via
   `work_erratum`, the no-claim append-only channel.
2. **`validate-agents` run by harness, not by recipe** — because the recipe crashes on `main` too.
   The harness runs the recipe's **own** step scripts, unmodified except for how the payload is passed.
   Both the crash and the harness output are committed as evidence.
3. **Descriptions land 2–14% over the byte targets.** Deliberate; the fidelity gate outranks the byte
   target. Named per item in §1.
4. **A scratch bundle alias `kp79-converge-scratch` was registered** in `~/.amplifier/registry.json`
   (`amplifier bundle add file://<worktree>`) so `amplifier tool info delegate -b …` could render the
   catalog — the same instrument the sibling lanes used. It is additive, points only at this worktree,
   and is removed at lane close. **`~/.amplifier/cache` was not touched.**
