"""Instance isolation, real logout, and steward-only authority.

converge-b2ak https-repair, items 1-3 -- gaps an independent review found in
the otherwise-complete HTTPS/PAM lane:

1. Two preview instances on one host share nothing: not a cookie name (a
   port is not a cookie boundary a browser respects), not a signing secret,
   not a logout-revocation store.
2. `/logout` ends the session server-side -- a copied or replayed cookie
   from before logout must fail, not merely this browser's own copy.
3. Decision (ratification), document lock/edit/restore, priority and
   steering are the registered steward's alone; an unregistered or
   mismatched identity is refused, fail closed, in plain words. Feedback,
   asks, presence and personal read-points/keeps stay open to any
   signed-in user -- unaffected here, proven in `test_priority_write.py`
   and `test_lock_write.py`/`test_changes.py`'s own passing tests.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app import auth, serve  # noqa: E402

GOOD_USER = "tester"
GOOD_PASSWORD = "correct horse battery staple"  # noqa: S105 - test fixture, not a real secret


class _FakePam:
    def authenticate(self, username: str, password: str, service: str = "login") -> bool:
        assert service == "login"
        return username == GOOD_USER and password == GOOD_PASSWORD


@pytest.fixture(autouse=True)
def _fake_pam(monkeypatch) -> None:
    monkeypatch.setattr(auth.pam_module, "pam", _FakePam)


def _make_app(
    tmp_path: Path,
    name: str,
    steward: str | None = None,
    instance_dir: Path | None = None,
    tmux_socket: str | None = None,
    manager_tmux: str | None = None,
):
    conf = tmp_path / f"{name}.toml"
    lines = [
        "[[managers]]\n",
        f'id = "{name}"\n',
        f'name = "{name}"\n',
    ]
    if steward is not None:
        lines.append(f'steward = "{steward}"\n')
    if tmux_socket is not None:
        lines.append(f'tmux_socket = "{tmux_socket}"\n')
    if manager_tmux is not None:
        lines.append(f'manager_tmux = "{manager_tmux}"\n')
    conf.write_text("".join(lines), encoding="utf-8")
    # An explicit `instance_dir` derives its own secret/sessions files (see
    # `serve.create_app`) -- proven by `test_two_instance_dirs_get_different_secrets`
    # below, which asserts those files land under `<instance_dir>/secret`. Only
    # the no-`instance_dir` ("default") case needs an explicit override here:
    # otherwise it would fall through to the single machine-wide secret and
    # sessions files and read/write the real ones on this host (converge-e2c3).
    extra: dict[str, Path] = (
        {}
        if instance_dir is not None
        else {
            "secret_path": tmp_path / f"{name}-secret",
            "sessions_path": tmp_path / f"{name}-sessions.json",
        }
    )
    return serve.create_app(
        config_path=conf,
        state_path=tmp_path / f"{name}-state.json",
        instance_dir=instance_dir,
        **extra,
    )


def _sign_in(client: TestClient) -> None:
    answer = client.post("/login", data={"username": GOOD_USER, "password": GOOD_PASSWORD, "next": "/"})
    assert answer.status_code == 302, answer.text


# --------------------------------------------------------------------------
# item 1: namespaced cookies, secrets and revocation stores
# --------------------------------------------------------------------------


def test_two_instance_dirs_get_different_cookie_names(tmp_path: Path) -> None:
    app_a = _make_app(tmp_path, "a", instance_dir=tmp_path / "instance-a")
    app_b = _make_app(tmp_path, "b", instance_dir=tmp_path / "instance-b")
    assert app_a.state.session_cookie != app_b.state.session_cookie
    assert app_a.state.csrf_cookie != app_b.state.csrf_cookie
    # And the default (no instance dir at all) is the original, unnamespaced
    # pair -- every existing deployment and test keeps working unchanged.
    app_default = _make_app(tmp_path, "default")
    assert app_default.state.session_cookie == auth.COOKIE == "cv_session"
    assert app_default.state.csrf_cookie == auth.CSRF_COOKIE == "cv_csrf"


def test_two_instance_dirs_get_different_secrets(tmp_path: Path) -> None:
    app_a = _make_app(tmp_path, "a", instance_dir=tmp_path / "instance-a")
    app_b = _make_app(tmp_path, "b", instance_dir=tmp_path / "instance-b")
    assert (tmp_path / "instance-a" / "secret").is_file()
    assert (tmp_path / "instance-b" / "secret").is_file()
    assert app_a.state.sessions.secret != app_b.state.sessions.secret
    # A cookie signed by one instance's secret must not be honoured by the
    # other -- proof, not inference, that the secrets are really separate.
    client_a = TestClient(app_a, follow_redirects=False)
    _sign_in(client_a)
    stolen = client_a.cookies.get(app_a.state.session_cookie)
    client_b = TestClient(app_b, follow_redirects=False)
    client_b.cookies.set(app_b.state.session_cookie, stolen)
    assert client_b.get("/api/boot").status_code == 401, (
        "instance B accepted a cookie signed by instance A's secret"
    )


def test_a_shared_browser_jar_cannot_cross_instances(tmp_path: Path) -> None:
    """The scenario the review actually named: one browser, two preview
    tabs on the same host, different `--instance-dir`s. Signing in on one
    must not read, overwrite, or invalidate the other's session."""
    app_a = _make_app(tmp_path, "a", steward=GOOD_USER, instance_dir=tmp_path / "instance-a")
    app_b = _make_app(tmp_path, "b", steward=GOOD_USER, instance_dir=tmp_path / "instance-b")
    client_a = TestClient(app_a, follow_redirects=False)
    client_b = TestClient(app_b, follow_redirects=False)

    _sign_in(client_a)
    _sign_in(client_b)

    # Simulate one shared cookie jar: both instances' cookies present at
    # once, under their own distinct namespaced names -- this is exactly
    # what a real browser holds once both tabs have signed in.
    jar = {**client_a.cookies, **client_b.cookies}
    assert app_a.state.session_cookie in jar and app_b.state.session_cookie in jar

    merged_a = TestClient(app_a, follow_redirects=False)
    for k, v in jar.items():
        merged_a.cookies.set(k, v)
    assert merged_a.get("/api/boot").json()["user"] == GOOD_USER, (
        "instance A could not read its own session out of a jar also holding B's cookies"
    )

    # Now log out of A only. B's own session cookie -- a different name --
    # must be completely unaffected.
    logout_a = merged_a.post("/logout")
    assert logout_a.status_code == 302
    assert client_b.get("/api/boot").status_code == 200, (
        "logging out of instance A also invalidated instance B's session"
    )
    # And A's own (now-revoked) cookie is genuinely dead, even replayed from
    # the merged jar rather than the browser's own cookie store.
    replay_a = TestClient(app_a, follow_redirects=False)
    replay_a.cookies.set(app_a.state.session_cookie, jar[app_a.state.session_cookie])
    assert replay_a.get("/api/boot").status_code == 401


