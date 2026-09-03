"""Read-only tmux viewer API for the Converge companion app.

Field guide: ai-context/BROWSER-TMUX-VIEWER.md — that document is the law here.
The rules it imposes, and where they live in this file:

* Poll ``capture-pane -e -p`` (never ``pipe-pane``, never ttyd).  ``_capture``.
* Use an **explicit socket**, never the ambient ``$TMUX``.  ``_socket_args`` and
  ``_env`` — ``TMUX`` is stripped from the child environment and reported back
  as ``ambient_tmux_ignored``.
* Read geometry in the **same tmux round-trip** as the capture: one process,
  ``display-message`` and ``capture-pane`` chained with ``;``.  ``_TMUX_FORMAT``
  and ``_capture``.
* Put a **server-side capture cache** in front of the clients: one capture per
  session per tick, single-flight so a slow capture cannot stampede.
  ``CaptureCache``.
* **Four states, never conflated**: ok / empty / ended / failed.  ``_classify``.
* **Never fall through to another session.** Targets are pinned with tmux's
  exact-match ``=`` prefix, and every response echoes the identity it answered
  for.  ``_target``.
* **Strip the trailing newline** ``capture-pane`` emits, or a full-height
  alt-screen TUI scrolls its title row out of view.  ``_split_capture``.
* Do **not** pass ``-a``: measured, it returns a blank alt screen.

Read-only in this version: there is no send-keys endpoint and no write path.
"""

from __future__ import annotations

import asyncio
import os
import shutil
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Query

# --------------------------------------------------------------------------
# constants
# --------------------------------------------------------------------------

#: Poll tick, milliseconds.  A capture younger than this is served from cache.
TICK_MS = 750

#: Capture bound (field guide §4: bound everything you write).
MAX_LINES = 2000
DEFAULT_LINES = 200

#: Metadata read.  Chained into the *same* tmux invocation as the capture so
#: geometry and text describe the same tick.
_TMUX_FORMAT = (
    "#{pane_width} #{pane_height} #{history_size} "
    "#{history_limit} #{alternate_on} #{cursor_x} #{cursor_y}"
)

#: stderr fragments that mean "the thing you asked about is gone", as opposed
#: to "the observation failed".
_GONE_MARKERS = (
    "can't find session",
    "can't find pane",
    "can't find window",
    "session not found",
    "no server running",
    "no current session",
    "error connecting to",
)


# --------------------------------------------------------------------------
# socket / environment resolution
# --------------------------------------------------------------------------


def ambient_tmux_ignored() -> str | None:
    """What ``$TMUX`` said, which we deliberately ignore.

    Reported in the sessions payload so an operator can tell at a glance which
    server this service is attached to (field guide §2).
    """
    return os.environ.get("TMUX") or None


def _socket_args(socket: str) -> list[str]:
    """tmux socket flags for *socket*.

    A value containing ``/`` is a socket **path** (``-S``); anything else is a
    socket **name** (``-L``).  Never ``$TMUX``.
    """
    if "/" in socket:
        return ["-S", socket]
    return ["-L", socket]


def _env() -> dict[str, str]:
    """Child environment with the ambient tmux server removed.

    ``TMUX_TMPDIR`` is kept: it is how ``-L <name>`` resolves to a socket path.
    ``TMUX`` is dropped so a mistargeted command can never land on the
    operator's real server.
    """
    env = dict(os.environ)
    env.pop("TMUX", None)
    return env


def _target(session: str) -> str:
    """Exact-match tmux target for *session*, as ``=<name>:``.

    tmux's ``-t`` does prefix/fnmatch resolution: measured on tmux 3.4,
    ``-t colo`` happily answers for the session ``colors``.  That is the silent
    re-target the field guide (§6) caught in a rendered browser.  The ``=``
    prefix forces an exact match, and the trailing ``:`` makes it a *pane*
    target (session, current window, active pane) — ``=name`` alone is rejected
    by ``display-message`` with "can't find pane".  Measured: ``=colo:`` fails
    with "can't find session: colo" where ``colo:`` returns ``colors``.

    This is the load-bearing half of "never fall through to another session".
    """
    return "=" + session + ":"


def tmux_available() -> bool:
    return shutil.which("tmux") is not None


# --------------------------------------------------------------------------
# frames
# --------------------------------------------------------------------------


