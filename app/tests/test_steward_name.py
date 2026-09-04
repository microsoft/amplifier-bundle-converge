"""Whose word counts, settled at registration -- `experience-collaboration.v1` Core 8.

Core 8 says the steward of a manager session is a fact about the **registered
session**, not an inference from whoever happens to be signed in. Before this
change nothing carried that fact: `app/collab.py`'s `steward_of` read a field
that did not exist, so `/api/boot` named no steward and the contract's own kit
reported rule 8a as the one FAIL left in it --

    8a  FAIL  no manager session names a steward, so whose word counts is
              inferred from whoever is looking (this target answers as
              'bkrabach')

The change is one field in three places: `steward` on `ManagerConfig`, read
from the `[[managers]]` block by `_manager_from_table`, and put on the card by
`app/data.py`'s `manager_payload`.

What is real here
-----------------
Everything on the Converge side: a real config file read by the real
`config.load`, a real FastAPI app built by `app/serve.py`, a real signed-in
session through the real cookie gate, and the contract's **own** conformance
kit run in-process over the app's own `/api/boot` -- so the verdict here and
the verdict a steward gets from ``uv run
conformance/experience-collaboration/run.py <app>`` come from one piece of code
rather than two that can drift.

Only PAM stands in, because a test may not know a machine account's password.

The two halves of the acceptance, and what would falsify each
------------------------------------------------------------
* A block carrying ``steward = "wren"`` makes rule 8a PASS. Falsified if the
  kit still reads no steward, or reads a different one.
* A block naming nobody answers with an **empty** steward, not the reader's
  name. Falsified if `/api/boot` answers ``"tester"`` -- the signed-in user --
  for a manager whose registration never named anybody. That is the exact
  inference Core 8 forbids, so it is asserted against directly.
"""

from __future__ import annotations

import json
import os
import sys
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from app import auth, config, data, serve  # noqa: E402

GOOD_USER = "tester"
GOOD_PASSWORD = "hunter2"
MANAGER = "demo"

#: Per-run socket name -- see `app/tests/conftest.py`. Nothing is ever started
#: on it; the point is that no OTHER run's tmux server can answer for it either.
SOCKET = f"cvsteward-{os.getpid()}-{uuid.uuid4().hex[:8]}"


# --------------------------------------------------------------------------
# a registration, and an app around it
# --------------------------------------------------------------------------
def _write_config(tmp_path: Path, steward_line: str) -> Path:
    """One `[[managers]]` block, with or without a `steward` line."""
    batch = tmp_path / "hw-demo"
    batch.mkdir(exist_ok=True)
    (batch / "HIGHWAY.md").write_text("# HIGHWAY\n\n## Outcome\nProve Core 8.\n", encoding="utf-8")
    (batch / "manifest.tsv").write_text("lane\tworktree\tbranch\n", encoding="utf-8")

    conf = tmp_path / f"converge-app{'-with' if steward_line else '-without'}.toml"
    conf.write_text(
        "[[managers]]\n"
        f'id = "{MANAGER}"\n'
        'name = "Demo manager"\n'
        f'batch_dir = "{batch}"\n'
        f'tmux_socket = "{SOCKET}"\n'
        f"{steward_line}",
        encoding="utf-8",
    )
    return conf


class _FakePam:
    def authenticate(self, username: str, password: str, service: str = "login") -> bool:
        return username == GOOD_USER and password == GOOD_PASSWORD


def _client(conf: Path, tmp_path: Path, monkeypatch) -> TestClient:
    """The real app over that registration, signed in as `tester`."""
    monkeypatch.setattr(auth.pam_module, "pam", _FakePam)
    made = serve.create_app(
        config_path=conf,
        secret_path=tmp_path / f"secret-{conf.stem}",
        state_path=tmp_path / f"state-{conf.stem}.json",
    )
    client = TestClient(made, follow_redirects=False)
    answer = client.post("/login", data={"username": GOOD_USER, "password": GOOD_PASSWORD, "next": "/"})
    assert answer.status_code == 302 and auth.COOKIE in answer.cookies
    return client


@pytest.fixture
def registered(tmp_path: Path, monkeypatch) -> TestClient:
    """A manager session whose registration names `wren` as its steward."""
    return _client(_write_config(tmp_path, 'steward = "wren"\n'), tmp_path, monkeypatch)


@pytest.fixture
def unregistered(tmp_path: Path, monkeypatch) -> TestClient:
    """The same session, with nobody named -- the registration is unfinished."""
    return _client(_write_config(tmp_path, ""), tmp_path, monkeypatch)


# --------------------------------------------------------------------------
# the field itself
# --------------------------------------------------------------------------
def test_the_registration_is_where_the_steward_is_read_from(tmp_path: Path) -> None:
    found = config.load(_write_config(tmp_path, 'steward = "wren"\n'))
    assert found.manager(MANAGER).steward == "wren"


def test_a_registration_that_names_nobody_answers_with_nobody(tmp_path: Path) -> None:
    """No key, and a key with only blanks in it, are the same answer: empty.

    Not the reader, not the machine account, not the first repo's owner. An
    unnamed steward is a registration that has not been finished, and Core 8 is
    precisely about not filling that in by inference.
    """
    assert config.load(_write_config(tmp_path, "")).manager(MANAGER).steward == ""
    assert config.load(_write_config(tmp_path, 'steward = "   "\n')).manager(MANAGER).steward == ""


