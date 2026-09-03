"""Each of the four writes, checked where it actually lands."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from amplifier_converge.reading.constraints import read_constraints
from amplifier_converge.writing.answer import answer_with_a_word, record_path
from amplifier_converge.writing.feedback import drop_feedback
from amplifier_converge.writing.priority import signal_priority
from amplifier_converge.writing.steer import steer


# ---- answer with a word ---------------------------------------------------


def test_every_answer_lands_in_the_dated_record(project: Path):
    result = answer_with_a_word(project, subject="Cut-out Contract", word="ratified")
    assert result.ok
    text = record_path(project).read_text(encoding="utf-8")
    assert "Cut-out Contract" in text
    assert "`ratified`" in text
    assert date.today().isoformat() in record_path(project).name


@pytest.mark.parametrize("word", ["ratified", "ratified with edits", "declined", "later"])
def test_all_four_words_are_accepted(project: Path, word: str):
    assert answer_with_a_word(project, subject=f"About {word}", word=word).ok


def test_no_fifth_word_is_accepted(project: Path):
    result = answer_with_a_word(project, subject="Something", word="approved")
    assert not result.ok
    assert "not one of the four words" in result.message


def test_later_is_recorded_as_not_dismissed(project: Path):
    answer_with_a_word(project, subject="Saying Ready", word="later")
    text = record_path(project).read_text(encoding="utf-8")
    assert "not dismissed" in text


def test_answering_appends_and_never_overwrites(project: Path):
    answer_with_a_word(project, subject="First thing", word="ratified")
    answer_with_a_word(project, subject="Second thing", word="declined")
    text = record_path(project).read_text(encoding="utf-8")
    assert "First thing" in text and "Second thing" in text


def test_an_answer_through_the_page_shortens_the_list(client, project):
    """Answering marks the record, and the page reads its own record back."""
    from amplifier_converge.reading.documents import lock_is_available, read_direction

    doc = next(d for d in read_direction(project).value if d.slug == "half.v1")
    assert not lock_is_available(doc, project)

    response = client.post(
        "/do/answer-with-a-word",
        data={"subject": doc.title, "word": "ratified", "back": "/direction/half.v1"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    text = record_path(project).read_text(encoding="utf-8")
    assert doc.title in text


# ---- signal priority ------------------------------------------------------


def test_a_priority_signal_is_either_sooner_or_later(project: Path):
    result = signal_priority(project, "kettle", "kettle-1", "urgent")
    assert not result.ok
    assert "sooner or later" in result.message


def test_a_priority_signal_says_so_when_the_queue_is_unreachable(project: Path, monkeypatch):
    monkeypatch.setattr("amplifier_converge.writing.priority.shutil.which", lambda _: None)
    result = signal_priority(project, "kettle", "kettle-1", "sooner")
    assert not result.ok
    assert "Nothing was changed" in result.message


# ---- drop feedback --------------------------------------------------------


def test_feedback_lands_in_the_project_where_the_manager_reads_it(project: Path):
    result = drop_feedback(project, text="The light never came on.", looking_at="unit 7")
    assert result.ok
    drops = list((project / ".converge" / "feedback").glob("*.md"))
    assert drops
    body = drops[0].read_text(encoding="utf-8")
    assert "The light never came on." in body
    assert "unit 7" in body
    assert "Not a work item" in body


def test_empty_feedback_is_refused_with_a_reason(project: Path):
    result = drop_feedback(project, text="   ")
    assert not result.ok
    assert "needs something in it" in result.message


def test_a_picture_can_come_with_the_words(project: Path):
    result = drop_feedback(
        project, text="Look at this.", attachment=b"\x89PNG\r\n", attachment_type="image/png"
    )
    assert result.ok
    assert list((project / ".converge" / "feedback").glob("*.png"))


# ---- steer ----------------------------------------------------------------


def test_steering_writes_the_limits_the_manager_session_reads(project: Path):
    result = steer(project, objective="Ship the cut-out", budget="until done", lane_width="6")
    assert result.ok
    constraints = read_constraints(project).value
    assert constraints.objective == "Ship the cut-out"
    assert constraints.budget == "until done"
    assert constraints.lane_width == "6"


def test_a_lane_count_must_be_a_number(project: Path):
    assert not steer(project, lane_width="lots").ok


def test_only_the_three_budget_shapes_are_accepted(project: Path):
    assert not steer(project, budget="until Tuesday-ish").ok


def test_filling_the_lanes_is_recorded_as_a_standing_request(project: Path):
    result = steer(project, ask="fill the lanes")
    assert result.ok
    text = (project / ".converge" / "constraints.yaml").read_text(encoding="utf-8")
    assert "Fill the lanes" in text


def test_the_page_never_offers_to_stop_anything(client):
    html = client.get("/operation").text
    for forbidden in ("Kill", "kill lane", "Stop lane", "Terminate"):
        assert forbidden not in html
    assert "never a button here" in html
