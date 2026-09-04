"""Surface.v1 clause 8, first half: the app says whether a promise is **kept**.

`Draft` and `Locked` answer a different question — where a promise stands as a
document. Clause 8 asks for the other one, in five fixed words: *Kept · Not yet
· Broken · Pinned open · Can't check*. Before this, Direction chipped every
promise `Draft` and a steward could not see whether any of them was being kept
(converge-6s8, and the shipped kit's rule 8b).

Three things are proved here, in order:

1. the fold from the project's own clause-by-clause record onto one word, with
   **every branch of it exercised**, including the three separate ways the
   answer is honestly *Can't check*;
2. that no word from the machinery can reach the page even if the record grows
   a term nobody has translated;
3. that Direction actually renders the word — the whole point, and the thing a
   green unit test would otherwise let us claim without.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from amplifier_converge import words
from amplifier_converge.reading.kept import (
    NO_RECORD,
    NOTHING_WATCHED,
    RELPATH,
    Standing,
    fold,
    read_promises,
    standing_of,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE = REPO_ROOT / "conformance" / "_superseded" / "surface" / "fixtures" / "app"


# --------------------------------------------------------------------------
# a record, written the way the real one is written
# --------------------------------------------------------------------------

#: The awkward parts of the real file, on purpose: a long run of the project's
#: own prose that contains a line reading like a field (`disposition:` inside
#: the notes), a nested list whose items carry a `file:` of their own, and a
#: block with no promise attached at all.
RECORD = """\
# A record of whether each promise is being kept.

- id: SYNC-000
  title: file hashes pinned
  kind: sync
  pins:
    - file: contracts/kept.v1.md
      sha256: abc123
  notes: >
    This block names no promise and must be counted against none.
    disposition: CONFORMS
    file: contracts/broken.v1.md

- id: R-001
  contract:
    file: contracts/kept.v1.md
    clause: "Core 1"
    quote: |
      Every part of this is true today.
      disposition: VIOLATION
  disposition: CONFORMS
  notes: >
    Ran and passed.

- id: R-002
  contract:
    file: contracts/kept.v1.md
    clause: "Core 2"
  disposition: CONFORMS

- id: R-003
  contract:
    file: contracts/broken.v1.md
    clause: "Core 1"
  disposition: CONFORMS

- id: R-004
  contract:
    file: contracts/broken.v1.md
    clause: "Core 2"
  disposition: VIOLATION

- id: R-005
  contract:
    file: contracts/broken.v1.md
    clause: "Core 3"
  disposition: GAP

- id: R-006
  contract:
    file: contracts/notyet.v1.md
    clause: "Core 1"
  disposition: GAP

- id: R-007
  contract:
    file: contracts/pinned.v1.md
    clause: "Core 1"
  disposition: OPEN-PINNED

- id: R-008
  contract:
    file: contracts/unsure.v1.md
    clause: "Core 1"
  disposition: NOT-ASSERTABLE
