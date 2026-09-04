# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""experience.v1 conformance kit — "the umbrella keeps its own promises".

`experience.v1` is the family's umbrella. Most of its clauses are kept by the
section contracts that hang off it, and those have their own kits. The clauses
left over are the umbrella's **own**, and until this kit existed nothing
asserted them — `ledger/rows.yaml` said so row by row (CVG-104, CVG-107,
CVG-108, CVG-112, CVG-113) rather than leaving the silence unexplained.

Two targets, because the umbrella makes two kinds of promise
------------------------------------------------------------
Some of its clauses are about the **running app** (how many writes exist, how
many things ask for your word, what the app says when it cannot do a thing).
Others are about how the family is **written** (does every behavior carry one
of the four words, is every behavior placed against the three surface classes,
do the contracts this umbrella names exist at all). So a target here is a pair:

===============  ==========================================================
the app          the running server, or a directory written by ``--capture``
the repository   where `contracts/`, `docs/workflow/` and `app/` live
===============  ==========================================================

The repository half is resolved rather than passed, so the kit keeps the one
command line every experience kit shares (`conformance/kitreport.py`):

* target is a URL → the repository is the checkout this kit lives in;
* target is a captured snapshot carrying a ``repo/`` directory → that;
* target is a captured snapshot **without** one → every repository-reading rule
  reports SKIP naming the missing half, never a pass and never a guess.

Both fixtures carry a ``repo/``, written by `make_fixtures.py` beside this file.

    uv run conformance/experience/run.py http://127.0.0.1:8788
    uv run conformance/experience/run.py conformance/experience/fixtures/sample-good

Stdlib only, and **no browser is launched**.

Numbering
---------
Rule ids anchor to the contract's **Core clause** numbers, as `documents.v1`
clause 5 asks and the steward ratified on 2026-09-03. Where one clause carries
several independent promises the kit emits one row per promise, lettered inside
the clause (`4a`, `4b`). Every one of the fifteen Core clauses has a row, and
`test_every_core_clause_has_a_row` fails if one does not.

Two rules SKIP, and say what a machine cannot settle
----------------------------------------------------
Core 10 and Core 11 are promises about **how a review is conducted** — that it
asks "is the behavior satisfied?" rather than "does it look the same?", and
that a shape never quietly removes a state or a refusal reason. Neither leaves
an artifact. A SKIP here is the kit refusing to claim work it did not do; the
reason names what would have to exist for the rule to become checkable.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from kitreport import Kit, run_cli  # noqa: E402
from repotarget import (  # noqa: E402
    core_clauses, reserved_section, resolve_repo,
)

CONTRACT = "contracts/experience.v1.md"

KIT = Kit(
    "experience.v1",
    CONTRACT,
    rules=[
        ("1", 1, "home_is_the_list_of_manager_sessions_sorted_by_need",
         "home lists the manager sessions you run, sorted by which one needs you"),
        ("2", 2, "two_places_and_only_two",
         "two places, and only two — Direction and Operation"),
        ("3", 3, "the_console_is_a_pane_never_a_third_place",
         "the Manager Console is a pane beside either place, never a third place"),
        ("4a", 4, "all_five_writes_exist",
         "all five writes the umbrella names exist in this body"),
        ("4b", 4, "nothing_else_writes_anything",
         "nothing beyond those five writes anything"),
        ("5a", 5, "at_most_five_things_ask_for_your_word",
         "at most five things ask for your word at once"),
        ("5b", 5, "every_answer_lands_in_a_dated_record",
         "every answer lands in a dated ratification record"),
        ("6a", 6, "the_state_words_the_app_serves_are_the_plain_ones",
         "every state the app serves is said in one of the three plain vocabularies"),
        ("6b", 6, "no_machine_vocabulary_outside_a_details_fold",
         "no machine vocabulary appears outside a Details fold"),
        ("7", 7, "the_app_holds_no_data_of_its_own",
         "the app holds no data of its own beyond what the umbrella leaves open"),
        ("8", 8, "every_write_names_a_manager_session_operation",
         "every write names a manager-session operation that does the same thing"),
        ("9", 9, "every_behavior_carries_one_of_four_words",
         "every behavior in a section contract carries one of the four words"),
        ("10", 10, "idiom_is_reviewed_as_behavior_not_shape",
         "IDIOM means the behavior is required and its shape is not"),
        ("11", 11, "idioms_never_subtract_a_behavior",
         "idioms satisfy behaviors; they never subtract them"),
        ("12", 12, "a_feature_no_contract_names_is_debt",
         "a body may exceed in idiom, never in features — an unnamed feature is debt"),
        ("13", 13, "every_behavior_placed_against_three_surface_classes",
         "every behavior is placed against full app · quick-access · notification"),
        ("14", 14, "a_limit_is_said_in_the_app_never_left_silent",
         "where a body genuinely cannot do a thing, it says so in the app"),
        ("15", 15, "every_contract_this_umbrella_names_exists",
         "this umbrella governs a family, and the contracts it names exist"),
    ],
    unfixturable={
        "10": ("whether review asked \"is the behavior satisfied?\" rather than \"does it "
               "look the same?\" is a fact about how a person read the work, and no "
               "artifact records it. It becomes checkable when a review leaves a record "
               "naming the behavior it judged — there is no such record to read today."),
        "11": ("the subtraction and transfer tests compare two bodies — whether a shape "
               "removed a state or a refusal reason, and whether the person was surprised "
               "or merely found it elsewhere. This family has one body (the browser app), "
               "so there is nothing to compare against; and the transfer test needs a "
               "person who learned the behavior in the other one."),
    },
)

