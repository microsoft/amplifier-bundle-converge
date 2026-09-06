"""Manager sessions register themselves, and this app finds them (`converge-eife`).

`experience.v1` Core 2 says Home is the list of manager sessions you run.
`experience-operation.v1` Core 1 says there is one manager session per operation,
found without configuration. Until this change neither was true: the app read
manager sessions from a hand-written `~/.amplifier/converge-app.toml`, so a new
session - or an existing one on another project - never appeared until a person
edited a file.

The mechanism is one file. On every wake a manager session writes
`<workspace>/.converge/<manager-id>/registration.toml`
(`scripts/register-manager.py`); the app scans every workspace root it is told
about and reads what it finds.

What is real here
-----------------
Everything except PAM. Real workspace directories on disk, the real
`scripts/register-manager.py` run as a subprocess against them, the real
`config.load`, the real FastAPI app from `app/serve.py`, and the real cookie
gate. Nothing feeds the readers a canned payload, because the thing worth
proving is that the readers read.

The acceptance, clause by clause, and what would falsify each
-------------------------------------------------------------
1. *A manager session waking in the mode leaves a registration with the named
   fields and a fresh last-seen.* Falsified if the script writes no file, omits
   a field, or stamps a time this run cannot have produced.
2. *No hand-written managers plus one registration under the default workspace
   root: Home lists it with steward, repos and lane count, and `/api/boot`
   carries it.* Falsified if `/api/boot` answers an empty `managers` list, or a
   card with no steward, no repo count, or no lane count.
3. *A heartbeat 16 minutes old reads "Silent - may have died".* Falsified if the
   card claims the session is there, or says nothing at all.
4. *A hand-written manager and a registration of the same id: the hand-written
   one is shown ONCE, with the registration's last-seen.* Falsified by two
   cards with one id, by the registration's name winning, or by a card with no
   last-seen.
5. *The app tests are green.* This file is part of that, and it is run with the
   rest of `app/tests`.

One deliberate wording note
---------------------------
The acceptance this file was written against punctuated the silent word with a
comma where the contract uses a dash. This repository spells that word once, in
`app/data.py`'s `LANE_WORD`, as **Silent - may have died** (em dash; this module
is ASCII, so the dash is transliterated here exactly as the middots in the
contract's list are), which is the spelling `experience.v1` Core 6 fixes and
which four existing test modules and the `experience-operation` kit already
assert. Introducing a second spelling of one state word would be the exact drift
Core 6 exists to prevent, so the served label reuses `LANE_WORD["silent"]` and
the assertion below is written against that constant - plus, separately, against
the two halves of the phrase, so this test still fails if the word stops saying
that a session may have died.

Settled on 2026-09-06 (`converge-lsa0`): the comma spelling is gone from this
module and from `context/manager/return-brief.md`, and
`conformance/experience/run.py` now transcribes the clause's whole phrase rather
than a short "Silent", which is what made its rule 6a read FAIL against an app
that was already right.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tomllib
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from app import auth, config, data, serve  # noqa: E402

GOOD_USER = "tester"
GOOD_PASSWORD = "hunter2"

#: Per-run socket name - see `app/tests/conftest.py`. Nothing is ever started on
#: it; the point is that no OTHER run's tmux server can answer for it either.
SOCKET = f"cvregister-{os.getpid()}-{uuid.uuid4().hex[:8]}"

REGISTER = REPO_ROOT / "scripts" / "register-manager.py"


# --------------------------------------------------------------------------
# a workspace to register in
# --------------------------------------------------------------------------


def _git(repo: Path, *args: str) -> str:
    done = subprocess.run(
        ["git", "-c", "user.name=Test", "-c", "user.email=test@example.invalid", *args],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )
    return done.stdout.strip()


def _workspace(tmp_path: Path, manager_id: str = "demo") -> dict:
    """A workspace root, one repository in it, and a batch directory.

    Shaped exactly as `modes/converge-manager.md` clause 5 describes, because
    that shape is what the script resolves and what the app scans for.
    """
    root = tmp_path / "workspace"
    root.mkdir(parents=True, exist_ok=True)
    (root / "WORKSPACE-MANIFEST.json").write_text('{"name": "demo-workspace"}\n', encoding="utf-8")

    repo = root / "demo-repo"
    repo.mkdir(exist_ok=True)
    _git(repo, "init", "-q", "-b", "main")
    (repo / "README.md").write_text("# demo\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "first")

    batch = root / config.CONVERGE_DIR / manager_id
    batch.mkdir(parents=True, exist_ok=True)
    (batch / "HIGHWAY.md").write_text(
        "# HIGHWAY\n\n## Outcome\nProve a manager registers itself.\n", encoding="utf-8"
    )
    (batch / "manifest.tsv").write_text(
        "lane\tworktree\tbranch\tbase\ttmux\tgoal\tlog\tlaunched_at\n"
        f"w1-alpha\t{batch / 'lanes' / 'w1-alpha'}\tlane/w1-alpha\tmain\t"
        f"hw__{manager_id}__w1-alpha\t\t\t\n",
        encoding="utf-8",
    )
    (batch / ".width").write_text("4\n", encoding="utf-8")
    lane = batch / "lanes" / "w1-alpha"
    lane.mkdir(parents=True, exist_ok=True)
    (lane / "lane.log").write_text("working\n", encoding="utf-8")

    return {"root": root, "repo": repo, "batch": batch, "id": manager_id}


def _register(place: dict, *extra: str) -> subprocess.CompletedProcess:
    """Run the real script, from the workspace root, as a manager session does."""
    done = subprocess.run(
        [
            sys.executable,
            str(REGISTER),
            "--id", place["id"],
            "--steward", "wren",
            "--tmux-socket", SOCKET,
            "--manager-tmux", f"hw__{place['id']}__manager",
            "--print",
            *extra,
        ],
        cwd=place["root"],
        capture_output=True,
        text=True,
        check=False,
    )
    print(done.stdout)
    if done.returncode != 0:
        print(done.stderr)
    assert done.returncode == 0, f"register-manager.py failed: {done.stderr}"
    return done


def _age_the_heartbeat(place: dict, minutes: int) -> str:
    """Rewrite last_seen to a stamp `minutes` old, leaving everything else.

    The clock is not mocked: an old stamp is what an old stamp looks like, and
    the reader is asked to read it exactly as it would read a real one.
    """
    path = place["batch"] / config.REGISTRATION_NAME
    when = datetime.now(timezone.utc) - timedelta(minutes=minutes)
    stamp = when.isoformat(timespec="seconds")
    text = path.read_text(encoding="utf-8")
    lines = [
        f'last_seen = "{stamp}"' if line.startswith("last_seen =") else line
        for line in text.splitlines()
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return stamp


def _app_config(tmp_path: Path, place: dict, *, managers: str = "") -> Path:
    """The app's own config: workspace roots to scan, and any hand-written blocks."""
    path = tmp_path / f"converge-app-{uuid.uuid4().hex[:6]}.toml"
    path.write_text(f'workspaces = ["{place["root"]}"]\n\n{managers}', encoding="utf-8")
    return path


