# Experience Contract — v1 (DRAFT)

**Who builds against this:** intent stewards and teammates, who open the app in
whatever body is at hand; whoever builds those bodies — browser, installable web
app, phone, desktop; the manager session, which must be able to do anything the
app can; and the authors of the section and platform contracts hanging off this.

## Purpose

One experience, many bodies. This contract holds what must be true of every
body, so a person who learns Converge on one carries it to the next without
surprise, and a platform can be wholly native without quietly dropping a
behavior on the way.

## Core (the teeth)

1. **The anchor is a manager session, not a repository.** One manager session
   may register several repositories and several work queues. Home is the list
   of manager sessions you run, sorted by which one needs you — how many things
   want your word, lanes running against lanes intended, the last brief line,
   quiet or silent.
2. **Two places, and only two.** *Direction* — the vision and contracts as one
   experience. *Operation* — the manager session at work as one experience.
   Conversation is a modality, not a place.
3. **The Manager Console is a pane, never a third place.** It stays open beside
   either place and survives the switch between them; `experience-console.v1`
   holds what it must do.
4. **Exactly five writes.** Answer with a word (ratified · ratified with edits ·
   declined · later) · raise or lower a priority · drop feedback · steer · ask
   for a proposal. Nothing else, in any body, writes anything.
5. **At most five things ask for your word at once,** re-ranked each refresh.
   Several small calls may arrive as one ratification sheet answered in a pass;
   every answer lands in a dated ratification record.
6. **Plain state words everywhere.** Contracts: *Kept · Not yet · Broken ·
   Pinned open · Can't check*. Work: *Truly ready · Waiting on you · Working ·
   Stuck · Done*. Lanes: *Working · Quiet · Silent — may have died*.
7. **The app holds no data of its own.** It shows the project's documents, code
   record, work queue, lanes, return log, and pending decisions. A second copy
   of the truth is a defect, not a cache.
8. **Whatever you can do here, the manager session can do too.** Every write
   names a manager-session operation that does the same thing, so nothing the
   project needs is reachable only by a person at a screen.
9. **Every behavior carries one of four words** — `REQUIRED`, `IDIOM`,
   `OPTIONAL`, `EXCLUDED`. Required is present and behaves as described, and its
   absence is a gap; optional a surface may carry; excluded it must not, and its
   presence is the defect.
10. **`IDIOM` means the behavior is required and its shape is not.** Review asks
    "is the behavior satisfied?", never "does it look the same?" — which is how
    a body gets to be wholly native without drifting.
11. **Idioms satisfy behaviors; they never subtract them.** Three tests settle
    idiom against divergence — *behavior*: same thing done, same fact learned,
    same refusal for the same reason; *transfer*: is the person surprised, or
    do they merely find it in a different place; *subtraction*: does the shape
    remove a state, a refusal reason, or required information.
12. **A body may exceed this umbrella in idiom, never in features.** Richer
    gestures and better affordances are welcome everywhere. A feature in one
    body and nowhere else is either a behavior that belongs in this family or
    it is debt — there is no third thing it can be.
13. **Three surface classes, named once:** *full app* · *quick-access* (widget,
    tray, menu bar) · *notification*. Every behavior is placed against all
    three, so "nobody thought about the widget" cannot pass as a decision.
14. **Where a body genuinely cannot do a thing, it says so in the app** — what
    the limit is, and what to do instead. Silence is the only wrong answer.
15. **This umbrella governs a family.** The places are held by
    `experience-direction.v1` · `experience-operation.v1` ·
    `experience-console.v1` · `experience-collaboration.v1`; the idioms of one
    body by one `platform-*.v1` — `platform-browser.v1` and
    `platform-web-app.v1` first, then one per native body. A platform contract
    adds no behavior and removes none.

## What v1 deliberately does NOT freeze

- Which behavior is required and which is idiom, class by class — promoted as
  each section contract lands and its matrix is written.
- Where a platform contract lives — here, or in a sub-project with its own
  steward — promoted when a body has an owner who is not this one.
- A shared look across bodies — promoted when a second body ships.

## Conformance kit asserts

- Home lists the manager sessions you run, sorted by which needs you, each card
  carrying the count, the lanes, the last brief line, and quiet or silent.
- Both places are reachable from either, and the console is still open, with its
  conversation intact, after the switch.
- Exactly five write paths, each named to a manager-session operation that does
  the same thing; never more than five things asking for a word at once; every
  answer lands in the dated ratification record.
- No machine vocabulary outside a Details fold.
- Every behavior in a section contract carries one of the four words for each of
  the three surface classes.
- A behavior found in one body and named in no contract is reported as debt.
- A person who learned a behavior in one body finds it in another without being
  told where — recorded by name and date.

## Reserved / open questions

- Whether quick-access and notification each earn their own contract once a body
  ships them.
- Where the reading cursor behind "what changed since you last read" is kept,
  given the app holds no data of its own.
