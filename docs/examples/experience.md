# Worked example — Experience v1 (the umbrella)

Contract: [`../../contracts/experience.v1.md`](../../contracts/experience.v1.md)
Kit: none — and that is the thing this example is about.

The umbrella has no kit of its own. Its promises are kept by the family that
hangs off it, so its check is assembled rather than run in one command. Every
block below is output from a command run on 2026-09-04 against this repository
at `f718a20`, with the app served from this worktree on port 8811.

> A contract with no kit is usually a contract nobody checks. This one is
> checked anyway — by borrowing its evidence from the four section kits and by
> reading the family's own text — and the ledger says, row by row, which of the
> two it used.

## Why there is no kit

Clause 15 delegates:

> **This umbrella governs a family.** The places are held by
> `experience-direction.v1` · `experience-operation.v1` ·
> `experience-console.v1` · `experience-collaboration.v1`; the idioms of one
> body by one `platform-*.v1` — `platform-browser.v1` and
> `platform-web-app.v1` first, then one per native body. A platform contract
> adds no behavior and removes none.

Read that clause against the folder it governs and one sentence of it is
already wrong:

```
$ ls contracts/platform-*.v1.md
contracts/platform-android.v1.md
contracts/platform-ios.v1.md
contracts/platform-macos.v1.md
contracts/platform-web.v1.md
contracts/platform-windows.v1.md
```

Neither `platform-browser.v1` nor `platform-web-app.v1` exists, and neither ever
did — the browser and the installable web app were written as one contract,
`platform-web.v1`, whose own clause 9 covers installing. The umbrella and the
family disagree about the family's own membership, and both were ratified in the
same pass. That is a steward's call, not a lane's, so it is filed as
`converge-d3n` and the clause stands as written until a word settles it. This
example quotes it whole rather than tidying the sentence away.

So the umbrella's teeth bite through the sections. Three kits exist and run
against the same body:

```
$ uv run conformance/experience-direction/run.py http://127.0.0.1:8811
   VERDICT: FAIL  (pass=6 fail=6 skip=0)
$ uv run conformance/experience-operation/run.py http://127.0.0.1:8811
   VERDICT: FAIL  (pass=7 fail=8 skip=0)
$ uv run conformance/experience-console/run.py  http://127.0.0.1:8811
   VERDICT: FAIL  (pass=7 fail=3 skip=0)
```

And the family's own structural promise — that no clause slipped through
unchecked — is a test, not an opinion:

```
$ uv run --with pytest pytest conformance/ -q -k "every_core_clause_has_a_row or every_rule_has_a_negative_fixture"
10 passed, 63 deselected in 0.57s
```

Ten tests: every Core clause of all five kitted contracts has a rule, and every
rule either fails on the bad fixture or is a declared Can't-check with its
reason written down.

## The umbrella's own fifteen rows

`ledger/rows.yaml` carries one row per Core clause of this contract. Their
current state:

| State | Rows |
|---|---|
| Kept | 3 — clauses 2, 3, 7 |
| Not yet | 9 — clauses 1, 4, 5, 6, 8, 9, 13, 14, 15 |
| Can't check | 3 — clauses 10, 11, 12 |

Nine of the fifteen borrow their evidence from a section kit's rule; six run a
command of their own against the contracts. None of them is an opinion.

## Right and wrong, told apart — clause 9

> **Every behavior carries one of four words** — `REQUIRED`, `IDIOM`,
> `OPTIONAL`, `EXCLUDED`.

The row for this clause runs a probe over the section contracts. Run it today:

```
$ for f in contracts/experience-direction.v1.md contracts/experience-operation.v1.md \
           contracts/experience-console.v1.md contracts/experience-collaboration.v1.md; do
    printf "%-46s %s\n" "$f" "$(grep -c '(REQUIRED)\|(IDIOM)\|(OPTIONAL)\|(EXCLUDED)' $f)"
  done

contracts/experience-direction.v1.md           11
contracts/experience-operation.v1.md           13
contracts/experience-console.v1.md              0
contracts/experience-collaboration.v1.md        0
```

There is the right and the wrong, side by side in one run. Direction tags all
eleven of its clauses and Operation all thirteen; Console and Collaboration tag
none. Clause 9 is Not yet, and the probe names exactly which two files owe the
words. It flips the moment either starts tagging — the check asserts the gap,
so it cannot rot into a quiet pass.

Clause 13 is checked the same way, and the answer is starker:

```
$ grep -rl 'quick-access' contracts/experience-*.v1.md | wc -l
0
$ grep -rl 'quick-access' contracts/platform-*.v1.md | wc -l
5
```

Every platform contract names the quick-access surface. Not one section
contract does — and the sections are where the behaviors live. "Nobody thought
about the widget" can still pass as a decision, which is the exact failure
clause 13 exists to stop. Carried by `converge-f1l`.

## The disagreement that is on purpose

Clause 14 says a body that cannot do a thing must say so. The Operation kit's
rule 10 passes:

```
[PASS] 10  feedback is accepted in every form this body claims
           (text, a screenshot) and reaches the feedback write;
           not offered here: voice
```

The section clause asks only about the forms this body *claims*, so it is Kept.
The umbrella asks whether the app *says* it cannot take a voice note, and the
app says nothing at all. So the umbrella's row is Not yet while the section's
rule is Kept — and the ledger states plainly that the two "disagree on purpose."
The passing rule's report is the evidence for the failing row. That is what
borrowing an assertion means, and why the row records which rule it borrowed.

## What is honestly unmeasurable

Three rows are Can't check, and they are the three about what `IDIOM` means
(clauses 10, 11, 12). A file scan can prove a contract carries the word; it
cannot prove a reviewer honoured it. What would settle them is written into the
rows: a second body, and a recorded review of one against the other, by name and
date — which is what this contract's own conformance list asks for in its last
bullet. Until then they stay Can't check, never a pass.

## Clause traceability

| Clause | How it is checked | State today |
|---|---|---|
| 1 — the anchor is a manager session | Operation kit, rule 13 | Not yet |
| 2 — two places, and only two | Console kit, rule 1 | Kept |
| 3 — the console is a pane, never a third place | Console kit, rule 1 | Kept |
| 4 — exactly five writes | Direction kit, rule 9 | Not yet — Ask is absent |
| 5 — at most five things ask for your word | probe over the ratification record | Not yet |
| 6 — plain state words everywhere | Operation kit, rule 8 | Not yet |
| 7 — the app holds no data of its own | probe over the app | Kept |
| 8 — the manager session can do it too | probe over the write routes | Not yet |
| 9 — every behavior carries one of four words | probe over the section contracts | Not yet — shown above |
| 10 — `IDIOM` means required, shape free | nothing can settle it yet | Can't check |
| 11 — idioms never subtract behaviors | nothing can settle it yet | Can't check |
| 12 — exceed in idiom, never in features | nothing can settle it yet | Can't check |
| 13 — three surface classes, placed against all | probe over the contracts | Not yet — shown above |
| 14 — say so where a body cannot | Operation kit, rule 10 | Not yet — the disagreement above |
| 15 — this umbrella governs a family | probe over the platform contracts | Not yet |

No claim here the contract does not make, and no verdict here that was not run.
