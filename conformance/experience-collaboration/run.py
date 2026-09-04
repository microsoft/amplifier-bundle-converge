# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""experience-collaboration.v1 conformance kit — "the seam stays where it is".

This contract fixes a **boundary**: people align through the repository host
they already use, Converge renders that flow, and two manager sessions never
grow a private channel between them. So the kit judges two things a machine can
actually settle — what the repository's own history and write path do, and what
the running app declares it can reach — and refuses the rest out loud.

    uv run conformance/experience-collaboration/run.py http://127.0.0.1:8788
    uv run conformance/experience-collaboration/run.py <a fixture directory>

Stdlib only, and **no browser is launched**.

Two targets
-----------
Like `conformance/experience/`, a target here is a pair: the app the steward
uses, and the repository it is a body for. The repository half is resolved by
the convention in `../experience/repotarget.py` — a snapshot with no ``repo/``
makes every repository-reading rule SKIP rather than silently judge whatever
checkout the kit sits in.

What only a person can see
--------------------------
Five of this contract's clauses were `NOT-ASSERTABLE` in `ledger/rows.yaml`
because "only a live host settles them". That is true of *half* of some of them
and not of others, and the difference matters:

* whether a bridge **exists** is provable from what the app declares — an absent
  route is an absent route, and this kit FAILs on it;
* whether a teammate's reply **came back attributed** needs a second party
  writing on a real host, and no file in this tree can stand in for one. That
  half SKIPs, with the reason naming exactly what is missing.

Numbering
---------
Rule ids anchor to the contract's **Core clause** numbers, as `documents.v1`
clause 5 asks and the steward ratified on 2026-09-03. Every one of the ten Core
clauses has a row, and `test_every_core_clause_has_a_row` fails if one does not.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "experience"))

from kitreport import Kit, run_cli  # noqa: E402
from repotarget import resolve_repo  # noqa: E402

CONTRACT = "contracts/experience-collaboration.v1.md"

KIT = Kit(
    "experience-collaboration.v1",
    CONTRACT,
    rules=[
        ("1", 1, "git_is_the_protocol",
         "collaboration happens through the shared repository host, and the write "
         "path is git"),
        ("2", 2, "no_manager_talks_to_another_manager",
         "manager sessions never talk to each other directly"),
        ("3", 3, "three_origins_one_review",
         "a proposal is shown identically whoever it came from"),
        ("4a", 4, "the_pull_request_bridge_exists",
         "a question asked in Converge can reach the host as a comment"),
        ("4b", 4, "the_reply_comes_back_attributed",
         "the reply arrives back inside the same review, attributed"),
        ("5a", 5, "the_answer_lands_in_the_dated_record",
         "your answer is written to the dated ratification record"),
        ("5b", 5, "the_answer_returns_to_its_origin",
         "your answer is posted back where the proposal came from"),
        ("6a", 6, "inbound_changes_arrive_without_asking",
         "inbound changes arrive without the steward asking for them"),
        ("6b", 6, "the_fallback_is_named_not_assumed",
         "the freshness mechanism is named in plain words"),
        ("7", 7, "the_manager_session_is_not_in_the_hot_path",
         "a write goes to the repository directly, not through the manager session"),
        ("8a", 8, "one_steward_per_manager_session",
         "whose word counts is settled when the session is registered"),
        ("8b", 8, "no_second_persons_word_is_recorded",
         "no second person's word is written to the ratification record"),
        ("9", 9, "a_ratification_is_an_ordinary_repository_change",
         "the word is recorded and the text it ratifies is committed, the ordinary way"),
        ("10", 10, "no_second_collaboration_surface",
         "Converge adds no second issue tracker, document store or review tool"),
    ],
    unfixturable={
        "4b": ("a comment written by a teammate on a real repository host, arriving back "
               "inside the review with their name on it, cannot be produced by any file "
               "in this tree. Settling it needs a live host and a second party on it — "
               "the app's own declared routes can only show whether a bridge exists at "
               "all, which is rule 4a."),
        "8b": ("whether a second person's word ever reached the ratification record needs "
               "two people answering on one manager session. This target has one signed-in "
               "reader and no way to be two; what IS checkable — that whose word counts is "
               "settled at registration rather than inferred from whoever is looking — is "
               "rule 8a."),
    },
)

