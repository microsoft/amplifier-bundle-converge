"""Who is asking, proved against the machine's own accounts.

The app holds no password list of its own. A sign-in is handed to PAM — the
same check `login` and `sudo` make — and what the app keeps afterwards is a
signed cookie naming the user, nothing more.

One rule matters more than the rest, and it is the reason this module exists
apart from the routes: **the gate never exempts a peer address.** A request
from 127.0.0.1 is a request like any other. When the server is bound to a LAN
address, "it came from localhost" is a claim about a socket, not a claim about
a person, and the whole point of binding to the LAN is that other machines can
reach it. There is no bypass here to find.
"""

from __future__ import annotations

import os
import secrets
from dataclasses import dataclass
from pathlib import Path

import pam as pam_module
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

#: The cookie the browser carries once a sign-in has been proved.
COOKIE = "cv_session"

#: How long a proved sign-in stays proved, in seconds.
MAX_AGE = 12 * 60 * 60

DEFAULT_SECRET_PATH = Path.home() / ".amplifier" / "converge-app.secret"

_SALT = "converge-app-session"

#: The PAM service a sign-in is checked against.
PAM_SERVICE = "login"


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


@dataclass
class Sessions:
    """Signs and reads the session cookie. One per running app."""

    secret: str

    def __post_init__(self) -> None:
        self._signer = URLSafeTimedSerializer(self.secret, salt=_SALT)

    def issue(self, username: str) -> str:
        return self._signer.dumps({"u": username})

    def user_of(self, token: str | None) -> str | None:
        """The user a cookie proves, or None for missing, tampered, or stale."""
        if not token:
            return None
        try:
            payload = self._signer.loads(token, max_age=MAX_AGE)
        except (BadSignature, SignatureExpired):
            return None
        user = payload.get("u") if isinstance(payload, dict) else None
        return user if isinstance(user, str) and user else None


__all__ = [
    "COOKIE",
    "MAX_AGE",
    "PAM_SERVICE",
    "DEFAULT_SECRET_PATH",
    "Sessions",
    "authenticate",
    "read_or_make_secret",
]
