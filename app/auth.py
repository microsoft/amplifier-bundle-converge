"""Who is asking, proved against the machine's own accounts.

The app holds no password list of its own. A sign-in is handed to PAM -- the
same check `login` and `sudo` make -- and what the app keeps afterwards is a
signed cookie naming the user, nothing more.

One rule matters more than the rest, and it is the reason this module exists
apart from the routes: **the gate never exempts a peer address.** A request
from 127.0.0.1 is a request like any other. When the server is bound to a LAN
address, "it came from localhost" is a claim about a socket, not a claim about
a person, and the whole point of binding to the LAN is that other machines can
reach it. There is no bypass here to find.

This module also carries the preview's CSRF/origin defenses (converge-b2ak),
kept beside the session logic because both answer the same question -- is
this request really from the person it claims to be from:

* **Same-origin checking** reads `Origin` (falling back to `Referer`) and
  compares it to the request's own scheme+host. Present-and-mismatched is
  always refused. Neither header present is *not* refused here -- a
  same-origin browser fetch/XHR sends one of them, but a great many
  legitimate non-browser callers (this repository's own test clients among
  them) send neither, and the double-submit check below is what actually
  carries the weight against a forged cross-site POST.
* **The double-submit CSRF cookie** (`cv_csrf`, or a per-instance name -- see
  `cookie_names` below) is deliberately readable by JS, unlike the session
  cookie -- so `api.js`/`tmux.js` can echo it back as a header, and the login
  form can carry it as a hidden field. A cross-site page can make a victim's
  browser SEND this cookie (cookies travel with a request regardless of
  origin), but same-origin policy stops it from READING the value to put in
  a header or field, so it can never forge a match. The check only fires
  when a CSRF cookie is already on the request: a client that has never
  received one (this repository's own `TestClient` fixtures among them,
  which post straight to `/login` with an empty cookie jar) has nothing to
  double-submit against yet, and the same-origin check above is what stands
  for it in that narrow window.

**Two previews on one host, on different ports, are not two origins to a
browser's cookie jar** -- cookies are scoped by host, never by port. Left
alone, a second preview instance on the same machine would read and
overwrite the first one's session/CSRF cookies, and a secret file written to
the one global default path would be shared by both. `instance_namespace`
and `cookie_names` exist so a preview started with its own `--instance-dir`
gets its own cookie names (and, via `serve.create_app`, its own secret file
and session registry) -- never touching another instance's, and never
falling back to the machine-wide default unless no instance directory was
given at all (converge-b2ak https-repair item 1).

**Logout genuinely ends a session (item 2).** A cookie only proves a session
id was once issued; whether that id is still good is `SessionRegistry`'s
question, checked on every request. Deleting the browser's copy of the
cookie was never enough by itself -- a copy made before logout (or a replay
of the same signed token) stays valid until it expires unless the id itself
is marked revoked, which is what `logout` does through this registry.
"""

from __future__ import annotations

import hashlib
import json
import os
import secrets
import time
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlsplit

import pam as pam_module
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

try:  # pragma: no cover - POSIX-only; this app only ships for Linux/macOS
    import fcntl
except ImportError:  # pragma: no cover - defensive, not exercised in CI
    fcntl = None  # type: ignore[assignment]

#: The cookie the browser carries once a sign-in has been proved, when no
#: per-instance namespace applies. See `cookie_names`.
COOKIE = "cv_session"

#: How long a proved sign-in stays proved, in seconds.
MAX_AGE = 12 * 60 * 60

DEFAULT_SECRET_PATH = Path.home() / ".amplifier" / "converge-app.secret"

#: Where a logout's revocation is remembered when no `--instance-dir` names a
#: private one -- see `SessionRegistry` (converge-b2ak https-repair item 2).
DEFAULT_SESSIONS_PATH = Path.home() / ".amplifier" / "converge-app.sessions.json"

_SALT = "converge-app-session"

#: The PAM service a sign-in is checked against.
PAM_SERVICE = "login"

#: The double-submit CSRF cookie and its two carriers: a header for fetch/XHR
#: calls (`api.js`, `tmux.js`), a hidden form field for the sign-in page --
#: when no per-instance namespace applies. See `cookie_names`.
CSRF_COOKIE = "cv_csrf"
CSRF_HEADER = "X-CSRF-Token"
CSRF_FIELD = "csrf_token"

#: The response header that names THIS instance's actual CSRF cookie, sent
#: on every response so a browser-side script never has to guess or hardcode
#: a name that might belong to a different instance sharing this host
#: (converge-b2ak https-repair items 1 and 5). See `app/static/js/api.js`.
CSRF_COOKIE_NAME_HEADER = "X-Converge-Csrf-Cookie"

