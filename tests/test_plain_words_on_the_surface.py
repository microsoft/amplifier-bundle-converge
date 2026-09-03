"""Surface.v1 clause 8: evidence over claims, **in plain words**.

Every page is rendered against a project whose own words are as loud as they
get — a locked contract, a proposal filed under the old CANDIDATE name, a work
queue whose items talk about the ledger, lanes that write about worktrees and
GAP rows — and then walked for terms a colleague who is not an engineer would
have to look up.

Two spans of text are set aside, and they are the same two the shipped
`conformance/surface/run.py` sets aside, for the same stated reason:

* **inside a Details fold** — that is exactly where the contract puts
  technical detail (surface.v1 clause 8, documents.v1 clause 11);
* **inside text marked as the project's own words** (`class="doc"`) — a
  contract's prose, a work item's title, a lane's note. The app displays them;
  it did not write them. Their vocabulary is documents.v1's business, and
  scanning it here would report the *project's* wording as an app defect.

That second exemption is only honest if the app cannot use it to launder its
own copy, so `test_the_apps_own_copy_never_uses_an_internal_term` reads every
string literal in the web package, and `test_the_walk_catches_a_real_leak`
proves the walk can fail.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import stat
from html.parser import HTMLParser
from pathlib import Path

import pytest

from amplifier_converge import words

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE = REPO_ROOT / "conformance" / "surface" / "fixtures" / "app"
WEB_PACKAGE = REPO_ROOT / "src" / "amplifier_converge" / "web"


# --------------------------------------------------------------------------
# a project that says everything the wrong way
# --------------------------------------------------------------------------

#: A work queue whose items are written in the machinery's own words. Every
#: one of these titles is a documents.v1 clause 9 problem in the *project*;
#: the app's job is to show them as quotations, not to speak like them.
WORK_TRACKER_STUB = '''#!/usr/bin/env python3
import json, sys
args = sys.argv[1:]
if args[:1] == ["list"]:
    print(json.dumps({"items": [
        {"id": "kettle-1", "title": "Reconcile the ledger against the frozen contract",
         "status": "open"},
        {"id": "kettle-2", "title": "Retire the full-wave recipe from the bundle",
         "status": "held", "holder": "a worker session"},
        {"id": "kettle-3", "title": "CANDIDATE amendment: the disposition of a GAP row",
         "status": "blocked"},
        {"id": "kettle-4", "title": "Ship the cut-out", "status": "resolved",
         "resolution": "done"},
        {"id": "kettle-5", "title": "Stop the orchestrator spawning a second subagent",
         "status": "intake"}]}))
elif args[:1] == ["status"]:
    print(json.dumps({"project": "kettle", "total": 5, "ready": 1, "held": 1, "blocked": 1,
                      "deferred": 0, "resolved": 1, "resolved_24h": 1,
                      "oldest_unclaimed_age_seconds": 900}))
elif args[:1] == ["instances"]:
    print(json.dumps([{"project": "kettle", "ready": 1, "held": 1, "resolved_24h": 1},
                      {"project": "ledger", "ready": 2, "held": 0, "resolved_24h": 0}]))
else:
    print("{}")
'''

LEGACY_PROPOSAL = """# Retiring the retry clause

target: contracts/gate.v1.md

## The exact change

Remove "the lane retries three times" from clause 4.

## The evidence

A real outage: the retry loop hid a dead worktree for forty minutes.

## What does not change

