"""Data-lane fixes for the Operation surface's preview (`operation-data.md`).

Five things were observed wrong before this file, each with its own falsity
condition below:

* **`summary=last[-1]` extracted incidental footer/fragments.** The manager
  card's `summary` field took the LAST sentence of the newest return-brief
  entry's whole body -- whichever part happened to be written last, not the
  part that says where the project stands. `latest_summary` reads the brief's
  own "Finished" part instead, and falls back to the entry's own heading (the
  few words the manager session wrote to describe its state) for a brief
  written before the return-brief convention labelled anything.
* **DRAFT conflated an unmeasured ledger with an unratified document.**
  `doc_state`'s legacy `state` field reads "draft" for two different silences:
  a document the ledger has never measured, and a document nobody has ever
  ratified. A steward reading the one word "draft" cannot tell which. The
  additive `docLock` (a fact about the DOCUMENT) and `conformance` (a fact
  about the LEDGER) objects keep the two apart, so a locked-but-unmeasured
  contract and an unlocked-but-kept one read as what they actually are.
* **`throughput()` served `0` for an unavailable tracker.** `0` derived items
  and "no tracker configured" are different claims; serving the first for the
  second is exactly the "unknown read as zero" the goal names.
* **`manifest_lanes()` read columns by position.** The goal-batch skill's own
  manifest convention (`lane \xb7 worktree \xb7 branch \xb7 tmux \xb7 goal \xb7 log \xb7
  session_id`) puts `tmux` one column earlier than the ten-lane-highway
  convention this reader was written against. Read positionally, a
  goal-batch manifest's `tmux` column lands in the `goal` field instead.
* **`highway_text()` silently assumed `HIGHWAY.md`.** A manager session that
  names its own `plan_record` explicitly was never asked; this app always
  read `<batch_dir>/HIGHWAY.md` regardless.

No fixture here mutates the live tracker or any real manager's files --
everything is built fresh under `tmp_path`.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app import config, data  # noqa: E402

OPERATION_HTML = Path(__file__).resolve().parents[1] / "templates" / "operation.html"


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "user.name=Test", "-c", "user.email=test@example.invalid", *args],
        cwd=repo,
        check=True,
        capture_output=True,
    )


# --------------------------------------------------------------------------
# docLock -- a fact about the document, read from its own H1
# --------------------------------------------------------------------------


def test_doc_lock_reads_the_h1_status_word_verbatim(tmp_path) -> None:
    frozen = tmp_path / "frozen.v1.md"
    frozen.write_text("# Frozen Contract \u2014 v1 (FROZEN 2026-09-04)\n\n## Core\n", encoding="utf-8")
    draft = tmp_path / "draft.v1.md"
    draft.write_text("# Draft Contract \u2014 v1 (DRAFT)\n\n## Core\n", encoding="utf-8")
    loose = tmp_path / "loose.v1.md"
    loose.write_text(
        "# Loose Contract \u2014 v1 (DRAFT \u2014 held loosely 2026-09-06)\n\n## Core\n", encoding="utf-8"
    )
    missing = tmp_path / "missing.v1.md"

    frozen_lock = data.doc_lock(frozen)
    assert frozen_lock["locked"] is True
    assert frozen_lock["label"] == "FROZEN 2026-09-04"
    assert frozen_lock["source"] == "document-h1"

    draft_lock = data.doc_lock(draft)
    assert draft_lock["locked"] is False
    assert draft_lock["label"] == "DRAFT"

    loose_lock = data.doc_lock(loose)
    assert loose_lock["locked"] is False
    assert "held loosely" in loose_lock["label"]

    # A file that cannot be read answers with an honest silence, never a guess.
    missing_lock = data.doc_lock(missing)
    assert missing_lock == {"locked": False, "label": "", "source": "document-h1"}


# --------------------------------------------------------------------------
# conformance -- a fact about the ledger, never dressed as a lock status
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "state,expected_label,expected_measured",
    [
        # Locked, but nothing watches it yet -- "Not checked", never "Draft".
        ({"state": "draft", "standing": "", "standingSentence": "", "clauses": 0}, "Not checked", False),
        # Measured and kept -- "Kept", never a lock word.
        ({"state": "kept", "standing": "Kept", "standingSentence": "All good.", "clauses": 3}, "Kept", True),
        ({"state": "gap", "standing": "Broken", "standingSentence": "One row failed.", "clauses": 2}, "Broken", True),
        ({"state": "gap", "standing": "Pinned open", "standingSentence": "Held open.", "clauses": 1}, "Pinned open", True),
        ({"state": "gap", "standing": "Can't check", "standingSentence": "Nothing checkable.", "clauses": 1}, "Can't check", True),
        # No ledger at all in the project -- the same honest "Not checked".
        ({"state": "draft", "standing": "", "standingSentence": "No conformance ledger in this project yet.", "clauses": 0}, "Not checked", False),
    ],
)
def test_doc_conformance_never_labels_unmeasured_as_draft_or_kept(
    state, expected_label, expected_measured
) -> None:
    made = data.doc_conformance(state)
    assert made["label"] == expected_label
    assert made["measured"] is expected_measured
    assert made["state"] == state["state"]
    assert made["clauses"] == state["clauses"]
    assert made["sentence"] == state["standingSentence"]
    # The one word this object must never say for something unmeasured.
    if not expected_measured:
        assert made["label"] not in ("Draft", "Kept")


LEDGER = """# Demo conformance ledger.
- id: DEMO-001
  title: the draft contract keeps its one promise
  contract:
    file: contracts/draft.v1.md
    clause: "Core 1"
  disposition: CONFORMS