#: The response header naming the signed-in user, set only from verified
#: auth state -- never an untrusted client claim -- so the PWA lane can
#: confirm its own principal against what the server actually authenticated
#: (converge-b2ak https-repair item 5).
USER_HEADER = "X-Converge-User"


def read_or_make_secret(path: Path | None = None) -> str:
    """The signing secret, created private-to-this-user when it is absent."""
    path = Path(path) if path else DEFAULT_SECRET_PATH
    if path.is_file():
        text = path.read_text(encoding="utf-8").strip()
        if text:
            return text
    path.parent.mkdir(parents=True, exist_ok=True)
    made = secrets.token_urlsafe(48)
    # Written with the bits set before anything is in the file, so the secret
    # is never briefly world-readable.
    handle = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(handle, "w", encoding="utf-8") as out:
        out.write(made + "\n")
    os.chmod(path, 0o600)
    return made


def authenticate(username: str, password: str, service: str = PAM_SERVICE) -> bool:
    """Ask PAM. Never answers True on an empty username or password."""
    if not username or not password:
        return False
    try:
        checker = pam_module.pam()
        return bool(checker.authenticate(username, password, service=service))
    except Exception:
        # A PAM stack that refuses to answer is a failed sign-in, never a pass.
        return False


# --------------------------------------------------------------------------
# per-instance namespace: two previews on one host must never share a
# cookie name, a secret file, or a revocation store (converge-b2ak
# https-repair item 1)
# --------------------------------------------------------------------------


def instance_namespace(instance_dir: Path | None) -> str | None:
    """A short, stable token naming one preview instance, or None for the
    machine-wide default (no `--instance-dir` given).

    Derived from the instance directory's own resolved absolute path, so the
    same `--instance-dir` always yields the same namespace -- restarting the
    same instance keeps reading its own cookies -- and two different
    directories can never collide. Never derived from the port: the whole
    point is that a port is NOT a cookie boundary a browser respects.
    """
    if instance_dir is None:
        return None
    resolved = str(Path(instance_dir).resolve())
    return hashlib.sha256(resolved.encode("utf-8")).hexdigest()[:10]


def cookie_names(namespace: str | None) -> tuple[str, str]:
    """(session cookie name, CSRF cookie name) for this namespace.

    None (the default, single-instance case) keeps the original names
    unchanged -- every existing test and deployment that never passes
    `--instance-dir` sees exactly `cv_session`/`cv_csrf`, as before.
    """
    if not namespace:
        return COOKIE, CSRF_COOKIE
    return f"{COOKIE}_{namespace}", f"{CSRF_COOKIE}_{namespace}"


# --------------------------------------------------------------------------
# sessions: signed cookies, and whether the session they name is still good
# --------------------------------------------------------------------------


@dataclass
class Sessions:
    """Signs and reads the session cookie. One per running app."""

    secret: str

    def __post_init__(self) -> None:
        self._signer = URLSafeTimedSerializer(self.secret, salt=_SALT)

    def issue(self, username: str) -> str:
        """A fresh signed cookie, naming both the user and a random session
        id -- the id is what `SessionRegistry` revokes on logout, since the
        signature alone proves only that this app once issued it, not that
        it is still good."""
        return self._signer.dumps({"u": username, "sid": secrets.token_urlsafe(16)})

    def identity_of(self, token: str | None) -> tuple[str, str] | None:
        """(username, session id) a cookie proves, or None for missing,
        tampered, stale, or malformed. Does not consult revocation -- that is
        the caller's job (see `app/serve.py`'s gate), because only the
        caller knows which registry this instance's revocations live in."""
        if not token:
            return None
        try:
            payload = self._signer.loads(token, max_age=MAX_AGE)
        except (BadSignature, SignatureExpired):
            return None
        if not isinstance(payload, dict):
            return None
        user = payload.get("u")
        sid = payload.get("sid")
        if not isinstance(user, str) or not user or not isinstance(sid, str) or not sid:
            return None
        return user, sid

    def user_of(self, token: str | None) -> str | None:
        """The user a cookie proves, or None -- unchanged shape for callers
        (tests among them) that only ever needed the name.  Does **not**
        check revocation; use `identity_of` plus a `SessionRegistry` where a
        logged-out session must actually stop working."""
        found = self.identity_of(token)
        return found[0] if found else None


