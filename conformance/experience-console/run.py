# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""experience-console.v1 conformance kit — "the Manager Console keeps its promises".

Point it at the companion app — the running server, or a snapshot captured from
it — and it asserts `contracts/experience-console.v1.md` against what the app
actually serves: where the console sits in the served shell, what the client
does with it, what the app's own route table reaches, and what its stylesheet
does to it at a small width.

    uv run conformance/experience-console/run.py http://127.0.0.1:8788
    uv run conformance/experience-console/run.py <a --capture directory>

Stdlib only, and **no browser is launched**.

Numbering
---------
Rule ids anchor to the contract's **Core clause** numbers: rule 7 judges Core 7.
Every one of the ten Core clauses has a row, and
`test_every_core_clause_has_a_row` fails if one does not.

What a static read buys, and what it does not
---------------------------------------------
Most of this contract is structural, which is the happy case for a static read:
whether the console is a pane beside the two places or a third place, whether
anything that needs a steward's word is reachable only from it, whether the
console's own form can reach the ratification write, whether the stylesheet
turns it into a tray at a small width.

Two things it cannot do, and says so rather than pretending: it never proves a
line typed in the console arrives in the manager session (that is a live round
trip — rule 3 judges only whether a path for it exists at all), and it never
judges a rendered layout (rule 4 reads the stylesheet's rules, not a viewport).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from kitreport import Kit, run_cli  # noqa: E402

CONTRACT = "contracts/experience-console.v1.md"

KIT = Kit(
    "experience-console.v1",
    CONTRACT,
    rules=[
        ("1", 1, "a_pane_beside_the_places_not_a_third_place",
         "the console is a pane beside Direction and Operation, never a third place"),
        ("2", 2, "it_carries_the_session_as_it_already_runs",
         "the pane embeds the live manager session through the tmux connector"),
        ("3", 3, "what_you_type_is_what_the_session_receives",
         "one console, one manager session — and it IS that session"),
        ("4", 4, "a_pane_when_wide_a_tray_when_small",
         "wide screen: a resizable pane; small screen: a sliding tray"),
        ("5", 5, "watch_session_reuses_this_pane",
         "watching a lane opens here, and leaving returns the manager conversation"),
        ("6", 6, "the_console_is_never_the_dashboard",
         "nothing in Operation requires reading the console to make sense"),
        ("7", 7, "nothing_needing_your_word_arrives_only_here",
         "every decision reaches you through the short list, not only through the console"),
        ("8", 8, "the_console_never_ratifies",
         "a word typed here is a message, never a ratification"),
        ("9", 9, "not_a_native_chat_in_v1",
         "it is not a native chat in V1, and the app says so"),
        ("10", 10, "one_managers_own_work_and_nothing_else",
         "it shows one manager session's own work and reaches nothing else"),
    ],
)

#: Core 1 — the umbrella's two places, and only two.
PLACES = ("direction", "operation")

#: Core 8 — the four words that would make a console message a ratification.
ANSWER_WORDS = ("ratified", "ratified with edits", "declined", "later")


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
    m = re.search(rf"function\s+{re.escape(name)}\s*\(", script)
    return _brace_block(script, m.start(), window) if m else ""


def handler_body(script: str, marker: str, window: int = 900) -> str:
    at = script.find(marker)
    return _brace_block(script, at, window) if at >= 0 else ""


def reaches_a_write(body: str, tokens) -> bool:
    if not body:
        return False
    if re.search(r"method:\s*['\"]POST['\"]", body, re.I):
        return True
    code = strip_string_literals(body)
    return any(re.search(rf"\w*{re.escape(t)}\w*\s*\(", code, re.I) for t in tokens)


def served(snapshot) -> str:
    return snapshot.text("/") + "\n" + snapshot.script_text()


def console_node(snapshot):
    shell = snapshot.html("/")
    return (shell.first(node_id="managerConsole")
            or shell.first(cls="manager-console")
            or next((n for n in shell.walk()
                     if "console" in (n.attrs.get("aria-label", "") or "").lower()), None))


# --------------------------------------------------------------------------- #
# rules                                                                        #
# --------------------------------------------------------------------------- #
def check_pane_not_a_place(snapshot):
    shell = snapshot.html("/")
    console = console_node(snapshot)
    if console is None:
        return KIT.bad("1", "the served shell carries no Manager Console at all")
    switch = shell.first(node_id="workspaceSwitch") or shell.first(cls="workspace-switch")
    tabs = [t.text().strip().lower() for t in switch.find(tag="button")] if switch else []
    problems = []
    if not switch:
        problems.append("the shell has no place switch to judge the console against")
    else:
        extra = [t for t in tabs if not any(p in t for p in PLACES)]
        if extra:
            problems.append(f"the place switch offers {tabs} — the console is a third place "
                            f"when it appears here ({extra})")
        if len(tabs) != 2:
            problems.append(f"the place switch offers {len(tabs)} places, not two")
    for place in ("directionView", "operationView"):
        if console.inside(node_id=place):
            problems.append(f"the console is nested inside #{place}, so switching places "
                            "takes it away")
    # Switching places must not close, restart, or empty the console.
    top = snapshot.script_named("render/top.js") or ""
    if re.search(r"consoleOpen\s*=|detach\(\)|consoleBody\b", top):
        problems.append("the place-switch renderer touches the console's open state or its "
                        "body, so switching does not leave it as it was")
    if problems:
        return KIT.bad("1", "; ".join(problems), places=tabs)
    return KIT.ok("1", f"the console is a pane beside the two places ({tabs}) and the place "
                       "switch neither lists it nor disturbs it",
                  places=tabs)


def check_carries_the_session(snapshot):
    manager = snapshot.manager() or {}
    named = manager.get("managerTmux") or manager.get("tmux") or manager.get("manager_tmux")
    routes = [p for p in snapshot.api_routes() if "/tmux" in p]
    attaches = bool(re.search(r"ConvergeTmux|attach\(", served(snapshot)))
    problems = []
    if not named:
        problems.append("the manager session names no live terminal session for the pane to "
                        "carry")
    if not routes:
        problems.append("the app answers no connector route, so nothing can reach a running "
                        "session")
    if not attaches:
        problems.append("the console never attaches to a session")
    if problems:
        return KIT.bad("2", "; ".join(problems), connector_routes=routes)
    return KIT.ok("2", f"the pane embeds the manager session as it already runs "
                       f"({named}) through the connector at {routes}",
                  connector_routes=routes, session=str(named))


def check_typing_reaches_the_session(snapshot):
    shell = snapshot.html("/")
    console = console_node(snapshot)
    if console is None:
        return KIT.bad("3", "the served shell carries no console")
    inputs = console.find(tag="input") + console.find(tag="textarea")
    if not inputs:
        return KIT.bad("3", "the console offers nothing to type into, so what you type "
                            "cannot be what the manager session receives")
    disabled = [i.describe() for i in inputs if "disabled" in i.attrs]
    submit = [b for b in console.find(tag="button") if b.attrs.get("type") == "submit"]
    dead_submit = [b.describe() for b in submit if "disabled" in b.attrs]
    send_route = [p for p, m in snapshot.api_routes().items()
                  if "POST" in m and re.search(r"tmux|console|send|keys|message", p, re.I)]
    problems = []
    if disabled:
        problems.append(f"the console's input is disabled ({disabled})")
    if dead_submit:
        problems.append(f"its send control is disabled ({dead_submit})")
    if not send_route:
        problems.append("the app answers no route that carries a keystroke to the session, so "
                        "there is no path for a typed line to arrive")
    if problems:
        return KIT.bad(
            "3",
            "; ".join(problems) + " — the pane shows the session but is not it. Whether a "
            "line ARRIVES is a live round trip this kit does not attempt; it judges only "
            "whether a path exists at all",
            send_routes=send_route)
    return KIT.ok("3", f"the console takes input and a route carries it to the session "
                       f"({send_route}); that the line arrives is a live round trip beyond "
                       "this kit",
                  send_routes=send_route)


def check_pane_when_wide_tray_when_small(snapshot):
    css = snapshot.style_text()
    if not css.strip():
        return KIT.skip("4", "the target served no stylesheet, so neither the pane nor the "
                             "tray can be read; point the kit at the running app")
    small = re.search(r"@media[^{]*max-width:\s*(\d+)px[^{]*\{(.*?)\n\}", css, re.S)
    tray_rules = re.findall(r"@media[^{]*max-width[^{]*\{[^@]*?\.manager-console\s*\{([^}]*)\}",
                            css, re.S)
    tray = any(re.search(r"position:\s*fixed|transform:\s*translate", block)
               for block in tray_rules)
    dismiss = bool(re.search(r"consoleClose|console-closed", served(snapshot)))
    resizable = bool(re.search(r"\.manager-console[^{]*\{[^}]*resize:\s*(horizontal|both)", css)
                     or re.search(r"console-(resize|handle|splitter)|data-console-resize",
                                  served(snapshot)))
    problems = []
    if not tray:
        problems.append("no stylesheet rule turns the console into a tray at a small width")
    if not dismiss:
        problems.append("nothing dismisses it, so it cannot get out of the way on demand")
    if not resizable:
        problems.append("no rule or control makes the pane resizable on a wide screen — the "
                        "shape may follow the platform, but the behaviour does not change")
    if problems:
        return KIT.bad("4", "; ".join(problems)
                       + ". Read from the stylesheet's rules; a rendered layout at two widths "
                         "is not judged here",
                       tray=tray, dismissible=dismiss, resizable=resizable)
    return KIT.ok("4", "a resizable pane on a wide screen and a dismissible sliding tray at a "
                       "small one, read from the stylesheet's own rules",
                  tray=tray, dismissible=dismiss, resizable=resizable)


def check_watch_reuses_the_pane(snapshot):
    script = snapshot.script_text()
    watch = function_body(script, "watchLane")
    if not watch:
        return KIT.bad("5", "nothing watches a lane, so the pane cannot be reused for it")
    into_console = bool(re.search(r"consoleContext|consoleTarget|renderConsole", watch))
    new_place = bool(re.search(r"screen\s*=|workspace\s*=|location\.href", watch))
    back = bool(re.search(r"function\s+showManagerConsole", script))
    restores = bool(re.search(r"function\s+showManagerConsole[\s\S]{0,400}?consoleContext\s*=\s*'manager'",
                              script))
    problems = []
    if not into_console:
        problems.append("watching a lane does not open in this pane")
    if new_place:
        problems.append("watching a lane changes place rather than reusing the pane")
    if not (back and restores):
        problems.append("leaving a watched lane does not return the manager conversation")
    if problems:
        return KIT.bad("5", "; ".join(problems))
    return KIT.ok("5", "watching a lane opens in this pane, and leaving it puts the manager "
                       "conversation back where it stood")


def check_never_the_dashboard(snapshot):
    shell = snapshot.text("/")
    operation = snapshot.script_named("render/operation.js") or ""
    op_view = snapshot.html("/").first(node_id="operationView")
    tells_you_to_read_it = re.search(
        r"(see|open|read|check|watch)\s+the\s+(manager\s+)?console", shell + operation, re.I)
    if tells_you_to_read_it:
        return KIT.bad("6", "Operation sends the reader to the console to make sense of it: "
                            f"{tells_you_to_read_it.group(0)!r}")
    if op_view is None:
        return KIT.bad("6", "the shell carries no Operation view, so the operation is not "
                            "understood anywhere but the console")
    own_reading = [name for name, pat in (
        ("the plan", r"wavesGrid"), ("the lanes", r"lanesGrid"),
        ("the return brief", r"returnBrief"), ("the flow", r"throughput"),
        ("confidence", r"confidence")) if re.search(pat, shell, re.I)]
    if len(own_reading) < 4:
        return KIT.bad("6", f"Operation carries only {own_reading}, so a reader would have to "
                            "fall back to raw session activity to understand the operation",
                       operation_shows=own_reading)
    return KIT.ok("6", "Operation is understood on its own terms (" + ", ".join(own_reading)
                       + "), and nothing sends the reader to the console",
                  operation_shows=own_reading)


def check_nothing_needing_your_word_only_here(snapshot):
    shell = snapshot.text("/")
    console = console_node(snapshot)
    short_list = bool(re.search(r"needsYouButton|need your word|needsYouCount", shell, re.I))
    needs_route = [p for p in snapshot.api_routes() if "/needs" in p]
    in_console = []
    if console is not None:
        for node in console.walk():
            if "data-decision" in node.attrs or re.search(
                    r"\b(ratify|decline)\b", node.text(), re.I):
                in_console.append(node.describe())
    problems = []
    if not short_list:
        problems.append("the shell has no short list of what needs your word")
    if not needs_route:
        problems.append("the app answers no route listing what needs your word")
    if in_console:
        problems.append(f"a decision is offered inside the console ({in_console[:3]}), so a "
                        "steward who never opens it would miss one")
    if problems:
        return KIT.bad("7", "; ".join(problems), needs_routes=needs_route)
    return KIT.ok("7", f"what needs your word arrives through the short list and {needs_route}, "
                       "never only through the console",
                  needs_routes=needs_route)


def check_console_never_ratifies(snapshot):
    script = snapshot.script_text()
    console = console_node(snapshot)
    form = None
    if console is not None:
        form = console.first(tag="form")
    body = handler_body(script, "consoleForm")
    decision_tokens = {t for t in write_tokens(snapshot) if re.search(r"decision|ratif", t, re.I)}
    reaches_decision = reaches_a_write(body, decision_tokens) if decision_tokens else False
    words_in_console = []
    if console is not None:
        text = console.text().lower()
        words_in_console = [w for w in ANSWER_WORDS if w in text]
    problems = []
    if form is None and console is not None:
        problems.append("the console has no form to judge")
    if reaches_decision:
        problems.append("the console's own submit reaches the ratification write, so a word "
                        "typed here can be read as a decision")
    if words_in_console:
        problems.append(f"the console offers the answer words themselves ({words_in_console})")
    if problems:
        return KIT.bad("8", "; ".join(problems))
    return KIT.ok("8", "the console's submit reaches no ratification write and offers none of "
                       "the answer words — a word typed here is a message")


def check_not_a_native_chat(snapshot):
    shell = snapshot.text("/")
    says_so = re.search(r"read-only in this version|not a chat|read only in this version",
                        shell, re.I)
    script = snapshot.script_text()
    # Nothing else may be built to depend on the console being a conversation.
    depends = re.search(r"(renderDirection|renderOperation|renderHome)[\s\S]{0,300}?"
                        r"consoleInput|consoleInput[\s\S]{0,120}?(decision|ratif)", script, re.I)
    problems = []
    if not says_so:
        problems.append("the app never says the console is not a conversation in this version, "
                        "so a steward is left to discover it by typing")
    if depends:
        problems.append("something outside the console depends on it being a chat: "
                        f"{depends.group(0)[:60]!r}")
    if problems:
        return KIT.bad("9", "; ".join(problems))
    return KIT.ok("9", f"the app says so in its own words ({says_so.group(0)!r}) and nothing "
                       "is built to depend on the console being a native chat")


def check_reaches_nothing_else(snapshot):
    manager = snapshot.manager() or {}
    op = snapshot.operation() or {}
    own = {str(manager.get("managerTmux") or manager.get("tmux") or "")}
    own |= {f"{(l.get('tmux') or {}).get('socket')}:{(l.get('tmux') or {}).get('session')}"
            for l in (op.get("lanes") or []) if l.get("tmux")}
    own.discard(":")
    enumerating = sorted(p for p in snapshot.api_routes()
                         if re.search(r"/tmux/sessions|/sessions$", p))
    script = snapshot.script_text()
    client_enumerates = bool(re.search(r"/tmux/sessions|listSessions", script))
    if enumerating:
        return KIT.bad(
            "10",
            f"the app answers {enumerating}, which enumerates every terminal session on a "
            "socket — the machine's other sessions, checkouts and queues are reachable merely "
            f"because they exist. The client itself calls it: {client_enumerates}. The console "
            f"pane shows only this manager's own targets ({len(own)} of them), so the defect is "
            "the reach, not the display",
            enumerating_routes=enumerating, client_calls_it=client_enumerates,
            own_targets=len(own))
    if not own:
        return KIT.bad("10", "the console names no target of its own, so what it shows cannot "
                             "be traced to this manager session")
    return KIT.ok("10", f"the console reaches only this manager session's own targets "
                        f"({len(own)}), and no route enumerates anything else",
                  own_targets=len(own))


# --------------------------------------------------------------------------- #
# driver                                                                       #
# --------------------------------------------------------------------------- #
def run_conformance(snapshot):
    results = [
        check_pane_not_a_place(snapshot),                    # 1
        check_carries_the_session(snapshot),                 # 2
        check_typing_reaches_the_session(snapshot),          # 3
        check_pane_when_wide_tray_when_small(snapshot),      # 4
        check_watch_reuses_the_pane(snapshot),               # 5
        check_never_the_dashboard(snapshot),                 # 6
        check_nothing_needing_your_word_only_here(snapshot),  # 7
        check_console_never_ratifies(snapshot),              # 8
        check_not_a_native_chat(snapshot),                   # 9
        check_reaches_nothing_else(snapshot),                # 10
    ]
    return KIT.report(snapshot, results, write_routes=snapshot.write_routes())


def main(argv=None) -> int:
    return run_cli("experience-console-conformance",
                   "Assert experience-console.v1 against the companion app.",
                   run_conformance, argv)


if __name__ == "__main__":
    raise SystemExit(main())
