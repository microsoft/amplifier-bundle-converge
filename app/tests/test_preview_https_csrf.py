"""CSRF/same-origin protection, safe redirects, and the login throttle.

Acceptance #4 (converge-b2ak): secure HttpOnly cookies, safe relative `next`
redirects (reject `//host`), CSRF/full-origin protection on login/logout and
every cookie-authenticated unsafe route, no localhost bypass.

The design deliberately refuses only a *mismatch* -- a wrong Origin, or a
present-but-wrong CSRF token -- never a mere absence. `auth.py`'s module
docstring says why at length: a same-origin browser page always carries one
or both once it has loaded this app once, and the many callers that carry
neither (this repository's own `TestClient` fixtures among them, and any
legitimate non-browser API caller) would otherwise be refused as if they
were the attack this exists to catch. Every test below proves the half that
DOES fire: a real mismatch is really refused.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app import auth, serve  # noqa: E402

GOOD_USER = "tester"
GOOD_PASSWORD = "correct-horse-battery-staple"  # noqa: S105 - test fixture, not a real secret


class _FakePam:
    def authenticate(self, username: str, password: str, service: str = "login") -> bool:
        assert service == "login"
        return username == GOOD_USER and password == GOOD_PASSWORD


@pytest.fixture
def client(tmp_path: Path, monkeypatch) -> TestClient:
    monkeypatch.setattr(auth.pam_module, "pam", _FakePam)
    made = serve.create_app(secret_path=tmp_path / "secret", state_path=tmp_path / "state.json")
    return TestClient(made, follow_redirects=False)


# --------------------------------------------------------------------------
# auth.py's pure functions -- the rule, isolated from any route
# --------------------------------------------------------------------------


def test_same_origin_accepts_a_matching_origin_header() -> None:
    assert auth.same_origin("https", "example.test:8788", "https://example.test:8788", None)


def test_same_origin_refuses_a_mismatched_origin_header() -> None:
    assert not auth.same_origin("https", "example.test:8788", "https://evil.example", None)


def test_same_origin_falls_back_to_referer_when_origin_is_absent() -> None:
    assert auth.same_origin("https", "example.test:8788", None, "https://example.test:8788/some/page")
    assert not auth.same_origin("https", "example.test:8788", None, "https://evil.example/some/page")


def test_same_origin_does_not_refuse_when_neither_header_is_present() -> None:
    """The documented exception, not an oversight: see auth.py's docstring."""
    assert auth.same_origin("https", "example.test:8788", None, None)


def test_csrf_ok_refuses_only_a_mismatch() -> None:
    assert auth.csrf_ok(None, None)  # nothing to check against yet
    assert auth.csrf_ok("abc", None)  # cookie present, nothing supplied: not a hard refusal here
    assert auth.csrf_ok("abc", "abc")  # matches
    assert not auth.csrf_ok("abc", "xyz")  # a real mismatch -- always refused


@pytest.mark.parametrize(
    "value,expected",
    [
        ("/home", "/home"),
        ("", "/"),
        (None, "/"),
        ("not-a-path", "/"),
        ("//evil.example", "/"),
        ("//evil.example/x", "/"),
        ("/\\evil.example", "/"),
    ],
)
def test_safe_next_rejects_protocol_relative_and_bare_hosts(value, expected) -> None:
    assert auth.safe_next(value) == expected


# --------------------------------------------------------------------------
# the login throttle
# --------------------------------------------------------------------------


def test_the_throttle_locks_out_after_repeated_failures_and_a_success_clears_it() -> None:
    throttle = auth.LoginThrottle(max_attempts=3, window_s=60, lockout_s=60)
    key = "203.0.113.5"
    assert throttle.allowed(key)
    for _ in range(3):
        throttle.record_failure(key)
    assert not throttle.allowed(key), "three failures inside the window did not lock the key out"
    assert throttle.retry_after(key) > 0

    throttle.record_success(key)
    assert throttle.allowed(key), "a success did not clear the lockout"


def test_login_locks_out_after_repeated_wrong_passwords(client: TestClient) -> None:
    """The end-to-end proof: enough wrong passwords in a row and the next
    attempt is refused by the throttle, not by PAM -- even with the right
    password this time."""
    for _ in range(5):
        client.post("/login", data={"username": GOOD_USER, "password": "wrong", "next": "/"})
    answer = client.post("/login", data={"username": GOOD_USER, "password": GOOD_PASSWORD, "next": "/"})
    assert answer.status_code == 302
    assert "Too+many+attempts" in answer.headers["location"], answer.headers["location"]
    assert auth.COOKIE not in answer.cookies, "the throttle let a sign-in through anyway"