Clause 5, and the conformance kit that checks it.
"""

#: Sentences added to a document after it was marked read, so the
#: what-changed view has the document's own words to show.
LOUD_SENTENCES = "The ledger disposition CONFORMS is recorded per clause, in YAML.\n"


def _lane_batch(root: Path) -> Path:
    """Two lanes: one finished with a loud note, one stopped with a louder one."""
    batch = root / "batch"
    for lane in ("w1-contracts", "w2-cut-out"):
        (batch / "lanes" / lane).mkdir(parents=True)
        (batch / "lanes" / lane / "lane.log").write_text("x", encoding="utf-8")
    (batch / ".width").write_text("3", encoding="utf-8")
    (batch / "manifest.tsv").write_text(
        "lane\tbranch\tworktree\tlog\tlaunched_at\n"
        + "".join(
            f"{lane}\tlane/{lane}\t{batch / 'lanes' / lane}\t"
            f"{batch / 'lanes' / lane / 'lane.log'}\t2026-09-02 10:00\n"
            for lane in ("w1-contracts", "w2-cut-out")
        ),
        encoding="utf-8",
    )
    (batch / "lanes" / "w1-contracts" / "DONE.json").write_text(
        json.dumps(
            {
                "status": "success",
                "summary": "Reconciled the ledger: 3 GAP rows and one VIOLATION row filed.",
            }
        ),
        encoding="utf-8",
    )
    (batch / "lanes" / "w2-cut-out" / "BLOCKED.md").write_text(
        "The full-wave recipe still points at the old bundle, so the worktree "
        "cannot be pruned and the tmux session id is stale.\n",
        encoding="utf-8",
    )
    return batch


@pytest.fixture
def loud_project(tmp_path, app_home, monkeypatch) -> Path:
    """The example project, with every kind of internal word the app can meet."""
    project = tmp_path / "loud-project"
    shutil.copytree(FIXTURE, project)

    locked = project / "contracts" / "half.v1.md"
    locked.write_text(
        locked.read_text(encoding="utf-8").replace("(DRAFT)", "(FROZEN 2026-09-02)"),
        encoding="utf-8",
    )
    (project / "contracts" / "CANDIDATE-retry-clause.md").write_text(
        LEGACY_PROPOSAL, encoding="utf-8"
    )

    stub_dir = tmp_path / "bin"
    stub_dir.mkdir()
    stub = stub_dir / "amplifier-work-tracker"
    stub.write_text(WORK_TRACKER_STUB, encoding="utf-8")
    stub.chmod(stub.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    monkeypatch.setenv("PATH", f"{stub_dir}{os.pathsep}{os.environ.get('PATH', '')}")
    return project


@pytest.fixture
def loud_client(loud_project, tmp_path):
    from fastapi.testclient import TestClient

    from amplifier_converge.web.app import create_app

    batch = _lane_batch(tmp_path)
    app = create_app(loud_project, "kettle", batch_dir=batch, include_remote_proposals=False)
    client = TestClient(app)

    # Read a document, then change it — so what-changed has real sentences of
    # the document's own to show, added and removed.
    client.post("/direction/gate.v1/mark-read")
    gate = loud_project / "contracts" / "gate.v1.md"
    text = gate.read_text(encoding="utf-8")
    first, _, rest = text.partition("\n\n")
    gate.write_text(f"{first}\n\n{LOUD_SENTENCES}\n{rest}", encoding="utf-8")
    return client


# --------------------------------------------------------------------------
# reading a page the way a person does
# --------------------------------------------------------------------------


class OwnWords(HTMLParser):
    """The words the page itself says: everything except a Details fold and
    everything except text marked as the project's own."""

    VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link",
            "meta", "param", "source", "track", "wbr"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.own: list[str] = []
        self.folded: list[str] = []
        self.quoted: list[str] = []
        self._stack: list[tuple[str, bool, bool, bool]] = []
        self._details = 0
        self._quoted = 0
        self._code = 0

    def handle_starttag(self, tag, attrs):
        if tag in self.VOID:
            return
        classes = dict((k, v or "") for k, v in attrs).get("class", "").split()
        is_details = tag == "details"
        is_quoted = "doc" in classes or "docpane" in classes
        is_code = tag in ("script", "style", "title")
        self._stack.append((tag, is_details, is_quoted, is_code))
        self._details += is_details
        self._quoted += is_quoted
        self._code += is_code

    def handle_endtag(self, tag):
        for index in range(len(self._stack) - 1, -1, -1):
            if self._stack[index][0] == tag:
                for _, is_details, is_quoted, is_code in self._stack[index:]:
                    self._details -= is_details
                    self._quoted -= is_quoted
                    self._code -= is_code
                del self._stack[index:]
                return

    def handle_data(self, data):
        if not data.strip():
            return
        if self._code:
            return
        if self._details:
            self.folded.append(data.strip())
        elif self._quoted:
            self.quoted.append(data.strip())
        else:
            self.own.append(data.strip())