# --------------------------------------------------------------------------- #
# the contract's own words                                                     #
# --------------------------------------------------------------------------- #
#: Core 1 — the write path's own transport.
GIT_CALL = re.compile(r"\[\s*[\"']git[\"']")

#: Core 1 / Core 7 — a transport that is NOT the repository.
OTHER_TRANSPORTS = (
    ("a terminal session", re.compile(r"\btmux\b|send[_-]?keys", re.I)),
    ("a network socket", re.compile(r"socket\.socket|websockets?\.connect", re.I)),
)

#: Core 2 — a second manager session as a destination. Reaching the HOST is
#: required by Core 4; reaching another MANAGER is what this clause forbids.
PEER_MARKERS = (
    ("a peer manager session", re.compile(r"\bpeer[_a-z]*\b", re.I)),
    ("federation", re.compile(r"\bfederat", re.I)),
    ("another manager session as a destination",
     re.compile(r"(other|remote|another)[_\s-]manager", re.I)),
)
#: A route that addresses one manager from another.
PEER_ROUTE = re.compile(r"/managers?/[^/]+/(peers?|federat|remote)", re.I)

#: Core 3 — how a review lays a proposal out, and how it must NOT.
REVIEW_RENDERER = re.compile(r"function\s+renderReview\b")
ORIGIN_AS_A_VALUE = re.compile(r"\$\{[^}]*\b(source|origin)\b[^}]*\}")
ORIGIN_AS_A_BRANCH = re.compile(
    r"(if\s*\([^)]*\b(origin|source)\b[^)]*===)|(switch\s*\([^)]*\b(origin|source)\b)", re.I)

#: Core 4 — a bridge to the host's own comments.
HOST_COMMENT_MARKERS = (
    ("the host's own command line", re.compile(r"\bgh\b[^\n]{0,40}\b(pr|issue)\b[^\n]{0,40}comment", re.I)),
    ("the host's comments endpoint", re.compile(r"api\.github\.com|/pulls?/[^\n]{0,30}/comments", re.I)),
    ("a call that posts a comment", re.compile(r"\b(post|send|write)[_A-Za-z]*comment", re.I)),
    ("a call that comments on a pull request",
     re.compile(r"comment[_A-Za-z]*(on|to)[_A-Za-z]*(host|pull|pr)\b", re.I)),
)
#: …and the same, seen from the app's own route table.
HOST_COMMENT_ROUTE = re.compile(r"/(comments?|pull[s-]?|pr)(/|$)", re.I)

#: Core 5 — the answer going back where it came from.
POST_BACK_MARKERS = (
    ("a call that posts the answer back", re.compile(r"post[_A-Za-z]*back", re.I)),
    ("the origin addressed as a destination",
     re.compile(r"\borigin\b[^\n]{0,60}(comment|post|reply)", re.I)),
    ("a reply addressed to the origin",
     re.compile(r"(comment|post|reply)[^\n]{0,60}\borigin\b", re.I)),
)

#: Core 6 — freshness that is not the steward's job.
ARRIVES_BY_ITSELF = (
    ("a webhook the host calls", re.compile(r"/(webhooks?|hooks)(/|$)", re.I)),
    ("a live stream", re.compile(r"EventSource|WebSocket\(", re.I)),
    ("polling on a timer", re.compile(r"setInterval\([^\n]{0,120}(reload|refresh|poll)", re.I)),
)
#: Core 6 — the same, said in plain words a steward reads.
FALLBACK_NAMED = re.compile(
    r"checked every|refreshe?[sd] every|updates? every|polling|poll(s|ed)? the host|"
    r"webhook", re.I)

#: Core 8 — whose word counts, settled at registration.
STEWARD_FIELD = re.compile(r"\bsteward\b", re.I)