# --------------------------------------------------------------------------- #
# the contract's own words                                                     #
# --------------------------------------------------------------------------- #
#: Core 4 — the five writes, and the word the app's own route table would use.
FIVE_WRITES = (
    ("answer with a word", "decision"),
    ("raise or lower a priority", "priority"),
    ("drop feedback", "feedback"),
    ("steer", "steer"),
    ("ask for a proposal", "ask"),
)

#: Core 4 — POST routes that are NOT a write to the project, each named by the
#: contract that holds it. A route is exempt because a contract says what it is,
#: never because counting it would be inconvenient.
WRITE_EXEMPTIONS = (
    (re.compile(r"^/(login|logout)$"),
     "the sign-in gate — a session, not the project (app/auth.py)"),
    (re.compile(r"^/api/tmux/"),
     "the console's message path — `experience-console.v1` Core 3 and 8: what you "
     "type there is a message to the manager session, and the console never ratifies"),
)

#: Core 5 — at most this many things ask for your word at once.
NEEDS_LIMIT = 5

#: Core 12 — writes beyond the five that a contract in this family DOES name,
#: each with the sentence that names it. The citation is checked against the
#: repository every run: if the quoted words are no longer in that clause, the
#: citation is stale and the write is reported as debt rather than as named.
#:
#: This table is written by hand on purpose. An earlier draft linked a route to
#: a clause by searching for the route's own word, and every link it produced
#: was fabricated — `keep` matched "keeps a teammate on plain tooling a
#: first-class participant", `read` matched "something a person can read", `ask`
#: matched "A question asked in Converge". A contract names behaviors in prose;
#: it does not name routes, and a keyword is not a citation.
CONTRACT_NAMED_WRITES = (
    (re.compile(r"/changes/\{[^}]+\}/restore$"),
     "experience-direction.v1.md", 6, re.compile(r"restoring from history", re.I)),
    (re.compile(r"/changes/\{[^}]+\}/keep$"),
     "experience-direction.v1.md", 8, re.compile(r"accepting and reverting", re.I)),
    (re.compile(r"/changes/\{[^}]+\}/edit$"),
     "experience-direction.v1.md", 5, re.compile(r"direct editing", re.I)),
    (re.compile(r"/docs/[^/]+/[^/]+/read$"),
     "experience.v1.md", None, re.compile(r"reading cursor", re.I)),
)

#: Core 6 — the three plain vocabularies, in the contract's own words.
PLAIN_WORDS = {
    "contracts": ("Kept", "Not yet", "Broken", "Pinned open", "Can't check"),
    "work": ("Truly ready", "Waiting on you", "Working", "Stuck", "Done"),
    "lanes": ("Working", "Quiet", "Silent"),
}

#: Core 6 — the machine's own words for the same states. Case-sensitive on
#: purpose: the plain word is `Done`, the machine's is `DONE`, and the whole
#: clause is about which of the two a steward is shown.
MACHINE_STATE_TOKENS = (
    # contracts
    "CONFORMS", "GAP", "VIOLATION", "NOT-ASSERTABLE", "OPEN-PINNED", "DIVERGED",
    # work
    "READY", "BLOCKED", "HELD", "DEFERRED", "RESOLVED", "CLOSED", "IN_PROGRESS",
    "IN-PROGRESS", "WIP", "TODO", "DONE", "WONTFIX", "BACKLOG",
    # lanes
    "RUNNING", "IDLE", "STALE", "DEAD",
)
MACHINE_STATE_RE = re.compile(
    r"\b(?:" + "|".join(sorted(MACHINE_STATE_TOKENS, key=len, reverse=True)) + r")\b")

#: Core 7 — what "a store of its own" looks like in Python.
STORE_MARKERS = (
    ("sqlite3", re.compile(r"\bsqlite3\b")),
    ("shelve", re.compile(r"\bshelve\b")),
    ("pickle", re.compile(r"\bpickle\.(dump|dumps)\b")),
    ("a JSON file of its own", re.compile(r"Path\.home\(\)[^\n]*\.json")),
)

#: Core 8 — how a body publishes the manager-session operation behind a write.
MANAGER_OPERATION_MARKERS = (
    re.compile(r"data-manager-operation"),
    re.compile(r"MANAGER_OPERATIONS?\b"),
    re.compile(r"manager[- ]session operation", re.I),
)

#: Core 9 — the four words a behavior may carry.
BEHAVIOR_WORDS = ("REQUIRED", "IDIOM", "OPTIONAL", "EXCLUDED")
BEHAVIOR_WORD_RE = re.compile(r"\((?:" + "|".join(BEHAVIOR_WORDS) + r")\)")