def own_words(html: str) -> str:
    reader = OwnWords()
    reader.feed(html)
    return " ".join(reader.own)


def every_page(client, project: Path) -> list[str]:
    """Every page this app can render, from the routes it actually declares."""
    from amplifier_converge.reading.documents import read_direction
    from amplifier_converge.reading.proposals import read_proposals

    pages = ["/", "/direction", "/operation", "/direction/nowhere"]
    for document in read_direction(project).value:
        pages.append(f"/direction/{document.slug}")
        for paragraph in document.paragraphs[:4]:
            pages.append(f"/direction/{document.slug}/ask?anchor={paragraph.anchor}")
    pages.append("/direction/proposal?key=nothing-by-that-name")
    for proposal in read_proposals(project, include_remote=False).value:
        pages.append(f"/direction/proposal?key={proposal.key}")
    return pages


# --------------------------------------------------------------------------
# the walk
# --------------------------------------------------------------------------


def test_no_internal_word_reaches_the_page(loud_client, loud_project):
    offenders: list[str] = []
    for page in every_page(loud_client, loud_project):
        text = own_words(loud_client.get(page).text)
        for term in words.internal_terms_in(text):
            offenders.append(f"{page} says “{term}” in its own words")
    assert not offenders, "\n".join(offenders)


def test_the_loud_words_are_on_the_page_and_merely_marked(loud_client, loud_project):
    """The walk must not pass by hiding the project from the reader.

    Every loud word the project uses still reaches the screen — quoted, or
    behind a fold. A page that simply dropped them would pass the check above
    and fail the steward.
    """
    seen: set[str] = set()
    for page in every_page(loud_client, loud_project):
        reader = OwnWords()
        reader.feed(loud_client.get(page).text)
        shown = " ".join(reader.quoted + reader.folded)
        seen.update(words.internal_terms_in(shown))
    for term in ("ledger", "recipe", "worktree", "GAP", "CANDIDATE"):
        assert term in seen, f"the project says “{term}” and the page shows it nowhere"


def test_the_walk_catches_a_real_leak():
    """A check nobody can make fail proves nothing."""
    leaking = (
        "<main><p>Reconcile the ledger before the recipe runs.</p>"
        "<details><summary>Details</summary><p>worktree /tmp/x</p></details>"
        '<p class="doc">A contract may say GAP if it likes.</p></main>'
    )
    found = words.internal_terms_in(own_words(leaking))
    assert "ledger" in found and "recipe" in found
    assert "worktree" not in found, "a Details fold is set aside"
    assert "GAP" not in found, "the project's own words are set aside"


def test_every_page_the_app_declares_is_walked(loud_client, loud_project):
    """A new page cannot quietly escape the check."""
    # `/openapi.json` is the machine-readable description the web framework
    # adds for itself. It is not a page anybody reads, and nothing links to it.
    declared = {
        route.path
        for route in loud_client.app.routes
        if "GET" in (getattr(route, "methods", set()) or set())
        and getattr(route, "path", "").startswith("/")
        and route.path != "/openapi.json"
    }
    walked = set()
    for page in every_page(loud_client, loud_project):
        path = page.split("?")[0]
        if path == "/" or path in ("/direction", "/operation"):
            walked.add(path)
        elif path.endswith("/ask"):
            walked.add("/direction/{slug}/ask")
        elif path.startswith("/direction/proposal"):
            walked.add("/direction/proposal")
        else:
            walked.add("/direction/{slug}")
    assert declared <= walked, f"never walked: {sorted(declared - walked)}"


def test_every_page_answers(loud_client, loud_project):
    for page in every_page(loud_client, loud_project):
        response = loud_client.get(page)
        assert response.status_code == 200, f"{page} answered {response.status_code}"


# --------------------------------------------------------------------------
# the map, and the honesty of the exemption
# --------------------------------------------------------------------------


