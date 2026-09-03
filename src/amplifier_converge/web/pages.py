"""The pages — two places, a short list, and the four things you can do.

Everything here is server-side rendered HTML. There is no framework and no
script: a form posts, the write runs, the page is drawn again. That is on
purpose — a page that needs JavaScript to show whether a lane died is a page
that can silently show nothing.
"""

from __future__ import annotations

from ..reading import Reading
from ..reading.brief import PlanStep
from ..reading.documents import Document, lock_conditions, lock_is_available
from ..reading.kept import standing_of
from ..reading.lanes import Board, Lane
from ..reading.proposals import Proposal
from ..reading.queue import QueueSummary, WorkItem
from ..reading.snapshot import Snapshot
from ..reading.strip import Decision, empty_state
from ..reading.whatchanged import WhatChanged
from ..words import GATE_WORDS
from ..writing import WRITES
from .markup import document_html, esc, inline, quoted, quoted_markup, state
from .styles import STYLESHEET, WORDMARK


# --------------------------------------------------------------------------
# shell
# --------------------------------------------------------------------------


def shell(
    *,
    title: str,
    place: str,
    snapshot: Snapshot,
    waiting: int,
    body: str,
    flash: tuple[str, bool] | None = None,
) -> str:
    flash_html = ""
    if flash:
        message, ok = flash
        flash_html = f'<div class="flash{"" if ok else " bad"}">{esc(message)}</div>'

    honest = "".join(
        f'<div class="honest">{esc(note)}'
        + (
            f'<details><summary>Details</summary><div class="inner"><p>{esc(detail)}</p></div></details>'
            if detail
            else ""
        )
        + "</div>"
        for note, detail in snapshot.notes
    )

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="color-scheme" content="light">
<title>{esc(title)} — {esc(WORDMARK)}</title>
<style>{STYLESHEET}</style>
</head>
<body>
<a class="skip" href="#main">Skip to the page</a>
<div class="shell">
  <header class="rail">
    <div class="brand">
      <span class="wordmark">{esc(WORDMARK)}</span>
      <span class="project">{esc(snapshot.repo.name)}</span>
    </div>
    <nav class="places" aria-label="Places">
      <a class="place{' is-on' if place == 'landing' else ''}" href="/">Needs your word
        {f'<span class="count">{waiting}</span>' if waiting else ''}</a>
      <a class="place{' is-on' if place == 'direction' else ''}" href="/direction">Direction</a>
      <a class="place{' is-on' if place == 'operation' else ''}" href="/operation">Operation</a>
    </nav>
  </header>
  <main id="main">
    {flash_html}
    {honest}
    {body}
    <p class="foot">This page keeps nothing of its own. Everything on it is read back from
    the project — its documents, its code record, its work queue, its lanes. Whatever you can
    do here, the manager session can do the same way.</p>
  </main>
</div>
</body>
</html>"""


# --------------------------------------------------------------------------
# the short list
# --------------------------------------------------------------------------


def _answer_form(decision: Decision) -> str:
    buttons = []
    for index, word in enumerate(decision.words):
        primary = " is-primary" if word == decision.word else ""
        buttons.append(
            f'<button class="word{primary}" type="submit" name="word" value="{esc(word)}">{esc(word)}</button>'
        )
    if decision.key == "fill-lanes":
        return f"""<form class="words" method="post" action="/do/steer">
  <input type="hidden" name="ask" value="fill the lanes">
  <input type="hidden" name="about" value="{esc(decision.what)}">
  <input type="hidden" name="back" value="/">
  <button class="word is-primary" type="submit">fill the lanes</button>
  <a class="word" href="/operation#lanes" style="text-align:center;line-height:46px;text-decoration:none">look first</a>
</form>"""
    return f"""<form class="words" method="post" action="/do/answer-with-a-word">
  <input type="hidden" name="subject" value="{esc(decision.what)}">
  <input type="hidden" name="back" value="/">
  {''.join(buttons)}
