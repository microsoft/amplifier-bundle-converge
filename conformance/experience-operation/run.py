# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""experience-operation.v1 conformance kit — "Operation keeps its promises".

Point it at the companion app — the running server, or a snapshot captured from
it — and it asserts `contracts/experience-operation.v1.md` against what the app
actually serves: the shell it renders into, the operation payload it answers
with, the client it ships, and its own route table at `/openapi.json`.

    uv run conformance/experience-operation/run.py http://127.0.0.1:8788
    uv run conformance/experience-operation/run.py <a --capture directory>

Stdlib only, and **no browser is launched**.

Numbering
---------
Rule ids anchor to the contract's **Core clause** numbers, as `documents.v1`
clause 5 asks: rule 7 judges Core 7. Where one clause carries several
independent promises the kit emits one row per promise, lettered inside the
clause (`2a`, `2b`, `5a`, `5b`). Every one of the thirteen Core clauses has a
row, and `test_every_core_clause_has_a_row` fails if one does not.

What a static read buys, and what it does not
---------------------------------------------
Operation is a reading surface, so most of its promises are about **what is
shown and in what order** — which is exactly what a served shell plus a real
payload can settle: whether the objective stands above the work, whether a wave
carries a reason or only a list, whether a lane's state word is one the contract
allows, whether two numbers are shown where the clause asks for two.

It cannot judge a rendered layout, and it cannot prove what a write records once
it lands. Rules leaning on either say so in their own detail.

Two lists of lanes, and both are judged
---------------------------------------
The payload carries lanes in two: ``lanes`` (still at work, read in the lane
words *Working · Quiet · Silent — may have died*) and ``reported`` (already come
back, read in the work words *Done · Stuck*). The split is legitimate — it is
what lets Core 8 be kept without stretching a three-word vocabulary over a state
it has no word for.

What was not legitimate is that until 2026-09-04 rules 8 and 9 read only
``lanes``. A reported lane could carry any word at all, or no evidence, and this
kit still said PASS. **A list nobody judges is a place to hide a lane**, so both
rules now read both lists, and rule 8 additionally faults a lane id appearing in
BOTH — the other way the split could be used to dodge a check.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from kitreport import Kit, run_cli  # noqa: E402

CONTRACT = "contracts/experience-operation.v1.md"

KIT = Kit(
    "experience-operation.v1",
    CONTRACT,
    rules=[
        ("1", 1, "objective_limits_strategy_stand_at_the_top",
         "the objective, the limits, and today's strategy stand above any list of work"),
        ("2a", 2, "waves_with_lanes_inside_them",
         "the plan is shown in waves, with the lanes inside them"),
        ("2b", 2, "every_grouping_carries_its_reason",
         "every grouping carries its reason, and a redrawn plan shows why"),
        ("3", 3, "the_return_brief_carries_all_five_parts",
         "the return brief is read first and carries all five of its parts"),
        ("4", 4, "each_turn_opens_onto_its_evidence",
         "every entry on the confidence timeline opens onto its evidence"),
        ("5a", 5, "the_flow_measures_are_shown",
         "work derived, resolved, verified, reopened and stuck are shown"),
        ("5b", 5, "flow_and_outcome_are_shown_apart",
         "flow is never offered as outcome — the two readings are shown apart"),
        ("6", 6, "lanes_running_against_lanes_intended",
         "lanes running, lanes intended, and the fill control appear together"),
        ("7", 7, "truly_ready_against_waiting_on_you",
         "work truly ready is shown against work waiting on you, as two numbers"),
        ("8", 8, "every_lane_speaks_a_plain_lane_word",
         "every lane \u2014 at work, or reported back \u2014 carries its plain state word and "
         "evidence you can open"),
        ("9", 9, "watch_session_reaches_the_worker",
         "Watch session opens that worker session's live view, on every lane offered one"),
        ("10", 10, "feedback_in_whatever_form_is_to_hand",
         "feedback can be dropped in seconds, in every form this body claims"),
        ("11", 11, "steering_sets_limits_and_assigns_nothing",
         "steering offers exactly the five limits and no way to assign work"),
        ("12", 12, "stopping_is_never_a_board_button",
         "no control on the board stops work by moving it"),
        ("13", 13, "every_manager_listed_and_tell_all",
         "every manager session is listed, sorted by which needs you, and one message reaches all"),
    ],
)

