"""The seam where the Manager Console meets a real running session.

THIS IS A SEAM, NOT AN IMPLEMENTATION. The proof of concept ships one
connector — ``CannedConnector`` — which replays a recorded transcript so the
console can be seen, sized, and argued about before the real one exists. The
real connector attaches to the live terminal multiplexer session the manager
session already runs in; the owner has a working proof of it and the notes are
coming. When they land, add a class beside ``CannedConnector`` that satisfies
the interface below and change one line in ``serve.py``.

The interface a connector must satisfy
--------------------------------------

    class Connector:

        def attach(self, session: str) -> Iterator[bytes]:
            '''Everything the session has shown so far, then everything it
            shows from now on, as raw terminal bytes including escape codes.

            Called once per viewer. Must be safe to call several times for the
            same session -- two people may watch the same lane. Must never
            block forever: yield nothing and return when the session is gone.
            '''

        def send(self, session: str, keys: bytes) -> None:
            '''Type these bytes into the session, exactly as a keyboard would.

            Raw bytes, not lines: a bare 0x03 is control-C and must reach the
            session as control-C. Returns when the keys are delivered, not when
            the session has finished reacting.
            '''

        def sessions(self) -> list[str]:
            '''The session names that can be attached to right now.'''

Two things the real connector must get right, and the canned one cannot teach:

* **Attaching must not steal the session.** Two viewers, and the manager
  session's own operator, all read the same stream; none of them may detach
  another. A read-only attach is the default and typing is the exception.
* **Bytes, not text.** Terminal output is not UTF-8 by construction. Decode at
  the very edge (the browser) and never in the middle, or a half-written
  character becomes a lost line.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

HERE = Path(__file__).resolve().parent

#: How the canned transcript is cut into pieces so the browser can play it back
#: at a readable pace rather than all at once.
CHUNK_LINES = 1


class CannedConnector:
    """Replays a recorded transcript. Real shape, recorded content."""

    def __init__(self, transcript: str, name: str = "recorded") -> None:
        self._transcript = transcript
        self._name = name
        self._typed: dict[str, list[bytes]] = {}

    # -- the interface ----------------------------------------------------

    def attach(self, session: str) -> Iterator[bytes]:
        for line in self._transcript.splitlines():
            yield (line + "\r\n").encode("utf-8")
        for keys in self._typed.get(session, []):
            yield keys

    def send(self, session: str, keys: bytes) -> None:
        typed = self._typed.setdefault(session, [])
        text = keys.decode("utf-8", "replace").strip()
        typed.append(f"\r\n\x1b[38;5;147myou\x1b[0m      {text}\r\n".encode())
        typed.append(self._reply(text))

    def sessions(self) -> list[str]:
        return [self._name]

    # -- canned behaviour, clearly its own thing --------------------------

    @staticmethod
    def _reply(text: str) -> bytes:
        reply = (
            "This console is playing back a recorded session, so I cannot answer that yet. "
            "When the real connector lands, this is where the manager session answers."
        )
        if text:
            reply = f'I heard "{text[:60]}". ' + reply
        return f"\x1b[38;5;179mmanager\x1b[0m  {reply}\r\n".encode()


def load_canned(name: str = "recorded") -> CannedConnector:
    path = HERE / "fixtures" / "console-transcript.txt"
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        text = "No recorded session was found beside this app.\r\n"
    return CannedConnector(text, name)
