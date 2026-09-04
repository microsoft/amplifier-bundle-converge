"""The things a steward can actually do."""


def record_decision(repo, *, word, proposal_id):
    """Append the steward's word to today's ratification record."""
    path = repo / "docs" / "workflow" / f"owner-ratifications-{day}.md"
    path.write_text(entry)
