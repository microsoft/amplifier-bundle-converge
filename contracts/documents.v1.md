# Documents Contract — v1 (DRAFT — amended 2026-09-03, owner-ratified)

**Who builds against this:** everyone who reads or writes a vision, contract,
proposal, brief, or work item under Converge — in this repository and in every
project that adopts the method. That includes colleagues who are not engineers
and coding agents that are not Amplifier sessions. Converge's own agents,
templates, and context are the reference implementation: they must produce this
anatomy and check for it.

## Purpose

Documents are the through-line. If they drift into jargon, sprawl, or status
reports, the humans stop reading and the agents inherit noise. This contract
fixes the shape so that a contract can be read in a minute, trusted, and
checked — by anyone, with any tool.

## Core (the teeth)

1. **Written for amplified information workers.** Anyone who has never opened a
   code editor can read it and know what it means. Terms of art are defined at
   first use or not used.
2. **One contract, one file, about one screen.** Fifty to a hundred lines.
   A vision fits two screens. A brief is a few sentences.
3. **Line 3 says who builds against this.** Two to six lines naming the people
   and systems that would be surprised by a silent change.
4. **The same sections, in the same order, every time.** Purpose → Core (the
   teeth) → What v1 deliberately does NOT freeze (with promotion triggers) →
   Conformance kit asserts → Reserved / open questions → Changelog only if amended.
   A contract may carry an additional section of its own, provided it neither
   displaces nor reorders the ones above.
5. **Clauses lead with the rule as fact,** in bold, then one to three plain lines
   of why. The kit's rule table is numbered to these Core clause numbers, so a failing
   rule names the clause it breaks.
6. **Status lives in the H1 parenthetical and nowhere else.** `(DRAFT)`,
   `(FROZEN 2026-09-02)`, or the hold-loosely form. Neither vision nor contract
   carries kept / broken / in-progress; that lives in the contract check.
7. **Visions are written as though already true,** end state in the present
   tense, with a dated changelog whose entries carry evidence.
8. **A proposal is `<contract>.vN-candidate.md`** and has three parts in order:
   the exact change, sentence by sentence; the evidence (a cost paid or a failure
   caught — preference is not evidence); what does **not** change. The original
   stays the law until ratified.
9. **A work item names its contract** in one line, defines done in plain words,
   and quotes the feedback or gap it came from.
10. **Plain state words everywhere.** Contracts: *Kept · Not yet · Broken ·
    Pinned open · Can't check*. Work: *Truly ready · Waiting on you · Working ·
    Stuck · Done*. Lanes: *Working · Quiet · Silent — may have died*.
11. **Technical detail is folded, never in the deciding sentence** — behind a
    Details fold in the app, in a marked section in a document.
12. **Every converged repository carries the participant kit,** so a colleague or
    a non-Amplifier agent knows what, how, and why without the bundle: a contracts
    README (anatomy, index, freeze bar, how to propose), an `AGENTS.md` addendum
    (converge toward the vision; never edit a locked contract; propose instead;
    where the ledger is; how to run conformance), a pins file of hard facts every
    lane reads first, and a pre-push scan that refuses edits to locked contracts.
13. **Converge is self-hosting.** Its negotiator and proposal drafter write this
    anatomy from shipped templates; its protocol authority checks documents
    against it; its own repository passes the same kit.

## What v1 deliberately does NOT freeze

- An automatic readability score — promoted when a non-engineer first reports a
  document unreadable.
- Translated state vocabulary — promoted when a non-English-first team adopts.
- The exact wording of the participant kit files — templates evolve by evidence.

## Conformance kit asserts

- Every contract: line 3 begins `**Who builds against this:**`; the section
  order above; 50–100 lines; status only in the H1; each clause bold-led.
- Every vision: present tense, no status, dated changelog present.
- Every proposal named `*.vN-candidate.md` has all three parts.
- Every work item names a contract and quotes its source.
- No document uses a machine state token where a plain state word belongs.
- No contract carries technical detail among its deciding sentences.
- A converged repository has all four participant-kit files.
- Converge's own templates and its own repository pass every assertion above.
- A reader who is not an engineer reads each document here and reports nothing
  they had to look up — recorded by name and date.

## Reserved / open questions (NOT frozen)

- Whether the participant kit should also ship a pull-request template asking
  "which contract does this serve?"

## Changelog

| Date | Change | Evidence |
|---|---|---|
| 2026-09-03 | Amended (still v1, DRAFT): clause 4 allows one extra section; clause 5 names clause-number anchoring; kit asserts cover Core 10–11 | documents.v2-candidate.md (ratified, owner word "lgtm") |
