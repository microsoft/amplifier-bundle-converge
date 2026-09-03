# Amplifier Converge — Vision (DRAFT)

*Written for amplified information workers. Terms of art are defined where they first appear; the full rules live in `docs/PROTOCOL.md`.*

---

## Where this is going

AI does more of the work every month, and an **amplified** person — one human, well-leveraged — now builds what recently took a team. The value is captured only by working above the level of tasks and code, and by collaborating there too: teams now move too fast, on efforts too large, for yesterday's coordination to keep pace. Converge is a way of working at that altitude.

It rests on three roles. The **manager session** is a long-running AI session that runs a project's work on your behalf, for days or weeks. **Worker sessions** are many short-lived AI sessions, each taking one bounded piece of work in isolation and returning with proof. You are the **intent steward**: you define where the project is going and what must be true of it, and you make the decisions only a person can make.

You define that in two documents. A **vision** — the project as it will be when it is right, written as though already true. And **contracts** — the specific promises the project must keep, each short enough to read in a minute and precise enough to check against reality. Both are written for people. Everything beneath them is worked out and managed for you.

The work unfolds over time, and you are present throughout. Long stretches run unattended; the decisions that need you arrive exactly when they need you and never otherwise; nothing is called done until it has been seen working. The vision and contracts mature as the work does — you need not get everything right on day one. The direction is grown, not declared.

Those same documents are where people align with one another. A teammate's proposal to change a contract and the manager session's proposal look and behave the same: what changes, the evidence for it, what does *not* change. You ratify or decline with a word, and the words you ratify are the words every session then obeys. One text, two audiences — an unbroken **through-line** from human agreement to AI guardrail.

---

## Principles

1. **Your attention is the scarcest resource in the system.** It is spent only where a person is irreplaceable: defining direction; confirming the major decisions as they arise; exercising taste and judgment — deciding what *not* to build is its clearest form; supplying the critical thinking that turns a proposal into a decision worth standing behind; and making exactly four kinds of call — **ratify** a change to the direction, make an **irreversible** choice, **check** what only a person or device can check, set **priority or stop**. Anything else that reaches you is a defect.

2. **Grown, not declared.** A vision or contract begins as a *draft* and becomes **locked** when it meets four conditions: it says what it means; it carries a real example of right and wrong; it can be checked against reality; you have read it and agreed. A locked contract changes only by written proposal backed by evidence — a cost actually paid or a failure actually caught. Preference is not evidence. Refinements are cheap; reversals owe evidence first. A contract that meets the bar may be held unlocked, deliberately, while its neighbors mature — the steward's call, recorded.

3. **One text, two audiences.** Proposals from teammates and from the manager session are reviewed identically and answered with one of four words: *ratified* · *ratified with edits* · *declined* · *later*. A teammate's proposal receives your questions and your answer where it was sent from. The through-line reaches every participant — a colleague, another tool's coding agent — through the repository itself: a contracts README, the `AGENTS.md` addendum every coding agent reads, a pins file of hard facts, and a pre-push guard. What, how, and why never depend on which tool someone brought.

4. **Contracts are checked against reality, continuously.** After each change lands, every contract is re-checked and reported in plain words — *Kept · Not yet · Broken · Pinned open · Can't check*. Drift is caught in both directions: a contract quietly broken, and one quietly kept without anyone saying so. This is the **ratchet**; progress only clicks forward.

5. **Work is derived, never invented.** Every item traces to the gap between a contract and what exists, or to feedback you gave, and names the contract it serves.

6. **Feedback is signal, handled with care.** You will react to work in progress — a screenshot, a voice note, "still not working" — at any point, and that is welcome. The manager session never files raw feedback as work. It reads the note against the contracts, the current work, and what is running; confirms which version you were looking at; merges reports that share a cause and splits one that hides several; supplies the detail your note lacked; updates existing work rather than duplicating it; surfaces failures you didn't report; and, when feedback is really a change of direction, brings you a decision instead of a ticket. "Still broken" reopens verification, not the tracker.