#: Core 13 — the three surface classes, named once.
SURFACE_CLASSES = ("full app", "quick-access", "notification")

#: Core 14 — the forms feedback may be dropped in (`experience-operation.v1`
#: clause 10), and how this body would show each.
#:
#: Every marker here is **offer-shaped**: a control, a MIME filter, or a
#: recorder API — something that only appears because the body takes that form.
#: A bare topic word is not one, and the third row used to be `\bvoice\b`.
#: Measured on this tree, 2026-09-04 (converge-gl6): once the app added the
#: Core 14 sentence "A voice note is not recorded here", the word `voice`
#: appeared in what the app serves, this rule stopped counting voice absent at
#: all, and rule 14's `cannot_do` went from
#: `['raise or lower a priority (priority)', 'feedback as voice']` to
#: `['raise or lower a priority (priority)']`. A sentence saying a form is NOT
#: taken read as an offer of it, and nothing here would have noticed voice going
#: missing. `app/tests/test_writes_named.py` holds the other side of this: it
#: asserts the shell carries no `audio/*` and no `MediaRecorder`, so the day the
#: app really does take voice, that assertion fires and this row starts matching
#: on the same evidence.
FEEDBACK_FORMS = (
    ("text", re.compile(r"feedbackText|<textarea")),
    ("a screenshot", re.compile(r"feedbackImage|accept=[\"']?image|image/\*")),
    ("voice", re.compile(r"feedbackVoice|accept=[\"']?audio|audio/\*|"
                         r"MediaRecorder|getUserMedia")),
)

#: Core 14, second half — "and what to do instead". A limit is only said in full
#: when the app also names somewhere the thing *can* be done. These are the
#: shapes that naming takes in this family; a negation is deliberately not one
#: of them, which is the entire point — a heading reading "… — not here" states
#: the limit and then stops.
REDIRECTION_MARKERS = (
    ("the manager session", re.compile(r"\bmanager session\b", re.I)),
    ("the Manager Console", re.compile(r"\bmanager console\b", re.I)),
    ("an explicit \"instead\"", re.compile(r"\binstead\b", re.I)),
    ("somewhere to put it", re.compile(r"\bdrop\b[^.;:!?]{0,120}\b(folder|file)\b",
                                       re.I)),
)

#: Core 14 — where one statement ends and the next begins, in what a body
#: serves. Sentence punctuation, the dashes this app writes its asides with
#: (`&mdash;`, `—`, ` -- `), and every HTML tag boundary.
#:
#: The tag boundary earns its place twice. A `<strong>` heading and the
#: `<span>` beneath it are two statements, not one run of prose — and a tag's
#: own attributes are consumed as the delimiter rather than read as something
#: the app *said*. Measured 2026-09-04 while fixing converge-gl6: reading a raw
#: ±220-character window instead let `<aside aria-label="Manager Console">` —
#: markup, about a different part of the page — stand in as "what to do
#: instead" for a body that had said nothing of the kind.
SEGMENT_SPLIT_RE = re.compile(
    r"(?<=[.;:!?])\s+|\s*(?:&mdash;|&ndash;|—|–|--)\s*|</?[a-zA-Z][^>]*>")

#: Core 14 — how far after the limit "what to do instead" may sit. The app says
#: both halves in one breath ("… is not recorded here — say it in the Manager
#: Console"), so the redirection is the same statement or very nearly the next.
#: Wide enough for a clause of context; narrow enough that prose elsewhere on
#: the page cannot be borrowed to finish a sentence the body never wrote.
REDIRECT_WITHIN_STATEMENTS = 3


# --------------------------------------------------------------------------- #
# reading the client the app ships                                             #
# --------------------------------------------------------------------------- #
def served_text(snapshot) -> str:
    """Everything a steward could be shown: the shell plus the client."""
    return snapshot.text("/") + "\n" + snapshot.script_text()


def present(snapshot, *patterns) -> bool:
    hay = served_text(snapshot)
    return any(re.search(p, hay, re.I) for p in patterns)


def strip_details_folds(text: str) -> str:
    """Blank out every `<details>…</details>`, wherever it is written.

    The app writes its folds inside template literals in the render modules, so
    the fold and the machine word arrive in the same file. Core 6 does not ask
    for silence — it asks for the machine's words to sit behind a fold.
    """
    return re.sub(r"<details\b.*?</details>", " ", text, flags=re.S | re.I)


def write_tail(path: str) -> str:
    """`/api/managers/{mid}/decision` → `decision`."""
    parts = [p for p in path.strip("/").split("/") if not p.startswith("{")]
    return parts[-1] if parts else ""


def exempt_write(path: str):
    for pattern, why in WRITE_EXEMPTIONS:
        if pattern.search(path):
            return why
    return None


