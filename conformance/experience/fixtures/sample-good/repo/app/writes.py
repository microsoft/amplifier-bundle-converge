"""The things a steward can actually do."""


def entry(word, proposal_id):
    """The line this ratification adds to today's record."""
    return f"{proposal_id}: {word}\n"


def record_decision(repo, *, word, proposal_id, day):
    """Append the steward's word to today's ratification record."""
    path = repo / "docs" / "workflow" / f"owner-ratifications-{day}.md"
    path.write_text(entry(word, proposal_id))