#: Core 8 / experience.v1 Core 6 — the only words a LANE AT WORK may be shown
#: in. All three answer one question: is this lane still doing anything?
LANE_WORDS = ("working", "quiet", "silent")

#: experience.v1 Core 6 — the WORK words a lane that has already REPORTED BACK
#: may be shown in. Such a lane is no longer answering the lane question at all,
#: so the app carries it in its own list (`reported`) rather than stretching a
#: three-word vocabulary over a state it has no word for. That split is
#: legitimate; what is not is a list nobody judges, which is what `reported` was
#: until 2026-09-04 (work item converge-0w2). Judging one list and not the other
#: makes the split a place to hide a lane, so rule 8 reads both.
WORK_WORDS = ("done", "stuck")

#: Core 3 — the five parts of the return brief.
BRIEF_PARTS = (
    ("time away", re.compile(r"\b(\d+\s*(m|min|h|hour|d|day)|just now|ago|away)\b", re.I)),
    ("what finished", re.compile(r"\b(finish|finished|landed|merged|resolved|complete)", re.I)),
    ("what is stuck", re.compile(r"\b(stuck|blocked|could not|failed|cannot)", re.I)),
    ("what needs your word", re.compile(r"\b(needs? your word|your word|decision|ratif|waiting on you)", re.I)),
    ("what quietly changed", re.compile(r"\b(changed|quietly|now|updated|replaced|deleted)", re.I)),
)

#: Core 5 — the five flow measures, in the clause's own words.
FLOW_MEASURES = ("derived", "resolved", "verified", "reopened", "stuck")

#: Core 11 — the five limits steering may set, and nothing else.
STEER_LIMITS = (
    ("objective", re.compile(r"steerObjective|\bobjective\b", re.I)),
    ("budget", re.compile(r"\bbudget\b|\bdeadline\b|\bspend\b|until done", re.I)),
    ("lane count", re.compile(r"steerLanes|maximum lanes|lane (count|width)", re.I)),
    ("fill the lanes", re.compile(r"fillLanes|fill the lanes|fill lanes", re.I)),
    ("have the manager review this", re.compile(r"review this|ask.{0,12}review|managerReview", re.I)),
)

#: Core 11 — a control that hands a specific piece of work to a specific lane.
ASSIGNS_WORK = re.compile(r"assign(ed|ment)?\s*(to)?\s*(lane|worker|session)|data-assign", re.I)

#: Core 12 — "Stopping something is never a board button."
STOP_WORDS = re.compile(r"\b(stop|kill|abort|terminate|halt)\b", re.I)


# --------------------------------------------------------------------------- #
# reading the client the app ships                                             #
# --------------------------------------------------------------------------- #
def write_tokens(snapshot):
    tokens = set()
    for path in snapshot.write_routes():
        tail = [p for p in path.strip("/").split("/") if not p.startswith("{")]
        if tail:
            tokens.add(tail[-1])
    return tokens


def strip_string_literals(code: str) -> str:
    """Blank out '…', "…" and `…` so a WORD in a message cannot pass for a call."""
    return re.sub(r"'[^'\n]*'|\"[^\"\n]*\"|`[^`]*`", "''", code, flags=re.S)


def _brace_block(script: str, at: int, window: int) -> str:
    start = script.find("{", at)
    if start < 0:
        return script[at:at + window]
    depth, i = 0, start
    while i < len(script) and i - start < window * 4:
        if script[i] == "{":
            depth += 1
        elif script[i] == "}":
            depth -= 1
            if depth == 0:
                return script[start:i + 1]
        i += 1
    return script[start:start + window]


