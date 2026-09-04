# Worked example — Collaboration v1

Contract: [`../../contracts/experience-collaboration.v1.md`](../../contracts/experience-collaboration.v1.md)
Kit: none — this contract's promises are mostly about a repository host, and
four of ten need a second person to settle.

This contract is checked against *this repository's own history*, because
Converge collaborates the way it says people should. Every block below is
output from a command run on 2026-09-04 against this repository at `f718a20`.

> Git is the protocol; Converge is the lens. The failure this contract exists to
> prevent is invisible from inside: two Converge users growing a private channel
> between their manager sessions, and a teammate on plain tooling quietly
> becoming a second-class participant.

## Start with one promise

Clause 2, in full:

> **Manager sessions never talk to each other directly.** Two stewards both
> running Converge still meet as Converge · host · Converge, and neither manager
> session knows the other exists.

A promise about something that must *not* exist is the hardest kind to keep
honestly, because nothing on screen shows its absence. So the check reads for
the capability rather than the behaviour:

```
$ if grep -rnE "httpx|requests\.(get|post)|urlopen" app/*.py | grep -q .; then
    echo APP-MAKES-OUTBOUND-CALLS; else echo APP-MAKES-NO-OUTBOUND-CALL; fi

APP-MAKES-NO-OUTBOUND-CALL
```

The app has no client for reaching anything off its own machine. There is no
private channel because there is no means of one. Kept.

Clause 10 is checked the same way — a surface that must not grow:

```
$ if grep -nE "@app\.(get|post)\(\"[^\"]*(issue|ticket|comment|review|thread)" app/serve.py \
     | grep -q .; then echo APP-GREW-A-SECOND-SURFACE; else echo NO-SECOND-SURFACE; fi

NO-SECOND-SURFACE
```

## Right and wrong, told apart — one review, whoever wrote it

Clause 3 says a proposal is shown identically whatever its origin. The Direction
kit's rule 7 is the assertion this row borrows, and the fixture pair is what
tells right from wrong:

```
$ uv run conformance/experience-direction/run.py conformance/experience-direction/fixtures/sample-good --json-only
exit=0   rule 7 PASS

$ uv run conformance/experience-direction/run.py conformance/experience-direction/fixtures/sample-bad --json-only
exit=1   rule 7 FAIL
```

Against the running body:

```
$ uv run conformance/experience-direction/run.py http://127.0.0.1:8811
   7 PASS  a proposal shows what changes · why · the evidence · what does not
           change · the word

   one review path lays out all five parts in the contract's order, and offers
   all four answer words
   parts_found: what changes, why, what does not change, the evidence,
                the word to answer with
```

One review path, five parts, four answer words — and no branch in it for where
the proposal came from. Kept.

The same shape is checked at the document level by the documents kit, which
reads the proposals actually sitting in `contracts/`:

```
$ uv run conformance/documents/run.py .
   8 PASS  every proposal has the three parts, in order
           all 1 proposal(s) carry the three parts in order

$ uv run conformance/documents/run.py conformance/documents/fixtures/sample-bad
   8 FAIL  contracts/broken.v1-candidate.md:
           missing part(s): ['the evidence', 'what does not change']
```

## The ratification, end to end

Clause 9 says a ratification is a change to the repository, made the ordinary
way. Follow one through this repository's own record.

The word lands in a dated file, not a store of the app's own:

```
$ grep -q 'owner-ratifications-' app/writes.py \
    && ls docs/workflow/owner-ratifications-*.md >/dev/null 2>&1 \
    && echo RATIFICATION-IS-A-FILE-IN-THE-REPOSITORY

RATIFICATION-IS-A-FILE-IN-THE-REPOSITORY

$ ls docs/workflow/owner-ratifications-*.md
docs/workflow/owner-ratifications-2026-09-02.md
docs/workflow/owner-ratifications-2026-09-03.md
```

And the text it ratifies is committed the ordinary way, carrying the steward's
literal word in the message:

```
$ git log --oneline --grep=ratified main | head -4
f718a20 ledger: the row quoting the turnkey sentence follows the ratified wording
978d266 ratified: operation.v1 turnkey sentence records the first green; lock held
        loosely; plan approved — owner word 'loosely, ratified, go'
19a3d7b H1 status: record the steward's given words on the vision and every
        contract — nothing locked
2eb0cee ratified: vision principle 8, the experience family, documents clause 14
        + fenced proposals, RIGHT-SIZING — owner word 'Yes, ratified, please go.'
```

The proposal that carried one of them is a sibling file, and it is in the
history too:

```
$ git log --diff-filter=A --name-only --pretty=format: main -- 'contracts/*candidate*'
contracts/documents.v2-candidate.md
```

And the seam between parties is the host, visibly:

```
$ git log --oneline --merges main | head -3
4507e46 Merge pull request #24 from microsoft/integration/gap
af83e8d Merge pull request #23 from microsoft/integration/ledger-green
59f4ac6 Merge pull request #22 from microsoft/integration/wave-7b
```

Word · proposal · commit · pull request. Nothing in that chain is a Converge
mechanism a teammate would need Converge to read.

## What is honestly unmeasurable

Five of the ten clauses are Can't check, and it is worth being blunt about why:
they are about a second person. Clause 1 (git is the protocol, Converge the
lens), clause 4 (pull-request comments as a two-way bridge), clause 5 (your
answer returns where the proposal came from), clause 6 (inbound changes arrive
without you asking), clause 8 (one steward per manager session). Each needs a
teammate, a host, and a date — the contract's own conformance list asks for
exactly that, "recorded by name and date."

They are recorded as Can't check, never as passes. A check that cannot run
reports what it is, and that is the whole reason this contract's row count and
its kept count are different numbers.

## Clause traceability

| Clause | How it is checked | State today |
|---|---|---|
| 1 — git is the protocol; Converge is the lens | needs a teammate on the host | Can't check |
| 2 — manager sessions never talk directly | probe: no outbound client | Kept |
| 3 — three origins, one review | Direction kit rule 7 + documents kit rule 8 | Kept |
| 4 — pull-request comments are a two-way bridge | needs a teammate | Can't check |
| 5 — your answer returns where it came from | needs a teammate | Can't check |
| 6 — inbound changes arrive unasked | needs a host and a webhook | Can't check |
| 7 — the manager session is not in the hot path | probe over `app/writes.py` | Kept |
| 8 — one steward per manager session | needs a second person | Can't check |
| 9 — a ratification is an ordinary repository change | probe + the git history above | Kept |
| 10 — no second collaboration surface | probe over the route table | Kept |

No claim here the contract does not make, and no verdict here that was not run.
