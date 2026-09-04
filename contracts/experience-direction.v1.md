# Experience: Direction Contract — v1 (DRAFT — content owner-ratified 2026-09-03)

**Who builds against this:** intent stewards and teammates who read, question,
and ratify a vision or a contract; the manager session, which proposes into the
same documents and must be able to do anything this place can; and whoever
builds a body for it. This contract is one section of the `experience.v1`
umbrella (`contracts/experience.v1.md`) and inherits its platform mechanism:
every clause below is tagged REQUIRED (present and behaving as written) or
IDIOM (required; its shape follows the platform, and the review question is
whether the behavior is satisfied). An idiom satisfies a behavior; it never
subtracts one.

## Purpose

Direction is where the agreement lives — the vision and the contracts as one
reading experience, not a folder of files. A steward should be able to read
what was agreed, see what moved since last time, answer a proposal, and ask for
one, without leaving for an editor, a comparison tool, or a code host.

## Core (the teeth)

1. **Documents are organized per repository, with an All view across them.**
   *(REQUIRED)* One manager session may hold several repositories, and the
   agreement is one body of work, not one reading per checkout.
2. **Documents render properly, and the source is always one gesture away.**
   *(REQUIRED)* Markdown, images, links between documents, tables, front
   matter, Mermaid and DOT diagrams, and safely embedded HTML all render, and a
   raw source view sits beside every rendered one.
3. **A reader can copy, download, zoom, and choose the width.** *(IDIOM)* Copy
   as rendered, copy as source, download the source, read at page width or full
   screen. The controls follow the platform; the four abilities do not.
4. **Every document carries four views: Reading · Changes · Review · History.**
   *(REQUIRED)* Reading is the clean document. Changes is what moved since you
   last read, sentence by sentence. Review is a proposal with its evidence and
   your word. History is the document over time, in dates and proposal names.
5. **Direct editing is offered exactly where it is legal, and the guard is the
   law.** *(REQUIRED)* A draft document may be edited in place, click to save.
   A locked one may not, and the refusal comes from the guard that refuses —
   never from a hidden control or an instruction someone might follow.
6. **Restoring from history is a real action, and it routes through a proposal
   when the target is locked.** *(REQUIRED)* Restore a wording, a paragraph, a
   section, or the whole document. On a locked document the same gesture
   produces a proposal to answer, so the lifecycle holds without the steward
   having to know it does.
7. **A proposal looks the same whoever proposed it.** *(REQUIRED)* Your manager
   session's, a teammate's, a pull request's: what changes sentence by sentence
   · why · the evidence · what does not change · the word to answer with. One
   that arrived from elsewhere carries your questions and your answer back to
   where it came from.
8. **Accepting and reverting individual changes constructs "ratified with
   edits."** *(REQUIRED)* A steward keeps six changes, drops one, fixes three
   words, and answers once. The granular choices are not a new kind of
   ratification; they build the one word already in the vocabulary.
9. **Ask is a scoped request whose output is always a proposal.** *(REQUIRED)*
   Point at a paragraph, a document, or every document, say what you want, and
   what returns is a proposal to review — never a silent edit, never a chat.
10. **Concurrent editing is met with courtesy presence and reconciliation.**
    *(IDIOM)* While a person is editing a section that is shown softly, and the
    manager session backs off and queues rather than fights. If changes do
    collide, the choice offered is Use combined · Keep mine · Review both.
11. **The lock control is gated on the four conditions, and they are shown.**
    *(REQUIRED)* It says what it means · it carries a real example of right and
    wrong · it can be checked against reality · the steward has read it and
    agreed. The control is live only when all four are met, and nothing locks
    on its own.

## What v1 deliberately does NOT freeze

- Editing richer than click, edit, save — promoted when a steward reports a
  real edit the simple path could not carry.
- Where each steward's "since you last read" mark is kept — promoted when a
  second steward reads the same repository.
- Answering a teammate's comments in place, in both directions — promoted when
  the first such comment has to be answered somewhere else.

## Conformance kit asserts

- Every document opens in all four views, and Changes shows removed sentences.
- Markdown, front matter, a Mermaid diagram, a DOT diagram, a table, an image,
  and a link between documents all render; raw view shows the same file.
- Copy rendered, copy source, download, zoom, and width each work on a body
  that claims them.
- The edit control is absent on a locked document, and the guard refuses the
  write even when the control is forced.
- Restore against a locked document produces a proposal and changes no file.
- A manager session's proposal and one arriving from a pull request render with
  the same parts in the same order.
- Granular choices produce exactly one answer of "ratified with edits", written
  to the dated ratification record.
- Ask returns a proposal every time, at all three scopes.
- The lock control stays inert until all four conditions are met.

## Reserved / open questions

- Whether a body may show two documents side by side, and what that would mean
  for the Changes view.