# --------------------------------------------------------------------------- #
# Core 1 — the anchor is a manager session                                     #
# --------------------------------------------------------------------------- #
def check_home_lists_the_sessions(snapshot):
    boot = snapshot.boot() or {}
    managers = boot.get("managers") or []
    if not managers:
        return KIT.bad("1", "the app lists no manager session at all, so home has nothing "
                            "to be the list of")
    home = snapshot.script_named("render/home.js") or snapshot.script_text()
    if not home.strip():
        return KIT.bad("1", "the app ships no home renderer, so the list of manager "
                            "sessions is never drawn")
    facts = {
        "how many things want your word": (r"\bneeds\b", r"need your word"),
        "lanes running against lanes intended": (r"lanesActive[^\n]{0,40}lanesMax",),
        "the last brief line": (r"\bsummary\b", r"lastBrief"),
        "quiet or silent": (r"statusLabel", r"status-dot"),
    }
    missing = [name for name, pats in facts.items()
               if not any(re.search(p, home) for p in pats)]
    # `.sort((a, b) => b.needs - a.needs …)` — the comparator's own parentheses
    # sit between `.sort(` and the field, so a `[^)]*` window reads NONE of it
    # and reported this app as unsorted. Take a fixed window instead.
    sorted_by_need = any("needs" in home[m.end():m.end() + 160]
                         for m in re.finditer(r"\.sort\(", home))
    problems = []
    if missing:
        problems.append("the card carries no " + ", no ".join(missing))
    if not sorted_by_need:
        problems.append("the list is not sorted by which session needs you")
    if problems:
        return KIT.bad("1", "; ".join(problems), managers=len(managers))
    return KIT.ok("1",
                  f"home lists {len(managers)} manager session(s), sorted by which needs "
                  "you, each card carrying the count, the lanes, the last brief line and "
                  "its quiet-or-silent state",
                  managers=len(managers))


# --------------------------------------------------------------------------- #
# Core 2 / 3 — two places, and a pane beside them                              #
# --------------------------------------------------------------------------- #
def workspace_tabs(snapshot):
    switch = snapshot.html("/").first(node_id="workspaceSwitch")
    if switch is None:
        return None
    return [(n.id, n.text().strip()) for n in switch.walk()
            if n.tag == "button" or "workspace-tab" in n.classes]


def check_two_places(snapshot):
    tabs = workspace_tabs(snapshot)
    if tabs is None:
        return KIT.bad("2", "the shell offers no workspace switch, so the two places are "
                            "not reachable from each other")
    names = [t.lower() for _, t in tabs]
    problems = []
    for want in ("direction", "operation"):
        if not any(want in n for n in names):
            problems.append(f"no {want.title()} place")
    extra = [t for _, t in tabs
             if not any(w in t.lower() for w in ("direction", "operation"))]
    if extra:
        problems.append(f"a third place beside the two the contract names: {extra} — "
                        "conversation is a modality, not a place")
    if problems:
        return KIT.bad("2", "; ".join(problems), places=[t for _, t in tabs])
    return KIT.ok("2", f"exactly two places, and only two ({', '.join(t for _, t in tabs)})",
                  places=[t for _, t in tabs])


def check_console_is_a_pane(snapshot):
    shell = snapshot.html("/")
    console = shell.first(node_id="managerConsole")
    if console is None:
        return KIT.bad("3", "the shell carries no Manager Console at all")
    tabs = workspace_tabs(snapshot) or []
    as_a_place = [t for _, t in tabs if "console" in t.lower()]
    problems = []
    if as_a_place:
        problems.append(f"the console is offered as a place in the workspace switch "
                        f"({as_a_place}), which makes it a third place")
    if console.inside(cls="view"):
        problems.append("the console sits inside a view, so switching places tears it "
                        "down rather than leaving it open beside them")
    if problems:
        return KIT.bad("3", "; ".join(problems))
    return KIT.ok("3",
                  f"the console is a <{console.tag}> beside both places, outside either "
                  "view, and is not offered as a third place; that its conversation "
                  "survives the switch at runtime is beyond a static read",
                  element=console.describe())


# --------------------------------------------------------------------------- #
# Core 4 — exactly five writes                                                 #
# --------------------------------------------------------------------------- #
def check_all_five_writes_exist(snapshot):
    routes = snapshot.write_routes()
    if not routes:
        return KIT.bad("4a", "the app declares no write route at all in its own "
                             "/openapi.json, so none of the five writes exists")
    found, missing = {}, []
    for name, token in FIVE_WRITES:
        hit = [r for r in routes if write_tail(r) == token]
        if hit:
            found[name] = hit[0]
        else:
            missing.append(f"{name} (`{token}`)")
    if missing:
        return KIT.bad(
            "4a",
            "the app declares no route for " + ", ".join(missing)
            + f" — the clause names five writes and this body offers {len(found)}",
            writes_found=found, writes_missing=missing, write_routes=routes)
    return KIT.ok("4a", "all five writes the umbrella names exist as routes the app "
                        "declares: " + ", ".join(f"{n} → {r}" for n, r in found.items()),
                  writes_found=found)


