"""Everything a steward does, relayed through the session that is watching."""

import subprocess


def record_decision(repo, *, word, proposal_id, day):
    """Tell the manager session; it will work out what to do."""
    subprocess.run(["tmux", "send-keys", "-t", "manager", f"decision {word}", "Enter"])


PEER_ENDPOINT = "the other manager session"


class _Channel:
    def __init__(self, endpoint):
        self.endpoint = endpoint

    def send(self, word):
        subprocess.run(["tmux", "send-keys", "-t", self.endpoint, f"decision {word}", "Enter"])


def peer_channel(endpoint):
    """A direct line to the other manager session, around the host."""
    return _Channel(endpoint)


def tell_the_other_manager(word):
    peer_channel(PEER_ENDPOINT).send(word)