def _client(config_path: Path, tmp_path: Path, monkeypatch) -> TestClient:
    monkeypatch.setattr(auth, "authenticate", lambda user, password: user == GOOD_USER)
    made = serve.create_app(
        config_path=config_path,
        secret_path=tmp_path / f"secret-{uuid.uuid4().hex[:6]}",
        state_path=tmp_path / f"state-{uuid.uuid4().hex[:6]}.json",
    )
    client = TestClient(made)
    answer = client.post(
        "/login",
        data={"username": GOOD_USER, "password": GOOD_PASSWORD, "next": "/"},
        follow_redirects=False,
    )
    assert answer.status_code == 302, answer.text
    return client


@pytest.fixture(autouse=True)
def _no_ambient_workspaces(monkeypatch):
    """`CONVERGE_WORKSPACES` from the surrounding shell is not this test's input."""
    monkeypatch.delenv(config.WORKSPACES_ENV, raising=False)


# --------------------------------------------------------------------------
# 1. a wake leaves a registration with the named fields and a fresh last-seen
# --------------------------------------------------------------------------


def test_a_wake_writes_a_registration_with_every_named_field(tmp_path: Path) -> None:
    """WHAT WOULD FALSIFY THIS: a missing file, a missing field, or a stale stamp."""
    place = _workspace(tmp_path)
    before = datetime.now(timezone.utc)
    _register(place)
    after = datetime.now(timezone.utc)

    path = place["batch"] / config.REGISTRATION_NAME
    assert path.is_file(), f"no registration at {path}"
    print(f"\nwrote {path}")
    print(path.read_text(encoding="utf-8"))

    with path.open("rb") as handle:
        table = tomllib.load(handle)

    assert table["id"] == "demo"
    assert table["name"]
    assert table["steward"] == "wren"
    assert table["workspace"] == str(place["root"])
    assert table["batch_dir"] == str(place["batch"])
    assert table["plan_record"] == str(place["batch"] / "HIGHWAY.md")
    assert table["tracker_project"] == "demo"
    assert table["tmux_socket"] == SOCKET
    assert table["manager_tmux"] == "hw__demo__manager"

    repos = table["repos"]
    assert [one["path"] for one in repos] == [str(place["repo"])], repos
    assert repos[0]["default_branch"] == "main", repos

    stamp = datetime.fromisoformat(table["last_seen"])
    assert before.replace(microsecond=0) <= stamp <= after, (
        f"last_seen {table['last_seen']} is not from this run "
        f"({before.isoformat()} .. {after.isoformat()})"
    )


