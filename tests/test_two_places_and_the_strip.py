"""Surface.v1 clauses 1, 2, 5, 6 and 7 — the two places and the short list."""

from __future__ import annotations

from pathlib import Path

from amplifier_converge.reading import snapshot as snapshot_reader
from amplifier_converge.reading import strip as strip_reader
from amplifier_converge.reading.documents import lock_is_available, read_direction
from amplifier_converge.reading.whatchanged import mark_read, what_changed


def _look(project: Path):
    return snapshot_reader.take(project, "kettle", include_remote_proposals=False)


def test_the_two_places_are_reachable_from_every_page(client):
    for page in ("/", "/direction", "/operation"):
        html = client.get(page).text
        assert 'href="/direction"' in html
        assert 'href="/operation"' in html


def test_the_short_list_never_shows_more_than_five(project):
    decisions = strip_reader.build(_look(project))
    assert len(decisions) <= strip_reader.MAX_ITEMS == 5


def test_every_decision_arrives_worked_out(project):
    for decision in strip_reader.build(_look(project)):
        assert decision.what.strip()
        assert decision.why_now.strip()
        assert decision.recommendation.strip()
        assert 0 < len(decision.trade_offs) <= 2, "at most two trade-offs, and at least one"
        assert decision.word in decision.words
        assert decision.place in ("direction", "operation")


def test_an_empty_list_reads_as_good_news(client, project):
    for path in (project / "contracts").glob("*-candidate.md"):
        path.unlink()
    html = client.get("/").text
    assert "Nothing needs your word" in html


def test_a_proposal_missing_its_evidence_is_named_as_such(client):
    html = client.get("/direction").text
    assert "Arrived incomplete" in html
    assert "evidence" in html


def test_both_kinds_of_proposal_are_read_the_same_way(client):
    html = client.get("/direction/proposal?key=file:contracts/gate.v2-candidate.md").text
    assert "The exact change" in html
    assert "The evidence" in html
    assert "What does not change" in html


def test_the_lock_control_is_off_until_all_four_are_green(client, project):
    docs = {d.slug: d for d in read_direction(project).value}

    ready = docs["gate.v1"]
    assert lock_is_available(ready, project)
    html = client.get("/direction/gate.v1").text
    assert "Lock it" in html
    assert "<button class=\"word\" type=\"submit\" disabled>Lock it</button>" not in html

    not_ready = docs["half.v1"]
    assert not lock_is_available(not_ready, project)
    html = client.get("/direction/half.v1").text
    assert "<button class=\"word\" type=\"submit\" disabled>Lock it</button>" in html
    assert "Not yet" in html


def test_what_changed_shows_removed_sentences_not_only_added(project):
    document = (project / "contracts" / "half.v1.md")
    text = document.read_text(encoding="utf-8")
    mark_read(project, "half.v1", text)

    rewritten = text.replace("2. **It says it once.**", "2. **It repeats until dismissed.**")
    rewritten += "\n\nA new sentence arrives at the end.\n"
    document.write_text(rewritten, encoding="utf-8")

    changed = what_changed(project, "half.v1", document.read_text(encoding="utf-8"))
    assert changed.seen_before
    assert any("says it once" in s for s in changed.removed), "a removed sentence went unreported"
    assert any("new sentence" in s for s in changed.added)
    assert "removed" in changed.summary


def test_a_hard_wrapped_sentence_is_reported_whole(project):
    """Documents wrap at about eighty columns. Reporting half a sentence as
    removed and the other half as added is the confusion this feature exists
    to remove, so the wrapping must be undone before comparing."""
    document = project / "docs" / "VISION.md"
    text = document.read_text(encoding="utf-8")
    mark_read(project, "VISION", text)

    document.write_text(
        text.replace(
            "It does one thing, it does\nit in under three minutes, and it never boils dry.",
            "It never boils dry.",
        ),
        encoding="utf-8",
    )
    changed = what_changed(project, "VISION", document.read_text(encoding="utf-8"))
    assert len(changed.removed) == 1, f"a wrapped sentence was reported in pieces: {changed.removed}"
    assert changed.removed[0].startswith("It does one thing")
    assert changed.removed[0].endswith("never boils dry.")


def test_what_changed_says_so_plainly_before_you_have_read_anything(project):
    doc = next(d for d in read_direction(project).value if d.slug == "VISION")
    changed = what_changed(project, doc.slug, doc.text)
    assert not changed.seen_before
    assert "nothing to compare" in changed.summary


def test_a_question_can_be_attached_to_a_paragraph(client):
    html = client.get("/direction/gate.v1").text
    assert "ask about this" in html
    page = client.get("/direction/gate.v1/ask?anchor=p3")
    assert page.status_code == 200
    assert "Ask about this paragraph" in page.text


def test_technical_words_stay_behind_a_details_fold(client):
    html = client.get("/operation").text
    if "<details>" in html:
        before_folds = html.split("<details>")[0]
        assert "worktree" not in before_folds
        assert "base_sha" not in before_folds
