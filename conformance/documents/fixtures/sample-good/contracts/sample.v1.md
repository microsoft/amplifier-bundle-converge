# Sample Contract — v1 (DRAFT)

**Who builds against this:** everyone who writes or reads a document in this
sample project, and the conformance kit that checks them. It is deliberately
ordinary: a worked example of the anatomy `documents.v1` fixes, written so a
colleague who has never opened a code editor can read it and know what it means.

## Purpose

A contract that cannot be read in a minute will not be read at all. This one
exists to show the shape — the same sections, in the same order, every time —
so the kit has something honest to go green against.

## Core (the teeth)

1. **A contract says who would be surprised by a silent change.** Line 3 names
   the people and the systems that build against it. A reader who is not on
   that list can stop reading; a reader who is knows the text is about them.
2. **One contract is about one screen.** Fifty to a hundred lines. Longer than
   that and it is two contracts wearing one filename, and neither gets checked.
3. **Status lives in the H1 parenthetical and nowhere else.** A status repeated
   in the body is a second source of truth, and the two drift apart quietly.
4. **Every clause leads with the rule as fact, in bold.** The bold sentence is
   the promise; the plain lines beneath it are why. A reader skimming only the
   bold text has read the whole contract.
5. **The sections never move.** Purpose, then Core, then what this version
   deliberately leaves open, then what the kit asserts, then the reserved
   questions. A reader who has read one contract can navigate every other one.
6. **What this version leaves open says so, and says what would close it.**
   An open question with no promotion trigger is not held open deliberately;
   it is just unfinished, and it will stay that way.
7. **A change to a locked clause arrives as a proposal, never as an edit.**
   The proposal carries the exact change, the evidence, and what does not
   change. The original stays the law until the steward answers with a word.

## What v1 deliberately does NOT freeze

- The wording of any individual clause — refinements are cheap and expected,
  and are promoted whenever a reader reports a sentence they had to reread.
- Whether a contract may carry sections beyond the five required ones —
  promoted when a real contract needs one and says why.

## Conformance kit asserts

- Line 3 begins with the who-builds-against-this marker.
- The five sections appear, in the order above.
- The file is between fifty and a hundred lines.
- No status token appears outside the H1.
- Every numbered clause in Core leads with bold text.

## Reserved / open questions (NOT frozen)

- Whether a contract should name the person who last read it end to end.
