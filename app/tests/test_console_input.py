"""The console the app SERVES is the console the contract promises.

``experience-console.v1`` Core 3 says the console *is* the manager session:
"what you type there is what the manager session receives".  Core 9 says it is
not a native chat in V1, and the app says so.

Both were made true in the browser by ``converge-tfu`` — the route exists, the
keystrokes arrive, and ``app/static/js/render/console.js`` clears ``disabled``
at render time.  None of that moved the SERVED markup, and for four days the
served page still shipped a greyed-out input and a footer reading "read-only in
this version".  Two different readers saw the false version:

* ``conformance/experience-console/run.py`` rule 3 reads the served HTML, not
  the rendered DOM, and reported the only FAIL in that kit;
* a steward, for the whole gap between first byte and first script.

So the round trip being green is not enough, and this file is deliberately NOT
another round-trip test (``test_console_live_rendered.py`` and
``test_tmux_send_keys.py`` already prove that against a real tmux server).
**This file reads the served bytes**, which is the half nothing else watched.

Nothing here touches tmux, so there is no socket to name and none to clean up.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app import auth, serve  # noqa: E402

GOOD_USER = "tester"
GOOD_PASSWORD = "correct-horse"


class _FakePam:
    """Stands in for `pam.pam()`. Answers only for the one right password."""

    def authenticate(self, username: str, password: str, service: str = "login") -> bool:
        return username == GOOD_USER and password == GOOD_PASSWORD


@pytest.fixture
def served(tmp_path, monkeypatch) -> str:
    """The HTML a signed-in steward's browser actually receives from ``/``.

    A config with no managers is enough: the shell is the same document either
    way, and this file judges the document, not the data poured into it.
    """
    monkeypatch.setattr(auth.pam_module, "pam", _FakePam)
    conf = tmp_path / "converge-app.toml"
    conf.write_text("", encoding="utf-8")
    made = serve.create_app(
        config_path=conf,
        secret_path=tmp_path / "secret",
        # Never the real ~/.amplifier: a test must not move a steward's own
        # read point or drop their kept marks.
        state_path=tmp_path / "state.json",
    )
    client = TestClient(made, follow_redirects=False)
    answer = client.post(
        "/login", data={"username": GOOD_USER, "password": GOOD_PASSWORD, "next": "/"}
    )
    assert answer.status_code == 302, "the fixture could not sign in, so it proves nothing"
    assert auth.COOKIE in answer.cookies
    page = client.get("/")
    assert page.status_code == 200
    return page.text


def _tag(html: str, pattern: str) -> str:
    """The one tag matching ``pattern``, or a failure naming what was searched."""
    found = re.search(pattern, html)
    assert found, f"the served page carries no tag matching {pattern!r}"
    return found.group(0)


# --------------------------------------------------------------------------
# Core 3 — the served controls are live, not decoration
# --------------------------------------------------------------------------


def test_the_served_input_is_not_disabled(served: str) -> None:
    """The exact byte the kit's rule 3 fails on.

    `console.js` enabling the field at render time is not a substitute: before
    the script runs, and to every reader of the served HTML, a `disabled`
    attribute here is the app saying the console takes nothing.
    """
    field = _tag(served, r"<input[^>]*id=\"consoleInput\"[^>]*>")
    assert "disabled" not in field, f"the served console input is disabled: {field}"


def test_the_served_send_control_is_not_disabled(served: str) -> None:
    console = served[served.index('id="consoleForm"') :]
    button = _tag(console, r"<button[^>]*type=\"submit\"[^>]*>")
    assert "disabled" not in button, f"the served send control is disabled: {button}"


# --------------------------------------------------------------------------
# Core 9 — it is not a native chat, and the served page says so
# --------------------------------------------------------------------------


def test_the_served_page_says_it_is_not_a_chat(served: str) -> None:
    """Rule 9 passed only on the words "read-only in this version".

    Dropping that span to satisfy rule 3 would have turned a passing clause
    red — the two clauses share three lines of markup. This asserts the
    replacement carries the claim, so the trade can never be made silently.
    """
    assert "not a chat" in served


def test_the_served_page_no_longer_claims_to_be_read_only(served: str) -> None:
    """The sentence that was false for four days, asserted against.

    The app has taken keystrokes since ``converge-tfu``. A page still saying
    the console is read-only in this version sends a steward looking for a
    feature that is already here.
    """
    assert not re.search(r"read.only in this version", served, re.I), (
        "the served page still says the console is read-only, "
        "though POST /api/tmux/{socket}/{session}/keys answers"
    )


# --------------------------------------------------------------------------
# the path a typed line takes has to exist for any of the above to mean anything
# --------------------------------------------------------------------------


def test_a_route_exists_to_carry_a_keystroke(tmp_path, monkeypatch) -> None:
    """A live-looking control with nowhere to send is worse than a dead one.

    Rule 3 judges the pair together, so this file does too. Whether the line
    ARRIVES is a real round trip, proved in ``test_tmux_send_keys.py``.

    Read through the OpenAPI schema, not ``app.routes``. Measured on the pinned
    FastAPI here: a router added with ``include_router`` stays wrapped as a
    single ``_IncludedRouter`` entry rather than being flattened into
    ``app.routes``, so walking that list finds none of the tmux paths and a test
    that walked it would fail while the route answered perfectly well. The
    schema is also what a reader outside the process sees, which is the point.
    """
    monkeypatch.setattr(auth.pam_module, "pam", _FakePam)
    conf = tmp_path / "converge-app.toml"
    conf.write_text("", encoding="utf-8")
    made = serve.create_app(
        config_path=conf, secret_path=tmp_path / "secret", state_path=tmp_path / "state.json"
    )
    paths = made.openapi()["paths"]
    keys = [p for p, methods in paths.items() if "keys" in p and "post" in methods]
    assert keys, (
        "no POST route carries a keystroke to a session, so the served console's "
        f"now-live controls send nowhere; paths seen: {sorted(paths)}"
    )
