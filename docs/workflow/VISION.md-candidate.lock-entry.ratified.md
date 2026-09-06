# Proposal — docs/VISION.md (candidate, 2026-09-06)

**RATIFIED 2026-09-06** — owner word "2) ratified" on the tidy card; applied to docs/VISION.md the same day under the guard's ratified-candidate rule.

**Target:** `docs/VISION.md`, which is `(FROZEN 2026-09-06)`. It is the only
file this proposal changes, and it is unchanged until the steward answers.

**What this asks for:** that the vision's 2026-09-06 lock entry be written as a
bullet, in the shape the two entries above it already use. It was written as a
markdown table row inside a bullet list, so it renders as literal pipes.

**Which promise it serves:** `documents.v1` Core 7 ("Visions are written as
though already true … with a dated changelog whose entries carry evidence") and
`experience-direction.v1` Core 2 (the render carries what the document
contains). Raised by work item `converge-gu8t`, carried by `converge-528q`.

Nothing about the lock, the steward's word, or the direction changes. The words
in the entry are kept verbatim; only their shape changes.

The original stays the law until the steward answers with one of four words:
*ratified* · *ratified with edits* · *declined* · *later*.

## The exact change

One change: the `## Changelog` section's three entries, replaced as a block so
the ordering is unambiguous. The file is 70 lines before and 70 lines after.

### 1. The changelog — the lock entry becomes a bullet, and leads

Current (the last three lines of the file):

```
- **2026-09-03 — v1 (DRAFT), amended.** Principle 8 rewritten from the owner's experience brief: manager-session anchor, Manager Console, the fifth write (ask), one experience across browser/PWA/native under one umbrella contract. Manager-to-manager talk moved from "not yet" to "deliberately does not."
- **2026-09-02 — v1 (DRAFT).** From the ratified rules, this project's own decision record, four rounds of alignment through the release announcement, and the measured record of the method in daily use.
| 2026-09-06 | Locked on the steward's word "Yep, all look good to me, make it so." — the four conditions answered in docs/workflow/LOCK-SHEET-2026-09-06.md; changes from here go through a `<name>.vN-candidate.md` proposal | docs/workflow/owner-ratifications-2026-09-06.md round 2 |
```

Replacement:

```
- **2026-09-06 — v1 (FROZEN).** Locked on the steward's word "Yep, all look good to me, make it so." — the four conditions answered in docs/workflow/LOCK-SHEET-2026-09-06.md; changes from here go through a `<name>.vN-candidate.md` proposal. Evidence: docs/workflow/owner-ratifications-2026-09-06.md round 2.
- **2026-09-03 — v1 (DRAFT), amended.** Principle 8 rewritten from the owner's experience brief: manager-session anchor, Manager Console, the fifth write (ask), one experience across browser/PWA/native under one umbrella contract. Manager-to-manager talk moved from "not yet" to "deliberately does not."
- **2026-09-02 — v1 (DRAFT).** From the ratified rules, this project's own decision record, four rounds of alignment through the release announcement, and the measured record of the method in daily use.
```

Two things happen, and both are deliberate:

- The row's three cells become the bullet's own parts — the date and status in
  the bold lead, the change as the sentence, and the evidence named at the end
  with the word "Evidence:" so nothing the row carried is lost.
- The entry moves to the top. The two entries below it run newest-first
  (2026-09-03, then 2026-09-02); the lock entry is the newest and was sitting
  last. Leaving it where it is would fix the pipes and keep a changelog that
  reads out of order.

## The evidence

**A failure actually caught, by this repository's own kit.** Run on this tree
against the app on 127.0.0.1:8788:

```
$ uv run conformance/experience-direction/run.py http://127.0.0.1:8788 --cookie <cookie>
  [PASS] 2a  rendered_with_the_source_one_gesture_away: all 12 document(s) arrive rendered with their source beside them, and a Raw control switches between them
  [FAIL] 2b  the_render_carries_what_the_documents_contain: the render drops a table (source has it, the render does not: ['docs/VISION.md'])
  ------------------------------------------------------------------------------
  VERDICT: FAIL  (pass=12 fail=1 skip=0)
```

That is the whole of the kit's failure: one rule, one document, this line.

**What the steward actually sees.** The app's own payload for `docs/VISION.md`,
read from the captured render, ends its changelog like this — the lock entry is
swallowed into the bottom of the 2026-09-02 bullet, pipes and all:

```
<li><strong>2026-09-02 — v1 (DRAFT).</strong> From the ratified rules, this project's own decision record, four rounds of alignment through the release announcement, and the measured record of the method in daily use.
| 2026-09-06 | Locked on the steward's word &quot;Yep, all look good to me, make it so.&quot; — the four conditions answered in docs/workflow/LOCK-SHEET-2026-09-06.md; changes from here go through a <code>&lt;name&gt;.vN-candidate.md</code> proposal | docs/workflow/owner-ratifications-2026-09-06.md round 2 |</li>
</ul>
```

The document that records the lock cannot show the lock. A single pipe row is
not a table in markdown — a table needs a header and a separator — so it is
neither a table nor a list item, and both readers get it wrong.

**A second kit, independently, cannot see the entry at all.** The documents kit
reads dated changelog entries as `- **YYYY-MM-DD …`, so it counts two where
there are three:

```
$ uv run conformance/documents/run.py .
  [PASS] 7b  vision_dated_changelog: docs/VISION.md carries 2 dated changelog entry/entries (most recent 2026-09-03)
```

The most recent thing that happened to the vision is that it was locked, on
2026-09-06. Nothing that reads this file mechanically can learn that.

**Measured that the change fixes it.** Both changes were applied to a throwaway
copy of `HEAD` (`git archive HEAD | tar -x -C /tmp/probe-w17`):

```
VISION lines after apply: 70
pipe-shaped lines left in VISION: 0
$ uv run conformance/documents/run.py /tmp/probe-w17
  [PASS] 7b  vision_dated_changelog: docs/VISION.md carries 3 dated changelog entry/entries (most recent 2026-09-06)
  [PASS] 2b  vision_fits_two_screens: docs/VISION.md is 70 lines -- inside two screens (200)
  VERDICT: PASS  (pass=18 fail=0 skip=9)
```

For the direction kit's rule 2b, the mechanism is exactly this: the rule fails
only where a document's *source* holds a table and its *render* does not. With
the pipe row gone, `docs/VISION.md` holds no table, and the four documents that
do hold one all render it — measured from the same capture:

```
composition has <table>: True
documents has <table>: True
operation has <table>: True
experience-console has <table>: True
```

So the capability stays demonstrated by real tables, and the one document that
was faking one stops.

## What does **not** change

- **The lock stands.** `# Amplifier Converge — Vision (FROZEN 2026-09-06)` is
  untouched. This proposal does not unlock, re-date, or re-open anything.
- **Not one word of the entry is dropped or reworded.** All three cells survive
  — the date, the sentence about the steward's word and the four conditions, and
  the pointer to `docs/workflow/owner-ratifications-2026-09-06.md` round 2. The
  only additions are the bullet marker, the bold lead, and the label
  "Evidence:", which is the column header the table shape was carrying implicitly.
- **The other two changelog entries are byte-identical.** They appear in the
  replacement only so the new order is unambiguous.
- **No principle, no section, and no other line of the vision changes.** Lines
  1–65 are untouched; the file is 70 lines before and after.
- **No file outside `docs/VISION.md` changes** — not a contract, not the ledger,
  not the app, not a kit. The app renders correctly today for every document
  whose source is correct; this is a document fix, not a renderer fix.
- **This says nothing about how future entries must be written.** Whether a
  vision changelog is a bullet list or a table is settled here only for this
  file, by matching what this file already does.

## The steward's word

**Ratified 2026-09-06.**

One of four: *ratified* · *ratified with edits* · *declined* · *later*.

Answer here:

```
Word:
Date:
Edits (if "ratified with edits"):
```
