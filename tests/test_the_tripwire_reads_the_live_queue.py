"""The live-work tripwire: what it fails, and what it refuses to call a pass.

`docs/LEDGER-FORMAT.md` §2 requires a `work` ref on every GAP / VIOLATION row,
and §6.3 requires that ref to be **live**. `ledger/checks/live_work.py` is the
rule; this file is the proof that it discriminates.

It was written because the rule could not fire. Until 2026-09-05 the check read
`docs/work-items.json`, a committed snapshot refreshed by a hand-run command
that nothing in the gate ran, and an id missing from that snapshot was reported
`[INFO]` rather than failed. Measured on 2026-09-04 (converge-j0u5): 76 items in
the snapshot against 202 live, 28 red rows citing resolved work — and `[OK]`
printed over all of it.

So five things are proved here, one per way the rule can be wrong:

1. a red row citing **resolved** work fails, and fails **by row id and ref**;
2. a ref the checker cannot resolve at all **fails** — it is never downgraded;
3. a red row citing live work passes, for every live status bd has;
4. an unreachable queue plus a **fresh** snapshot warns, and never reports OK;
5. an unreachable queue plus a **stale or absent** snapshot fails outright.

THEY WERE RUN AGAINST THE OLD LOGIC, WHICH IS THE ONLY WAY TO KNOW THEY
DISCRIMINATE. The pre-2026-09-05 tripwire was transcribed verbatim behind this
module's API and this file pointed at it: **20 of these 22 failed**. The two
that passed are the two that exercise the single path the old rule could take —
a ref the export itself already called resolved — which is exactly the narrow
window the measurement above says it was firing in.
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
#: The module under test. Kept on one line: a control run points it elsewhere.
TRIPWIRE = REPO_ROOT / "ledger" / "checks" / "live_work.py"


def _load(path: Path):
    """Load the checker by path — it is a script beside the ledger, not a package."""
    name = "live_work_under_test"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    # `@dataclass` resolves its module through sys.modules, so register first.
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


live_work = _load(TRIPWIRE)


# --------------------------------------------------------------------------
# stand-ins for the queue, so no test here needs a running tracker
# --------------------------------------------------------------------------


def queue(**statuses: str):
    """A reachable queue holding exactly these `id: status` pairs."""

    def statuses_for(project: str) -> dict[str, str]:
        return {i: s for i, s in statuses.items() if live_work.project_of(i) == project}

    return statuses_for


def unreachable(reason: str = "the tracker is not answering"):
    """A queue that cannot be read at all."""

    def statuses_for(project: str) -> dict[str, str]:
        raise live_work.LiveQueueUnreachable(reason)

    return statuses_for


def snapshot(tmp_path: Path, *, age_hours: float = 0.0, **statuses: str) -> Path:
    """A committed-export-shaped file of a chosen age."""
    path = tmp_path / "work-items.json"
    path.write_text(
        json.dumps([{"id": i, "status": s} for i, s in statuses.items()]),
        encoding="utf-8",
    )
    when = time.time() - age_hours * 3600
    os.utime(path, (when, when))
    return path


# --------------------------------------------------------------------------
# 1. resolved work, cited by a red row, fails by name
# --------------------------------------------------------------------------


def test_a_red_row_citing_resolved_work_fails_by_row_id_and_ref():
    report = live_work.evaluate(
        [("CVG-008", "converge-2ro")],
        statuses_for=queue(**{"converge-2ro": "resolved"}),
    )
    assert report.verdict == "FAIL"
    assert report.source == "live"
    assert report.failures == ["CVG-008 cites converge-2ro, which is already resolved"]
    assert "  [FAIL] CVG-008 cites converge-2ro, which is already resolved" in report.detail


def test_the_rows_that_fail_are_named_one_at_a_time_not_counted():
    report = live_work.evaluate(
        [("CVG-008", "converge-2ro"), ("CVG-009", "converge-f1l"), ("CVG-103", "converge-ism")],
        statuses_for=queue(
            **{"converge-2ro": "resolved", "converge-f1l": "resolved", "converge-ism": "open"}
        ),
    )
    assert report.verdict == "FAIL"
    assert len(report.failures) == 2
    assert {"CVG-008", "CVG-009"} == {f.split()[0] for f in report.failures}


# --------------------------------------------------------------------------
# 2. an id the checker cannot resolve is a failure, not a note
# --------------------------------------------------------------------------


def test_a_ref_absent_from_the_live_project_fails_and_is_never_downgraded():
    report = live_work.evaluate(
        [("CVG-012", "converge-do8")],
        statuses_for=queue(**{"converge-ism": "open"}),
    )
    assert report.verdict == "FAIL"
    assert report.failures == [
        "CVG-012 cites converge-do8, which does not exist in project converge"
    ]
    assert not any("INFO" in line for line in report.detail)


def test_a_ref_that_is_not_a_tracker_id_at_all_fails():
    report = live_work.evaluate(
        [("CVG-999", "see the wave-8 thread")],
        statuses_for=queue(**{"converge-ism": "open"}),
    )
    assert report.verdict == "FAIL"
    assert "is not a tracker ref" in report.failures[0]


# --------------------------------------------------------------------------
# 3. live work passes — every status bd calls live
# --------------------------------------------------------------------------


@pytest.mark.parametrize("status", ["open", "held", "blocked", "deferred"])
def test_a_red_row_citing_live_work_passes(status: str):
    report = live_work.evaluate(
        [("CVG-103", "converge-ism")], statuses_for=queue(**{"converge-ism": status})
    )
    assert report.verdict == "OK"
    assert report.failures == []
    assert report.source == "live"
    assert "LIVE queue" in report.summary


def test_the_project_queried_comes_from_the_ref_itself():
    """No second copy of `converge` lives in the checker — the row names it."""
    asked: list[str] = []

    def statuses_for(project: str) -> dict[str, str]:
        asked.append(project)
        return {"some-other-project-a1b2": "open"}

    report = live_work.evaluate(
        [("CVG-001", "some-other-project-a1b2")], statuses_for=statuses_for
    )
    assert asked == ["some-other-project"]
    assert report.verdict == "OK"


# --------------------------------------------------------------------------
# 4. unreachable + fresh snapshot: warn, and never OK
# --------------------------------------------------------------------------


def test_an_unreachable_queue_with_a_fresh_snapshot_warns_and_never_reports_ok(tmp_path):
    snap = snapshot(tmp_path, **{"converge-ism": "open"})
    report = live_work.evaluate(
        [("CVG-103", "converge-ism")], statuses_for=unreachable(), snapshot=snap
    )
    assert report.verdict == "WARN"
    assert report.source == "snapshot"
    assert report.failures == []
    assert "UNREACHABLE" in "\n".join(report.detail)
    assert str(snap) in "\n".join(report.detail)
    assert "NOT evaluated against live data" in report.summary


def test_the_fallback_still_fails_a_row_the_snapshot_itself_calls_resolved(tmp_path):
    snap = snapshot(tmp_path, **{"converge-2ro": "resolved"})
    report = live_work.evaluate(
        [("CVG-008", "converge-2ro")], statuses_for=unreachable(), snapshot=snap
    )
    assert report.verdict == "FAIL"
    assert report.failures == ["CVG-008 cites converge-2ro, which is already resolved"]


def test_the_fallback_calls_an_absent_ref_unjudged_rather_than_passed(tmp_path):
    snap = snapshot(tmp_path, **{"converge-ism": "open"})
    report = live_work.evaluate(
        [("CVG-012", "converge-do8")], statuses_for=unreachable(), snapshot=snap
    )
    assert report.verdict == "WARN"
    assert "UNJUDGED" in "\n".join(report.detail)
    assert "UNJUDGED" in report.summary


# --------------------------------------------------------------------------
# 5. unreachable + stale or absent snapshot: fail, never OK
# --------------------------------------------------------------------------


def test_an_unreachable_queue_with_a_stale_snapshot_fails(tmp_path):
    snap = snapshot(tmp_path, age_hours=30, **{"converge-ism": "open"})
    report = live_work.evaluate(
        [("CVG-103", "converge-ism")], statuses_for=unreachable(), snapshot=snap
    )
    assert report.verdict == "FAIL"
    assert "could not be evaluated" in report.summary
    assert report.failures == [report.summary]


def test_an_unreachable_queue_with_no_snapshot_at_all_fails(tmp_path):
    report = live_work.evaluate(
        [("CVG-103", "converge-ism")],
        statuses_for=unreachable(),
        snapshot=tmp_path / "nothing-here.json",
    )
    assert report.verdict == "FAIL"
    assert "no snapshot" in report.summary
    assert "could not be evaluated" in report.summary


def test_a_checkout_fresh_mtime_cannot_launder_an_old_snapshot(tmp_path):
    """A fresh clone stamps every file with the checkout time. That is not age.

    Without this, a snapshot exported months ago passes as minutes old in CI —
    the one environment where a stale fallback most needs catching.
    """
    repo = tmp_path / "clone"
    repo.mkdir()
    env = {
        **os.environ,
        "GIT_AUTHOR_DATE": "2020-01-01T00:00:00 +0000",
        "GIT_COMMITTER_DATE": "2020-01-01T00:00:00 +0000",
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@example.com",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@example.com",
    }
    run = lambda *a: subprocess.run(a, cwd=repo, env=env, capture_output=True, check=True)
    run("git", "init", "-q")
    snap = repo / "work-items.json"
    snap.write_text(json.dumps([{"id": "converge-ism", "status": "open"}]), encoding="utf-8")
    run("git", "add", "work-items.json")
    run("git", "commit", "-qm", "export")
    os.utime(snap, None)  # what `git checkout` does to mtime

    hours, stamp = live_work.snapshot_age_hours(snap)
    assert hours > live_work.SNAPSHOT_MAX_AGE_H
    assert "last commit" in stamp

    report = live_work.evaluate(
        [("CVG-103", "converge-ism")], statuses_for=unreachable(), snapshot=snap
    )
    assert report.verdict == "FAIL"
    assert "could not be evaluated" in report.summary


# --------------------------------------------------------------------------
# reading the queue: every incomplete answer is unreachable, not a verdict
# --------------------------------------------------------------------------


def _runner(stdout: str = "", returncode: int = 0, stderr: str = "", raises=None):
    def run(cmd, **kwargs):
        if raises is not None:
            raise raises
        return subprocess.CompletedProcess(cmd, returncode, stdout, stderr)

    return run


def test_the_live_read_asks_the_cli_for_the_whole_queue_as_json():
    seen: dict[str, list[str]] = {}

    def run(cmd, **kwargs):
        seen["cmd"] = list(cmd)
        payload = {
            "project": "converge",
            "items": [{"id": "converge-ism", "status": "open"}],
            "returned_count": 1,
            "total_count": 1,
            "truncated": False,
        }
        return subprocess.CompletedProcess(cmd, 0, json.dumps(payload), "")

    assert live_work.live_statuses("converge", runner=run) == {"converge-ism": "open"}
    assert seen["cmd"] == [
        "amplifier-work-tracker",
        "list",
        "--project",
        "converge",
        "--limit",
        "500",
        "--json",
    ]


def test_a_truncated_queue_is_unreachable_because_absence_would_be_a_lie():
    payload = {
        "items": [{"id": "converge-ism", "status": "open"}],
        "returned_count": 1,
        "total_count": 236,
        "truncated": True,
    }
    with pytest.raises(live_work.LiveQueueUnreachable, match="partial queue"):
        live_work.live_statuses("converge", runner=_runner(json.dumps(payload)))


@pytest.mark.parametrize(
    "runner, match",
    [
        (_runner("", 2, "connection refused"), "exited 2"),
        (_runner("not json at all"), "did not print JSON"),
        (_runner(json.dumps({"items": []})), "no items at all"),
        (_runner(raises=FileNotFoundError()), "not on PATH"),
    ],
)
def test_every_unreadable_answer_raises_rather_than_returning_an_empty_queue(runner, match):
    with pytest.raises(live_work.LiveQueueUnreachable, match=match):
        live_work.live_statuses("converge", runner=runner)


def test_no_red_rows_is_vacuously_kept_and_says_so():
    report = live_work.evaluate([], statuses_for=unreachable())
    assert report.verdict == "OK"
    assert report.source == "none"
    assert "no GAP/VIOLATION rows to judge" in report.summary
