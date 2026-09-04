"""The reasons Operation shows, and the parts it is made of.

`experience-operation.v1` fixes three things this file pins, and all three were
measured wrong on the running app on 2026-09-03/04 (work item converge-lwa,
ledger rows CVG-141, CVG-142, CVG-143):

* **Core 2 — every grouping carries its reason.** All eleven waves carried
  none: each wave's heading was its own lane names joined by commas, which is a
  list of members and not a statement of what the batch is for. Nothing showed
  why the plan had been redrawn either, though the run had been reopened twice.
* **Core 3 — the return brief carries all five parts.** The brief was the
  newest log entry's *first six sentences*. Six is not five, and the truncation
  is what cut the part a steward most needs — what needs their word — off the
  end of a fifteen-sentence entry.
* **Core 4 — each turn opens onto its evidence.** Every timeline entry was
  `[date, title, one sentence]` with nothing to open: it said that confidence
  moved and gave the reader no way to inspect why.

Two rules run through every test below, and each has its own falsity condition.

**A reason is quoted, never composed.** Every reason on the page is a sentence
some record already contains — HIGHWAY.md's weave-in log first, then the owner
return log — and the payload names which record it came from. A wave no record
names says so plainly and is marked `reasonRecorded: false`; it is never given
a sentence the manager session did not write.

**A part is labelled only where the brief labelled it.** An entry written to
the return-brief convention is read as its five labelled parts. An entry that
labels nothing is shown whole, unlabelled — this module never decides which
unlabelled sentence "is really" the stuck one.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app import auth, data, serve  # noqa: E402

GOOD_USER = "tester"
GOOD_PASSWORD = "correct horse"

OPERATION_JS = Path(__file__).resolve().parents[1] / "static" / "js" / "render" / "operation.js"
OPERATION_HTML = Path(__file__).resolve().parents[1] / "templates" / "operation.html"

VISION = "# Demo Vision (DRAFT)\n\n## Where this is going\n\nOne place for direction, one for operation.\n"

#: The batch record, in the shape a manager session actually writes it: an
#: outcome, then one weave-in line per launch, cycle, incident and reopen.
HIGHWAY = """# Highway — demo

## Outcome: RUNNING
Make the demo path real end to end.

## Weave-in log

- 2026-09-01T10:00:00Z W1 launched on owner word "go": prove the sign-in path before anything is built on top of it.
- 2026-09-01T14:00:00Z W1 cycle 1: merged w1-alpha. Live: w1-bravo.
- 2026-09-02T09:00:00Z REOPENED on owner word: the contract changed under us, so the plan is redrawn around the new clause.
"""

#: The steward-facing record. The last entry is deliberately unlabelled and
#: eight sentences long: it is the shape every entry written before the
#: five-part convention has, and eight is more than the six the old reading
#: kept. The word `app` appears in it in a sentence that is NOT about the app
#: wave — that is the measured trap a bare-key search falls into.
OWNER_LOG = """# Owner return log

Plain-sentence briefs for the intent steward. Newest last.

## 2026-09-01 — the run begins
You ratified the vision with the word "lgtm." I derived four items from the gap and started wave 1 as two real lanes.

## 2026-09-02 — wave 2 is about the guard
Wave 2 exists to close the guard gap the documents kit found, and nothing else.
The companion app's first pass landed alongside it.