#: Core 9 — a proposal's file name, the repository's own shape.
CANDIDATE_SHAPE = re.compile(r"-candidate\.md")
COMMIT_CALL = re.compile(r"[\"']commit[\"']")

#: Core 10 — a surface Converge must not grow. `comment` is deliberately NOT
#: here: a comment RELAYED to the host is Core 4's bridge. What this clause
#: forbids is Converge KEEPING one.
SECOND_SURFACE_ROUTE = re.compile(
    r"/(issues?|tickets?|threads?|boards?|wikis?|code[-_]?reviews?)(/|$)", re.I)


# --------------------------------------------------------------------------- #
# reading                                                                      #
# --------------------------------------------------------------------------- #
def served_text(snapshot) -> str:
    return snapshot.text("/") + "\n" + snapshot.script_text()


def app_text(repo) -> str:
    return "\n".join(body for _, body in repo.app_sources())


def strip_python_prose(code: str) -> str:
    """Blank out docstrings, string literals and `#` comments.

    Measured against the live app: `app/serve.py` explains its auth gate with
    "There is deliberately no exemption for a loopback peer." Read as bare
    words, `peer` in that sentence looked like a channel to another manager
    session and rule 2 reported a body that has no such channel as having one —
    a fabricated finding, and the same shape as the direction kit's "a write is
    a call, not a word in a message". A channel is CODE, so only code is read.
    """
    code = re.sub(r'"""[\s\S]*?"""|\'\'\'[\s\S]*?\'\'\'', " ", code)
    code = re.sub(r"'[^'\n]*'|\"[^\"\n]*\"", " ", code)
    return re.sub(r"#[^\n]*", " ", code)


def any_match(named_patterns, text):
    """The plain-word names of every marker that matched — never a raw pattern."""
    return [name for name, pattern in named_patterns if pattern.search(text)]


# --------------------------------------------------------------------------- #
# Core 1 / 2 — the seam                                                        #
# --------------------------------------------------------------------------- #
def check_git_is_the_protocol(snapshot, repo):
    if not repo:
        return KIT.skip("1", repo.missing)
    writer = repo.text("app/writes.py")
    if not writer:
        return KIT.bad("1", "the app has no writer module, so nothing shows what a write "
                            "actually goes through", repository=str(repo.root))
    if not GIT_CALL.search(writer):
        return KIT.bad(
            "1",
            "the write path never runs git, so a change made here does not reach the "
            "shared repository the way every other participant's does — Converge would "
            "be replacing the flow rather than rendering it",
            repository=str(repo.root))
    others = [name for name, pattern in OTHER_TRANSPORTS if pattern.search(writer)]
    if others:
        return KIT.bad("1", f"the write path reaches the repository through git AND "
                            f"through {others}; a second transport beside git is a second "
                            "protocol, and a teammate on plain tooling cannot see it",
                       other_transports=others)
    return KIT.ok("1", "every write reaches the shared repository through git and nothing "
                       "else; what the host then does with it is the host's own business",
                  repository=str(repo.root))


def check_no_manager_to_manager(snapshot, repo):
    routes = list(snapshot.api_routes())
    peer_routes = [r for r in routes if PEER_ROUTE.search(r)]
    found = []
    if repo:
        code = strip_python_prose(app_text(repo))
        found = [name for name, pattern in PEER_MARKERS if pattern.search(code)]
    if peer_routes or found:
        return KIT.bad(
            "2",
            "this body offers a way for one manager session to reach another"
            + (f" — routes: {peer_routes}" if peer_routes else "")
            + (f" — in the app's own source: {found}" if found else "")
            + ". Two stewards both running Converge must still meet as Converge · host · "
              "Converge, or a teammate on plain tooling stops being a first-class "
              "participant.",
            peer_routes=peer_routes, peer_markers=found)
    detail = (f"no route among the {len(routes)} this app declares addresses a second "
              "manager session")
    if repo:
        detail += ", and the app's own source names no peer, no federation and no other "\
                  "manager as a destination"
    else:
        detail += "; the app's own source was not read (this target carries no repository "\
                  "half), so this row judges the route table alone"
    return KIT.ok("2", detail, routes_read=len(routes))


