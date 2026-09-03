# Collaboration Contract — v1 (DRAFT)

**Who builds against this:** teammates who send and receive proposals, whether
or not they run Converge; the intent steward, who answers them; the manager
session, which reads and writes the shared repository host; and whoever builds
the review experience in Direction and the intake that feeds it.

## Purpose

People align above the level of tasks, and they do it through the repository
host they already use. This contract fixes that boundary, so a teammate on plain
tooling loses nothing, and so two Converge users never grow a private channel
between their manager sessions.

## Core (the teeth)

1. **Git is the protocol; Converge is the lens.** Collaboration between people
   happens through the shared repository host — commits, pull requests, and
   their comments. Converge renders that flow; it never replaces it.
2. **Manager sessions never talk to each other directly.** Two stewards both
   running Converge still meet as Converge · host · Converge, and neither
   manager session knows the other exists. That is what keeps a teammate on
   plain tooling a first-class participant, and keeps the seam between two
   parties something a person can read.
3. **Three origins, one review.** A proposal from your manager session, from a
   teammate, or from a pull request is shown identically: what changes sentence
   by sentence · the evidence · what does not change. Where it came from is a
   fact about the proposal, never a different experience.
4. **Pull-request comments are a two-way bridge.** A question asked in Converge
   arrives as a comment; the reply arrives back inside the same review. The
   teammate never leaves their tools, and the steward never copies a judgment
   between tools.
5. **Your answer returns where the proposal came from.** *ratified · ratified
   with edits · declined · later* — written to the dated ratification record and
   posted back to the origin, in the steward's own words.
6. **Inbound changes arrive without you asking for them.** Webhooks where the
   host offers them, polling as the honest fallback. Freshness is never made the
   steward's job, and the fallback is named rather than assumed.
7. **The manager session is not in the hot path.** A write made in the app goes
   through the ordinary repository and proposal mechanism directly; the manager
   session learns of it as an event and folds it into its next turn.
8. **One steward per manager session.** Whose word counts is settled when the
   session is registered, not inferred from whoever is looking. Everyone else is
   a teammate, whose proposals get the same reading and none of the authority.
9. **A ratification is a change to the repository, made the ordinary way.** The
   word is recorded and the text it ratifies is committed, so what was agreed
   has one record, and it is the one everybody already reads.
10. **Converge adds no second collaboration surface.** Not another issue
    tracker, another document store, or a code-review tool. What a teammate
    needs to see is visible on the host, in the host's own terms.

## What v1 deliberately does NOT freeze

- Which repository hosts are supported beyond the one in use — promoted when a
  project adopts a different one.
- How the steward's identity is proved across the app, the local repository, and
  the host — promoted when a second person's word must be told from the
  steward's on the same manager session.
- Whether a teammate can be answered where no pull request exists — promoted
  when someone proposes a change by another route.

## Conformance kit asserts

- A proposal from each of the three origins renders the same three parts and
  offers the same controls.
- An answer given in Converge reaches the origin and the dated ratification
  record; a comment written on the host appears inside the review, attributed.
- With webhooks unavailable, polling still brings a new proposal in without the
  steward acting, and the fallback is reported in plain words, never silently.
- No route exists by which one manager session reaches another; between two
  parties there is only the host.
- A write made in the app lands through the repository mechanism without waiting
  for a manager turn.
- Exactly one steward is registered per manager session, and no second person's
  word is written to the ratification record.
- A teammate who never opens Converge can propose, discuss, and be answered
  using the host alone — recorded by name and date.

## Reserved / open questions

- Whether accepting some changes and reverting others to build *ratified with
  edits* means anything beyond that one answer. It must not quietly become
  ratification line by line.
- What a manager session does with a pull request that edits a locked contract
  and carries no proposal beside it.