</form>"""


def _with_quotes(sentence: str, borrowed: str) -> str:
    """The app's own sentence, with the project's words inside it marked.

    A decision names the thing it is about — a document, a lane, a proposal —
    and that name is the project's word, not the page's. Marking it keeps the
    sentence around it the page's own, and plainly so.
    """
    if borrowed and borrowed in sentence:
        head, _, tail = sentence.partition(borrowed)
        return f"{esc(head)}{quoted(borrowed)}{esc(tail)}"
    return esc(sentence)


def decision_card(decision: Decision) -> str:
    trade_offs = "".join(f"<li>{esc(t)}</li>" for t in decision.trade_offs)
    note = (
        f'<p class="why">{quoted(decision.quote)}</p>'
        if decision.quote
        else ""
    )
    return f"""<article class="card decision">
  <h3>{_with_quotes(decision.what, decision.subject)}</h3>
  <p class="why">{esc(decision.why_now)}</p>
  {note}
  <p class="rec"><span class="lbl">We suggest</span><br>{esc(decision.recommendation)}</p>
  <ul class="tradeoffs">{trade_offs}</ul>
  {_answer_form(decision)}
  <p class="muted" style="margin-top:10px"><a href="{esc(decision.link)}">Open it in {esc(decision.place.title())}</a></p>
</article>"""


def landing(snapshot: Snapshot, decisions: list[Decision]) -> str:
    if not decisions:
        return f"""<section class="strip-empty">
  <h2>Nothing needs your word.</h2>
  <p>{esc(empty_state(snapshot))}</p>
</section>
<div class="section"><h2>While you were away</h2></div>
{_brief_card(snapshot)}"""

    plural = "thing" if len(decisions) == 1 else "things"
    cards = "".join(decision_card(d) for d in decisions)
    return f"""<div class="section">
  <h2>{len(decisions)} {plural} need{'s' if len(decisions) == 1 else ''} your word</h2>
  <p>Each one is worked out already: what it is, why now, what we suggest, and the two ways it could go.
  Answering <em>later</em> re-ranks it and never dismisses it.</p>
</div>
{cards}
{_brief_card(snapshot)}"""


def _brief_card(snapshot: Snapshot) -> str:
    from ..reading.brief import return_brief

    sentences = "".join(f"<p>{esc(line)}</p>" for line in return_brief(snapshot))
    return f"""<article class="card stack">
  <span class="lbl">Since you were last here</span>
  {sentences}
  <p class="muted"><a href="/operation">Open Operation</a></p>
</article>"""


# --------------------------------------------------------------------------
# Direction
# --------------------------------------------------------------------------


#: How the word beside a promise is coloured. Moss for kept, brick for broken,
#: amber for the two that are neither, and nothing for a word that is only an
#: admission that we could not look.
KEPT_TONE = {
    "Kept": "kept",
    "Broken": "broken",
    "Not yet": "open",
    "Pinned open": "open",
}


def _document_chip(doc: Document) -> str:
    """Where it stands as a document: still being written, or settled."""
    return state(doc.state_word, "chip locked" if doc.locked else "chip")


def _kept_line(doc: Document, snapshot: Snapshot) -> str:
    """Whether the promise is being kept — a different question, said apart.

    Only a promise gets one. The vision says where the project is going; it is
    not a thing that can be kept or broken clause by clause, and putting a word
    there would be inventing a judgement nothing measured.
    """
    if doc.kind != "contract":
        return ""
    standing = standing_of(doc.relpath, snapshot.promises.value)
    chip = state(standing.word, f"chip {KEPT_TONE.get(standing.word, 'unsure')}")
    return (
        f'<p class="muted" style="margin-top:6px">{chip} &nbsp; {esc(standing.sentence)}</p>'
    )


def _document_row(doc: Document, snapshot: Snapshot) -> str:
    conditions = lock_conditions(doc, snapshot.repo)
    green = sum(1 for _, ok, _ in conditions if ok)
    gate = (
        "Locked — it changes only by a written proposal backed by evidence."
        if doc.locked
        else f"{green} of the four conditions for locking are green."
    )
    return f"""<article class="card">
  <h3><a href="/direction/{esc(doc.slug)}">{quoted(doc.title)}</a></h3>
  <p class="muted" style="margin-top:6px">{_document_chip(doc)} &nbsp; {esc(gate)}</p>
  {_kept_line(doc, snapshot)}
