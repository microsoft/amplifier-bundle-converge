"""converge-51oq: step (j) reads the REGISTERED plan record, not a nearby
batch HIGHWAY.

The measured defect: a manager's actual registration names an operation
PLAN.md that lives OUTSIDE its nested batch directory, while the batch
directory (`--workspace`) carries its own free-form HIGHWAY.md and the lane
facts (manifest.tsv, briefs, worktrees) `wave_workspace` still supplies.
`read_plan_record`'s legacy HIGHWAY/PLAN/WAVE-LOG search only ever looks
inside `--workspace`, so it silently picked the nearer batch file over the
one actually registered.

These tests discriminate the fix along the five lines converge-51oq names:

  * an explicit plan record wins over a nearer legacy file in the workspace
  * legacy fallback is unchanged when no explicit record is given
  * a missing/invalid explicit override fails clearly -- it never falls back
  * different lane data (B) plus an external plan (P) read correctly at once
  * the wrapper forwards CONVERGE_PLAN_RECORD only when it is set (its own
    focused test lives in tests/test_turnkey_clause_branch.py, beside the
    matching CONVERGE_INTEGRATION_BRANCH coverage)

Every fixture here is synthetic: no real turnkey wave, no live queue.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TURNKEY = ROOT / "evaluations" / "turnkey"


def _load_harness():
    """Import run.py by path. It is a `uv run` script, not an installed module."""
    spec = importlib.util.spec_from_file_location("turnkey_run", TURNKEY / "run.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    # Register before executing: @dataclass resolves its own module out of
    # sys.modules while the class body is being processed.
    sys.modules["turnkey_run"] = module
    spec.loader.exec_module(module)
    return module


run = _load_harness()


# ---------------------------------------------------------------------------
# a fake environment: an in-memory file table, everything else refuses
# ---------------------------------------------------------------------------


class _FilesEnv(run.Env):
    """An environment whose only fact is a table of path -> text.

    Every `run()` call fails (`Ran(1, ...)`), so callers that gracefully
    degrade on a failing command (read_worktrees, read_tmux_panes,
    commits_beyond, ...) see exactly what a workspace with no git history and
    no live tmux session looks like -- never an exception.
    """

    def __init__(self, files: dict[str, str]):
        self.files = files

    def read(self, path: str) -> str | None:
        return self.files.get(path)

    def exists(self, path: str) -> bool:
        return path in self.files

    def run(self, argv, cwd=None, timeout=120.0, env=None):
        return run.Ran(1, "", "nothing runs in this fixture", argv=argv)


# A real dated, reasoned entry -- the shape clause 2 asks for (a decision word
# AND a reason word in the same entry).
REASONED_ENTRY = "- 2026-09-08T10:00:00Z refill: width 2, because two disjoint items were ready\n"

# A decoy: dated, has a decision word ("merged"), but announces rather than
# reasons -- clause 2's own FAIL shape. If step (j) ever fell back to reading
# this instead of the registered plan, the reading would flip to FAIL.
ANNOUNCEMENT_ONLY_ENTRY = "- 2026-09-01T00:00:00Z merged X. Live 1.\n"


# ---------------------------------------------------------------------------
# read_plan_record: explicit wins, legacy fallback is unchanged, a broken
# explicit override fails clearly
# ---------------------------------------------------------------------------


def test_explicit_plan_record_wins_over_a_nearer_legacy_file():
    env = _FilesEnv({
        "/B/HIGHWAY.md": ANNOUNCEMENT_ONLY_ENTRY,
        "/P/PLAN.md": REASONED_ENTRY,
    })
    where, text, source = run.read_plan_record(env, "/B", explicit="/P/PLAN.md")
    assert (where, text, source) == ("/P/PLAN.md", REASONED_ENTRY, "explicit")


def test_legacy_fallback_without_override_is_unchanged():
    env = _FilesEnv({"/B/HIGHWAY.md": REASONED_ENTRY})
    where, text, source = run.read_plan_record(env, "/B", explicit=None)
    assert (where, text, source) == ("/B/HIGHWAY.md", REASONED_ENTRY, "legacy_fallback")


def test_legacy_fallback_tries_every_plan_record_name_in_order():
    env = _FilesEnv({"/B/WAVE-LOG.md": REASONED_ENTRY})
    where, text, source = run.read_plan_record(env, "/B", explicit=None)
    assert where == "/B/WAVE-LOG.md"
    assert source == "legacy_fallback"


def test_a_missing_explicit_override_does_not_fall_back_to_the_nearer_highway():
    env = _FilesEnv({"/B/HIGHWAY.md": REASONED_ENTRY})  # a perfectly good legacy file
    where, text, source = run.read_plan_record(env, "/B", explicit="/P/does-not-exist.md")
    assert where == "/P/does-not-exist.md"  # pinned to the registered path, not silently /B's
    assert text is None
    assert source == "explicit_unreadable"


def test_step_j_fails_clearly_on_an_unreadable_explicit_override_never_a_skip():
    """The whole clause-reading step refuses, naming the registered path --
    this is the 'fail clearly, never silently fall back' half of the fix."""
    env = _FilesEnv({"/B/HIGHWAY.md": REASONED_ENTRY, "/B/manifest.tsv": ""})
    ctx = run.Context(
        env=env, host=env, mode=run.OBSERVED, workspace="/B", repo="/repo",
        project="converge", integration_branch="main", answer_key={},
        plan_record="/P/does-not-exist.md",
    )
    result = run.step_clauses(ctx)
    assert result.status == run.FAIL
    assert "/P/does-not-exist.md" in result.detail
    assert result.evidence["plan_record_source"] == "explicit_unreadable"
    assert result.evidence["workspace_read"] == "/B"  # lane workspace untouched


# ---------------------------------------------------------------------------
# --plan-record / CONVERGE_PLAN_RECORD at the CLI: an invalid override fails
# the run before any step is attempted -- never a silent legacy fallback
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("bad", ["missing.md", "a-directory"])
def test_a_missing_or_directory_plan_record_refuses_the_run(tmp_path, capsys, bad):
    target = tmp_path / bad
    if bad == "a-directory":
        target.mkdir()
    # else: never created -- "missing.md" does not exist

    exit_code = run.main([
        "--env", "local", "--steps", "j",
        "--plan-record", str(target),
    ])
    captured = capsys.readouterr()
    assert exit_code != 0
    assert "--plan-record" in captured.err
    assert str(target) in captured.err


def test_a_valid_plan_record_passes_cli_validation(tmp_path):
    """The mirror control: a real file at that path is accepted, not refused."""
    target = tmp_path / "PLAN.md"
    target.write_text(REASONED_ENTRY, encoding="utf-8")
    workspace = tmp_path / "batch"
    workspace.mkdir()
    exit_code = run.main([
        "--env", "local", "--steps", "j",
        "--workspace", str(workspace),
        "--repo", str(ROOT),
        "--plan-record", str(target),
        "--json-only",
    ])
    # Validation passed and the run completed (a step (j) SKIP/PASS/FAIL exit,
    # never the argument-refusal exit this file's other test asserts on).
    assert exit_code in (0, 1)


# ---------------------------------------------------------------------------
# the actual targeting bug: different lane data in B, an external plan at P
# ---------------------------------------------------------------------------


def test_different_b_lane_data_plus_external_p_plan_are_both_read_correctly():
    """B supplies the lane facts (manifest.tsv) and its OWN decoy HIGHWAY.md;
    P is the manager's actually-registered plan record, outside B entirely.

    Before the fix, `read_plan_record` only ever looked inside `wave_workspace`
    (B), so it would read B's decoy -- an announcement with no reason, clause
    2's own FAIL shape -- and never see P at all. The discriminator is the
    verdict itself: FAIL if B's decoy were read, PASS only if P was.
    """
    env = _FilesEnv({
        "/B/manifest.tsv": "lane\tworktree\tbranch\tbase_sha\ttmux\tgoal\tlaunched_at\n"
                           "a\t/B/lanes/a/repo\tlane/a\tbase0000\t\t\t\n",
        "/B/HIGHWAY.md": ANNOUNCEMENT_ONLY_ENTRY,  # the nearer batch file -- must NOT be read
        "/external/P/PLAN.md": REASONED_ENTRY,     # the manager's actual registration
    })
    ctx = run.Context(
        env=env, host=env, mode=run.OBSERVED, workspace="/B", repo="/repo",
        project="converge", integration_branch="main", answer_key={},
        plan_record="/external/P/PLAN.md",
    )
    assert ctx.wave_workspace == "/B"  # lane facts targeting is unchanged

    result = run.step_clauses(ctx)

    assert result.evidence["workspace_read"] == "/B"
    assert result.evidence["plan_record"] == "/external/P/PLAN.md"
    assert result.evidence["plan_record_source"] == "explicit"

    clause_2 = next(r for r in result.evidence["clause_readings"] if r["clause"] == "Core 2")
    assert clause_2["verdict"] == run.PASS, clause_2["why"]
    assert clause_2["plan_record"] == "/external/P/PLAN.md"
    # The decoy never surfaces as the source of a PASS.
    assert "/B/HIGHWAY.md" not in str(clause_2)


def test_omitting_plan_record_keeps_reading_bs_own_highway_as_before():
    """The negative control: with no override, B's own file is exactly what
    is read -- the legacy behaviour this fix must leave untouched."""
    env = _FilesEnv({
        "/B/manifest.tsv": "lane\tworktree\tbranch\tbase_sha\ttmux\tgoal\tlaunched_at\n"
                           "a\t/B/lanes/a/repo\tlane/a\tbase0000\t\t\t\n",
        "/B/HIGHWAY.md": REASONED_ENTRY,
    })
    ctx = run.Context(
        env=env, host=env, mode=run.OBSERVED, workspace="/B", repo="/repo",
        project="converge", integration_branch="main", answer_key={},
        # plan_record left at its default (None)
    )
    result = run.step_clauses(ctx)
    assert result.evidence["plan_record"] == "/B/HIGHWAY.md"
    assert result.evidence["plan_record_source"] == "legacy_fallback"
    clause_2 = next(r for r in result.evidence["clause_readings"] if r["clause"] == "Core 2")
    assert clause_2["verdict"] == run.PASS, clause_2["why"]