def test_a_discovered_manager_names_no_steward(tmp_path: Path) -> None:
    """Discovery finds batches, not registrations -- so it names nobody."""
    (tmp_path / "dev" / "hw-found").mkdir(parents=True)
    (tmp_path / "dev" / "hw-found" / "HIGHWAY.md").write_text("# HIGHWAY\n", encoding="utf-8")
    found = config.discover(home=tmp_path)
    assert [one.id for one in found] == ["found"]
    assert found[0].steward == ""


def test_the_manager_card_carries_the_registered_steward(tmp_path: Path) -> None:
    """`manager_payload` puts it on the card, always -- present even when empty.

    Always present is the point: a consumer reads one key and gets either a
    name or nothing, never a missing key it has to guess the meaning of.
    """
    named = config.load(_write_config(tmp_path, 'steward = "wren"\n')).manager(MANAGER)
    nobody = config.load(_write_config(tmp_path, "")).manager(MANAGER)
    assert data.manager_payload(named)["steward"] == "wren"
    assert data.manager_payload(nobody)["steward"] == ""


# --------------------------------------------------------------------------
# what `/api/boot` actually answers, over the real gate
# --------------------------------------------------------------------------
def test_boot_answers_the_registered_steward_not_the_signed_in_reader(registered, capsys) -> None:
    boot = registered.get("/api/boot").json()
    manager = boot["managers"][0]
    with capsys.disabled():
        print(f"\n  /api/boot: user={boot['user']!r} manager[0].steward={manager['steward']!r}")
    assert boot["user"] == GOOD_USER, "the reader is signed in as somebody else entirely"
    assert manager["steward"] == "wren"
    assert manager["steward"] != boot["user"], "the steward was inferred from whoever is looking"


def test_boot_answers_an_empty_steward_when_the_registration_names_nobody(unregistered, capsys) -> None:
    """The second half of the acceptance, and the inference Core 8 forbids."""
    boot = unregistered.get("/api/boot").json()
    manager = boot["managers"][0]
    with capsys.disabled():
        print(f"  /api/boot (nobody named): user={boot['user']!r} manager[0].steward={manager['steward']!r}")
    assert boot["user"] == GOOD_USER
    assert "steward" in manager, "the key vanished, so a reader cannot tell empty from absent"
    assert manager["steward"] == "", f"whose word counts was guessed: {manager['steward']!r}"


# --------------------------------------------------------------------------
# the contract's own kit, over this app's own boot
# --------------------------------------------------------------------------
def _kit():
    """The kit script itself, loaded the way its own command line loads it."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "collab_kit", REPO_ROOT / "conformance" / "experience-collaboration" / "run.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)          # this puts conformance/ on sys.path
    return module


def _snapshot(client, tmp_path: Path):
    """Just the two routes rule 8a reads: `/api/boot` and the manager card."""
    _kit()  # puts conformance/ on sys.path
    import appsnapshot  # the kit's own reader

    bodies = {
        "/api/boot": client.get("/api/boot").text,
        f"/api/managers/{MANAGER}": client.get(f"/api/managers/{MANAGER}").text,
    }
    base = tmp_path / "snapshot"
    base.mkdir(exist_ok=True)
    return appsnapshot.AppSnapshot(str(base), "snapshot", bodies, list(bodies), {"manager": MANAGER})


def test_rule_8a_passes_over_this_apps_own_boot(registered, tmp_path, capsys) -> None:
    """The acceptance's first half, judged by the contract's own kit."""
    kit = _kit()
    row = kit.check_one_steward(_snapshot(registered, tmp_path))
    with capsys.disabled():
        print(f"  8a {row['status']}  {row['detail']}")
    assert row["status"] == "PASS", row
    assert row.get("stewards") == [MANAGER], row


def test_rule_8a_reads_the_key_and_not_its_value(unregistered, tmp_path, capsys) -> None:
    """A residual, asserted rather than left to be discovered again.

    `conformance/experience-collaboration/run.py` finds a steward by looking
    for a KEY matching /steward/i on each manager, never at what that key
    says. So a manager card carrying `steward: ""` -- a registration nobody
    finished -- satisfies rule 8a as written, even though `/api/boot` is
    correctly answering "nobody" (the test above proves that half).

    This is the check's own bar, not this app's behaviour, and the kit is not
    this lane's file to change. It is recorded here so the next reader sees a
    known limit rather than a green light, and filed for the kit's owner as
    `converge-isf` -- which asks for this test to be deleted when it lands.
    """
    kit = _kit()
    row = kit.check_one_steward(_snapshot(unregistered, tmp_path))
    with capsys.disabled():
        print(f"  8a {row['status']}  (nobody named) {row['detail']}")
    assert row["status"] == "PASS", (
        "the kit now reads the value -- good, and this characterisation test "
        "should be deleted along with the work item that asked for it"
    )
    assert json.loads(_snapshot(unregistered, tmp_path).text("/api/boot"))["managers"][0]["steward"] == ""