# --------------------------------------------------------------------------
# item 2: logout actually revokes the session, not just this browser's copy
# --------------------------------------------------------------------------


def test_logout_revokes_the_session_even_if_the_cookie_is_replayed(tmp_path: Path) -> None:
    app = _make_app(tmp_path, "demo", instance_dir=tmp_path / "instance")
    client = TestClient(app, follow_redirects=False)
    _sign_in(client)
    saved_cookie = client.cookies.get(app.state.session_cookie)
    assert client.get("/api/boot").status_code == 200

    client.post("/logout")

    # This client's own jar no longer carries the cookie (unchanged, prior
    # behavior) --
    assert app.state.session_cookie not in client.cookies
    # -- but the real proof is a REPLAY: a copy of the cookie saved before
    # logout (a second browser, a saved bookmark, whatever) must also now
    # be refused, because the session id itself is revoked server-side.
    replayed = TestClient(app, follow_redirects=False)
    replayed.cookies.set(app.state.session_cookie, saved_cookie)
    assert replayed.get("/api/boot").status_code == 401, (
        "a cookie saved before logout still worked after logout -- the session was never really revoked"
    )


def test_a_fresh_login_after_logout_works_again(tmp_path: Path) -> None:
    """Revocation is per session id, not per user -- signing in again issues
    a new id and is not itself refused by the registry."""
    app = _make_app(tmp_path, "demo", instance_dir=tmp_path / "instance")
    client = TestClient(app, follow_redirects=False)
    _sign_in(client)
    client.post("/logout")
    _sign_in(client)
    assert client.get("/api/boot").status_code == 200


