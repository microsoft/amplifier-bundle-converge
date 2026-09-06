"""Surface.v1 clause 8: evidence over claims, **in plain words**.

The walk this file used to run rendered every page of the earlier
server-rendered page against a project whose own words were as loud as they get,
then read the result for terms a colleague who is not an engineer would have to
look up. That page was retired on 2026-09-06 on the steward's word, so the seven
assertions that needed a rendered page went with it — including the one that ran
the shipped `conformance/_superseded/surface/run.py` rule 8c against it, which
ledger row CVG-066 names as its probe. The kit itself stays where it is.

What remains is the part that never needed a page: the one map that turns every
internal state into a surface word, and the proof that the walk which reads a
page can actually fail. Both are the library's promises, not the page's.
"""

from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path

from amplifier_converge import words


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