</article>"""


def direction_index(snapshot: Snapshot) -> str:
    docs = snapshot.documents.value
    vision = [d for d in docs if d.kind == "vision"]
    contracts = [d for d in docs if d.kind == "contract"]
    proposals = snapshot.proposals.value

    parts = [
        '<div class="section"><h2>Direction</h2>'
        "<p>Where this project is going, and the promises it must keep. "
        "The same words a colleague reads are the words every session obeys.</p></div>"
    ]
    if vision:
        parts.append("".join(_document_row(d, snapshot) for d in vision))
    if contracts:
        parts.append('<div class="section"><h2>The promises</h2></div>')
        parts.append('<div class="rows two">' + "".join(_document_row(d, snapshot) for d in contracts) + "</div>")
    if not docs:
        parts.append(f'<article class="card"><p>{esc(snapshot.documents.note)}</p></article>')

    parts.append('<div class="section" id="proposals"><h2>Proposals waiting on you</h2>'
                 "<p>A change proposed here and a teammate's pull request are read the same way: "
                 "what changes, the evidence for it, what does not change.</p></div>")
    if snapshot.proposals.note:
        parts.append(f'<div class="honest">{esc(snapshot.proposals.note)}</div>')
    if proposals:
        parts.append("".join(_proposal_row(p) for p in proposals))
    else:
        parts.append('<article class="card"><p>No change is waiting on your word.</p></article>')
    return "\n".join(parts)


def _proposal_row(proposal: Proposal) -> str:
    flag = (
        ""
        if proposal.complete
        else '<p class="muted" style="margin-top:6px">Arrived incomplete — it is missing '
        + esc(", ".join(proposal.missing))
        + ".</p>"
    )
    return f"""<article class="card">
  <h3><a href="/direction/proposal?key={esc(proposal.key)}">{quoted(proposal.title)}</a></h3>
  <p class="muted" style="margin-top:6px">Changes {quoted(proposal.target)} — {esc(proposal.origin_detail)}.</p>
  {flag}
  {_where_fold(proposal)}
</article>"""


def _where_fold(proposal: Proposal) -> str:
    """Where the proposal is kept — a path or a link, so behind the fold."""
    if not proposal.where:
        return ""
    return (
        "<details><summary>Details</summary>"
        f'<div class="inner"><p>{esc(proposal.where)}</p></div></details>'
    )


def _what_changed_card(doc: Document, changed: WhatChanged) -> str:
    if not changed.seen_before:
        return f"""<article class="card">
  <span class="lbl">What changed since you last read this</span>
  <p class="muted" style="margin-top:8px">{esc(changed.summary)}</p>
  <form method="post" action="/direction/{esc(doc.slug)}/mark-read" class="words">
    <button class="word" type="submit">I have read this</button>
  </form>
</article>"""

    if changed.unchanged:
        return f"""<article class="card">
  <span class="lbl">What changed since you last read this</span>
  <p class="muted" style="margin-top:8px">{esc(changed.summary)}</p>
</article>"""

    # Every sentence here is the document's own, added or taken away. They are
    # marked as quoted for the same reason the document itself is: their
    # wording is documents.v1's business, not this page's.
    added = "".join(f'<li class="added">{esc(s)}</li>' for s in changed.added[:40])
    removed = "".join(f'<li class="removed">{esc(s)}</li>' for s in changed.removed[:40])
    return f"""<article class="card">
  <span class="lbl">What changed since you last read this</span>
  <p class="muted" style="margin-top:8px">{esc(changed.summary)}</p>
  <ul class="diff doc">{removed}{added}</ul>
  <form method="post" action="/direction/{esc(doc.slug)}/mark-read" class="words">
    <button class="word" type="submit">I have read this</button>
  </form>
</article>"""


def _lock_card(doc: Document, repo) -> str:
    if doc.locked:
        return """<article class="card">
  <span class="lbl">Locked</span>
  <p class="muted" style="margin-top:8px">This is locked. Nothing edits it in place — not a person,
  not a session. It changes only by a written proposal backed by evidence.</p>