def function_body(script: str, name: str, window: int = 1400) -> str:
    """The body of the named function — never its mention in an import list.

    Reading `script.find("fillLanes")` lands on `import { … fillLanes … }` at
    the top of main.js and returns whatever brace follows, which is not the
    function at all. Measured: that read reported the fill control reaching no
    write, when `fillLanes` calls `api.steer` two lines down in actions.js.
    """
    m = re.search(rf"function\s+{re.escape(name)}\s*\(", script)
    return _brace_block(script, m.start(), window) if m else ""


def handler_body(script: str, marker: str, window: int = 900) -> str:
    at = script.find(marker)
    if at < 0:
        return ""
    return _brace_block(script, at, window)


def reaches_a_write(body: str, tokens) -> bool:
    if not body:
        return False
    if re.search(r"method:\s*['\"]POST['\"]", body, re.I):
        return True
    code = strip_string_literals(body)
    return any(re.search(rf"\w*{re.escape(t)}\w*\s*\(", code, re.I) for t in tokens)


def served(snapshot) -> str:
    return snapshot.text("/") + "\n" + snapshot.script_text()


def present(snapshot, *patterns) -> bool:
    hay = served(snapshot)
    return any(re.search(p, hay, re.I) for p in patterns)


def dom_order(snapshot, *ids):
    """Where each id sits in the served shell, in document order."""
    text = snapshot.text("/")
    return {i: text.find(f'id="{i}"') for i in ids}


# --------------------------------------------------------------------------- #
# rules                                                                        #
# --------------------------------------------------------------------------- #
def check_objective_stands_at_the_top(snapshot):
    manager = snapshot.manager()
    if not manager:
        return KIT.bad("1", "the app served no manager payload, so nothing states the objective")
    said = {
        "the objective": (manager.get("objective") or "").strip(),
        "the limits": " ".join(str(manager.get(k) or "") for k in
                               ("deadline", "lanesMax")).strip(),
        "today's strategy": " ".join(str(manager.get(k) or "") for k in
                                     ("strategy", "strategyNarrative")).strip(),
    }
    silent = [k for k, v in said.items() if not v]
    order = dom_order(snapshot, "opObjectiveText", "strategyHeadline",
                      "wavesGrid", "lanesGrid")
    missing_el = [k for k, v in order.items() if v < 0]
    problems = []
    if silent:
        problems.append("the manager session says nothing for " + ", ".join(silent))
    if missing_el:
        problems.append(f"the shell has no {missing_el}")
    elif not (order["opObjectiveText"] < order["wavesGrid"]
              and order["strategyHeadline"] < order["lanesGrid"]):
        problems.append("the objective and strategy do not stand above the lists of work")
    if problems:
        return KIT.bad("1", "; ".join(problems), said={k: v[:60] for k, v in said.items()})
    return KIT.ok("1",
                  "objective, limits and strategy are all stated in the manager session's own "
                  "words and stand above the waves and the lanes",
                  said={k: v[:80] for k, v in said.items()})


def check_waves_with_lanes(snapshot):
    op = snapshot.operation()
    if not op:
        return KIT.bad("2a", "the app served no operation payload, so there is no plan to read")
    waves = op.get("waves") or []
    lanes = op.get("lanes") or []
    if not waves:
        return KIT.bad("2a", "the plan carries no waves")
    empty = [w.get("label") or w.get("id") for w in waves if not (w.get("items") or [])]
    orphan = [l.get("id") for l in lanes if not (l.get("wave") or "").strip()]
    problems = []
    if empty:
        problems.append(f"waves with no lanes inside them: {empty[:5]}")
    if orphan:
        problems.append(f"{len(orphan)} lane(s) sit in no wave: {orphan[:5]}")
    if problems:
        return KIT.bad("2a", "; ".join(problems), waves=len(waves), lanes=len(lanes))
    return KIT.ok("2a", f"{len(waves)} wave(s), each with the lanes inside it; "
                        f"all {len(lanes)} lane(s) name their wave",
                  waves=len(waves), lanes=len(lanes))


