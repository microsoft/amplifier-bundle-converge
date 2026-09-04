"""The words and numbers Operation is read in.

`experience-operation.v1` fixes three things this file pins, and all three were
measured wrong on the running app on 2026-09-03 (work item converge-q66):

* **Core 8, the lane words.** A lane is shown in a lane word — *Working ·
  Quiet · Silent — may have died* (`experience.v1` Core 6). The surface was
  showing each lane's raw state instead, so 42 lanes read `done` and 2 read
  `stuck`. Those are WORK words, not lane words. A lane that has already
  reported back is not answering "is this still doing anything?" at all, so it
  is carried in its own list and told in the work words — never squeezed into a
  lane word the vocabulary does not have.
* **Core 5, the flow measures.** Derived · resolved · verified · reopened ·
  **stuck**. The fifth was missing, so the one measure that says work has
  stopped moving was the one a steward could not see.
* **Core 7, the queue numbers.** Work truly ready, shown against work waiting
  on you. Only the second was on the surface, which is how an operation stalls
  politely behind a person nobody counted.

Every test below runs against a real batch directory and a real git repository
made for the occasion. Two seams are stubbed and named where they are:
`tmux_sessions` (a live session is a fact about this machine, not about the
words) and `run` for the one test that parses the work queue's own output.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app import auth, config, data, serve  # noqa: E402

GOOD_USER = "tester"
GOOD_PASSWORD = "let-me-in"

OPERATION_JS = Path(__file__).resolve().parents[1] / "static" / "js" / "render" / "operation.js"

VISION = """# Demo Vision (DRAFT)

## Where this is going

One place for direction and one place for operation.
"""

HIGHWAY = """# Highway — demo