"""


@pytest.fixture
def recorded(tmp_path) -> Path:
    project = tmp_path / "recorded"
    (project / RELPATH.parent).mkdir(parents=True)
    (project / RELPATH).write_text(RECORD, encoding="utf-8")
    return project


# --------------------------------------------------------------------------
# 1. the fold, branch by branch
# --------------------------------------------------------------------------


def test_every_clause_kept_reads_kept():
    assert fold(["CONFORMS", "CONFORMS", "CONFORMS"]) == "Kept"


def test_one_broken_clause_breaks_the_promise():
    """The worst honest word wins. A promise is not kept on average."""
    assert fold(["CONFORMS", "CONFORMS", "VIOLATION"]) == "Broken"


def test_broken_outranks_not_yet():
    """Both are red; only one of them says something is untrue *today*."""
    assert fold(["GAP", "VIOLATION"]) == "Broken"


def test_a_part_not_built_yet_reads_not_yet():
    assert fold(["CONFORMS", "GAP"]) == "Not yet"


def test_held_open_on_purpose_reads_pinned_open():
    assert fold(["OPEN-PINNED"]) == "Pinned open"
    assert fold(["CONFORMS", "OPEN-PINNED"]) == "Pinned open", (
        "a promise part of which is deliberately open is not simply kept"
    )


def test_nothing_checkable_reads_cant_check():
    """AGENTS.md rule 3: a check that cannot run never reports a pass."""
    assert fold(["NOT-ASSERTABLE"]) == "Can't check"
    assert fold(["CONFORMS", "NOT-ASSERTABLE"]) == "Can't check", (
        "one clause nobody can check is enough to stop us saying the whole "
        "promise is kept"
    )


def test_nothing_at_all_reads_cant_check():
    assert fold([]) == "Can't check"
    assert fold(None) == "Can't check"


def test_a_word_nobody_translated_reads_cant_check():
    """The map is the only way onto the page, so an untranslated term is
    an admission rather than a leak."""
    assert fold(["SOMETHING-NOBODY-HAS-TAUGHT-US"]) == "Can't check"


def test_the_fold_only_ever_says_one_of_the_five_words():
    said = {
        fold(mix)
        for mix in (
            [],
            ["CONFORMS"],
            ["GAP"],
            ["VIOLATION"],
            ["DIVERGED"],
            ["OPEN-PINNED"],
            ["NOT-ASSERTABLE"],
            ["EXCLUDED"],
            ["what"],
            ["CONFORMS", "GAP", "VIOLATION", "OPEN-PINNED", "NOT-ASSERTABLE"],
        )
    }
    assert said <= set(words.CONTRACT_STATES), sorted(said - set(words.CONTRACT_STATES))
    assert "Broken" in said and "Kept" in said, "a fold nobody can move proves nothing"


# --------------------------------------------------------------------------
# 2. reading the project's record
# --------------------------------------------------------------------------


def test_each_promise_gets_the_word_its_own_clauses_earn(recorded):
    reading = read_promises(recorded)
    assert reading.available
    got = {name: standing.word for name, standing in reading.value.items()}
    assert got == {
        "contracts/kept.v1.md": "Kept",
        "contracts/broken.v1.md": "Broken",
        "contracts/notyet.v1.md": "Not yet",
        "contracts/pinned.v1.md": "Pinned open",
        "contracts/unsure.v1.md": "Can't check",
    }


def test_the_projects_own_prose_is_skipped_whole_not_half_read(recorded):
    """A sentence inside a quoted block that looks like a field is prose.

    `contracts/kept.v1.md` quotes a clause containing the line
    `disposition: VIOLATION`, and a block naming no promise carries both a
    `disposition:` and a `file:` in its notes. Read half-carefully, either
    would break a promise that is being kept, or invent one that is not there.
    """
    reading = read_promises(recorded)
    assert reading.value["contracts/kept.v1.md"].word == "Kept"
    assert reading.value["contracts/kept.v1.md"].clauses == 2
    assert set(reading.value) == {
        "contracts/kept.v1.md",
        "contracts/broken.v1.md",
        "contracts/notyet.v1.md",
        "contracts/pinned.v1.md",
        "contracts/unsure.v1.md",
    }, "a nested list of pinned files was mistaken for a promise"


def test_a_project_with_no_record_says_so_rather_than_guessing(tmp_path):
    reading = read_promises(tmp_path)
    assert not reading.available
    assert reading.value == {}
    assert reading.note == NO_RECORD
    assert standing_of("contracts/anything.v1.md", reading.value).word == "Can't check"


def test_a_record_that_cannot_be_read_is_never_a_pass(tmp_path):
    project = tmp_path / "shut"
    (project / RELPATH.parent).mkdir(parents=True)
    path = project / RELPATH
    path.write_text(RECORD, encoding="utf-8")
    path.chmod(0o000)
    if os.access(path, os.R_OK):  # running as a user nothing can be hidden from
        pytest.skip("this user can read a file with no read permission")
    try:
        reading = read_promises(project)
    finally:
        path.chmod(0o644)
    assert not reading.available
    assert reading.value == {}
    assert standing_of("contracts/kept.v1.md", reading.value).word == "Can't check"


def test_a_promise_no_clause_watches_is_said_apart_from_one_with_no_record(recorded):
    """Two silences, and they do not mean the same thing."""
    reading = read_promises(recorded)
    unwatched = standing_of("contracts/nobody-watches-this.v1.md", reading.value)
    assert unwatched.word == "Can't check"
    assert unwatched.sentence == NOTHING_WATCHED

    no_record = standing_of("contracts/nobody-watches-this.v1.md", {})
    assert no_record.word == "Can't check"
    assert no_record.sentence == NO_RECORD


def test_every_sentence_beside_the_word_reads_plainly(recorded):
    standings = list(read_promises(recorded).value.values())
    standings += [Standing("Kept"), standing_of("contracts/x.md", {})]
    for standing in standings:
        assert words.is_surface_word(standing.word), standing.word
        assert words.reads_plainly(standing.sentence), words.internal_terms_in(
            standing.sentence
        )


def test_this_projects_own_record_reads(recorded):
    """The one that matters: Converge's own promises, from Converge's own file.

    A parser that only ever met its own fixture has proved nothing about the
    file it will actually be pointed at.
    """
    reading = read_promises(REPO_ROOT)
    assert reading.available, reading.note
    # 2026-09-04: the record grew from the original four contracts to the
    # whole set (the experience family). Growth is not drift: the originals
    # must still be read, and every file the record names must exist.
    originals = {
        "contracts/composition.v1.md",
        "contracts/documents.v1.md",
        "contracts/operation.v1.md",
        "contracts/surface.v1.md",
    }
    assert originals <= set(reading.value), originals - set(reading.value)
    for rel in reading.value:
        assert (REPO_ROOT / rel).exists(), rel
    for name, standing in reading.value.items():
        assert standing.word in words.CONTRACT_STATES, f"{name}: {standing.word}"
        assert standing.clauses > 0, name


# --------------------------------------------------------------------------
# 3. the page says it
# --------------------------------------------------------------------------


def _client(project: Path):
    from fastapi.testclient import TestClient

    from amplifier_converge.web.app import create_app

    return TestClient(create_app(project, "kettle", include_remote_proposals=False))


@pytest.fixture
def direction_with_a_record(tmp_path, app_home):
    """The example project, plus a record covering both of its promises."""
    import shutil

    project = tmp_path / "with-a-record"
    shutil.copytree(FIXTURE, project)
    (project / RELPATH.parent).mkdir(parents=True)
    (project / RELPATH).write_text(
        RECORD.replace("contracts/kept.v1.md", "contracts/gate.v1.md").replace(
            "contracts/broken.v1.md", "contracts/half.v1.md"
        ),
        encoding="utf-8",
    )
    return _client(project)


def _chips(html: str) -> list[str]:
    import re

    return [
        match.group(1).strip()
        for match in re.finditer(r'<span class="chip[^"]*">([^<]+)</span>', html)
    ]


def test_direction_says_whether_each_promise_is_kept(direction_with_a_record):
    html = direction_with_a_record.get("/direction").text
    shown = _chips(html)
    assert "Kept" in shown, shown
    assert "Broken" in shown, shown


def test_direction_never_offers_draft_as_the_answer(direction_with_a_record):
    """The failure this closes: every promise chipped `Draft` and nothing else.

    `Draft` still appears — it is the document's own status and stays — but it
    is no longer the only word beside a promise.
    """
    shown = set(_chips(direction_with_a_record.get("/direction").text))
    assert shown - set(words.DOCUMENT_STATES), (
        f"the only state beside a promise is still {sorted(shown)}"
    )
    assert shown & set(words.CONTRACT_STATES) - set(words.DOCUMENT_STATES), sorted(shown)


def test_both_signals_stay_on_the_row(direction_with_a_record):
    """Lock state and kept state are two separate questions, both answered."""
    shown = _chips(direction_with_a_record.get("/direction").text)
    assert "Draft" in shown, "the document's own status was dropped"
    assert "Kept" in shown, "whether the promise is kept was dropped"


def test_a_promise_page_says_it_too(direction_with_a_record):
    html = direction_with_a_record.get("/direction/gate.v1").text
    assert "Kept" in _chips(html)


def test_the_vision_is_never_given_a_word_nothing_measured(direction_with_a_record):
    """Nothing checks the vision clause by clause, so nothing claims about it."""
    html = direction_with_a_record.get("/direction/VISION").text
    assert _chips(html) == ["Draft"], _chips(html)


def test_a_project_with_no_record_says_it_cannot_check(project):
    """The example project keeps no record, and the page admits it in the
    contract's own word rather than showing a pass or saying nothing."""
    shown = _chips(_client(project).get("/direction").text)
    assert "Can't check" in shown, shown
    assert "Kept" not in shown, shown


def test_every_chip_on_direction_is_one_of_the_plain_words(direction_with_a_record):
    for page in ("/direction", "/direction/gate.v1", "/direction/half.v1", "/direction/VISION"):
        for shown in _chips(direction_with_a_record.get(page).text):
            assert words.is_surface_word(shown), f"{page} shows “{shown}”"