@dataclass
class Frame:
    """One observation of one pane, at one tmux tick."""

    state: str  # "ok" | "empty" | "ended" | "failed"
    text: str
    geometry: dict[str, Any] | None
    captured_at: str
    socket: str
    session: str
    lines: int
    detail: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "state": self.state,
            "text": self.text,
            "geometry": self.geometry,
            "captured_at": self.captured_at,
            # Identity echo: the client binds its viewer to this and can prove
            # the frame it is painting belongs to the session it asked for.
            "socket": self.socket,
            "session": self.session,
            "lines": self.lines,
            "detail": self.detail,
        }


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_geometry(line: str) -> dict[str, Any] | None:
    parts = line.split()
    if len(parts) != 7:
        return None
    try:
        width, height, history_size, history_limit, alternate_on, cx, cy = (int(p) for p in parts)
    except ValueError:
        return None
    return {
        "width": width,
        "height": height,
        "history_size": history_size,
        "history_limit": history_limit,
        "alternate_on": bool(alternate_on),
        "cursor_x": cx,
        "cursor_y": cy,
    }


def _split_capture(stdout: str) -> tuple[str, str]:
    """Split the combined round-trip output into (metadata line, pane text).

    The metadata line is what ``display-message -p`` printed first; everything
    after the first newline is the capture.  The single trailing newline
    ``capture-pane`` emits is stripped here — leaving it on scrolls the top row
    of a full-height alt-screen TUI out of view (field guide §6, a real defect).
    """
    head, _, rest = stdout.partition("\n")
    if rest.endswith("\n"):
        rest = rest[:-1]
    return head, rest


def _classify(returncode: int, stdout: str, stderr: str) -> tuple[str, str, dict[str, Any] | None, str]:
    """Return ``(state, text, geometry, detail)`` for one tmux round-trip.

    The distinction this function exists to make: an **empty** pane and a
    **failed** observation both yield empty text, and presenting either as
    healthy is the failure mode the whole design guards against.  Metadata
    present + empty text is ``empty``; metadata unreadable is ``failed``; the
    session being gone is ``ended``.
    """
    err = (stderr or "").strip()
    if returncode != 0:
        low = err.lower()
        if any(marker in low for marker in _GONE_MARKERS):
            return "ended", "", None, err
        return "failed", "", None, err or f"tmux exited {returncode}"

    meta_line, text = _split_capture(stdout)
    geometry = _parse_geometry(meta_line)
    if geometry is None:
        return "failed", "", None, f"unreadable metadata: {meta_line!r}"
    if text.strip() == "":
        return "empty", "", geometry, ""
    return "ok", text, geometry, ""


# --------------------------------------------------------------------------
# capture cache
# --------------------------------------------------------------------------


@dataclass
class _Entry:
    frame: Frame
    mono: float


class CaptureCache:
    """One capture per session per tick, fanned out to every client.

    N browser tabs must not multiply tmux captures.  A frame younger than
    ``tick_ms`` is served as-is; a stale key is refreshed under a per-key
    single-flight lock, so concurrent clients coalesce onto one subprocess
    instead of stampeding.

    ``captures`` counts actual tmux round-trips and is the evidence that the
    fan-out works.
    """

    def __init__(self, tick_ms: int = TICK_MS) -> None:
        self.tick_ms = tick_ms
        self.captures = 0
        self._entries: dict[tuple[str, str, int], _Entry] = {}
        self._locks: dict[tuple[str, str, int], asyncio.Lock] = {}

    # -- internals ---------------------------------------------------------

    def _fresh(self, key: tuple[str, str, int]) -> Frame | None:
        entry = self._entries.get(key)
        if entry is None:
            return None
        if (time.monotonic() - entry.mono) * 1000.0 < self.tick_ms:
            return entry.frame
        return None

    async def _capture(self, socket: str, session: str, lines: int) -> Frame:
        """ONE tmux round-trip: metadata and capture, chained with ``;``."""
        argv = self.command(socket, session, lines)
        self.captures += 1
        try:
            proc = await asyncio.create_subprocess_exec(
                *argv,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=_env(),
            )
            out_b, err_b = await proc.communicate()
            returncode = proc.returncode or 0
        except FileNotFoundError:
            return Frame(
                state="failed",
                text="",
                geometry=None,
                captured_at=_now_iso(),
                socket=socket,
                session=session,
                lines=lines,
                detail="tmux not found on PATH",
            )
        except OSError as exc:  # pragma: no cover - defensive
            return Frame(
                state="failed",
                text="",
                geometry=None,
                captured_at=_now_iso(),
                socket=socket,
                session=session,
                lines=lines,
                detail=f"tmux could not be run: {exc}",
            )

        stdout = out_b.decode("utf-8", "replace")
        stderr = err_b.decode("utf-8", "replace")
        state, text, geometry, detail = _classify(returncode, stdout, stderr)
        return Frame(
            state=state,
            text=text,
            geometry=geometry,
            # The tmux tick this frame came from, never the time it was served.
            captured_at=_now_iso(),
            socket=socket,
            session=session,
            lines=lines,
            detail=detail,
        )

    # -- public ------------------------------------------------------------

    @staticmethod
    def command(socket: str, session: str, lines: int) -> list[str]:
        """The exact argv of the single tmux round-trip (also printed as evidence).

        ``-e`` keeps colours; ``-a`` is deliberately absent (measured blank);
        the ``;`` element is tmux's own command separator, so this is one
        process and one server round-trip.
        """
        lines = max(1, min(int(lines), MAX_LINES))
        return [
            "tmux",
            *_socket_args(socket),
            "display-message",
            "-p",
            "-t",
            _target(session),
            _TMUX_FORMAT,
            ";",
            "capture-pane",
            "-e",
            "-p",
            "-t",
            _target(session),
            "-S",
            f"-{lines}",
        ]

    async def get(self, socket: str, session: str, lines: int = DEFAULT_LINES) -> Frame:
        lines = max(1, min(int(lines), MAX_LINES))
        key = (socket, session, lines)

        frame = self._fresh(key)
        if frame is not None:
            return frame

        lock = self._locks.get(key)
        if lock is None:
            lock = self._locks.setdefault(key, asyncio.Lock())

        async with lock:
            # Re-check: whoever held the lock may have just refreshed it.
            frame = self._fresh(key)
            if frame is not None:
                return frame
            frame = await self._capture(socket, session, lines)
            self._entries[key] = _Entry(frame=frame, mono=time.monotonic())
            return frame

    def reset(self) -> None:
        self._entries.clear()
        self._locks.clear()
        self.captures = 0


