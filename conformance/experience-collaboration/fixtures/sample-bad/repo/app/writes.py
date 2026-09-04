"""Everything a steward does, relayed through the session that is watching."""

import subprocess


def record_decision(repo, *, word, proposal_id, day):
    """Tell the manager session; it will work out what to do."""
    subprocess.run(["tmux", "send-keys", "-t", "manager", f"decision {word}", "Enter"])


PEER_ENDPOINT = "the other manager session"


def tell_the_other_manager(word):
    peer_channel(PEER_ENDPOINT).send(word)