</article>"""

    rows = []
    for text, ok, why in lock_conditions(doc, repo):
        met, not_yet = GATE_WORDS
        state = (
            f'<span class="state green">{esc(met)}</span>'
            if ok
            else f'<span class="state not-yet">{esc(not_yet)}</span>'
        )
        rows.append(f"<li>{state}<span>{esc(text)}<br><span class='muted'>{esc(why)}</span></span></li>")
    ready = lock_is_available(doc, repo)
    button = (
        f'<button class="word is-primary" type="submit" name="word" value="ratified">Lock it</button>'
        if ready
        else '<button class="word" type="submit" disabled>Lock it</button>'
    )
    note = (
        "All four are green. Locking it is your call, and it is recorded."
        if ready
        else "The control stays off until all four are green. The page never locks anything on its own."
    )
    return f"""<article class="card">
  <span class="lbl">Locking</span>
  <ul class="gate">{''.join(rows)}</ul>
  <form method="post" action="/do/answer-with-a-word" class="words">
    <input type="hidden" name="subject" value="Lock {esc(doc.title)}">
    <input type="hidden" name="note" value="Locked from the companion page — all four conditions green.">
    <input type="hidden" name="back" value="/direction/{esc(doc.slug)}">
    {button}
  </form>
  <p class="gate-note">{esc(note)}</p>
</article>"""


def _answer_document_card(doc: Document) -> str:
    return f"""<article class="card">
  <span class="lbl">Answer with a word</span>
  <p class="muted" style="margin-top:8px">Your word is recorded in the dated ratification record,
  and it is the word every session afterwards obeys.</p>
  <form method="post" action="/do/answer-with-a-word">
    <input type="hidden" name="subject" value="{esc(doc.title)}">
    <input type="hidden" name="back" value="/direction/{esc(doc.slug)}">
    <div class="field"><label for="note-{esc(doc.slug)}">In your words, if you want to say more</label>
      <textarea id="note-{esc(doc.slug)}" name="note" placeholder="Any edits you want first, or why you are declining."></textarea></div>
    <div class="words">
      <button class="word is-primary" type="submit" name="word" value="ratified">ratified</button>
      <button class="word" type="submit" name="word" value="ratified with edits">ratified with edits</button>
      <button class="word" type="submit" name="word" value="declined">declined</button>
      <button class="word" type="submit" name="word" value="later">later</button>
    </div>
  </form>
</article>"""


def direction_document(snapshot: Snapshot, doc: Document, changed: WhatChanged) -> str:
    body = document_html(doc.text, ask_href=f"/direction/{doc.slug}/ask?anchor={{anchor}}")
    return f"""<p class="muted"><a href="/direction">← Direction</a></p>
<div class="section"><h2>{quoted(doc.title)}</h2><p>{_document_chip(doc)}</p>
{_kept_line(doc, snapshot)}
<details><summary>Details</summary><div class="inner"><p>{esc(doc.relpath)}</p></div></details></div>
{_what_changed_card(doc, changed)}
{_answer_document_card(doc)}
{_lock_card(doc, snapshot.repo)}
<article class="card doc">{body}</article>"""


def ask_a_question(doc: Document, anchor: str, paragraph: str) -> str:
    return f"""<p class="muted"><a href="/direction/{esc(doc.slug)}#{esc(anchor)}">← {quoted(doc.title)}</a></p>
<div class="section"><h2>Ask about this paragraph</h2>
<p>Your question goes to the manager session as feedback, attached to this paragraph.
It is not filed as work — the manager session reads it against the contracts and decides what it is.</p></div>
<article class="card">
  <blockquote class="muted" style="border-left:3px solid var(--rule);padding-left:12px">{quoted_markup(inline(paragraph))}</blockquote>
  <form method="post" action="/do/drop-feedback" style="margin-top:16px">
    <input type="hidden" name="looking_at" value="{esc(doc.relpath)} — paragraph {esc(anchor)}: {esc(paragraph[:300])}">
    <input type="hidden" name="back" value="/direction/{esc(doc.slug)}">
    <div class="field"><label for="q">Your question</label>
      <textarea id="q" name="text" placeholder="What is unclear, or what would you change?"></textarea></div>
    <div class="words"><button class="word is-primary" type="submit">Send it</button></div>
  </form>
</article>"""


def proposal_page(snapshot: Snapshot, proposal: Proposal) -> str:
    def part(label: str, body: str, empty: str) -> str:
        return f"""<article class="card">
  <span class="lbl">{esc(label)}</span>
  <div class="doc" style="margin-top:10px">{document_html(body, heading_shift=2) if body.strip() else f'<p class="muted">{esc(empty)}</p>'}</div>
</article>"""

    link = (
        f'<p class="muted" style="margin-top:6px"><a href="{esc(proposal.url)}">Open it where it came from</a></p>'
        if proposal.url
        else ""
    )
    return f"""<p class="muted"><a href="/direction#proposals">← Direction</a></p>