Width 4.
"""

MANIFEST_HEAD = "lane\tworktree\tbranch\tbase\ttmux\tgoal\tlog\tstarted\n"

#: Verbatim capture of `amplifier-work-tracker status --project converge` on
#: 2026-09-04. Kept whole, including the lines that must NOT be mistaken for a
#: count of their own — `READY AGE BUCKETS` is not READY, and `RESOLVED (24h)`
#: is not RESOLVED.
TRACKER_STATUS = """PROJECT:   converge
TOTAL:     76
READY:     8
HELD:      7  (by: agent-spark-1-3014438, agent-spark-1-3014486)
INTAKE:    0
BLOCKED:   3
DEFERRED:  4
RESOLVED:  57
LAST ACTIVITY:            2026-09-04T09:28:04+00:00
OLDEST UNCLAIMED (seconds): 19393.73571
RESOLVED (24h):           8
RESOLVED (7d):            57
READY AGE BUCKETS:        0-1d=8  2-3d=0  4-6d=0  7+d=0  unknownd=0
"""


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "user.name=Test", "-c", "user.email=test@example.invalid", *args],
        cwd=repo,
        check=True,
        capture_output=True,
    )


def _lane(batch: Path, name: str, log: str) -> None:
    (batch / "lanes" / name).mkdir(parents=True)
    (batch / "lanes" / name / "lane.log").write_text(log, encoding="utf-8")
    (batch / "goals" / f"{name}.md").write_text(f"# Lane {name} — do the {name} thing\n", encoding="utf-8")


@pytest.fixture
def project(tmp_path) -> dict:
    """Four lanes, one in each situation the surface must have a word for."""
    repo = tmp_path / "demo-repo"
    (repo / "docs").mkdir(parents=True)
    (repo / "docs" / "VISION.md").write_text(VISION, encoding="utf-8")
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "seed: the vision")

    batch = tmp_path / "hw-demo"
    (batch / "goals").mkdir(parents=True)
    (batch / "HIGHWAY.md").write_text(HIGHWAY, encoding="utf-8")
    (batch / ".width").write_text("4\n", encoding="utf-8")

    for name in ("w1-alpha", "w1-bravo", "w1-charlie", "w1-delta"):
        _lane(batch, name, "working\n")

    # charlie finished; delta stopped and said why.
    (batch / "lanes" / "w1-charlie" / "DONE.json").write_text(
        json.dumps({"status": "success", "summary": "Charlie landed. Nothing residual."}), encoding="utf-8"
    )
    (batch / "lanes" / "w1-delta" / "BLOCKED.md").write_text(
        "# Lane w1-delta — BLOCKED\n\n"
        "**Date:** 2026-09-01\n"
        "**Outcome:** B) BLOCKED. The signing key is not on this host, so the one\n"
        "acceptance item that needs it cannot be proved.\n",
        encoding="utf-8",
    )

    rows = "".join(
        f"{name}\t{batch}/lanes/{name}/demo-repo\tlane/{name}\tdeadbee\thw__hw-demo__{name}\t"
        f"{batch}/goals/{name}.md\t{batch}/lanes/{name}/lane.log\t2026-09-01T10:00:00Z\n"
        for name in ("w1-alpha", "w1-bravo", "w1-charlie", "w1-delta")
    )
    (batch / "manifest.tsv").write_text(MANIFEST_HEAD + rows, encoding="utf-8")

    conf = tmp_path / "converge-app.toml"
    conf.write_text(
        "[[managers]]\n"
        'id = "demo"\n'
        'name = "Demo manager"\n'
        f'batch_dir = "{batch}"\n'
        f'repos = ["{repo}"]\n'
        'tracker_project = ""\n'
        'tmux_socket = "test-socket-that-does-not-exist"\n',
        encoding="utf-8",
    )
    return {"config": conf, "secret": tmp_path / "secret", "state": tmp_path / "state.json", "batch": batch}


class _FakePam:
    def pam(self):
        return self

    def authenticate(self, username: str, password: str, service: str = "login") -> bool:
        return username == GOOD_USER and password == GOOD_PASSWORD


@pytest.fixture
def client(project, monkeypatch) -> TestClient:
    monkeypatch.setattr(auth.pam_module, "pam", _FakePam)
    # A live tmux session is a fact about this machine, not about the words.
    # alpha's session is alive; bravo's is not.
    monkeypatch.setattr(data, "tmux_sessions", lambda socket: {"hw__hw-demo__w1-alpha"})
    made = serve.create_app(
        config_path=project["config"], secret_path=project["secret"], state_path=project["state"]
    )
    made_client = TestClient(made, follow_redirects=False)
    answer = made_client.post("/login", data={"username": GOOD_USER, "password": GOOD_PASSWORD, "next": "/"})
    assert answer.status_code == 302
    return made_client


def operation(client: TestClient) -> dict:
    answer = client.get("/api/managers/demo/operation")
    assert answer.status_code == 200
    return answer.json()


# --------------------------------------------------------------------------
# Core 8 — a lane is read in a lane word, and nothing else
# --------------------------------------------------------------------------


def test_every_lane_at_work_is_read_in_a_lane_word(client: TestClient) -> None:
    payload = operation(client)
    lanes = {lane["id"]: lane for lane in payload["lanes"]}

    assert set(lanes) == {"w1-alpha", "w1-bravo"}
    assert lanes["w1-alpha"]["status"] == "working"
    assert lanes["w1-alpha"]["statusLabel"] == "Working"
    # bravo's session is not on the socket, so nothing may claim it is working.
    assert lanes["w1-bravo"]["status"] == "silent"
    assert lanes["w1-bravo"]["statusLabel"] == "Silent — may have died"

    for lane in payload["lanes"]:
        assert lane["status"] in data.LANE_WORD, f"{lane['id']} reads {lane['status']!r}"
        assert lane["statusLabel"] == data.LANE_WORD[lane["status"]]
        assert lane["statusLabel"] not in data.OUTCOME_WORD.values()


def test_a_lane_that_reported_back_is_carried_apart_in_the_work_words(client: TestClient) -> None:
    payload = operation(client)
    reported = {lane["id"]: lane for lane in payload["reported"]}

    assert set(reported) == {"w1-charlie", "w1-delta"}
    assert reported["w1-charlie"]["outcome"] == "done"
    assert reported["w1-charlie"]["outcomeLabel"] == "Done"
    assert reported["w1-delta"]["outcome"] == "stuck"
    assert reported["w1-delta"]["outcomeLabel"] == "Stuck"
    # A finished lane carries no lane word at all — that is the whole point.
    for lane in payload["reported"]:
        assert "status" not in lane and "statusLabel" not in lane


def test_every_lane_appears_exactly_once_across_the_two_lists(client: TestClient) -> None:
    """Splitting the list must not lose a lane — that would be hiding, not sorting."""
    payload = operation(client)
    seen = [lane["id"] for lane in payload["lanes"]] + [lane["id"] for lane in payload["reported"]]
    assert sorted(seen) == ["w1-alpha", "w1-bravo", "w1-charlie", "w1-delta"]
    assert len(seen) == len(set(seen))


def test_every_lane_carries_evidence_that_can_be_opened(client: TestClient) -> None:
    payload = operation(client)
    for lane in payload["lanes"] + payload["reported"]:
        assert str(lane["evidence"]).strip(), f"{lane['id']} carries nothing to open"
    reported = {lane["id"]: lane for lane in payload["reported"]}
    assert reported["w1-charlie"]["evidence"] == "Charlie landed."
    assert reported["w1-delta"]["evidence"].startswith("The signing key is not on this host")


# --------------------------------------------------------------------------
# Core 5 — the five flow measures; Core 7 — the two queue numbers
# --------------------------------------------------------------------------


def test_the_work_queue_counts_are_read_from_its_own_output(monkeypatch) -> None:
    """The parse, against the queue's real printed output — including its traps."""
    monkeypatch.setattr(data, "run", lambda *a, **k: TRACKER_STATUS)
    counts = data.tracker_counts(config.ManagerConfig(id="demo", name="Demo", tracker_project="converge"))
    assert counts["TOTAL"] == 76
    assert counts["READY"] == 8
    assert counts["BLOCKED"] == 3
    assert counts["RESOLVED"] == 57
    # The two lines that must not be mistaken for the counts above.
    assert counts["READY AGE BUCKETS"] == 0
    assert counts["RESOLVED (24H)"] == 8