def check_nothing_else_writes(snapshot):
    routes = snapshot.write_routes()
    if not routes:
        return KIT.bad("4b", "the app declares no write route at all, so this cannot be "
                             "read as five and no more")
    named = {t for _, t in FIVE_WRITES}
    beyond, exempted = [], []
    for route in routes:
        if write_tail(route) in named:
            continue
        why = exempt_write(route)
        if why:
            exempted.append({"route": route, "exempt": why})
        else:
            beyond.append(route)
    if beyond:
        return KIT.bad(
            "4b",
            f"{len(beyond)} route(s) beyond the five write something: {beyond}. The "
            "umbrella names five writes and says nothing else, in any body, writes "
            "anything; the section contracts offer these (editing, restoring and "
            "per-change choices are `experience-direction.v1` clauses 5, 6 and 8, and "
            "the read point is this umbrella's own open question). The disagreement is "
            "between the contracts, and it is the steward's to settle.",
            writes_beyond_the_five=beyond, exempted=exempted)
    return KIT.ok("4b",
                  f"nothing beyond the five writes anything; {len(exempted)} route(s) are "
                  "exempt by a contract that says what they are",
                  exempted=exempted)


# --------------------------------------------------------------------------- #
# Core 5 — at most five ask for your word, and every answer is recorded        #
# --------------------------------------------------------------------------- #
def check_needs_limit(snapshot):
    needs = snapshot.needs()
    if needs is None:
        return KIT.bad("5a", "the app served no needs payload, so nothing counts what is "
                             "asking for your word")
    items = needs if isinstance(needs, list) else (needs.get("items") or [])
    if len(items) > NEEDS_LIMIT:
        return KIT.bad(
            "5a",
            f"{len(items)} things ask for your word at once, and the clause fixes the "
            f"limit at {NEEDS_LIMIT}; several small calls are meant to arrive as one "
            "ratification sheet, not as a longer list",
            asking=len(items))
    return KIT.ok("5a", f"{len(items)} thing(s) ask for your word at once, within the "
                        f"limit of {NEEDS_LIMIT}",
                  asking=len(items))


def check_dated_ratification_record(snapshot, repo):
    if not repo:
        return KIT.skip("5b", repo.missing)
    records = repo.glob("docs/workflow/owner-ratifications-*.md")
    writer = repo.text("app/writes.py")
    problems = []
    if not records:
        problems.append("the repository holds no dated ratification record "
                        "(docs/workflow/owner-ratifications-<date>.md)")
    if not writer:
        problems.append("the app has no writer module to read, so nothing shows where an "
                        "answer lands")
    elif "owner-ratifications-" not in writer:
        problems.append("the app's write path never names the dated ratification record, "
                        "so an answer given here lands somewhere else")
    if problems:
        return KIT.bad("5b", "; ".join(problems),
                       records=[repo.rel(p) for p in records], repository=str(repo.root))
    dated = [repo.rel(p) for p in records]
    return KIT.ok("5b",
                  f"the answer write names the dated ratification record, and {len(dated)} "
                  f"record(s) exist ({', '.join(dated[:3])}); what one holds once written "
                  "is beyond a static read",
                  records=dated, repository=str(repo.root))


# --------------------------------------------------------------------------- #
# Core 6 — plain state words everywhere                                        #
# --------------------------------------------------------------------------- #
def served_state_values(snapshot):
    """Every state word the app SERVES, with where it came from."""
    out = []
    boot = snapshot.boot() or {}
    for m in boot.get("managers") or []:
        out.append(("a manager session's state", m.get("statusLabel")))
    manager = snapshot.manager() or {}
    for repo in manager.get("repositories") or []:
        for doc in repo.get("docs") or []:
            out.append(("a document's standing", doc.get("standing")))
    op = snapshot.operation() or {}
    for lane in op.get("lanes") or []:
        out.append(("a lane's state", lane.get("statusLabel")))
    for wave in op.get("waves") or []:
        out.append(("a wave's phase", wave.get("phase")))
    return [(where, str(value).strip()) for where, value in out if value]


def check_state_words_served(snapshot):
    values = served_state_values(snapshot)
    if not values:
        return KIT.bad("6a", "the app serves no state word at all, so a steward is told "
                             "nothing about where anything stands")
    plain = {w for group in PLAIN_WORDS.values() for w in group}
    foreign = {}
    for where, value in values:
        if value in plain:
            continue
        foreign.setdefault(f"{where}: {value!r}", 0)
        foreign[f"{where}: {value!r}"] += 1
    if foreign:
        return KIT.bad(
            "6a",
            "the app serves state words outside the three vocabularies this clause "
            "fixes: " + "; ".join(f"{k} ({n}×)" for k, n in sorted(foreign.items())[:6])
            + f". The plain words are {sorted(plain)}",
            foreign=sorted(foreign), read=len(values))
    return KIT.ok("6a",
                  f"all {len(values)} state word(s) the app serves are plain ones "
                  f"({sorted({v for _, v in values})})",
                  read=len(values))