def test_a_second_wake_rewrites_the_stamp_rather_than_leaving_it(tmp_path: Path) -> None:
    """The stamp IS the heartbeat, so a wake that finds a file still writes one.

    WHAT WOULD FALSIFY THIS: a `last_seen` unchanged after a second run - which
    is what a "write it only if missing" implementation would leave, and which
    would report a dead session as alive forever.
    """
    place = _workspace(tmp_path)
    _register(place)
    old = _age_the_heartbeat(place, 40)
    _register(place)

    path = place["batch"] / config.REGISTRATION_NAME
    with path.open("rb") as handle:
        table = tomllib.load(handle)
    print(f"\nbefore the second wake: {old}\nafter:  {table['last_seen']}")
    assert table["last_seen"] != old, "the second wake left the old stamp in place"
    assert data.stamp_age(table["last_seen"]) < 60


# --------------------------------------------------------------------------
# 2. one registration, no hand-written managers: Home lists it, boot carries it
# --------------------------------------------------------------------------


def test_home_lists_a_registered_manager_nobody_named_by_hand(tmp_path: Path, monkeypatch) -> None:
    """WHAT WOULD FALSIFY THIS: an empty `managers` list, or a card missing the
    steward, the repo count, or the lane count."""
    place = _workspace(tmp_path)
    _register(place)
    client = _client(_app_config(tmp_path, place), tmp_path, monkeypatch)

    payload = client.get("/api/boot").json()
    print(f"\n/api/boot config: {payload['config']}")
    print(f"managers: {[one['id'] for one in payload['managers']]}")

    assert [one["id"] for one in payload["managers"]] == ["demo"], (
        "a registered manager session did not reach Home"
    )
    card = payload["managers"][0]
    print(f"card: steward={card['steward']!r} repos={card['repos']} "
          f"lanes={card['lanesActive']}/{card['lanesMax']} presence={card['presenceLabel']!r}")
    assert card["steward"] == "wren", "the card does not carry the registered steward"
    assert card["repos"] == 1, f"the card counts {card['repos']} repositories, expected 1"
    assert card["lanesMax"] == 4, f"the card reads {card['lanesMax']} lanes intended, expected 4"
    assert card["presence"] == "here", f"a fresh registration reads {card['presence']!r}"
    assert str(place["root"]) in payload["config"]["workspaces"], payload["config"]

    # Core 8's own reading: where this manager came from, for the Details fold.
    assert str(place["batch"] / config.REGISTRATION_NAME) in card["origin"], card["origin"]
    assert card["registration"] == str(place["batch"] / config.REGISTRATION_NAME)
    assert card["workspace"] == str(place["root"])
    assert card["repoBranches"] == [{"path": str(place["repo"]), "branch": "main"}]