def test_session_registry_is_revoked_and_revoke_are_consistent(tmp_path: Path) -> None:
    reg = auth.SessionRegistry(path=tmp_path / "sessions.json")
    assert not reg.is_revoked("abc")
    reg.revoke("abc")
    assert reg.is_revoked("abc")
    # A second registry pointed at the same file sees the same revocation --
    # proof this is really persisted, not merely in-memory.
    again = auth.SessionRegistry(path=tmp_path / "sessions.json")
    assert again.is_revoked("abc")


# --------------------------------------------------------------------------
# item 1 (converge-e2c3): the registry fails CLOSED on corrupt/unreadable
# state, rather than treating "cannot prove revoked" as "not revoked" --
# which is what let a copied, logged-out cookie work again.
# --------------------------------------------------------------------------


def test_missing_registry_file_is_the_ordinary_fresh_state_not_corruption(tmp_path: Path) -> None:
    """No file at all (a brand-new instance, nobody has ever logged out) is
    the normal empty-registry state -- never treated as corruption."""
    reg = auth.SessionRegistry(path=tmp_path / "never-written.json")
    assert not reg.is_revoked("anything")
    # And a write from this state must succeed normally (no exception) --
    # the fail-closed behavior below is about an EXISTING, untrustworthy
    # file, never about one that simply has not been created yet.
    reg.revoke("abc")
    assert reg.is_revoked("abc")


def test_is_revoked_fails_closed_on_corrupt_json(tmp_path: Path) -> None:
    """A registry file that exists but is not valid JSON must deny every
    session, not silently answer \"not revoked\" -- that is exactly the gap
    that let a copied, logged-out cookie work again."""
    path = tmp_path / "sessions.json"
    path.write_text("{not valid json at all", encoding="utf-8")
    reg = auth.SessionRegistry(path=path)
    assert reg.is_revoked("some-session-id") is True


def test_is_revoked_fails_closed_on_wrong_shape(tmp_path: Path) -> None:
    """Valid JSON, but not the `{"revoked": [...]}` shape this registry
    expects -- also cannot be trusted, so also fails closed."""
    path = tmp_path / "sessions.json"
    path.write_text('["just", "a", "list"]', encoding="utf-8")
    reg = auth.SessionRegistry(path=path)
    assert reg.is_revoked("some-session-id") is True

    path.write_text('{"revoked": "not-a-list"}', encoding="utf-8")
    reg2 = auth.SessionRegistry(path=path)
    assert reg2.is_revoked("some-session-id") is True


@pytest.mark.skipif(os.name != "posix" or os.geteuid() == 0, reason="permission bits are meaningless as root")
def test_is_revoked_fails_closed_on_unreadable_file(tmp_path: Path) -> None:
    """A registry file that cannot even be read (permissions) is the same
    situation as corrupt content: cannot prove not-revoked, so fails
    closed."""
    path = tmp_path / "sessions.json"
    path.write_text('{"revoked": ["already-revoked"]}', encoding="utf-8")
    path.chmod(0o000)
    try:
        reg = auth.SessionRegistry(path=path)
        assert reg.is_revoked("brand-new-id-never-revoked") is True
    finally:
        path.chmod(0o600)  # tempdir cleanup needs this back


def test_revoke_never_overwrites_corrupt_history_with_an_empty_list(tmp_path: Path) -> None:
    """A `revoke()` call against a corrupt file must not silently replace
    that file's (unreadable) history with a table holding only the new
    id -- that would erase every other revocation the corruption is hiding,
    the moment the process happens to log someone else out.

    It raises instead, and writes nothing at all.
    """
    path = tmp_path / "sessions.json"
    original = "{not valid json at all"
    path.write_text(original, encoding="utf-8")
    reg = auth.SessionRegistry(path=path)
    with pytest.raises(auth.SessionRegistryCorrupt):
        reg.revoke("new-sid")
    # Untouched -- not overwritten with a fresh, effectively-empty table.
    assert path.read_text(encoding="utf-8") == original