def test_one_map_turns_every_internal_state_into_a_surface_word():
    from amplifier_converge.reading.documents import Document
    from amplifier_converge.reading.lanes import Lane
    from amplifier_converge.reading.queue import WorkItem

    document = Document(
        slug="x", path=Path("x.md"), relpath="x.md", title="X",
        state="FROZEN 2026-09-02", kind="contract", text="",
    )
    assert document.state_word == "Locked"
    assert WorkItem(id="1", title="t", status="held", holder="", resolution="").state_word == "Working"
    assert WorkItem(id="1", title="t", status="wat", holder="", resolution="").state_word == "Can't check"

    lane = Lane(
        name="w1", branch="b", worktree="w", launched_at="", log_path="l",
        seconds_since_write=10.0, finished=False, blocked=True, outcome="", summary="",
    )
    assert lane.liveness == "Stuck"
    for word in (document.state_word, lane.liveness):
        assert words.is_surface_word(word), f"“{word}” is not one of the plain words"


def test_every_state_word_shown_is_one_of_the_plain_words(loud_client, loud_project):
    """Whatever a page puts in a state chip or mark came from the map."""
    for page in every_page(loud_client, loud_project):
        html = loud_client.get(page).text
        for match in re.finditer(r'<span class="(?:chip|mark|state)[^"]*">([^<]+)</span>', html):
            shown = match.group(1).strip()
            assert words.is_surface_word(shown), f"{page} shows the state “{shown}”"


#: The modules that write words onto a page. `styles.py` is a stylesheet — the
#: `gap` in `gap:8px` is a layout property, not a word anyone reads.
SPEAKING_MODULES = ("pages.py", "app.py", "markup.py")

#: A Details fold, wherever it is written in the source.
FOLD = re.compile(r"<details.*?</details>", re.S)

#: A note to whoever reads the source. Not copy.
COMMENT = re.compile(r"^\s*#.*$", re.M)


def test_the_apps_own_copy_never_uses_an_internal_term():
    """The marking cannot be used to launder the page's own words.

    Text marked as the project's own is set aside by the walk above, which
    would be a loophole if the page could mark its *own* copy that way. So
    this reads the copy at its source instead: the modules that write words
    onto a page, with their Details folds — where technical words belong —
    taken out first.
    """
    offenders = []
    for name in SPEAKING_MODULES:
        source = (WEB_PACKAGE / name).read_text(encoding="utf-8")
        spoken = COMMENT.sub(" ", FOLD.sub(" ", source))
        for term in words.internal_terms_in(spoken):
            offenders.append(f"{name} says “{term}” in its own copy")
    assert not offenders, "\n".join(offenders)


# --------------------------------------------------------------------------
# the shipped kit's own verdict, on the app's own pages
# --------------------------------------------------------------------------


def _surface_kit():
    """The kit as shipped, imported from where it lives. Read, never changed."""
    import importlib.util

    path = REPO_ROOT / "conformance" / "surface" / "run.py"
    spec = importlib.util.spec_from_file_location("surface_kit", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_shipped_kit_reports_rule_8c_pass_on_every_page(loud_client, loud_project, tmp_path):
    """`conformance/surface/run.py`, run at the app rather than at the mockup.

    Rule 8c is the one this walks alongside: *no internal vocabulary outside
    Details folds*, the surface kit's row for surface.v1 clause 8. The kit is
    the contract's own runnable definition, so its verdict — not this file's
    opinion — is what settles the question.

    Select it by the id the kit publishes today. That row was numbered `5`
    until 2026-09-03, when the steward anchored kit rule ids to their
    contract's Core clauses; `5` now judges Core 5 (proposals) and SKIPs on a
    page with no proposal on it. An id that still resolves — to a different
    rule — is the failure mode conformance/README.md names, so keep this in
    step with that kit's README table.
    """
    kit = _surface_kit()
    rendered = tmp_path / "rendered"
    rendered.mkdir()

    verdicts = []
    for number, page in enumerate(every_page(loud_client, loud_project)):
        target = rendered / f"page-{number}.html"
        target.write_text(loud_client.get(page).text, encoding="utf-8")
        report = kit.run_conformance(target)
        rule = next(r for r in report["results"] if r["rule"] == "8c")
        verdicts.append(f"{page}: {rule['status']} — {rule['detail']}")
        assert rule["status"] == "PASS", f"{page}: {rule['detail']}"
    assert verdicts