#: Module-level cache the router uses.  Tests read ``CACHE.captures``.
CACHE = CaptureCache()


# --------------------------------------------------------------------------
# sessions listing
# --------------------------------------------------------------------------

_LIST_FORMAT = "#{session_name}\t#{pane_current_path}\t#{session_activity}\t#{socket_path}"


async def list_sessions(socket: str) -> dict[str, Any]:
    argv = ["tmux", *_socket_args(socket), "list-sessions", "-F", _LIST_FORMAT]
    sessions: list[dict[str, Any]] = []
    error = ""
    socket_path = ""
    try:
        proc = await asyncio.create_subprocess_exec(
            *argv,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=_env(),
        )
        out_b, err_b = await proc.communicate()
        returncode = proc.returncode or 0
    except FileNotFoundError:
        returncode, out_b, err_b = 127, b"", b"tmux not found on PATH"

    if returncode != 0:
        # No server on this socket is a normal, honest answer: zero sessions.
        error = err_b.decode("utf-8", "replace").strip()
    else:
        for line in out_b.decode("utf-8", "replace").splitlines():
            if not line.strip():
                continue
            parts = line.split("\t")
            while len(parts) < 4:
                parts.append("")
            name, cwd, activity, sock_path = parts[0], parts[1], parts[2], parts[3]
            socket_path = socket_path or sock_path
            last_activity = ""
            try:
                last_activity = datetime.fromtimestamp(int(activity), tz=timezone.utc).isoformat()
            except (TypeError, ValueError):
                last_activity = activity
            sessions.append(
                {
                    "name": name,
                    "socket": socket,
                    "cwd": cwd,
                    "last_activity": last_activity,
                }
            )

    return {
        "socket": socket,
        "socket_path": socket_path,
        "sessions": sessions,
        "count": len(sessions),
        # We resolved the socket from configuration and ignored the ambient
        # one; say so, so an operator knows which server this is.
        "ambient_tmux_ignored": ambient_tmux_ignored(),
        "error": error,
    }


# --------------------------------------------------------------------------
# router
# --------------------------------------------------------------------------

router = APIRouter(prefix="/api/tmux", tags=["tmux"])


@router.get("/sessions")
async def get_sessions(socket: str = Query("hw")) -> dict[str, Any]:
    """Live sessions on an explicit socket, plus the ambient socket we ignored."""
    return await list_sessions(socket)


@router.get("/{socket}/{session}")
async def get_session(
    socket: str,
    session: str,
    lines: int = Query(DEFAULT_LINES, ge=1, le=MAX_LINES),
) -> dict[str, Any]:
    """One frame of one pane: state, text, geometry, captured_at.

    Always answers for the session named in the path — on loss the state is
    ``ended``, never another session's pane.
    """
    frame = await CACHE.get(socket, session, lines)
    return frame.as_dict()
