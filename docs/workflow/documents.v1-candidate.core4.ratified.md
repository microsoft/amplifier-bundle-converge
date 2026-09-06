# Proposal — documents.v1 (candidate, 2026-09-06)

**Target:** `contracts/documents.v1.md`. It is the only file this proposal
changes, and it is unchanged until the steward answers.

**What this asks for:** that `documents.v1` says what records an amendment when
the contract being amended has no room left for a changelog row.

**Which promise it serves:** Core 2 ("One contract, one file, about one screen.
Fifty to a hundred lines.") and Core 4 ("… → Reserved / open questions →
Changelog only if amended."). Raised by work item `converge-tabm`, carried by
`converge-528q`.

`documents.v1` is `(DRAFT)`, so neither guard would refuse an edit in place.
This is written as a proposal anyway: Core 8 is how a contract changes, and a
draft is not a reason to skip the record of who decided what.

The original stays the law until the steward answers with one of four words:
*ratified* · *ratified with edits* · *declined* · *later*.

## The exact change

One change. One line becomes two.

### 1. Core 4 — what records an amendment when the changelog will not fit

Current:

```
   Conformance kit asserts → Reserved / open questions → Changelog only if amended.
```

Replacement:

```
   Conformance kit asserts → Reserved / open questions → Changelog only if amended
   and it fits; otherwise the archived proposal is the record, H1 `amended <date>`.
```

For reading only — **not** a fenced pair to apply. Clause 4 entire, after the
change:

> 4. **The same sections, in the same order, every time.** Purpose → Core (the
>    teeth) → What v1 deliberately does NOT freeze (with promotion triggers) →
>    Conformance kit asserts → Reserved / open questions → Changelog only if amended
>    and it fits; otherwise the archived proposal is the record, H1 `amended <date>`.
>    A contract may carry an additional section of its own, provided it neither
>    displaces nor reorders the ones above.

"The archived proposal" is the one Core 8 already requires. In this repository
it is kept as `docs/workflow/<stem>.ratified.md`, stamped with the steward's
word, the date, and what was applied.

## The evidence

**A cost actually paid, on this tree, yesterday's work and today's.**

**1. An amendment landed on four contracts and left no record inside them.**
Commit `d45918a` (2026-09-06) applied six ratified proposals. Its own message,
verbatim:

```
  experience.v1              2 pairs + 1 deletion   100 lines -> 100
  experience-direction       3 pairs (9 + 2 tags)    96 -> 99
  experience-operation       3 pairs (11 + 2 tags)   96 -> 99
  experience-console        11 pairs                 80 -> 90, 96 with changelog
  experience-collaboration  11 pairs                 85 -> 96
```

and, further down:

```
  Filed rather than fixed: converge-tabm (four of these contracts are at the
  100-line ceiling and cannot carry the changelog row their amendment owes)
```

**2. Measured now.** `wc -l` and a grep for the section, on this tree:

```
contracts/experience-collaboration.v1.md        96 lines  changelog=0
contracts/experience-console.v1.md              96 lines  changelog=1
contracts/experience-direction.v1.md            99 lines  changelog=0
contracts/experience-operation.v1.md            99 lines  changelog=0
contracts/experience.v1.md                     100 lines  changelog=0
```

Only the one with room got the row.

**3. A changelog costs six lines, minimum.** The same commit measured it:
experience-console went `80 -> 90, 96 with changelog`. The six are a blank line,
`## Changelog`, a blank line, the header row, the separator, and the entry —
`tail -6 contracts/experience-console.v1.md`:

```
## Changelog

| Date | Change | Evidence |
|---|---|---|
| 2026-09-06 | Every clause carries one of the four words as a code span, and each is placed across full app · quick-access · notification | `docs/workflow/experience-console.v1-candidate.ratified.md`; owner words 2026-09-05T20:01:47-07:00 and 2026-09-06 round 2 |
```

**4. The arithmetic that blocked the other four.** 100+6=106 · 99+6=105 ·
99+6=105 · 96+6=102. Every one of them breaks Core 2's ceiling, which the kit
enforces as rule 2 (`all 14 contract(s) are 50–100 lines`). There was no wording
that would have fit; the row itself is the overflow.

**5. What a reader sees today.** `head -1 contracts/experience-direction.v1.md`:

```
# Experience: Direction Contract — v1 (DRAFT — content owner-ratified 2026-09-03)
```

That contract was amended on 2026-09-06 and says 2026-09-03. The only way to
learn otherwise is to leave the contract — for a git log, or for
`docs/workflow/`. A document that cannot say when it last changed is the drift
Core 4 exists to prevent.

**6. This proposal pays the same cost, which is the point.** `documents.v1` is
99 lines. The replacement adds one. Applied, it is exactly 100 — it can never
carry a changelog row of its own, and the rule it adds is the rule that will
record it. Measured by applying both changes to a throwaway copy of `HEAD`:

```
$ git archive HEAD | tar -x -C /tmp/probe-w17     # then apply this change
documents.v1 lines after apply: 100
$ uv run conformance/documents/run.py /tmp/probe-w17
  [PASS] 2   contract_length: all 14 contract(s) are 50–100 lines
  [PASS] 4   contract_section_order: all 14 contract(s) carry the required sections in order
  [PASS] 5a  contract_clauses_bold_led: all 14 contract(s) lead every Core clause in bold
  [PASS] 5c  contract_clauses_carry_their_why: all 14 contract(s) say why after every bold lead
  [PASS] 6   contract_status_only_in_h1: all 14 contract(s) keep status in the H1 alone
  VERDICT: PASS  (pass=18 fail=0 skip=9)
```

### Why the archive and the H1, and not "a changelog is exempt from the count"

The work item named two shapes. This picks the first, for three measured
reasons.

- **The archive already exists, and it already carries more.** Core 8 requires
  every amendment to come from a proposal, and this repository keeps each one as
  `docs/workflow/<stem>.ratified.md` with the word, the date, what was applied,
  and the original evidence. The changelog row is a lossy summary of a record
  that is already mandatory. Nothing new has to be invented or maintained.
- **The H1 form is already in use and already legal.** `documents.v1`'s own
  first line reads `# Documents Contract — v1 (DRAFT — amended 2026-09-03,
  owner-ratified twice)`, and rule 6 passes on it today (`all 14 contract(s)
  keep status in the H1 alone`). This proposal names a practice the repository
  already has rather than adding one.
- **An exemption would make Core 2's number stop meaning what Core 2 says.**
  The number is a promise about what a reader must scroll through — "about one
  screen". A changelog is on that screen whether or not it is counted, and it
  only grows: measured on this tree, `composition.v1`'s changelog rows run 205
  and 311 characters, and it has three of them after two amendments and a lock.
  Exempting them lets a contract be 100 countable lines and 140 real ones while
  the kit reports it inside the band. It would also force every reader of Core 2
  to hold two numbers, and the kit to report both.

**What this costs, plainly.** The evidence column leaves the contract. A reader
who wants to know *why* a clause changed opens the archived proposal instead of
reading a row in place, and the H1 date is the only thing telling them there is
something to open. That is the trade this asks the steward to make. The
alternative — a growing changelog inside a document promised to be one screen —
was judged the worse of the two, but it is a judgment, and it is the steward's
to overturn.

## What does **not** change

- **Core 2's numbers stand.** Fifty to a hundred lines, a vision in two screens,
  a brief in a few sentences. No exemption, no second number.
- **Every contract that already carries a changelog keeps it**, unchanged —
  `composition.v1`, `documents.v1`, `operation.v1`, `experience-console.v1`. The
  clause makes the changelog conditional, never forbidden: where it fits, it is
  still the record and still preferred.
- **Core 8 is untouched.** A proposal is still `<contract>.vN-candidate.md`
  with the same three parts in the same order.
- **Core 6 is untouched.** Status still lives in the H1 and nowhere else;
  `amended <date>` sits beside the status in that same parenthetical, exactly as
  `documents.v1`'s H1 already does.
- **No section is added, removed, renumbered, or reordered**, and no other
  clause is reworded. The word-level difference between the current block and
  its replacement is the eleven words after "amended".
- **The status stays `(DRAFT)`.** This proposal locks nothing.
- **No file outside `contracts/documents.v1.md` changes.** Not the vision, not
  the ledger, not the app, not another contract. The four contracts that owe a
  record are not touched here; ratifying this is what makes stamping their H1s
  legal, and that stamping is separate work.
- **The kit learns no new assert, and this proposal does not pretend it does.**
  Rule 4 already treats `Changelog` as optional, so the change is conformant the
  day it lands — but nothing yet checks that an amended contract carries *either*
  a changelog row *or* an `amended <date>` in its H1. Adding that assert needs a
  line in the Conformance kit asserts section, and after this change there is no
  line left. Filed as work rather than claimed here.

## The steward's word

**Ratified 2026-09-06.** Word given on the tidy card: \"2) ratified\". Applied exactly; the contract's H1 carries `amended 2026-09-06` because a changelog row would have put it at 101 lines — the very case this clause settles.

One of four: *ratified* · *ratified with edits* · *declined* · *later*.

Answer here:

```
Word:
Date:
Edits (if "ratified with edits"):
```