# --------------------------------------------------------------------------- #
# Core 3 — three origins, one review                                           #
# --------------------------------------------------------------------------- #
def check_three_origins_one_review(snapshot):
    review = snapshot.script_named("render/direction.js") or snapshot.script_text()
    if not review.strip():
        return KIT.bad("3", "the app ships no review renderer, so a proposal is laid out "
                            "nowhere")
    renderers = len(REVIEW_RENDERER.findall(review))
    problems = []
    if renderers == 0:
        problems.append("no review renderer at all")
    elif renderers > 1:
        problems.append(f"{renderers} review renderers — where it came from cannot be a "
                        "fact ABOUT the proposal if each origin is laid out by its own code")
    if not ORIGIN_AS_A_VALUE.search(review):
        problems.append("the origin is never rendered as a value, so a reader is not told "
                        "where a proposal came from at all")
    branch = ORIGIN_AS_A_BRANCH.search(review)
    if branch:
        problems.append(f"the layout branches on the origin ({branch.group(0)[:48]!r}), "
                        "which is a different experience per origin")
    if problems:
        return KIT.bad("3", "; ".join(problems), review_renderers=renderers)
    return KIT.ok("3", "one review path lays out every proposal, and the origin is a value "
                       "it renders rather than a branch it takes",
                  review_renderers=renderers)


# --------------------------------------------------------------------------- #
# Core 4 / 5 — the bridge, and the answer going home                           #
# --------------------------------------------------------------------------- #
def bridge_evidence(snapshot, repo):
    hay = served_text(snapshot)
    if repo:
        hay += "\n" + app_text(repo)
    marks = any_match(HOST_COMMENT_MARKERS, hay)
    routes = [r for r in snapshot.api_routes() if HOST_COMMENT_ROUTE.search(r)]
    return marks, routes


def check_the_bridge_exists(snapshot, repo):
    marks, routes = bridge_evidence(snapshot, repo)
    if not marks and not routes:
        return KIT.bad(
            "4a",
            "nothing in this body can carry a question to the host as a comment: no route "
            "the app declares addresses a pull request or its comments, and no code path "
            "posts one. A steward asking a question here has to leave and say it "
            "somewhere else, which is the copying between tools this clause exists to stop.",
            comment_routes=routes)
    return KIT.ok("4a", f"a path to the host's own comments exists (routes: {routes or 'none'}; "
                        f"code: {marks or 'none'}); whether a comment actually lands is "
                        "beyond a static read",
                  comment_routes=routes, markers=marks)


def check_answer_lands_in_the_record(snapshot, repo):
    if not repo:
        return KIT.skip("5a", repo.missing)
    records = repo.glob("docs/workflow/owner-ratifications-*.md")
    writer = repo.text("app/writes.py")
    problems = []
    if not writer:
        problems.append("the app has no writer module, so nothing shows where an answer goes")
    elif "owner-ratifications-" not in writer:
        problems.append("the app's write path never names the dated ratification record")
    if not records:
        problems.append("the repository holds no dated ratification record")
    if problems:
        return KIT.bad("5a", "; ".join(problems), repository=str(repo.root))
    return KIT.ok("5a", f"the answer write names the dated ratification record, and "
                        f"{len(records)} record(s) exist "
                        f"({', '.join(repo.rel(p) for p in records[:3])})",
                  records=[repo.rel(p) for p in records])


def check_answer_returns_to_its_origin(snapshot, repo):
    hay = served_text(snapshot)
    if repo:
        hay += "\n" + app_text(repo)
    back = any_match(POST_BACK_MARKERS, hay)
    _marks, routes = bridge_evidence(snapshot, repo)
    if not back:
        return KIT.bad(
            "5b",
            "the steward's word is recorded but nothing posts it back where the proposal "
            "came from" + ("" if routes else " — and there is no bridge to post it through "
                           "either (see rule 4a)")
            + ". A teammate who proposed on the host learns the answer only if someone "
              "copies it there by hand, which is the judgment-copying this clause forbids.",
            post_back_markers=back)
    return KIT.ok("5b", f"a path posts the steward's word back to the origin ({back}); that "
                        "it arrives in the steward's own words is beyond a static read",
                  post_back_markers=back)


