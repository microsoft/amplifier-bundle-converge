# A small project, for examining the page

This is a whole Converge project in miniature. It exists so the page can be
examined in every state it is supposed to reach, without needing a real project
in exactly the right condition at exactly the right moment.

Serve it:

    uv run --extra web amplifier-converge web \
      --repo conformance/surface/fixtures/app --port 8091 --no-remote

What it is arranged to show:

| Where | What you should see |
|---|---|
| The short list | Two things needing your word, never more than five |
| `gate.v1` | All four lock conditions green, and the lock control live |
| `half.v1` | One condition green, three not yet, and the lock control off |
| The vision | A draft with your word already on it, and lockable |
| Proposals | One complete, one arriving without its evidence |
| Operation | No work queue and no lanes here — said plainly, not as zeros |

The last row is the point of the fixture as much as the rest: this folder has
no work queue and no lanes beside it, so the page must say so in words rather
than draw an empty board that reads like "nothing to do".
