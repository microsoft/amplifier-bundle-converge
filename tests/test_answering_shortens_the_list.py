"""Answering marks the card and shortens the list — and `later` does not.

Surface.v1 clause 3 makes `later` a real answer that re-ranks and never
dismisses. If `later` removed a card, the steward would lose the one word that
lets them get out of the way of something without deciding it.
"""

from __future__ import annotations

from pathlib import Path

from amplifier_converge.reading import snapshot as snapshot_reader
from amplifier_converge.reading import strip as strip_reader
from amplifier_converge.writing.answer import answer_with_a_word


def _decisions(project: Path):
    snap = snapshot_reader.take(project, "kettle", include_remote_proposals=False)
    return strip_reader.build(snap)


def test_a_settling_word_takes_the_card_off_the_list(project: Path):
    before = _decisions(project)
    assert before, "the example project should have something needing a word"

    target = before[0]
    answer_with_a_word(project, subject=target.what, word="ratified")

    after = _decisions(project)
    assert len(after) == len(before) - 1
    assert target.key not in {d.key for d in after}


def test_declining_also_settles_it(project: Path):
    before = _decisions(project)
    target = before[0]
    answer_with_a_word(project, subject=target.what, word="declined")
    assert target.key not in {d.key for d in _decisions(project)}


def test_later_keeps_it_but_moves_it_out_of_the_way(project: Path):
    before = _decisions(project)
    assert len(before) >= 2, "this needs at least two things to re-rank"
    target = before[0]

    answer_with_a_word(project, subject=target.what, word="later")

    after = _decisions(project)
    keys = [d.key for d in after]
    assert target.key in keys, "`later` dismissed a card, and it must never do that"
    assert keys[-1] == target.key, "`later` did not move it out of the way"
    assert len(after) == len(before)


def test_the_list_is_read_back_from_the_project_not_remembered(project: Path):
    """Deleting the record puts the card back, because the record is the only
    place the answer was ever kept."""
    before = _decisions(project)
    target = before[0]
    answer_with_a_word(project, subject=target.what, word="ratified")
    assert target.key not in {d.key for d in _decisions(project)}

    for path in (project / "docs" / "workflow").glob("owner-ratifications-*.md"):
        path.unlink()
    assert target.key in {d.key for d in _decisions(project)}


def test_answering_through_the_page_shortens_the_page(client, project):
    before = _decisions(project)
    target = before[0]

    client.post(
        "/do/answer-with-a-word",
        data={"subject": target.what, "word": "ratified", "back": "/"},
        follow_redirects=False,
    )

    html = client.get("/").text
    assert target.what not in html
    assert len(_decisions(project)) == len(before) - 1


def test_the_list_still_never_exceeds_five(project: Path):
    assert len(_decisions(project)) <= 5