# --------------------------------------------------------------------------- #
# Core 6 — freshness is never the steward's job                                #
# --------------------------------------------------------------------------- #
def arrival_mechanisms(snapshot):
    hay = served_text(snapshot)
    routes = " ".join(snapshot.api_routes())
    return [name for name, pattern in ARRIVES_BY_ITSELF
            if pattern.search(hay) or pattern.search(routes)]


def check_inbound_arrives(snapshot):
    found = arrival_mechanisms(snapshot)
    if not found:
        return KIT.bad(
            "6a",
            "nothing brings an inbound change in on its own: the app declares no webhook "
            "route, opens no live stream, and runs no timer that reloads the project's "
            "own data. Freshness is the steward's job in this body — they find out by "
            "reloading.",
            mechanisms=found)
    return KIT.ok("6a", f"an inbound change arrives without the steward asking, by {found}",
                  mechanisms=found)


def check_the_fallback_is_named(snapshot):
    said = FALLBACK_NAMED.search(served_text(snapshot))
    found = arrival_mechanisms(snapshot)
    if not said:
        detail = ("nothing on the surface says how this body stays fresh — not \"checked "
                  "every N minutes\", not \"webhook\", not \"polling\". The clause asks for "
                  "the fallback to be named rather than assumed, and a steward reading "
                  "this app cannot tell whether it is current.")
        if not found:
            detail += (" This follows from rule 6a: there is no mechanism to name — a "
                       "derived failure, not a second one.")
        return KIT.bad("6b", detail, mechanisms=found)
    return KIT.ok("6b", f"the surface names how it stays fresh in plain words "
                        f"({said.group(0)!r})", mechanisms=found)


# --------------------------------------------------------------------------- #
# Core 7 — the manager session is not in the hot path                          #
# --------------------------------------------------------------------------- #
def check_not_in_the_hot_path(snapshot, repo):
    if not repo:
        return KIT.skip("7", repo.missing)
    writer = repo.text("app/writes.py")
    if not writer:
        return KIT.bad("7", "the app has no writer module, so what a write goes through "
                            "cannot be read", repository=str(repo.root))
    reaching = [name for name, pattern in OTHER_TRANSPORTS if pattern.search(writer)]
    if reaching:
        return KIT.bad(
            "7",
            f"a write reaches {reaching} on its way to the repository, so the steward's "
            "action waits on a session rather than landing directly. The manager session "
            "is meant to learn of a write as an event and fold it into its next turn.",
            reaching=reaching)
    others = sorted(set(re.findall(r"subprocess\.run\(\s*\n?\s*\[\s*[\"']([a-z0-9_-]+)[\"']",
                                   writer)))
    started = [c for c in others if c != "git"]
    detail = ("no write reaches the manager session: the write path runs git and never "
              "sends a keystroke to a terminal session or opens a socket")
    if started:
        detail += (f". It does start {started} — a fresh headless session for one drafting "
                   "step, which is not the manager session and does not carry its state")
    return KIT.ok("7", detail, processes_started=others)


# --------------------------------------------------------------------------- #
# Core 8 — one steward per manager session                                     #
# --------------------------------------------------------------------------- #
def check_one_steward(snapshot):
    boot = snapshot.boot() or {}
    managers = boot.get("managers") or []
    if not managers:
        return KIT.bad("8a", "the app lists no manager session, so no steward is "
                             "registered against one")
    manager = snapshot.manager() or {}
    named = [m.get("id") for m in managers if any(STEWARD_FIELD.search(k) for k in m)]
    if STEWARD_FIELD.search(" ".join(manager)):
        named.append(manager.get("id"))
    if not named:
        signed_in = boot.get("user")
        return KIT.bad(
            "8a",
            f"no manager session names a steward, so whose word counts is inferred from "
            f"whoever is looking (this target answers as {signed_in!r}). The clause asks "
            "for it to be settled when the session is registered — everyone else is a "
            "teammate, whose proposals get the same reading and none of the authority.",
            managers=[m.get("id") for m in managers], signed_in_as=signed_in)
    return KIT.ok("8a", f"{len(set(named))} manager session(s) each name exactly one "
                        "steward, settled at registration",
                  stewards=sorted(set(named)))