def check_every_grouping_carries_its_reason(snapshot):
    op = snapshot.operation()
    if not op:
        return KIT.bad("2b", "the app served no operation payload")
    waves = op.get("waves") or []
    reasonless = []
    for w in waves:
        # A reason is a sentence saying what the batch is FOR. A title that is
        # only the lane names repeated is a list, not a reason.
        reason = str(w.get("reason") or w.get("why") or w.get("purpose") or "").strip()
        title = str(w.get("title") or "")
        items = {str(i[0] if isinstance(i, (list, tuple)) else i) for i in (w.get("items") or [])}
        # A title is a LIST, not a reason, when its comma-separated parts are
        # the wave's own lane names. Two matching parts is enough: a sentence
        # saying what a batch is for does not read as its members' names.
        parts = [s.strip() for s in title.split(",") if s.strip()]
        looks_like_a_list = len([s for s in parts if s in items]) >= 2 or (
            len(parts) == 1 and parts[0] in items)
        if not reason and (not title or looks_like_a_list):
            reasonless.append(w.get("label") or w.get("id"))
    redraw = present(snapshot, r"redraw|replan|re-?planned|why the plan changed")
    problems = []
    if reasonless:
        problems.append(
            f"{len(reasonless)} of {len(waves)} waves carry no reason — only their lane "
            f"names ({reasonless[:5]})")
    if not redraw:
        problems.append("nothing shows why the plan was redrawn when it is")
    if problems:
        return KIT.bad("2b", "; ".join(problems), waves=len(waves))
    return KIT.ok("2b", f"all {len(waves)} waves carry a reason, and a redraw shows why",
                  waves=len(waves))


def check_return_brief(snapshot):
    op = snapshot.operation()
    if not op:
        return KIT.bad("3", "the app served no operation payload, so there is no brief")
    brief = op.get("returnBrief") or []
    if not brief:
        return KIT.bad("3", "the return brief is empty — a returning steward reads nothing")
    manager = snapshot.manager() or {}
    text = " ".join(str(s) for s in brief) + " " + str(manager.get("age") or "")
    missing = [name for name, rx in BRIEF_PARTS if not rx.search(text)]
    order = dom_order(snapshot, "returnBrief", "wavesGrid", "lanesGrid")
    problems = []
    if missing:
        problems.append("the brief never says " + ", never says ".join(missing))
    if order["returnBrief"] < 0:
        problems.append("the shell has no place for the brief")
    elif order["wavesGrid"] > 0 and order["returnBrief"] > order["lanesGrid"] > 0:
        problems.append("the brief sits below the lists of work, so it is not the first "
                        "thing read")
    if problems:
        return KIT.bad("3", "; ".join(problems), sentences=len(brief))
    return KIT.ok("3", f"the brief is {len(brief)} sentence(s) and carries all five parts, "
                       "above the lists of work",
                  sentences=len(brief))


def check_timeline_opens_onto_evidence(snapshot):
    op = snapshot.operation()
    if not op:
        return KIT.bad("4", "the app served no operation payload")
    timeline = op.get("timeline") or []
    if not timeline:
        return KIT.bad("4", "the confidence timeline is empty, so no turn in the narrative "
                            "can be opened at all")
    def has_evidence(entry):
        if isinstance(entry, dict):
            return bool(entry.get("evidence") or entry.get("href") or entry.get("ref"))
        return isinstance(entry, (list, tuple)) and len(entry) > 3 and bool(entry[3])
    blind = [i for i, e in enumerate(timeline) if not has_evidence(e)]
    if blind:
        return KIT.bad(
            "4",
            f"{len(blind)} of {len(timeline)} timeline entries carry nothing to open — they "
            "state that confidence moved and give the reader no way to inspect why",
            entries=len(timeline), without_evidence=len(blind),
            shape=str(timeline[0])[:160])
    return KIT.ok("4", f"all {len(timeline)} timeline entries open onto their evidence",
                  entries=len(timeline))


