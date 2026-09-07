# Proposed patch: the lane-goal template's outcome branches

**Filed under the goal's own instruction**, which this lane had not executed until now:

> "If the only way to satisfy a deliverable is to write a file outside your worktree … that is a
> **DEFECT IN THIS GOAL, not a task**. Report it against the goal, **ship the patch as an artifact
> under your ARTIFACT ROOT, and resolve** — do not edit another repo, and **do not invent a fourth
> outcome branch**."

This is the patch, shipped as an artifact. It is **not applied** — the template lives outside this
worktree, and applying it here would be the very scope breach the clause forbids.

---

## The defect, in one sentence

**The outcome branches are defined as *checkable end states*, but the Procedure steps route to them by
*verbs only a holding lane can call* — so a lane whose claim is refused is structurally exempt from
every verb while the states themselves remain perfectly checkable.**

A reviewing judge named this precisely: *"structure-locked: the condition applies a universal
requirement to a set that contains a structurally-exempt member."*

## What it cost, measured on this batch

| | |
|---|---|
| Lanes hitting a refused claim on `kp79` | **≥ 5** (android-tester, browser-tester, dot-graph, infographic-builder, reality-check, stories, converge) |
| Independent lanes that diagnosed the trap unprompted | **5** |
| Lanes reaching **opposite** classifications on identical facts | **2** (converge → A; stories → A-by-substance after explicitly refusing to write BLOCKED.md) |
| Classification changes by this lane alone, with **zero** measurement changes | **4** (A → C → A → invented-fourth → A) |
| Errata appended to one item to repair classification churn | **5** |

Every one of those is goal-text cost, not work cost. The underlying repo work never changed once.

## Patch 1 — say that an outcome is a STATE, and name who may satisfy it

The template already says "OUTCOME (checkable end state)". Make it decisive, because five lanes read
it as a verb anyway.

```diff
-OUTCOME (checkable end state) — EXACTLY ONE of these three, and they are exhaustive:
+OUTCOME (checkable end state) — EXACTLY ONE of these three, and they are exhaustive.
+
+A BRANCH IS A STATE, NOT A VERB YOU MUST PERSONALLY CALL. Check the state as written. If the state
+holds — whoever made it hold — the branch is satisfied, and you record HOW it came to hold. The
+Procedure's `work_resolve` / `work_release` are the MECHANISMS a HOLDING lane uses to reach a state;
+they are not the states themselves. A lane whose claim was refused is exempt from the mechanism and
+is NOT thereby exempt from the outcome.
```

## Patch 2 — make branch C executable by a non-holder

Today C requires `work_release`, and Procedure 5 adds *"Release while you still HOLD the item."* A
refused lane can never do both. Measured verbatim on this lane:

```
work_release(id="model_performance-kp79")
-> not currently holding 'model_performance-kp79' in this session
   -- refusing to release an item this session did not claim
work_status() -> "holding": null
```

```diff
-**C. BLOCKED.** … `BLOCKED.md` in the lane directory names it, is committed, and the item is
-released via work_release.
+**C. BLOCKED.** … `BLOCKED.md` in the lane directory names it and is committed. If this session HOLDS
+the item, also release it via `work_release`. IF IT NEVER HELD THE ITEM, there is nothing to release:
+record the refusal verbatim in BLOCKED.md and append the outcome to the item with `work_erratum`,
+which requires no claim, mutates no status/holder, and is idempotent on identical text.
```

## Patch 3 — resolve the Procedure 1 / branch A contradiction

Procedure 1 says a refused claim ⇒ **stop**. Branch A says the outcome is a state that may already
hold. Both fire at once, and every lane resolved the contradiction differently.

```diff
 1. FIRST: `work_claim(...)`. If the claim is refused (held elsewhere / blocked),
-   write BLOCKED.md, commit, write the completion marker, stop.
+   write BLOCKED.md recording the refusal verbatim, commit it, and then CHECK THE OUTCOME BRANCHES
+   BEFORE STOPPING. A refused claim does not by itself make the outcome unreachable — the work may be
+   fully doable without custody (text edits, renders, a test run need no claim). If the outcome is
+   reachable, DO IT, and record both facts: the deliverable state reached, AND that this lane never
+   held the item. Stop only if the outcome is genuinely unreachable — that, and only that, is C.
```

## Patch 4 — the fix that prevents all of the above

```diff
+ONE CHILD ITEM PER LANE. Never launch N per-repo lanes at a single-holder item id. File one child per
+repo under a parent that closes when its children do, and give each lane the id it can actually hold.
+Every pathology in this batch — the refusals, the churn, the five errata, two lanes disagreeing on
+identical facts — follows from N lanes contending for one id.
```

## What this lane recommends, ranked

1. **Patch 4** — kills the whole class. Everything else is a safety net.
2. **Patch 1** — one paragraph; ends the state-vs-verb ambiguity that produced four reclassifications here.
3. **Patch 3** — removes the direct Procedure-1-vs-branch-A contradiction.
4. **Patch 2** — makes C honest for the case it is most often reached in.

## What this lane is NOT proposing

**No fourth outcome branch.** The template forbids it, and this lane briefly invented one
(`GOAL NOT SATISFIED`) before withdrawing it. The three branches are sufficient **once they are read
as states** — which is Patch 1. Adding a fourth would paper over the real defect.
