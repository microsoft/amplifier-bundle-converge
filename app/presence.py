"""Who is editing which section, right now -- courtesy, never a lock.

`experience-direction.v1` clause 10 asks for two things when two people reach
the same paragraph at once: while a person is editing, that section is *shown
softly*; and the manager session *backs off and queues rather than fights*.
Both need a channel, and until this file there was none. What the Reading view
showed softly was the steward's own open editor, in their own browser, which is
company only in the way a mirror is.

This is that channel, and it is deliberately three small facts:

* **a mark** -- "<person> has the editor open on <section> of <document>", set
  by their browser every few seconds while the editor is open;
* **an expiry** -- a mark older than :data:`TTL_SECONDS` is not a signal any
  more, it is a browser that was closed, so it is dropped rather than shown;
* **a queue** -- a writer that is not a browser (the manager session) asking
  "is anyone on this section?" and, when someone is, recording that it is
  waiting instead of writing.

Three things this is NOT, and each of them on purpose:

**Not a lock.** Nothing here refuses a write. A mark makes a section *look*
occupied; it never makes it unwritable. The clause says courtesy, and courtesy
that can be enforced is a lock wearing a friendlier word. What actually stops
two writes from silently overwriting each other is the collision path that
already exists -- `app/writes.py` refuses a sentence that moved, and the
steward is offered Use combined / Keep mine / Review both.

**Not on disk.** Presence lives in this process's memory and nowhere else. It
is not written to the repository -- a note about the next sixty seconds has no
business in a history meant to outlive everyone -- and it is not written to
`app/state_store.py`, which is the record of what a steward has *read and
kept*: facts that must survive a restart. Presence is the opposite kind of
fact. A restart *should* forget it, because after a restart every one of those
browsers is a claim nobody is making any more.

**Not a promise about the manager session.** :meth:`Presence.queue` is the app
holding up its half -- it answers, plainly, "this section is held by <person>,
for another <n> seconds". A session that asks and then writes anyway is not
something this file can prevent; what it can do is make backing off cheap,
honest, and visible to the steward, which is what :meth:`here` reports back.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from threading import Lock

#: How long a mark stands without being refreshed. A browser beats every few
#: seconds while its editor is open, so a full minute of silence means the tab
#: is gone, the laptop is shut, or the network went away -- none of which are
#: "someone is editing this".
TTL_SECONDS = 60.0


@dataclass(frozen=True)
class Mark:
    """One person, one section, one moment. Immutable: a refresh replaces it."""

    user: str
    section: str
    at: float
    kind: str = "editing"
    note: str = ""


class Presence:
    """The live marks, per document. One instance per running app.

    Every method takes the person explicitly. There is no ambient "current
    user" here for the same reason there is none in `app/state_store.py`: a
    signal that quietly belonged to whoever asked last would be worse than no
    signal, because it would be *believed*.
    """

    def __init__(self, ttl: float = TTL_SECONDS, clock=time.monotonic) -> None:
        self._ttl = float(ttl)
        self._clock = clock
        self._lock = Lock()
        # (repo, doc) -> user -> Mark. One section per person per document:
        # a steward has one editor open, and a second mark from the same
        # person would be a mark nobody is standing behind.
        self._editing: dict[tuple[str, str], dict[str, Mark]] = {}
        # (repo, doc) -> (user, section) -> Mark. A queue is per section,
        # because a session waiting on two sections is waiting twice.
        self._queued: dict[tuple[str, str], dict[tuple[str, str], Mark]] = {}

    # ------------------------------------------------------------------ time
    @property
    def ttl(self) -> float:
        return self._ttl

    def _prune(self, marks: dict, now: float) -> dict:
        for key, mark in list(marks.items()):
            if now - mark.at > self._ttl:
                del marks[key]
        return marks

    def _payload(self, mark: Mark, now: float) -> dict:
        left = self._ttl - (now - mark.at)
        return {
            "user": mark.user,
            "section": mark.section,
            "kind": mark.kind,
            "note": mark.note,
            "ago": int(max(0.0, now - mark.at)),
            "expiresIn": int(max(0.0, left)),
        }

    # --------------------------------------------------------------- editing
    def editing(self, *, user: str, repo: str, doc: str, section: str) -> list[dict]:
        """Record that `user` has the editor open on `section` -- or has closed it.

        An empty `section` is a release, and it is the same call rather than a
        second route on purpose: a browser that beats "I am editing nothing"
        cannot forget to say goodbye, and a browser that stops beating at all
        is covered by the expiry.
        """
        now = self._clock()
        with self._lock:
            here = self._prune(self._editing.setdefault((repo, doc), {}), now)
            who = user or "unknown"
            if section:
                here[who] = Mark(user=who, section=section, at=now)
            else:
                here.pop(who, None)
            return [self._payload(one, now) for one in here.values()]

    def release(self, *, user: str, repo: str, doc: str) -> None:
        self.editing(user=user, repo=repo, doc=doc, section="")

    # ----------------------------------------------------------------- reads
    def here(self, *, repo: str, doc: str) -> dict:
        """Every live mark on one document: who is editing, who is waiting."""
        now = self._clock()
        with self._lock:
            editing = self._prune(self._editing.setdefault((repo, doc), {}), now)
            queued = self._prune(self._queued.setdefault((repo, doc), {}), now)
            return {
                "editing": sorted(
                    (self._payload(one, now) for one in editing.values()),
                    key=lambda row: (row["section"], row["user"]),
                ),
                "queued": sorted(
                    (self._payload(one, now) for one in queued.values()),
                    key=lambda row: (row["section"], row["user"]),
                ),
                "ttlSeconds": int(self._ttl),
            }

    def holder(self, *, repo: str, doc: str, section: str, besides: str = "") -> dict | None:
        """Whoever has `section` open, if it is anyone but `besides`."""
        for row in self.here(repo=repo, doc=doc)["editing"]:
            if row["section"] == section and row["user"] != (besides or ""):
                return row
        return None

    # ----------------------------------------------------------------- queue
    def queue(self, *, user: str, repo: str, doc: str, section: str, note: str = "") -> dict:
        """A writer that is not a browser asks whether to write, or to wait.

        Returns the answer, and records the wait only when there is something
        to wait for. Nothing here writes, refuses, or defers anything on the
        caller's behalf -- the caller keeps its own work and retries. Being
        told plainly is the whole of what the app can honestly offer, and it
        is the half clause 10 was missing.
        """
        held = self.holder(repo=repo, doc=doc, section=section, besides=user or "unknown")
        if held is None:
            return {
                "queued": False,
                "heldBy": None,
                "section": section,
                "said": "Nobody has that section open. Write it.",
            }
        now = self._clock()
        with self._lock:
            waiting = self._prune(self._queued.setdefault((repo, doc), {}), now)
            waiting[(user or "unknown", section)] = Mark(
                user=user or "unknown", section=section, at=now, kind="queued", note=note
            )
        return {
            "queued": True,
            "heldBy": held["user"],
            "section": section,
            "expiresIn": held["expiresIn"],
            "said": (
                f"{held['user']} has that section open. Your write is queued, not made -- "
                f"hold it and ask again in up to {held['expiresIn']}s."
            ),
        }

    def unqueue(self, *, user: str, repo: str, doc: str, section: str) -> None:
        with self._lock:
            waiting = self._queued.setdefault((repo, doc), {})
            waiting.pop((user or "unknown", section), None)


__all__ = ["Mark", "Presence", "TTL_SECONDS"]