# --------------------------------------------------------------------------- #
# Core 9 / 10 — the ordinary way, and no second surface                        #
# --------------------------------------------------------------------------- #
def check_ordinary_repository_change(snapshot, repo):
    if not repo:
        return KIT.skip("9", repo.missing)
    writer = repo.text("app/writes.py")
    if not writer:
        return KIT.bad("9", "the app has no writer module, so how a ratification is made "
                            "cannot be read", repository=str(repo.root))
    problems = []
    if not COMMIT_CALL.search(writer):
        problems.append("the write path never commits, so the text a word ratifies is not "
                        "carried into the record everybody already reads")
    if not CANDIDATE_SHAPE.search(writer):
        problems.append("the write path never produces the repository's own proposal shape "
                        "(`<document>.vN-candidate.md` beside the document), so a locked "
                        "document has no ordinary way to be proposed against")
    if "owner-ratifications-" not in writer:
        problems.append("the word itself is never recorded in the repository")
    if problems:
        return KIT.bad("9", "; ".join(problems), repository=str(repo.root))
    beside = [repo.rel(p) for p in repo.glob("contracts/*-candidate.md")]
    return KIT.ok("9", "a ratification is an ordinary repository change: the word is "
                       "recorded, the text is committed, and a proposal is a sibling "
                       f"`*-candidate.md` file ({len(beside)} in the repository now)",
                  candidates=beside)


def check_no_second_surface(snapshot):
    routes = list(snapshot.api_routes())
    grown = [r for r in routes if SECOND_SURFACE_ROUTE.search(r)]
    if grown:
        return KIT.bad(
            "10",
            f"the app answers {grown} — a second collaboration surface of its own. What a "
            "teammate needs to see is meant to be visible on the host, in the host's own "
            "terms; a tracker here is one more place they cannot reach.",
            routes=grown)
    return KIT.ok("10", f"none of the {len(routes)} routes this app declares is an issue "
                        "tracker, a document store or a review tool of its own; a comment "
                        "relayed to the host is rule 4a's bridge, not a surface kept here",
                  routes_read=len(routes))


# --------------------------------------------------------------------------- #
# driver                                                                       #
# --------------------------------------------------------------------------- #
def run_conformance(snapshot):
    repo = resolve_repo(snapshot, __file__)
    results = [
        check_git_is_the_protocol(snapshot, repo),          # 1
        check_no_manager_to_manager(snapshot, repo),        # 2
        check_three_origins_one_review(snapshot),           # 3
        check_the_bridge_exists(snapshot, repo),            # 4a
        KIT.skip("4b"),                                     # 4b
        check_answer_lands_in_the_record(snapshot, repo),   # 5a
        check_answer_returns_to_its_origin(snapshot, repo),  # 5b
        check_inbound_arrives(snapshot),                    # 6a
        check_the_fallback_is_named(snapshot),              # 6b
        check_not_in_the_hot_path(snapshot, repo),          # 7
        check_one_steward(snapshot),                        # 8a
        KIT.skip("8b"),                                     # 8b
        check_ordinary_repository_change(snapshot, repo),   # 9
        check_no_second_surface(snapshot),                  # 10
    ]
    return KIT.report(snapshot, results,
                      repository=str(repo.root) if repo else None,
                      repository_kind=repo.kind,
                      write_routes=snapshot.write_routes())


def main(argv=None) -> int:
    return run_cli("experience-collaboration-conformance",
                   "Assert experience-collaboration.v1 against the companion app and the "
                   "repository it is a body for.",
                   run_conformance, argv)


if __name__ == "__main__":
    raise SystemExit(main())