<div class="section"><h2>{quoted(proposal.title)}</h2>
<p>Changes {quoted(proposal.target)} — {esc(proposal.origin_detail)}. The original stands until you ratify this.</p>{link}
{_where_fold(proposal)}</div>
{part("The exact change", proposal.change, "This proposal does not say what it changes. That alone is reason to decline it.")}
{part("The evidence", proposal.evidence, "No evidence is given — no cost paid, no failure caught. A preference is not evidence.")}
{part("What does not change", proposal.not_change, "It does not say what stays the same, so the blast radius is unknown.")}
<article class="card">
  <span class="lbl">Answer with a word</span>
  <form method="post" action="/do/answer-with-a-word">
    <input type="hidden" name="subject" value="Proposal: {esc(proposal.title)}">
    <input type="hidden" name="back" value="/direction/proposal?key={esc(proposal.key)}">
    <div class="field"><label for="pn">In your words, if you want to say more</label>
      <textarea id="pn" name="note"></textarea></div>
    <div class="words">
      <button class="word is-primary" type="submit" name="word" value="ratified">ratified</button>
      <button class="word" type="submit" name="word" value="ratified with edits">ratified with edits</button>
      <button class="word" type="submit" name="word" value="declined">declined</button>
      <button class="word" type="submit" name="word" value="later">later</button>
    </div>
  </form>
</article>
<article class="card">
  <span class="lbl">Or hand it to the manager session</span>
  <p class="muted" style="margin-top:8px">It checks the proposal against the protocol and comes back with a recommendation.</p>
  <form method="post" action="/do/steer" class="words">
    <input type="hidden" name="ask" value="review this proposal">
    <input type="hidden" name="about" value="{esc(proposal.title)}">
    <input type="hidden" name="back" value="/direction/proposal?key={esc(proposal.key)}">
    <button class="word" type="submit">Have the manager session review this</button>
  </form>
</article>"""


# --------------------------------------------------------------------------
# Operation
# --------------------------------------------------------------------------


def _gauge_card(board: Reading[Board], truly_ready: int, ready_known: bool) -> str:
    if not board.available:
        return f"""<article class="card" id="lanes">
  <span class="lbl">Lanes</span>
  <p class="muted" style="margin-top:8px">{esc(board.note)}</p>
</article>"""

    value = board.value
    pips = ""
    if value.width_target:
        pips = '<div class="pips">' + "".join(
            f'<span class="pip{" on" if i < value.running else ""}"></span>'
            for i in range(max(value.width_target, value.running))
        ) + "</div>"

    if value.short_by:
        ready_line = (
            f"{truly_ready} piece{'s' if truly_ready != 1 else ''} of work need nothing from you."
            if ready_known
            else "The work queue cannot be read, so we cannot say what is waiting to start."
        )
        fill = f"""<p class="muted" style="margin-top:10px">{esc(ready_line)}</p>
<form method="post" action="/do/steer" class="words">
  <input type="hidden" name="ask" value="fill the lanes">
  <input type="hidden" name="back" value="/operation">
  <button class="word is-primary" type="submit">Fill the lanes</button>
</form>"""
    else:
        fill = '<p class="muted" style="margin-top:10px">Every lane you asked for is carrying work.</p>'

    return f"""<article class="card" id="lanes">
  <span class="lbl">Lanes</span>
  <div class="gauge" style="margin-top:6px"><span class="big">{esc(value.gauge)}</span></div>
  {pips}
  {fill}
</article>"""


def _lane_card(lane: Lane) -> str:
    mark = {
        "Working": "good",
        "Done": "good",
        "Stuck": "bad",
        "Silent — may have died": "bad",
        "Can't check": "",
    }.get(lane.liveness, "warn")
    # A badge's label is the page's word for the evidence; the detail beside
    # it is what the lane or the code record actually said, so it is quoted.
    badges = "".join(
        f'<span class="badge">{esc(e.label)}: {quoted(e.detail)}</span>' for e in lane.evidence
    )
    # The lane's own note. Nothing here is a worker session's account of
    # itself — so when the page shows one, it shows it as a quotation.
    summary = f'<p class="why">{quoted(lane.summary)}</p>' if lane.summary else ""
    return f"""<article class="card" id="lane-{esc(lane.name)}">
  <div class="step">
    <div class="body">
      <h3>{quoted(lane.name)}</h3>
      <p class="muted" style="margin-top:4px"><span class="mark {mark}">{esc(lane.liveness)}</span></p>
      {summary}
      <div class="evidence">{badges}</div>
    </div>
  </div>
  <details>
    <summary>Details</summary>
    <div class="inner">
      <p>branch {esc(lane.branch or "—")}</p>
      <p>worktree {esc(lane.worktree or "—")}</p>
      <p>log {esc(lane.log_path or "—")}</p>
      <p>launched {esc(lane.launched_at or "—")}</p>
    </div>
  </details>
