"""The things a steward can actually do."""

import sqlite3


def record_decision(repo, *, word, proposal_id):
    """Keep the steward's word in the app's own database."""
    sqlite3.connect("decisions.db").execute("insert into decisions values (?)", (word,))
