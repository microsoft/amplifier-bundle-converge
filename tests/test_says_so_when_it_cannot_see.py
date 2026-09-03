"""Data sources degrade honestly.

The failure this guards against is the worst one a surface can have: showing a
zero when the truth is "we could not look". A board that says `0 of 10 running`
because the lanes directory is missing is a lie told by omission.
"""

from __future__ import annotations

from pathlib import Path

from amplifier_converge.reading.constraints import read_constraints
from amplifier_converge.reading.documents import read_direction
from amplifier_converge.reading.gitfacts import read_git
from amplifier_converge.reading.lanes import read_board
from amplifier_converge.reading.queue import read_items, read_summary


def test_a_missing_lanes_directory_is_said_in_words(tmp_path):
    reading = read_board(tmp_path, batch_dir=None)
    assert not reading.available
    assert reading.note
    assert "does not mean zero" in reading.note.lower() or "no board to read" in reading.note.lower()


def test_a_lanes_directory_without_a_manifest_says_which_is_missing(tmp_path):
    (tmp_path / "lanes").mkdir()
    reading = read_board(tmp_path, batch_dir=tmp_path)
    assert not reading.available
    assert "manifest" in reading.note


def test_an_unknown_work_queue_project_is_said_in_words(tmp_path):
    reading = read_items(tmp_path, "a-project-that-does-not-exist")
    assert not reading.available
    assert reading.note.strip()
    assert reading.value == []


def test_the_queue_summary_degrades_without_showing_zeroes_as_truth(tmp_path):
    reading = read_summary(tmp_path, "a-project-that-does-not-exist")
    assert not reading.available
    assert reading.note.strip()


def test_a_folder_that_is_not_a_repository_is_said_in_words(tmp_path):
    reading = read_git(tmp_path)
    assert not reading.available
    assert "no code record" in reading.note
    assert "git" not in reading.note, "the deciding sentence carries a technical word"
    assert "git" in reading.detail, "the technical reason was thrown away rather than folded"


def test_a_folder_with_no_documents_is_said_in_words(tmp_path):
    reading = read_direction(tmp_path)
    assert not reading.available
    assert "VISION" in reading.note or "contracts" in reading.note


def test_unset_limits_are_an_invitation_not_a_failure(tmp_path):
    reading = read_constraints(tmp_path)
    assert reading.available, "no limits set is not the same as unable to read them"
    assert "not set any limits" in reading.note


def test_the_page_shows_every_honest_note_it_has(client):
    """The example project has no work queue and no lanes. Both must be said."""
    html = client.get("/operation").text
    assert "honest" in html, "the page hid what it could not read"
    assert "0 of" not in html, "a gauge was drawn from data that could not be read"


def test_an_empty_answer_and_an_unreadable_source_never_look_the_same(project: Path):
    """A queue that answers and is empty is `available`; one that cannot be
    reached is not. The page draws these two differently, which it can only do
    if the readers keep them apart."""
    unreadable = read_items(project, "a-project-that-does-not-exist")
    assert not unreadable.available and unreadable.value == []

    empty_but_readable = read_direction(project)
    assert empty_but_readable.available and empty_but_readable.value