7. **The manager session runs the whole operation.** It owns the queue; plans what to build next and in what order, and shows you that plan with its reasons; briefs and launches worker sessions in **lanes** — each a separate, independent session in its own copy of the code, never a sub-agent tucked inside the manager session itself; fills the lanes with work that cannot collide; notices silence; judges completion by a check it re-runs itself, never by a worker session's account or a marker file; integrates, verifies, and re-checks the contracts; and writes you a brief in plain sentences for your return. Its governing strategy is to **maximize the useful work that proceeds without you**, within the limits you set — objective, budget, lane count — so that when something must wait for your word, everything else keeps moving. Each worker session's piece ends one of three ways: done with proof; stuck, with the cause; needs your judgment.

8. **The app has two places.** **Direction** — the vision and contracts as one experience: what changed since you last read, whether each contract is kept, your questions on any paragraph, every proposal awaiting you. **Operation** — the manager session at work: your return brief, the plan, what is running against what waits on you, lanes running against lanes intended, evidence you can inspect, your limits, a place to drop feedback, every manager session you run. At most five things ask for your word at once. You can do exactly four things: answer with a word, raise or lower a priority, drop feedback, steer. The app holds no data of its own and shows only the project's truth; whatever you can do in it, the manager session can do too. It begins as a companion web page beside your project, your conversation with the manager session still in your usual place; in time the whole experience, that conversation included, lives in the app.

9. **Rules are enforced, not aspired to.** No one — person or AI — can edit a locked contract in place; the system refuses. Where enforcement is not yet possible, we say so rather than pretend.

10. **Converge is the method, not the project.** It carries *how*: the rules, the AI roles, the manager session's practice, the contract check, the app. Each project owns *what*: its vision, contracts, work, and results. The method serves one repository or a program of many.

11. **Written for people.** Everything Converge writes — here or in your project — is readable by an amplified information worker who has never opened a code editor.

12. **Turnkey, with honest dependencies.** Converge composes proven pieces — the shared work queue, the parallel-lanes practice, standard developer tooling — rather than reinventing them. One install brings them up and checks them, or says plainly what is missing.

---

## What Converge deliberately does not do

Own any project's vision, contracts, work, or results · ratify anything · invent contracts where none is needed · make the four kinds of call for you · claim enforcement it lacks · reduce the manager session to a rigid pipeline (automation only where the work is truly mechanical) · own the tooling worker sessions run on · alter the tools of other work in your session · become another issue tracker, monitoring console, notification stream, or code-review tool · promise one-shot magic or pursue autonomy for its own sake · depend on a heavyweight base · keep history in documents meant to stay current.

## Not yet true

Worker sessions on a remote service · the manager conversation inside the app · a protocol for manager sessions coordinating with one another · enforced per-role tool limits (an upstream request) · the one-install turnkey check for the operation half, which is not yet green.

## What we have seen

The method end to end in isolated environments — a 6-for-6 evaluation, the guard refusing an AI's edit to a locked contract, the system catching its own author locking a contract improperly. The first half in daily use ratifies cleanly one document at a time; its failures were a draft that waited five hours because nothing said "waiting on you," and drafts whose completeness could not be checked without re-reading. The second half in daily use showed lanes dwindling unnoticed for hours, a person serving as the tester of work reported done, and a person hand-carrying one incident into four manager sessions. Feedback, meanwhile, was handled well daily in a real project — merged and split by cause, dated against the build, enriched before filing, escalated as decisions when it concerned direction. The contracts exist to keep the first and close the rest.

## Reading order

`docs/PROTOCOL.md` → `README.md` → `docs/ANNOUNCEMENT.md` → `docs/design/mechanism-spec.md` → the presentation. The rules stay always-true; design records carry snapshot labels.
**Governing contracts:** `composition.v1` · `operation.v1` · `surface.v1` · `documents.v1`

## Changelog

- **2026-09-02 — v1 (DRAFT).** From the ratified rules, this project's own decision record, four rounds of alignment through the release announcement, and the measured record of the method in daily use.