"""

FROZEN_CONTRACT = "# Frozen Contract \u2014 v1 (FROZEN 2026-09-04)\n\n## Core\n\n1. **Locked, unmeasured.**\n"
DRAFT_CONTRACT = "# Draft Contract \u2014 v1 (DRAFT)\n\n## Core\n\n1. **Draft, kept.** Watched below.\n"


@pytest.fixture
def ledger_repo(tmp_path) -> Path:
    """A locked contract the ledger never measures, beside a draft it keeps."""
    repo = tmp_path / "demo-repo"
    (repo / "contracts").mkdir(parents=True)
    (repo / "ledger").mkdir(parents=True)
    (repo / "docs").mkdir(parents=True)
    (repo / "docs" / "VISION.md").write_text("# Vision (DRAFT)\n", encoding="utf-8")
    (repo / "contracts" / "frozen.v1.md").write_text(FROZEN_CONTRACT, encoding="utf-8")
    (repo / "contracts" / "draft.v1.md").write_text(DRAFT_CONTRACT, encoding="utf-8")
    (repo / "ledger" / "rows.yaml").write_text(LEDGER, encoding="utf-8")
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "seed")
    return repo


def test_repositories_payload_shows_a_locked_document_the_ledger_never_measured(ledger_repo) -> None:
    """The exact conflation the goal names: locked-but-unmeasured vs draft-but-kept."""
    mc = config.ManagerConfig(id="demo", name="Demo", repos=(ledger_repo,))
    payload = data.repositories_payload(mc)
    docs = {one["path"]: one for one in payload[0]["docs"]}

    frozen_doc = docs["contracts/frozen.v1.md"]
    assert frozen_doc["docLock"]["locked"] is True
    assert frozen_doc["conformance"]["measured"] is False
    assert frozen_doc["conformance"]["label"] == "Not checked"
    # Legacy fields untouched -- a reader that has never heard of docLock or
    # conformance still reads exactly what it always read.
    assert frozen_doc["state"] == "draft"
    assert frozen_doc["clauses"] == 0

    draft_doc = docs["contracts/draft.v1.md"]
    assert draft_doc["docLock"]["locked"] is False
    assert draft_doc["conformance"]["measured"] is True
    assert draft_doc["conformance"]["label"] == "Kept"
    assert draft_doc["state"] == "kept"


def test_doc_payload_adds_docLock_and_conformance_beside_legacy_fields(ledger_repo) -> None:
    frozen_path = ledger_repo / "contracts" / "frozen.v1.md"
    payload = data.doc_payload(ledger_repo, frozen_path)
    assert payload["docLock"] == {"locked": True, "label": "FROZEN 2026-09-04", "source": "document-h1"}
    assert payload["conformance"]["measured"] is False
    assert payload["conformance"]["label"] == "Not checked"
    # The pre-existing lock fields this UI already reads are unchanged.
    assert payload["locked"] == "FROZEN"
    assert payload["editable"] is False


def test_conformance_is_not_checked_with_no_ledger_in_the_project_at_all(tmp_path) -> None:
    """Malformed/absent ledger data: the honest silence, never a false pass."""
    repo = tmp_path / "no-ledger-repo"
    (repo / "contracts").mkdir(parents=True)
    (repo / "docs").mkdir(parents=True)
    (repo / "docs" / "VISION.md").write_text("# Vision (DRAFT)\n", encoding="utf-8")
    (repo / "contracts" / "solo.v1.md").write_text(DRAFT_CONTRACT, encoding="utf-8")
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "seed")

    state = data.doc_state(repo, repo / "contracts" / "solo.v1.md")
    conformance = data.doc_conformance(state)
    assert conformance["measured"] is False
    assert conformance["label"] == "Not checked"


# --------------------------------------------------------------------------
# latest_summary -- a meaningful line, not whatever sentence was last
# --------------------------------------------------------------------------


def test_latest_summary_prefers_the_finished_part_over_the_last_sentence() -> None:
    body = (
        "**Time away.** Ten hours, one wave.\n"
        "**Finished.** The gap analysis's whole plan landed and was re-checked.\n"
        "**Stuck.** Nothing is stuck.\n"
        "**Needs you.** Nothing needs you this turn.\n"
        "**Anything quietly broken.** A settings file was corrupted at 09:24 UTC "
        "by the CLI's own update check; worth knowing if other sessions failed "
        "to start this morning.\n"
    )
    entries = [("2026-09-04", "the run closed", body)]
    summary = data.latest_summary(entries)
    # The falsity condition this replaces: the old reading returned the LAST
    # sentence of the WHOLE body, which is the "quietly broken" footer here,
    # not a meaningful account of where the project stands.
    assert "corrupted" not in summary
    assert "gap analysis's whole plan landed" in summary


def test_latest_summary_falls_back_to_the_heading_when_nothing_is_labelled() -> None:
    body = "The long-form explainer landed. The turnkey harness is honestly red."
    entries = [("2026-09-02", "explainer and turnkey landed", body)]
    assert data.latest_summary(entries) == "explainer and turnkey landed"


def test_latest_summary_is_empty_with_no_entries() -> None:
    assert data.latest_summary([]) == ""


def test_manager_payload_summary_is_not_a_footer_fragment(tmp_path) -> None:
    """End-to-end: `manager_payload`'s own `summary` field, not the helper."""
    repo = tmp_path / "demo-repo"
    (repo / "docs" / "workflow").mkdir(parents=True)
    (repo / "docs" / "workflow" / "OWNER-RETURN-LOG.md").write_text(
        "# Owner return log\n\n"
        "## 2026-09-04 13:49 - return\n"
        "**Time away.** Ten hours, one wave.\n"
        "**Finished.** Every write the umbrella names now exists in the app.\n"
        "**Stuck.** Nothing is stuck.\n"
        "**Needs you.** Nothing needs you.\n"
        "**Anything quietly broken.** A settings file was corrupted overnight.\n",
        encoding="utf-8",
    )
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "seed")

    mc = config.ManagerConfig(id="demo", name="Demo", repos=(repo,))
    payload = data.manager_payload(mc)
    assert "corrupted" not in payload["summary"]
    assert "Every write the umbrella names" in payload["summary"]