## 2026-09-03 — where things stand
The sign-in path is real and was re-checked on the merged result.
Two lanes merged and one is still running.
The ledger was re-derived and its self-checks pass.
The guard follow-up is stuck: the signing key is not on this host.
Nothing else stopped.
One thing waits on your word: whether the kit ids anchor to clause numbers.
I broke the export script and fixed it in the same cycle, which cost an hour.
Everything else is on main.
"""

#: The same brief, written to the convention: five parts, each opening with its
#: own bold label (`context/manager/return-brief.md`).
LABELLED_ENTRY = """**Time away.** You were gone 5h and two waves ran in it.
**Finished.** The sign-in path landed and the kit was re-run on the merged result.
**Stuck.** The guard follow-up stopped because the signing key is not on this host.
**Needs you.** Whether the kit ids anchor to clause numbers.
**Anything quietly broken.** I broke the export script and fixed it in the same cycle, which cost an hour.
"""

MANIFEST_HEAD = "lane\tworktree\tbranch\tbase\ttmux\tgoal\tlog\tstarted\n"

LANES = ("w1-alpha", "w1-bravo", "w2-charlie", "app-delta")


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "user.name=Test", "-c", "user.email=test@example.invalid", *args],
        cwd=repo,
        check=True,
        capture_output=True,
    )


@pytest.fixture
def project(tmp_path) -> dict:
    """Four lanes in three waves, and the two records a reason is read from."""
    repo = tmp_path / "demo-repo"
    (repo / "docs" / "workflow").mkdir(parents=True)
    (repo / "docs" / "VISION.md").write_text(VISION, encoding="utf-8")
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "seed: the vision")

    # Two commits, so the timeline's evidence can name which one recorded a
    # turn — and so the commit date is visibly a different fact from the date
    # in the entry's own heading.
    head, _split, tail = OWNER_LOG.partition("## 2026-09-03")
    log_path = repo / "docs" / "workflow" / "OWNER-RETURN-LOG.md"
    log_path.write_text(head, encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "brief: the run begins, and wave 2")
    log_path.write_text(OWNER_LOG, encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "brief: where things stand")

    batch = tmp_path / "hw-demo"
    (batch / "goals").mkdir(parents=True)
    (batch / "HIGHWAY.md").write_text(HIGHWAY, encoding="utf-8")
    (batch / ".width").write_text("4\n", encoding="utf-8")
    for name in LANES:
        (batch / "lanes" / name).mkdir(parents=True)
        (batch / "lanes" / name / "lane.log").write_text("working\n", encoding="utf-8")
        (batch / "goals" / f"{name}.md").write_text(f"# Lane {name}\n", encoding="utf-8")
    (batch / "manifest.tsv").write_text(
        MANIFEST_HEAD
        + "".join(
            f"{name}\t{batch}/lanes/{name}\tlane/{name}\tdeadbee\thw__hw-demo__{name}\t"
            f"{batch}/goals/{name}.md\t{batch}/lanes/{name}/lane.log\t2026-09-01T10:00:00Z\n"
            for name in LANES
        ),
        encoding="utf-8",
    )

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
    return {"config": conf, "secret": tmp_path / "secret", "state": tmp_path / "state.json",
            "repo": repo, "batch": batch}


class _FakePam:
    def pam(self):
        return self

    def authenticate(self, username: str, password: str, service: str = "login") -> bool:
        return username == GOOD_USER and password == GOOD_PASSWORD


@pytest.fixture
def client(project, monkeypatch) -> TestClient:
    monkeypatch.setattr(auth.pam_module, "pam", _FakePam)
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


def waves_by_id(payload: dict) -> dict:
    return {wave["id"]: wave for wave in payload["waves"]}


def entries(project) -> list:
    return data._owner_log_entries(project["repo"])


# --------------------------------------------------------------------------
# Core 2 — every grouping carries its reason, quoted from the record
# --------------------------------------------------------------------------


def test_a_wave_carries_the_launch_line_that_says_what_it_is_for(client: TestClient) -> None:
    wave = waves_by_id(operation(client))["w1"]
    assert wave["reasonRecorded"] is True
    assert wave["reason"] == (
        'W1 launched on owner word "go": prove the sign-in path before anything is '
        "built on top of it."
    )
    # Which record, and which line of it — a reason with no source is a claim.
    assert wave["reasonSource"] == "HIGHWAY.md · weave-in log · 2026-09-01T10:00:00Z"


def test_a_wave_the_weave_log_never_names_falls_back_to_the_owner_log(client: TestClient) -> None:
    wave = waves_by_id(operation(client))["w2"]
    assert wave["reasonRecorded"] is True
    assert wave["reason"] == "Wave 2 exists to close the guard gap the documents kit found, and nothing else."
    assert wave["reasonSource"] == "docs/workflow/OWNER-RETURN-LOG.md · wave 2 is about the guard"


def test_a_wave_no_record_names_says_so_and_is_never_given_a_sentence(client: TestClient) -> None:
    """The measured trap: `app` is an ordinary word as well as a wave's key.

    Searching the owner log for the key `app` — or for its label `App`, which
    is the same word Title-cased — picks up "The companion app's first pass
    landed alongside it.", a sentence about something else entirely. A wave
    with nothing on record says nothing, and is marked so.
    """
    wave = waves_by_id(operation(client))["app"]
    assert wave["reasonRecorded"] is False
    assert wave["reason"] == data.NO_REASON_ON_RECORD
    assert wave["reasonSource"] == ""
    assert "companion app" not in wave["reason"]


def test_a_sentence_that_names_two_waves_is_no_wave_s_reason() -> None:
    """It names two batches and says what neither is for, so it is neither's.

    Measured on the real log: "…verified all four wave-1 lanes by git facts,
    merged them, and refilled with wave 2" is about wave 1 and mentions wave 2
    in passing. Read as wave 2's reason it is simply wrong.
    """
    both = "While we talked the watchdog verified all four wave-1 lanes and refilled with wave 2."
    assert data.waves_named_in(both) == {"w1", "w2"}
    said = [("2026-09-02", "wave 1 landed", both)]
    for key, label in (("w1", "Wave 1"), ("w2", "Wave 2")):
        assert data.wave_reason(key, label, [], [], said)["recorded"] is False
    # One wave named, and it is this one: that sentence is a reason.
    alone = [("2026-09-02", "the guard", "Wave 2 exists to close the guard gap.")]
    assert data.wave_reason("w2", "Wave 2", [], [], alone)["reason"] == "Wave 2 exists to close the guard gap."


def test_a_wave_named_in_either_style_is_the_same_wave() -> None:
    assert data.waves_named_in("W8 launched; the wave-8 lanes are live") == {"w8"}
    assert data.waves_named_in("the experience wave e1 reopened") == {"e1"}
    assert data.waves_named_in("nothing here names a wave at all") == set()


def test_no_wave_is_headed_by_its_own_lane_names(client: TestClient) -> None:
    """The defect this closes: a heading that lists the members it contains.

    Falsity condition — if a wave's heading is again its lane names joined by
    commas, `title` equals the members and this fails.
    """
    for wave in operation(client)["waves"]:
        members = {name for name, _flag in wave["items"]}
        parts = {part.strip() for part in str(wave["title"]).split(",") if part.strip()}
        assert not (parts & members), f"{wave['id']} is headed by its own lane names"
        assert wave["title"] == wave["reason"]


def test_every_wave_carries_a_reason_field_at_all(client: TestClient) -> None:
    waves = operation(client)["waves"]
    assert len(waves) == 3
    for wave in waves:
        assert str(wave["reason"]).strip(), f"{wave['id']} carries no reason at all"
        assert isinstance(wave["reasonRecorded"], bool)


def test_a_redraw_is_shown_with_the_reason_the_record_gives(client: TestClient) -> None:
    redraws = operation(client)["redraws"]
    assert len(redraws) == 1
    assert redraws[0]["when"] == "2026-09-02T09:00:00Z"
    assert redraws[0]["why"].startswith("REOPENED on owner word: the contract changed under us")


def test_a_run_that_was_never_redrawn_claims_no_redraw() -> None:
    assert data.plan_redraws("# Highway\n\n## Weave-in log\n\n- 2026-09-01T10:00:00Z W1 launched.\n") == []


def test_the_weave_log_is_read_as_stamp_and_sentence() -> None:
    read = data.weave_log(HIGHWAY)
    assert len(read) == 3
    assert read[0][0] == "2026-09-01T10:00:00Z"
    assert read[0][1].startswith('W1 launched on owner word "go"')
    # A batch that keeps no weave-in log yields nothing, never a guess.
    assert data.weave_log("# Highway — demo\n\nWidth 4.\n") == []


# --------------------------------------------------------------------------
# Core 3 — the return brief carries all five parts
# --------------------------------------------------------------------------


def test_the_brief_is_the_whole_entry_and_is_never_cut_to_six_sentences(project) -> None:
    """Falsity condition — the old reading kept `sentences(body)[:6]`.

    This entry is eight sentences and the part a steward most needs is the
    seventh. A brief that stops at six drops it, which is the measured defect.
    """
    brief = data.return_brief(entries(project))
    assert len(brief) == 8
    assert any("waits on your word" in one for one in brief), "the seventh sentence must survive"
    assert brief[-1] == "Everything else is on main."


def test_an_entry_written_to_the_convention_is_read_as_its_five_labelled_parts() -> None:
    brief = data.return_brief([("2026-09-03", "a stamped return", LABELLED_ENTRY)])
    assert brief == [
        "Time away: You were gone 5h and two waves ran in it.",
        "What finished: The sign-in path landed and the kit was re-run on the merged result.",
        "What is stuck: The guard follow-up stopped because the signing key is not on this host.",
        "What needs your word: Whether the kit ids anchor to clause numbers.",
        "What quietly changed: I broke the export script and fixed it in the same cycle, which cost an hour.",
    ]


def test_a_part_written_as_two_sentences_is_not_cut_in_half() -> None:
    said = (
        "**Time away.** You were gone 5h.\n"
        "**Finished.** One lane landed. The kit was re-run on the merged result.\n"
    )
    parts = {one["part"]: one["text"] for one in data.brief_parts(said)}
    assert parts["finished"] == "One lane landed. The kit was re-run on the merged result."


def test_an_unlabelled_entry_yields_no_parts_at_all(project) -> None:
    """This module reads a shape; it never decides which sentence is which part."""
    assert data.brief_parts(entries(project)[-1][2]) == []


def test_the_reading_says_which_parts_the_brief_on_record_labels(project) -> None:
    reading = data.brief_reading(entries(project))
    assert reading["labelled"] is False
    assert reading["entry"] == "where things stand"
    assert [one["label"] for one in reading["parts"]] == [
        "Time away", "What finished", "What is stuck", "What needs your word", "What quietly changed"
    ]
    assert all(one["recorded"] is False for one in reading["parts"])
    # Nothing is invented to fill a missing part — there is no text field to fill.
    assert all("text" not in one for one in reading["parts"])


def test_a_brief_missing_one_part_reads_as_missing_that_one_part() -> None:
    without_stuck = "\n".join(
        line for line in LABELLED_ENTRY.splitlines() if not line.startswith("**Stuck.")
    )
    reading = data.brief_reading([("2026-09-03", "a stamped return", without_stuck)])
    assert reading["labelled"] is True
    missing = [one["label"] for one in reading["parts"] if not one["recorded"]]
    assert missing == ["What is stuck"]


def test_no_entries_at_all_is_an_empty_brief_and_not_a_crash() -> None:
    assert data.return_brief([]) == []
    assert data.brief_reading([])["labelled"] is False


# --------------------------------------------------------------------------
# Core 4 — every turn on the timeline opens onto its evidence
# --------------------------------------------------------------------------


def test_every_timeline_entry_carries_evidence_to_open(client: TestClient) -> None:
    """A turn is [date, title, one sentence, evidence] — the fourth place is new.

    Falsity condition — the shape this replaces was three places long, so a
    turn had nothing to open at all; a row of length 3 fails here.
    """
    timeline = operation(client)["timeline"]
    assert len(timeline) == 3
    for date, title, _text, proof in timeline:
        assert date and title
        assert proof, f"{title} carries nothing to open"
        assert proof["sentences"], "the evidence is the entry the summary was cut from"
        assert proof["ref"].startswith("docs/workflow/OWNER-RETURN-LOG.md §")


def test_the_evidence_is_the_whole_entry_the_summary_was_cut_from(client: TestClient) -> None:
    _date, title, text, proof = operation(client)["timeline"][0]
    assert title == "where things stand"
    assert text == "The sign-in path is real and was re-checked on the merged result."
    said = proof["sentences"]
    assert said[0] == text
    assert len(said) == 8, "the summary is one sentence of eight; the other seven are the evidence"


def test_the_evidence_names_the_commit_that_recorded_the_turn(client: TestClient, project) -> None:
    timeline = operation(client)["timeline"]
    shas = {turn[1]: turn[3]["commit"] for turn in timeline}
    assert all(shas.values()), "a turn with no commit named cannot be read back off the machine"
    # The two entries written in the first commit share it; the third does not.
    assert shas["the run begins"] == shas["wave 2 is about the guard"]
    assert shas["where things stand"] != shas["the run begins"]
    # And the sha is real: git can show it.
    subprocess.run(["git", "show", "--quiet", shas["where things stand"]],
                   cwd=project["repo"], check=True, capture_output=True)


def test_the_commit_date_is_the_commits_own_and_is_not_corrected(client: TestClient) -> None:
    """The heading's date and the commit's date are different facts.

    On the real log the newest entry is headed 2026-09-04 and was committed on
    2026-09-03. Neither is adjusted to agree with the other.
    """
    date, _title, _text, proof = operation(client)["timeline"][0]
    assert date == "2026-09-03"
    assert proof["committedOn"], "the commit's own date is carried, whatever it says"


def test_an_entry_no_commit_added_still_reports_honestly() -> None:
    """A repo with no such file names no commit — and never invents one."""
    assert data.owner_log_commits(None) == {}
    turns = data.confidence_timeline([("2026-09-03", "unstamped", "One sentence only.")], None)
    assert turns[0][3]["commit"] == ""
    assert turns[0][3]["sentences"] == ["One sentence only."]


# --------------------------------------------------------------------------
# what the surface does with them — read from the client the app ships
# --------------------------------------------------------------------------


def test_the_wave_card_shows_the_reason_and_marks_one_that_is_not_recorded() -> None:
    source = OPERATION_JS.read_text(encoding="utf-8")
    assert "w.reason" in source and "reasonSource" in source
    assert "Not recorded" in source, "a wave with no reason on record must read as an absence"


def test_a_reason_is_allowed_to_break_anywhere_so_none_of_it_is_cut_off() -> None:
    """Measured at 1280: one reason ran 216px wide inside a 186px card.

    The wave card hides its overflow, so the end of that sentence was gone off
    the right edge — a reason nobody can finish reading. The tokens that do it
    (`umbrella+console+collaboration`, a path, a sha) are what records are full
    of, so the reason and its source are told they may break anywhere.
    """
    source = OPERATION_JS.read_text(encoding="utf-8")
    assert "overflow-wrap:anywhere" in source
    assert source.count("${WRAP}") >= 3, "the reason, its source, and a redraw all carry long tokens"


def test_the_surface_shows_why_the_plan_was_redrawn() -> None:
    shell = OPERATION_HTML.read_text(encoding="utf-8")
    source = OPERATION_JS.read_text(encoding="utf-8")
    assert "Why the plan was redrawn" in shell
    assert "planRedrawList" in source and "op.redraws" in source


def test_the_surface_names_the_five_parts_and_which_are_labelled() -> None:
    shell = OPERATION_HTML.read_text(encoding="utf-8")
    source = OPERATION_JS.read_text(encoding="utf-8")
    assert 'id="briefParts"' in shell
    assert "renderBriefParts" in source and "briefReading" in source


def test_the_timeline_entry_offers_its_evidence_to_open() -> None:
    source = OPERATION_JS.read_text(encoding="utf-8")
    assert "Open the evidence" in source and "data-open-evidence" in source
    # Both payload shapes read: the live one, and the dev fixtures' older list.
    assert "Array.isArray(entry)" in source