def check_flow_measures(snapshot):
    op = snapshot.operation()
    if not op:
        return KIT.bad("5a", "the app served no operation payload")
    flow = op.get("throughput") or {}
    shown = [m for m in FLOW_MEASURES
             if m in flow or re.search(rf"throughput{m}", served(snapshot), re.I)]
    missing = [m for m in FLOW_MEASURES if m not in shown]
    if missing:
        return KIT.bad("5a",
                       f"the flow reading shows {shown} and never says " + ", ".join(missing)
                       + " — the clause names all five as what says whether things are moving",
                       shown=shown, missing=missing)
    return KIT.ok("5a", "all five flow measures are shown: " + ", ".join(shown), shown=shown)


def check_flow_and_outcome_apart(snapshot):
    op = snapshot.operation()
    if not op:
        return KIT.bad("5b", "the app served no operation payload")
    flow_card = present(snapshot, r"throughput-card|Flow today")
    outcome_card = present(snapshot, r"confidence-card|Reality vs direction|Contract confidence")
    if not flow_card or not outcome_card:
        return KIT.bad("5b",
                       f"flow shown: {flow_card}; the outcome reading shown: {outcome_card} — "
                       "the clause asks for both, apart",
                       flow=flow_card, outcome=outcome_card)
    # The failure the clause guards against is one number standing for both.
    summed = re.search(r"(kept|conf\w*)\s*[+]\s*(resolved|derived|verified)"
                       r"|(resolved|derived|verified)\s*[+]\s*(kept|conf\w*)",
                       snapshot.script_text(), re.I)
    if summed:
        return KIT.bad("5b", "a single measure sums flow with the outcome reading: "
                             f"{summed.group(0)!r}")
    return KIT.ok("5b", "flow and the outcome reading are two separate readings, never summed "
                        "into one number")


def check_lanes_running_against_intended(snapshot):
    manager = snapshot.manager() or {}
    order = dom_order(snapshot, "activeLaneCount", "laneBudgetCount", "fillLanesButton")
    absent = [k for k, v in order.items() if v < 0]
    problems = []
    if absent:
        problems.append(f"the shell has no {absent}")
    if manager.get("lanesActive") is None or manager.get("lanesMax") is None:
        problems.append("the manager payload does not carry both lanes running and lanes intended")
    body = function_body(snapshot.script_text(), "fillLanes")
    if not reaches_a_write(body, write_tokens(snapshot)):
        problems.append("the fill control reaches no write the app declares, so filling "
                        "cannot update the ratio or the plan")
    if problems:
        return KIT.bad("6", "; ".join(problems))
    return KIT.ok("6",
                  f"{manager.get('lanesActive')} running of {manager.get('lanesMax')} intended, "
                  "with the fill control beside them, and filling reaches a write",
                  running=manager.get("lanesActive"), intended=manager.get("lanesMax"))


def check_truly_ready_against_waiting(snapshot):
    hay = served(snapshot)
    ready = re.search(r"truly[\s-]?ready|readyCount|trulyReady", hay, re.I)
    waiting = re.search(r"waiting on you|needsYouCount|need your word", hay, re.I)
    if ready and waiting:
        return KIT.ok("7", "both numbers are shown — work truly ready, and work waiting on you")
    shown = [n for n, m in (("truly ready", ready), ("waiting on you", waiting)) if m]
    return KIT.bad(
        "7",
        f"only {shown or 'neither'} is shown; the clause asks for two numbers, and the "
        "second — the steward's own backlog — is what keeps the operation from stalling "
        "politely behind a person",
        shown=shown)


def field_shown_for_lanes(script: str) -> str:
    """Which field the surface actually SHOWS as a lane-at-work's state word."""
    return "statusLabel" if re.search(r"lane-status[^`]{0,80}statusLabel", script) else "status"