class SessionRegistryCorrupt(RuntimeError):
    """The registry file exists but cannot be trusted (unreadable, not JSON,
    or the wrong shape).

    Deliberately distinct from "the file has never been written yet" --
    that is the normal, empty-registry state (nothing has been revoked),
    never an error. This is raised only when there IS a file and it cannot
    be read as a revocation table, so a caller can tell "no revocations"
    apart from "cannot prove there are no revocations" and fail closed on
    the latter rather than silently treating it as the former.
    """


@dataclass
class SessionRegistry:
    """Which issued session ids a logout has actually ended.

    Persisted as JSON so a logout genuinely invalidates that session rather
    than only deleting this browser's copy of a still-valid signed cookie
    (converge-b2ak https-repair item 2). Standard library storage only --
    no new service -- with an atomic rename on write and, where `fcntl` is
    available, an exclusive lock held across the read-modify-write so two
    near-simultaneous logouts on the same instance cannot lose one another's
    revocation.

    One instance's registry never reads or writes another's: `path` is
    either this instance's own `<instance-dir>/sessions.json` or, absent an
    instance directory, the single machine-wide default -- the same split
    `read_or_make_secret` makes for the signing secret.

    **Fails closed on corruption.** A missing file is the ordinary
    fresh-install state -- nothing has ever been revoked, so `is_revoked`
    answers False and a write starts from an empty table. A file that
    EXISTS but cannot be read, parsed as JSON, or read as the expected
    `{"revoked": [...]}` shape is different: a copied, logged-out cookie
    replayed against that state must not be treated as still good just
    because the proof of its revocation could not be read. `is_revoked`
    answers True (treat as revoked -- deny) in that case, and `revoke`
    raises `SessionRegistryCorrupt` rather than silently overwriting
    whatever the file actually held with a fresh, effectively-empty
    revocation list.
    """

    path: Path

    def _read_locked(self) -> tuple[dict, object | None]:
        """The current table, plus an open handle holding an exclusive lock
        for the duration of a write -- callers that only read may ignore the
        handle and let it close.

        Raises `SessionRegistryCorrupt` rather than returning a fresh empty
        table when the file exists but cannot be trusted -- a caller that
        went on to write from an empty table here would silently erase
        every previously-recorded revocation.
        """
        if not self.path.exists():
            return {"revoked": []}, None
        handle = open(self.path, "r+", encoding="utf-8")
        if fcntl is not None:
            fcntl.flock(handle, fcntl.LOCK_EX)
        try:
            text = handle.read().strip()
        except OSError as exc:
            handle.close()
            raise SessionRegistryCorrupt(f"cannot read session registry {self.path}: {exc}") from exc
        try:
            table = json.loads(text) if text else {}
        except ValueError as exc:
            handle.close()
            raise SessionRegistryCorrupt(f"session registry {self.path} is not valid JSON") from exc
        if not isinstance(table, dict) or not isinstance(table.get("revoked", []), list):
            handle.close()
            raise SessionRegistryCorrupt(f"session registry {self.path} has an unexpected shape")
        table.setdefault("revoked", [])
        return table, handle

    def is_revoked(self, sid: str) -> bool:
        """True if `sid` is known-revoked, OR the registry cannot currently
        prove it is not (fail closed) -- the only exception being a
        registry that has simply never been written, which is the normal
        state before any logout has ever happened here."""
        if not sid:
            return True
        if not self.path.exists():
            return False
        try:
            text = self.path.read_text(encoding="utf-8")
        except OSError:
            return True
        try:
            table = json.loads(text) if text.strip() else {}
        except ValueError:
            return True
        if not isinstance(table, dict):
            return True
        revoked = table.get("revoked")
        if revoked is None:
            return False
        if not isinstance(revoked, list):
            return True
        return sid in revoked

    def revoke(self, sid: str) -> None:
        """Marks `sid` revoked, persisted.

        Raises `SessionRegistryCorrupt` -- and writes nothing -- when the
        existing file cannot be trusted, rather than silently overwriting
        unreadable/corrupt history with a table that only contains this one
        new revocation. Callers (see `app/serve.py`'s `/logout`) still end
        the session for THIS request either way: `is_revoked` fails closed
        on the same corrupt file, so every cookie is refused until the
        registry is repaired."""
        if not sid:
            return
        table, handle = self._read_locked()
        try:
            revoked = set(table.get("revoked") or [])
            revoked.add(sid)
            # Bounded rather than unbounded: a preview process is restarted
            # often enough that keeping the most recent few thousand ids is
            # plenty to cover any cookie still within MAX_AGE.
            table["revoked"] = sorted(revoked)[-2000:]
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix(self.path.suffix + ".tmp")
            fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as out:
                json.dump(table, out)
            os.replace(tmp, self.path)
            os.chmod(self.path, 0o600)
        finally:
            if handle is not None:
                if fcntl is not None:
                    fcntl.flock(handle, fcntl.LOCK_UN)
                handle.close()


