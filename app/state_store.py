"""Where each steward's own reading is remembered, between visits.

Two facts live here and nowhere else, both of them per person rather than per
browser:

* **the read point** -- the commit a steward has already read a document up
  to, so the Changes view can answer "since *you* last read" rather than
  "between the last two commits", which is what it used to answer and which is
  why nothing was ever finished;
* **the kept marks** -- which changes that steward has already said they are
  keeping, so leaving the page and coming back does not throw the answers away.

Both used to be missing entirely: Keep was a toast and the read point did not
exist. Keeping them in the browser would have been easier and wrong -- the
steward reads on a laptop and again on a phone, and the same person must see
the same reading.

The file is one small JSON document, rewritten whole and moved into place, so
a crash mid-write leaves the previous reading intact rather than a half file.
"""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock

DEFAULT_STATE_PATH = Path.home() / ".amplifier" / "converge-app.state.json"


def _stamp() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


class Store:
    """The app's memory of what each steward has read and kept.

    One instance per running app. Every method takes the steward explicitly:
    there is no ambient "current user" here, because a reading that quietly
    belonged to whoever asked last would be worse than no reading at all.
    """

    def __init__(self, path: Path | None = None) -> None:
        self.path = Path(path) if path else DEFAULT_STATE_PATH
        self._lock = Lock()

    # ------------------------------------------------------------- the file
    def read(self) -> dict:
        try:
            found = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {"stewards": {}}
        if not isinstance(found, dict):
            return {"stewards": {}}
        found.setdefault("stewards", {})
        return found

    def write(self, whole: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        handle, temporary = tempfile.mkstemp(dir=str(self.path.parent), prefix=".converge-state-")
        try:
            with os.fdopen(handle, "w", encoding="utf-8") as out:
                json.dump(whole, out, indent=2, sort_keys=True)
                out.write("\n")
            os.replace(temporary, self.path)
        except OSError:
            Path(temporary).unlink(missing_ok=True)
            raise

    # ------------------------------------------------------------- the keys
    @staticmethod
    def key(repo: str, doc: str) -> str:
        return f"{repo}/{doc}"

    def _corner(self, whole: dict, user: str) -> dict:
        stewards = whole.setdefault("stewards", {})
        mine = stewards.setdefault(user or "unknown", {})
        mine.setdefault("read", {})
        mine.setdefault("kept", {})
        return mine

    # -------------------------------------------------------- the read point
    def read_point(self, user: str, repo: str, doc: str) -> str:
        whole = self.read()
        mine = whole.get("stewards", {}).get(user or "unknown", {})
        found = mine.get("read", {}).get(self.key(repo, doc))
        return str(found.get("sha", "")) if isinstance(found, dict) else str(found or "")

    def set_read_point(self, user: str, repo: str, doc: str, sha: str) -> None:
        with self._lock:
            whole = self.read()
            mine = self._corner(whole, user)
            mine["read"][self.key(repo, doc)] = {"sha": sha, "at": _stamp()}
            # A reading that has been marked read carries no unanswered marks.
            mine["kept"].pop(self.key(repo, doc), None)
            self.write(whole)

    # --------------------------------------------------------- the kept marks
    def kept(self, user: str, repo: str, doc: str) -> set[str]:
        whole = self.read()
        mine = whole.get("stewards", {}).get(user or "unknown", {})
        found = mine.get("kept", {}).get(self.key(repo, doc)) or []
        return {str(one) for one in found} if isinstance(found, list) else set()

    def keep(self, user: str, repo: str, doc: str, change: str, on: bool = True) -> set[str]:
        with self._lock:
            whole = self.read()
            mine = self._corner(whole, user)
            here = set(mine["kept"].get(self.key(repo, doc)) or [])
            if on:
                here.add(change)
            else:
                here.discard(change)
            if here:
                mine["kept"][self.key(repo, doc)] = sorted(here)
            else:
                mine["kept"].pop(self.key(repo, doc), None)
            self.write(whole)
            return here


__all__ = ["DEFAULT_STATE_PATH", "Store"]