def test_replaying_a_prelogout_cookie_after_registry_corruption_is_still_refused(tmp_path: Path) -> None:
    """The actual attack this item closes: sign in, save a copy of the
    cookie, log out (which revokes it), then have the registry file that
    recorded the revocation become corrupted (disk fault, truncated write,
    whatever) -- the saved cookie must still not work, because the fix
    fails closed on a registry it cannot read, rather than falling back to
    "not revoked".
    """
    app = _make_app(tmp_path, "demo", instance_dir=tmp_path / "instance")
    client = TestClient(app, follow_redirects=False)
    _sign_in(client)
    saved_cookie = client.cookies.get(app.state.session_cookie)
    assert client.get("/api/boot").status_code == 200

    client.post("/logout")

    sessions_path = tmp_path / "instance" / "sessions.json"
    assert sessions_path.is_file(), "logout should have persisted a revocation"
    sessions_path.write_text("{corrupted, not json", encoding="utf-8")

    replayed = TestClient(app, follow_redirects=False)
    replayed.cookies.set(app.state.session_cookie, saved_cookie)
    assert replayed.get("/api/boot").status_code == 401, (
        "a corrupted registry let a copied, logged-out cookie work again"
    )


# --------------------------------------------------------------------------
# converge-e2c3: a terminal keystroke is a write like decision/priority/
# steer, and needs the same steward-only enforcement -- missed between lane
# ownerships. Reads (the frame/capture route) stay open to any signed-in
# user, unaffected here.
# --------------------------------------------------------------------------


def test_tmux_keys_refuse_a_signed_in_stranger(tmp_path: Path) -> None:
    app = _make_app(
        tmp_path, "demo", steward="someone-else", tmux_socket="sock1", manager_tmux="sess1"
    )
    client = TestClient(app, follow_redirects=False)
    _sign_in(client)
    answer = client.post("/api/tmux/sock1/sess1/keys", json={"keys": "echo hi", "enter": True})
    assert answer.status_code == 403, answer.text
    said = answer.json()["error"]
    assert "someone-else" in said and GOOD_USER in said, said


def test_tmux_keys_refuse_when_no_steward_is_registered(tmp_path: Path) -> None:
    app = _make_app(tmp_path, "demo", steward=None, tmux_socket="sock1", manager_tmux="sess1")
    client = TestClient(app, follow_redirects=False)
    _sign_in(client)
    answer = client.post("/api/tmux/sock1/sess1/keys", json={"keys": "echo hi", "enter": True})
    assert answer.status_code == 403, answer.text
    assert "no registered steward" in answer.json()["error"]


def test_tmux_keys_are_allowed_for_the_registered_steward(tmp_path: Path) -> None:
    """The positive case: the gate must actually open for the right
    identity, not merely close for the wrong one. No real tmux server is
    running in this fixture, so the answer past the gate is whatever
    `tmux_view.send_keys` reports for a missing session (`failed`/`ended`)
    -- the only thing asserted here is that it is not 403."""
    app = _make_app(tmp_path, "demo", steward=GOOD_USER, tmux_socket="sock1", manager_tmux="sess1")
    client = TestClient(app, follow_redirects=False)
    _sign_in(client)
    answer = client.post("/api/tmux/sock1/sess1/keys", json={"keys": "echo hi", "enter": True})
    assert answer.status_code != 403, answer.text


def test_tmux_keys_refused_when_no_manager_owns_the_session(tmp_path: Path) -> None:
    """A socket/session that names no manager's own console at all --
    a guess, a lane session, anything unregistered -- is refused the same
    as a mismatch, never treated as \"nobody's console, so anyone may type\"."""
    app = _make_app(tmp_path, "demo", steward=GOOD_USER, tmux_socket="sock1", manager_tmux="sess1")
    client = TestClient(app, follow_redirects=False)
    _sign_in(client)
    answer = client.post("/api/tmux/sock1/some-other-session/keys", json={"keys": "x", "enter": False})
    assert answer.status_code == 403, answer.text
    assert "no registered manager owns this tmux session" in answer.json()["error"]


def test_tmux_reads_stay_open_to_any_signed_in_user(tmp_path: Path) -> None:
    """The frame/capture route is a read, unaffected by the write-only
    steward check above -- any signed-in user (not just the steward) may
    still watch a console."""
    app = _make_app(tmp_path, "demo", steward="someone-else", tmux_socket="sock1", manager_tmux="sess1")
    client = TestClient(app, follow_redirects=False)
    _sign_in(client)
    answer = client.get("/api/tmux/sock1/sess1")
    assert answer.status_code != 401 and answer.status_code != 403, answer.text


