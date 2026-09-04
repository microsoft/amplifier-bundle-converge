"""The things a steward can actually do, written where they belong."""

import subprocess


def _git(repo, *args):
    return subprocess.run(["git", *args], cwd=str(repo), capture_output=True, text=True)


def record_decision(repo, *, word, proposal_id, day):
    """Append the steward word to today ratification record, and commit it."""
    path = repo / "docs" / "workflow" / f"owner-ratifications-{day}.md"
    path.write_text(entry(word, proposal_id))
    _git(repo, "add", str(path))
    _git(repo, "commit", "-m", f"ratification: {proposal_id}")
    return path


def candidate_path(path):
    """The proposal beside the document it proposes against."""
    return path.with_name(f"{path.stem}.v2-candidate.md")


def post_back_to_origin(repo, *, proposal, word):
    """Send the steward own word to the origin, as a comment on the host."""
    return _git(repo, "push", "origin", "HEAD")