# --------------------------------------------------------------------------
# throughput -- unknown is not zero
# --------------------------------------------------------------------------


def test_throughput_reports_unknown_not_zero_for_an_unavailable_tracker() -> None:
    flow = data.throughput({}, merged=3, reopened=1)
    assert flow["derived"] is None
    assert flow["resolved"] is None
    assert flow["stuck"] is None
    assert flow["available"] is False
    # Verified and reopened are read from git/the plan record directly, so
    # they stay real counts whether or not a tracker answers.
    assert flow["verified"] == 3
    assert flow["reopened"] == 1


def test_throughput_reports_real_counts_when_the_tracker_answers() -> None:
    flow = data.throughput({"TOTAL": 76, "RESOLVED": 57, "BLOCKED": 3}, merged=5, reopened=2)
    assert flow["derived"] == 76
    assert flow["resolved"] == 57
    assert flow["stuck"] == 3
    assert flow["available"] is True


# --------------------------------------------------------------------------
# manifest_lanes -- read by header name, never by a fixed position
# --------------------------------------------------------------------------


def _batch(tmp_path: Path, manifest_text: str) -> Path:
    batch = tmp_path / "hw-demo"
    (batch / "lanes" / "w1-alpha").mkdir(parents=True)
    (batch / "manifest.tsv").write_text(manifest_text, encoding="utf-8")
    return batch


def test_manifest_lanes_reads_the_highway_convention_by_name(tmp_path) -> None:
    """The ten-lane-highway convention: `base` sits between branch and tmux."""
    batch = _batch(
        tmp_path,
        "lane\tworktree\tbranch\tbase\ttmux\tgoal\tlog\tstarted\n"
        "w1-alpha\t/wt/alpha\tlane/w1-alpha\tdeadbee\thw__demo__w1-alpha\t"
        "/goals/w1-alpha.md\t/logs/w1-alpha.log\t2026-09-01T10:00:00Z\n",
    )
    mc = config.ManagerConfig(id="demo", name="Demo", batch_dir=batch)
    rows = {row.name: row for row in data.manifest_lanes(mc)}
    alpha = rows["w1-alpha"]
    assert alpha.tmux == "hw__demo__w1-alpha"
    assert alpha.goal == "/goals/w1-alpha.md"
    assert alpha.log == "/logs/w1-alpha.log"
    assert alpha.launched_at == "2026-09-01T10:00:00Z"