def check_machine_vocabulary_is_folded(snapshot):
    exposed = {}
    for route in snapshot.order:
        body = snapshot.text(route)
        if not body or route.endswith(".css"):
            continue
        if route.startswith("/api/") or route == "/openapi.json":
            continue          # a payload is not a surface; 6a judges what it carries
        for match in MACHINE_STATE_RE.finditer(strip_details_folds(body)):
            exposed.setdefault(route, set()).add(match.group(0))
    folded = len(re.findall(r"<details\b", served_text(snapshot), re.I))
    if exposed:
        shown = "; ".join(f"{r}: {sorted(w)}" for r, w in sorted(exposed.items())[:4])
        return KIT.bad(
            "6b",
            f"the machine's own state words appear outside a Details fold — {shown}. "
            "The clause does not ask for silence; it asks for the machine's words to sit "
            "behind a fold, and this body already has "
            f"{folded} fold(s) that do exactly that.",
            exposed={r: sorted(w) for r, w in exposed.items()})
    return KIT.ok("6b",
                  f"no machine state word appears outside a Details fold in what the app "
                  f"serves; {folded} fold(s) carry the detail. A word the app never "
                  "writes down but renders from a payload is judged by rule 6a.",
                  details_folds=folded)


# --------------------------------------------------------------------------- #
# Core 7 — the app holds no data of its own                                    #
# --------------------------------------------------------------------------- #
def check_no_data_of_its_own(snapshot, repo):
    if not repo:
        return KIT.skip("7", repo.missing)
    stores = []
    for path in repo.glob("app/*.py"):
        body = path.read_text(encoding="utf-8", errors="replace")
        for name, pattern in STORE_MARKERS:
            if pattern.search(body):
                stores.append({"file": repo.rel(path), "kind": name})
    if not stores:
        return KIT.ok("7", "the app keeps no store of its own — every screen is drawn "
                           "from the project's own files and queues",
                      repository=str(repo.root))
    reserved = reserved_section(repo.text(CONTRACT))
    left_open = bool(re.search(r"reading cursor|last read", reserved, re.I))
    listed = ", ".join(f"{s['file']} ({s['kind']})" for s in stores)
    if not left_open:
        return KIT.bad(
            "7",
            f"the app keeps a store of its own — {listed} — and the umbrella's Reserved "
            "section leaves no such question open, so this is a second copy of the truth",
            stores=stores)
    return KIT.ok(
        "7",
        f"the app keeps one store of its own ({listed}), and it is exactly the question "
        "the umbrella's Reserved section leaves open — where the reading cursor behind "
        "\"what changed since you last read\" is kept. What that store actually holds is "
        "beyond a static read; that it is an open question and not a silent second copy "
        "is what this row asserts.",
        stores=stores, reserved_question=True)


# --------------------------------------------------------------------------- #
# Core 8 — every write names a manager-session operation                       #
# --------------------------------------------------------------------------- #
def check_writes_name_a_manager_operation(snapshot):
    offered = [(name, token) for name, token in FIVE_WRITES
               if any(write_tail(r) == token for r in snapshot.write_routes())]
    if not offered:
        return KIT.bad("8", "the app offers none of the five writes, so there is nothing "
                            "that could name a manager-session operation")
    hay = served_text(snapshot)
    published = [p.pattern for p in MANAGER_OPERATION_MARKERS if p.search(hay)]
    if not published:
        return KIT.bad(
            "8",
            f"this body offers {len(offered)} of the five writes "
            f"({', '.join(n for n, _ in offered)}) and publishes no manager-session "
            "operation for any of them. A reader cannot check that what they can do here "
            "the manager session can do too — nothing on the surface says which operation "
            "does the same thing.",
            writes_offered=[n for n, _ in offered])
    named = []
    for name, token in offered:
        # Every occurrence, not the first: the word `decision` appears in a dozen
        # places, and reading only the first would report a body that publishes
        # the mapping as one that does not.
        windows = re.finditer(rf"[^\n]{{0,200}}{re.escape(token)}[^\n]{{0,200}}", hay, re.I)
        if any(any(p.search(w.group(0)) for p in MANAGER_OPERATION_MARKERS)
               for w in windows):
            named.append(name)
    unnamed = [n for n, _ in offered if n not in named]
    if unnamed:
        return KIT.bad("8", f"the surface names a manager-session operation for {named} "
                            f"but not for {unnamed}",
                       named=named, unnamed=unnamed)
    return KIT.ok("8", f"every write this body offers names the manager-session operation "
                       f"that does the same thing ({', '.join(named)})",
                  named=named)


# --------------------------------------------------------------------------- #
# Core 9 / 13 — how the family is written                                      #
# --------------------------------------------------------------------------- #
def check_behavior_words(snapshot, repo):
    if not repo:
        return KIT.skip("9", repo.missing)
    family = repo.family_contracts()
    if not family:
        return KIT.bad("9", "the repository holds no section contract, so there is no "
                            "behavior to carry one of the four words",
                       repository=str(repo.root))
    rows, untagged = {}, []
    for name, text in sorted(family.items()):
        clauses = core_clauses(text)
        tagged = [n for n, body in clauses if BEHAVIOR_WORD_RE.search(body)]
        rows[name] = {"clauses": len(clauses), "carrying_a_word": len(tagged)}
        if clauses and len(tagged) < len(clauses):
            untagged.append(f"{name} ({len(clauses) - len(tagged)} of {len(clauses)})")
    if untagged:
        return KIT.bad(
            "9",
            "section contracts with behaviors carrying none of "
            f"{list(BEHAVIOR_WORDS)}: " + "; ".join(untagged)
            + ". Required, idiom, optional and excluded are how a body knows what its "
              "absence means; an untagged behavior means nothing either way.",
            contracts=rows)
    return KIT.ok("9", "every behavior in every section contract carries one of the four "
                       "words: " + "; ".join(f"{n} ({r['clauses']})" for n, r in rows.items()),
                  contracts=rows)