def field_shown_for_reported(script: str) -> str:
    """Which field the surface actually SHOWS for a lane that has reported back.

    Both lists are drawn by the same `laneCard`, so the parameter name inside it
    says nothing about which list is which. What tells them apart is what the
    REPORTED grid hands in.
    """
    passed = re.search(r"reported\w*[\s\S]{0,300}?laneCard\(([^)]*)\)", script, re.I)
    return "outcomeLabel" if passed and "outcomeLabel" in passed.group(1) else "outcome"


def words_read(rows, field) -> dict:
    seen = {}
    for row in rows:
        word = str(row.get(field) or "").strip()
        seen.setdefault(word, 0)
        seen[word] += 1
    return seen


def outside(rows, field, vocabulary) -> dict:
    """`{lane id: the word it reads}` for every row outside the vocabulary.

    Keyed by LANE, not by word, because the clause is kept or broken one lane at
    a time and the reader's next question is always "which one?".
    """
    named = {}
    for row in rows:
        word = str(row.get(field) or "").strip()
        if not any(word.lower().startswith(v) for v in vocabulary):
            named[str(row.get("id") or "?")] = word
    return named


def without_evidence(rows) -> list:
    return [str(r.get("id") or "?") for r in rows if not str(r.get("evidence") or "").strip()]


def check_lane_state_words(snapshot):
    """Core 8, over BOTH lists of lanes.

    The payload carries lanes in two: `lanes`, still at work and read in the
    lane words, and `reported`, already come back and read in the work words.
    The split is what lets the clause be kept without stretching a three-word
    vocabulary over a state it has no word for.

    Until 2026-09-04 this rule read only `lanes` (work item converge-0w2), so a
    reported lane could carry any word at all, or no evidence, and the kit still
    reported PASS. A list nobody judges is a place to hide a lane, so a lane id
    appearing in BOTH lists is faulted too: that is the other way the split
    could be used to dodge a check.
    """
    op = snapshot.operation()
    if not op:
        return KIT.bad("8", "the app served no operation payload, so no lane can be read")
    lanes = op.get("lanes") or []
    reported = op.get("reported") or []
    if not lanes and not reported:
        return KIT.bad("8", "no lane is shown at all")
    script = snapshot.script_named("render/operation.js") or snapshot.script_text()
    field = field_shown_for_lanes(script)
    reported_field = field_shown_for_reported(script)

    seen = words_read(lanes, field)
    reported_seen = words_read(reported, reported_field)
    foreign = outside(lanes, field, LANE_WORDS)
    reported_foreign = outside(reported, reported_field, WORK_WORDS)
    blind = without_evidence(lanes)
    reported_blind = without_evidence(reported)
    # A lane in both lists is read in two vocabularies at once, and is one
    # rename away from being in neither.
    in_both = sorted({str(l.get("id")) for l in lanes} & {str(r.get("id")) for r in reported})

    problems = []
    if foreign:
        problems.append(
            f"the surface shows each working lane's `{field}`, and "
            + ", ".join(f"{lane} reads {word!r}" for lane, word in sorted(foreign.items())[:6])
            + f" — outside the lane vocabulary the contract fixes ({list(LANE_WORDS)})")
    if blind:
        problems.append(f"{len(blind)} working lane(s) carry no evidence to open: {blind[:4]}")
    if reported_foreign:
        problems.append(
            f"the surface shows each reported lane's `{reported_field}`, and "
            + ", ".join(f"{lane} reads {word!r}"
                        for lane, word in sorted(reported_foreign.items())[:6])
            + f" — outside the work vocabulary a lane that has come back is read in "
              f"({list(WORK_WORDS)})")
    if reported_blind:
        problems.append(
            f"{len(reported_blind)} reported lane(s) carry no evidence to open: "
            f"{reported_blind[:4]} — a lane that has finished is exactly the one whose "
            "claim a steward wants to inspect")
    if in_both:
        problems.append(
            f"{len(in_both)} lane(s) appear in both `lanes` and `reported`: {in_both[:4]} — "
            "each list is read in a different vocabulary, so a lane in both is told in two "
            "states at once")
    if problems:
        return KIT.bad("8", "; ".join(problems),
                       words_shown=seen, field_shown=field,
                       reported_words_shown=reported_seen, reported_field_shown=reported_field,
                       lanes_faulted=sorted(foreign), reported_faulted=sorted(reported_foreign),
                       without_evidence=blind + reported_blind, in_both_lists=in_both)
    return KIT.ok("8",
                  f"every one of {len(lanes)} working lane(s) reads as a plain lane word "
                  f"({sorted(seen)}) and every one of {len(reported)} reported lane(s) reads as "
                  f"a plain work word ({sorted(reported_seen)}); all carry evidence to open, and "
                  "no lane is in both lists",
                  words_shown=seen, field_shown=field,
                  reported_words_shown=reported_seen, reported_field_shown=reported_field)