</article>"""


def _plan_card(steps: list[PlanStep], items: Reading[list[WorkItem]], project: str) -> str:
    if not items.available:
        return f"""<article class="card">
  <span class="lbl">What is planned next</span>
  <p class="muted" style="margin-top:8px">{esc(items.note)}</p>
</article>"""
    if not steps:
        return """<article class="card">
  <span class="lbl">What is planned next</span>
  <p class="muted" style="margin-top:8px">Nothing is queued. The work queue answered, and it is empty.</p>
</article>"""

    rows = []
    for step in steps:
        rows.append(f"""<div class="step" style="margin-top:16px">
  <span class="n">{step.position}</span>
  <div class="body">
    <p><strong>{quoted(step.title)}</strong></p>
    <p class="why">{esc(step.why)}</p>
    <form method="post" action="/do/signal-priority" class="words" style="margin-top:8px">
      <input type="hidden" name="item_id" value="{esc(step.id)}">
      <input type="hidden" name="back" value="/operation">
      <button class="word" type="submit" name="direction" value="sooner">sooner</button>
      <button class="word" type="submit" name="direction" value="later">later</button>
    </form>
  </div>
</div>""")
    return f"""<article class="card">
  <span class="lbl">What is planned next, and why</span>
  <p class="muted" style="margin-top:6px">The strategy is to keep as much moving without you as possible.
  Anything parked on your word is set aside; it never holds up the rest.</p>
  {''.join(rows)}
</article>"""


def _ready_card(snapshot: Snapshot) -> str:
    if not snapshot.items.available:
        return ""
    ready = snapshot.truly_ready
    waiting = snapshot.waiting_on_you
    def listing(items: list[WorkItem]) -> str:
        if not items:
            return '<p class="muted">None.</p>'
        return "".join(f'<p class="why">{quoted(i.title)}</p>' for i in items[:6])
    return f"""<div class="rows two">
  <article class="card">
    <span class="lbl">Truly ready — needs nothing from you</span>
    <p class="gauge" style="margin-top:6px"><span class="big">{len(ready)}</span></p>
    {listing(ready)}
  </article>
  <article class="card">
    <span class="lbl">Waiting on you</span>
    <p class="gauge" style="margin-top:6px"><span class="big">{len(waiting)}</span></p>
    {listing(waiting)}
  </article>
</div>"""


def _constraints_card(snapshot: Snapshot) -> str:
    c = snapshot.constraints.value
    note = (
        f'<p class="muted" style="margin-top:8px">{esc(snapshot.constraints.note)}</p>'
        if snapshot.constraints.note
        else ""
    )
    return f"""<article class="card" id="limits">
  <span class="lbl">Your limits</span>
  {note}
  <form method="post" action="/do/steer" style="margin-top:12px">
    <input type="hidden" name="back" value="/operation">
    <div class="field"><label for="objective">Today's objective</label>
      <input type="text" id="objective" name="objective" value="{esc(c.objective)}" placeholder="What today is for, in one line."></div>
    <div class="field"><label for="budget">Budget</label>
      <select id="budget" name="budget">
        <option value="until done"{' selected' if c.budget in ("", "until done") else ''}>until done</option>
        <option value="until a time"{' selected' if c.budget == "until a time" else ''}>until a time</option>
        <option value="until a spend"{' selected' if c.budget == "until a spend" else ''}>until a spend</option>
      </select></div>
    <div class="field"><label for="lane_width">How many lanes to run</label>
      <input type="text" id="lane_width" name="lane_width" value="{esc(c.lane_width)}" placeholder="A whole number."></div>
    <div class="words"><button class="word is-primary" type="submit">Set them</button></div>
  </form>
  <p class="gate-note">Stopping something is never a button here. A stop is a decision, and it arrives
  on the short list with its reasons.</p>