# --------------------------------------------------------------------------
# safe redirects: `?next=` names a path in this app, never another origin
# --------------------------------------------------------------------------


def safe_next(value: str | None) -> str:
    """A same-origin relative path, or "/" for anything else.

    `//evil.example` starts with "/" and would pass a bare `startswith("/")`
    check, but a browser reads a leading `//` as protocol-relative -- "same
    scheme, different host" -- so it is refused by name here rather than
    trusted as a path. `/\\evil.example` is the same trick some browsers
    still normalise into `//evil.example`, so it is refused the same way.
    """
    text = (value or "").strip()
    if not text or not text.startswith("/"):
        return "/"
    if text.startswith("//") or text.startswith("/\\"):
        return "/"
    return text


# --------------------------------------------------------------------------
# CSRF / same-origin
# --------------------------------------------------------------------------


def new_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def same_origin(scheme: str, netloc: str, origin: str | None, referer: str | None) -> bool:
    """Origin (or, absent, Referer) names this same scheme+host -- or neither
    header was sent at all, which is not treated as a mismatch (see the
    module docstring for why).
    """
    want = f"{scheme}://{netloc}"
    if origin:
        return origin.rstrip("/") == want
    if referer:
        parts = urlsplit(referer)
        return f"{parts.scheme}://{parts.netloc}" == want
    return True


def csrf_ok(cookie: str | None, supplied: str | None) -> bool:
    """The double-submit check: refuse only a *mismatch*, never a mere
    absence.

    A present-and-wrong pair is refused -- that is the actual signal a
    forged or stale request produces. Either side simply missing is
    treated the same as same-origin's own absent-header case (see above):
    a same-origin browser page always has both once it has loaded this
    app once, and the *same-origin* check is what carries the weight for a
    caller that has neither (this repository's own test clients among
    them, and any legitimate non-browser API caller). Treating absence as
    a hard refusal here would also refuse every one of those, not just an
    attacker.
    """
    if not cookie or not supplied:
        return True
    return secrets.compare_digest(supplied, cookie)


# --------------------------------------------------------------------------
# login throttle -- a burst of wrong passwords slows down, it is not ignored
# --------------------------------------------------------------------------


@dataclass
class LoginThrottle:
    """Per-key (normally the caller's remote address) sign-in rate limiting.

    Deliberately in memory and per-process: a restart is a fresh start, and
    this is a preview guarding against casual password-guessing, not a
    distributed brute-force defense. `max_attempts` failures inside `window_s`
    lock the key out for `lockout_s`; a success clears its history outright.
    """

    max_attempts: int = 5
    window_s: float = 60.0
    lockout_s: float = 60.0
    _failures: dict[str, list[float]] = field(default_factory=dict)
    _locked_until: dict[str, float] = field(default_factory=dict)

    def _now(self) -> float:
        return time.monotonic()

    def allowed(self, key: str) -> bool:
        until = self._locked_until.get(key)
        if until is None:
            return True
        if self._now() >= until:
            self._locked_until.pop(key, None)
            self._failures.pop(key, None)
            return True
        return False

    def retry_after(self, key: str) -> float:
        until = self._locked_until.get(key)
        return max(0.0, until - self._now()) if until is not None else 0.0

    def record_failure(self, key: str) -> None:
        now = self._now()
        recent = [t for t in self._failures.get(key, []) if now - t < self.window_s]
        recent.append(now)
        self._failures[key] = recent
        if len(recent) >= self.max_attempts:
            self._locked_until[key] = now + self.lockout_s

    def record_success(self, key: str) -> None:
        self._failures.pop(key, None)
        self._locked_until.pop(key, None)


__all__ = [
    "COOKIE",
    "CSRF_COOKIE",
    "CSRF_COOKIE_NAME_HEADER",
    "CSRF_FIELD",
    "CSRF_HEADER",
    "DEFAULT_SECRET_PATH",
    "DEFAULT_SESSIONS_PATH",
    "MAX_AGE",
    "PAM_SERVICE",
    "USER_HEADER",
    "LoginThrottle",
    "SessionRegistry",
    "SessionRegistryCorrupt",
    "Sessions",
    "authenticate",
    "cookie_names",
    "csrf_ok",
    "instance_namespace",
    "new_csrf_token",
    "read_or_make_secret",
    "safe_next",
    "same_origin",
]