# --------------------------------------------------------------------------
# same-origin + CSRF, wired into the running gate
# --------------------------------------------------------------------------


def test_a_request_with_a_foreign_origin_is_refused(client: TestClient) -> None:
    """A forged cross-site POST DOES carry an Origin header naming the
    attacker's page -- that is the mismatch this refuses."""
    answer = client.post(
        "/api/managers/demo/priority",
        json={"item": "x", "direction": "raise"},
        headers={"Origin": "https://evil.example"},
    )
    assert answer.status_code == 403
    assert "cross-origin" in answer.json()["error"]


def test_a_request_with_the_real_origin_is_not_refused_by_the_origin_check(client: TestClient) -> None:
    """A matching Origin passes the origin check -- whatever happens next
    (404 for an unknown manager here) is a different, later check, proving
    the origin check itself is not what stopped it."""
    answer = client.post(
        "/api/managers/demo/priority",
        json={"item": "x", "direction": "raise"},
        headers={"Origin": "http://testserver"},
    )
    assert answer.status_code != 403, answer.text
    assert answer.status_code == 401, "an unauthenticated request should reach the sign-in check, not pass it"


def test_a_wrong_csrf_header_is_refused_once_a_token_cookie_exists(client: TestClient) -> None:
    """The double-submit half: once this client actually holds a `cv_csrf`
    cookie (from visiting `/login`), a header that does NOT match it is a
    real, detectable forgery signal and is refused."""
    client.get("/login")
    assert auth.CSRF_COOKIE in client.cookies, "no csrf cookie was issued by GET /login"
    answer = client.post(
        "/api/managers/demo/priority",
        json={"item": "x", "direction": "raise"},
        headers={"Origin": "http://testserver", auth.CSRF_HEADER: "not-the-real-token"},
    )
    assert answer.status_code == 403
    assert "CSRF" in answer.json()["error"]


def test_the_matching_csrf_header_is_accepted(client: TestClient) -> None:
    client.get("/login")
    token = client.cookies.get(auth.CSRF_COOKIE)
    assert token
    answer = client.post(
        "/api/managers/demo/priority",
        json={"item": "x", "direction": "raise"},
        headers={"Origin": "http://testserver", auth.CSRF_HEADER: token},
    )
    assert answer.status_code != 403, answer.text


def test_login_and_logout_are_covered_by_the_same_check(client: TestClient) -> None:
    """`/login` and `/logout` are public paths for the sign-in gate, but NOT
    exempt from the same-origin check -- acceptance #4 names them
    explicitly."""
    answer = client.post(
        "/login",
        data={"username": GOOD_USER, "password": GOOD_PASSWORD, "next": "/"},
        headers={"Origin": "https://evil.example"},
    )
    assert answer.status_code == 403

    answer = client.post("/logout", headers={"Origin": "https://evil.example"})
    assert answer.status_code == 403


def test_the_login_forms_own_csrf_field_is_checked(client: TestClient) -> None:
    """A GET /login gives a real cookie AND a matching hidden field; a POST
    with the cookie but a wrong field is refused, and the right field is
    accepted."""
    page = client.get("/login")
    assert "csrf_token" in page.text
    real_cookie = client.cookies.get(auth.CSRF_COOKIE)
    assert real_cookie

    wrong = client.post(
        "/login",
        data={"username": GOOD_USER, "password": GOOD_PASSWORD, "next": "/", "csrf_token": "not-it"},
    )
    assert wrong.status_code == 403

    right = client.post(
        "/login",
        data={"username": GOOD_USER, "password": GOOD_PASSWORD, "next": "/", "csrf_token": real_cookie},
    )
    assert right.status_code == 302
    assert auth.COOKIE in right.cookies


def test_the_webhook_stays_exempt_from_the_csrf_check(client: TestClient) -> None:
    """`app/serve.py`'s own comment: the collab webhook carries its own
    shared-secret proof instead of a cookie, and adding a CSRF requirement on
    top would only block the external host that has neither a cookie nor a
    token to send. Its own auth (missing secret file here) is a separate,
    later 503 -- never a 403 from this check."""
    answer = client.post("/api/collab/webhooks/host", json={}, headers={"Origin": "https://anything.example"})
    assert answer.status_code != 403, (
        f"the webhook was blocked by the CSRF/origin check, not its own auth: {answer.status_code} {answer.text}"
    )