def check_watch_session(snapshot):
    """Core 9, on every lane the surface offers the control to.

    A body that also offers Watch on a lane that has REPORTED BACK — whose
    session is still alive to look at — is offering the same rung of the ladder
    a second time, and it is judged the same way: the handler must reach that
    lane's own session. Until 2026-09-04 no rule looked at it at all
    (converge-0w2). A body that does not offer it is not faulted for absence;
    the clause is about where the control goes, not how many there are.
    """
    op = snapshot.operation() or {}
    lanes = op.get("lanes") or []
    control = present(snapshot, r"data-watch-lane", r"watchLane", r"Watch session")
    if not control:
        return KIT.bad("9", "no lane offers Watch session, so the bottom rung of the ladder "
                            "cannot be reached")
    script = snapshot.script_text()
    own_session = re.compile(r"lane\.tmux|lanes\.find|consoleTarget")
    body = function_body(script, "watchLane")
    targets_own_lane = bool(own_session.search(body or ""))
    without_session = [l.get("id") for l in lanes if not l.get("tmux")]
    problems = []
    if not targets_own_lane:
        problems.append("Watch session does not open the lane's own live session")
    if lanes and len(without_session) == len(lanes):
        problems.append("no lane names a live session to watch")

    reported_control = present(snapshot, r"data-watch-reported", r"watchReported")
    reported_reaches = None
    if reported_control:
        reported_body = function_body(script, "watchReported")
        reported_reaches = bool(own_session.search(reported_body or ""))
        if not reported_reaches:
            problems.append(
                "a lane that has reported back is offered Watch session too, and its handler "
                "does not open that lane's own session — a control that reaches nothing is "
                "worse than one that is absent, because the ladder looks walkable")
    if problems:
        return KIT.bad("9", "; ".join(problems), lanes_without_session=len(without_session),
                       reported_watch_offered=reported_control,
                       reported_watch_reaches_its_lane=reported_reaches)
    reach = (f"; the same control on a lane that has reported back reaches that lane's own "
             f"session too" if reported_control else
             "; no lane that has reported back is offered it, which the clause does not ask for")
    return KIT.ok("9",
                  f"Watch session opens the lane's own live view; {len(lanes) - len(without_session)}"
                  f" of {len(lanes)} lane(s) name a session to reach{reach}",
                  lanes_without_session=len(without_session),
                  reported_watch_offered=reported_control,
                  reported_watch_reaches_its_lane=reported_reaches)


def check_feedback(snapshot):
    forms = {
        "text": r"feedbackText|<textarea",
        "a screenshot": r"feedbackImage|accept=\"image|image/\*",
        "voice": r"\bvoice\b|audio/\*|MediaRecorder",
    }
    claimed = [name for name, pat in forms.items() if present(snapshot, pat)]
    absent = [n for n in forms if n not in claimed]
    if not claimed:
        return KIT.bad("10", "feedback can be dropped in no form at all")
    body = function_body(snapshot.script_text(), "openFeedback")
    if not reaches_a_write(body, write_tokens(snapshot)):
        return KIT.bad("10", f"feedback is offered in {claimed} but reaches no write the app "
                             "declares, so nothing is dropped anywhere")
    return KIT.ok(
        "10",
        f"feedback is accepted in every form this body claims ({', '.join(claimed)}) and "
        f"reaches the feedback write; not offered here: {', '.join(absent) or 'none'} — where "
        "a body cannot do a thing, experience.v1 clause 14 asks it to say so in the app",
        forms_accepted=claimed, forms_absent=absent)


