"""Surface.v1 clauses 1, 2, 5, 6 and 7 — the two places and the short list."""

from __future__ import annotations

from pathlib import Path

from amplifier_converge.reading import snapshot as snapshot_reader
from amplifier_converge.reading import strip as strip_reader
from amplifier_converge.reading.documents import lock_is_available, read_direction
from amplifier_converge.reading.whatchanged import mark_read, what_changed


def _look(project: Path):
    return snapshot_reader.take(project, "kettle", include_remote_proposals=False)


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


def test_the_lock_control_is_off_until_all_four_are_green(project):
    """The three assertions that read the retired page's own button were
    deleted with it on 2026-09-06. The predicate the control reads is here."""
    docs = {d.slug: d for d in read_direction(project).value}

    ready = docs["gate.v1"]
    assert lock_is_available(ready, project)

    not_ready = docs["half.v1"]
    assert not lock_is_available(not_ready, project)


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