</article>"""


def _feedback_card() -> str:
    return """<article class="card" id="feedback">
  <span class="lbl">Drop feedback</span>
  <p class="muted" style="margin-top:8px">Just say what you saw. The manager session works out whether it is
  a bug, a change of plan, or a decision for you — it is never filed as work straight from here.</p>
  <form method="post" action="/do/drop-feedback" enctype="multipart/form-data" style="margin-top:12px">
    <input type="hidden" name="back" value="/operation">
    <div class="field"><label for="fb">What you saw</label>
      <textarea id="fb" name="text" placeholder="Still not working on my phone — the list is empty."></textarea></div>
    <div class="field"><label for="fbw">What you were looking at, if it helps</label>
      <input type="text" id="fbw" name="looking_at" placeholder="The settings page, on the build from this morning."></div>
    <div class="field"><label for="fbi">A picture, if you have one</label>
      <input type="file" id="fbi" name="picture" accept="image/*"></div>
    <div class="words"><button class="word is-primary" type="submit">Drop it</button></div>
  </form>
</article>"""


def _managers_card(managers: Reading[list[QueueSummary]], current: str) -> str:
    if not managers.available:
        return f"""<article class="card" id="managers">
  <span class="lbl">Every manager session you run</span>
  <p class="muted" style="margin-top:8px">{esc(managers.note)}</p>
</article>"""

    rows = []
    for summary in managers.value:
        here = " — this one" if summary.project == current else ""
        rows.append(
            f'<p class="why"><strong>{quoted(summary.project)}</strong>{esc(here)}: '
            f"{summary.ready} truly ready, {summary.held} being worked, {summary.resolved_24h} finished today.</p>"
        )
    note = f'<p class="muted" style="margin-top:6px">{esc(managers.note)}</p>' if managers.note else ""
    return f"""<article class="card" id="managers">
  <span class="lbl">Every manager session you run</span>
  {note}
  <div style="margin-top:10px">{''.join(rows) or '<p class="muted">None found.</p>'}</div>
  <form method="post" action="/do/drop-feedback" style="margin-top:14px">
    <input type="hidden" name="looking_at" value="Sent to every manager session.">
    <input type="hidden" name="back" value="/operation">
    <div class="field"><label for="tellall">Tell them all one thing</label>
      <input type="text" id="tellall" name="text" placeholder="The staging box is down — stop testing against it."></div>
    <div class="words"><button class="word" type="submit">Tell all</button></div>
  </form>
</article>"""


def operation(
    snapshot: Snapshot,
    brief_lines: list[str],
    steps: list[PlanStep],
    managers: Reading[list[QueueSummary]],
) -> str:
    board = snapshot.board
    lanes = "".join(_lane_card(lane) for lane in board.value.lanes) if board.available else ""
    return f"""<div class="section"><h2>Operation</h2>
<p>The manager session at work, and what it needs from you.</p></div>
<article class="card stack">
  <span class="lbl">Since you were last here</span>
  {''.join(f'<p>{esc(line)}</p>' for line in brief_lines)}
</article>
{_gauge_card(board, len(snapshot.truly_ready), snapshot.items.available)}
{_ready_card(snapshot)}
{_plan_card(steps, snapshot.items, snapshot.project)}
<div class="section"><h2>The lanes, one by one</h2>
<p>State in words, and the evidence behind it. Nothing here is a worker session's account of itself.</p></div>
{lanes or ''}
{_constraints_card(snapshot)}
{_feedback_card()}
{_managers_card(managers, snapshot.project)}
<article class="card">
  <span class="lbl">The four things you can do here</span>
  <div style="margin-top:10px">
  {''.join(f'<p class="why"><strong>{esc(w.label)}</strong></p>' for w in WRITES)}
  </div>
  <p class="gate-note">Everything else on this page is read. Whichever of the four you use,
  the manager session can do the same thing the same way.</p>
  <details>
    <summary>Details</summary>
    <div class="inner">
    {''.join(f'<p>{esc(w.name)} → {esc(w.lands_in)} — manager operation {esc(w.manager_operation)}</p>' for w in WRITES)}
    </div>
  </details>
</article>"""
