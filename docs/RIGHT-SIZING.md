# Right-sizing a contract

A **contract** is a short promise this project must keep. `docs/CONTRACTS-README.md`
says what shape one takes. This page answers the question the shape does not:
*how much* belongs in one.

Converge is opinionated about it. A contract that sprawls stops being read, and
an unread contract governs nothing. A contract too thin to fill its own sections
never says what it means. Those are the same failure — the boundary was drawn in
the wrong place — and the cure is the same: draw it again.

## The rule

**One contract is one domain component.** Three things follow, and all three
must hold at once:

1. **It reads in a minute** — fifty to a hundred lines, about one screen.
2. **It has one "who builds against this"** — a single list of the people and
   systems that would be surprised by a silent change to the text.
3. **It has one conformance kit** — one runnable check, pointed at one target.

If any of the three is false, the file is not one contract. Split it, or merge
it back.

## Split it when any of these is true

- **The "who builds against this" list has divided.** Two audiences that do not
  overlap are two promises. Neither one reads the other's half, and each pays
  attention for a change that was never theirs.
- **The kit would need two targets.** One check that must be pointed at a
  repository *and* at a running app is two checks wearing one name, and the half
  that cannot run hides behind the half that can.
- **The clauses have stopped referring to one another.** Clauses that never
  mention their neighbours are not holding one promise together; they are
  separate promises that happen to share a file.

Length alone is a symptom, never the test. A file at a hundred and ten lines
whose three signals still hold is trimmed. A file at seventy lines whose
audience has divided is split, however comfortable it reads.

## Merge it back when this is true

- **The file cannot fill its own sections.** A Core section of one clause, or
  nothing real under *What v1 deliberately does NOT freeze*, means this is a
  clause of a larger promise that was given its own file too early. Fold it into
  the contract it belongs to, and let the larger promise carry it.

## The hierarchy: umbrella, section, platform

A domain too large for one contract becomes a **family**, never a longer file.

- The **umbrella** holds what is true everywhere in the domain — the behaviors
  every member keeps, and the vocabulary they all share.
- A **section** contract holds one coherent area of the domain, written in the
  umbrella's own terms.
- A **platform** contract holds how one body expresses those behaviors — its
  idiom. A platform may exceed the umbrella in idiom, never in features. Idioms
  satisfy behaviors; they never subtract them.

The umbrella is **upstream** of everything beneath it, and each member **pins it
by hash** — naming the exact revision it was written against. A pin is what
makes the relationship checkable: when the umbrella moves, the pin still names
what the member agreed to, so the difference is visible rather than assumed.
Changing the umbrella is a proposal like any other, ratified by the intent
steward, and each member's pin is reviewed against it before the member follows.

Reviewing a member asks *"is the behavior satisfied?"* — never *"does it look
the same?"*

## The same boundary is the sub-project boundary

The line that decides where one contract ends is the same line that decides
where one project ends.

A section or a platform contract may become **its own repository**, with its own
intent steward, its own vision, its own work, and its own Converge instance. It
carries a **pins file** naming the umbrella and the hash it was written against.
That file is the whole of the relationship; nothing else crosses the boundary.

Making that split is a choice, not a consequence. One manager session may run
several of these repositories at once — splitting the contract does not oblige
you to split the operation. Split the project when a member needs its own
direction, its own pace, or its own steward. Do not split it merely because a
file grew.

## Worked example — the experience family

The app began as one contract covering every place, every write, and every body
it would ever run on. It failed all three signals at once: it ran past a screen,
its audience had divided (whoever builds a phone body is not surprised by a
change to how proposals are reviewed), and its check would have needed two
targets — a repository of documents and a running app.

So it became a family. An umbrella holds the behaviors every body keeps.
Section contracts hold Direction, Operation, the Manager Console, and
collaboration through the shared code host. One platform contract per body holds
that body's idiom. Each pins the umbrella by hash. The original is kept for the
record and marked superseded; the index in `docs/CONTRACTS-README.md` shows the
whole family in one table.

Any one of those members could become its own repository tomorrow, with its own
steward, and nothing about the umbrella would have to change.

## The test, in one line

If you cannot say in a sentence which domain component this file promises, and
name one audience and one check for it, you are holding two contracts — or half
of one.