def check_surface_classes(snapshot, repo):
    if not repo:
        return KIT.skip("13", repo.missing)
    family = repo.family_contracts()
    if not family:
        return KIT.bad("13", "the repository holds no section contract, so no behavior is "
                             "placed against anything", repository=str(repo.root))
    rows, silent = {}, []
    for name, text in sorted(family.items()):
        placed = [c for c in SURFACE_CLASSES
                  if re.search(re.escape(c).replace(r"\ ", r"[\s-]+"), text, re.I)]
        rows[name] = placed
        if len(placed) < len(SURFACE_CLASSES):
            silent.append(f"{name} places behavior against {placed or 'none'}")
    if silent:
        return KIT.bad(
            "13",
            "; ".join(silent) + f" — the three classes are {list(SURFACE_CLASSES)}, and "
            "the clause exists so that \"nobody thought about the widget\" cannot pass as "
            "a decision",
            placement=rows)
    return KIT.ok("13", "every section contract places its behaviors against all three "
                        "surface classes", placement=rows)


def check_named_contracts_exist(snapshot, repo):
    if not repo:
        return KIT.skip("15", repo.missing)
    umbrella = repo.text(CONTRACT)
    if not umbrella:
        return KIT.bad("15", f"the repository holds no {CONTRACT} to read the family from",
                       repository=str(repo.root))
    clause = dict(core_clauses(umbrella)).get(15, "")
    named = sorted(set(re.findall(r"`([a-z0-9-]+\.v\d+)`", clause)))
    if not named:
        return KIT.bad("15", "clause 15 names no contract, so the family it governs "
                             "cannot be checked")
    missing = [n for n in named if not repo.exists(f"contracts/{n}.md")]
    if missing:
        return KIT.bad(
            "15",
            f"the umbrella names {len(named)} contract(s) in its family and "
            f"{len(missing)} do not exist: {missing}. A family member named and unwritten "
            "is a promise nothing keeps.",
            named=named, missing=missing)
    return KIT.ok("15", f"every one of the {len(named)} contracts this umbrella names "
                        "exists in the repository", named=named)


# --------------------------------------------------------------------------- #
# Core 12 — a feature no contract names is debt                                #
# --------------------------------------------------------------------------- #
def verify_citation(repo, contract_name: str, clause, phrase) -> str:
    """The cited clause, if it still says what the citation claims. Else "".

    A citation nobody re-reads is a citation that rots. Every run re-opens the
    contract and looks for the quoted words in the clause named, so a clause
    that moved or was reworded makes the citation stale rather than silently
    wrong.
    """
    text = repo.text(f"contracts/{contract_name}")
    if not text:
        return ""
    if clause is None:
        region = reserved_section(text)
        where = f"{contract_name} Reserved"
    else:
        region = dict(core_clauses(text)).get(clause, "")
        where = f"{contract_name} Core {clause}"
    return where if region and phrase.search(region) else ""


def check_unnamed_features_are_debt(snapshot, repo):
    if not repo:
        return KIT.skip("12", repo.missing)
    if not repo.text(CONTRACT):
        return KIT.bad("12", f"the repository holds no {CONTRACT}, so no feature can be "
                             "told from debt", repository=str(repo.root))
    named_by_the_umbrella = {t for _, t in FIVE_WRITES}
    debt, named, stale = [], {}, []
    for route in snapshot.write_routes():
        if exempt_write(route):
            continue
        if write_tail(route) in named_by_the_umbrella:
            named[route] = "experience.v1.md Core 4 (one of the five)"
            continue
        cite = ""
        for pattern, contract_name, clause, phrase in CONTRACT_NAMED_WRITES:
            if not pattern.search(route):
                continue
            cite = verify_citation(repo, contract_name, clause, phrase)
            if not cite:
                stale.append(f"{route} → {contract_name} "
                             f"{'Core %s' % clause if clause else 'Reserved'}")
            break
        if cite:
            named[route] = cite
        else:
            debt.append(route)
    if debt:
        return KIT.bad(
            "12",
            f"{len(debt)} feature(s) this body offers are named by no contract in the "
            f"family: {debt}. A feature in one body and nowhere else is either a behavior "
            "that belongs in this family or it is debt — there is no third thing it can "
            "be." + (f" ({len(stale)} citation(s) went stale: {stale})" if stale else ""),
            debt=debt, named=named, stale_citations=stale)
    return KIT.ok("12",
                  f"every one of the {len(named)} writes this body offers is named by a "
                  "contract in the family, each citation re-read this run, so none of "
                  "them is debt",
                  named=named)


# --------------------------------------------------------------------------- #
# Core 14 — a limit is said, never left silent                                 #
# --------------------------------------------------------------------------- #
NEGATION_RE = re.compile(r"\bnot\b|\bno\b|cannot|can't|does not|isn't|"
                         r"unavailable|not offered|not yet", re.I)


