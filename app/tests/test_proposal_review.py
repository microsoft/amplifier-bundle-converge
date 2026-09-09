"""converge-neu6 -- `app/data.py`'s `proposals_for` reads a candidate's own
sections faithfully, instead of putting the exact-change text into `why` and
leaving the renderer to substitute the proposal's title for the actual
change (`render/direction.js`'s old `renderReview`).

Unit-level: these exercise `proposals_for` directly against real files on
disk (never a mock of it), which is what the mounted browser proof in
`test_hackathon_journey.py` then drives through the real UI.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app import data

GENERIC_TITLE_DIFFERENT_SENTENCES = """# AFK Preview Contract -- Console -- proposed wording

**What this asks for:** that the console's idle-state sentence stop implying
a live connection when none exists, because a steward reading it at a glance
has no other signal to go on.

**Which promise it serves:** experience-console.v1 Core 3 (the console never
claims a state it cannot prove).

## The exact change

Current:

> Console is listening.

Replacement:

> Console is idle -- no session is attached.

## The evidence

- A steward read "listening" as attached and waited four minutes for a reply
  that was never coming.

## What does not change

The console's position, its open/close gesture, and every other sentence.
"""

UNSTRUCTURED_PROSE = """# Tidy the changelog wording

Just reflow the changelog entry so it reads as one sentence instead of a
table row. Nothing else about the document changes.
"""


def _write_candidate(tmp_path: Path, stem: str, text: str) -> tuple[Path, Path]:
    repo = tmp_path / "repo"
    repo.mkdir()
    doc = repo / f"{stem}.md"
    doc.write_text(f"# {stem}\n\n## Core\n\n1. Something.\n", encoding="utf-8")
    (repo / f"{stem}.v1-candidate.md").write_text(text, encoding="utf-8")
    return doc, repo


def test_the_actual_change_is_not_the_title(tmp_path: Path) -> None:
    """A generic title must never stand in for the real exact-change text."""
    doc, repo = _write_candidate(tmp_path, "console", GENERIC_TITLE_DIFFERENT_SENTENCES)
    one = data.proposals_for(doc, repo)[0]
    assert one["title"] == "AFK Preview Contract -- Console -- proposed wording"
    assert one["changeRecognized"] is True
    # The real sentence-level wording, never the title, never a first
    # sentence lifted out of context.
    assert "Console is idle" in one["change"]
    assert "Console is idle" in one["changeHtml"]
    assert one["title"] not in one["change"]


def test_rationale_and_change_are_kept_separate(tmp_path: Path) -> None:
    """The exact-change sentence must not leak into `why`, and the file's own
    rationale prose (its preamble, before the first `## ` heading) must not
    be silently dropped the way it used to be."""
    doc, repo = _write_candidate(tmp_path, "console2", GENERIC_TITLE_DIFFERENT_SENTENCES)
    one = data.proposals_for(doc, repo)[0]
    assert "Console is idle" not in one["why"]
    assert "reading it at a glance" in one["why"]
    assert one["whyHtml"]
    assert "reading it at a glance" in one["whyHtml"]


def test_evidence_and_unchanged_are_kept_and_flagged_recognized(tmp_path: Path) -> None:
    doc, repo = _write_candidate(tmp_path, "console3", GENERIC_TITLE_DIFFERENT_SENTENCES)
    one = data.proposals_for(doc, repo)[0]
    assert one["evidenceRecognized"] is True
    assert any("four minutes" in x for x in one["evidence"])
    assert one["unchangedRecognized"] is True
    assert "open/close gesture" in one["unchanged"]


def test_a_proposal_without_labeled_sections_says_so_honestly(tmp_path: Path) -> None:
    """No `## The exact change` heading at all: `changeRecognized` is False
    and `change` is empty -- never the title, never invented before/after
    text -- while the complete original proposal stays reachable."""
    doc, repo = _write_candidate(tmp_path, "changelog", UNSTRUCTURED_PROSE)
    one = data.proposals_for(doc, repo)[0]
    assert one["changeRecognized"] is False
    assert one["change"] == ""
    assert one["evidenceRecognized"] is False
    assert one["unchangedRecognized"] is False
    # The complete, unedited proposal is still fully reachable.
    assert "reflow the changelog entry" in one["body"]
    assert "reflow the changelog entry" in one["bodyHtml"]


def test_markdown_in_the_rendered_fields_is_escaped_not_executed(tmp_path: Path) -> None:
    """Reuses the existing safe renderer (`render_markdown`, html: False) --
    a script tag in a candidate file must never become live markup."""
    hostile = """# Title

## The exact change

<script>alert(1)</script> becomes plain text.
"""
    doc, repo = _write_candidate(tmp_path, "hostile", hostile)
    one = data.proposals_for(doc, repo)[0]
    assert "<script>" not in one["changeHtml"]
    assert "&lt;script&gt;" in one["changeHtml"]


@pytest.mark.parametrize("stem", ["plain"])
def test_a_proposal_with_no_preamble_has_no_fabricated_rationale(tmp_path: Path, stem: str) -> None:
    """A candidate that opens straight into `## The exact change` (no author
    prose above it) must report an honestly empty rationale, never invent
    one from the title or the change text."""
    text = """# Widen Core 1

## The exact change

Core 1 gains a sentence about silence.

## The evidence

- A steward read a placeholder as real data once.
"""
    doc, repo = _write_candidate(tmp_path, stem, text)
    one = data.proposals_for(doc, repo)[0]
    assert one["why"] == ""
    assert one["whyHtml"] == ""