@pytest.mark.real_default_roots
def test_the_default_workspace_root_is_the_parent_of_the_apps_own_repo(tmp_path: Path) -> None:
    """With no `workspaces` key, the app looks beside its own checkout.

    WHAT WOULD FALSIFY THIS: a default root pointing anywhere else - which is
    how "found without configuration" (`experience-operation.v1` Core 1) stops
    being true for the ordinary layout, where the app is one repository in the
    workspace it watches.
    """
    roots = config.default_workspace_roots()
    print(f"\ndefault workspace roots: {[str(one) for one in roots]}")
    assert roots == (config.app_repo_root().parent,)

    place = _workspace(tmp_path)
    _register(place)
    # And the env variable adds to them rather than replacing them.
    found = config.discover_registrations(config.env_workspace_roots(str(place["root"])))
    assert [one.id for one in found] == ["demo"], found


# --------------------------------------------------------------------------
# 3. sixteen minutes: Silent - may have died
# --------------------------------------------------------------------------


def test_a_sixteen_minute_old_heartbeat_reads_silent(tmp_path: Path, monkeypatch) -> None:
    """WHAT WOULD FALSIFY THIS: a card that still claims the session is there,
    or one that says nothing at all about it."""
    place = _workspace(tmp_path)
    _register(place)
    stamp = _age_the_heartbeat(place, 16)
    client = _client(_app_config(tmp_path, place), tmp_path, monkeypatch)

    card = client.get("/api/boot").json()["managers"][0]
    print(f"\nlast_seen {stamp} -> presence={card['presence']!r} "
          f"label={card['presenceLabel']!r} heard={card['heard']!r}")

    assert card["presence"] == "silent"
    assert card["presenceLabel"] == data.LANE_WORD["silent"], (
        "the silent word must be the repository's one spelling of it "
        "(`experience.v1` Core 6), not a second one"
    )
    assert card["presenceLabel"].startswith("Silent") and "may have died" in card["presenceLabel"]
    assert card["lastSeen"] == stamp


def test_fourteen_minutes_is_not_yet_silent(tmp_path: Path, monkeypatch) -> None:
    """The threshold is a threshold, not a rounding.

    WHAT WOULD FALSIFY THIS: a card inside the window reading silent, which
    would make the word meaningless for every healthy session.
    """
    place = _workspace(tmp_path)
    _register(place)
    _age_the_heartbeat(place, 14)
    client = _client(_app_config(tmp_path, place), tmp_path, monkeypatch)

    card = client.get("/api/boot").json()["managers"][0]
    print(f"\n14 minutes -> presence={card['presence']!r} label={card['presenceLabel']!r}")
    assert card["presence"] == "here"
    assert "may have died" not in card["presenceLabel"]
    assert card["heard"] == "14m"


def test_a_manager_that_never_registered_reads_neither_word(tmp_path: Path, monkeypatch) -> None:
    """Never having registered is a different silence from having gone quiet.

    WHAT WOULD FALSIFY THIS: a hand-written manager with no registration
    reading "Silent - may have died" - a claim about a heartbeat that has never
    existed - or reading as freshly heard from, which is the same fabrication
    the other way.
    """
    place = _workspace(tmp_path, manager_id="unregistered")
    conf = _app_config(
        tmp_path,
        place,
        managers=(
            "[[managers]]\n"
            'id = "unregistered"\n'
            'name = "Named by hand"\n'
            f'batch_dir = "{place["batch"]}"\n'
            f'tmux_socket = "{SOCKET}"\n'
        ),
    )
    client = _client(conf, tmp_path, monkeypatch)

    card = client.get("/api/boot").json()["managers"][0]
    print(f"\nnever registered -> presence={card['presence']!r} "
          f"label={card['presenceLabel']!r} lastSeen={card['lastSeen']!r}")
    assert card["presence"] == ""
    assert card["presenceLabel"] == ""
    assert card["lastSeen"] == ""
    assert "config file" in card["origin"], card["origin"]