# --------------------------------------------------------------------------
# item 3: steward-only authority -- ratification, document LOCKING,
# priority, steering; fails closed for no steward or a mismatch
#
# Document EDIT and RESTORE are deliberately NOT in this list (converge-bk6o).
# They were briefly gated here too, and that was too broad:
# `experience-direction.v1` Core 10 promises concurrent editing met with
# courtesy presence and reconciliation, which a single-writer gate makes
# impossible, while `experience-collaboration.v1` Core 8 reserves whose word
# COUNTS -- ratification and locking -- not every draft write. A teammate's
# write to a locked document is turned into a proposal by
# `writes.apply_change`, not refused by identity. Both halves are proven in
# `test_collaborative_drafts.py`.
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "path,payload",
    [
        ("/api/managers/demo/priority", {"item": "x", "direction": "raise"}),
        ("/api/managers/demo/steer", {"lanes": 3}),
        (
            "/api/managers/demo/decision",
            {"repoId": "r", "docId": "d", "proposalId": "p", "decision": "ratified"},
        ),
    ],
)
def test_steward_only_routes_refuse_a_signed_in_stranger(tmp_path: Path, path: str, payload: dict) -> None:
    """Registered steward is `someone-else`; GOOD_USER is signed in but is
    not that steward, and every one of these routes must refuse them by
    name -- being signed in proves identity, not authority."""
    app = _make_app(tmp_path, "demo", steward="someone-else", instance_dir=tmp_path / "instance")
    client = TestClient(app, follow_redirects=False)
    _sign_in(client)
    answer = client.post(path, json=payload)
    assert answer.status_code == 403, answer.text
    said = answer.json()["error"]
    assert "someone-else" in said and GOOD_USER in said, said


@pytest.mark.parametrize(
    "path,payload",
    [
        ("/api/managers/demo/priority", {"item": "x", "direction": "raise"}),
        ("/api/managers/demo/steer", {"lanes": 3}),
        (
            "/api/managers/demo/decision",
            {"repoId": "r", "docId": "d", "proposalId": "p", "decision": "ratified"},
        ),
    ],
)
def test_steward_only_routes_refuse_when_no_steward_is_registered(tmp_path: Path, path: str, payload: dict) -> None:
    """No `steward =` line at all: nobody is authorized yet, so this is
    refused the same as a mismatch -- never treated as "anyone may act"."""
    app = _make_app(tmp_path, "demo", steward=None, instance_dir=tmp_path / "instance")
    client = TestClient(app, follow_redirects=False)
    _sign_in(client)
    answer = client.post(path, json=payload)
    assert answer.status_code == 403, answer.text
    assert "no registered steward" in answer.json()["error"]


def test_the_registered_steward_is_not_refused(tmp_path: Path) -> None:
    """The positive case, so the gate is proven to actually open for the
    right identity, not merely close for the wrong one."""
    app = _make_app(tmp_path, "demo", steward=GOOD_USER, instance_dir=tmp_path / "instance")
    client = TestClient(app, follow_redirects=False)
    _sign_in(client)
    answer = client.post("/api/managers/demo/priority", json={"item": "x", "direction": "raise"})
    # Not 403 -- whatever it answers next (400 for "no batch directory" in
    # this bare fixture) is a different, later check, proving the steward
    # gate itself is not what stopped it.
    assert answer.status_code != 403, answer.text


def test_feedback_and_ask_stay_open_to_any_signed_in_user_no_steward_needed(tmp_path: Path) -> None:
    """The routes `preview-common.md` says must stay open -- proved directly
    against a manager with NO registered steward at all, which is exactly
    the case the gate above refuses for priority/steer/decision."""
    app = _make_app(tmp_path, "demo", steward=None, instance_dir=tmp_path / "instance")
    client = TestClient(app, follow_redirects=False)
    _sign_in(client)
    feedback = client.post("/api/managers/demo/feedback", json={"text": "looks good", "context": ""})
    assert feedback.status_code != 403, feedback.text
    ask = client.post(
        "/api/managers/demo/ask",
        json={"repoId": "r", "docId": "d", "scope": "paragraph", "text": "why?"},
    )
    assert ask.status_code != 403, ask.text