def test_the_flow_reading_shows_all_five_measures(monkeypatch) -> None:
    monkeypatch.setattr(data, "run", lambda *a, **k: TRACKER_STATUS)
    counts = data.tracker_counts(config.ManagerConfig(id="demo", name="Demo", tracker_project="converge"))
    flow = data.throughput(counts, merged=5, reopened=2)
    assert flow["derived"] == 76
    assert flow["resolved"] == 57
    assert flow["verified"] == 5
    assert flow["reopened"] == 2
    assert flow["stuck"] == 3
    assert flow["available"] is True
    # Flow and the outcome reading are never summed into one number.
    assert "confidence" not in flow and "kept" not in flow


def test_the_flow_reading_still_names_stuck_when_there_is_no_queue_to_read() -> None:
    """A measure that cannot be read says nothing — it never silently vanishes."""
    flow = data.throughput({}, merged=0, reopened=0)
    assert set(flow) == {"derived", "resolved", "verified", "reopened", "stuck", "spark", "available"}
    assert flow["available"] is False


def test_work_truly_ready_is_a_number_of_its_own(monkeypatch) -> None:
    monkeypatch.setattr(data, "run", lambda *a, **k: TRACKER_STATUS)
    counts = data.tracker_counts(config.ManagerConfig(id="demo", name="Demo", tracker_project="converge"))
    assert data.queue_reading(counts) == {"trulyReady": 8, "available": True}
    assert data.queue_reading({}) == {"trulyReady": 0, "available": False}


def test_the_operation_payload_carries_the_queue_reading(client: TestClient) -> None:
    payload = operation(client)
    assert "queue" in payload and "trulyReady" in payload["queue"]
    assert "stuck" in payload["throughput"]
    # The second number is the manager card's own count, not a second copy here.
    manager = client.get("/api/managers/demo").json()
    assert "needs" in manager


# --------------------------------------------------------------------------
# what the surface does with them — read from the client the app ships
# --------------------------------------------------------------------------


def test_the_surface_shows_the_lane_word_and_not_the_raw_state() -> None:
    source = OPERATION_JS.read_text(encoding="utf-8")
    assert re.search(r"lane-status[^`]{0,80}statusLabel", source), (
        "the lane's state pill must render the lane word (statusLabel); rendering the "
        "raw `status` field is the defect this file exists to pin"
    )
    assert "l.statusLabel" in source and "l.outcomeLabel" in source


def test_the_surface_shows_both_queue_numbers_and_the_fifth_flow_measure() -> None:
    source = OPERATION_JS.read_text(encoding="utf-8")
    assert re.search(r"truly[\s-]?ready|trulyReady", source, re.I)
    assert re.search(r"waiting on you|needsYouCount", source, re.I)
    assert "throughputStuck" in source and "flow.stuck" in source


def test_the_surface_offers_the_fifth_limit_and_one_message_to_all() -> None:
    source = OPERATION_JS.read_text(encoding="utf-8")
    assert re.search(r"review this", source, re.I), "Core 11's fifth limit"
    assert re.search(r"tell all", source, re.I), "Core 13 — one message reaches every session"
    # Core 11 again: steering sets limits and hands out no work.
    assert not re.search(r"assign(ed|ment)?\s*(to)?\s*(lane|worker|session)|data-assign", source, re.I)
    # Core 12: nothing here stops work by moving it.
    assert not re.search(r">\s*(Stop|Kill|Abort|Terminate|Halt)\b", source)