def test_manifest_lanes_reads_the_goal_batch_convention_without_misaligning_tmux(tmp_path) -> None:
    """goal-batch's own manifest shape (its skill body): no `base` column, so
    `tmux` sits one column earlier than the highway convention.

    Read positionally (the bug this replaces), `tmux` would read this row's
    `goal` value instead -- the exact "don't silently shift tmux/goal/log
    columns" failure the goal names.
    """
    batch = _batch(
        tmp_path,
        "lane\tworktree\tbranch\ttmux\tgoal\tlog\tsession_id\n"
        "w1-alpha\t/wt/alpha\tlane/w1-alpha\tgb__demo__w1-alpha\t"
        "/goals/w1-alpha.md\t/logs/w1-alpha.log\tsess-123\n",
    )
    mc = config.ManagerConfig(id="demo", name="Demo", batch_dir=batch)
    rows = {row.name: row for row in data.manifest_lanes(mc)}
    alpha = rows["w1-alpha"]
    assert alpha.tmux == "gb__demo__w1-alpha"
    assert alpha.goal == "/goals/w1-alpha.md"
    assert alpha.log == "/logs/w1-alpha.log"


def test_manifest_lanes_falls_back_to_the_old_layout_for_an_unrecognized_header(tmp_path) -> None:
    """A header naming nothing this reader recognizes reads by the fixed
    8-column layout this app has always assumed (`name, worktree, branch,
    <unused>, tmux, goal, log, launched_at`) rather than by name."""
    batch = tmp_path / "hw-demo"
    batch.mkdir(parents=True)
    (batch / "manifest.tsv").write_text(
        "col1\tcol2\tcol3\tcol4\tcol5\tcol6\tcol7\tcol8\n"
        "w1-alpha\t/wt/alpha\tlane/w1-alpha\tdeadbee\thw__demo__w1-alpha\t"
        "/goals/w1-alpha.md\t/logs/w1-alpha.log\t2026-09-01T10:00:00Z\n",
        encoding="utf-8",
    )
    mc = config.ManagerConfig(id="demo", name="Demo", batch_dir=batch)
    rows = {row.name: row for row in data.manifest_lanes(mc)}
    alpha = rows["w1-alpha"]
    assert alpha.tmux == "hw__demo__w1-alpha"
    assert alpha.goal == "/goals/w1-alpha.md"


# --------------------------------------------------------------------------
# plan_record_path / highway_text -- an explicit plan record wins
# --------------------------------------------------------------------------


def test_highway_text_honors_an_explicit_plan_record_over_highway_md(tmp_path) -> None:
    batch = tmp_path / "hw-demo"
    batch.mkdir(parents=True)
    (batch / "HIGHWAY.md").write_text("# Highway\n\nThe old convention's file.\n", encoding="utf-8")
    explicit = tmp_path / "elsewhere" / "PLAN.md"
    explicit.parent.mkdir(parents=True)
    explicit.write_text("# Plan\n\nThe explicitly named plan record.\n", encoding="utf-8")

    mc = config.ManagerConfig(id="demo", name="Demo", batch_dir=batch, plan_record=explicit)
    assert "explicitly named plan record" in data.highway_text(mc)
    assert data.plan_record_path(mc) == explicit


def test_highway_text_falls_back_to_highway_md_when_no_plan_record_is_named(tmp_path) -> None:
    batch = tmp_path / "hw-demo"
    batch.mkdir(parents=True)
    (batch / "HIGHWAY.md").write_text("# Highway\n\nThe old convention's file.\n", encoding="utf-8")

    mc = config.ManagerConfig(id="demo", name="Demo", batch_dir=batch)
    assert "old convention" in data.highway_text(mc)
    assert data.plan_record_path(mc) == batch / "HIGHWAY.md"


# --------------------------------------------------------------------------
# layout -- the return brief is the main, full-width thing on the page
# --------------------------------------------------------------------------


def test_return_card_is_full_width_not_squeezed_beside_three_others() -> None:
    """Core 3: the return brief is the FIRST thing a returning steward reads.

    It shared a quarter-width column with strategy/throughput/confidence,
    which made "first" untrue in practice -- a steward had to find it among
    four narrow cards. `wide-card` is this app's own full-row class.
    """
    html = OPERATION_HTML.read_text(encoding="utf-8")
    assert '"return-card panel-card wide-card"' in html, (
        "the return brief card must carry wide-card so it is not squeezed "
        "into the same row as strategy/throughput/confidence"
    )