def statements(text: str) -> list:
    """What a body serves, cut into the separate statements it makes.

    Markup is a delimiter here, never content: what a clause about *saying* a
    thing may read is the prose between the tags.
    """
    return [s.strip() for s in SEGMENT_SPLIT_RE.split(text) if s and s.strip()]


def says_so(snapshot, thing: str) -> str:
    """How fully does the app state this limit? — `""`, `"limit"`, or `"both"`.

    Core 14 asks for two things, "what the limit is, and what to do instead",
    so this reads for two things and reports which it found.

    - **the limit** — one *statement* that names the thing and denies it: the
      negation and the thing sit in the same statement, not merely within
      shouting distance. Measured on this tree, 2026-09-04 (converge-gl6):
      deleting the whole limit sentence from `app/templates/shell.html` left
      only the heading "Raise or lower a priority — not here", and the old
      ±220-character window still PASSed this rule on it, because `priority`
      and `not` were near each other across a tag boundary. `<strong>` and the
      `<span>` beneath it are two statements; the heading alone is half of one.
    - **what to do instead** — a `REDIRECTION_MARKERS` phrase in that statement
      or one of the next `REDIRECT_WITHIN_STATEMENTS`, naming somewhere the
      thing *can* be done. This is the half the old rule never read at all.
    """
    said = ""
    stmts = statements(served_text(snapshot))
    thing_re = re.compile(re.escape(thing), re.I)
    for i, stmt in enumerate(stmts):
        if not (thing_re.search(stmt) and NEGATION_RE.search(stmt)):
            continue
        said = "limit"
        nearby = [stmt, *stmts[i + 1: i + 1 + REDIRECT_WITHIN_STATEMENTS]]
        if any(pattern.search(s) for s in nearby for _, pattern in REDIRECTION_MARKERS):
            return "both"
    return said


def check_limits_are_said(snapshot):
    absent = []
    for name, token in FIVE_WRITES:
        if not any(write_tail(r) == token for r in snapshot.write_routes()):
            absent.append(f"{name} (`{token}`)")
    hay = served_text(snapshot)
    for form, pattern in FEEDBACK_FORMS:
        if not pattern.search(hay):
            absent.append(f"feedback as {form}")
    if not absent:
        return KIT.ok("14", "this body does everything the family names of it, so there "
                            "is no limit left to state")
    said = {thing: says_so(snapshot, re.sub(r"\s*\(`[^`]+`\)", "", thing).split()[-1])
            for thing in absent}
    silent = [thing for thing, how in said.items() if how == ""]
    half = [thing for thing, how in said.items() if how == "limit"]
    if silent or half:
        parts = []
        if silent:
            parts.append(f"says nothing anywhere about {silent} — not what the limit "
                         "is, and not what to do instead")
        if half:
            parts.append(f"states the limit on {half} but never names what to do "
                         "instead, which is the second half this clause asks for "
                         f"(looked for {[name for name, _ in REDIRECTION_MARKERS]})")
        return KIT.bad(
            "14",
            f"this body cannot do {absent}, and " + "; ".join(parts) +
            ". Silence is the only wrong answer this clause names, and half a "
            "sentence is most of the way to silence.",
            cannot_do=absent, said_nothing_about=silent, limit_stated_no_redirect=half)
    return KIT.ok("14",
                  f"this body cannot do {absent}, and for each one says both halves in "
                  "the app — what the limit is, and what to do instead",
                  cannot_do=absent)


# --------------------------------------------------------------------------- #
# driver                                                                       #
# --------------------------------------------------------------------------- #
def run_conformance(snapshot):
    repo = resolve_repo(snapshot, __file__)
    results = [
        check_home_lists_the_sessions(snapshot),            # 1
        check_two_places(snapshot),                         # 2
        check_console_is_a_pane(snapshot),                  # 3
        check_all_five_writes_exist(snapshot),              # 4a
        check_nothing_else_writes(snapshot),                # 4b
        check_needs_limit(snapshot),                        # 5a
        check_dated_ratification_record(snapshot, repo),    # 5b
        check_state_words_served(snapshot),                 # 6a
        check_machine_vocabulary_is_folded(snapshot),       # 6b
        check_no_data_of_its_own(snapshot, repo),           # 7
        check_writes_name_a_manager_operation(snapshot),    # 8
        check_behavior_words(snapshot, repo),               # 9
        KIT.skip("10"),                                     # 10
        KIT.skip("11"),                                     # 11
        check_unnamed_features_are_debt(snapshot, repo),    # 12
        check_surface_classes(snapshot, repo),              # 13
        check_limits_are_said(snapshot),                    # 14
        check_named_contracts_exist(snapshot, repo),        # 15
    ]
    return KIT.report(snapshot, results,
                      repository=str(repo.root) if repo else None,
                      repository_kind=repo.kind,
                      write_routes=snapshot.write_routes())


def main(argv=None) -> int:
    return run_cli("experience-conformance",
                   "Assert experience.v1 — the umbrella's own clauses — against the "
                   "companion app and the repository it is a body for.",
                   run_conformance, argv)


if __name__ == "__main__":
    raise SystemExit(main())