# --------------------------------------------------------------------------
# 4. both: the hand-written one, once, with the registration's last-seen
# --------------------------------------------------------------------------


def test_a_hand_written_block_wins_once_and_takes_the_registrations_last_seen(
    tmp_path: Path, monkeypatch
) -> None:
    """WHAT WOULD FALSIFY THIS: two cards carrying one id; the registration's
    name winning over the block's; or a card with no last-seen, which would
    throw away the only fact the session itself supplied."""
    place = _workspace(tmp_path)
    _register(place)
    stamp = _age_the_heartbeat(place, 3)

    conf = _app_config(
        tmp_path,
        place,
        managers=(
            "[[managers]]\n"
            'id = "demo"\n'
            'name = "Named by hand"\n'
            f'batch_dir = "{place["batch"]}"\n'
            f'repos = ["{place["repo"]}"]\n'
            'steward = "a-person"\n'
            f'tmux_socket = "{SOCKET}"\n'
        ),
    )
    client = _client(conf, tmp_path, monkeypatch)

    payload = client.get("/api/boot").json()
    ids = [one["id"] for one in payload["managers"]]
    print(f"\nlisted: {ids}")
    assert ids == ["demo"], f"the same manager session is listed {len(ids)} times: {ids}"

    card = payload["managers"][0]
    print(f"name={card['name']!r} steward={card['steward']!r} "
          f"lastSeen={card['lastSeen']!r} origin={card['origin']!r}")
    assert card["name"] == "Named by hand", "the registration overruled the hand-written block"
    assert card["steward"] == "a-person", "the registration overruled the hand-written steward"
    assert card["lastSeen"] == stamp, "the hand-written block did not take the registration's last-seen"
    assert card["presence"] == "here"
    assert card["registration"] == str(place["batch"] / config.REGISTRATION_NAME)
    assert "config file" in card["origin"] and "registering itself" in card["origin"], card["origin"]


# --------------------------------------------------------------------------
# 5. the surface actually draws it
# --------------------------------------------------------------------------


def test_home_draws_the_steward_the_presence_and_the_origin_fold() -> None:
    """The payload carrying a field proves nothing about the screen showing it.

    This is the same defect `test_words_readme.py` was written for: a payload
    that has been right all along, and a surface that never drew it. Read here
    from the served sources rather than a browser, because these three are
    string-for-string questions and a browser adds nothing to them.

    WHAT WOULD FALSIFY THIS: `render/home.js` dropping any of the three, or
    `home.html` losing the fold they are written into.
    """
    js = (REPO_ROOT / "app" / "static" / "js" / "render" / "home.js").read_text(encoding="utf-8")
    html = (REPO_ROOT / "app" / "templates" / "home.html").read_text(encoding="utf-8")

    assert "m.steward" in js, "Home never draws the steward"
    assert "m.presenceLabel" in js, "Home never draws whether the session is still there"
    assert "m.origin" in js, "Home never says where a manager session came from"
    assert "homeOriginBody" in js and 'id="homeOriginBody"' in html, (
        "the Details fold that says where managers came from is not wired"
    )
    assert 'id="homeOriginFold"' in html and "op-parity" in html
    print("\nhome.js draws steward, presence and origin; home.html carries the fold")


def test_the_mode_and_the_convention_say_to_register_on_every_wake() -> None:
    """The app can only find what the mode actually writes.

    WHAT WOULD FALSIFY THIS: an operating loop with no registration step, or one
    that reads as conditional - "if it does not exist" - which is exactly the
    version that leaves every already-running session invisible.
    """
    mode = (REPO_ROOT / "modes" / "converge-manager.md").read_text(encoding="utf-8")
    convention = (REPO_ROOT / "context" / "manager" / "registration.md").read_text(encoding="utf-8")

    assert "scripts/register-manager.py" in mode, "the operating loop never registers"
    assert "@converge:context/manager/registration.md" in mode, "the convention is never loaded"
    assert "every wake" in mode.lower()
    assert "unconditionally" in mode.lower()
    assert "registration.toml" in convention
    print("\nthe mode registers on every wake, unconditionally, and loads the convention")