def check_steering(snapshot):
    hay = served(snapshot)
    offered = [name for name, rx in STEER_LIMITS if rx.search(hay)]
    missing = [name for name, _ in STEER_LIMITS if name not in offered]
    assigns = ASSIGNS_WORK.search(hay)
    problems = []
    if missing:
        problems.append(f"steering offers {offered} and no way to set " + ", ".join(missing))
    if assigns:
        problems.append(f"a control assigns work rather than setting a limit: "
                        f"{assigns.group(0)!r}")
    if problems:
        return KIT.bad("11", "; ".join(problems), offered=offered, missing=missing)
    return KIT.ok("11", "steering offers exactly the five limits and no way to assign work",
                  offered=offered)


def check_no_stop_button(snapshot):
    shell = snapshot.html("/")
    offenders = []
    for node in shell.walk():
        if node.tag not in ("button", "a"):
            continue
        label = " ".join([node.text(), node.attrs.get("title", ""),
                          node.attrs.get("aria-label", "")]).strip()
        if STOP_WORDS.search(label):
            offenders.append(f"{node.describe()}: {label[:50]!r}")
    if offenders:
        return KIT.bad("12", "controls on the board stop work: " + "; ".join(offenders[:5]),
                       controls=offenders[:8])
    return KIT.ok("12", "no control on the board stops work — stopping happens because the "
                        "objective changed or the steward said so in words")


def check_every_manager_listed(snapshot):
    boot = snapshot.boot() or {}
    managers = boot.get("managers") or []
    if not managers:
        return KIT.bad("13", "no manager session is listed at all")
    home = snapshot.script_named("render/home.js") or snapshot.script_text()
    sorts_by_needs = bool(re.search(r"sort\([^)]*needs|b\.needs\s*-\s*a\.needs", home))
    tell_all = present(snapshot, r"tell all|tellAll|message all|broadcast")
    problems = []
    if not sorts_by_needs:
        problems.append("the list is not sorted by which manager session needs you")
    if not tell_all:
        problems.append("there is no way to tell them all at once, so several projects must "
                        "be visited in turn")
    if problems:
        return KIT.bad("13", "; ".join(problems), managers=len(managers))
    return KIT.ok("13", f"all {len(managers)} manager session(s) listed, sorted by which needs "
                        "you, with one message that reaches all",
                  managers=len(managers))


# --------------------------------------------------------------------------- #
# driver                                                                       #
# --------------------------------------------------------------------------- #
def run_conformance(snapshot):
    results = [
        check_objective_stands_at_the_top(snapshot),        # 1
        check_waves_with_lanes(snapshot),                   # 2a
        check_every_grouping_carries_its_reason(snapshot),  # 2b
        check_return_brief(snapshot),                       # 3
        check_timeline_opens_onto_evidence(snapshot),       # 4
        check_flow_measures(snapshot),                      # 5a
        check_flow_and_outcome_apart(snapshot),             # 5b
        check_lanes_running_against_intended(snapshot),     # 6
        check_truly_ready_against_waiting(snapshot),        # 7
        check_lane_state_words(snapshot),                   # 8
        check_watch_session(snapshot),                      # 9
        check_feedback(snapshot),                           # 10
        check_steering(snapshot),                           # 11
        check_no_stop_button(snapshot),                     # 12
        check_every_manager_listed(snapshot),               # 13
    ]
    return KIT.report(snapshot, results, write_routes=snapshot.write_routes())


def main(argv=None) -> int:
    return run_cli("experience-operation-conformance",
                   "Assert experience-operation.v1 against the companion app.",
                   run_conformance, argv)


if __name__ == "__main__":
    raise SystemExit(main())
